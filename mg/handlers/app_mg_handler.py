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
from tornado.web import RequestHandler
from websdk2.jwt_token import gen_md5
from websdk2.tools import check_password
from libs.base_handler import BaseHandler
from models.admin_model import Users
from websdk2.db_context import DBContext
from websdk2.base_handler import LivenessProbe
from models.admin_schemas import get_opt_log_list
###
from sqlalchemy import exc
from websdk2.model_utils import GetInsertOrUpdateObj
from models.admin_model import Menus, Functions, Components, Roles
#
from websdk2.utils import SendMail
from .configs_init import configs_init
from websdk2.consts import const
from websdk2.tools import convert
from websdk2.cache_context import cache_conn
from websdk2.jwt_token import AuthToken


class LogHandler(BaseHandler):
    def get(self, *args, **kwargs):
        start_date = self.get_argument('start_date', default=None, strip=True)
        end_date = self.get_argument('end_date', default=None, strip=True)
        key = self.get_argument('key', default=None, strip=True)
        value = self.get_argument('value', default=None, strip=True)
        filter_map = self.get_argument('filter_map', default=None, strip=True)
        page_size = self.get_argument('page', default='1', strip=True)
        limit = self.get_argument('limit', default='10', strip=True)

        filter_map = json.loads(filter_map) if filter_map else {key: value}
        if not key or not value: filter_map = {}

        count, queryset = get_opt_log_list(int(page_size), int(limit), start_date, end_date, filter_map)

        return self.write(dict(code=0, result=True, msg="获取日志成功", count=count, data=queryset))


class UserRegisterHandler(RequestHandler):
    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        username = data.get('username', None)
        nickname = data.get('nickname', None)
        password = data.get('password', None)
        department = data.get('department', None)
        tel = data.get('tel', None)
        # wechat = data.get('wechat', None)
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

        redis_conn = cache_conn()
        configs_init('all')
        config_info = redis_conn.hgetall(const.APP_SETTINGS)
        config_info = convert(config_info)
        obj = SendMail(mail_host=config_info.get(const.EMAIL_HOST), mail_port=config_info.get(const.EMAIL_PORT),
                       mail_user=config_info.get(const.EMAIL_HOST_USER),
                       mail_password=config_info.get(const.EMAIL_HOST_PASSWORD),
                       mail_ssl=True if config_info.get(const.EMAIL_USE_SSL) == '1' else False,
                       mail_tls=True if config_info.get(const.EMAIL_USE_TLS) == '1' else False)

        with DBContext('w', None, True) as session:
            session.add(Users(username=username, password=password, nickname=nickname, department=department, tel=tel,
                           email=email, google_key=mfa, superuser='10', status=user_state))

        obj.send_mail(email, '用户注册成功', '密码为：{} \n MFA：{}'.format(the_password, mfa), subtype='plain')
        return self.write(dict(code=0, msg='恭喜你！ 注册成功，赶紧联系管理员给你添加权限吧！！！', mfa=mfa))


