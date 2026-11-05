from typing import List, Dict, Any
from pydantic import BaseModel

class OverviewStats(BaseModel):
    total_complaints: int
    pending_complaints: int
    under_investigation: int
    resolved_complaints: int
    escalated_complaints: int
    tier1_count: int
    tier2_count: int
    tier3_count: int
    overdue_count: int
    approaching_deadline_count: int
    duplicates_detected: int
    average_resolution_days: float

class KeyValueStat(BaseModel):
    label: str
    count: int
    percentage: float

class DepartmentEscalationStat(BaseModel):
    department_name: str
    department_code: str
    total_complaints: int
    tier1_count: int
    tier2_count: int
    tier3_count: int
    resolved_count: int

class TrendStat(BaseModel):
    month: str
    submitted: int
    resolved: int
    escalated: int

class AnalyticsDashboardResponse(BaseModel):
    overview: OverviewStats
    by_category: List[KeyValueStat]
    by_department: List[KeyValueStat]
    by_priority: List[KeyValueStat]
    by_status: List[KeyValueStat]
    department_escalations: List[DepartmentEscalationStat]
    monthly_trends: List[TrendStat]

