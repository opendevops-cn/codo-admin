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
from sqlalchemy import or_
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.sqlalchemy_pagination import paginate
from websdk2.tools import convert
from websdk2.cache_context import cache_conn
from models.paas_model import BizModel
from websdk2.model_utils import CommonOptView

ROLE_USER_INFO_STR = "ROLE_USER_INFO_STR"
opt_obj = CommonOptView(BizModel)


# opt_obj2 = CommonOptView(TenantModel)


def _get_biz_value(value: str = None):
    if not value:
        return True
    return or_(
        BizModel.biz_cn_name.like(f'%{value}%'), BizModel.biz_en_name.like(f'%{value}%'),
        BizModel.biz_sre.like(f'%{value}%'), BizModel.biz_developer.like(f'%{value}%'),
        BizModel.biz_tester.like(f'%{value}%'), BizModel.life_cycle.like(f'%{value}%'),
    )


def get_biz_list_for_api(**params) -> dict:
    value = params.get('searchValue') if "searchValue" in params else params.get('searchVal')

    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    if 'biz_id' in filter_map:
        filter_map.pop('biz_id')  # 暂时不隔离
    if 'page_size' not in params:
        params['page_size'] = 300  # 默认获取到全部数据
    add_init_default()
    with DBContext('r') as session:
        page = paginate(session.query(BizModel).filter(_get_biz_value(value)).filter_by(**filter_map), **params)

    for b in page.items:
        if b.get('maintainer'):
            b['maintainer'] = b.get('maintainer').get('role')
        if b.get('biz_sre'):
            b['biz_sre'] = b.get('biz_sre').get('role')
        if b.get('biz_developer'):
            b['biz_developer'] = b.get('biz_developer').get('role')
        if b.get('biz_tester'):
            b['biz_tester'] = b.get('biz_tester').get('role')
        if b.get('biz_pm'):
            b['biz_pm'] = b.get('biz_pm').get('role')

    return dict(msg='获取成功', code=0, count=page.total, data=page.items)


def add_init_default():
    # 添加初始化 公共项目
    with DBContext('w', None, True) as session:
        is_exist = session.query(BizModel).filter(BizModel.biz_cn_name == '所有项目').first()
        if is_exist:
            return

        session.add(BizModel(**dict(biz_cn_name='所有项目', biz_en_name='all', biz_id=str(500), life_cycle='已上线')))
        session.add(
            BizModel(**dict(biz_cn_name='公共项目', biz_en_name='public', biz_id=str(501), life_cycle='已上线')))
        session.add(
            BizModel(**dict(biz_cn_name='默认项目', biz_en_name='default', biz_id=str(502), life_cycle='已上线')))
    return


def get_biz_list_v3(**params):
    params['page_size'] = 300  # 默认获取到全部数据
    is_superuser = params.get('is_superuser')
    user_id = params.get('user_id')

    with DBContext('r') as session:
        queryset = session.query(BizModel).filter(BizModel.life_cycle != "停运").all()
    view_biz_list = []
    for b in queryset:
        print(is_superuser,user_id, b.biz_id, b.users_info)
        if is_superuser or b.biz_id in ['501', '502'] or user_id in b.users_info:
            view_biz_list.append(
                dict(id=b.id, biz_id=b.biz_id, biz_cn_name=b.biz_cn_name, biz_en_name=b.biz_en_name))
    return view_biz_list


# def get_biz_tree(**params) -> list:
#     # TODO 后续补充权限
#     the_tree = []
#     is_superuser = params.get('is_superuser')
#     user = params.get('user')
#     with DBContext('r') as session:
#         b_set = session.query(TenantModel).all()
#         for t in b_set:
#             tmp_data = dict(
#                 label=t.name,
#                 tenantid=t.tenantid,
#                 value=t.tenantid,
#                 id=t.id,
#                 children=[{
#                     "label": biz.biz_cn_name,
#                     "biz_id": biz.biz_id,
#                     "value": biz.biz_id,
#                     "id": biz.id,
#                 } for biz in t.biz if is_superuser or user in biz.ext_info]
#             )
#             the_tree.append(tmp_data)
#     return the_tree


# def _get_t_value(value: str = None):
#     if not value:
#         return True
#     return or_(
#         TenantModel.tenantid.like(f'%{value}%'),
#         TenantModel.name.like(f'%{value}%')
#     )
#
#
# def get_tenant_list_for_api(**params) -> dict:
#     value = params.get('searchValue') if "searchValue" in params else params.get('searchVal')
#
#     filter_map = params.pop('filter_map') if "filter_map" in params else {}
#     if 'biz_id' in filter_map:
#         filter_map.pop('biz_id')
#     if 'page_size' not in params:
#         params['page_size'] = 300  # 默认获取到全部数据
#
#     with DBContext('r') as session:
#         page = paginate(session.query(TenantModel).filter(_get_t_value(value)).filter_by(**filter_map), **params)
#     return dict(msg='获取成功', code=0, count=page.total, data=page.items)


def _get_s_value(value: str = None):
    if not value:
        return True
    return or_(
        BizModel.id == value,
    )


def sync_biz_role_user(**params):
    the_id = params.get('id')
    redis_conn = cache_conn()
    role_user_info = redis_conn.get(ROLE_USER_INFO_STR)
    role_user_dict = json.loads(convert(role_user_info))
    new_data = []

    if not role_user_dict or not isinstance(role_user_dict, dict):
        return dict(msg='缓存数据有误', code=-1)

    with DBContext('w', None, True) as session:
        queryset = session.query(BizModel).filter(BizModel.life_cycle != "停运", _get_s_value(the_id)).all()

        for b in queryset:
            biz_user_list = []
            for field in ['maintainer', 'biz_sre', 'biz_developer', 'biz_tester', 'biz_pm']:
                try:
                    roles = b.__dict__.get(field, {}).get('role')
                    if roles is None:
                        continue
                    for r in roles:
                        if r is None:
                            continue
                        biz_user_list.extend(list(role_user_dict.get(str(r), {}).keys()))
                except Exception as err:
                    pass
            # Get current ext_info value, create an empty dictionary if it's None
            # current_ext_info = b.ext_info if b.ext_info else {}
            #
            # # Ensure current_ext_info['users'] is initialized as an empty list
            # current_ext_info.setdefault('users', [])
            #
            # # Update ext_info field with the list of users
            # current_ext_info['users'] = list(set(biz_user_list))
            print(biz_user_list)
            new_data.append({'id': b.id, 'users_info': list(set(biz_user_list))})

        session.bulk_update_mappings(BizModel, new_data)
        session.commit()
