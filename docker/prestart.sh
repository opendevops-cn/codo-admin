#!/bin/sh
cd /var/www/codo-admin/

  #管理后端-admin
  echo -e "\033[32m [INFO]: 开始修改各项目的配置文件 \033[0m"
  source /opt/codo/env.sh
  sed -i "s#cookie_secret = .*#cookie_secret = '${cookie_secret}'#g" codo-admin-settings.py
  sed -i "s#token_secret = .*#token_secret = '${token_secret}'#g" codo-admin-settings.py
  DEFAULT_DB_DBNAME='codo_admin'
  sed -i "s#DEFAULT_DB_DBHOST = .*#DEFAULT_DB_DBHOST = os.getenv('DEFAULT_DB_DBHOST', '${DEFAULT_DB_DBHOST}')#g" codo-admin-settings.py
  sed -i "s#DEFAULT_DB_DBPORT = .*#DEFAULT_DB_DBPORT = os.getenv('DEFAULT_DB_DBPORT', '${DEFAULT_DB_DBPORT}')#g" codo-admin-settings.py
  sed -i "s#DEFAULT_DB_DBUSER = .*#DEFAULT_DB_DBUSER = os.getenv('DEFAULT_DB_DBUSER', '${DEFAULT_DB_DBUSER}')#g" codo-admin-settings.py
  sed -i "s#DEFAULT_DB_DBPWD = .*#DEFAULT_DB_DBPWD = os.getenv('DEFAULT_DB_DBPWD', '${DEFAULT_DB_DBPWD}')#g" codo-admin-settings.py
  sed -i "s#DEFAULT_DB_DBNAME = .*#DEFAULT_DB_DBNAME = os.getenv('DEFAULT_DB_DBNAME', '${DEFAULT_DB_DBNAME}')#g" codo-admin-settings.py
  sed -i "s#READONLY_DB_DBHOST = .*#READONLY_DB_DBHOST = os.getenv('READONLY_DB_DBHOST', '${READONLY_DB_DBHOST}')#g" codo-admin-settings.py
  sed -i "s#READONLY_DB_DBPORT = .*#READONLY_DB_DBPORT = os.getenv('READONLY_DB_DBPORT', '${READONLY_DB_DBPORT}')#g" codo-admin-settings.py
  sed -i "s#READONLY_DB_DBUSER = .*#READONLY_DB_DBUSER = os.getenv('READONLY_DB_DBUSER', '${READONLY_DB_DBUSER}')#g" codo-admin-settings.py
  sed -i "s#READONLY_DB_DBPWD = .*#READONLY_DB_DBPWD = os.getenv('READONLY_DB_DBPWD', '${READONLY_DB_DBPWD}')#g" codo-admin-settings.py
  sed -i "s#READONLY_DB_DBNAME = .*#READONLY_DB_DBNAME = os.getenv('READONLY_DB_DBNAME', '${DEFAULT_DB_DBNAME}')#g" codo-admin-settings.py
  sed -i "s#DEFAULT_REDIS_HOST = .*#DEFAULT_REDIS_HOST = os.getenv('DEFAULT_REDIS_HOST', '${DEFAULT_REDIS_HOST}')#g" codo-admin-settings.py
  sed -i "s#DEFAULT_REDIS_PORT = .*#DEFAULT_REDIS_PORT = os.getenv('DEFAULT_REDIS_PORT', '${DEFAULT_REDIS_PORT}')#g" codo-admin-settings.py
  sed -i "s#DEFAULT_REDIS_PASSWORD = .*#DEFAULT_REDIS_PASSWORD = os.getenv('DEFAULT_REDIS_PASSWORD', '${DEFAULT_REDIS_PASSWORD}')#g" codo-admin-settings.py

#python3 /var/www/kerrigan/db_sync.py