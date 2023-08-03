#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023/07/10 15:14
Desc    : 解释一下吧
"""
import base64
import json
from sqlalchemy import or_
from websdk2.consts import const
from websdk2.utils import SendMail
from websdk2.cache_context import cache_conn
from websdk2.tools import convert
from websdk2.db_context import DBContextV2 as DBContext
from models.paas_model import SystemSettings
from websdk2.utils.cc_crypto import AESCryptoV3
from websdk2.model_utils import CommonOptView

mc = AESCryptoV3()
opt_obj = CommonOptView(SystemSettings)

init_conf = {
    'feishu_access_url': 'https://passport.feishu.cn/suite/passport/oauth/token',
    'feishu_user_info_url': 'https://passport.feishu.cn/suite/passport/oauth/userinfo'
}


def _get_value(value: str = None):
    if not value or value == 'all':
        return True

    if value == 'email':
        return or_(
            SystemSettings.name.like(f'EMAIL_%'),
        )
    elif value == 'ldap':
        return or_(
            SystemSettings.name.like(f'LDAP_%'),
        )

    elif value == 'feishu':
        return or_(
            SystemSettings.name.like(f'feishu_%'),
        )

    return or_(
        SystemSettings.name.like(f'%{value}%'),
    )


def get_sys_conf_dict(**params) -> dict:
    category = params.get('category', 'all')

    with DBContext('r') as session:
        __info = session.query(SystemSettings).filter(_get_value(category)).all()
    conf_dict = dict()
    for i in __info:
        if i.is_secret == 'n':
            conf_dict[i.name] = i.value
    return dict(msg='获取成功', code=0, data=conf_dict)


def get_sys_conf_dict_for_me(**params) -> dict:
    category = params.get('category', 'all')
    conf_dict = dict()
    redis_conn = cache_conn()
    __dict = redis_conn.hgetall(const.APP_SETTINGS)

    for k, v in convert(__dict).items():
        if k.startswith(f'{category.upper()}_') or k.startswith(f'{category.lower()}_'):
            conf_dict[k] = v
            if 'secret' in k or 'SECRET' in k or 'PASSWORD' in k or 'password' in k:
                conf_dict[k] = base64.b64decode(mc.my_decrypt(v)).decode()
    conf_dict.update(**init_conf)
    return conf_dict


def settings_add(data: dict) -> dict:
    with DBContext('w', None, True) as session:
        for k, v in data.items():
            if k and v:
                session.query(SystemSettings).filter(SystemSettings.name == k).delete(synchronize_session=False)
        for k, v in data.items():
            if isinstance(v, dict):
                v = json.dumps(v)
            if 'secret' in k or 'SECRET' in k or 'PASSWORD' in k or 'password' in k:
                is_secret = 'y'
                v = mc.my_encrypt(base64.b64encode(v.encode()).decode('utf-8'))
            else:
                is_secret = 'n'
            session.add(SystemSettings(name=k, value=v, is_secret=is_secret))

        __info = session.query(SystemSettings).all()

        # 刷新缓存
        conf_dict = {i.name: i.value for i in __info}
    redis_conn = cache_conn()
    redis_conn.hmset(const.APP_SETTINGS, conf_dict)
    return dict(code=0, msg='配置成功')


def init_email():
    email_conf = get_sys_conf_dict_for_me(**dict(category='email'))
    obj = SendMail(mail_host=email_conf.get(const.EMAIL_HOST),
                   mail_port=email_conf.get(const.EMAIL_PORT),
                   mail_user=email_conf.get(const.EMAIL_HOST_USER),
                   mail_password=email_conf.get(const.EMAIL_HOST_PASSWORD),
                   mail_ssl=True if email_conf.get(const.EMAIL_USE_SSL) == 'yes' else False,
                   mail_tls=True if email_conf.get(const.EMAIL_USE_TLS) == 'yes' else False)
    return obj
