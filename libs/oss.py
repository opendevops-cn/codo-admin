#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2021/4/28 16:27 
Desc    : 解释一下吧
"""
import oss2
import datetime


class OSSApi:
    def __init__(self, **kwargs):
        self.key = kwargs.get('STORAGE_KEY_ID')
        __secret = kwargs.get('STORAGE_KEY_SECRET')
        region = kwargs.get('STORAGE_REGION')
        self.endpoint = f"http://oss-{region}.aliyuncs.com"
        self.bucket_name = kwargs.get('STORAGE_NAME')
        self.base_dir = kwargs.get('STORAGE_PATH')
        self.date = datetime.datetime.now().strftime('%Y%m%d')
        self.__auth = oss2.Auth(self.key, __secret)

    def setObj(self, filename, data):
        """存储str对象"""
        bucket = oss2.Bucket(self.__auth, self.endpoint, self.bucket_name)
        result = bucket.put_object('%s/%s' % (self.base_dir, filename), data)
        return filename if result.status == 200 else print('[Faild] Put obj Faild!')


if __name__ == '__main__':
    pass
