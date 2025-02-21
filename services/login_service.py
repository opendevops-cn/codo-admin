#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
author : shenshuo
date   : 2017年11月21日
role   : 用户登录
"""

import logging
import base64
import pyotp
from typing import *
from shortuuid import uuid
from datetime import datetime
from websdk2.jwt_token import AuthToken, gen_md5
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.consts import const
from websdk2.ldap import LdapApiV4
from libs.login_by_feishu import FeiShuAuth
from libs.login_by_other import OtherAuthV3
from services.sys_service import get_sys_conf_dict_for_me
from models.authority import Users


async def base_verify(username, password) -> Optional[Users]:
    with DBContext('r') as session:
        user_info: Optional[Users] = session.query(Users).filter(Users.username == username,
                                                                 Users.password == gen_md5(password),
                                                                 Users.status != '10').first()
    return user_info


async def ldap_verify(username, password):
    try:
        # password = base64.b64decode(password).decode("utf-8")
        # password = base64.b64decode(password).decode("utf-8")

        ldap_conf = get_sys_conf_dict_for_me(**dict(category='ldap'))
        if ldap_conf.get(const.LDAP_ENABLE) == 'no':
            return dict(code=-5, msg='请联系管理员启用LDAP登录')

        if not ldap_conf:
            return dict(code=-5, msg='请补全LDAP信息')

        try:
            obj = LdapApiV4(ldap_conf.get(const.LDAP_SERVER_HOST), ldap_conf.get(const.LDAP_ADMIN_DN),
                            ldap_conf.get(const.LDAP_ADMIN_PASSWORD), ldap_conf.get(const.LDAP_USE_SSL))

            ldap_pass_info = obj.ldap_auth(username, password, ldap_conf.get(const.LDAP_SEARCH_BASE),
                                           ldap_conf.get(const.LDAP_ATTRIBUTES),
                                           ldap_conf.get(const.LDAP_SEARCH_FILTER))
        except Exception as err:
            logging.error(f"LDAP信息出错 {err}")
            return dict(code=-4, msg='LDAP信息出错')

        if not ldap_pass_info[0]:
            return dict(code=-4, msg='LDAP认证账号密码错误')

        with DBContext('w') as session:
            user_info = session.query(Users).filter(Users.username == username, Users.status != '10').first()

            if not user_info:
                # 没有账户就自动注册一个
                mfa = base64.b32encode(bytes(str(uuid() + uuid())[:-9], encoding="utf-8")).decode("utf-8")
                attr_dict = ldap_pass_info[1]

                session.add(Users(username=attr_dict.get('username'),
                                  nickname=attr_dict.get('nickname', username),
                                  email=attr_dict.get('email'),
                                  password=gen_md5(password),
                                  tel='',
                                  google_key=mfa))
        return user_info

    except Exception as err:
        logging.error(f"LDAP信息出错 {err}")
        return {'code': -4, 'msg': 'LDAP信息出错'}


async def feishu_verify(**kwargs) -> Optional[Users]:
    return FeiShuAuth(**kwargs)()


async def uc_verify(**kwargs) -> Optional[Users]:
    try:
        return OtherAuthV3(**kwargs)()
    except Exception as err:
        logging.error(err)
        return None


def update_login_ip(user_id: str, login_ip_list: str):
    try:
        if not isinstance(user_id, str) or not isinstance(login_ip_list, str):
            raise ValueError("Invalid input")

        login_ip = login_ip_list.split(",")[0]
        with DBContext('w', None, True) as session:
            user = session.query(Users).filter(Users.id == user_id).first()
            if user:
                user.last_ip = login_ip
                user.last_login = datetime.now()
                session.commit()
            else:
                logging.error(f"用户不存在: {user_id}")

    except Exception as err:
        logging.error(f"记录登录IP失败: {err}")


async def generate_token(user_info, dynamic=None):
    mfa_key = None
    auth_token = AuthToken()
    user_id = str(user_info.id)

    if user_info.google_key:
        if not dynamic:
            return dict(code=66, msg='跳转二次认证')
        if pyotp.TOTP(user_info.google_key).now() != str(dynamic):
            return dict(code=-5, msg='MFA错误')
        mfa_key = auth_token.encode_mfa_token(user_id=user_id, email=user_info.email)
        # self.set_cookie("mfa_key", mfa_key, expires_days=1, httponly=True)

    token_info = dict(user_id=user_id, username=user_info.username, nickname=user_info.nickname,
                      email=user_info.email, is_superuser=True if user_info.superuser == '0' else False)

    auth_key = auth_token.encode_auth_token_v2(**token_info)
    if isinstance(auth_key, bytes):
        auth_key = auth_key.decode()
    return dict(auth_key=auth_key, mfa_key=mfa_key)


def get_user_info_for_id(user_id: int) -> Optional[Users]:
    with DBContext('r') as session:
        user_info: Optional[Users] = session.query(Users).filter(Users.id == user_id,
                                                                 Users.status == "0").first()
    return user_info
