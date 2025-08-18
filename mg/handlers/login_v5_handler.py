#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
author : shenshuo
date   : 2017年11月21日
role   : 用户登录
"""

import base64
import json
import logging
from abc import ABC
import time
import pyotp
from tornado.web import RequestHandler
from websdk2.jwt_token import AuthToken

from libs.base_handler import BaseHandler
from services.login_service import update_login_ip, base_verify, ldap_verify, feishu_verify, dingtalk_verify, \
    wechatwork_verify, uc_verify, generate_token, get_user_info_for_id, generate_auth_and_refresh_token, get_user_info
from services.sys_service import get_sys_conf_dict_for_me


class LoginHandler(RequestHandler, ABC):

    def check_xsrf_cookie(self):
        pass

    async def authenticate(self, username: str, password: str, login_type: str, data: dict):
        """
        用户认证函数，根据不同的登录类型调用相应的认证方法。

        :param username: 用户名
        :param password: 密码，可能是 Base64 编码的字符串
        :param login_type: 登录类型，例如 'feishu', 'dingtalk', 'wechatwork', 'ldap', 'base'
        :param data: 附加数据，用于特定登录类型的认证
        :return: 登录结果，成功返回用户信息，失败返回错误信息
        """

        if login_type in ['feishu', 'dingtalk', 'wechatwork']:
            try:
                conf = get_sys_conf_dict_for_me(category=login_type)
                login_dict = {
                    'feishu': dict(code=data.get('code'), fs_redirect_uri=data.get('fs_redirect_uri'), fs_conf=conf),
                    'dingtalk': dict(code=data.get('code'), dd_redirect_uri=data.get('dd_redirect_uri'), dd_conf=conf),
                    'wechatwork': dict(code=data.get('code'), wx_redirect_uri=data.get('wx_redirect_uri'), wx_conf=conf)
                }.get(login_type)

                verify_function = {'feishu': feishu_verify, 'dingtalk': dingtalk_verify,
                                   'wechatwork': wechatwork_verify}.get(login_type)

                return await verify_function(**login_dict)

            except Exception as err:
                logging.error(f"{login_type} 登录失败: {err}")
                return dict(code=-1, msg=f'{login_type} 登录失败')

        if password:
            try:
                password = base64.b64decode(password).decode("utf-8")
                password = base64.b64decode(password).decode("utf-8")
            except Exception as err:
                logging.error(f"密码解码失败: {err}")
                return dict(code=-1, msg='账号密码错误')

        if login_type == 'ldap':
            return await ldap_verify(username, password)

        # if not login_type or login_type == 'ucenter':
        if not username or not password:
            return dict(code=-1, msg='账号密码不能为空')

        uc_conf = self.settings.get('uc_conf')
        login_dict = dict(username=username, password=password, uc_conf=uc_conf)
        user_info = await uc_verify(**login_dict)
        if user_info:
            return user_info
        login_type = None

        if not login_type or login_type == 'base':
            if not username or not password:
                return dict(code=-1, msg='账号密码不能为空')
            return await base_verify(username=username, password=password)

    async def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        username = data.get('username')
        password = data.get('password')
        dynamic = data.get('dynamic')
        c_url = data.get('c_url', '/')
        login_type = data.get('login_type')
        user_info = await self.authenticate(username, password, login_type, data)
        if not user_info:
            if login_type == 'feishu':
                return self.write(dict(code=-3, msg='账号异常，请联系管理员'))
            return self.write(dict(code=-4, msg='用户名密码错误'))

        if isinstance(user_info, dict) and "code" in user_info:
            return self.write(user_info)

        if user_info.status != '0':
            return self.write(dict(code=-5, msg='账号被禁用'))

        user_id = str(user_info.id)
        generate_token_dict = await generate_token(user_info, dynamic)
        if "auth_key" not in generate_token_dict:
            return self.write(generate_token_dict)
        else:
            auth_key = generate_token_dict.get('auth_key')
            mfa_key = generate_token_dict.get('mfa_key')
            refresh_token = generate_token_dict.get('refresh_token', '')

        # 更新登录IP 和登录时间
        update_login_ip(user_id, self.request.headers.get("X-Forwarded-For"))

        # self.set_cookie("auth_key", auth_key, expires_days=1, httponly=True)
        self.set_secure_cookie("nickname", user_info.nickname)
        self.set_secure_cookie("username", user_info.username)
        self.set_secure_cookie("user_id", user_id)
        self.set_cookie("auth_key", auth_key, expires_days=1)
        self.set_cookie("refresh_token", refresh_token, httponly=True, expires_days=3)
        self.set_cookie("is_login", 'yes', expires_days=1)
        if mfa_key:
            self.set_cookie("mfa_key", mfa_key, expires_days=1, httponly=True)

        # TODO 清理外层数据
        real_login_dict = dict(code=0, msg='登录成功',
                               username=user_info.username,
                               nickname=user_info.nickname,
                               auth_key=auth_key,
                               avatar=user_info.avatar,
                               c_url=c_url,
                               data=dict(username=user_info.username, nickname=user_info.nickname, auth_key=auth_key,
                                         avatar=user_info.avatar, c_url=c_url))
        return self.write(real_login_dict)


class VerifyMFAHandler(BaseHandler, ABC):
    async def get(self, *args, **kwargs):
        await self.handle_verification()

    async def post(self, *args, **kwargs):
        await self.handle_verification()

    async def handle_verification(self):
        dynamic = self.get_argument("dynamic", "")
        if not dynamic:
            return self.write(dict(code=-1, msg='动态码不能为空'))

        user_info = get_user_info_for_id(int(self.user_id))

        if not user_info:
            return self.write(dict(code=-4, msg='用户不存在或者账号被禁用'))
        if user_info.google_key:
            totp = pyotp.TOTP(user_info.google_key)
            if not totp.verify(dynamic):
                return self.write(dict(code=-5, msg='MFA错误'))
            auth_token = AuthToken()
            mfa_key = auth_token.encode_mfa_token(user_id=self.user_id, email=user_info.email)
            self.set_cookie("mfa_key", mfa_key, expires_days=1, httponly=True)
            return self.write(dict(code=0, msg='认证成功', data=dict(mfa_key=mfa_key)))

        return self.write(dict(code=0, msg='当前用户未开启二次认证'))


class LogoutHandler(RequestHandler, ABC):

    def get(self):
        try:
            root_domain = self.request.headers.get('Codo-root-domain')
            self.clear_all_cookies()
            self.clear_cookie("auth_key", domain=root_domain)
            self.clear_cookie("is_login", domain=root_domain)
        except Exception as err:
            logging.error(err)
        self.set_status(401)
        self.finish()

    def post(self):
        try:
            root_domain = self.request.headers.get('Codo-root-domain')
            self.clear_all_cookies()
            self.clear_cookie("auth_key", domain=root_domain)
            self.clear_cookie("is_login", domain=root_domain)
        except Exception as err:
            logging.error(err)
        self.set_status(401)
        self.finish()


class RefreshTokenHandler(RequestHandler, ABC):
    def get(self):
        try:
            refresh_token = self.get_cookie("refresh_token")
            if not refresh_token:
                self.set_status(401)
                self.write({"code": -1, "msg": "缺失 refresh_token in cookie"})
                return

            auth_token = AuthToken()
            try:
                payload = auth_token.decode_auth_token(refresh_token)
                user_id = payload.get("user_id")
                if not user_id:
                    raise ValueError("Invalid payload")
            except Exception as e:
                self.set_status(401)
                self.write({"code": -1, "msg": f"Invalid or expired refresh token: {str(e)}"})
                return

            user_info = get_user_info(user_id)
            if not user_info:
                self.set_status(401)
                self.write({"code": -1, "msg": "User not found or inactive"})
                return

            auth_key, refresh_token = generate_auth_and_refresh_token(user_info)

            # 设置 cookies
            self.set_cookie("auth_key", auth_key, expires_days=1)
            self.set_cookie("refresh_token", refresh_token, httponly=True, expires_days=3)
            self.set_cookie("is_login", "yes", expires_days=1)

            self.write({"code": 0, "msg": "刷新成功", "auth_key": auth_key,
                        "reason": "", "timestamp": int(time.time() * 1000)})

        except Exception as e:
            self.set_status(500)
            self.write({"code": -1, "msg": f"Server error: {str(e)}"})


login_v5_urls = [
    (r"/v4/na/login/05/", LoginHandler),
    (r"/v4/na/logout/", LogoutHandler),
    (r"/v4/verify/mfa/", VerifyMFAHandler),
    (r"/v4/na/refresh-token/", RefreshTokenHandler)
]

if __name__ == "__main__":
    pass
