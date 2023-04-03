#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
from libs.base_handler import BaseHandler
from websdk2.cache_context import cache_conn
from websdk2.db_context import DBContextV2 as DBContext
from models.authority_model import SubscribeRole
from services.subscribe_role import get_role_subscribe, add_operation_log, get_subscribe_preview, sign_subscribe, unsign_subscribe


class SubscribeHandler(BaseHandler):
    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        raw_data = data.copy()
        role_id = data.get('role_id')
        subscribe_type = data.get('subscribe_type')
        data = data.get('data')
        if not role_id: return self.write(dict(code=-1, msg='角色不能为空'))
        if not subscribe_type: return self.write(dict(code=-2, msg='订阅类型不能为空'))

        app_all = data.get('app_all')
        app_list = data.get('app_list')

        if not app_all and (not app_list or not isinstance(app_list, list)): return self.write(dict(code=-3, msg='应用列表有误'))
        if subscribe_type == 'function' and data.get('match_method') not in ["GET", "ALL"]:
            return self.write(dict(code=-4, msg='接口类型有误'))

        subs_obj = dict(
            role_id=role_id,
            subscribe_type=subscribe_type,
            app_all=app_all,
            app_list=data.get('app_list') if not app_all else [],
            match_key=data.get('match_key'),
            match_type=data.get('match_type'),
            match_method=data.get('match_method') if subscribe_type == 'function' else "",
            desc=data.get('desc'),
            status='0',
        )
        with DBContext('w', None, True) as session:
            exist_query = session.query(SubscribeRole).filter(SubscribeRole.role_id == subs_obj.get('role_id'),
                                                           SubscribeRole.app_all == subs_obj.get('app_all'),
                                                           SubscribeRole.match_key == subs_obj.get('match_key'),
                                                           SubscribeRole.match_type == subs_obj.get('match_type'),
                                                           SubscribeRole.match_method == subs_obj.get('match_method')).all()
            for exist in exist_query:
                if set(exist.app_list) >= set(subs_obj.get('app_list')):
                    return self.write(dict(code=-5, msg='该订阅已注册'))
            session.add(SubscribeRole(**subs_obj))
            sign_subscribe(**subs_obj)

        add_operation_log(dict(
            username=self.request_username,
            operation="角色订阅",
            result=True,
            msg='订阅成功',
            data=raw_data
        ))
        return self.write(dict(code=0, result=True, msg="角色订阅成功"))

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        raw_data = data.copy()
        subscribe_role_id = data.get('subscribe_role_id', None)
        if not subscribe_role_id: return self.write(dict(code=-1, msg='不能为空'))

        with DBContext('w', None, True) as session:
            subs_obj = session.query(SubscribeRole).filter(SubscribeRole.subscribe_role_id == subscribe_role_id).first()
            if not subs_obj: return self.write(dict(code=-2, msg='该订阅已删除'))
            data = dict(
                role_id=subs_obj.role_id,
                subscribe_type=subs_obj.subscribe_type,
                app_all=subs_obj.app_all,
                app_list=subs_obj.app_list,
                match_key=subs_obj.match_key,
                match_type=subs_obj.match_type,
                match_method=subs_obj.match_method,
                )
            session.query(SubscribeRole).filter(SubscribeRole.subscribe_role_id == subscribe_role_id).delete(synchronize_session=False)
            unsign_subscribe(**data)

            # 删除相应权限
            add_operation_log(dict(
                username=self.request_username,
                operation="删除订阅",
                result=True,
                msg='删除订阅成功',
                data=raw_data,
            ))
        return self.write(dict(code=0, msg='删除成功'))


class SubscribeRoleHandler(BaseHandler):
    def get(self, *args, **kwargs):
        role_id = self.params.get('role_id')
        subscribe_type = self.params.get("subscribe_type")
        if not role_id: return self.write(dict(code=-1, msg='角色不能为空'))
        self.params["role_list"] = [int(role_id)]
        self.params["subscribe_type"] = [subscribe_type] if subscribe_type else []
        count, data = get_role_subscribe(**self.params)
        return self.write(dict(code=0, msg='获取角色订阅成功', count=count, data=data))


class SubscribePreviewHandler(BaseHandler):
    def get(self, *args, **kwargs):
        subscribe_role_id = self.params.get('subscribe_role_id')
        if not subscribe_role_id: return self.write(dict(code=-1, msg='订阅id不能为空'))

        with DBContext('w', None, True) as session:
            is_exist = session.query(SubscribeRole).filter(SubscribeRole.subscribe_role_id == subscribe_role_id).first()
            if not is_exist: return self.write(dict(code=-3, msg='该订阅不存在'))

            data = dict(
                subscribe_type=is_exist.subscribe_type,
                app_all=is_exist.app_all,
                app_list=is_exist.app_list,
                match_key=is_exist.match_key,
                match_type=is_exist.match_type,
                match_method=is_exist.match_method,
            )
            query = get_subscribe_preview(**data)
        return self.write(dict(code=0, result=True, msg="获取预览成功", data=query))


subscribe_urls = [
    (r"/auth/v3/accounts/subscribe/", SubscribeHandler, {"handle_name": "订阅列表"}),
    (r"/auth/v3/accounts/subscribe/role/", SubscribeRoleHandler, {"handle_name": "订阅列表-角色"}),
    (r"/auth/v3/accounts/subscribe/preview/", SubscribePreviewHandler, {"handle_name": "订阅预览"}),
]

if __name__ == "__main__":
    pass
