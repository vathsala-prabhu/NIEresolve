from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from backend.app.database import utc_now

from backend.app.models.complaint import (
    Complaint,
    ComplaintStatus,
    ComplaintTier,
    ComplaintPriority,
    ComplaintEvidence,
    ComplaintLocation,
    ComplaintTimeline,
)
from backend.app.models.user import User, UserRole, Department
from backend.app.models.audit import AuditLog
from backend.app.models.notification import Notification, NotificationType
from backend.app.ml.priority_model import priority_predictor
from backend.app.ml.duplicate_detector import duplicate_detector
from backend.app.config import settings

def generate_grievance_id(db: Session) -> str:
    """Generates unique institutional grievance ID format: NIE-YYYY-XXXX"""
    current_year = utc_now().year
    prefix = f"NIE-{current_year}-"
    last_complaint = (
        db.query(Complaint)
        .filter(Complaint.grievance_id.like(f"{prefix}%"))
        .order_by(Complaint.id.desc())
        .first()
    )
    if not last_complaint:
        return f"{prefix}0001"
    
    try:
        last_seq = int(last_complaint.grievance_id.split("-")[-1])
        next_seq = last_seq + 1
    except Exception:
        next_seq = db.query(Complaint).count() + 1
        
    return f"{prefix}{next_seq:04d}"

