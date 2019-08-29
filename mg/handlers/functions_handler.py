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
from models.admin import Functions, RoleFunctions, model_to_dict


class FuncHandler(BaseHandler):
    def get(self, *args, **kwargs):
        key = self.get_argument('key', default=None, strip=True)
        value = self.get_argument('value', default=None, strip=True)
        page_size = self.get_argument('page', default=1, strip=True)
        limit = self.get_argument('limit', default=2000, strip=True)
        limit_start = (int(page_size) - 1) * int(limit)
        func_list = []
        with DBContext('r') as session:
            if key and value:
                count = session.query(Functions).filter(Functions.status != '10').filter_by(**{key: value}).count()
                func_info = session.query(Functions).filter(Functions.status != '10').filter_by(
                    **{key: value}).order_by(Functions.func_id).offset(limit_start).limit(int(limit))
            else:
                count = session.query(Functions).filter(Functions.status != '10').count()
                func_info = session.query(Functions).filter(Functions.status != '10').order_by(
                    Functions.func_id).offset(limit_start).limit(int(limit))
        for msg in func_info:
            data_dict = model_to_dict(msg)
            data_dict['ctime'] = str(data_dict['ctime'])
            data_dict['utime'] = str(data_dict['utime'])
            func_list.append(data_dict)

        return self.write(dict(code=0, msg='获取成功', data=func_list, count=count))

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        func_name = data.get('func_name', None)
        method_type = data.get('method_type', None)
        uri = data.get('uri', None)
        if not func_name or not method_type or not uri:
            return self.write(dict(code=-1, msg='不能为空'))

        with DBContext('r') as session:
            is_exist = session.query(Functions.func_id).filter(Functions.func_name == func_name).first()

        if is_exist:
            return self.write(dict(code=-3, msg='权限"{}"已存在'.format(func_name)))

        with DBContext('w', None, True) as session:
            session.add(Functions(func_name=func_name, method_type=method_type, uri=uri, status='0'))

        self.write(dict(code=0, msg='权限创建成功'))

    def put(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        func_id = data.get('func_id', None)
        func_name = data.get('func_name', None)
        method_type = data.get('method_type', None)
        uri = data.get('uri', None)

        if not func_id or not func_name or not method_type or not uri:
            return self.write(dict(code=-1, msg='不能为空'))

        with DBContext('w', None, True) as session:
            session.query(Functions).filter(Functions.func_id == int(func_id)).update(
                {Functions.method_type: method_type, Functions.func_name: func_name,
                 Functions.uri: uri})

        return self.write(dict(code=0, msg='编辑成功'))

    def patch(self, *args, **kwargs):
        """禁用、启用"""
        data = json.loads(self.request.body.decode("utf-8"))
        func_id = data.get('func_id', None)
        msg = '权限不存在'

        if not func_id:
            return self.write(dict(code=-1, msg='不能为空'))

        with DBContext('r') as session:
            func_status = session.query(Functions.status).filter(Functions.func_id == func_id,
                                                                 Functions.status != 10).first()
        if not func_status:
            return self.write(dict(code=-2, msg=msg))

        if func_status[0] == '0':
            msg = '禁用成功'
            new_status = '20'

        elif func_status[0] == '20':
            msg = '启用成功'
            new_status = '0'
        else:
            msg = '状态不符合预期，删除'
            new_status = '10'

        with DBContext('w', None, True) as session:
            session.query(Functions).filter(Functions.func_id == func_id, Functions.status != 10).update(
                {Functions.status: new_status})

        return self.write(dict(code=0, msg=msg))

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        func_id = data.get('func_id', None)
        if not func_id:
            return self.write(dict(code=-1, msg='不能为空'))

        with DBContext('w', None, True) as session:
            session.query(Functions).filter(Functions.func_id == func_id).delete(synchronize_session=False)
            session.query(RoleFunctions).filter(RoleFunctions.func_id == func_id).delete(synchronize_session=False)

        return self.write(dict(code=0, msg='删除成功'))


class RoleFuncHandler(BaseHandler):

    def get(self, *args, **kwargs):
        role_id = self.get_argument('role_id', default=1, strip=True)
        data_list = []

        if not role_id:
            return self.write(dict(code=-1, msg='角色不能为空'))

        with DBContext('r') as session:
            role_func = session.query(Functions).outerjoin(RoleFunctions,
                                                           Functions.func_id == RoleFunctions.func_id).filter(
                RoleFunctions.role_id == role_id, RoleFunctions.status == '0').all()

        for msg in role_func:
            menu_dict = {}
            data_dict = model_to_dict(msg)
            menu_dict["func_id"] = data_dict["func_id"]
            menu_dict["func_name"] = data_dict["func_name"]
            menu_dict["method_type"] = data_dict["method_type"]
            menu_dict["uri"] = data_dict["uri"]
            data_list.append(menu_dict)

        return self.write(dict(code=0, msg='获取成功', data=data_list))

    def patch(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        func_id = data.get('func_id', None)
        role_id = data.get('role_id', None)

        if not func_id or not role_id:
            return self.write(dict(code=-1, msg='不能为空'))

        with DBContext('r') as session:
            is_exist = session.query(RoleFunctions.id).filter(RoleFunctions.func_id == func_id,
                                                              RoleFunctions.role_id == role_id,
                                                              RoleFunctions.status != '10').first()

        with DBContext('w', None, True) as session:
            if not is_exist:
                session.add(RoleFunctions(role_id=role_id, func_id=func_id, status='0'))
                return self.write(dict(code=0, msg='添加路由权限成功'))
            else:
                session.query(RoleFunctions).filter(RoleFunctions.role_id == role_id,
                                                    RoleFunctions.func_id == func_id).delete(synchronize_session=False)
            return self.write(dict(code=0, msg='删除路由权限成功'))

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        role_id = data.get('role_id', None)
        func_list = data.get('func_list', None)
        func_list = list(set(func_list))

        if not role_id:
            return self.write(dict(code=-1, msg='角色不能为空'))

        if not func_list:
            return self.write(dict(code=-1, msg='选择的权限不能为空'))

        with DBContext('w', None, True) as session:
            new_funcs = [RoleFunctions(role_id=role_id, func_id=i, status='0') for i in func_list]
            session.add_all(new_funcs)

        return self.write(dict(code=0, msg='权限加入角色成功'))

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        role_id = data.get('role_id', None)
        func_list = data.get('func_list', None)
        func_list = list(set(func_list))

        if not role_id:
            return self.write(dict(code=-1, msg='角色不能为空'))

        if not func_list:
            return self.write(dict(code=-1, msg='选择的权限不能为空'))

        ## 删除
        with DBContext('w', None, True) as session:
            session.query(RoleFunctions).filter(RoleFunctions.role_id == role_id,
                                                RoleFunctions.func_id.in_(func_list)).delete(
                synchronize_session=False)

        self.write(dict(code=0, msg='从角色中删除权限成功'))


functions_urls = [
    (r"/v2/accounts/role_func/", RoleFuncHandler),
    (r"/v2/accounts/func/", FuncHandler),

]

if __name__ == "__main__":
    pass
