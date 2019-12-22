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
from websdk.jwt_token import gen_md5
from websdk.tools import check_password
from libs.base_handler import BaseHandler
from websdk.db_context import DBContext
from models.admin import Users, UserRoles,model_to_dict
from websdk.consts import const
from websdk.cache_context import cache_conn


class UserHandler(BaseHandler):
    def get(self, *args, **kwargs):
        key = self.get_argument('key', default=None, strip=True)
        value = self.get_argument('value', default=None, strip=True)
        page_size = self.get_argument('page', default=1, strip=True)
        limit = self.get_argument('limit', default=30, strip=True)
        limit_start = (int(page_size) - 1) * int(limit)
        user_list = []
        with DBContext('r') as session:
            if key and value:
                count = session.query(Users).filter(Users.status != '10').filter_by(**{key: value}).count()
                user_info = session.query(Users).filter(Users.status != '10').filter_by(**{key: value}).order_by(
                    Users.user_id).offset(limit_start).limit(int(limit))
            else:
                count = session.query(Users).filter(Users.status != '10').count()
                user_info = session.query(Users).filter(Users.status != '10').order_by(Users.user_id).offset(
                    limit_start).limit(int(limit))

            all_user = session.query(Users).filter(Users.status != '10').all()
            if int(limit) > 200:
                user_info = all_user

        for msg in user_info:
            data_dict = model_to_dict(msg)
            data_dict.pop('password')
            data_dict.pop('google_key')
            data_dict['last_login'] = str(data_dict['last_login'])
            data_dict['ctime'] = str(data_dict['ctime'])
            user_list.append(data_dict)

        redis_conn = cache_conn()
        redis_conn.delete(const.USERS_INFO) ### 清空集合数据
        with redis_conn.pipeline(transaction=False) as p:
            for msg in all_user:
                data_dict = model_to_dict(msg)
                data_dict.pop('password')
                data_dict.pop('google_key')
                data_dict['last_login'] = str(data_dict['last_login'])
                data_dict['ctime'] = str(data_dict['ctime'])
                nickname_key = bytes(data_dict['nickname'] + '__contact', encoding='utf-8')
                p.hmset(nickname_key, {"tel": data_dict["tel"], "email": data_dict["email"]})
                p.sadd(const.USERS_INFO, json.dumps(data_dict))
            p.execute()
        self.write(dict(code=0, msg='获取用户成功', count=count, data=user_list))

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        username = data.get('username', None)
        nickname = data.get('nickname', None)
        password = data.get('password', None)
        department = data.get('department', None)
        tel = data.get('tel', None)
        wechat = data.get('wechat', None)
        no = data.get('no', None)
        email = data.get('email', None)
        user_state = data.get('user_state', '20')
        if not username or not nickname or not department or not tel or not wechat or not no or not email:
            return self.write(dict(code=-1, msg='参数不能为空'))

        with DBContext('r') as session:
            user_info1 = session.query(Users).filter(Users.username == username).first()
            user_info2 = session.query(Users).filter(Users.tel == tel).first()
            user_info3 = session.query(Users).filter(Users.email == email).first()
            user_info4 = session.query(Users).filter(Users.nickname == nickname).first()
        if user_info1:
            return self.write(dict(code=-2, msg='用户名已注册'))

        if user_info2:
            return self.write(dict(code=-3, msg='手机号已注册'))

        if user_info3:
            return self.write(dict(code=-4, msg='邮箱已注册'))

        if user_info4:
            return self.write(dict(code=-4, msg='昵称已注册'))

        if not password:
            password = '7d491c440ba46ca20fde0c5be1377aec'
        else:
            if not check_password(password):
                return self.write(dict(code=-5, msg='你这密码复杂度是逗我玩吗？密码复杂度： 超过8位，英文加数字，大小写，没有特殊符号'))
            password = gen_md5(password)

        mfa = base64.b32encode(bytes(str(shortuuid.uuid() + shortuuid.uuid())[:-9], encoding="utf-8")).decode("utf-8")

        with DBContext('w', None, True) as session:
            session.add(Users(username=username, password=password, nickname=nickname, department=department, tel=tel,
                              wechat=wechat, no=no, email=email, google_key=mfa, superuser='10', status=user_state))

        self.write(dict(code=0, msg='如果没填写密码 则新用户密码为：shenshuo'))

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        user_id = data.get('user_id', None)
        if not user_id:
            return self.write(dict(code=-1, msg='不能为空'))

        with DBContext('w', None, True) as session:
            user_info = session.query(Users.username).filter(Users.user_id == user_id).first()
            if user_info[0] == 'admin':
                return self.write(dict(code=-2, msg='系统管理员用户无法删除'))

            session.query(Users).filter(Users.user_id == user_id).delete(synchronize_session=False)
            session.query(UserRoles).filter(UserRoles.user_id == user_id).delete(synchronize_session=False)

        self.write(dict(code=0, msg='删除成功'))

    def put(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        key = data.get('key', None)
        value = data.get('value', None)
        user_id = data.get('user_id', None)

        if not key or not value or not user_id:
            return self.write(dict(code=-1, msg='不能为空'))

        try:
            with DBContext('w', None, True) as session:
                session.query(Users).filter(Users.user_id == user_id).update({key: value})
        except Exception as e:
            return self.write(dict(code=-2, msg='修改失败，请检查数据是否合法或者重复'))

        self.write(dict(code=0, msg='编辑成功'))

    def patch(self, *args, **kwargs):
        """禁用、启用"""
        data = json.loads(self.request.body.decode("utf-8"))
        user_id = str(data.get('user_id', None))
        msg = '用户不存在'

        if not user_id:
            return self.write(dict(code=-1, msg='不能为空'))

        with DBContext('r') as session:
            user_status = session.query(Users.status).filter(Users.user_id == user_id, Users.status != 10).first()
        if not user_status:
            return self.write(dict(code=-2, msg=msg))

        if user_status[0] == '0':
            msg = '用户禁用成功'
            new_status = '20'

        elif user_status[0] == '20':
            msg = '用户启用成功'
            new_status = '0'
        else:
            new_status = '10'

        with DBContext('w', None, True) as session:
            session.query(Users).filter(Users.user_id == user_id, Users.status != '10').update(
                {Users.status: new_status})

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


user_mg_urls = [
    (r"/v2/accounts/user/", UserHandler),
    (r"/v2/accounts/user/tree/", UserTreeHandler),
]

if __name__ == "__main__":
    pass
