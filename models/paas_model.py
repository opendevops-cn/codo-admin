#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
author : shenshuo
date   : 2023年06月05日
desc   : 平台管理
"""
from sqlalchemy import Column, DateTime
from datetime import datetime
from sqlalchemy.orm import relationship, backref
from sqlalchemy import Column, String, Integer, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from models import TimeBaseModel

Base = declarative_base()


class AppsModel(TimeBaseModel, Base):
    __tablename__ = 'codo_apps'

    # 应用名称表
    id = Column('id', Integer, primary_key=True, autoincrement=True)
    name = Column('name', String(100), unique=True)
    app_code = Column('app_code', String(100), index=True)  #
    href = Column('href', String(255), default='')  # 前端直接跳转的URL  没用接入的应用使用
    path = Column('path', String(255), default='')  # 文件加载地址
    img = Column('img', String(255), default='')  # 图片地址
    icon = Column('icon', String(255), default='')  # 图标
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


class TenantModel(TimeBaseModel, Base):
    __tablename__ = 'codo_tenant'

    id = Column('id', Integer, primary_key=True, autoincrement=True)
    tenantid = Column('tenantid', String(15), index=True, unique=True)
    name = Column('name', String(50), index=True, unique=True, comment='业务集')  # 业务集  租户
    sort = Column('sort', Integer, default=100, index=True, comment='排序')  # 排序
    description = Column('description', String(255), default='', comment='描述')  # 描述、备注

    biz = relationship('BizModel', backref='codo_biz')  # 默认一对多


class BizModel(TimeBaseModel, Base):
    __tablename__ = 'codo_biz'

    id = Column('id', Integer, primary_key=True, autoincrement=True)
    biz_id = Column('biz_id', String(15), index=True, unique=True)
    biz_en_name = Column('biz_en_name', String(50), unique=True, index=True)  # 业务英文命
    biz_cn_name = Column('biz_cn_name', String(50), index=True, default='')  # 业务中文名

    maintainer = Column('maintainer', JSON(), comment='管理员')
    biz_sre = Column('biz_sre', JSON(), comment='运维人员')
    biz_developer = Column('biz_developer', JSON(), comment='开发人员')
    biz_tester = Column('biz_tester', JSON(), comment='测试人员')
    biz_pm = Column('biz_pm', JSON(), comment='产品运营')
    ext_info = Column('ext_info', JSON(), default={}, comment='扩展字段存JSON')  # 扩展字段

    corporate = Column('corporate', String(255), default="", comment='公司实体')  # 公司实体
    sort = Column('sort', Integer, default=100, index=True)  # 排序
    life_cycle = Column('life_cycle', String(15), default='已上线', index=True)  # 开发中  测试中  已上线  停运
    description = Column('description', String(255), default='')  # 描述、备注
    update_time = Column(DateTime, nullable=False, default=datetime.now, index=True)  # 更新时间 改为非自动

    tenantid = Column(String(12), ForeignKey('codo_tenant.tenantid'))
    set_model = relationship("TenantModel", backref=backref("codo_tenant", uselist=False))

    @property
    def custom_extend_column_dict(self):
        return {"tenant": self.set_model.name}

    __mapper_args__ = {"order_by": (sort, biz_en_name)}
