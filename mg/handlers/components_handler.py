#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2018/11/2
Desc    : 组件
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

        if self.check_app_permission(component_name) is not True:
            return self.write(dict(code=-8, msg="You don't have permission to apply"))

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

        if self.check_app_permission(app_code, comp_id) is not True:
            return self.write(dict(code=-8, msg="You don't have permission to apply"))

        if '_index' in data: data.pop('_index')
        if '_rowKey' in data: data.pop('_rowKey')

        with DBContext('w', None, True) as session:
            is_exist = session.query(Components).filter(Components.comp_id != comp_id,
                                                        Components.component_name == component_name).first()

            if is_exist:  return self.write(dict(code=-2, msg=f'{component_name}已存在'))
            session.query(Components).filter(Components.comp_id == comp_id).update(data)

        return self.write(dict(code=0, msg='编辑成功'))

    def patch(self, *args, **kwargs):
        """禁用、启用"""
        data = json.loads(self.request.body.decode("utf-8"))
        comp_id = data.get('comp_id')
        msg = '组件不存在'

        if not comp_id:   return self.write(dict(code=-1, msg='ID不能为空'))

        if self.check_app_permission('', comp_id) is not True:
            return self.write(dict(code=-8, msg="You don't have permission to apply"))

        with DBContext('r') as session:
            comp_status = session.query(Components.status).filter(Components.comp_id == comp_id,
                                                                  Components.status != 10).first()

        if not comp_status:  return self.write(dict(code=-2, msg=msg))

        if comp_status[0] == '0':
            msg = '禁用成功'
            new_status = '20'

        elif comp_status[0] == '20':
            msg = '启用成功'
            new_status = '0'
        else:
            msg = '状态不符合预期，删除'
            new_status = '10'

        with DBContext('w', None, True) as session:
            session.query(Components).filter(Components.comp_id == comp_id, Components.status != 10).update(
                {Components.status: new_status})

        return self.write(dict(code=0, msg=msg))

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        comp_id = data.get('comp_id', None)
        if not comp_id:  return self.write(dict(code=-1, msg='不能为空'))

        if self.check_app_permission('', comp_id) is not True:
            return self.write(dict(code=-8, msg="You don't have permission to apply"))

        with DBContext('w', None, True) as session:
            session.query(Components).filter(Components.comp_id == comp_id).delete(synchronize_session=False)
            session.query(RolesComponents).filter(RolesComponents.comp_id == comp_id).delete(synchronize_session=False)

        return self.write(dict(code=0, msg='删除成功'))

    def check_app_permission(self, app_code, comp_id=None):
        if self.is_super: return True
        with DBContext('w', None, True) as session:
            if comp_id:
                app_code = session.query(Components.app_code).filter(Components.comp_id == comp_id).first()
                app_code = app_code[0]
            user_info = session.query(Apps.user_list).filter(Apps.status != '10', Apps.app_code == app_code).first()

        if not user_info: return False
        user_list = user_info[0]
        if not user_list or not isinstance(user_list, list): return False
        return True if self.nickname in user_list else False


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


components_urls = [
    (r"/v3/accounts/components/", ComponentsHandler, {"handle_name": "权限中心-组件管理"}),
    (r"/v3/accounts/role_comp/", RoleCompHandler, {"handle_name": "权限中心-组件角色"}),
]

if __name__ == "__main__":
    pass
