#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
Author : shenshuo
date   : 2017-10-11
role   : 管理端 Application
"""

from abc import ABC
from tornado.ioloop import PeriodicCallback
from websdk2.application import Application as myApplication

from libs.sync_user_verift_v4 import async_archive_old_logs, async_user_center, async_api_permission_v4
from mg.handlers import urls
from mg.subscribe import RedisSubscriber as SubApp


class Application(myApplication, ABC):
    def __init__(self, **settings):
        # 归档日志
        check_callback_archive = PeriodicCallback(async_archive_old_logs, 36000000)  # 36000000 10小时
        # check_callback_archive.start()

        # 同步用户
        check_callback_user = PeriodicCallback(async_user_center, 3600000)  # 3600000  一个小时
        check_callback_user.start()

        # 同步权限
        check_callback_permission = PeriodicCallback(async_api_permission_v4, 300000)  # 300000 五分钟
        check_callback_permission.start()
        super(Application, self).__init__(urls, **settings)
        self.sub_app = SubApp(**settings)
        self.sub_app.start_server()


if __name__ == '__main__':
    pass
