from websdk2.db_context import DBContextV2 as DBContext
from models.authority_model import OperationLogs
def add_operation_log(data: dict):
    """用户操作日志"""
    with DBContext('w', None, True) as session:
        new_log = OperationLogs(**data)
        session.add(new_log)
        session.commit()
        log_id = new_log.id
    return log_id
