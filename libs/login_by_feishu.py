#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023/6/10 15:14
Desc    : 飞书登录验证
"""
import json
import urllib.parse
import requests
from shortuuid import uuid
from websdk2.cache_context import cache_conn
from websdk2.db_context import DBContextV2 as DBContext
from models.authority import Users


class FeiShuAuth:
    def __init__(self, **kwargs):
        self.__fs_conf = kwargs.get('fs_conf')
        self.code = kwargs.get('code')
        self.fs_redirect_uri = kwargs.get('fs_redirect_uri')
        self.redis_conn = cache_conn()

    def call(self):
        user_info = self.get_cache_info()
        if user_info: return user_info

        access_token = self.get_access_token()
        res = self.get_feishu_user(access_token)

        if not res or 'user_id' not in res: return None
        with DBContext('r') as session:
            user_info = session.query(Users).filter(Users.fs_id == res.get('user_id'),
                                                    Users.status != '10').first()

        self.redis_conn.set(f"feishu_login_cache___{self.code}", res.get('user_id'), ex=120)
        return user_info

    def get_cache_info(self):
        fs_id = self.redis_conn.get(f"feishu_login_cache___{self.code}")
        if fs_id:
            with DBContext('r') as session:
                user_info = session.query(Users).filter(Users.fs_id == fs_id, Users.status != '10').first()
            return user_info
        else:
            return None

    def get_access_token(self):
        # 构建请求的 URL
        url = self.__fs_conf.get('access_url')

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'  # 设置为 JSON 格式
        }

        # 构建请求参数
        payload = {
            'client_id': self.__fs_conf.get('client_id'),
            'client_secret': self.__fs_conf.get('client_secret'),
            'grant_type': 'authorization_code',
            'redirect_uri': self.fs_redirect_uri,
            'code': self.code
        }

        # 发送 POST 请求
        response = requests.post(url, headers=headers, data=payload)

        # 解析响应
        if response.status_code == 200:
            try:
                data = response.json()
                return data['access_token']
            except Exception as err:
                return None

        # 验证失败，返回 None 或抛出异常
        return None

    def get_feishu_user(self, access_token):
        # 构建请求的 URL
        url = self.__fs_conf.get('user_info_url')

        headers = {
            "Content-Type": "application/json; charset=utf-8",  # 设置为 JSON 格式
            "Authorization": f"Bearer {access_token}"
        }
        # 构建请求参数
        payload = {
            'grant_type': 'authorization_code',
            'code': self.code
        }
        response = requests.get(url, headers=headers)

        # 解析响应
        if response.status_code == 200:
            try:
                return response.json()
            except Exception as err:
                # print(response.text, err)
                return None

        # 验证失败，返回 None 或抛出异常
        return None

    def __call__(self, *args, **kwargs):
        return self.call()


# url_dict = dict(
#     test6667={
#         "login_url": "http://10.241.0.40:8888/api/p/v4/login/feishu/",
#         "real_url": "https://flow.huanle.com/#/orderCenter/order-list",
#         "client_id": 'cli_a270b45f63b9100b'
#     }
# )

# https://applink.feishu.cn/client/web_url/open?url=http://10.241.0.40:8888/api/p/v4/m/test6667?order_id=666
def with_protocol_feishu(url_code, query_params):
    try:
        redis_conn = cache_conn()
        link_map = redis_conn.get('LOGIN_LINK_MAP')
        url_dict = json.loads(link_map.decode())
    except Exception as err:
        print(err)
        url_dict = {}
    if url_code not in url_dict:
        return None

    client_id = url_dict.get(url_code).get('client_id')
    c_url = url_dict.get(url_code).get('real_url') + '?' + urllib.parse.urlencode(query_params)
    # 跳转登录URL
    redirect_uri = urllib.parse.urlencode(dict(redirect_uri=url_dict.get(url_code).get('login_url')))
    state = uuid()
    redis_conn = cache_conn()
    redis_conn.set(f"feishu_c_url___{state}", c_url, ex=120)
    redis_conn.set(f"feishu_fs_redirect_uri___{state}", url_dict.get(url_code).get('login_url'), ex=120)

    result = f'https://passport.feishu.cn/accounts/auth_login/oauth2/authorize?client_id={client_id}&response_type=code&{redirect_uri}&state={state}'

    return result
