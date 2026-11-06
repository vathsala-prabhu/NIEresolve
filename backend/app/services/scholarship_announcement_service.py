from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from backend.app.database import utc_now
from backend.app.models.user import User, UserRole
from backend.app.models.scholarship import (
    Scholarship,
    ScholarshipAnnouncement,
    ScholarshipApplication,
    ScholarshipStageSchedule,
)
from backend.app.models.notification import Notification, NotificationType
from backend.app.models.audit import AuditLog
from backend.app.schemas.scholarship_announcement import (
    ScholarshipAnnouncementCreate,
    ScholarshipAnnouncementUpdate,
    ScholarshipAnnouncementResponse,
    StageScheduleUpdate,
    StageScheduleResponse,
    ApplicationProgressResponse,
    CoordinatorSummaryResponse,
    ScholarshipModuleStats,
)

class ScholarshipAnnouncementService:

    @staticmethod
    def _format_announcement(a: ScholarshipAnnouncement) -> ScholarshipAnnouncementResponse:
        author_name = a.author.full_name if a.author else "Institutional Coordinator"
        author_role = a.author.role.replace("_", " ").title() if a.author else "Coordinator"
        return ScholarshipAnnouncementResponse(
            id=a.id,
            scholarship_name=a.scholarship_name,
            title=a.title,
            description=a.description,
            eligibility_criteria=a.eligibility_criteria,
            application_start_date=a.application_start_date,
            application_deadline=a.application_deadline,
            links_and_documents=a.links_and_documents,
            event_date=a.event_date,
            event_time_window=a.event_time_window,
            event_location=a.event_location,
            required_documents=a.required_documents,
            responsible_authority=a.responsible_authority,
            seal_signature_instructions=a.seal_signature_instructions,
            status=a.status,
            is_urgent=bool(a.is_urgent),
            author_id=a.author_id,
            author_name=author_name,
            author_role=author_role,
            published_at=a.published_at,
            created_at=a.created_at,
            updated_at=a.updated_at,
        )

    @staticmethod
    def get_announcements(
        db: Session,
        only_published: bool = False,
    ) -> List[ScholarshipAnnouncementResponse]:
        query = db.query(ScholarshipAnnouncement)
        if only_published:
            query = query.filter(ScholarshipAnnouncement.status == "published")
        query = query.order_by(
            ScholarshipAnnouncement.is_urgent.desc(),
            ScholarshipAnnouncement.created_at.desc(),
        )
        items = query.all()
        return [ScholarshipAnnouncementService._format_announcement(a) for a in items]

    @staticmethod
    def get_announcement_by_id(db: Session, announcement_id: int) -> Optional[ScholarshipAnnouncement]:
        return db.query(ScholarshipAnnouncement).filter(ScholarshipAnnouncement.id == announcement_id).first()

    @staticmethod
    def _notify_students_without_duplicates(db: Session, title: str, message: str):
        """
        Broadcasting notification to all active students.
        Safely avoids duplicate notifications by checking (user_id, title).
        """
        students = db.query(User).filter(User.role == UserRole.STUDENT, User.is_active == True).all()
        for s in students:
            existing = db.query(Notification).filter(
                Notification.user_id == s.id,
                Notification.title == title,
                Notification.notification_type == NotificationType.SCHOLARSHIP,
            ).first()
            if not existing:
                notif = Notification(
                    user_id=s.id,
                    title=title,
                    message=message,
                    notification_type=NotificationType.SCHOLARSHIP,
                    is_read=False,
                    created_at=utc_now(),
                )
                db.add(notif)
        db.commit()

    @staticmethod
    def create_announcement(
        db: Session,
        payload: ScholarshipAnnouncementCreate,
        author: User,
    ) -> ScholarshipAnnouncementResponse:
        now = utc_now()
        is_pub = payload.status == "published"
        announcement = ScholarshipAnnouncement(
            scholarship_name=payload.scholarship_name,
            title=payload.title,
            description=payload.description,
            eligibility_criteria=payload.eligibility_criteria,
            application_start_date=payload.application_start_date,
            application_deadline=payload.application_deadline,
            links_and_documents=payload.links_and_documents,
            event_date=payload.event_date,
            event_time_window=payload.event_time_window,
            event_location=payload.event_location,
            required_documents=payload.required_documents,
            responsible_authority=payload.responsible_authority or author.full_name,
            seal_signature_instructions=payload.seal_signature_instructions,
            is_urgent=payload.is_urgent,
            status=payload.status,
            author_id=author.id,
            published_at=now if is_pub else None,
            created_at=now,
            updated_at=now,
        )
        db.add(announcement)
        db.commit()
        db.refresh(announcement)

        # Audit log
        db.add(AuditLog(
            actor_id=author.id,
            action="CREATE_SCHOLARSHIP_ANNOUNCEMENT",
            entity_type="scholarship_announcement",
            entity_id=str(announcement.id),
            details=f"Announcement '{announcement.title}' created with status '{announcement.status}'",
            created_at=now,
        ))
        db.commit()

        # Send non-duplicate notification to students if published
        if is_pub:
            notif_title = f"New Scholarship Update: {announcement.scholarship_name}"
            event_info = f" (Event: {announcement.event_time_window} at {announcement.event_location})" if announcement.event_location else ""
            notif_msg = f"{announcement.title}. {announcement.description[:140]}...{event_info}"
            ScholarshipAnnouncementService._notify_students_without_duplicates(db, notif_title, notif_msg)

        return ScholarshipAnnouncementService._format_announcement(announcement)

    @staticmethod
    def update_announcement(
        db: Session,
        announcement_id: int,
        payload: ScholarshipAnnouncementUpdate,
        author: User,
    ) -> ScholarshipAnnouncementResponse:
        announcement = db.query(ScholarshipAnnouncement).filter(ScholarshipAnnouncement.id == announcement_id).first()
        if not announcement:
            raise ValueError(f"Scholarship announcement {announcement_id} not found.")

        old_status = announcement.status
        now = utc_now()

        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(announcement, field, value)

        announcement.updated_at = now
        if payload.status == "published" and old_status != "published" and not announcement.published_at:
            announcement.published_at = now

        db.commit()
        db.refresh(announcement)

        # Audit log
        db.add(AuditLog(
            actor_id=author.id,
            action="UPDATE_SCHOLARSHIP_ANNOUNCEMENT",
            entity_type="scholarship_announcement",
            entity_id=str(announcement.id),
            details=f"Announcement updated by {author.full_name} ({author.role})",
            created_at=now,
        ))
        db.commit()

        # If updated with new schedule or published status, notify students without duplicates
        if announcement.status == "published":
            notif_title = f"Updated Schedule: {announcement.scholarship_name}"
            notif_msg = f"{announcement.title}: Updates made to appointment/verification schedule at {announcement.event_location or 'Scholarship Section'}."
            ScholarshipAnnouncementService._notify_students_without_duplicates(db, notif_title, notif_msg)

        return ScholarshipAnnouncementService._format_announcement(announcement)

    @staticmethod
    def withdraw_announcement(
        db: Session,
        announcement_id: int,
        author: User,
    ) -> ScholarshipAnnouncementResponse:
        announcement = db.query(ScholarshipAnnouncement).filter(ScholarshipAnnouncement.id == announcement_id).first()
        if not announcement:
            raise ValueError(f"Scholarship announcement {announcement_id} not found.")

        now = utc_now()
        announcement.status = "withdrawn"
        announcement.updated_at = now

        db.add(AuditLog(
            actor_id=author.id,
            action="WITHDRAW_SCHOLARSHIP_ANNOUNCEMENT",
            entity_type="scholarship_announcement",
            entity_id=str(announcement.id),
            details=f"Announcement '{announcement.title}' withdrawn by {author.full_name}",
            created_at=now,
        ))
        db.commit()
        db.refresh(announcement)
        return ScholarshipAnnouncementService._format_announcement(announcement)

    @staticmethod
    def get_student_applications(
        db: Session,
        student_user_id: int,
    ) -> List[ApplicationProgressResponse]:
        apps = (
            db.query(ScholarshipApplication)
            .filter(ScholarshipApplication.student_id == student_user_id)
            .order_by(ScholarshipApplication.updated_at.desc())
            .all()
        )
        results = []
        for a in apps:
            stages_resp = [
                StageScheduleResponse(
                    id=s.id,
                    stage_name=s.stage_name,
                    stage_order=s.stage_order,
                    status=s.status,
                    expected_date=s.expected_date,
                    expected_time_window=s.expected_time_window,
                    location_or_office=s.location_or_office,
                    required_documents=s.required_documents,
                    responsible_authority=s.responsible_authority,
                    seal_signature_instructions=s.seal_signature_instructions,
                    officer_remarks=s.officer_remarks,
                    completed_at=s.completed_at,
                    updated_at=s.updated_at,
                )
                for s in a.stages
            ]
            results.append(
                ApplicationProgressResponse(
                    id=a.id,
                    scholarship_id=a.scholarship_id,
                    scholarship_name=a.scholarship_name,
                    student_id=a.student_id,
                    application_number=a.application_number,
                    current_stage=a.current_stage,
                    status=a.status,
                    submitted_at=a.submitted_at,
                    updated_at=a.updated_at,
                    stages=stages_resp,
                )
            )
        return results

    @staticmethod
    def update_stage_schedule(
        db: Session,
        stage_id: int,
        payload: StageScheduleUpdate,
        officer: User,
    ) -> StageScheduleResponse:
        stage = db.query(ScholarshipStageSchedule).filter(ScholarshipStageSchedule.id == stage_id).first()
        if not stage:
            raise ValueError(f"Stage schedule {stage_id} not found.")

        now = utc_now()
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(stage, field, value)

        if payload.status == "completed" and not stage.completed_at:
            stage.completed_at = now

        stage.updated_at = now
        app = stage.application
        if app:
            app.updated_at = now
            if payload.status == "completed":
                # Find next stage
                next_stage = (
                    db.query(ScholarshipStageSchedule)
                    .filter(
                        ScholarshipStageSchedule.application_id == app.id,
                        ScholarshipStageSchedule.stage_order > stage.stage_order,
                    )
                    .order_by(ScholarshipStageSchedule.stage_order.asc())
                    .first()
                )
                if next_stage:
                    app.current_stage = next_stage.stage_name
                    if next_stage.status == "pending":
                        next_stage.status = "in_progress"
                else:
                    app.current_stage = "Final Approval Granted"
                    app.status = "approved"

        db.commit()
        db.refresh(stage)

        # Notify student about stage update without duplicates
        if app and app.student_id:
            notif_title = f"Scholarship Stage Update: {stage.stage_name}"
            loc_info = f" at {stage.location_or_office}" if stage.location_or_office else ""
            time_info = f" ({stage.expected_time_window})" if stage.expected_time_window else ""
            notif_msg = f"Your application {app.application_number} is now at stage: '{stage.stage_name}'. Status: {stage.status.upper()}{loc_info}{time_info}. Instructions: {stage.seal_signature_instructions or 'Please check portal details.'}"
            
            # Check duplicate
            existing = db.query(Notification).filter(
                Notification.user_id == app.student_id,
                Notification.title == notif_title,
                Notification.message == notif_msg,
            ).first()
            if not existing:
                db.add(Notification(
                    user_id=app.student_id,
                    title=notif_title,
                    message=notif_msg,
                    notification_type=NotificationType.SCHOLARSHIP,
                    is_read=False,
                    created_at=now,
                ))
                db.commit()

        # Audit log
        db.add(AuditLog(
            actor_id=officer.id,
            action="UPDATE_SCHOLARSHIP_STAGE",
            entity_type="scholarship_stage",
            entity_id=str(stage.id),
            details=f"Stage '{stage.stage_name}' status set to '{stage.status}' by {officer.full_name}",
            created_at=now,
        ))
        db.commit()

        return StageScheduleResponse(
            id=stage.id,
            stage_name=stage.stage_name,
            stage_order=stage.stage_order,
            status=stage.status,
            expected_date=stage.expected_date,
            expected_time_window=stage.expected_time_window,
            location_or_office=stage.location_or_office,
            required_documents=stage.required_documents,
            responsible_authority=stage.responsible_authority,
            seal_signature_instructions=stage.seal_signature_instructions,
            officer_remarks=stage.officer_remarks,
            completed_at=stage.completed_at,
            updated_at=stage.updated_at,
        )

    @staticmethod
    def get_module_stats(db: Session) -> ScholarshipModuleStats:
        total_sch = db.query(Scholarship).filter(Scholarship.is_active == True).count()
        pub_announcements = db.query(ScholarshipAnnouncement).filter(ScholarshipAnnouncement.status == "published").count()
        act_apps = db.query(ScholarshipApplication).filter(ScholarshipApplication.status.in_(["submitted", "in_progress"])).count()
        upcoming_appointments = (
            db.query(ScholarshipStageSchedule)
            .filter(
                ScholarshipStageSchedule.status.in_(["pending", "in_progress"]),
                ScholarshipStageSchedule.expected_date != None,
            )
            .count()
        )
        return ScholarshipModuleStats(
            total_scholarships=total_sch,
            published_announcements=pub_announcements,
            active_applications=act_apps,
            upcoming_appointments=upcoming_appointments,
        )

    @staticmethod
    def get_coordinators(db: Session) -> List[CoordinatorSummaryResponse]:
        users = db.query(User).filter(
            or_(
                User.role == UserRole.SCHOLARSHIP_COORDINATOR,
                User.can_publish_scholarships == True,
                User.role.in_([UserRole.FACULTY, UserRole.DEPT_OFFICER, UserRole.GRIEVANCE_CELL]),
            )
        ).all()

        results = []
        for u in users:
            ann_count = db.query(ScholarshipAnnouncement).filter(ScholarshipAnnouncement.author_id == u.id).count()
            results.append(CoordinatorSummaryResponse(
                id=u.id,
                full_name=u.full_name,
                email=u.email,
                role=u.role,
                can_publish_scholarships=bool(u.can_publish_scholarships or u.role == UserRole.SCHOLARSHIP_COORDINATOR),
                announcements_count=ann_count,
            ))
        return results

    @staticmethod
    def set_coordinator_permission(
        db: Session,
        user_id: int,
        can_publish: bool,
        admin: User,
    ) -> CoordinatorSummaryResponse:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found.")

        user.can_publish_scholarships = can_publish
        db.commit()

        # Audit log
        db.add(AuditLog(
            actor_id=admin.id,
            action="SET_SCHOLARSHIP_COORDINATOR_PERMISSION",
            entity_type="user",
            entity_id=str(user.id),
            details=f"Admin {admin.full_name} set can_publish_scholarships={can_publish} for {user.full_name}",
            created_at=utc_now(),
        ))
        db.commit()

        ann_count = db.query(ScholarshipAnnouncement).filter(ScholarshipAnnouncement.author_id == user.id).count()
        return CoordinatorSummaryResponse(
            id=user.id,
            full_name=user.full_name,
            email=user.email,
            role=user.role,
            can_publish_scholarships=bool(user.can_publish_scholarships or user.role == UserRole.SCHOLARSHIP_COORDINATOR),
            announcements_count=ann_count,
        )

