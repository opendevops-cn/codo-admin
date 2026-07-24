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
from loguru import logger
from shortuuid import uuid
from websdk2.cache_context import cache_conn
from websdk2.db_context import DBContextV2 as DBContext
from models.authority import Users

"""
feishu_client_id
feishu_client_secret
feishu_auth
"""


class FeiShuAuth:
    def __init__(self, **kwargs):
        self.__fs_conf = kwargs.get('fs_conf')
        self.code = kwargs.get('code')
        self.fs_redirect_uri = kwargs.get('fs_redirect_uri')
        self.redis_conn = cache_conn()

    @staticmethod
    def _decode_cached(cached):
        """Redis 可能返回 bytes，统一转 str。"""
        if isinstance(cached, bytes):
            return cached.decode('utf-8')
        return cached

    @staticmethod
    def _extract_email(res: dict) -> str:
        """飞书可能返回 email 或 enterprise_email。"""
        raw = res.get('email') or res.get('enterprise_email') or ''
        if isinstance(raw, bytes):
            raw = raw.decode('utf-8')
        return str(raw).strip()

    def _bind_user_by_email(self, session, res: dict, fs_id: str):
        """fs_id 未命中时，用邮箱兜底匹配并补录 fs_id。"""
        from sqlalchemy import func

        fs_email = self._extract_email(res)
        if not fs_email:
            logger.warning(
                f"[FeiShu] fs_id={fs_id} 未匹配且无 email/enterprise_email，跳过邮箱兜底；"
                f"res_keys={list(res.keys()) if isinstance(res, dict) else type(res)}"
            )
            return None

        # 大小写不敏感匹配，兼容 email / enterprise_email 与库内大小写差异
        user_info = session.query(Users).filter(
            func.lower(Users.email) == fs_email.lower(),
            Users.status != '10'
        ).first()

        if user_info:
            user_info.fs_id = fs_id
            user_info.fs_open_id = res.get('open_id', user_info.fs_open_id or '') or ''
            session.commit()
            logger.info(f"[FeiShu] 邮箱兜底绑定成功: email={fs_email}, fs_id={fs_id}")
        else:
            logger.warning(f"[FeiShu] 邮箱兜底未找到用户: email={fs_email}, fs_id={fs_id}")
        return user_info

    def call(self):
        user_info = self.get_cache_info()
        if user_info: return user_info

        access_token = self.get_access_token()
        res = self.get_feishu_user(access_token)
        if not res or 'user_id' not in res:
            logger.warning(
                f"[FeiShu] 获取用户信息失败或缺少 user_id: "
                f"res_keys={list(res.keys()) if isinstance(res, dict) else res}"
            )
            return None

        fs_id = res.get('user_id')
        with DBContext('w') as session:
            user_info = session.query(Users).filter(Users.fs_id == fs_id,
                                                    Users.status != '10').first()

            if not user_info:
                user_info = self._bind_user_by_email(session, res, fs_id)

        self.redis_conn.set(f"feishu_login_cache___{self.code}", json.dumps(res), ex=180)
        return user_info

    def get_cache_info(self):
        cached = self.redis_conn.get(f"feishu_login_cache___{self.code}")
        if not cached:
            return None

        cached = self._decode_cached(cached)
        try:
            res = json.loads(cached)
            if not isinstance(res, dict):
                res = {'user_id': str(res)}
        except (TypeError, json.JSONDecodeError):
            # 兼容旧缓存（只存了 fs_id 字符串）
            res = {'user_id': cached}

        fs_id = res.get('user_id')
        if isinstance(fs_id, bytes):
            fs_id = fs_id.decode('utf-8')
        if not fs_id:
            return None

        with DBContext('w') as session:
            user_info = session.query(Users).filter(Users.fs_id == fs_id, Users.status != '10').first()

            if not user_info:
                user_info = self._bind_user_by_email(session, res, fs_id)

        return user_info

    def test_feishu(self):
        # 发送测试信息
        pass

    def get_access_token(self):
        # 构建请求的 URL
        url = self.__fs_conf.get('feishu_access_url')

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'  # 设置为 JSON 格式
        }

        # 构建请求参数
        payload = {
            'client_id': self.__fs_conf.get('feishu_client_id'),
            'client_secret': self.__fs_conf.get('feishu_client_secret'),
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
        url = self.__fs_conf.get('feishu_user_info_url')

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
    logger.warning(result)
    return result
