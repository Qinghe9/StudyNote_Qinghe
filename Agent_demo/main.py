"""
AI 自适应学习系统 - 主入口
演示完整的事件驱动流程
"""

import asyncio
import uuid
from datetime import datetime

from events.event_bus import event_bus, Event
from models.schemas import Student
from database.memory_db import db
from agents.core_agents import (
    AssessmentAgent, CurriculumAgent, TutorAgent, 
    HintAgent, EngagementAgent, ParentNotificationAgent
)


class AdaptiveLearningSystem:
    """自适应学习系统主控"""

    def __init__(self):
        self.system_name = "AI Adaptive Learning System"
        self.version = "1.0.0"

        # 初始化所有 Agents (Mesh网络自动注册)
        print("\n" + "="*60)
        print(f"🚀 初始化 {self.system_name} v{self.version}")
        print("="*60 + "\n")

        self.assessment_agent = AssessmentAgent()
        self.curriculum_agent = CurriculumAgent()
        self.tutor_agent = TutorAgent()
        self.hint_agent = HintAgent()
        self.engagement_agent = EngagementAgent()
        self.parent_agent = ParentNotificationAgent()

        print("\n" + "="*60)
        print("✅ 所有 Agent 已注册到 Mesh 网络")
        print("="*60 + "\n")

    async def register_student(self, name: str) -> str:
        """注册新学生"""
        student_id = f"student_{uuid.uuid4().hex[:8]}"
        student = Student(student_id=student_id, name=name)
        db.create_student(student)

        await event_bus.publish(Event(
            event_type="STUDENT_CREATED",
            payload=student.to_dict(),
            source="System"
        ))

        print(f"[System] 学生注册成功: {name} (ID: {student_id})")
        return student_id

    async def submit_answer(self, student_id: str, question_id: str, 
                           answer: str, time_spent: int = 60):
        """
        学生提交答案 - 触发核心事件流:
        STUDENT_SUBMISSION -> Assessment Agent -> MASTERY_UPDATED -> 
        Curriculum Agent -> ASSESSMENT_COMPLETE -> Tutor Agent -> 
        Engagement Agent (并行)
        """
        print(f"\n{'─'*60}")
        print(f"📤 学生提交答案: {student_id} -> 题目{question_id}")
        print(f"{'─'*60}")

        await event_bus.publish(Event(
            event_type="STUDENT_SUBMISSION",
            payload={
                "student_id": student_id,
                "question_id": question_id,
                "answer": answer,
                "time_spent_seconds": time_spent,
                "timestamp": datetime.now().isoformat()
            },
            source="Student"
        ))

        # 等待事件处理完成
        await asyncio.sleep(0.5)

    async def get_student_status(self, student_id: str) -> dict:
        """获取学生学习状态"""
        student = db.get_student(student_id)
        if not student:
            return {"error": "学生不存在"}

        mastery_list = db.get_student_mastery(student_id)
        submissions = db.get_submissions(student_id)
        schedules = db.get_schedules(student_id)

        return {
            "student": student.to_dict(),
            "mastery": [m.to_dict() for m in mastery_list],
            "submissions_count": len(submissions),
            "recent_submissions": [s.to_dict() for s in submissions[-5:]],
            "schedules": [s.to_dict() for s in schedules[-5:]],
            "event_log_count": len(event_bus.get_event_log())
        }

    def get_system_events(self) -> list:
        """获取系统事件日志(事件溯源)"""
        events = event_bus.get_event_log()
        return [e.to_dict() for e in events]

    def get_mesh_status(self) -> dict:
        """获取 Mesh 网络状态"""
        return {
            "registered_agents": list(event_bus._agent_registry.keys()),
            "event_types": list(event_bus._subscribers.keys()),
            "total_events": len(event_bus._event_log)
        }


async def demo():
    """演示完整的学习流程"""

    # 初始化系统
    system = AdaptiveLearningSystem()

    # 注册学生
    student_id = await system.register_student("小明")

    print("\n" + "="*60)
    print("📝 场景1: 正常答题流程")
    print("="*60)

    # 场景1: 正常答题
    await system.submit_answer(student_id, "q1", "3", time_spent=30)
    await system.submit_answer(student_id, "q2", "25", time_spent=25)
    await system.submit_answer(student_id, "q3", "3x²", time_spent=45)

    print("\n" + "="*60)
    print("📝 场景2: 连续答错触发提示系统")
    print("="*60)

    # 场景2: 连续答错 (触发 HINT_NEEDED)
    await system.submit_answer(student_id, "q5", "2x", time_spent=120)
    await system.submit_answer(student_id, "q5", "2x²", time_spent=90)
    await system.submit_answer(student_id, "q5", "x² + C", time_spent=60)

    print("\n" + "="*60)
    print("📝 场景3: 挫败感检测与难度调整")
    print("="*60)

    # 场景3: 挫败感检测
    await system.submit_answer(student_id, "q4", "[0,1,2]", time_spent=100)
    await system.submit_answer(student_id, "q4", "[0,2]", time_spent=80)

    # 等待所有事件处理完成
    await asyncio.sleep(1)

    # 显示学生状态
    print("\n" + "="*60)
    print("📊 学生学习状态报告")
    print("="*60)

    status = await system.get_student_status(student_id)
    student = status["student"]

    print(f"\n👤 学生: {student['name']}")
    print(f"📈 总尝试: {student['total_attempts']}")
    print(f"✅ 正确数: {student['correct_attempts']}")
    print(f"📊 正确率: {student['correct_attempts']/max(student['total_attempts'],1)*100:.1f}%")
    print(f"😰 挫败感: {student['frustration_level']:.2f}")
    print(f"🎯 参与度: {student['engagement_score']:.2f}")
    print(f"⚙️ 当前难度: {student['current_difficulty']}")

    print(f"\n📚 掌握度:")
    for m in status["mastery"]:
        bar = "█" * int(m["level"] * 10) + "░" * (10 - int(m["level"] * 10))
        print(f"   {m['topic']:12s} [{bar}] {m['level']*100:.0f}% (EF:{m['ease_factor']:.2f})")

    print(f"\n📅 复习计划:")
    for s in status["schedules"][-3:]:
        print(f"   {s['topic']:12s} 计划: {s['scheduled_date'][:10]} 优先级: {s['priority']:.2f}")

    # 显示 Mesh 网络状态
    print("\n" + "="*60)
    print("🌐 Mesh 网络状态")
    print("="*60)
    mesh = system.get_mesh_status()
    print(f"\n已注册 Agents: {', '.join(mesh['registered_agents'])}")
    print(f"事件类型: {', '.join(mesh['event_types'])}")
    print(f"总事件数: {mesh['total_events']}")

    # 显示事件日志
    print("\n" + "="*60)
    print("📋 事件溯源日志 (最近10条)")
    print("="*60)

    events = system.get_system_events()[-10:]
    for i, e in enumerate(events, 1):
        print(f"\n{i}. [{e['timestamp'][11:19]}] {e['event_type']}")
        print(f"   来源: {e['source']} | ID: {e['event_id'][:8]}...")
        payload_summary = str(e['payload'])[:80] + "..." if len(str(e['payload'])) > 80 else str(e['payload'])
        print(f"   数据: {payload_summary}")

    print("\n" + "="*60)
    print("✅ 演示完成!")
    print("="*60)

    return system, student_id


if __name__ == "__main__":
    asyncio.run(demo())
