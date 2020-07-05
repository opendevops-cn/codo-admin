#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
author : shenshuo
date   : 2020年4月11日
desc   : 资源组管理API
"""

import json
from libs.base_handler import BaseHandler
from models.resource_model import get_all_by_user, get_all_by_id, get_resource, create_resource, delete_resource, \
    resource_user, update_resource


class ResourceHandler(BaseHandler):
    def get(self):
        key = self.get_argument('key', default=None, strip=True)
        value = self.get_argument('value', default=None, strip=True)
        data_list = get_resource(key, value)
        return self.write(dict(code=0, msg='获取成功', data=data_list))

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        res = create_resource(data)

        self.write(res)

    def put(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        res = update_resource(data)
        self.write(res)

    ### 修改用户
    def patch(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        res = resource_user(data)
        self.write(res)

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        res = delete_resource(data)
        self.write(res)


class ResourceByUserHandler(BaseHandler):
    def get(self):
        nickname = self.get_argument('nickname', default=None, strip=True)
        expand = self.get_argument('expand', default=None, strip=True)
        if nickname:
            data_list = get_all_by_user(nickname)
        else:
            data_list = get_all_by_id(self.request_user_id)

        if expand: data_list = filter(lambda x: x.get('expand') == expand, data_list)
        return self.write(dict(code=0, msg='获取成功', data=data_list))


resource_urls = [
    (r"/v2/overall/resource/", ResourceHandler),
    (r"/v2/overall/resource/user/", ResourceHandler),
]

if __name__ == "__main__":
    pass
