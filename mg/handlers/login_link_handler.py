#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023/6/28
Desc    : 解释个锤子
"""

import json
from abc import ABC
from shortuuid import uuid
from libs.base_handler import BaseHandler
from services.link_service import opt_obj, get_link_list_for_api


class LinkHandler(BaseHandler, ABC):
    def get(self, *args, **kwargs):
        res = get_link_list_for_api(**self.params)

        return self.write(res)

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        data['code'] = uuid()
        res = opt_obj.handle_add(data)
        self.write(res)

    def put(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        if 'code' in data:
            del data['code']
        res = opt_obj.handle_update(data)
        self.write(res)

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        res = opt_obj.handle_delete(data)
        self.write(res)


link_v4_urls = [
    (r"/v4/login/link/", LinkHandler),
]

if __name__ == "__main__":
    pass
