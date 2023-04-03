# #!/usr/bin/env python
# # -*- coding: utf-8 -*-
# """
# Version : 0.0.1
# Contact : 191715030@qq.com
# Author  : shenshuo
# Date    : 2021/1/5 17:15
# Desc    : 解释一下吧
# """
#
# import requests
# import json
#
#
# class TestApi:
#     def __init__(self):
#         self.auth_key = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9."
#         self.test_api = "http://10.10.6.154:8888/api/mg/v3/notifications/template/"  # API
#         self.test_api = "https://dmz-tianmen.diezhi.net/api/mg/v3/notifications/template/"  # API
#
#     def run(self, method="post", **body) -> bool:
#
#         headers = {"Sdk-Method": "zQtY4sw7sqYspVLrqV", "Cookie": f"auth_key={self.auth_key}"}
#         try:
#             # method
#             response = requests.request(method, self.test_api, data=json.dumps(body), headers=headers, timeout=10)
#             status_code = response.status_code
#             print(status_code)
#             if status_code == 401:
#                 print('没登陆')
#                 return False
#             if status_code == 403:
#                 print('没权限')
#                 return False
#
#             res = json.loads(response.text)
#             print(res)
#             if res['code'] == 0:
#                 print(res['msg'])
#                 return True
#             else:
#                 print('请求出错')
#                 return False
#
#         except Exception as e:
#             print('[Error:] 通知接口连接失败，错误信息：{}'.format(e))
#             return False
#
#
# obj = TestApi()
# ### 阿里云短信
# body = {
#     "id": 1,
#     "msg": {"msg": "这个即将发布的新版本，创始人xx称它为红树林。而在此之前，每当面临重大升级"}
# }
# # obj.run(**body)
# ### 阿里云电话
# body = {
#     "id": 2,
#     "msg": {"msg": "这个即将发布的新版本，创始人xx称它为红树林。而在此之前，每当面临重大升级"}
# }
# # obj.run(**body)
# notice_conf = json.dumps({"secret": "SEC133d45bacf468eedca6326e696b9ab2325ecb456292d3d7b04f80ba18ffbf28e",
#                           "webhook": "https://oapi.dingtalk.com/robot/send?access_token=9edc1903fb16c17417fefb6fc70b5ac6cb6ccb035585c2de0257b38e7cc3294c"})
# ### 钉钉
#
# body = {
#     "notice_conf": notice_conf,
#     "name": 'default',
#     "msg": {"msg": "这个即将发布的新版本，创始人xx称它为红树林。而在此之前，每当面临重大升级"}
# }
#
# ### 带着通知人参数
# send_addr = {"tel": ["15618718060", "18017313756", "15618718888", "15340265295"],
#              "email": ["shenshuo@papegames.net", "lujian@papegames.net", "191715030@qq.com",
#                        "zhanghuihui@papegames.net"],
#              "dd_id": ["15688638390555576", "16056688742201265", "15753397533701553"]}
# body = {
#     "send_addr": send_addr,
#     "notice_conf": notice_conf,
#     "name": 'default',
#     "msg": {"msg": "这个即将发布的新版本，创始人xx称它为红树林。而在此之前，每当面临重大升级"}
# }
# # obj.run(**body)
# body = {
#     "agent_id": 276892406,
#     "status_value": "已同意",
#     "status_bg": "0xFF78C06E",
#     "task_id": 374918481997
# }
# # obj.run("put", **body)
# # obj.run("get", **body)
# # #!/usr/bin/env python
# # # -*- coding: utf-8 -*-
#
# import fire
# import json
#
# env_list = ["test", "pre", "prod", "sgp"]
#
# def get_env_and_app_name(VERSION):
#     NS = 'platform-a'
#     # VERSION = "prod.pjob-f.20210331_01"
#     if VERSION.split('.')[0] not in env_list:
#         data_dict = json.dumps({"ENV": "NO"})
#     else:
#         ENV, APP_NAME, ns_tag = VERSION.split('.')[0], VERSION.split('.')[1], VERSION.split('.')[-1]
#         if len(ns_tag) == 1: NS = f'platform-{ns_tag}'
#         data_dict = json.dumps({"ENV": ENV, "APP_NAME": APP_NAME, "NS": NS})
#     print(f"###SOF###{data_dict}###EOF###")
#
#
# if __name__ == "__main__":
#     fire.Fire(get_env_and_app_name)
# import time
# import requests
# import json
# import base64
# from settings import settings_auth_key as auth_key
#
# endpoint = "http://10.10.6.154:8888"
#
# headers = {"Sdk-Method": "zQtY4sw7sqYspVLrqV", "Cookie": f"auth_key={auth_key}"}
#
# token_url = endpoint + "/api/mg/v3/accounts/token/"
# response = requests.get(url=token_url,headers=headers)
# print(response.status_code)
# print(response.text)
#
#
# for i in range(2000):
#     response = requests.get(url=token_url, headers=headers)
#     if response.status_code != 200: print(response.text)
# print('end')

from functools import lru_cache


@lru_cache(50)
def add(x, y):
    print(f'-------{x} + {y}')
    return x + y


print(add(1, 2))
print(add(1, 2))
print(add(2, 3))
print(add(1, 2))


