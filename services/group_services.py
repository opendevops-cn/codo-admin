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
from models.authority_model import Menus, Functions, Components, Apps, Roles, Users, UserRoles, UserToken, Groups, \
    UserGroups, RolesMutual, RolesInherit, GroupRoles, OperationLogs, GroupsRelate


# 用户
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
                        or_(Users.username.like(f'%{value}%'), Users.nickname.like(f'%{value}%'),
                            Users.department.like(f'%{value}%'), )).order_by(Users.user_id.desc()), **kwargs)
            else:
                page = paginate(
                    session.query(Users).filter(Users.user_id.in_(all_user_list), Users.status == '0').filter_by(
                        **filter_map).order_by(Users.user_id.desc()), **kwargs)
            return page.total, page.items


def get_privilege_for_role(**kwargs) -> tuple:
    """通过角色查看权限"""
    role_id = kwargs.get('role_id')
    dict_list = ['user_id', 'username', 'nickname']
    with DBContext('r') as session:
        if role_id:
            count = session.query(UserRoles).filter(UserRoles.status != '10', UserRoles.role_id == role_id).count()
            role_info = session.query(UserRoles.user_id, Users.username,
                                      Users.nickname).outerjoin(Users, Users.user_id == UserRoles.user_id).filter(
                UserRoles.role_id == role_id, Users.status == '0').order_by(UserRoles.role_id).all()
        # else:
        #     dict_list = ['role_name', 'user_role_id', 'role_id', 'user_id', 'username', 'nickname']
        #     count = session.query(Roles).outerjoin(UserRoles, UserRoles.role_id == Roles.role_id).filter(
        #         UserRoles.status != '10', Roles.role_name == role_name).count()
        #     role_info = session.query(Roles.role_name, UserRoles.user_role_id, UserRoles.role_id, UserRoles.user_id,
        #                               Users.username, Users.nickname).outerjoin(UserRoles,
        #                                                                         UserRoles.role_id == Roles.role_id).outerjoin(
        #         Users, Users.user_id == UserRoles.user_id).filter(
        #         Roles.role_name == role_name, Users.status == '0').order_by(UserRoles.role_id).all()

    queryset = [dict(zip(dict_list, msg)) for msg in role_info]
    return count, queryset


def get_all_roles_herit(**kwargs):
    with DBContext('r') as session:
        role_info = session.query(RolesInherit.role_inherit_id, RolesInherit.role_inherit_name,
                                  RolesInherit.role_parent_id).outerjoin(UserRoles,
                                                                         UserRoles.role_id == Roles.role_id).outerjoin(
            Users, Users.user_id == UserRoles.user_id).filter(RolesInherit.status == '0').all()

        # role_inherit_id = Column('role_inherit_id', Integer, primary_key=True, autoincrement=True)
        # role_inherit_name = Column('role_inherit_name', String(30), index=True)
        # role_parent_id = Column('role_parent_id', Integer, index=True)
        # role_child_id = Column('role_child_id', Integer, index=True)
        # desc = Column('desc', String(250), default='')  ### 描述、备注
        # status = Column('status', String(5), default='0', index=True)


def get_all_user_list_for_role(**kwargs):
    role_user_dict = dict()
    with DBContext('r') as session:
        role_info = session.query(Roles.role_name, Users.username,
                                  Users.nickname).outerjoin(UserRoles, UserRoles.role_id == Roles.role_id).outerjoin(
            Users, Users.user_id == UserRoles.user_id).filter(Roles.status == '0', Users.status == '0').all()

    for msg_tuple in role_info:
        role_name = msg_tuple[0]
        username = msg_tuple[1]
        nickname = msg_tuple[2]
        val_dict = role_user_dict.get(role_name)
        if val_dict and isinstance(val_dict, dict):
            role_user_dict[role_name] = {**val_dict, **{f"{username}({nickname})": "y"}}
        else:
            role_user_dict[role_name] = {f"{username}({nickname})": "y"}
    return role_user_dict


