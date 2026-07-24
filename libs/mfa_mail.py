#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MFA / 账号开通邮件：HTML 模板 + TOTP 扫码图。
Issuer 固定为 Codo。
"""
import base64
import io
import logging
from typing import Optional

import pyotp

MFA_ISSUER = 'Codo'


def generate_mfa_secret() -> str:
    """生成与现网一致风格的 base32 MFA 密钥。"""
    import shortuuid
    return base64.b32encode(
        bytes(str(shortuuid.uuid() + shortuuid.uuid())[:-9], encoding='utf-8')
    ).decode('utf-8')


def build_otpauth_uri(secret: str, account_name: str, issuer: str = MFA_ISSUER) -> str:
    totp = pyotp.TOTP(secret)
    name = account_name or 'user'
    return totp.provisioning_uri(name=name, issuer_name=issuer)


def build_qrcode_data_uri(otpauth_uri: str) -> str:
    """生成 data:image/png;base64,... 供 HTML 内嵌。失败返回空串。"""
    try:
        import qrcode
    except ImportError:
        logging.warning('[MFAMail] 未安装 qrcode，邮件将不包含二维码图片')
        return ''

    try:
        img = qrcode.make(otpauth_uri)
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        b64 = base64.b64encode(buf.getvalue()).decode('ascii')
        return f'data:image/png;base64,{b64}'
    except Exception as err:
        logging.warning(f'[MFAMail] 生成二维码失败: {err}')
        return ''


def _format_secret_groups(secret: str) -> str:
    s = (secret or '').replace(' ', '')
    return ' '.join(s[i:i + 4] for i in range(0, len(s), 4))


def build_account_open_html(
        *,
        username: str,
        email: str,
        plain_password: str,
        mfa_secret: str,
        nickname: str = '',
) -> str:
    """账号开通：密码 + MFA 扫码。"""
    account = email or username
    uri = build_otpauth_uri(mfa_secret, account)
    qr = build_qrcode_data_uri(uri)
    display_name = nickname or username or email
    secret_fmt = _format_secret_groups(mfa_secret)
    qr_block = (
        f'<img src="{qr}" alt="MFA QR Code" width="200" height="200" '
        f'style="display:block;margin:12px auto;border:1px solid #e5e7eb;border-radius:8px;"/>'
        if qr else
        '<p style="color:#b45309;">二维码生成失败，请使用下方手动密钥添加。</p>'
    )
    return f'''<!DOCTYPE html>
<html><head><meta charset="utf-8"/></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f3f4f6;padding:24px 0;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.08);">
        <tr><td style="background:linear-gradient(135deg,#2563eb,#1d4ed8);padding:20px 28px;color:#fff;">
          <div style="font-size:20px;font-weight:700;letter-spacing:.5px;">Codo</div>
          <div style="font-size:14px;opacity:.9;margin-top:4px;">账号开通通知</div>
        </td></tr>
        <tr><td style="padding:28px;">
          <p style="margin:0 0 16px;color:#111827;font-size:15px;">你好，{display_name}：</p>
          <p style="margin:0 0 20px;color:#4b5563;font-size:14px;line-height:1.6;">
            系统已为你开通账号。请妥善保存以下信息，并尽快绑定二次验证（MFA）。
          </p>
          <table width="100%" style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:8px;margin-bottom:20px;">
            <tr><td style="padding:16px 18px;font-size:14px;color:#374151;line-height:1.8;">
              <div><strong>登录账号：</strong>{username}</div>
              <div><strong>邮箱：</strong>{email}</div>
              <div><strong>初始密码：</strong><code style="background:#fee2e2;color:#991b1b;padding:2px 8px;border-radius:4px;font-size:13px;">{plain_password}</code></div>
            </td></tr>
          </table>
          <h3 style="margin:0 0 8px;font-size:15px;color:#111827;">绑定二次验证（MFA）</h3>
          <p style="margin:0 0 8px;color:#6b7280;font-size:13px;">使用 Google Authenticator / Microsoft Authenticator 等扫描：</p>
          {qr_block}
          <p style="margin:12px 0 4px;color:#6b7280;font-size:13px;">无法扫码时，可手动添加密钥：</p>
          <div style="background:#111827;color:#f9fafb;padding:12px 14px;border-radius:8px;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:14px;letter-spacing:1px;word-break:break-all;text-align:center;">
            {secret_fmt}
          </div>
          <p style="margin:8px 0 0;color:#9ca3af;font-size:12px;text-align:center;">Issuer：{MFA_ISSUER}</p>
          <ol style="margin:20px 0 0;padding-left:18px;color:#4b5563;font-size:13px;line-height:1.7;">
            <li>打开 Authenticator 应用，扫描上方二维码（或手动输入密钥）</li>
            <li>登录时输入应用生成的 6 位动态码</li>
            <li>建议首次登录后修改密码，请勿转发本邮件</li>
          </ol>
        </td></tr>
        <tr><td style="padding:14px 28px;background:#f9fafb;color:#9ca3af;font-size:12px;text-align:center;">
          本邮件由 Codo 系统自动发送，请勿回复
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>'''


def build_mfa_reset_html(
        *,
        username: str,
        email: str,
        mfa_secret: str,
        nickname: str = '',
) -> str:
    """重置 MFA：仅密钥 + 扫码。"""
    account = email or username
    uri = build_otpauth_uri(mfa_secret, account)
    qr = build_qrcode_data_uri(uri)
    display_name = nickname or username or email
    secret_fmt = _format_secret_groups(mfa_secret)
    qr_block = (
        f'<img src="{qr}" alt="MFA QR Code" width="200" height="200" '
        f'style="display:block;margin:12px auto;border:1px solid #e5e7eb;border-radius:8px;"/>'
        if qr else
        '<p style="color:#b45309;">二维码生成失败，请使用下方手动密钥添加。</p>'
    )
    return f'''<!DOCTYPE html>
<html><head><meta charset="utf-8"/></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f3f4f6;padding:24px 0;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.08);">
        <tr><td style="background:linear-gradient(135deg,#7c3aed,#5b21b6);padding:20px 28px;color:#fff;">
          <div style="font-size:20px;font-weight:700;letter-spacing:.5px;">Codo</div>
          <div style="font-size:14px;opacity:.9;margin-top:4px;">MFA 重置通知</div>
        </td></tr>
        <tr><td style="padding:28px;">
          <p style="margin:0 0 16px;color:#111827;font-size:15px;">你好，{display_name}：</p>
          <p style="margin:0 0 20px;color:#4b5563;font-size:14px;line-height:1.6;">
            你的二次验证（MFA）密钥已重置。请删除验证器中的旧条目，并用下方二维码重新绑定。
          </p>
          <table width="100%" style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:8px;margin-bottom:20px;">
            <tr><td style="padding:16px 18px;font-size:14px;color:#374151;line-height:1.8;">
              <div><strong>登录账号：</strong>{username or '-'}</div>
              <div><strong>邮箱：</strong>{email or '-'}</div>
            </td></tr>
          </table>
          <h3 style="margin:0 0 8px;font-size:15px;color:#111827;">重新绑定 MFA</h3>
          <p style="margin:0 0 8px;color:#6b7280;font-size:13px;">使用 Authenticator 扫描：</p>
          {qr_block}
          <p style="margin:12px 0 4px;color:#6b7280;font-size:13px;">手动密钥：</p>
          <div style="background:#111827;color:#f9fafb;padding:12px 14px;border-radius:8px;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:14px;letter-spacing:1px;word-break:break-all;text-align:center;">
            {secret_fmt}
          </div>
          <p style="margin:8px 0 0;color:#9ca3af;font-size:12px;text-align:center;">Issuer：{MFA_ISSUER}</p>
          <p style="margin:20px 0 0;color:#b45309;font-size:13px;background:#fffbeb;border:1px solid #fcd34d;border-radius:8px;padding:12px 14px;">
            安全提示：旧 MFA 已失效。请勿转发本邮件。
          </p>
        </td></tr>
        <tr><td style="padding:14px 28px;background:#f9fafb;color:#9ca3af;font-size:12px;text-align:center;">
          本邮件由 Codo 系统自动发送，请勿回复
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>'''


def send_account_open_mail(
        mailer,
        *,
        to_email: str,
        username: str,
        email: str,
        plain_password: str,
        mfa_secret: str,
        nickname: str = '',
) -> bool:
    """发送账号开通邮件。成功 True，失败 False（不抛异常）。"""
    if not to_email or not mailer:
        logging.warning('[MFAMail] 开通邮件跳过：无收件人或邮件客户端')
        return False
    try:
        html = build_account_open_html(
            username=username,
            email=email,
            plain_password=plain_password,
            mfa_secret=mfa_secret,
            nickname=nickname,
        )
        mailer.send_mail(to_email, '【Codo】账号开通通知', html, subtype='html')
        logging.info(f'[MFAMail] 开通邮件已发送: to={to_email}, user={username}')
        return True
    except Exception as err:
        logging.error(f'[MFAMail] 开通邮件发送失败: to={to_email}, err={err}')
        return False


def send_mfa_reset_mail(
        mailer,
        *,
        to_email: str,
        username: str = '',
        email: str = '',
        mfa_secret: str,
        nickname: str = '',
) -> bool:
    """发送 MFA 重置邮件。成功 True，失败 False。"""
    if not to_email or not mailer:
        logging.warning('[MFAMail] MFA 重置邮件跳过：无收件人或邮件客户端')
        return False
    try:
        html = build_mfa_reset_html(
            username=username,
            email=email or to_email,
            mfa_secret=mfa_secret,
            nickname=nickname,
        )
        mailer.send_mail(to_email, '【Codo】MFA 重置通知', html, subtype='html')
        logging.info(f'[MFAMail] MFA 重置邮件已发送: to={to_email}')
        return True
    except Exception as err:
        logging.error(f'[MFAMail] MFA 重置邮件发送失败: to={to_email}, err={err}')
        return False
