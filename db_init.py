# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2024/3/27
# @Description: 数据库创建和数据初始化
import os
from sqlalchemy import create_engine, text
from websdk2.consts import const

from models.authority import Base as AuBase
from models.paas_model import Base as AppsBase
from settings import settings as app_settings

default_configs = app_settings[const.DB_CONFIG_ITEM][const.DEFAULT_DB_KEY]

engine = create_engine(
    f'mysql+pymysql://{default_configs.get(const.DBUSER_KEY)}:'
    f'{default_configs.get(const.DBPWD_KEY)}@{default_configs.get(const.DBHOST_KEY)}:'
    f'{default_configs.get(const.DBPORT_KEY)}/{default_configs.get(const.DBNAME_KEY)}'
    f'?charset=utf8mb4',
    echo=True
)

sql_folder = './docs/sql/'


def import_data():
    err_cnt = 0
    success_cnt = 0
    for filename in os.listdir(sql_folder):
        file_path = os.path.join(sql_folder, filename)
        if filename.endswith('.sql'):
            with open(file_path, 'r') as file:
                for line in file.readlines():
                    with engine.connect() as conn:
                        try:
                            conn.execute(text(line.strip()))
                            conn.commit()
                        except Exception as e:
                            err_cnt += 1
                            print(f"Executed SQL file: {filename} error, sql:{line}, msg: {e}")
                        else:
                            success_cnt += 1
                            print(f"Executed SQL file: {filename} success. sql: {line}")
    print(f"errors: {err_cnt}, success: {success_cnt}")


if __name__ == '__main__':
    import_data()
