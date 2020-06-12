FROM registry.cn-hangzhou.aliyuncs.com/sourcegarden/python:centos7-3.6

RUN mkdir -p /var/www/
ADD . /var/www/codo-admin/

RUN pip3 install  -i https://pypi.tuna.tsinghua.edu.cn/simple -r /var/www/codo-admin/requirements.txt

COPY docker/nginx_ops.conf /etc/nginx/conf.d/codo-admin.conf
COPY docker/supervisor_ops.conf  /etc/supervisord.conf

EXPOSE 80
CMD ["/usr/bin/supervisord"]