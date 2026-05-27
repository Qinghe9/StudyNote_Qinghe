"""FastAPI 主入口 + WebSocket 实时交互"""
import sys
from pathlib import Path
# 确保 backend 目录在 Python 路径中
sys.path.insert(0, str(Path(__file__).parent))

"""FastAPI 主入口 + WebSocket 实时交互"""
import asyncio
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)

# 导入模型和Agent
from models.events import Event, EventType
from models.student import StudentProfile, MasteryState
from event_bus import event_bus
from services.question_bank import QUESTION_BANK, KNOWLEDGE_POINTS
from services.llm import llm_service

from agents.assessment import AssessmentAgent
from agents.curriculum import CurriculumAgent
from agents.tutor import TutorAgent
from agents.engagement import EngagementAgent
from agents.hint import HintAgent

# 内存数据库
students_db: Dict[str, StudentProfile] = {}
active_connections: Dict[str, WebSocket] = {}

# 初始化Agent
assessment_agent = AssessmentAgent(students_db)
curriculum_agent = CurriculumAgent(students_db, QUESTION_BANK)
tutor_agent = TutorAgent(students_db, llm_service)
engagement_agent = EngagementAgent(students_db)
hint_agent = HintAgent(students_db, QUESTION_BANK)

app = FastAPI(
    title="EduMesh - 多Agent智能教育系统",
    description="Mesh + 事件驱动的多Agent教育平台",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ WebSocket 转发器 ============
async def websocket_forwarder(event: Event):
    """将事件总线的事件转发到对应学生的WebSocket连接"""
    ws = active_connections.get(event.student_id)
    if ws:
        try:
            await ws.send_json({
                "type": event.type.value,
                "source": event.source,
                "payload": event.payload,
                "timestamp": event.timestamp
            })
        except Exception as e:
            logger.error(f"WebSocket send error: {e}")

# 订阅所有事件类型，转发到WebSocket
for et in EventType:
    event_bus.subscribe(et, websocket_forwarder)

# ============ API 模型 ============
class StudentCreate(BaseModel):
    name: str

class AnswerSubmit(BaseModel):
    student_id: str
    question_id: str
    answer: str

class ChatMessage(BaseModel):
    student_id: str
    message: str

# ============ REST API ============
@app.get("/")
def root():
    return {"message": "EduMesh API 运行中", "version": "1.0.0"}

@app.post("/api/students")
async def create_student(data: StudentCreate):
    import uuid
    sid = f"stu_{uuid.uuid4().hex[:8]}"
    student = StudentProfile(id=sid, name=data.name)
    students_db[sid] = student

    # 初始化学习路径
    await curriculum_agent._build_learning_path(student)

    logger.info(f"Created student: {sid} - {data.name}")
    return {"student_id": sid, "name": data.name, "message": "学生创建成功"}

@app.get("/api/students/{student_id}")
def get_student(student_id: str):
    student = students_db.get(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")

    return {
        "id": student.id,
        "name": student.name,
        "engagement_score": student.engagement_score,
        "total_questions": student.total_questions,
        "consecutive_errors": student.consecutive_errors,
        "mastery_count": len(student.mastery),
        "current_path": student.current_path,
        "path_index": student.path_index
    }

@app.get("/api/students/{student_id}/mastery")
def get_mastery(student_id: str):
    student = students_db.get(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")

    result = []
    for kpid, m in student.mastery.items():
        kp_info = KNOWLEDGE_POINTS.get(kpid, {"name": kpid, "subject": "未知"})
        result.append({
            "knowledge_point_id": kpid,
            "name": kp_info["name"],
            "subject": kp_info["subject"],
            "p_known": round(m.p_known, 3),
            "attempts": m.attempts,
            "correct_rate": round(m.correct_count / m.attempts, 2) if m.attempts > 0 else 0,
            "interval_days": m.interval_days,
            "ef": round(m.ef, 2),
            "next_review": m.next_review
        })
    return sorted(result, key=lambda x: x["p_known"])

@app.get("/api/questions/next")
def get_next_question(student_id: str):
    student = students_db.get(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")

    question = curriculum_agent.get_next_question(student_id)
    if not question:
        raise HTTPException(status_code=404, detail="暂无可用题目")

    return {
        "question_id": question.id,
        "knowledge_point_id": question.knowledge_point_id,
        "content": question.content,
        "options": question.options,
        "difficulty": question.difficulty,
        "subject": KNOWLEDGE_POINTS.get(question.knowledge_point_id, {}).get("subject", "")
    }

@app.post("/api/answers")
async def submit_answer(data: AnswerSubmit):
    student = students_db.get(data.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")

    question = next((q for q in QUESTION_BANK if q.id == data.question_id), None)
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在")

    is_correct = data.answer.strip() == question.correct_answer.strip()

    # 发布学生提交事件 -> 触发Assessment Agent
    await event_bus.publish(Event(
        type=EventType.STUDENT_SUBMISSION,
        student_id=data.student_id,
        source="API",
        payload={
            "question_id": data.question_id,
            "knowledge_point_id": question.knowledge_point_id,
            "answer": data.answer,
            "is_correct": is_correct
        }
    ))

    # 推进学习路径
    if is_correct:
        curriculum_agent.advance(data.student_id)

    return {
        "correct": is_correct,
        "correct_answer": question.correct_answer,
        "explanation": question.explanation
    }

@app.get("/api/questions")
def list_questions():
    return [
        {
            "id": q.id,
            "knowledge_point_id": q.knowledge_point_id,
            "content": q.content[:50] + "...",
            "difficulty": q.difficulty
        }
        for q in QUESTION_BANK
    ]

@app.get("/api/events/{student_id}")
def get_events(student_id: str, limit: int = 20):
    events = event_bus.get_history(student_id, limit)
    return [
        {
            "type": e.type.value,
            "source": e.source,
            "payload": e.payload,
            "timestamp": e.timestamp
        }
        for e in events
    ]

# ============ WebSocket 实时通信 ============
@app.websocket("/ws/{student_id}")
async def websocket_endpoint(websocket: WebSocket, student_id: str):
    await websocket.accept()
    active_connections[student_id] = websocket
    logger.info(f"WebSocket connected: {student_id}")

    # 发送连接成功消息
    await websocket.send_json({
        "type": "SYSTEM_MESSAGE",
        "source": "System",
        "payload": {"message": "已连接到EduMesh实时学习系统"},
        "timestamp": datetime.now().isoformat()
    })

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "")

            if msg_type == "answer":
                # 通过WebSocket提交答案
                qid = data.get("question_id", "")
                answer = data.get("answer", "")

                question = next((q for q in QUESTION_BANK if q.id == qid), None)
                if question:
                    is_correct = answer.strip() == question.correct_answer.strip()
                    await event_bus.publish(Event(
                        type=EventType.STUDENT_SUBMISSION,
                        student_id=student_id,
                        source="WebSocket",
                        payload={
                            "question_id": qid,
                            "knowledge_point_id": question.knowledge_point_id,
                            "answer": answer,
                            "is_correct": is_correct
                        }
                    ))
                    if is_correct:
                        curriculum_agent.advance(student_id)

            elif msg_type == "chat":
                # 学生发送消息，Tutor Agent处理
                msg = data.get("message", "")
                await websocket.send_json({
                    "type": "TUTOR_RESPONSE",
                    "source": "TutorAgent",
                    "payload": {
                        "type": "chat",
                        "message": f"收到你的消息: '{msg}'。继续加油学习！"
                    },
                    "timestamp": datetime.now().isoformat()
                })

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        active_connections.pop(student_id, None)
        logger.info(f"WebSocket disconnected: {student_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        active_connections.pop(student_id, None)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
