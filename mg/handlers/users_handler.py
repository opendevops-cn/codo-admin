#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
author : shenshuo
date   : 2017年11月20日11:10:29
role   : 用户管理API

status = '0'    正常
status = '10'   逻辑删除
status = '20'   禁用
"""

import json
import shortuuid
import base64
from websdk2.jwt_token import gen_md5
from websdk2.tools import check_password
from websdk2.cache_context import cache_conn
from libs.base_handler import BaseHandler
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.model_utils import model_to_dict
from models.admin_model import Users, UserRoles
from models.admin_schemas import get_user_list_v2


class UserHandler(BaseHandler):

    def get(self, *args, **kwargs):
        limit = self.params.get('limit')
        if not limit: limit = 301
        if limit: limit = int(limit) if isinstance(limit, str) else limit

        redis_conn = cache_conn()
        if limit > 300:
            all_user_info_list = redis_conn.get('all_user_info_list')
            if all_user_info_list and len(all_user_info_list.decode()) > 200:
                queryset = json.loads(all_user_info_list.decode())
                return self.write(
                    dict(code=0, msg='获取成功，limit大于300不支持搜索', count=len(queryset), data=queryset))

        count, queryset = get_user_list_v2(**self.params)
        if limit > 300 and len(queryset) > 300: redis_conn.set('all_user_info_list', json.dumps(queryset), ex=180)

        self.write(dict(code=0, msg='获取用户成功', count=count, data=queryset))

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        username = data.get('username', None)
        nickname = data.get('nickname', None)
        password = data.get('password', None)
        department = data.get('department', None)
        tel = data.get('tel', None)
        have_token = data.get('have_token', 'no')
        no = data.get('no', None)
        email = data.get('email', None)
        status = data.get('status', '0')
        if not username or not nickname or not department or not tel or not email:
            return self.write(dict(code=-1, msg='重要参数不能为空'))

        with DBContext('r') as session:
            user_info1 = session.query(Users).filter(Users.username == username).first()
            user_info2 = session.query(Users).filter(Users.tel == tel).first()
            user_info3 = session.query(Users).filter(Users.email == email).first()
            user_info4 = session.query(Users).filter(Users.nickname == nickname).first()

        if user_info1:  return self.write(dict(code=-2, msg='用户名已注册'))

        if user_info2: return self.write(dict(code=-3, msg='手机号已注册'))

        if user_info3: return self.write(dict(code=-4, msg='邮箱已注册'))

        if user_info4: return self.write(dict(code=-4, msg='昵称已注册'))

        if not password:
            # password = '7d491c440ba46ca20fde0c5be1377aec'
            password = gen_md5(f"{username}@123")
        else:
            if not check_password(password):
                return self.write(dict(code=-5, msg='密码复杂度： 超过8位，英文加数字，大小写，没有特殊符号'))
            password = gen_md5(password)

        mfa = base64.b32encode(bytes(str(shortuuid.uuid() + shortuuid.uuid())[:-9], encoding="utf-8")).decode("utf-8")

        with DBContext('w', None, True) as session:
            user = Users(username=username, password=password, nickname=nickname, department=department, tel=tel,
                         have_token=have_token, email=email, google_key=mfa, superuser='10', status=status)
            session.add(user)
            # session.commit()
            # user_id = user.id
            # session.query(Users).filter(Users.id == user.id).update({"user_id": user_id})

        self.write(
            dict(code=0, msg=f'如果没填写密码 请让管理重置密码，密码信息会发送到注册的邮箱，默认密码为：{username}@123'))

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        user_id = data.get('user_id')
        id_list = data.get('id_list')
        if not user_id and not id_list:  return self.write(dict(code=-1, msg='不能为空'))

        with DBContext('w', None, True) as session:
            if user_id:
                user_info = session.query(Users.username).filter(Users.user_id == user_id).first()
                if user_info[0] == 'admin':  return self.write(dict(code=-2, msg='系统管理员用户无法删除'))

                session.query(Users).filter(Users.user_id == user_id).delete(synchronize_session=False)
                session.query(UserRoles).filter(UserRoles.user_id == user_id).delete(synchronize_session=False)
            elif id_list:
                for user_id in id_list:
                    user_info = session.query(Users.username).filter(Users.user_id == user_id).first()
                    if user_info[0] == 'admin':  return self.write(dict(code=-2, msg='系统管理员用户无法删除'))

                    session.query(Users).filter(Users.user_id == user_id).delete(synchronize_session=False)
                    session.query(UserRoles).filter(UserRoles.user_id == user_id).delete(synchronize_session=False)

        self.write(dict(code=0, msg='删除成功'))

    def put(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))

        if '_index' in data.keys(): data.pop('_index')
        if '_rowKey' in data.keys(): data.pop('_rowKey')
        if 'last_login' in data.keys(): data.pop('last_login')
        if 'username' in data.keys(): data.pop('username')
        user_id = data.pop('user_id')
        if not user_id and not isinstance(user_id, int):
            return self.write(dict(code=-1, msg="关键参数不能为空", result=False))

        with DBContext('w', None, True) as session:
            session.query(Users).filter(Users.user_id == user_id).update(data)

        return self.write(dict(code=0, msg="修改成功", result=True))

    def patch(self, *args, **kwargs):
        """禁用、启用"""
        data = json.loads(self.request.body.decode("utf-8"))
        user_id = str(data.get('user_id', None))
        msg = '用户不存在'

        if not user_id: return self.write(dict(code=-1, msg='不能为空'))

        with DBContext('r') as session:
            user_status = session.query(Users.status).filter(Users.user_id == user_id, Users.status != 10).first()

        if not user_status:  return self.write(dict(code=-2, msg=msg))

        if user_status[0] == '0':
            msg = '用户禁用成功'
            new_status = '20'

        elif user_status[0] == '20':
            msg = '用户启用成功'
            new_status = '0'
        else:
            new_status = '10'

        with DBContext('w', None, True) as db:
            db.query(Users).filter(Users.user_id == user_id, Users.status != '10').update({Users.status: new_status})

        return self.write(dict(code=0, msg=msg))


class UserTreeHandler(BaseHandler):
    def get(self, *args, **kwargs):
        user_list = []
        with DBContext('r') as session:
            user_info = session.query(Users).filter(Users.status == '0').all()

        for msg in user_info:
            data_dict = model_to_dict(msg)
            user_list.append(data_dict)

        _tree = [{"label": "all", "children": []}]
        if user_list:
            tmp_tree = {"department": {}, "nickname": {}}

            for t in user_list:
                department, nickname, user_id = t["department"], t['nickname'], t['user_id']

                # 因为是第一层所以没有parent
                tmp_tree["department"][department] = {"label": department, "parent": "all", "children": [],
                                                      "id": shortuuid.uuid()}

                tmp_tree["nickname"][department + "|" + nickname] = {
                    "label": nickname, "parent": department, "department": department, "id": nickname
                }

            for tmp_group in tmp_tree["nickname"].values():
                tmp_tree["department"][tmp_group["parent"]]["children"].append(tmp_group)

            for tmp_git in tmp_tree["department"].values():
                _tree[0]["children"].append(tmp_git)

            return self.write(dict(code=0, msg='获取用户Tree成功', data=_tree[0]["children"]))
        else:
            return self.write(dict(code=0, msg='获取用户Tree失败', data=_tree[0]["children"]))


# user_mg_urls = [
#     (r"/v3/accounts/user/", UserHandler, {"handle_name": "权限中心-用户管理"}),
#     (r"/v3/accounts/user/tree/", UserTreeHandler, {"handle_name": "权限中心-用户树"}),
# ]

if __name__ == "__main__":
    pass
