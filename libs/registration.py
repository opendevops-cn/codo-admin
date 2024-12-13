#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2024/12/13 17:07
Desc    : 注册各种信息到管理平台
"""

import json
import logging

from websdk2.client import AcsClient
from websdk2.configs import configs
from settings import settings

if configs.can_import: configs.import_dict(**settings)
client = AcsClient()

uri = "/api/p/v4/authority/register/"

menu_list = [
    {
        "name": "MGauthority",
        "details": "管理后台-权限-权限管理"
    }, {
        "name": "MGuserlist",
        "details": "管理后台-权限-用户列表"
    }, {
        "name": "MGtokenlist",
        "details": "管理后台-权限-令牌列表"
    }, {
        "name": "MGLinklist",
        "details": "管理后台-权限-免密链接"
    }, {
        "name": "MGapplist",
        "details": "管理后台-权限-应用列表"
    }, {
        "name": "MGbusiness",
        "details": "管理后台-权限-业务管理列表"
    }, {
        "name": "MGmenus",
        "details": "管理后台-权限-菜单列表"
    }, {
        "name": "MGcomponents",
        "details": "管理后台-权限-前端组件"
    }, {
        "name": "MGfunctions",
        "details": "管理后台-权限-权限列表"
    }, {
        "name": "MGrole",
        "details": "管理后台-权限-角色管理"
    },
    {
        "name": "systeMmanage",
        "details": "管理后台-平台管理"
    },
    {
        "name": "systemconf",
        "details": "管理后台-平台配置"
    },
    {
        "name": "systemEmail",
        "details": "管理后台-配置-邮件设置"
    },
    {
        "name": "systemLdap",
        "details": "管理后台-配置-LDAP设置"
    },
    {
        "name": "systemBase",
        "details": "管理后台-配置-基础设置"
    },
    {
        "name": "systemFeishu",
        "details": "管理后台-配置-飞书设置"
    },
    {
        "name": "systemAudit",
        "details": "管理后台-审计"
    },
    {
        "name": "systemAuditLog",
        "details": "管理后台-审计日志"
    },
    {
        "name": "homepageManage",
        "details": "管理后台-首页管理"
    },
    {
        "name": "MGopsService",
        "details": "管理后台-首页管理-导航页步骤"
    },
    {
        "name": "MGopsGlobalCategory",
        "details": "管理后台-首页管理-导航页项目分类"
    },
    {
        "name": "MGopsGlobalService",
        "details": "管理后台-首页管理-导航页项目服务"
    },
]
component_list = [
    {
        "name": "reset_password_btn",
        "details": "权限中心-用户列表-重置密码"
    }, {
        "name": "reset_mfa_btn",
        "details": "权限中心-用户列表-重置二次认证"
    }, {
        "name": "get_token_btn",
        "details": "权限中心 用户列表 获取令牌"
    }, {
        "name": "edit_user_btn",
        "details": "权限中心 用户列表 编辑用户"
    }, {
        "name": "del_user_btn",
        "details": "权限中心 用户列表 删除用户"
    }, {
        "name": "new_user_btn",
        "details": "权限中心 用户列表 添加用户"
    }, {
        "name": "edit_token_a",
        "details": "权限中心-编辑令牌备注"
    }, {
        "name": "del_token_a",
        "details": "权限中心-删除令牌"
    }, {
        "name": "edit_app_btn",
        "details": "权限中心 应用列表 编辑按钮"
    }, {
        "name": "del_app_btn",
        "details": "权限中心 应用列表 删除按钮"
    }, {
        "name": "new_app_btn",
        "details": "权限中心 应用列表 添加按钮"
    }, {
        "name": "new_func_btn",
        "details": "权限中心 权限列表 添加权限按钮"
    }, {
        "name": "edit_fun_a",
        "details": "权限中心 权限列表 编辑A标签"
    }, {
        "name": "del_fun_a",
        "details": "权限中心 权限列表 删除A标签"
    }, {
        "name": "new_menu_btn",
        "details": "权限中心 前端菜单列表 添加菜单按钮"
    }, {
        "name": "edit_menu_a",
        "details": "权限中心 前端菜单列表 编辑A标签"
    }, {
        "name": "del_menu_a",
        "details": "权限中心 前端菜单列表 删除A标签"
    }, {
        "name": "new_component_btn",
        "details": "权限中心 前端组件列表 添加组件按钮"
    }, {
        "name": "edit_component_a",
        "details": "权限中心 前端组件列表 编辑A标签"
    }, {
        "name": "del_component_a",
        "details": "权限中心 前端组件列表 删除A标签"
    }, {
        "name": "new_role_btn",
        "details": "权限中心 角色列表 添加角色按钮"
    }, {
        "name": "edit_role_btn",
        "details": "权限中心 角色列表 编辑角色按钮"
    }, {
        "name": "del_role_btn",
        "details": "权限中心 角色列表 删除角色按钮"
    }, {
        "name": "edit_role_user_btn",
        "details": "权限中心 角色列表 编辑角色-用户 按钮"
    }, {
        "name": "edit_role_app_btn",
        "details": "权限中心 角色列表 编辑角色-应用 按钮"
    }, {
        "name": "edit_role_func_btn",
        "details": "权限中心 角色列表 编辑角色-权限 按钮"
    }, {
        "name": "edit_role_menu_btn",
        "details": "权限中心 角色列表 编辑角色-菜单 按钮"
    }, {
        "name": "edit_role_component_btn",
        "details": "权限中心 角色列表 编辑角色-组件 按钮"
    }, {
        "name": "new_notice_template_btn",
        "details": "通知中心-添加通知模板"
    }, {
        "name": "edit_notice_template_btn",
        "details": "通知中心-编辑通知模板"
    }, {
        "name": "test_notice_template_btn",
        "details": "通知中心-通知模板测试"
    }, {
        "name": "del_notice_template_btn",
        "details": "通知中心-通知模板测试按钮"
    }, {
        "name": "new_notice_group_btn",
        "details": "通知中心-添加通知组按钮"
    }, {
        "name": "edit_notice_group_btn",
        "details": "通知中心-编辑通知组按钮"
    }, {
        "name": "del_notice_group_btn",
        "details": "通知中心-删除通知组按钮"
    }, {
        "name": "new_notice_config_btn",
        "details": "通知中心-添加通知配置按钮"
    }, {
        "name": "edit_notice_config_btn",
        "details": "通知中心-编辑通知配置按钮"
    }, {
        "name": "del_notice_config_btn",
        "details": "通知中心-删除通知配置按钮"
    }
]
func_list = []
role_list = []

method_dict = dict(
    ALL="管理",
    GET="查看",
    # POST="添加",
    # PATCH="修改",
    # DELETE="删除"
)


def registration_to_paas():
    app_code = "p"
    api_info_url = f"/api/{app_code}/v1/probe/meta/urls/"
    func_info = client.do_action_v2(**dict(
        method='GET',
        url=api_info_url,
    ))
    if func_info.status_code == 200:
        temp_func_list = func_info.json().get('data')
        for f in temp_func_list:
            if 'name' not in f or f.get('name') == '暂无': continue
            for m, v in method_dict.items():
                if f.get('method') and m not in f.get('method'):
                    continue
                func = dict(method_type=m, name=f"{v}-{f['name']}", uri=f"/api/{app_code}{f.get('url')}")
                if f.get('status') == 'y':  func['status'] = '0'
                func_list.append(func)
    body = {
        "app_code": app_code,
        "menu_list": menu_list,
        "component_list": component_list,
        "func_list": func_list,
        "role_list": role_list
    }
    registration_data = dict(method='POST',
                             url=uri,
                             body=json.dumps(body),
                             description='自动注册')
    response = client.do_action(**registration_data)
    logging.info(json.loads(response))
    return response


class Registration:
    def __init__(self, **kwargs):
        pass

    @staticmethod
    def start_server():
        registration_to_paas()
        raise Exception('初始化完成')
