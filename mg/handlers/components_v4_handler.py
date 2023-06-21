#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2018/11/2
Desc    : 解释个锤子
"""

import json
from libs.base_handler import BaseHandler
from websdk2.db_context import DBContextV2 as DBContext
from models.admin_model import Components, RolesComponents, Apps
from models.admin_schemas import get_components_list, get_components_list_for_role


class ComponentsHandler(BaseHandler):
    def get(self, *args, **kwargs):
        count, queryset = get_components_list(**self.params)

        return self.write(dict(code=0, result=True, msg="获取成功", count=count, data=queryset))

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        component_name = data.get('component_name')
        if not component_name:   return self.write(dict(code=-1, msg='不能为空'))

        with DBContext('w', None, True) as session:
            is_exist = session.query(Components).filter(Components.component_name == component_name).first()

            if is_exist:  return self.write(dict(code=-2, msg=f'{component_name}已存在'))
            session.add(Components(**data))

        return self.write(dict(code=0, msg='组件创建成功'))

    def put(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        comp_id = data.get('comp_id')
        component_name = data.get('component_name')
        app_code = data.get('app_code')

        if not comp_id: return self.write(dict(code=-1, msg='ID不能为空'))
        if not component_name: return self.write(dict(code=-2, msg='组件名称不能为空'))
        if '_index' in data: data.pop('_index')
        if '_rowKey' in data: data.pop('_rowKey')

        with DBContext('w', None, True) as session:
            is_exist = session.query(Components).filter(Components.comp_id != comp_id,
                                                        Components.component_name == component_name).first()

            if is_exist:  return self.write(dict(code=-2, msg=f'{component_name}已存在'))
            session.query(Components).filter(Components.comp_id == comp_id).update(data)

        return self.write(dict(code=0, msg='编辑成功'))

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        comp_id = data.get('comp_id', None)
        if not comp_id:  return self.write(dict(code=-1, msg='不能为空'))

        with DBContext('w', None, True) as session:
            session.query(Components).filter(Components.comp_id == comp_id).delete(synchronize_session=False)
            session.query(RolesComponents).filter(RolesComponents.comp_id == comp_id).delete(synchronize_session=False)

        return self.write(dict(code=0, msg='删除成功'))


class RoleCompHandler(BaseHandler):

    def get(self, *args, **kwargs):
        role_id = self.get_argument('role_id', default=None, strip=True)

        if not role_id:   return self.write(dict(code=-1, msg='角色不能为空'))

        data_list = get_components_list_for_role(int(role_id))
        return self.write(dict(code=0, msg='获取成功', data=data_list))

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        comp_list = data.get('comp_list', None)
        role_id = data.get('role_id', None)
        comp_list = list(set(comp_list))

        if not role_id:   return self.write(dict(code=-1, msg='角色不能为空'))

        if not comp_list:  return self.write(dict(code=-1, msg='选择的组件不能为空'))

        with DBContext('w', None, True) as session:
            new_comps = [RolesComponents(role_id=role_id, comp_id=i, status='0') for i in comp_list]
            session.add_all(new_comps)

        return self.write(dict(code=0, msg='组件加入角色成功'))

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        comp_list = data.get('comp_list', None)
        role_id = data.get('role_id', None)
        comp_list = list(set(comp_list))

        if not role_id:  return self.write(dict(code=-1, msg='角色不能为空'))

        if not comp_list: return self.write(dict(code=-1, msg='选择的组件不能为空'))

        ## 删除
        with DBContext('w', None, True) as session:
            session.query(RolesComponents).filter(RolesComponents.role_id == role_id,
                                                  RolesComponents.comp_id.in_(comp_list)).delete(
                synchronize_session=False)

        self.write(dict(code=0, msg='从角色中删除组件成功'))


comp_v4_urls = [
    (r"/v4/components/", ComponentsHandler, {"handle_name": "权限中心-组件管理"}),
    (r"/v4/role_comp/", RoleCompHandler, {"handle_name": "权限中心-组件角色"}),
]

if __name__ == "__main__":
    pass