def get_user_exclude_list_for_role(**params) -> tuple:
    """通过角色查找用户"""
    value = params.get('searchValue') if "searchValue" in params else params.get('value')
    params['page_size'] = 300  ### 默认获取到全部数据
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    if 'resource_group' in filter_map: filter_map.pop('resource_group')

    role_id = params.get('role_id')
    with DBContext('r') as session:
        _, user_info = get_user_list_for_role(role_id=role_id)
        user_list = [u.get('user_id') for u in user_info]

        if value:
            page = paginate(session.query(Users).filter(Users.status == '0', Users.user_id.notin_(user_list)).filter_by(
                **filter_map).filter(
                or_(Users.username.like(f'%{value}%'),
                    Users.nickname.like(f'%{value}%'),
                    Users.department.like(f'%{value}%'), )), **params)
        else:
            page = paginate(session.query(Users).filter(Users.status == '0', Users.user_id.notin_(user_list)).filter_by(
                **filter_map), **params)
    return page.total, page.items


def get_group_exclude_list_for_role(**params) -> tuple:
    """通过角色查找可添加关联的用户组"""
    value = params.get('searchValue') if "searchValue" in params else params.get('value')
    params['page_size'] = 500  ### 默认获取到全部数据
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    if 'resource_group' in filter_map: filter_map.pop('resource_group')
    ignore_info = params.pop('ignore_info') if "ignore_info" in params else True

    role_id = params.get('role_id')
    with DBContext('r') as session:
        _, group_info = get_group_list_for_role(role_id=role_id)

        group_list = [g.get('group_id') for g in group_info]

        if value:
            page = paginate(session.query(Groups).filter(Groups.status == '0', Groups.source != "组织架构同步",
                                                         Groups.group_id.notin_(group_list)).filter_by(
                **filter_map).filter(
                Groups.group_name.like(f'%{value}%')).order_by(case(value=Groups.source, whens={"自定义": 0,
                                                                                                "自动": 1,
                                                                                                "组织架构同步": 2}),
                                                               Groups.group_id.desc()), **params)
        else:
            page = paginate(session.query(Groups).filter(Groups.status == '0', Groups.source != "组织架构同步",
                                                         Groups.group_id.notin_(group_list)).filter_by(
                **filter_map).order_by(case(value=Groups.source, whens={"自定义": 0,
                                                                        "自动": 1,
                                                                        "组织架构同步": 2}), Groups.group_id.desc()),
                            **params)
    if not ignore_info:
        for q in page.items:
            cnt, user_list = get_user_list_for_group(group_id=q.get('group_id'), contain_relate=True)
            q['user_cnt'] = cnt
            q['user_list'] = user_list

            cnt, relate_list = get_relate_group_list_for_group(group_id=q.get('group_id'))
            q['relate_cnt'] = cnt
            q['relate_list'] = relate_list
    return page.total, page.items


