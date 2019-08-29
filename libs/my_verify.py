#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
author : shenshuo
date   : 2017年11月15日
role   : 权限鉴定类
"""

from websdk.cache_context import cache_conn
from models.admin import Users, UserRoles, RoleFunctions, Functions
from websdk.db_context import DBContext


class MyVerify:
    def __init__(self, user_id, is_superuser=False):
        self.redis_conn = cache_conn()
        self.user_id = user_id
        self.is_superuser = is_superuser
        self.method_list = ["GET", "POST", "PATCH", "DELETE", "PUT", "ALL"]

    def write_verify(self):
        ### 再确认一次是否是超级用户
        if self.is_superuser:
            with DBContext('r') as session:
                is_super = session.query(Users.superuser).filter(Users.user_id == self.user_id).first()
            if is_super:
                if is_super[0] == '0':
                    user_method = self.user_id + 'ALL'
                    self.redis_conn.sadd(user_method, '/')
                    self.redis_conn.expire(user_method, time=3 * 86400)
                    return '权限已经写入缓存'
                else:
                    self.is_superuser = False

        for method in self.method_list:
            user_method = self.user_id + method
            self.redis_conn.delete(user_method)
        with DBContext('r') as session:
            func_list = session.query(Functions.method_type, Functions.uri
                                      ).outerjoin(RoleFunctions, Functions.func_id == RoleFunctions.func_id).outerjoin(
                UserRoles, RoleFunctions.role_id == UserRoles.role_id).filter(UserRoles.user_id == self.user_id,
                                                                              Functions.status == '0',
                                                                              RoleFunctions.status == '0',
                                                                              UserRoles.status == '0').all()

        for func in func_list:
            ### 把权限写入redis
            self.redis_conn.sadd(self.user_id + func[0], func[1])
            self.redis_conn.expire(self.user_id + func[0], time=3 * 86400)
        return '权限已经写入缓存'

    def get_verify(self, my_method, my_uri):
        my_verify = self.redis_conn.smembers(self.user_id + my_method)
        all_verify = self.redis_conn.smembers(self.user_id + 'ALL')
        ### 把uri 转化为bytes
        my_uri = bytes(my_uri, encoding="utf8")
        for i in my_verify:
            is_exist = my_uri.startswith(i)
            if is_exist:
                return True

        for i in all_verify:
            is_exist = my_uri.startswith(i)
            if is_exist:
                return True

        if my_uri in my_verify:
            return True

        elif my_uri in all_verify:
            return True
        else:
            return False
