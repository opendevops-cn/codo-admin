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
from string import Template
from websdk2.web_logs import ins_log


class DingTalk:
    def __init__(self, **kwargs):
        pass

    def signature(self, secret):
        timestamp = round(time.time() * 1000)
        secret_enc = secret.encode('utf-8')

        string_to_sign = '{}\n{}'.format(timestamp, secret)
        string_to_sign_enc = string_to_sign.encode('utf-8')
        # 使用HmacSHA256算法计算签名
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        # 进行Base64 encode把签名参数再进行urlEncode
        sign = parse.quote(base64.b64encode(hmac_code))
        return timestamp, sign

    def send(self, **kwargs):
        notice_conf = kwargs.get('__conf')
        if not notice_conf: return False
        if not isinstance(notice_conf, dict): return False
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
            return {"Message": '钉钉模板格式化或消息转换失败', "Code": -3}
        ###
        secret = notice_conf.get('secret')
        webhook = notice_conf.get('webhook')
        timestamp, sign = self.signature(secret)
        url = f"{webhook}&timestamp={timestamp}&sign={sign}"
        if data and isinstance(data, dict):
            data["at"] = {"atMobiles": at_mobiles, "isAtAll": False}
            msgtype = data.get('msgtype')
            if msgtype == "text":
                data[msgtype]["content"] = data[msgtype]["content"] + " @" + '@'.join(at_mobiles)
            elif msgtype == "markdown" and data[msgtype] and "text" in data[msgtype]:
                data[msgtype]["text"] = data[msgtype]["text"] + " @" + '@'.join(at_mobiles)
        headers = {
            "Content-Type": "application/json"
        }
        try:
            if isinstance(data, dict): data = json.dumps(data)
            # data.safe_substitute(d)
            res = requests.post(url=url, data=data, headers=headers)
            ret = json.loads(res.content)
            if ret['errcode'] == 0: return {"Message": "OK", "Code": 0}
        except Exception as err:
            ins_log.read_log('error', f'send ding talk error: {err}')

            return {"Message": str(err), "Code": -1}

        return {"Message": "error", "Code": -2}
