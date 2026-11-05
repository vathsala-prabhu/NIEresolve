from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.app.database import Base

class NotificationType:
    SUBMISSION = "submission"
    VERIFICATION = "verification"
    ASSIGNMENT = "assignment"
    PRIORITY_CHANGE = "priority_change"
    STATUS_UPDATE = "status_update"
    DUPLICATE_MERGE = "duplicate_merge"
    ESCALATION_WARNING = "escalation_warning"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    CONFIRMATION = "confirmation"
    SCHOLARSHIP = "scholarship"
    GENERAL = "general"

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(String(50), default=NotificationType.GENERAL, index=True)
    is_read = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User", back_populates="notifications")
    complaint = relationship("Complaint")

