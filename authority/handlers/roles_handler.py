#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
from sqlalchemy import or_
from libs.base_handler import BaseHandler
from websdk2.cache_context import cache_conn
from websdk2.db_context import DBContextV2 as DBContext
from models.authority_model import Roles, UserRoles, GroupRoles, RolesMutual, RolesInherit, \
    Groups, Users, RoleApp, RoleBusiness, RoleMenu, RoleComponent, RoleFunction
from services.role_services import get_roles_list, get_user_list_for_role, get_role_herit_list, get_role_mutual_list, \
    get_group_list_for_role, add_operation_log, check_mutual_role, get_user_list_for_group, get_role_list_for_user, \
    get_user_exclude_list_for_role, get_group_exclude_list_for_role

BUILTED_IN_ROLE = ['base', 'default']


class RoleHandler(BaseHandler):

    def get(self, *args, **kwargs):
        count, queryset = get_roles_list(**self.params)

        return self.write(dict(code=0, result=True, msg="获取角色成功", count=count, data=queryset))

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        raw_data = data.copy()

        role_name = data.get('role_name')
        inherit_list = list(set(data.pop("inherit_list", [])))
        mutual_list = list(set(data.pop("mutual_list", [])))

        if not role_name: return self.write(dict(code=-1, msg='角色名不能为空'))

        if set(mutual_list) & set(data.get('prerequisites', [])):
            return self.write(dict(code=-2, msg='互斥角色和先决条件有交集'))

        with DBContext('w', None, True) as session:
            is_exist = session.query(Roles).filter(Roles.role_name == role_name).first()
            if is_exist: return self.write(dict(code=-3, msg='角色已注册'))

            new_role = Roles(**data)
            session.add(new_role)
            session.commit()
            role_id = new_role.role_id

            # 建立继承关系
            new_inherit = [RolesInherit(inherit_from_role_id=int(i), role_id=role_id) for i in inherit_list]
            session.add_all(new_inherit)
            # 建立互斥关系
            new_mutual = [RolesMutual(role_left_id=int(i), role_right_id=role_id) for i in mutual_list]
            session.add_all(new_mutual)

            redis_conn = cache_conn()
            redis_conn.set(f"need_sync_all_cache", 'y', ex=600)

            add_operation_log(dict(
                username=self.request_username,
                operation="新增角色",
                result=True,
                msg='角色创建成功',
                data=raw_data
            ))
        return self.write(dict(code=0, msg='角色创建成功'))

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        raw_data = data.copy()
        role_id = data.get('role_id', None)
        if not role_id: return self.write(dict(code=-1, msg='不能为空'))

        with DBContext('w', None, True) as session:
            exist_obj = session.query(Roles).filter(Roles.role_id == role_id).first()
            if not exist_obj:
                return self.write(dict(code=-2, msg='角色不存在'))

            if exist_obj.status == '0':
                return self.write(dict(code=-3, msg='角色状态有效，不可删除'))

            if exist_obj.role_type in BUILTED_IN_ROLE:
                return self.write(dict(code=-4, msg=f"角色类型为{exist_obj.role_type}， 不可删除"))

            # 查看继承关系，如果有其他角色继承该角色组，删除失败
            herit_list = session.query(RolesInherit).outerjoin(Roles, Roles.role_id == RolesInherit.role_id).filter(
                RolesInherit.inherit_from_role_id == role_id, Roles.status == '0', RolesInherit.status == '0').all()
            if herit_list: return self.write(dict(code=-5, msg='该角色正被其他角色继承，不能删除'))

            session.query(Roles).filter(Roles.role_id == role_id).delete(synchronize_session=False)
            session.query(UserRoles).filter(UserRoles.role_id == role_id).delete(synchronize_session=False)
            session.query(GroupRoles).filter(GroupRoles.role_id == role_id).delete(synchronize_session=False)
            session.query(RolesInherit).filter(RolesInherit.role_id == role_id).delete(synchronize_session=False)
            session.query(RolesMutual).filter(
                or_(RolesMutual.role_left_id == role_id, RolesMutual.role_right_id == role_id)).delete(
                synchronize_session=False)

            session.query(RoleApp).filter(RoleApp.role_id == role_id).delete(synchronize_session=False)
            session.query(RoleBusiness).filter(RoleBusiness.role_id == role_id).delete(synchronize_session=False)
            session.query(RoleMenu).filter(RoleMenu.role_id == role_id).delete(synchronize_session=False)
            session.query(RoleComponent).filter(RoleComponent.role_id == role_id).delete(synchronize_session=False)
            session.query(RoleFunction).filter(RoleFunction.role_id == role_id).delete(synchronize_session=False)

            add_operation_log(dict(
                username=self.request_username,
                operation="删除角色",
                result=True,
                msg='角色删除成功',
                data=raw_data
            ))
        return self.write(dict(code=0, msg='删除成功'))

    def put(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        raw_data = data.copy()
        role_id = data.get('role_id')
        role_name = data.get('role_name')
        count_limit = data.get('count_limit', -1)
        inherit_list = list(set(data.pop("inherit_list", [])))
        mutual_list = list(set(data.pop("mutual_list", [])))

        if not role_id: return self.write(dict(code=-1, msg='ID不能为空'))
        if not role_name: return self.write(dict(code=-2, msg='角色名称不能为空'))
        if set(mutual_list) & set(data.get('prerequisites')):
            return self.write(dict(code=-3, msg='互斥角色和先决条件有交集'))

        if '_index' in data: data.pop('_index')
        if '_rowKey' in data: data.pop('_rowKey')

        with DBContext('w', None, True) as session:
            is_exist = session.query(Roles.role_id).filter(Roles.role_id != role_id, Roles.status != '10',
                                                           Roles.role_name == role_name).first()
            if is_exist: return self.write(dict(code=-4, msg=f'角色 "{role_name}" 已存在'))

            user_count = session.query(UserRoles).filter(UserRoles.role_id == role_id, UserRoles.status == '0').count()
            if count_limit and count_limit != -1 and user_count > int(count_limit):
                return self.write(dict(code=-5, msg='该角色现有授权用户大于所设定的数量限制'))

            session.query(Roles).filter(Roles.role_id == role_id).update(data)
            # 更新继承关系
            session.query(RolesInherit).filter(RolesInherit.role_id == role_id).delete(synchronize_session=False)
            new_inherit = [RolesInherit(inherit_from_role_id=int(i), role_id=role_id) for i in inherit_list]
            session.add_all(new_inherit)
            # 更新互斥关系
            session.query(RolesMutual).filter(RolesMutual.role_right_id == role_id).delete(synchronize_session=False)
            new_mutual = [RolesMutual(role_left_id=int(i), role_right_id=role_id) for i in mutual_list]
            session.add_all(new_mutual)

            redis_conn = cache_conn()
            redis_conn.set(f"need_sync_all_cache", 'y', ex=600)

            add_operation_log(dict(
                username=self.request_username,
                operation="修改角色",
                result=True,
                msg='角色修改成功',
                data=raw_data
            ))
        return self.write(dict(code=0, msg='编辑成功'))

    def patch(self, *args, **kwargs):
        """禁用、启用"""
        data = json.loads(self.request.body.decode("utf-8"))
        raw_data = data.copy()
        role_id = str(data.get('role_id', None))
        msg = '角色不存在'

        if not role_id: return self.write(dict(code=-1, msg='不能为空'))

        with DBContext('r') as session:
            exist_obj = session.query(Roles).filter(Roles.role_id == role_id).first()
            if exist_obj.role_type in BUILTED_IN_ROLE:
                return self.write(dict(code=-3, msg=f"exist_obj.role_type，状态不可改变"))

            role_status = session.query(Roles.status).filter(Roles.role_id == role_id, Roles.status != '10').first()

        if not role_status: return self.write(dict(code=-2, msg=msg))

        if role_status[0] == '0':
            msg = '禁用成功'
            new_status = '20'

        elif role_status[0] == '20':
            msg = '启用成功'
            new_status = '0'
        else:
            msg = '状态不符合预期，删除'
            new_status = '10'

        with DBContext('w', None, True) as session:
            session.query(Roles).filter(Roles.role_id == role_id, Roles.status != '10').update(
                {Roles.status: new_status})
            session.query(UserRoles).filter(UserRoles.role_id == role_id).update({UserRoles.status: new_status})
            session.query(GroupRoles).filter(GroupRoles.role_id == role_id).update({GroupRoles.status: new_status})

            add_operation_log(dict(
                username=self.request_username,
                operation="启/禁用角色",
                result=True,
                msg=msg,
                data=raw_data
            ))
        self.write(dict(code=0, msg=msg))


class RoleGroupHandler(BaseHandler):
    def get(self, *args, **kwargs):
        role_id = self.get_argument('role_id', default=None, strip=True)
        if not role_id: return self.write(dict(status=-1, msg='关键参数不能为空'))

        count, role_list = get_group_list_for_role(ignore_info=False, is_page=True, **self.params)

        return self.write(dict(code=0, msg='获取成功', count=count, data=role_list))

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        raw_data = data.copy()
        group_list = data.get('group_list', [])
        role_id = data.get('role_id', None)
        group_list = list(set(group_list))

        if not role_id: return self.write(dict(code=-1, msg='角色不能为空'))
        if not group_list: return self.write(dict(code=-2, msg='选择的用户组不能为空'))

        success_group, fail_group = [], []
        log_data = []
        with DBContext('w', None, True) as session:
            current_role = session.query(Roles).filter(Roles.role_id == role_id).first()
            if not current_role: return self.write(dict(code=-3, msg='当前角色不存在'))
            prereqst_list = session.query(Roles).filter(Roles.status == '0',
                                                        Roles.role_id.in_(current_role.prerequisites)).all()
            prereqst_list = [pre.role_id for pre in prereqst_list]

            for group in group_list:
                exist_valid, msg = self.check_group_exist(group, role_id)
                if not exist_valid:
                    fail_group.append(group)
                    log_data.append({'group': group, 'msg': msg})
                    continue

                # 用户组已授权角色 与当前角色不互斥
                bound_role_list = session.query(Roles.role_id, Roles.role_name, Roles.prerequisites).outerjoin(
                    GroupRoles,
                    Roles.role_id == GroupRoles.role_id).filter(
                    GroupRoles.group_id == group, Roles.status == '0', GroupRoles.status == '0',
                    Groups.status == '0').all()
                mutual_valid, msg = self.check_mutual_valid(group, role_id, bound_role_list)
                if not mutual_valid:
                    fail_group.append(group)
                    log_data.append({'group': group, 'msg': msg})
                    continue

                # 用户组内的所有用户， 满足角色的先决条件
                _, user_group_list = get_user_list_for_group(group_id=group, contain_relate=True)
                if prereqst_list:
                    pre_user_valid, msg = self.check_user_prequest_valid(group, prereqst_list, user_group_list)
                    if not pre_user_valid:
                        fail_group.append(group)
                        log_data.append({'group': group, 'msg': msg})
                        continue

                # 用户已有角色 与 当前角色 不互斥
                mutual_user_valid, msg = self.check_user_mutual_valid(group, role_id, user_group_list)
                if not mutual_user_valid:
                    fail_group.append(group)
                    log_data.append({'group': group, 'msg': msg})
                    continue

                # 满足所有条件，授权成功
                success_group.append(group)

            new_groups = [GroupRoles(role_id=role_id, group_id=int(i)) for i in success_group]
            session.add_all(new_groups)
            redis_conn = cache_conn()
            redis_conn.set(f"need_sync_all_cache", 'y', ex=600)

            msg = f"成功添加用户组{len(success_group)}个，失败{len(fail_group)}条"
            log_id = add_operation_log(dict(
                username=self.request_username,
                operation="角色授权用户组",
                result=True,
                msg=msg,
                data=raw_data,
                response=dict(log_data=log_data)
            ))
        return self.write(
            dict(code=0, success_user=success_group, fail_user=fail_group, msg=msg, log_id=log_id, log_data=log_data))

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        raw_data = data.copy()
        group_list = data.get('group_list', [])
        role_id = data.get('role_id', None)
        group_list = list(set(group_list))

        if not role_id:  return self.write(dict(code=-1, msg='角色不能为空'))
        if not group_list: return self.write(dict(code=-2, msg='选择的用户组不能为空'))

        ## 删除
        with DBContext('w', None, True) as session:
            session.query(GroupRoles).filter(GroupRoles.role_id == role_id,
                                             GroupRoles.group_id.in_(group_list)).delete(synchronize_session=False)
            ###
            redis_conn = cache_conn()
            redis_conn.set(f"need_sync_all_cache", 'y', ex=600)

            add_operation_log(dict(
                username=self.request_username,
                operation="角色删除用户组",
                result=True,
                msg='从角色中删除用户组成功',
                data=raw_data
            ))
        self.write(dict(code=0, msg='从角色中删除用户组成功'))

    def check_group_exist(self, group_id, role_id):
        """检查用户组是否已在当前角色"""
        with DBContext('r', None, True) as session:
            group = session.query(GroupRoles).filter(GroupRoles.status == '0', GroupRoles.group_id == group_id,
                                                     GroupRoles.role_id == role_id).first()
            if group:
                group_name = session.query(Groups.group_name).filter(Groups.group_id == group_id).first()
                return False, f'用户组{group_name[0]}已在该角色中'
        return True, ''

    def check_mutual_valid(self, group_id, role_id, bound_role_list):
        """角色授权用户组时， 检查互斥条件"""
        bound_role_list_id = [i[0] for i in bound_role_list]
        check_list = bound_role_list_id + [role_id]
        check_list = list(set(check_list))
        res = check_mutual_role(check_list)
        if res:
            with DBContext('r', None, True) as session:
                group_name = session.query(Groups.group_name).filter(Groups.group_id == group_id).first()
                return False, f'所选用户组[{group_name[0]}]已授权角色与当前角色互斥'
        return True, ''

    def check_user_prequest_valid(self, group_id, prereqst_list, user_group_list):
        """角色授权用户组时，所有用户已权限先决条件"""
        if not prereqst_list:
            return True, ''
        user_id_list = [user.get('user_id') for user in user_group_list]

        for user in user_id_list:
            _, user_role_list = get_role_list_for_user(user_id=user)
            role_list = [i.get('role_id') for i in user_role_list]
            if not set(role_list) >= set(prereqst_list):
                with DBContext('r', None, True) as session:
                    group_name = session.query(Groups.group_name).filter(Groups.group_id == group_id).first()
                    return False, f'所选用户组[{group_name[0]}]不满足角色的先决条件'
        return True, ''

    def check_user_mutual_valid(self, group_id, role_id, user_group_list):
        """角色授权用户组时，所有用户不互斥"""
        user_id_list = [user.get('user_id') for user in user_group_list]
        for user in user_id_list:
            _, user_role_list = get_role_list_for_user(user_id=user)
            role_list = [i.get('role_id') for i in user_role_list]
            check_list = role_list + [role_id]
            check_list = list(set(check_list))
            res = check_mutual_role(check_list)
            if res:
                with DBContext('r', None, True) as session:
                    group_name = session.query(Groups.group_name).filter(Groups.group_id == group_id).first()
                    return False, f'所选用户组[{group_name[0]}]中用户的已有角色与当前角色互斥'
        return True, ''


class RoleUserHandler(BaseHandler):
    def get(self, *args, **kwargs):
        role_id = self.get_argument('role_id', default=None, strip=True)
        role_name = self.get_argument('role_name', default=None, strip=True)
        if not role_id and not role_name: return self.write(dict(status=-1, msg='关键参数不能为空'))

        extra = self.get_argument('extra', default=None, strip=True)
        extra = json.loads(extra) if extra else {}
        ignore_group = extra.get("ignore_group", False)
        count, role_list = get_user_list_for_role(ignore_group=ignore_group, is_page=True, **self.params)

        return self.write(dict(code=0, msg='获取成功', count=count, data=role_list))

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        raw_data = data.copy()
        user_list = data.get('user_list', None)
        role_id = data.get('role_id', None)
        user_list = list(set(user_list))

        if not role_id: return self.write(dict(code=-1, msg='角色不能为空'))

        if not user_list: return self.write(dict(code=-2, msg='选择的用户不能为空'))

        pre_check = data.get('pre_check', False)

        success_user, fail_user = [], []
        log_data = []
        with DBContext('w', None, True) as session:
            current_role = session.query(Roles).filter(Roles.role_id == role_id).first()
            if not current_role: return self.write(dict(code=-3, msg='当前角色不存在'))
            count_limit = current_role.count_limit
            if count_limit != -1:
                exit_user = session.query(UserRoles).filter(UserRoles.role_id == role_id, UserRoles.status == '0').all()
                if len(user_list) + len(exit_user) > count_limit:
                    return self.write(dict(code=-4, msg=f'角色用户数超过上限，已有{len(exit_user)}/{count_limit}'))

            # 角色的先决条件
            prereqst_list = session.query(Roles).filter(Roles.status == '0',
                                                        Roles.role_id.in_(current_role.prerequisites)).all()
            prereqst_list = [pre.role_id for pre in prereqst_list]

            if pre_check:
                trans_u = session.query(Users.user_id).filter(Users.username == user_list[0]).first()
                trans_id = trans_u[0]
                if not trans_id: return self.write(dict(code=-5, msg="用户不存在"))
                user_list = [trans_id]

            for user in user_list:
                exist_valid, msg = self.check_user_exist(user, role_id)
                if not exist_valid:
                    fail_user.append(user)
                    log_data.append({'user': user, 'msg': msg})
                    continue

                _, user_role_list = get_role_list_for_user(user_id=user)
                user_role_list = [i.get('role_id') for i in user_role_list]

                # 用户满足当前角色的先决条件
                pre_valid, msg = self.check_pre_valid(user, prereqst_list, user_role_list)
                if not pre_valid:
                    fail_user.append(user)
                    log_data.append({'user': user, 'msg': msg})
                    continue

                # 用户已有角色与当前角色不互斥
                mutual_valid, msg = self.check_mutual_valid(user, role_id, user_role_list)
                if not mutual_valid:
                    fail_user.append(user)
                    log_data.append({'user': user, 'msg': msg})
                    continue

                # 满足所有条件，授权成功
                success_user.append(user)

            # 预先检查
            if pre_check:
                if len(success_user) == len(user_list):
                    return self.write(
                        dict(code=0, success_user=success_user, fail_user=fail_user, log_data=log_data,
                             msg="预检查通过，角色添加用户满足条件"))
                else:
                    return self.write(
                        dict(code=-6, success_user=success_user, fail_user=fail_user, log_data=log_data,
                             msg="预检查失败，角色添加用户不满足条件"))

            new_users = [UserRoles(role_id=role_id, user_id=int(i)) for i in success_user]
            session.add_all(new_users)
            redis_conn = cache_conn()
            redis_conn.set(f"need_sync_all_cache", 'y', ex=600)

            msg = f"成功添加用户{len(success_user)}个，失败{len(fail_user)}条"
            log_id = add_operation_log(dict(
                username=self.request_username,
                operation="角色授权用户组",
                result=True,
                msg=msg,
                data=raw_data,
                response=dict(log_data=log_data)
            ))
        return self.write(
            dict(code=0, success_user=success_user, fail_user=fail_user, msg=msg, log_id=log_id,
                 log_data=log_data))

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        raw_data = data.copy()
        user_list = data.get('user_list', None)
        role_id = data.get('role_id', None)
        user_list = list(set(user_list))

        if not role_id: return self.write(dict(code=-1, msg='角色不能为空'))
        if not user_list: return self.write(dict(code=-2, msg='选择的用户不能为空'))

        ## 删除
        with DBContext('w', None, True) as session:
            session.query(UserRoles).filter(UserRoles.role_id == role_id,
                                            UserRoles.user_id.in_(user_list)).delete(synchronize_session=False)
            ###
            redis_conn = cache_conn()
            redis_conn.set(f"need_sync_all_cache", 'y', ex=600)

            add_operation_log(dict(
                username=self.request_username,
                operation="角色删除用户",
                result=True,
                msg='从角色中删除用户成功',
                data=raw_data
            ))

        self.write(dict(code=0, msg='从角色中删除用户成功'))

    def check_user_exist(self, user, role_id):
        """检查用户是否已在当前角色"""
        with DBContext('r', None, True) as session:
            user = session.query(UserRoles).filter(UserRoles.status == '0', UserRoles.user_id == user,
                                                   UserRoles.role_id == role_id).first()
            if user:
                user_name = session.query(Users.username).filter(Users.user_id == user).first()
                return False, f'用户{user_name[0]}已在该角色中'
        return True, ''

    def check_pre_valid(self, user_id, pre_list, user_role_list):
        """角色授权用户时，用户满足先决条件"""
        if not pre_list:
            return True, ''
        if not set(user_role_list) >= set(pre_list):
            with DBContext('r', None, True) as session:
                user_name = session.query(Users.username).filter(Users.user_id == user_id).first()
                return False, f'所选用户[{user_name[0]}]不满足角色的先决条件'
        return True, ''

    def check_mutual_valid(self, user, role_id, user_role_list):
        """用户授权用户时，检查互斥条件"""
        check_list = user_role_list + [role_id]
        check_list = list(set(check_list))
        res = check_mutual_role(check_list)
        if res:
            with DBContext('r', None, True) as session:
                user_name = session.query(Users.username).filter(Users.user_id == user).first()
                return False, f'用户{user_name[0]}已有角色与当前角色互斥'
        return True, ''


class RoleHeritHandler(BaseHandler):
    def get(self, *args, **kwargs):
        count, queryset = get_role_herit_list(**self.params)
        return self.write(dict(code=0, result=True, msg="获取角色继承关系成功", count=count, data=queryset))

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        role_id = data.get('role_id', None)
        if not role_id: return self.write(dict(code=-1, msg='不能为空'))

        with DBContext('w', None, True) as session:
            session.query(RolesInherit).filter(RolesInherit.role_id == role_id).delete(synchronize_session=False)
        return self.write(dict(code=0, msg='删除成功'))

    def put(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        role_id = data.get('role_id')

        if not role_id: return self.write(dict(code=-1, msg='ID不能为空'))
        if '_index' in data: data.pop('_index')
        if '_rowKey' in data: data.pop('_rowKey')

        params = dict(
            desc=data.get('desc', ''),
        )
        with DBContext('w', None, True) as session:
            session.query(RolesInherit).filter(RolesInherit.role_id == role_id).update(params)

        return self.write(dict(code=0, msg='编辑成功'))

    def herit_permission(self, parent_role_id, child_role_id):
        """检查继承关系"""
        return True


class RoleMutualHandler(BaseHandler):
    def get(self, *args, **kwargs):
        role_id = self.get_argument('role_id', default=None, strip=True)
        if not role_id: return self.write(dict(code=-1, msg='不能为空'))
        count, queryset = get_role_mutual_list(**self.params)
        return self.write(dict(code=0, result=True, msg="获取角色互斥关系成功", count=count, data=queryset))

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        role_left_id = data.get('role_left_id')
        role_right_id = data.get('role_right_id')

        if not self.mutual_permission(role_left_id, role_right_id):
            return self.write(dict(code=-1, msg='该互斥关系不允许'))

        with DBContext('w', None, True) as session:
            is_exist = session.query(RolesMutual).filter(RolesMutual.role_left_id == role_left_id,
                                                         RolesMutual.role_right_id == role_right_id).first()
            if is_exist: return self.write(dict(code=-2, msg='已存在互斥关系'))
            new_mutual = RolesMutual(**data)
            session.add(new_mutual)
            session.commit()
            redis_conn = cache_conn()
            redis_conn.set(f"need_sync_all_cache", 'y', ex=600)
        return self.write(dict(code=0, msg='互斥关系创建成功'))

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        role_mutual_id = data.get('role_mutual_id', None)
        if not role_mutual_id:  return self.write(dict(code=-1, msg='不能为空'))

        with DBContext('w', None, True) as session:
            session.query(RolesMutual).filter(RolesMutual.role_mutual_id == role_mutual_id).delete(
                synchronize_session=False)
        return self.write(dict(code=0, msg='删除成功'))

    def put(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        role_mutual_id = data.get('role_mutual_id')

        if not role_mutual_id: return self.write(dict(code=-1, msg='ID不能为空'))
        if '_index' in data: data.pop('_index')
        if '_rowKey' in data: data.pop('_rowKey')

        params = dict(
            desc=data.get('desc', ''),
            role_mutual_name=data.get('role_mutual_name', '')
        )
        with DBContext('w', None, True) as session:
            session.query(RolesMutual).filter(RolesMutual.role_mutual_id == role_mutual_id).update(params)

        return self.write(dict(code=0, msg='编辑成功'))

    def mutual_permission(self, left_role_id, right_role_id):
        """检查互斥关系"""
        return True


class RoleUserExcludeHandler(BaseHandler):
    def get(self, *args, **kwargs):
        role_id = self.get_argument('role_id', default=None, strip=True)
        if not role_id: return self.write(dict(status=-1, msg='关键参数不能为空'))

        count, user_list = get_user_exclude_list_for_role(**self.params)

        return self.write(dict(code=0, msg='获取成功', count=count, data=user_list))


class RoleGroupExcludeHandler(BaseHandler):
    def get(self, *args, **kwargs):
        role_id = self.get_argument('role_id', default=None, strip=True)
        if not role_id: return self.write(dict(status=-1, msg='关键参数不能为空'))

        count, user_list = get_group_exclude_list_for_role(ignore_info=False, **self.params)

        return self.write(dict(code=0, msg='获取成功', count=count, data=user_list))


roles_urls = [
    (r"/auth/v3/accounts/role/", RoleHandler, {"handle_name": "角色列表"}),
    (r"/auth/v3/accounts/role/user/", RoleUserHandler, {"handle_name": "角色-用户", "handle_status": "y"}),
    (r"/auth/v3/accounts/role/group/", RoleGroupHandler, {"handle_name": "角色-用户组"}),
    (r"/auth/v3/accounts/role/user_exclude/", RoleUserExcludeHandler, {"handle_name": "用户组-可关联用户"}),
    (r"/auth/v3/accounts/role/group_exclude/", RoleGroupExcludeHandler, {"handle_name": "用户组-可关联用户组"}),
    (r"/auth/v3/accounts/role/inherit/", RoleHeritHandler, {"handle_name": "角色继承关系"}),
    (r"/auth/v3/accounts/role/mutual/", RoleMutualHandler, {"handle_name": "角色互斥关系"}),
]

if __name__ == "__main__":
    pass
