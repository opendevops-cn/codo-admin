#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2018/12/24
Desc    : 数据表生成
"""

from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL
from websdk2.consts import const
from settings import settings as app_settings
from models.paas_model import Base as AppsBase
from models.authority import Base as AuBase

# ORM创建表结构

default_configs = app_settings[const.DB_CONFIG_ITEM][const.DEFAULT_DB_KEY]

url_object = URL.create(
    drivername='mysql+pymysql',
    username=default_configs.get(const.DBUSER_KEY),
    password=default_configs.get(const.DBPWD_KEY),
    host=default_configs.get(const.DBHOST_KEY),
    port=int(default_configs.get(const.DBPORT_KEY)),
    database=default_configs.get(const.DBNAME_KEY),
    query={'charset': 'utf8mb4'}
)
engine = create_engine(url_object, echo=True)


def create():
    try:
        AuBase.metadata.create_all(engine)
        AppsBase.metadata.create_all(engine)
        print('[Success] 表结构创建成功!')
    except Exception as err:
        print(f'[Error] {err}!')


def drop():
    AuBase.metadata.drop_all(engine)
    AppsBase.metadata.drop_all(engine)


if __name__ == '__main__':
    create()
