#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2018/11/2
Desc    : 用户组
"""

import json
from libs.base_handler import BaseHandler
from websdk2.cache_context import cache_conn
from websdk2.model_utils import model_to_dict
from websdk2.db_context import DBContextV2 as DBContext
from models.authority_model import Groups, Roles, UserRoles, UserGroups, GroupRoles, Users, GroupsRelate
from services.group_services import get_user_list_for_role, get_all_user_list_for_role, get_groups_list,\
    check_mutual_role, add_operation_log, get_role_list_for_user, get_user_list_for_group, get_user_exclude_list_for_group


class GroupHandler(BaseHandler):

    def get(self, *args, **kwargs):
        count, queryset = get_groups_list(**self.params)
        return self.write(dict(code=0, result=True, msg="获取用户组成功", count=count, data=queryset))

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        raw_data = data.copy()
        group_name = data.get('group_name')
        if not group_name: return self.write(dict(code=-1, msg='用户组名不能为空'))

        is_relate = data.get('is_relate')
        relate_group = data.get('relate_group')
        # if not is_relate and not data.get('end_time'): return self.write(dict(code=-2, msg='缺失关键参数【到期日期】'))

        with DBContext('w', None, True) as session:
            if is_relate:
                if not relate_group:
                    return self.write(dict(code=-3, msg='关联用户组为空'))
                group_check = session.query(Groups).filter(Groups.group_id.in_(relate_group), Groups.source != "组织架构同步").all()
                if group_check:
                    return self.write(dict(code=-4, msg='关联用户组非法'))

            is_exist = session.query(Groups).filter(Groups.group_name == group_name).first()
            if is_exist: return self.write(dict(code=-5, msg='用户组已存在'))

            group_data = dict(
                group_name=group_name,
                desc=data.get('desc'),
                end_time=data.get('end_time')
            )

            new_group = Groups(**group_data)
            session.add(new_group)
            session.commit()
            group_id = new_group.group_id

            # 建立用户组关联组织架构
            if is_relate:
                relate_valid = session.query(Groups.group_id).filter(Groups.status == '0',
                                                                     Groups.group_id.in_(relate_group),
                                                                     Groups.source == "组织架构同步").all()
                relate_valid = [int(i[0]) for i in relate_valid if i[0]]
                new_relate = [GroupsRelate(group_id=group_id, relate_id=int(i)) for i in relate_valid]
                session.add_all(new_relate)

            redis_conn = cache_conn()
            redis_conn.set(f"need_sync_all_cache", 'y', ex=600)

            add_operation_log(dict(
                username=self.request_username,
                operation="新增用户组",
                result=True,
                msg='用户组创建成功',
                data=raw_data
            ))
        return self.write(dict(code=0, msg='用户组创建成功'))

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        raw_data = data.copy()
        group_id = data.get('group_id', None)
        if not group_id: return self.write(dict(code=-1, msg='不能为空'))

        with DBContext('w', None, True) as session:
            # relate_q = session.query(GroupsRelate).outerjoin(Groups, Groups.group_id == GroupsRelate.group_id).filter(
            #     GroupsRelate.group_id == group_id, GroupsRelate.status == '0', Groups.status == '0').all()
            # if relate_q: return self.write(dict(code=-2, msg='存在关联用户组，不可删除'))

            group_obj = session.query(Groups).filter(Groups.group_id == group_id).first()
            if not group_obj: return self.write(dict(code=-3, msg='用户组不存在'))
            if group_obj.status == '0':
                return self.write(dict(code=-3, msg=f"当前用户组状态有效, 不可删除"))

            session.query(Groups).filter(Groups.group_id == group_id).update(dict(status='10'))
            session.query(UserGroups).filter(UserGroups.group_id == group_id).update(dict(status='10'))
            session.query(GroupRoles).filter(GroupRoles.group_id == group_id).update(dict(status='10'))

            add_operation_log(dict(
                username=self.request_username,
                operation="删除用户组",
                result=True,
                msg='用户组删除成功',
                data=raw_data
            ))
        return self.write(dict(code=0, msg='删除成功'))

    def put(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        raw_data = data.copy()
        group_id = data.get('group_id')
        group_name = data.get('group_name')

        if not group_id: return self.write(dict(code=-1, msg='ID不能为空'))
        if not group_name: return self.write(dict(code=-2, msg='用户组名称不能为空'))

        is_relate = data.get('is_relate')
        relate_group = data.get('relate_group')
        # if not is_relate and not data.get('end_time'): return self.write(dict(code=-3, msg='缺失关键参数【到期日期】'))

        with DBContext('w', None, True) as session:
            if is_relate:
                if not relate_group:
                    return self.write(dict(code=-4, msg='关联用户组为空'))
                group_check = session.query(Groups).filter(Groups.group_id.in_(relate_group), Groups.source != "组织架构同步").all()
                if group_check:
                    return self.write(dict(code=-5, msg='关联用户组非法'))

            is_exist = session.query(Groups.group_id).filter(Groups.group_id != group_id, Groups.status != '10',
                                                             Groups.group_name == group_name).first()
            if is_exist:
                return self.write(dict(code=-6, msg=f'用户组 "{group_name}" 已存在'))

            group_data = dict(
                group_name=group_name,
                desc=data.get('desc'),
                end_time=data.get('end_time')
            )
            session.query(Groups).filter(Groups.group_id == group_id).update(group_data)

            session.query(GroupsRelate).filter(GroupsRelate.group_id == group_id).delete()
            if is_relate:
                relate_valid = session.query(Groups.group_id).filter(Groups.status == '0',
                                                                     Groups.group_id.in_(relate_group),
                                                                     Groups.source == "组织架构同步").all()
                relate_valid = [int(i[0]) for i in relate_valid if i[0]]
                new_relate = [GroupsRelate(group_id=group_id, relate_id=int(i)) for i in relate_valid]
                session.add_all(new_relate)

            add_operation_log(dict(
                username=self.request_username,
                operation="修改用户组",
                result=True,
                msg='用户组修改成功',
                data=raw_data
            ))
        return self.write(dict(code=0, msg='编辑成功'))

    def patch(self, *args, **kwargs):
        """禁用、启用"""
        data = json.loads(self.request.body.decode("utf-8"))
        raw_data = data.copy()
        group_id = str(data.get('group_id', None))
        if not group_id: return self.write(dict(code=-1, msg='用户组id不能为空'))

        with DBContext('r') as session:
            group_status = session.query(Groups.status, Groups.source).filter(Groups.group_id == group_id, Groups.status != '10').first()

        if not group_status: return self.write(dict(code=-2, msg='用户组不存在'))

        if group_status[1] == '组织架构同步': return self.write(dict(code=-3, msg=f"用户组来源为{group_status[1]}, 不可更改状态"))

        if group_status[0] == '0':
            msg = '用户组禁用成功'
            new_status = '20'

        elif group_status[0] == '20':
            msg = '用户组启用成功'
            new_status = '0'
        else:
            new_status = '10'

        with DBContext('w', None, True) as db:
            db.query(Groups).filter(Groups.group_id == group_id, Groups.status != '10').update({Groups.status: new_status})

            add_operation_log(dict(
                username=self.request_username,
                operation="启/禁用用户组",
                result=True,
                msg=msg,
                data=raw_data
            ))
        return self.write(dict(code=0, msg=msg))


class GroupUserHandler(BaseHandler):
    def get(self, *args, **kwargs):
        group_id = self.get_argument('group_id', default=None, strip=True)
        group_name = self.get_argument('group_name', default=None, strip=True)
        if not group_id and not group_name: return self.write(dict(status=-1, msg='关键参数不能为空'))
        count, user_list = get_user_list_for_group(is_page=True, contain_relate=True, **self.params)

        return self.write(dict(code=0, msg='获取成功', count=count, data=user_list))

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        raw_data = data.copy()
        group_id = data.get('group_id')
        user_list = data.get('user_list', [])
        if not group_id: return self.write(dict(code=-1, msg='用户组id不能为空'))
        if not user_list: return self.write(dict(code=-2, msg='选择的用户不能为空'))

        # user_list = list(set(user_list))

        success_user, fail_user = [], []
        log_data = []
        with DBContext('w', None, True) as session:

            exist = session.query(Groups).filter(Groups.group_id == group_id).first()
            if exist.source != "自定义": return self.write(dict(code=-3, msg=f'该用户组从组织架构同步,不能添加用户'))

            relate_exist = session.query(GroupsRelate).filter(GroupsRelate.group_id == group_id, GroupsRelate.status == '0').all()
            if not exist.end_time and relate_exist:
                return self.write(dict(code=-3, msg=f'用户组类型为【组织架构关联组】,不能添加用户'))

            group_role = session.query(GroupRoles).filter(GroupRoles.status == '0', GroupRoles.group_id == group_id).all()
            if not group_role:
                # 直接添加
                success_user, fail_user = user_list, []
            else:
                # 先决条件 互斥条件均满足，才能添加成功
                bound_role_list = session.query(Roles.role_id, Roles.role_name, Roles.prerequisites,).outerjoin(GroupRoles,
                                                                                         Roles.role_id == GroupRoles.role_id).filter(GroupRoles.group_id == group_id, Roles.status == '0', GroupRoles.status == '0').all()
                for user in user_list:
                    exist_valid, msg = self.check_user_exist(user, group_id)
                    if not exist_valid:
                        fail_user.append(user)
                        log_data.append({'user': user, 'msg': msg})
                        continue

                    _, user_role_list = get_role_list_for_user(user_id=user)
                    pre_valid, msg = self.check_prequest_valid(user, bound_role_list, user_role_list)
                    if not pre_valid:
                        fail_user.append(user)
                        log_data.append({'user': user, 'msg': msg})
                        continue

                    mutual_valid, msg = self.check_mutual_valid(user, bound_role_list, user_role_list)
                    if not mutual_valid:
                        fail_user.append(user)
                        log_data.append({'user': user, 'msg': msg})
                        continue

                    success_user.append(user)
            new_users = [UserGroups(group_id=group_id, user_id=int(i)) for i in success_user]
            session.add_all(new_users)
            redis_conn = cache_conn()
            redis_conn.set(f"need_sync_all_cache", 'y', ex=600)

            msg = f"成功添加用户{len(success_user)}个，失败{len(fail_user)}条"
            log_id = add_operation_log(dict(
                username=self.request_username,
                operation="用户组授权用户",
                result=True,
                msg=msg,
                data=raw_data,
                response=dict(log_data=log_data)
            ))
        return self.write(dict(code=0, success_user=success_user, fail_user=fail_user,msg=msg, log_id=log_id, log_data=log_data))

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        raw_data = data.copy()
        group_id = data.get('group_id', None)
        user_list = data.get('user_list', [])
        user_list = list(set(user_list))
        if not group_id: return self.write(dict(code=-1, msg='不能为空'))
        if not user_list: return self.write(dict(code=-2, msg='选择的用户不能为空'))

        with DBContext('w', None, True) as session:

            exist = session.query(Groups).filter(Groups.group_id == group_id).first()
            if not exist: return self.write(dict(code=-3, msg='用户组不存在'))

            if exist.source != "自定义": return self.write(dict(code=-4, msg=f'该用户组从组织架构同步,不能删除用户'))

            relate_exist = session.query(GroupsRelate).filter(GroupsRelate.group_id == group_id, GroupsRelate.status == '0').all()
            if not exist.end_time and relate_exist:
                return self.write(dict(code=-5, msg=f'用户组类型为【组织架构关联组】,不能删除用户'))

            session.query(UserGroups).filter(UserGroups.group_id == group_id,
                                            UserGroups.user_id.in_(user_list)).delete(synchronize_session=False)
            redis_conn = cache_conn()
            redis_conn.set(f"need_sync_all_cache", 'y', ex=600)

            add_operation_log(dict(
                username=self.request_username,
                operation="用户组删除用户",
                result=True,
                msg='从用户组中删除用户成功',
                data=raw_data
            ))
        return self.write(dict(code=0, msg='删除成功'))

    def check_user_exist(self, user, group_id):
        """检查用户是否已在当前组"""
        with DBContext('r', None, True) as session:
            user = session.query(UserGroups).filter(UserGroups.status == '0', UserGroups.user_id == user, UserGroups.group_id == group_id).first()
            if user:
                user_name = session.query(Users.username).filter(Users.user_id == user).first()
                return False, f'用户{user_name[0]}已在该组中'
        return True, ''

    def check_prequest_valid(self, user, prereqst_list, user_role_list):
        """用户授权用户组时，检查先觉条件"""
        if not prereqst_list:
            return True, ''

        role_list = [i.get('role_id') for i in user_role_list]
        for pre in prereqst_list:
            if pre[2]:  # 如果有先决条件
                with DBContext('r', None, True) as session:
                    prereqst_list = session.query(Roles).filter(Roles.status == '0',
                                                                Roles.role_id.in_(pre[2])).all()
                    prereqst_list = [pre.role_id for pre in prereqst_list]

                    if not set(role_list) >= set(prereqst_list):
                        user_name = session.query(Users.username).filter(Users.user_id == user).first()
                        return False, f'用户{user_name[0]}不满足角色[{pre[1]}]的先决条件'
        return True, ''

    def check_mutual_valid(self, user, bound_role_list, user_role_list):
        """用户授权用户组时，检查互斥条件"""
        bound_role_list = [i[0] for i in bound_role_list]
        user_role_list = [i.get('role_id') for i in user_role_list]
        check_list = bound_role_list + user_role_list
        res = check_mutual_role(check_list)
        if res:
            with DBContext('r', None, True) as session:
                user_name = session.query(Users.username).filter(Users.user_id == user).first()
                return False, f'用户{user_name[0]}与该用户组当前角色互斥'
        return True, ''


class GroupUserExcludeHandler(BaseHandler):
    def get(self, *args, **kwargs):
        group_id = self.get_argument('group_id', default=None, strip=True)
        group_name = self.get_argument('group_name', default=None, strip=True)
        if not group_id and not group_name: return self.write(dict(status=-1, msg='关键参数不能为空'))

        with DBContext('w', None, True) as session:

            exist = session.query(Groups).filter(Groups.group_id == group_id).first()
            if exist.source != "自定义": return self.write(dict(code=-3, msg=f'该用户组从组织架构同步,不能添加用户'))

            relate_exist = session.query(GroupsRelate).filter(GroupsRelate.group_id == group_id, GroupsRelate.status == '0').all()
            if not exist.end_time and relate_exist:
                return self.write(dict(code=-3, msg=f'用户组类型为【组织架构关联组】,不能添加用户'))

        count, user_list = get_user_exclude_list_for_group(**self.params)

        return self.write(dict(code=0, msg='获取成功', count=count, data=user_list))


class GroupDepTreeHandler(BaseHandler):
    def get(self, *args, **kwargs):
        with DBContext('r') as session:
            group_info = session.query(Groups.group_id, Groups.group_name).filter(Groups.status == '0', Groups.source == '组织架构同步').all()

        group_list = [dict(id=str(g[0]), label=g[1].replace("(Feishu)", "")) for g in group_info]

        tree = []

        for group in group_list:
            level_list = group.get("label").split("丨")

            level, children = len(level_list), tree
            while level:
                find_flag = False
                for c in children:
                    if c.get("label") == level_list[len(level_list) - level]:
                        if "children" not in c.keys():
                            c["children"] = []
                        children = c["children"]
                        find_flag = True
                        break
                if not find_flag:
                    children.append(dict(id=str(group.get("id")), label=level_list[len(level_list) - level]))
                level -= 1

        return self.write(dict(code=0, result=True, msg="获取用户组成功", count=len(group_list), data=tree))


groups_urls = [
    (r"/auth/v3/accounts/group/", GroupHandler, {"handle_name": "用户组列表"}),
    (r"/auth/v3/accounts/group/dep_tree/", GroupDepTreeHandler, {"handle_name": "组织架构树列表"}),
    (r"/auth/v3/accounts/group/user/", GroupUserHandler, {"handle_name": "用户组-用户关联"}),
    (r"/auth/v3/accounts/group/user_exclude/", GroupUserExcludeHandler, {"handle_name": "用户组-可关联用户"}),
]

if __name__ == "__main__":
    pass
