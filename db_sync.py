#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2018/12/24
Desc    : 
"""

from models.admin_model import Base as Abase
from models.notice_model import Base
from models.biz_model import Base as Bbase
from models.authority_model import Base as AuthBase
from websdk2.consts import const
from settings import settings as app_settings
# ORM创建表结构
from sqlalchemy import create_engine

default_configs = app_settings[const.DB_CONFIG_ITEM][const.DEFAULT_DB_KEY]
engine = create_engine('mysql+pymysql://%s:%s@%s:%s/%s?charset=utf8' % (
    default_configs.get(const.DBUSER_KEY),
    default_configs.get(const.DBPWD_KEY),
    default_configs.get(const.DBHOST_KEY),
    default_configs.get(const.DBPORT_KEY),
    default_configs.get(const.DBNAME_KEY),
), encoding='utf-8', echo=True)


def create():
    Base.metadata.create_all(engine)
    Abase.metadata.create_all(engine)
    Bbase.metadata.create_all(engine)
    # AuthBase.metadata.create_all(engine)
    print('[Success] 表结构创建成功!')


def drop():
    Base.metadata.drop_all(engine)
    Abase.metadata.drop_all(engine)
    Bbase.metadata.drop_all(engine)
    # AuthBase.metadata.drop_all(engine)


if __name__ == '__main__':
    create()
