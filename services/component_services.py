#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2020/12/10 15:14
Desc    : 解释一下吧
"""

from sqlalchemy import or_
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.sqlalchemy_pagination import paginate
from models.authority import Components, RolesComponents
from libs.feature_model_utils import CommonOptView, queryset_to_list

opt_obj = CommonOptView(Components)


def _get_value(value: str = None):
    if not value: return True
    return or_(
        Components.id == value,
        Components.details.like(f'%{value}%'),
        Components.name.like(f'%{value}%'),
        Components.app_code == value
    )


def _get_by_app_code(app_code: str = None):
    """过滤筛选"""
    if not app_code:
        return True

    return or_(
        Components.app_code == app_code
    )


def get_component_list_for_api(**params) -> dict:
    value = params.get('searchValue') if "searchValue" in params else params.get('searchVal')
    app_code = params.get('app_code')
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    if 'biz_id' in filter_map: filter_map.pop('biz_id')  # 暂时不隔离
    if 'page_size' not in params: params['page_size'] = 300  # 默认获取到全部数据
    with DBContext('r') as session:
        page = paginate(session.query(Components).filter(_get_value(value), _get_by_app_code(app_code)
                                                         ).filter_by(**filter_map), **params)

    return dict(code=0, msg="获取成功", count=page.total, data=page.items)


def get_component_list_for_role(role_id: int) -> list:
    with DBContext('r') as db:
        role_func = db.query(Components).outerjoin(RolesComponents, Components.id == RolesComponents.comp_id
                                                   ).filter(RolesComponents.role_id == role_id).all()

    return queryset_to_list(role_func)
