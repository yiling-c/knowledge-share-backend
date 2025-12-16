"""
数据库配置和模型定义
"""
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# 数据库文件路径
DATABASE_URL = "sqlite:///./quiz_data.db"

# 创建数据库引擎
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # SQLite 需要这个参数
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类
Base = declarative_base()

# ==================== 数据库模型 ====================

class QuizRecord(Base):
    """答题记录表"""
    __tablename__ = "quiz_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    quiz_id = Column(String(50), nullable=False, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    user_name = Column(String(100), nullable=False)
    selected_option = Column(String(10), nullable=False)
    is_correct = Column(Boolean, nullable=False)
    answered_at = Column(DateTime, default=datetime.now, nullable=False)

class UserScore(Base):
    """用户积分表"""
    __tablename__ = "user_scores"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_name = Column(String(100), unique=True, nullable=False, index=True)
    correct_count = Column(Integer, default=0, nullable=False)
    wrong_count = Column(Integer, default=0, nullable=False)
    total_score = Column(Integer, default=0, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

class QuizStat(Base):
    """问题统计表"""
    __tablename__ = "quiz_stats"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    quiz_id = Column(String(50), unique=True, nullable=False, index=True)
    correct_count = Column(Integer, default=0, nullable=False)
    wrong_count = Column(Integer, default=0, nullable=False)
    total_count = Column(Integer, default=0, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

# ==================== 辅助函数 ====================

def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """初始化数据库，创建所有表"""
    Base.metadata.create_all(bind=engine)
    print("数据库初始化完成！")

if __name__ == "__main__":
    # 直接运行此文件可以初始化数据库
    init_db()
