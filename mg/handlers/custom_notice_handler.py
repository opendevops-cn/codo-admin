#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2021/5/17 16:52 
Desc    : 定制类型的通知
"""

import json
from tornado.concurrent import run_on_executor
from concurrent.futures import ThreadPoolExecutor
from libs.base_handler import BaseHandler
from libs.notice_utils import notice_factory
from tornado import gen
from websdk2.tools import convert
from websdk2.cache_context import cache_conn
###
from websdk2.db_context import DBContextV2 as DBContext
from models.admin_model import Users, Roles, UserRoles
from models.notice_model import NoticeGroup, NoticeConfig
from websdk2.model_utils import model_to_dict


class CustomNoticeHandler(BaseHandler):
    _thread_pool = ThreadPoolExecutor(10)

    @run_on_executor(executor='_thread_pool')
    def send_notice(self, way, notice_conf_map=None, **send_kwargs):

        try:
            obj = notice_factory(way, notice_conf_map=notice_conf_map)

            response = obj.send_update(**send_kwargs) if 'oa_update' in send_kwargs else obj.send_custom(**send_kwargs)

            if response and isinstance(response, bytes): response = response.decode()
            if response and isinstance(response, str):  response = json.loads(response)

            if response.get("Message") == "OK":
                res_msg = dict(code=0, msg=f'{way}发送成功')
                if "task_id" in response: res_msg["task_id"] = response.get('task_id')
                if "agent_id" in response: res_msg["agent_id"] = response.get('agent_id')
                return res_msg
            else:
                return dict(code=-4, msg=f'{way}发送失败{str(response)}')

        except Exception as e:
            return dict(code=-5, msg=f'{way}发送失败! {str(e)}')

    @gen.coroutine
    def post(self, *args, **kwargs):
        ### 发送钉钉OA类型
        data = json.loads(self.request.body.decode('utf-8'))
        msg = data.get('msg')
        userid_list = data.get('userid_list')
        if isinstance(userid_list, list): userid_list = ','.join(userid_list)
        ###

        redis_conn = cache_conn()
        notice_conf_map = redis_conn.hgetall("notice_conf_map")
        notice_conf_map = convert(notice_conf_map) if notice_conf_map else self.settings.get('notice_conf_map')
        if not notice_conf_map: notice_conf_map = get_notice_config()
        way = "dd_work"
        send_kwargs = {"msg": msg, "userid_list": userid_list}
        res = yield self.send_notice(way, notice_conf_map=notice_conf_map, **send_kwargs)
        return self.write(res)


class NoticeAddrHandler(BaseHandler):

    def get(self):
        users_str = self.get_argument('users_str', default=None, strip=True)  ### 用户
        notice_group_str = self.get_argument('notice_group_str', default=None, strip=True)  ###通知组
        roles_str = self.get_argument('roles_str', default=None, strip=True)  ### 角色组

        notice_user = []
        ### 处理通知组
        with DBContext('r') as session:
            if notice_group_str and isinstance(notice_group_str, str):
                notice_group_list = notice_group_str.split(',')
                group_info = session.query(NoticeGroup.user_list).filter(NoticeGroup.name.in_(notice_group_list)).all()
                for group in group_info:
                    if group[0]: notice_user = notice_user + group[0]

            if users_str and isinstance(users_str, str):
                user_list = users_str.split(',')
                notice_user = notice_user + user_list

            if roles_str and isinstance(roles_str, str):
                role_list = roles_str.split(',')
                role_info = session.query(Roles.role_name, UserRoles.user_id, Users.nickname).outerjoin(UserRoles,
                                                                                                        UserRoles.role_id == Roles.role_id).outerjoin(
                    Users, Users.user_id == UserRoles.user_id).filter(
                    Roles.role_name.in_(role_list), Users.status == '0').order_by(UserRoles.role_id).all()
                role_user_list = [msg[-1] for msg in role_info]
                notice_user = notice_user + role_user_list

            nickname_list = list(set(notice_user))

            tel_list = []
            email_list = []
            ddid_list = []

            notice_user_info = session.query(Users.tel, Users.email, Users.dd_id).filter(
                Users.nickname.in_(nickname_list)).all()

            notice_user_info2 = session.query(Users.tel, Users.email, Users.dd_id).filter(
                Users.username.in_(nickname_list)).all()

        for u in notice_user_info:
            if u[0]: tel_list.append(u[0])
            if u[1]: email_list.append(u[1])
            if u[2]: ddid_list.append(u[2])

        for u in notice_user_info2:
            if u[0]: tel_list.append(u[0])
            if u[1]: email_list.append(u[1])
            if u[2]: ddid_list.append(u[2])

        user_addr_info = {'tel': tel_list, 'email': email_list, 'dd_id': ddid_list}
        return self.write(dict(code=0, msg='获取成功', data=user_addr_info))


def get_notice_config():
    with DBContext('r') as session:
        all_config = session.query(NoticeConfig).filter(NoticeConfig.status == '0').all()

    all_config_dict = {}
    for msg in all_config:
        data_dict = model_to_dict(msg)
        key = data_dict['key']
        conf_map = data_dict.get('conf_map')
        try:
            json.loads(conf_map)
        except Exception as err:
            conf_map = "{}"
        if not conf_map: conf_map = "{}"

        all_config_dict[key] = conf_map
    return all_config_dict


custom_notice_urls = [
    (r'/v1/notifications/custom/', CustomNoticeHandler, {"handle_name": "通知中心-自定义通知"}),
    (r'/v1/notifications/send_addr/', NoticeAddrHandler, {"handle_name": "通知中心-获取通知信息"}),
]

if __name__ == "__main__":
    pass