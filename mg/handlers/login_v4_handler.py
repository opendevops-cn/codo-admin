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
from shortuuid import uuid
from loguru import logger
from libs.base_handler import BaseHandler
from tornado.web import RequestHandler, HTTPError
from concurrent.futures import ThreadPoolExecutor
from tornado.concurrent import run_on_executor
from tornado import gen
from websdk2.jwt_token import AuthToken, gen_md5
import pyotp
from websdk2.db_context import DBContextV2 as DBContext
from models.authority import Users, Components, RolesComponents, Menus, RoleMenus, UserRoles, Roles
from websdk2.consts import const
from websdk2.cache_context import cache_conn
from websdk2.ldap import LdapApi
from services.sys_service import get_sys_conf_dict_for_me
from libs.login_by_feishu import FeiShuAuth, with_protocol_feishu
from libs.login_by_other import OtherAuthV3


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

    @run_on_executor(executor='_thread_pool')
    def ldap_authentication(self, username, password):
        password = base64.b64decode(password).decode("utf-8")
        password = base64.b64decode(password).decode("utf-8")

        ldap_conf = get_sys_conf_dict_for_me(**dict(category='ldap'))
        if ldap_conf.get(const.LDAP_ENABLE) == 'no':
            return dict(code=-5, msg='请联系管理员启用LDAP登录')

        if not ldap_conf:
            return dict(code=-5, msg='请补全LDAP信息')

        try:
            obj = LdapApi(ldap_conf.get(const.LDAP_SERVER_HOST), ldap_conf.get(const.LDAP_ADMIN_DN),
                          ldap_conf.get(const.LDAP_ADMIN_PASSWORD), ldap_conf.get(const.LDAP_USE_SSL))

            ldap_pass_info = obj.ldap_auth_v3(username, password, ldap_conf.get(const.LDAP_SEARCH_BASE),
                                              ldap_conf.get(const.LDAP_ATTRIBUTES),
                                              ldap_conf.get(const.LDAP_SEARCH_FILTER))
        except Exception as err:
            logger.error(f"LDAP信息出错 {err}")
            return dict(code=-4, msg='LDAP信息出错')

        if not ldap_pass_info[0]:
            return dict(code=-4, msg='账号密码错误')

        with DBContext('r') as session:
            user_info = session.query(Users).filter(Users.username == username, Users.status != '10').first()

            if not user_info:
                # 没有账户就自动注册一个
                mfa = base64.b32encode(bytes(str(uuid() + uuid())[:-9], encoding="utf-8")).decode("utf-8")
                attr_dict = ldap_pass_info[1]

                session.add(Users(username=attr_dict.get('username', username),
                                  nickname=attr_dict.get('nickname', username),
                                  email=attr_dict.get('email'), password=gen_md5(password), tel='', google_key=mfa))
        return user_info

    #
    @staticmethod
    def update_login_ip(user_id: str, login_ip_list: str):
        try:
            if not isinstance(user_id, str):
                raise ValueError("Invalid user_id")

            if not isinstance(login_ip_list, str):
                raise ValueError("Invalid login_ip_list")

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

        uc_conf = self.settings.get('uc_conf')
        user_info = None
        if login_type == 'feishu':
            fs_conf = get_sys_conf_dict_for_me(**dict(category='feishu'))
            feishu_login_dict = dict(code=data.get('code'), fs_redirect_uri=data.get('fs_redirect_uri'),
                                     fs_conf=fs_conf)
            user_info = yield self.feishu_authentication(**feishu_login_dict)

        if login_type == 'ldap':
            ldap_login_data = yield self.ldap_authentication(username, password)
            if isinstance(ldap_login_data, dict):
                return self.write(ldap_login_data)
            else:
                user_info = ldap_login_data
            # 如果 ldap 没启用 使用ucenter
            if not get_sys_conf_dict_for_me(**dict(category='ldap')): login_type = 'ucenter'

        if login_type == 'ucenter':
            if not username or not password:
                return self.write(dict(code=-1, msg='账号密码不能为空'))
            ucenter_password = base64.b64decode(password).decode("utf-8")
            ucenter_password = base64.b64decode(ucenter_password).decode("utf-8")
            login_dict = dict(username=username, password=ucenter_password, uc_conf=uc_conf)
            user_info = yield self.other_authentication(**login_dict)
            if not user_info: login_type = None

        if not login_type or login_type == 'base':
            # 这段逻辑 是给一个保底策略
            if not username or not password:
                return self.write(dict(code=-1, msg='账号密码不能为空'))
            user_info = self.base_authentication(username=username, password=password)

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

        # 更新登录IP 和登录时间
        self.update_login_ip(user_id, self.request.headers.get("X-Forwarded-For"))
        real_login_dict = dict(code=0, username=user_info.username, nickname=user_info.nickname, auth_key=auth_key,
                               avatar=user_info.avatar, c_url=c_url, msg='登录成功')

        # self.set_cookie("auth_key", auth_key, expires_days=7, httponly=True)
        self.set_cookie("auth_key", auth_key, expires_days=1)
        self.set_cookie("is_login", 'yes', expires_days=1)

        self.finish(real_login_dict)


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
        page_data, component_data, avatar = {'all': False}, {'all': False}, ''

        with DBContext('r') as session:
            if self.request_is_superuser:
                components_info = session.query(Components.name).all()
                page_data['all'] = True
                for msg in components_info: component_data[msg[0]] = True

            else:
                __role = session.query(Roles).outerjoin(UserRoles, UserRoles.role_id == Roles.id).filter(
                    UserRoles.user_id == self.request_user_id).all()

                _role_list = []
                if __role:
                    for role in __role:
                        _role_list.append(role.id)
                        if role.role_subs:
                            _role_list.extend(role.role_subs)

                    _role_list = set(_role_list)
                    # print(_role_list)
                    __menus = session.query(Menus.menu_name).outerjoin(RoleMenus, Menus.id == RoleMenus.menu_id).filter(
                        RoleMenus.role_id.in_(_role_list)).all()

                    __component = session.query(Components.name).outerjoin(RolesComponents,
                                                                           Components.id == RolesComponents.comp_id).filter(
                        RolesComponents.role_id.in_(_role_list)).all()
                    for p in __menus: page_data[p[0]] = True
                    for c in __component: component_data[c[0]] = True

            ###
            __user = session.query(Users.avatar).filter(Users.id == self.request_user_id).first()
            # if not __user: return self.write(dict(code=-2, msg='当前账户状态错误'))
            if __user: avatar = __user[0]
        # logger.error(f"{page_data}, {self.request_username},{self.request_user_id} super {self.request_is_superuser}")
        data = dict(rules=dict(page=page_data, component=component_data), username=self.request_username,
                    nickname=self.request_nickname, avatar=avatar)
        return self.write(dict(data=data, code=0, msg='获取前端权限成功'))


