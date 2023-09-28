#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2020/12/10 15:14
Desc    : 解释一下吧
"""

import json
from loguru import logger
from sqlalchemy import or_
from websdk2.tools import RedisLock
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.sqlalchemy_pagination import paginate
from websdk2.cache_context import cache_conn
from models.authority import Roles, UserRoles, Users
from libs.feature_model_utils import CommonOptView

opt_obj = CommonOptView(Roles)
ROLE_USER_INFO_STR = "ROLE_USER_INFO_STR"


def _get_value(value: str = None):
    if not value:
        return True
    return or_(
        Roles.id == value,
        Roles.role_name.like(f'%{value}%'),
        Roles.role_type == value
    )


def _get_role_type(value: str = None):
    if not value:
        return True
    return or_(
        Roles.role_type == value
    )


def get_role_list_for_api(**params) -> dict:
    value = params.get('searchValue') if "searchValue" in params else params.get('searchVal')
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    if 'biz_id' in filter_map: filter_map.pop('biz_id')  # 暂时不隔离
    if 'page_size' not in params: params['page_size'] = 300  # 默认获取到全部数据
    role_type = params.get('role_type')
    with DBContext('r') as session:
        page = paginate(
            session.query(Roles).filter(_get_role_type(role_type), _get_value(value)).filter_by(**filter_map), **params)

    return dict(code=0, msg='获取成功', data=page.items, count=page.total)


def get_normal_role_list_for_api(**params) -> dict:
    value = params.get('searchValue') if "searchValue" in params else params.get('searchVal')
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    if 'biz_id' in filter_map: filter_map.pop('biz_id')  # 暂时不隔离
    if 'page_size' not in params: params['page_size'] = 300  # 默认获取到全部数据
    with DBContext('r') as session:
        page = paginate(session.query(Roles).filter(Roles.role_type == 'normal').filter(
            _get_value(value)).filter_by(**filter_map), **params)

    return dict(code=0, msg='获取成功', data=page.items, count=page.total)


def get_base_role_list_for_api(**params) -> dict:
    params['page_size'] = 300  # 默认获取到全部数据
    with DBContext('r') as session:
        page = paginate(session.query(Roles).filter(Roles.role_type == 'base'), **params)

    return dict(code=0, msg='获取成功', data=page.items, count=page.total)


# 通过角色查找用户
def get_users_for_role(**kwargs) -> dict:
    role_id = kwargs.get('role_id')
    if not role_id:
        return dict(code=-1, msg='角色ID 不能为空')
    dict_list = ['user_role_id', 'role_id', 'user_id', 'username', 'nickname', 'email', 'source']
    with DBContext('r') as session:
        count = session.query(UserRoles).filter(UserRoles.role_id == role_id).count()
        role_info = session.query(UserRoles.id, UserRoles.role_id, UserRoles.user_id, Users.username,
                                  Users.nickname, Users.email, Users.source).outerjoin(Users,
                                                                                       Users.id == UserRoles.user_id).filter(
            UserRoles.role_id == role_id, Users.status == '0').order_by(UserRoles.role_id).all()

    queryset = [dict(zip(dict_list, msg)) for msg in role_info]
    return dict(code=0, msg='获取成功', data=queryset, count=count)


def get_all_user_list_for_role(**kwargs):
    role_user_dict = dict()
    role_id_user_dict = dict()
    with DBContext('r') as session:
        role_info = session.query(Roles.id, Roles.role_name, Users.username, Users.nickname, Users.id).outerjoin(
            UserRoles, UserRoles.role_id == Roles.id).outerjoin(
            Users, Users.id == UserRoles.user_id).filter(Roles.status == '0', Users.status == '0').all()

    for msg_tuple in role_info:
        role_id = msg_tuple[0]
        role_name = msg_tuple[1]
        username = msg_tuple[2]
        nickname = msg_tuple[3]
        user_id = msg_tuple[4]
        val_dict = role_user_dict.get(role_name)
        if val_dict and isinstance(val_dict, dict):
            role_user_dict[role_name] = {**val_dict, **{f"{username}({nickname})": "y"}}
        else:
            role_user_dict[role_name] = {f"{username}({nickname})": "y"}

        val_dict2 = role_id_user_dict.get(role_id)
        if val_dict2 and isinstance(val_dict2, dict):
            role_id_user_dict[role_id] = {**val_dict2, **{user_id: "y"}}
        else:
            role_id_user_dict[role_id] = {user_id: "y"}
        redis_conn = cache_conn()
        redis_conn.set(ROLE_USER_INFO_STR, json.dumps(role_id_user_dict))
    return role_user_dict


def role_sync_all():
    from libs.sync_user_verift_v4 import MyVerify
    from services.biz_service import sync_biz_role_user
    obj = MyVerify()
    obj.sync_all_permission()
    get_all_user_list_for_role()
    sync_biz_role_user()
    # 同步角色对应的用户 生成缓存字典
    # RBAC权限生成ACL到ETCD
    # 推送业务角色信息到数据库和缓存
    return True
