#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2020/12/10 15:14
Desc    : 解释一下吧
"""

from sqlalchemy import or_, and_, func, desc, case
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.sqlalchemy_pagination import paginate
# from models.authority_model import Roles, UserRoles, Groups, UserGroups, GroupRoles
from models.authority import Users
from websdk2.model_utils import CommonOptView

opt_obj = CommonOptView(Users)


def _get_value(value: str = None):
    if not value: return True
    return or_(
        Users.id == value,
        Users.username.like(f'%{value}%'),
        Users.email.like(f'%{value}%'),
        Users.tel.like(f'%{value}%'),
        Users.department.like(f'%{value}%'),
        Users.source_account_id.like(f'%{value}%'),
        Users.nickname.like(f'%{value}%')
    )


def get_user_list_v3(**params) -> tuple:
    value = params.get('searchValue') if "searchValue" in params else params.get('searchVal')
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    if 'biz_id' in filter_map: filter_map.pop('biz_id')  # 暂时不隔离
    if 'page_size' not in params: params['page_size'] = 300  # 默认获取到全部数据
    with DBContext('r') as session:
        page = paginate(session.query(Users).filter(_get_value(value)).filter_by(**filter_map), **params)

    queryset = []
    for msg in page.items:
        data_dict = dict()
        data_dict['id'] = msg.get('id')
        data_dict['username'] = msg.get('username')
        data_dict['nickname'] = msg.get('nickname')
        data_dict['email'] = msg.get('email')
        queryset.append(data_dict)

    return page.total, queryset


def get_user_list_v2(**params) -> tuple:
    value = params.get('searchValue') if "searchValue" in params else params.get('searchVal')
    # params["items_not_to_list"] = "yes"
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    if 'resource_group' in filter_map: filter_map.pop('resource_group')
    if 'biz_id' in filter_map: filter_map.pop('biz_id')
    if 'page_size' not in params:
        params['page_size'] = 300  # 默认获取到全部数据

    with DBContext('r') as session:
        page = paginate(session.query(Users).filter_by(**filter_map).filter(_get_value(value)), **params)

    queryset = []
    for data_dict in page.items:
        # data_dict = model_to_dict(msg)
        data_dict.pop('password')
        data_dict.pop('google_key')
        queryset.append(data_dict)

    return page.total, queryset


def get_group_list_for_user(**kwargs):
    """获取用户的用户组"""
    user_id = kwargs.get('user_id')
    user_name = kwargs.get('user_name')
    if not user_id and not user_name:
        return 0, []
    dict_list = ['group_id', 'group_name']
    with DBContext('r') as session:
        if not user_id and user_name:
            user = session.query(Users.user_id).filter(Users.username == user_name).first()
            if not user:
                return 0, []
            user_id = user[0]
        group_info = session.query(Groups.group_id, Groups.group_name).outerjoin(UserGroups,
                                                                                 Groups.group_id == UserGroups.group_id) \
            .outerjoin(Users, Users.user_id == UserGroups.user_id).filter(Users.user_id == user_id).all()
    queryset = [dict(zip(dict_list, msg)) for msg in group_info]
    count = len(queryset)
    return count, queryset


def get_role_list_for_user(**kwargs):
    """获取用户的角色"""
    user_id = kwargs.get('user_id')
    user_name = kwargs.get('user_name')
    if not user_id and not user_name:
        return 0, []
    dict_list = ['role_id', 'role_name']
    with DBContext('r') as session:
        if not user_id and user_name:
            user = session.query(Users.user_id).filter(Users.username == user_name).first()
            if not user:
                return 0, []
            user_id = user[0]

        role_info = session.query(Roles.role_id, Roles.role_name).outerjoin(UserRoles,
                                                                            Roles.role_id == UserRoles.role_id) \
            .outerjoin(Users, Users.user_id == UserRoles.user_id).filter(Users.user_id == user_id, Roles.status == '0',
                                                                         UserRoles.status == '0',
                                                                         Users.status == '0').all()

        group_list = session.query(Groups.group_id, Groups.group_name).outerjoin(UserGroups,
                                                                                 Groups.group_id == UserGroups.group_id) \
            .outerjoin(Users, Users.user_id == UserGroups.user_id).filter(Users.user_id == user_id,
                                                                          Groups.status == '0',
                                                                          UserGroups.status == '0',
                                                                          Users.status == '0').all()
        group_list = [g[0] for g in group_list]

        role_info.extend(session.query(Roles.role_id, Roles.role_name).outerjoin(GroupRoles,
                                                                                 Roles.role_id == GroupRoles.role_id) \
                         .outerjoin(Groups, Groups.group_id == GroupRoles.group_id).filter(
            Groups.group_id.in_(group_list), Groups.status == '0', Roles.status == '0', GroupRoles.status == '0').all())

    role_info = list(set(role_info))
    queryset = [dict(zip(dict_list, msg)) for msg in role_info]
    count = len(queryset)
    return count, queryset
