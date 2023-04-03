#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2020/6/10 14:43
Desc    : 业务隔离
"""

import json
import base64
from libs.base_handler import BaseHandler
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.model_utils import model_to_dict
from models.biz_model import BusinessModel
from sqlalchemy import or_
from websdk2.sqlalchemy_pagination import paginate


class BusinessHandler(BaseHandler):

    def check_xsrf_cookie(self):
        pass

    def prepare(self):
        self.get_params_dict()
        self.codo_login()

    def get(self):
        self.params['is_superuser'] = self.request_is_superuser
        self.params['username'] = self.request_username
        count, all_queryset, queryset, view_biz = get_biz_list_v2(**self.params)

        the_biz_map = dict()
        the_tenant_map = dict()
        try:
            if self.request_tenantid:
                the_biz_list = list(filter(lambda x: x.get('business_id') == self.request_tenantid, view_biz))
                if the_biz_list and isinstance(the_biz_list, list) and len(the_biz_list) == 1:
                    the_biz = the_biz_list[0]
                    the_biz_map = dict(resource_group=the_biz.get('resource_group'))
                    the_tenant_map = dict(tenantid=self.request_tenantid)
            else:
                the_biz_list = list(filter(lambda x: x.get('resource_group') not in ['默认项目', '公共项目'], view_biz))
                if the_biz_list and isinstance(the_biz_list, list) and len(the_biz_list) >= 1:
                    the_biz = the_biz_list[0]
                    the_biz_map = dict(resource_group=the_biz.get('resource_group'))
                    the_tenant_map = dict(tenantid=the_biz.get('business_id'))
        except Exception as err:
            print('BusinessHandler', err)

        if not the_biz_map: the_biz_map = dict(resource_group='默认项目')
        if not the_tenant_map and the_biz_map.get('resource_group') == '默认项目':
            try:
                the_biz_list = list(filter(lambda x: x.get('resource_group') == '默认项目', view_biz))
                the_tenant_map = dict(tenantid=the_biz_list[0].get('business_id'))
            except Exception as e:
                pass

        self.write(dict(code=0, result=True, msg="获取成功", count=count, data=view_biz, all_data=all_queryset,
                        queryset=queryset, the_biz_map=the_biz_map, the_tenant_map=the_tenant_map))
        add_init_resource_group_all()
        add_init_resource_group_public()

    def post(self):
        data = json.loads(self.request.body.decode("utf-8"))
        business_zh = data.get('business_zh')
        business_en = data.get('business_en')
        resource_group = data.get('resource_group')

        if not business_en or not business_zh or not resource_group:
            return self.write(dict(code=-1, result=False, msg="关键参数不能为空"))

        with DBContext('w', None, True) as session:
            is_exist = session.query(BusinessModel).filter(BusinessModel.business_en == business_en).first()
            if is_exist: return self.write(dict(code=-2, msg='不要重复添加', result=False))

            biz_id = session.query(BusinessModel).order_by(-BusinessModel.id).limit(1).first()
            business_id = biz_id.id + 500 if biz_id else 500
            data['business_id'] = business_id
            session.add(BusinessModel(**data))

        return self.write(dict(code=0, msg="添加成功", result=True))

    def put(self):
        data = json.loads(self.request.body.decode("utf-8"))
        biz_id = data.get('id')
        business_id = data.get('business_id')
        business_zh = data.get('business_zh')
        business_en = data.get('business_en')
        resource_group = data.get('resource_group')
        if '_index' in data: data.pop('_index')
        if '_rowKey' in data: data.pop('_rowKey')

        if not business_id or not business_en or not business_zh or not resource_group:
            return self.write(dict(code=-1, result=False, msg="关键参数不能为空"))

        with DBContext('w', None, True) as session:
            session.query(BusinessModel).filter(BusinessModel.id == biz_id).update(data)

        return self.write(dict(code=0, msg="修改成功", result=True))

    def patch(self):
        ## 切换
        data = json.loads(self.request.body.decode("utf-8"))
        business_id = data.get('business_id', data.get('tenantid'))
        resource_group = data.get('resource_group')

        if not business_id and not resource_group: return self.write(dict(code=-1, result=False, msg="缺少必要参数"))

        with DBContext('r') as session:
            if business_id:
                biz_info = session.query(BusinessModel).filter(BusinessModel.business_id == str(business_id)).first()
            else:
                biz_info = session.query(BusinessModel).filter(BusinessModel.resource_group == resource_group).first()

        if not biz_info: return self.write(dict(code=-2, result=False, msg="未知业务信息/资源组信息"))

        try:
            self.set_secure_cookie("business_id", str(biz_info.business_id))
            self.set_secure_cookie("resource_group", biz_info.resource_group)
            self.set_secure_cookie("tenantid", str(biz_info.business_id))
            self.set_cookie("tenant", base64.b64encode(biz_info.resource_group.encode('utf-8')).decode())
        except Exception as err:
            print(err)

        # biz_dict = model_to_dict(biz_info)
        biz_dict = {"tenantid": str(biz_info.business_id), "tenant": biz_info.resource_group,
                    "business_id": str(biz_info.business_id),
                    "business_en": biz_info.business_en, "resource_group": biz_info.resource_group}
        return self.write(dict(code=0, result=True, msg="获取成功", data=biz_dict))

    def delete(self):
        data = json.loads(self.request.body.decode("utf-8"))
        delete_id = data.get('id')
        if not delete_id: return self.write(dict(code=-1, msg="关键参数不能为空", result=False))

        with DBContext('w', None, True) as session:
            session.query(BusinessModel).filter(BusinessModel.id == delete_id).delete(synchronize_session=False)

        return self.write(dict(code=0, msg="删除成功", result=True))


def add_init_resource_group_all():
    ### 添加初始化的资源组
    with DBContext('w', None, True) as session:
        is_exist = session.query(BusinessModel).filter(BusinessModel.resource_group == '所有项目').first()
        if is_exist: return

        session.add(BusinessModel(**dict(business_zh='所有项目', business_en='all',
                                         business_id=str(500), resource_group='所有项目')))
        return


def add_init_resource_group_public():
    ### 添加初始化的资源组
    with DBContext('w', None, True) as session:
        is_exist = session.query(BusinessModel).filter(BusinessModel.resource_group == '公共项目').first()
        if is_exist: return

        session.add(BusinessModel(**dict(business_zh='公共项目', business_en='public',
                                         business_id=str(501), resource_group='公共项目')))
        return


###
def get_biz_list_v2(**params):
    value = params.get('value')
    if "searchValue" in params: value = params.get('searchValue')
    params['page_size'] = 300  ### 默认获取到全部数据
    is_superuser = params.get('is_superuser')
    username = params.get('username')

    with DBContext('r') as session:
        if value:
            page = paginate(session.query(BusinessModel).filter(BusinessModel.life_cycle != "停运").filter(
                or_(BusinessModel.business_zh.like('%{}%'.format(value)),
                    BusinessModel.business_en.like('%{}%'.format(value)),
                    BusinessModel.resource_group.like('%{}%'.format(value)),
                    BusinessModel.business_id == value)), **params)
        else:
            page = paginate(session.query(BusinessModel).filter(BusinessModel.life_cycle != "停运"), **params)

    all_queryset = page.items

    queryset = [q for q in all_queryset if q.get('resource_group')]
    view_biz_list = queryset if is_superuser else [biz for biz in queryset if
                                                   (biz.get('maintainer') and username in biz.get(
                                                       'maintainer')) or biz.get('business_en') in ['default',
                                                                                                    'public']]

    return page.total, all_queryset, queryset, view_biz_list


biz_mg_urls = [
    (r"/v1/base/biz/", BusinessHandler, {"handle_name": "权限中心-租户管理"}),
]
if __name__ == "__main__":
    pass
