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
import datetime
import time
from sqlalchemy import or_, and_, func, desc, case
from sqlalchemy.exc import IntegrityError
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.model_utils import queryset_to_list, model_to_dict, GetInsertOrUpdateObj
from websdk2.utils.pydantic_utils import sqlalchemy_to_pydantic, ValidationError, PydanticDel, BaseModel
from websdk2.sqlalchemy_pagination import paginate
from models.authority_model import Menus, Functions, Components, Apps, Roles, Users, UserRoles, UserToken, OperationRecord, \
    FavoritesModel, Groups, UserGroups, RolesMutual, RolesInherit, GroupRoles, OperationLogs, SyncLogs, RoleApp, \
    RoleBusiness, RoleMenu, RoleComponent, RoleFunction, Resources, SubscribeRole, GroupsRelate
from websdk2.cache_context import cache_conn

from models.biz_model import BusinessModel

# 用户
def get_user_list_v2(**params) -> tuple:
    value = params.get('searchValue') if "searchValue" in params else params.get('value')
    params["items_not_to_list"] = "yes"
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    filter_map['status'] = '0'
    if 'resource_group' in filter_map: filter_map.pop('resource_group')

    ignore_info = params.pop('ignore_info') if "ignore_info" in params else True

    with DBContext('r') as session:
        if value:
            page = paginate(session.query(Users).filter_by(
                **filter_map).filter(or_(Users.user_id == value, Users.username.like(f'%{value}%'),
                                         Users.nickname.like(f'%{value}%'), Users.email.like(f'%{value}%'),
                                         Users.tel.like(f'%{value}%'), Users.wechat.like(f'{value}%'),
                                         Users.no.like(f'{value}%'), Users.department.like(f'%{value}%'),
                                         Users.source_account_id.like(f'%{value}%'))), **params)
        else:
            page = paginate(session.query(Users).filter_by(**filter_map), **params)

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
        group_info = session.query(Groups.group_id, Groups.group_name).outerjoin(UserGroups, Groups.group_id == UserGroups.group_id)\
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
            .outerjoin(Users, Users.user_id == UserRoles.user_id).filter(Users.user_id == user_id, Roles.status == '0', UserRoles.status == '0', Users.status == '0').all()

        group_list = session.query(Groups.group_id, Groups.group_name).outerjoin(UserGroups, Groups.group_id == UserGroups.group_id)\
            .outerjoin(Users, Users.user_id == UserGroups.user_id).filter(Users.user_id == user_id, Groups.status == '0', UserGroups.status == '0', Users.status == '0').all()
        group_list = [g[0] for g in group_list]

        role_info.extend(session.query(Roles.role_id, Roles.role_name).outerjoin(GroupRoles,
                                                                                 Roles.role_id == GroupRoles.role_id) \
            .outerjoin(Groups, Groups.group_id == GroupRoles.group_id).filter(Groups.group_id.in_(group_list), Groups.status == '0', Roles.status == '0', GroupRoles.status == '0').all())

    role_info = list(set(role_info))
    queryset = [dict(zip(dict_list, msg)) for msg in role_info]
    count = len(queryset)
    return count, queryset


PydanticMenus = sqlalchemy_to_pydantic(Menus, exclude=['menu_id'])  ### 排除自增ID
PydanticMenusUP = sqlalchemy_to_pydantic(Menus)


class PydanticcMenusDel(BaseModel):
    menu_id: int


# 业务
def get_business_list_for_role(role_list: list) -> list:
    with DBContext('r') as session:
        dict_list = ["business_id", "business_en"]
        business_info = session.query(RoleBusiness.business_id, BusinessModel.business_en).outerjoin(BusinessModel, BusinessModel.business_id == RoleBusiness.business_id).filter(RoleBusiness.role_id.in_(role_list), RoleBusiness.status == '0').all()
        queryset = [dict(zip(dict_list, msg)) for msg in business_info]
    return queryset


# 树结构
def get_tree_data(data: list, parent_id: int, parent_type: str):
    """统一结构，递归获取树结构"""
    res = []
    for d in data:
        if d.get('parent_id') == parent_id and d.get('parent_type') == parent_type:
            next_type = d.get('record_type')
            next_idx = 'app_id' if next_type == 'app' else 'menu_id' if next_type == 'menu' else 'component_id' if next_type == 'component' \
                else 'function_id'
            next_pid = d.get(next_idx)
            d["children"] = get_tree_data(data, next_pid, next_type)
            d["expand"] = True if len(d["children"]) > 0 else False
            # d["expand"] = True if len(
            #     [d for d in data if d.get('parent_id') == next_pid and d.get('parent_type') == next_type]) else False
            res.append(d)
    return res


def get_menu_tree(menu_query: list):
    """处理信息， parent id parent type"""
    with DBContext('r') as session:
        app_query = session.query(Apps).filter(Apps.status == '0').all()
        app_query = [model_to_dict(app) for app in app_query]
        # parent_info_query = []
        for app in app_query:
            app["title"] = app["app_code"]
            app["parent_id"] = 0
            app["parent_type"] = "root"
            app["record_type"] = "app"
            # parent_info_query.append(app)

    for q in menu_query:  # 处理menu
        if q.get('parent_id') == 0:
            parent_type, parent_id = 'app', [a['app_id'] for a in app_query if a['app_code'] == q.get('app_code')]
            parent_id = parent_id[0] if parent_id else None
        else:
            parent_type, parent_id = 'menu', q.get('parent_id')

        q["title"] = q.get('details')
        q["parent_id"] = parent_id
        q["parent_type"] = parent_type
        q["record_type"] = "menu"

    app_query.extend(menu_query)
    res = get_tree_data(app_query, 0, 'root')
    return res


def get_menu_list(**params) -> tuple:
    # 获取menu list

    value = params.get('searchValue') if "searchValue" in params else params.get('value')
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    params['page_size'] = 500
    if "app_code" in params:
        filter_map['app_code'] = params.get('app_code')
    else:
        params["order_by"] = "app_code"

    if 'resource_group' in filter_map: filter_map.pop('resource_group')

    with DBContext('r') as session:
        if value:
            page = paginate(session.query(Menus).filter(Menus.status != '10').filter_by(**filter_map).filter(
                or_(Menus.app_code == value, Menus.menu_name.like(f'%{value}%'),
                    Menus.details.like(f'%{value}%'))), **params)
        else:
            page = paginate(session.query(Menus).filter(Menus.status != '10').filter_by(**filter_map), **params)
    tree_data = params.get('tree_data') if "tree_data" in params else False

    if tree_data:
        result = get_menu_tree(page.items)
        if "app_code" in filter_map.keys():
            for app in result:
                if app.get("app_code") == filter_map['app_code']:
                    result = app
                    break

    else:
        result = page.items

    return page.total, result


