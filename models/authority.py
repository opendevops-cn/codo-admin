#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
author : shenshuo
date   : 2023年06月05日
desc   : 平台管理
"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, JSON, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from models import TimeBaseModel

Base = declarative_base()


class Users(TimeBaseModel, Base):
    __tablename__ = 'codo_a_users'

    # 用户表
    id = Column('id', Integer, primary_key=True, autoincrement=True)
    username = Column('username', String(50), nullable=False, index=True)
    password = Column('password', String(100))
    nickname = Column('nickname', String(100), nullable=False, index=True)
    email = Column('email', String(80), index=True)  # 邮箱
    tel = Column('tel', String(18), index=True)  # 手机号
    department = Column('department', String(600))  # 部门
    google_key = Column('google_key', String(80))  # 谷歌认证秘钥
    superuser = Column('superuser', String(5), default='10', index=True)  # 超级用户  '0'代表超级用户
    avatar = Column('avatar', String(1000), default='')  # 头像
    source = Column('source', String(15), default='注册')
    source_account_id = Column('source_account_id', String(250), default='', index=True)
    manager = Column('manager', String(180), default='')  # 上级
    dd_id = Column('dd_id', String(80), default='')  # 钉钉ID
    status = Column('status', String(5), default='0', index=True)  # '0' 正常  '10' 删除  '20' 禁用
    have_token = Column('have_token', String(5), default='no')
    fs_open_id = Column('fs_open_id', String(180), default='')  # 飞书 open id
    fs_id = Column('fs_id', String(180), default='')  # 飞书ID
    ext_info = Column('ext_info', JSON(), default={}, comment='扩展字段存JSON')  # 扩展字段
    ##
    last_ip = Column('last_ip', String(20), default='')
    last_login = Column('last_login', DateTime(), default=datetime.now, onupdate=datetime.now)

    __table_args__ = (UniqueConstraint('username', 'nickname', name="username_and_nickname"),
                      UniqueConstraint('username', 'email', name="username_and_email"),)


class Roles(TimeBaseModel, Base):
    __tablename__ = 'codo_a_roles'
    # 角色表
    id = Column('id', Integer, primary_key=True, autoincrement=True)
    role_name = Column('role_name', String(35), unique=True, index=True)
    details = Column('details', String(250), default='')  # 描述、备注
    status = Column('status', String(5), default='0', index=True)
    role_type = Column('role_type', String(10), default='normal')  # 角色类型， normal, base, default
    role_subs = Column('role_subs', JSON(), default=[])
    is_conf = Column('is_conf', String(5), default='no')  # 是否配置权限  yes no


class UserRoles(Base):
    __tablename__ = 'codo_a_user_role'

    # 用户角色关联表
    id = Column('id', Integer, primary_key=True, autoincrement=True)
    role_id = Column('role_id', Integer, index=True)
    user_id = Column('user_id', Integer, index=True)
    __table_args__ = (UniqueConstraint('role_id', 'user_id', name="role_id_and_user_id"),)


class Menus(TimeBaseModel, Base):
    __tablename__ = 'codo_a_menus'

    # 前端路由权限
    id = Column('id', Integer, primary_key=True, autoincrement=True)
    menu_name = Column('menu_name', String(80), unique=True, index=True)
    pid = Column('pid', Integer, index=True)
    app_code = Column('app_code', String(20), index=True)
    details = Column('details', String(50), default='')  # 描述、备注


class RoleMenus(Base):
    __tablename__ = 'codo_a_role_menus'

    # 角色与前端路由关联
    id = Column('id', Integer, primary_key=True, autoincrement=True)
    role_id = Column('role_id', Integer, index=True)
    menu_id = Column('menu_id', Integer, index=True)


class Functions(TimeBaseModel, Base):
    __tablename__ = 'codo_a_functions'

    # 权限表
    id = Column('id', Integer, primary_key=True, autoincrement=True)
    menu_id = Column('menu_id', Integer, index=True)
    func_name = Column('func_name', String(50), index=True)
    app_code = Column('app_code', String(20), index=True)
    uri = Column('uri', String(250), index=True)
    method_type = Column('method_type', String(10), index=True)
    parameters = Column('parameters', Text(), default='')
    status = Column('status', String(5), default='0', index=True)
    details = Column('details', Text(), default='')  # 描述、备注
    __table_args__ = (UniqueConstraint('app_code', 'func_name', name="app_code_and_func_name"),)


class RoleFunctions(Base):
    __tablename__ = 'codo_a_role_functions'

    # 角色权限关联表
    id = Column('id', Integer, primary_key=True, autoincrement=True)
    role_id = Column('role_id', Integer, index=True)
    func_id = Column('func_id', Integer, index=True)


class RoleApps(Base):
    __tablename__ = 'codo_a_role_apps'

    # 角色应用关联表
    id = Column('id', Integer, primary_key=True, autoincrement=True)
    role_id = Column('role_id', Integer, index=True)
    app_id = Column('app_id', Integer, index=True)


class Components(TimeBaseModel, Base):
    __tablename__ = 'codo_a_components'

    # 组件表
    id = Column('id', Integer, primary_key=True, autoincrement=True)
    name = Column('name', String(80), unique=True, index=True)
    app_code = Column('app_code', String(20), index=True)
    details = Column('details', String(250), default='')  # 描述、备注


class RolesComponents(Base):
    __tablename__ = 'codo_a_roles_components'

    # 角色与前端组件关联表
    id = Column('id', Integer, primary_key=True, autoincrement=True)
    role_id = Column('role_id', Integer, index=True)
    comp_id = Column('comp_id', Integer, index=True)


class UserToken(Base):
    __tablename__ = 'codo_a_user_token'

    # 用户长期token表
    token_id = Column('token_id', Integer, primary_key=True, autoincrement=True)
    user_id = Column('user_id', Integer, index=True)
    nickname = Column('nickname', String(80), index=True)
    token_md5 = Column('token_md5', String(35), index=True)
    token = Column('token', Text(), default='')
    status = Column('status', String(5), default='0', index=True)
    details = Column('details', String(250), default='')  # 描述、备注
    expire_time = Column(DateTime, nullable=False)  # 过期时间
    create_time = Column(DateTime, nullable=False, default=datetime.now)  # 记录的创建时间
