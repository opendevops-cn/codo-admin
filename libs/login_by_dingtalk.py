#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2025/5/22 15:14
Desc    : 钉钉登录验证（v4/v5）

对齐飞书近期能力：
- dd_id 主匹配
- 邮箱兜底 + 自动补录 dd_id
- V5 可自动注册（username=邮箱本地部分，补 tel/avatar，MFA bound=no）
- 已绑定用户回填空 tel/avatar
- 缓存 JSON + 旧缓存兼容
- 无邮箱自动注册时返回 last_error
"""
import json
import logging
import shortuuid
import requests
from loguru import logger
from websdk2.cache_context import cache_conn
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.jwt_token import gen_md5
from models.authority import Users

"""
dingtalk_client_id
dingtalk_client_secret
dingtalk_agent_id
dingtalk_auth
"""

# 钉钉 Open API（写死，不读配置）
DINGTALK_BASE_URL = "https://oapi.dingtalk.com"
DINGTALK_GET_TOKEN_URL = f"{DINGTALK_BASE_URL}/gettoken"
DINGTALK_USER_GET_URL = f"{DINGTALK_BASE_URL}/topapi/v2/user/get"
DINGTALK_USER_GETBYUNIONID_URL = f"{DINGTALK_BASE_URL}/topapi/user/getbyunionid"


class DingTalkAuth:
    def __init__(self, **kwargs):
        self.__dd_conf = kwargs.get('dd_conf') or {}
        self.code = kwargs.get('code')
        self.dd_redirect_uri = kwargs.get('dd_redirect_uri')
        self.allow_auto_register = bool(kwargs.get('allow_auto_register', False))
        self.redis_conn = cache_conn()
        self.last_error = None

        self._appid = self.__dd_conf.get('dingtalk_client_id') or self.__dd_conf.get('dingtalk_app_key')
        self._appsecret = self.__dd_conf.get('dingtalk_client_secret') or self.__dd_conf.get('dingtalk_app_secret')
        self._agentid = self.__dd_conf.get('dingtalk_agent_id')
        self._access_token = None

    # ------------------------------------------------------------------ utils
    @staticmethod
    def _decode_cached(cached):
        if isinstance(cached, bytes):
            return cached.decode('utf-8')
        return cached

    @staticmethod
    def _extract_dd_id(user_info_data: dict) -> str:
        if not isinstance(user_info_data, dict):
            return ''
        return (
            user_info_data.get('unionid')
            or user_info_data.get('openid')
            or user_info_data.get('dingId')
            or user_info_data.get('userid')
            or ''
        )

    @staticmethod
    def _extract_email(data: dict) -> str:
        if not isinstance(data, dict):
            return ''
        raw = data.get('email') or data.get('org_email') or ''
        if isinstance(raw, bytes):
            raw = raw.decode('utf-8')
        if isinstance(raw, bool) or raw is None:
            return ''
        return str(raw).strip()

    @staticmethod
    def _extract_mobile(data: dict) -> str:
        """手机号按字符串取用；忽略 bool。"""
        if not isinstance(data, dict):
            return ''
        for key in ('mobile', 'mobile_number', 'tel', 'phone'):
            raw = data.get(key)
            if isinstance(raw, bool) or raw is None:
                continue
            if isinstance(raw, bytes):
                raw = raw.decode('utf-8')
            if isinstance(raw, str):
                s = raw.strip()
                if s:
                    return s
                continue
            if isinstance(raw, int):
                return str(raw)
        return ''

    @staticmethod
    def _extract_avatar(data: dict) -> str:
        if not isinstance(data, dict):
            return ''
        for key in ('avatar', 'avatar_url', 'avatarMediaId'):
            val = data.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
        return ''

    @staticmethod
    def _username_from_email(email: str, dd_id: str = '') -> str:
        local = ''
        if email and '@' in email:
            local = email.split('@', 1)[0].strip()
        safe = ''.join(ch for ch in local if ch.isalnum() or ch in ('.', '_', '-'))
        safe = safe.strip('._-') or ''
        if safe:
            return safe[:50]
        fallback = (dd_id or 'dd_user').replace(' ', '')[:50]
        return fallback or 'dd_user'

    def _ensure_unique_username(self, session, username: str, dd_id: str) -> str:
        base = (username or 'dd_user')[:40]
        candidate = base
        n = 0
        while True:
            exists = session.query(Users).filter(
                Users.username == candidate,
                Users.status != '10',
            ).first()
            if not exists:
                return candidate
            n += 1
            suffix = f"_{n}" if n < 50 else f"_{(dd_id or 'x')[-6:]}"
            candidate = f"{base[:50 - len(suffix)]}{suffix}"
            if n >= 50:
                return candidate

    @staticmethod
    def _detach_user(session, user_info):
        if user_info is None:
            return None
        try:
            session.refresh(user_info)
        except Exception:
            pass
        try:
            session.expunge(user_info)
        except Exception:
            pass
        return user_info

    # ----------------------------------------------------------- dingtalk api
    def _get_access_token(self):
        if self._access_token:
            return self._access_token

        url = self.__dd_conf.get('dingtalk_access_url') or DINGTALK_GET_TOKEN_URL
        params = {'appkey': self._appid, 'appsecret': self._appsecret}
        try:
            response = requests.get(url, params=params, timeout=10)
            result = response.json()
            if result.get('errcode') == 0:
                self._access_token = result.get('access_token')
                return self._access_token
            logger.error(f"[DingTalk] Access Token Error: {result}")
            return None
        except Exception as e:
            logger.error(f"[DingTalk] Error fetching access token: {e}")
            return None

    def _get_dingtalk_user_by_code(self, access_token: str):
        """SNS: tmp_auth_code 换用户基本信息（含 unionid）。"""
        url = self.__dd_conf.get('dingtalk_user_info_url')
        if not url or not access_token:
            return None
        data = {"tmp_auth_code": self.code}
        try:
            full_url = f"{url}?access_token={access_token}"
            response = requests.post(
                full_url, json=data,
                headers={'Content-Type': 'application/json'}, timeout=10,
            )
            result = response.json()
            if result.get('errcode') != 0:
                logger.error(f"[DingTalk] User Info Error: {result}")
                return None
            return result
        except Exception as e:
            logger.error(f"[DingTalk] Error fetching user info: {e}")
            return None

    def _get_userid_by_unionid(self, access_token: str, unionid: str) -> str:
        if not access_token or not unionid:
            return ''
        try:
            resp = requests.post(
                DINGTALK_USER_GETBYUNIONID_URL,
                params={'access_token': access_token},
                json={'unionid': unionid},
                timeout=10,
            )
            data = resp.json()
            if data.get('errcode') == 0:
                return (data.get('result') or {}).get('userid') or ''
            logger.warning(f"[DingTalk] getbyunionid 失败: {data}")
        except Exception as err:
            logger.warning(f"[DingTalk] getbyunionid 异常: {err}")
        return ''

    def _get_user_detail(self, access_token: str, userid: str) -> dict:
        """通讯录详情：email / mobile / avatar / name。"""
        if not access_token or not userid:
            return {}
        try:
            resp = requests.post(
                DINGTALK_USER_GET_URL,
                params={'access_token': access_token},
                json={'userid': userid},
                timeout=10,
            )
            data = resp.json()
            if data.get('errcode') == 0:
                detail = data.get('result') or {}
                logger.info(
                    f"[DingTalk] 用户详情成功: keys={list(detail.keys())}, "
                    f"has_mobile={bool(detail.get('mobile'))}, "
                    f"has_email={bool(detail.get('email') or detail.get('org_email'))}"
                )
                return detail
            logger.warning(f"[DingTalk] 用户详情失败: {data}")
        except Exception as err:
            logger.warning(f"[DingTalk] 用户详情异常: {err}")
        return {}

    def fetch_user_profile(self) -> dict:
        """
        聚合钉钉登录用户资料，统一字段：
        dd_id, userid, unionid, name, email, mobile, avatar
        """
        access_token = self._get_access_token()
        if not access_token:
            return {}

        raw = self._get_dingtalk_user_by_code(access_token)
        if not raw or 'user_info' not in raw:
            logger.error("[DingTalk] Invalid user response")
            return {}

        ui = raw.get('user_info') or {}
        unionid = ui.get('unionid') or ''
        openid = ui.get('openid') or ''
        ding_id = ui.get('dingId') or ''
        nick = ui.get('nick') or ''

        userid = ''
        if unionid:
            userid = self._get_userid_by_unionid(access_token, unionid)

        detail = {}
        if userid:
            detail = self._get_user_detail(access_token, userid)

        profile = {
            'dd_id': unionid or openid or ding_id or userid,
            'userid': userid or detail.get('userid') or '',
            'unionid': unionid,
            'openid': openid,
            'name': detail.get('name') or nick or '',
            'email': self._extract_email(detail) or self._extract_email(ui),
            'mobile': self._extract_mobile(detail) or self._extract_mobile(ui),
            'avatar': self._extract_avatar(detail) or self._extract_avatar(ui),
            # 保留原始片段便于排查
            'raw_user_info': ui,
        }
        if not profile['dd_id']:
            logger.warning(f"[DingTalk] 无有效 dd_id: profile_keys={list(profile.keys())}")
            return {}
        logger.info(
            f"[DingTalk] 聚合用户资料: dd_id={profile['dd_id']}, "
            f"email={bool(profile['email'])}, mobile={bool(profile['mobile'])}"
        )
        return profile

    # -------------------------------------------------------- resolve / bind
    def _backfill_user_profile(self, session, user_info, profile: dict) -> None:
        if not user_info or not isinstance(profile, dict):
            return
        changed = False
        mobile = self._extract_mobile(profile)
        cur_tel = (user_info.tel or '').strip()
        if mobile and (not cur_tel or cur_tel.lower() in ('true', 'false', 'none', 'null')):
            user_info.tel = mobile
            changed = True
        avatar = self._extract_avatar(profile)
        if avatar and not (user_info.avatar or '').strip():
            user_info.avatar = avatar
            changed = True
        if changed:
            session.commit()
            logger.info(
                f"[DingTalk] 回填用户资料: id={getattr(user_info, 'id', '')}, "
                f"tel={bool(mobile)}, avatar={bool(avatar)}"
            )

    def _bind_user_by_email(self, session, profile: dict, dd_id: str):
        from sqlalchemy import func

        email = self._extract_email(profile)
        if not email:
            logger.warning(
                f"[DingTalk] dd_id={dd_id} 未匹配且无 email，跳过邮箱兜底"
            )
            return None

        user_info = session.query(Users).filter(
            func.lower(Users.email) == email.lower(),
            Users.status != '10',
        ).first()
        if not user_info:
            logger.warning(f"[DingTalk] 邮箱兜底未找到用户: email={email}")
            return None

        user_info.dd_id = dd_id
        mobile = self._extract_mobile(profile)
        if mobile and (
            not (user_info.tel or '').strip()
            or (user_info.tel or '').strip().lower() in ('true', 'false')
        ):
            user_info.tel = mobile
        avatar = self._extract_avatar(profile)
        if avatar and not (user_info.avatar or '').strip():
            user_info.avatar = avatar
        session.commit()
        logger.info(f"[DingTalk] 邮箱兜底绑定成功: email={email}, dd_id={dd_id}")
        return user_info

    def _auto_register_user(self, session, profile: dict, dd_id: str):
        from libs.mfa_mail import generate_mfa_secret, send_account_open_mail
        from libs.mfa_utils import build_ext_info_with_mfa_bound
        from services.sys_service import init_email

        email = self._extract_email(profile)
        if not email:
            logger.warning(f"[DingTalk] 自动注册失败：缺少邮箱 dd_id={dd_id}")
            self.last_error = dict(
                code=-3,
                msg='钉钉账号未绑定企业邮箱，无法自动开通，请联系管理员',
            )
            return None

        nickname = (profile.get('name') or email or dd_id or '').strip() or dd_id
        username = self._ensure_unique_username(
            session,
            self._username_from_email(email, dd_id=dd_id),
            dd_id,
        )
        tel = self._extract_mobile(profile)
        avatar = self._extract_avatar(profile)
        plain_password = shortuuid.uuid()
        mfa_secret = generate_mfa_secret()

        user = Users(
            username=username,
            nickname=nickname,
            email=email,
            tel=tel,
            avatar=avatar,
            dd_id=dd_id,
            password=gen_md5(plain_password),
            google_key=mfa_secret,
            source='钉钉',
            status='0',
            ext_info=build_ext_info_with_mfa_bound(bound='no'),
        )
        session.add(user)
        session.commit()
        logger.info(
            f"[DingTalk] 自动注册用户成功: username={username}, email={email}, "
            f"dd_id={dd_id}, tel={bool(tel)}, avatar={bool(avatar)}"
        )

        try:
            mailer = init_email()
            send_account_open_mail(
                mailer,
                to_email=email,
                username=username,
                email=email,
                plain_password=plain_password,
                mfa_secret=mfa_secret,
                nickname=nickname,
            )
        except Exception as err:
            logger.error(f"[DingTalk] 自动注册发信异常（不阻断登录）: {err}")

        return user

    def _resolve_user(self, session, profile: dict):
        dd_id = profile.get('dd_id') or ''
        if not dd_id:
            return None

        user_info = session.query(Users).filter(
            Users.dd_id == dd_id,
            Users.status != '10',
        ).first()
        if user_info:
            need_profile = (
                not (user_info.tel or '').strip()
                or (user_info.tel or '').strip().lower() in ('true', 'false')
                or not (user_info.avatar or '').strip()
            )
            if need_profile:
                self._backfill_user_profile(session, user_info, profile)
            return user_info

        user_info = self._bind_user_by_email(session, profile, dd_id)
        if user_info:
            return user_info

        if self.allow_auto_register:
            return self._auto_register_user(session, profile, dd_id)
        return None

    # --------------------------------------------------------------- public
    def call(self):
        self.last_error = None
        user_info = self.get_cache_info()
        if user_info:
            return user_info

        profile = self.fetch_user_profile()
        dd_id = profile.get('dd_id') if profile else ''
        if not profile or not dd_id:
            return None

        with DBContext('w') as session:
            user_info = self._resolve_user(session, profile)
            user_info = self._detach_user(session, user_info)

        # 缓存完整 profile JSON，兼容旧纯 dd_id
        try:
            self.redis_conn.set(
                f"dingtalk_login_cache___{self.code}",
                json.dumps(profile, ensure_ascii=False),
                ex=180,
            )
        except Exception as err:
            logger.warning(f"[DingTalk] 写缓存失败: {err}")
            try:
                self.redis_conn.set(f"dingtalk_login_cache___{self.code}", dd_id, ex=180)
            except Exception:
                pass
        return user_info

    def get_cache_info(self):
        cached = self.redis_conn.get(f"dingtalk_login_cache___{self.code}")
        if not cached:
            return None

        cached = self._decode_cached(cached)
        profile = None
        try:
            obj = json.loads(cached)
            if isinstance(obj, dict):
                profile = obj
            else:
                profile = {'dd_id': str(obj)}
        except (TypeError, json.JSONDecodeError):
            profile = {'dd_id': cached}

        dd_id = profile.get('dd_id') or self._extract_dd_id(profile)
        if not dd_id:
            return None
        profile['dd_id'] = dd_id

        with DBContext('w') as session:
            user_info = self._resolve_user(session, profile)
            user_info = self._detach_user(session, user_info)
        return user_info

    def __call__(self, *args, **kwargs):
        return self.call()
