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
from sqlalchemy.exc import IntegrityError
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.sqlalchemy_pagination import paginate
from models.authority_model import  Roles, Users, UserRoles, \
    FavoritesModel, Groups, UserGroups,  GroupRoles, OperationLogs,  GroupsRelate

def add_operation_log(data: dict):
    """用户操作日志"""
    with DBContext('w', None, True) as session:
        new_log = OperationLogs(**data)
        session.add(new_log)
        session.commit()
        log_id = new_log.id
    return log_id

def get_user_list_for_role(**kwargs) -> tuple:
    """通过角色查看用户"""
    role_id = kwargs.get('role_id')
    ignore_group = kwargs.get('ignore_group', False)
    is_page = kwargs.get('is_page', False)

    dict_list = ['user_id', 'username', 'nickname', 'department']
    with DBContext('r') as session:
        if ignore_group:
            user_group_list = []
        else:
            group_info = session.query(GroupRoles).outerjoin(Groups, Groups.group_id == GroupRoles.group_id).filter(
                GroupRoles.role_id == role_id, GroupRoles.status == '0', Roles.status == '0').all()

            group_info = [g.group_id for g in group_info]
            user_group_list = session.query(UserGroups.user_id).filter(
                UserGroups.group_id.in_(group_info), UserGroups.status == '0').all()
            user_group_list = [u[0] for u in user_group_list]

        user_role_list = session.query(UserRoles.user_id).filter(
            UserRoles.role_id == role_id, UserRoles.status == '0').all()
        user_role_list = [u[0] for u in user_role_list]
        all_user_list = list(set(user_group_list + user_role_list))

        if not is_page:
            user_info = session.query(Users.user_id, Users.username, Users.nickname, Users.department).filter(
                Users.user_id.in_(all_user_list), Users.status == '0').all()

            queryset = [dict(zip(dict_list, msg)) for msg in user_info]
            return len(queryset), queryset

        else:
            value = kwargs.get('searchValue') if "searchValue" in kwargs else kwargs.get('value')
            kwargs['page_size'] = 30  ### 默认获取到全部数据
            filter_map = kwargs.pop('filter_map') if "filter_map" in kwargs else {}
            if 'resource_group' in filter_map: filter_map.pop('resource_group')
            if value:
                page = paginate(
                    session.query(Users).filter(Users.user_id.in_(all_user_list), Users.status == '0').filter_by(
                        **filter_map).filter(
                        or_(Users.username.like(f'%{value}%'), Users.nickname.like(f'%{value}%'), Users.department.like(f'%{value}%'),)).order_by(Users.user_id.desc()), **kwargs)
            else:
                page = paginate(
                    session.query(Users).filter(Users.user_id.in_(all_user_list), Users.status == '0').filter_by(
                        **filter_map).order_by(Users.user_id.desc()), **kwargs)
            return page.total, page.items

# 用户
def get_user_list_for_group(**kwargs) -> tuple:
    """通过用户组查找用户"""
    group_id = kwargs.get('group_id')
    group_name = kwargs.get('group_name')
    contain_relate = kwargs.get("contain_relate")
    is_page = kwargs.get("is_page")

    dict_list = ['user_id', 'username', 'nickname', 'department']
    with DBContext('r') as session:
        if not group_id and group_name:
            group_obj = session.query(Groups.group_id).filter(Groups.group_name == group_name, Groups.status == '0').first()
            if group_obj:
                group_id = group_obj[0]
                if not group_id:
                    return 0, []

        if contain_relate:
            relate_group = session.query(GroupsRelate.relate_id).filter(GroupsRelate.status == '0',
                                                                        GroupsRelate.group_id == group_id).all()
            group_list = [r[0] for r in relate_group if r[0]]
            group_list.append(group_id)
            group_list = list(set(group_list))
        else:
            group_list = [group_id]

        user_info = session.query(UserGroups.user_id, Users.username,
                                  Users.nickname, Users.department).outerjoin(Users, Users.user_id == UserGroups.user_id).filter(
            UserGroups.group_id.in_(group_list), Users.status == '0', UserGroups.status == '0').distinct()

        if not is_page:
            queryset = [dict(zip(dict_list, msg)) for msg in user_info]
            return len(queryset), queryset
        else:
            value = kwargs.get('searchValue') if "searchValue" in kwargs else kwargs.get('value')
            kwargs['page_size'] = 30  ### 默认获取到全部数据
            filter_map = kwargs.pop('filter_map') if "filter_map" in kwargs else {}
            if 'resource_group' in filter_map: filter_map.pop('resource_group')
            user_id_list = [msg[0] for msg in user_info]
            if value:
                page = paginate(
                    session.query(Users).filter(Users.user_id.in_(user_id_list)).filter_by(
                        **filter_map).filter(
                        or_(Users.username.like(f'%{value}%'), Users.nickname.like(f'%{value}%'), Users.department.like(f'%{value}%'),)).order_by(Users.user_id.desc()), **kwargs)
            else:
                page = paginate(
                    session.query(Users).filter(Users.user_id.in_(user_id_list)).filter_by(
                        **filter_map).order_by(Users.user_id.desc()), **kwargs)
            return page.total, page.items
