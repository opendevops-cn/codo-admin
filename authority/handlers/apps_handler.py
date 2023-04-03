#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2018/11/2
Desc    : 应用管理
"""

import json
from libs.base_handler import BaseHandler
from websdk2.db_context import DBContextV2 as DBContext
from models.authority_model import Apps, RoleApp
from services.app_services import get_apps_list, get_app_list_v2


class AppsHandler(BaseHandler):
    def get(self, *args, **kwargs):
        self.params['nickname'] = self.nickname
        self.params['is_super'] = self.is_super
        count, queryset = get_app_list_v2(**self.params)
        return self.write(dict(code=0, result=True, msg="获取成功", count=count, data=queryset))

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        app_name = data.get('app_name', None)

        with DBContext('w', None, True) as session:
            is_exist = session.query(Apps).filter(Apps.app_name == app_name).first()
            if is_exist: return self.write(dict(code=-3, msg=f'{app_name}已存在'))

            session.add(Apps(**data))

        return self.write(dict(code=0, msg='创建成功'))

    def put(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        app_id = data.get('app_id')
        app_name = data.get('app_name')

        if not app_id: return self.write(dict(code=-1, msg='ID不能为空'))
        if not app_name: return self.write(dict(code=-2, msg='应用名称不能为空'))

        if '_index' in data: data.pop('_index')
        if '_rowKey' in data: data.pop('_rowKey')

        with DBContext('w', None, True) as session:
            is_exist = session.query(Apps).filter(Apps.app_id != app_id, Apps.app_name == app_name).first()
            if is_exist:  return self.write(dict(code=-3, msg=f'应用 "{app_name}" 已存在'))

            session.query(Apps).filter(Apps.app_id == app_id).update(data)

        return self.write(dict(code=0, msg='编辑成功'))

    def patch(self, *args, **kwargs):
        """禁用、启用"""

        return self.write(dict(code=0, msg="不支持禁用启用"))

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        app_id = data.get('app_id')

        if not app_id or not isinstance(app_id, int): return self.write(dict(code=-1, msg='ID不能为空，必须为int'))

        with DBContext('w', None, True) as session:
            session.query(Apps).filter(Apps.app_id == app_id).delete(synchronize_session=False)
            session.query(RoleApp).filter(RoleApp.app_id == app_id).delete(synchronize_session=False)
        return self.write(dict(code=0, msg='删除成功'))


class AppListHandler(BaseHandler):
    def get(self, *args, **kwargs):
        count, queryset = get_apps_list(**self.params)
        return self.write(dict(code=0, msg="获取成功", count=count, data=queryset))


apps_urls = [
    (r"/auth/v3/accounts/apps/", AppsHandler, {"handle_name": "权限中心-应用管理"}),
    (r"/auth/v3/accounts/app/list/", AppListHandler, {"handle_name": "权限中心-全部应用列表"}),

]

if __name__ == "__main__":
    pass
