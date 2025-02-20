#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2024/12/6 15:14
Desc    : 业务数据
"""

import json
import logging
from sqlalchemy import or_
from websdk2.cache_context import cache_conn
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.sqlalchemy_pagination import paginate
from websdk2.tools import convert

from libs.feature_model_utils import CommonOptView
from models.paas_model import BizModel

ROLE_USER_INFO_STR = "ROLE_USER_INFO_STR"
opt_obj = CommonOptView(BizModel)


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
    # with DBContext('w', None, True) as session:
    #     is_exist = session.query(BizModel).filter(BizModel.biz_cn_name == '所有项目').first()
    #     if is_exist:
    #         return
    #
    #     session.add(BizModel(**dict(biz_cn_name='所有项目', biz_en_name='all', biz_id=str(500), life_cycle='已上线')))
    #     session.add(
    #         BizModel(**dict(biz_cn_name='公共项目', biz_en_name='public', biz_id=str(501), life_cycle='已上线')))
    #     session.add(
    #         BizModel(**dict(biz_cn_name='默认项目', biz_en_name='default', biz_id=str(502), life_cycle='已上线')))
    #     session.add(
    #         BizModel(**dict(biz_cn_name='运维项目', biz_en_name='ops', biz_id=str(504), life_cycle='已上线')))

    init_data = [
        dict(biz_cn_name='所有项目', biz_en_name='all', biz_id='500', life_cycle='已上线'),
        dict(biz_cn_name='公共项目', biz_en_name='public', biz_id='501', life_cycle='已上线'),
        dict(biz_cn_name='默认项目', biz_en_name='default', biz_id='502', life_cycle='已上线'),
        dict(biz_cn_name='运维项目', biz_en_name='ops', biz_id='504', life_cycle='已上线')
    ]
    with DBContext('w', None, True) as session:
        # 获取已存在的项目名称
        existing_names = {row.biz_cn_name for row in session.query(BizModel.biz_cn_name).all()}

        # 过滤需要插入的记录
        new_records = [BizModel(**data) for data in init_data if data['biz_cn_name'] not in existing_names]

        if new_records:
            session.add_all(new_records)
    return


# TODO 待废弃
def get_biz_list_v3(**params):
    params['page_size'] = 300  # 默认获取到全部数据
    is_superuser = params.get('is_superuser')
    user_id = params.get('user_id')

    with DBContext('r') as session:
        queryset = session.query(BizModel).filter(BizModel.life_cycle != "停运").all()
        view_biz_list = []
        for b in queryset:
            if is_superuser or b.biz_id in ['501', '502'] or str(user_id) in b.users_info:
                view_biz_list.append(
                    dict(id=b.id, biz_id=b.biz_id, biz_cn_name=b.biz_cn_name, biz_en_name=b.biz_en_name))
    # print(view_biz_list)
    return view_biz_list


def get_biz_list_v4(**params):
    try:
        params['page_size'] = 300  # 默认获取到全部数据
        is_superuser = params.get('is_superuser')
        user_id = params.get('user_id')

        # 使用数据库上下文进行查询，并且在查询时加入过滤条件，减少无用数据的传输
        with DBContext('r') as session:
            # 过滤掉停运的业务，确保只处理有效的业务
            queryset = session.query(BizModel).filter(BizModel.life_cycle != "停运").all()

            # 构建返回的业务列表
            view_biz_list = [
                dict(id=b.id, biz_id=b.biz_id, biz_cn_name=b.biz_cn_name, biz_en_name=b.biz_en_name)
                for b in queryset
                if can_view_biz(is_superuser, user_id, b)
            ]

        return view_biz_list

    except Exception as err:
        logging.error(f"Error occurred in get_biz_list_v4: {err}")
        return {"code": -1, "msg": "服务器内部错误"}


def can_view_biz(is_superuser, user_id, biz_model):
    """
    Helper function to determine if the user has permission to view the business.
    """
    # Check if the user is a superuser or has access to the business
    return is_superuser or biz_model.biz_id in ['501', '502'] or str(user_id) in biz_model.users_info


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
    if not role_user_info:
        logging.error(f"ROLE_USER_INFO_STR 为空")
        return
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
            new_data.append({'id': b.id, 'users_info': list(set(biz_user_list))})

        session.bulk_update_mappings(BizModel, new_data)
        session.commit()


def get_biz_map(view_biz, request_tenant_id) -> dict:
    if request_tenant_id:
        # 使用 next() 寻找第一个匹配的业务，如果没有找到则返回 None
        the_biz = next((biz for biz in view_biz if biz.get('biz_id') == request_tenant_id), None)
    else:
        # 使用列表推导式过滤出不包含指定 biz_id 的业务列表
        the_biz_list = [biz for biz in view_biz if biz.get('biz_id') not in ['501', '502']]
        the_biz = the_biz_list[0] if the_biz_list else None

    return dict(biz_cn_name=the_biz.get('biz_cn_name'), biz_id=the_biz.get('biz_id')) if the_biz else None


def switch_business(set_secure_cookie, **params) -> dict:
    biz_id = params.get('biz_id') or params.get('tenantid')
    is_superuser = params.get('is_superuser')
    user_id = params.get('user_id')

    # 参数验证
    if not biz_id:
        return {"code": -1, "msg": "缺少必要参数"}

    # 封装数据库查询和权限检查
    try:
        with DBContext('r') as session:
            biz_info = session.query(BizModel).filter(BizModel.biz_id == str(biz_id)).first()

            # 业务信息检查
            if not biz_info:
                return {"code": -2, "msg": "未知业务信息/资源组信息"}
            # 权限检查，是否为超级用户或该用户是否在业务信息中
            if not (biz_id in ['501', '502'] or is_superuser or user_id in biz_info.users_info):
                return {"code": -3, "msg": "你没有访问的业务权限，请联系管理员"}

    except Exception as db_err:
        logging.error(f"数据库查询失败: {db_err}")
        return {"code": -4, "msg": "数据库操作失败"}

    # 设置cookie
    try:
        set_secure_cookie("biz_id", str(biz_info.biz_id))
    except Exception as err:
        logging.error(f"设置 cookie 失败: {err}")
        return {"code": -5, "msg": "设置 cookie 失败"}

    # 返回业务数据
    biz_dict = {
        "biz_id": str(biz_info.biz_id),
        "biz_cn_name": str(biz_info.biz_cn_name),
        "biz_en_name": biz_info.biz_en_name
    }

    return {"code": 0, "msg": "获取成功", "data": biz_dict}
