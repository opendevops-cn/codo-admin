#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
飞书第三方服务模块

提供飞书认证、部门查询、用户信息获取和数据同步服务
"""

from .department import LarkDepartment

__all__ = ["LarkDepartment"]