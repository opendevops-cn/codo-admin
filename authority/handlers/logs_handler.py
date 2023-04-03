#!/usr/bin/env python
# -*- coding: utf-8 -*-

from libs.base_handler import BaseHandler
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.sqlalchemy_pagination import paginate
from models.authority_model import OperationLogs, SyncLogs


class OperationLogsHandler(BaseHandler):

    def get(self, *args, **kwargs):
        value = self.params.get('searchValue') if "searchValue" in self.params else self.params.get('value')
        self.params['page_size'] = 300
        filter_map = self.params.pop('filter_map') if "filter_map" in self.params else {}
        if 'resource_group' in filter_map: filter_map.pop('resource_group')

        with DBContext('r') as session:
            if value:
                page = paginate(session.query(OperationLogs).filter_by(**filter_map).filter(
                    OperationLogs.operation.like(f'%{value}%')).order_by(OperationLogs.create_time.desc()), **self.params)
            else:
                page = paginate(session.query(OperationLogs).filter_by(**filter_map).order_by(OperationLogs.create_time.desc()), **self.params)

        count, queryset = page.total, page.items
        return self.write(dict(code=0, result=True, msg="获取操作日志成功", count=count, data=queryset))


class SyncLogsHandler(BaseHandler):

    def get(self, *args, **kwargs):
        value = self.params.get('searchValue') if "searchValue" in self.params else self.params.get('value')
        self.params['page_size'] = 300
        filter_map = self.params.pop('filter_map') if "filter_map" in self.params else {}
        if 'resource_group' in filter_map: filter_map.pop('resource_group')

        with DBContext('r') as session:
            if value:
                page = paginate(session.query(SyncLogs).filter_by(**filter_map).filter(
                    SyncLogs.operation.like(f'%{value}%')).order_by(SyncLogs.create_time.desc()), **self.params)
            else:
                page = paginate(session.query(SyncLogs).filter_by(**filter_map).order_by(SyncLogs.create_time.desc()), **self.params)

        count, queryset = page.total, page.items
        return self.write(dict(code=0, result=True, msg="获取同步日志成功", count=count, data=queryset))


logs_urls = [
    (r"/auth/v3/accounts/logs/operation/", OperationLogsHandler, {"handle_name": "操作日志"}),
    (r"/auth/v3/accounts/logs/sync/", SyncLogsHandler, {"handle_name": "操作日志"}),
]

if __name__ == "__main__":
    pass
