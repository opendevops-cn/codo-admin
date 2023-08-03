#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2018/12/7
Desc    : 系统配置项
"""

import json
import base64
from sqlalchemy import Column, String, Integer, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from sqlalchemy import TypeDecorator

Base = declarative_base()


class TimeBaseModel(object):
    """模型基类，为模型补充创建时间与更新时间"""
    create_time = Column(DateTime, nullable=False, default=datetime.now)  # 记录的创建时间
    update_time = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)  # 记录的更新时间


class AppSettings(TimeBaseModel, Base):
    __tablename__ = 'mg_app_settings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)  # key
    value = Column(Text(), default="")  # value
    is_secret = Column(String(5), default="n")  # 加密


class JsonColumn(TypeDecorator):
    impl = Text

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value)
        return value


class JsonSecret(TypeDecorator):
    impl = Text

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json.dumps(value)
            value = base64.b64encode(value.encode())
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = base64.b64decode(value)
            value = json.loads(value)
        return value


class NoticeTemplate(TimeBaseModel, Base):
    ### 通知模板
    __tablename__ = 'mg_notice_template'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column('name', String(50), unique=True, nullable=False)  # 通知模板名称
    user_list = Column('user_list', JSON(), default="")  # 通知用户
    notice_group = Column('notice_group', JSON(), default="")  # 通知组
    user_info = Column('user_info', JsonColumn(), default="")  # 用户信息，定时同步用户列表的内容
    manager_info = Column('manager_info', JsonColumn(), default="")  # 通知用户的上级信息，用来通知升级

    way = Column('way', String(30), index=True, default="sms")  # 通知类型
    silence = Column('silence', Integer, index=True, default=1)  # 静默事件 分钟单位
    notice_conf = Column('notice_conf', String(255), default="")  # '钉钉/微信/短信/短信调用地址 和信息
    msg_template = Column('msg_template', Text(), default="")  # 通知模板
    test_msg = Column('test_msg', JSON(), default="{}")  # 测试数据
    status = Column('status', String(1), default='0')  ###状态（0正常 1停用）
    remark = Column('remark', String(128), default="")  # 备注说明
    extra = Column('extra', JSON(), default="{}")  # 额外字段


class NoticeGroup(TimeBaseModel, Base):
    ### 通知组
    __tablename__ = 'mg_notice_group'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column('name', String(50), unique=True, nullable=False)  # 通知模板名称
    user_list = Column('user_list', JSON(), default="")  # 用户列表
    user_info = Column('user_info', JsonColumn(), default="")  # 用户信息，定时同步用户列表的内容

    remark = Column('remark', String(128), default="")  # 备注说明


class NoticeConfig(TimeBaseModel, Base):
    ### 通知配置
    __tablename__ = 'mg_notice_config'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column('name', String(20), unique=True, nullable=False)  # 配置名称
    key = Column('key', String(20), unique=True, nullable=False)  # 配置索引key
    status = Column('status', String(5), default='0', index=True)
    conf_map = Column('conf_map', JsonSecret(), default="")  # 配置文件

    remark = Column('remark', String(128), default="")  # 备注说明

