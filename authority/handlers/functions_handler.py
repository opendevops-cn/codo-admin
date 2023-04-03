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
from models.authority_model import Functions, Apps, RoleFunction
from services.func_services import get_func_list, get_func_subtree
from websdk2.model_utils import GetInsertOrUpdateObj


class FuncHandler(BaseHandler):
    def get(self, *args, **kwargs):
        count, queryset = get_func_list(**self.params)

        return self.write(dict(code=0, result=True, msg="获取成功", count=count, data=queryset))

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        func_name = data.get('func_name', None)
        app_code = data.get('app_code')
        method_type = data.get('method_type', [])
        url = data.get('url', None)
        parameters = data.get('parameters', {})

        if not func_name or not method_type or not url: return self.write(dict(code=-1, msg='不能为空'))

        if self.check_app_permission(app_code) is not True:
            return self.write(dict(code=-8, msg="You don't have permission to apply"))

        try:
            if parameters: json.loads(parameters)
        except Exception as err:
            return self.write(dict(code=-3, msg='参数备注必须为JSON格式，JSON是双引号哟', result=False))

        with DBContext('w', None, True) as session:
            is_exist = session.query(Functions.function_id).filter(Functions.func_name == func_name).first()
            if is_exist: return self.write(dict(code=-3, msg=f'权限"{func_name}"已存在'))
            session.add(Functions(**data))

        with DBContext('w', None, True) as session:
            try:
                url_list = url.split('/')
                url_list = [u for u in url_list if u]
                parent_id, path, last_u = 0, '', url_list[-1]

                for u in url_list:
                    path += '/' + u
                    data = dict(
                        app_code=app_code,
                        func_name=func_name if u == last_u else '',
                        uri=u,
                        path=path,
                        parent_id=parent_id,
                        status='0',
                        parameters=json.dumps(func_name.get('parameters', {})),
                    )
                    fun_obj = GetInsertOrUpdateObj(Functions,
                                                   f"app_code='{app_code}' and uri='{u}' and method_type='{data.get('method_type', '')}' and path='{data.get('path')}'",
                                                   **data)
                    session.add(fun_obj)
                    session.commit()
                    parent_id = fun_obj.function_id

                    if u == last_u:
                        data['func_name'] = ''
                        data['parent_id'] = parent_id
                        for method in method_type:
                            data["method_type"] = method
                            session.add(GetInsertOrUpdateObj(Functions,
                                                             f"app_code='{app_code}' and uri='{u}' and method_type='{data.get('method_type', '')}' and path='{data.get('path')}'",
                                                             **data))
            except Exception as err:
                pass

        self.write(dict(code=0, msg='权限创建成功', result=True))

    def put(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        function_id = data.get('function_id')
        func_name = data.get('func_name')
        app_code = data.get('app_code')
        parameters = data.get('parameters')

        if self.check_app_permission(app_code) is not True:
            return self.write(dict(code=-8, msg="You don't have permission to apply"))

        if '_index' in data: data.pop('_index')
        if '_rowKey' in data: data.pop('_rowKey')

        if not function_id and not isinstance(function_id, int):
            return self.write(dict(code=-1, msg="关键参数不能为空", result=False))

        if 'func_name' not in data or 'method_type' not in data or 'uri' not in data:
            return self.write(dict(code=-2, msg='不能为空', result=False))

        try:
            if parameters: json.loads(parameters)
        except Exception as err:
            return self.write(dict(code=-3, msg='参数备注必须为JSON格式，JSON是双引号哟', result=False))

        with DBContext('w', None, True) as session:
            is_exist = session.query(Functions).filter(Functions.function_id != function_id,
                                                       Functions.func_name == func_name).first()
            if is_exist:  return self.write(dict(code=-3, msg=f'菜单"{func_name}"已存在'))

            session.query(Functions).filter(Functions.function_id == function_id).update(data)

        return self.write(dict(code=0, msg='修改成功', result=True))

    def patch(self, *args, **kwargs):
        """禁用、启用"""
        data = json.loads(self.request.body.decode("utf-8"))
        function_id = data.get('function_id')
        msg = '权限不存在'

        if not function_id: return self.write(dict(code=-1, msg='不能为空'))

        if self.check_app_permission('', function_id) is not True:
            return self.write(dict(code=-8, msg="You don't have permission to apply"))

        with DBContext('r') as session:
            func_status = session.query(Functions.status).filter(Functions.function_id == function_id,
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
            session.query(Functions).filter(Functions.function_id == function_id, Functions.status != 10).update(
                {Functions.status: new_status})

        return self.write(dict(code=0, msg=msg))

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        function_id = data.get('function_id', [])

        if not function_id: return self.write(dict(code=-1, msg='关键参数不能为空', result=False))

        if self.check_app_permission('', function_id) is not True:
            return self.write(dict(code=-8, msg="You don't have permission to apply"))

        if self.check_children_exist(function_id):
            return self.write(dict(code=-8, msg="当前删除列表存在子节点，不可删除"))

        with DBContext('w', None, True) as session:
            session.query(Functions).filter(Functions.function_id.in_(function_id)).delete(synchronize_session=False)
            session.query(RoleFunction).filter(RoleFunction.function_id.in_(function_id)).delete(synchronize_session=False)

        return self.write(dict(code=0, msg='删除成功', result=True))

    def check_children_exist(self, func_list):
        with DBContext('w', None, True) as session:
            if func_list:
                for function_id in func_list:
                    children_list = session.query(Functions.function_id).filter(Functions.parent_id == function_id, Functions.status == '0').all()
                    for child in children_list:
                        if child[0] not in func_list and child[0] != 0:
                            return True
        return False

    def check_app_permission(self, app_code, function_id=None):
        if self.is_super: return True
        with DBContext('w', None, True) as session:
            if function_id:
                app_code = session.query(Functions.app_code).filter(Functions.function_id == function_id).first()
                app_code = app_code[0]
            user_info = session.query(Apps.user_list).filter(Apps.status != '10', Apps.app_code == app_code).first()

        if not user_info: return False
        user_list = user_info[0]
        if not user_list or not isinstance(user_list, list): return False
        return True if self.nickname in user_list else False


class FuncSubTreeHandler(BaseHandler):
    def get(self, *args, **kwargs):
        record_type = self.get_argument('record_type', default=None, strip=True)
        id = self.get_argument('id', default=None, strip=True)

        if not record_type: return self.write(dict(code=-1, msg='record type不能为空'))
        if record_type not in ["app", "function"]: return self.write(dict(code=-2, msg='record type非法'))
        if not id: return self.write(dict(code=-3, msg='id不能为空'))

        count, queryset = get_func_subtree(**self.params)
        return self.write(dict(code=0, result=True, msg="获取成功", count=count, data=queryset))


functions_urls = [
    (r"/auth/v3/accounts/func/", FuncHandler, {"handle_name": "权限中心-API管理"}),
    (r"/auth/v3/accounts/func/subtree/", FuncSubTreeHandler, {"handle_name": "权限中心-菜单子树"}),
]

if __name__ == "__main__":
    pass
