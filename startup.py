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
from authority.applications import Application as AuthApp
from mg.subscribe import RedisSubscriber as SubApp
from libs.registration import Registration

define("service", default='api', help="start service flag", type=str)


class MyProgram(MainProgram):
    def __init__(self, service='api', progressid=''):
        self.__app = None
        settings = app_settings
        if service in ['admin-mg-api', 'mg-api', 'mg']:
            self.__app = MgApp(**settings)
        elif service in ['auth-api','auth']:
            self.__app = AuthApp(**settings)
        elif service in ['sub_log', 'gw_log', 'gw-log', 'admin-gw-log']:
            self.__app = SubApp(service=service, **settings)
        elif service in ['init']:
            self.__app = Registration(**settings)
        super(MyProgram, self).__init__(progressid)
        self.__app.start_server()


if __name__ == '__main__':
    fire.Fire(MyProgram)

### python3 startup.py --service=admin-mg-api --port=8010
### python3 startup.py --service=auth-api --port=8020
### python3 startup.py --service=sub_log
### python3 startup.py --service=gw_log
### python3 startup.py --service=init

### docker build  --no-cache --build-arg SERVICE_NAME=admin-mg-api  . -t ops_mg_image
### docker build --build-arg SERVICE_NAME=gw_log  . -t ops_mg_log_image
###
