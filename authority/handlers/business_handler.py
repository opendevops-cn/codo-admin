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
from models.biz_model import BusinessModel, BusinessTreeModel
from websdk2.model_utils import model_to_dict
from models.authority_model import RoleBusiness, Roles
from services.biz_services import get_user_list_for_group, add_operation_log, get_user_list_for_role
from sqlalchemy import or_, case
from websdk2.sqlalchemy_pagination import paginate


CMDB_BIZ_DEFAULT_ROLE = {"运维角色": "maintainer", "产品角色": "productor", "测试角色": "tester", "开发角色": "developer",
                         "操作角色": "operator", "通知角色": "noticer"}


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
        raw_data = data.copy()
        business_zh = data.get('business_zh')
        business_en = data.get('business_en')
        resource_group = data.get('resource_group')

        if not business_en or not business_zh or not resource_group:
            return self.write(dict(code=-1, result=False, msg="关键参数不能为空"))
        with DBContext('w', None, True) as session:
            is_exist = session.query(BusinessModel).filter(BusinessModel.business_en == business_en).first()
            if is_exist: return self.write(dict(code=-2, msg='业务名已存在', result=False))

            biz_id = session.query(BusinessModel).filter(BusinessModel.business_group == "OPS").order_by(-BusinessModel.business_id).limit(1).first()

            business_id = int(biz_id.business_id) + 1 if biz_id else 500
            data['business_id'] = str(business_id)
            data["business_group"] = "OPS"
            session.add(BusinessModel(**data))

        add_operation_log(dict(
            username=self.request_username,
            operation="新增业务",
            result=True,
            msg='业务创建成功',
            data=raw_data
        ))
        return self.write(dict(code=0, msg="添加成功", result=True))

    def put(self):
        data = json.loads(self.request.body.decode("utf-8"))
        raw_data = data.copy()
        business_id = data.pop('business_id')
        business_zh = data.get('business_zh')
        resource_group = data.get('resource_group')
        user_list = data.get("user_list")
        group_list = data.get("group_list")
        if isinstance(data, dict) and "business_en" in data.keys():
            return self.write(dict(code=-1, result=False, msg="业务英文名 business_en 不可修改"))

        if not business_id:
            return self.write(dict(code=-2, result=False, msg="关键参数不能为空"))

        if not isinstance(user_list, list) or not isinstance(group_list, list):
            return self.write(dict(code=-3, result=False, msg="关联人员格式有误"))

        with DBContext('w', None, True) as session:
            exist = session.query(BusinessModel).filter(BusinessModel.business_zh == business_zh, BusinessModel.business_id != business_id).first()
            if exist:
                return self.write(dict(code=-4, result=False, msg=f"【{business_zh}】已存在"))

            session.query(BusinessModel).filter(BusinessModel.business_id == business_id).update(data)

        add_operation_log(dict(
            username=self.request_username,
            operation="修改业务",
            result=True,
            msg='业务修改成功',
            data=raw_data
        ))
        return self.write(dict(code=0, msg="修改成功", result=True))

    def patch(self):
        ## 切换
        data = json.loads(self.request.body.decode("utf-8"))
        business_id = data.get('business_id', data.get('tenantid'))
        resource_group = data.get('resource_group')

        if not business_id and not resource_group: return self.write(dict(code=-1, result=False, msg="缺少必要参数"))
        if business_id: return self.write(dict(code=-2, result=False, msg="业务数据不支持修改状态"))

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
        if delete_id: return self.write(dict(code=-1, msg="业务数据不支持删除", result=False))
        if not delete_id: return self.write(dict(code=-2, msg="关键参数不能为空", result=False))

        with DBContext('w', None, True) as session:
            session.query(BusinessModel).filter(BusinessModel.id == delete_id).delete(synchronize_session=False)
            session.query(RoleBusiness).filter(RoleBusiness.business_id == delete_id).delete(synchronize_session=False)

        return self.write(dict(code=0, msg="删除成功", result=True))


def add_init_resource_group_all():
    ### 添加初始化的资源组
    with DBContext('w', None, True) as session:
        is_exist = session.query(BusinessModel).filter(BusinessModel.resource_group == '所有项目').first()
        if is_exist: return

        session.add(BusinessModel(**dict(business_zh='所有项目-有权限的所有项目', business_en='all',
                                         business_id=str(500), resource_group='所有项目',
                                         business_group="OPS")))
        return


