#!/bin/sh
cd /var/www/codo-admin/

  #管理后端-admin
  echo -e "\033[32m [INFO]: 开始修改各项目的配置文件 \033[0m"
  sed -i "s#cookie_secret = .*#cookie_secret = '${cookie_secret}'#g" settings.py
  sed -i "s#token_secret = .*#token_secret = '${token_secret}'#g" settings.py
  DEFAULT_DB_DBNAME='codo_admin'
  sed -i "s#DEFAULT_DB_DBHOST = .*#DEFAULT_DB_DBHOST = os.getenv('DEFAULT_DB_DBHOST', '${DEFAULT_DB_DBHOST}')#g" settings.py
  sed -i "s#DEFAULT_DB_DBPORT = .*#DEFAULT_DB_DBPORT = os.getenv('DEFAULT_DB_DBPORT', '${DEFAULT_DB_DBPORT}')#g" settings.py
  sed -i "s#DEFAULT_DB_DBUSER = .*#DEFAULT_DB_DBUSER = os.getenv('DEFAULT_DB_DBUSER', '${DEFAULT_DB_DBUSER}')#g" settings.py
  sed -i "s#DEFAULT_DB_DBPWD = .*#DEFAULT_DB_DBPWD = os.getenv('DEFAULT_DB_DBPWD', '${DEFAULT_DB_DBPWD}')#g" settings.py
  sed -i "s#DEFAULT_DB_DBNAME = .*#DEFAULT_DB_DBNAME = os.getenv('DEFAULT_DB_DBNAME', '${DEFAULT_DB_DBNAME}')#g" settings.py
  sed -i "s#READONLY_DB_DBHOST = .*#READONLY_DB_DBHOST = os.getenv('READONLY_DB_DBHOST', '${READONLY_DB_DBHOST}')#g" settings.py
  sed -i "s#READONLY_DB_DBPORT = .*#READONLY_DB_DBPORT = os.getenv('READONLY_DB_DBPORT', '${READONLY_DB_DBPORT}')#g" settings.py
  sed -i "s#READONLY_DB_DBUSER = .*#READONLY_DB_DBUSER = os.getenv('READONLY_DB_DBUSER', '${READONLY_DB_DBUSER}')#g" settings.py
  sed -i "s#READONLY_DB_DBPWD = .*#READONLY_DB_DBPWD = os.getenv('READONLY_DB_DBPWD', '${READONLY_DB_DBPWD}')#g" settings.py
  sed -i "s#READONLY_DB_DBNAME = .*#READONLY_DB_DBNAME = os.getenv('READONLY_DB_DBNAME', '${DEFAULT_DB_DBNAME}')#g" settings.py
  sed -i "s#DEFAULT_REDIS_HOST = .*#DEFAULT_REDIS_HOST = os.getenv('DEFAULT_REDIS_HOST', '${DEFAULT_REDIS_HOST}')#g" settings.py
  sed -i "s#DEFAULT_REDIS_PORT = .*#DEFAULT_REDIS_PORT = os.getenv('DEFAULT_REDIS_PORT', '${DEFAULT_REDIS_PORT}')#g" settings.py
  sed -i "s#DEFAULT_REDIS_PASSWORD = .*#DEFAULT_REDIS_PASSWORD = os.getenv('DEFAULT_REDIS_PASSWORD', '${DEFAULT_REDIS_PASSWORD}')#g" settings.py


try_num=0

while [[ $try_num -le 100 ]];
do
     if $(curl  -s ${DEFAULT_DB_DBHOST}:${DEFAULT_DB_DBPORT}  > /dev/null);then
          python3 db_sync.py
          sleep 3
          mycli -h${DEFAULT_DB_DBHOST} -u${DEFAULT_DB_DBUSER} -p${MYSQL_PASSWORD} codo_admin < codo_admin_beta0.3.sql
          check_admin_user_num=`mycli -h${DEFAULT_DB_DBHOST} -u${DEFAULT_DB_DBUSER} -p${MYSQL_PASSWORD} codo_admin -e "select username from mg_users where username='admin';" | wc -l`
          if [ ${check_admin_user_num} -eq 0 ]; then 
               mysql -h${DEFAULT_DB_DBHOST} -u${DEFAULT_DB_DBUSER} -p${MYSQL_PASSWORD} codo_admin < ./codo_admin_beta0.3.sql; 
          else 
               echo "初始化用户已存在" ; 
          fi
          
          if [ $? -eq 0 ]; then 
               echo -e "\033[32m [INFO]: 导入codo-admin用户权限数据完成. \033[0m"; 
          else 
               echo -e "\033[31m [ERROR]: 导入codo-admin用户权限数据完成失败 \033[0m" && exit -6; 
          fi

          exit 0
     else
          echo 'wait mysql start to do db_sync.py'
     fi
     let try_num+=1
     sleep 3
done