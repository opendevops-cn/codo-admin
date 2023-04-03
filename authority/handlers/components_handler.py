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
from models.authority_model import Components, Apps, RoleComponent
from services.component_services import get_components_list, get_component_subtree, get_components_list_tansfer


class ComponentsHandler(BaseHandler):
    def get(self, *args, **kwargs):
        # 获取树形组件
        count, queryset = get_components_list(**self.params)
        return self.write(dict(code=0, result=True, msg="获取成功",  count=count, data=queryset))

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        component_name = data.get('component_name')
        if not component_name: return self.write(dict(code=-1, msg='不能为空'))

        if self.check_app_permission(component_name) is not True:
            return self.write(dict(code=-8, msg="You don't have permission to apply"))

        with DBContext('w', None, True) as session:
            is_exist = session.query(Components).filter(Components.component_name == component_name).first()

            if is_exist: return self.write(dict(code=-2, msg=f'{component_name}已存在'))
            session.add(Components(**data))

        return self.write(dict(code=0, msg='组件创建成功'))

    def put(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        component_id = data.get('component_id')
        component_name = data.get('component_name')
        app_code = data.get('app_code')

        if not component_id: return self.write(dict(code=-1, msg='ID不能为空'))
        if not component_name: return self.write(dict(code=-2, msg='组件名称不能为空'))

        if self.check_app_permission(app_code, component_id) is not True:
            return self.write(dict(code=-8, msg="You don't have permission to apply"))

        if '_index' in data: data.pop('_index')
        if '_rowKey' in data: data.pop('_rowKey')

        with DBContext('w', None, True) as session:
            is_exist = session.query(Components).filter(Components.component_id != component_id,
                                                        Components.component_name == component_name).first()

            if is_exist:  return self.write(dict(code=-2, msg=f'{component_name}已存在'))
            session.query(Components).filter(Components.component_id == component_id).update(data)

        return self.write(dict(code=0, msg='编辑成功'))

    def patch(self, *args, **kwargs):
        """禁用、启用"""
        data = json.loads(self.request.body.decode("utf-8"))
        component_id = data.get('component_id')
        msg = '组件不存在'

        if not component_id: return self.write(dict(code=-1, msg='ID不能为空'))

        if self.check_app_permission('', component_id) is not True:
            return self.write(dict(code=-8, msg="You don't have permission to apply"))

        with DBContext('r') as session:
            comp_status = session.query(Components.status).filter(Components.component_id == component_id,
                                                                  Components.status != 10).first()

        if not comp_status: return self.write(dict(code=-2, msg=msg))

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
            session.query(Components).filter(Components.component_id == component_id, Components.status != 10).update(
                {Components.status: new_status})

        return self.write(dict(code=0, msg=msg))

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        component_id = data.get('component_id', None)
        if not component_id:  return self.write(dict(code=-1, msg='不能为空'))

        if self.check_app_permission('', component_id) is not True:
            return self.write(dict(code=-8, msg="You don't have permission to apply"))

        with DBContext('w', None, True) as session:
            session.query(Components).filter(Components.component_id == component_id).delete(synchronize_session=False)
            session.query(RoleComponent).filter(RoleComponent.component_id == component_id).delete(synchronize_session=False)

        return self.write(dict(code=0, msg='删除成功'))

    def check_app_permission(self, app_code, component_id=None):
        """app管理员有权更改"""
        if self.is_super: return True
        with DBContext('w', None, True) as session:
            if component_id:
                app_code = session.query(Components.app_code).filter(Components.component_id == component_id).first()
                app_code = app_code[0]
            user_info = session.query(Apps.user_list).filter(Apps.status != '10', Apps.app_code == app_code).first()

        if not user_info: return False
        user_list = user_info[0]
        if not user_list or not isinstance(user_list, list): return False
        return True if self.nickname in user_list else False


class ComponentSubTreeHandler(BaseHandler):
    def get(self, *args, **kwargs):
        record_type = self.get_argument('record_type', default=None, strip=True)
        id = self.get_argument('id', default=None, strip=True)

        if not record_type: return self.write(dict(code=-1, msg='record type不能为空'))
        if record_type not in ["app", "menu", "component"]: return self.write(dict(code=-2, msg='record type非法'))
        if not id: return self.write(dict(code=-3, msg='id不能为空'))

        count, queryset = get_component_subtree(**self.params)
        return self.write(dict(code=0, result=True, msg="获取成功", count=count, data=queryset))


class ComponentTransfer(BaseHandler):
    def get(self, *args, **kwargs):
        # 获取穿梭框接口
        count, queryset = get_components_list_tansfer(**self.params)
        return self.write(dict(code=0, result=True, msg="获取成功", count=count, data=queryset))


components_urls = [
    (r"/auth/v3/accounts/components/", ComponentsHandler, {"handle_name": "权限中心-组件管理"}),
    (r"/auth/v3/accounts/components/subtree/", ComponentSubTreeHandler, {"handle_name": "权限中心-组件子树"}),
    (r"/auth/v3/accounts/components/transfer/", ComponentTransfer, {"handle_name": "权限中心-组件穿梭框结构"}),
]

if __name__ == "__main__":
    pass