def get_menu_subtree(**params) -> tuple:
    # 获取menu 子树
    record_type = params.get('record_type')
    id = params.get('id')
    with DBContext('r') as session:
        if record_type == 'app':
            app_obj = session.query(Apps.app_code).filter(Apps.app_id == id).first()
            app_code = app_obj[0]
            if not app_code:
                return 0, []

            page = paginate(session.query(Menus).filter(Menus.status == '0', Menus.app_code == app_code), **params)
        if record_type == 'menu':
            menu_id = [int(id)]
            all_menu_id = menu_id
            cnt = 0
            while menu_id and cnt < 50:
                cnt += 1
                menu_query = session.query(Menus.menu_id).filter(Menus.status == '0', Menus.parent_id.in_(menu_id)).all()
                menu_id = [m[0] for m in menu_query]
                menu_id = list(set(menu_id))
                all_menu_id += menu_id

            page = paginate(session.query(Menus).filter(Menus.status == '0', Menus.menu_id.in_(all_menu_id)), **params)
    return page.total, page.items


def add_menu(data: dict):
    """添加菜单"""
    try:
        PydanticMenus(**data)
    except ValidationError as e:
        return dict(code=-1, msg=str(e))

    try:
        with DBContext('w', None, True) as db:
            db.add(Menus(**data))
    except IntegrityError as e:
        return dict(code=-2, msg="添加重复了")

    return dict(code=0, msg="创建成功")


def up_menu(data: dict):
    """修改菜单"""
    if '_index' in data: data.pop('_index')
    if '_rowKey' in data: data.pop('_rowKey')
    try:
        valid_data = PydanticMenusUP(**data)
    except ValidationError as e:
        return dict(code=-1, msg=str(e))

    try:
        with DBContext('w', None, True) as db:
            db.query(Menus).filter(Menus.menu_id == valid_data.menu_id).update(data)
    except IntegrityError as e:
        return dict(code=-2, msg="添加重复了")
    except Exception as err:
        return dict(code=-3, msg=f'修改失败, {str(err)}')

    return dict(code=0, msg="菜单修改成功")


def del_menu(data: dict):
    """删除菜单"""
    try:
        valid_data = PydanticcMenusDel(**data)
    except ValidationError as e:
        return dict(code=-1, msg=str(e))

    try:
        with DBContext('w', None, True) as db:
            db.query(Menus).filter(Menus.menu_id == valid_data.menu_id).delete(synchronize_session=False)
    except Exception as err:
        return dict(code=-3, msg=f'删除失败, {str(err)}')
    return dict(code=0, msg="删除成功")


def get_menu_list_for_role(role_list, app_code=None) -> list:
    with DBContext('r') as session:
        dict_list = ["menu_id", "menu_name"]
        if app_code:
            comp_info = session.query(RoleMenu.menu_id, Menus.menu_name).outerjoin(Menus, Menus.menu_id == RoleMenu.menu_id).filter(RoleMenu.role_id.in_(role_list), RoleMenu.status == '0', Menus.status == '0', Menus.app_code == app_code).all()
        else:
            comp_info = session.query(RoleMenu.menu_id, Menus.menu_name).outerjoin(Menus,
                                                                                   Menus.menu_id == RoleMenu.menu_id).filter(
                RoleMenu.role_id.in_(role_list), RoleMenu.status == '0', Menus.status == '0').all()
        queryset = [dict(zip(dict_list, msg)) for msg in comp_info]
    return queryset


# 接口
def get_func_tree(func_query: list):
    """处理信息， parent id parent type"""
    with DBContext('r') as session:
        app_page = paginate(session.query(Apps).filter(Apps.status == '0'), **{"page_size": 200})
        app_query = app_page.items

        for app in app_query:
            app["title"] = app["app_code"]
            app["parent_id"] = 0
            app["parent_type"] = "root"
            app["record_type"] = "app"
            # parent_info_query.append(app)

    for q in func_query:  # 处理func
        if q.get('parent_id') == 0:
            parent_type, parent_id = 'app', [a['app_id'] for a in app_query if a['app_code'] == q.get('app_code')]
            parent_id = parent_id[0] if parent_id else None
        else:
            parent_type, parent_id = 'function', q.get('parent_id')
        q["title"] = f"【{q.get('method_type')}】{q.get('path')} ({q.get('func_name')})" if q.get('method_type') else f"{q.get('uri')}"
        q["parent_id"] = parent_id
        q["parent_type"] = parent_type
        q["record_type"] = "function"

    app_query.extend(func_query)
    res = get_tree_data(app_query, 0, 'root')
    return res


def get_func_list(**params) -> tuple:
    value = params.get('searchValue') if "searchValue" in params else params.get('value')

    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    params['page_size'] = 5000
    if "app_code" in params:
        filter_map['app_code'] = params.get('app_code')
    else:
        params["order_by"] = "app_code"
    if 'resource_group' in filter_map: filter_map.pop('resource_group')

    with DBContext('r') as session:
        if value:
            page = paginate(session.query(Functions).filter(Functions.status != '10').filter_by(**filter_map).filter(
                or_(Functions.app_code == value, Functions.func_name.like(f'%{value}%'),
                    Functions.uri.like(f'%{value}%'),
                    Functions.method_type.like(f'{value}%'), Functions.app_code.like(f'%{value}%'))), **params)
        else:
            page = paginate(session.query(Functions).filter(Functions.status != '10').filter_by(**filter_map), **params)

    tree_data = params.get('tree_data') if "tree_data" in params else False
    if tree_data:
        result = get_func_tree(page.items)

        if "app_code" in filter_map.keys():
            for app in result:
                if app.get("app_code") == filter_map['app_code']:
                    result = app
                    break
    else:
        result = page.items
    return page.total, result


def get_func_subtree(**params) -> tuple:
    # 获取func 子树
    record_type = params.pop('record_type')
    id = params.pop('id')

    with DBContext('r') as session:
        if record_type == 'app':
            app_obj = session.query(Apps.app_code).filter(Apps.app_id == id).first()
            app_code = app_obj[0]
            if not app_code:
                return 0, []

            page = paginate(session.query(Functions).filter(Functions.status == '0',
                                                            Functions.app_code == app_code,
                                                            Functions.method_type != ""), **params)
        if record_type == 'function':
            func_id = [int(id)]
            all_func_id = func_id
            cnt = 0
            while func_id and cnt < 50:
                cnt += 1
                func_query = session.query(Functions.function_id).filter(Functions.status == '0',
                                                                         Functions.parent_id.in_(func_id),
                                                                         ).all()
                func_id = [m[0] for m in func_query]
                func_id = list(set(func_id))
                all_func_id += func_id

            page = paginate(session.query(Functions).filter(Functions.status == '0',
                                                            Functions.function_id.in_(all_func_id),
                                                            Functions.method_type != ""), **params)
    return page.total, page.items


