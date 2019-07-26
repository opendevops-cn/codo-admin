#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
author : shenshuo
date   : 2018年10月23日
desc   : 管理后台数据库
"""


from sqlalchemy import Column, String, Integer, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import class_mapper
from datetime import datetime

Base = declarative_base()


def model_to_dict(model):
    model_dict = {}
    for key, column in class_mapper(model.__class__).c.items():
        model_dict[column.name] = getattr(model, key, None)
    return model_dict


class OperationRecord(Base):
    __tablename__ = 'operation_record'

    ### 操作记录
    id = Column('id', Integer, primary_key=True, autoincrement=True)
    username = Column('username', String(50))
    nickname = Column('nickname', String(50))
    login_ip = Column('login_ip', String(20))
    method = Column('method', String(10))
    uri = Column('uri', String(150))
    data = Column('data', Text())
    ctime = Column('ctime', DateTime(), default=datetime.now, onupdate=datetime.now)



class Users(Base):
    __tablename__ = 'mg_users'

    ### 用户表
    user_id = Column('user_id', Integer, primary_key=True, autoincrement=True)
    username = Column('username', String(50), unique=True)
    password = Column('password', String(100))
    nickname = Column('nickname', String(100))
    email = Column('email', String(80), unique=True)  ### 邮箱
    tel = Column('tel', String(11))  ### 手机号
    wechat = Column('wechat', String(50))  ### 微信号
    no = Column('no', String(50))  ### 工号
    department = Column('department', String(50))  ### 部门
    google_key = Column('google_key', String(80))  ### 谷歌认证秘钥
    superuser = Column('superuser', String(5), default='10')  ### 超级用户  0代表超级用户
    status = Column('status', String(5), default='0')
    last_ip = Column('last_ip', String(20), default='')
    last_login = Column('last_login', DateTime(), default=datetime.now, onupdate=datetime.now)
    ctime = Column('ctime', DateTime(), default=datetime.now)


class Roles(Base):
    __tablename__ = 'mg_roles'

    ### 角色表
    role_id = Column('role_id', Integer, primary_key=True, autoincrement=True)
    role_name = Column('role_name', String(30))
    status = Column('status', String(5), default='0')
    ctime = Column('ctime', DateTime(), default=datetime.now, onupdate=datetime.now)


class UserRoles(Base):
    __tablename__ = 'mg_user_roles'

    ### 用户角色关联表
    user_role_id = Column('user_role_id', Integer, primary_key=True, autoincrement=True)
    role_id = Column('role_id', String(11))
    user_id = Column('user_id', String(11))
    status = Column('status', String(5), default='0')
    utime = Column('utime', DateTime(), default=datetime.now, onupdate=datetime.now)
    ctime = Column('ctime', DateTime(), default=datetime.now)


class Components(Base):
    __tablename__ = 'mg_components'

    ### 组件表
    comp_id = Column('comp_id', Integer, primary_key=True, autoincrement=True)
    component_name = Column('component_name', String(60))
    status = Column('status', String(5), default='0')


class RolesComponents(Base):
    __tablename__ = 'mg_roles_components'

    ### 角色与前端组件关联表
    role_comp_id = Column('role_comp_id', Integer, primary_key=True, autoincrement=True)
    role_id = Column('role_id', String(11))
    comp_id = Column('comp_id', String(11))
    status = Column('status', String(5), default='0')


class Menus(Base):
    __tablename__ = 'mg_menus'

    ### 前端路由权限
    menu_id = Column('menu_id', Integer, primary_key=True, autoincrement=True)
    menu_name = Column('menu_name', String(60))
    status = Column('status', String(5), default='0')

class RoleMenus(Base):
    __tablename__ = 'mg_role_menus'

    ### 角色与前端路由关联
    role_menu_id = Column('role_menu_id', Integer, primary_key=True, autoincrement=True)
    role_id = Column('role_id', String(11))
    menu_id = Column('menu_id', String(11))
    status = Column('status', String(5), default='0')

class Functions(Base):
    __tablename__ = 'mg_functions'

    ### 权限表
    func_id = Column('func_id', Integer, primary_key=True, autoincrement=True)
    func_name = Column('func_name', String(60))
    uri = Column('uri', String(300))
    method_type = Column('method_type', String(10))
    status = Column('status', String(5), default='0')
    utime = Column('utime', DateTime(), default=datetime.now, onupdate=datetime.now)
    ctime = Column('ctime', DateTime(), default=datetime.now)


class RoleFunctions(Base):
    __tablename__ = 'mg_role_functions'

    ### 角色权限关联表
    id = Column('id', Integer, primary_key=True, autoincrement=True)
    role_id = Column('role_id', String(11))
    func_id = Column('func_id', String(11))
    status = Column('status', String(5), default='0')
