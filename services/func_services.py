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
from websdk2.sqlalchemy_pagination import paginate
from models.authority import Functions, RoleFunctions
from websdk2.model_utils import CommonOptView, queryset_to_list

opt_obj = CommonOptView(Functions)


def _get_value(value: str = None):
    if not value: return True
    return or_(
        Functions.id == value,
        Functions.details.like(f'%{value}%'),
        Functions.func_name.like(f'%{value}%'),
        Functions.uri.like(f'%{value}%'),
        Functions.app_code == value
    )


def _get_by_app_code(app_code: str = None):
    """过滤筛选"""
    if not app_code:
        return True

    return or_(
        Functions.app_code == app_code
    )


def get_func_list_for_api(**params) -> dict:
    value = params.get('searchValue') if "searchValue" in params else params.get('searchVal')
    app_code = params.get('app_code')
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    if 'biz_id' in filter_map: filter_map.pop('biz_id')  # 暂时不隔离
    if 'page_size' not in params: params['page_size'] = 300  # 默认获取到全部数据
    with DBContext('r') as session:
        page = paginate(
            session.query(Functions).filter(_get_value(value), _get_by_app_code(app_code)).filter_by(**filter_map),
            **params)

    return dict(code=0, msg="获取成功", count=page.total, data=page.items)


def get_func_list_for_role(role_id: int) -> list:
    with DBContext('r') as db:
        role_func = db.query(Functions).outerjoin(RoleFunctions, Functions.id == RoleFunctions.func_id
                                                  ).filter(RoleFunctions.role_id == role_id).all()

    return queryset_to_list(role_func)

###########
# def get_tree_data(data: list, parent_id: int, parent_type: str):
#     """统一结构，递归获取树结构"""
#     res = []
#     for d in data:
#         if d.get('parent_id') == parent_id and d.get('parent_type') == parent_type:
#             next_type = d.get('record_type')
#             next_idx = 'app_id' if next_type == 'app' else 'menu_id' if next_type == 'menu' else 'component_id' if next_type == 'component' \
#                 else 'function_id'
#             next_pid = d.get(next_idx)
#             d["children"] = get_tree_data(data, next_pid, next_type)
#             d["expand"] = True if len(d["children"]) > 0 else False
#             res.append(d)
#     return res


# def get_func_tree(func_query: list):
#     """处理信息， parent id parent type"""
#     with DBContext('r') as session:
#         app_page = paginate(session.query(Apps).filter(Apps.status == '0'), **{"page_size": 200})
#         app_query = app_page.items
#
#         for app in app_query:
#             app["title"] = app["app_code"]
#             app["parent_id"] = 0
#             app["parent_type"] = "root"
#             app["record_type"] = "app"
#             # parent_info_query.append(app)
#
#     for q in func_query:  # 处理func
#         if q.get('parent_id') == 0:
#             parent_type, parent_id = 'app', [a['app_id'] for a in app_query if a['app_code'] == q.get('app_code')]
#             parent_id = parent_id[0] if parent_id else None
#         else:
#             parent_type, parent_id = 'function', q.get('parent_id')
#         q["title"] = f"【{q.get('method_type')}】{q.get('path')} ({q.get('func_name')})" if q.get(
#             'method_type') else f"{q.get('uri')}"
#         q["parent_id"] = parent_id
#         q["parent_type"] = parent_type
#         q["record_type"] = "function"
#
#     app_query.extend(func_query)
#     res = get_tree_data(app_query, 0, 'root')
#     return res


# def get_func_list(**params) -> tuple:
#     value = params.get('searchValue') if "searchValue" in params else params.get('value')
#
#     filter_map = params.pop('filter_map') if "filter_map" in params else {}
#     params['page_size'] = 5000
#     if "app_code" in params:
#         filter_map['app_code'] = params.get('app_code')
#     else:
#         params["order_by"] = "app_code"
#     if 'resource_group' in filter_map: filter_map.pop('resource_group')
#
#     with DBContext('r') as session:
#         if value:
#             page = paginate(session.query(Functions).filter(Functions.status != '10').filter_by(**filter_map).filter(
#                 or_(Functions.app_code == value, Functions.func_name.like(f'%{value}%'),
#                     Functions.uri.like(f'%{value}%'),
#                     Functions.method_type.like(f'{value}%'), Functions.app_code.like(f'%{value}%'))), **params)
#         else:
#             page = paginate(session.query(Functions).filter(Functions.status != '10').filter_by(**filter_map), **params)
#
#     tree_data = params.get('tree_data') if "tree_data" in params else False
#     if tree_data:
#         result = get_func_tree(page.items)
#
#         if "app_code" in filter_map.keys():
#             for app in result:
#                 if app.get("app_code") == filter_map['app_code']:
#                     result = app
#                     break
#     else:
#         result = page.items
#     return page.total, result


# def get_func_subtree(**params) -> tuple:
#     # 获取func 子树
#     record_type = params.pop('record_type')
#     id = params.pop('id')
#
#     with DBContext('r') as session:
#         if record_type == 'app':
#             app_obj = session.query(Apps.app_code).filter(Apps.app_id == id).first()
#             app_code = app_obj[0]
#             if not app_code:
#                 return 0, []
#
#             page = paginate(session.query(Functions).filter(Functions.status == '0',
#                                                             Functions.app_code == app_code,
#                                                             Functions.method_type != ""), **params)
#         if record_type == 'function':
#             func_id = [int(id)]
#             all_func_id = func_id
#             cnt = 0
#             while func_id and cnt < 50:
#                 cnt += 1
#                 func_query = session.query(Functions.function_id).filter(Functions.status == '0',
#                                                                          Functions.parent_id.in_(func_id),
#                                                                          ).all()
#                 func_id = [m[0] for m in func_query]
#                 func_id = list(set(func_id))
#                 all_func_id += func_id
#
#             page = paginate(session.query(Functions).filter(Functions.status == '0',
#                                                             Functions.function_id.in_(all_func_id),
#                                                             Functions.method_type != ""), **params)
#     return page.total, page.items
