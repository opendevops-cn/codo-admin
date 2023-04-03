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
from models.admin_model import Functions, RoleFunctions, Apps
from models.admin_schemas import get_func_list_v2, get_func_list_for_role


class FuncHandler(BaseHandler):
    def get(self, *args, **kwargs):
        count, queryset = get_func_list_v2(**self.params)

        return self.write(dict(code=0, result=True, msg="获取成功", count=count, data=queryset))

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        func_name = data.get('func_name', None)
        app_code = data.get('app_code')
        method_type = data.get('method_type', None)
        uri = data.get('uri', None)
        parameters = data.get('parameters', None)

        if not func_name or not method_type or not uri:  return self.write(dict(code=-1, msg='不能为空'))

        if self.check_app_permission(app_code) is not True:
            return self.write(dict(code=-8, msg="You don't have permission to apply"))

        try:
            if parameters: json.loads(parameters)
        except Exception as err:
            return self.write(dict(code=-3, msg='参数备注必须为JSON格式，JSON是双引号哟', result=False))

        with DBContext('w', None, True) as session:
            is_exist = session.query(Functions.func_id).filter(Functions.func_name == func_name).first()
            if is_exist:  return self.write(dict(code=-3, msg=f'权限"{func_name}"已存在'))
            session.add(Functions(**data))

        self.write(dict(code=0, msg='权限创建成功', result=True))

    def put(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        func_id = data.get('func_id')
        func_name = data.get('func_name')
        app_code = data.get('app_code')
        parameters = data.get('parameters')

        if self.check_app_permission(app_code) is not True:
            return self.write(dict(code=-8, msg="You don't have permission to apply"))

        if '_index' in data: data.pop('_index')
        if '_rowKey' in data: data.pop('_rowKey')

        if not func_id and not isinstance(func_id, int):
            return self.write(dict(code=-1, msg="关键参数不能为空", result=False))

        if 'func_name' not in data or 'method_type' not in data or 'uri' not in data:
            return self.write(dict(code=-2, msg='不能为空', result=False))

        try:
            if parameters: json.loads(parameters)
        except Exception as err:
            return self.write(dict(code=-3, msg='参数备注必须为JSON格式，JSON是双引号哟', result=False))

        with DBContext('w', None, True) as session:
            is_exist = session.query(Functions).filter(Functions.func_id != func_id,
                                                       Functions.func_name == func_name).first()
            if is_exist:  return self.write(dict(code=-3, msg=f'菜单"{func_name}"已存在'))

            session.query(Functions).filter(Functions.func_id == func_id).update(data)

        return self.write(dict(code=0, msg='修改成功', result=True))

    def patch(self, *args, **kwargs):
        """禁用、启用"""
        data = json.loads(self.request.body.decode("utf-8"))
        func_id = data.get('func_id')
        msg = '权限不存在'

        if not func_id: return self.write(dict(code=-1, msg='不能为空'))

        if self.check_app_permission('', func_id) is not True:
            return self.write(dict(code=-8, msg="You don't have permission to apply"))

        with DBContext('r') as session:
            func_status = session.query(Functions.status).filter(Functions.func_id == func_id,
                                                                 Functions.status != 10).first()
        if not func_status:  return self.write(dict(code=-2, msg=msg))

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

        if not func_id: return self.write(dict(code=-1, msg='关键参数不能为空', result=False))

        if self.check_app_permission('', func_id) is not True:
            return self.write(dict(code=-8, msg="You don't have permission to apply"))

        with DBContext('w', None, True) as session:
            session.query(Functions).filter(Functions.func_id == func_id).delete(synchronize_session=False)
            session.query(RoleFunctions).filter(RoleFunctions.func_id == func_id).delete(synchronize_session=False)

        return self.write(dict(code=0, msg='删除成功', result=True))

    def check_app_permission(self, app_code, func_id=None):
        if self.is_super: return True
        with DBContext('w', None, True) as session:
            if func_id:
                app_code = session.query(Functions.app_code).filter(Functions.func_id == func_id).first()
                app_code = app_code[0]
            user_info = session.query(Apps.user_list).filter(Apps.status != '10', Apps.app_code == app_code).first()

        if not user_info: return False
        user_list = user_info[0]
        if not user_list or not isinstance(user_list, list): return False
        return True if self.nickname in user_list else False


class RoleFuncHandler(BaseHandler):

    def get(self, *args, **kwargs):
        role_id = self.get_argument('role_id', default=None, strip=True)

        if not role_id: return self.write(dict(code=-1, msg='角色不能为空'))

        data_list = get_func_list_for_role(int(role_id))
        return self.write(dict(code=0, msg='获取成功', data=data_list))

    def patch(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        func_id = data.get('func_id', None)
        role_id = data.get('role_id', None)

        if not func_id or not role_id:  return self.write(dict(code=-1, msg='不能为空'))

        with DBContext('w', None, True) as session:
            is_exist = session.query(RoleFunctions.id).filter(RoleFunctions.func_id == func_id,
                                                              RoleFunctions.role_id == role_id,
                                                              RoleFunctions.status != '10').first()

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

        if not role_id:  return self.write(dict(code=-1, msg='角色不能为空'))

        if not func_list: return self.write(dict(code=-1, msg='选择的权限不能为空'))

        with DBContext('w', None, True) as session:
            new_funcs = [RoleFunctions(role_id=role_id, func_id=i, status='0') for i in func_list]
            session.add_all(new_funcs)

        return self.write(dict(code=0, msg='权限加入角色成功'))

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        role_id = data.get('role_id', None)
        func_list = data.get('func_list', None)
        func_list = list(set(func_list))

        if not role_id:   return self.write(dict(code=-1, msg='角色不能为空'))

        if not func_list: return self.write(dict(code=-1, msg='选择的权限不能为空'))

        ## 删除
        with DBContext('w', None, True) as session:
            session.query(RoleFunctions).filter(RoleFunctions.role_id == role_id,
                                                RoleFunctions.func_id.in_(func_list)).delete(
                synchronize_session=False)

        self.write(dict(code=0, msg='从角色中删除权限成功'))


functions_urls = [
    (r"/v3/accounts/role_func/", RoleFuncHandler, {"handle_name": "权限中心-API角色"}),
    (r"/v3/accounts/func/", FuncHandler, {"handle_name": "权限中心-API管理"}),

]

if __name__ == "__main__":
    pass
