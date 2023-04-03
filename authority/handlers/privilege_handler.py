#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
from libs.base_handler import BaseHandler
from websdk2.cache_context import cache_conn
from websdk2.db_context import DBContextV2 as DBContext
from services import add_operation_log
from services.privilege_services import sign_privilege, get_role_privilege, get_user_privilege, \
    get_role_privilege_transfer


class PrivilegeHandler(BaseHandler):
    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        raw_data = data.copy()
        role_id = data.get('role_id')
        if not role_id: return self.write(dict(code=-1, msg='角色不能为空'))

        res, msg = sign_privilege(**data)

        add_operation_log(dict(
            username=self.request_username,
            operation="角色授权",
            result=res,
            msg=msg,
            data=raw_data
        ))
        return self.write(dict(code=0 if res else -2, msg=msg))


class PrivilegeRoleHandler(BaseHandler):
    def get(self, *args, **kwargs):
        role_id = self.params.get('role_id')
        resource_list = self.params.get("resource_list")
        if not role_id: return self.write(dict(code=-1, msg='角色不能为空'))
        self.params["role_list"] = [int(role_id)]
        self.params["resource_list"] = [resource_list] if resource_list else []
        data = get_role_privilege(**self.params)
        return self.write(dict(code=0, result=True, msg="获取角色权限成功", data=data))


class PrivilegeUserHandler(BaseHandler):
    def get(self, *args, **kwargs):
        user_id = self.params.get('user_id')
        username = self.params.get('username')
        resource_list = self.params.get("resource_list")
        if not user_id and not username: return self.write(dict(code=-1, msg='用户不能为空'))
        self.params["resource_list"] = json.loads(resource_list) if resource_list else []
        data = get_user_privilege(**self.params)
        return self.write(dict(code=0, result=True, msg="获取用户权限成功", data=data))


class PrivilegeRoleTransferHandler(BaseHandler):
    def get(self, *args, **kwargs):
        role_id = self.params.get('role_id')
        resource_list = self.params.get("resource_list")
        if not role_id: return self.write(dict(code=-1, msg='角色不能为空'))
        self.params["role_list"] = [int(role_id)]
        self.params["resource_list"] = [resource_list] if resource_list else []
        data = get_role_privilege_transfer(**self.params)
        return self.write(dict(code=0, result=True, msg="获取角色权限成功", data=data))


privilege_urls = [
    (r"/auth/v3/accounts/privilege/", PrivilegeHandler, {"handle_name": "权限列表"}),
    (r"/auth/v3/accounts/privilege/role/", PrivilegeRoleHandler, {"handle_name": "权限列表-角色"}),
    (r"/auth/v3/accounts/privilege/user/", PrivilegeUserHandler, {"handle_name": "权限列表"}),
    (r"/auth/v3/accounts/privilege/role/transfer/", PrivilegeRoleTransferHandler, {"handle_name": "权限列表-角色-穿梭框"}),
]

if __name__ == "__main__":
    pass
