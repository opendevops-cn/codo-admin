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
from websdk2.model_utils import queryset_to_list, model_to_dict, GetInsertOrUpdateObj
from websdk2.utils.pydantic_utils import sqlalchemy_to_pydantic, ValidationError, PydanticDel, BaseModel
from websdk2.sqlalchemy_pagination import paginate
from models.authority_model import Menus, Functions, Components, Apps, Roles, Users, UserRoles, UserToken, OperationRecord, \
    FavoritesModel, Groups, UserGroups, RolesMutual, RolesInherit, GroupRoles, OperationLogs, SyncLogs, RoleApp, \
    RoleBusiness, RoleMenu, RoleComponent, RoleFunction, Resources, SubscribeRole, GroupsRelate
from websdk2.cache_context import cache_conn

from models.biz_model import BusinessModel

def get_apps_list(**params) -> tuple:
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    if 'resource_group' in filter_map: filter_map.pop('resource_group')
    params['page_size'] = 300  ### 默认获取到全部数据
    with DBContext('r') as session:
        page = paginate(session.query(Apps).filter_by(**filter_map), **params)
    return page.total, page.items


def get_app_list_v2(**params) -> tuple:
    value = params.get('searchValue') if "searchValue" in params else params.get('value')
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    if "app_code" in params: filter_map['app_code'] = params.get('app_code')
    if 'resource_group' in filter_map: filter_map.pop('resource_group')

    params['page_size'] = 300  ### 默认获取到全部数据
    nickname = params.get('nickname')
    queryset = []

    with DBContext('r') as session:
        if value:
            page = paginate(session.query(Apps).filter_by(**filter_map).filter(
                or_(Apps.app_code == value, Apps.app_name.like(f'%{value}%'), Apps.path.like(f'%{value}%'))), **params)
        else:
            page = paginate(session.query(Apps).filter_by(**filter_map), **params)

    if params.get('is_super') is not True and params.get('all') != 'yes':
        for i in page.items:
            user_list = i['user_list']
            if user_list and isinstance(user_list, list) and nickname in user_list:
                queryset.append(i)
    else:
        queryset = page.items

    return page.total, queryset
