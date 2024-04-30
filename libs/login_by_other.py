#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2021/1/7 11:24 
Desc    : 解释一下吧
"""

import base64
import hashlib
import json
import requests
import time

from cryptography.fernet import Fernet
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
            # print('login ok')
            with DBContext('r') as session:
                user_info = session.query(Users).filter(Users.username == self.__username,
                                                        Users.status != '10').first()
            return user_info
        return None

    def __call__(self, *args, **kwargs):
        return self.call()


class OtherAuthV4:
    """对接安全中心认证"""

    def __init__(self, **kwargs):
        self.__uc_conf = kwargs.get('uc_conf')
        self.app_id_v2 = self.__uc_conf['app_id_v2']
        self.__username = kwargs.get('username')
        self.__password = kwargs.get('password')
        self.__auth_obj = HLAuthSDK(self.__uc_conf['auth_api_v2'], self.__uc_conf['app_secret_v2'])

    def call(self):
        try:
            res_code = self.__auth_obj.authenticate(self.app_id_v2, self.__username, self.__password)
        except Exception as err:
            print(err)
            res_code = False
        return res_code

    def __call__(self, *args, **kwargs):
        return self.call()


class HLAuthSDK:
    def __init__(self, server_url, encryption_key):
        self.server_url = server_url
        self.encryption_key = encryption_key
        self.cipher_suite = Fernet(encryption_key)

    def authenticate(self, app_id, username, password):
        timestamp = int(time.time()) * 256

        # 要发送的数据
        data = {
            'username': username,
            'password': password
        }

        # 将数据转换为 JSON 格式
        json_data = json.dumps(data)

        # 加密数据
        encrypted_data = self.cipher_suite.encrypt(json_data.encode())

        data_string = f'key={timestamp}&app_id={app_id}&data={encrypted_data}'
        encoded_data_string = base64.b64encode(data_string.encode()).decode()

        try:
            # 发送加密后的数据和请求头到服务器
            response = requests.post(self.server_url, data=encoded_data_string)

            # 检查服务器响应
            if response.status_code == 200:
                return True
            else:
                return False

        except Exception as e:
            print('An error occurred:', str(e))
            return False
