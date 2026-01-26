#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Author  : AI Assistant
Date    : 2026/01/23
Desc    : 角色与身份提供商部门关联管理
"""

import json
from abc import ABC
from libs.base_handler import BaseHandler
from services.role_idp_department_service import (
    get_role_idp_departments,
    bind_role_idp_departments,
)


class RoleIdpDepartmentHandler(BaseHandler, ABC):
    """角色与身份提供商部门关联处理器"""

    def get(self, *args, **kwargs):
        """
        查询角色绑定的身份提供商部门
        参数: role_id - 角色ID
        """
        role_id = self.get_argument("role_id", default=None, strip=True)

        if not role_id:
            return self.write(dict(code=-1, msg="角色ID不能为空"))

        res = get_role_idp_departments(role_id=role_id)
        return self.write(res)

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        role_id = data.get("role_id")
        idp_department_ids = data.get("idp_department_ids")

        res = bind_role_idp_departments(
            role_id=role_id, idp_department_ids=idp_department_ids
        )
        return self.write(res)


role_idp_department_urls = [
    (
        r"/v4/role/idp_department/",
        RoleIdpDepartmentHandler,
        {"handle_name": "权限中心-角色身份提供商部门管理", "method": ["GET", "POST"]},
    )
]


if __name__ == "__main__":
    pass
