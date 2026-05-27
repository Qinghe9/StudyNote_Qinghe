"""学生与学习数据模型"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime

@dataclass
class KnowledgePoint:
    id: str
    name: str
    subject: str
    difficulty: float  # 0-1
    prerequisites: List[str] = field(default_factory=list)

@dataclass
class MasteryState:
    knowledge_point_id: str
    p_known: float = 0.3  # BKT: P(L) 掌握概率
    p_learn: float = 0.1  # BKT: P(T) 学习概率
    p_guess: float = 0.2  # BKT: P(G) 猜测概率
    p_slip: float = 0.1   # BKT: P(S) 失误概率
    p_forget: float = 0.05 # 遗忘概率
    attempts: int = 0
    correct_count: int = 0
    last_review: Optional[str] = None
    next_review: Optional[str] = None
    interval_days: int = 1  # SM-2
    ef: float = 2.5  # SM-2: Easiness Factor
    version: int = 0

@dataclass
class StudentProfile:
    id: str
    name: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    mastery: Dict[str, MasteryState] = field(default_factory=dict)
    engagement_score: float = 1.0  # 0-1, 1=highly engaged
    consecutive_errors: int = 0
    total_questions: int = 0
    session_history: List[Dict] = field(default_factory=list)
    current_path: List[str] = field(default_factory=list)
    path_index: int = 0

@dataclass
class Question:
    id: str
    knowledge_point_id: str
    content: str
    options: Optional[List[str]] = None
    correct_answer: str = ""
    explanation: str = ""
    difficulty: float = 0.5
    hint_level1: str = ""
    hint_level2: str = ""
    hint_level3: str = ""
