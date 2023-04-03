#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2021/1/13 16:04 
Desc    : 发送钉钉消息
"""

import json
import requests
import time
import hmac
import hashlib
import base64
from urllib import parse
from loguru import logger
from string import Template


class FeiShu:
    def __init__(self, **kwargs):
        pass

    def signature(self, secret):
        # 拼接timestamp和secret
        timestamp = round(time.time())
        string_to_sign = '{}\n{}'.format(timestamp, secret)
        hmac_code = hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()

        # 对结果进行base64处理
        sign = base64.b64encode(hmac_code).decode('utf-8')

        return timestamp, sign

    def send(self, **kwargs):
        notice_conf = kwargs.get('__conf')

        if not notice_conf or not isinstance(notice_conf, dict):   return {"Message": '配置错误', "Code": -1}

        ### @ 某人
        send_addr = kwargs.get('send_addr')
        at_mobiles = send_addr.get('tel')
        ### 通知模板
        msg_template = kwargs.get('msg_template')
        msg = kwargs.get('msg', {})
        s = Template(msg_template)

        try:
            data = s.safe_substitute(msg)
            data = json.loads(data, strict=False)
        except Exception as err:
            return {"Message": '飞书模板格式化或消息转换失败', "Code": -3}
        ###
        secret = notice_conf.get('secret')
        webhook = notice_conf.get('webhook')
        timestamp, sign = self.signature(secret)

        ### @人 暂不支持
        # if data and isinstance(data, dict):
        #     data["at"] = {"atMobiles": at_mobiles, "isAtAll": False}
        #     msgtype = data.get('msgtype')
        #     if msgtype == "text":
        #         data[msgtype]["content"] = data[msgtype]["content"] + " @" + '@'.join(at_mobiles)
        #     elif msgtype == "markdown" and data[msgtype] and "text" in data[msgtype]:
        #         data[msgtype]["text"] = data[msgtype]["text"] + " @" + '@'.join(at_mobiles)

        headers = {
            "Content-Type": "application/json;charset=UTF-8"
        }

        try:
            data['sign'] = sign
            data['timestamp'] = timestamp
            if isinstance(data, dict): data = json.dumps(data)
            res = requests.post(url=webhook, data=data, headers=headers)
            ret = res.json()
            if ret.get('StatusCode') == 0: return {"Message": "OK", "Code": 0}
            if ret.get('StatusCode') != 0: return {"Message": str(ret.get(msg, '')), "Code": -1}
        except Exception as err:
            logger.error(f'send fei shu error: {err}')
            return {"Message": str(err), "Code": -1}

        return {"Message": "error", "Code": -2}
