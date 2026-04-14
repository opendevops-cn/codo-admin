#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# @File    :   role_idp_department_service.py
# @Time    :   2026/01/23 11:53:04
# @Author  :   DongdongLiu
# @Version :   1.0
# @Desc    :   角色与身份提供商部门关联服务

import json
import logging
from sqlalchemy import func

from websdk2.db_context import DBContextV2 as DBContext
from models.authority import RoleIdpDepartments, Roles, IdpDepartments, Users


def get_all_child_department_ids(session, parent_dept_ids):
    """
    递归获取所有子部门ID
    :param session: 数据库会话
    :param parent_dept_ids: 父部门ID列表
    :return: 包含所有子部门的ID集合
    """
    all_dept_ids = set(parent_dept_ids)
    current_level_ids = parent_dept_ids

    while current_level_ids:
        # 查询当前层级的所有子部门
        child_depts = (
            session.query(IdpDepartments.department_id)
            .filter(
                IdpDepartments.parent_department_id.in_(current_level_ids),
                IdpDepartments.status == "0",
            )
            .all()
        )

        # 提取子部门ID
        child_dept_ids = [dept.department_id for dept in child_depts]

        if not child_dept_ids:
            break

        # 添加到总集合中
        all_dept_ids.update(child_dept_ids)

        # 准备查询下一层级
        current_level_ids = child_dept_ids

    return all_dept_ids


def get_users_from_role_idp_departments(session, role_id):
    """
    获取角色绑定的身份提供商部门中的用户（包含所有子部门），并转换为系统用户ID列表
    :param session: 数据库会话
    :param role_id: 角色ID
    :return: 系统用户ID列表
    """
    user_ids = []

    # 1. 查询角色绑定的部门ID列表
    role_idp_dept = (
        session.query(RoleIdpDepartments)
        .filter(RoleIdpDepartments.role_id == role_id)
        .first()
    )

    if not role_idp_dept or not role_idp_dept.idp_department_ids:
        return user_ids

    # 2. 递归获取所有子部门ID（包括绑定的部门本身）
    all_dept_ids = get_all_child_department_ids(
        session, role_idp_dept.idp_department_ids
    )

    # 3. 根据所有部门ID列表查询部门信息，获取部门用户
    departments = (
        session.query(IdpDepartments)
        .filter(
            IdpDepartments.department_id.in_(list(all_dept_ids)),
            IdpDepartments.status == "0",
        )
        .all()
    )

    # 4. 收集所有部门用户的第三方ID (飞书ID/钉钉ID等)
    third_party_user_ids = set()
    for dept in departments:
        if dept.department_users and isinstance(dept.department_users, list):
            third_party_user_ids.update(dept.department_users)

    if not third_party_user_ids:
        return user_ids

    # 5. 根据第三方用户ID (fs_id) 查询系统用户ID
    users = (
        session.query(Users.id)
        .filter(Users.fs_id.in_(list(third_party_user_ids)), Users.status == "0")
        .all()
    )

    user_ids = [user.id for user in users]

    return user_ids



def get_role_idp_departments(**kwargs) -> dict:
    """
    查询角色绑定的身份提供商部门
    :param kwargs: role_id - 角色ID
    :return: dict
    """
    role_id = kwargs.get("role_id")
    if not role_id:
        return dict(code=-1, msg="角色ID不能为空")

    with DBContext("r") as session:
        role_idp_department = (
            session.query(RoleIdpDepartments)
            .filter(RoleIdpDepartments.role_id == role_id)
            .first()
        )

        if not role_idp_department:
            return dict(
                code=0,
                msg="查询成功",
                data={"role_id": role_id, "idp_department_ids": []},
            )

        data = {
            "id": role_idp_department.id,
            "role_id": role_idp_department.role_id,
            "idp_department_ids": role_idp_department.idp_department_ids or [],
        }

    return dict(code=0, msg="查询成功", data=data)


def bind_role_idp_departments(**kwargs) -> dict:
    """
    绑定/更新角色与身份提供商部门（覆盖式更新）
    :param kwargs:
        - role_id: 角色ID
        - idp_department_ids: 身份提供商部门ID列表（传入空数组则清空绑定）
    :return: dict
    使用示例：
        # 绑定部门
        bind_role_idp_departments(role_id=1, idp_department_ids=['dept1', 'dept2'])
        # 清空绑定（解绑）
        bind_role_idp_departments(role_id=1, idp_department_ids=[])
    """
    role_id = kwargs.get("role_id")
    idp_department_ids = kwargs.get("idp_department_ids")

    if not role_id:
        return dict(code=-1, msg="角色ID不能为空")

    if not isinstance(idp_department_ids, list):
        return dict(code=-1, msg="身份提供商部门ID列表必须是数组")

    with DBContext("w", None, True) as session:
        # 检查角色是否存在
        role = session.query(Roles).filter(Roles.id == role_id).first()
        if not role:
            return dict(code=-2, msg="角色不存在")

        # 查询是否已存在绑定关系
        role_idp_dept = (
            session.query(RoleIdpDepartments)
            .filter(RoleIdpDepartments.role_id == role_id)
            .first()
        )

        if not idp_department_ids:
            # 如果传入空列表，删除绑定关系
            if role_idp_dept:
                session.delete(role_idp_dept)
        else:
            if role_idp_dept:
                # 如果已存在，直接覆盖更新
                role_idp_dept.idp_department_ids = idp_department_ids
            else:
                # 如果不存在，创建新记录
                new_role_idp_dept = RoleIdpDepartments(
                    role_id=role_id, idp_department_ids=idp_department_ids
                )
                session.add(new_role_idp_dept)

    return dict(code=0, msg="操作成功")