def add_init_resource_group_public():
    ### 添加初始化的资源组
    with DBContext('w', None, True) as session:
        is_exist = session.query(BusinessModel).filter(BusinessModel.resource_group == '公共项目').first()
        if is_exist: return

        session.add(BusinessModel(**dict(business_zh='公共项目-大家都有权限', business_en='public',
                                         business_id=str(501), resource_group='公共项目',
                                         business_group="OPS")))
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
            page = paginate(session.query(BusinessModel).filter_by(**dict(life_cycle="2")).filter(
                or_(BusinessModel.business_zh.like('%{}%'.format(value)),
                    BusinessModel.business_en.like('%{}%'.format(value)),
                    BusinessModel.resource_group.like('%{}%'.format(value)),
                    BusinessModel.business_id == value)).order_by(
                case(value=BusinessModel.business_group, whens={"OPS": 0,
                                                                "CMS": 1,
                                                                }),
                BusinessModel.business_group.desc()), **params)
        else:
            page = paginate(session.query(BusinessModel).filter_by(**dict(life_cycle="2")).order_by(
                case(value=BusinessModel.business_group, whens={"OPS": 0,
                                                                "CMS": 1,
                                                                }),
                BusinessModel.business_group.desc()), BusinessModel.business_id, **params)

        biz_query = session.query(BusinessModel).filter(BusinessModel.life_cycle == '2').all()
        map_dict = {biz.business_id: biz.business_zh for biz in biz_query}

    for item in page.items:
        if item.get('business_group') == 'OPS' and item.get('map_client_id'):
            item["map_resource"] = "CMS丨" + map_dict.get(str(item.get('map_client_id')))

    all_queryset = page.items

    queryset = [q for q in all_queryset if q.get('resource_group')]
    view_biz_list = queryset if is_superuser else [biz for biz in queryset if
                                                   (biz.get('maintainer') and username in biz.get(
                                                       'maintainer')) or biz.get('business_en') in ['default',
                                                                                                    'public']]

    return page.total, all_queryset, queryset, view_biz_list


def get_biz_user(biz_query):
    with DBContext('w', None, True) as session:
        # 默认角色人员
        role_list = session.query(Roles.role_id, Roles.role_name).filter(Roles.role_name.in_(CMDB_BIZ_DEFAULT_ROLE.keys()), Roles.role_type == 'default').all()

        role_user_dict = {}
        for role in role_list:
            role_id, role_name = role[0], role[1]
            _, user_list = get_user_list_for_role(role_id=role_id)
            role_user_dict[role_name] = [u.get("username") for u in user_list if u.get("username")]

        # 业务人员， 如果在默认角色中， 则是该业务的角色人员
        for biz in biz_query:
            user_list, group_list = biz.get("user_list", []), biz.get("group_list", [])
            all_group_user = []
            for group in group_list:
                _, group_user = get_user_list_for_group(group_name=group, contain_relate=True)
                for u in group_user:
                    if u.get("username") not in all_group_user:
                        all_group_user.append(u.get("username"))
            user_list += all_group_user
            biz["user_list"] = list(set(user_list))

            for _, v in CMDB_BIZ_DEFAULT_ROLE.items():
                biz[v] = []

            for user in biz["user_list"]:
                for key, value in CMDB_BIZ_DEFAULT_ROLE.items():
                    if key in role_user_dict.keys() and user in role_user_dict[key]:
                        biz[value].append(user)

            # tag
            tree_q = session.query(BusinessTreeModel.tag, BusinessTreeModel.tree_id,
                                  BusinessTreeModel.business_list).filter(BusinessTreeModel.status == '0').all()
            tag_q = [tree for tree in tree_q if int(biz.get('business_id')) in tree[2]]

            # tag_q = session.query(BusinessTreeModel.tag, BusinessTreeModel.tree_id, BusinessTreeModel.business_list).filter(BusinessTreeModel.business_list.in_(biz.get('business_id'))).all()
            biz['tag'] = [t[0] for t in tag_q if t[0]]
            biz['tag_id'] = [t[1] for t in tag_q if t[1]]

        return biz_query


