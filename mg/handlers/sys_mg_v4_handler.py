#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2018/10/29
Desc    : 应用相关逻辑
"""

import json
import shortuuid
import base64
from abc import ABC
from sqlalchemy import exc
from tornado.web import RequestHandler
from tornado import gen
from tornado.concurrent import run_on_executor
from concurrent.futures import ThreadPoolExecutor
from libs.base_handler import BaseHandler
from websdk2.db_context import DBContext
from websdk2.base_handler import LivenessProbe
from websdk2.jwt_token import gen_md5
from websdk2.tools import check_password
from websdk2.ldap import LdapApi
from websdk2.model_utils import insert_or_update
from websdk2.consts import const
from models.authority import Users, Menus, Functions, Components, Roles
from services.audit_service import get_opt_log_list_v4
from services.sys_service import settings_add, get_sys_conf_dict, get_sys_open_conf_dict, init_email


class LogV4Handler(BaseHandler, ABC):
    def get(self, *args, **kwargs):
        res = get_opt_log_list_v4(**self.params)

        return self.write(res)


class UserRegisterHandler(RequestHandler, ABC):
    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        username = data.get('username', None)
        nickname = data.get('nickname', None)
        password = data.get('password', None)
        department = data.get('department', None)
        tel = data.get('tel', None)
        no = data.get('no', None)
        email = data.get('email', None)
        user_state = data.get('user_state', '0')
        if not username or not nickname or not department or not tel or not no or not email:
            return self.write(dict(code=-1, msg='参数不能为空'))

        with DBContext('r') as session:
            user_info1 = session.query(Users).filter(Users.username == username).first()
            user_info2 = session.query(Users).filter(Users.tel == tel).first()
            user_info3 = session.query(Users).filter(Users.email == email).first()
            user_info4 = session.query(Users).filter(Users.nickname == nickname).first()

        if user_info1:
            return self.write(dict(code=-2, msg='用户名已注册'))

        if user_info2:
            return self.write(dict(code=-3, msg='手机号已注册'))

        if user_info3:
            return self.write(dict(code=-4, msg='邮箱已注册'))

        if user_info4:
            return self.write(dict(code=-4, msg='昵称已注册'))

        if not password:
            the_password = shortuuid.uuid()
        else:
            if not check_password(password):
                return self.write(dict(code=-5, msg='密码复杂度必须为： 超过8位，包含数字，大小写字母 等'))
            the_password = password

        password = gen_md5(the_password)

        mfa = base64.b32encode(bytes(str(shortuuid.uuid() + shortuuid.uuid())[:-9], encoding="utf-8")).decode("utf-8")

        with DBContext('w', None, True) as session:
            session.add(Users(username=username, password=password, nickname=nickname, department=department, tel=tel,
                              email=email, google_key=mfa, superuser='10', status=user_state))

        obj = init_email()
        obj.send_mail(email, '用户注册成功', '密码为：{} \n MFA：{}'.format(the_password, mfa), subtype='plain')

        return self.write(dict(code=0, msg='恭喜你！ 注册成功，赶紧联系管理员给你添加权限吧！！！', mfa=mfa))


class AuthorityRegister(BaseHandler):
    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        self.app_code = data.get('app_code')
        func_list = data.get('func_list')
        menu_list = data.get('menu_list')
        component_list = data.get('component_list')
        role_list = data.get('role_list')

        if not self.app_code: return self.write(dict(code=-1, msg='服务编码不能为空'))

        if func_list and isinstance(func_list, list):
            try:
                self.register_func(func_list)
            except Exception as err:
                print(err)
                return self.write(dict(code=-2, msg='注册API权限失败'))

        if menu_list and isinstance(menu_list, list):
            try:
                self.register_menu(menu_list)
            except Exception as err:
                return self.write(dict(code=-3, msg='注册前端菜单失败'))

        if component_list and isinstance(component_list, list):
            try:
                self.register_component(component_list)
            except Exception as err:
                return self.write(dict(code=-4, msg='注册前端组件失败'))

        if role_list and isinstance(role_list, list):
            try:
                self.register_role(role_list)
            except Exception as err:
                return self.write(dict(code=-5, msg='注册角色信息失败'))

        return self.write(dict(code=0, msg='注册结束'))

    def register_menu(self, data):
        for d in data:
            menu_name = d.get('name')
            details = d.get('details', '')[0:250]
            if not menu_name: continue
            with DBContext('w', None, True) as session:
                try:
                    session.add(insert_or_update(Menus, f"menu_name='{menu_name}' and app_code='{self.app_code}'",
                                                 app_code=self.app_code, details=details,
                                                 menu_name=menu_name))
                except exc.IntegrityError as e:
                    print(e)
                except Exception as err:
                    print(err)

    def register_component(self, data):
        for d in data:
            status = d.get('status', '0')
            name = d.get('name')
            details = d.get('details', '')[0:250]
            if not name: continue
            with DBContext('w', None, True) as session:
                try:
                    session.add(insert_or_update(Components,
                                                 f"name='{name}' and app_code='{self.app_code}'",
                                                 app_code=self.app_code, details=details, name=name))
                except exc.IntegrityError as e:
                    print(e)
                except Exception as err:
                    print(err)

    def register_func(self, data):
        for d in data:
            status = d.get('status', '0')
            func_name = d.get('name')
            details = d.get('details', '')[0:250]
            method_type = d.get('method_type')
            uri = d.get('uri')
            parameters = d.get('parameters', '{}')
            if not func_name or not method_type or not uri: continue
            with DBContext('w', None, True) as session:
                update_dict = dict(app_code=self.app_code, status=status, details=details,
                                   func_name=func_name, method_type=method_type, uri=uri)
                if parameters != '{}': update_dict['parameters'] = parameters
                print(update_dict)
                try:
                    session.add(insert_or_update(Functions,
                                                 f"uri='{uri}' and method_type='{method_type}' and func_name='{func_name}' and app_code='{self.app_code}'",
                                                 **update_dict))
                except exc.IntegrityError as e:
                    print(e)
                except Exception as err:
                    print(err)

    def register_role(self, data):
        for d in data:
            role_name = d.get('name')
            details = d.get('details', '')[0:250]
            if not role_name: continue
            with DBContext('w', None, True) as session:
                try:
                    session.add(Roles(**dict(role_name=role_name, details=details)))
                except exc.IntegrityError as e:
                    print(e)
                except Exception as err:
                    print(err)


class AppSettingsHandler(BaseHandler, ABC):

    def get(self):
        # category
        res = get_sys_conf_dict(**self.params)
        return self.write(res)

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode('utf-8'))
        res = settings_add(data)
        return self.write(res)


class OpenConfHandler(BaseHandler, ABC):

    def get(self):
        # 通用数据
        res = get_sys_open_conf_dict(**self.params)
        return self.write(res)


class CheckSettingsHandler(BaseHandler, ABC):
    _thread_pool = ThreadPoolExecutor(5)

    @run_on_executor(executor='_thread_pool')
    def send_test_mail(self, test_mail, data):
        obj = init_email()
        obj.send_mail(test_mail, data.get(const.EMAIL_SUBJECT_PREFIX, '测试邮件'), '测试发送邮件成功',
                      subtype='plain')
        return True

    @run_on_executor(executor='_thread_pool')
    def send_test_ldap(self, data):
        obj = LdapApi(data.get(const.LDAP_SERVER_HOST), data.get(const.LDAP_ADMIN_DN),
                      data.get(const.LDAP_ADMIN_PASSWORD),
                      data.get(const.LDAP_USE_SSL))
        obj.ldap_server_test()
        return True

    @gen.coroutine
    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode('utf-8'))
        check_key = data.get('check_key')
        test_mail = data.get('EMAIL_TEST_USER')
        if check_key == 'EMAIL':
            yield self.send_test_mail(test_mail, data)
            return self.write(dict(code=0, msg='测试邮件已经发送'))
        elif check_key == 'LDAP':
            state = yield self.send_test_ldap(data)
            if state:
                return self.write(dict(code=0, msg='LDAP连接测试成功'))
            else:
                return self.write(dict(code=-1, msg='LDAP连接测试不成功，请仔细检查配置'))

        else:
            return self.write(dict(code=-1, msg='未知测试项目'))


sys_mg_v4_urls = [
    (r"/v4/app/opt_log/", LogV4Handler, {"handle_name": "PAAS管理-操作日志V4"}),
    (r"/v4/na/conf/", OpenConfHandler, {"handle_name": "PAAS管理-开放配置"}),
    (r'/v4/sysconfig/settings/', AppSettingsHandler, {"handle_name": "PAAS管理-系统设置", "method": ["ALL"]}),
    (r'/v4/sysconfig/check/', CheckSettingsHandler, {"handle_name": "PAAS管理-系统设置检查", "method": ["ALL"]}),
    (r'/v4/authority/register/', AuthorityRegister, {"handle_name": "PAAS管理-权限注册", "method": ["ALL"]}),
    (r"/are_you_ok/", LivenessProbe)
]

if __name__ == "__main__":
    pass
