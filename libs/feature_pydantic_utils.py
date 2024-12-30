#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.9
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2024/12/30 20:28
Desc    : https://github.com/tiangolo/pydantic-sqlalchemy
"""

####
from typing import Container, Optional, Type
from pydantic import BaseModel, create_model, ValidationError, ConfigDict


#  删除的时候一般只有id
class PydanticDel(BaseModel):
    id: int


class PydanticDelList(BaseModel):
    id_list: list[int]


def sqlalchemy_to_pydantic(db_model: Type, *, exclude: Container[str] = ()) -> Type[BaseModel]:
    table = db_model.metadata.tables[db_model.__tablename__]
    fields = {}
    config = ConfigDict(from_attributes=True)
    for column in table.columns:
        name = column.name
        if name in exclude:
            continue
        python_type: Optional[type] = None
        if hasattr(column.type, "impl"):
            if hasattr(column.type.impl, "python_type"):
                python_type = column.type.impl.python_type
        elif hasattr(column.type, "python_type"):
            python_type = column.type.python_type
        assert python_type, f"Could not infer python_type for {column}"

        default = ... if column.default is None and not column.nullable else None

        fields[name] = (python_type, default)

    return create_model(db_model.__name__, __config__=config, **fields)
