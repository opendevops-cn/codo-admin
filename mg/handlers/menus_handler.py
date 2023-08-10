#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2018/11/2
Desc    : 
"""

import json
from libs.base_handler import BaseHandler
from websdk2.db_context import DBContextV2 as DBContext
from models.admin_model import Menus, RoleMenus, Apps
from models.admin_schemas import get_menu_list, get_menu_list_for_role, up_menu, add_menu, del_menu


class MenusHandler(BaseHandler):
    def get(self, *args, **kwargs):
        count, queryset = get_menu_list(**self.params)

        return self.write(dict(code=0, result=True, msg="获取成功", count=count, data=queryset))

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        app_code = data.get('app_code')
        if self.check_app_permission(app_code) is not True:
            return self.write(dict(code=-8, msg="You don't have permission to apply"))

        res = add_menu(data)
        self.write(res)

    def put(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        app_code = data.get('app_code')
        if self.check_app_permission(app_code) is not True:
            return self.write(dict(code=-8, msg="You don't have permission to apply"))

        res = up_menu(data)
        self.write(res)

    def patch(self, *args, **kwargs):
        """禁用、启用"""
        data = json.loads(self.request.body.decode("utf-8"))
        menu_id = data.get('menu_id', None)
        msg = '菜单不存在'

        if not menu_id:   return self.write(dict(code=-1, msg='不能为空'))

        if self.check_app_permission('', menu_id) is not True:
            return self.write(dict(code=-8, msg="You don't have permission to apply"))

        with DBContext('r') as session:
            menu_status = session.query(Menus.status).filter(Menus.menu_id == menu_id, Menus.status != 10).first()

        if not menu_status:   return self.write(dict(code=-2, msg=msg))

        if menu_status[0] == '0':
            msg = '禁用成功'
            new_status = '20'

        elif menu_status[0] == '20':
            msg = '启用成功'
            new_status = '0'
        else:
            msg = '状态不符合预期，删除'
            new_status = '10'

        with DBContext('w', None, True) as session:
            session.query(Menus).filter(Menus.menu_id == menu_id, Menus.status != '10').update(
                {Menus.status: new_status})

        return self.write(dict(code=0, msg=msg))

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        menu_id = data.get('menu_id')
        if self.check_app_permission('', menu_id) is not True:
            return self.write(dict(code=-8, msg="You don't have permission to apply"))
        res = del_menu(data)
        self.write(res)

    def check_app_permission(self, app_code, menu_id=None):
        if self.is_super: return True
        with DBContext('w', None, True) as session:
            if menu_id:
                app_code = session.query(Menus.app_code).filter(Menus.menu_id == menu_id).first()
                app_code = app_code[0]
            user_info = session.query(Apps.user_list).filter(Apps.status != '10', Apps.app_code == app_code).first()

        if not user_info: return False
        user_list = user_info[0]
        if not user_list or not isinstance(user_list, list): return False
        return True if self.nickname in user_list else False


class RoleMenuHandler(BaseHandler):
    """
    菜单和角色关联
    """

    def get(self, *args, **kwargs):
        role_id = self.get_argument('role_id', default=None, strip=True)

        if not role_id: return self.write(dict(code=-1, msg='角色不能为空'))

        data_list = get_menu_list_for_role(int(role_id))

        return self.write(dict(code=0, msg='获取成功', data=data_list))

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        role_id = data.get('role_id', None)
        menu_list = data.get('menu_list', None)
        menu_list = list(set(menu_list))

        if not role_id:   return self.write(dict(code=-1, msg='角色不能为空'))

        if not menu_list: return self.write(dict(code=-1, msg='选择的菜单不能为空'))

        with DBContext('w', None, True) as session:
            new_menus = [RoleMenus(role_id=role_id, menu_id=i, status='0') for i in menu_list]
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


# menus_urls = [
#     (r"/v3/accounts/menus/", MenusHandler, {"handle_name": "权限中心-菜单管理"}),
#     (r"/v3/accounts/role_menu/", RoleMenuHandler, {"handle_name": "权限中心-菜单角色"})
#
# ]

if __name__ == "__main__":
    pass