def get_func_list_for_role(role_list, app_code=None) -> list:
    with DBContext('r') as session:
        dict_list = ["function_id", "path"]
        if app_code:
            func_info = session.query(RoleFunction.function_id, Functions.path).outerjoin(Functions, Functions.function_id == RoleFunction.function_id).filter(RoleFunction.role_id.in_(role_list), RoleFunction.status == '0', Functions.status == '0', Functions.app_code == app_code).all()
        else:
            func_info = session.query(RoleFunction.function_id, Functions.path).outerjoin(Functions,
                                                                                          Functions.function_id == RoleFunction.function_id).filter(
                RoleFunction.role_id.in_(role_list), RoleFunction.status == '0', Functions.status == '0').all()
        queryset = [dict(zip(dict_list, msg)) for msg in func_info]
    return queryset


# 组件
def get_component_tree(component_query: list):
    """处理信息， parent id parent type"""
    with DBContext('r') as session:
        app_query = session.query(Apps).filter(Apps.status == '0').all()
        app_query = [model_to_dict(q) for q in app_query]
        menu_query = session.query(Menus).filter(Menus.status == '0').all()
        menu_query = [model_to_dict(q) for q in menu_query]

    for app in app_query:
        app["title"] = app.get("app_code")
        app["parent_id"] = 0
        app["parent_type"] = "root"
        app["record_type"] = "app"
        app["key"] = f"app-{app['app_id']}"

    for q in menu_query:  # 处理menu
        if q["parent_id"] == 0:
            parent_type, parent_id = 'app', [a['app_id'] for a in app_query if a['app_code'] == q['app_code']]
            parent_id = parent_id[0] if parent_id else None
        else:
            parent_type, parent_id = 'menu', q["parent_id"]

        q["title"] = q['details']
        q["parent_id"] = parent_id
        q["parent_type"] = parent_type
        q["record_type"] = 'menu'
        q["key"] = f"menu-{q['menu_id']}"

    for q in component_query:
        q["title"] = q.get('details')
        q["parent_id"] = q.get('menu_id')
        q["parent_type"] = 'menu'
        q["record_type"] = 'component'
        q["key"] = f"component-{q['component_id']}"

    app_query.extend(menu_query)
    app_query.extend(component_query)
    res = get_tree_data(app_query, 0, 'root')
    return res


def get_components_list(**params) -> tuple:
    ### 树形组件
    value = params.get('searchValue') if "searchValue" in params else params.get('value')
    params['page_size'] = 500
    filter_map = params.pop('filter_map') if "filter_map" in params else {}

    if "app_code" in params:
        filter_map['app_code'] = params.get('app_code')
    else:
        params["order_by"] = "app_code"

    if 'resource_group' in filter_map: filter_map.pop('resource_group')

    with DBContext('r') as session:
        if value:
            page = paginate(session.query(Components).filter(Components.status != '10').filter_by(**filter_map).filter(
                or_(Components.app_code == value, Components.component_name.like(f'%{value}%'),
                    Components.details.like(f'%{value}%'))), **params)
        else:
            page = paginate(session.query(Components).filter(Components.status != '10').filter_by(**filter_map),
                            **params)

    tree_data = params.get('tree_data') if "tree_data" in params else False
    if tree_data:
        result = get_component_tree(page.items)

        if "app_code" in filter_map.keys():
            for app in result:
                if app.get("app_code") == filter_map['app_code']:
                    result = app
                    break
    else:
        result = page.items
    return page.total, result


def get_components_list_tansfer(**params) -> tuple:
    ### 组件 - 使用穿梭框, 会包含app menu
    value = params.get('searchValue') if "searchValue" in params else params.get('value')
    filter_map = params.pop('filter_map') if "filter_map" in params else {}

    if "app_code" in params:
        filter_map['app_code'] = params.get('app_code')
    else:
        params["order_by"] = "app_code"

    if 'resource_group' in filter_map: filter_map.pop('resource_group')

    with DBContext('r') as session:
        if value:
            component_query = session.query(Components).filter(Components.status != '10').filter_by(**filter_map).filter(
                or_(Components.app_code == value, Components.component_name.like(f'%{value}%'),
                    Components.details.like(f'%{value}%'))).all()
        else:

            component_query = session.query(Components).filter(Components.status != '10').filter_by(
                **filter_map).all()

    component_data = [model_to_dict(c) for c in component_query]
    result = get_component_tree(component_data)
    return len(component_query), result


def get_component_subtree(**params) -> tuple:
    """组件子树"""
    record_type = params.get('record_type')
    id = params.get('id')
    with DBContext('r') as session:
        if record_type == 'app':
            app_obj = session.query(Apps.app_code).filter(Apps.app_id == id).first()
            app_code = app_obj[0]
            if not app_code:
                return 0, []

            page = paginate(session.query(Components).filter(Components.status == '0', Components.app_code == app_code), **params)
        if record_type == 'menu':

            menu_id = [int(id)]
            all_menu_id = menu_id
            cnt = 0
            while menu_id and cnt < 50:
                cnt += 1
                menu_query = session.query(Menus.menu_id).filter(Menus.status == '0',
                                                                 Menus.parent_id.in_(menu_id)).all()
                menu_id = [m[0] for m in menu_query]
                menu_id = list(set(menu_id))
                all_menu_id += menu_id
            page = paginate(session.query(Components).filter(Components.status == '0', Components.menu_id.in_(all_menu_id)),
                            **params)
        if record_type == 'component':
            page = paginate(session.query(Components).filter(Components.status == '0', Components.component_id == id),
                            **params)

        all_compt_id = [i.get("component_id") for i in page.items]
        compt_menu = session.query(Components.component_id, Menus.details).outerjoin(Menus, Menus.menu_id == Components.menu_id).filter(Components.component_id.in_(all_compt_id)).all()
        belong_menu_info = {i[0]: i[1] for i in compt_menu}
        for p in page.items:
            p["belong_menu_name"] = belong_menu_info.get(p["component_id"], "")
    return page.total, page.items


