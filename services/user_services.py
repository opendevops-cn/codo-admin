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
from models.authority import Users, Roles, UserRoles
# from websdk2.model_utils import CommonOptView
from libs.feature_model_utils import CommonOptView

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
        data_dict.pop('password')
        data_dict.pop('google_key')
        queryset.append(data_dict)

    return page.total, queryset


def get_user_noc_addr(users_str: str, roles_str: str) -> dict:
    notice_user = []

    with DBContext('r') as session:

        if users_str and isinstance(users_str, str):
            user_list = users_str.split(',')
            notice_user = notice_user + user_list

        if roles_str and isinstance(roles_str, str):
            role_id_list = roles_str.split(',')
            __role_info = session.query(Users).outerjoin(UserRoles, UserRoles.user_id == Users.id).filter(
                UserRoles.role_id.in_(role_id_list), Users.status == '0').all()

            role_user_list = [u.username for u in __role_info]
            notice_user = notice_user + role_user_list

        nickname_list = list(set(notice_user))

        tel_list = []
        email_list = []
        ddid_list = []
        fsid_list = []

        __nickname_info = session.query(Users.tel, Users.email, Users.dd_id, Users.fs_id).filter(
            or_(Users.id.in_(nickname_list), Users.nickname.in_(nickname_list),
                Users.username.in_(nickname_list))).all()

        for u in __nickname_info:
            if u[0]: tel_list.append(u[0])
            if u[1]: email_list.append(u[1])
            if u[2]: ddid_list.append(u[2])
            if u[3]: fsid_list.append(u[3])

    user_addr_info = {'tel': tel_list, 'email': email_list, 'dd_id': ddid_list, 'fs_id': fsid_list}
    return dict(code=0, msg='获取成功', data=user_addr_info)
