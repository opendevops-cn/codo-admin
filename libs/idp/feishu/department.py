#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# @File    :   department.py
# @Time    :   2026/01/22 14:15:28
# @Author  :   DongdongLiu
# @Version :   1.0
# @Desc    :   飞书部门模块 - 使用官方SDK递归获取所有部门和用户

import json
import lark_oapi as lark
from loguru import logger
from typing import Dict, List
from lark_oapi.api.contact.v3 import (
    ChildrenDepartmentRequest,
    ChildrenDepartmentResponse,
    ListUserRequest,
    ListUserResponse,
)


class LarkDepartment:
    """飞书部门类 - 提供递归获取所有部门和用户的功能"""

    def __init__(self, app_id: str, app_secret: str):
        """
        初始化部门服务

        :param app_id: 飞书应用ID
        :param app_secret: 飞书应用密钥
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self.client = lark.Client.builder().app_id(app_id).app_secret(app_secret).log_level(lark.LogLevel.INFO).build()

    def get_department_users(self, department_id: str) -> List[str]:
        """
        获取指定部门的所有用户（支持分页）

        :param department_id: 部门ID
        :return: 用户open_id列表
        """
        users = []
        page_token = None

        try:
            while True:
                # 构造请求
                request_builder = (
                    ListUserRequest.builder()
                    .department_id(department_id)
                    .user_id_type("open_id")
                    .department_id_type("open_department_id")
                    .page_size(50)
                )
                if page_token:
                    request_builder.page_token(page_token)

                request = request_builder.build()
                response: ListUserResponse = self.client.contact.v3.user.list(request)

                if not response.success():
                    logger.error(
                        f"[FeiShu Department] 获取部门用户失败, dept_id: {department_id}, code: {response.code}"
                    )
                    break

                # 收集当前页的用户
                if response.data and response.data.items:
                    for user in response.data.items:
                        try:
                            user_dict = json.loads(lark.JSON.marshal(user))
                            users.append(user_dict)
                        except Exception as e:
                            logger.error(f"[FeiShu Department] 用户对象序列化失败, user: {user}, error: {e}")

                # 检查是否还有下一页
                if not response.data or not response.data.has_more:
                    break

                page_token = response.data.page_token

            logger.debug(f"[FeiShu Department] 部门 {department_id} 共 {len(users)} 个用户")
            return users

        except Exception as e:
            logger.error(f"[FeiShu Department] 获取部门用户异常: {e}")
            return users

    def _get_all_departments_recursive(
        self, department_id: str = "0", all_departments: List[Dict] = None
    ) -> List[Dict]:
        """
        递归获取所有部门（内部方法）

        :param department_id: 部门ID
        :param all_departments: 累积的部门列表
        :return: 部门列表
        """
        if all_departments is None:
            all_departments = []

        try:
            request = (
                ChildrenDepartmentRequest.builder()
                .department_id(department_id)
                .user_id_type("open_id")
                .department_id_type("open_department_id")
                .fetch_child(False)
                .page_size(50)
                .build()
            )
            response: ChildrenDepartmentResponse = self.client.contact.v3.department.children(request)

            if not response.success():
                logger.error(f"[FeiShu Department] 获取部门失败, dept_id: {department_id}, code: {response.code}")
                return all_departments

            if response.data and response.data.items:
                for dept in response.data.items:
                    dept_id = dept.open_department_id

                    # 将Department对象转换为字典
                    try:
                        dept_dict = json.loads(lark.JSON.marshal(dept))
                    except Exception as e:
                        logger.error(f"[FeiShu Department] 部门对象序列化失败, dept: {dept}, error: {e}")
                        continue
                        # 获取部门用户
                    dept_users = self.get_department_users(dept_id)
                    dept_dict["users"] = dept_users

                    all_departments.append(dept_dict)
                    logger.info(
                        f"[FeiShu Department] 已获取部门: {dept_dict['name']} ({dept_id}), 用户数: {len(dept_users)}"
                    )

                    # 递归获取子部门
                    self._get_all_departments_recursive(dept_id, all_departments)

            return all_departments

        except Exception as e:
            logger.error(f"[FeiShu Department] 递归获取部门异常: {e}", exc_info=True)
            return all_departments

    def get_all_departments(self) -> List[Dict]:
        """
        获取所有部门（递归获取，包含用户列表）

        :return: 所有部门列表，每个部门包含用户信息
        示例返回格式:
        [
            {
                "open_department_id": "od-xxx",
                "name": "技术部",
                "parent_department_id": "0",
                "member_count": 50,
                "users": [user1, user2, ...]
            },
            ...
        ]
        """
        logger.info("[FeiShu Department] 开始递归获取所有部门...")
        all_departments = self._get_all_departments_recursive("0")
        unique_user_ids = {
            user["open_id"] for dept in all_departments for user in dept.get("users", []) if user.get("open_id")
        }

        total_users = len(unique_user_ids)

        logger.info(f"[FeiShu Department] 获取完成，共 {len(all_departments)} 个部门, {total_users} 个用户")
        return all_departments
