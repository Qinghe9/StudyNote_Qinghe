"""Assessment Agent - 使用BKT模型评估学生掌握度"""
from agents.base import BaseAgent
from models.events import Event, EventType
from models.student import StudentProfile, MasteryState
from typing import Dict
import logging

logger = logging.getLogger(__name__)

class AssessmentAgent(BaseAgent):
    def __init__(self, student_db: Dict[str, StudentProfile]):
        super().__init__("AssessmentAgent")
        self.students = student_db
        self.subscribe(EventType.STUDENT_SUBMISSION)

    async def handle(self, event: Event):
        student_id = event.student_id
        payload = event.payload

        qid = payload.get("question_id")
        kpid = payload.get("knowledge_point_id")
        is_correct = payload.get("is_correct", False)
        answer = payload.get("answer", "")

        student = self.students.get(student_id)
        if not student:
            logger.error(f"Student {student_id} not found")
            return

        # BKT 更新
        mastery = student.mastery.get(kpid)
        if not mastery:
            mastery = MasteryState(knowledge_point_id=kpid)
            student.mastery[kpid] = mastery

        # 贝叶斯更新
        old_p = mastery.p_known
        if is_correct:
            # P(L|Correct) = P(Correct|L) * P(L) / P(Correct)
            p_correct_given_known = 1 - mastery.p_slip
            p_correct_given_unknown = mastery.p_guess
            p_correct = p_correct_given_known * old_p + p_correct_given_unknown * (1 - old_p)
            new_p_known = (p_correct_given_known * old_p) / p_correct if p_correct > 0 else old_p
        else:
            # P(L|Incorrect) = P(Incorrect|L) * P(L) / P(Incorrect)
            p_incorrect_given_known = mastery.p_slip
            p_incorrect_given_unknown = 1 - mastery.p_guess
            p_incorrect = p_incorrect_given_known * old_p + p_incorrect_given_unknown * (1 - old_p)
            new_p_known = (p_incorrect_given_known * old_p) / p_incorrect if p_incorrect > 0 else old_p

        # 学习概率更新 (即使答错也有学习可能)
        new_p_known = new_p_known + (1 - new_p_known) * mastery.p_learn
        mastery.p_known = min(0.99, max(0.01, new_p_known))
        mastery.attempts += 1
        if is_correct:
            mastery.correct_count += 1
            student.consecutive_errors = 0
        else:
            student.consecutive_errors += 1
        mastery.version += 1

        student.total_questions += 1

        self.log(f"Student {student_id} Q{qid}: {'✓' if is_correct else '✗'} | "
                  f"Mastery[{kpid}]: {old_p:.2f} → {mastery.p_known:.2f}")

        # 发布掌握度更新事件
        await self.emit(Event(
            type=EventType.MASTERY_UPDATED,
            student_id=student_id,
            payload={
                "knowledge_point_id": kpid,
                "p_known": mastery.p_known,
                "attempts": mastery.attempts,
                "is_correct": is_correct,
                "consecutive_errors": student.consecutive_errors,
                "version": mastery.version
            }
        ))

        # 发布评估完成事件
        await self.emit(Event(
            type=EventType.ASSESSMENT_COMPLETE,
            student_id=student_id,
            payload={
                "question_id": qid,
                "is_correct": is_correct,
                "answer": answer,
                "mastery": mastery.p_known,
                "consecutive_errors": student.consecutive_errors,
                "needs_hint": student.consecutive_errors >= 2
            }
        ))
