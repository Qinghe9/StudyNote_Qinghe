"""事件定义"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from enum import Enum
from datetime import datetime

class EventType(str, Enum):
    STUDENT_SUBMISSION = "STUDENT_SUBMISSION"
    ASSESSMENT_COMPLETE = "ASSESSMENT_COMPLETE"
    MASTERY_UPDATED = "MASTERY_UPDATED"
    HINT_NEEDED = "HINT_NEEDED"
    HINT_RESPONSE = "HINT_RESPONSE"
    ENGAGEMENT_ALERT = "ENGAGEMENT_ALERT"
    TUTOR_RESPONSE = "TUTOR_RESPONSE"
    CURRICULUM_UPDATED = "CURRICULUM_UPDATED"
    SYSTEM_MESSAGE = "SYSTEM_MESSAGE"

@dataclass
class Event:
    type: EventType
    payload: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    source: str = "system"
    student_id: str = ""
    event_id: str = field(default_factory=lambda: f"evt_{datetime.now().timestamp()}")
