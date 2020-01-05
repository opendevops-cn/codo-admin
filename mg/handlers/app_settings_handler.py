#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2018/12/7
Desc    : 系统配置API
"""

import time
import json
from tornado import gen
from tornado.concurrent import run_on_executor
from concurrent.futures import ThreadPoolExecutor
from libs.base_handler import BaseHandler
from websdk.ldap import LdapApi
from websdk.utils import SendMail, SendSms
from websdk.consts import const
from websdk.tools import convert
from websdk.cache_context import cache_conn

from .configs_init import configs_init
from models.app_config import AppSettings
from models.admin import Users
from websdk.db_context import DBContext


class AppSettingsHandler(BaseHandler):
    @gen.coroutine
    def get(self, setting_key):
        return_code = configs_init(setting_key)
        return self.write(return_code)

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode('utf-8'))
        settings_key = list(data.keys())

        with DBContext('w', None, True) as session:
            for k in settings_key:
                session.query(AppSettings).filter(AppSettings.name == k).delete(synchronize_session=False)
            for s in settings_key:
                new_list = AppSettings(name=s, value=data.get(s))
                session.add(new_list)
            session.commit()
        return self.write(dict(code=0, msg='获取配置成功'))


class CheckSettingsHandler(BaseHandler):

    _thread_pool = ThreadPoolExecutor(5)
    @run_on_executor(executor='_thread_pool')
    def send_mail_pool(self, *args_list):
        send_list = args_list[0]
        config_info = args_list[1]
        try:
            obj = SendMail(mail_host=config_info.get(const.EMAIL_HOST),
                           mail_port=config_info.get(const.EMAIL_PORT),
                           mail_user=config_info.get(const.EMAIL_HOST_USER),
                           mail_password=config_info.get(const.EMAIL_HOST_PASSWORD),
                           mail_ssl=True if config_info.get(const.EMAIL_USE_SSL) == '1' else False,
                           mail_tls=True if config_info.get(const.EMAIL_USE_TLS) == '1' else False)

            obj.send_mail(send_list[0], send_list[1], send_list[2], subtype=send_list[3], att=send_list[4])
            return dict(code=0, msg='邮件发送成功')

        except Exception as e:
            return dict(code=-1, msg='邮件发送失败 {}'.format(str(e)))

    @gen.coroutine
    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode('utf-8'))
        check_key = data.get('check_key')
        user_id = self.get_current_id()

        redis_conn = cache_conn()
        config_info = redis_conn.hgetall(const.APP_SETTINGS)
        config_info = convert(config_info)

        if check_key == 'EMAIL':
            with DBContext('r') as session:
                mail_to = session.query(Users.email).filter(Users.user_id == user_id).first()

            send_list = [mail_to[0], 'OPS测试邮件',  '测试发送邮件成功', 'plain', None]
            res = yield self.send_mail_pool(send_list, config_info)
            return self.write(res)

        elif check_key == 'SMS':
            obj = SendSms(config_info.get(const.SMS_REGION), config_info.get(const.SMS_DOMAIN),
                          config_info.get(const.SMS_PRODUCT_NAME), config_info.get(const.SMS_ACCESS_KEY_ID),
                          config_info.get(const.SMS_ACCESS_KEY_SECRET))

            query_response = obj.query_send_detail('', '11111111111', 1, 1, time.strftime("%Y%m%d", time.localtime()))
            query_response = json.loads(query_response.decode('utf-8'))
            if query_response.get("Message") == "OK":
                return self.write(dict(code=0, msg='测试短信成功'))
            else:
                return self.write(dict(code=-2, msg='测试短信失败{}'.format(str(query_response))))
        elif check_key == 'LDAP':
            ldap_ssl = True if config_info.get(const.LDAP_USE_SSL) == '1' else False

            obj = LdapApi(config_info.get(const.LDAP_SERVER_HOST), config_info.get(const.LDAP_ADMIN_DN),
                          config_info.get(const.LDAP_ADMIN_PASSWORD), int(config_info.get(const.LDAP_SERVER_PORT, 389)),
                          ldap_ssl)

            if obj.ldap_server_test():
                return self.write(dict(code=0, msg='LDAP连接测试成功'))
            else:
                return self.write(dict(code=-1, msg='LDAP连接测试不成功，请仔细检查配置'))

        else:
            return self.write(dict(code=-1, msg='未知测试项目'))


app_settings_urls = [
    (r'/v2/sysconfig/settings/([\w-]*)/', AppSettingsHandler),
    (r'/v2/sysconfig/check/', CheckSettingsHandler),
]

if __name__ == "__main__":
    pass