class LoginMHandler(RequestHandler, ABC):
    def get(self, url_code):
        params = {k: self.get_argument(k) for k in self.request.arguments}
        # 第一步 https://applink.feishu.cn/client/web_url/open?url=http://10.241.0.40:8888/api/acc/m/test6666
        # 第二 f'https://passport.feishu.cn/accounts/auth_login/oauth2/authorize?client_id={client_id}&response_type=code&{redirect_uri}&state={state}'
        # print(with_protocol_feishu(url_code, params))
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

        # fs_conf = self.settings.get('fs_conf')
        fs_conf = get_sys_conf_dict_for_me(**dict(category='feishu'))
        feishu_login_dict = dict(code=code, fs_redirect_uri=fs_redirect_uri, fs_conf=fs_conf)

        user_info = yield self.feishu_authentication(**feishu_login_dict)
        print(user_info)

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

        self.set_secure_cookie('is_login', 'yes', expires_days=1, httponly=False)
        self.set_cookie("auth_key", auth_key, expires_days=1, httponly=False)

        self.redirect(c_url)


login_v4_urls = [
    (r"/v4/na/login/", LoginHandler),
    (r"/v4/na/logout/", LogoutHandler),
    (r"/v4/na/authorization/", AuthorizationHandler),
    (r"/v4/na/m/(.+)", LoginMHandler),
    (r"/v4/na/login/feishu/", LoginFSHandler),
]

if __name__ == "__main__":
    pass
