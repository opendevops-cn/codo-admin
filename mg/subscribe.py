#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2018/10/26
Desc    : 订阅redis的消息，写入数据库
"""
import json
import redis
from websdk.db_context import DBContext
from models.admin import OperationRecord


class RedisSubscriber:
    """
    Redis频道订阅类
    """

    def __init__(self, channel='gw', **settings):
        ### 订阅日志使用默认redis 如果有需求 请自行修改配置
        redis_info = settings.get('redises', None).get('default', None)
        if not settings.get('redises', None).get('default', None):
            exit('not redis')
        self.pool = redis.ConnectionPool(host=redis_info.get('host', '127.0.0.1'), port=redis_info.get('port', 6379),
                                         db=redis_info.get('db', 7), password=redis_info.get('password', None))
        self.conn = redis.StrictRedis(connection_pool=self.pool)
        self.channel = channel  # 定义频道名称
        self.__settings = settings

    def start_server(self):
        pub = self.conn.pubsub()
        pub.subscribe(self.channel)  # 同时订阅多个频道，要用psubscribe
        try:
            with DBContext('w', None, True, **self.__settings) as session:
                for item in pub.listen():
                    if item['type'] == 'message':
                        data = json.loads(item['data'].decode())
                        # print(data)
                        if data.get('data'):
                            body_data = str(data.get('data'))
                        else:
                            body_data = ''
                        if data.get('login_ip'):
                            login_ip = data.get('login_ip').split(',')[0]
                        else:
                            login_ip = ''
                        session.add(OperationRecord(username=data.get('username'), nickname=data.get('nickname'),
                                                    login_ip=login_ip, method=data.get('method'),
                                                    uri=data.get('uri'), data=body_data, ctime=data.get('time')))
                        session.commit()
                    if item['data'] == 'over':
                        break
            pub.unsubscribe('spub')

        except KeyboardInterrupt:
            pub.unsubscribe('spub')
