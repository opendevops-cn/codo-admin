# !/usr/bin/env python
# -*- coding: utf-8 -*-

from authority.handlers.users_handler import user_mg_urls
from authority.handlers.roles_handler import roles_urls
from authority.handlers.group_handler import groups_urls
from authority.handlers.functions_handler import functions_urls
from authority.handlers.menus_handler import menus_urls
from authority.handlers.components_handler import components_urls
from authority.handlers.apps_handler import apps_urls
from authority.handlers.business_handler import biz_mg_urls
from authority.handlers.privilege_handler import privilege_urls
from authority.handlers.logs_handler import logs_urls
from authority.handlers.subscribe_handler import subscribe_urls
from authority.handlers.login_handler import login_urls

urls = []
urls.extend(user_mg_urls)
urls.extend(roles_urls)
urls.extend(groups_urls)
urls.extend(functions_urls)
urls.extend(components_urls)
urls.extend(menus_urls)
urls.extend(apps_urls)
urls.extend(biz_mg_urls)
urls.extend(privilege_urls)
urls.extend(logs_urls)
urls.extend(subscribe_urls)
urls.extend(login_urls)