class PasswordHandler(BaseHandler):

    def patch(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        old_password = data.get('old_password', None)
        new_password1 = data.get('new_password1', None)
        new_password2 = data.get('new_password2', None)
        username = self.get_current_user()
        if not check_password(new_password1):
            return self.write(dict(code=-5, msg='密码复杂度必须为： 超过8位，包含数字，大小写字母 等'))

        if not old_password or not new_password1 or not new_password2 or not username:
            return self.write(dict(code=-1, msg='不能有空值'))

        if new_password1 != new_password2:
            return self.write(dict(code=-2, msg='新密码输入不一致'))

        with DBContext('r') as session:
            user_info = session.query(Users).filter(Users.username == username).first()

        if user_info.password != gen_md5(old_password):
            return self.write(dict(code=-3, msg='密码错误'))

        with DBContext('w', None, True) as session:
            session.query(Users).filter(Users.username == username).update({Users.password: gen_md5(new_password1)})

        return self.write(dict(code=0, msg='修改成功'))


class ResetMFAHandler(BaseHandler):
    def put(self, *args, **kwargs):
        if not self.is_superuser:  return self.write(dict(code=-1, msg='不是超级管理员，没有权限'))

        data = json.loads(self.request.body.decode("utf-8"))
        user_list = data.get('user_list', None)

        if len(user_list) < 1: return self.write(dict(code=-1, msg='用户不能为空'))

        redis_conn = cache_conn()
        configs_init('all')
        config_info = redis_conn.hgetall(const.APP_SETTINGS)
        config_info = convert(config_info)
        obj = SendMail(mail_host=config_info.get(const.EMAIL_HOST), mail_port=config_info.get(const.EMAIL_PORT),
                       mail_user=config_info.get(const.EMAIL_HOST_USER),
                       mail_password=config_info.get(const.EMAIL_HOST_PASSWORD),
                       mail_ssl=True if config_info.get(const.EMAIL_USE_SSL) == '1' else False,
                       mail_tls=True if config_info.get(const.EMAIL_USE_TLS) == '1' else False)

        with DBContext('w', None, True) as session:
            for user_id in user_list:
                mfa = base64.b32encode(bytes(str(shortuuid.uuid() + shortuuid.uuid())[:-9], encoding="utf-8")).decode(
                    "utf-8")
                session.query(Users).filter(Users.user_id == user_id).update({Users.last_ip: '', Users.google_key: mfa})
                mail_to = session.query(Users.email).filter(Users.user_id == user_id).first()

                obj.send_mail(mail_to[0], '重置MFA', mfa, subtype='plain')

        return self.write(dict(code=0, msg='重置MFA成功，新的MFA已经发送到邮箱'))


class ResetPasswordHandler(BaseHandler):
    def put(self, *args, **kwargs):
        if not self.is_superuser:    return self.write(dict(code=-1, msg='不是超级管理员，没有权限'))

        data = json.loads(self.request.body.decode("utf-8"))
        user_list = data.get('user_list')

        if len(user_list) < 1:  return self.write(dict(code=-2, msg='用户不能为空'))

        redis_conn = cache_conn()
        configs_init('all')
        config_info = redis_conn.hgetall(const.APP_SETTINGS)
        config_info = convert(config_info)
        obj = SendMail(mail_host=config_info.get(const.EMAIL_HOST), mail_port=config_info.get(const.EMAIL_PORT),
                       mail_user=config_info.get(const.EMAIL_HOST_USER),
                       mail_password=config_info.get(const.EMAIL_HOST_PASSWORD),
                       mail_ssl=True if config_info.get(const.EMAIL_USE_SSL) == '1' else False,
                       mail_tls=True if config_info.get(const.EMAIL_USE_TLS) == '1' else False)

        with DBContext('w', None, True) as session:
            for user_id in user_list:
                md5_password = shortuuid.uuid()
                new_password = gen_md5(md5_password)
                session.query(Users).filter(Users.user_id == user_id).update({Users.password: new_password})
                mail_to = session.query(Users.email).filter(Users.user_id == user_id).first()

                obj.send_mail(mail_to[0], '修改密码', md5_password, subtype='plain')

        return self.write(dict(code=0, msg='重置密码成功，新密码已经发送到邮箱'))


class TokenHandler(BaseHandler):
    ### 获取长期令牌
    def put(self, *args, **kwargs):
        if not self.is_superuser: return self.write(dict(code=-1, msg='不是超级管理员，没有权限'))

        data = json.loads(self.request.body.decode("utf-8"))
        user_list = data.get('user_list', None)

        if len(user_list) != 1:  return self.write(dict(code=-2, msg='一次只能选择一个用户，且不能为空'))

        user_id = user_list[0]
        with DBContext('r') as session:
            user_info = session.query(Users).filter(Users.user_id == user_id).first()

        ### 生成token
        is_superuser = True if user_info.superuser == '0' else False

        token_info = dict(user_id=user_id, username=user_info.username, nickname=user_info.nickname,
                          is_superuser=is_superuser, exp_days=1825)
        auth_token = AuthToken()
        auth_key = auth_token.encode_auth_token_v2(**token_info)
        if isinstance(auth_key, bytes): auth_key = auth_key.decode()

        redis_conn = cache_conn()
        configs_init('all')
        config_info = redis_conn.hgetall(const.APP_SETTINGS)
        config_info = convert(config_info)
        obj = SendMail(mail_host=config_info.get(const.EMAIL_HOST), mail_port=config_info.get(const.EMAIL_PORT),
                       mail_user=config_info.get(const.EMAIL_HOST_USER),
                       mail_password=config_info.get(const.EMAIL_HOST_PASSWORD),
                       mail_ssl=True if config_info.get(const.EMAIL_USE_SSL) == '1' else False,
                       mail_tls=True if config_info.get(const.EMAIL_USE_TLS) == '1' else False)

        with DBContext('w', None, True) as session:
            mail_to = session.query(Users.email).filter(Users.user_id == self.get_current_id()).first()

        if mail_to[0] == user_info.email:
            obj.send_mail(mail_to[0], '令牌，有效期五年', auth_key, subtype='plain')
        else:
            obj.send_mail(mail_to[0], '令牌，有效期五年', auth_key, subtype='plain')
            obj.send_mail(user_info.email, '令牌，有效期五年', auth_key, subtype='plain')
        return self.write(dict(code=0, msg='Token已经发送到邮箱', data=auth_key))


class AuthorityRegister(BaseHandler):
    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        self.app_code = data.get('app_code')
        func_list = data.get('func_list')
        menu_list = data.get('menu_list')
        component_list = data.get('component_list')
        role_list = data.get('role_list')
        print(data)
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
            status = d.get('status', '0')
            menu_name = d.get('name')
            details = d.get('details', '')[0:250]
            if not menu_name: continue
            with DBContext('w', None, True) as session:
                try:
                    session.add(GetInsertOrUpdateObj(Menus, f"menu_name='{menu_name}' and app_code='{self.app_code}'",
                                                     app_code=self.app_code, status=status, details=details,
                                                     menu_name=menu_name))
                except exc.IntegrityError as e:
                    print(e)
                except Exception as err:
                    print(err)

    def register_component(self, data):
        for d in data:
            status = d.get('status', '0')
            component_name = d.get('name')
            details = d.get('details', '')[0:250]
            if not component_name: continue
            with DBContext('w', None, True) as session:
                try:
                    session.add(GetInsertOrUpdateObj(Components,
                                                     f"component_name='{component_name}' and app_code='{self.app_code}'",
                                                     app_code=self.app_code, status=status, details=details,
                                                     component_name=component_name))
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
                    session.add(GetInsertOrUpdateObj(Functions,
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


app_mg_urls = [
    (r"/v3/app/opt_log/", LogHandler, {"handle_name": "PAAS-操作日志"}),
    (r"/v3/accounts/register/", UserRegisterHandler),
    (r"/v2/accounts/password/", PasswordHandler, {"handle_name": "PAAS-修改密码"}),
    (r"/v3/accounts/reset_mfa/", ResetMFAHandler, {"handle_name": "PAAS-重置二次认证"}),
    (r"/v3/accounts/reset_pw/", ResetPasswordHandler, {"handle_name": "PAAS-重置密码"}),
    (r"/v3/accounts/authority/register/", AuthorityRegister, {"handle_name": "权限注册接口"}),
    (r"/are_you_ok/", LivenessProbe, {"handle_name": "MG-存活接口"})
]

if __name__ == "__main__":
    pass
