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
from websdk.db_context import DBContext
from models.admin import Menus, RoleMenus, model_to_dict


class MenusHandler(BaseHandler):
    def get(self, *args, **kwargs):
        key = self.get_argument('key', default=None, strip=True)
        value = self.get_argument('value', default=None, strip=True)
        menu_list = []
        with DBContext('r') as session:
            if key and value:
                count = session.query(Menus).filter(Menus.status != '10').filter_by(**{key: value}).count()
                menu_info = session.query(Menus).filter(Menus.status != '10').filter_by(**{key: value}).order_by(
                    Menus.menu_id).all()
            else:
                count = session.query(Menus).filter(Menus.status != '10').count()
                menu_info = session.query(Menus).filter(Menus.status != '10').order_by(Menus.menu_id).all()

        for msg in menu_info:
            data_dict = model_to_dict(msg)
            menu_list.append(data_dict)

        return self.write(dict(code=0, msg='获取成功', data=menu_list, count=count))

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        menu_name = data.get('menu_name', None)

        if not menu_name:
            return self.write(dict(code=-1, msg='不能为空'))

        with DBContext('r') as session:
            is_exist = session.query(Menus.menu_id).filter(Menus.menu_name == menu_name).first()

        if is_exist:
            return self.write(dict(code=-3, msg='"{}"已存在'.format(menu_name)))

        with DBContext('w', None, True) as session:
            session.add(Menus(menu_name=menu_name, status='0'))

        return self.write(dict(code=0, msg='菜单创建成功'))

    def put(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        menu_id = data.get('menu_id', None)
        menu_name = data.get('menu_name', None)

        if not menu_id or not menu_name:
            return self.write(dict(code=-1, msg='不能为空'))

        with DBContext('w', None, True) as session:
            session.query(Menus).filter(Menus.menu_id == int(menu_id)).update({Menus.menu_name: menu_name})

        return self.write(dict(code=0, msg='菜单编辑成功'))

    def patch(self, *args, **kwargs):
        """禁用、启用"""
        data = json.loads(self.request.body.decode("utf-8"))
        menu_id = data.get('menu_id', None)
        msg = '菜单不存在'

        if not menu_id:
            return self.write(dict(code=-1, msg='不能为空'))

        with DBContext('r') as session:
            menu_status = session.query(Menus.status).filter(Menus.menu_id == menu_id, Menus.status != 10).first()
        if not menu_status:
            return self.write(dict(code=-2, msg=msg))

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
            session.query(Menus).filter(Menus.menu_id == menu_id, Menus.status != 10).update({Menus.status: new_status})

        return self.write(dict(code=0, msg=msg))

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        menu_id = data.get('menu_id', None)
        if not menu_id:
            return self.write(dict(code=-1, msg='不能为空'))

        with DBContext('w', None, True) as session:
            session.query(Menus).filter(Menus.menu_id == menu_id).delete(synchronize_session=False)
            session.query(RoleMenus).filter(RoleMenus.menu_id == menu_id).delete(synchronize_session=False)

        return self.write(dict(code=0, msg='删除成功'))


class RoleMenuHandler(BaseHandler):
    """
    菜单和角色关联
    """

    def get(self, *args, **kwargs):
        role_id = self.get_argument('role_id', default=1, strip=True)
        data_list = []

        if not role_id:
            return self.write(dict(code=-1, msg='角色不能为空'))

        with DBContext('r') as session:
            role_menu = session.query(Menus).outerjoin(RoleMenus, Menus.menu_id == RoleMenus.menu_id).filter(
                RoleMenus.role_id == role_id, RoleMenus.status == '0', Menus.status == '0').all()

        for msg in role_menu:
            menu_dict = {}
            data_dict = model_to_dict(msg)
            menu_dict["menu_name"] = data_dict["menu_name"]
            menu_dict["menu_id"] = data_dict["menu_id"]
            data_list.append(menu_dict)

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
            new_menus = [RoleMenus(role_id=role_id, menu_id=i, status='0') for i in menu_list]
            session.add_all(new_menus)

        return self.write(dict(code=0, msg='菜单加入角色成功'))

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        role_id = data.get('role_id', None)
        menu_list = data.get('menu_list', None)
        menu_list = list(set(menu_list))

        if not role_id:
            return self.write(dict(code=-1, msg='角色不能为空'))

        if not menu_list:
            return self.write(dict(code=-1, msg='选择的菜单不能为空'))

        ## 删除
        with DBContext('w', None, True) as session:
            session.query(RoleMenus).filter(RoleMenus.role_id == role_id, RoleMenus.menu_id.in_(menu_list)).delete(
                synchronize_session=False)

        self.write(dict(code=0, msg='从角色中删除菜单成功'))


menus_urls = [
    (r"/v2/accounts/role_menu/", RoleMenuHandler),
    (r"/v2/accounts/menus/", MenusHandler),

]

if __name__ == "__main__":
    pass
