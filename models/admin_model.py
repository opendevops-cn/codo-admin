#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
author : shenshuo
date   : 2018年10月23日
desc   : 管理后台数据库
"""

from sqlalchemy import Column, String, Integer, DateTime, Text, JSON, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class TimeBaseModel(object):
    """模型基类，为模型补充创建时间与更新时间"""
    create_time = Column(DateTime, nullable=False, default=datetime.now)  # 记录的创建时间
    update_time = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)  # 记录的更新时间


class OperationRecord(TimeBaseModel, Base):
    __tablename__ = 'operation_record'

    ### 操作记录
    id = Column('id', Integer, primary_key=True, autoincrement=True)
    user_id = Column('user_id', String(128), index=True)
    username = Column('username', String(80), index=True)
    nickname = Column('nickname', String(80), index=True)
    client_ip = Column('client_ip', String(25))
    service_name = Column('service_name', String(35))
    scheme = Column('scheme', String(25))
    trace_id = Column('trace_id', String(80), index=True)
    latency = Column('latency', String(128))
    upstream = Column('upstream', String(255))

    method = Column('method', String(10))
    uri = Column('uri', String(255), index=True)
    data = Column('data', Text())
    start_time = Column('start_time', DateTime(), default=datetime.now)
    response_status = Column('response_status', String(15))


class Users(TimeBaseModel, Base):
    __tablename__ = 'mg_users'

    ### 用户表
    user_id = Column('user_id', Integer, primary_key=True, autoincrement=True)
    username = Column('username', String(50), index=True)
    password = Column('password', String(100))
    nickname = Column('nickname', String(100), index=True)
    email = Column('email', String(80), index=True)  ### 邮箱
    tel = Column('tel', String(11), index=True)  ### 手机号
    department = Column('department', String(600))  ### 部门
    google_key = Column('google_key', String(80))  ### 谷歌认证秘钥
    superuser = Column('superuser', String(5), default='10', index=True)  ### 超级用户  0代表超级用户
    avatar = Column('avatar', String(1000), default='')  ### 头像
    source = Column('source', String(15), default='注册')
    source_account_id = Column('source_account_id', String(250), default='', index=True)
    manager = Column('manager', String(180), default='')  ###上级领导
    dd_id = Column('dd_id', String(80), default='')  ###钉钉ID
    status = Column('status', String(5), default='0', index=True)  ### 0 10 20
    have_token = Column('have_token', String(5), default='no')
    feishu_userid = Column('feishu_userid', String(180), default='')  ###飞书ID
    ##
    last_ip = Column('last_ip', String(20), default='')
    last_login = Column('last_login', DateTime(), default=datetime.now, onupdate=datetime.now)

    __table_args__ = (UniqueConstraint('username', 'nickname', name="username_and_nickname"),
                      UniqueConstraint('username', 'email', name="username_and_email"),)


class Roles(TimeBaseModel, Base):
    __tablename__ = 'mg_roles'

    ### 角色表
    role_id = Column('role_id', Integer, primary_key=True, autoincrement=True)
    role_name = Column('role_name', String(30), unique=True, index=True)
    details = Column('details', String(250), default='')  ### 描述、备注
    status = Column('status', String(5), default='0', index=True)


class UserRoles(Base):
    __tablename__ = 'mg_user_roles'

    ### 用户角色关联表
    user_role_id = Column('user_role_id', Integer, primary_key=True, autoincrement=True)
    role_id = Column('role_id', Integer, index=True)
    user_id = Column('user_id', Integer, index=True)
    status = Column('status', String(5), default='0', index=True)


class Components(TimeBaseModel, Base):
    __tablename__ = 'mg_components'

    ### 组件表
    comp_id = Column('comp_id', Integer, primary_key=True, autoincrement=True)
    component_name = Column('component_name', String(80), unique=True, index=True)
    app_code = Column('app_code', String(20), index=True)
    details = Column('details', String(250), default='')  ### 描述、备注
    status = Column('status', String(5), default='0', index=True)


class RolesComponents(Base):
    __tablename__ = 'mg_roles_components'

    ### 角色与前端组件关联表
    role_comp_id = Column('role_comp_id', Integer, primary_key=True, autoincrement=True)
    role_id = Column('role_id', Integer, index=True)
    comp_id = Column('comp_id', Integer, index=True)
    status = Column('status', String(5), default='0', index=True)


class Menus(TimeBaseModel, Base):
    __tablename__ = 'mg_menus'

    ### 前端路由权限
    menu_id = Column('menu_id', Integer, primary_key=True, autoincrement=True)
    menu_name = Column('menu_name', String(80), unique=True, index=True)
    app_code = Column('app_code', String(20), index=True)
    details = Column('details', String(250), default='')  ### 描述、备注
    status = Column('status', String(5), default='0', index=True)


class RoleMenus(Base):
    __tablename__ = 'mg_role_menus'

    ### 角色与前端路由关联
    role_menu_id = Column('role_menu_id', Integer, primary_key=True, autoincrement=True)
    role_id = Column('role_id', Integer, index=True)
    menu_id = Column('menu_id', Integer, index=True)
    status = Column('status', String(5), default='0', index=True)


class Functions(TimeBaseModel, Base):
    __tablename__ = 'mg_functions'

    ### 权限表
    func_id = Column('func_id', Integer, primary_key=True, autoincrement=True)
    func_name = Column('func_name', String(50), index=True)
    app_code = Column('app_code', String(20), index=True)
    uri = Column('uri', String(250), index=True)
    method_type = Column('method_type', String(10), index=True)
    parameters = Column('parameters', Text(), default='')
    status = Column('status', String(5), default='0', index=True)
    __table_args__ = (UniqueConstraint('app_code', 'func_name', name="app_code_and_func_name"),)


class RoleFunctions(Base):
    __tablename__ = 'mg_role_functions'

    ### 角色权限关联表
    id = Column('id', Integer, primary_key=True, autoincrement=True)
    role_id = Column('role_id', Integer, index=True)
    func_id = Column('func_id', Integer, index=True)
    status = Column('status', String(5), default='0', index=True)


class Apps(TimeBaseModel, Base):
    __tablename__ = 'mg_apps'

    ### 应用列表
    app_id = Column('app_id', Integer, primary_key=True, autoincrement=True)
    app_name = Column('app_name', String(80), unique=True, index=True)
    app_code = Column('app_code', String(20), index=True)  ###多个项目可以公用一个code
    user_list = Column('user_list', JSON(), default=[])  # 用户列表
    is_up = Column('is_up', String(15), default='no', index=True)
    # title = Column('title', String(20), index=True)
    href = Column('href', String(255), default='')  ### 前端直接跳转的URL
    path = Column('path', String(255), default='')  ### 前端访问地址
    img = Column('img', String(255), default='')  ### 图片地址
    icon = Column('icon', String(255), default='')  ### 图标
    content = Column('content', String(150), default='')  ### 描述、备注
    status = Column('status', String(5), default='0', index=True)
    power = Column('power', String(5), default='yes', index=True)
    ###


class RoleApps(Base):
    __tablename__ = 'mg_role_apps'

    ### 角色权限关联表
    id = Column('id', Integer, primary_key=True, autoincrement=True)
    role_id = Column('role_id', Integer, index=True)
    app_id = Column('app_id', Integer, index=True)
    status = Column('status', String(5), default='0', index=True)


class UserToken(Base):
    __tablename__ = 'mg_user_token'

    ### 用户长期token表
    token_id = Column('token_id', Integer, primary_key=True, autoincrement=True)
    user_id = Column('user_id', Integer, index=True)
    nickname = Column('nickname', String(80), index=True)
    token_md5 = Column('token_md5', String(35), index=True)
    token = Column('token', Text(), default='')
    status = Column('status', String(5), default='0', index=True)
    details = Column('details', String(150), default='')  ### 描述、备注
    expire_time = Column(DateTime, nullable=False)  # 过期时间
    create_time = Column(DateTime, nullable=False, default=datetime.now)  # 记录的创建时间


class StorageMG(TimeBaseModel, Base):
    __tablename__ = 'mg_storage'

    # 用户上传数据记录
    id = Column('id', Integer, primary_key=True, autoincrement=True)
    storage_key = Column('storage_key', String(80))
    nickname = Column('nickname', String(80), default="匿名", index=True)
    action = Column('action', String(15), default="上传")
    storage_type = Column('storage_type', String(15), default='OSS')
    file_dir = Column('file_dir', String(80), default='', index=True)
    filename = Column('filename', String(150), default='', index=True)


class FavoritesModel(Base):
    __tablename__ = 'mg_favorites'

    # 用户收藏表
    id = Column('id', Integer, primary_key=True, autoincrement=True)
    nickname = Column('nickname', String(80), default="团团团", index=True)
    app_code = Column('app_code', String(20), default="overall", index=True)
    key = Column('key', String(35), default="", index=True)
    # value = Column('value', Text(), default="")
    value = Column('value', JSON(), default='{}')
    __table_args__ = (UniqueConstraint('nickname', 'app_code', 'key', name="app_code_and_key_nickname"),)
