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
from models.authority_model import Menus, Functions, Components, Apps

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


# 用户
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
