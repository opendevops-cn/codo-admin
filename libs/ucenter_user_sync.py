#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
用户中心 → codo_a_users 同步：身份匹配与单条 upsert。

匹配顺序：source_account_id → email → username → fs_id
- 命中已有用户：更新资料，不覆盖 google_key / password / ext_info
- 均未命中：新建并生成 MFA
- 单条失败隔离（savepoint），不拖垮整批同步
"""
import logging
from typing import Any, Dict, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from models.authority import Users


# 更新时绝不写入的字段（保护 MFA / 密码）
_PROTECTED_ON_UPDATE = frozenset({'google_key', 'password', 'ext_info'})


def _norm_str(val) -> str:
    if val is None:
        return ''
    if isinstance(val, bytes):
        val = val.decode('utf-8', errors='ignore')
    return str(val).strip()


def build_ucenter_profile(user: dict) -> Dict[str, Any]:
    """从用户中心单条记录构造可写库字段（不含 MFA）。"""
    user_id = _norm_str(user.get('uid'))
    return dict(
        source_account_id=user_id,
        fs_id=_norm_str(user.get('feishu_userid')) or '',
        nickname=_norm_str(user.get('name')) or user_id or 'unknown',
        manager=_norm_str(user.get('manager', '')),
        department=_norm_str(user.get('position')),
        email=_norm_str(user.get('email')),
        source='ucenter',
        tel=_norm_str(user.get('mobile')),
        status='0',
        avatar=_norm_str(user.get('avatar')),
        username=_norm_str(user.get('english_name')) or user_id or 'unknown',
    )


def find_existing_user(session, profile: dict) -> Tuple[Optional[Users], str]:
    """
    多键认人。返回 (user_or_None, match_reason)。
    reason: source_account_id | email | username | fs_id | ''
    """
    user_id = _norm_str(profile.get('source_account_id'))
    email = _norm_str(profile.get('email'))
    username = _norm_str(profile.get('username'))
    fs_id = _norm_str(profile.get('fs_id'))

    if user_id:
        row = session.query(Users).filter(
            Users.source_account_id == user_id,
            Users.status != '10',
        ).first()
        if row:
            return row, 'source_account_id'

    if email:
        row = session.query(Users).filter(
            func.lower(Users.email) == email.lower(),
            Users.status != '10',
        ).first()
        if row:
            return row, 'email'

    if username:
        row = session.query(Users).filter(
            Users.username == username,
            Users.status != '10',
        ).first()
        if row:
            return row, 'username'

    if fs_id:
        row = session.query(Users).filter(
            Users.fs_id == fs_id,
            Users.status != '10',
        ).first()
        if row:
            return row, 'fs_id'

    return None, ''


def apply_profile_to_user(row: Users, profile: dict, *, is_new: bool = False) -> None:
    """把 profile 写到 ORM 对象；更新路径跳过受保护字段。"""
    for k, v in profile.items():
        if not is_new and k in _PROTECTED_ON_UPDATE:
            continue
        if hasattr(row, k):
            # fs_id：空值不覆盖已有飞书 id
            if k == 'fs_id' and not v and getattr(row, 'fs_id', None):
                continue
            # avatar：空不覆盖
            if k == 'avatar' and not v and getattr(row, 'avatar', None):
                continue
            setattr(row, k, v)


def upsert_ucenter_user(session, user: dict) -> str:
    """
    同步单条用户中心用户。
    返回: 'created' | 'updated' | 'skipped'
    异常向上抛，由调用方做 savepoint 隔离。
    """
    profile = build_ucenter_profile(user)
    user_id = profile.get('source_account_id') or ''
    if not user_id:
        logging.warning('[UCenterSync] 跳过：无 uid, raw_keys=%s', list(user.keys()) if isinstance(user, dict) else type(user))
        return 'skipped'

    existing, reason = find_existing_user(session, profile)
    if existing:
        apply_profile_to_user(existing, profile, is_new=False)
        # 显式绑定用户中心 id（飞书先注册场景）
        existing.source_account_id = user_id
        existing.source = 'ucenter'
        if existing.status == '20':
            existing.status = '0'
        session.add(existing)
        logging.info(
            '[UCenterSync] 更新用户 match=%s id=%s username=%s source_account_id=%s',
            reason, getattr(existing, 'id', ''), existing.username, user_id,
        )
        return 'updated'

    # 全新用户：补 MFA
    from libs.mfa_mail import generate_mfa_secret
    from libs.mfa_utils import build_ext_info_with_mfa_bound

    profile['google_key'] = generate_mfa_secret()
    profile['ext_info'] = build_ext_info_with_mfa_bound(bound='no')
    row = Users(**{k: v for k, v in profile.items() if hasattr(Users, k)})
    session.add(row)
    logging.info(
        '[UCenterSync] 新建用户 username=%s email=%s source_account_id=%s',
        profile.get('username'), profile.get('email'), user_id,
    )
    return 'created'


def upsert_ucenter_user_safe(session, user: dict) -> str:
    """
    带 savepoint 的单条同步：失败 rollback 到点，返回 'error'，不污染外层事务。
    """
    uid = _norm_str((user or {}).get('uid'))
    try:
        nested = session.begin_nested()
    except Exception:
        # 部分驱动/连接不支持 nested：退化为直接执行 + 失败时 rollback 整会话风险由调用方处理
        try:
            return upsert_ucenter_user(session, user)
        except Exception as err:
            logging.error('[UCenterSync] 同步失败 uid=%s: %s', uid, err)
            try:
                session.rollback()
            except Exception:
                pass
            return 'error'

    try:
        result = upsert_ucenter_user(session, user)
        nested.commit()
        return result
    except IntegrityError as err:
        nested.rollback()
        logging.warning(
            '[UCenterSync] 唯一键冲突已跳过 uid=%s username=%s: %s',
            uid, (user or {}).get('english_name'), err,
        )
        return 'error'
    except SQLAlchemyError as err:
        nested.rollback()
        logging.error('[UCenterSync] DB 错误已跳过 uid=%s: %s', uid, err)
        return 'error'
    except Exception as err:
        nested.rollback()
        logging.error('[UCenterSync] 同步失败已跳过 uid=%s: %s', uid, err)
        return 'error'
