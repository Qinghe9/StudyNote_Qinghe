"""
数据模型 - 学习者模型与核心数据结构
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import json


@dataclass
class Student:
    """学生/学习者模型"""
    student_id: str
    name: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    total_attempts: int = 0
    correct_attempts: int = 0
    current_difficulty: str = "medium"  # easy, medium, hard
    engagement_score: float = 1.0  # 0.0-1.0，学习投入度
    frustration_level: float = 0.0  # 0.0-1.0，挫败感
    learning_style: str = "adaptive"  # inductive, deductive, adaptive

    def to_dict(self) -> dict:
        return {
            "student_id": self.student_id,
            "name": self.name,
            "created_at": self.created_at,
            "total_attempts": self.total_attempts,
            "correct_attempts": self.correct_attempts,
            "current_difficulty": self.current_difficulty,
            "engagement_score": self.engagement_score,
            "frustration_level": self.frustration_level,
            "learning_style": self.learning_style
        }


@dataclass
class Question:
    """题目模型"""
    question_id: str
    content: str
    correct_answer: str
    difficulty: str  # easy, medium, hard
    subject: str
    topic: str
    hints: List[str] = field(default_factory=list)
    explanation: str = ""

    def to_dict(self) -> dict:
        return {
            "question_id": self.question_id,
            "content": self.content,
            "difficulty": self.difficulty,
            "subject": self.subject,
            "topic": self.topic,
            "hints": self.hints,
            "explanation": self.explanation
        }


@dataclass
class Mastery:
    """
    掌握度模型 - 单写者策略(仅Assessment Agent写入)
    包含版本号防止并发冲突
    """
    student_id: str
    topic: str
    level: float = 0.0  # 0.0-1.0
    ease_factor: float = 2.5  # SM-2 轻松因子
    interval_days: int = 0  # 当前间隔天数
    repetitions: int = 0  # 重复次数
    version: int = 1  # 版本号
    last_reviewed: Optional[str] = None
    next_review: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "student_id": self.student_id,
            "topic": self.topic,
            "level": self.level,
            "ease_factor": self.ease_factor,
            "interval_days": self.interval_days,
            "repetitions": self.repetitions,
            "version": self.version,
            "last_reviewed": self.last_reviewed,
            "next_review": self.next_review
        }


@dataclass
class Submission:
    """学生答题提交"""
    submission_id: str
    student_id: str
    question_id: str
    answer: str
    is_correct: bool
    time_spent_seconds: int
    attempt_number: int = 1  # 第几次尝试
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "submission_id": self.submission_id,
            "student_id": self.student_id,
            "question_id": self.question_id,
            "answer": self.answer,
            "is_correct": self.is_correct,
            "time_spent_seconds": self.time_spent_seconds,
            "attempt_number": self.attempt_number,
            "timestamp": self.timestamp
        }


@dataclass
class ReviewSchedule:
    """SM-2 复习计划"""
    schedule_id: str
    student_id: str
    topic: str
    scheduled_date: str
    status: str = "pending"  # pending, completed, skipped
    priority: float = 1.0  # 优先级

    def to_dict(self) -> dict:
        return {
            "schedule_id": self.schedule_id,
            "student_id": self.student_id,
            "topic": self.topic,
            "scheduled_date": self.scheduled_date,
            "status": self.status,
            "priority": self.priority
        }
