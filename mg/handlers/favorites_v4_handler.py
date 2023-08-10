#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023年06月05日
Desc    : 用户收藏
"""

import json
from abc import ABC
from libs.base_handler import BaseHandler
from services.favorite_service import get_favorites_list, up_favorites, add_favorites, del_favorites


class FavoritesHandler(BaseHandler, ABC):
    def get(self, *args, **kwargs):
        key = self.get_argument('key', default=None, strip=True)  # 索引
        if not key:
            return self.write(dict(code=-1, msg="缺少关键字"))

        self.params['nickname'] = self.request_nickname
        count, queryset = get_favorites_list(**self.params)

        return self.write(dict(code=0, msg="获取成功", data=queryset))

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        data['nickname'] = self.request_nickname
        res = add_favorites(data)
        self.write(res)

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))

        res = del_favorites(data)
        self.write(res)


favorites_urls = [
    (r"/v4/favorites/", FavoritesHandler, {"handle_name": "PAAS-基础功能-公用收藏接口", "method": ["ALL"]}),

]

if __name__ == "__main__":
    pass
