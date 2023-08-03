#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023/4/28 16:26
Desc    : 管理对象存储
"""

from libs.base_handler import BaseHandler
from libs.oss import OSSApi
from websdk2.db_context import DBContextV2 as DBContext
from models.paas_model import StorageMG


class StoragePrivate(BaseHandler):

    def prepare(self):
        self.codo_login()

    def post(self):
        file_dir = self.request.headers.get('file-dir')
        app_code = self.get_argument('app_code', default=None, strip=True)
        file_path = self.get_argument('file_path', default=None, strip=True)
        file_dir = app_code if app_code else file_dir
        if '/' in app_code: return self.write(dict(code=-1, msg='应用编码不应包含 /'))
        if '/' not in file_path:  return self.write(dict(code=-1, msg='文件路径应当包含 /'))
        if not file_dir:  return self.write(dict(code=-1, msg='必须有携带应用编码，方便目录归类'))

        upload_data = self.request.files.values()
        if not upload_data:  return self.write(dict(code=-2, msg='没有上传数据'))
        oss_data = self.settings.get('oss_data_private')

        ###
        if file_path: file_dir = f"{app_code}{file_path}"
        if file_dir: oss_data['STORAGE_PATH'] = file_dir
        real_file_dir = oss_data['STORAGE_PATH']
        storage_key = oss_data.get('STORAGE_KEY_ID')
        for meta in upload_data:
            meta = meta[0]
            filename = meta['filename']
            file_data = meta['body']

            try:
                obj = OSSApi(**oss_data)
                obj.setObj(filename, file_data)
                with DBContext('w', None, True) as session:
                    session.add(StorageMG(nickname=self.nickname, action='上传', storage_type='OSS',
                                          storage_key=storage_key, file_dir=real_file_dir, filename=filename))
            except Exception as e:
                return self.write(dict(code=-1, msg='上传失败，请检查OSS配置'))

        return self.write(dict(code=0, result=True, msg="上传成功"))


class StoragePublic(BaseHandler):
    def prepare(self):
        pass

    def post(self):
        app_code = self.get_argument('app_code', default='', strip=True)
        file_path = self.get_argument('file_path', default=None, strip=True)
        file_dir = app_code if app_code else ''

        if '/' in app_code: return self.write(dict(code=-1, msg='应用编码不应包含 /'))

        upload_data = self.request.files.values()
        if not upload_data:  return self.write(dict(code=-2, msg='没有上传数据'))

        oss_data = self.settings.get('oss_data')
        if not oss_data:  return self.write(dict(code=-2, msg='没有对象存储配置'))

        if file_path: file_dir = f"{app_code}{file_path}"
        if file_dir: oss_data['STORAGE_PATH'] = file_dir

        for meta in upload_data:
            meta = meta[0]
            filename = meta['filename']
            file_data = meta['body']

            try:
                obj = OSSApi(**oss_data)
                obj.setObj(filename, file_data)
            except Exception as e:
                return self.write(dict(code=-1, msg='上传失败，请检查OSS配置'))

        return self.write(dict(code=0, result=True, msg="上传成功"))


class CDNAuth(BaseHandler):

    def get(self):
        # 记录CDN鉴权日志，暂不需要
        return self.write(dict(code=0, msg="鉴权成功"))


storage_urls = [
    (r"/v1/storage/file/private/", StoragePrivate, {"handle_name": "存储管理-私有"}),
    (r"/v1/storage/file/public/", StoragePublic, {"handle_name": "存储管理-公共读"}),
    (r"/v1/cdn/auth/", CDNAuth, {"handle_name": "CDN鉴权"})
]
if __name__ == "__main__":
    pass
