#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2021/1/27 11:02 
Desc    : 解释一下吧
"""

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from .pydantic_utils import sqlalchemy_to_pydantic, ValidationError
from .notice_model import NoticeConfig, NoticeTemplate
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.sqlalchemy_pagination import paginate

PydanticNoticeConfig = sqlalchemy_to_pydantic(NoticeConfig, exclude=['id'])
PydanticNoticeConfigUP = sqlalchemy_to_pydantic(NoticeConfig)


### 模板查询
def get_notice_template(**params):
    value = params.get('searchValue') if "searchValue" in params else params.get('value')
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    if 'resource_group' in filter_map: filter_map.pop('resource_group')  ### 暂时不隔离
    if 'page_size' not in params: params['page_size'] = 300  ### 默认获取到全部数据
    with DBContext('r') as session:
        if value:
            page = paginate(session.query(NoticeTemplate).filter(
                or_(NoticeTemplate.name.like(f'%{value}%'), NoticeTemplate.way.like(f'{value}%'),
                    NoticeTemplate.msg_template.like(f'{value}%'), NoticeTemplate.id == value,
                    NoticeTemplate.remark.like(f'%{value}%'))).filter_by(**filter_map), **params)
        else:
            page = paginate(session.query(NoticeTemplate).filter_by(**filter_map), **params)

    return page.total, page.items


### 添加
def add_notice_config(data: dict):
    try:
        PydanticNoticeConfig(**data)
    except ValidationError as e:
        return dict(code=-1, msg=str(e))

    try:
        with DBContext('w', None, True) as db:
            db.add(NoticeConfig(**data))
    except IntegrityError as e:
        return dict(code=-2, msg='不要重复添加相同的配置')

    return dict(code=0, msg="配置创建成功")


### 修改
def update_notice_config(data: dict):
    try:
        valid_data = PydanticNoticeConfigUP(**data)
    except ValidationError as e:
        return dict(code=-1, msg=str(e))

    try:
        with DBContext('w', None, True) as db:
            db.query(NoticeConfig).filter(NoticeConfig.id == valid_data.id).update(data)
    except Exception as err:
        return dict(code=-2, msg='修改失败, {}'.format(str(err)))

    return dict(code=0, msg="修改成功")
