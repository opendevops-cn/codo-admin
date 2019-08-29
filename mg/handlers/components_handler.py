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
from websdk.db_context import DBContext
from models.admin import Components, RolesComponents, model_to_dict


class ComponentsHandler(BaseHandler):
    def get(self, *args, **kwargs):
        key = self.get_argument('key', default=None, strip=True)
        value = self.get_argument('value', default=None, strip=True)
        comp_list = []
        with DBContext('r') as session:
            if key and value:
                count = session.query(Components).filter(Components.status != '10').filter_by(**{key: value}).count()
                comp_info = session.query(Components).filter(Components.status != '10').filter_by(
                    **{key: value}).order_by(Components.comp_id).all()
            else:
                count = session.query(Components).filter(Components.status != '10').count()
                comp_info = session.query(Components).filter(Components.status != '10').order_by(
                    Components.comp_id).all()

        for msg in comp_info:
            data_dict = model_to_dict(msg)
            comp_list.append(data_dict)

        return self.write(dict(code=0, msg='获取成功', data=comp_list, count=count))

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        component_name = data.get('component_name', None)
        if not component_name:
            return self.write(dict(code=-1, msg='不能为空'))

        with DBContext('r') as session:
            is_exist = session.query(Components.comp_id).filter(Components.comp_id == component_name).first()

        if is_exist:
            return self.write(dict(code=-3, msg='"{}"已存在'.format(component_name)))

        with DBContext('w', None, True) as session:
            session.add(Components(component_name=component_name, status='0'))
            session.commit()
        return self.write(dict(code=0, msg='组件创建成功'))

    def put(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        comp_id = data.get('comp_id', None)
        component_name = data.get('component_name', None)

        if not comp_id or not component_name:
            return self.write(dict(code=-1, msg='不能为空'))

        with DBContext('w', None, True) as session:
            session.query(Components).filter(Components.comp_id == int(comp_id)).update(
                {Components.component_name: component_name})

        return self.write(dict(code=0, msg='编辑成功'))

    def patch(self, *args, **kwargs):
        """禁用、启用"""
        data = json.loads(self.request.body.decode("utf-8"))
        comp_id = data.get('comp_id', None)
        msg = '组件不存在'

        if not comp_id:
            return self.write(dict(code=-1, msg='不能为空'))

        with DBContext('r') as session:
            comp_status = session.query(Components.status).filter(Components.comp_id == comp_id,
                                                                  Components.status != 10).first()
        if not comp_status:
            return self.write(dict(code=-2, msg=msg))

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
        if not comp_id:
            return self.write(dict(code=-1, msg='不能为空'))

        with DBContext('w', None, True) as session:
            session.query(Components).filter(Components.comp_id == comp_id).delete(synchronize_session=False)
            session.query(RolesComponents).filter(RolesComponents.comp_id == comp_id).delete(synchronize_session=False)

        return self.write(dict(code=0, msg='删除成功'))


class RoleCompHandler(BaseHandler):

    def get(self, *args, **kwargs):
        role_id = self.get_argument('role_id', default=None, strip=True)
        data_list = []

        if not role_id:
            return self.write(dict(code=-1, msg='角色不能为空'))

        with DBContext('r') as session:
            comp_info = session.query(Components).outerjoin(RolesComponents,
                                                            Components.comp_id == RolesComponents.comp_id).filter(
                RolesComponents.role_id == role_id, RolesComponents.status == '0', Components.status == '0').all()

        for msg in comp_info:
            comp_dict = {}
            data_dict = model_to_dict(msg)
            comp_dict["comp_id"] = data_dict["comp_id"]
            comp_dict["component_name"] = data_dict["component_name"]
            data_list.append(comp_dict)

        return self.write(dict(code=0, msg='获取成功', data=data_list))

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        comp_list = data.get('comp_list', None)
        role_id = data.get('role_id', None)
        comp_list = list(set(comp_list))

        if not role_id:
            return self.write(dict(code=-1, msg='角色不能为空'))

        if not comp_list:
            return self.write(dict(code=-1, msg='选择的组件不能为空'))

        with DBContext('w', None, True) as session:
            new_comps = [RolesComponents(role_id=role_id, comp_id=i, status='0') for i in comp_list]
            session.add_all(new_comps)

        return self.write(dict(code=0, msg='组件加入角色成功'))

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        comp_list = data.get('comp_list', None)
        role_id = data.get('role_id', None)
        comp_list = list(set(comp_list))

        if not role_id:
            return self.write(dict(code=-1, msg='角色不能为空'))

        if not comp_list:
            return self.write(dict(code=-1, msg='选择的组件不能为空'))

        ## 删除
        with DBContext('w', None, True) as session:
            session.query(RolesComponents).filter(RolesComponents.role_id == role_id,
                                                  RolesComponents.comp_id.in_(comp_list)).delete(
                synchronize_session=False)

        self.write(dict(code=0, msg='从角色中删除组件成功'))


components_urls = [
    (r"/v2/accounts/components/", ComponentsHandler),
    (r"/v2/accounts/role_comp/", RoleCompHandler),
]

if __name__ == "__main__":
    pass
