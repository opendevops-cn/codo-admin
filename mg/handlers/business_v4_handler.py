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
from services.biz_service import opt_obj, get_biz_list_for_api, get_biz_list_v3, sync_biz_role_user


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


class BusinessListHandler(BaseHandler, ABC):

    def check_xsrf_cookie(self):
        pass

    def prepare(self):
        self.get_params_dict()
        self.codo_login()

    @staticmethod
    def get_biz_map(view_biz, request_tenantid):
        if request_tenantid:
            # 使用 next() 寻找第一个匹配的业务，如果没有找到则返回 None
            the_biz = next((biz for biz in view_biz if biz.get('biz_id') == request_tenantid), None)
        else:
            # 使用列表推导式过滤出不包含指定 biz_id 的业务列表
            the_biz_list = [biz for biz in view_biz if biz.get('biz_id') not in ['501', '502']]
            the_biz = the_biz_list[0] if the_biz_list else None

        return dict(biz_cn_name=the_biz.get('biz_cn_name'), biz_id=the_biz.get('biz_id')) if the_biz else None

    def get(self):
        self.params['is_superuser'] = self.request_is_superuser
        self.params['user_id'] = self.request_user_id
        view_biz = get_biz_list_v3(**self.params)

        try:
            the_biz_map = self.get_biz_map(view_biz, self.request_tenantid)
            if not the_biz_map:
                the_biz_map = dict(biz_cn_name='默认项目', biz_id='502')
        except Exception as err:
            logging.error(f'Error fetching business list: {err}')
            the_biz_map = dict(biz_cn_name='默认项目', biz_id='502')

        self.write(dict(code=0, msg="获取成功", data=view_biz, the_biz_map=the_biz_map))

    # def get(self):
    #     self.params['is_superuser'] = self.request_is_superuser
    #     self.params['user_id'] = self.request_user_id
    #     # self.params['user'] = self.request_fullname()
    #     view_biz = get_biz_list_v3(**self.params)
    #
    #     the_biz_map = dict()
    #     try:
    #         if self.request_tenantid:
    #             the_biz_list = list(filter(lambda x: x.get('biz_id') == self.request_tenantid, view_biz))
    #             if the_biz_list and isinstance(the_biz_list, list) and len(the_biz_list) == 1:
    #                 the_biz = the_biz_list[0]
    #                 the_biz_map = dict(biz_cn_name=the_biz.get('biz_cn_name'), biz_id=the_biz.get('biz_id'))
    #         else:
    #             the_biz_list = list(filter(lambda x: x.get('biz_id') not in ['501', '502'], view_biz))
    #             if the_biz_list and isinstance(the_biz_list, list) and len(the_biz_list) >= 1:
    #                 the_biz = the_biz_list[0]
    #                 the_biz_map = dict(biz_cn_name=the_biz.get('biz_cn_name'), biz_id=the_biz.get('biz_id'))
    #     except Exception as err:
    #         logging.error(f'业务列表 请求错误, {err}')
    #
    #     if not the_biz_map:
    #         the_biz_map = dict(biz_cn_name='默认项目', biz_id='502')
    #
    #     self.write(dict(code=0, msg="获取成功", data=view_biz, the_biz_map=the_biz_map))

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


# class BusinessTreeHandler(BaseHandler, ABC):
#
#     def check_xsrf_cookie(self):
#         pass
#
#     def prepare(self):
#         self.get_params_dict()
#         self.codo_login()
#
#     def get(self):
#         self.params['is_superuser'] = self.request_is_superuser
#         self.params['user'] = str(self.request_user_id)
#         tree_data = get_biz_tree(**self.params)
#         return self.write(dict(code=0, msg="获取成功", data=tree_data))


# class TenantHandler(BaseHandler, ABC):
#     def get(self):
#         res = get_tenant_list_for_api(**self.params)
#         self.write(res)
#
#     def post(self):
#         data = json.loads(self.request.body.decode("utf-8"))
#         res = opt_obj2.handle_add(data)
#
#         self.write(res)
#
#     def put(self):
#         data = json.loads(self.request.body.decode("utf-8"))
#         res = opt_obj2.handle_update(data)
#
#         self.write(res)
#
#     def delete(self):
#         data = json.loads(self.request.body.decode("utf-8"))
#         res = opt_obj2.handle_delete(data)
#
#         self.write(res)


biz_v4_mg_urls = [
    (r"/v4/biz/", BusinessHandler, {"handle_name": "权限中心-业务管理", "method": ["ALL"]}),
    # (r"/v4/tenant/", TenantHandler, {"handle_name": "权限中心-租户管理"}),
    (r"/v4/biz/list/", BusinessListHandler, {"handle_name": "PAAS基础功能-查看业务列表和切换", "method": ["GET"]}),
    # (r"/v4/biz/tree/", BusinessTreeHandler, {"handle_name": "权限中心-业务树"}),
]
if __name__ == "__main__":
    pass
