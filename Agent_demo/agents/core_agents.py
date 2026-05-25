"""
AI Agents - 自适应学习系统的核心智能体
包含: Assessment Agent, Tutor Agent, Curriculum Agent, Engagement Agent, Hint Agent
"""

import asyncio
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from events.event_bus import Event, event_bus
from models.schemas import Student, Question, Mastery, Submission, ReviewSchedule
from models.sm2 import SM2Algorithm
from database.memory_db import db


class BaseAgent:
    """Agent 基类"""

    def __init__(self, name: str):
        self.name = name
        self.event_bus = event_bus
        # 注册到 Mesh 网络
        event_bus.register_agent(name, self)

    async def emit(self, event_type: str, payload: Dict[str, Any], source: str = None):
        """发送事件"""
        event = Event(
            event_type=event_type,
            payload=payload,
            source=source or self.name
        )
        await self.event_bus.publish(event)


class AssessmentAgent(BaseAgent):
    """
    评估 Agent - 单写者
    职责:
    - 评估学生答题正确性
    - 更新掌握度 (唯一写入者)
    - 触发 MASTERY_UPDATED 事件
    """

    def __init__(self):
        super().__init__("AssessmentAgent")
        # 订阅学生提交事件
        self.event_bus.subscribe("STUDENT_SUBMISSION", self.handle_submission)

    async def handle_submission(self, event: Event):
        """处理学生答题提交"""
        payload = event.payload
        student_id = payload["student_id"]
        question_id = payload["question_id"]
        answer = payload["answer"]
        time_spent = payload.get("time_spent_seconds", 60)

        student = db.get_student(student_id)
        question = db.get_question(question_id)

        if not student or not question:
            return

        # 评估正确性
        is_correct = self._evaluate_answer(answer, question.correct_answer)

        # 记录提交
        submission = Submission(
            submission_id=str(uuid.uuid4()),
            student_id=student_id,
            question_id=question_id,
            answer=answer,
            is_correct=is_correct,
            time_spent_seconds=time_spent,
            attempt_number=len(db.get_submissions_for_question(student_id, question_id)) + 1
        )
        db.add_submission(submission)

        # 更新学生统计
        student.total_attempts += 1
        if is_correct:
            student.correct_attempts += 1
        db.update_student(student)

        # 计算质量评分
        quality = SM2Algorithm.get_quality_from_correctness(
            is_correct, time_spent
        )

        # 更新掌握度 (单写者)
        mastery = db.get_mastery(student_id, question.topic)
        if not mastery:
            mastery = Mastery(
                student_id=student_id,
                topic=question.topic,
                ease_factor=2.5,
                interval_days=0,
                repetitions=0
            )

        updated_mastery = SM2Algorithm.calculate_next_review(mastery, quality)
        db.set_mastery(updated_mastery)

        # 发布评估完成事件
        await self.emit("MASTERY_UPDATED", {
            "student_id": student_id,
            "topic": question.topic,
            "mastery": updated_mastery.to_dict(),
            "submission": submission.to_dict(),
            "quality": quality,
            "is_correct": is_correct
        })

        await self.emit("ASSESSMENT_COMPLETE", {
            "student_id": student_id,
            "question_id": question_id,
            "is_correct": is_correct,
            "quality": quality,
            "submission_id": submission.submission_id
        })

        print(f"[AssessmentAgent] 评估完成: 学生{student_id} 题目{question_id} 正确={is_correct} 质量={quality}")

    def _evaluate_answer(self, user_answer: str, correct_answer: str) -> bool:
        """评估答案"""
        return user_answer.strip().lower() == correct_answer.strip().lower()


