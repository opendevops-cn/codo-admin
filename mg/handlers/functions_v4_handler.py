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
from models.authority import RoleFunctions
from services.func_services import get_func_list_for_api, opt_obj, get_func_list_for_role


class FuncHandler(BaseHandler, ABC):
    def get(self, *args, **kwargs):
        res = get_func_list_for_api(**self.params)

        return self.write(res)

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        res = opt_obj.handle_add(data)
        data['menu_id'] = 1
        self.write(res)

    def put(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        data['menu_id'] = 1
        res = opt_obj.handle_update(data)
        self.write(res)

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        id_list = data.get('id_list')
        res = opt_obj.handle_delete(data)

        with DBContext('w', None, True) as session:
            session.query(RoleFunctions).filter(RoleFunctions.func_id.in_(id_list)).delete(synchronize_session=False)

        self.write(res)


class FuncListHandler(BaseHandler, ABC):
    def get(self, *args, **kwargs):
        res = get_func_list_for_api(**self.params)

        return self.write(res)


class RoleFuncHandler(BaseHandler, ABC):

    def get(self, *args, **kwargs):
        role_id = self.get_argument('role_id', default=None, strip=True)

        if not role_id:
            return self.write(dict(code=-1, msg='角色不能为空'))

        data_list = get_func_list_for_role(int(role_id))
        return self.write(dict(code=0, msg='获取成功', data=data_list))

    def patch(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        func_id = data.get('func_id', None)
        role_id = data.get('role_id', None)

        if not func_id or not role_id:
            return self.write(dict(code=-1, msg='不能为空'))

        with DBContext('w', None, True) as session:
            is_exist = session.query(RoleFunctions.id).filter(RoleFunctions.func_id == func_id,
                                                              RoleFunctions.role_id == role_id).first()

            if not is_exist:
                session.add(RoleFunctions(role_id=role_id, func_id=func_id))
                return self.write(dict(code=0, msg='添加后端权限成功'))
            else:
                session.query(RoleFunctions).filter(RoleFunctions.role_id == role_id,
                                                    RoleFunctions.func_id == func_id).delete(synchronize_session=False)
            return self.write(dict(code=0, msg='删除后端权限成功'))

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        role_id = data.get('role_id', None)
        func_list = data.get('func_list', None)
        func_list = list(set(func_list))

        if not role_id:  return self.write(dict(code=-1, msg='角色不能为空'))

        if not func_list: return self.write(dict(code=-1, msg='选择的权限不能为空'))

        with DBContext('w', None, True) as session:
            new_funcs = [RoleFunctions(role_id=role_id, func_id=i) for i in func_list]
            session.add_all(new_funcs)

        return self.write(dict(code=0, msg='权限加入角色成功'))

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        role_id = data.get('role_id', None)
        func_list = data.get('func_list', None)
        func_list = list(set(func_list))

        if not role_id:   return self.write(dict(code=-1, msg='角色不能为空'))

        if not func_list: return self.write(dict(code=-1, msg='选择的权限不能为空'))

        # 删除
        with DBContext('w', None, True) as session:
            session.query(RoleFunctions).filter(RoleFunctions.role_id == role_id,
                                                RoleFunctions.func_id.in_(func_list)).delete(synchronize_session=False)

        self.write(dict(code=0, msg='从角色中删除权限成功'))


func_v4_urls = [
    (r"/v4/role_func/", RoleFuncHandler, {"handle_name": "权限中心-接口权限角色管理", "method": ["ALL"]}),
    (r"/v4/func/", FuncHandler, {"handle_name": "权限中心-接口权限管理", "method": ["ALL"]}),
    (r"/v4/func/list/", FuncListHandler, {"handle_name": "权限中心-查看接口权限列表", "method": ["GET"]}),

]

if __name__ == "__main__":
    pass
