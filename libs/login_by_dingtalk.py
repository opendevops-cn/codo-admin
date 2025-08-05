#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2025/5/22 15:14
Desc    : 钉钉登录验证
"""
import logging
from loguru import logger
import requests
from websdk2.cache_context import cache_conn
from websdk2.db_context import DBContextV2 as DBContext
from models.authority import Users

"""
dingtalk_client_id
dingtalk_client_secret
dingtalk_agent_id
dingtalk_auth
"""


class DingTalkAuth:
    def __init__(self, **kwargs):
        self.__dd_conf = kwargs.get('dd_conf')  # 钉钉配置，包括 URL 和凭证
        self.code = kwargs.get('code')  # 钉钉登录时返回的临时授权码
        self.dd_redirect_uri = kwargs.get('dd_redirect_uri')  # 回调地址
        self.redis_conn = cache_conn()  # Redis 连接

        self._appid = self.__dd_conf.get('dingtalk_client_id')
        self._appsecret = self.__dd_conf.get('dingtalk_client_secret')
        self._agentid = self.__dd_conf.get('dingtalk_agent_id')

    def call(self):
        user_info = self.get_cache_info()
        if user_info:
            return user_info

        access_token = self._get_access_token()
        logging.error(access_token)
        res = self._get_dingtalk_user(access_token)
        logger.info(res)
        if not res or 'user_info' not in res:
            logging.error("Invalid user response from DingTalk.")
            return None

        user_info_data = res['user_info']
        dd_id = user_info_data.get("unionid") or user_info_data.get("openid") or user_info_data.get("dingId")
        with DBContext('r') as session:
            user_info = session.query(Users).filter(Users.dd_id == dd_id, Users.status != '10').first()

        self.redis_conn.set(f"dingtalk_login_cache___{self.code}", dd_id, ex=180)
        return user_info

    def get_cache_info(self):
        dd_id = self.redis_conn.get(f"dingtalk_login_cache___{self.code}")
        if isinstance(dd_id, bytes):
            dd_id = dd_id.decode('utf-8')

        if dd_id:
            with DBContext('r') as session:
                user_info = session.query(Users).filter(Users.dd_id == dd_id, Users.status != '10').first()
            return user_info
        else:
            return None

    def _get_access_token(self):
        url = self.__dd_conf.get('dingtalk_access_url')
        params = {'appkey': self._appid, 'appsecret': self._appsecret}

        try:
            response = requests.get(url, params=params, timeout=5)
            logger.info(f"[DingTalk] Get Access Token Response: {response.text}")
            result = response.json()
            if result.get('errcode') == 0:
                return result.get('access_token')
            else:
                logger.error(f"[DingTalk] Access Token Error: {result}")
                return None
        except Exception as e:
            logger.error(f"[DingTalk] Error fetching access token: {e}")
            return None

    def _get_dingtalk_user(self, access_token: str):
        """通过 code 换取用户信息"""
        url = self.__dd_conf.get('dingtalk_user_info_url')
        data = {"tmp_auth_code": self.code}

        try:
            full_url = f"{url}?access_token={access_token}"
            response = requests.post(full_url, json=data, headers={'Content-Type': 'application/json'}, timeout=5)
            logger.info(f"[DingTalk] Get User Info Response: {response.text}")
            result = response.json()
            if result.get('errcode') != 0:
                logger.error(f"[DingTalk] User Info Error: {result}")
                return None

            return result
        except Exception as e:
            logger.error(f"[DingTalk] Error fetching user info: {e}")
            return None

    def __call__(self, *args, **kwargs):
        return self.call()
