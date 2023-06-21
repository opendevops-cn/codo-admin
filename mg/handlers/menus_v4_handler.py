#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2018/11/2
Desc    : 解释个锤子
"""

import json
from abc import ABC
from libs.base_handler import BaseHandler
from websdk2.db_context import DBContextV2 as DBContext
from models.authority import RoleMenus
from services.menu_service import get_menu_list_for_api, opt_obj, get_menu_list_for_role


class MenusHandler(BaseHandler, ABC):
    def get(self, *args, **kwargs):
        res = get_menu_list_for_api(**self.params)

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


class RoleMenuHandler(BaseHandler, ABC):
    """
    菜单和角色关联
    """

    def get(self, *args, **kwargs):
        role_id = self.get_argument('role_id', default=None, strip=True)

        if not role_id:
            return self.write(dict(code=-1, msg='角色不能为空'))

        data_list = get_menu_list_for_role(int(role_id))

        return self.write(dict(code=0, msg='获取成功', data=data_list))

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        role_id = data.get('role_id', None)
        menu_list = data.get('menu_list', None)
        menu_list = list(set(menu_list))

        if not role_id:
            return self.write(dict(code=-1, msg='角色不能为空'))

        if not menu_list:
            return self.write(dict(code=-1, msg='选择的菜单不能为空'))

        with DBContext('w', None, True) as session:
            new_menus = [RoleMenus(role_id=role_id, menu_id=i) for i in menu_list]
            session.add_all(new_menus)

        return self.write(dict(code=0, msg='菜单加入角色成功'))

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        role_id = data.get('role_id', None)
        menu_list = data.get('menu_list', None)
        menu_list = list(set(menu_list))

        if not role_id:   return self.write(dict(code=-1, msg='角色不能为空'))

        if not menu_list: return self.write(dict(code=-2, msg='选择的菜单不能为空'))

        ## 删除
        with DBContext('w', None, True) as session:
            session.query(RoleMenus).filter(RoleMenus.role_id == role_id, RoleMenus.menu_id.in_(menu_list)).delete(
                synchronize_session=False)

        self.write(dict(code=0, msg='从角色中删除菜单成功'))


menus_v4_urls = [
    (r"/v4/menus/", MenusHandler, {"handle_name": "权限中心-菜单管理"}),
    (r"/v4/role_menu/", RoleMenuHandler, {"handle_name": "权限中心-菜单角色"})

]

if __name__ == "__main__":
    pass
