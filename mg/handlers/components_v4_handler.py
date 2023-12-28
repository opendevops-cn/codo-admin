#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2018/11/2
Desc    : 解释个锤子
"""

# TODO 未完成
import json
from abc import ABC
from libs.base_handler import BaseHandler
from websdk2.db_context import DBContextV2 as DBContext
from models.authority import RolesComponents
from services.component_services import get_component_list_for_api, get_component_list_for_role, opt_obj


class ComponentsHandler(BaseHandler, ABC):
    def get(self, *args, **kwargs):
        res = get_component_list_for_api(**self.params)

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
            session.query(RolesComponents).filter(RolesComponents.comp_id.in_(id_list)).delete(
                synchronize_session=False)

        self.write(res)


class CompListHandler(BaseHandler, ABC):
    def get(self, *args, **kwargs):
        res = get_component_list_for_api(**self.params)

        return self.write(res)


class RoleCompHandler(BaseHandler, ABC):

    def get(self, *args, **kwargs):
        role_id = self.get_argument('role_id', default=None, strip=True)

        if not role_id:
            return self.write(dict(code=-1, msg='角色不能为空'))

        data_list = get_component_list_for_role(int(role_id))
        return self.write(dict(code=0, msg='获取成功', data=data_list))

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        role_id = data.get('role_id', None)
        comp_list = data.get('comp_list', None)
        comp_list = list(set(comp_list))

        if not role_id:
            return self.write(dict(code=-1, msg='角色不能为空'))

        if not comp_list:
            return self.write(dict(code=-1, msg='选择的权限不能为空'))

        with DBContext('w', None, True) as session:
            new_funcs = [RolesComponents(role_id=role_id, comp_id=i) for i in comp_list]
            session.add_all(new_funcs)

        return self.write(dict(code=0, msg='权限加入角色成功'))

    def patch(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        comp_id = data.get('comp_id', None)
        role_id = data.get('role_id', None)

        if not comp_id or not role_id:
            return self.write(dict(code=-1, msg='不能为空'))

        with DBContext('w', None, True) as session:
            is_exist = session.query(RolesComponents.id).filter(RolesComponents.comp_id == comp_id,
                                                                RolesComponents.role_id == role_id).first()

            if not is_exist:
                session.add(RolesComponents(role_id=role_id, comp_id=comp_id))
                return self.write(dict(code=0, msg='添加组件权限成功'))
            else:
                session.query(RolesComponents).filter(RolesComponents.role_id == role_id,
                                                      RolesComponents.comp_id == comp_id).delete(
                    synchronize_session=False)
            return self.write(dict(code=0, msg='删除组件权限成功'))

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        comp_list = data.get('comp_list', None)
        role_id = data.get('role_id', None)
        comp_list = list(set(comp_list))

        if not role_id:
            return self.write(dict(code=-1, msg='角色不能为空'))

        if not comp_list:
            return self.write(dict(code=-1, msg='选择的组件不能为空'))

        # 删除
        with DBContext('w', None, True) as session:
            session.query(RolesComponents).filter(RolesComponents.role_id == role_id,
                                                  RolesComponents.comp_id.in_(comp_list)).delete(
                synchronize_session=False)

        self.write(dict(code=0, msg='从角色中删除组件成功'))


comp_v4_urls = [
    (r"/v4/components/", ComponentsHandler, {"handle_name": "权限中心-组件管理", "method": ["ALL"]}),
    (r"/v4/role_comp/", RoleCompHandler, {"handle_name": "权限中心-组件权限角色管理", "method": ["ALL"]}),
    (r"/v4/comp/list/", CompListHandler, {"handle_name": "权限中心-查看组件列表", "method": ["GET"]}),
]

if __name__ == "__main__":
    pass
