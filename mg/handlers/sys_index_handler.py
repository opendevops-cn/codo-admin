#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2024年12月02日
Desc    : 首页卡片
"""

import json
from abc import ABC
from libs.base_handler import BaseHandler
from services.index_service import get_step_list, up_step, add_step, del_step, get_service_dict, get_service_list,\
    add_service, up_service, del_service, opt_server_list_obj, get_service_categories


class IndexStepHandler(BaseHandler, ABC):
    def get(self, *args, **kwargs):
        res = get_step_list()
        return self.write(res)

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        res = add_step(data)
        self.write(res)

    def put(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        res = up_step(data)
        self.write(res)

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        res = del_step(data)
        self.write(res)


class ServiceCategoriesHandler(BaseHandler, ABC):
    def get(self, *args, **kwargs):
        res = get_service_categories()
        return self.write(res)

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        res = opt_server_list_obj.handle_add(data)
        self.write(res)

    def put(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        res = opt_server_list_obj.handle_update(data)
        self.write(res)

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        res = opt_server_list_obj.handle_delete(data)
        self.write(res)


class IndexServiceHandler(BaseHandler, ABC):
    def get(self, *args, **kwargs):
        res = get_service_list()
        return self.write(res)

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        res = add_service(data)
        self.write(res)

    def put(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        res = up_service(data)
        self.write(res)

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        res = del_service(data)
        self.write(res)


class IndexStep(BaseHandler, ABC):
    def get(self, *args, **kwargs):
        res = get_step_list()
        return self.write(res)


class ServiceCategories(BaseHandler, ABC):
    def get(self, *args, **kwargs):
        res = get_service_categories()
        return self.write(res)


class IndexService(BaseHandler, ABC):
    def get(self, *args, **kwargs):
        res = get_service_dict()
        return self.write(res)


index_step_urls = [
    (r"/v4/ops-step-service/", IndexStepHandler, {"handle_name": "PAAS-基础功能-首页步骤管理", "method": ["ALL"]}),
    (r"/v4/ops-service-categories/", ServiceCategoriesHandler, {"handle_name": "PAAS-基础功能-首页服务列表", "method": ["ALL"]}),
    (r"/v4/ops-index-service/", IndexServiceHandler, {"handle_name": "PAAS-基础功能-首页服务管理", "method": ["ALL"]}),
    (r"/v4/na/index-step/", IndexStep, {"handle_name": "PAAS-基础功能-首页步骤", "method": ["GET"]}),  # 免认证
    (r"/v4/na/index-service-categories/", ServiceCategories, {"handle_name": "PAAS-基础功能-首页服务定制表", "method": ["GET"]}),
    (r"/v4/na/index-service/", IndexService, {"handle_name": "PAAS-基础功能-首页服务", "method": ["GET"]})  # 免认证
]

if __name__ == "__main__":
    pass
