#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
Author : shenshuo
Date   : 2017-10-11 12:58:26
Desc   : 配置文件
"""

import os
from websdk2.consts import const

ROOT_DIR = os.path.dirname(__file__)
debug = True
xsrf_cookies = False
expire_seconds = 365 * 24 * 60 * 60
cookie_secret = '61oETzKXQAGaYdkL5gEmGeJJFuYh7EQnp2X6TP1o/Vo='
token_secret = "pXFb44gfdh96(3df&%18iodGq4ODQyMzc4"
max_body_size = 3 * 1024 * 1024 * 1024
max_buffer_size = 3 * 1024 * 1024 * 1024
etcd_prefix = "/my/gw/"

DEFAULT_DB_DBHOST = os.getenv('DEFAULT_DB_DBHOST', '192.168.0.111')
DEFAULT_DB_DBPORT = os.getenv('DEFAULT_DB_DBPORT', 3306)
DEFAULT_DB_DBUSER = os.getenv('DEFAULT_DB_DBUSER', 'root')
DEFAULT_DB_DBPWD = os.getenv('DEFAULT_DB_DBPWD', '')
DEFAULT_DB_DBNAME = os.getenv('DEFAULT_DB_DBNAME', 'codo_admin')

READONLY_DB_DBHOST = os.getenv('READONLY_DB_DBHOST', '192.168.0.111')
READONLY_DB_DBPORT = os.getenv('READONLY_DB_DBPORT', 3306)
READONLY_DB_DBUSER = os.getenv('READONLY_DB_DBUSER', 'root')
READONLY_DB_DBPWD = os.getenv('READONLY_DB_DBPWD', '')
READONLY_DB_DBNAME = os.getenv('READONLY_DB_DBNAME', 'codo_admin')

DEFAULT_REDIS_HOST = os.getenv('DEFAULT_REDIS_HOST', '10.10.40.8')
DEFAULT_REDIS_PORT = os.getenv('DEFAULT_REDIS_PORT', 6379)
DEFAULT_REDIS_DB = os.getenv('DEFAULT_REDIS_DB', 7)
DEFAULT_REDIS_AUTH = os.getenv('DEFAULT_REDIS_AUTH', True)
DEFAULT_REDIS_CHARSET = os.getenv('DEFAULT_REDIS_CHARSET', 'utf-8')
DEFAULT_REDIS_PASSWORD = os.getenv('DEFAULT_REDIS_PASSWORD', '')

DEFAULT_ETCD_HOST_PORT = os.getenv('DEFAULT_ETCD_HOST_PORT', (("10.10.6.154", 2379), ("10.10.6.154", 2379)))
DEFAULT_ETCD_PROTOCOL = os.getenv('DEFAULT_ETCD_PROTOCOL', 'http')
DEFAULT_REDIS_USER = os.getenv('DEFAULT_REDIS_USER', None)
DEFAULT_ETCD_PASSWORD = os.getenv('DEFAULT_ETCD_PASSWORD', None)
api_gw = ""  # 网关
settings_auth_key = ""  # 服务之间认证
notice_conf_map = {}  # 通知中心使用
oss_data_private = {}  ### 上传私有仓库使用
###
uc_conf = {}  # 从用户中心同步数据
try:
    from local_settings import *
except:
    pass

settings = dict(
    debug=debug,
    xsrf_cookies=xsrf_cookies,
    cookie_secret=cookie_secret,
    token_secret=token_secret,
    expire_seconds=expire_seconds,
    max_body_size=max_body_size,
    max_buffer_size=max_buffer_size,
    uc_conf=uc_conf,
    api_gw=api_gw,
    settings_auth_key=settings_auth_key,
    notice_conf_map=notice_conf_map,
    oss_data_private=oss_data_private,
    etcd_prefix=etcd_prefix,
    app_name='codo_mg',
    databases={
        const.DEFAULT_DB_KEY: {
            const.DBHOST_KEY: DEFAULT_DB_DBHOST,
            const.DBPORT_KEY: DEFAULT_DB_DBPORT,
            const.DBUSER_KEY: DEFAULT_DB_DBUSER,
            const.DBPWD_KEY: DEFAULT_DB_DBPWD,
            const.DBNAME_KEY: DEFAULT_DB_DBNAME,
        },
        const.READONLY_DB_KEY: {
            const.DBHOST_KEY: READONLY_DB_DBHOST,
            const.DBPORT_KEY: READONLY_DB_DBPORT,
            const.DBUSER_KEY: READONLY_DB_DBUSER,
            const.DBPWD_KEY: READONLY_DB_DBPWD,
            const.DBNAME_KEY: READONLY_DB_DBNAME,
        }
    },
    redises={
        const.DEFAULT_RD_KEY: {
            const.RD_HOST_KEY: DEFAULT_REDIS_HOST,
            const.RD_PORT_KEY: DEFAULT_REDIS_PORT,
            const.RD_DB_KEY: DEFAULT_REDIS_DB,
            const.RD_AUTH_KEY: DEFAULT_REDIS_AUTH,
            const.RD_CHARSET_KEY: DEFAULT_REDIS_CHARSET,
            const.RD_PASSWORD_KEY: DEFAULT_REDIS_PASSWORD
        }
    },
    etcds={
        "DEFAULT_ETCD_KEY": {
            "DEFAULT_ETCD_HOST_PORT": DEFAULT_ETCD_HOST_PORT,
            "DEFAULT_ETCD_PROTOCOL": DEFAULT_ETCD_PROTOCOL,
            "DEFAULT_REDIS_USER": DEFAULT_REDIS_USER,
            "DEFAULT_ETCD_PASSWORD": DEFAULT_ETCD_PASSWORD,
        }
    }
)
