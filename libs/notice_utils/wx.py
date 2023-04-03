#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2021/1/13 16:07 
Desc    : 解释一下吧
"""

import requests
import json
from string import Template
from websdk2.web_logs import ins_log


class WorkWeiXin:
    def __init__(self, **kwargs):
        pass

    def send(self, **kwargs):
        notice_conf = kwargs.get('__conf')
        if not notice_conf: return False
        if not isinstance(notice_conf, dict): return False
        ### 通知模板
        msg_template = kwargs.get('msg_template')
        msg = kwargs.get('msg', {})
        s = Template(msg_template)
        data = s.safe_substitute(msg)
        data = json.loads(data)

        ### @ 某人
        send_addr = kwargs.get('send_addr')
        at_mobiles = send_addr.get('tel')
        if at_mobiles and data and isinstance(data, dict) and data.get('msgtype') == "text":
            data['text']["mentioned_mobile_list"] = at_mobiles

        webhook = notice_conf.get('webhook')

        headers = {
            "Content-Type": "application/json"
        }
        try:
            if isinstance(data, dict): data = json.dumps(data)
            res = requests.post(url=webhook, data=data, headers=headers)
            ret = json.loads(res.content)
            if ret['errcode'] == 0: return {"Message": "OK", "Code": 0}
        except Exception as err:
            ins_log.read_log('error', f'send work wei xin error: {err}')
            return {"Message": str(err), "Code": -1}

        return {"Message": "error", "Code": -2}