def get_components_list_for_role(role_list, app_code=None) -> list:
    with DBContext('r') as session:
        dict_list = ["component_id", "component_name"]
        if app_code:
            comp_info = session.query(RoleComponent.component_id, Components.component_name).outerjoin(Components, Components.component_id == RoleComponent.component_id).filter(RoleComponent.role_id.in_(role_list), RoleComponent.status == '0', Components.status == '0', Components.app_code == app_code).all()
        else:
            comp_info = session.query(RoleComponent.component_id, Components.component_name).outerjoin(Components,
                                                                                                       Components.component_id == RoleComponent.component_id).filter(
                RoleComponent.role_id.in_(role_list), RoleComponent.status == '0', Components.status == '0').all()
        queryset = [dict(zip(dict_list, msg)) for msg in comp_info]
    return queryset


##### 应用
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


def get_apps_list_for_role(role_list: list) -> list:
    with DBContext('r') as session:
        dict_list = ["app_id", "app_name"]
        app_info = session.query(RoleApp.app_id, Apps.app_name).outerjoin(Apps, Apps.app_id == RoleApp.app_id).filter(RoleApp.role_id.in_(role_list), RoleApp.status == '0', Apps.status == '0').all()
        queryset = [dict(zip(dict_list, msg)) for msg in app_info]
    return queryset


####### 角色
def get_roles_list(**params) -> tuple:
    """角色列表"""
    value = params.get('searchValue') if "searchValue" in params else params.get('value')
    params['page_size'] = 300  ### 默认获取到全部数据
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    if 'resource_group' in filter_map: filter_map.pop('resource_group')

    with DBContext('r') as session:
        if value:
            page = paginate(session.query(Roles).filter(Roles.status != '10').filter_by(**filter_map).filter(
                Roles.role_name.like(f'%{value}%')).order_by(Roles.role_id.desc()), **params)
        else:
            page = paginate(session.query(Roles).filter(Roles.status != '10').filter_by(**filter_map).order_by(Roles.role_id.desc()), **params)

        for role in page.items:
            role_id = role['role_id']
            _, role['herit_list'] = get_role_herit_list(**{'role_id': role_id})
            _, role['mutual_list'] = get_role_mutual_list(**{'role_id': role_id})
            _, role['prerequisites_list'] = get_role_prerequisites_list(**{'prerequisites': role['prerequisites']})
    return page.total, page.items


def get_role_herit_list(**params):
    """获取角色继承关系"""
    params['page_size'] = 300  ### 默认获取到全部数据
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    role_id = params.pop('role_id') if 'role_id' in params else None
    if not role_id:
        return 0, []

    with DBContext('r') as session:

        role_list = session.query(RolesInherit.inherit_from_role_id).filter(RolesInherit.role_id == role_id, RolesInherit.status == '0').all()
        role_list = [r[0] for r in role_list]

        page = paginate(session.query(Roles).filter(Roles.status != '10', Roles.role_id.in_(role_list)).filter_by(**filter_map), **params)
    return page.total, page.items


def get_role_mutual_list(**params):
    """获取角色互斥关系"""
    params['page_size'] = 300  ### 默认获取到全部数据
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    role_id = params.pop('role_id') if 'role_id' in params else None
    if not role_id:
        return 0, []

    with DBContext('r') as session:
        role_list = session.query(RolesMutual).filter(RolesMutual.status == '0', or_(RolesMutual.role_left_id == role_id, RolesMutual.role_right_id == role_id)).all()
        mutual_list = []
        for role in role_list:
            if role.role_left_id == int(role_id):
                mutual_list.append(role.role_right_id)
            elif role.role_right_id == int(role_id):
                mutual_list.append(role.role_left_id)
        mutual_list = list(set(mutual_list))
        page = paginate(session.query(Roles).filter(Roles.status == '0', Roles.role_id.in_(mutual_list)).filter_by(**filter_map), **params)
    return page.total, page.items


def get_role_prerequisites_list(**params):
    """获取角色先决关系"""
    params['page_size'] = 300  ### 默认获取到全部数据
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    prerequisites = params.pop('prerequisites') if 'prerequisites' in params else None
    if not prerequisites:
        return 0, []
    with DBContext('r') as session:
        page = paginate(session.query(Roles).filter(Roles.status == '0', Roles.role_id.in_(prerequisites)).filter_by(**filter_map), **params)
    return page.total, page.items


def check_mutual_role(role_list):
    """检查角色是否有互斥关系"""
    with DBContext('r') as session:
        query = session.query(RolesMutual).filter(RolesMutual.role_left_id.in_(role_list), RolesMutual.role_right_id.in_(role_list), RolesMutual.status == '0').all()

        if len(query) > 0:
            return True
        else:
            return False


