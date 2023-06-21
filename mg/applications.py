#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
Author : shenshuo
date   : 2017-10-11
role   : 管理端 Application
"""

from tornado.ioloop import PeriodicCallback
from concurrent.futures import ThreadPoolExecutor
from websdk2.application import Application as myApplication
from libs.sync_user_verift_v4 import async_api_permission_v4
from mg.handlers import urls


class Application(myApplication):
    def __init__(self, **settings):
        # 同步权限
        check_callback = PeriodicCallback(async_api_permission, 18000)  ### 2000  60000  48000
        check_callback_notice = PeriodicCallback(async_notice_info, 13000)  ### 2000  13000
        check_callback.start()
        check_callback_notice.start()
        ###
        check_callback_user = PeriodicCallback(async_user_center, 60000)  ### 3600000  一个小时
        check_callback_user.start()
        ###
        check_callback_v4 = PeriodicCallback(async_api_permission_v4, 6000)  ### 2000  60000  48000
        check_callback_v4.start()
        super(Application, self).__init__(urls, **settings)


def async_api_permission():
    # 启用线程去同步任务，防止阻塞
    from libs.sync_user_verify import MyVerify
    obj = MyVerify()
    executor = ThreadPoolExecutor(max_workers=3)
    executor.submit(obj.sync_diff_api_permission)
    executor.submit(obj.sync_all_api_permission)
    executor.submit(obj.token_block_list)


def async_notice_info():
    ### 启用线程去同步任务，防止阻塞
    from libs.sync_notice_user import NoticeUserInfo
    obj = NoticeUserInfo()
    executor = ThreadPoolExecutor(max_workers=2)
    executor.submit(obj.cache_user)
    executor.submit(obj.index)


def async_user_center():
    ### 启用线程去同步钉钉用户
    from libs.sync_user_verify import sync_user_from_ucenter
    executor = ThreadPoolExecutor(max_workers=1)
    executor.submit(sync_user_from_ucenter)


if __name__ == '__main__':
    pass
