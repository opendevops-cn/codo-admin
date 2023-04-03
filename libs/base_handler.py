#!/usr/bin/env python
# -*-coding:utf-8-*-


from websdk2.base_handler import BaseHandler as SDKBaseHandler

class BaseHandler(SDKBaseHandler):
    def __init__(self, *args, **kwargs):
        super(BaseHandler, self).__init__(*args, **kwargs)
        self.token_verify = True
        self.tenant_filter = False

    def prepare(self):
        ### 获取url参数为字典
        self.get_params_dict()
        ### 验证客户端CSRF
        self.check_xsrf_cookie()
        self.xsrf_token

        ### 登陆验证
        self.codo_login()