def get_group_list_for_role(**kwargs) -> tuple:
    """通过角色查找用户组"""
    role_id = kwargs.get('role_id')
    dict_list = ['group_id', 'group_name']
    is_page = kwargs.get('is_page', False)
    ignore_info = kwargs.get('ignore_info', True)

    with DBContext('r') as session:
        role_info = session.query(GroupRoles.group_id, Groups.group_name).outerjoin(Groups,
                                                                                    Groups.group_id == GroupRoles.group_id) \
            .filter(GroupRoles.role_id == role_id, Groups.status == '0', GroupRoles.status == '0').order_by(
            GroupRoles.role_id).all()

        all_group_list = [msg[0] for msg in role_info if msg[0]]

        if not is_page:  # 不分页 查询全部
            queryset = [dict(zip(dict_list, msg)) for msg in role_info]

            count, queryset = len(queryset), queryset
        else:
            value = kwargs.get('searchValue') if "searchValue" in kwargs else kwargs.get('value')
            kwargs['page_size'] = 30  ### 默认获取到全部数据
            filter_map = kwargs.pop('filter_map') if "filter_map" in kwargs else {}
            if value:
                page = paginate(
                    session.query(Groups).filter(Groups.group_id.in_(all_group_list), Groups.status == '0').filter_by(
                        **filter_map).filter(Groups.group_name.like(f'%{value}%')).order_by(Groups.group_id.desc()), **kwargs)
            else:
                page = paginate(
                    session.query(Groups).filter(Groups.group_id.in_(all_group_list), Groups.status == '0').filter_by(
                        **filter_map).order_by(Groups.group_id.desc()), **kwargs)

            count, queryset = page.total, page.items

    if not ignore_info:
        for q in queryset:
            cnt, user_list = get_user_list_for_group(group_id=q.get('group_id'), contain_relate=True)
            q['user_cnt'] = cnt
            q['user_list'] = user_list

            cnt, relate_list = get_relate_group_list_for_group(group_id=q.get('group_id'))
            q['relate_cnt'] = cnt
            q['relate_list'] = relate_list
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
                        or_(Users.username.like(f'%{value}%'), Users.nickname.like(f'%{value}%'), Users.department.like(f'%{value}%'),)).order_by(Users.user_id.desc()), **kwargs)
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
            page = paginate(session.query(Users).filter(Users.status == '0', Users.user_id.notin_(user_list)).filter_by(**filter_map).filter(
                or_(Users.username.like(f'%{value}%'),
                    Users.nickname.like(f'%{value}%'),
                    Users.department.like(f'%{value}%'),)), **params)
        else:
            page = paginate(session.query(Users).filter(Users.status == '0', Users.user_id.notin_(user_list)).filter_by(**filter_map), **params)
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
            page = paginate(session.query(Groups).filter(Groups.status != '10', Groups.source.in_(source_filter)).filter_by(**filter_map).filter(
                Groups.group_name.like(f'%{value}%')).order_by(case(value=Groups.source, whens={"自定义": 0,
                                                                                                "自动": 1,
                                                                                                "组织架构同步": 2}), Groups.group_id.desc()), **params)
        else:
            page = paginate(
                session.query(Groups).filter(Groups.status != '10', Groups.source.in_(source_filter)).filter_by(
                    **filter_map).order_by(case(value=Groups.source, whens={"自定义": 0,
                                                                            "自动": 1,
                                                                            "组织架构同步": 2}), Groups.group_id.desc()),
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
                or_(Users.username.like(f'%{value}%'), Users.nickname.like(f'%{value}%'), Users.department.like(f'%{value}%'))), **params)
        else:
            page = paginate(session.query(Users).filter(Users.status == '0', Users.user_id.notin_(user_list)).filter_by(**filter_map), **params)
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
            roles_info = session.query(GroupRoles.role_id, Roles.role_name, Roles.desc).outerjoin(Roles, Roles.role_id == GroupRoles.role_id).outerjoin(Groups, Groups.group_id == GroupRoles.group_id).filter(Groups.group_name == group_name, GroupRoles.status == '0', Roles.status == '0').all()
    queryset = [dict(zip(dict_list, msg)) for msg in roles_info]
    return len(queryset), queryset


def get_relate_group_list_for_group(**kwargs) -> tuple:
    """通过用户组查找关联组织架构"""
    group_id = kwargs.get('group_id')
    group_name = kwargs.get('group_name')
    dict_list = ['group_id', 'group_name', 'status']
    with DBContext('r') as session:
        if group_id:
            group_info = session.query(Groups.group_id, Groups.group_name, Groups.status).outerjoin(GroupsRelate, GroupsRelate.relate_id == Groups.group_id).filter(
                GroupsRelate.status == '0', GroupsRelate.group_id == group_id).all()
        else:
            group_info = session.query(Groups.group_id, Groups.group_name, Groups.status).outerjoin(GroupsRelate,
                                                                                     GroupsRelate.relate_id == Groups.group_id).filter(
                GroupsRelate.status == '0', Groups.group_name == group_name).all()
    queryset = [dict(zip(dict_list, msg)) for msg in group_info]
    return len(queryset), queryset


# 权限
def sign_privilege(**params) -> tuple:
    """给某角色赋值
    资源类型： business，app， menu， component， function
    """
    role_id = params.get('role_id')
    data = params.get('data')
    with DBContext('r') as session:
        for d in data:
            resource_type, id_list, app_code = d.get('resource_type'), d.get('id_list', []), d.get('app_code')

            if resource_type == 'business':
                try:
                    session.query(RoleBusiness).filter(RoleBusiness.role_id == role_id).update(dict(status='20'))
                    session.commit()
                    for business_id in id_list:
                        data = dict(
                                role_id=role_id,
                                business_id=business_id,
                                status='0',
                            )
                        session.add(GetInsertOrUpdateObj(RoleBusiness,
                                                     f"role_id='{role_id}' and business_id='{business_id}'",
                                                     **data))
                    session.commit()
                except Exception as e:
                    return False, f"授权业务权限失败, {e}"

            elif resource_type == 'app':
                try:
                    session.query(RoleApp).filter(RoleApp.role_id == role_id).update(dict(status='20'))
                    session.commit()
                    for app_id in id_list:
                        data = dict(
                            role_id=role_id,
                            app_id=app_id,
                            status='0',
                        )
                        session.add(GetInsertOrUpdateObj(RoleApp,
                                                         f"role_id='{role_id}' and app_id='{app_id}'",
                                                         **data))
                    session.commit()
                except Exception as e:
                    return False, f"授权应用权限失败, {e}"

            elif resource_type == 'menu':
                try:
                    update_delete = session.query(RoleMenu.role_menu_id).outerjoin(Menus,
                                                                                   Menus.menu_id == RoleMenu.menu_id).filter(
                        RoleMenu.role_id == role_id,
                        Menus.app_code == app_code).all()
                    update_delete_id = [d[0] for d in update_delete]
                    if update_delete_id:
                        session.query(RoleMenu).filter(RoleMenu.role_menu_id.in_(update_delete_id)).update(
                            dict(status='20'), synchronize_session='fetch')
                    session.commit()

                    # 父menu赋权
                    parent_menu = session.query(Menus.parent_id).filter(Menus.menu_id.in_(id_list), Menus.status == '0',
                                                                        Menus.app_code == app_code).all()

                    cnt = 0
                    while parent_menu and cnt < 50:
                        cnt += 1
                        parent_menu_id = [p[0] for p in parent_menu]
                        parent_menu_id = list(set(parent_menu_id))
                        id_list += parent_menu_id
                        parent_menu = session.query(Menus.parent_id).filter(Menus.menu_id.in_(parent_menu_id),
                                                                            Menus.app_code == app_code,
                                                                            Menus.status == '0').all()
                    id_list = list(set(id_list))
                    if 0 in id_list:
                        id_list.remove(0)
                    for menu_id in id_list:
                        data = dict(
                                role_id=role_id,
                                menu_id=menu_id,
                                status='0',
                            )
                        session.add(GetInsertOrUpdateObj(RoleMenu,
                                                         f"role_id='{role_id}' and menu_id='{menu_id}'",
                                                         **data))
                    session.commit()
                except Exception as e:
                    return False, f"授权菜单权限失败, {e}"

            elif resource_type == 'component':
                try:
                    # 每一页保存
                    # current_menu_id = d.get('current_menu_id')
                    # if not current_menu_id:
                    #     return False, '组件授权缺少必要参数, current_menu_id'
                    # session.query(RoleComponent).filter(RoleComponent.role_id == role_id, RoleComponent.component_id == Components.component_id, Components.menu_id == current_menu_id,
                    #     RoleComponent.status != '20').update(dict(status='20'),  synchronize_session=False)
                    # session.commit()
                    # for component_id in id_list:
                    #     data = dict(
                    #         role_id=role_id,
                    #         component_id=component_id,
                    #         status='0',
                    #     )
                    #     session.add(GetInsertOrUpdateObj(RoleComponent,
                    #                                      f"role_id='{role_id}' and component_id='{component_id}'",
                    #                                      **data))
                    # session.commit()

                    # 所有页保存
                    update_delete = session.query(RoleComponent.role_component_id).outerjoin(Components,
                                                                                             Components.component_id == RoleComponent.component_id).filter(
                        RoleComponent.role_id == role_id,
                        Components.app_code == app_code).all()
                    update_delete_id = [d[0] for d in update_delete]
                    if update_delete_id:
                        session.query(RoleComponent).filter(RoleComponent.role_component_id.in_(update_delete_id)).update(
                            dict(status='20'), synchronize_session='fetch')
                    session.commit()
                    for component_id in id_list:
                        data = dict(
                            role_id=role_id,
                            component_id=component_id,
                            status='0',
                        )
                        session.add(GetInsertOrUpdateObj(RoleComponent,
                                                         f"role_id='{role_id}' and component_id='{component_id}'",
                                                         **data))
                    session.commit()
                except Exception as e:
                    return False, f"授权组件权限失败, {e}"

            elif resource_type == 'function':
                try:
                    update_delete = session.query(RoleFunction.role_function_id).outerjoin(Functions, Functions.function_id == RoleFunction.function_id).filter(RoleFunction.role_id == role_id, Functions.app_code == app_code).all()
                    update_delete_id = [d[0] for d in update_delete]
                    if update_delete_id:
                        session.query(RoleFunction).filter(RoleFunction.role_function_id.in_(update_delete_id)).update(
                            dict(status='20'), synchronize_session='fetch')
                    session.commit()
                    for function_id in id_list:
                        data = dict(
                            role_id=role_id,
                            function_id=function_id,
                            status='0',
                        )
                        session.add(GetInsertOrUpdateObj(RoleFunction,
                                                         f"role_id='{role_id}' and function_id='{function_id}'",
                                                         **data))
                    session.commit()
                except Exception as e:
                    return False, f"授权接口权限失败, {e}"

        session.query(Roles).filter(Roles.role_id == role_id).update(dict(is_confg=True))
        session.commit()

        redis_conn = cache_conn()
        redis_conn.set(f"need_sync_all_cache", 'y', ex=600)
    return True, '授权成功'


