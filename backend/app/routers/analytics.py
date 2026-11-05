from datetime import datetime
from collections import defaultdict
from typing import Dict, Any, List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.database import get_db, utc_now
from backend.app.models.complaint import Complaint, ComplaintStatus, ComplaintTier, ComplaintPriority
from backend.app.models.user import Department, User, UserRole
from backend.app.schemas.analytics import AnalyticsDashboardResponse, OverviewStats, KeyValueStat, DepartmentEscalationStat, TrendStat
from backend.app.auth.dependencies import require_any_officer

router = APIRouter(prefix="/api/analytics", tags=["Institutional Analytics & Reporting"])

@router.get("/overview", response_model=AnalyticsDashboardResponse)
def get_analytics_overview(
    current_user: User = Depends(require_any_officer),
    db: Session = Depends(get_db),
):
    """
    Computes institution-wide grievance analytics derived directly from live database records:
    - Overview metrics
    - Category breakdown
    - Department breakdown
    - Priority distribution
    - Status breakdown
    - Department escalation status
    - Monthly trends
    """
    now = utc_now()
    all_complaints = db.query(Complaint).all()
    total = len(all_complaints)

    resolved = [c for c in all_complaints if c.status in [ComplaintStatus.RESOLVED, ComplaintStatus.CLOSED]]
    pending = [c for c in all_complaints if c.status not in [ComplaintStatus.RESOLVED, ComplaintStatus.CLOSED]]
    investigating = [c for c in all_complaints if c.status == ComplaintStatus.UNDER_INVESTIGATION]
    duplicates = [c for c in all_complaints if c.is_duplicate]

    t1_count = sum(1 for c in pending if c.current_tier == ComplaintTier.TIER_1)
    t2_count = sum(1 for c in pending if c.current_tier == ComplaintTier.TIER_2)
    t3_count = sum(1 for c in pending if c.current_tier == ComplaintTier.TIER_3)
    escalated_total = t2_count + t3_count

    # Overdue and Approaching deadline
    overdue_count = 0
    approaching_count = 0
    for c in pending:
        if c.expected_deadline and not c.is_escalation_paused:
            diff = (c.expected_deadline - now).total_seconds() / 86400.0
            if diff < 0:
                overdue_count += 1
            elif diff <= 3.0:
                approaching_count += 1

    # Average resolution days
    if resolved:
        total_res_days = sum((r.resolution_date - r.submission_date).total_seconds() / 86400.0 for r in resolved if r.resolution_date)
        avg_res_days = round(total_res_days / len(resolved), 1)
    else:
        avg_res_days = 0.0

    overview = OverviewStats(
        total_complaints=total,
        pending_complaints=len(pending),
        under_investigation=len(investigating),
        resolved_complaints=len(resolved),
        escalated_complaints=escalated_total,
        tier1_count=t1_count,
        tier2_count=t2_count,
        tier3_count=t3_count,
        overdue_count=overdue_count,
        approaching_deadline_count=approaching_count,
        duplicates_detected=len(duplicates),
        average_resolution_days=avg_res_days,
    )

    # 1. By Category
    cat_counts = defaultdict(int)
    for c in all_complaints:
        cat_counts[c.category] += 1
    by_category = [
        KeyValueStat(
            label=k,
            count=v,
            percentage=round((v / total * 100.0), 1) if total > 0 else 0.0,
        )
        for k, v in sorted(cat_counts.items(), key=lambda x: x[1], reverse=True)
    ]

    # 2. By Department
    dept_map = {d.id: d for d in db.query(Department).all()}
    dept_counts = defaultdict(int)
    for c in all_complaints:
        name = dept_map[c.department_id].name if c.department_id in dept_map else "Unknown"
        dept_counts[name] += 1
    by_department = [
        KeyValueStat(
            label=k,
            count=v,
            percentage=round((v / total * 100.0), 1) if total > 0 else 0.0,
        )
        for k, v in sorted(dept_counts.items(), key=lambda x: x[1], reverse=True)
    ]

    # 3. By Priority
    prio_counts = defaultdict(int)
    for c in all_complaints:
        prio_counts[c.final_priority] += 1
    by_priority = [
        KeyValueStat(
            label=p,
            count=prio_counts[p],
            percentage=round((prio_counts[p] / total * 100.0), 1) if total > 0 else 0.0,
        )
        for p in [ComplaintPriority.CRITICAL, ComplaintPriority.HIGH, ComplaintPriority.MEDIUM, ComplaintPriority.LOW]
        if p in prio_counts
    ]

    # 4. By Status
    status_counts = defaultdict(int)
    for c in all_complaints:
        status_counts[c.status.replace('_', ' ').title()] += 1
    by_status = [
        KeyValueStat(
            label=k,
            count=v,
            percentage=round((v / total * 100.0), 1) if total > 0 else 0.0,
        )
        for k, v in sorted(status_counts.items(), key=lambda x: x[1], reverse=True)
    ]

    # 5. Department Escalation Details
    dept_escalations = []
    for d_id, dept in dept_map.items():
        d_comps = [c for c in all_complaints if c.department_id == d_id]
        t1 = sum(1 for c in d_comps if c.status not in [ComplaintStatus.RESOLVED, ComplaintStatus.CLOSED] and c.current_tier == ComplaintTier.TIER_1)
        t2 = sum(1 for c in d_comps if c.status not in [ComplaintStatus.RESOLVED, ComplaintStatus.CLOSED] and c.current_tier == ComplaintTier.TIER_2)
        t3 = sum(1 for c in d_comps if c.status not in [ComplaintStatus.RESOLVED, ComplaintStatus.CLOSED] and c.current_tier == ComplaintTier.TIER_3)
        res = sum(1 for c in d_comps if c.status in [ComplaintStatus.RESOLVED, ComplaintStatus.CLOSED])
        dept_escalations.append(DepartmentEscalationStat(
            department_name=dept.name,
            department_code=dept.code,
            total_complaints=len(d_comps),
            tier1_count=t1,
            tier2_count=t2,
            tier3_count=t3,
            resolved_count=res,
        ))

    # 6. Monthly Trends (last 6 months)
    monthly_data = defaultdict(lambda: {"submitted": 0, "resolved": 0, "escalated": 0})
    for c in all_complaints:
        m_str = c.submission_date.strftime("%b %Y")
        monthly_data[m_str]["submitted"] += 1
        if c.resolution_date:
            res_m = c.resolution_date.strftime("%b %Y")
            monthly_data[res_m]["resolved"] += 1
        if c.current_tier in [ComplaintTier.TIER_2, ComplaintTier.TIER_3]:
            monthly_data[m_str]["escalated"] += 1

    monthly_trends = [
        TrendStat(
            month=m,
            submitted=v["submitted"],
            resolved=v["resolved"],
            escalated=v["escalated"],
        )
        for m, v in list(monthly_data.items())[-6:]
    ]

    return AnalyticsDashboardResponse(
        overview=overview,
        by_category=by_category,
        by_department=by_department,
        by_priority=by_priority,
        by_status=by_status,
        department_escalations=dept_escalations,
        monthly_trends=monthly_trends,
    )

