#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
Author : ming
date   : 2018年1月12日13:43:27
role   : 定制 Application
"""

import asyncio
import logging
from abc import ABC

from shortuuid import uuid
from tornado import httpserver
from tornado.options import options, define, parse_command_line
from tornado.web import Application as TornadoApp, RequestHandler
from websdk2.configs import configs
from websdk2.logger import init_logging

define("addr", default='0.0.0.0', help="run on the given ip address", type=str)
define("port", default=8000, help="run on the given port", type=int)
define("progid", default=str(uuid()), help="tornado progress id", type=str)
init_logging()
urls_meta_list = []


class Application(TornadoApp):
    """ 定制 Tornado Application 集成日志、sqlalchemy 等功能 """

    def __init__(self, handlers=None, **settings):
        parse_command_line()
        handlers = handlers or []
        handlers.append((r"/v1/probe/meta/urls/", MetaProbe))

        if configs.can_import:
            configs.import_dict(**settings)

        self._generate_url_metadata(handlers)

        max_buffer_size = configs.get("max_buffer_size")
        max_body_size = configs.get("max_body_size")
        super().__init__(handlers, **configs)

        self.http_server = httpserver.HTTPServer(
            self, max_buffer_size=max_buffer_size, max_body_size=max_body_size
        )

    async def http_server_main(self):
        self.http_server.listen(options.port, address=options.addr)
        logging.info(f"Server started on {options.addr}:{options.port} with process ID {options.progid}")
        await asyncio.Event().wait()

    def start_server(self):
        """Start Tornado server."""
        try:
            logging.info(f"Process ID: {options.progid}")
            asyncio.run(self.http_server_main())
        except KeyboardInterrupt:
            logging.info("Server shut down gracefully.")
        except Exception as e:
            logging.error(f"Unexpected error: {e}", exc_info=True)

    @staticmethod
    def _generate_url_metadata(urls):
        """Generate metadata for registered URLs."""
        for url in urls:
            meta = {
                "url": url[0],
                "name": url[2].get("handle_name", "暂无")[:30] if len(url) > 2 else "暂无",
                "method": url[2].get("method", []) if len(url) > 2 else [],
                "status": url[2].get("handle_status", "y")[:2] if len(url) > 2 else "y",
            }
            urls_meta_list.append(meta)


class MetaProbe(ABC, RequestHandler):
    def head(self, *args, **kwargs):
        self._write_response()

    def get(self, *args, **kwargs):
        self._write_response()

    def _write_response(self):
        self.write({
            "code": 0,
            "msg": "Get success",
            "count": len(urls_meta_list),
            "data": urls_meta_list,
        })


if __name__ == '__main__':
    pass
