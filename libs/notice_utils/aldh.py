#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2021/1/21 15:09 
Desc    : 阿里云发送电话
"""

import json
from aliyunsdkcore.client import AcsClient
from aliyunsdkdyvmsapi.request.v20170525.SingleCallByTtsRequest import SingleCallByTtsRequest


class AlSendTTS(object):
    def __init__(self, **kwargs):
        self.client = AcsClient(kwargs.get('tts_access_key_id'), kwargs.get('tts_access_key_secret'),
                                kwargs.get('region', 'cn-hangzhou'))

    def send(self, **kwargs):

        notice_conf = kwargs.get('__conf')
        if not notice_conf: return False
        if not isinstance(notice_conf, dict): return False
        template_code = notice_conf.get('template_code')
        show_number = notice_conf.get('show_number')
        send_addr = kwargs.get('send_addr')
        phone_numbers = send_addr.get('tel', [])

        template_param = kwargs.get('msg', {})
        ###
        request = SingleCallByTtsRequest()
        request.set_accept_format('json')
        request.set_CalledShowNumber(show_number)
        # request.set_CalledNumber(phone_numbers)
        request.set_TtsCode(template_code)
        if template_param is not None:  request.set_TtsParam(template_param)
        request.set_PlayTimes(3)

        for phone in phone_numbers:
            ### 不支持多个传入，所以要遍历
            request.set_CalledNumber(phone)
            if template_param is not None:  request.set_TtsParam(template_param)
            response = self.client.do_action_with_exception(request)
            if json.loads(response).get('Message') != "OK": return response

        return json.dumps({"Message": "OK", "Code": "OK"})
