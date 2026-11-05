from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

class ChatQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    session_uuid: Optional[str] = None

class ChatQueryResponse(BaseModel):
    session_uuid: str
    response: str
    sources: List[str] = []
    is_live_data: bool = False
    context_type: Optional[str] = None # e.g. "complaint_status", "scholarship_info", "institutional_policy"
    created_at: datetime

class KnowledgeBaseCreate(BaseModel):
    category: str
    title: str
    content: str
    keywords: Optional[str] = None
    source_reference: Optional[str] = None

class KnowledgeBaseResponse(BaseModel):
    id: int
    category: str
    title: str
    content: str
    keywords: Optional[str] = None
    source_reference: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

