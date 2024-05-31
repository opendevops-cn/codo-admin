#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2018/11/2
Desc    : 应用管理
"""

import json
from abc import ABC
from libs.base_handler import BaseHandler
from websdk2.db_context import DBContextV2 as DBContext
from models.authority import RoleApps
from services.app_service import get_apps_list_for_main, get_apps_list_for_api, opt_obj, get_apps_list_for_role


class RoleAPPHandler(BaseHandler, ABC):
    """
    应用和角色关联
    TODO 未完成
    """

    def get(self, *args, **kwargs):
        role_id = self.get_argument('role_id', default=None, strip=True)

        if not role_id: return self.write(dict(code=-1, msg='角色不能为空'))

        data_list = get_apps_list_for_role(int(role_id))

        return self.write(dict(code=0, msg='获取成功', data=data_list))

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        role_id = data.get('role_id', None)
        app_list = data.get('app_list', [])
        app_list = list(set(app_list))

        if not role_id:   return self.write(dict(code=-1, msg='角色不能为空'))

        if not app_list: return self.write(dict(code=-1, msg='选择的应用不能为空'))

        with DBContext('w', None, True) as session:
            new_menus = [RoleApps(role_id=role_id, app_id=i) for i in app_list]
            session.add_all(new_menus)

        return self.write(dict(code=0, msg='应用加入角色成功'))

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        role_id = data.get('role_id', None)
        app_list = data.get('app_list', [])
        app_list = list(set(app_list))

        if not role_id: return self.write(dict(code=-1, msg='角色不能为空'))

        if not app_list: return self.write(dict(code=-2, msg='选择的应用不能为空'))

        # 删除
        with DBContext('w', None, True) as session:
            session.query(RoleApps).filter(RoleApps.role_id == role_id, RoleApps.app_id.in_(app_list)).delete(
                synchronize_session=False)

        self.write(dict(code=0, msg='从角色中删除菜单成功'))


class AppsV4Handler(BaseHandler, ABC):
    def get(self, *args, **kwargs):
        res = get_apps_list_for_api(**self.params)
        return self.write(res)

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        res = opt_obj.handle_add(data)

        self.write(res)

    def put(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        res = opt_obj.handle_update(data)

        self.write(res)

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        res = opt_obj.handle_delete(data)

        self.write(res)


class AppListHandler(BaseHandler, ABC):
    def get(self, *args, **kwargs):
        res = get_apps_list_for_main(**self.params)
        self.write(res)


apps_urls = [
    (r"/v4/apps/", AppsV4Handler, {"handle_name": "PAAS管理-应用管理", "method": ["ALL"]}),
    (r"/v4/role_app/", RoleAPPHandler, {"handle_name": "权限中心-应用角色管理", "method": ["ALL"]}),
    (r"/v4/apps/list/", AppListHandler, {"handle_name": "PAAS-基础功能-查看应用列表", "method": ["GET"]}),
    (r"/v4/na/apps/list/", AppListHandler, {"handle_name": "PAAS-基础功能-免认证查看应用列表", "method": ["GET"]}),

]

if __name__ == "__main__":
    pass
