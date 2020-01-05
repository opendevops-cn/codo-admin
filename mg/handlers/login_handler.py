#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
author : shenshuo
date   : 2017年11月21日
role   : 用户登录
"""

import json
from libs.base_handler import BaseHandler
from tornado.web import RequestHandler, HTTPError
from websdk.jwt_token import AuthToken, gen_md5
from websdk.tools import is_mail
from libs.my_verify import MyVerify
from websdk.utils import mail_login
import pyotp
from websdk.db_context import DBContext
from models.admin import Users, Components, RolesComponents, Menus, RoleMenus, UserRoles
from .configs_init import configs_init
from websdk.consts import const
from websdk.cache_context import cache_conn

from websdk.tools import convert
from ast import literal_eval
### LDAP
from websdk.ldap import LdapApi


class LoginHandler(RequestHandler):

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        username = data.get('username', None)
        password = data.get('password', None)
        dynamic = data.get('dynamic', None)

        if not username or not password: return self.write(dict(code=-1, msg='账号密码不能为空'))

        redis_conn = cache_conn()
        configs_init('all')
        if is_mail(username):
            login_mail = redis_conn.hget(const.APP_SETTINGS, const.EMAILLOGIN_DOMAIN)
            if login_mail:
                if is_mail(username, login_mail.decode('utf-8')):
                    email = username
                    username = email.split("@")[0]
                    email_server = redis_conn.hget(const.APP_SETTINGS, const.EMAILLOGIN_SERVER).decode('utf-8')
                    if not email_server:
                        return self.write(dict(code=-9, msg='请配置邮箱服务的SMTP服务地址'))

                    if not mail_login(email, password, email_server):
                        return self.write(dict(code=-2, msg='邮箱登陆认证失败'))

                    with DBContext('r') as session:
                        user_info = session.query(Users).filter(Users.email == email, Users.username == username,
                                                                Users.status != '10').first()
                    if not user_info:
                        return self.write(dict(code=-3, msg='邮箱认证通过，请根据邮箱完善用户信息', username=username, email=email))

        else:
            with DBContext('r') as session:
                user_info = session.query(Users).filter(Users.username == username, Users.password == gen_md5(password),
                                                        Users.status != '10').first()

            if not user_info:
                # redis_conn = cache_conn()
                # configs_init('all')
                ldap_login = redis_conn.hget(const.APP_SETTINGS, const.LDAP_ENABLE)
                ldap_login = convert(ldap_login)
                if ldap_login != '1':
                    return self.write(dict(code=-4, msg='账号密码错误'))

                ### 如果开启了LDAP认证 则进行LDAP认证
                else:
                    ####
                    config_info = redis_conn.hgetall(const.APP_SETTINGS)
                    config_info = convert(config_info)
                    ldap_ssl = True if config_info.get(const.LDAP_USE_SSL) == '1' else False

                    obj = LdapApi(config_info.get(const.LDAP_SERVER_HOST), config_info.get(const.LDAP_ADMIN_DN),
                                  config_info.get(const.LDAP_ADMIN_PASSWORD),
                                  int(config_info.get(const.LDAP_SERVER_PORT, 389)),
                                  ldap_ssl)

                    ldap_pass_info = obj.ldap_auth(username, password, config_info.get(const.LDAP_SEARCH_BASE),
                                                   config_info.get(const.LDAP_SEARCH_FILTER))

                    if ldap_pass_info[0]:
                        with DBContext('r') as session:
                            if not ldap_pass_info[2]:
                                return self.write(dict(code=-11, msg='LDAP认证成功，但是没有找到用户邮箱，请完善！'))
                            else:
                                user_info = session.query(Users).filter(Users.email == ldap_pass_info[2],
                                                                        Users.username == username,
                                                                        Users.status != '10').first()
                            if not user_info:
                                return self.write(dict(code=-3, msg='LDAP认证通过，完善用户信息', username=ldap_pass_info[1],
                                                       email=ldap_pass_info[2]))
                    else:
                        return self.write(dict(code=-4, msg='账号密码错误'))

        if 'user_info' not in dir():
            return self.write(dict(code=-4, msg='账号异常'))

        if user_info.status != '0':
            return self.write(dict(code=-4, msg='账号被禁用'))

        is_superuser = True if user_info.superuser == '0' else False

        ### 如果被标记为必须动态验证切没有输入动态密钥，则跳转到二维码添加密钥的地方
        ### 默认为 True， False 则全局禁用MFA
        mfa_global = False if convert(redis_conn.hget(const.APP_SETTINGS, const.MFA_GLOBAL)) == '1' else True
        if mfa_global and user_info.google_key:
            if not dynamic:
                ### 第一次不带MFA的认证
                return self.write(dict(code=1, msg='跳转二次认证'))
            else:
                ### 二次认证
                t_otp = pyotp.TOTP(user_info.google_key)
                if t_otp.now() != str(dynamic):
                    return self.write(dict(code=-5, msg='MFA错误'))

        user_id = str(user_info.user_id)
        ### 生成token 并写入cookie
        token_exp_hours = redis_conn.hget(const.APP_SETTINGS, const.TOKEN_EXP_TIME)
        if token_exp_hours and convert(token_exp_hours):
            token_info = dict(user_id=user_id, username=user_info.username, nickname=user_info.nickname,
                              email=user_info.email, is_superuser=is_superuser, exp_hours=token_exp_hours)
        else:
            token_info = dict(user_id=user_id, username=user_info.username, nickname=user_info.nickname,
                              email=user_info.email, is_superuser=is_superuser)
        auth_token = AuthToken()
        auth_key = auth_token.encode_auth_token_v2(**token_info)
        login_ip_list = self.request.headers.get("X-Forwarded-For")
        if login_ip_list:
            login_ip = login_ip_list.split(",")[0]
            with DBContext('w', None, True) as session:
                session.query(Users).filter(Users.user_id == user_id).update({Users.last_ip: login_ip})
                session.commit()

        self.set_secure_cookie("nickname", user_info.nickname)
        self.set_secure_cookie("username", user_info.username)
        self.set_secure_cookie("user_id", str(user_info.user_id))
        self.set_cookie('auth_key', auth_key, expires_days=1)

        ### 后端权限写入缓存
        my_verify = MyVerify(user_id, is_superuser)
        my_verify.write_verify()
        ### 前端权限写入缓存
        # get_user_rules(user_id, is_superuser)

        return self.write(dict(code=0, auth_key=auth_key.decode(), username=user_info.username,
                               nickname=user_info.nickname, msg='登录成功'))


class LogoutHandler(BaseHandler):
    def get(self):
        self.clear_all_cookies()
        raise HTTPError(401, 'logout')

    def post(self):
        self.clear_all_cookies()
        raise HTTPError(401, 'logout')


class AuthorizationHandler(BaseHandler):
    async def get(self, *args, **kwargs):

        page_data, component_data = {'all': False}, {'all': False}

        with DBContext('r') as session:

            if self.request_is_superuser:
                components_info = session.query(Components.component_name).filter(Components.status == '0').all()
                page_data['all'] = True
                for msg in components_info: component_data[msg[0]] = True

            else:
                this_menus = session.query(Menus.menu_name).outerjoin(RoleMenus,
                                                                      Menus.menu_id == RoleMenus.menu_id).outerjoin(
                    UserRoles, RoleMenus.role_id == UserRoles.role_id).filter(UserRoles.user_id == self.request_user_id,
                                                                              UserRoles.status == '0',
                                                                              Menus.status == '0').all()

                this_components = session.query(Components.component_name).outerjoin(RolesComponents,
                                                                                     Components.comp_id == RolesComponents.comp_id
                                                                                     ).outerjoin(
                    UserRoles, RolesComponents.role_id == UserRoles.role_id).filter(
                    UserRoles.user_id == self.request_user_id, UserRoles.status == '0', Components.status == '0').all()

                for p in this_menus: page_data[p[0]] = True
                for c in this_components: component_data[c[0]] = True

        data = dict(rules=dict(page=page_data, component=component_data))
        return self.write(dict(data=data, code=0, msg='获取前端权限成功'))


# class AuthorizationHandler(BaseHandler):
#     def get(self, *args, **kwargs):
#         user_id = self.get_current_id()
#
#         redis_conn = cache_conn()
#         page = redis_conn.hget("{}_rules".format(user_id), 'page')
#         component = redis_conn.hget("{}_rules".format(user_id), 'component')
#
#         data = dict(rules=dict(page=literal_eval(convert(page)), component=literal_eval(convert(component))))
#         return self.write(dict(data=data, code=0, msg='获取前端权限成功'))


def get_user_rules(user_id, is_superuser=False):
    page_data = {}
    component_data = {}

    with DBContext('r') as session:

        if is_superuser:
            components_info = session.query(Components.component_name).filter(Components.status == '0').all()
            page_data['all'] = True
            component_data['all'] = True
            for msg in components_info:
                component_data[msg[0]] = True

        else:
            this_menus = session.query(Menus.menu_name).outerjoin(RoleMenus,
                                                                  Menus.menu_id == RoleMenus.menu_id).outerjoin(
                UserRoles, RoleMenus.role_id == UserRoles.role_id).filter(UserRoles.user_id == user_id,
                                                                          UserRoles.status == '0',
                                                                          Menus.status == '0').all()

            this_components = session.query(Components.component_name).outerjoin(RolesComponents,
                                                                                 Components.comp_id == RolesComponents.comp_id
                                                                                 ).outerjoin(
                UserRoles, RolesComponents.role_id == UserRoles.role_id).filter(UserRoles.user_id == user_id,
                                                                                UserRoles.status == '0',
                                                                                Components.status == '0').all()

            ## 如果不是超级用户 插入一个没有权限的
            page_data['all'] = False
            component_data['all'] = False
            for p in this_menus:
                page_data[p[0]] = True

            for c in this_components:
                component_data[c[0]] = True

    redis_conn = cache_conn()
    redis_conn.hmset("{}_rules".format(user_id), dict(page=page_data, component=component_data))


login_urls = [
    (r"/login/", LoginHandler),
    (r"/logout/", LogoutHandler),
    (r"/authorization/", AuthorizationHandler),
]

if __name__ == "__main__":
    pass
