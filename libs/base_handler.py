#!/usr/bin/env python
# -*-coding:utf-8-*-

import shortuuid
from websdk.cache import get_cache
from websdk.base_handler import BaseHandler as SDKBaseHandler
from tornado.web import HTTPError
from websdk.jwt_token import AuthToken
from .my_verify import MyVerify


class BaseHandler(SDKBaseHandler):
    def __init__(self, *args, **kwargs):
        self.new_csrf_key = str(shortuuid.uuid())
        self.user_id = None
        self.username = None
        self.nickname = None
        self.is_super = False
        self.is_superuser = self.is_super

        super(BaseHandler, self).__init__(*args, **kwargs)

    def prepare(self):

        # 验证客户端CSRF，如请求为GET，则不验证，否则验证。最后将写入新的key
        cache = get_cache()
        if self.request.method != 'GET':
            csrf_key = self.get_cookie('csrf_key')
            pipeline = cache.get_pipeline()
            result = cache.get(csrf_key, private=False, pipeline=pipeline)
            cache.delete(csrf_key, private=False, pipeline=pipeline)
            if result != '1':
                raise HTTPError(400, 'csrf error')

        cache.set(self.new_csrf_key, 1, expire=1800, private=False)
        self.set_cookie('csrf_key', self.new_csrf_key)

        ### 登陆验证
        auth_key = self.get_cookie('auth_key', None)
        if not auth_key:
            # 没登录，就让跳到登陆页面
            raise HTTPError(401, 'auth failed 1')

        else:
            auth_token = AuthToken()
            user_info = auth_token.decode_auth_token(auth_key)
            self.user_id = user_info.get('user_id', None)
            self.username = user_info.get('username', None)
            self.nickname = user_info.get('nickname', None)
            self.is_super = user_info.get('is_superuser', False)

            if not self.user_id:
                raise HTTPError(401, 'auth failed 2')
            else:
                self.user_id = str(self.user_id)
                self.set_secure_cookie("user_id", self.user_id)
                self.set_secure_cookie("nickname", self.nickname)
                self.set_secure_cookie("username", self.username)

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

    # def set_default_headers(self):
    #     self.set_header("Access-Control-Allow-Origin", "*")
    #     self.set_header("Access-Control-Allow-Headers", "x-requested-with,access_token")
    #     self.set_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS, DELETE, PUT, PATCH")
    #     self.set_header("Access-Control-Max-Age", "3600")
