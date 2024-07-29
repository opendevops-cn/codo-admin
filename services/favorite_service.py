#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023年06月05日
Desc    : 用户收藏
"""

from sqlalchemy.exc import IntegrityError
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.sqlalchemy_pagination import paginate

from libs.feature_pydantic_utils import sqlalchemy_to_pydantic, ValidationError, PydanticDel
from models.paas_model import FavoritesModel

PydanticFavorites = sqlalchemy_to_pydantic(FavoritesModel, exclude=['id'])  # 排除自增ID
PydanticFavoritesUP = sqlalchemy_to_pydantic(FavoritesModel)


def get_favorites_list(**params) -> tuple:
    nickname = params.get('nickname')
    app_code = params.get('app_code', 'overall')
    key = params.get('key', '')
    with DBContext('r') as session:
        page = paginate(session.query(FavoritesModel).filter(FavoritesModel.app_code == app_code,
                                                             FavoritesModel.nickname == nickname,
                                                             FavoritesModel.key == key), **params)
    return page.total, page.items


def add_favorites(data: dict):
    """添加收藏"""
    if '_index' in data: data.pop('_index')
    if '_rowKey' in data: data.pop('_rowKey')
    try:
        with DBContext('w', None, True) as db:
            db.add(FavoritesModel(**data))
    except IntegrityError as e:
        with DBContext('w', None, True) as db:
            db.query(FavoritesModel).filter(FavoritesModel.app_code == data.get('app_code'),
                                            FavoritesModel.nickname == data.get('nickname'),
                                            FavoritesModel.key == data.get('key')).update(data)
        return dict(code=0, msg="修改成功")
    except Exception as err:
        return dict(code=-1, msg='创建失败')

    return dict(code=0, msg="创建成功")


def up_favorites(data: dict):
    """修改收藏"""
    if '_index' in data: data.pop('_index')
    if '_rowKey' in data: data.pop('_rowKey')
    try:
        with DBContext('w', None, True) as db:
            db.query(FavoritesModel).filter(FavoritesModel.app_code == data.get('app_code'),
                                            FavoritesModel.nickname == data.get('nickname'),
                                            FavoritesModel.key == data.get('key')).update(data)
    except IntegrityError as e:
        return dict(code=-2, msg="添加重复了")
    except Exception as err:
        return dict(code=-3, msg=f'修改失败, {str(err)}')

    return dict(code=0, msg="修改成功")


def del_favorites(data: dict):
    """删除收藏"""
    try:
        valid_data = PydanticDel(**data)
    except ValidationError as e:
        return dict(code=-1, msg=str(e))

    try:
        with DBContext('w', None, True) as db:
            db.query(FavoritesModel).filter(FavoritesModel.id == valid_data.id).delete(synchronize_session=False)
    except Exception as err:
        return dict(code=-3, msg=f'删除失败, {str(err)}')

    return dict(code=0, msg="删除成功")
