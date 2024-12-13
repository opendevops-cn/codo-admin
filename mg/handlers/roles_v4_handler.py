#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2018/11/2
Desc    : 角色管理
"""

import json
from abc import ABC
from concurrent.futures import ThreadPoolExecutor
from tornado.concurrent import run_on_executor
from sqlalchemy.exc import IntegrityError
from libs.base_handler import BaseHandler
from websdk2.cache_context import cache_conn
from websdk2.db_context import DBContextV2 as DBContext
from services.role_service import get_role_list_for_api, get_normal_role_list_for_api, get_base_role_list_for_api, \
    opt_obj, get_users_for_role, get_all_user_list_for_role, role_sync_all
from models.authority import Roles, UserRoles, RolesComponents, RoleMenus, RoleApps


class RoleHandler(BaseHandler, ABC):

    def get(self, *args, **kwargs):
        res = get_role_list_for_api(**self.params)

        return self.write(res)

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        res = opt_obj.handle_add(data)
        self.write(res)

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        role_id = data.get('role_id', None)
        if not role_id:
            return self.write(dict(code=-1, msg='不能为空'))

        with DBContext('w', None, True) as session:
            session.query(Roles).filter(Roles.id == role_id).delete(synchronize_session=False)
            session.query(UserRoles).filter(UserRoles.role_id == role_id).delete(synchronize_session=False)
            session.query(RolesComponents).filter(RolesComponents.role_id == role_id).delete(synchronize_session=False)
            session.query(RoleMenus).filter(RoleMenus.role_id == role_id).delete(synchronize_session=False)
            session.query(RoleApps).filter(RoleApps.role_id == role_id).delete(synchronize_session=False)

        return self.write(dict(code=0, msg='删除成功'))

    def put(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        role_id = data.get('id')
        role_name = data.get('role_name')
        details = data.get('details')
        if not role_id:
            return self.write(dict(code=-1, msg='角色不能为空'))

        with DBContext('w', None, True) as session:
            new_data = dict(details=details, role_name=role_name)
            session.query(Roles).filter(Roles.id == role_id).update(new_data)
        return self.write(dict(code=0, msg='角色编辑成功'))


class RoleListHandler(BaseHandler, ABC):

    def get(self, *args, **kwargs):
        res = get_normal_role_list_for_api(**self.params)

        return self.write(res)


class RoleBaseListHandler(BaseHandler, ABC):

    def get(self, *args, **kwargs):
        res = get_base_role_list_for_api(**self.params)

        return self.write(res)


class RoleUserHandler(BaseHandler, ABC):
    _thread_pool = ThreadPoolExecutor(5)

    @run_on_executor(executor='_thread_pool')
    def handle_sync(self):
        return role_sync_all()

    def get(self, *args, **kwargs):
        role_id = self.get_argument('role_id', default=None, strip=True)
        res = get_users_for_role(role_id=role_id)

        return self.write(res)

    async def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        user_list = data.get('user_list', None)
        role_list = data.get('role_list', [])
        role_id = data.get('role_id', None)
        user_list = list(set(user_list))
        role_list = list(set(role_list))
        if not role_id:
            return self.write(dict(code=-1, msg='角色不能为空'))

        if not user_list:
            return self.write(dict(code=-1, msg='选择的用户不能为空'))

        # 先删除
        with DBContext('w', None, True) as session:
            session.query(UserRoles).filter(UserRoles.role_id == role_id,
                                            UserRoles.user_id.notin_(user_list)).delete(synchronize_session=False)

        for i in user_list:
            try:
                with DBContext('w', None, True) as session:
                    session.add(UserRoles(role_id=role_id, user_id=int(i)))
            except IntegrityError as e:
                pass
            except Exception as err:
                print(err)

        try:
            with DBContext('w', None, True) as session:
                for r in role_list:
                    e_info = session.query(Roles).filter(Roles.id == r, Roles.role_type == 'base').first()
                    if not e_info:
                        role_list.remove(r)
                        continue
                session.query(Roles).filter(Roles.id == role_id).update(dict(role_subs=role_list),
                                                                        synchronize_session=False)
        except IntegrityError as e:
            print(e)
        except Exception as err:
            print(err)
        ###
        await self.handle_sync()
        return self.write(dict(code=0, msg='用户加入角色成功'))


class RoleUserAllHandler(BaseHandler, ABC):
    def prepare(self):
        pass

    def get(self, *args, **kwargs):
        role_list = get_all_user_list_for_role()

        return self.write(dict(code=0, msg='获取成功', data=role_list))


class RoleSyncHandler(BaseHandler, ABC):
    _thread_pool = ThreadPoolExecutor(3)

    @run_on_executor(executor='_thread_pool')
    def handle_sync(self):
        return role_sync_all()

    async def post(self, *args, **kwargs):
        res = await self.handle_sync()
        if res:
            self.write(dict(code=0, msg="同步成功"))
        else:
            self.write(dict(code=-1, msg="同步失败"))


roles_v4_urls = [
    (r"/v4/role/list/", RoleListHandler, {"handle_name": "PAAS-基础功能-查看常规角色列表", "method": ["GET"]}),
    (r"/v4/role/base_list/", RoleBaseListHandler, {"handle_name": "PAAS-基础功能-查看所有基础角色", "method": ["GET"]}),
    # (r"/v3/accounts/role/", RoleHandler, {"handle_name": "角色列表-待销毁", "method": ["ALL"]}),
    (r"/v4/role/", RoleHandler, {"handle_name": "权限中心-角色管理V4", "method": ["ALL"]}),
    (r"/v4/role/sync/", RoleSyncHandler, {"handle_name": "权限中心-角色权限同步", "method": ["ALL"]}),
    (r"/v4/role_user/", RoleUserHandler, {"handle_name": "权限中心-角色用户管理", "method": ["ALL"]}),
    # TODO 暂时保留
    # (r"/v3/accounts/all_role_user/", RoleUserAllHandler, {"handle_name": "查询所有用户角色-待废弃", "method": ["GET"]}),
    (r"/v4/all_role_user/", RoleUserAllHandler, {"handle_name": "权限中心-查询所有用户角色V4", "method": ["GET"]})
]

if __name__ == "__main__":
    pass
