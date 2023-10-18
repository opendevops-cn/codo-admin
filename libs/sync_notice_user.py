#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2021/1/14 15:46 
Desc    : 解释一下吧
"""

import json
import datetime
from websdk2.cache_context import cache_conn
from models.admin_model import Users
from models.notice_model import NoticeTemplate, NoticeGroup
from websdk2.jwt_token import gen_md5
from websdk2.consts import const
from websdk2.tools import RedisLock
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.model_utils import model_to_dict


def deco(cls, release=False):
    def _deco(func):
        def __deco(*args, **kwargs):
            if not cls.get_lock(cls, key_timeout=90, func_timeout=1): return False
            try:
                return func(*args, **kwargs)
            finally:
                ### 执行完就释放key，默认不释放
                if release: cls.release(cls)

        return __deco

    return _deco


def deco1(cls, release=False):
    ### 180
    def _deco(func):
        def __deco(*args, **kwargs):
            if not cls.get_lock(cls, key_timeout=120, func_timeout=1): return False
            try:
                return func(*args, **kwargs)
            finally:
                ### 执行完就释放key，默认不释放
                if release: cls.release(cls)

        return __deco

    return _deco


class NoticeUserInfo:
    def __init__(self, **kwargs):
        pass

    @deco(RedisLock("async__user_info_redis_lock_key"))
    def cache_user(self):
        redis_conn = cache_conn()
        # ins_log.read_log('info', f'async__user_info_to_redis, {datetime.datetime.now()}')
        with DBContext('r') as session:
            all_user = session.query(Users).filter(Users.status == '0').all()
        try:
            with redis_conn.pipeline(transaction=False) as p:
                p.delete(const.USERS_INFO)
                for msg in all_user:
                    data_dict = model_to_dict(msg)
                    if 'password' in data_dict: data_dict.pop('password')
                    if 'google_key' in data_dict: data_dict.pop('google_key')
                    # nickname = data_dict.get('nickname')
                    # nickname_key = f"{gen_md5(nickname)}__contact"
                    # p.hmset(nickname_key, {"tel": data_dict.get('tel'), "email": data_dict.get('email')})
                    p.rpush(const.USERS_INFO, json.dumps(data_dict))
                p.execute()
        except Exception as err:
            pass

    def sync(self):
        with DBContext('r') as session:
            __info = session.query(NoticeTemplate.id, NoticeTemplate.user_list, NoticeTemplate.notice_group).all()

        all_info = []
        for i in __info:
            tel_list = []
            email_list = []
            ddid_list = []  ### 钉钉ID
            manager_list = []  ### 上级领导

            notice_id = i[0]
            notice_group_list = i[2]
            notice_user = []

            ### 处理通知组
            if notice_group_list and isinstance(notice_group_list, list):
                group_info = session.query(NoticeGroup.user_list).filter(NoticeGroup.name.in_(notice_group_list)).all()
                for group in group_info:
                    if group[0]: notice_user = notice_user + group[0]

            ### 处理通知用户
            user_list = i[1]
            if user_list and isinstance(user_list, list):
                notice_user = notice_user + user_list

            nickname_list = list(set(notice_user))
            with DBContext('r') as session:
                notice_user_info = session.query(Users.tel, Users.email, Users.dd_id, Users.manager).filter(
                    Users.nickname.in_(nickname_list)).all()

            for u in notice_user_info:
                if u[0]: tel_list.append(u[0])
                if u[1]: email_list.append(u[1])
                if u[2]: ddid_list.append(u[2])
                if u[3]: manager_list.append(u[3])

            user_info = {'tel': tel_list, 'email': email_list, 'dd_id': ddid_list}

            ##处理用户上级的逻辑
            try:
                manager_tel_list = []
                manager_email_list = []
                manager_ddid_list = []  ### 钉钉ID

                manager_list2 = []
                for m in manager_list:
                    manager_list2.extend(m.split(','))
                manager_list3 = [m2.split('(')[0] for m2 in manager_list2]
                with DBContext('r') as session:
                    notice_manager_info = session.query(Users.tel, Users.email, Users.dd_id).filter(
                        Users.username.in_(manager_list3)).all()
                for u in notice_manager_info:
                    if u[0]: manager_tel_list.append(u[0])
                    if u[1]: manager_email_list.append(u[1])
                    if u[2]: manager_ddid_list.append(u[2])
                manager_info = {'tel': manager_tel_list, 'email': manager_email_list, 'dd_id': manager_ddid_list}
            except:
                manager_info = {}

            all_info.append({"id": notice_id, "user_info": user_info, "manager_info": manager_info})
        with DBContext('w', None, True) as session:
            session.bulk_update_mappings(NoticeTemplate, all_info)

    @deco1(RedisLock("async_notice_user_info_redis_lock_key"))
    def index(self):
        # ins_log.read_log('info', f'async_notice_user_info, {datetime.datetime.now()}')
        self.sync()
