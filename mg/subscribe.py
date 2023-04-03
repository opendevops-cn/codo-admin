#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2018/10/26
Desc    : 订阅redis的消息，写入数据库
"""

import json
import time
import datetime
import redis
from shortuuid import uuid
from websdk2.db_context import DBContext
from models.admin_model import OperationRecord
from concurrent.futures import ThreadPoolExecutor
from websdk2.consts import const
from websdk2.web_logs import ins_log


class RedisSubscriber:

    def __init__(self, service='gw1', channel='gw', **settings):
        ### 订阅日志使用默认redis 如果有需求 请自行修改配置
        self.consumer_name = f"{service}-{uuid()[0:8]}"
        self.group_name = "gw-consumer-group"
        self.stream_name = channel
        redis_info = settings.get(const.REDIS_CONFIG_ITEM, None).get(const.DEFAULT_RD_KEY, None)
        if not redis_info:  exit('not redis')
        self.pool = redis.ConnectionPool(host=redis_info.get(const.RD_HOST_KEY),
                                         port=redis_info.get(const.RD_PORT_KEY, 6379),
                                         db=redis_info.get(const.RD_DB_KEY, 0),
                                         password=redis_info.get(const.RD_PASSWORD_KEY, None), decode_responses=True)
        self.redis_conn = redis.StrictRedis(connection_pool=self.pool)
        # self.channel = channel  # 定义频道名称
        self.__settings = settings
        ### 创建消费者组
        self.create_consumer_group(self.stream_name, self.group_name)

    @staticmethod
    def process_message(msg_id, fields):
        if 'test' in fields: return {}
        ins_log.read_log('info', msg_id)

        log_data = list(fields.values())[0]
        log_data_dict = json.loads(log_data)

        response_data = log_data_dict.pop('response')
        request_data = log_data_dict.pop('request')
        user_info = dict()
        if "user_info" in log_data_dict: user_info = log_data_dict.pop('user_info')
        ###
        log_data_dict['user_id'] = user_info.get('user_id', '-1')
        log_data_dict['username'] = user_info.get('username', 'nimingyonghu')
        log_data_dict['nickname'] = user_info.get('nickname', '匿名用户')

        log_data_dict['scheme'] = request_data.get('scheme')
        log_data_dict['uri'] = request_data.get('uri')[0:255]
        log_data_dict['method'] = request_data.get('method')

        request_data_data = request_data.get('data')
        try:
            if request_data_data:
                request_data_data = json.loads(request_data_data)
                if "password" in request_data_data: request_data_data['password'] = "*********************"
                request_data_data = json.dumps(request_data_data)[0:60000]
        except:
            pass

        log_data_dict['data'] = request_data_data
        try:
            log_data_dict['trace_id'] = request_data.get('headers').get('x-trace-id')[0:80]
        except:
            pass

        log_data_dict['response_status'] = response_data.get('status')

        start_time = log_data_dict.get('start_time')
        start_time = int(start_time) / 1000
        times = datetime.datetime.fromtimestamp(start_time)
        log_data_dict['start_time'] = times
        ins_log.read_log('info', log_data_dict)
        return log_data_dict

    def create_consumer_group(self, stream_name, group_name):
        try:
            if not self.redis_conn.exists(stream_name):
                self.redis_conn.xadd(stream_name, {'test': 'true'})
            ret = self.redis_conn.xgroup_create(stream_name, group_name, id=0)
            print(ret)
        except Exception as err:
            print('create_consumer_group', err)

    def stream_message(self, stream_name):
        """stream and groups info"""
        ins_log.read_log('info', f'stream info: {self.redis_conn.xinfo_stream(stream_name)}')
        ins_log.read_log('info', f'groups info: {self.redis_conn.xinfo_groups(stream_name)}')

    def subscribe_msgs(self, consumer_name):
        ins_log.read_log('info', f"Consumer {consumer_name} starting...")
        lastid = '0-0'
        check_backlog = True
        while True:
            consumer_id = lastid if check_backlog else '>'

            # block 0 时阻塞等待, 其他数值表示读取超时时间
            try:
                print(self.group_name, consumer_name, {self.stream_name: consumer_id})
                items = self.redis_conn.xreadgroup(self.group_name, consumer_name, {self.stream_name: consumer_id},
                                                   block=0, count=1)
            except Exception as err:
                print(err)
                items = []

            if not items:  # 如果 block 不是 0或者为空, 会需要这段
                print("Timeout!")
                self.stream_message(self.stream_name)
                time.sleep(3)  # 空值等待 3s
                self.redis_conn.xack(self.stream_name, self.group_name, lastid)  ### 删除错误信息
                continue
            elif not items[0][1]:
                check_backlog = False

            for id, fields in items[0][1]:
                try:
                    log_data = self.process_message(id, fields)
                    if log_data:
                        with DBContext('w', None, True, **self.__settings) as session:
                            session.add(OperationRecord(**log_data))
                    # 0 / 0  # 这个模拟处理崩溃
                    # 这里是你要做的事情，封一个函数这里调用即可
                    # pass
                except Exception as e:
                    print('subscribe_msgs', e)
                    continue
                finally:
                    lastid = id  # 无论是出错还是正常执行完毕,都要去读取下一个,否则可能会无限循环读取处理报错的数据
                self.redis_conn.xack(self.stream_name, self.group_name, id)
            time.sleep(2)  # 间隔时长，自取

    def start_server(self):
        print('start', datetime.datetime.now())
        # print(self.consumer_name)
        # consumer_name_list = [f'{self.consumer_name}1', f'{self.consumer_name}2', f'{self.consumer_name}3']
        self.subscribe_msgs(self.consumer_name)

        # with ThreadPoolExecutor() as executor:
        #     executor.map(self.subscribe_msgs, consumer_name_list)
