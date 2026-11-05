from datetime import datetime
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.database import get_db, utc_now
from backend.app.models.complaint import Complaint, ComplaintStatus, ComplaintTier
from backend.app.models.user import Department
from backend.app.models.escalation import EscalationConfig, EscalationLog
from backend.app.auth.dependencies import require_any_officer, require_admin
from backend.app.services.escalation_service import EscalationService

router = APIRouter(prefix="/api/escalations", tags=["Escalation Matrix"])

@router.get("/dashboard")
def get_escalation_dashboard(
    current_user = Depends(require_any_officer),
    db: Session = Depends(get_db),
):
    """
    Returns high-level institutional escalation metrics:
    - Approaching deadlines (< 3 days)
    - Overdue complaints
    - Current counts at Tier 1, Tier 2, Tier 3
    - Department-wise escalation breakdown
    - Average resolution time
    """
    now = utc_now()

    # Active complaints
    active_complaints = (
        db.query(Complaint)
        .filter(
            Complaint.status.notin_([ComplaintStatus.RESOLVED, ComplaintStatus.CLOSED]),
            Complaint.is_duplicate == False,
        )
        .all()
    )

    tier1_count = sum(1 for c in active_complaints if c.current_tier == ComplaintTier.TIER_1)
    tier2_count = sum(1 for c in active_complaints if c.current_tier == ComplaintTier.TIER_2)
    tier3_count = sum(1 for c in active_complaints if c.current_tier == ComplaintTier.TIER_3)

    approaching_deadline = []
    overdue_complaints = []

    for c in active_complaints:
        if c.expected_deadline and not c.is_escalation_paused:
            diff_days = (c.expected_deadline - now).total_seconds() / 86400.0
            item = {
                "id": c.id,
                "grievance_id": c.grievance_id,
                "title": c.title,
                "category": c.category,
                "department_code": c.department.code if c.department else "GEN",
                "current_tier": c.current_tier,
                "days_remaining": round(diff_days, 1),
                "final_priority": c.final_priority,
            }
            if diff_days < 0:
                overdue_complaints.append(item)
            elif diff_days <= 3.0:
                approaching_deadline.append(item)

    # Department escalation statistics
    dept_stats = []
    departments = db.query(Department).all()
    for d in departments:
        d_comps = [c for c in active_complaints if c.department_id == d.id]
        t1 = sum(1 for c in d_comps if c.current_tier == ComplaintTier.TIER_1)
        t2 = sum(1 for c in d_comps if c.current_tier == ComplaintTier.TIER_2)
        t3 = sum(1 for c in d_comps if c.current_tier == ComplaintTier.TIER_3)
        dept_stats.append({
            "department_id": d.id,
            "department_name": d.name,
            "department_code": d.code,
            "tier1_count": t1,
            "tier2_count": t2,
            "tier3_count": t3,
            "total_active": len(d_comps),
        })

    # Average resolution time across resolved complaints
    resolved = db.query(Complaint).filter(Complaint.resolution_date.isnot(None)).all()
    if resolved:
        total_days = sum((r.resolution_date - r.submission_date).total_seconds() / 86400.0 for r in resolved)
        avg_days = round(total_days / len(resolved), 1)
    else:
        avg_days = 0.0

    return {
        "tier1_count": tier1_count,
        "tier2_count": tier2_count,
        "tier3_count": tier3_count,
        "approaching_deadline_count": len(approaching_deadline),
        "approaching_deadline_items": approaching_deadline,
        "overdue_count": len(overdue_complaints),
        "overdue_items": overdue_complaints,
        "average_resolution_days": avg_days,
        "department_escalations": dept_stats,
    }

@router.post("/run-check")
def trigger_escalation_job(
    current_user = Depends(require_any_officer),
    db: Session = Depends(get_db),
):
    """Manual or cron trigger to evaluate 15-day escalation boundaries."""
    result = EscalationService.check_and_run_escalations(db)
    return {
        "message": "Escalation check completed.",
        "details": result,
    }

@router.get("/configs")
def get_escalation_configs(
    current_user = Depends(require_any_officer),
    db: Session = Depends(get_db),
):
    """Retrieves current tier duration settings."""
    configs = db.query(EscalationConfig).all()
    return configs

@router.put("/configs/{tier_name}")
def update_escalation_config(
    tier_name: str,
    duration_days: int,
    current_user = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin endpoint to modify escalation deadlines for tiers."""
    cfg = db.query(EscalationConfig).filter(EscalationConfig.tier_name == tier_name).first()
    if not cfg:
        cfg = EscalationConfig(tier_name=tier_name, duration_days=duration_days)
        db.add(cfg)
    else:
        cfg.duration_days = duration_days
        cfg.updated_at = utc_now()
    db.commit()
    return {"message": f"Updated {tier_name} deadline to {duration_days} days."}

