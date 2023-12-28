#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
author : shenshuo
date   : 2017年11月15日
role   : 权限同步和鉴定
"""
import time
import hashlib
import json
import datetime
import logging
from websdk2.cache_context import cache_conn
from models.authority import Users, UserRoles, RoleFunctions, Functions, UserToken
from settings import settings
from websdk2.tools import RedisLock
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.tools import now_timestamp, convert
from websdk2.jwt_token import gen_md5
from libs.etcd import Etcd3Client

import requests
from websdk2.model_utils import insert_or_update

try:
    requests.packages.urllib3.disable_warnings()
except:
    pass


def deco(cls, release=False):
    def _deco(func):
        def __deco(*args, **kwargs):
            if not cls.get_lock(cls, key_timeout=120, func_timeout=110): return False
            try:
                return func(*args, **kwargs)
            finally:
                ### 执行完就释放key，默认不释放
                if release: cls.release(cls)

        return __deco

    return _deco


def deco1(cls, release=False):
    def _deco(func):
        def __deco(*args, **kwargs):
            if not cls.get_lock(cls, key_timeout=180, func_timeout=30): return False
            try:
                return func(*args, **kwargs)
            finally:
                ### 执行完就释放key，默认不释放
                if release: cls.release(cls)

        return __deco

    return _deco


class MyVerify:
    def __init__(self, is_superuser=False, **kwargs):
        self.redis_conn = cache_conn()
        if "etcds" not in settings: raise SystemExit('找不到ETCD配置')
        self.etcd_dict = settings.get('etcds').get('DEFAULT_ETCD_KEY')
        self.etcd_prefix = settings.get('etcd_prefix', '/')
        self.crbac_prefix = f"{self.etcd_prefix}codorbac/"
        self.token_block_prefix = f"{self.etcd_prefix}tokenblock/"
        self.is_superuser = is_superuser
        self.method_list = ["GET", "POST", "PATCH", "DELETE", "PUT", "ALL"]

    @staticmethod
    def api_permissions():
        ### 超级用户网关直接放行
        api_permissions_dict = dict()
        with DBContext('r') as session:
            func_list = session.query(Functions.func_id, Functions.func_name, Functions.app_code, Functions.uri,
                                      Functions.method_type, UserRoles.user_id).outerjoin(
                RoleFunctions, Functions.func_id == RoleFunctions.func_id).outerjoin(
                UserRoles, RoleFunctions.role_id == UserRoles.role_id
            ).outerjoin(Users, UserRoles.user_id == Users.user_id).filter(Functions.status == '0',
                                                                          RoleFunctions.status == '0',
                                                                          UserRoles.status == '0',
                                                                          Users.status == "0").all()
        for func in func_list:
            key, val = f"{func[0]}---{func[1]}---{func[2]}---{func[3]}---{func[4]}", func[5]

            val_dict = api_permissions_dict.get(key)
            if val_dict and isinstance(val_dict, dict):
                api_permissions_dict[key] = {**val_dict, **{val: "y"}}
            else:
                api_permissions_dict[key] = {val: "y"}
        return api_permissions_dict

    @deco1(RedisLock("async_all_api_permission_redis_lock_key"))
    def sync_all_api_permission(self):
        ttl_id = now_timestamp()
        logging.info(f'sync_all_api_permission {ttl_id}, {datetime.datetime.now()}')
        client = Etcd3Client(hosts=self.etcd_dict.get('DEFAULT_ETCD_HOST_PORT'))

        api_data = self.api_permissions()
        client.ttl(ttl_id=ttl_id, ttl=720000)

        ###
        for k, v in api_data.items():
            func_id, func_name, app_code, uri, method = k.split('---')
            match_key = f"/{app_code}/{method}{uri}"
            value = {
                "name": func_name,
                "time": now_timestamp(),
                "key": match_key,
                "uri": uri,
                "method": method,
                "func_id": func_id,
                "app_code": app_code,
                "status": 1,
                "rules": v
            }
            key = f"{self.crbac_prefix}{func_id}{match_key}"
            client.put(key, json.dumps(value), lease=ttl_id)

    @deco(RedisLock("async_diff_api_permission_redis_lock_key"))
    def sync_diff_api_permission(self):
        ttl_id = now_timestamp()
        logging.info(f'sync_diff_api_permission {ttl_id}, {datetime.datetime.now()}')
        client = Etcd3Client(hosts=self.etcd_dict.get('DEFAULT_ETCD_HOST_PORT'))

        api_data = self.api_permissions()
        client.ttl(ttl_id=ttl_id, ttl=7200)
        ###
        api_permission_new_dict = {}
        api_permission_dict_key = "api_permission_dict_key"
        api_permission_old_dict = self.redis_conn.hgetall(api_permission_dict_key)

        for k, v in api_data.items():
            k_md5 = gen_md5(k)
            v_md5 = gen_md5(json.dumps(v))
            api_permission_new_dict[k_md5] = v_md5

        self.redis_conn.hmset(api_permission_dict_key, api_permission_new_dict)
        self.redis_conn.expire(api_permission_dict_key, 120)
        api_permission_old_dict = convert(api_permission_old_dict)

        if api_permission_new_dict == api_permission_old_dict: return

        for k, v in api_data.items():
            func_id, func_name, app_code, uri, method = k.split('---')
            k_md5 = gen_md5(k)
            v_md5 = gen_md5(json.dumps(v))
            match_key = f"/{app_code}/{method}{uri}"
            value = {
                "name": func_name,
                "time": now_timestamp(),
                "key": match_key,
                "uri": uri,
                "method": method,
                "func_id": func_id,
                "app_code": app_code,
                "status": 1,
                "rules": v
            }
            key = f"{self.crbac_prefix}{func_id}{match_key}"
            ########
            if k_md5 in api_permission_old_dict:
                if v_md5 != api_permission_old_dict.get(k_md5):
                    # print(f'{k}   ####API关联关系改变，要更新一下')
                    client.put(key, json.dumps(value), lease=ttl_id)
            else:
                # print(f'{k}    ####新API  要更新一下')
                client.put(key, json.dumps(value), lease=ttl_id)

    ##################################################################
    @deco(RedisLock("async_token_block_list_redis_lock_key"))
    def token_block_list(self):
        ttl_id = now_timestamp()
        logging.info(f'async_token_block_list {ttl_id}, {datetime.datetime.now()}')
        with DBContext('r') as session:
            token_info = session.query(UserToken.token_md5).filter(UserToken.status != '0').all()

        client = Etcd3Client(hosts=self.etcd_dict.get('DEFAULT_ETCD_HOST_PORT'))
        client.ttl(ttl_id=ttl_id, ttl=86400)  ### 一天
        block_dict = {}
        for token_md5 in token_info:
            token_md5 = token_md5[0]
            block_dict[token_md5] = 'y'

        client.put(f'{self.token_block_prefix}block', json.dumps(block_dict), lease=ttl_id)
