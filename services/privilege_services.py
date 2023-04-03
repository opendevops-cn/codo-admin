#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2020/12/10 15:14
Desc    : 解释一下吧
"""

from websdk2.db_context import DBContextV2 as DBContext
from websdk2.model_utils import GetInsertOrUpdateObj
from models.authority_model import Menus, Functions, Components, Apps, Roles, RoleApp, \
    RoleBusiness, RoleMenu, RoleComponent, RoleFunction, Resources, SubscribeRole, GroupsRelate
from websdk2.cache_context import cache_conn

from services.role_services import get_menu_list_for_role
from services.role_services import get_components_list_for_role
from services.role_services import get_func_list_for_role
from services.role_services import get_role_list_for_user


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
                        session.query(RoleComponent).filter(
                            RoleComponent.role_component_id.in_(update_delete_id)).update(
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
                    update_delete = session.query(RoleFunction.role_function_id).outerjoin(Functions,
                                                                                           Functions.function_id == RoleFunction.function_id).filter(
                        RoleFunction.role_id == role_id, Functions.app_code == app_code).all()
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
            resource_query = session.query(Resources.resource_type).filter(Resources.status == '0',
                                                                           Resources.resource_type.in_(
                                                                               resource_list)).all()

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
            resource_query = session.query(Resources.resource_type).filter(Resources.status == '0',
                                                                           Resources.resource_type.in_(
                                                                               resource_list)).all()

    data = {"front": [], "function": []}
    for q in resource_query:
        resource = q[0]
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
