#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2024年12月02日
Desc    : 首页卡片
"""

import json
from collections import defaultdict
from sqlalchemy import or_
from websdk2.sqlalchemy_pagination import paginate
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.model_utils import queryset_to_list

from libs.feature_pydantic_utils import sqlalchemy_to_pydantic, ValidationError, PydanticDel
from models.paas_model import IndexStepModel, IndexServiceModel

PydanticFavorites = sqlalchemy_to_pydantic(IndexStepModel, exclude=['id'])  # 排除自增ID
PydanticFavoritesUP = sqlalchemy_to_pydantic(IndexStepModel)


def get_step_list() -> dict:
    with DBContext('r') as session:
        queryset = queryset_to_list(session.query(IndexStepModel).all())
    return dict(code=0, msg="创建成功", data=queryset)


def add_step(data: dict):
    """添加"""
    if '_index' in data: data.pop('_index')
    if '_rowKey' in data: data.pop('_rowKey')
    try:
        with DBContext('w', None, True) as db:
            db.add(IndexStepModel(**data))
    except Exception as err:
        return dict(code=-1, msg='创建失败')

    return dict(code=0, msg="创建成功")


def up_step(data: dict):
    """修改"""
    if '_index' in data: data.pop('_index')
    if '_rowKey' in data: data.pop('_rowKey')
    if 'id' not in data:
        return dict(code=-1, msg="缺少关键参数ID")
    try:
        with DBContext('w', None, True) as db:
            db.query(IndexStepModel).filter(IndexStepModel.id == data.get('id')).update(data)
    except Exception as err:
        return dict(code=-3, msg=f'修改失败, {str(err)}')

    return dict(code=0, msg="修改成功")


def del_step(data: dict):
    """删除"""
    try:
        valid_data = PydanticDel(**data)
    except ValidationError as e:
        return dict(code=-1, msg=str(e))

    try:
        with DBContext('w', None, True) as db:
            db.query(IndexStepModel).filter(IndexStepModel.id == valid_data.id).delete(synchronize_session=False)
    except Exception as err:
        return dict(code=-3, msg=f'删除失败, {str(err)}')

    return dict(code=0, msg="删除成功")


def get_service_dict() -> dict:
    with DBContext('w', None, True) as session:
        result = session.query(IndexServiceModel).all()
        result = queryset_to_list(result)
        # 初始化嵌套的结果字典
        formatted_result = []

        for service in result:
            # 获取regions字段
            regions = service.get('regions', {}).get('all', [])

            # 生成具体的服务项
            service_item = {
                "title": service.get('name', ''),
                "description": service.get('description', ''),
                "href": service.get('href', '')
            }

            # 组织服务项到不同地区
            for region in regions:
                # 查找当前category是否已经存在
                category_found = False
                for category_item in formatted_result:
                    if category_item["categoryName"] == service['category']:
                        category_found = True
                        # 将服务项添加到对应地区
                        category_item["categoryData"]["regionServices"].setdefault(region, []).append(service_item)
                        break

                # 如果该类别没有找到，添加新的类别项
                if not category_found:
                    formatted_result.append({
                        "categoryName": service['category'],
                        "categoryData": {
                            "regionServices": {
                                region: [service_item]
                            }
                        }
                    })

    return dict(code=0, data=formatted_result)


def _get_value(value: str = None):
    if not value: return True
    return or_(
        IndexServiceModel.id == value,
        IndexServiceModel.category == value,
        IndexServiceModel.regions.like(f'%{value}%'),
        IndexServiceModel.name.like(f'%{value}%'),
        IndexServiceModel.description.like(f'%{value}%')
    )


def get_service_list(**params) -> dict:
    value = params.get('searchValue') or params.get('searchVal')
    filter_map = params.pop('filter_map', {})
    filter_map.pop('biz_id', None)  # 暂时不隔离 biz_id

    params.setdefault('page_size', 300)
    with DBContext('r') as session:
        query = session.query(IndexServiceModel).filter(_get_value(value))

        # 使用 filter_map 添加过滤条件
        if filter_map:
            query = query.filter_by(**filter_map)

        # 分页查询
        page = paginate(query, **params)
    return dict(code=0, msg="创建成功", data=page.items, count=page.total)


def add_service(data: dict):
    """添加"""
    if '_index' in data: data.pop('_index')
    if '_rowKey' in data: data.pop('_rowKey')
    try:
        with DBContext('w', None, True) as db:
            db.add(IndexServiceModel(**data))
    except Exception as err:
        return dict(code=-1, msg='创建失败')

    return dict(code=0, msg="创建成功")


def up_service(data: dict) -> dict:
    """添加"""
    if '_index' in data: data.pop('_index')
    if '_rowKey' in data: data.pop('_rowKey')
    if 'id' not in data:
        return dict(code=-1, msg="缺少关键参数ID")
    try:
        with DBContext('w', None, True) as db:
            db.query(IndexServiceModel).filter(IndexServiceModel.id == data.get('id')).update(data)
    except Exception as err:
        return dict(code=-3, msg=f'修改失败, {str(err)}')

    return dict(code=0, msg="修改成功")


def del_service(data: dict) -> dict:
    """删除"""
    if 'id' not in data:
        return dict(code=-1, msg="缺少关键参数ID")

    try:
        with DBContext('w', None, True) as db:
            db.query(IndexServiceModel).filter(IndexServiceModel.id == data.get('id')).delete(synchronize_session=False)
    except Exception as err:
        return dict(code=-3, msg=f'删除失败, {str(err)}')

    return dict(code=0, msg="删除成功")
