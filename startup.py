#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
author : shenshuo
date   : 2017年11月14日20:11:27
role   : 启动程序
"""

import fire
from tornado.options import define
from websdk.program import MainProgram
from settings import settings as app_settings
from mg.applications import Application as MgApp
from mg.subscribe import RedisSubscriber as SubApp

define("service", default='api', help="start service flag", type=str)


class MyProgram(MainProgram):
    def __init__(self, service='mg_api', progressid=''):
        self.__app = None
        settings = app_settings
        if service == 'mg':
            self.__app = MgApp(**settings)
        elif service == 'sub_log':
            self.__app = SubApp(**settings)
        super(MyProgram, self).__init__(progressid)
        self.__app.start_server()


if __name__ == '__main__':
    fire.Fire(MyProgram)