##### 用户组
def get_groups_list(**params) -> tuple:
    """用户组列表"""
    value = params.get('searchValue') if "searchValue" in params else params.get('value')
    params['page_size'] = 30  ### 默认获取到全部数据
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    if 'resource_group' in filter_map: filter_map.pop('resource_group')

    all_source = ["自定义", "自动", "组织架构同步"]
    source_filter = params.get('source_filter', "")
    source_filter = source_filter.split(',')
    source_filter = [s for s in source_filter if s]
    # if source_filter and not isinstance(source_filter, list):
    #     source_filter = json.loads(source_filter)
    if not source_filter:
        source_filter = all_source

    with DBContext('r') as session:
        if value:
            page = paginate(
                session.query(Groups).filter(Groups.status != '10', Groups.source.in_(source_filter)).filter_by(
                    **filter_map).filter(
                    Groups.group_name.like(f'%{value}%')).order_by(case(value=Groups.source, whens={"自定义": 0,
                                                                                                    "自动": 1,
                                                                                                    "组织架构同步": 2}),
                                                                   Groups.group_id.desc()), **params)
        else:
            page = paginate(
                session.query(Groups).filter(Groups.status != '10', Groups.source.in_(source_filter)).filter_by(
                    **filter_map).order_by(case(value=Groups.source, whens={"自定义": 0,
                                                                            "自动": 1,
                                                                            "组织架构同步": 2}),
                                           Groups.group_id.desc()),
                **params)

        ignore_info = params.get('ignore_info') if "ignore_info" in params else params.get('ignore_info')

        if ignore_info == 'true':
            return page.total, page.items
        for group in page.items:
            group_id = group['group_id']

            count, queryset = get_user_list_for_group(group_id=group_id, contain_relate=True)
            group['user_cnt'] = count
            group['user_list'] = queryset

            count, queryset = get_role_list_for_group(group_id=group_id)
            group['role_cnt'] = count
            group['role_list'] = queryset

            count, queryset = get_relate_group_list_for_group(group_id=group_id)
            group['relate_cnt'] = count
            group['relate_list'] = queryset

    return page.total, page.items


def get_user_list_for_group(**kwargs) -> tuple:
    """通过用户组查找用户"""
    group_id = kwargs.get('group_id')
    group_name = kwargs.get('group_name')
    contain_relate = kwargs.get("contain_relate")
    is_page = kwargs.get("is_page")

    dict_list = ['user_id', 'username', 'nickname', 'department']
    with DBContext('r') as session:
        if not group_id and group_name:
            group_obj = session.query(Groups.group_id).filter(Groups.group_name == group_name,
                                                              Groups.status == '0').first()
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
                                  Users.nickname, Users.department).outerjoin(Users,
                                                                              Users.user_id == UserGroups.user_id).filter(
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
                        or_(Users.username.like(f'%{value}%'), Users.nickname.like(f'%{value}%'),
                            Users.department.like(f'%{value}%'), )).order_by(Users.user_id.desc()), **kwargs)
            else:
                page = paginate(
                    session.query(Users).filter(Users.user_id.in_(user_id_list)).filter_by(
                        **filter_map).order_by(Users.user_id.desc()), **kwargs)
            return page.total, page.items


def get_user_exclude_list_for_group(**params) -> tuple:
    """通过用户组查找用户"""
    value = params.get('searchValue') if "searchValue" in params else params.get('value')
    params['page_size'] = 300  ### 默认获取到全部数据
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    if 'resource_group' in filter_map: filter_map.pop('resource_group')

    group_id = params.get('group_id')
    group_name = params.get('group_name')
    with DBContext('r') as session:
        if group_id:
            user_info = session.query(UserGroups).outerjoin(Users, Users.user_id == UserGroups.user_id).filter(
                UserGroups.group_id == group_id, Users.status == '0').order_by(UserGroups.group_id).all()
        else:
            user_info = session.query(UserGroups).outerjoin(UserGroups,
                                                            UserGroups.group_id == Groups.group_id).outerjoin(
                Users, Users.user_id == UserGroups.user_id).filter(
                Groups.group_name == group_name, Users.status == '0').order_by(UserGroups.group_id).all()
        user_list = [u.user_id for u in user_info]
        if value:
            page = paginate(session.query(Users).filter(Users.status == '0', Users.user_id.notin_(user_list)).filter_by(
                **filter_map).filter(
                or_(Users.username.like(f'%{value}%'), Users.nickname.like(f'%{value}%'),
                    Users.department.like(f'%{value}%'))), **params)
        else:
            page = paginate(session.query(Users).filter(Users.status == '0', Users.user_id.notin_(user_list)).filter_by(
                **filter_map), **params)
    return page.total, page.items


