#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023/6/28 15:14
Desc    : 解释个锤子
"""

import json
from sqlalchemy import or_, func
from websdk2.cache_context import cache_conn
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.sqlalchemy_pagination import paginate
# from websdk2.model_utils import CommonOptView
from libs.feature_model_utils import CommonOptView
from models.paas_model import LoginLinkModel


class CustomOptView(CommonOptView):
    def __init__(self, model, **kwargs):
        super(CustomOptView, self).__init__(model, **kwargs)
        self.model = model

    def prepare(self):
        make_link_cache()


opt_obj = CustomOptView(LoginLinkModel)


def _get_value(value: str = None):
    if not value: return True
    return or_(
        LoginLinkModel.id == value,
        LoginLinkModel.name.like(f'%{value}%'),
        LoginLinkModel.code.like(f'%{value}%')
    )


def get_link_list_for_api(**params) -> dict:
    value = params.get('searchValue') if "searchValue" in params else params.get('searchVal')
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    if 'biz_id' in filter_map: filter_map.pop('biz_id')  # 暂时不隔离
    if 'page_size' not in params: params['page_size'] = 300  # 默认获取到全部数据
    with DBContext('r') as session:
        page = paginate(session.query(LoginLinkModel).filter(_get_value(value)).filter_by(**filter_map), **params)

    return dict(code=0, msg="获取成功", count=page.total, data=page.items)


def make_link_cache():
    with DBContext('r') as session:
        queryset = session.query(LoginLinkModel).all()
    link_map = dict()
    for link in queryset:
        link_map[link.code] = dict(
            login_url=link.login_url,
            real_url=link.real_url,
            client_id=link.client_id
        )
    redis_conn = cache_conn()
    redis_conn.set('LOGIN_LINK_MAP', json.dumps(link_map))


make_link_cache()
