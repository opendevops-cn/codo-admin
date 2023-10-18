#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2021/1/13 16:04 
Desc    : 发送钉钉工作通知
"""

import json
import requests
import logging
from string import Template


class DingTalkWork:

    def __init__(self, **conf):
        self.endpoint = 'https://oapi.dingtalk.com'
        self.appkey = conf['appkey']
        self.appsecret = conf['appsecret']
        self.agent_id = conf['agent_id']

        self.access_token = self.get_access_token()

    def send(self, **kwargs):
        ### 接收人
        send_addr = kwargs.get('send_addr')
        to_list = send_addr.get('dd_id')
        if not to_list: return {"Message": "No one was informed", "Code": -23}
        to_ids_str = ','.join(to_list)
        """发送工作通知"""
        ### 通知模板
        msg_template = kwargs.get('msg_template')
        msg = kwargs.get('msg', {})
        s = Template(msg_template)
        msg_data = s.safe_substitute(msg)
        try:
            msg_data = json.loads(msg_data)
        except:
            return {"Message": "No one was informed", "Code": -24}

        real_data = {
            "msg": msg_data,
            "to_all_user": "false",
            "agent_id": self.agent_id,
            "userid_list": to_ids_str
        }
        url = f"{self.endpoint}/topapi/message/corpconversation/asyncsend_v2?access_token={self.access_token}"
        try:
            if isinstance(real_data, dict): real_data = json.dumps(real_data)
            res = requests.post(url=url, data=real_data)
            if res.json()['errcode'] == 0:
                return {"Message": "OK", "task_id": res.json().get('task_id'), "Code": 0, "agent_id": self.agent_id}
            else:
                return {"Message": res.json()['errmsg'], "Code": -25}
        except Exception as err:
            logging.error( f'send ding work talk error: {err}')
            return {"Message": str(err), "Code": -26}

    def send_custom(self, **kwargs):
        msg = kwargs.get('msg')
        userid_list = kwargs.get('userid_list')
        real_data = {
            "msg": msg,
            "to_all_user": "false",
            "agent_id": self.agent_id,
            "userid_list": userid_list
        }
        url = f"{self.endpoint}/topapi/message/corpconversation/asyncsend_v2?access_token={self.access_token}"
        try:
            if isinstance(real_data, dict): real_data = json.dumps(real_data)
            res = requests.post(url=url, data=real_data)
            if res.json()['errcode'] == 0:
                return {"Message": "OK", "task_id": res.json().get('task_id'), "Code": 0, "agent_id": self.agent_id}
            else:
                return {"Message": res.json()['errmsg'], "Code": -25}
        except Exception as err:
            logging.error( f'send ding work talk error: {err}')
            return {"Message": str(err), "Code": -26}

    def send_update(self, **kwargs):
        msg = kwargs.get('msg', {})
        url = f"{self.endpoint}/topapi/message/corpconversation/status_bar/update?access_token={self.access_token}"
        try:
            if isinstance(msg, dict): msg = json.dumps(msg)
            res = requests.post(url=url, data=msg)
            if res.json()['errcode'] == 0:
                return {"Message": "OK", "Code": 0, "msg": "Status changed successfully"}
            else:
                return {"Message": res.json()['errmsg'], "Code": -27}
        except Exception as err:
            logging.error( f'send_update ding work talk error: {err}')
            return {"Message": str(err), "Code": -28}

    def get_access_token(self):
        access_token_url = f"{self.endpoint}/gettoken?appkey={self.appkey}&appsecret={self.appsecret}"
        res = requests.get(url=access_token_url)
        if res.status_code != 200: print('请求失败')
        access_token = res.json().get('access_token')
        return access_token
