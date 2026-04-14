#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# @File    :   idp_service.py
# @Time    :   2026/01/22 14:20:00
import datetime
from typing import Dict, List
from loguru import logger
from sqlalchemy.dialects.mysql import insert as mysql_insert
from websdk2.db_context import DBContextV2 as DBContext
from models.authority import IdpDepartments
from models.authority import RoleIdpDepartments, Users


def batch_create_departments(
    departments: List[Dict],
    provider: str = "feishu",
    mark_missing_as_deleted: bool = True,
) -> bool:
    """
    批量创建部门数据（数据库级别upsert + 标记删除）
    :param departments: 部门数据列表
    :param provider: 第三方平台标识
    :param mark_missing_as_deleted: 是否将远程已删除的部门标记为删除状态
    :return: 操作是否成功
    """
    logger.info(
        f"[IDPService] 开始批量upsert {provider} 部门数据: {len(departments)} 个"
    )
    if provider not in ["feishu"]:
        logger.error(f"[IDPService] 不支持的第三方平台: {provider}")
        return False
    try:
        with DBContext("w", tag="batch_upsert") as session:
            # 数据库级别 upsert 操作
            # 1. 获取远程部门ID列表
            remote_department_ids = set()
            upsert_departments = []
            for department in departments:
                try:
                    department_id = department.get("open_department_id")
                    if not department_id:
                        logger.warning(f"[IDPService] 部门缺少ID: {department}")
                        continue
                    department_name = department.get("name", "")
                    if not department_name:
                        logger.warning(f"[IDPService] 部门缺少名称: {department}")
                        continue
                    remote_department_ids.add(department_id)
                    # 构建 upsert 数据
                    dept_data = {
                        "provider": provider,
                        "department_id": department_id,
                        "department_name": department.get("name", ""),
                        "parent_department_id": department.get(
                            "parent_department_id", ""
                        ),
                        "member_count": department.get("member_count", 0),
                        "department_users": department.get("users", []),
                        "status": "0",
                        "update_time": datetime.datetime.now(),
                    }
                    upsert_departments.append(dept_data)
                except Exception as e:
                    logger.error(f"[IDPService] 处理部门失败: {department_name}, {e}")
            # 2. 批量执行 upsert 操作
            if upsert_departments:
                try:
                    insert_stmt = mysql_insert(IdpDepartments).values(
                        upsert_departments
                    )

                    update_stmt = insert_stmt.on_duplicate_key_update(
                        department_name=insert_stmt.inserted.department_name,
                        parent_department_id=insert_stmt.inserted.parent_department_id,
                        member_count=insert_stmt.inserted.member_count,
                        department_users=insert_stmt.inserted.department_users,
                        status=insert_stmt.inserted.status,
                        update_time=insert_stmt.inserted.update_time,
                    )
                    # 执行 upsert 操作
                    session.execute(update_stmt)
                    logger.info("[IDPService] upsert操作完成")
                except Exception as e:
                    logger.error(f"[IDPService] upsert操作失败: {e}")
            # 3. 本地标记删除：将远程已不存在的部门标记为删除状态
            if mark_missing_as_deleted:
                try:
                    # 使用 UPDATE 语句标记删除
                    session.query(IdpDepartments).filter(
                        IdpDepartments.provider == provider,
                        ~IdpDepartments.department_id.in_(remote_department_ids),
                        IdpDepartments.status == "0",
                    ).update(
                        {"status": "10", "update_time": datetime.datetime.now()},
                        synchronize_session=False,
                    )
                except Exception as e:
                    logger.error(f"[IDPService] 标记删除操作失败: {e}")
            session.commit()
            return True
    except Exception as e:
        logger.error(f"[IDPService] 批量upsert异常: {e}")
    return False


