from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException

from backend.app.models.complaint import (
    Complaint,
    ComplaintStatus,
    ComplaintTier,
    ComplaintTimeline,
)
from backend.app.models.escalation import EscalationLog, EscalationConfig
from backend.app.models.user import User, UserRole
from backend.app.models.notification import Notification, NotificationType
from backend.app.models.audit import AuditLog
from backend.app.config import settings

class EscalationService:
    @staticmethod
    def get_tier_duration(db: Session, tier_name: str) -> int:
        """Retrieves configured duration in days for a tier."""
        cfg = db.query(EscalationConfig).filter(EscalationConfig.tier_name == tier_name).first()
        if cfg and cfg.is_active:
            return cfg.duration_days
        if tier_name == ComplaintTier.TIER_1:
            return settings.TIER1_ESCALATION_DAYS
        if tier_name == ComplaintTier.TIER_2:
            return settings.TIER2_ESCALATION_DAYS
        return 15

    @staticmethod
    def check_and_run_escalations(db: Session) -> Dict[str, Any]:
        """
        Scans all unresolved complaints across Tier 1 and Tier 2.
        Automatically escalates complaints that have exceeded their 15-day window without resolution.
        Sends escalation warnings for complaints within 3 days of deadline.
        """
        now = datetime.utcnow()
        escalated_tier2 = []
        escalated_tier3 = []
        warnings_sent = []

        tier1_days = EscalationService.get_tier_duration(db, ComplaintTier.TIER_1)
        tier2_days = EscalationService.get_tier_duration(db, ComplaintTier.TIER_2)

        active_complaints = (
            db.query(Complaint)
            .filter(
                Complaint.status.notin_([ComplaintStatus.RESOLVED, ComplaintStatus.CLOSED]),
                Complaint.is_duplicate == False,
                Complaint.is_escalation_paused == False,
            )
            .all()
        )

        # Retrieve Grievance Cell & Principal users for notifications
        grievance_cell_users = db.query(User).filter(User.role == UserRole.GRIEVANCE_CELL, User.is_active == True).all()
        principal_users = db.query(User).filter(User.role == UserRole.PRINCIPAL, User.is_active == True).all()

        for comp in active_complaints:
            # 1. Tier 1 -> Tier 2 Escalation Check
            if comp.current_tier == ComplaintTier.TIER_1:
                start_time = comp.tier1_entered_at or comp.submission_date
                elapsed_days = (now - start_time).total_seconds() / 86400.0

                # Check warning (e.g. 12+ days elapsed, < 3 days remaining)
                if elapsed_days >= (tier1_days - 3) and elapsed_days < tier1_days:
                    # Send warning if not already sent recently
                    comp.expected_deadline = start_time + timedelta(days=tier1_days)
                    warnings_sent.append(comp.grievance_id)

                # Automatic Escalation
                elif elapsed_days >= tier1_days:
                    comp.current_tier = ComplaintTier.TIER_2
                    comp.tier2_entered_at = now
                    comp.expected_deadline = now + timedelta(days=tier2_days)
                    reason = f"Automatic Institutional Escalation: Unresolved after {int(elapsed_days)} days at Department Level (Tier 1)."

                    # Escalation Log
                    db.add(EscalationLog(
                        complaint_id=comp.id,
                        from_tier=ComplaintTier.TIER_1,
                        to_tier=ComplaintTier.TIER_2,
                        escalation_date=now,
                        reason=reason,
                        automated=True,
                        notified_authorities="Institutional Grievance Redressal Cell",
                    ))

                    # Timeline Entry
                    db.add(ComplaintTimeline(
                        complaint_id=comp.id,
                        action="Auto-Escalated to Tier 2 (Grievance Cell)",
                        actor_id=None,
                        remarks=reason,
                        from_status=comp.status,
                        to_status=comp.status,
                        timestamp=now,
                    ))

                    # Notify Complainant
                    db.add(Notification(
                        user_id=comp.complainant_id,
                        complaint_id=comp.id,
                        title=f"Grievance Escalated to Tier 2: {comp.grievance_id}",
                        message=f"Your grievance exceeded the 15-day department resolution window and has been automatically escalated to the Institutional Grievance Redressal Cell.",
                        notification_type=NotificationType.ESCALATED,
                    ))

                    # Notify Grievance Cell members
                    for gc in grievance_cell_users:
                        db.add(Notification(
                            user_id=gc.id,
                            complaint_id=comp.id,
                            title=f"Tier 2 Escalation Alert: {comp.grievance_id}",
                            message=f"Grievance '{comp.title}' from {comp.department.name} escalated to Grievance Cell. Immediate review required.",
                            notification_type=NotificationType.ESCALATED,
                        ))

                    escalated_tier2.append(comp.grievance_id)

            # 2. Tier 2 -> Tier 3 Escalation Check
            elif comp.current_tier == ComplaintTier.TIER_2:
                start_time = comp.tier2_entered_at or comp.tier1_entered_at or comp.submission_date
                elapsed_days = (now - start_time).total_seconds() / 86400.0

                if elapsed_days >= tier2_days:
                    comp.current_tier = ComplaintTier.TIER_3
                    comp.tier3_entered_at = now
                    comp.expected_deadline = None # Tier 3 is highest executive authority
                    reason = f"Critical Executive Escalation: Unresolved after {int(elapsed_days)} days at Grievance Cell (Tier 2). Referred to Principal / Higher Authority."

                    db.add(EscalationLog(
                        complaint_id=comp.id,
                        from_tier=ComplaintTier.TIER_2,
                        to_tier=ComplaintTier.TIER_3,
                        escalation_date=now,
                        reason=reason,
                        automated=True,
                        notified_authorities="Principal / Higher Institutional Authority",
                    ))

                    db.add(ComplaintTimeline(
                        complaint_id=comp.id,
                        action="Auto-Escalated to Tier 3 (Principal)",
                        actor_id=None,
                        remarks=reason,
                        from_status=comp.status,
                        to_status=comp.status,
                        timestamp=now,
                    ))

                    db.add(Notification(
                        user_id=comp.complainant_id,
                        complaint_id=comp.id,
                        title=f"Grievance Escalated to Tier 3: {comp.grievance_id}",
                        message="Your grievance has been escalated to Tier 3 for direct review and executive action by the Principal / Higher Authority.",
                        notification_type=NotificationType.ESCALATED,
                    ))

                    for pr in principal_users:
                        db.add(Notification(
                            user_id=pr.id,
                            complaint_id=comp.id,
                            title=f"Tier 3 Executive Alert: {comp.grievance_id}",
                            message=f"Grievance '{comp.title}' escalated to Principal's office after 30 days pending across Tiers 1 and 2.",
                            notification_type=NotificationType.ESCALATED,
                        ))

                    escalated_tier3.append(comp.grievance_id)

        db.commit()

        return {
            "escalated_to_tier2": escalated_tier2,
            "escalated_to_tier3": escalated_tier3,
            "warnings_count": len(warnings_sent),
            "timestamp": now.isoformat(),
        }

    @staticmethod
    def toggle_deadline_pause(
        db: Session,
        actor: User,
        complaint_id: int,
        paused: bool,
        reason: str,
    ) -> Complaint:
        """Authorized action to pause or resume escalation deadline countdown."""
        comp = db.query(Complaint).filter(Complaint.id == complaint_id).first()
        if not comp:
            raise HTTPException(status_code=404, detail="Complaint not found")

        comp.is_escalation_paused = paused
        comp.escalation_pause_reason = reason if paused else None

        now = datetime.utcnow()
        action_name = "Escalation Paused" if paused else "Escalation Resumed"
        db.add(ComplaintTimeline(
            complaint_id=comp.id,
            action=action_name,
            actor_id=actor.id,
            remarks=f"{action_name} by {actor.full_name}. Reason: {reason}",
            from_status=comp.status,
            to_status=comp.status,
            timestamp=now,
        ))

        db.add(AuditLog(
            actor_id=actor.id,
            action="PAUSE_ESCALATION" if paused else "RESUME_ESCALATION",
            entity_type="complaint",
            entity_id=str(comp.id),
            details=f"Status: paused={paused}. Reason: {reason}",
        ))

        db.commit()
        db.refresh(comp)
        return comp