class CurriculumAgent(BaseAgent):
    """
    课程 Agent
    职责:
    - 维护 SM-2 复习计划
    - 根据掌握度推荐题目
    - 调整学习路径
    """

    def __init__(self):
        super().__init__("CurriculumAgent")
        self.event_bus.subscribe("MASTERY_UPDATED", self.handle_mastery_update)
        self.event_bus.subscribe("ENGAGEMENT_ALERT", self.handle_engagement_alert)

    async def handle_mastery_update(self, event: Event):
        """处理掌握度更新 - 更新复习计划"""
        payload = event.payload
        student_id = payload["student_id"]
        topic = payload["topic"]
        mastery_data = payload["mastery"]

        # 创建/更新复习计划
        schedule = ReviewSchedule(
            schedule_id=str(uuid.uuid4()),
            student_id=student_id,
            topic=topic,
            scheduled_date=mastery_data["next_review"],
            status="pending",
            priority=1.0 - mastery_data["level"]  # 掌握度越低优先级越高
        )
        db.add_schedule(schedule)

        # 推荐下一题
        recommendation = self._recommend_next_question(student_id)

        await self.emit("RECOMMENDATION_READY", {
            "student_id": student_id,
            "recommended_question": recommendation,
            "schedule": schedule.to_dict()
        })

        print(f"[CurriculumAgent] 复习计划已更新: 学生{student_id} 主题'{topic}' 下次复习{mastery_data['next_review'][:10]}")

    async def handle_engagement_alert(self, event: Event):
        """处理参与度告警 - 放慢节奏/降低难度"""
        payload = event.payload
        student_id = payload["student_id"]

        student = db.get_student(student_id)
        if student:
            # 降低难度
            if student.current_difficulty == "hard":
                student.current_difficulty = "medium"
            elif student.current_difficulty == "medium":
                student.current_difficulty = "easy"
            db.update_student(student)

            await self.emit("DIFFICULTY_ADJUSTED", {
                "student_id": student_id,
                "new_difficulty": student.current_difficulty,
                "reason": "frustration_detected"
            })

            print(f"[CurriculumAgent] 难度已降低: 学生{student_id} -> {student.current_difficulty}")

    def _recommend_next_question(self, student_id: str) -> Optional[Dict]:
        """推荐下一道题目"""
        student = db.get_student(student_id)
        if not student:
            return None

        # 获取当前难度的题目
        questions = db.get_questions_by_difficulty(student.current_difficulty)

        # 优先推荐掌握度低且到复习时间的主题
        mastery_list = db.get_student_mastery(student_id)
        due_topics = [
            m.topic for m in mastery_list 
            if SM2Algorithm.is_due_for_review(m)
        ]

        # 如果有到期复习的主题，优先推荐
        if due_topics:
            for topic in due_topics:
                topic_questions = db.get_questions_by_topic(topic)
                if topic_questions:
                    q = topic_questions[0]
                    return q.to_dict()

        # 否则推荐当前难度的题目
        if questions:
            import random
            q = random.choice(questions)
            return q.to_dict()

        return None

    def get_review_schedule(self, student_id: str) -> List[Dict]:
        """获取学生的复习计划"""
        schedules = db.get_schedules(student_id)
        return [s.to_dict() for s in schedules]


class TutorAgent(BaseAgent):
    """
    导师 Agent
    职责:
    - 生成苏格拉底式回复
    - 提供个性化反馈
    - 检测学生是否需要提示
    """

    def __init__(self):
        super().__init__("TutorAgent")
        self.event_bus.subscribe("ASSESSMENT_COMPLETE", self.handle_assessment_complete)
        self.event_bus.subscribe("HINT_NEEDED", self.handle_hint_needed)

    async def handle_assessment_complete(self, event: Event):
        """处理评估完成 - 生成反馈"""
        payload = event.payload
        student_id = payload["student_id"]
        question_id = payload["question_id"]
        is_correct = payload["is_correct"]
        quality = payload["quality"]

        student = db.get_student(student_id)
        question = db.get_question(question_id)

        if not student or not question:
            return

        # 生成苏格拉底式回复
        feedback = self._generate_socratic_feedback(
            student, question, is_correct, quality
        )

        # 检测是否需要提示 (连续答错>=2次)
        submissions = db.get_submissions_for_question(student_id, question_id)
        consecutive_wrong = sum(1 for s in submissions[-3:] if not s.is_correct)

        if consecutive_wrong >= 2 and not is_correct:
            await self.emit("HINT_NEEDED", {
                "student_id": student_id,
                "question_id": question_id,
                "attempt_count": len(submissions),
                "context": feedback
            })

        await self.emit("TUTOR_RESPONSE", {
            "student_id": student_id,
            "question_id": question_id,
            "feedback": feedback,
            "is_correct": is_correct,
            "style": student.learning_style
        })

        print(f"[TutorAgent] 反馈已生成: 学生{student_id} 正确={is_correct}")

    async def handle_hint_needed(self, event: Event):
        """处理提示请求 - 转发给 Hint Agent"""
        payload = event.payload
        # Tutor Agent 转发事件，实际处理由 Hint Agent 完成
        print(f"[TutorAgent] 提示请求已转发: 学生{payload['student_id']}")

    def _generate_socratic_feedback(
        self, student: Student, question: Question, 
        is_correct: bool, quality: int
    ) -> str:
        """生成苏格拉底式反馈"""
        if is_correct:
            if quality >= 4:
                return f"🎉 太棒了！你不仅答对了，而且速度很快。你能解释一下你的思路吗？这样我可以确认你真正理解了这个概念。"
            else:
                return f"✅ 答案正确！不过你花了较长时间，我们来看看是否有更高效的方法？"
        else:
            # 苏格拉底式引导
            return f"🤔 这个答案不太对。让我们一步步思考：{question.content}\n\n你能告诉我，第一步应该做什么？"


