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
from websdk.db_context import DBContext
from models.admin import Users, Roles, UserRoles,RolesComponents,RoleMenus, model_to_dict


class RoleHandler(BaseHandler):

    def get(self, *args, **kwargs):
        key = self.get_argument('key', default=None, strip=True)
        value = self.get_argument('value', default=None, strip=True)
        page_size = self.get_argument('page', default=1, strip=True)
        limit = self.get_argument('limit', default=10, strip=True)
        limit_start = (int(page_size) - 1) * int(limit)
        role_list = []
        with DBContext('r') as session:
            if key and value:
                count = session.query(Roles).filter(Roles.status != '10').filter_by(**{key: value}).count()
                role_info = session.query(Roles).filter(Roles.status != '10').filter_by(**{key: value}).order_by(
                    Roles.role_id).offset( limit_start).limit(int(limit))
            else:
                count = session.query(Roles).filter(Roles.status != '10').count()
                role_info = session.query(Roles).filter(Roles.status != '10').order_by(Roles.role_id).offset(
                    limit_start).limit(int(limit))

        for msg in role_info:
            data_dict = model_to_dict(msg)
            data_dict['ctime'] = str(data_dict['ctime'])
            role_list.append(data_dict)

        return self.write(dict(code=0, msg='获取角色成功', count=count, data=role_list))

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        role_name = data.get('role_name', None)
        if not role_name:
            return self.write(dict(code=-1, msg='角色名不能为空'))

        with DBContext('r') as session:
            is_exist = session.query(Roles).filter(Roles.role_name == role_name).first()
        if is_exist:
            return self.write(dict(code=-2, msg='角色已注册'))

        with DBContext('w', None, True) as session:
            session.add(Roles(role_name=role_name, status='0'))

        return self.write(dict(code=0, msg='角色创建成功'))

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        role_id = data.get('role_id', None)
        if not role_id:
            return self.write(dict(code=-1, msg='不能为空'))

        with DBContext('w', None, True) as session:
            session.query(Roles).filter(Roles.role_id == role_id).delete(synchronize_session=False)
            session.query(UserRoles).filter(UserRoles.role_id == role_id).delete(synchronize_session=False)
            session.query(RolesComponents).filter(RolesComponents.role_id == role_id).delete(synchronize_session=False)
            session.query(RoleMenus).filter(RoleMenus.role_id == role_id).delete(synchronize_session=False)

        return self.write(dict(code=0, msg='删除成功'))

    def put(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        role_id = data.get('role_id', None)
        key = data.get('key', None)
        value = data.get('value', None)

        if not key or not value:
            return self.write(dict(code=-1, msg='不能为空'))

        with DBContext('r') as session:
            is_exist = session.query(Roles.role_id).filter(Roles.status != '10', Roles.role_name == value).first()

        if is_exist:
            return self.write(dict(code=-2, msg='角色名已存在'))

        with DBContext('w', None, True) as session:
            session.query(Roles).filter(Roles.role_id == role_id).update({key: value})

        return self.write(dict(code=0, msg='编辑成功'))

    def patch(self, *args, **kwargs):
        """禁用、启用"""
        data = json.loads(self.request.body.decode("utf-8"))
        role_id = str(data.get('role_id', None))
        msg = '用户不存在'

        if not role_id:
            return self.write(dict(code=-1, msg='不能为空'))

        with DBContext('r') as session:
            role_status = session.query(Roles.status).filter(Roles.role_id == role_id, Roles.status != '10').first()
        if not role_status:
            return self.write(dict(code=-2, msg=msg))

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
            session.query(Roles).filter(Roles.role_id == role_id, Roles.status != '10').update({Roles.status: new_status})
            session.query(UserRoles).filter(UserRoles.role_id == role_id).update({UserRoles.status: new_status})

        self.write(dict(code=0, msg=msg))


class RoleUserHandler(BaseHandler):
    def get(self, *args, **kwargs):
        role_id = self.get_argument('role_id', default=None, strip=True)
        if not role_id:
            return self.write(dict(status=-1, msg='角色ID不能为空'))

        role_list = []
        dict_list = ['user_role_id', 'role_id', 'user_id', 'username', 'nickname']
        with DBContext('r') as session:
            count = session.query(UserRoles).filter(UserRoles.status != '10', UserRoles.role_id == role_id).count()
            role_info = session.query(UserRoles.user_role_id, UserRoles.role_id, UserRoles.user_id, Users.username,
                                      Users.nickname).outerjoin(Users, Users.user_id == UserRoles.user_id).filter(
                UserRoles.role_id == role_id, UserRoles.status == '0', Users.status == '0').order_by(
                UserRoles.role_id).all()

        for msg in role_info:
            role_list.append(dict(zip(dict_list, msg)))

        return self.write(dict(code=0, msg='获取成功', count=count, data=role_list))

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        user_list = data.get('user_list', None)
        role_id = data.get('role_id', None)
        user_list = list(set(user_list))

        if not role_id:
            return self.write(dict(code=-1, msg='角色不能为空'))

        if not user_list:
            return self.write(dict(code=-1, msg='选择的用户不能为空'))

        with DBContext('w', None, True) as session:
            new_users = [UserRoles(role_id=role_id, user_id=i, status='0') for i in user_list]
            session.add_all(new_users)

        return self.write(dict(code=0, msg='用户加入角色成功'))

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        user_list = data.get('user_list', None)
        role_id = data.get('role_id', None)
        user_list = list(set(user_list))

        if not role_id:
            return self.write(dict(code=-1, msg='角色不能为空'))

        if not user_list:
            return self.write(dict(code=-1, msg='选择的用户不能为空'))

        ## 删除
        with DBContext('w', None, True) as session:
            session.query(UserRoles).filter(UserRoles.role_id == role_id,
                                            UserRoles.user_id.in_(user_list)).delete(synchronize_session=False)

        self.write(dict(code=0, msg='从角色中删除用户成功'))


roles_urls = [
    (r"/v2/accounts/role/", RoleHandler),
    (r"/v2/accounts/role_user/", RoleUserHandler),

]

if __name__ == "__main__":
    pass
