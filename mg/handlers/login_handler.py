#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
author : shenshuo
date   : 2017年11月21日
role   : 用户登录
"""

import json
from libs.base_handler import BaseHandler
from tornado.web import RequestHandler, HTTPError
from websdk.jwt_token import AuthToken, gen_md5
from websdk.tools import is_mail
from libs.my_verify import MyVerify
from websdk.utils import mail_login
import pyotp
from websdk.db_context import DBContext
from models.admin import Users, Components, RolesComponents, Menus, RoleMenus, UserRoles
from .configs_init import configs_init
from websdk.consts import const
from websdk.cache_context import cache_conn

from websdk.tools import convert


class LoginHandler(RequestHandler):

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        username = data.get('username', None)
        password = data.get('password', None)
        dynamic = data.get('dynamic', None)
        next_url = data.get('next_url', None)

        if not username or not password:
            return self.write(dict(code=-1, msg='账号密码不能为空'))
        if is_mail(username):
            redis_conn = cache_conn()
            configs_init('all')
            login_mail = redis_conn.hget(const.APP_SETTINGS, const.EMAILLOGIN_DOMAIN)
            if login_mail:
                if is_mail(username, login_mail.decode('utf-8')):
                    email = username
                    username = email.split("@")[0]
                    email_server = redis_conn.hget(const.APP_SETTINGS, const.EMAILLOGIN_SERVER).decode('utf-8')
                    if not email_server:
                        return self.write(dict(code=-9, msg='请配置邮箱服务的SMTP服务地址'))

                    if not mail_login(email, password, email_server):
                        return self.write(dict(code=-2, msg='邮箱登陆认证失败'))

                    with DBContext('r') as session:
                        user_info = session.query(Users).filter(Users.email == email, Users.username == username,
                                                                Users.status != '10').first()
                    if not user_info:
                        return self.write(dict(code=-3, msg='邮箱认证通过，请根据邮箱完善用户信息', email=email))

        else:
            with DBContext('r') as session:
                user_info = session.query(Users).filter(Users.username == username, Users.password == gen_md5(password),
                                                        Users.status != '10').first()

            if not user_info:
                return self.write(dict(code=-4, msg='账号密码错误'))

        if user_info.status != '0':
            return self.write(dict(code=-4, msg='账号被禁用'))

        if user_info.superuser == '0':
            is_superuser = True
        else:
            is_superuser = False

        ### 如果被标记为必须动态验证切没有输入动态密钥，则跳转到二维码添加密钥的地方
        if user_info.google_key:
            totp = pyotp.TOTP(user_info.google_key)
            if dynamic:
                if totp.now() != str(dynamic):
                    return self.write(dict(code=-5, msg='MFA错误'))

            else:
                return self.write(dict(code=-8, msg='请输入MFA'))

        user_id = str(user_info.user_id)
        ### 生成token 并写入cookie
        token_info = dict(user_id=user_id, username=user_info.username, nickname=user_info.nickname,
                          is_superuser=is_superuser)
        auth_token = AuthToken()
        auth_key = auth_token.encode_auth_token(**token_info)
        login_ip_list = self.request.headers.get("X-Forwarded-For")
        if login_ip_list:
            login_ip = login_ip_list.split(",")[0]
            with DBContext('w', None, True) as session:
                session.query(Users).filter(Users.username == username).update({Users.last_ip: login_ip})

        self.set_secure_cookie("nickname", user_info.nickname)
        self.set_secure_cookie("username", user_info.username)
        self.set_secure_cookie("user_id", str(user_info.user_id))
        self.set_cookie('auth_key', auth_key, expires_days=1)

        self.write(dict(code=0, auth_key=auth_key.decode(encoding="utf-8"), username=user_info.username,
                        nickname=user_info.nickname, next_url=next_url, msg='登录成功'))
        ### 后端权限写入缓存
        my_verify = MyVerify(user_id)
        my_verify.write_verify()
        ### 前端权限写入缓存
        get_user_rules(user_id)


class LogoutHandler(BaseHandler):
    def get(self):
        self.clear_all_cookies()
        raise HTTPError(401, 'logout')

    def post(self):
        self.clear_all_cookies()
        raise HTTPError(401, 'logout')


class AuthorizationHandler(BaseHandler):
    def get(self, *args, **kwargs):
        user_id = self.get_current_id()
        redis_conn = cache_conn()
        rules = convert(redis_conn.hgetall("{}_rules".format(user_id)))

        self.write(dict(data=dict(rules=rules), code=0, msg='获取前端权限成功'))



def get_user_rules(user_id):
    page_data = {}
    component_data = {}
    with DBContext('r') as session:
        this_menus = session.query(Menus.menu_name
                                   ).outerjoin(RoleMenus, Menus.menu_id == RoleMenus.menu_id).outerjoin(
            UserRoles, RoleMenus.role_id == UserRoles.role_id).filter(UserRoles.user_id == user_id).all()

        this_components = session.query(Components.component_name
                                        ).outerjoin(RolesComponents,
                                                    Components.comp_id == RolesComponents.comp_id).outerjoin(
            UserRoles, RolesComponents.role_id == UserRoles.role_id).filter(UserRoles.user_id == user_id).all()

    for p in this_menus:
        page_data[p[0]] = True
    for c in this_components:
        component_data[c[0]] = True

    ## 插入一个没有权限的
    page_data['all'] = False
    component_data['all'] = False
    redis_conn = cache_conn()
    redis_conn.hmset("{}_rules".format(user_id), dict(page=page_data, component=component_data))


login_urls = [
    (r"/login/", LoginHandler),
    (r"/logout/", LogoutHandler),
    (r"/authorization/", AuthorizationHandler),
]

if __name__ == "__main__":
    pass
