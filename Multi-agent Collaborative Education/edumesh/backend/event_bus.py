"""Mesh 事件总线 - 支持发布/订阅和双向异步通信"""
import asyncio
from typing import Dict, List, Callable, Awaitable
from models.events import Event, EventType
import logging

logger = logging.getLogger(__name__)

class EventBus:
    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable[[Event], Awaitable[None]]]] = {et: [] for et in EventType}
        self._history: List[Event] = []
        self._max_history = 1000
        self._lock = asyncio.Lock()

    def subscribe(self, event_type: EventType, handler: Callable[[Event], Awaitable[None]]):
        self._subscribers[event_type].append(handler)
        logger.info(f"[EventBus] {handler.__qualname__} subscribed to {event_type.value}")

    async def publish(self, event: Event):
        async with self._lock:
            self._history.append(event)
            if len(self._history) > self._max_history:
                self._history.pop(0)

        logger.info(f"[EventBus] Publishing {event.type.value} from {event.source}")
        handlers = self._subscribers.get(event.type, [])
        if not handlers:
            logger.warning(f"[EventBus] No handlers for {event.type.value}")
            return

        # 并行触发所有订阅者 (Mesh特性)
        tasks = [self._safe_call(h, event) for h in handlers]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _safe_call(self, handler, event):
        try:
            await handler(event)
        except Exception as e:
            logger.error(f"[EventBus] Handler {handler.__qualname__} error: {e}")

    def get_history(self, student_id: str = None, limit: int = 50) -> List[Event]:
        events = self._history
        if student_id:
            events = [e for e in events if e.student_id == student_id]
        return events[-limit:]

# 全局事件总线实例
event_bus = EventBus()
