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
from sqlalchemy import or_, func
from sqlalchemy.exc import IntegrityError
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.model_utils import queryset_to_list, model_to_dict
from websdk2.utils.pydantic_utils import sqlalchemy_to_pydantic, ValidationError, PydanticDel, BaseModel
from websdk2.sqlalchemy_pagination import paginate
from models.admin_model import Menus, RoleMenus, Functions, RoleFunctions, Components, RolesComponents, Apps, RoleApps, \
    Roles, Users, UserRoles, UserToken, OperationRecord, FavoritesModel


def get_user_list_v2(**params) -> tuple:
    value = params.get('searchValue') if "searchValue" in params else params.get('value')
    params["items_not_to_list"] = "yes"
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    # filter_map['status'] = '0'
    if 'resource_group' in filter_map: filter_map.pop('resource_group')

    with DBContext('r') as session:
        if value:
            page = paginate(session.query(Users).filter_by(
                **filter_map).filter(or_(Users.user_id == value, Users.username.like(f'%{value}%'),
                                         Users.nickname.like(f'%{value}%'), Users.email.like(f'%{value}%'),
                                         Users.tel.like(f'%{value}%'),
                                         Users.department.like(f'%{value}%'))), **params)
        else:
            page = paginate(session.query(Users).filter_by(**filter_map), **params)

    queryset = []
    for msg in page.items:
        data_dict = model_to_dict(msg)
        data_dict.pop('password')
        data_dict.pop('google_key')
        queryset.append(data_dict)

    return page.total, queryset


###### 菜单


PydanticMenus = sqlalchemy_to_pydantic(Menus, exclude=['menu_id'])  ### 排除自增ID
PydanticMenusUP = sqlalchemy_to_pydantic(Menus)


class PydanticcMenusDel(BaseModel):
    menu_id: int


def get_menu_list(**params) -> tuple:
    value = params.get('searchValue') if "searchValue" in params else params.get('value')

    filter_map = params.pop('filter_map') if "filter_map" in params else {}
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

    return page.total, page.items


"""添加菜单"""


def add_menu(data: dict):
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


def get_menu_list_for_role(role_id: int) -> list:
    with DBContext('r') as session:
        role_menu = session.query(Menus).outerjoin(RoleMenus, Menus.menu_id == RoleMenus.menu_id).filter(
            RoleMenus.role_id == role_id, RoleMenus.status == '0', Menus.status == '0').all()

    return queryset_to_list(role_menu)


###########

def get_func_list_v2(**params) -> tuple:
    value = params.get('searchValue') if "searchValue" in params else params.get('value')

    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    if "app_code" in params:
        filter_map['app_code'] = params.get('app_code')
    else:
        params["order_by"] = "app_code"
    if 'resource_group' in filter_map: filter_map.pop('resource_group')

    with DBContext('r') as session:
        if value:
            page = paginate(session.query(Functions).filter(Functions.status != '10').filter_by(**filter_map).filter(
                or_(Functions.func_id == value, Functions.func_name.like(f'%{value}%'),
                    Functions.uri.like(f'%{value}%'),
                    Functions.method_type.like(f'{value}%'), Functions.app_code.like(f'%{value}%'))), **params)
        else:
            page = paginate(session.query(Functions).filter(Functions.status != '10').filter_by(**filter_map), **params)

    return page.total, page.items


def get_func_list_for_role(role_id: int) -> list:
    with DBContext('r') as db:
        role_func = db.query(Functions).outerjoin(RoleFunctions, Functions.func_id == RoleFunctions.func_id
                                                  ).filter(RoleFunctions.role_id == role_id,
                                                           RoleFunctions.status == '0').all()

    return queryset_to_list(role_func)


