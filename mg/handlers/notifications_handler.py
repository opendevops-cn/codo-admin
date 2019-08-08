#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2018/11/2
Desc    : 发送通知 API
"""

import json
from tornado.concurrent import run_on_executor
from concurrent.futures import ThreadPoolExecutor
from libs.base_handler import BaseHandler
from tornado import gen
from websdk.utils import SendMail, SendSms
from .configs_init import configs_init
from websdk.consts import const
from websdk.tools import convert
from websdk.cache_context import cache_conn


class SendMailHandler(BaseHandler):
    @gen.coroutine
    def get(self, *args, **kwargs):
        return self.write(dict(code=-1, msg='Hello, SendMail, Please use POST SendMail!'))

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
        ### 发送邮件
        data = json.loads(self.request.body.decode('utf-8'))
        to_list = data.get('to_list', None)
        subject = data.get('subject', None)
        content = data.get('content', None)
        subtype = data.get('subtype', None)
        att = data.get('att', None)
        redis_conn = cache_conn()
        if not to_list and not subject and not content:
            return self.write(dict(code=-1, msg='收件人、邮件标题、邮件内容不能为空'))

        configs_init('all')
        config_info = redis_conn.hgetall(const.APP_SETTINGS)
        config_info = convert(config_info)
        send_list = [to_list, subject, content, subtype, att]
        res = yield self.send_mail_pool(send_list, config_info)
        return self.write(res)


class SendSmsHandler(BaseHandler):
    _thread_pool = ThreadPoolExecutor(5)

    @run_on_executor(executor='_thread_pool')
    def send_sms_pool(self, *args_list):
        send_list = args_list[0]
        config_info = args_list[1]
        try:
            obj = SendSms(config_info.get(const.SMS_REGION), config_info.get(const.SMS_DOMAIN),
                          config_info.get(const.SMS_PRODUCT_NAME), config_info.get(const.SMS_ACCESS_KEY_ID),
                          config_info.get(const.SMS_ACCESS_KEY_SECRET))

            params = json.dumps(send_list[1])
            sms_response = obj.send_sms(send_list[0], template_param=params, sign_name=send_list[2],
                                        template_code=send_list[3])
            sms_response = json.loads(sms_response.decode('utf-8'))
            if sms_response.get("Message") == "OK":
                return dict(code=0, msg='短信发送成功')
            else:
                return dict(code=-2, msg='短信发送失败{}'.format(str(sms_response)))

        except Exception as e:
            return dict(code=-1, msg='短信发送失败 {}'.format(str(e)))

    @gen.coroutine
    def get(self, *args, **kwargs):
        return self.write(dict(code=-1, msg='Hello, Send sms, Please use POST !'))

    @gen.coroutine
    def post(self, *args, **kwargs):
        ### 发送短信
        data = json.loads(self.request.body.decode('utf-8'))
        phone = data.get('phone', None)
        msg = data.get('msg', None)  # json格式 对应短信模板里设置的参数
        template_code = data.get('template_code', None)
        sign_name = data.get('sign_name', 'OPS')
        redis_conn = cache_conn()
        if not phone and not msg and not template_code:
            return self.write(dict(code=-1, msg='收件人、邮件标题、邮件内容不能为空'))

        configs_init('all')
        config_info = redis_conn.hgetall(const.APP_SETTINGS)
        config_info = convert(config_info)
        #
        send_list = [phone, msg, sign_name, template_code]
        res = yield self.send_sms_pool(send_list, config_info)
        return self.write(res)


notifications_urls = [
    (r'/v2/notifications/mail/', SendMailHandler),
    (r'/v2/notifications/sms/', SendSmsHandler),
]

if __name__ == "__main__":
    pass
