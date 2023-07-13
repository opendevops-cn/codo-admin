#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2021/1/7 11:24 
Desc    : 解释一下吧
"""

import time
import requests
import hashlib
from websdk2.db_context import DBContextV2 as DBContext
from models.authority import Users


class OtherAuthV2:
    """兼容sso登录"""

    def __init__(self, **kwargs):
        self.__uc_conf = kwargs.get('uc_conf')
        self.url = self.__uc_conf['endpoint'] + "/api/login"
        self.__username = kwargs.get('username')
        self.__password = kwargs.get('password')

    def call(self):
        def md5hex(sign):
            md5 = hashlib.md5()  # 创建md5加密对象
            md5.update(sign.encode('utf-8'))  # 指定需要加密的字符串
            str_md5 = md5.hexdigest()  # 加密后的字符串
            return str_md5

        # uc_conf = settings.get('uc_conf')

        now = int(time.time())
        params = {
            "app_id": "devops",
            "sign": md5hex(self.__uc_conf['app_id'] + str(now) + self.__uc_conf['app_secret']),
            "timestamp": now,
            "username": self.__username,
            "password": self.__password,
        }
        response = requests.post(url=self.url, params=params)
        res = response.json()
        if response.status_code == 200 and res.get('message') == 'OK': return True
        return False

    def __call__(self, *args, **kwargs):
        return self.call()


class OtherAuthV3:
    """兼容sso登录"""

    def __init__(self, **kwargs):
        self.__uc_conf = kwargs.get('uc_conf')
        self.url = self.__uc_conf['endpoint'] + "/api/login"
        self.__username = kwargs.get('username')
        self.__password = kwargs.get('password')

    def call(self):
        def md5hex(sign):
            md5 = hashlib.md5()  # 创建md5加密对象
            md5.update(sign.encode('utf-8'))  # 指定需要加密的字符串
            str_md5 = md5.hexdigest()  # 加密后的字符串
            return str_md5

        # uc_conf = settings.get('uc_conf')

        now = int(time.time())
        params = {
            "app_id": "devops",
            "sign": md5hex(self.__uc_conf['app_id'] + str(now) + self.__uc_conf['app_secret']),
            "timestamp": now,
            "username": self.__username,
            "password": self.__password,
        }
        response = requests.post(url=self.url, params=params)
        res = response.json()
        if response.status_code == 200 and res.get('message') == 'OK':
            with DBContext('r') as session:
                user_info = session.query(Users).filter(Users.username == self.__username,
                                                        Users.status != '10').first()
            return user_info
        return None

    def __call__(self, *args, **kwargs):
        return self.call()
