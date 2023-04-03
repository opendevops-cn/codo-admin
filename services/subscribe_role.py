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
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.model_utils import queryset_to_list, model_to_dict, GetInsertOrUpdateObj
from models.authority_model import Menus, Functions, Components, Apps, Roles, \
    OperationRecord, OperationLogs, SyncLogs, RoleApp, \
    RoleBusiness, RoleMenu, RoleComponent, RoleFunction, Resources, SubscribeRole
from websdk2.cache_context import cache_conn

from models.biz_model import BusinessModel


def get_role_subscribe(**params) -> tuple:
    """获取角色的订阅
    订阅类型： frontend， function
    """
    role_list = params.get('role_list')
    subscribe_type = params.get('subscribe_type', [])
    with DBContext('r') as session:
        if not subscribe_type:  # 全部资源
            subscribe_query = session.query(SubscribeRole).filter(SubscribeRole.status == '0',
                                                                  SubscribeRole.role_id.in_(role_list)).all()
        else:
            subscribe_query = session.query(SubscribeRole).filter(SubscribeRole.status == '0',
                                                                  SubscribeRole.role_id.in_(role_list),
                                                                  SubscribeRole.subscribe_type.in_(
                                                                      subscribe_type)).all()
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
            component_data = session.query(Components).filter(Components.status == '0',
                                                              Components.app_code.in_(app_list))
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
                custom_menu = session.query(RoleMenu.menu_id).filter(RoleMenu.role_id == role_id,
                                                                     RoleMenu.menu_id.in_(menu_id_list),
                                                                     RoleMenu.status == '0',
                                                                     RoleMenu.source == 'custom').all()
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
                custom_component = session.query(RoleComponent.component_id).filter(RoleComponent.role_id == role_id,
                                                                                    RoleComponent.component_id.in_(
                                                                                        component_id_list),
                                                                                    RoleComponent.status == '0',
                                                                                    RoleComponent.source == 'custom').all()
                custom_component = [i[0] for i in custom_component]
                need_add_list = [m for m in component_id_list if m not in custom_component]

                for component_id in need_add_list:
                    data = dict(
                        role_id=role_id,
                        component_id=component_id,
                        status='0',
                        source='subscribe'
                    )
                    session.add(
                        GetInsertOrUpdateObj(RoleComponent, f"role_id='{role_id}' and component_id='{component_id}'",
                                             **data))
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
                session.query(RoleFunction).filter(RoleFunction.role_id == role_id, RoleFunction.status == '0',
                                                   RoleFunction.source == 'subscribe',
                                                   RoleFunction.function_id.in_(function_id_list)).delete(
                    synchronize_session=False)
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
