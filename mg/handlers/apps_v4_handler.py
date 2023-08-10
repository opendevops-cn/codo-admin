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
from models.admin_schemas import get_apps_list, get_apps_list_for_role
from services.app_service import get_apps_list_for_main, get_apps_list_for_api, opt_obj


# class AppsHandler(BaseHandler, ABC):
#     def get(self, *args, **kwargs):
#         self.params['nickname'] = self.nickname
#         self.params['is_super'] = self.is_super
#         count, queryset = get_apps_list_for_api(**self.params)
#         self.write(dict(code=0, result=True, msg="获取成功", count=count, data=queryset))
#
#     def post(self, *args, **kwargs):
#         data = json.loads(self.request.body.decode("utf-8"))
#         app_name = data.get('app_name', None)
#
#         with DBContext('w', None, True) as session:
#             is_exist = session.query(Apps).filter(Apps.app_name == app_name).first()
#             if is_exist:  return self.write(dict(code=-3, msg=f'{app_name}已存在'))
#
#             session.add(Apps(**data))
#
#         return self.write(dict(code=0, msg='创建成功'))
#
#     def put(self, *args, **kwargs):
#         data = json.loads(self.request.body.decode("utf-8"))
#         app_id = data.get('app_id')
#         app_name = data.get('app_name')
#
#         if not app_id: return self.write(dict(code=-1, msg='ID不能为空'))
#         if not app_name: return self.write(dict(code=-2, msg='应用名称不能为空'))
#
#         if '_index' in data: data.pop('_index')
#         if '_rowKey' in data: data.pop('_rowKey')
#
#         with DBContext('w', None, True) as session:
#             is_exist = session.query(Apps).filter(Apps.app_id != app_id, Apps.app_name == app_name).first()
#             if is_exist:  return self.write(dict(code=-3, msg=f'应用 "{app_name}" 已存在'))
#
#             session.query(Apps).filter(Apps.app_id == app_id).update(data)
#
#         return self.write(dict(code=0, msg='编辑成功'))
#
#     def patch(self, *args, **kwargs):
#         """禁用、启用"""
#
#         return self.write(dict(code=0, msg="不支持禁用启用"))
#
#     def delete(self, *args, **kwargs):
#         data = json.loads(self.request.body.decode("utf-8"))
#         app_id = data.get('app_id')
#
#         if not app_id or not isinstance(app_id, int):  return self.write(dict(code=-1, msg='ID不能为空，必须为int'))
#
#         with DBContext('w', None, True) as session:
#             session.query(Apps).filter(Apps.app_id == app_id).delete(synchronize_session=False)
#             session.query(RoleApps).filter(RoleApps.app_id == app_id).delete(synchronize_session=False)
#
#         return self.write(dict(code=0, msg='删除成功'))
#
#
class RoleMenuHandler(BaseHandler, ABC):
    """
    应用和角色关联
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
            new_menus = [RoleApps(role_id=role_id, app_id=i, status='0') for i in app_list]
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
    (r"/v4/role_app/", RoleMenuHandler, {"handle_name": "权限中心-应用角色管理", "method": ["ALL"]}),
    (r"/v4/apps/list/", AppListHandler, {"handle_name": "PAAS-基础功能-查看应用列表", "method": ["GET"]}),

]

if __name__ == "__main__":
    pass
