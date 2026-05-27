"""Engagement Agent - 监测学习状态，检测挫败感"""
from agents.base import BaseAgent
from models.events import Event, EventType
from models.student import StudentProfile
from typing import Dict
import logging

logger = logging.getLogger(__name__)

class EngagementAgent(BaseAgent):
    def __init__(self, student_db: Dict[str, StudentProfile]):
        super().__init__("EngagementAgent")
        self.students = student_db
        self.subscribe(EventType.ASSESSMENT_COMPLETE)
        self.subscribe(EventType.TUTOR_RESPONSE)

    async def handle(self, event: Event):
        student_id = event.student_id
        student = self.students.get(student_id)
        if not student:
            return

        if event.type == EventType.ASSESSMENT_COMPLETE:
            await self._analyze_performance(student, event.payload)
        elif event.type == EventType.TUTOR_RESPONSE:
            await self._analyze_interaction(student, event.payload)

    async def _analyze_performance(self, student: StudentProfile, payload: Dict):
        is_correct = payload["is_correct"]
        consecutive = payload.get("consecutive_errors", 0)

        # 计算参与度分数
        if is_correct:
            student.engagement_score = min(1.0, student.engagement_score + 0.05)
        else:
            student.engagement_score = max(0.1, student.engagement_score - 0.1)

        # 挫败检测: 连续错误>=3 或 参与度<0.3
        is_frustrated = consecutive >= 3 or student.engagement_score < 0.3

        if is_frustrated:
            self.log(f"FRUSTRATION DETECTED for {student.id}: "
                      f"consecutive={consecutive}, engagement={student.engagement_score:.2f}")

            await self.emit(Event(
                type=EventType.ENGAGEMENT_ALERT,
                student_id=student.id,
                payload={
                    "alert_type": "frustration",
                    "consecutive_errors": consecutive,
                    "engagement_score": student.engagement_score,
                    "message": "检测到学习挫败，建议降低难度",
                    "action": "reduce_difficulty"
                }
            ))
        else:
            self.log(f"Student {student.id} engagement: {student.engagement_score:.2f}")

    async def _analyze_interaction(self, student: StudentProfile, payload: Dict):
        # 分析交互质量，可以扩展为检测长时间无响应等
        msg_type = payload.get("type", "")
        if msg_type == "hint":
            # 使用提示可能意味着遇到困难
            student.engagement_score = max(0.2, student.engagement_score - 0.05)
