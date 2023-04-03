#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2021/5/31 16:58 
Desc    : 单元测试
"""

from tornado.testing import AsyncTestCase, gen_test, AsyncHTTPTestCase
from startup import MgApp
from local_settings import settings_auth_key as auth_key
from websdk2.client import AcsClient
import json
import unittest
import requests

headers = {"Sdk-Method": "LrqV", "Cookie": f"auth_key={auth_key}"}
endpoint = 'http://127.0.0.1:8000'


class TestMGApp(AsyncHTTPTestCase):
    def get_app(self):
        return MgApp()

    # def test_storage_file_public(self):
    #     response = self.fetch('/v1/storage/file/public/', method="POST", body=json.dumps({}),
    #                           raise_error=False)
    #     res = json.loads(response.body)
    #     self.assertEqual(response.code, 200)
    #     self.assertEqual(-1, res.get('code'))


class TestStorageApp(unittest.TestCase):
    def test_storage_file_private(self):
        """测试OSS私有存储"""
        """使用tornado异步过于复杂 附上链接 https://github.com/tornadoweb/tornado/blob/master/demos/file_upload/file_uploader.py"""
        uri = "/v1/storage/file/private/?app_code=test"
        multiple_files = [
            ('field1', ('foo.png', open("/tmp/filePath1", 'rb'), 'image/png')),
            ('field2', ('bar.png', open('/tmp/filePath2', 'rb'), 'image/png'))
        ]
        response = requests.post(f"{endpoint}{uri}", headers=headers, files=multiple_files, timeout=10)
        result = response.json()
        self.assertEqual(response.status_code, 200, msg='状态非200')
        self.assertEqual(0, result.get('code'), msg=result.get('msg'))

    def test_storage_file_public(self):
        uri = "/v1/storage/file/public/"
        response = requests.post(f"{endpoint}{uri}", data=json.dumps({}))
        result = response.json()
        self.assertEqual(200, response.status_code)
        # self.assertEqual(0, result.get('code'), msg=result.get('msg'))

    def test_cdn_auth(self):
        uri = "/v1/cdn/auth/"
        response = requests.get(f"{endpoint}{uri}", headers=headers)
        result = response.json()
        # 断言
        self.assertEqual(200, response.status_code)
        self.assertEqual(0, result.get('code'))


# if __name__ == '__main__':
#     unittest.main()