def get_components_list(**params) -> tuple:
    value = params.get('searchValue') if "searchValue" in params else params.get('value')

    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    if "app_code" in params:
        filter_map['app_code'] = params.get('app_code')
    else:
        params["order_by"] = "app_code"

    if 'resource_group' in filter_map: filter_map.pop('resource_group')

    with DBContext('r') as session:
        if value:
            page = paginate(session.query(Components).filter(Components.status != '10').filter_by(**filter_map).filter(
                or_(Components.app_code == value, Components.component_name.like(f'{value}%'),
                    Components.details.like(f'%{value}%'))), **params)
        else:
            page = paginate(session.query(Components).filter(Components.status != '10').filter_by(**filter_map),
                            **params)

    return page.total, page.items


def get_components_list_for_role(role_id: int) -> list:
    with DBContext('r') as session:
        comp_info = session.query(Components).outerjoin(RolesComponents,
                                                        Components.comp_id == RolesComponents.comp_id).filter(
            RolesComponents.role_id == role_id, RolesComponents.status == '0', Components.status == '0').all()

    return queryset_to_list(comp_info)


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


def get_apps_list_for_role(role_id: int) -> list:
    with DBContext('r') as session:
        app_info = session.query(Apps).outerjoin(RoleApps, Apps.app_id == RoleApps.app_id).filter(
            RoleApps.role_id == role_id, RoleApps.status == '0', Apps.status == '0').all()

    return queryset_to_list(app_info)


######角色列表 Roles
def get_roles_list_v2(**params) -> tuple:
    value = params.get('searchValue') if "searchValue" in params else params.get('value')
    params['page_size'] = 300  ### 默认获取到全部数据
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    if 'resource_group' in filter_map: filter_map.pop('resource_group')

    with DBContext('r') as session:
        if value:
            page = paginate(session.query(Roles).filter(Roles.status != '10').filter_by(**filter_map).filter(
                Roles.role_name.like(f'%{value}%')), **params)
        else:
            page = paginate(session.query(Roles).filter(Roles.status != '10').filter_by(**filter_map), **params)

    return page.total, page.items


### 通过角色查找用户
def get_user_list_for_role(**kwargs) -> tuple:
    role_id = kwargs.get('role_id')
    role_name = kwargs.get('role_name')
    dict_list = ['user_role_id', 'role_id', 'user_id', 'username', 'nickname']
    with DBContext('r') as session:
        if role_id:
            count = session.query(UserRoles).filter(UserRoles.status != '10', UserRoles.role_id == role_id).count()
            role_info = session.query(UserRoles.user_role_id, UserRoles.role_id, UserRoles.user_id, Users.username,
                                      Users.nickname).outerjoin(Users, Users.user_id == UserRoles.user_id).filter(
                UserRoles.role_id == role_id, Users.status == '0').order_by(UserRoles.role_id).all()
        else:
            dict_list = ['role_name', 'user_role_id', 'role_id', 'user_id', 'username', 'nickname']
            count = session.query(Roles).outerjoin(UserRoles, UserRoles.role_id == Roles.role_id).filter(
                UserRoles.status != '10', Roles.role_name == role_name).count()
            role_info = session.query(Roles.role_name, UserRoles.user_role_id, UserRoles.role_id, UserRoles.user_id,
                                      Users.username, Users.nickname).outerjoin(UserRoles,
                                                                                UserRoles.role_id == Roles.role_id).outerjoin(
                Users, Users.user_id == UserRoles.user_id).filter(
                Roles.role_name == role_name, Users.status == '0').order_by(UserRoles.role_id).all()

    queryset = [dict(zip(dict_list, msg)) for msg in role_info]
    return count, queryset


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


