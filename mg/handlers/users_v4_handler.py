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
from websdk2.cache_context import cache_conn
from libs.base_handler import BaseHandler
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.model_utils import model_to_dict
from models.authority import Users, UserRoles
# from models.admin_schemas import get_user_list_v2
from services.user_services import opt_obj, get_user_list_v2, get_user_list_v3


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
        # username = data.get('username', None)
        # nickname = data.get('nickname', None)
        # password = data.get('password', None)
        # department = data.get('department', None)
        # tel = data.get('tel', None)
        # have_token = data.get('have_token', 'no')
        # email = data.get('email', None)
        # status = data.get('status', '0')
        # if not username or not nickname or not department or not tel or not email:
        #     return self.write(dict(code=-1, msg='重要参数不能为空'))
        #
        # with DBContext('r') as session:
        #     user_info1 = session.query(Users).filter(Users.username == username).first()
        #     user_info2 = session.query(Users).filter(Users.tel == tel).first()
        #     user_info3 = session.query(Users).filter(Users.email == email).first()
        #     user_info4 = session.query(Users).filter(Users.nickname == nickname).first()
        #
        # if user_info1:  return self.write(dict(code=-2, msg='用户名已注册'))
        #
        # if user_info2: return self.write(dict(code=-3, msg='手机号已注册'))
        #
        # if user_info3: return self.write(dict(code=-4, msg='邮箱已注册'))
        #
        # if user_info4: return self.write(dict(code=-4, msg='昵称已注册'))
        #
        # if not password:
        #     # password = '7d491c440ba46ca20fde0c5be1377aec'
        #     password = gen_md5(f"{username}@123")
        # else:
        #     if not check_password(password):
        #         return self.write(dict(code=-5, msg='密码复杂度： 超过8位，英文加数字，大小写，没有特殊符号'))
        #     password = gen_md5(password)
        #
        # mfa = base64.b32encode(bytes(str(shortuuid.uuid() + shortuuid.uuid())[:-9], encoding="utf-8")).decode("utf-8")
        #
        # with DBContext('w', None, True) as session:
        #     user = Users(username=username, password=password, nickname=nickname, department=department, tel=tel,
        #                  have_token=have_token, email=email, google_key=mfa, superuser='10', status=status)
        #     session.add(user)
        #     # session.commit()
        #     # user_id = user.id
        #     # session.query(Users).filter(Users.id == user.id).update({"user_id": user_id})
        #
        # self.write(
        #     dict(code=0, msg=f'如果没填写密码 请让管理重置密码，密码信息会发送到注册的邮箱，默认密码为：{username}@123'))

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

        with DBContext('w', None, True) as session:
            for user_id in user_list:
                mfa = base64.b32encode(bytes(str(shortuuid.uuid() + shortuuid.uuid())[:-9], encoding="utf-8")).decode(
                    "utf-8")
                session.query(Users).filter(Users.id == user_id).update({Users.last_ip: '', Users.google_key: mfa})

        return self.write(dict(code=0, msg='重置MFA成功', data=mfa))


class ResetPasswordHandler(BaseHandler, ABC):
    def put(self, *args, **kwargs):
        if not self.is_superuser:
            return self.write(dict(code=-1, msg='不是超级管理员，没有权限'))

        data = json.loads(self.request.body.decode("utf-8"))
        user_list = data.get('id_list')

        if len(user_list) < 1:
            return self.write(dict(code=-2, msg='用户不能为空'))

        with DBContext('w', None, True) as session:
            for user_id in user_list:
                md5_password = shortuuid.uuid()
                new_password = gen_md5(md5_password)
                session.query(Users).filter(Users.id == user_id).update({Users.password: new_password})
                # mail_to = session.query(Users.email).filter(Users.user_id == user_id).first()

                # obj.send_mail(mail_to[0], '修改密码', md5_password, subtype='plain')

        return self.write(dict(code=0, msg='重置密码成功，新密码已经发送到邮箱', data=md5_password))


user_v4_mg_urls = [
    (r"/v4/user/list/", UserListHandler, {"handle_name": "权限中心-用户列表"}),
    (r"/v4/reset_mfa/", ResetMFAHandler, {"handle_name": "PAAS-重置二次认证"}),
    (r"/v4/reset_pw/", ResetPasswordHandler, {"handle_name": "PAAS-重置密码"}),
    (r"/v4/user/", UserHandler, {"handle_name": "权限中心-用户管理"}),
]

if __name__ == "__main__":
    pass
