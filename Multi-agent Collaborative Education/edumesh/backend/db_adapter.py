"""数据库适配层 - 将内存 students_db 替换为 PostgreSQL/SQLite"""
from typing import Dict, Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from db_models import SessionLocal, StudentDB, MasteryDB, QuestionDB, EventLogDB, init_db
from models.student import StudentProfile, MasteryState, Question
from models.events import Event

class DatabaseStore:
    def __init__(self):
        init_db()
        self._local_cache: Dict[str, StudentProfile] = {}  # 内存缓存，减少DB查询

    def _get_db(self) -> Session:
        return SessionLocal()

    # ===== Student 操作 =====
    def get_student(self, student_id: str) -> Optional[StudentProfile]:
        # 先查缓存
        if student_id in self._local_cache:
            return self._local_cache[student_id]

        db = self._get_db()
        try:
            row = db.query(StudentDB).filter(StudentDB.id == student_id).first()
            if not row:
                return None

            # 加载掌握度
            mastery_rows = db.query(MasteryDB).filter(MasteryDB.student_id == student_id).all()
            mastery = {}
            for m in mastery_rows:
                mastery[m.knowledge_point_id] = MasteryState(
                    knowledge_point_id=m.knowledge_point_id,
                    p_known=m.p_known,
                    p_learn=m.p_learn,
                    p_guess=m.p_guess,
                    p_slip=m.p_slip,
                    p_forget=m.p_forget,
                    attempts=m.attempts,
                    correct_count=m.correct_count,
                    last_review=m.last_review.isoformat() if m.last_review else None,
                    next_review=m.next_review.isoformat() if m.next_review else None,
                    interval_days=m.interval_days,
                    ef=m.ef,
                    version=m.version
                )

            student = StudentProfile(
                id=row.id,
                name=row.name,
                created_at=row.created_at.isoformat(),
                mastery=mastery,
                engagement_score=row.engagement_score,
                consecutive_errors=row.consecutive_errors,
                total_questions=row.total_questions,
                session_history=row.session_history or [],
                current_path=row.current_path or [],
                path_index=row.path_index
            )
            self._local_cache[student_id] = student
            return student
        finally:
            db.close()

    def save_student(self, student: StudentProfile):
        db = self._get_db()
        try:
            row = db.query(StudentDB).filter(StudentDB.id == student.id).first()
            if not row:
                row = StudentDB(id=student.id)
                db.add(row)

            row.name = student.name
            row.engagement_score = student.engagement_score
            row.consecutive_errors = student.consecutive_errors
            row.total_questions = student.total_questions
            row.current_path = student.current_path
            row.path_index = student.path_index
            row.session_history = student.session_history

            # 保存掌握度
            for kpid, m in student.mastery.items():
                m_row = db.query(MasteryDB).filter(
                    MasteryDB.student_id == student.id,
                    MasteryDB.knowledge_point_id == kpid
                ).first()

                if not m_row:
                    m_row = MasteryDB(
                        id=f"{student.id}:{kpid}",
                        student_id=student.id,
                        knowledge_point_id=kpid
                    )
                    db.add(m_row)

                m_row.p_known = m.p_known
                m_row.p_learn = m.p_learn
                m_row.p_guess = m.p_guess
                m_row.p_slip = m.p_slip
                m_row.p_forget = m.p_forget
                m_row.attempts = m.attempts
                m_row.correct_count = m.correct_count
                m_row.interval_days = m.interval_days
                m_row.ef = m.ef
                m_row.version = m.version

                if m.last_review:
                    m_row.last_review = datetime.fromisoformat(m.last_review)
                if m.next_review:
                    m_row.next_review = datetime.fromisoformat(m.next_review)

            db.commit()
            self._local_cache[student.id] = student
        finally:
            db.close()

    def delete_student(self, student_id: str):
        db = self._get_db()
        try:
            db.query(MasteryDB).filter(MasteryDB.student_id == student_id).delete()
            db.query(StudentDB).filter(StudentDB.id == student_id).delete()
            db.commit()
            self._local_cache.pop(student_id, None)
        finally:
            db.close()

    # ===== Question 操作 =====
    def load_questions(self) -> List[Question]:
        db = self._get_db()
        try:
            rows = db.query(QuestionDB).all()
            return [
                Question(
                    id=r.id,
                    knowledge_point_id=r.knowledge_point_id,
                    content=r.content,
                    options=r.options,
                    correct_answer=r.correct_answer,
                    explanation=r.explanation,
                    difficulty=r.difficulty,
                    hint_level1=r.hint_level1,
                    hint_level2=r.hint_level2,
                    hint_level3=r.hint_level3
                )
                for r in rows
            ]
        finally:
            db.close()

    def save_question(self, q: Question):
        db = self._get_db()
        try:
            row = db.query(QuestionDB).filter(QuestionDB.id == q.id).first()
            if not row:
                row = QuestionDB(id=q.id)
                db.add(row)

            row.knowledge_point_id = q.knowledge_point_id
            row.content = q.content
            row.options = q.options
            row.correct_answer = q.correct_answer
            row.explanation = q.explanation
            row.difficulty = q.difficulty
            row.hint_level1 = q.hint_level1
            row.hint_level2 = q.hint_level2
            row.hint_level3 = q.hint_level3

            db.commit()
        finally:
            db.close()

    # ===== Event Log =====
    def log_event(self, event: Event):
        db = self._get_db()
        try:
            row = EventLogDB(
                id=event.event_id,
                event_type=event.type.value,
                student_id=event.student_id,
                source=event.source,
                payload=event.payload
            )
            db.add(row)
            db.commit()
        finally:
            db.close()

    def get_events(self, student_id: str, limit: int = 50) -> List[dict]:
        db = self._get_db()
        try:
            rows = db.query(EventLogDB).filter(
                EventLogDB.student_id == student_id
            ).order_by(EventLogDB.created_at.desc()).limit(limit).all()

            return [
                {
                    "type": r.event_type,
                    "source": r.source,
                    "payload": r.payload,
                    "timestamp": r.created_at.isoformat()
                }
                for r in rows
            ]
        finally:
            db.close()

# 全局实例
db_store = DatabaseStore()
