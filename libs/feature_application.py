#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
Author : ming
date   : 2018年1月12日13:43:27
role   : 定制 Application
"""

import asyncio
import logging
from shortuuid import uuid
from tornado import httpserver, ioloop
from tornado import options as tnd_options
from tornado.options import options, define
from tornado.web import Application as tornadoApp
from tornado.web import RequestHandler
from websdk2.configs import configs

define("addr", default='0.0.0.0', help="run on the given ip address", type=str)
define("port", default=8000, help="run on the given port", type=int)
define("progid", default=str(uuid()), help="tornado progress id", type=str)

urls_meta_list = []


class Application(tornadoApp):
    """ 定制 Tornado Application 集成日志、sqlalchemy 等功能 """

    def __init__(self, handlers=None, default_host="", transforms=None, **settings):
        tnd_options.parse_command_line()
        if configs.can_import: configs.import_dict(**settings)
        handlers.extend([(r"/v1/probe/meta/urls/", MetaProbe), ])
        self.urls_meta_handle(handlers)
        max_buffer_size = configs.get('max_buffer_size')
        max_body_size = configs.get('max_body_size')
        super(Application, self).__init__(handlers, default_host, transforms, **configs)
        self.http_server = httpserver.HTTPServer(self, max_buffer_size=max_buffer_size, max_body_size=max_body_size)
        self.__options = options
        # self.http_server.listen(options.port, address=options.addr)
        # self.io_loop = ioloop.IOLoop.instance()

    async def http_server_main(self):
        self.http_server.listen(self.__options.port, address=self.__options.addr)
        await asyncio.Event().wait()

    def start_server(self):
        """
        启动 tornado 服务
        :return:
        """
        try:
            # init_logging()
            logging.info('progressid: %(progid)s' % dict(progid=options.progid))
            logging.info('server address: %(addr)s:%(port)d' % dict(addr=options.addr, port=options.port))
            logging.info('web server start sucessfuled.')
            # self.io_loop.start()
            asyncio.run(self.http_server_main())
        except KeyboardInterrupt:
            pass
            # self.io_loop.stop()
        except:
            import traceback
            logging.error('%(tra)s' % dict(tra=traceback.format_exc()))

    def urls_meta_handle(self, urls):
        # 数据写入内存，启动的时候上报至权限管理
        urls_meta_list.extend([{"url": u[0], "name": u[2].get('handle_name')[0:30] if u[2].get('handle_name') else "",
                                "method": u[2].get('method') if u[2].get('method') and len(
                                    u[2].get('method')) < 100 else [],
                                "status": u[2].get('handle_status')[0:2] if u[2].get('handle_status') else "y"} if len(
            u) > 2 else {"url": u[0], "name": "暂无", "status": "y"} for u in urls])


class MetaProbe(RequestHandler):
    def head(self, *args, **kwargs):
        self.write(dict(code=0, msg="Get success", count=len(urls_meta_list), data=urls_meta_list))

    def get(self, *args, **kwargs):
        self.write(dict(code=0, msg="Get success", count=len(urls_meta_list), data=urls_meta_list))


if __name__ == '__main__':
    pass
