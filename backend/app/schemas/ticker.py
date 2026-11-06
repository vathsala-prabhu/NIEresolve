from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

class TickerAnnouncementItem(BaseModel):
    id: int
    title: str = Field(..., description="Announcement headline")
    message: str = Field(..., description="Full or summary text of the update")
    category: str = Field(..., description="Category: Scholarship, Examination, Campus Safety, Infrastructure, Administration")
    publication_date: str = Field(..., description="Formatted date string YYYY-MM-DD or DD MMM YYYY")
    publication_time: str = Field(..., description="Formatted time string HH:MM AM/PM")
    priority: str = Field("Normal", description="Priority level: Critical, High, Normal, Low")
    is_urgent: bool = False
    is_active: bool = True
    destination_route: Optional[str] = Field(None, description="Internal frontend route: scholarships, community, dashboard, escalations")
    destination_url: Optional[str] = Field(None, description="Optional external web portal destination")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TickerAnnouncementCreate(BaseModel):
    title: str
    message: str
    category: str = "General"
    priority: str = "Normal"
    is_urgent: bool = False
    is_active: bool = True
    destination_route: Optional[str] = None
    destination_url: Optional[str] = None

