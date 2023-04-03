#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2021/1/13 16:00 
Desc    : 阿里云发送邮件
"""

from aliyunsdkdysmsapi.request.v20170525 import SendSmsRequest, QuerySendDetailsRequest
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.profile import region_provider
import uuid


class AlSendSms(object):
    def __init__(self, **kwargs):
        self.acs_client = AcsClient(kwargs.get('sms_access_key_id'), kwargs.get('sms_access_key_secret'),
                                    kwargs.get('region'))
        region_provider.add_endpoint(kwargs.get('PRODUCT_NAME'), kwargs.get('region'), kwargs.get('DOMAIN'))

    def send(self, **kwargs):
        notice_conf = kwargs.get('__conf')
        if not notice_conf: return False
        if not isinstance(notice_conf, dict): return False
        template_code = notice_conf.get('template_code')
        sign_name = notice_conf.get('sign_name')
        send_addr = kwargs.get('send_addr')
        phone_numbers = send_addr.get('tel', [])
        # phone_numbers = kwargs.get('send_addr', [])
        if isinstance(phone_numbers, list): phone_numbers = ','.join(phone_numbers)
        template_param = kwargs.get('msg', {})
        ###
        business_id = uuid.uuid1()
        ###

        sms_request = SendSmsRequest.SendSmsRequest()
        # 申请的短信模板编码,必填
        sms_request.set_TemplateCode(template_code)

        # 短信模板变量参数
        if template_param is not None:  sms_request.set_TemplateParam(template_param)

        # 设置业务请求流水号，必填。
        sms_request.set_OutId(business_id)

        # 短信签名
        sms_request.set_SignName(sign_name)

        # 短信发送的号码列表，必填。
        sms_request.set_PhoneNumbers(phone_numbers)

        # 调用短信发送接口，返回json
        sms_response = self.acs_client.do_action_with_exception(sms_request)

        ##业务处理
        return sms_response

    def query_send_detail(self, biz_id, phone_number, page_size, current_page, send_date):
        query_request = QuerySendDetailsRequest.QuerySendDetailsRequest()
        # 查询的手机号码
        query_request.set_PhoneNumber(phone_number)
        # 可选 - 流水号
        query_request.set_BizId(biz_id)
        # 必填 - 发送日期 支持30天内记录查询，格式yyyyMMdd
        query_request.set_SendDate(send_date)
        # 必填-当前页码从1开始计数
        query_request.set_CurrentPage(current_page)
        # 必填-页大小
        query_request.set_PageSize(page_size)

        # 数据提交方式
        # queryRequest.set_method(MT.POST)

        # 数据提交格式
        # queryRequest.set_accept_format(FT.JSON)

        # 调用短信记录查询接口，返回json
        query_response = self.acs_client.do_action_with_exception(query_request)
        # print(query_response.decode('utf-8'))

        return query_response
