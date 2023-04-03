#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
from libs.base_handler import BaseHandler
from websdk2.cache_context import cache_conn
from websdk2.db_context import DBContextV2 as DBContext
from models.admin_schemas import sign_privilege, get_role_privilege, get_user_privilege, add_operation_log
from libs.resource_registration import Registration

FUNC_SUPPORT_TYPE = ["swagger", "manual"]
MENU_SUPPORT_TYPE = ["manual"]
COMP_SUPPORT_TYPE = ["manual"]


class RegistrationFuncHandler(BaseHandler):
    def post(self, *args, **kwargs):
        try:
            data = json.loads(self.request.body.decode("utf-8"))
        except Exception as e:
            return self.write(dict(code=-1, msg="数据格式有误"))

        register_type = data.get('register_type')
        if not register_type: return self.write(dict(code=-1, msg='注册方式不能为空'))
        if register_type not in FUNC_SUPPORT_TYPE:
            return self.write(dict(code=-2, msg='注册方式目前仅支持{0}'.format(','.join(FUNC_SUPPORT_TYPE))))

        res, msg = Registration(**data).register_func()

        return self.write(dict(code=0 if res else -3, msg=msg))


class RegistrationMenuHandler(BaseHandler):
    def post(self, *args, **kwargs):
        try:
            data = json.loads(self.request.body.decode("utf-8"))
        except Exception as e:
            return self.write(dict(code=-1, msg="数据格式有误"))

        register_type = data.get('register_type')
        if not register_type: return self.write(dict(code=-1, msg='注册方式不能为空'))
        if register_type not in MENU_SUPPORT_TYPE:
            return self.write(dict(code=-2, msg='注册方式目前仅支持{0}'.format(','.join(MENU_SUPPORT_TYPE))))

        res, msg = Registration(**data).register_menu()

        return self.write(dict(code=0 if res else -3, msg=msg))


class RegistrationCompHandler(BaseHandler):
    def post(self, *args, **kwargs):
        try:
            data = json.loads(self.request.body.decode("utf-8"))
        except Exception as e:
            return self.write(dict(code=-1, msg="数据格式有误"))

        register_type = data.get('register_type')
        if not register_type: return self.write(dict(code=-1, msg='注册方式不能为空'))
        if register_type not in COMP_SUPPORT_TYPE:
            return self.write(dict(code=-2, msg='注册方式目前仅支持{0}'.format(','.join(COMP_SUPPORT_TYPE))))

        res, msg = Registration(**data).register_compnent()

        return self.write(dict(code=0 if res else -3, msg=msg))


register_urls = [
    (r"/auth/v3/accounts/register/func/", RegistrationFuncHandler, {"handle_name": "注册-接口"}),
    (r"/auth/v3/accounts/register/menu/", RegistrationMenuHandler, {"handle_name": "注册-菜单"}),
    (r"/auth/v3/accounts/register/comp/", RegistrationCompHandler, {"handle_name": "注册-组件"}),
]

if __name__ == "__main__":
    pass
