#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023/6/10 14:43
Desc    : 业务隔离
"""

import json
import logging
from abc import ABC
from datetime import datetime
from libs.base_handler import BaseHandler
from websdk2.db_context import DBContextV2 as DBContext
from models.paas_model import BizModel
from services.biz_service import opt_obj, get_biz_list_for_api, get_biz_list_v3, sync_biz_role_user, get_biz_map, \
    switch_business, get_biz_list_v4


class BusinessHandler(BaseHandler, ABC):
    def get(self):
        self.params['is_superuser'] = self.request_is_superuser
        self.params['username'] = self.request_username
        res = get_biz_list_for_api(**self.params)
        self.write(res)

    def post(self):
        # TODO  用户处理
        data = json.loads(self.request.body.decode("utf-8"))
        data['maintainer'] = dict(role=data.get('maintainer'))
        data['biz_sre'] = dict(role=data.get('biz_sre'))
        data['biz_developer'] = dict(role=data.get('biz_developer'))
        data['biz_tester'] = dict(role=data.get('biz_tester'))
        data['biz_pm'] = dict(role=data.get('biz_pm'))
        res = opt_obj.handle_add(data)
        sync_biz_role_user()

        self.write(res)

    def put(self):
        # TODO  用户处理
        data = json.loads(self.request.body.decode("utf-8"))
        if 'tenant' in data:
            del data['tenant']
        if 'ext_info' in data:
            del data['ext_info']
        if 'users_info' in data:
            del data['users_info']
        data['maintainer'] = dict(role=data.get('maintainer'))
        data['biz_sre'] = dict(role=data.get('biz_sre'))
        data['biz_developer'] = dict(role=data.get('biz_developer'))
        data['biz_tester'] = dict(role=data.get('biz_tester'))
        data['biz_pm'] = dict(role=data.get('biz_pm'))
        data['update_time'] = datetime.now()
        res = opt_obj.handle_update(data)
        sync_biz_role_user(id=data.get('id'))

        self.write(res)

    def delete(self):
        data = json.loads(self.request.body.decode("utf-8"))
        res = opt_obj.handle_delete(data)

        self.write(res)

# TODO 待废弃
class BusinessListHandler(BaseHandler, ABC):

    def check_xsrf_cookie(self):
        pass

    def prepare(self):
        self.get_params_dict()
        self.codo_login()

    def get(self):
        self.params['is_superuser'] = self.request_is_superuser
        self.params['user_id'] = self.request_user_id
        view_biz = get_biz_list_v3(**self.params)

        try:
            the_biz_map = get_biz_map(view_biz, self.request_tenantid)
            if not the_biz_map:
                the_biz_map = dict(biz_cn_name='默认项目', biz_id='502')
        except Exception as err:
            logging.error(f'Error fetching business list: {err}')
            the_biz_map = dict(biz_cn_name='默认项目', biz_id='502')

        self.write(dict(code=0, msg="获取成功", data=view_biz, the_biz_map=the_biz_map))

    def patch(self):
        #  手动切换  前端记录
        data = json.loads(self.request.body.decode("utf-8"))
        biz_id = data.get('biz_id')

        if not biz_id: return self.write(dict(code=-1, msg="缺少必要参数"))

        with DBContext('r') as session:
            biz_info = session.query(BizModel).filter(BizModel.biz_id == str(biz_id)).first()

            if not biz_info:
                return self.write(dict(code=-2, msg="未知业务信息/资源组信息"))

        try:
            self.set_secure_cookie("biz_id", str(biz_info.biz_id))
        except Exception as err:
            print(err)

        biz_dict = {"biz_id": str(biz_info.biz_id), "biz_cn_name": str(biz_info.biz_cn_name),
                    "biz_en_name": biz_info.biz_en_name}
        return self.write(dict(code=0, msg="获取成功", data=biz_dict))


class BizListNaHandler(BaseHandler, ABC):

    def get(self):
        self.params['is_superuser'] = self.request_is_superuser
        self.params['user_id'] = self.request_user_id
        view_biz = get_biz_list_v4(**self.params)

        try:
            the_biz_map = get_biz_map(view_biz, self.request_tenantid)
            if not the_biz_map:
                the_biz_map = dict(biz_cn_name='默认项目', biz_id='502')
        except Exception as err:
            logging.error(f'Error fetching business list: {err}')
            the_biz_map = dict(biz_cn_name='默认项目', biz_id='502')

        self.write(dict(code=0, msg="获取成功", data=view_biz, the_biz_map=the_biz_map))


class BizChangeNaHandler(BaseHandler, ABC):

    def get(self):
        self.params['is_superuser'] = self.request_is_superuser
        self.params['user_id'] = self.request_user_id
        res = switch_business(self.set_secure_cookie, **self.params)

        return self.write(res)


biz_v4_mg_urls = [
    (r"/v4/biz/", BusinessHandler, {"handle_name": "权限中心-业务管理", "method": ["ALL"]}),
    (r"/v4/biz/list/", BusinessListHandler, {"handle_name": "PAAS-基础功能-查看业务列表和切换", "method": ["GET"]}),
    (r"/v4/na/biz/list/", BizListNaHandler),  # 免认证查看业务列表
    (r"/v4/na/biz/change/", BizChangeNaHandler)   # 免认证切换业务
]
if __name__ == "__main__":
    pass