def get_user_privilege(**params) -> tuple:
    """获取用户的权限
    """
    user_id, username = params.get('user_id'), params.get('username')
    resource_list = params.get('resource_list', [])

    _, role_list = get_role_list_for_user(user_id=user_id, user_name=username)
    role_list = [r.get('role_id') for r in role_list]
    data = get_role_privilege(role_list=role_list, resource_list=resource_list)
    return data


def get_role_privilege(**params) -> tuple:
    """获取角色的权限
    资源类型： business，app， menu， component， function
    """
    role_list = params.get('role_list')
    resource_list = params.get('resource_list', [])
    app_code = params.get("app_code")

    with DBContext('r') as session:
        if not resource_list:  # 全部资源
            resource_query = session.query(Resources.resource_type).filter(Resources.status == '0').all()
        else:
            resource_query = session.query(Resources.resource_type).filter(Resources.status == '0', Resources.resource_type.in_(resource_list)).all()

    data = {}
    for q in resource_query:
        resource = q[0]
        # if resource == 'business':
        #     data[resource] = get_business_list_for_role(role_list)
        # if resource == 'app':
        #     data[resource] = get_apps_list_for_role(role_list)
        if resource == 'menu':
            data[resource] = get_menu_list_for_role(role_list, app_code=app_code)
        if resource == 'component':
            data[resource] = get_components_list_for_role(role_list, app_code=app_code)
        if resource == 'function':
            data[resource] = get_func_list_for_role(role_list, app_code=app_code)
    return data


def get_role_privilege_transfer(**params) -> tuple:
    """获取角色的权限 适用于穿梭框
    资源类型： business，app， menu， component， function
    """
    role_list = params.get('role_list')
    resource_list = params.get('resource_list', [])
    app_code = params.get("app_code")

    with DBContext('r') as session:
        if not resource_list:  # 全部资源
            resource_query = session.query(Resources.resource_type).filter(Resources.status == '0').all()
        else:
            resource_query = session.query(Resources.resource_type).filter(Resources.status == '0', Resources.resource_type.in_(resource_list)).all()

    data = {"front": [], "function": []}
    for q in resource_query:
        resource = q[0]
        # if resource == 'business':
        #     data[resource] = get_business_list_for_role(role_list)
        # if resource == 'app':
        #     data[resource] = get_apps_list_for_role(role_list)
        if resource == 'menu':
            tmp = get_menu_list_for_role(role_list, app_code=app_code)
            for i in tmp:
                data["front"].append(f"menu-{i['menu_id']}")
        if resource == 'component':
            tmp = get_components_list_for_role(role_list, app_code=app_code)
            for i in tmp:
                data["front"].append(f"component-{i['component_id']}")
        if resource == 'function':
            tmp = get_func_list_for_role(role_list, app_code=app_code)
            data["function"] = [i["function_id"] for i in tmp]
    return data


# 订阅
def get_role_subscribe(**params) -> tuple:
    """获取角色的订阅
    订阅类型： frontend， function
    """
    role_list = params.get('role_list')
    subscribe_type = params.get('subscribe_type', [])
    with DBContext('r') as session:
        if not subscribe_type:  # 全部资源
            subscribe_query = session.query(SubscribeRole).filter(SubscribeRole.status == '0', SubscribeRole.role_id.in_(role_list)).all()
        else:
            subscribe_query = session.query(SubscribeRole).filter(SubscribeRole.status == '0', SubscribeRole.role_id.in_(role_list), SubscribeRole.subscribe_type.in_(subscribe_type)).all()
    return len(subscribe_query), queryset_to_list(subscribe_query)


