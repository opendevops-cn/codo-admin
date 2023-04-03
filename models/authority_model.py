#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
author : shenshuo
date   : 2018年10月23日
desc   : 管理后台数据库
"""

from sqlalchemy import Column, String, Integer, DateTime, Text, JSON, UniqueConstraint, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class TimeBaseModel(object):
    """模型基类，为模型补充创建时间与更新时间"""
    create_time = Column(DateTime, nullable=False, default=datetime.now)  # 记录的创建时间
    update_time = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)  # 记录的更新时间


class Users(TimeBaseModel, Base):
    __tablename__ = 'auth_users'

    ### 用户表
    user_id = Column('user_id', Integer, primary_key=True, autoincrement=True)
    username = Column('username', String(50), index=True)
    password = Column('password', String(100))
    nickname = Column('nickname', String(100), index=True)
    fs_id = Column('fs_id', String(100), index=True)  ### 飞书id
    fs_open_id = Column('fs_open_id', String(100), index=True)  ### 飞书open id

    email = Column('email', String(80), index=True)  ### 邮箱
    tel = Column('tel', String(50), index=True, default='')  ### 手机号

    department = Column('department', String(600))  ### 部门
    dep_id = Column('dep_id', String(200), index=True)  ### 部门id

    google_key = Column('google_key', String(80))  ### 谷歌认证秘钥
    superuser = Column('superuser', String(5), default='10', index=True)  ### 超级用户  0代表超级用户
    avatar = Column('avatar', String(255), default='')  ### 头像
    source = Column('source', String(15), default='注册', index=True)
    source_account_id = Column('source_account_id', String(250), default='', index=True, unique=True)  # 用户唯一表示id
    manager = Column('manager', String(180), default='')  ###上级领导
    dd_id = Column('dd_id', String(80), default='', index=True)  ###钉钉ID
    status = Column('status', String(5), default='0', index=True)  # 0激活，10非激活
    have_token = Column('have_token', String(5), default='no', index=True)
    last_ip = Column('last_ip', String(20), default='')
    last_login = Column('last_login', DateTime(), default=datetime.now, onupdate=datetime.now)

    # __table_args__ = (UniqueConstraint('source_account_id', 'source', 'username', name="source_and_id_and_user"),)

## 资源
class Resources(TimeBaseModel, Base):
    __tablename__ = 'auth_resource'
    ### app, business, menus, component, function
    resource_type = Column('resource_type', String(50), primary_key=True, index=True)
    desc = Column('desc', String(250), default='')  ### 描述、备注
    status = Column('status', String(5), default='0', index=True)


class Apps(TimeBaseModel, Base):
    __tablename__ = 'auth_apps'

    ### 应用列表
    app_id = Column('app_id', Integer, primary_key=True, autoincrement=True)
    app_name = Column('app_name', String(80), unique=True, index=True)
    app_code = Column('app_code', String(20), index=True)  ###多个项目可以公用一个code
    user_list = Column('user_list', JSON(), default=[])  # 管理员列表
    is_up = Column('is_up', String(15), default='no', index=True)
    href = Column('href', String(255), default='')  ### 前端直接跳转的URL
    path = Column('path', String(255), default='')  ### 前端访问地址
    img = Column('img', String(255), default='')  ### 图片地址
    icon = Column('icon', String(255), default='')  ### 图标
    content = Column('content', String(150), default='')  ### 描述、备注
    status = Column('status', String(5), default='0', index=True)
    power = Column('power', String(5), default='yes', index=True)
    swagger_url = Column('swagger_url', String(150), default='')  ### swagger接口地址
    api_prefix = Column('api_prefix', String(150), default='')  ### 接口前缀


class Menus(TimeBaseModel, Base):
    __tablename__ = 'auth_menus'

    ### 前端路由权限
    menu_id = Column('menu_id', Integer, primary_key=True, autoincrement=True)
    menu_name = Column('menu_name', String(80), unique=True, index=True)
    app_code = Column('app_code', String(20), index=True)
    parent_id = Column('parent_id', Integer, index=True)
    details = Column('details', String(250), default='')  ### 描述、备注
    status = Column('status', String(5), default='0', index=True)


class Components(TimeBaseModel, Base):
    __tablename__ = 'auth_components'

    ### 组件表
    component_id = Column('component_id', Integer, primary_key=True, autoincrement=True)
    component_name = Column('component_name', String(80), unique=True, index=True)
    app_code = Column('app_code', String(20), index=True)
    menu_id = Column('menu_id', Integer, index=True)
    details = Column('details', String(250), default='')  ### 描述、备注
    status = Column('status', String(5), default='0', index=True)


class Functions(TimeBaseModel, Base):
    __tablename__ = 'auth_functions'

    ### 接口列表
    function_id = Column('function_id', Integer, primary_key=True, autoincrement=True)
    func_name = Column('func_name', String(50), default='', index=True)
    app_code = Column('app_code', String(20), index=True)
    uri = Column('uri', String(250), index=True)  # 模块，路径第一模块
    path = Column('path', String(250), default='')  # 完整路径
    method_type = Column('method_type', String(10), default='', index=True)
    parameters = Column('parameters', Text(), default='')
    parent_id = Column('parent_id', Integer, index=True)
    status = Column('status', String(5), default='0', index=True)
    __table_args__ = (UniqueConstraint('app_code', 'uri', 'path', 'method_type', name="app_code_and_func_name"),)


class RoleBusiness(Base):
    __tablename__ = 'auth_role_business'

    ### 角色业务关联表
    role_business_id = Column('role_business_id', Integer, primary_key=True, autoincrement=True)
    role_id = Column('role_id', Integer, index=True)
    business_id = Column('business_id', Integer, index=True)
    source = Column('source', String(20), default='custom', index=True)  # custom手动，subscribe订阅
    status = Column('status', String(5), default='0', index=True)


class RoleApp(Base):
    __tablename__ = 'auth_role_app'

    ### 角色系统关联表
    role_app_id = Column('role_app_id', Integer, primary_key=True, autoincrement=True)
    role_id = Column('role_id', Integer, index=True)
    app_id = Column('app_id', Integer, index=True)
    source = Column('source', String(20), default='custom', index=True)  # custom手动，subscribe订阅
    status = Column('status', String(5), default='0', index=True)


class RoleMenu(Base):
    __tablename__ = 'auth_role_menu'

    ### 角色菜单关联表
    role_menu_id = Column('role_menu_id', Integer, primary_key=True, autoincrement=True)
    role_id = Column('role_id', Integer, index=True)
    menu_id = Column('menu_id', Integer, index=True)
    source = Column('source', String(20), default='custom', index=True)  # custom手动，subscribe订阅
    status = Column('status', String(5), default='0', index=True)


class RoleComponent(Base):
    __tablename__ = 'auth_role_component'

    ### 角色组件关联表
    role_component_id = Column('role_component_id', Integer, primary_key=True, autoincrement=True)
    role_id = Column('role_id', Integer, index=True)
    component_id = Column('component_id', Integer, index=True)
    source = Column('source', String(20), default='custom', index=True)  # custom手动，subscribe订阅
    status = Column('status', String(5), default='0', index=True)


class RoleFunction(Base):
    __tablename__ = 'auth_role_function'

    ### 角色api关联表
    role_function_id = Column('role_function_id', Integer, primary_key=True, autoincrement=True)
    role_id = Column('role_id', Integer, index=True)
    function_id = Column('function_id', Integer, index=True)
    source = Column('source', String(20), default='custom', index=True)  # custom手动，subscribe订阅
    status = Column('status', String(5), default='0', index=True)


class SubscribeRole(TimeBaseModel, Base):
    __tablename__ = 'auth_subscribe_role'

    ### 角色订阅
    subscribe_role_id = Column('subscribe_role_id', Integer, primary_key=True, autoincrement=True)
    role_id = Column('role_id', Integer, index=True)
    subscribe_type = Column('subscribe_type', String(50), index=True, default='')  # 接口function, 前端frontend
    app_list = Column('app_list', JSON(), default=[])
    app_all = Column('app_all', Boolean, default=False)
    match_key = Column('match_key', String(50), index=True, default='')
    match_type = Column('match_type', String(50), index=True,
                        default='')  # 前缀prefix, 后缀suffix，包含contain，正则reg，排除exclude
    match_method = Column('match_method', String(50), index=True, default='')  # 接口权限时，方法GET/ALL
    desc = Column('desc', String(100), default='')
    status = Column('status', String(5), default='0', index=True)





class Roles(TimeBaseModel, Base):
    __tablename__ = 'auth_roles'

    ### 角色表
    role_id = Column('role_id', Integer, primary_key=True, autoincrement=True)
    role_name = Column('role_name', String(30), unique=True, index=True)
    desc = Column('desc', String(250), default='')  ### 描述
    status = Column('status', String(5), default='0', index=True)
    count_limit = Column('count_limit', Integer, default=-1)
    prerequisites = Column('prerequisites', JSON(), default=[])  ### 先决条件
    role_type = Column('role_type', String(250), default='normal')  ### 角色类型， normal, base, default
    is_confg = Column('is_confg', Boolean, default=False)  # 是否配置权限


class RolesMutual(TimeBaseModel, Base):
    __tablename__ = 'auth_role_mutual'

    ### 角色互斥关系
    role_mutual_id = Column('role_mutual_id', Integer, primary_key=True, autoincrement=True)
    role_left_id = Column('role_left_id', Integer, index=True)
    role_right_id = Column('role_right_id', Integer, index=True)
    desc = Column('desc', String(250), default='')  ### 描述、备注
    status = Column('status', String(5), default='0', index=True)


class RolesInherit(TimeBaseModel, Base):
    __tablename__ = 'auth_role_inheirt'

    ### 角色继承关系
    role_inherit_id = Column('role_inherit_id', Integer, primary_key=True, autoincrement=True)
    role_id = Column('role_id', Integer, index=True)
    inherit_from_role_id = Column('inherit_from_role_id', Integer, index=True)  # 继承该角色的所有权限功能
    desc = Column('desc', String(250), default='')  ### 描述、备注
    status = Column('status', String(5), default='0', index=True)


class Groups(TimeBaseModel, Base):
    __tablename__ = 'auth_groups'

    ### 用户组
    group_id = Column('group_id', Integer, primary_key=True, autoincrement=True)
    group_name = Column('group_name', String(100), index=True)
    source = Column('source', String(50), default='自定义', index=True)  ### 类型， 自定义(默认)/组织架构同步(不可改)/自动(自动关联组)
    desc = Column('desc', String(250), default='')  ### 描述
    status = Column('status', String(5), default='0', index=True)
    dep_id = Column('dep_id', String(200), default='')
    end_time = Column(DateTime, nullable=True)  # 用户组的无效时间


class GroupsRelate(TimeBaseModel, Base):
    __tablename__ = 'auth_group_relate'

    ### 用户组组织架构关联
    group_relate_id = Column('group_relate_id', Integer, primary_key=True, autoincrement=True)
    group_id = Column('group_id', Integer, index=True)  # 自动的用户组关联到组织架构， 一对多关系
    relate_id = Column('relate_id', Integer, index=True)
    status = Column('status', String(5), default='0', index=True)


class UserGroups(TimeBaseModel, Base):
    __tablename__ = 'auth_user_groups'

    ### 用户与用户组关联表
    user_group_id = Column('user_group_id', Integer, primary_key=True, autoincrement=True)
    group_id = Column('group_id', Integer, index=True)
    user_id = Column('user_id', Integer, index=True)
    status = Column('status', String(5), default='0', index=True)


class UserRoles(Base):
    __tablename__ = 'auth_user_roles'

    ### 用户角色关联表
    user_role_id = Column('user_role_id', Integer, primary_key=True, autoincrement=True)
    role_id = Column('role_id', Integer, index=True)
    user_id = Column('user_id', Integer, index=True)
    status = Column('status', String(5), default='0', index=True)


class GroupRoles(Base):
    __tablename__ = 'auth_group_roles'

    ### 用户组与角色关联表
    group_role_id = Column('group_role_id', Integer, primary_key=True, autoincrement=True)
    group_id = Column('group_id', Integer, index=True)
    role_id = Column('role_id', Integer, index=True)
    status = Column('status', String(5), default='0', index=True)


###
class UserToken(Base):
    __tablename__ = 'auth_user_token'

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
    __tablename__ = 'auth_storage'

    ### 用户长期token表
    id = Column('id', Integer, primary_key=True, autoincrement=True)
    storage_key = Column('storage_key', String(80))
    nickname = Column('nickname', String(80), default="匿名", index=True)
    action = Column('action', String(15), default="上传")
    storage_type = Column('storage_type', String(15), default='OSS')
    file_dir = Column('file_dir', String(80), default='', index=True)
    filename = Column('filename', String(150), default='', index=True)


class FavoritesModel(Base):
    __tablename__ = 'auth_favorites'

    ### 用户收藏表
    id = Column('id', Integer, primary_key=True, autoincrement=True)
    nickname = Column('nickname', String(80), default="团团团", index=True)
    app_code = Column('app_code', String(20), default="overall", index=True)
    key = Column('key', String(35), default="", index=True)
    # value = Column('value', Text(), default="")
    value = Column('value', JSON(), default='{}')
    __table_args__ = (UniqueConstraint('nickname', 'app_code', 'key', name="app_code_and_key_nickname"),)


class OperationLogs(TimeBaseModel, Base):
    __tablename__ = 'auth_operation_logs'

    ### 用户操作记录
    id = Column('id', Integer, primary_key=True, autoincrement=True)
    username = Column('username', String(50), index=True)
    operation = Column('operation', String(100), index=True)
    result = Column('result', Boolean, default=True)
    msg = Column('msg', String(100), default='')
    data = Column('data', JSON(), default='{}')
    response = Column('response', JSON(), default='{}')


class SyncLogs(TimeBaseModel, Base):
    __tablename__ = 'auth_sync_logs'

    ### 同步记录
    id = Column('id', Integer, primary_key=True, autoincrement=True)
    username = Column('username', String(50), index=True)
    operation = Column('operation', String(100), index=True)
    result = Column('result', Boolean, default=True)
    msg = Column('msg', String(100), default='')
    data = Column('data', JSON(), default='{}')
    response = Column('response', JSON(), default='{}')


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
