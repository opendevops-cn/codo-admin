#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2020/12/10 15:14
Desc    : 解释个锤子
"""
from sqlalchemy import or_, func
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.sqlalchemy_pagination import paginate
from models.authority import UserToken


def _get_value(value: str = None):
    if not value: return True
    return or_(
        UserToken.user_id == value,
        UserToken.details.like(f'%{value}%'),
        UserToken.nickname.like(f'%{value}%'),
        UserToken.token == value
    )


def get_token_list_for_api(params) -> dict:
    value = params.get('searchValue') if "searchValue" in params else params.get('searchVal')
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    if 'biz_id' in filter_map: filter_map.pop('biz_id')  # 暂时不隔离
    if 'page_size' not in params: params['page_size'] = 300  # 默认获取到全部数据
    with DBContext('r') as session:
        page = paginate(session.query(UserToken).filter(_get_value(value)).filter_by(**filter_map), **params)

    queryset = []
    for msg in page.items:
        msg['token'] = f"{msg.get('token')[0:10]} --------  {msg.get('token')[-10:]}"
        queryset.append(msg)
    return dict(code=0, msg="获取成功", count=page.total, data=queryset)
