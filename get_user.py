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

from models.authority import Users
from settings import settings
from libs.ucenter_user_sync import upsert_ucenter_user_safe

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
            stats = {'created': 0, 'updated': 0, 'skipped': 0, 'error': 0}
            for user in get_all_user() or []:
                user_id = str(user.get('uid') or '')
                if user_id:
                    user_id_list.append(user_id)
                if not user.get('position'):
                    try:
                        # 无职位：历史逻辑按 id 删除（uid 与主键未必一致，保留原行为）
                        if user_id.isdigit():
                            session.query(Users).filter(Users.id == int(user_id)).delete(
                                synchronize_session=False
                            )
                            session.commit()
                    except Exception as err:
                        print('del', err)
                    continue

                result = upsert_ucenter_user_safe(session, user)
                stats[result] = stats.get(result, 0) + 1

            if user_id_list:
                session.query(Users).filter(
                    Users.source == "ucenter",
                    Users.status != "20",
                    Users.source_account_id.notin_(user_id_list),
                ).update({"status": "20"}, synchronize_session=False)
        logging.info(
            f'async_all_user_redis_lock_key end created={stats["created"]} '
            f'updated={stats["updated"]} skipped={stats["skipped"]} error={stats["error"]}'
        )

    index()


sync_user_from_ucenter()
