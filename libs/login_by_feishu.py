#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023/6/10 15:14
Desc    : 飞书登录验证（v4/v5）

用户信息获取优先走 Open API（与 v6 相同接口，URL 写死在本文件）：
  tenant_access_token -> authen/v1/oidc/access_token -> authen/v1/user_info
失败时回退旧 Passport OAuth（URL 仍来自 fs_conf，兼容现网配置）。
"""
import json
import time
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

# ---------------------------------------------------------------------------
# 飞书 Open API（与 v6 一致，写死本文件，不读配置、不引用 v6 模块）
# ---------------------------------------------------------------------------
FEISHU_OPEN_BASE_URL = "https://open.feishu.cn/open-apis"
FEISHU_TENANT_TOKEN_URL = f"{FEISHU_OPEN_BASE_URL}/auth/v3/tenant_access_token/internal"
FEISHU_OIDC_ACCESS_TOKEN_URL = f"{FEISHU_OPEN_BASE_URL}/authen/v1/oidc/access_token"
FEISHU_USER_INFO_URL = f"{FEISHU_OPEN_BASE_URL}/authen/v1/user_info"
FEISHU_CONTACT_USER_URL = f"{FEISHU_OPEN_BASE_URL}/contact/v3/users/{{user_id}}"


class FeiShuAuth:
    def __init__(self, **kwargs):
        self.__fs_conf = kwargs.get('fs_conf') or {}
        self.code = kwargs.get('code')
        self.fs_redirect_uri = kwargs.get('fs_redirect_uri')
        self.redis_conn = cache_conn()
        self._tenant_access_token = None
        self._token_expires_at = 0

    def _get_app_credentials(self):
        conf = self.__fs_conf or {}
        app_id = conf.get('feishu_client_id') or conf.get('feishu_app_id')
        app_secret = conf.get('feishu_client_secret') or conf.get('feishu_app_secret')
        return app_id, app_secret

    def _get_tenant_access_token(self):
        """Open API: tenant_access_token（写死 URL）。"""
        if self._tenant_access_token and time.time() < self._token_expires_at:
            return self._tenant_access_token

        app_id, app_secret = self._get_app_credentials()
        if not app_id or not app_secret:
            logger.warning("[FeiShu] 缺少 client_id/client_secret，无法调用 Open API")
            return None

        try:
            resp = requests.post(
                FEISHU_TENANT_TOKEN_URL,
                json={'app_id': app_id, 'app_secret': app_secret},
                timeout=10,
            )
            data = resp.json()
            if data.get('code') == 0:
                self._tenant_access_token = data.get('tenant_access_token')
                self._token_expires_at = time.time() + data.get('expire', 7200) - 300
                return self._tenant_access_token
            logger.warning(f"[FeiShu] 获取 tenant_access_token 失败: {data}")
        except Exception as err:
            logger.warning(f"[FeiShu] 获取 tenant_access_token 异常: {err}")
        return None

    def _get_user_info_by_open_api(self, code: str):
        """
        与 v6 相同链路（URL 写死本文件）:
          tenant_access_token -> oidc/access_token -> user_info
        """
        tenant_token = self._get_tenant_access_token()
        if not tenant_token:
            return None

        try:
            token_resp = requests.post(
                FEISHU_OIDC_ACCESS_TOKEN_URL,
                headers={
                    'Authorization': f'Bearer {tenant_token}',
                    'Content-Type': 'application/json',
                },
                json={'grant_type': 'authorization_code', 'code': code},
                timeout=10,
            )
            token_data = token_resp.json()
            if token_data.get('code') != 0:
                logger.warning(f"[FeiShu] Open API 换 user access_token 失败: {token_data}")
                return None

            user_access_token = (token_data.get('data') or {}).get('access_token')
            if not user_access_token:
                logger.warning(f"[FeiShu] Open API 响应无 access_token: {token_data}")
                return None

            info_resp = requests.get(
                FEISHU_USER_INFO_URL,
                headers={'Authorization': f'Bearer {user_access_token}'},
                timeout=10,
            )
            info_data = info_resp.json()
            if info_data.get('code') != 0:
                logger.warning(f"[FeiShu] Open API 获取 user_info 失败: {info_data}")
                return None

            return info_data.get('data') or {}
        except Exception as err:
            logger.warning(f"[FeiShu] Open API 获取用户信息异常: {err}")
            return None

    def _get_contact_user(self, user_id: str, user_id_type: str = 'user_id'):
        """通讯录查用户详情（写死 URL），用于补 email。"""
        tenant_token = self._get_tenant_access_token()
        if not tenant_token or not user_id:
            return None

        url = FEISHU_CONTACT_USER_URL.format(user_id=user_id)
        try:
            resp = requests.get(
                url,
                headers={'Authorization': f'Bearer {tenant_token}'},
                params={'user_id_type': user_id_type},
                timeout=10,
            )
            data = resp.json()
            if data.get('code') == 0:
                return (data.get('data') or {}).get('user') or {}
            logger.warning(f"[FeiShu] 通讯录查询失败 id_type={user_id_type}: {data}")
        except Exception as err:
            logger.warning(f"[FeiShu] 通讯录查询异常 id_type={user_id_type}: {err}")
        return None

    def fetch_user_info(self):
        """
        获取飞书用户信息。
        优先 Open API（写死 URL）；失败再回退 Passport userinfo。
        """
        # 1) Open API（与 v6 相同接口）
        if self.code:
            res = self._get_user_info_by_open_api(self.code)
            if res and (res.get('user_id') or res.get('open_id')):
                logger.info(
                    f"[FeiShu] Open API 获取用户信息成功: keys={list(res.keys())}"
                )
                return res
            logger.warning(f"[FeiShu] Open API 未返回有效用户: res={res}")

        # 2) 回退旧 Passport（URL 来自现网 fs_conf）
        logger.warning("[FeiShu] 回退 Passport OAuth 获取用户信息")
        access_token = self.get_access_token()
        if not access_token:
            logger.warning("[FeiShu] Passport 获取 access_token 失败")
            return None
        res = self.get_feishu_user(access_token)
        if res and (res.get('user_id') or res.get('open_id')):
            logger.info(
                f"[FeiShu] Passport 获取用户信息成功: keys={list(res.keys())}"
            )
            return res
        logger.warning(f"[FeiShu] Passport 获取用户信息失败: res={res}")
        return None

    @staticmethod
    def _decode_cached(cached):
        """Redis 可能返回 bytes，统一转 str。"""
        if isinstance(cached, bytes):
            return cached.decode('utf-8')
        return cached

    @staticmethod
    def _extract_email(res: dict) -> str:
        """飞书可能返回 email 或 enterprise_email。"""
        if not isinstance(res, dict):
            return ''
        raw = res.get('email') or res.get('enterprise_email') or ''
        if isinstance(raw, bytes):
            raw = raw.decode('utf-8')
        return str(raw).strip()

    def _enrich_email_from_contact(self, res: dict) -> None:
        """user_info 无 email 时，用通讯录补全（写死 URL）。"""
        if not isinstance(res, dict) or self._extract_email(res):
            return

        detail = None
        fs_id = res.get('user_id')
        open_id = res.get('open_id')
        if fs_id:
            detail = self._get_contact_user(fs_id, user_id_type='user_id')
        if not detail and open_id:
            detail = self._get_contact_user(open_id, user_id_type='open_id')

        if not detail:
            logger.warning(
                f"[FeiShu] 通讯录未能补到邮箱: user_id={res.get('user_id')}, "
                f"open_id={res.get('open_id')}"
            )
            return

        email = detail.get('email') or detail.get('enterprise_email') or ''
        if email:
            res['email'] = email
            if detail.get('enterprise_email'):
                res['enterprise_email'] = detail.get('enterprise_email')
            logger.info(f"[FeiShu] 通讯录补邮箱成功: email={email}")
        else:
            logger.warning(
                f"[FeiShu] 通讯录用户无邮箱字段: keys={list(detail.keys())}"
            )

    def _bind_user_by_email(self, session, res: dict, fs_id: str):
        """fs_id 未命中时，用邮箱兜底匹配并补录 fs_id。"""
        from sqlalchemy import func

        self._enrich_email_from_contact(res)
        fs_email = self._extract_email(res)
        if not fs_email:
            logger.warning(
                f"[FeiShu] fs_id={fs_id} 未匹配且无 email/enterprise_email，跳过邮箱兜底；"
                f"res_keys={list(res.keys()) if isinstance(res, dict) else type(res)}"
            )
            return None

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

    def _resolve_user(self, session, res: dict):
        """fs_id -> open_id -> email 三级匹配，命中则补录 fs_id。"""
        fs_id = res.get('user_id') or res.get('open_id')
        if not fs_id:
            return None

        user_info = session.query(Users).filter(
            Users.fs_id == fs_id,
            Users.status != '10'
        ).first()
        if user_info:
            return user_info

        open_id = res.get('open_id') or ''
        if open_id:
            user_info = session.query(Users).filter(
                Users.fs_open_id == open_id,
                Users.status != '10'
            ).first()
            if user_info:
                user_info.fs_id = fs_id
                session.commit()
                logger.info(
                    f"[FeiShu] open_id 兜底绑定成功: open_id={open_id}, fs_id={fs_id}"
                )
                return user_info

        return self._bind_user_by_email(session, res, fs_id)

    def call(self):
        user_info = self.get_cache_info()
        if user_info:
            return user_info

        res = self.fetch_user_info()
        fs_id = (res or {}).get('user_id') or (res or {}).get('open_id')
        if not res or not fs_id:
            logger.warning(
                f"[FeiShu] 获取用户信息失败或缺少 user_id/open_id: "
                f"res_keys={list(res.keys()) if isinstance(res, dict) else res}"
            )
            return None

        # 统一写入 user_id，方便缓存与后续匹配
        if not res.get('user_id') and res.get('open_id'):
            res['user_id'] = res.get('open_id')

        with DBContext('w') as session:
            user_info = self._resolve_user(session, res)

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

        fs_id = res.get('user_id') or res.get('open_id')
        if isinstance(fs_id, bytes):
            fs_id = fs_id.decode('utf-8')
            res['user_id'] = fs_id
        if not fs_id:
            return None

        with DBContext('w') as session:
            user_info = self._resolve_user(session, res)

        return user_info

    def test_feishu(self):
        # 发送测试信息
        pass

    def get_access_token(self):
        """旧 Passport 换 token（回退路径，URL 来自 fs_conf）。"""
        url = self.__fs_conf.get('feishu_access_url')
        if not url:
            return None

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        payload = {
            'client_id': self.__fs_conf.get('feishu_client_id'),
            'client_secret': self.__fs_conf.get('feishu_client_secret'),
            'grant_type': 'authorization_code',
            'redirect_uri': self.fs_redirect_uri,
            'code': self.code
        }

        response = requests.post(url, headers=headers, data=payload)
        if response.status_code == 200:
            try:
                data = response.json()
                return data['access_token']
            except Exception:
                return None
        return None

    def get_feishu_user(self, access_token):
        """旧 Passport userinfo（回退路径，URL 来自 fs_conf）。"""
        url = self.__fs_conf.get('feishu_user_info_url')
        if not url or not access_token:
            return None

        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {access_token}"
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            try:
                return response.json()
            except Exception:
                return None
        return None

    def __call__(self, *args, **kwargs):
        return self.call()


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
