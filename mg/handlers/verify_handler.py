#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
author : shenshuo
date   : 2017年11月20日15:52:07
role   : 缓存权限
"""

import json
from tornado.web import RequestHandler
from libs.my_verify import MyVerify
from settings import settings as my_settings


# class SsoHandler(RequestHandler):
#     def get(self, *args, **kwargs):
#         return self.write(dict(status=-1, msg='请求方法错误'))
#
#     def post(self, *args, **kwargs):
#         data = json.loads(self.request.body.decode("utf-8"))
#         auth_key = data.get('auth_key', None)
#         method = data.get('method', None)
#         uri = data.get('uri', None)
#
#         if not method or not uri:
#             return self.write(dict(status=-5, msg='参数不完整'))
#
#         if not auth_key:
#             self.set_status(401)
#             return self.write(dict(status=-1, msg='没有登陆'))
#
#         else:
#             auth_token = AuthToken()
#             user_info = auth_token.decode_auth_token(auth_key)
#             user_id = user_info.get('user_id', None)
#             username = user_info.get('username', None)
#             nickname = user_info.get('nickname', None)
#
#         if not user_id:
#             self.set_status(401)
#             return self.write(dict(status=-2, msg='没有登陆'))
#
#         my_verify = MyVerify(user_id)
#
#         if not is_superuser(user_id):
#
#             # 没权限，就让跳到权限页面 0代表有权限，1代表没权限
#             if my_verify.get_verify(method, uri) != 0:
#                 '''如果没有权限，就刷新一次权限'''
#                 my_verify.write_verify()
#
#             if my_verify.get_verify(method, uri) != 0:
#                 self.set_status(403)
#                 return self.write(dict(status=-3, msg='没有权限'))
#
#         return self.write(dict(status=0, user_id=user_id, username=username, nickname=nickname))


class VerifyHandler(RequestHandler):

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        user_id = data.get('user_id', None)
        secret_key = data.get('secret_key', None)
        if secret_key != my_settings.get('secret_key'):
            return self.write(dict(code=-1, msg='secret key error'))

        if not user_id:
            return self.write(dict(code=-2, msg='auth failed'))

        else:
            my_verify = MyVerify(str(user_id))
            my_verify.write_verify()
        return self.write(dict(code=0, msg='缓存成功'))


sso_urls = [
    # (r"/v1/accounts/sso/", SsoHandler),
    (r"/v2/accounts/verify/", VerifyHandler),
]

if __name__ == "__main__":
    pass
