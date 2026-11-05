from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.app.database import Base, utc_now

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(100), nullable=False) # e.g. "MERGE_COMPLAINT", "OVERRIDE_PRIORITY", "PAUSE_ESCALATION", "UPDATE_CONFIG"
    entity_type = Column(String(50), nullable=False) # "complaint", "user", "scholarship", "system"
    entity_id = Column(String(50), nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=utc_now, index=True)

    actor = relationship("User", foreign_keys=[actor_id])

