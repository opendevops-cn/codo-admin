#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# @File    :   role_idp_department_service.py
# @Time    :   2026/01/23 11:53:04
# @Author  :   DongdongLiu
# @Version :   1.0
# @Desc    :   角色与身份提供商部门关联服务


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
