#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
Author : shenshuo
date   : 2017-10-11
role   : 管理端 Application
"""

from websdk2.application import Application as myApplication
from authority.handlers import urls

###
from tornado.ioloop import PeriodicCallback
from concurrent.futures import ThreadPoolExecutor


class Application(myApplication):
    def __init__(self, **settings):
        ###同步订阅
        # subs_callback = PeriodicCallback(async_subscribe, 1800000)  # 30min
        # subs_callback.start()

        ### 同步权限至etcd
        check_callback = PeriodicCallback(async_api_permission, 1800000)  # 30min
        # check_callback_notice = PeriodicCallback(async_notice_info, 13000)  ### 2000  13000

        check_callback.start()
        # check_callback_notice.start()

        ### 同步用户和组织架构
        # check_callback_user = PeriodicCallback(async_user_dep, 86400000)  # 一天一次
        # check_callback_user.start()
        super(Application, self).__init__(urls, **settings)


# def async_subscribe():
#     from libs.sync_resource import sync_subscribe
#     executor = ThreadPoolExecutor(max_workers=1)
#     executor.submit(sync_subscribe)
#
#
# def async_biz_info():
#     from libs.sync_user_verify import biz_sync
#     executor = ThreadPoolExecutor(max_workers=1)
#     executor.submit(biz_sync)


def async_api_permission():
    ### 启用线程去同步任务，防止阻塞
    from libs.sync_user_verify import MyVerify
    obj = MyVerify()
    executor = ThreadPoolExecutor(max_workers=4)
    executor.submit(obj.sync_diff_api_permission)
    # executor.submit(obj.sync_all_api_permission)
    executor.submit(obj.token_block_list)
    # executor.submit(obj.sync_business_user)


def async_notice_info():
    ### 启用线程去同步任务，防止阻塞
    from libs.sync_notice_user import NoticeUserInfo
    obj = NoticeUserInfo()
    executor = ThreadPoolExecutor(max_workers=2)
    executor.submit(obj.cache_user)
    executor.submit(obj.index)


# def async_user_dep():
#     ### 启用线程去同步用户和组织架构
#     from libs.sync_user_verify import sync_dd_user, sync_groups_department
#     executor = ThreadPoolExecutor(max_workers=2)
#     executor.submit(sync_dd_user)
#     executor.submit(sync_groups_department)


if __name__ == '__main__':
    pass