def get_biz_info(**params):
    value = params.get('searchValue') if "searchValue" in params else params.get('value')
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    params['page_size'] = 500

    if 'resource_group' in filter_map: filter_map.pop('resource_group')

    with DBContext('r') as session:
        if value:
            page = paginate(session.query(BusinessModel).filter(BusinessModel.life_cycle == '2').filter_by(**filter_map).filter(
                or_(BusinessModel.business_zh == value, BusinessModel.business_en.like(f'%{value}%'),
                    BusinessModel.resource_group.like(f'%{value}%'))), **params)
        else:
            page = paginate(session.query(BusinessModel).filter(BusinessModel.life_cycle == '2').filter_by(**filter_map), **params)

    page.items = get_biz_user(page.items)
    return page.total, page.items


class BusinessInfoHandler(BaseHandler):
    """业务列表详细信息，会拆分各类人员"""

    def get(self, *args, **kwargs):
        count, queryset = get_biz_info(**self.params)
        return self.write(dict(code=0, result=True, msg="获取成功", count=count, data=queryset))


def biz2tree(source, parent):
    tree = []
    for item in source:
        if item.get('parent') == parent:
            if item.get('tree_node'):
                item['children'] = biz2tree(source, item.get('tree_id'))
            tree.append(item)
    return tree


def get_biz_tree():
    """业务集 树形结构"""
    with DBContext('r') as session:
        query = session.query(BusinessTreeModel).filter(BusinessTreeModel.status != '10').all()
        data = [model_to_dict(q) for q in query]
        res = biz2tree(data, 0)
    return len(query), res


class BusinessTreeHandler(BaseHandler):
    """业务列表- 仅展示有权限"""

    def get(self, *args, **kwargs):
        user_name = self.request_username
        with DBContext('r') as session:
            query = session.query(BusinessModel).filter().all()
            biz_list = [int(q.business_id) for q in query if user_name in q.user_list]
            query = session.query(BusinessTreeModel).filter(BusinessTreeModel.status != '10').all()
            display_query = []
            for q in query:
                set_biz_list = [int(i) for i in q.business_list] if q.business_list else []
                if set(biz_list) & set(set_biz_list):
                    display_query.append(q)

            data = [model_to_dict(q) for q in display_query]
            for biz in data:
                if not biz.get('tree_node'):
                    map_biz_id = biz.get('business_list')[0] if len(biz.get('business_list')) == 1 else ''
                    if map_biz_id:
                        map_biz_query = session.query(BusinessModel).filter(BusinessModel.business_id == map_biz_id).first()
                        biz['map_business_id'] = map_biz_id
                        biz['map_business_en'] = map_biz_query.business_en
                        biz['map_business_zh'] = map_biz_query.business_zh

            res = biz2tree(data, 0)
            return self.write(dict(code=0, result=True, msg="获取成功", count=len(display_query), data=res))
        #
        # count, queryset = get_biz_tree()
        # return self.write(dict(code=0, result=True, msg="获取成功", count=count, data=queryset))


class BusinessTreeSubsHandler(BaseHandler):
    """业务列表-子树"""

    def get(self, *args, **kwargs):
        business_list = json.loads(self.params['business_list'])
        with DBContext('r') as session:
            query = session.query(BusinessModel).filter(BusinessModel.business_id.in_(business_list)).all()

            query = [model_to_dict(q) for q in query]
        return self.write(dict(code=0, result=True, msg="获取成功", count=len(query), data=query))


class BusinessTreeALLHandler(BaseHandler):
    """业务集-全部"""

    def get(self, *args, **kwargs):
        count, queryset = get_biz_tree()
        return self.write(dict(code=0, result=True, msg="获取成功", count=count, data=queryset))


biz_mg_urls = [
    (r"/auth/v1/base/biz/", BusinessHandler, {"handle_name": "业务列表-列表"}),
    (r"/auth/v1/biz_info/", BusinessInfoHandler, {"handle_name": "权限中心-业务列表详细信息"}),
    (r"/auth/biz/biz_tree/", BusinessTreeHandler, {"handle_name": "业务集-仅展示有权限"}),
    (r"/auth/biz/biz_tree/subs/", BusinessTreeSubsHandler, {"handle_name": "业务集-子列表"}),
    (r"/auth/biz/biz_tree/all/", BusinessTreeALLHandler, {"handle_name": "业务集-全部"}),
]
if __name__ == "__main__":
    pass
