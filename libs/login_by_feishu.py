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
        # V5 飞书登录允许自动注册；V4 等其它入口保持「只匹配不注册」
        self.allow_auto_register = bool(kwargs.get('allow_auto_register', False))
        self.redis_conn = cache_conn()
        self._tenant_access_token = None
        self._token_expires_at = 0
        # call() 失败时的业务错误（供 handler 直接返回）
        self.last_error = None

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
        返回的 dict 额外带 _user_access_token，供后续用用户身份拉通讯录补手机号。
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

            token_payload = token_data.get('data') or {}
            user_access_token = token_payload.get('access_token')
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

            res = dict(info_data.get('data') or {})
            # 内部字段：用于补手机号，不要当业务字段写库
            res['_user_access_token'] = user_access_token
            # 部分租户在 token 接口 data 里直接带 mobile（少见，有则用）
            for k in ('mobile', 'email', 'enterprise_email'):
                if not res.get(k) and token_payload.get(k):
                    res[k] = token_payload.get(k)
            return res
        except Exception as err:
            logger.warning(f"[FeiShu] Open API 获取用户信息异常: {err}")
            return None

    def _get_contact_user(self, user_id: str, user_id_type: str = 'user_id',
                          user_access_token: str = None):
        """
        通讯录查用户详情（写死 URL），用于补 email/mobile/avatar。
        优先用 OIDC user_access_token（用户本人授权，更容易拿到自己的手机号）；
        失败再回退 tenant_access_token（需应用通讯录手机号权限）。
        """
        if not user_id:
            return None

        url = FEISHU_CONTACT_USER_URL.format(user_id=user_id)
        tokens = []
        if user_access_token:
            tokens.append(('user', user_access_token))
        tenant_token = self._get_tenant_access_token()
        if tenant_token:
            tokens.append(('tenant', tenant_token))

        for token_kind, token in tokens:
            try:
                resp = requests.get(
                    url,
                    headers={'Authorization': f'Bearer {token}'},
                    params={
                        'user_id_type': user_id_type,
                        'department_id_type': 'open_department_id',
                    },
                    timeout=10,
                )
                data = resp.json()
                if data.get('code') == 0:
                    user = (data.get('data') or {}).get('user') or {}
                    logger.info(
                        f"[FeiShu] 通讯录查询成功 token={token_kind}, "
                        f"id_type={user_id_type}, keys={list(user.keys())}, "
                        f"has_mobile={bool(user.get('mobile'))}"
                    )
                    if user.get('mobile') or token_kind == 'tenant' or len(tokens) == 1:
                        return user
                    # user token 成功但无 mobile，继续试 tenant
                    continue
                logger.warning(
                    f"[FeiShu] 通讯录查询失败 token={token_kind}, "
                    f"id_type={user_id_type}: {data}"
                )
            except Exception as err:
                logger.warning(
                    f"[FeiShu] 通讯录查询异常 token={token_kind}, "
                    f"id_type={user_id_type}: {err}"
                )
        return None

    def fetch_user_info(self):
        """
        获取飞书用户信息。
        优先 Open API（写死 URL）；失败再回退 Passport userinfo。
        拿到身份后立刻尝试补手机号（user_access_token + 通讯录）。
        """
        res = None
        # 1) Open API（与 v6 相同接口）
        if self.code:
            res = self._get_user_info_by_open_api(self.code)
            if res and (res.get('user_id') or res.get('open_id')):
                logger.info(
                    f"[FeiShu] Open API 获取用户信息成功: keys={list(res.keys())}, "
                    f"has_mobile={bool(self._extract_mobile(res))}"
                )
                # 登录 user_info 通常无 mobile，立即用 user_access_token 补全
                if not self._extract_mobile(res):
                    self._enrich_profile_from_contact(res)
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
            if not self._extract_mobile(res):
                self._enrich_profile_from_contact(res)
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

    @staticmethod
    def _extract_avatar(res: dict) -> str:
        """从 user_info / 通讯录结构中取头像 URL。"""
        if not isinstance(res, dict):
            return ''
        for key in ('avatar_url', 'avatar_big', 'avatar_middle', 'avatar_thumb', 'picture'):
            val = res.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
        avatar = res.get('avatar')
        if isinstance(avatar, str) and avatar.strip():
            return avatar.strip()
        if isinstance(avatar, dict):
            for key in ('avatar_240', 'avatar_640', 'avatar_72', 'avatar_origin', 'avatar'):
                val = avatar.get(key)
                if isinstance(val, str) and val.strip():
                    return val.strip()
        return ''

    @staticmethod
    def _extract_mobile(res: dict) -> str:
        """
        手机号按字符串取用（飞书一般为 str，如 '+86138...'）。
        不要读 mobile_visible：那是 bool「是否可见」，不是号码。
        """
        if not isinstance(res, dict):
            return ''
        # 仅号码字段；显式排除 mobile_visible
        for key in ('mobile', 'mobile_number', 'tel', 'phone'):
            raw = res.get(key)
            # bool 绝不是手机号（曾误把 mobile_visible=True 写成 tel）
            if isinstance(raw, bool) or raw is None:
                continue
            if isinstance(raw, bytes):
                raw = raw.decode('utf-8')
            # 正常路径：字符串手机号，strip 后非空即用
            if isinstance(raw, str):
                s = raw.strip()
                if s:
                    return s
                continue
            # 少数接口可能给纯数字
            if isinstance(raw, int):
                return str(raw)
        return ''

    @staticmethod
    def _username_from_email(email: str, fs_id: str = '') -> str:
        """
        username 用邮箱 @ 前本地部分，例如 aaa@xxx.com -> aaa。
        不做中文名。
        """
        local = ''
        if email and '@' in email:
            local = email.split('@', 1)[0].strip()
        # 仅保留常见安全字符，避免异常符号
        safe = ''.join(ch for ch in local if ch.isalnum() or ch in ('.', '_', '-'))
        safe = safe.strip('._-') or ''
        if safe:
            return safe[:50]
        # 兜底：fs_id / open_id 截断
        fallback = (fs_id or 'fs_user').replace(' ', '')[:50]
        return fallback or 'fs_user'

    def _ensure_unique_username(self, session, username: str, fs_id: str) -> str:
        """username 冲突时追加后缀，保证可登录标识可用。"""
        base = (username or 'fs_user')[:40]
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
            suffix = f"_{n}" if n < 50 else f"_{(fs_id or 'x')[-6:]}"
            candidate = f"{base[:50 - len(suffix)]}{suffix}"
            if n >= 50:
                return candidate

    def _enrich_profile_from_contact(self, res: dict) -> None:
        """
        补全 email / mobile / avatar。
        Open API user_info 常缺 mobile，需走通讯录。
        """
        if not isinstance(res, dict):
            return

        need_email = not self._extract_email(res)
        need_mobile = not self._extract_mobile(res)
        need_avatar = not self._extract_avatar(res)
        if not (need_email or need_mobile or need_avatar):
            return

        detail = None
        fs_id = res.get('user_id')
        open_id = res.get('open_id')
        user_at = res.get('_user_access_token') or None
        if fs_id:
            detail = self._get_contact_user(
                fs_id, user_id_type='user_id', user_access_token=user_at,
            )
        if (not detail or (need_mobile and not self._extract_mobile(detail))) and open_id:
            detail2 = self._get_contact_user(
                open_id, user_id_type='open_id', user_access_token=user_at,
            )
            if detail2:
                # 合并：后取的补前取没有的字段
                if not detail:
                    detail = detail2
                else:
                    for k, v in detail2.items():
                        if v and not detail.get(k):
                            detail[k] = v

        if not detail:
            if need_email or need_mobile:
                logger.warning(
                    f"[FeiShu] 通讯录未能补全资料: user_id={res.get('user_id')}, "
                    f"open_id={res.get('open_id')}, "
                    f"need_email={need_email}, need_mobile={need_mobile}, "
                    f"has_user_token={bool(user_at)}"
                )
            return

        if need_email:
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

        if need_mobile:
            mobile = self._extract_mobile(detail)
            if mobile:
                res['mobile'] = mobile
                logger.info(f"[FeiShu] 通讯录补手机成功: mobile={mobile}")
            else:
                # 便于排查权限：通讯录成功但无 mobile（常见缺手机号权限）
                logger.warning(
                    f"[FeiShu] 通讯录未返回手机号: user_keys={list(detail.keys())}。"
                    f"请确认飞书应用已开通「获取用户手机号」并发布授权。"
                )

        if need_avatar:
            avatar = self._extract_avatar(detail)
            if avatar:
                res['avatar_url'] = avatar
                logger.info("[FeiShu] 通讯录补头像成功")

    # 兼容旧方法名
    def _enrich_email_from_contact(self, res: dict) -> None:
        self._enrich_profile_from_contact(res)

    def _backfill_user_profile(self, session, user_info, res: dict) -> bool:
        """
        用飞书资料回填库中空的 tel/avatar/fs_open_id（不覆盖已有有效值）。
        返回是否有字段被更新。
        """
        if not user_info or not isinstance(res, dict):
            return False
        changed = False

        mobile = self._extract_mobile(res)
        cur_tel = (user_info.tel or '').strip()
        # 空、或历史脏数据 True/False，允许用飞书号码覆盖
        if mobile and (
            not cur_tel or cur_tel.lower() in ('true', 'false', 'none', 'null')
        ):
            user_info.tel = mobile
            changed = True

        avatar = self._extract_avatar(res)
        if avatar and not (user_info.avatar or '').strip():
            user_info.avatar = avatar
            changed = True

        open_id = res.get('open_id') or ''
        if open_id and not (user_info.fs_open_id or '').strip():
            user_info.fs_open_id = open_id
            changed = True

        if changed:
            session.commit()
            logger.info(
                f"[FeiShu] 回填用户资料: user_id={getattr(user_info, 'id', '')}, "
                f"tel={bool(mobile)}, avatar={bool(avatar)}"
            )
        return changed

    def _bind_user_by_email(self, session, res: dict, fs_id: str):
        """fs_id 未命中时，用邮箱兜底匹配并补录 fs_id。"""
        from sqlalchemy import func

        self._enrich_profile_from_contact(res)
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
            # 邮箱绑定时一并回填手机/头像
            mobile = self._extract_mobile(res)
            if mobile and (
                not (user_info.tel or '').strip()
                or (user_info.tel or '').strip().lower() in ('true', 'false')
            ):
                user_info.tel = mobile
            avatar = self._extract_avatar(res)
            if avatar and not (user_info.avatar or '').strip():
                user_info.avatar = avatar
            session.commit()
            logger.info(
                f"[FeiShu] 邮箱兜底绑定成功: email={fs_email}, fs_id={fs_id}, "
                f"tel={bool(user_info.tel)}, avatar={bool(user_info.avatar)}"
            )
        else:
            logger.warning(f"[FeiShu] 邮箱兜底未找到用户: email={fs_email}, fs_id={fs_id}")
        return user_info

    def _auto_register_user(self, session, res: dict, fs_id: str):
        """
        V5 专用：三级匹配均失败后自动注册。
        无邮箱 → 设置 last_error，不注册。
        username 取邮箱 @ 前本地部分（非中文名）；补 tel / avatar。
        发信失败不阻断登录。
        """
        import shortuuid
        from websdk2.jwt_token import gen_md5
        from libs.mfa_mail import generate_mfa_secret, send_account_open_mail
        from services.sys_service import init_email

        self._enrich_profile_from_contact(res)
        fs_email = self._extract_email(res)
        if not fs_email:
            logger.warning(
                f"[FeiShu] 自动注册失败：缺少邮箱 fs_id={fs_id}, "
                f"res_keys={list(res.keys()) if isinstance(res, dict) else type(res)}"
            )
            self.last_error = dict(
                code=-3,
                msg='飞书账号未绑定企业邮箱，无法自动开通，请联系管理员',
            )
            return None

        nickname = (res.get('name') or res.get('en_name') or fs_email or fs_id or '').strip() or fs_id
        username = self._ensure_unique_username(
            session,
            self._username_from_email(fs_email, fs_id=fs_id),
            fs_id,
        )
        tel = self._extract_mobile(res)
        avatar = self._extract_avatar(res)
        plain_password = shortuuid.uuid()
        mfa_secret = generate_mfa_secret()
        open_id = res.get('open_id') or ''

        from libs.mfa_utils import build_ext_info_with_mfa_bound

        user = Users(
            username=username,
            nickname=nickname,
            email=fs_email,
            tel=tel or '',
            avatar=avatar or '',
            fs_id=fs_id,
            fs_open_id=open_id,
            password=gen_md5(plain_password),
            google_key=mfa_secret,
            source='飞书',
            status='0',
            ext_info=build_ext_info_with_mfa_bound(bound='no'),
        )
        session.add(user)
        session.commit()
        if not tel:
            logger.warning(
                f"[FeiShu] 自动注册时未拿到手机号: username={username}, "
                f"email={fs_email}, fs_id={fs_id}, res_keys={list(res.keys())}"
            )
        logger.info(
            f"[FeiShu] 自动注册用户成功: username={username}, email={fs_email}, "
            f"fs_id={fs_id}, tel={tel or ''}, avatar={bool(avatar)}"
        )

        # 发信失败不阻断登录
        try:
            mailer = init_email()
            send_account_open_mail(
                mailer,
                to_email=fs_email,
                username=username,
                email=fs_email,
                plain_password=plain_password,
                mfa_secret=mfa_secret,
                nickname=nickname,
            )
        except Exception as err:
            logger.error(f"[FeiShu] 自动注册发信异常（不阻断登录）: {err}")

        return user

    @staticmethod
    def _detach_user(session, user_info):
        """
        commit 后属性会被 expire；session 关闭后 handler 再读 status 会
        DetachedInstanceError。在离开 session 前 refresh + expunge。
        """
        if user_info is None:
            return None
        try:
            session.refresh(user_info)
        except Exception:
            # refresh 失败时至少把已加载字段留在实例上
            pass
        session.expunge(user_info)
        return user_info

    def _resolve_user(self, session, res: dict):
        """fs_id -> open_id -> email 三级匹配；V5 可再自动注册。"""
        fs_id = res.get('user_id') or res.get('open_id')
        if not fs_id:
            return None

        user_info = session.query(Users).filter(
            Users.fs_id == fs_id,
            Users.status != '10'
        ).first()
        if user_info:
            # 已绑定用户也可能缺手机号：补通讯录再回填空字段
            need_profile = (
                not (user_info.tel or '').strip()
                or (user_info.tel or '').strip().lower() in ('true', 'false')
                or not (user_info.avatar or '').strip()
            )
            if need_profile:
                self._enrich_profile_from_contact(res)
                self._backfill_user_profile(session, user_info, res)
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
                self._enrich_profile_from_contact(res)
                self._backfill_user_profile(session, user_info, res)
                return user_info

        user_info = self._bind_user_by_email(session, res, fs_id)
        if user_info:
            return user_info

        if self.allow_auto_register:
            return self._auto_register_user(session, res, fs_id)

        return None

    def call(self):
        self.last_error = None
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
            user_info = self._detach_user(session, user_info)

        # 缓存勿写入内部 token 字段
        cache_payload = {
            k: v for k, v in res.items()
            if not str(k).startswith('_')
        }
        self.redis_conn.set(
            f"feishu_login_cache___{self.code}",
            json.dumps(cache_payload, ensure_ascii=False),
            ex=180,
        )
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
            user_info = self._detach_user(session, user_info)

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