def get_subscribe_preview(**params) -> tuple:
    """获取订阅预览
    """
    subscribe_type = params.get('subscribe_type')
    match_type = params.get('match_type')
    match_key = params.get('match_key')

    # 前缀prefix, 后缀suffix，包含contain，正则reg，排除exclude
    if match_type == 'prefix':
        like_str = f'{match_key}%'
    if match_type == 'suffix':
        like_str = f'%{match_key}'
    if match_type == 'contain':
        like_str = f'%{match_key}%'
    if match_type == 'reg':
        like_str = f'{match_key}'
    if match_type == 'exclude':
        like_str = f'%{match_key}%'

    if subscribe_type == 'function':
        method_type = ["GET"] if params.get('match_method') == 'GET' else ["GET", "PUT", "POST", "PATCH", "DELETE"]

    with DBContext('r') as session:
        app_all = params.get('app_all', False)
        if app_all:
            app_list = session.query(Apps.app_code).filter(Apps.status == '0').all()
            app_list = [a[0] for a in app_list]
        else:
            app_list = params.get('app_list')

        if subscribe_type == 'function':
            data = session.query(Functions).filter(Functions.status == '0', Functions.app_code.in_(app_list),
                                                   Functions.method_type.in_(method_type))
            if match_type == 'exclude':
                data = data.filter(Functions.path.notlike(like_str)).all()
            else:
                data = data.filter(Functions.path.like(like_str)).all()
            result = [dict(
                resource_type='function',
                data=queryset_to_list(data)
            )]

        if subscribe_type == 'frontend':
            menu_data = session.query(Menus).filter(Menus.status == '0', Menus.app_code.in_(app_list))
            component_data = session.query(Components).filter(Components.status == '0', Components.app_code.in_(app_list))
            if match_type == 'exclude':
                menu_data = menu_data.filter(Menus.menu_name.notlike(like_str)).all()
                component_data = component_data.filter(Components.component_name.notlike(like_str)).all()
            else:
                menu_data = menu_data.filter(Menus.menu_name.like(like_str)).all()
                component_data = component_data.filter(Components.component_name.like(like_str)).all()
            result = []
            if menu_data:
                result.append(dict(
                    resource_type='menu',
                    data=queryset_to_list(menu_data)
                ))
            if component_data:
                result.append(dict(
                    resource_type='component',
                    data=queryset_to_list(component_data)
                ))
    return result


def sign_subscribe(**params) -> tuple:
    """订阅赋权
    """
    subscribe_data = get_subscribe_preview(**params)
    role_id = params.get('role_id')

    with DBContext('r') as session:
        for sub in subscribe_data:
            resource_type = sub.get('resource_type')
            data = sub.get('data')

            if resource_type == 'function':
                function_id_list = [d.get('function_id') for d in data]
                # 剔除已经手动添加过的
                custom_function = session.query(RoleFunction.function_id).filter(RoleFunction.role_id == role_id,
                                                                                    RoleFunction.function_id.in_(
                                                                                        function_id_list),
                                                                                    RoleFunction.status == '0',
                                                                                    RoleFunction.source == 'custom').all()
                custom_function = [i[0] for i in custom_function]
                need_add_list = [m for m in function_id_list if m not in custom_function]

                for function_id in need_add_list:
                    data = dict(
                        role_id=role_id,
                        function_id=function_id,
                        status='0',
                        source='subscribe'
                    )
                    session.add(
                        GetInsertOrUpdateObj(RoleFunction, f"role_id='{role_id}' and function_id='{function_id}'",
                                             **data))
                    session.commit()
            if resource_type == 'menu':
                menu_id_list = [d.get('menu_id') for d in data]

                # 剔除已经手动添加过的
                custom_menu = session.query(RoleMenu.menu_id).filter(RoleMenu.role_id == role_id, RoleMenu.menu_id.in_(menu_id_list), RoleMenu.status == '0', RoleMenu.source == 'custom').all()
                custom_menu = [i[0] for i in custom_menu]
                need_add_list = [m for m in menu_id_list if m not in custom_menu]

                for menu_id in need_add_list:
                    data = dict(
                            role_id=role_id,
                            menu_id=menu_id,
                            status='0',
                            source='subscribe'
                        )
                    session.add(GetInsertOrUpdateObj(RoleMenu, f"role_id='{role_id}' and menu_id='{menu_id}'", **data))
                    session.commit()

            if resource_type == 'component':
                component_id_list = [d.get('component_id') for d in data]

                # 剔除已经手动添加过的
                custom_component = session.query(RoleComponent.component_id).filter(RoleComponent.role_id == role_id, RoleComponent.component_id.in_(component_id_list), RoleComponent.status == '0', RoleComponent.source == 'custom').all()
                custom_component = [i[0] for i in custom_component]
                need_add_list = [m for m in component_id_list if m not in custom_component]

                for component_id in need_add_list:
                    data = dict(
                            role_id=role_id,
                            component_id=component_id,
                            status='0',
                            source='subscribe'
                        )
                    session.add(GetInsertOrUpdateObj(RoleComponent, f"role_id='{role_id}' and component_id='{component_id}'", **data))
                    session.commit()

        session.query(Roles).filter(Roles.role_id == role_id).update(dict(is_confg=True))
        session.commit()
        redis_conn = cache_conn()
        redis_conn.set(f"need_sync_all_cache", 'y', ex=600)

    return True


def unsign_subscribe(**params) -> tuple:
    """订阅删除，接触赋权
    """
    subscribe_data = get_subscribe_preview(**params)
    role_id = params.get('role_id')

    for sub in subscribe_data:
        resource_type = sub.get('resource_type')
        data = sub.get('data')
        with DBContext('r') as session:
            if resource_type == 'function':
                function_id_list = [d.get('function_id') for d in data]
                session.query(RoleFunction).filter(RoleFunction.role_id == role_id, RoleFunction.status == '0', RoleFunction.source == 'subscribe', RoleFunction.function_id.in_(function_id_list)).delete(synchronize_session=False)
                session.commit()
            if resource_type == 'menu':
                menu_id_list = [d.get('menu_id') for d in data]
                session.query(RoleMenu).filter(RoleMenu.role_id == role_id, RoleMenu.status == '0',
                                                   RoleMenu.source == 'subscribe',
                                                   RoleMenu.menu_id.in_(menu_id_list)).delete(
                    synchronize_session=False)
                session.commit()

            if resource_type == 'component':
                component_id_list = [d.get('component_id') for d in data]
                session.query(RoleComponent).filter(RoleComponent.role_id == role_id, RoleComponent.status == '0',
                                               RoleComponent.source == 'subscribe',
                                               RoleComponent.component_id.in_(component_id_list)).delete(
                    synchronize_session=False)
    return True


