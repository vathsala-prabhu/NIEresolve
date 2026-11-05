from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.app.database import Base, utc_now

class EscalationLog(Base):
    __tablename__ = "escalation_logs"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False)
    from_tier = Column(String(50), nullable=False)
    to_tier = Column(String(50), nullable=False)
    escalation_date = Column(DateTime, default=utc_now, nullable=False)
    reason = Column(Text, nullable=False) # e.g. "Automatic escalation: Unresolved after 15 calendar days at Tier 1"
    automated = Column(Boolean, default=True)
    notified_authorities = Column(Text, nullable=True) # Summary of who was notified
    created_at = Column(DateTime, default=utc_now)

    complaint = relationship("Complaint", back_populates="escalation_logs")

class EscalationConfig(Base):
    __tablename__ = "escalation_configs"

    id = Column(Integer, primary_key=True, index=True)
    tier_name = Column(String(50), unique=True, nullable=False) # tier_1, tier_2
    duration_days = Column(Integer, default=15, nullable=False)
    description = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

