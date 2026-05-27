"""数据库模型 - SQLAlchemy + PostgreSQL"""
from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

Base = declarative_base()

# 数据库连接 (修改为你的数据库URL)
# PostgreSQL: postgresql://user:pass@localhost/edumesh
# MySQL: mysql+pymysql://user:pass@localhost/edumesh
# SQLite: sqlite:///edumesh.db (本地测试)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///edumesh.db")

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class StudentDB(Base):
    __tablename__ = "students"

    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    engagement_score = Column(Float, default=1.0)
    consecutive_errors = Column(Integer, default=0)
    total_questions = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    current_path = Column(JSON, default=list)
    path_index = Column(Integer, default=0)
    session_history = Column(JSON, default=list)

class MasteryDB(Base):
    __tablename__ = "mastery"

    id = Column(String(100), primary_key=True)  # student_id:knowledge_point_id
    student_id = Column(String(50), nullable=False, index=True)
    knowledge_point_id = Column(String(50), nullable=False)
    p_known = Column(Float, default=0.3)
    p_learn = Column(Float, default=0.1)
    p_guess = Column(Float, default=0.2)
    p_slip = Column(Float, default=0.1)
    p_forget = Column(Float, default=0.05)
    attempts = Column(Integer, default=0)
    correct_count = Column(Integer, default=0)
    last_review = Column(DateTime, nullable=True)
    next_review = Column(DateTime, nullable=True)
    interval_days = Column(Integer, default=1)
    ef = Column(Float, default=2.5)
    version = Column(Integer, default=0)

class QuestionDB(Base):
    __tablename__ = "questions"

    id = Column(String(50), primary_key=True)
    knowledge_point_id = Column(String(50), nullable=False, index=True)
    subject = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    options = Column(JSON, nullable=True)
    correct_answer = Column(String(200), nullable=False)
    explanation = Column(Text, default="")
    difficulty = Column(Float, default=0.5)
    hint_level1 = Column(Text, default="")
    hint_level2 = Column(Text, default="")
    hint_level3 = Column(Text, default="")

class EventLogDB(Base):
    __tablename__ = "event_logs"

    id = Column(String(100), primary_key=True)
    event_type = Column(String(50), nullable=False, index=True)
    student_id = Column(String(50), nullable=False, index=True)
    source = Column(String(50), nullable=False)
    payload = Column(JSON)
    created_at = Column(DateTime, default=datetime.now, index=True)

# 初始化数据库表
def init_db():
    Base.metadata.create_all(bind=engine)
    print("✅ 数据库表已创建")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
