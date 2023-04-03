#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2020/12/10 15:14
Desc    : 解释一下吧
"""
from typing import List
from sqlalchemy import or_, and_, func, desc, case
from sqlalchemy.exc import IntegrityError
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.model_utils import model_to_dict
from websdk2.utils.pydantic_utils import sqlalchemy_to_pydantic, ValidationError, PydanticDel, BaseModel
from websdk2.sqlalchemy_pagination import paginate
from models.authority_model import Roles, Users, UserRoles, Groups, UserGroups, GroupRoles

PydanticUsers = sqlalchemy_to_pydantic(Users, exclude=['user_id'])
PydanticUserUP = sqlalchemy_to_pydantic(Users)


class PydanticUserDel(BaseModel):
    user_id: int
    user_list: List[int] = None


def _get_value(value: str = None):
    if not value: return True
    return or_(
        Users.user_id == value,
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
    if 'biz_id' in filter_map: filter_map.pop('biz_id')  ### 暂时不隔离
    if 'page_size' not in params: params['page_size'] = 300  ### 默认获取到全部数据
    with DBContext('r') as session:
        page = paginate(session.query(Users).filter(_get_value(value)).filter_by(**filter_map), **params)

    queryset = []
    for msg in page.items:
        data_dict = dict()
        data_dict['user_id'] = msg.user_id
        data_dict['nickname'] = msg.nickname
        data_dict['nickname'] = msg.nickname
        queryset.append(data_dict)

    return page.total, queryset


def add_user(data: dict):
    try:
        PydanticUsers(**data)
    except ValidationError as e:
        return dict(code=-1, msg=str(e))

    try:
        with DBContext('w', None, True) as db:
            db.add(Users(**data))
    except IntegrityError as e:
        return dict(code=-2, msg='不要重复添加')

    except Exception as e:
        return dict(code=-3, msg=f'{e}')

    return dict(code=0, msg="创建成功")


def del_user(data: dict):
    try:
        valid_data = PydanticDel(**data)
    except ValidationError as e:
        return dict(code=-1, msg=str(e))

    try:
        with DBContext('w', None, True) as db:
            db.query(Users).filter(Users.id == valid_data.id).delete(
                synchronize_session=False)
    except Exception as err:
        return dict(code=-3, msg=f'删除失败, {str(err)}')

    return dict(code=0, msg="删除成功")


###
# 用户
def get_user_list_v2(**params) -> tuple:
    value = params.get('searchValue') if "searchValue" in params else params.get('value')
    params["items_not_to_list"] = "yes"
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    filter_map['status'] = '0'
    if 'resource_group' in filter_map: filter_map.pop('resource_group')
    if 'biz_id' in filter_map: filter_map.pop('biz_id')  ### 暂时不隔离

    ignore_info = params.pop('ignore_info') if "ignore_info" in params else True

    with DBContext('r') as session:
        page = paginate(session.query(Users).filter(_get_value(value)).filter_by(**filter_map), **params)

    queryset = []
    for msg in page.items:
        data_dict = model_to_dict(msg)
        data_dict.pop('password')
        data_dict.pop('google_key')

        if not ignore_info:
            data_dict['group_cnt'], data_dict['group_list'] = get_group_list_for_user(user_id=data_dict['user_id'])
            data_dict['role_cnt'], data_dict['role_list'] = get_role_list_for_user(user_id=data_dict['user_id'])
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