def build_department_tree(
    provider: str = "feishu", root_department_id: str = "0"
) -> Dict:
    """
    构建飞书部门组织架构树
    :param provider: 第三方平台标识
    :param root_department_id: 根部门ID
    :return: 部门树结构
    """
    logger.info(f"[IDPService] 构建 {provider} 部门树，根部门: {root_department_id}")
    try:
        with DBContext("r") as session:
            # 获取所有部门
            departments = (
                session.query(IdpDepartments)
                .filter(
                    IdpDepartments.provider == provider, IdpDepartments.status == "0"
                )
                .order_by(IdpDepartments.department_name)  # 只按名称排序，不依赖层级
                .all()
            )
            if not departments:
                logger.warning(f"[IDPService] 未获取到任何 {provider} 部门数据")
                return dict(code=0, data=[])
            department_mapping = {dept.department_id: dept for dept in departments}
            # 递归构建树结构
            tree = _build_tree_recursive(root_department_id, department_mapping)
            return dict(code=0, data=tree)
    except Exception as e:
        logger.error(f"[IDPService] 构建部门树失败: {e}")
        return dict(code=1, message=str(e))


def _build_tree_recursive(parent_id: str, department_mapping: Dict) -> List[Dict]:
    """
    递归构建部门树
    :param parent_id: 父部门ID
    :param department_mapping: 部门映射字典
    :return: 子部门树列表
    """
    children = []
    for department_id, department in department_mapping.items():
        if department.parent_department_id == parent_id:
            node = {
                "id": department.id,
                "department_id": department.department_id,  # 添加部门ID
                "department_name": department.department_name,
                "member_count": department.member_count,
                "parent_department_id": department.parent_department_id,
                # "department_users": department.department_users,
                "create_time": department.create_time.isoformat()
                if department.create_time
                else None,
                "update_time": department.update_time.isoformat()
                if department.update_time
                else None,
                "children": [],
            }
            # 递归获取子部门
            node["children"] = _build_tree_recursive(department_id, department_mapping)
            children.append(node)
    # 按部门名称排序
    children.sort(key=lambda x: x["id"])
    return children


def get_departments(
    department_ids: List[str], include_children: bool = False, provider: str = "feishu"
) -> List[Dict]:
    """
    根据部门ID列表获取多个部门信息，支持递归获取子部门

    :param department_ids: 第三方部门ID列表
    :param include_children: 是否包含子部门（递归查询）
    :param provider: 第三方平台标识
    :return: 部门数据字典列表
    """
    if not department_ids:
        return []

    try:
        logger.info(
            f"[IDPService] 获取 {len(department_ids)} 个部门，包含子部门: {include_children}"
        )

        departments = []
        failed_ids = []

        # 逐个调用 get_department 方法
        for dept_id in department_ids:
            dept_data = get_department(
                dept_id, include_children=include_children, provider=provider
            )
            if dept_data:
                departments.append(dept_data)
            else:
                failed_ids.append(dept_id)

        if failed_ids:
            logger.warning(f"[IDPService] 以下部门ID未找到: {failed_ids}")

        logger.info(
            f"[IDPService] 成功获取 {len(departments)}/{len(department_ids)} 个部门"
        )
        return departments

    except Exception as e:
        logger.error(f"[IDPService] 批量获取部门失败: {e}")
        return []


def get_department(
    department_id: str, include_children: bool = True, provider: str = "feishu"
) -> Dict:
    """
    根据部门ID获取单个部门信息，支持递归获取子部门

    :param department_id: 第三方部门ID
    :param include_children: 是否包含子部门（递归查询）
    :param provider: 第三方平台标识
    :return: 部门数据字典，包含子部门树结构
    """
    try:
        with DBContext("r") as session:
            # 获取目标部门
            department = (
                session.query(IdpDepartments)
                .filter(
                    IdpDepartments.provider == provider,
                    IdpDepartments.department_id == department_id,
                    IdpDepartments.status == "0",
                )
                .first()
            )

            if not department:
                logger.warning(f"[IDPService] 未找到部门: {department_id}")
                return None

            # 构建部门基本信息
            department_data = {
                "id": department.id,
                "department_id": department.department_id,
                "department_name": department.department_name,
                "member_count": department.member_count,
                "parent_department_id": department.parent_department_id,
                "department_users": department.department_users,
                "create_time": department.create_time.isoformat()
                if department.create_time
                else None,
                "update_time": department.update_time.isoformat()
                if department.update_time
                else None,
                "children": [],
            }

            # 如果需要包含子部门，递归获取所有子部门
            if include_children:
                # 获取所有部门用于构建映射
                all_departments = (
                    session.query(IdpDepartments)
                    .filter(
                        IdpDepartments.provider == provider,
                        IdpDepartments.status == "0",
                    )
                    .all()
                )

                # 构建部门映射字典
                department_mapping = {
                    dept.department_id: dept for dept in all_departments
                }

                # 递归获取子部门树
                department_data["children"] = _build_tree_recursive(
                    department_id, department_mapping
                )

            else:
                logger.info(f"[IDPService] 获取部门 {department_id} (不包含子部门)")

            return department_data

    except Exception as e:
        logger.error(f"[IDPService] 获取部门失败: {e}")
        return None


