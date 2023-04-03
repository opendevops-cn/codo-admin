from sqlalchemy import Column, DateTime
from datetime import datetime
class TimeBaseModel(object):
    """模型基类，为模型补充创建时间与更新时间"""
    create_time = Column(DateTime, nullable=False, default=datetime.now)  # 记录的创建时间
    update_time = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)  # 记录的更新时间
