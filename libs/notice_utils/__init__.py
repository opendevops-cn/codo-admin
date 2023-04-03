#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2021/1/13 16:00 
Desc    : 通知工厂
"""

import json
from .aldx import AlSendSms
from .email import MailNotice
from .dd import DingTalk
from .dd_work import DingTalkWork
from .wx import WorkWeiXin
from .aldh import AlSendTTS
from .fs import FeiShu


def notice_factory(way, notice_conf_map, **kwargs):
    notice_map = dict(
        dd=DingTalk,
        dd_work=DingTalkWork,
        wx=WorkWeiXin,
        fs=FeiShu,
        sms=AlSendSms,
        aldx=AlSendSms,
        aldh=AlSendTTS,
        aldx2=AlSendSms,
        aldh2=AlSendTTS,
        txdx=None,
        txdh=None,
        email=MailNotice,
    )
    cls = notice_map.get(way)
    if cls is None: return None
    if not kwargs: kwargs = notice_conf_map.get(way)
    if isinstance(kwargs, str): kwargs = json.loads(kwargs)
    return cls(**kwargs)
