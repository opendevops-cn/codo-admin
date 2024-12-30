#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
author : shenshuo
date   : 2017年11月15日
role   : 权限同步和鉴定
"""
import datetime
import hashlib
import json
import logging
import time

import requests
from websdk2.db_context import DBContextV2 as DBContext
from libs.feature_model_utils import insert_or_update

from models.authority import Users
from settings import settings

try:
    requests.packages.urllib3.disable_warnings()
except:
    pass


def get_all_user():
    def md5hex(sign):
        md5 = hashlib.md5()  # 创建md5加密对象
        md5.update(sign.encode('utf-8'))  # 指定需要加密的字符串
        str_md5 = md5.hexdigest()  # 加密后的字符串
        return str_md5

    uc_conf = settings.get('uc_conf')
    if not isinstance(uc_conf, dict):
        uc_conf = json.loads(uc_conf)

    now = int(time.time())
    params = {
        "app_id": "devops",
        "sign": md5hex(uc_conf['app_id'] + str(now) + uc_conf['app_secret']),
        "token": uc_conf['token'],
        "timestamp": now
    }
    url = uc_conf['endpoint'] + "/api/all-users-4-outer"
    response = requests.get(url=url, params=params)
    res = response.json()
    print(res.get('message'))
    return res.get('data')


def sync_user_from_ucenter():
    def index():
        logging.info(f'async_all_user_redis_lock_key {datetime.datetime.now()}')
        with DBContext('w', None, True, **settings) as session:
            user_id_list = []
            for user in get_all_user():
                user_id = str(user.get('uid'))
                user_id_list.append(user_id)
                username = user.get('english_name')
                if not user.get('position'):
                    try:
                        session.query(Users).filter(Users.id == user_id).delete(synchronize_session=False)
                        session.commit()
                    except Exception as err:
                        print('del', err)
                    continue
                if username.startswith('wb-'): continue

                try:
                    session.add(insert_or_update(Users,
                                                 # f"username='{user_name}' and source_account_id='{user_id}' and nickname='{user.get('name')}'",
                                                 f"source_account_id='{user_id}'",
                                                 source_account_id=user_id, fs_id=user.get('feishu_userid'),
                                                 nickname=user.get('name'), manager=user.get('manager', ''),
                                                 department=user.get('position'), email=user.get('email'),
                                                 source="ucenter", tel=user.get('mobile'), status='0',
                                                 avatar=user.get('avatar'), username=user.get('english_name')))
                except Exception as err:
                    logging.info(f'async_all_user_redis_lock_key Exception {err}')

            session.query(Users).filter(Users.source == "ucenter", Users.status != "20",
                                        Users.source_account_id.notin_(user_id_list)).update(
                {"status": "20"}, synchronize_session=False)
        logging.info(f'async_all_user_redis_lock_key end ')

    index()


sync_user_from_ucenter()

# dict1 = api_permissions()
# dict2 = api_permissions_v2()
# # 对比两字典的每一对键值对
# for key in dict1.keys():
#     if key in dict2:
#         if dict1[key] != dict2[key]:
#             print(f"不一致Key: {key}, Dict1 Value: {dict1[key]}, Dict2 Value: {dict2[key]}")
#     else:
#         print(f"Key: {key}, Dict1 Value: {dict1[key]}, Dict2 Value: <not present>")
# #
# if dict1 == dict2:
#     print("The JSON objects are equal")
# else:
#     print("The JSON objects are different")
#
#
# def get_md5_hash(data):
#     # 将字典转换为排序后的 JSON 字符串
#     json_str = json.dumps(data, sort_keys=True)
#     # 计算 JSON 字符串的 MD5 哈希值
#     return hashlib.md5(json_str.encode()).hexdigest()
#
#
# hash1 = get_md5_hash(dict1)
# hash2 = get_md5_hash(dict2)
#
# print(f"Hash of dict1: {hash1}")
# print(f"Hash of dict2: {hash2}")
#
# if hash1 == hash2:
#     print("dict1 and dict2 are equal")
# else:
#     print("dict1 and dict2 are different")
