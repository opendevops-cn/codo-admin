##部署文档
### 初始化环境变量
```
### 请自行修改相关配置
export mysql_database="shenshuo"
export MYSQL_PASSWORD="m9uSFL7duAVXfeAwGUSG"
export REDIS_PASSWORD="cWCVKJ7ZHUK12mVbivUf"
export MQ_USER="ss"
export MQ_PASSWORD="5Q2ajBHRT2lFJjnvaU0g"
### 管理后端地址
export mg_domain="mg.opendevops.cn"
### 定时任务地址
export cron_domain="cron.opendevops.cn"
### 任务系统地址
export task_domain="task.opendevops.cn"
### 前端地址
export front_domain="demo.opendevops.cn"
### api网关地址
export api_gw_url="http://gw.opendevops.cn/"
```
### 基础环境 python3
```bash
[ -f /usr/local/bin/python3 ] && echo "Python3 already exists" && exit -1
yum groupinstall Development tools -y
yum -y install zlib-devel
yum install -y python36-devel-3.6.3-7.el7.x86_64 openssl-devel libxslt-devel libxml2-devel libcurl-devel
cd /usr/local/src/
wget -q -c https://www.python.org/ftp/python/3.6.4/Python-3.6.4.tar.xz
tar xf  Python-3.6.4.tar.xz >/dev/null 2>&1 && cd Python-3.6.4
./configure >/dev/null 2>&1
make >/dev/null 2>&1 && make install >/dev/null 2>&1
if [ $? == 0 ];then
    echo "[安装python3] ==> OK"
else
    echo "[安装python3] ==> Faild"
    exit -1
fi
```
### docker docker-compose 安装
```bash
yum install -y yum-utils device-mapper-persistent-data lvm2
yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
yum-config-manager --enable docker-ce-edge
yum install -y docker-ce
###启动
/bin/systemctl start docker.service
### 开机自启
/bin/systemctl enable docker.service
#安装docker-compose编排工具
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
python3 get-pip.py
pip3 install docker-compose
```
#### MySQL安装
```bash
cat >docker-compose.yml <<EOF
mysql:
  restart: unless-stopped
  image: mysql:5.7
  volumes:
    - /data/mysql:/var/lib/mysql
    - /data/mysql_conf:/etc/mysql/conf.d
  ports:
    - "3306:3306"
  environment:
    - MYSQL_ROOT_PASSWORD=${MYSQL_PASSWORD}
EOF

#启动mysql容器（在docker-compose.yml同级目录）
docker-compose up -d
### 安装MySQL客户端测试一下
yum install http://www.percona.com/downloads/percona-release/redhat/0.1-3/percona-release-0.1-3.noarch.rpm
yum -y install Percona-Server-client-56
echo  "mysql -h 127.0.0.1 -u root -p ${MYSQL_PASSWORD}"
```
### 安装 Redis
```bash
function init_redis()
{
    echo "Start init redis"
    ### 开启AOF
    sed -i 's#appendonly no$#appendonly yes#g' /etc/redis.conf
    ### 操作系统决定
    sed -i 's#appendfsync .*$$#appendfsync everysec$#g' /etc/redis.conf
    ### 修改绑定IP
    sed -i 's/^bind 127.0.0.1$/#bind 127.0.0.1/g' /etc/redis.conf
    ### 是否以守护进程方式启动
    sed -i 's#daemonize no$#daemonize yes#g' /etc/redis.conf
    ### 当时间间隔超过60秒，或存储超过1000条记录时，进行持久化
    sed -i 's#^save 60 .*$#save 60 1000#g' /etc/redis.conf
    ### 快照压缩
    sed -i 's#rdbcompression no$#rdbcompression yes#g' /etc/redis.conf
    ### 添加密码
    sed -i "s#.*requirepass .*#requirepass ${REDIS_PASSWORD}#g" /etc/redis.conf
    echo "Start init redis end, must restart redis !!!"
}

[ -f /usr/bin/redis-server ] && echo "redis already exists" && init_redis && exit 0
echo "Start install redis server "
yum -y install redis-3.2.*

init_redis
systemctl restart redis
systemctl status redis

if [ $? == 0 ]; then
        echo "install successful"
else
        echo "install error" && exit -2
fi
```
### 安装 RabbitMQ
```bash
yum install  -y rabbitmq-server
rabbitmq-plugins enable rabbitmq_management
rabbitmqctl add_user ${MQ_USER} ${MQ_PASSWORD}
rabbitmqctl set_user_tags ${MQ_USER} administrator
rabbitmqctl  set_permissions  -p  '/'  ${MQ_USER} '.' '.' '.'
systemctl restart rabbitmq-server
systemctl enable rabbitmq-server
```
## 安装部署 do_mg
### MySQL 数据初始化
```bash
mysql -h 127.0.0.1 -u root -p ${MYSQL_PASSWORD} -e "create database ${mysql_database} default character set utf8mb4 collate utf8mb4_unicode_ci;"
mysql -h 127.0.0.1 -u root -p ${MYSQL_PASSWORD} < doc/data.sql
```
### 修改相关配置
```
### 进程数量
vi doc/supervisor_ops.conf
### nginx域名配置 doc/nginx_ops.conf
sed -i "s#\tserver_name .*#\tserver_name ${mg_domain};#g" doc/nginx_ops.conf
### 一定修改 配置文件中的  cookie_secret token_secret  请自行生成复杂的密钥串
export cookie_secret="nJ2oZis0V/xlArY2rzpIE6ioC9/KlqR2fd59sD=UXZJ=3OeROB"
export token_secret="1txIq2QUkeFsZizt3vEpVzUQNFS2@DpEQwbbw8k0YJt0biFScH"

sed -i "s#cookie_secret = .*#cookie_secret = '${cookie_secret}'#g" settings.py
sed -i "s#token_secret = .*#token_secret = '${token_secret}'#g" settings.py
vi settings
```
### 项目变量（选填）， 如果想从变量中获取配置请修改
```bash
# 写数据库
export DEFAULT_DB_DBHOST="10.2.2.236"
export DEFAULT_DB_DBPORT='3306'
export DEFAULT_DB_DBUSER='root'
export DEFAULT_DB_DBPWD=${MYSQL_PASSWORD}
export DEFAULT_DB_DBNAME=${mysql_database}
# 读数据库
export READONLY_DB_DBHOST='10.2.2.236'
export READONLY_DB_DBPORT='3306'
export READONLY_DB_DBUSER='root'
export READONLY_DB_DBPWD=${MYSQL_PASSWORD}
export READONLY_DB_DBNAME=${mysql_database}
# 消息队列
export DEFAULT_MQ_ADDR='10.2.2.236'
export DEFAULT_MQ_USER=${MQ_USER}
export DEFAULT_MQ_PWD=${MQ_PASSWORD}
# 缓存
export DEFAULT_REDIS_HOST='10.2.2.236'
export DEFAULT_REDIS_PORT=6379
export DEFAULT_REDIS_PASSWORD=${REDIS_PASSWORD}
```
### 编译镜像
```bash
docker build . -t do_mg_image
```
### docker 启动
```bash
cat >docker-compose.yml <<EOF
auto_ops:
  restart: unless-stopped
  image: do_mg_image
  volumes:
    - /var/log/supervisor/:/var/log/supervisor/
    - /var/www/do_mg/:/var/www/do_mg/
    - /sys/fs/cgroup:/sys/fs/cgroup
  ports:
    - "${PROJECT_PORT}:80"
  environment:
    - DOMAIN_NAME=${DOMAIN_NAME}
    - PROJECT_PORT=${PROJECT_PORT}
    - DEFAULT_DB_DBHOST=${DEFAULT_DB_DBHOST}
    - DEFAULT_DB_DBPORT=${DEFAULT_DB_DBPORT}
    - DEFAULT_DB_DBUSER=${DEFAULT_DB_DBUSER}
    - DEFAULT_DB_DBPWD=${DEFAULT_DB_DBPWD}
    - DEFAULT_DB_DBNAME=${DEFAULT_DB_DBNAME}
    - READONLY_DB_DBHOST=${READONLY_DB_DBHOST}
    - READONLY_DB_DBPORT=${READONLY_DB_DBPORT}
    - READONLY_DB_DBUSER=${READONLY_DB_DBUSER}
    - READONLY_DB_DBPWD=${READONLY_DB_DBPWD}
    - READONLY_DB_DBNAME=${READONLY_DB_DBNAME}
    - DEFAULT_MQ_ADDR=${DEFAULT_MQ_ADDR}
    - DEFAULT_MQ_USER=${DEFAULT_MQ_USER}
    - DEFAULT_MQ_PWD=${DEFAULT_MQ_PWD}
    - DEFAULT_REDIS_HOST=${DEFAULT_REDIS_HOST}
    - DEFAULT_REDIS_PORT=${DEFAULT_REDIS_PORT}
    - DEFAULT_REDIS_PASSWORD=${DEFAULT_REDIS_PASSWORD}
  hostname: OPS-NW-mg-exec01
EOF
docker-compose up -d
```