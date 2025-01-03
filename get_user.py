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
from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning
from websdk2.db_context import DBContextV2 as DBContext
from libs.feature_model_utils import insert_or_update

from models.authority import Users
from settings import settings

disable_warnings(InsecureRequestWarning)


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
    logging.info(res.get('message'))
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
