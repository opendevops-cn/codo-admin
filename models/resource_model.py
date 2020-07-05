#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
author : shenshuo
date   : 2020年4月02日
desc   : 扩展组管理（资源组/业务线/项目组）
"""

from datetime import datetime
from typing import List
from shortuuid import uuid
from websdk.db_context import DBContext
from websdk.model_utils import queryset_to_list
from sqlalchemy.exc import IntegrityError
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel, ValidationError, constr
from models.admin import Users

Base = declarative_base()


class ResourceOrm(Base):
    __tablename__ = 'mg_resource_group'

    ### 资源组
    id = Column(Integer, primary_key=True, autoincrement=True)

    resource_id = Column('resource_id', String(50), unique=True, default="rg-{}".format(uuid()))
    code = Column('code', String(30), unique=True, nullable=False)  ## 这里不要太长，会影响格式
    name = Column('name', String(30), unique=True, nullable=False)  ## 这里不要太长，会影响格式
    entity = Column('entity', String(100), default='')
    expand = Column('expand', String(10), index=True, default='no')  # 可以扩展为目录/默认只有标记的属性
    state = Column('state', String(10), index=True, default='enabled')  # 是否启用
    ctime = Column('ctime', DateTime(), default=datetime.now)


class UserResource(Base):
    __tablename__ = 'mg_user_resource'

    ### 用户与资源组关联
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column('user_id', Integer, index=True)
    group_id = Column('group_id', Integer, index=True)


### schemas

class ResourceModel(BaseModel):
    code: constr(max_length=30)
    name: constr(max_length=30)
    entity: constr(max_length=100) = ''
    user_id: int = None

    class Config:
        orm_mode = True


class ResourceCreateModel(ResourceModel):
    expand: constr(max_length=10)


class ResourceUpdateModel(ResourceModel):
    id: int
    expand: constr(max_length=10)


class ResourceDeleteModel(BaseModel):
    id: int


class ResourceUserModel(BaseModel):
    id: int
    user_list: List[int] = []


class ResourceStateModel(BaseModel):
    id: int
    state: constr(max_length=10)

    class Config:
        orm_mode = True


## crud
### 根据用户昵称查询所有有权限资源
### 查询所有限资源
def get_resource(key: str = None, value: str = None) -> list:
    new_queryset = []
    with DBContext('r') as db:
        if key and value:
            queryset = queryset_to_list(db.query(ResourceOrm).filter_by(**{key: value}).all())
        else:
            queryset = queryset_to_list(db.query(ResourceOrm).all())

        for i in queryset:
            user_list = db.query(UserResource.user_id).outerjoin(ResourceOrm, ResourceOrm.id == UserResource.group_id
                                                                 ).filter(ResourceOrm.id == i.get('id')).all()
            i['user_list'] = [u[0] for u in user_list]
            new_queryset.append(i)
    return new_queryset


### 添加
def create_resource(data: dict):
    try:
        ResourceCreateModel(**data)
    except ValidationError as e:
        return dict(code=-1, msg=str(e))

    try:
        with DBContext('w', None, True) as db:
            db.add(ResourceOrm(**data))
    except IntegrityError as e:
        return dict(code=-2, msg='不要重复添加相同的资源组')

    return dict(code=0, msg="添加成功")


### 修改
def update_resource(data: dict):
    try:
        valid_data = ResourceUpdateModel(**data)
    except ValidationError as e:
        return dict(code=-1, msg=str(e))

    try:
        with DBContext('w', None, True) as db:
            db.query(ResourceOrm).filter(ResourceOrm.id == valid_data.id).update(
                {'name': valid_data.name, 'code': valid_data.code, 'expand': valid_data.expand,
                 'entity': valid_data.entity})
    except Exception as err:
        return dict(code=-2, msg='修改失败, {}'.format(str(err)))

    return dict(code=0, msg="修改成功")


def delete_resource(data: dict):
    try:
        ResourceDeleteModel(**data)
    except ValidationError as e:
        return dict(code=-1, msg=str(e))

    with DBContext('w', None, True) as db:
        try:
            db.query(ResourceOrm).filter(ResourceOrm.id == data.get('id')).delete(synchronize_session=False)
        except Exception as err:
            return dict(code=-2, msg='删除失败, {}'.format(str(err)))

    return dict(code=0, msg="删除成功")


def resource_user(data: dict):
    try:
        valid_data = ResourceUserModel(**data)
    except ValidationError as e:
        return dict(code=-1, msg=str(e))

    with DBContext('w', None, True) as db:
        try:
            db.query(UserResource).filter(UserResource.group_id == valid_data.id).delete(synchronize_session=False)
            for user_id in valid_data.user_list: db.add(UserResource(group_id=valid_data.id, user_id=user_id))
        except Exception as err:
            return dict(code=-2, msg='修改失败, {}'.format(str(err)))

    return dict(code=0, msg="修改成功")


### 根据用户昵称查询所有有权限资源
def get_all_by_user(nickname: str, state: str = 'enabled') -> list:
    with DBContext('r') as db:
        info = db.query(ResourceOrm).outerjoin(UserResource, UserResource.group_id == ResourceOrm.id).outerjoin(
            Users, Users.user_id == UserResource.user_id).filter(Users.nickname == nickname,
                                                                 ResourceOrm.state == state).all()
    return queryset_to_list(info)


def get_all_by_id(user_id: id, state: str = 'enabled') -> list:
    with DBContext('r') as db:
        info = db.query(ResourceOrm).outerjoin(UserResource, UserResource.group_id == ResourceOrm.id).filter(
            UserResource.user_id == user_id, ResourceOrm.state == state).all()
    return queryset_to_list(info)