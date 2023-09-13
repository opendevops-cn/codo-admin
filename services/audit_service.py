#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023/7/10 15:14
Desc    : 审计日志
"""

import json
from websdk2.utils.date_format import date_format_to8
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.sqlalchemy_pagination import paginate
from models.paas_model import OperationRecords


def get_opt_log_list_v4(**params) -> dict:
    key = params.get('key')
    value = params.get('value')
    start_date = params.get('start_date')
    end_date = params.get('end_date')
    filter_map = params.get('filter_map')
    filter_map = json.loads(filter_map) if filter_map else {}
    if key and value:
        filter_map = {key: value}
    start_time_tuple, end_time_tuple = date_format_to8(start_date, end_date)

    with DBContext('r') as session:
        page = paginate(session.query(OperationRecords).filter(
            OperationRecords.create_time.between(start_time_tuple, end_time_tuple)).filter_by(**filter_map), **params)

    return dict(code=0, msg="获取成功", count=page.total, data=page.items)
