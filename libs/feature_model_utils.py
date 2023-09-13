#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
Author : shenshuo
Date   : 2019年12月11日
Desc   : models类
"""

from typing import Type, Union
from datetime import datetime
from sqlalchemy.orm import class_mapper
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from websdk2.utils import get_contain_dict
from websdk2.db_context import DBContextV2 as DBContext
from libs.feature_pydantic_utils import sqlalchemy_to_pydantic, ValidationError, PydanticDelList


def model_to_dict(model):
    model_dict = {}
    for key, column in class_mapper(model.__class__).c.items():
        if isinstance(getattr(model, key), datetime):
            model_dict[column.name] = str(getattr(model, key))
        else:
            model_dict[column.name] = getattr(model, key, None)

    if isinstance(getattr(model, "custom_extend_column_dict", None), dict):
        model_dict.update(**getattr(model, "custom_extend_column_dict", {}))
    return model_dict


def queryset_to_list(queryset, **kwargs) -> list:
    if kwargs: return [model_to_dict(q) for q in queryset if get_contain_dict(kwargs, model_to_dict(q))]
    return [model_to_dict(q) for q in queryset]


def GetInsertOrUpdateObj(cls: Type, str_filter: str, **kw) -> classmethod:
    """
    cls:            Model 类名
    str_filter:      filter的参数.eg:"name='name-14'" 必须设置唯一 支持 and or
    **kw:           【属性、值】字典,用于构建新实例，或修改存在的记录
    session.add(GetInsertOrUpdateObj(TableTest, "name='name-114'", age=33114, height=123.14, name='name-114'))
    """
    with DBContext('r') as session:
        existing = session.query(cls).filter(text(str_filter)).first()
    if not existing:
        res = cls()
        for k, v in kw.items():
            if hasattr(res, k):
                setattr(res, k, v)
        return res
    else:
        res = existing
        for k, v in kw.items():
            if hasattr(res, k):
                setattr(res, k, v)

        return res


def insert_or_update(cls: Type[DeclarativeMeta], str_filter: str, **kw) -> Union[None, DeclarativeMeta]:
    """
    cls:            Model 类名
    str_filter:      filter的参数.eg:"name='name-14'" 必须设置唯一 支持 and or
    **kw:           【属性、值】字典,用于构建新实例，或修改存在的记录
    session.add(insert_or_update(TableName, "name='name-114'", age=33114, height=123.14, name='name-114'))
    """
    with DBContext('r') as session:
        existing = session.query(cls).filter(text(str_filter)).first()
    if not existing:
        res = cls(**kw)
        for k, v in kw.items():
            if hasattr(res, k):
                setattr(res, k, v)
        return res
    else:
        res = existing
        for k, v in kw.items():
            if hasattr(res, k):
                setattr(res, k, v)

        return res


class CommonOptView:
    def __init__(self, model, **kwargs):
        self.model = model
        self.pydantic_model_base = sqlalchemy_to_pydantic(model)
        self.pydantic_model = sqlalchemy_to_pydantic(model, exclude=['id'])

    def prepare(self):
        pass

    @staticmethod
    def del_data(data) -> dict:
        if '_index' in data:
            del data['_index']
        if '_rowKey' in data:
            del data['_rowKey']
        return data

    def handle_add(self, data: dict) -> dict:
        self.prepare()
        data = self.del_data(data)
        try:
            self.pydantic_model(**data)
        except ValidationError as e:
            return dict(code=-1, msg=str(e))

        try:
            with DBContext('w', None, True) as db:
                db.add(self.model(**data))
        except IntegrityError as e:
            return dict(code=-2, msg='不要重复添加')

        except Exception as e:
            return dict(code=-3, msg=f'{e}')

        return dict(code=0, msg="创建成功")

    def handle_update(self, data: dict) -> dict:
        self.prepare()
        data = self.del_data(data)
        try:
            valid_data = self.pydantic_model_base(**data)
        except ValidationError as e:
            return dict(code=-1, msg=str(e))

        try:
            with DBContext('w', None, True) as db:
                db.query(self.model).filter(self.model.id == valid_data.id).update(data)

        except IntegrityError as e:
            return dict(code=-2, msg=f'修改失败，已存在')

        except Exception as err:
            return dict(code=-3, msg=f'修改失败, {err}')

        return dict(code=0, msg="修改成功")

    def handle_delete(self, data: dict) -> dict:
        self.prepare()
        try:
            valid_data = PydanticDelList(**data)
        except ValidationError as e:
            return dict(code=-1, msg=str(e))

        with DBContext('w', None, True) as session:
            session.query(self.model).filter(self.model.id.in_(valid_data.id_list)).delete(synchronize_session=False)
        return dict(code=0, msg=f"删除成功")