##
# def get_token_list(page: int = 1, limit: int = 100, filter_value=None, **filter_map) -> tuple:
#     limit_start = (int(page) - 1) * int(limit)
#
#     with DBContext('r') as db:
#         if int(limit) > 100:
#             token_info = db.query(UserToken).filter(UserToken.status != '10').order_by(UserToken.user_id)
#             count = db.query(UserToken).filter(UserToken.status != '10').count()
#         else:
#             token_info = db.query(UserToken).filter(UserToken.status != '10').filter(
#                 or_(UserToken.user_id == filter_value, UserToken.details.like(f'%{filter_value}%'),
#                     UserToken.nickname.like(f'%{filter_value}%'),
#                     UserToken.token == filter_value)).filter_by(
#                 **filter_map).order_by(UserToken.user_id).offset(limit_start).limit(int(limit))
#
#             count = db.query(UserToken).filter(UserToken.status != '10').filter(
#                 or_(UserToken.user_id == filter_value, UserToken.details.like(f'%{filter_value}%'),
#                     UserToken.nickname.like(f'%{filter_value}%'),
#                     UserToken.token == filter_value)).filter_by(**filter_map).count()
#     queryset = []
#     for msg in token_info:
#         msg = model_to_dict(msg)
#         msg['token'] = f"{msg.get('token')[0:10]} --------  {msg.get('token')[-10:]}"
#         queryset.append(msg)
#     return count, queryset


#### 我的收藏

# PydanticFavorites = sqlalchemy_to_pydantic(FavoritesModel, exclude=['id'])  ### 排除自增ID
# PydanticFavoritesUP = sqlalchemy_to_pydantic(FavoritesModel)
#
#
# def get_favorites_list(**params) -> tuple:
#     nickname = params.get('nickname')
#     app_code = params.get('app_code', 'overall')
#     key = params.get('key', '')
#     with DBContext('r') as session:
#         page = paginate(session.query(FavoritesModel).filter(FavoritesModel.app_code == app_code,
#                                                              FavoritesModel.nickname == nickname,
#                                                              FavoritesModel.key == key), **params)
#     return page.total, page.items
#
#
# def add_favorites(data: dict):
#     """添加收藏"""
#     # try:
#     #     PydanticFavorites(**data)
#     # except ValidationError as e:
#     #     return dict(code=-1, msg=str(e))
#     if '_index' in data: data.pop('_index')
#     if '_rowKey' in data: data.pop('_rowKey')
#     try:
#         with DBContext('w', None, True) as db:
#             db.add(FavoritesModel(**data))
#     except IntegrityError as e:
#         with DBContext('w', None, True) as db:
#             db.query(FavoritesModel).filter(FavoritesModel.app_code == data.get('app_code'),
#                                             FavoritesModel.nickname == data.get('nickname'),
#                                             FavoritesModel.key == data.get('key')).update(data)
#         return dict(code=0, msg="修改成功")
#     except Exception as err:
#         return dict(code=-1, msg='创建失败')
#
#     return dict(code=0, msg="创建成功")
#
#
# def up_favorites(data: dict):
#     """修改收藏"""
#     if '_index' in data: data.pop('_index')
#     if '_rowKey' in data: data.pop('_rowKey')
#     # try:
#     #     valid_data = PydanticFavorites(**data)
#     # except ValidationError as e:
#     #     return dict(code=-1, msg=str(e))
#
#     try:
#         with DBContext('w', None, True) as db:
#             db.query(FavoritesModel).filter(FavoritesModel.app_code == data.get('app_code'),
#                                             FavoritesModel.nickname == data.get('nickname'),
#                                             FavoritesModel.key == data.get('key')).update(data)
#     except IntegrityError as e:
#         return dict(code=-2, msg="添加重复了")
#     except Exception as err:
#         return dict(code=-3, msg=f'修改失败, {str(err)}')
#
#     return dict(code=0, msg="修改成功")
#
#
# def del_favorites(data: dict):
#     """删除收藏"""
#     try:
#         valid_data = PydanticDel(**data)
#     except ValidationError as e:
#         return dict(code=-1, msg=str(e))
#
#     try:
#         with DBContext('w', None, True) as db:
#             db.query(FavoritesModel).filter(FavoritesModel.id == valid_data.id).delete(synchronize_session=False)
#     except Exception as err:
#         return dict(code=-3, msg=f'删除失败, {str(err)}')
#
#     return dict(code=0, msg="删除成功")
