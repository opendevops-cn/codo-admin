#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2021/4/28 16:27 
Desc    : 操作对象存储
"""
import oss2
import logging
import datetime
import sys
import os

from qcloud_cos import CosS3Client, CosConfig
from qcloud_cos.cos_exception import CosClientError, CosServiceError


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


class COSApi:
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    def __init__(self, **kwargs):
        secret_id = kwargs.get('COS_SECRET_ID')
        secret_key = kwargs.get('COS_SECRET_KEY')
        region = 'ap-beijing'  # 替换为用户的 region，已创建桶归属的 region 可以在控制台查看，https://console.cloud.tencent.com/cos5/bucket
        # COS 支持的所有 region 列表参见 https://cloud.tencent.com/document/product/436/6224
        token = None  # 如果使用永久密钥不需要填入 token，如果使用临时密钥需要填入，临时密钥生成和使用指引参见 https://cloud.tencent.com/document/product/436/14048
        scheme = 'https'  # 指定使用 http/https 协议来访问 COS，默认为 https，可不填

        config = CosConfig(Region=region, SecretId=secret_id, SecretKey=secret_key, Token=token, Scheme=scheme)
        self.bucket = kwargs.get('bucket')
        self.client = CosS3Client(config)

    def put_obj(self, filename, data):
        """
        # Bucket 存储桶名称，由 BucketName-APPID 构成
        # 对象键（Key）是对象在存储桶中的唯一标识。例如，在对象的访问域名 examplebucket-1250000000.cos.ap-guangzhou.myqcloud.com/doc/pic.jpg 中，对象键为 doc/pic.jpg
        # LocalFilePath 本地文件的路径名
        """
        response = None
        for i in range(0, 10):
            try:
                response = self.client.upload_file(
                    Bucket=self.bucket,
                    Key=filename,
                    LocalFilePath=data)
                break
            except CosClientError or CosServiceError as e:
                logging.error(e)
        return response


if __name__ == '__main__':
    pass
