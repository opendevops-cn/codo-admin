#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2021/1/11 15:38 
Desc    : 解释一下吧
"""

import json
from abc import ABC
from libs.base_handler import BaseHandler
from websdk2.jwt_token import AuthToken, gen_md5
from websdk2.db_context import DBContextV2 as DBContext
from models.authority import UserToken, Users
from services.token_service import get_token_list_for_api
from services.sys_service import init_email
from datetime import datetime, timedelta


class TokenHandler(BaseHandler, ABC):

    def get(self, *args, **kwargs):
        if not self.is_superuser:
            return self.write(dict(code=-1, msg='不是超级管理员，没有权限'))
        res = get_token_list_for_api(self.params)

        return self.write(res)

    # 获取长期令牌
    def post(self, *args, **kwargs):
        if not self.is_superuser: return self.write(dict(code=-1, msg='不是超级管理员，没有权限'))

        data = json.loads(self.request.body.decode("utf-8"))
        user_list = data.get('id_list', None)

        if len(user_list) != 1:  return self.write(dict(code=-2, msg='一次只能选择一个用户，且不能为空'))

        user_id = user_list[0]
        with DBContext('r') as session:
            user_info = session.query(Users).filter(Users.id == user_id).first()

            # if user_info.superuser == '0':
            #     return self.write(dict(code=-4, msg='超级用户不能生成长期令牌'))

        # 生成token
        is_superuser = True if user_info.superuser == '0' else False

        token_info = dict(user_id=user_id, username=user_info.username, nickname=user_info.nickname,
                          is_superuser=is_superuser, exp_days=1825)
        auth_token = AuthToken()
        auth_key = auth_token.encode_auth_token_v2(**token_info)
        if isinstance(auth_key, bytes): auth_key = auth_key.decode()

        # 入库
        with DBContext('w', None, True) as session:
            token_count = session.query(UserToken).filter(UserToken.user_id == user_id,
                                                          UserToken.status != '10').count()
            if token_count >= 3:  return self.write(dict(code=-5, msg='不能拥有太多的token'))

            expire_time = datetime.now() + timedelta(days=+360 * 5)
            session.add(UserToken(user_id=int(user_id), nickname=user_info.nickname, token=auth_key,
                                  expire_time=expire_time, token_md5=gen_md5(auth_key)))

        obj = init_email()

        with DBContext('w', None, True) as session:
            mail_to = session.query(Users.email).filter(Users.id == self.get_current_id()).first()

        if mail_to[0] == user_info.email:
            obj.send_mail(mail_to[0], '令牌，有效期五年', auth_key, subtype='plain')
        else:
            obj.send_mail(mail_to[0], '令牌，有效期五年', auth_key, subtype='plain')
            obj.send_mail(user_info.email, '令牌，有效期五年', auth_key, subtype='plain')
        return self.write(dict(code=0, msg='Token已经发送到邮箱', data=auth_key))

    def patch(self, *args, **kwargs):
        if not self.is_superuser: return self.write(dict(code=-1, msg='不是超级管理员，没有权限'))

        """禁用、启用"""
        data = json.loads(self.request.body.decode("utf-8"))
        token_id = data.get('token_id', None)
        msg = 'token不存在'

        if not token_id:   return self.write(dict(code=-1, msg='不能为空'))

        with DBContext('r') as session:
            t_status = session.query(UserToken.status).filter(UserToken.token_id == token_id,
                                                              UserToken.status != 10).first()

        if not t_status:   return self.write(dict(code=-2, msg=msg))

        if t_status[0] == '0':
            msg = '禁用成功'
            new_status = '20'

        elif t_status[0] == '20':
            msg = '启用成功'
            new_status = '0'
        else:
            msg = '状态不符合预期，删除'
            new_status = '10'

        with DBContext('w', None, True) as session:
            session.query(UserToken).filter(UserToken.token_id == token_id, UserToken.status != '10').update(
                {UserToken.status: new_status})

        return self.write(dict(code=0, msg=msg))

    def put(self, *args, **kwargs):
        if not self.is_superuser: return self.write(dict(code=-1, msg='不是超级管理员，没有权限'))

        data = json.loads(self.request.body.decode("utf-8"))
        token_id = data.get('token_id')
        details = data.get('details')
        if not token_id:   return self.write(dict(code=-2, msg='不能为空'))

        with DBContext('w', None, True) as session:
            session.query(UserToken).filter(UserToken.token_id == token_id).update({UserToken.details: details})

        return self.write(dict(code=0, msg="修改备注信息完成"))

    def delete(self, *args, **kwargs):
        if not self.is_superuser: return self.write(dict(code=-1, msg='不是超级管理员，没有权限'))
        data = json.loads(self.request.body.decode("utf-8"))
        token_id = data.get('token_id')
        if not token_id:   return self.write(dict(code=-1, msg='不能为空'))

        with DBContext('w', None, True) as session:
            session.query(UserToken).filter(UserToken.token_id == token_id).update({UserToken.status: '10'})

        return self.write(dict(code=0, msg='删除成功'))


token_urls = [
    (r"/v4/token/", TokenHandler, {"handle_name": "权限中心-令牌管理", "method": ["ALL"]}),

]

if __name__ == "__main__":
    pass