# log
def get_opt_log_list(page: int = 1, limit: int = 30, start_date=None, end_date=None, filter_map: dict = None) -> tuple:
    limit_start = (int(page) - 1) * int(limit)

    if start_date and end_date:
        try:
            start_time_tuple = datetime.datetime.strptime(start_date, "%Y-%m-%dT%H:%M:%S.%fZ") + datetime.timedelta(
                hours=8)
            end_time_tuple = datetime.datetime.strptime(end_date, "%Y-%m-%dT%H:%M:%S.%fZ") + datetime.timedelta(
                hours=8)
        except ValueError as err:
            start_time_tuple = datetime.datetime.strptime(start_date, "%Y-%m-%d")
            end_time_tuple = datetime.datetime.strptime(end_date, "%Y-%m-%d")

    else:
        start_date = datetime.date.today() - datetime.timedelta(days=30)
        end_date = datetime.date.today() + datetime.timedelta(days=1)
        start_time_tuple = time.strptime(str(start_date), '%Y-%m-%d')
        end_time_tuple = time.strptime(str(end_date), '%Y-%m-%d')

    with DBContext('r') as db:
        if filter_map:
            __info = db.query(OperationRecord).filter(OperationRecord.create_time > start_time_tuple,
                                                      OperationRecord.create_time < end_time_tuple).filter_by(
                **filter_map).order_by(-OperationRecord.id).offset(limit_start).limit(int(limit))
            count = db.query(OperationRecord).filter(OperationRecord.create_time > start_time_tuple,
                                                     OperationRecord.create_time < end_time_tuple).filter_by(
                **filter_map).order_by(-OperationRecord.id).count()
        else:
            __info = db.query(OperationRecord).filter(OperationRecord.create_time > start_time_tuple,
                                                      OperationRecord.create_time < end_time_tuple).order_by(
                -OperationRecord.id).offset(limit_start).limit(int(limit))
            count = db.query(OperationRecord).filter(OperationRecord.create_time > start_time_tuple,
                                                     OperationRecord.create_time < end_time_tuple).order_by(
                -OperationRecord.id).count()

    queryset = queryset_to_list(__info)
    return count, queryset


def add_operation_log(data: dict):
    """用户操作日志"""
    with DBContext('w', None, True) as session:
        new_log = OperationLogs(**data)
        session.add(new_log)
        session.commit()
        log_id = new_log.id
    return log_id


def add_sync_log(data: dict):
    """系统同步日志"""
    with DBContext('w', None, True) as session:
        new_log = SyncLogs(**data)
        session.add(new_log)
        session.commit()
        log_id = new_log.id
    return log_id


# token
def get_token_list(page: int = 1, limit: int = 100, filter_value=None, **filter_map) -> tuple:
    limit_start = (int(page) - 1) * int(limit)

    with DBContext('r') as db:
        if int(limit) > 100:
            token_info = db.query(UserToken).filter(UserToken.status != '10').order_by(UserToken.user_id)
            count = db.query(UserToken).filter(UserToken.status != '10').count()
        else:
            token_info = db.query(UserToken).filter(UserToken.status != '10').filter(
                or_(UserToken.user_id == filter_value, UserToken.details.like(f'%{filter_value}%'),
                    UserToken.nickname.like(f'%{filter_value}%'),
                    UserToken.token == filter_value)).filter_by(
                **filter_map).order_by(UserToken.user_id).offset(limit_start).limit(int(limit))

            count = db.query(UserToken).filter(UserToken.status != '10').filter(
                or_(UserToken.user_id == filter_value, UserToken.details.like(f'%{filter_value}%'),
                    UserToken.nickname.like(f'%{filter_value}%'),
                    UserToken.token == filter_value)).filter_by(**filter_map).count()
    queryset = []
    for msg in token_info:
        msg = model_to_dict(msg)
        msg['token'] = f"{msg.get('token')[0:10]} --------  {msg.get('token')[-10:]}"
        queryset.append(msg)
    return count, queryset


#### 我的收藏
PydanticFavorites = sqlalchemy_to_pydantic(FavoritesModel, exclude=['id'])  ### 排除自增ID
PydanticFavoritesUP = sqlalchemy_to_pydantic(FavoritesModel)


def get_favorites_list(**params) -> tuple:
    nickname = params.get('nickname')
    app_code = params.get('app_code', 'overall')
    key = params.get('key', '')
    with DBContext('r') as session:
        page = paginate(session.query(FavoritesModel).filter(FavoritesModel.app_code == app_code,
                                                             FavoritesModel.nickname == nickname,
                                                             FavoritesModel.key == key), **params)
    return page.total, page.items


def add_favorites(data: dict):
    """添加收藏"""
    # try:
    #     PydanticFavorites(**data)
    # except ValidationError as e:
    #     return dict(code=-1, msg=str(e))
    if '_index' in data: data.pop('_index')
    if '_rowKey' in data: data.pop('_rowKey')
    try:
        with DBContext('w', None, True) as db:
            db.add(FavoritesModel(**data))
    except IntegrityError as e:
        with DBContext('w', None, True) as db:
            db.query(FavoritesModel).filter(FavoritesModel.app_code == data.get('app_code'),
                                            FavoritesModel.nickname == data.get('nickname'),
                                            FavoritesModel.key == data.get('key')).update(data)
        return dict(code=0, msg="修改成功")
    except Exception as err:
        return dict(code=-1, msg='创建失败')

    return dict(code=0, msg="创建成功")


def up_favorites(data: dict):
    """修改收藏"""
    if '_index' in data: data.pop('_index')
    if '_rowKey' in data: data.pop('_rowKey')
    # try:
    #     valid_data = PydanticFavorites(**data)
    # except ValidationError as e:
    #     return dict(code=-1, msg=str(e))

    try:
        with DBContext('w', None, True) as db:
            db.query(FavoritesModel).filter(FavoritesModel.app_code == data.get('app_code'),
                                            FavoritesModel.nickname == data.get('nickname'),
                                            FavoritesModel.key == data.get('key')).update(data)
    except IntegrityError as e:
        return dict(code=-2, msg="添加重复了")
    except Exception as err:
        return dict(code=-3, msg=f'修改失败, {str(err)}')

    return dict(code=0, msg="修改成功")


def del_favorites(data: dict):
    """删除收藏"""
    try:
        valid_data = PydanticDel(**data)
    except ValidationError as e:
        return dict(code=-1, msg=str(e))

    try:
        with DBContext('w', None, True) as db:
            db.query(FavoritesModel).filter(FavoritesModel.id == valid_data.id).delete(synchronize_session=False)
    except Exception as err:
        return dict(code=-3, msg=f'删除失败, {str(err)}')

    return dict(code=0, msg="删除成功")


def is_super_user(nicknamae: str):
    """查看用户是否为超级用户"""
    return False