def _collect_all_child_department_ids(
    parent_id: str, department_mapping: Dict, result_set: set
):
    """
    递归收集所有子部门ID（内存递归，复用 _build_tree_recursive 的逻辑）
    :param parent_id: 父部门ID
    :param department_mapping: 部门映射字典
    :param result_set: 结果集合
    """
    for department_id, department in department_mapping.items():
        if department.parent_department_id == parent_id:
            result_set.add(department_id)
            # 递归收集子部门的子部门
            _collect_all_child_department_ids(
                department_id, department_mapping, result_set
            )


def get_all_child_department_ids(session, parent_department_ids, provider="feishu"):
    """
    获取所有子部门ID（包括所有层级）
    :param session: 数据库会话
    :param parent_department_ids: 父部门ID列表
    :param provider: 第三方平台标识
    :return: 包含所有子部门的ID集合（包括父部门本身）
    """
    # 一次性查询所有部门到内存，避免多次数据库查询
    all_departments = (
        session.query(IdpDepartments)
        .filter(IdpDepartments.provider == provider, IdpDepartments.status == "0")
        .all()
    )

    # 构建部门映射
    department_mapping = {
        department.department_id: department for department in all_departments
    }

    # 收集所有子部门ID
    all_department_ids = set(parent_department_ids)  # 包括父部门本身
    for parent_id in parent_department_ids:
        _collect_all_child_department_ids(
            parent_id, department_mapping, all_department_ids
        )

    return all_department_ids


def get_users_from_role_idp_departments(role_id, provider="feishu", session=None):
    """
    获取角色绑定的身份提供商部门中的用户（包含所有子部门），并转换为系统用户ID列表
    :param role_id: 角色ID
    :param provider: 第三方平台标识，默认为 feishu
    :param session: 数据库会话（可选，如果不传则内部创建）
    :return: 系统用户ID列表
    """

    def _get_users(db_session):
        user_ids = []

        # 1. 查询角色绑定的部门ID列表
        role_idp_department = (
            db_session.query(RoleIdpDepartments)
            .filter(RoleIdpDepartments.role_id == role_id)
            .first()
        )

        if not role_idp_department or not role_idp_department.idp_department_ids:
            return user_ids

        # 2. 递归获取所有子部门ID（包括绑定的部门本身）
        all_department_ids = get_all_child_department_ids(
            db_session, role_idp_department.idp_department_ids, provider
        )

        # 3. 根据所有部门ID列表查询部门信息，获取部门用户
        departments = (
            db_session.query(IdpDepartments)
            .filter(
                IdpDepartments.department_id.in_(list(all_department_ids)),
                IdpDepartments.provider == provider,
                IdpDepartments.status == "0",
            )
            .all()
        )

        # 4. 收集所有部门用户的第三方ID (飞书ID/钉钉ID等)
        third_party_user_ids = set()
        for department in departments:
            if department.department_users and isinstance(
                department.department_users, list
            ):
                department_user_ids = [
                    user.get("user_id") for user in department.department_users if user.get("user_id")
                ]
                third_party_user_ids.update(department_user_ids)

        if not third_party_user_ids:
            return user_ids

        # 5. 根据第三方用户ID (fs_id) 查询系统用户ID
        # 注意：这里假设 fs_id 对应飞书，如果是钉钉需要使用 dd_id
        users = (
            db_session.query(Users.id)
            .filter(Users.fs_id.in_(list(third_party_user_ids)), Users.status == "0")
            .all()
        )

        user_ids = [user.id for user in users]

        return user_ids

    # 如果传入了 session，直接使用
    if session is not None:
        return _get_users(session)

    # 否则创建新的 session
    with DBContext("r") as new_session:
        return _get_users(new_session)
