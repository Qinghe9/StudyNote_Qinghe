"""Curriculum Agent - 基于SM-2算法动态调整学习路径"""
from agents.base import BaseAgent
from models.events import Event, EventType
from models.student import StudentProfile, MasteryState, Question
from typing import Dict, List
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class CurriculumAgent(BaseAgent):
    def __init__(self, student_db: Dict[str, StudentProfile], question_bank: List[Question]):
        super().__init__("CurriculumAgent")
        self.students = student_db
        self.question_bank = question_bank
        self.knowledge_points = self._build_kp_map()
        self.subscribe(EventType.MASTERY_UPDATED)
        self.subscribe(EventType.ENGAGEMENT_ALERT)

    def _build_kp_map(self):
        kp_map = {}
        for q in self.question_bank:
            if q.knowledge_point_id not in kp_map:
                kp_map[q.knowledge_point_id] = q
        return kp_map

    async def handle(self, event: Event):
        student_id = event.student_id
        student = self.students.get(student_id)
        if not student:
            return

        if event.type == EventType.MASTERY_UPDATED:
            await self._update_sm2(student, event.payload)
            await self._build_learning_path(student)
        elif event.type == EventType.ENGAGEMENT_ALERT:
            await self._slow_down(student, event.payload)

    async def _update_sm2(self, student: StudentProfile, payload: Dict):
        kpid = payload["knowledge_point_id"]
        is_correct = payload["is_correct"]
        mastery = student.mastery.get(kpid)
        if not mastery:
            return

        # SM-2 算法
        old_ef = mastery.ef
        old_interval = mastery.interval_days

        if is_correct:
            if old_interval == 1:
                mastery.interval_days = 1
            elif old_interval == 2:
                mastery.interval_days = 6
            else:
                mastery.interval_days = int(old_interval * old_ef)
        else:
            mastery.interval_days = 1
            mastery.ef = max(1.3, mastery.ef - 0.8)

        # 更新EF因子
        q = 5 if is_correct else 0  # 质量评分 0-5
        mastery.ef = mastery.ef + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
        mastery.ef = max(1.3, mastery.ef)

        now = datetime.now()
        mastery.last_review = now.isoformat()
        mastery.next_review = (now + timedelta(days=mastery.interval_days)).isoformat()

        self.log(f"SM-2 Update [{kpid}]: EF {old_ef:.2f}→{mastery.ef:.2f}, "
                  f"Interval {old_interval}→{mastery.interval_days}d")

        await self.emit(Event(
            type=EventType.CURRICULUM_UPDATED,
            student_id=student.id,
            payload={
                "knowledge_point_id": kpid,
                "next_review": mastery.next_review,
                "interval_days": mastery.interval_days,
                "ef": mastery.ef,
                "p_known": mastery.p_known
            }
        ))

    async def _build_learning_path(self, student: StudentProfile):
        # 基于掌握度构建学习路径: 优先复习即将遗忘的，然后学习新知识点
        review_queue = []
        new_queue = []

        for kpid, mastery in student.mastery.items():
            if mastery.next_review:
                review_time = datetime.fromisoformat(mastery.next_review)
                if review_time <= datetime.now() + timedelta(days=1):
                    review_queue.append((kpid, mastery.p_known))
            elif mastery.p_known < 0.7:
                new_queue.append((kpid, mastery.p_known))

        # 排序: 掌握度低的优先
        review_queue.sort(key=lambda x: x[1])
        new_queue.sort(key=lambda x: x[1])

        path = [kpid for kpid, _ in review_queue + new_queue]

        # 如果没有知识点，从题库中初始化
        if not path:
            available = [q.knowledge_point_id for q in self.question_bank[:10]]
            path = list(dict.fromkeys(available))  # 去重

        student.current_path = path
        student.path_index = 0

        self.log(f"Built path for {student.id}: {path[:5]}...")

    async def _slow_down(self, student: StudentProfile, payload: Dict):
        # 挫败时放慢节奏: 减少间隔，降低难度
        self.log(f"Slowing down for student {student.id}")
        student.engagement_score = max(0.3, student.engagement_score - 0.1)

        # 调整当前路径，插入简单复习
        if student.current_path:
            current_kp = student.current_path[student.path_index] if student.path_index < len(student.current_path) else None
            if current_kp:
                # 在当前位置重复一次
                student.current_path.insert(student.path_index, current_kp)

        await self.emit(Event(
            type=EventType.CURRICULUM_UPDATED,
            student_id=student.id,
            payload={
                "action": "slow_down",
                "engagement_score": student.engagement_score,
                "message": "已调整学习节奏，降低难度"
            }
        ))

    def get_next_question(self, student_id: str) -> Question:
        student = self.students.get(student_id)
        if not student or not student.current_path:
            return self.question_bank[0] if self.question_bank else None

        if student.path_index >= len(student.current_path):
            student.path_index = 0

        kpid = student.current_path[student.path_index]
        questions = [q for q in self.question_bank if q.knowledge_point_id == kpid]

        if not questions:
            questions = self.question_bank

        # 根据掌握度选择难度
        mastery = student.mastery.get(kpid)
        target_diff = 0.5
        if mastery:
            target_diff = 1 - mastery.p_known  # 掌握度越低，难度应该越低

        # 找最接近目标难度的题
        questions.sort(key=lambda q: abs(q.difficulty - target_diff))
        return questions[0]

    def advance(self, student_id: str):
        student = self.students.get(student_id)
        if student:
            student.path_index = min(student.path_index + 1, len(student.current_path) - 1)
