#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
author : shenshuo
date   : 2017年11月20日11:10:29
role   : 用户管理API

status = '0'    正常
status = '10'   逻辑删除
status = '20'   禁用
"""

import json
import shortuuid
import base64
from abc import ABC
from websdk2.jwt_token import gen_md5
from websdk2.tools import check_password
from libs.base_handler import BaseHandler
from websdk2.db_context import DBContextV2 as DBContext
from models.authority import Users, UserRoles
from services.sys_service import init_email
from services.user_services import opt_obj, get_user_list_v2, get_user_list_v3, get_user_noc_addr


class UserHandler(BaseHandler, ABC):

    def get(self, *args, **kwargs):
        count, queryset = get_user_list_v2(**self.params)
        self.write(dict(code=0, msg='获取用户成功', count=count, data=queryset))

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        username = data.get('username', None)
        password = data.get('password', None)
        data['google_key'] = base64.b32encode(
            bytes(str(shortuuid.uuid() + shortuuid.uuid())[:-9], encoding="utf-8")).decode("utf-8")
        if not password:
            data['password'] = gen_md5(f"{username}@123")
        else:
            if not check_password(password):
                return self.write(dict(code=-5, msg='密码复杂度： 超过8位，英文加数字，大小写，没有特殊符号'))
            data['password'] = gen_md5(password)

        res = opt_obj.handle_add(data)
        self.write(res)

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        id_list = data.get('id_list')
        if not id_list:
            return self.write(dict(code=-1, msg='不能为空'))

        with DBContext('w', None, True) as session:
            for user_id in id_list:
                user_info = session.query(Users.username).filter(Users.id == user_id).first()
                if user_info[0] == 'admin':
                    return self.write(dict(code=-2, msg='系统管理员用户无法删除'))

                session.query(Users).filter(Users.id == user_id).delete(synchronize_session=False)
                session.query(UserRoles).filter(UserRoles.user_id == user_id).delete(synchronize_session=False)

        self.write(dict(code=0, msg='删除成功'))

    def put(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        if 'last_login' in data: data.pop('last_login')
        # if 'username' in data: data.pop('username')
        if 'fs_open_id' not in data: data['fs_open_id'] = ''
        res = opt_obj.handle_update(data)
        self.write(res)

    def patch(self, *args, **kwargs):
        """禁用、启用"""
        data = json.loads(self.request.body.decode("utf-8"))
        user_id = str(data.get('user_id', None))
        msg = '用户不存在'

        if not user_id: return self.write(dict(code=-1, msg='不能为空'))

        with DBContext('r') as session:
            user_status = session.query(Users.status).filter(Users.id == user_id, Users.status != 10).first()

        if not user_status:
            return self.write(dict(code=-2, msg=msg))

        if user_status[0] == '0':
            msg = '用户禁用成功'
            new_status = '20'

        elif user_status[0] == '20':
            msg = '用户启用成功'
            new_status = '0'
        else:
            new_status = '10'

        with DBContext('w', None, True) as db:
            db.query(Users).filter(Users.id == user_id, Users.status != '10').update({Users.status: new_status})

        return self.write(dict(code=0, msg=msg))


class UserListHandler(BaseHandler, ABC):
    def get(self, *args, **kwargs):
        count, queryset = get_user_list_v3(**self.params)
        self.write(dict(code=0, msg='获取用户成功', count=count, data=queryset))


class ResetMFAHandler(BaseHandler, ABC):
    def put(self, *args, **kwargs):
        if not self.is_superuser:
            return self.write(dict(code=-1, msg='不是超级管理员，没有权限'))

        data = json.loads(self.request.body.decode("utf-8"))
        user_list = data.get('id_list', None)

        if len(user_list) < 1:
            return self.write(dict(code=-1, msg='用户不能为空'))

        obj = init_email()

        with DBContext('w', None, True) as session:
            for user_id in user_list:
                mfa = base64.b32encode(bytes(str(shortuuid.uuid() + shortuuid.uuid())[:-9], encoding="utf-8")).decode(
                    "utf-8")
                session.query(Users).filter(Users.id == user_id).update({Users.last_ip: '', Users.google_key: mfa})
                mail_to = session.query(Users.email).filter(Users.id == user_id).first()

                obj.send_mail(mail_to[0], '重置MFA', mfa, subtype='plain')
        return self.write(dict(code=0, msg='重置MFA成功', data=mfa))


class ResetPasswordHandler(BaseHandler, ABC):
    def put(self, *args, **kwargs):
        if not self.is_superuser:
            return self.write(dict(code=-1, msg='不是超级管理员，没有权限'))

        data = json.loads(self.request.body.decode("utf-8"))
        user_list = data.get('id_list')

        if len(user_list) < 1:
            return self.write(dict(code=-2, msg='用户不能为空'))

        obj = init_email()

        with DBContext('w', None, True) as session:
            for user_id in user_list:
                md5_password = shortuuid.uuid()
                new_password = gen_md5(md5_password)
                session.query(Users).filter(Users.id == user_id).update({Users.password: new_password})
                mail_to = session.query(Users.email).filter(Users.id == user_id).first()

                obj.send_mail(mail_to[0], '修改密码', md5_password, subtype='plain')

        return self.write(dict(code=0, msg='重置密码成功，新密码已经发送到邮箱', data=md5_password))


class UserAddrHandler(BaseHandler, ABC):
    """
    users_str  可以是用户名  昵称  id
    roles_str   id
    """

    def get(self):
        users_str = self.get_argument('users_str', default=None, strip=True)
        roles_str = self.get_argument('roles_str', default=None, strip=True)
        if not users_str and not roles_str:
            return self.write(dict(code=-1, msg='参数不能为空'))

        res = get_user_noc_addr(users_str, roles_str)
        self.write(res)


user_v4_mg_urls = [
    (r"/v4/user/list/", UserListHandler, {"handle_name": "PAAS-基础功能-查看用户列表", "method": ["GET"]}),
    (r"/v4/user/send_addr/", UserAddrHandler, {"handle_name": "PAAS-基础功能-查看用户联系方式", "method": ["GET"]}),
    (r"/v4/reset_mfa/", ResetMFAHandler, {"handle_name": "PAAS管理-重置二次认证", "method": ["ALL"]}),
    (r"/v4/reset_pw/", ResetPasswordHandler, {"handle_name": "PAAS管理-重置密码", "method": ["ALL"]}),
    (r"/v3/accounts/user/", UserHandler, {"handle_name": "权限中心-用户管理-待废弃", "method": ["ALL"]}),
    (r"/v4/user/", UserHandler, {"handle_name": "权限中心-用户管理V4", "method": ["ALL"]}),
]

if __name__ == "__main__":
    pass
