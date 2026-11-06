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
    ComplaintCampus,
    ComplaintCategory,
    ComplaintEvidence,
    ComplaintLocation,
    ComplaintTimeline,
    ComplaintVote,
    InternalComplaintMessage,
)
from backend.app.models.user import User, UserRole, Department
from backend.app.models.audit import AuditLog
from backend.app.models.notification import Notification, NotificationType
from backend.app.ml.priority_model import priority_predictor
from backend.app.ml.duplicate_detector import duplicate_detector
from backend.app.services.sms_service import SmsService
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
        campus: str = "North Campus",
        department_id: Optional[int] = None,
        location_name: Optional[str] = None,
        is_confidential_evidence: bool = False,
        is_anonymous: bool = False, # Deprecated: anonymous submission is strictly disabled
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        accuracy_meters: Optional[float] = None,
        exception_reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Creates a new complaint, applies ML priority prediction & checks for duplicates."""
        # Auto-route department if not explicitly selected
        dept = None
        if department_id:
            dept = db.query(Department).filter(Department.id == department_id).first()
        
        if not dept:
            category_lower = category.lower()
            if "placement" in category_lower or "career" in category_lower:
                dept = db.query(Department).filter(Department.code == "CSE").first()
            elif "exam" in category_lower or "result" in category_lower:
                dept = db.query(Department).filter(Department.code == "EXAM").first()
            elif "infrastructure" in category_lower or "maintenance" in category_lower or "hostel" in category_lower or "safety" in category_lower:
                dept = db.query(Department).filter(Department.code == "ESTATE").first()
            elif "lab" in category_lower or "equipment" in category_lower:
                dept = db.query(Department).filter(Department.code == "MECH").first()
            else:
                dept = db.query(Department).first()

        department_id = dept.id if dept else 1

        grievance_id = generate_grievance_id(db)

        # ML Priority Prediction & Safety Guardrail (with initial 1 reporter)
        pred = priority_predictor.predict(category, title, description, upvote_count=1)

        now = utc_now()
        expected_deadline = now + timedelta(days=settings.TIER1_ESCALATION_DAYS)

        complaint = Complaint(
            grievance_id=grievance_id,
            title=title.strip(),
            description=description.strip(),
            category=category,
            campus=campus if campus in ComplaintCampus.ALL else ComplaintCampus.NORTH_CAMPUS,
            department_id=department_id,
            complainant_id=complainant.id,
            is_anonymous=False, # Strictly disabled
            location_name=location_name,
            is_confidential_evidence=is_confidential_evidence,
            upvote_count=0,
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

        # Save Location Data if coordinates provided (optional exception flow)
        if latitude is not None and longitude is not None:
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
            remarks=f"Grievance registered for {complaint.campus}. Initial priority assessed as {pred['final_priority']}.",
            from_status=None,
            to_status=ComplaintStatus.SUBMITTED,
            timestamp=now,
        )
        db.add(timeline)

        # Notify Complainant in-app
        notif = Notification(
            user_id=complainant.id,
            complaint_id=complaint.id,
            title="Grievance Registered",
            message=f"Your grievance '{title}' has been registered with ID {grievance_id} ({complaint.campus}). Assigned to {dept.name if dept else 'Department'} (Tier 1). Expected action within 15 days.",
            notification_type=NotificationType.SUBMISSION,
        )
        db.add(notif)

        # Dispatch SMS 1 — Complaint Registration
        recipient_phone = complainant.phone
        if not recipient_phone and complainant.student_profile:
            recipient_phone = complainant.student_profile.student_phone_number or complainant.student_profile.parent_phone_number
        if recipient_phone:
            SmsService.send_sms(
                recipient_phone=recipient_phone,
                event_type="complaint_registered",
                template_params={
                    "name": complainant.full_name,
                    "grievance_id": grievance_id,
                },
                complaint_id=complaint.id,
                recipient_id=complainant.id,
                db=db,
            )

        # Notify Department Officer if assigned
        if dept and dept.grievance_officer_id:
            db.add(Notification(
                user_id=dept.grievance_officer_id,
                complaint_id=complaint.id,
                title=f"New Grievance Assigned: {grievance_id}",
                message=f"New grievance submitted in {dept.name} ({complaint.campus}). Priority: {pred['final_priority']}. Please verify evidence and commence investigation.",
                notification_type=NotificationType.ASSIGNMENT,
            ))

        # Check for potential duplicates among active in-progress complaints
        active_complaints = (
            db.query(Complaint)
            .filter(
                Complaint.id != complaint.id,
                Complaint.status.in_([
                    ComplaintStatus.SUBMITTED,
                    ComplaintStatus.VERIFIED,
                    ComplaintStatus.ASSIGNED,
                    ComplaintStatus.UNDER_INVESTIGATION,
                    ComplaintStatus.ACTION_TAKEN,
                    ComplaintStatus.REOPENED,
                ]),
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

            # Auto-consolidate into active master grievance when semantic similarity >= 0.70
            if top_match["similarity_score"] >= 0.70:
                master = db.query(Complaint).filter(Complaint.id == top_match["complaint_id"]).first()
                if (
                    master
                    and master.id != complaint.id
                    and master.status not in [
                        ComplaintStatus.RESOLVED,
                        ComplaintStatus.CLOSED,
                        ComplaintStatus.RESOLVED_AWAITING_CONFIRMATION,
                        ComplaintStatus.CONFIRMED_RESOLVED,
                        ComplaintStatus.AUTO_CONFIRMED_RESOLVED,
                        "confirmed_resolved",
                        "auto_confirmed_resolved",
                    ]
                ):
                    # Traverse to root master if already chained
                    while master.master_complaint_id:
                        parent = db.query(Complaint).filter(Complaint.id == master.master_complaint_id).first()
                        if not parent or parent.id == master.id:
                            break
                        master = parent

                    complaint.is_duplicate = True
                    complaint.master_complaint_id = master.id
                    complaint.duplicate_flag_reason = (
                        f"Automatically consolidated with active master grievance {master.grievance_id} "
                        f"({int(top_match['similarity_score'] * 100)}% similarity on '{master.title}')"
                    )

                    # Increment affected students count on master
                    master.affected_students_count = (master.affected_students_count or 1) + 1

                    # Dynamic priority adjustment based on affected count
                    if master.affected_students_count >= 15 and master.final_priority != ComplaintPriority.CRITICAL:
                        master.final_priority = ComplaintPriority.CRITICAL
                        master.priority_override_reason = (
                            f"Automatically promoted to CRITICAL: {master.affected_students_count} affected students reported this issue."
                        )
                    elif master.affected_students_count >= 5 and master.final_priority == ComplaintPriority.LOW:
                        master.final_priority = ComplaintPriority.MEDIUM
                        master.priority_override_reason = (
                            f"Automatically adjusted to MEDIUM: {master.affected_students_count} affected students reported this issue."
                        )

                    # Log timeline on the newly submitted duplicate complaint
                    db.add(ComplaintTimeline(
                        complaint_id=complaint.id,
                        action="Consolidated with Active Master Issue",
                        actor_id=complainant.id,
                        remarks=f"Grievance linked to active master case {master.grievance_id} ({int(top_match['similarity_score'] * 100)}% match). Progress synchronized to '{master.status}'.",
                        from_status=ComplaintStatus.SUBMITTED,
                        to_status=master.status,
                        timestamp=now,
                    ))

                    # Log timeline on the master complaint
                    identifier = ""
                    if complainant.student_profile and complainant.student_profile.usn:
                        identifier = f" ({complainant.student_profile.usn})"
                    elif complainant.faculty_profile and complainant.faculty_profile.faculty_id:
                        identifier = f" ({complainant.faculty_profile.faculty_id})"

                    db.add(ComplaintTimeline(
                        complaint_id=master.id,
                        action="Duplicate Grievance Consolidated",
                        actor_id=complainant.id,
                        remarks=f"Duplicate grievance {complaint.grievance_id} from {complainant.full_name}{identifier} linked. Total affected students: {master.affected_students_count}.",
                        from_status=master.status,
                        to_status=master.status,
                        timestamp=now,
                    ))

                    # Log audit trail
                    db.add(AuditLog(
                        actor_id=complainant.id,
                        action="AUTO_CONSOLIDATE_DUPLICATE",
                        entity_type="complaint",
                        entity_id=str(complaint.id),
                        details=f"Consolidated new grievance {complaint.grievance_id} into master {master.grievance_id}. Total affected: {master.affected_students_count}.",
                    ))

                    # Notify submitting student of consolidation
                    db.add(Notification(
                        user_id=complainant.id,
                        complaint_id=complaint.id,
                        title=f"Grievance Consolidated: {complaint.grievance_id}",
                        message=(
                            f"Your grievance has been identified as a common issue and consolidated with active case {master.grievance_id}. "
                            f"You can continue tracking updates under your reference {complaint.grievance_id} (Status: {master.status})."
                        ),
                        notification_type=NotificationType.DUPLICATE_MERGE,
                    ))

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

        # Resolution Workflow: Officer marks as resolved -> enters Awaiting Confirmation state
        is_resolution_event = new_status in [
            ComplaintStatus.RESOLVED,
            ComplaintStatus.RESOLVED_AWAITING_CONFIRMATION,
        ]

        if is_resolution_event:
            complaint.status = ComplaintStatus.RESOLVED_AWAITING_CONFIRMATION
            complaint.resolved_at = now
            complaint.resolution_date = now
            complaint.resolution_remarks = remarks
            complaint.confirmation_deadline = now + timedelta(days=getattr(settings, "AUTO_CONFIRMATION_DAYS", 5))
            complaint.student_confirmed = None # Reset for fresh confirmation
        else:
            complaint.status = new_status

        if assigned_to_id:
            complaint.assigned_to_id = assigned_to_id
        if resolution_evidence_url:
            complaint.resolution_evidence_url = resolution_evidence_url

        action_name = f"Status Changed to {complaint.status.replace('_', ' ').title()}"
        if is_resolution_event:
            action_name = "Marked as Resolved by Officer"

        db.add(ComplaintTimeline(
            complaint_id=complaint.id,
            action=action_name,
            actor_id=actor.id,
            remarks=remarks or f"Status transitioned to {complaint.status}",
            from_status=old_status,
            to_status=complaint.status,
            timestamp=now,
        ))

        # In-app notification for complainant
        notif_msg = f"Your grievance {complaint.grievance_id} is now '{complaint.status.replace('_', ' ').title()}'."
        if remarks:
            notif_msg += f" Officer Remarks: {remarks}"
        if is_resolution_event:
            notif_msg = f"Your grievance {complaint.grievance_id} has been marked as resolved by {actor.full_name}. Please confirm whether the issue has actually been fixed within 5 days."

        db.add(Notification(
            user_id=complaint.complainant_id,
            complaint_id=complaint.id,
            title=f"Update: {complaint.grievance_id}",
            message=notif_msg,
            notification_type=NotificationType.RESOLVED if is_resolution_event else NotificationType.STATUS_UPDATE,
        ))

        # Dispatch SMS 2 — Complaint Resolved
        if is_resolution_event:
            recipient_phone = complaint.complainant.phone
            if not recipient_phone and complaint.complainant.student_profile:
                recipient_phone = complaint.complainant.student_profile.student_phone_number or complaint.complainant.student_profile.parent_phone_number
            if recipient_phone:
                SmsService.send_sms(
                    recipient_phone=recipient_phone,
                    event_type="complaint_resolved",
                    template_params={"grievance_id": complaint.grievance_id},
                    complaint_id=complaint.id,
                    recipient_id=complaint.complainant_id,
                    db=db,
                )

        # Synchronize linked duplicates
        for dup in complaint.duplicates:
            dup.status = complaint.status
            if is_resolution_event:
                dup.resolution_date = now
                dup.resolved_at = now
                dup.resolution_remarks = remarks
                dup.confirmation_deadline = complaint.confirmation_deadline
            db.add(Notification(
                user_id=dup.complainant_id,
                complaint_id=dup.id,
                title=f"Master Case Update: {complaint.grievance_id}",
                message=f"The common grievance has been updated to '{complaint.status.replace('_', ' ').title()}'.",
                notification_type=NotificationType.STATUS_UPDATE,
            ))

        db.commit()
        db.refresh(complaint)
        return complaint

    @staticmethod
    def confirm_resolution(
        db: Session,
        complaint_id: int,
        student: Optional[User] = None,
        confirmed: bool = True,
        remarks: Optional[str] = None,
        actor: Optional[User] = None,
    ) -> Complaint:
        """
        Student/Faculty explicit resolution confirmation workflow:
        - Confirmed (YES) -> Status becomes 'confirmed_resolved'
        - Unresolved (NO) -> Reopens complaint ('reopened'), stops auto-confirm timer, notifies officer
        """
        user = student or actor
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required.")

        complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
        if not complaint:
            raise HTTPException(status_code=404, detail="Complaint not found")

        if complaint.complainant_id != user.id and user.role not in [UserRole.SUPER_ADMIN]:
            raise HTTPException(status_code=403, detail="Only the original complainant can confirm resolution.")

        now = utc_now()
        complaint.student_confirmed = confirmed
        complaint.student_confirmed_at = now
        complaint.student_confirmation_remarks = remarks
        complaint.is_auto_confirmed = False

        if confirmed:
            complaint.status = ComplaintStatus.CONFIRMED_RESOLVED
            db.add(ComplaintTimeline(
                complaint_id=complaint.id,
                action="Resolution Confirmed by Complainant",
                actor_id=user.id,
                remarks=remarks or "Complainant confirmed issue is satisfactorily resolved.",
                from_status=ComplaintStatus.RESOLVED_AWAITING_CONFIRMATION,
                to_status=ComplaintStatus.CONFIRMED_RESOLVED,
                timestamp=now,
            ))

            # Notify assigned officer
            if complaint.assigned_to_id:
                db.add(Notification(
                    user_id=complaint.assigned_to_id,
                    complaint_id=complaint.id,
                    title=f"Resolution Confirmed: {complaint.grievance_id}",
                    message=f"The complainant has confirmed satisfactory resolution for grievance {complaint.grievance_id}.",
                    notification_type=NotificationType.STATUS_UPDATE,
                ))
        else:
            # Reopen workflow
            complaint.status = ComplaintStatus.REOPENED
            complaint.reopen_reason = remarks or "Complainant indicated issue is still unresolved."
            complaint.reopen_count = (complaint.reopen_count or 0) + 1
            complaint.reopened_at = now
            complaint.confirmation_deadline = None # Cancel auto-confirmation timer

            db.add(ComplaintTimeline(
                complaint_id=complaint.id,
                action="Grievance Reopened by Complainant",
                actor_id=user.id,
                remarks=remarks or "Issue reported still unresolved. Sent back to responsible authority.",
                from_status=ComplaintStatus.RESOLVED_AWAITING_CONFIRMATION,
                to_status=ComplaintStatus.REOPENED,
                timestamp=now,
            ))

            # Notify assigned officer & department
            officer_id = complaint.assigned_to_id
            if not officer_id and complaint.department:
                officer_id = complaint.department.grievance_officer_id

            if officer_id:
                db.add(Notification(
                    user_id=officer_id,
                    complaint_id=complaint.id,
                    title=f"Grievance Reopened: {complaint.grievance_id}",
                    message=f"Complainant reported issue as unresolved: '{remarks}'. Immediate follow-up required.",
                    notification_type=NotificationType.STATUS_UPDATE,
                ))

            # Dispatch SMS alert for reopening
            phone = complaint.complainant.phone
            if not phone and complaint.complainant.student_profile:
                phone = complaint.complainant.student_profile.student_phone_number
            if phone:
                SmsService.send_sms(
                    recipient_phone=phone,
                    event_type="complaint_reopened",
                    template_params={"grievance_id": complaint.grievance_id, "remarks": remarks or "Unresolved"},
                    complaint_id=complaint.id,
                    recipient_id=complaint.complainant_id,
                    db=db,
                )

        db.commit()
        db.refresh(complaint)
        return complaint

    @staticmethod
    def check_and_run_auto_confirmations(db: Session) -> Dict[str, Any]:
        """
        Scheduled 5-day auto-confirmation job:
        If complainant has not responded within 5 calendar days after officer marks as resolved,
        automatically sets status to 'auto_confirmed_resolved'.
        """
        now = utc_now()
        pending_confirmations = (
            db.query(Complaint)
            .filter(
                Complaint.status == ComplaintStatus.RESOLVED_AWAITING_CONFIRMATION,
                Complaint.student_confirmed == None,
                Complaint.confirmation_deadline != None,
                Complaint.confirmation_deadline <= now,
            )
            .all()
        )

        auto_confirmed_ids = []
        for comp in pending_confirmations:
            comp.status = ComplaintStatus.AUTO_CONFIRMED_RESOLVED
            comp.student_confirmed = True
            comp.is_auto_confirmed = True
            comp.student_confirmed_at = now
            comp.student_confirmation_remarks = "System auto-confirmed: Complainant did not respond within 5 calendar days."

            db.add(ComplaintTimeline(
                complaint_id=comp.id,
                action="Auto-Confirmed Resolved (5-Day Timeout)",
                actor_id=None,
                remarks="Auto-confirmed resolution after 5-day response window elapsed without dispute.",
                from_status=ComplaintStatus.RESOLVED_AWAITING_CONFIRMATION,
                to_status=ComplaintStatus.AUTO_CONFIRMED_RESOLVED,
                timestamp=now,
            ))

            db.add(Notification(
                user_id=comp.complainant_id,
                complaint_id=comp.id,
                title=f"Auto-Confirmed: {comp.grievance_id}",
                message=f"Grievance {comp.grievance_id} was auto-confirmed as resolved following the 5-day window.",
                notification_type=NotificationType.STATUS_UPDATE,
            ))

            # Dispatch SMS Notification
            phone = comp.complainant.phone
            if not phone and comp.complainant.student_profile:
                phone = comp.complainant.student_profile.student_phone_number
            if phone:
                SmsService.send_sms(
                    recipient_phone=phone,
                    event_type="auto_confirmed",
                    template_params={"grievance_id": comp.grievance_id},
                    complaint_id=comp.id,
                    recipient_id=comp.complainant_id,
                    db=db,
                )

            auto_confirmed_ids.append(comp.grievance_id)

        if auto_confirmed_ids:
            db.commit()
            print(f"[AutoConfirmation] Processed {len(auto_confirmed_ids)} complaints: {auto_confirmed_ids}")

        return {
            "total_processed": len(auto_confirmed_ids),
            "auto_confirmed": auto_confirmed_ids,
            "auto_confirmed_grievance_ids": auto_confirmed_ids,
        }

    @staticmethod
    def upvote_complaint(db: Session, complaint_id: int, user: Optional[User] = None, actor: Optional[User] = None) -> Dict[str, Any]:
        """
        Registers support ("I am facing this issue too") for an existing complaint.
        Prevents duplicates via DB constraint; dynamically re-evaluates ML priority.
        """
        target_user = user or actor
        if not target_user:
            raise HTTPException(status_code=401, detail="Authentication required.")

        complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
        if not complaint:
            raise HTTPException(status_code=404, detail="Complaint not found")

        # Check existing vote
        existing_vote = db.query(ComplaintVote).filter(
            ComplaintVote.complaint_id == complaint_id,
            ComplaintVote.user_id == target_user.id,
        ).first()

        if existing_vote:
            return {
                "upvoted": True,
                "has_upvoted": True,
                "upvote_count": complaint.upvote_count,
                "final_priority": complaint.final_priority,
                "message": "Already upvoted",
            }

        # Add vote
        vote = ComplaintVote(complaint_id=complaint_id, user_id=target_user.id, created_at=utc_now())
        db.add(vote)
        complaint.upvote_count = (complaint.upvote_count or 0) + 1
        complaint.affected_students_count = max(complaint.affected_students_count or 1, complaint.upvote_count + 1)

        # Dynamic priority re-evaluation with updated community count
        pred = priority_predictor.predict(
            complaint.category,
            complaint.title,
            complaint.description,
            upvote_count=complaint.upvote_count,
        )

        old_priority = complaint.final_priority
        if pred["final_priority"] != old_priority:
            complaint.final_priority = pred["final_priority"]
            complaint.priority_explanation = pred["explanation"]
            db.add(ComplaintTimeline(
                complaint_id=complaint.id,
                action="Priority Adjusted (Community Support)",
                actor_id=target_user.id,
                remarks=f"Priority updated from {old_priority} to {pred['final_priority']} ({complaint.upvote_count} supporters).",
                from_status=complaint.status,
                to_status=complaint.status,
                timestamp=utc_now(),
            ))

        db.commit()
        db.refresh(complaint)

        return {
            "upvoted": True,
            "has_upvoted": True,
            "upvote_count": complaint.upvote_count,
            "final_priority": complaint.final_priority,
            "message": "Support registered successfully",
        }

    @staticmethod
    def remove_upvote(db: Session, complaint_id: int, user: Optional[User] = None, actor: Optional[User] = None) -> Dict[str, Any]:
        """Removes support vote from a complaint."""
        target_user = user or actor
        if not target_user:
            raise HTTPException(status_code=401, detail="Authentication required.")

        complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
        if not complaint:
            raise HTTPException(status_code=404, detail="Complaint not found")

        vote = db.query(ComplaintVote).filter(
            ComplaintVote.complaint_id == complaint_id,
            ComplaintVote.user_id == target_user.id,
        ).first()

        if vote:
            db.delete(vote)
            complaint.upvote_count = max(0, (complaint.upvote_count or 1) - 1)
            complaint.affected_students_count = max(1, complaint.upvote_count + 1)
            db.commit()
            db.refresh(complaint)

        return {
            "upvoted": False,
            "has_upvoted": False,
            "upvote_count": complaint.upvote_count or 0,
            "final_priority": complaint.final_priority,
            "message": "Support removed",
        }

    @staticmethod
    def post_internal_message(
        db: Session,
        complaint_id: int,
        officer: Optional[User] = None,
        message: str = "",
        attachment_url: Optional[str] = None,
        attachment_name: Optional[str] = None,
        actor: Optional[User] = None,
    ) -> InternalComplaintMessage:
        """
        Creates an internal discussion message strictly between authorized officer tiers.
        Students/faculty are barred from accessing this channel.
        """
        target_officer = officer or actor
        if not target_officer:
            raise HTTPException(status_code=401, detail="Authentication required.")

        complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
        if not complaint:
            raise HTTPException(status_code=404, detail="Complaint not found")

        if target_officer.role in [UserRole.STUDENT, UserRole.FACULTY]:
            raise HTTPException(status_code=403, detail="Students and faculty cannot access internal officer discussions.")

        now = utc_now()
        msg = InternalComplaintMessage(
            complaint_id=complaint_id,
            sender_id=target_officer.id,
            message=message.strip(),
            attachment_url=attachment_url,
            attachment_name=attachment_name,
            created_at=now,
        )
        db.add(msg)

        # Record timeline action
        db.add(ComplaintTimeline(
            complaint_id=complaint_id,
            action="Internal Officer Note Added",
            actor_id=target_officer.id,
            remarks=f"Internal note posted by {target_officer.full_name} ({target_officer.role.replace('_', ' ').title()}).",
            from_status=complaint.status,
            to_status=complaint.status,
            timestamp=now,
        ))

        # Deliver inter-tier notifications to relevant administrative authorities
        recipient_ids = set()
        if complaint.assigned_to_id and complaint.assigned_to_id != target_officer.id:
            recipient_ids.add(complaint.assigned_to_id)
        if complaint.department and complaint.department.grievance_officer_id and complaint.department.grievance_officer_id != target_officer.id:
            recipient_ids.add(complaint.department.grievance_officer_id)

        if target_officer.role != UserRole.GRIEVANCE_CELL:
            g_officers = db.query(User).filter(User.role == UserRole.GRIEVANCE_CELL, User.is_active == True).all()
            for u in g_officers:
                if u.id != target_officer.id:
                    recipient_ids.add(u.id)

        if complaint.current_tier == ComplaintTier.TIER_3 or target_officer.role == UserRole.GRIEVANCE_CELL:
            p_officers = db.query(User).filter(User.role == UserRole.PRINCIPAL, User.is_active == True).all()
            for u in p_officers:
                if u.id != target_officer.id:
                    recipient_ids.add(u.id)

        for rid in recipient_ids:
            db.add(Notification(
                user_id=rid,
                complaint_id=complaint.id,
                title=f"Inter-Tier Note on {complaint.grievance_id}",
                message=f"{target_officer.full_name} ({target_officer.role.replace('_', ' ').title()}) posted: '{message[:80]}...'",
                notification_type=NotificationType.STATUS_UPDATE,
            ))

        db.commit()
        db.refresh(msg)
        return msg

    @staticmethod
    def get_internal_messages(db: Session, complaint_id: int, officer: Optional[User] = None, actor: Optional[User] = None) -> List[InternalComplaintMessage]:
        """Returns all internal discussion messages for authorized officer roles."""
        target_officer = officer or actor
        if not target_officer or target_officer.role in [UserRole.STUDENT, UserRole.FACULTY]:
            raise HTTPException(status_code=403, detail="Access denied to internal officer discussions.")

        return (
            db.query(InternalComplaintMessage)
            .filter(InternalComplaintMessage.complaint_id == complaint_id)
            .order_by(InternalComplaintMessage.created_at.asc())
            .all()
        )

    @staticmethod
    def get_categories_summary(db: Session, campus: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns aggregated summary for all 14 official categories."""
        summaries = []
        for cat in ComplaintCategory.ALL:
            query = db.query(Complaint).filter(Complaint.category == cat, Complaint.is_duplicate == False)
            if campus and campus != "All":
                query = query.filter(Complaint.campus == campus)

            all_cat_complaints = query.all()
            total = len(all_cat_complaints)
            pending = len([c for c in all_cat_complaints if c.status not in [ComplaintStatus.RESOLVED, ComplaintStatus.CLOSED, ComplaintStatus.CONFIRMED_RESOLVED, ComplaintStatus.AUTO_CONFIRMED_RESOLVED]])
            resolved = len([c for c in all_cat_complaints if c.status in [ComplaintStatus.RESOLVED, ComplaintStatus.CLOSED, ComplaintStatus.CONFIRMED_RESOLVED, ComplaintStatus.AUTO_CONFIRMED_RESOLVED]])
            critical = len([c for c in all_cat_complaints if c.final_priority == ComplaintPriority.CRITICAL])
            summaries.append({
                "category": cat,
                "total_complaints": total,
                "pending_complaints": pending,
                "resolved_complaints": resolved,
                "critical_complaints": critical,
            })
        return summaries

