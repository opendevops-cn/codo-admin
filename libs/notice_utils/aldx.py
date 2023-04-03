#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2021/1/13 16:00 
Desc    : 阿里云发送短信
"""

from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest


class AlSendSms(object):
    def __init__(self, **kwargs):
        self.acs_client = AcsClient(kwargs.get('sms_access_key_id'), kwargs.get('sms_access_key_secret'),
                                    kwargs.get('region', 'cn-hangzhou'))

    @staticmethod
    def sms_request():
        request = CommonRequest()
        request.set_accept_format('json')
        request.set_domain('dysmsapi.aliyuncs.com')
        request.set_method('POST')
        request.set_protocol_type('https')  # https | http
        request.set_version('2017-05-25')
        request.set_action_name('SendSms')
        request.add_query_param('RegionId', "cn-hangzhou")
        return request

    def send(self, **kwargs):
        notice_conf = kwargs.get('__conf')
        if not notice_conf: return False
        if not isinstance(notice_conf, dict): return False
        template_code = notice_conf.get('template_code')
        sign_name = notice_conf.get('sign_name')
        send_addr = kwargs.get('send_addr')

        template_param = kwargs.get('msg', {})

        ###电话号码
        phone_numbers = send_addr.get('tel', [])
        if isinstance(phone_numbers, list): phone_numbers = ','.join(phone_numbers)
        ###

        request = self.sms_request()
        request.add_query_param('PhoneNumbers', phone_numbers)
        request.add_query_param('SignName', sign_name)
        request.add_query_param('TemplateCode', template_code)
        request.add_query_param('TemplateParam', template_param)

        response = self.acs_client.do_action_with_exception(request)
        return response
