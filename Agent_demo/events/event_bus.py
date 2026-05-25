"""
Event Bus - 事件驱动架构核心
实现发布-订阅模式，支持Agent间的松耦合通信
"""

from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import json
import uuid


@dataclass
class Event:
    """事件对象"""
    event_type: str
    payload: Dict[str, Any]
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    source: str = "system"
    version: int = 1

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "source": self.source,
            "version": self.version
        }


class EventBus:
    """
    事件总线 - Mesh架构核心
    支持:
    - 发布/订阅
    - 事件持久化(内存)
    - 异步处理
    - 事件溯源
    """

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._event_log: List[Event] = []
        self._agent_registry: Dict[str, Any] = {}
        self._lock = asyncio.Lock()

    def register_agent(self, agent_name: str, agent_instance: Any):
        """注册Agent到Mesh网络"""
        self._agent_registry[agent_name] = agent_instance
        print(f"[Mesh] Agent '{agent_name}' 已注册到网络")

    def get_agent(self, agent_name: str) -> Optional[Any]:
        """从Mesh网络获取Agent"""
        return self._agent_registry.get(agent_name)

    def subscribe(self, event_type: str, handler: Callable):
        """订阅特定事件类型"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        print(f"[EventBus] 新订阅者注册: {event_type} -> {handler.__name__}")

    async def publish(self, event: Event):
        """发布事件到总线"""
        async with self._lock:
            self._event_log.append(event)

        print(f"[EventBus] 事件发布: {event.event_type} (id={event.event_id[:8]}...)")

        # 通知所有订阅者
        handlers = self._subscribers.get(event.event_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(handler(event))
                else:
                    handler(event)
            except Exception as e:
                print(f"[EventBus] 处理事件失败 {event.event_type}: {e}")

    def get_event_log(self, event_type: Optional[str] = None) -> List[Event]:
        """获取事件日志(事件溯源)"""
        if event_type:
            return [e for e in self._event_log if e.event_type == event_type]
        return self._event_log.copy()

    def get_event_stream(self, entity_id: str) -> List[Event]:
        """获取特定实体的完整事件流"""
        return [
            e for e in self._event_log 
            if e.payload.get("student_id") == entity_id or 
               e.payload.get("entity_id") == entity_id
        ]


# 全局事件总线实例
event_bus = EventBus()
