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
# from libs.feature_application import Application as myApplication
from libs.sync_user_verift_v4 import async_api_permission_v4, async_user_center
from mg.handlers import urls


class Application(myApplication, ABC):
    def __init__(self, **settings):
        # 同步用户
        check_callback_user = PeriodicCallback(async_user_center, 3600000)  # 3600000  一个小时
        check_callback_user.start()

        # 同步权限
        check_callback_v4 = PeriodicCallback(async_api_permission_v4, 300000)  # 300000 五分钟
        check_callback_v4.start()
        super(Application, self).__init__(urls, **settings)


if __name__ == '__main__':
    pass
