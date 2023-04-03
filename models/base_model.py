#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
author : shenshuo
date   : 2023年2月23日
desc   : 管理后台数据库
"""

from sqlalchemy import Column, String, Integer, DateTime, Text, JSON, UniqueConstraint, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class TimeBaseModel(object):
    """模型基类，为模型补充创建时间与更新时间"""
    create_time = Column(DateTime, nullable=False, default=datetime.now, index=True)  # 记录的创建时间
    update_time = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)  # 记录的更新时间
