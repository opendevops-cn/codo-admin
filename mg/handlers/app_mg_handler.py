#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2018/10/29
Desc    : 应用相关逻辑
"""

import json
import shortuuid
import base64
import time, datetime
from tornado.web import RequestHandler
from websdk.jwt_token import gen_md5
from websdk.tools import check_password
from libs.base_handler import BaseHandler
from models.admin import OperationRecord, Users, model_to_dict
from websdk.db_context import DBContext
from websdk.base_handler import LivenessProbe
from dateutil.relativedelta import relativedelta
#
from websdk.utils import SendMail
from .configs_init import configs_init
from websdk.consts import const
from websdk.tools import convert
from websdk.cache_context import cache_conn
from websdk.jwt_token import AuthToken


class LogHandler(BaseHandler):
    def get(self, *args, **kwargs):
        page_size = self.get_argument('page', default=1, strip=True)
        limit = self.get_argument('limit', default=10, strip=True)
        key = self.get_argument('key', default=None, strip=True)
        value = self.get_argument('value', default=None, strip=True)
        start_date = self.get_argument('start_date', default=None, strip=True)
        end_date = self.get_argument('end_date', default=None, strip=True)
        limit_start = (int(page_size) - 1) * int(limit)

        if not start_date:
            start_date = datetime.date.today() - relativedelta(months=+1)
        if not end_date:
            end_date = datetime.date.today() + datetime.timedelta(days=1)

        start_time_tuple = time.strptime(str(start_date), '%Y-%m-%d')
        end_time_tuple = time.strptime(str(end_date), '%Y-%m-%d')
        log_list = []

        with DBContext('r') as session:
            if key and value:
                count = session.query(OperationRecord).filter(OperationRecord.ctime > start_time_tuple,
                                                              OperationRecord.ctime < end_time_tuple).filter_by(
                    **{key: value}).count()
                log_info = session.query(OperationRecord).filter(OperationRecord.ctime > start_time_tuple,
                                                                 OperationRecord.ctime < end_time_tuple).filter_by(
                    **{key: value}).order_by(-OperationRecord.ctime)
            else:
                count = session.query(OperationRecord).filter(OperationRecord.ctime > start_time_tuple,
                                                              OperationRecord.ctime < end_time_tuple).count()
                log_info = session.query(OperationRecord).filter(OperationRecord.ctime > start_time_tuple,
                                                                 OperationRecord.ctime < end_time_tuple).order_by(
                    -OperationRecord.ctime).offset(limit_start).limit(int(limit))

        for msg in log_info:
            data_dict = model_to_dict(msg)
            data_dict['ctime'] = str(data_dict['ctime'])
            log_list.append(data_dict)

        return self.write(dict(code=0, msg='获取日志成功', count=count, data=log_list))


class UserRegisterHandler(RequestHandler):
    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        username = data.get('username', None)
        nickname = data.get('nickname', None)
        password = data.get('password', None)
        department = data.get('department', None)
        tel = data.get('tel', None)
        wechat = data.get('wechat', None)
        no = data.get('no', None)
        email = data.get('email', None)
        user_state = data.get('user_state', '20')
        if not username or not nickname or not department or not tel or not wechat or not no or not email:
            return self.write(dict(code=-1, msg='参数不能为空'))

        with DBContext('r') as session:
            user_info1 = session.query(Users).filter(Users.username == username).first()
            user_info2 = session.query(Users).filter(Users.tel == tel).first()
            user_info3 = session.query(Users).filter(Users.email == email).first()
            user_info4 = session.query(Users).filter(Users.nickname == nickname).first()

        if user_info1:
            return self.write(dict(code=-2, msg='用户名已注册'))

        if user_info2:
            return self.write(dict(code=-3, msg='手机号已注册'))

        if user_info3:
            return self.write(dict(code=-4, msg='邮箱已注册'))

        if user_info4:
            return self.write(dict(code=-4, msg='昵称已注册'))

        if not password:
            the_password = shortuuid.uuid()
        else:
            if not check_password(password):
                return self.write(dict(code=-5, msg='密码复杂度必须为： 超过8位，包含数字，大小写字母 等'))
            the_password = password

        password = gen_md5(the_password)

        mfa = base64.b32encode(bytes(str(shortuuid.uuid() + shortuuid.uuid())[:-9], encoding="utf-8")).decode("utf-8")

        redis_conn = cache_conn()
        configs_init('all')
        config_info = redis_conn.hgetall(const.APP_SETTINGS)
        config_info = convert(config_info)
        obj = SendMail(mail_host=config_info.get(const.EMAIL_HOST), mail_port=config_info.get(const.EMAIL_PORT),
                       mail_user=config_info.get(const.EMAIL_HOST_USER),
                       mail_password=config_info.get(const.EMAIL_HOST_PASSWORD),
                       mail_ssl=True if config_info.get(const.EMAIL_USE_SSL) == '1' else False,
                       mail_tls=True if config_info.get(const.EMAIL_USE_TLS) == '1' else False)

        with DBContext('w', None, True) as session:
            session.add(Users(username=username, password=password, nickname=nickname, department=department, tel=tel,
                              wechat=wechat, no=no, email=email, google_key=mfa, superuser='10', status=user_state))

        obj.send_mail(email, '用户注册成功', '密码为：{} \n MFA：{}'.format(the_password, mfa), subtype='plain')
        return self.write(dict(code=0, msg='恭喜你！ 注册成功，赶紧联系管理员给你添加权限吧！！！', mfa=mfa))


class PasswordHandler(BaseHandler):

    def patch(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        old_password = data.get('old_password', None)
        new_password1 = data.get('new_password1', None)
        new_password2 = data.get('new_password2', None)
        username = self.get_current_user()
        if not check_password(new_password1):
            return self.write(dict(code=-5, msg='密码复杂度必须为： 超过8位，包含数字，大小写字母 等'))

        if not old_password or not new_password1 or not new_password2 or not username:
            return self.write(dict(code=-1, msg='不能有空值'))

        if new_password1 != new_password2:
            return self.write(dict(code=-2, msg='新密码输入不一致'))

        with DBContext('r') as session:
            user_info = session.query(Users).filter(Users.username == username).first()

        if user_info.password != gen_md5(old_password):
            return self.write(dict(code=-3, msg='密码错误'))

        with DBContext('w', None, True) as session:
            session.query(Users).filter(Users.username == username).update({Users.password: gen_md5(new_password1)})

        return self.write(dict(code=0, msg='修改成功'))


class ResetMFAHandler(BaseHandler):
    def put(self, *args, **kwargs):
        if not self.is_superuser:
            return self.write(dict(code=-1, msg='不是超级管理员，没有权限'))

        data = json.loads(self.request.body.decode("utf-8"))
        user_list = data.get('user_list', None)

        if len(user_list) < 1:
            return self.write(dict(code=-1, msg='用户不能为空'))

        redis_conn = cache_conn()
        configs_init('all')
        config_info = redis_conn.hgetall(const.APP_SETTINGS)
        config_info = convert(config_info)
        obj = SendMail(mail_host=config_info.get(const.EMAIL_HOST), mail_port=config_info.get(const.EMAIL_PORT),
                       mail_user=config_info.get(const.EMAIL_HOST_USER),
                       mail_password=config_info.get(const.EMAIL_HOST_PASSWORD),
                       mail_ssl=True if config_info.get(const.EMAIL_USE_SSL) == '1' else False,
                       mail_tls=True if config_info.get(const.EMAIL_USE_TLS) == '1' else False)

        with DBContext('w', None, True) as session:
            for user_id in user_list:
                mfa = base64.b32encode(bytes(str(shortuuid.uuid() + shortuuid.uuid())[:-9], encoding="utf-8")).decode(
                    "utf-8")
                session.query(Users).filter(Users.user_id == user_id).update({Users.last_ip: '', Users.google_key: mfa})
                mail_to = session.query(Users.email).filter(Users.user_id == user_id).first()

                obj.send_mail(mail_to[0], '重置MFA', mfa, subtype='plain')

        return self.write(dict(code=0, msg='重置MFA成功，新的MFA已经发送到邮箱'))


class ResetPasswordHandler(BaseHandler):
    def put(self, *args, **kwargs):
        if not self.is_superuser:
            return self.write(dict(code=-1, msg='不是超级管理员，没有权限'))

        data = json.loads(self.request.body.decode("utf-8"))
        user_list = data.get('user_list', None)

        if len(user_list) < 1:
            return self.write(dict(code=-2, msg='用户不能为空'))

        redis_conn = cache_conn()
        configs_init('all')
        config_info = redis_conn.hgetall(const.APP_SETTINGS)
        config_info = convert(config_info)
        obj = SendMail(mail_host=config_info.get(const.EMAIL_HOST), mail_port=config_info.get(const.EMAIL_PORT),
                       mail_user=config_info.get(const.EMAIL_HOST_USER),
                       mail_password=config_info.get(const.EMAIL_HOST_PASSWORD),
                       mail_ssl=True if config_info.get(const.EMAIL_USE_SSL) == '1' else False,
                       mail_tls=True if config_info.get(const.EMAIL_USE_TLS) == '1' else False)

        with DBContext('w', None, True) as session:
            for user_id in user_list:
                md5_password = shortuuid.uuid()
                new_password = gen_md5(md5_password)
                session.query(Users).filter(Users.user_id == user_id).update(
                    {Users.password: new_password})
                mail_to = session.query(Users.email).filter(Users.user_id == user_id).first()

                obj.send_mail(mail_to[0], '修改密码', md5_password, subtype='plain')
        return self.write(dict(code=0, msg='重置密码成功，新密码已经发送到邮箱'))


class TokenHandler(BaseHandler):
    ### 获取长期令牌
    def put(self, *args, **kwargs):
        if not self.is_superuser:
            return self.write(dict(code=-1, msg='不是超级管理员，没有权限'))

        data = json.loads(self.request.body.decode("utf-8"))
        user_list = data.get('user_list', None)

        if len(user_list) != 1:
            return self.write(dict(code=-2, msg='一次只能选择一个用户，且不能为空'))

        user_id = user_list[0]
        with DBContext('r') as session:
            user_info = session.query(Users).filter(Users.user_id == user_id).first()

        ### 生成token
        if user_info.superuser == '0':
            is_superuser = True
        else:
            is_superuser = False

        token_info = dict(user_id=user_id, username=user_info.username, nickname=user_info.nickname,
                          is_superuser=is_superuser, exp_time=1100)
        auth_token = AuthToken()
        auth_key = auth_token.encode_auth_token(**token_info)

        redis_conn = cache_conn()
        configs_init('all')
        config_info = redis_conn.hgetall(const.APP_SETTINGS)
        config_info = convert(config_info)
        obj = SendMail(mail_host=config_info.get(const.EMAIL_HOST), mail_port=config_info.get(const.EMAIL_PORT),
                       mail_user=config_info.get(const.EMAIL_HOST_USER),
                       mail_password=config_info.get(const.EMAIL_HOST_PASSWORD),
                       mail_ssl=True if config_info.get(const.EMAIL_USE_SSL) == '1' else False,
                       mail_tls=True if config_info.get(const.EMAIL_USE_TLS) == '1' else False)

        with DBContext('w', None, True) as session:
            mail_to = session.query(Users.email).filter(Users.user_id == self.get_current_id()).first()

        if mail_to[0] == user_info.email:
            obj.send_mail(mail_to[0], '令牌，有效期三年', auth_key.decode(), subtype='plain')
        else:
            obj.send_mail(mail_to[0], '令牌，有效期三年', auth_key.decode(), subtype='plain')
            obj.send_mail(user_info.email, '令牌，有效期三年', auth_key.decode(), subtype='plain')
        return self.write(dict(code=0, msg='Token已经发送到邮箱', data=auth_key.decode()))


app_mg_urls = [
    (r"/v2/app/opt_log/", LogHandler),
    (r"/register/", UserRegisterHandler),
    (r"/v2/accounts/password/", PasswordHandler),
    (r"/v2/accounts/reset_mfa/", ResetMFAHandler),
    (r"/v2/accounts/reset_pw/", ResetPasswordHandler),
    (r"/v2/accounts/token/", TokenHandler),
    (r"/are_you_ok/", LivenessProbe),
]

if __name__ == "__main__":
    pass
