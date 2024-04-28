import sys
import getpass
from datetime import datetime
import hashlib
import os
import argparse

from sqlalchemy import create_engine, text
from websdk2.consts import const

from settings import settings as app_settings

default_configs = app_settings[const.DB_CONFIG_ITEM][const.DEFAULT_DB_KEY]

engine = create_engine(
    f'mysql+pymysql://{default_configs.get(const.DBUSER_KEY)}:'
    f'{default_configs.get(const.DBPWD_KEY)}@{default_configs.get(const.DBHOST_KEY)}:'
    f'{default_configs.get(const.DBPORT_KEY)}/{default_configs.get(const.DBNAME_KEY)}'
    f'?charset=utf8mb4',
)

BASE_DIR = os.getcwd()
SQL_FOLDER = os.path.join(BASE_DIR, 'docs', 'sql')


def calculate_md5(input_string):
    # 创建一个 MD5 哈希对象
    md5_hash = hashlib.md5()

    # 将输入字符串编码为字节串，并更新哈希对象
    md5_hash.update(input_string.encode('utf-8'))

    # 获取哈希值的十六进制表示
    md5_hex = md5_hash.hexdigest()

    return md5_hex


class CommandError(Exception):
    """自定义异常类，用于处理命令执行过程中的错误"""
    pass


class BaseCommand:
    """命令的基类，用于定义和执行命令"""

    def handle(self):
        """解析命令行参数并执行相应的命令"""
        raise NotImplementedError('子类需要实现 handle 方法')


class DBInit(BaseCommand):
    """
    数据初始化
    """

    def handle(self):
        err_cnt = 0
        success_cnt = 0
        for filename in os.listdir(SQL_FOLDER):
            file_path = os.path.join(SQL_FOLDER, filename)
            if filename.endswith('.sql'):
                with open(file_path, 'r') as file:
                    for line in file.readlines():
                        with engine.connect() as conn:
                            trans = conn.begin()
                            try:
                                conn.execute(text(line.strip()))
                                trans.commit()
                            except Exception as e:
                                trans.rollback()
                                err_cnt += 1
                                print(
                                    f"Executed SQL file: {filename} error, sql:{line}, msg: {e}")
                            else:
                                success_cnt += 1
                                print(
                                    f"Executed SQL file: {filename} success. sql: {line}")
            print(f"errors: {err_cnt}, success: {success_cnt}")


class CreateSuperUser(BaseCommand):
    """创建超级用户"""

    def handle(self):
        """解析命令行参数并执行相应的命令"""
        # 提示用户输入用户名
        username = input("Enter username: ")
        # 提示用户输入昵称名
        nickname = input("Enter nickname: ")
        # 提示用户输入电子邮件
        email = input("Enter email: ")
        # 提示用户输入密码
        password = getpass.getpass("Enter password: ")
        create_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        raw = f"""INSERT INTO `codo_a_users` (`create_time`, `update_time`, 
        `username`,`password`, `nickname`, `email`, `superuser`, `status`) 
        SELECT '{create_time}', '{create_time}', '{username}', 
        '{calculate_md5(password)}', '{nickname}','{email}', '0', '0' 
        FROM dual WHERE NOT EXISTS 
        (SELECT * FROM `codo_a_users` WHERE username = '{create_time}')"""
        with engine.connect() as conn:
            trans = conn.begin()
            try:
                conn.execute(text(raw))
                trans.commit()
            except Exception as e:
                print(f"Create SuperUser Error: {e}")
                trans.rollback()
                sys.exit(1)
            else:
                print(f"Create SuperUser Success: {username}")


def execute_from_command_line(argv):
    """解析命令行参数并执行相应的命令"""
    if len(argv) < 2:
        print("Usage: manage.py <subcommand>")
        sys.exit(1)
    parser = argparse.ArgumentParser(description='A simple command line tool.',
                                     usage='%(prog)s <subcommand>')

    # 添加子命令
    subparsers = parser.add_subparsers(title='subcommands', dest='subcommand')

    # 添加子命令 'createsuperuser'
    hello_parser = subparsers.add_parser('createsuperuser',
                                         help='used to create superuser.')
    hello_parser.set_defaults(func=CreateSuperUser.handle)

    # 添加子命令 'db_init'
    goodbye_parser = subparsers.add_parser('db_init', help='used to db init.')
    goodbye_parser.set_defaults(func=DBInit.handle)

    # 解析命令行参数
    args = parser.parse_args()
    # 调用相应的子命令处理函数
    args.func(args)


if __name__ == "__main__":
    execute_from_command_line(sys.argv)