class HintAgent(BaseAgent):
    """
    提示 Agent
    职责:
    - 提供分级提示 (1/2/3级)
    - 根据尝试次数决定提示级别
    """

    def __init__(self):
        super().__init__("HintAgent")
        self.event_bus.subscribe("HINT_NEEDED", self.handle_hint_needed)

    async def handle_hint_needed(self, event: Event):
        """处理提示请求"""
        payload = event.payload
        student_id = payload["student_id"]
        question_id = payload["question_id"]
        attempt_count = payload["attempt_count"]

        question = db.get_question(question_id)
        if not question:
            return

        # 决定提示级别
        hint_level = min(attempt_count - 1, len(question.hints))
        hint_level = max(1, min(hint_level, 3))  # 限制在1-3

        # 获取对应级别的提示
        hint_index = min(hint_level - 1, len(question.hints) - 1)
        hint_text = question.hints[hint_index] if question.hints else "再仔细思考一下..."

        await self.emit("HINT_RESPONSE", {
            "student_id": student_id,
            "question_id": question_id,
            "hint_level": hint_level,
            "hint_text": hint_text,
            "total_hints": len(question.hints)
        })

        print(f"[HintAgent] 提示已生成: 学生{student_id} 级别{hint_level}")


class EngagementAgent(BaseAgent):
    """
    参与度 Agent
    职责:
    - 分析学习状态
    - 检测挫败感
    - 触发参与度告警
    """

    def __init__(self):
        super().__init__("EngagementAgent")
        self.event_bus.subscribe("ASSESSMENT_COMPLETE", self.handle_assessment_complete)

    async def handle_assessment_complete(self, event: Event):
        """分析学习状态"""
        payload = event.payload
        student_id = payload["student_id"]
        is_correct = payload["is_correct"]

        student = db.get_student(student_id)
        if not student:
            return

        # 计算挫败感指标
        submissions = db.get_submissions(student_id)
        recent = submissions[-5:] if len(submissions) >= 5 else submissions

        if len(recent) >= 3:
            wrong_count = sum(1 for s in recent if not s.is_correct)
            wrong_ratio = wrong_count / len(recent)

            # 更新挫败感
            student.frustration_level = min(1.0, wrong_ratio * 1.5)

            # 更新参与度
            if wrong_ratio > 0.6:
                student.engagement_score = max(0.3, student.engagement_score - 0.1)
            elif is_correct:
                student.engagement_score = min(1.0, student.engagement_score + 0.05)

            db.update_student(student)

            # 检测挫败感告警
            if student.frustration_level > 0.7:
                await self.emit("ENGAGEMENT_ALERT", {
                    "student_id": student_id,
                    "alert_type": "frustration",
                    "frustration_level": student.frustration_level,
                    "engagement_score": student.engagement_score,
                    "message": "检测到学生挫败感较高，建议降低难度"
                })
                print(f"[EngagementAgent] ⚠️ 挫败感告警: 学生{student_id} 挫败感{student.frustration_level:.2f}")


class ParentNotificationAgent(BaseAgent):
    """
    家长通知 Agent - 演示开闭原则
    新增Agent无需修改任何现有代码
    """

    def __init__(self):
        super().__init__("ParentNotificationAgent")
        self.event_bus.subscribe("ENGAGEMENT_ALERT", self.handle_alert)
        self.event_bus.subscribe("MASTERY_UPDATED", self.handle_mastery)

    async def handle_alert(self, event: Event):
        """处理告警事件"""
        payload = event.payload
        print(f"[ParentNotificationAgent] 📱 家长通知: 学生{payload['student_id']} {payload['message']}")

    async def handle_mastery(self, event: Event):
        """处理掌握度更新"""
        payload = event.payload
        mastery = payload["mastery"]
        if mastery["level"] > 0.8:
            print(f"[ParentNotificationAgent] 📱 家长通知: 学生{payload['student_id']} 已掌握 '{payload['topic']}'!")
