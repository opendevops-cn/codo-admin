#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2021/11/10 14:33 
Desc    : 解释一下吧
"""

from sqlalchemy import Column, String, Integer, DateTime, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class TimeBaseModel(object):
    """模型基类，为模型补充创建时间与更新时间"""
    id = Column('id', Integer, primary_key=True, autoincrement=True)
    create_time = Column(DateTime, nullable=False, default=datetime.now, index=True)  # 记录的创建时间
    update_time = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now, index=True)  # 记录的更新时间


class BusinessModel(TimeBaseModel, Base):
    __tablename__ = 'mg_biz_list'

    id = Column('id', Integer, primary_key=True, autoincrement=True)
    business_id = Column('business_id', String(11), index=True, unique=True)
    business_en = Column('business_en', String(80), unique=True, index=True)  ###业务英文命
    business_zh = Column('business_zh', String(80), index=True, default='')  ###业务中文名
    resource_group = Column('resource_group', String(80), index=True, default='')  ###资源组名 / 资源隔离名
    maintainer = Column('maintainer', JSON(), default="")
    user_list = Column('user_list', JSON(), default=[])
    group_list = Column('group_list', JSON(), default=[])
    corporate = Column('corporate', String(255), default="")  ### 公司实体
    sort = Column('sort', Integer, default=10, index=True)  ### 排序
    life_cycle = Column('life_cycle', String(15), default='已上线', index=True)  ### 开发中  测试中  已上线  停运
    description = Column('description', String(255), default='')  ### 描述、备注

    business_group = Column('business_group', String(50), default='')  ### 业务集 CMS/OPS
    client_group_id = Column('client_group_id', String(11), nullable=True)  ### 租户组id
    map_client_id = Column('map_client_id', Integer, index=True, nullable=True)
    __mapper_args__ = {"order_by": (sort, business_en)}


class BusinessTreeModel(Base):
    __tablename__ = 'biz_tree'

    create_time = Column(DateTime, nullable=False, default=datetime.now, index=True)  # 记录的创建时间
    update_time = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now, index=True)  # 记录的更新时间
    tree_id = Column('tree_id', Integer, primary_key=True, autoincrement=True)
    business_set = Column('title', String(50), index=True, unique=True, nullable=True)  ## 业务集title
    parent = Column('parent', Integer, index=True, nullable=True)  # 上层业务集
    business_list = Column('business_list', JSON(), default=[])
    tree_node = Column('tree_node', Boolean, default=True)
    tag = Column('tag', String(50), default='', index=True)
    status = Column('status', String(5), default='0', index=True)
