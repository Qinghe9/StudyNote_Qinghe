"""Hint Agent - 三级提示策略"""
from agents.base import BaseAgent
from models.events import Event, EventType
from models.student import StudentProfile, Question
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class HintAgent(BaseAgent):
    def __init__(self, student_db: Dict[str, StudentProfile], question_bank: List[Question]):
        super().__init__("HintAgent")
        self.students = student_db
        self.question_bank = {q.id: q for q in question_bank}
        self.subscribe(EventType.HINT_NEEDED)

    async def handle(self, event: Event):
        student_id = event.student_id
        payload = event.payload
        qid = payload["question_id"]
        consecutive = payload.get("consecutive_errors", 0)

        question = self.question_bank.get(qid)
        if not question:
            logger.error(f"Question {qid} not found")
            return

        # 确定提示级别
        if consecutive == 2:
            level = 1
            hint = question.hint_level1 or "仔细看看题目中的关键词。"
        elif consecutive == 3:
            level = 2
            hint = question.hint_level2 or "回忆一下相关的公式或定义。"
        else:
            level = 3
            hint = question.hint_level3 or question.explanation or "这是详细的解题步骤..."

        self.log(f"Providing level {level} hint for {qid} (consecutive={consecutive})")

        await self.emit(Event(
            type=EventType.HINT_RESPONSE,
            student_id=student_id,
            payload={
                "question_id": qid,
                "level": level,
                "hint": hint,
                "consecutive_errors": consecutive
            }
        ))
