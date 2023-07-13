from mg.handlers.login_handler import login_urls
from mg.handlers.login_v4_handler import login_v4_urls
from mg.handlers.users_handler import user_mg_urls
from mg.handlers.users_v4_handler import user_v4_mg_urls
from mg.handlers.roles_v4_handler import roles_v4_urls
from mg.handlers.functions_v4_handler import func_v4_urls
from mg.handlers.menus_v4_handler import menus_v4_urls
from mg.handlers.roles_handler import roles_urls
from mg.handlers.functions_handler import functions_urls
from mg.handlers.menus_handler import menus_urls
from mg.handlers.components_handler import components_urls
from mg.handlers.apps_v4_handler import apps_urls
from mg.handlers.business_handler import biz_mg_urls
from mg.handlers.business_v4_handler import biz_v4_mg_urls
from mg.handlers.token_v4_handler import token_urls
from mg.handlers.login_link_handler import link_v4_urls
from mg.handlers.app_mg_handler import app_mg_urls
from mg.handlers.configs_handler import app_settings_urls
from mg.handlers.notifications_handler import notifications_urls
from mg.handlers.custom_notice_handler import custom_notice_urls
from mg.handlers.storage_handler import storage_urls
from mg.handlers.favorites_v4_handler import favorites_urls

urls = []
urls.extend(user_mg_urls)
urls.extend(user_v4_mg_urls)
urls.extend(roles_v4_urls)
urls.extend(func_v4_urls)
urls.extend(menus_v4_urls)
urls.extend(login_urls)
urls.extend(login_v4_urls)
urls.extend(link_v4_urls)
urls.extend(roles_urls)
urls.extend(functions_urls)
urls.extend(components_urls)
urls.extend(menus_urls)
urls.extend(apps_urls)
urls.extend(biz_mg_urls)
urls.extend(biz_v4_mg_urls)
urls.extend(token_urls)
urls.extend(app_mg_urls)
urls.extend(app_settings_urls)
urls.extend(notifications_urls)
urls.extend(custom_notice_urls)
urls.extend(storage_urls)
urls.extend(favorites_urls)