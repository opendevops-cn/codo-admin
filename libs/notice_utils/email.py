#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2021/1/13 16:02 
Desc    : 发送邮件
"""

import os
import json
import smtplib
from string import Template
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class MailNotice(object):
    def __init__(self, **kwargs):
        """
        :param mail_host:     SMTP主机
        :param mail_port:     SMTP端口
        :param mail_user:     SMTP账号
        :param mail_password: SMTP密码
        :param mail_ssl:      SSL=True, 如果SMTP端口是465，通常需要启用SSL，  如果SMTP端口是587，通常需要启用TLS
        """
        self.mail_host = kwargs.get('mail_host')
        self.mail_port = kwargs.get('mail_port')
        self.__mail_user = kwargs.get('mail_user')
        self.__mail_password = kwargs.get('mail_password')
        self.mail_ssl = kwargs.get('mail_ssl')
        self.mail_tls = kwargs.get('mail_tls')

    def send(self, **kwargs):
        """
        :param to_list:  收件人，多收件人半角逗号分割， 必填
        :param subject:  标题， 必填
        :param content:  内容， 必填
        :param subtype:  格式，默认：plain, 可选html
        :param att:      附件，支持单附件，选填
        """
        # msg = kwargs.get('msg')
        ### 通知模板
        msg_template = kwargs.get('msg_template')
        msg = kwargs.get('msg', {})
        s = Template(msg_template)
        data = s.safe_substitute(msg)
        data = json.loads(data)
        ###


        send_addr = kwargs.get('send_addr')
        to_list = send_addr.get('email')
        if isinstance(to_list, list): to_list = ','.join(to_list)
        subject = data.get('subject')
        content = data.get('content')

        subtype = data.get('subtype', 'plain')
        att = data.get('att')
        ###
        msg = MIMEMultipart()
        msg['Subject'] = subject  ## 标题
        msg['From'] = self.__mail_user  ## 发件人
        msg['To'] = to_list  # 收件人，必须是一个字符串
        # 邮件正文内容
        msg.attach(MIMEText(content, subtype, 'utf-8'))
        if att:
            if not os.path.isfile(att): raise FileNotFoundError('{0} file does not exist'.format(att))

            dirname, filename = os.path.split(att)
            # 构造附件1，传送当前目录下的 test.txt 文件
            att1 = MIMEText(open(att, 'rb').read(), 'base64', 'utf-8')
            att1["Content-Type"] = 'application/octet-stream'
            # 这里的filename可以任意写，写什么名字，邮件中显示什么名字
            att1["Content-Disposition"] = 'attachment; filename="{0}"'.format(filename)
            msg.attach(att1)

        try:
            if self.mail_ssl:
                '''SSL加密方式，通信过程加密，邮件数据安全, 使用端口465'''
                server = smtplib.SMTP_SSL()
                server.connect(self.mail_host, self.mail_port)  # 连接服务器
                server.login(self.__mail_user, self.__mail_password)  # 登录操作
                server.sendmail(self.__mail_user, to_list.split(','), msg.as_string())
                server.close()
            elif self.mail_tls:
                # print('Use TLS SendMail')
                '''使用TLS模式'''
                server = smtplib.SMTP()
                server.connect(self.mail_host, self.mail_port)  # 连接服务器
                server.starttls()
                server.login(self.__mail_user, self.__mail_password)  # 登录操作
                server.sendmail(self.__mail_user, to_list.split(','), msg.as_string())
                server.close()
            else:
                '''使用普通模式'''
                server = smtplib.SMTP()
                server.connect(self.mail_host, self.mail_port)  # 连接服务器
                server.login(self.__mail_user, self.__mail_password)  # 登录操作
                server.sendmail(self.__mail_user, to_list.split(','), msg.as_string())
                server.close()
        except Exception as e:
            return {"Message": str(e), "Code": -1}

        return {"Message": "OK", "Code": 0}
