#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
author : shenshuo
date   : 2017年11月15日
role   : 权限同步和鉴定
"""
import time
import hashlib
import datetime

from models.admin_model import Users
from models.authority import Users
from settings import settings

from websdk2.web_logs import ins_log
from websdk2.db_context import DBContextV2 as DBContext

import requests
from websdk2.model_utils import insert_or_update

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

    now = int(time.time())
    params = {
        "app_id": "devops",
        "sign": md5hex(uc_conf['app_id'] + str(now) + uc_conf['app_secret']),
        "token": uc_conf['token'],
        "timestamp": now
    }
    url = uc_conf['endpoint'] + "/api/all-users"
    response = requests.get(url=url, params=params)
    res = response.json()
    print(res.get('message'))
    return res.get('data')


def sync_user_from_ucenter():
    def index():
        ins_log.read_log('info', f'async_all_user_redis_lock_key {datetime.datetime.now()}')
        with DBContext('w', None, True, **settings) as session:
            for user in get_all_user():
                user_id = str(user.get('uid'))
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
                    ins_log.read_log('info', f'\n async_all_user_redis_lock_key Exception {err}')
        ins_log.read_log('info', f'async_all_user_redis_lock_key end ')

    index()


sync_user_from_ucenter()
