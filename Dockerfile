FROM rockylinux:9.1

MAINTAINER "shenshuo<191715030@qq.com>"
# 设置编码和同步时间
ENV LANG C.UTF-8
ENV TZ=Asia/Shanghai

# 安装必要的软件包
RUN yum install -y python3 python3-pip git && \
    yum clean all && \
    rm -rf /var/cache/yum

# 升级 pip 并安装 codo_sdk
RUN python3 -m pip install --upgrade pip && \
    pip install -U git+https://github.com/ss1917/codo_sdk.git

# 设置环境变量
ARG SERVICE_NAME
ENV SERVICE_NAME=${SERVICE_NAME}

# 设置工作目录并复制文件
WORKDIR /data
COPY . .

# 安装项目依赖并赋予执行权限
RUN pip install -r docs/requirements.txt &> /dev/null && \
    chmod -R a+x /data/run-py.sh

# 暴露端口并启动服务
EXPOSE 8000
CMD /data/run-py.sh ${SERVICE_NAME}

### docker build --no-cache --build-arg SERVICE_NAME=admin-mg-api  . -t codo-admin-image