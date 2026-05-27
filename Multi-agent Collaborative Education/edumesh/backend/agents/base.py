"""Agent 基类"""
from abc import ABC, abstractmethod
from typing import Dict, Any
from models.events import Event, EventType
from event_bus import event_bus
import logging

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"agent.{name}")

    def subscribe(self, event_type: EventType):
        event_bus.subscribe(event_type, self.handle)
        self.logger.info(f"Subscribed to {event_type.value}")

    async def emit(self, event: Event):
        event.source = self.name
        await event_bus.publish(event)

    @abstractmethod
    async def handle(self, event: Event):
        pass

    def log(self, msg: str):
        self.logger.info(f"[{self.name}] {msg}")
