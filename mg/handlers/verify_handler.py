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


class VerifyHandler(RequestHandler):

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        user_id = data.get('user_id', None)
        secret_key = data.get('secret_key', None)
        is_superuser = data.get('is_superuser', False)
        if secret_key != my_settings.get('secret_key'):
            return self.write(dict(code=-1, msg='secret key error'))

        if not user_id:
            return self.write(dict(code=-2, msg='auth failed'))

        else:
            my_verify = MyVerify(str(user_id), is_superuser)
            my_verify.write_verify()
        return self.write(dict(code=0, msg='缓存成功'))


sso_urls = [
    (r"/v2/accounts/verify/", VerifyHandler),
]

if __name__ == "__main__":
    pass
