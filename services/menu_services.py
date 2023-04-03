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
from sqlalchemy.exc import IntegrityError
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.model_utils import model_to_dict
from websdk2.utils.pydantic_utils import sqlalchemy_to_pydantic, ValidationError, PydanticDel, BaseModel
from websdk2.sqlalchemy_pagination import paginate
from models.authority_model import Menus, RoleMenu, Apps


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
                menu_query = session.query(Menus.menu_id).filter(Menus.status == '0',
                                                                 Menus.parent_id.in_(menu_id)).all()
                menu_id = [m[0] for m in menu_query]
                menu_id = list(set(menu_id))
                all_menu_id += menu_id

            page = paginate(session.query(Menus).filter(Menus.status == '0', Menus.menu_id.in_(all_menu_id)), **params)
    return page.total, page.items


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
                menu_query = session.query(Menus.menu_id).filter(Menus.status == '0',
                                                                 Menus.parent_id.in_(menu_id)).all()
                menu_id = [m[0] for m in menu_query]
                menu_id = list(set(menu_id))
                all_menu_id += menu_id

            page = paginate(session.query(Menus).filter(Menus.status == '0', Menus.menu_id.in_(all_menu_id)), **params)
    return page.total, page.items


PydanticMenus = sqlalchemy_to_pydantic(Menus, exclude=['menu_id'])  ### 排除自增ID
PydanticMenusUP = sqlalchemy_to_pydantic(Menus)


class PydanticcMenusDel(BaseModel):
    menu_id: int


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
            comp_info = session.query(RoleMenu.menu_id, Menus.menu_name).outerjoin(Menus,
                                                                                   Menus.menu_id == RoleMenu.menu_id).filter(
                RoleMenu.role_id.in_(role_list), RoleMenu.status == '0', Menus.status == '0',
                                                 Menus.app_code == app_code).all()
        else:
            comp_info = session.query(RoleMenu.menu_id, Menus.menu_name).outerjoin(Menus,
                                                                                   Menus.menu_id == RoleMenu.menu_id).filter(
                RoleMenu.role_id.in_(role_list), RoleMenu.status == '0', Menus.status == '0').all()
        queryset = [dict(zip(dict_list, msg)) for msg in comp_info]
    return queryset
