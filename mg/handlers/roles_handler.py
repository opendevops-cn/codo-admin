#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2018/11/2
Desc    : 角色
"""

import json
from libs.base_handler import BaseHandler
from websdk2.cache_context import cache_conn
from websdk2.db_context import DBContextV2 as DBContext
from models.admin_model import Roles, UserRoles, RolesComponents, RoleMenus, RoleApps
from models.admin_schemas import get_roles_list_v2, get_user_list_for_role, get_all_user_list_for_role


class RoleHandler(BaseHandler):

    def get(self, *args, **kwargs):
        count, queryset = get_roles_list_v2(**self.params)

        return self.write(dict(code=0, result=True, msg="获取角色成功", count=count, data=queryset))

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        role_name = data.get('role_name')
        if not role_name: return self.write(dict(code=-1, msg='角色名不能为空'))

        with DBContext('w', None, True) as session:
            is_exist = session.query(Roles).filter(Roles.role_name == role_name).first()
            if is_exist: return self.write(dict(code=-2, msg='角色已注册'))

            session.add(Roles(**data))
        return self.write(dict(code=0, msg='角色创建成功'))

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        role_id = data.get('role_id', None)
        if not role_id:  return self.write(dict(code=-1, msg='不能为空'))

        with DBContext('w', None, True) as session:
            session.query(Roles).filter(Roles.role_id == role_id).delete(synchronize_session=False)
            session.query(UserRoles).filter(UserRoles.role_id == role_id).delete(synchronize_session=False)
            session.query(RolesComponents).filter(RolesComponents.role_id == role_id).delete(synchronize_session=False)
            session.query(RoleMenus).filter(RoleMenus.role_id == role_id).delete(synchronize_session=False)
            session.query(RoleApps).filter(RoleApps.role_id == role_id).delete(synchronize_session=False)

        return self.write(dict(code=0, msg='删除成功'))

    def put(self, *args, **kwargs):

        data = json.loads(self.request.body.decode("utf-8"))
        role_id = data.get('role_id')
        role_name = data.get('role_name')

        if not role_id: return self.write(dict(code=-1, msg='ID不能为空'))
        if not role_name: return self.write(dict(code=-2, msg='角色名称不能为空'))

        if '_index' in data: data.pop('_index')
        if '_rowKey' in data: data.pop('_rowKey')

        with DBContext('w', None, True) as session:
            is_exist = session.query(Roles.role_id).filter(Roles.role_id != role_id, Roles.status != '10',
                                                           Roles.role_name == role_name).first()
            if is_exist:  return self.write(dict(code=-3, msg=f'角色 "{role_name}" 已存在'))

            session.query(Roles).filter(Roles.role_id == role_id).update(data)

        return self.write(dict(code=0, msg='编辑成功'))

    def patch(self, *args, **kwargs):
        """禁用、启用"""
        data = json.loads(self.request.body.decode("utf-8"))
        role_id = str(data.get('role_id', None))
        msg = '角色不存在'

        if not role_id:  return self.write(dict(code=-1, msg='不能为空'))

        with DBContext('r') as session:
            role_status = session.query(Roles.status).filter(Roles.role_id == role_id, Roles.status != '10').first()

        if not role_status:  return self.write(dict(code=-2, msg=msg))

        if role_status[0] == '0':
            msg = '禁用成功'
            new_status = '20'

        elif role_status[0] == '20':
            msg = '启用成功'
            new_status = '0'
        else:
            msg = '状态不符合预期，删除'
            new_status = '10'

        with DBContext('w', None, True) as session:
            session.query(Roles).filter(Roles.role_id == role_id, Roles.status != '10').update(
                {Roles.status: new_status})
            session.query(UserRoles).filter(UserRoles.role_id == role_id).update({UserRoles.status: new_status})

        self.write(dict(code=0, msg=msg))


class RoleUserHandler(BaseHandler):
    def get(self, *args, **kwargs):
        role_id = self.get_argument('role_id', default=None, strip=True)
        role_name = self.get_argument('role_name', default=None, strip=True)
        if not role_id and not role_name:   return self.write(dict(status=-1, msg='关键参数不能为空'))

        count, role_list = get_user_list_for_role(role_id=role_id, role_name=role_name)

        return self.write(dict(code=0, msg='获取成功', count=count, data=role_list))

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        user_list = data.get('user_list', None)
        role_id = data.get('role_id', None)
        user_list = list(set(user_list))

        if not role_id:  return self.write(dict(code=-1, msg='角色不能为空'))

        if not user_list: return self.write(dict(code=-1, msg='选择的用户不能为空'))

        with DBContext('w', None, True) as session:
            new_users = [UserRoles(role_id=role_id, user_id=int(i)) for i in user_list]
            session.add_all(new_users)
            ###
            redis_conn = cache_conn()
            redis_conn.set(f"need_sync_all_cache", 'y', ex=600)

        return self.write(dict(code=0, msg='用户加入角色成功'))

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        user_list = data.get('user_list', None)
        role_id = data.get('role_id', None)
        user_list = list(set(user_list))

        if not role_id:   return self.write(dict(code=-1, msg='角色不能为空'))

        if not user_list: return self.write(dict(code=-1, msg='选择的用户不能为空'))

        ## 删除
        with DBContext('w', None, True) as session:
            session.query(UserRoles).filter(UserRoles.role_id == role_id,
                                            UserRoles.user_id.in_(user_list)).delete(synchronize_session=False)
            ###
            redis_conn = cache_conn()
            redis_conn.set(f"need_sync_all_cache", 'y', ex=600)

        self.write(dict(code=0, msg='从角色中删除用户成功'))


class RoleUserAllHandler(BaseHandler):
    def prepare(self):
        pass

    def get(self, *args, **kwargs):
        role_list = get_all_user_list_for_role()

        return self.write(dict(code=0, msg='获取成功', data=role_list))


roles_urls = [
    (r"/v3/accounts/role/", RoleHandler, {"handle_name": "角色列表"}),
    (r"/v3/accounts/role_user/", RoleUserHandler, {"handle_name": "通过角色查询角色内用户", "handle_status": "y"}),
    (r"/v3/accounts/all_role_user/", RoleUserAllHandler, {"handle_name": "查询所有用户角色", "handle_status": "y"})
]

if __name__ == "__main__":
    pass
