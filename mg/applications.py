#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
Author : shenshuo
date   : 2017-10-11
role   : 管理端 Application
"""

from websdk2.application import Application as myApplication
from mg.handlers.login_handler import login_urls
from mg.handlers.users_handler import user_mg_urls
from mg.handlers.roles_handler import roles_urls
from mg.handlers.functions_handler import functions_urls
from mg.handlers.menus_handler import menus_urls
from mg.handlers.components_handler import components_urls
from mg.handlers.apps_handler import apps_urls
from mg.handlers.business_handler import biz_mg_urls
from mg.handlers.token_handler import token_urls
from mg.handlers.app_mg_handler import app_mg_urls
from mg.handlers.configs_handler import app_settings_urls
from mg.handlers.notifications_handler import notifications_urls
from mg.handlers.custom_notice_handler import custom_notice_urls
from mg.handlers.storage_handler import storage_urls
from mg.handlers.favorites_handler import favorites_urls
###
from tornado.ioloop import PeriodicCallback
from concurrent.futures import ThreadPoolExecutor


class Application(myApplication):
    def __init__(self, **settings):
        urls = []
        urls.extend(user_mg_urls)
        urls.extend(login_urls)
        urls.extend(roles_urls)
        urls.extend(functions_urls)
        urls.extend(components_urls)
        urls.extend(menus_urls)
        urls.extend(apps_urls)
        urls.extend(biz_mg_urls)
        urls.extend(token_urls)
        urls.extend(app_mg_urls)
        urls.extend(app_settings_urls)
        urls.extend(notifications_urls)
        urls.extend(custom_notice_urls)
        urls.extend(storage_urls)
        urls.extend(favorites_urls)
        ###
        ### 同步权限
        check_callback = PeriodicCallback(async_api_permission, 18000)  ### 2000  60000  48000
        check_callback_notice = PeriodicCallback(async_notice_info, 13000)  ### 2000  13000
        check_callback.start()
        check_callback_notice.start()
        ###
        check_callback_dduser = PeriodicCallback(async_user_center, 60000)  ### 3600000  一个小时
        check_callback_dduser.start()
        super(Application, self).__init__(urls, **settings)



def async_api_permission():
    ### 启用线程去同步任务，防止阻塞
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
