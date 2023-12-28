#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2018/12/24
Desc    : 数据表生成
"""

# from models.notice_model import Base
from models.paas_model import Base as AppsBase
from models.authority import Base as AuBase
from websdk2.consts import const
from settings import settings as app_settings
# ORM创建表结构
from sqlalchemy import create_engine

default_configs = app_settings[const.DB_CONFIG_ITEM][const.DEFAULT_DB_KEY]
# engine = create_engine('mysql+pymysql://%s:%s@%s:%s/%s?charset=utf8mb4' % (
#     default_configs.get(const.DBUSER_KEY),
#     default_configs.get(const.DBPWD_KEY),
#     default_configs.get(const.DBHOST_KEY),
#     default_configs.get(const.DBPORT_KEY),
#     default_configs.get(const.DBNAME_KEY),
# ), echo=True)

engine = create_engine(
    f'mysql+pymysql://{default_configs.get(const.DBUSER_KEY)}:{default_configs.get(const.DBPWD_KEY)}@{default_configs.get(const.DBHOST_KEY)}:{default_configs.get(const.DBPORT_KEY)}/{default_configs.get(const.DBNAME_KEY)}',
    echo=True)


def create():
    # Base.metadata.create_all(engine)
    AuBase.metadata.create_all(engine)
    AppsBase.metadata.create_all(engine)
    print('[Success] 表结构创建成功!')


def drop():
    # Base.metadata.drop_all(engine)
    AuBase.metadata.drop_all(engine)
    AppsBase.metadata.drop_all(engine)


if __name__ == '__main__':
    create()