class ComplaintService:
    @staticmethod
    def create_complaint(
        db: Session,
        complainant: User,
        title: str,
        description: str,
        category: str,
        department_id: int,
        location_name: Optional[str] = None,
        is_anonymous: bool = False,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        accuracy_meters: Optional[float] = None,
        exception_reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Creates a new complaint, applies ML priority prediction & checks for duplicates."""
        dept = db.query(Department).filter(Department.id == department_id).first()
        if not dept:
            raise HTTPException(status_code=400, detail="Invalid department ID")

        grievance_id = generate_grievance_id(db)

        # ML Priority Prediction & Safety Guardrail
        pred = priority_predictor.predict(category, title, description)

        now = utc_now()
        expected_deadline = now + timedelta(days=settings.TIER1_ESCALATION_DAYS)

        complaint = Complaint(
            grievance_id=grievance_id,
            title=title.strip(),
            description=description.strip(),
            category=category,
            department_id=department_id,
            complainant_id=complainant.id,
            is_anonymous=is_anonymous,
            location_name=location_name,
            status=ComplaintStatus.SUBMITTED,
            current_tier=ComplaintTier.TIER_1,
            predicted_priority=pred["predicted_priority"],
            final_priority=pred["final_priority"],
            priority_confidence=pred["confidence"],
            priority_explanation=pred["explanation"],
            is_safety_critical=pred["is_safety_critical"],
            submission_date=now,
            expected_deadline=expected_deadline,
            tier1_entered_at=now,
            affected_students_count=1,
        )
        db.add(complaint)
        db.flush()

        # Save Location Data
        loc = ComplaintLocation(
            complaint_id=complaint.id,
            latitude=latitude,
            longitude=longitude,
            accuracy_meters=accuracy_meters,
            is_exception_granted=bool(exception_reason),
            exception_reason=exception_reason,
            captured_at=now,
        )
        db.add(loc)

        # Save Initial Timeline Entry
        timeline = ComplaintTimeline(
            complaint_id=complaint.id,
            action="Complaint Submitted",
            actor_id=complainant.id,
            remarks=f"Grievance submitted by {complainant.role}. Initial priority assessed as {pred['final_priority']}.",
            from_status=None,
            to_status=ComplaintStatus.SUBMITTED,
            timestamp=now,
        )
        db.add(timeline)

        # Notify Complainant
        notif = Notification(
            user_id=complainant.id,
            complaint_id=complaint.id,
            title="Grievance Registered",
            message=f"Your grievance '{title}' has been registered with ID {grievance_id}. Assigned to {dept.name} (Tier 1). Expected action within 15 days.",
            notification_type=NotificationType.SUBMISSION,
        )
        db.add(notif)

        # Notify Department Officer if assigned
        if dept.grievance_officer_id:
            db.add(Notification(
                user_id=dept.grievance_officer_id,
                complaint_id=complaint.id,
                title=f"New Grievance Assigned: {grievance_id}",
                message=f"New grievance submitted in {dept.name}. Priority: {pred['final_priority']}. Please verify evidence and commence investigation.",
                notification_type=NotificationType.ASSIGNMENT,
            ))

        # Check for potential duplicates among active complaints
        active_complaints = (
            db.query(Complaint)
            .filter(
                Complaint.id != complaint.id,
                Complaint.status.notin_([ComplaintStatus.RESOLVED, ComplaintStatus.CLOSED]),
                Complaint.is_duplicate == False,
            )
            .all()
        )
        potential_duplicates = duplicate_detector.find_potential_duplicates(
            title, description, category, department_id, active_complaints
        )

        if potential_duplicates:
            top_match = potential_duplicates[0]
            complaint.duplicate_similarity_score = top_match["similarity_score"]
            complaint.duplicate_flag_reason = f"High similarity ({int(top_match['similarity_score'] * 100)}%) with {top_match['grievance_id']}: '{top_match['title']}'"

        db.commit()
        db.refresh(complaint)

        return {
            "complaint": complaint,
            "prediction": pred,
            "potential_duplicates": potential_duplicates,
        }

    @staticmethod
    def merge_complaints(
        db: Session,
        actor: User,
        master_complaint_id: int,
        duplicate_complaint_id: int,
        reason: str,
    ) -> Complaint:
        """
        Merges duplicate complaint into a master complaint.
        Preserves original records, updates affected count, and notifies reporter.
        """
        if master_complaint_id == duplicate_complaint_id:
            raise HTTPException(status_code=400, detail="Cannot merge a complaint into itself.")

        master = db.query(Complaint).filter(Complaint.id == master_complaint_id).first()
        duplicate = db.query(Complaint).filter(Complaint.id == duplicate_complaint_id).first()

        if not master or not duplicate:
            raise HTTPException(status_code=404, detail="Master or duplicate complaint not found.")

        now = utc_now()
        duplicate.is_duplicate = True
        duplicate.master_complaint_id = master.id
        duplicate.status = master.status # Synchronize status

        master.affected_students_count += duplicate.affected_students_count

        # Log timeline on duplicate
        db.add(ComplaintTimeline(
            complaint_id=duplicate.id,
            action="Merged as Duplicate",
            actor_id=actor.id,
            remarks=f"Merged with master complaint {master.grievance_id}. Reason: {reason}",
            from_status=duplicate.status,
            to_status=master.status,
            timestamp=now,
        ))

        # Log timeline on master
        db.add(ComplaintTimeline(
            complaint_id=master.id,
            action="Duplicate Complaint Linked",
            actor_id=actor.id,
            remarks=f"Linked grievance {duplicate.grievance_id} as duplicate. Total affected individuals: {master.affected_students_count}.",
            from_status=master.status,
            to_status=master.status,
            timestamp=now,
        ))

        # Log audit trail
        db.add(AuditLog(
            actor_id=actor.id,
            action="MERGE_DUPLICATE_COMPLAINT",
            entity_type="complaint",
            entity_id=str(duplicate.id),
            details=f"Merged {duplicate.grievance_id} into {master.grievance_id}. Reason: {reason}",
        ))

        # Notify Complainant of duplicate complaint
        db.add(Notification(
            user_id=duplicate.complainant_id,
            complaint_id=duplicate.id,
            title=f"Update on Grievance {duplicate.grievance_id}",
            message=f"Your grievance has been identified as a common issue and linked with master case {master.grievance_id}. You can track progress seamlessly.",
            notification_type=NotificationType.DUPLICATE_MERGE,
        ))

        db.commit()
        db.refresh(master)
        return master

    @staticmethod
    def override_priority(
        db: Session,
        actor: User,
        complaint_id: int,
        new_priority: str,
        reason: str,
    ) -> Complaint:
        """Authorized priority override with recorded reason."""
        complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
        if not complaint:
            raise HTTPException(status_code=404, detail="Complaint not found")

        old_priority = complaint.final_priority
        complaint.final_priority = new_priority
        complaint.priority_override_reason = f"Manual override by {actor.full_name} ({actor.role}): {reason}"

        now = utc_now()
        db.add(ComplaintTimeline(
            complaint_id=complaint.id,
            action="Priority Overridden",
            actor_id=actor.id,
            remarks=f"Priority updated from {old_priority} to {new_priority}. Reason: {reason}",
            from_status=complaint.status,
            to_status=complaint.status,
            timestamp=now,
        ))

        db.add(AuditLog(
            actor_id=actor.id,
            action="OVERRIDE_PRIORITY",
            entity_type="complaint",
            entity_id=str(complaint.id),
            details=f"Changed priority from {old_priority} to {new_priority}. Reason: {reason}",
        ))

        # Notify complainant
        db.add(Notification(
            user_id=complaint.complainant_id,
            complaint_id=complaint.id,
            title=f"Priority Updated for {complaint.grievance_id}",
            message=f"Your grievance priority was updated to {new_priority}.",
            notification_type=NotificationType.PRIORITY_CHANGE,
        ))

        db.commit()
        db.refresh(complaint)
        return complaint

    @staticmethod
    def update_status(
        db: Session,
        actor: User,
        complaint_id: int,
        new_status: str,
        remarks: Optional[str] = None,
        assigned_to_id: Optional[int] = None,
        resolution_evidence_url: Optional[str] = None,
    ) -> Complaint:
        complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
        if not complaint:
            raise HTTPException(status_code=404, detail="Complaint not found")

        old_status = complaint.status
        now = utc_now()

        complaint.status = new_status
        if assigned_to_id:
            complaint.assigned_to_id = assigned_to_id
        if resolution_evidence_url:
            complaint.resolution_evidence_url = resolution_evidence_url
        if new_status == ComplaintStatus.RESOLVED:
            complaint.resolution_date = now
            complaint.resolution_remarks = remarks

        action_name = f"Status Changed to {new_status.replace('_', ' ').title()}"
        db.add(ComplaintTimeline(
            complaint_id=complaint.id,
            action=action_name,
            actor_id=actor.id,
            remarks=remarks or f"Status transitioned to {new_status}",
            from_status=old_status,
            to_status=new_status,
            timestamp=now,
        ))

        # Notify complainant
        notif_msg = f"Your grievance {complaint.grievance_id} is now '{new_status.replace('_', ' ').title()}'."
        if remarks:
            notif_msg += f" Officer Remarks: {remarks}"
        if new_status == ComplaintStatus.RESOLVED:
            notif_msg += " Please review and confirm the resolution in your dashboard."

        db.add(Notification(
            user_id=complaint.complainant_id,
            complaint_id=complaint.id,
            title=f"Update: {complaint.grievance_id}",
            message=notif_msg,
            notification_type=NotificationType.RESOLVED if new_status == ComplaintStatus.RESOLVED else NotificationType.STATUS_UPDATE,
        ))

        # Synchronize linked duplicates
        for dup in complaint.duplicates:
            dup.status = new_status
            if new_status == ComplaintStatus.RESOLVED:
                dup.resolution_date = now
                dup.resolution_remarks = remarks
            db.add(Notification(
                user_id=dup.complainant_id,
                complaint_id=dup.id,
                title=f"Master Case Update: {complaint.grievance_id}",
                message=f"The common grievance has been updated to '{new_status.replace('_', ' ').title()}'.",
                notification_type=NotificationType.STATUS_UPDATE,
            ))

        db.commit()
        db.refresh(complaint)
        return complaint

