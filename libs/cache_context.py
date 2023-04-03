#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2020/12/22 18:17 
Desc    : 解释一下吧
"""
import redis
from websdk2.consts import const
from websdk2.configs import configs

cache_conns = {}


def cache_conn(key=None, db=None):
    redis_configs = configs[const.REDIS_CONFIG_ITEM]

    if not key: key = const.DEFAULT_RD_KEY
    for config_key, redis_config in redis_configs.items():
        auth = redis_config[const.RD_AUTH_KEY]
        host = redis_config[const.RD_HOST_KEY]
        port = redis_config[const.RD_PORT_KEY]
        password = redis_config[const.RD_PASSWORD_KEY]

        db = db if db else redis_config[const.RD_DB_KEY]

        return_utf8 = False
        if const.RD_DECODE_RESPONSES in redis_config:
            return_utf8 = redis_config[const.RD_DECODE_RESPONSES]

        if isinstance(port, str): port = int(port)

        if auth:
            redis_pool = redis.ConnectionPool(host=host, port=port, db=db, password=password,
                                              decode_responses=return_utf8)
        else:
            redis_pool = redis.ConnectionPool(host=host, port=port, db=db, decode_responses=return_utf8)
        cache_conns[config_key] = redis.StrictRedis(connection_pool=redis_pool)
    return cache_conns[key]