def get_business_list_for_group(**kwargs) -> tuple:
    """通过用户组查找业务列表"""
    pass
    # group_id = kwargs.get('group_id')
    # group_name = kwargs.get('group_name')
    # dict_list = ['business_id', 'business_en', 'business_zh']
    # with DBContext('r') as session:
    #     if group_id:
    #         business_info = session.query(GroupBusiness.business_id, BusinessModel.business_en, BusinessModel.business_zh).outerjoin(BusinessModel, BusinessModel.business_id == GroupBusiness.business_id).filter(
    #             GroupBusiness.status == '0', GroupBusiness.group_id == group_id, BusinessModel.life_cycle == '2').order_by(
    #             GroupBusiness.group_id).all()
    #     else:
    #         dict_list = ['business_id', 'business_en', 'business_zh']
    #         business_info = session.query(GroupBusiness.business_id, BusinessModel.business_en, BusinessModel.business_zh).outerjoin(BusinessModel, BusinessModel.business_id == GroupBusiness.business_id).outerjoin(Groups, Groups.group_id == GroupBusiness.group_id).filter(Groups.group_name == group_name, GroupBusiness.status == '0', BusinessModel.life_cycle == '2').all()
    # queryset = [dict(zip(dict_list, msg)) for msg in business_info]
    # return len(queryset), queryset


def get_role_list_for_group(**kwargs) -> tuple:
    """通过用户组查找角色"""
    group_id = kwargs.get('group_id')
    group_name = kwargs.get('group_name')
    dict_list = ['role_id', 'role_name', 'desc']
    with DBContext('r') as session:
        if group_id:
            roles_info = session.query(GroupRoles.role_id, Roles.role_name, Roles.desc).outerjoin(Roles,
                                                                                                  Roles.role_id == GroupRoles.role_id).filter(
                GroupRoles.status == '0', GroupRoles.group_id == group_id, Roles.status == '0').order_by(
                GroupRoles.group_id).all()
        else:
            dict_list = ['role_id', 'role_name', 'desc']
            roles_info = session.query(GroupRoles.role_id, Roles.role_name, Roles.desc).outerjoin(Roles,
                                                                                                  Roles.role_id == GroupRoles.role_id).outerjoin(
                Groups, Groups.group_id == GroupRoles.group_id).filter(Groups.group_name == group_name,
                                                                       GroupRoles.status == '0',
                                                                       Roles.status == '0').all()
    queryset = [dict(zip(dict_list, msg)) for msg in roles_info]
    return len(queryset), queryset


def get_relate_group_list_for_group(**kwargs) -> tuple:
    """通过用户组查找关联组织架构"""
    group_id = kwargs.get('group_id')
    group_name = kwargs.get('group_name')
    dict_list = ['group_id', 'group_name', 'status']
    with DBContext('r') as session:
        if group_id:
            group_info = session.query(Groups.group_id, Groups.group_name, Groups.status).outerjoin(GroupsRelate,
                                                                                                    GroupsRelate.relate_id == Groups.group_id).filter(
                GroupsRelate.status == '0', GroupsRelate.group_id == group_id).all()
        else:
            group_info = session.query(Groups.group_id, Groups.group_name, Groups.status).outerjoin(GroupsRelate,
                                                                                                    GroupsRelate.relate_id == Groups.group_id).filter(
                GroupsRelate.status == '0', Groups.group_name == group_name).all()
    queryset = [dict(zip(dict_list, msg)) for msg in group_info]
    return len(queryset), queryset


def check_mutual_role(role_list):
    """检查角色是否有互斥关系"""
    with DBContext('r') as session:
        query = session.query(RolesMutual).filter(RolesMutual.role_left_id.in_(role_list),
                                                  RolesMutual.role_right_id.in_(role_list),
                                                  RolesMutual.status == '0').all()

        if len(query) > 0:
            return True
        else:
            return False


def add_operation_log(data: dict):
    """用户操作日志"""
    with DBContext('w', None, True) as session:
        new_log = OperationLogs(**data)
        session.add(new_log)
        session.commit()
        log_id = new_log.id
    return log_id
