#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MFA 状态与首次绑定引导辅助。
bound 使用 yes/no 字符串（非布尔）。
"""
import copy
import logging
import shortuuid
from typing import Any, Dict, Optional

from websdk2.cache_context import cache_conn
from websdk2.db_context import DBContextV2 as DBContext
from models.authority import Users
from libs.mfa_mail import (
    MFA_ISSUER,
    build_otpauth_uri,
    build_qrcode_data_uri,
)

MFA_TICKET_PREFIX = 'mfa_login_ticket_'
MFA_TICKET_TTL = 600  # 10 分钟


def _as_dict(val) -> dict:
    if isinstance(val, dict):
        return val
    return {}


def get_mfa_bound(user: Users) -> str:
    """
    返回 'yes' / 'no'。
    ext_info.mfa.bound 缺失时视为 'yes'（兼容存量已在用 MFA 的用户）。
    """
    ext = _as_dict(getattr(user, 'ext_info', None))
    mfa = _as_dict(ext.get('mfa'))
    bound = mfa.get('bound', 'yes')
    if bound in ('yes', 'no'):
        return bound
    # 兼容历史 true/false
    if bound is True or str(bound).lower() == 'true':
        return 'yes'
    if bound is False or str(bound).lower() == 'false':
        return 'no'
    return 'yes'


def is_mfa_pending_setup(user: Users) -> bool:
    """有密钥且尚未完成首次验证。"""
    if not getattr(user, 'google_key', None):
        return False
    return get_mfa_bound(user) == 'no'


def build_ext_info_with_mfa_bound(ext_info=None, bound: str = 'no') -> dict:
    """构造/合并 ext_info，bound 仅允许 yes/no。"""
    if bound not in ('yes', 'no'):
        bound = 'no'
    ext = copy.deepcopy(_as_dict(ext_info))
    mfa = _as_dict(ext.get('mfa'))
    mfa['bound'] = bound
    ext['mfa'] = mfa
    return ext


def mark_mfa_bound(user_id: int, bound: str = 'yes') -> bool:
    """将用户 MFA 绑定状态写入 ext_info。"""
    if bound not in ('yes', 'no'):
        bound = 'yes'
    try:
        with DBContext('w', None, True) as session:
            user = session.query(Users).filter(Users.id == user_id).first()
            if not user:
                return False
            user.ext_info = build_ext_info_with_mfa_bound(user.ext_info, bound=bound)
            if bound == 'yes':
                from datetime import datetime
                mfa = dict(_as_dict(user.ext_info.get('mfa')))
                mfa['bound'] = 'yes'
                mfa['bound_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ext = dict(_as_dict(user.ext_info))
                ext['mfa'] = mfa
                user.ext_info = ext
            session.commit()
        return True
    except Exception as err:
        logging.error(f'[MFA] mark_mfa_bound 失败 user_id={user_id}: {err}')
        return False


def create_mfa_ticket(user_id: int, ttl: int = MFA_TICKET_TTL) -> str:
    """身份认证通过后发放短时 ticket，供二次提交 dynamic。"""
    ticket = shortuuid.uuid()
    try:
        redis_conn = cache_conn()
        redis_conn.set(f'{MFA_TICKET_PREFIX}{ticket}', str(user_id), ex=ttl)
    except Exception as err:
        logging.error(f'[MFA] create_mfa_ticket 失败: {err}')
    return ticket


def pop_user_id_by_mfa_ticket(ticket: str) -> Optional[int]:
    """
    校验 ticket 并返回 user_id。
    不删除 ticket，允许用户输错 dynamic 后重试（TTL 内有效）。
    """
    if not ticket:
        return None
    try:
        redis_conn = cache_conn()
        raw = redis_conn.get(f'{MFA_TICKET_PREFIX}{ticket}')
        if not raw:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode('utf-8')
        return int(raw)
    except Exception as err:
        logging.error(f'[MFA] 读取 mfa_ticket 失败: {err}')
        return None


def delete_mfa_ticket(ticket: str) -> None:
    if not ticket:
        return
    try:
        cache_conn().delete(f'{MFA_TICKET_PREFIX}{ticket}')
    except Exception:
        pass


def build_setup_payload(user: Users) -> Dict[str, Any]:
    """首次绑定引导数据；otp_secret 与库中 google_key 一致。"""
    secret = user.google_key or ''
    account = user.email or user.username or str(user.id)
    uri = build_otpauth_uri(secret, account, issuer=MFA_ISSUER) if secret else ''
    qr = build_qrcode_data_uri(uri) if uri else ''
    return {
        'mfa_state': 'pending_setup',
        'user_id': str(user.id),
        'username': user.username or '',
        'email': user.email or '',
        'nickname': user.nickname or '',
        'issuer': MFA_ISSUER,
        'otp_secret': secret,
        'otpauth_uri': uri,
        'qrcode_data_uri': qr,
        'hint': '请使用 Authenticator 扫码或手动输入密钥，然后填写 6 位动态码完成绑定并登录',
    }


def build_verify_payload(user: Users) -> Dict[str, Any]:
    return {
        'mfa_state': 'bound',
        'user_id': str(user.id),
        'username': user.username or '',
        'email': user.email or '',
        'nickname': user.nickname or '',
    }
