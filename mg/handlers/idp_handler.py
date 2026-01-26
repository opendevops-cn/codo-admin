#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# @File    :   third_party_handler.py
# @Time    :   2026/01/22 18:00:14
# @Author  :   DongdongLiu
# @Version :   1.0
# @Desc    :   第三方平台用户处理器模块

from abc import ABC
from services.idp_service import build_department_tree

from libs.base_handler import BaseHandler


class DepartmentTreeHandler(BaseHandler, ABC):
    """组织架构树结构接口"""

    def get(self):
        provider = self.params.get("provider")
        if not provider:
            return self.write(dict(code=-1, msg="缺少参数: provider"))
        result = build_department_tree(provider=provider)
        self.write(result)


idp_urls = [
    (r"/v4/idp/department/tree/", DepartmentTreeHandler),
]