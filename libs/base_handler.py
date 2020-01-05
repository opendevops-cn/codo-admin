#!/usr/bin/env python
# -*-coding:utf-8-*-

import jwt
import shortuuid
from websdk.cache import get_cache
from websdk.base_handler import BaseHandler as SDKBaseHandler
from tornado.web import HTTPError
from websdk.jwt_token import AuthToken
from .my_verify import MyVerify


class BaseHandler(SDKBaseHandler):
    def __init__(self, *args, **kwargs):
        self.new_csrf_key = str(shortuuid.uuid())
        self.user_id, self.username, self.nickname, self.email, self.is_super = None, None, None, None, False
        self.is_superuser = self.is_super
        self.token_verify = True

        super(BaseHandler, self).__init__(*args, **kwargs)

    def prepare(self):

        # 验证客户端CSRF，如请求为GET，则不验证，否则验证。最后将写入新的key
        cache = get_cache()
        if self.request.method in ("GET", "HEAD", "OPTIONS") or self.request.headers.get(
                'Sdk-Method') == 'zQtY4sw7sqYspVLrqV':
            pass
        else:
            csrf_key = self.get_cookie('csrf_key')
            pipeline = cache.get_pipeline()
            result = cache.get(csrf_key, private=False, pipeline=pipeline)
            cache.delete(csrf_key, private=False, pipeline=pipeline)
            if result != '1':
                raise HTTPError(402, 'csrf error')

        cache.set(self.new_csrf_key, 1, expire=1800, private=False)
        self.set_cookie('csrf_key', self.new_csrf_key)

        ### 登陆验证
        auth_key = self.get_cookie('auth_key', None)
        if not auth_key:
            # 没登录，就让跳到登陆页面
            raise HTTPError(401, 'auth failed 1')

        else:
            if self.token_verify:
                auth_token = AuthToken()
                user_info = auth_token.decode_auth_token(auth_key)
            else:
                user_info = jwt.decode(auth_key, verify=False).get('data')
            self.user_id = user_info.get('user_id', None)
            self.username = user_info.get('username', None)
            self.nickname = user_info.get('nickname', None)
            self.email = user_info.get('email', None)
            self.is_super = user_info.get('is_superuser', False)

            if not self.user_id:
                raise HTTPError(401, 'auth failed 2')
            else:
                self.user_id = str(self.user_id)
                self.set_secure_cookie("user_id", self.user_id)
                self.set_secure_cookie("nickname", self.nickname)
                self.set_secure_cookie("username", self.username)
                self.set_secure_cookie("email", str(self.email))

        self.is_superuser = self.is_super
        ## 此处为示例， 如果通过API给个鉴权，则注释
        ### 如果不是超级管理员,开始鉴权
        # my_verify = MyVerify(self.user_id)
        # if self.is_super:
        #     # 没权限，就让跳到权限页面 0代表有权限，1代表没权限
        #     if not my_verify.get_verify(self.request.method, self.request.uri):
        #         '''如果没有权限，就刷新一次权限'''
        #         my_verify.write_verify()
        #
        #     if not my_verify.get_verify(self.request.method, self.request.uri):
        #         raise HTTPError(403, 'request forbidden!')

        ### 写入日志 改为网关收集