def get_user_department_hierarchy(session, user_fs_id):
    """
    获取用户所属部门及所有父级部门的ID列表

    业务逻辑：
    1. 查询用户所在的直属部门（department_users 包含该用户的部门）
    2. 一次性加载所有部门数据，构建部门映射表
    3. 在内存中向上递归查询所有父级部门
    4. 返回用户直属部门的 department_id + 所有父级部门的 department_id 集合

    Args:
        session: 数据库会话
        user_fs_id: 用户的飞书ID

    Returns:
        set: 部门ID集合（department_id，即飞书部门ID，包括直属部门和所有父级部门）
    """
    if not user_fs_id:
        return set()

    try:
        # 步骤1：查询用户的直属部门
        direct_departments = (
            session.query(
                IdpDepartments.department_id,  # 部门ID（飞书部门ID）
                IdpDepartments.parent_department_id,  # 父部门ID
            )
            .filter(
                func.JSON_CONTAINS(
                    IdpDepartments.department_users,
                    json.dumps({"user_id": user_fs_id}),
                ) == 1,
                IdpDepartments.status == "0",
            )
            .all()
        )

        if not direct_departments:
            return set()

        # 步骤2：一次性加载所有部门数据
        all_depts = (
            session.query(
                IdpDepartments.department_id,  # 部门ID（飞书部门ID）
                IdpDepartments.parent_department_id,  # 父部门ID
            )
            .filter(IdpDepartments.status == "0")
            .all()
        )

        # 步骤3：构建 department_id -> parent_department_id 的映射表
        department_map = {d[0]: d[1] for d in all_depts}

        user_depeartment_ids = set()

        # 步骤4：向上查找每个直属部门的所有父级部门
        for department_id, parent_department_id in direct_departments:
            user_depeartment_ids.add(department_id)  # 添加直属部门的 department_id

            # 向上递归查找父部门，直到根部门（parent_department_id 为空）
            while parent_department_id:
                if parent_department_id == "0":
                    break  # 根部门，停止查找

                # 防止循环引用
                if parent_department_id in user_depeartment_ids:
                    break

                user_depeartment_ids.add(
                    parent_department_id
                )  # 添加父部门的 department_id

                # 继续向上查找
                parent_department_id = department_map.get(parent_department_id)

        return user_depeartment_ids

    except Exception as e:
        logging.error(f"获取用户部门层级失败: {e}")
        return set()


def get_user_role_ids_from_idp_departments(session, user_fs_id):
    """
    查询用户通过飞书部门关联的角色（包含部门层级关系）- 优化版

    业务逻辑：
    1. 查询用户所在的直属部门
    2. 查询直属部门的所有父级部门
    3. 查询角色绑定的部门列表（idp_department_ids）是否包含用户的任一部门ID
    4. 如果角色绑定的部门列表与用户部门列表有交集，则用户拥有该角色

    Args:
        session: 数据库会话
        user_fs_id: 用户的飞书ID

    Returns:
        list: 角色ID列表

    示例：
        部门层级：
          公司 (id=1)
            └── 技术部 (id=2)
                  └── 后端组 (id=3)

        用户A在"后端组"，部门ID列表：[3, 2, 1]

        角色绑定：
        - 角色1: idp_department_ids = [2, 5]  → 用户A有此角色（2 in [3,2,1]）
        - 角色2: idp_department_ids = [4, 6]  → 用户A无此角色（无交集）

    """
    if not user_fs_id:
        return []

    try:
        # 步骤1 + 步骤2：获取用户所属部门及所有父级部门的ID集合
        user_dept_ids = get_user_department_hierarchy(session, user_fs_id)

        if not user_dept_ids:
            return []

        # 步骤3：查询所有角色绑定关系
        role_mappings = session.query(
            RoleIdpDepartments.role_id, RoleIdpDepartments.idp_department_ids
        ).all()

        # 步骤4：判断交集
        role_ids = [
            role_id
            for role_id, dept_ids in role_mappings
            if dept_ids and isinstance(dept_ids, list) and set(dept_ids) & user_dept_ids
        ]

        return role_ids

    except Exception as e:
        logging.error(f"查询用户飞书部门角色失败: {e}")
        return []
