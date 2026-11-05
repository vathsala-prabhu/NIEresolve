from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.app.database import Base, utc_now

class KnowledgeBaseCategory:
    POLICY = "policy"
    FAQ = "faq"
    DEPARTMENT = "department"
    SCHOLARSHIP = "scholarship"
    NOTICE = "notice"
    CONTACT = "contact"

class KnowledgeBaseItem(Base):
    __tablename__ = "knowledge_base_items"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(50), default=KnowledgeBaseCategory.FAQ, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    keywords = Column(String(500), nullable=True) # Comma-separated search keywords
    source_reference = Column(String(255), nullable=True) # e.g. "NIE Student Handbook 2025-26, Section 4.2"
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_uuid = Column(String(100), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=utc_now)
    
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.created_at.asc()")

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    sender = Column(String(20), nullable=False) # "user" or "bot"
    message = Column(Text, nullable=False)
    context_sources = Column(Text, nullable=True) # Sources retrieved for RAG answer
    created_at = Column(DateTime, default=utc_now)

    session = relationship("ChatSession", back_populates="messages")

