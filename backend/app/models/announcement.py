from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.app.database import Base, utc_now

class InstitutionalAnnouncement(Base):
    __tablename__ = "institutional_announcements"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    category = Column(String(100), default="General", index=True) # Scholarship, Examination, Campus Safety, Placement, Administration
    priority = Column(String(50), default="Normal", index=True) # Critical, High, Normal, Low
    is_urgent = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True, index=True)
    destination_route = Column(String(100), nullable=True) # scholarships, community, dashboard, escalations
    destination_url = Column(String(500), nullable=True)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    published_at = Column(DateTime, default=utc_now)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    author = relationship("User", foreign_keys=[author_id])

