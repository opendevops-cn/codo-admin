#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
author : shenshuo
date   : 2017年11月21日
role   : 用户登录
"""

import json
import base64
from typing import *
from abc import ABC
from libs.base_handler import BaseHandler
from tornado.web import RequestHandler, HTTPError
from websdk2.jwt_token import AuthToken, gen_md5
# from websdk2.tools import is_mail
# from websdk2.utils import mail_login
# from websdk2.model_utils import queryset_to_list, model_to_dict
import pyotp
from websdk2.db_context import DBContextV2 as DBContext
from models.authority import Users, Components, RolesComponents, Menus, RoleMenus, UserRoles
from websdk2.consts import const
from websdk2.cache_context import cache_conn
# from websdk2.tools import convert
from websdk2.ldap import LdapApi
from libs.login_by_feishu import FeiShuAuth, with_protocol_feishu
from libs.login_by_other import OtherAuthV3
from concurrent.futures import ThreadPoolExecutor
from tornado.concurrent import run_on_executor
from tornado import gen


class LoginHandler(RequestHandler, ABC):
    _thread_pool = ThreadPoolExecutor(5)

    def check_xsrf_cookie(self):
        pass

    @run_on_executor(executor='_thread_pool')
    def feishu_authentication(self, **kwargs) -> Optional[Users]:
        return FeiShuAuth(**kwargs)()

    @staticmethod
    def base_authentication(username, password) -> Optional[Users]:

        password = base64.b64decode(password).decode("utf-8")
        password = base64.b64decode(password).decode("utf-8")
        with DBContext('r') as session:
            user_info: Optional[Users] = session.query(Users).filter(Users.username == username,
                                                                     Users.password == gen_md5(password),
                                                                     Users.status != '10').first()
        return user_info

    @run_on_executor(executor='_thread_pool')
    def other_authentication(self, **kwargs) -> Optional[Users]:
        return OtherAuthV3(**kwargs)()

    # @run_on_executor(executor='_thread_pool')
    # def other_authentication(self, **kwargs):
    #     from libs.login_by_other import OtherAuthV2
    #     return OtherAuthV2(**kwargs)()
    #
    # @run_on_executor(executor='_thread_pool')
    # def mail_authentication(self, username, password, user_info):
    #     login_mail = self.redis_conn.hget(const.APP_SETTINGS, const.EMAILLOGIN_DOMAIN)
    #     if isinstance(login_mail, bytes): login_mail = login_mail.decode('utf-8')
    #
    #     if login_mail:
    #         if is_mail(username, login_mail):
    #             email = username
    #             username = email.split("@")[0]
    #             email_server = self.redis_conn.hget(const.APP_SETTINGS, const.EMAILLOGIN_SERVER).decode('utf-8')
    #             if not email_server: return dict(code=-9, msg='请配置邮箱服务的SMTP服务地址')
    #             mail_login_state = mail_login(email, password, email_server)
    #             # print(mail_login_state)
    #             if not mail_login_state: return dict(code=-2, msg='邮箱登陆认证失败')
    #             if not user_info: return dict(code=-3, msg='邮箱认证通过，请根据邮箱完善用户信息', username=username,
    #                                           email=email)
    #
    #     return True
    #
    @run_on_executor(executor='_thread_pool')
    def ldap_authentication(self, username, password, ldap_conf):
        ldap_ssl = True if ldap_conf.get(const.LDAP_USE_SSL) == '1' else False

        obj = LdapApi(ldap_conf.get(const.LDAP_SERVER_HOST), ldap_conf.get(const.LDAP_ADMIN_DN),
                      ldap_conf.get(const.LDAP_ADMIN_PASSWORD),
                      int(ldap_conf.get(const.LDAP_SERVER_PORT, 389)), ldap_ssl)

        ldap_pass_info = obj.ldap_auth_v2(username, password, ldap_conf.get(const.LDAP_SEARCH_BASE),
                                          ldap_conf.get(const.LDAP_SEARCH_FILTER))

        if not ldap_pass_info[0]:
            return dict(code=-4, msg='账号密码错误')

        with DBContext('r') as session:
            user_info = session.query(Users).filter(Users.username == username, Users.status != '10').first()

        if not user_info:
            return dict(code=-6, msg='LDAP认证通过，完善用户信息', username=ldap_pass_info[1],
                        email=ldap_pass_info[2])
        return user_info

    #
    @staticmethod
    def update_login_ip(user_id, login_ip_list):
        try:
            login_ip = login_ip_list.split(",")[0]
            with DBContext('w', None, True) as session:
                session.query(Users).filter(Users.id == user_id).update({Users.last_ip: login_ip})
                session.commit()
        except Exception as err:
            print(err)

    @gen.coroutine
    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        print(data)
        username = data.get('username')
        password = data.get('password')
        dynamic = data.get('dynamic')
        c_url = data.get('c_url', '/')
        login_type = data.get('login_type')

        fs_conf = self.settings.get('fs_conf')
        uc_conf = self.settings.get('uc_conf')
        ldap_conf = self.settings.get('ldap_conf')
        user_info = None
        if login_type == 'feishu':
            feishu_login_dict = dict(code=data.get('code'), fs_redirect_uri=data.get('fs_redirect_uri'),
                                     fs_conf=fs_conf)
            user_info = yield self.feishu_authentication(**feishu_login_dict)
        elif login_type == 'ldap' and ldap_conf and ldap_conf.get(const.LDAP_ENABLE) == 'yes':
            ldap_login_data = yield self.ldap_authentication(username, password, ldap_conf)
            if isinstance(ldap_login_data, dict):
                return self.write(ldap_login_data)
            else:
                user_info = ldap_login_data

        elif not login_type or login_type == 'base':
            if not username or not password:
                return self.write(dict(code=-1, msg='账号密码不能为空'))
            user_info = self.base_authentication(username=username, password=password)

        elif login_type == 'ucenter':
            if not username or not password:
                return self.write(dict(code=-1, msg='账号密码不能为空'))
            login_dict = dict(username=username, password=password, uc_conf=uc_conf)
            user_info = yield self.other_authentication(**login_dict)

        if not user_info:
            return self.write(dict(code=-4, msg='账号异常'))

        if user_info.status != '0':
            return self.write(dict(code=-4, msg='账号被禁用'))

        is_superuser = True if user_info.superuser == '0' else False

        # 如果被标记为必须动态验证切没有输入动态密钥，则跳转到二维码添加密钥的地方
        if user_info.google_key:
            # 第一次不带MFA的认证
            if not dynamic:
                return self.write(dict(code=66, msg='跳转二次认证'))
            # 二次认证
            if pyotp.TOTP(user_info.google_key).now() != str(dynamic):
                return self.write(dict(code=-5, msg='MFA错误'))

        user_id = str(user_info.id)

        # 生成token 并写入cookie
        token_info = dict(user_id=user_id, username=user_info.username, nickname=user_info.nickname,
                          email=user_info.email, is_superuser=is_superuser)

        auth_token = AuthToken()
        auth_key = auth_token.encode_auth_token_v2(**token_info)
        if isinstance(auth_key, bytes):
            auth_key = auth_key.decode()

        self.set_secure_cookie("nickname", user_info.nickname)
        self.set_secure_cookie("username", user_info.username)
        self.set_secure_cookie("user_id", user_id)
        # self.set_cookie('auth_key', auth_key, expires_days=1)

        # 更新登录IP 和登录时间
        self.update_login_ip(user_id, self.request.headers.get("X-Forwarded-For"))
        real_login_dict = dict(code=0, username=user_info.username, nickname=user_info.nickname, auth_key=auth_key,
                               avatar=user_info.avatar, c_url=c_url, msg='登录成功')

        self.set_cookie("auth_key", auth_key, expires_days=7, httponly=True)

        return self.write(real_login_dict)


class LogoutHandler(RequestHandler, ABC):
    def get(self):
        self.clear_all_cookies()
        self.set_status(401)
        self.finish()
        # raise HTTPError(401, 'logout')

    def post(self):
        self.clear_all_cookies()
        self.set_status(401)
        self.finish()


class AuthorizationHandler(BaseHandler, ABC):
    async def get(self, *args, **kwargs):
        app_code = self.get_argument('app_code', default=None, strip=True)

        app_data, page_data, component_data = [], {'all': False}, {'all': False}

        with DBContext('r') as session:
            # all_app = session.query(AppsModel).filter(AppsModel.status == '0').all()

            if self.request_is_superuser:
                components_info = session.query(Components.component_name).filter(Components.status == '0').all()
                page_data['all'] = True
                for msg in components_info: component_data[msg[0]] = True
                # app_data = queryset_to_list(all_app)

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

            # if not self.request_is_superuser:
            #     this_app = session.query(Apps).outerjoin(RoleApps, Apps.app_id == RoleApps.app_id).outerjoin(
            #         UserRoles, RoleApps.role_id == UserRoles.role_id).filter(
            #         UserRoles.user_id == self.request_user_id, UserRoles.status == '0', Apps.status == '0').all()
            #
            #     this_app_id_list = [i.app_id for i in this_app]
            #     for a in all_app:
            #         app_dict = model_to_dict(a)
            #         if a.app_id not in this_app_id_list:
            #             app_dict['power'] = 'no'
            #         app_data.append(app_dict)

            ###
            __user = session.query(Users.avatar).filter(Users.user_id == self.request_user_id).first()
        data = dict(rules=dict(page=page_data, component=component_data), username=self.request_username,
                    nickname=self.request_nickname, avatar=__user[0])
        return self.write(dict(data=data, code=0, msg='获取前端权限成功'))


class LoginMHandler(RequestHandler, ABC):
    def get(self, url_code):
        params = {k: self.get_argument(k) for k in self.request.arguments}
        # 第一步 https://applink.feishu.cn/client/web_url/open?url=http://10.241.0.40:8888/api/p/v4/m/test6666
        # 第二 f'https://passport.feishu.cn/accounts/auth_login/oauth2/authorize?client_id={client_id}&response_type=code&{redirect_uri}&state={state}'
        print(with_protocol_feishu(url_code, params))
        return self.redirect(with_protocol_feishu(url_code, params))


class LoginFSHandler(RequestHandler, ABC):
    _thread_pool = ThreadPoolExecutor(5)

    def check_xsrf_cookie(self):
        pass

    @run_on_executor(executor='_thread_pool')
    def feishu_authentication(self, **kwargs) -> Optional[Users]:
        return FeiShuAuth(**kwargs)()

    #
    @staticmethod
    def update_login_ip(user_id, login_ip_list):
        try:
            login_ip = login_ip_list.split(",")[0]
            with DBContext('w', None, True) as session:
                session.query(Users).filter(Users.id == user_id).update({Users.last_ip: login_ip})
                session.commit()
        except Exception as err:
            print(err)

    @gen.coroutine
    def get(self, *args, **kwargs):

        code = self.get_argument('code')
        state = self.get_argument('state', default=None)

        redis_conn = cache_conn()
        c_url = redis_conn.get(f"feishu_c_url___{state}")
        fs_redirect_uri = redis_conn.get(f"feishu_fs_redirect_uri___{state}")
        if not c_url or not fs_redirect_uri:
            return self.write(dict(code=-10, msg='登录出错，请重试'))

        fs_conf = self.settings.get('fs_conf')
        feishu_login_dict = dict(code=code, fs_redirect_uri=fs_redirect_uri, fs_conf=fs_conf)

        user_info = yield self.feishu_authentication(**feishu_login_dict)

        if not user_info:
            return self.write(dict(code=-4, msg='账号异常'))

        if user_info.status != '0':
            return self.write(dict(code=-4, msg='账号被禁用'))

        is_superuser = True if user_info.superuser == '0' else False

        user_id = str(user_info.id)

        # 生成token 并写入cookie
        token_info = dict(user_id=user_id, username=user_info.username, nickname=user_info.nickname,
                          email=user_info.email, is_superuser=is_superuser)

        auth_token = AuthToken()
        auth_key = auth_token.encode_auth_token_v2(**token_info)
        if isinstance(auth_key, bytes):
            auth_key = auth_key.decode()

        self.set_secure_cookie("nickname", user_info.nickname)
        self.set_secure_cookie("username", user_info.username)
        self.set_secure_cookie("user_id", user_id)

        # 更新登录IP 和登录时间
        self.update_login_ip(user_id, self.request.headers.get("X-Forwarded-For"))
        # real_login_dict = dict(code=0, username=user_info.username, nickname=user_info.nickname, auth_key=auth_key,
        #                        avatar=user_info.avatar, c_url=c_url, msg='登录成功')

        self.set_secure_cookie('auth_key_login', 'is_login', expires_days=1, httponly=False)
        self.set_cookie("auth_key", auth_key, expires_days=1, httponly=True)

        self.redirect(c_url)


login_v4_urls = [
    (r"/v4/login/", LoginHandler),
    (r"/v4/logout/", LogoutHandler),
    (r"/v4/authorization/", AuthorizationHandler),
    (r"/v4/m/(.+)", LoginMHandler),
    (r"/v4/login/feishu/", LoginFSHandler),
]

if __name__ == "__main__":
    pass
