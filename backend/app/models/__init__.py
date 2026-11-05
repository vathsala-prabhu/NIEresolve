from backend.app.database import Base
from backend.app.models.user import User, UserRole, Department, StudentProfile, FacultyProfile
from backend.app.models.complaint import (
    Complaint,
    ComplaintStatus,
    ComplaintTier,
    ComplaintPriority,
    ComplaintCategory,
    ComplaintEvidence,
    ComplaintLocation,
    ComplaintTimeline,
)
from backend.app.models.escalation import EscalationLog, EscalationConfig
from backend.app.models.notification import Notification, NotificationType
from backend.app.models.scholarship import Scholarship, ScholarshipRecommendation
from backend.app.models.chatbot import KnowledgeBaseItem, KnowledgeBaseCategory, ChatSession, ChatMessage
from backend.app.models.audit import AuditLog

__all__ = [
    "Base",
    "User",
    "UserRole",
    "Department",
    "StudentProfile",
    "FacultyProfile",
    "Complaint",
    "ComplaintStatus",
    "ComplaintTier",
    "ComplaintPriority",
    "ComplaintCategory",
    "ComplaintEvidence",
    "ComplaintLocation",
    "ComplaintTimeline",
    "EscalationLog",
    "EscalationConfig",
    "Notification",
    "NotificationType",
    "Scholarship",
    "ScholarshipRecommendation",
    "KnowledgeBaseItem",
    "KnowledgeBaseCategory",
    "ChatSession",
    "ChatMessage",
    "AuditLog",
]

