#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
author : shenshuo
date   : 2023年06月05日
desc   : 平台管理
"""
from datetime import datetime

from sqlalchemy import Column, String, Integer, JSON, UniqueConstraint, Text
from sqlalchemy import DateTime
from sqlalchemy.dialects.mysql import LONGTEXT, MEDIUMTEXT
from sqlalchemy.ext.declarative import declarative_base
from websdk2.utils.cc_crypto import AESCryptoV3

from models import TimeBaseModel

Base = declarative_base()
mc = AESCryptoV3()


class AppsModel(TimeBaseModel, Base):
    __tablename__ = 'codo_apps'

    # 应用名称表
    id = Column('id', Integer, primary_key=True, autoincrement=True)
    name = Column('name', String(100), unique=True)
    app_code = Column('app_code', String(100), index=True)  #
    href = Column('href', String(255), default='')  # 前端直接跳转的URL  没用接入的应用使用
    # path = Column('path', String(255), default='')  # 文件加载地址
    img = Column('img', String(255), default='')  # 图片地址
    icon = Column('icon', String(255), default='')  # 图标
    classify = Column('classify', String(50), default='SaaS', index=True)  # 分类
    description = Column('description', String(250), default='')  # 描述、备注


class FavoritesModel(Base):
    __tablename__ = 'codo_favorites'

    # 用户收藏表
    id = Column('id', Integer, primary_key=True, autoincrement=True)
    nickname = Column('nickname', String(80), default="团团团", index=True)
    app_code = Column('app_code', String(20), default="overall", index=True)
    key = Column('key', String(35), default="", index=True)
    value = Column('value', JSON(), default='{}')
    __table_args__ = (UniqueConstraint('nickname', 'app_code', 'key', name="app_code_and_key_nickname"),)


# class TenantModel(TimeBaseModel, Base):
#     __tablename__ = 'codo_tenant'
#
#     id = Column('id', Integer, primary_key=True, autoincrement=True)
#     tenantid = Column('tenantid', String(15), unique=True)
#     name = Column('name', String(50), unique=True, comment='租户')  # 业务集  租户
#     sort = Column('sort', Integer, default=100, index=True, comment='排序')  # 排序
#     description = Column('description', String(255), default='', comment='描述')  # 描述、备注
#     # biz = relationship('BizModel', backref='codo_biz')  # 默认一对多


class BizModel(TimeBaseModel, Base):
    __tablename__ = 'codo_biz'

    id = Column('id', Integer, primary_key=True, autoincrement=True)
    biz_id = Column('biz_id', String(15), index=True, unique=True)
    biz_en_name = Column('biz_en_name', String(50), unique=True)  # 业务英文命
    biz_cn_name = Column('biz_cn_name', String(50), index=True, default='')  # 业务中文名

    maintainer = Column('maintainer', JSON(), comment='管理员')
    biz_sre = Column('biz_sre', JSON(), comment='运维人员')
    biz_developer = Column('biz_developer', JSON(), comment='开发人员')
    biz_tester = Column('biz_tester', JSON(), comment='测试人员')
    biz_pm = Column('biz_pm', JSON(), comment='产品运营')
    ext_info = Column('ext_info', JSON(), default={}, comment='扩展字段存JSON')  # 扩展字段
    users_info = Column('users_info', JSON(), default={}, comment='换成用户JSON')

    corporate = Column('corporate', String(255), default="", comment='公司实体')  # 公司实体
    sort = Column('sort', Integer, default=100, index=True)  # 排序
    life_cycle = Column('life_cycle', String(15), default='已上线', index=True)  # 开发中  测试中  已上线  停运
    description = Column('description', String(255), default='')  # 描述、备注
    update_time = Column(DateTime, nullable=False, default=datetime.now, index=True)  # 更新时间 改为非自动

    # tenantid = Column(String(12), ForeignKey('codo_tenant.tenantid'))
    # set_model = relationship("TenantModel", backref=backref("codo_tenant", uselist=False))

    # @property
    # def custom_extend_column_dict(self):
    #     return {"tenant": self.set_model.name}


class LoginLinkModel(TimeBaseModel, Base):
    __tablename__ = 'codo_login_link'

    # 登录链接
    id = Column('id', Integer, primary_key=True, autoincrement=True)
    name = Column('name', String(100), nullable=False, index=True)
    login_url = Column('login_url', String(255), nullable=False, index=True)  # 后端登录地址
    real_url = Column('real_url', String(255), nullable=False, default='')  # 跳转地址
    client_id = Column('client_id', String(255), nullable=False, default='')  # 应用ID
    code = Column('code', String(50), nullable=False, default='', unique=True)  #


class SystemSettings(TimeBaseModel, Base):
    __tablename__ = 'codo_sys_settings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)  # key
    value = Column(Text(), default="", comment='数据')  # value
    is_secret = Column(String(5), default="n")  # 加密

    @property
    def custom_secret_data(self):
        if self.is_secret == 'n':
            return {"value": self.value}
        else:
            return {"value": None}


class StorageMG(TimeBaseModel, Base):
    __tablename__ = 'codo_mg_storage'

    # 用户上传数据记录
    id = Column('id', Integer, primary_key=True, autoincrement=True)
    storage_key = Column('storage_key', String(80))
    nickname = Column('nickname', String(80), default="匿名", index=True)
    action = Column('action', String(15), default="上传")
    storage_type = Column('storage_type', String(15), default='OSS')
    file_dir = Column('file_dir', String(80), default='', index=True)
    filename = Column('filename', String(150), default='', index=True)


class OperationRecords(TimeBaseModel, Base):
    __tablename__ = 'codo_opt_records'

    # 操作记录
    id = Column('id', Integer, primary_key=True, autoincrement=True)
    user_id = Column('user_id', String(128), index=True)
    username = Column('username', String(128), index=True)
    nickname = Column('nickname', String(128), index=True)
    client_ip = Column('client_ip', String(25))
    service_name = Column('service_name', String(35))
    scheme = Column('scheme', String(25))
    trace_id = Column('trace_id', String(80), index=True)
    latency = Column('latency', String(128))
    upstream = Column('upstream', String(255))

    method = Column('method', String(10), index=True)
    uri = Column('uri', String(255), index=True)
    rq_headers = Column('rq_headers', MEDIUMTEXT())
    rq_data = Column('rq_data', LONGTEXT())
    start_time = Column('start_time', DateTime(), default=datetime.now)
    response_data = Column('response_data', LONGTEXT())
    response_status = Column('response_status', String(15))
