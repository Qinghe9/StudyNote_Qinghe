"""Tutor Agent - 苏格拉底式提问 + 三级提示策略"""
from agents.base import BaseAgent
from models.events import Event, EventType
from models.student import StudentProfile
from typing import Dict
import logging

logger = logging.getLogger(__name__)

class TutorAgent(BaseAgent):
    def __init__(self, student_db: Dict[str, StudentProfile], llm_service=None):
        super().__init__("TutorAgent")
        self.students = student_db
        self.llm = llm_service
        self.subscribe(EventType.ASSESSMENT_COMPLETE)
        self.subscribe(EventType.HINT_RESPONSE)
        self.subscribe(EventType.ENGAGEMENT_ALERT)

    async def handle(self, event: Event):
        student_id = event.student_id
        student = self.students.get(student_id)
        if not student:
            return

        if event.type == EventType.ASSESSMENT_COMPLETE:
            await self._handle_assessment(student, event.payload)
        elif event.type == EventType.HINT_RESPONSE:
            await self._forward_hint(student, event.payload)
        elif event.type == EventType.ENGAGEMENT_ALERT:
            await self._handle_frustration(student, event.payload)

    async def _handle_assessment(self, student: StudentProfile, payload: Dict):
        is_correct = payload["is_correct"]
        qid = payload["question_id"]
        mastery = payload["mastery"]
        needs_hint = payload.get("needs_hint", False)

        if is_correct:
            # 答对了 - 苏格拉底式深化
            if mastery > 0.8:
                msg = self._generate_socratic_deepening(qid)
            else:
                msg = self._generate_encouragement(qid, mastery)
        else:
            if needs_hint:
                # 连续错误，请求提示
                await self.emit(Event(
                    type=EventType.HINT_NEEDED,
                    student_id=student.id,
                    payload={
                        "question_id": qid,
                        "consecutive_errors": payload["consecutive_errors"],
                        "mastery": mastery
                    }
                ))
                return
            else:
                # 普通错误，引导思考
                msg = self._generate_socratic_guidance(qid)

        await self.emit(Event(
            type=EventType.TUTOR_RESPONSE,
            student_id=student.id,
            payload={
                "type": "socratic" if not is_correct else "deepening",
                "message": msg,
                "question_id": qid,
                "mastery": mastery
            }
        ))

    async def _forward_hint(self, student: StudentProfile, payload: Dict):
        hint = payload.get("hint", "")
        level = payload.get("level", 1)
        qid = payload.get("question_id", "")

        # 包装提示为苏格拉底式
        wrapped = self._wrap_hint_socratic(hint, level)

        await self.emit(Event(
            type=EventType.TUTOR_RESPONSE,
            student_id=student.id,
            payload={
                "type": "hint",
                "level": level,
                "message": wrapped,
                "question_id": qid
            }
        ))

    async def _handle_frustration(self, student: StudentProfile, payload: Dict):
        msg = (
            "没关系，学习就是不断尝试的过程。\n"
            "让我们换个角度思考这个问题。\n"
            "你已经很努力了，稍微休息一下，我们降低一点难度继续。"
        )

        await self.emit(Event(
            type=EventType.TUTOR_RESPONSE,
            student_id=student.id,
            payload={
                "type": "engagement",
                "message": msg,
                "action": "reduce_difficulty"
            }
        ))

    def _generate_socratic_guidance(self, qid: str) -> str:
        prompts = [
            "这是一个很好的思考机会。你能告诉我，你觉得这个问题的关键概念是什么？",
            "让我们一步步来。如果把这个大问题拆分成几个小问题，你会从哪里开始？",
            "想象一下你已经知道答案了。反推一下，什么样的思路会带你到正确答案？",
            "你之前的尝试很有价值。哪个部分让你觉得最有把握？哪个部分还有疑问？",
        ]
        import random
        return random.choice(prompts)

    def _generate_socratic_deepening(self, qid: str) -> str:
        prompts = [
            "很好！你已经掌握了基础。那么，如果这个概念应用到更复杂的场景中，你会怎么做？",
            "完全正确！你能用自己的话解释一下为什么这个答案是正确的吗？",
            " excellent! 既然你理解了这一点，你觉得它和之前学过的哪个知识点有联系？",
        ]
        import random
        return random.choice(prompts)

    def _generate_encouragement(self, qid: str, mastery: float) -> str:
        return f"答对了！你的掌握度已经提升到 {mastery*100:.0f}%。继续保持！"

    def _wrap_hint_socratic(self, hint: str, level: int) -> str:
        if level == 1:
            return f"给你一个小线索：{hint}\n\n基于这个线索，你能想到下一步吗？"
        elif level == 2:
            return f"再深入一点：{hint}\n\n试着结合这个信息和你已知的知识。"
        else:
            return f"详细解释：{hint}\n\n理解了吗？我们可以再试一题巩固一下。"
