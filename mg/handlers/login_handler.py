#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
author : shenshuo
date   : 2017年11月21日
role   : 用户登录
"""

import json
import base64
from libs.base_handler import BaseHandler
from tornado.web import RequestHandler, HTTPError
from websdk2.jwt_token import AuthToken, gen_md5
from websdk2.tools import is_mail
from websdk2.utils import mail_login
from websdk2.model_utils import queryset_to_list, model_to_dict
import pyotp
from websdk2.db_context import DBContextV2 as DBContext
from models.admin_model import Users, Components, RolesComponents, Menus, RoleMenus, UserRoles, Apps, RoleApps
from .configs_init import configs_init
from websdk2.consts import const
from websdk2.cache_context import cache_conn
from websdk2.tools import convert
from websdk2.ldap import LdapApi

from concurrent.futures import ThreadPoolExecutor
from tornado.concurrent import run_on_executor
from tornado import gen


class LoginHandler(RequestHandler):
    def check_xsrf_cookie(self):
        pass

    _thread_pool = ThreadPoolExecutor(2)

    @run_on_executor(executor='_thread_pool')
    def other_authentication(self, **kwargs):
        from libs.login_by_other import OtherAuthV2
        return OtherAuthV2(**kwargs)()

    @run_on_executor(executor='_thread_pool')
    def mail_authentication(self, username, password, user_info):
        login_mail = self.redis_conn.hget(const.APP_SETTINGS, const.EMAILLOGIN_DOMAIN)
        if isinstance(login_mail, bytes): login_mail = login_mail.decode('utf-8')

        if login_mail:
            if is_mail(username, login_mail):
                email = username
                username = email.split("@")[0]
                email_server = self.redis_conn.hget(const.APP_SETTINGS, const.EMAILLOGIN_SERVER).decode('utf-8')
                if not email_server: return dict(code=-9, msg='请配置邮箱服务的SMTP服务地址')
                mail_login_state = mail_login(email, password, email_server)
                # print(mail_login_state)
                if not mail_login_state: return dict(code=-2, msg='邮箱登陆认证失败')
                if not user_info: return dict(code=-3, msg='邮箱认证通过，请根据邮箱完善用户信息', username=username,
                                              email=email)

        return True

    @run_on_executor(executor='_thread_pool')
    def LDAP_authentication(self, username, password):
        config_info = self.redis_conn.hgetall(const.APP_SETTINGS)
        config_info = convert(config_info)
        ldap_ssl = True if config_info.get(const.LDAP_USE_SSL) == '1' else False

        obj = LdapApi(config_info.get(const.LDAP_SERVER_HOST), config_info.get(const.LDAP_ADMIN_DN),
                      config_info.get(const.LDAP_ADMIN_PASSWORD),
                      int(config_info.get(const.LDAP_SERVER_PORT, 389)), ldap_ssl)

        ldap_pass_info = obj.ldap_auth_v2(username, password, config_info.get(const.LDAP_SEARCH_BASE),
                                          config_info.get(const.LDAP_SEARCH_FILTER))

        if not ldap_pass_info[0]: return dict(code=-4, msg='账号密码错误')

        with DBContext('r') as session:
            user_info = session.query(Users).filter(Users.username == username, Users.status != '10').first()

        if not user_info:  return dict(code=-6, msg='LDAP认证通过，完善用户信息', username=ldap_pass_info[1],
                                       email=ldap_pass_info[2])
        return user_info

    @staticmethod
    def update_login_ip(user_id, login_ip_list):
        try:
            login_ip = login_ip_list.split(",")[0]
            with DBContext('w', None, True) as session:
                session.query(Users).filter(Users.user_id == user_id).update({Users.last_ip: login_ip})
                session.commit()
        except Exception as err:
            print(err)

    @gen.coroutine
    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        username = data.get('username', None)
        password = data.get('password', None)
        dynamic = data.get('dynamic', None)
        c_url = data.get('c_url', None)

        if not username or not password:  return self.write(dict(code=-1, msg='账号密码不能为空'))

        password = base64.b64decode(password).decode("utf-8")
        password = base64.b64decode(password).decode("utf-8")

        self.redis_conn = cache_conn()

        configs_init('all')
        uc_conf = self.settings.get('uc_conf')
        login_mail = self.redis_conn.hget(const.APP_SETTINGS, const.EMAILLOGIN_DOMAIN)

        with DBContext('r') as session:

            if is_mail(username) and login_mail:
                user_info = session.query(Users).filter(Users.email == username, Users.status != '10').first()
            else:
                user_info = session.query(Users).filter(Users.username == username, Users.password == gen_md5(password),
                                                        Users.status != '10').first()

        ## 通过第三方SSO登录
        if uc_conf and not user_info:
            login_dict = dict(username=username, password=password, uc_conf=uc_conf)
            login_state = yield self.other_authentication(**login_dict)
            if login_state is False:  return self.write(dict(code=-14, msg='第三方登录失败'))
            with DBContext('r') as session:
                user_info = session.query(Users).filter(Users.username == username, Users.status != '10').first()


        ###通过邮箱登录
        elif is_mail(username) and login_mail:
            mail_login_data = yield self.mail_authentication(username, password, user_info)
            if mail_login_data is not True: return self.write(mail_login_data)

        ### 通过LDAP登录
        elif not user_info:
            """如果没有用户信息则使用LDAP"""
            ldap_login = self.redis_conn.hget(const.APP_SETTINGS, const.LDAP_ENABLE)
            if ldap_login not in ['1', b'1']:  return self.write(dict(code=-4, msg='账号密码错误'))
            ### 如果开启了LDAP认证 则进行LDAP认证
            ldap_login_data = yield self.LDAP_authentication(username, password)
            if isinstance(ldap_login_data, dict):
                return self.write(ldap_login_data)
            else:
                user_info = ldap_login_data

        if 'user_info' not in dir():  return self.write(dict(code=-4, msg='账号异常'))
        if not user_info:  return self.write(dict(code=-4, msg='账号异常'))
        if user_info.status != '0': return self.write(dict(code=-4, msg='账号被禁用'))

        is_superuser = True if user_info.superuser == '0' else False

        ### 如果被标记为必须动态验证切没有输入动态密钥，则跳转到二维码添加密钥的地方
        if user_info.google_key:
            ### 第一次不带MFA的认证
            if not dynamic: return self.write(dict(code=1, msg='跳转二次认证'))
            ### 二次认证
            if pyotp.TOTP(user_info.google_key).now() != str(dynamic):  return self.write(dict(code=-5, msg='MFA错误'))

        user_id = str(user_info.user_id)

        ### 生成token 并写入cookie
        token_info = dict(user_id=user_id, username=user_info.username, nickname=user_info.nickname,
                          email=user_info.email, is_superuser=is_superuser)

        auth_token = AuthToken()
        auth_key = auth_token.encode_auth_token_v2(**token_info)
        if isinstance(auth_key, bytes): auth_key = auth_key.decode()

        self.set_secure_cookie("nickname", user_info.nickname)
        self.set_secure_cookie("username", user_info.username)
        self.set_secure_cookie("user_id", str(user_info.user_id))
        self.set_cookie('auth_key', auth_key, expires_days=1)

        ###更新登录IP 和登录时间
        self.update_login_ip(user_id, self.request.headers.get("X-Forwarded-For"))
        real_login_dict = dict(code=0, auth_key=auth_key, username=user_info.username, nickname=user_info.nickname,
                               avatar=user_info.avatar, c_url=c_url, msg='登录成功')

        # if other_sso_data and isinstance(other_sso_data, dict):
        #     real_login_dict = {**other_sso_data, **real_login_dict}
        #     for k, v in other_sso_data.items():
        #         self.set_cookie(k, v, expires_days=1)

        return self.write(real_login_dict)


class LogoutHandler(BaseHandler):
    def get(self):
        self.clear_all_cookies()
        raise HTTPError(401, 'logout')

    def post(self):
        self.clear_all_cookies()
        raise HTTPError(401, 'logout')


class AuthorizationHandler(BaseHandler):
    async def get(self, *args, **kwargs):
        app_code = self.get_argument('app_code', default=None, strip=True)

        app_data, page_data, component_data = [], {'all': False}, {'all': False}

        with DBContext('r') as session:

            all_app = session.query(Apps).filter(Apps.status == '0').all()

            if self.request_is_superuser:
                components_info = session.query(Components.component_name).filter(Components.status == '0').all()
                page_data['all'] = True
                for msg in components_info: component_data[msg[0]] = True
                app_data = queryset_to_list(all_app)

            elif app_code and app_code != 'all':
                this_menus = session.query(Menus.menu_name).outerjoin(
                    RoleMenus, Menus.menu_id == RoleMenus.menu_id).outerjoin(
                    UserRoles, RoleMenus.role_id == UserRoles.role_id).filter(
                    UserRoles.user_id == self.request_user_id, UserRoles.status == '0', Menus.app_code == app_code,
                    Menus.status == '0').all()

                this_components = session.query(Components.component_name).outerjoin(
                    RolesComponents, Components.comp_id == RolesComponents.comp_id).outerjoin(
                    UserRoles, RolesComponents.role_id == UserRoles.role_id).filter(
                    UserRoles.user_id == self.request_user_id, UserRoles.status == '0',
                    Components.app_code == app_code, Components.status == '0').all()

                for p in this_menus: page_data[p[0]] = True
                for c in this_components: component_data[c[0]] = True

            else:
                this_menus = session.query(Menus.menu_name).outerjoin(
                    RoleMenus, Menus.menu_id == RoleMenus.menu_id).outerjoin(
                    UserRoles, RoleMenus.role_id == UserRoles.role_id).filter(
                    UserRoles.user_id == self.request_user_id, UserRoles.status == '0', Menus.status == '0').all()

                this_components = session.query(Components.component_name).outerjoin(
                    RolesComponents, Components.comp_id == RolesComponents.comp_id).outerjoin(
                    UserRoles, RolesComponents.role_id == UserRoles.role_id).filter(
                    UserRoles.user_id == self.request_user_id, UserRoles.status == '0',
                    Components.status == '0').all()

                for p in this_menus: page_data[p[0]] = True
                for c in this_components: component_data[c[0]] = True

            if not self.request_is_superuser:
                this_app = session.query(Apps).outerjoin(RoleApps, Apps.app_id == RoleApps.app_id).outerjoin(
                    UserRoles, RoleApps.role_id == UserRoles.role_id).filter(
                    UserRoles.user_id == self.request_user_id, UserRoles.status == '0', Apps.status == '0').all()

                this_app_id_list = [i.app_id for i in this_app]
                for a in all_app:
                    app_dict = model_to_dict(a)
                    if a.app_id not in this_app_id_list:
                        app_dict['power'] = 'no'
                    app_data.append(app_dict)

            ###
            __user = session.query(Users.avatar).filter(Users.user_id == self.request_user_id).first()
        data = dict(rules=dict(page=page_data, component=component_data), app=app_data, username=self.request_username,
                    nickname=self.request_nickname, avatar="")
        return self.write(dict(data=data, code=0, msg='获取前端权限成功'))


login_urls = [
    (r"/accounts/login/", LoginHandler),
    (r"/accounts/logout/", LogoutHandler),
    (r"/accounts/authorization/", AuthorizationHandler),
]

if __name__ == "__main__":
    pass
