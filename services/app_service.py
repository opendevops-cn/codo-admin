#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023/07/10 15:14
Desc    : 解释一下吧
"""

from sqlalchemy import or_
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.sqlalchemy_pagination import paginate
from models.paas_model import AppsModel
from websdk2.model_utils import CommonOptView

opt_obj = CommonOptView(AppsModel)


def get_apps_list_for_main(**params) -> dict:
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    params['page_size'] = 300  # 默认获取到全部数据
    with DBContext('r') as session:
        page = paginate(session.query(AppsModel).filter_by(**filter_map), **params)
    return dict(code=0, msg='获取成功', data=page.items, count=page.total)


def _get_value(value: str = None):
    if not value:
        return True
    return or_(
        AppsModel.name.like(f'%{value}%'),
        AppsModel.code.like(f'%{value}%'),
        AppsModel.path.like(f'%{value}%'),
    )


def get_apps_list_for_api(**params) -> dict:
    value = params.get('searchValue') if "searchValue" in params else params.get('searchVal')
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    if 'biz_id' in filter_map:
        filter_map.pop('biz_id')  # 暂时不隔离
    if 'page_size' not in params:
        params['page_size'] = 300  # 默认获取到全部数据
    with DBContext('r') as session:
        page = paginate(session.query(AppsModel).filter(_get_value(value)).filter_by(**filter_map), **params)
    return dict(msg='获取成功', code=0, count=page.total, data=page.items)
