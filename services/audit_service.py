#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023/7/10 15:14
Desc    : 审计日志
"""

import json
import logging
from datetime import datetime, timedelta

from sqlalchemy import inspect, text
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.sqlalchemy_pagination import paginate
from websdk2.utils.date_format import date_format_to8

from models.paas_model import OperationRecords


def get_opt_log_list_v4(**params) -> dict:
    key = params.get('key')
    value = params.get('value')
    start_date = params.get('start_date')
    end_date = params.get('end_date')
    filter_map = params.get('filter_map')
    filter_map = json.loads(filter_map) if filter_map else {}
    if key and value:
        filter_map = {key: value}
    start_time_tuple, end_time_tuple = date_format_to8(start_date, end_date)

    with DBContext('r') as session:
        page = paginate(session.query(OperationRecords).filter(
            OperationRecords.create_time.between(start_time_tuple, end_time_tuple)).filter_by(**filter_map), **params)

    return dict(code=0, msg="获取成功", count=page.total, data=page.items)


def table_exists(session, table_name):
    """检查表是否存在"""
    try:
        # 使用 inspect 检查表是否存在
        inspector = inspect(session.bind)
        return table_name in inspector.get_table_names()
    except Exception as e:
        logging.info(f"Error checking table existence: {e}")
        return False


def create_archive_table(session, table_name):
    """动态创建归档表，如果不存在"""
    if table_exists(session, table_name):
        logging.info(f"Archive table {table_name} already exists. Skipping creation.")
        return

    try:
        # 动态创建归档表，结构与主表一致
        create_table_sql = text(f"CREATE TABLE {table_name} LIKE codo_opt_records;")
        session.execute(create_table_sql)
        logging.info(f"Successfully created archive table: {table_name}")
    except Exception as e:
        session.rollback()
        logging.error(f"Failed to create archive table {table_name}: {e}")
        raise


def archive_data():
    """将上上个月的日志归档到归档表"""
    with DBContext('w', None, True) as session:
        try:
            # 获取当前日期和归档时间点
            current_date = datetime.now()
            logging.info(f"开启日志归档")

            # 计算上上个月的日期
            # 当前月份减去2个月
            archive_date = current_date - timedelta(days=60)  # 上上个月的日期
            archive_year = archive_date.year
            archive_month = archive_date.month

            # 获取归档表名
            archive_table_name = f"codo_opt_records_archive_{archive_date.strftime('%Y%m')}"

            # 如果表不存在，创建归档表
            if not table_exists(session, archive_table_name):
                create_archive_table(session, archive_table_name)
            else:
                return

            # 迁移上上个月的数据到归档表
            logging.info(f"Archiving data for {archive_year}-{archive_month:02d} to {archive_table_name}")
            sql_query = text("""
                INSERT INTO :archive_table_name
                SELECT * FROM codo_opt_records 
                WHERE EXTRACT(YEAR FROM create_time) = :archive_year
                  AND EXTRACT(MONTH FROM create_time) = :archive_month;
            """)
            logging.info(sql_query)
            session.execute(sql_query, {
                "archive_table_name": archive_table_name,
                "archive_year": archive_year,
                "archive_month": archive_month
            })

            # 删除主表中已归档的数据
            logging.info(f"Deleting archived data for {archive_year}-{archive_month:02d} from main table")
            sql_delete = text("""
                DELETE FROM codo_opt_records
                WHERE EXTRACT(YEAR FROM create_time) = :archive_year
                  AND EXTRACT(MONTH FROM create_time) = :archive_month;
            """)

            # 执行删除操作并传递参数
            session.execute(sql_delete, {
                "archive_year": archive_year,
                "archive_month": archive_month
            })

            # 提交事务
            session.commit()
            logging.info(f"Data for {archive_year}-{archive_month:02d} successfully archived and deleted .")

        except Exception as e:
            session.rollback()  # 回滚事务
            logging.error(f"Error during archiving process: {e}")
