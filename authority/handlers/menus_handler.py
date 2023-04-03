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
from models.authority_model import Menus, Apps, RoleMenu
from services.menu_services import get_menu_list, up_menu, add_menu, del_menu, get_menu_subtree


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

        if not menu_id: return self.write(dict(code=-1, msg='不能为空'))

        if self.check_app_permission('', menu_id) is not True:
            return self.write(dict(code=-8, msg="You don't have permission to apply"))

        with DBContext('r') as session:
            menu_status = session.query(Menus.status).filter(Menus.menu_id == menu_id, Menus.status != 10).first()

        if not menu_status: return self.write(dict(code=-2, msg=msg))

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
        with DBContext('w', None, True) as session:
            session.query(RoleMenu).filter(RoleMenu.menu_id == menu_id).delete(synchronize_session=False)
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


class MenusSubTreeHandler(BaseHandler):
    def get(self, *args, **kwargs):
        record_type = self.get_argument('record_type', default=None, strip=True)
        id = self.get_argument('id', default=None, strip=True)

        if not record_type: return self.write(dict(code=-1, msg='record type不能为空'))
        if record_type not in ["app", "menu"]: return self.write(dict(code=-2, msg='record type非法'))
        if not id: return self.write(dict(code=-3, msg='id不能为空'))

        count, queryset = get_menu_subtree(**self.params)
        return self.write(dict(code=0, result=True, msg="获取成功", count=count, data=queryset))


menus_urls = [
    (r"/auth/v3/accounts/menus/", MenusHandler, {"handle_name": "权限中心-菜单管理"}),
    (r"/auth/v3/accounts/menus/subtree/", MenusSubTreeHandler, {"handle_name": "权限中心-菜单子树"}),
]

if __name__ == "__main__":
    pass
