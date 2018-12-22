#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2018/12/11
Desc    : 
"""

from models.app_config import AppSettings, model_to_dict
from websdk.db_context import DBContext
from websdk.consts import const
from websdk.cache_context import cache_conn

def configs_init(setting_key):
    new_dict = {}
    """返回所有数据"""
    with DBContext('r') as session:
        if setting_key == 'all':
            conf_info = session.query(AppSettings).all()
        else:
            conf_info = session.query(AppSettings).filter(AppSettings.name.like(setting_key + '%')).all()

    for msg in conf_info:
        data_dict = model_to_dict(msg)
        new_dict[data_dict.get('name')] = data_dict.get('value')
    if new_dict:
        redis_conn = cache_conn()
        redis_conn.hmset(const.APP_SETTINGS, new_dict)
    return dict(code=0, msg='获取配置成功', data=new_dict)