#!/usr/bin/env python
# -*-coding:utf-8-*-

import shortuuid
from websdk.cache_context import cache_conn
from websdk.base_handler import BaseHandler as SDKBaseHandler
from tornado.web import HTTPError
from websdk.jwt_token import AuthToken, jwt


class BaseHandler(SDKBaseHandler):
    def __init__(self, *args, **kwargs):
        self.new_csrf_key = str(shortuuid.uuid())
        self.user_id, self.username, self.nickname, self.email, self.is_super = None, None, None, None, False
        self.is_superuser = self.is_super
        self.token_verify = True

        super(BaseHandler, self).__init__(*args, **kwargs)

    def get_params_dict(self):
        self.params = {k: self.get_argument(k) for k in self.request.arguments}
        if "auth_key" in self.params: self.params.pop('auth_key')

    def codo_csrf(self):
        # 验证客户端CSRF，如请求为GET，则不验证，否则验证。最后将写入新的key
        cache = cache_conn()

        # or self.request.headers.get('X-Gitlab-Token')
        if self.request.method in ("GET", "HEAD", "OPTIONS") or self.request.headers.get('Sdk-Method'):
            pass
        else:
            csrf_key = self.get_cookie('csrf_key')
            if not csrf_key:  raise HTTPError(402, 'csrf error need csrf key')
            result = cache.get(csrf_key)
            cache.delete(csrf_key)
            if isinstance(result, bytes): result = result.decode()
            if result != '1':   raise HTTPError(402, 'csrf error')
        cache.set(self.new_csrf_key, '1', ex=1800)
        self.set_cookie('csrf_key', self.new_csrf_key)

    def codo_login(self):
        ### 登陆验证
        auth_key = self.get_cookie('auth_key', None)
        if not auth_key:
            url_auth_key = self.get_argument('auth_key', default=None, strip=True)
            if url_auth_key: auth_key = bytes(url_auth_key, encoding='utf-8')

        if not auth_key: raise HTTPError(401, 'auth failed')

        if self.token_verify:
            auth_token = AuthToken()
            user_info = auth_token.decode_auth_token(auth_key)
        else:
            user_info = jwt.decode(auth_key, options={"verify_signature": False}).get('data')

        if not user_info: raise HTTPError(401, 'auth failed')

        self.user_id = user_info.get('user_id', None)
        self.username = user_info.get('username', None)
        self.nickname = user_info.get('nickname', None)
        self.email = user_info.get('email', None)
        self.is_super = user_info.get('is_superuser', False)

        if not self.user_id: raise HTTPError(401, 'auth failed')

        self.user_id = str(self.user_id)
        self.set_secure_cookie("user_id", self.user_id)
        self.set_secure_cookie("nickname", self.nickname)
        self.set_secure_cookie("username", self.username)
        self.set_secure_cookie("email", str(self.email))
        self.is_superuser = self.is_super

    def prepare(self):
        ### 验证客户端CSRF
        self.get_params_dict()
        self.codo_csrf()

        ### 登陆验证
        self.codo_login()
