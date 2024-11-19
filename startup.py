#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
author : shenshuo
date   : 2017年11月14日20:11:27
role   : 启动程序
"""

import fire
from tornado.options import define
from websdk2.program import MainProgram
from settings import settings as app_settings
from mg.applications import Application as MgApp
from mg.subscribe import RedisSubscriber as SubApp
from libs.registration import Registration

define("service", default='api', help="start service flag", type=str)


class MyProgram(MainProgram):
    def __init__(self, service='api', progressid=''):
        self.__app = None
        settings = app_settings
        if service in ['admin-mg-api', 'mg-api', 'mg', 'api', 'adminv4'] or not service:
            self.__app = MgApp(**settings)
        elif service in ['sub_log', 'gw_log', 'gw-log', 'admin-gw-log']:
            self.__app = SubApp(service=service, **settings)
        elif service == 'init':
            self.__app = Registration(**settings)
        super(MyProgram, self).__init__(progressid)
        self.__app.start_server()


if __name__ == '__main__':
    fire.Fire(MyProgram)

"""
python3 startup.py --service=mg --port=8010
python3 startup.py --service=init

docker build  --no-cache --build-arg SERVICE_NAME=mg  . -t codo-admin-image
"""
