import os
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.user import User, UserRole
from backend.app.models.complaint import Complaint, ComplaintEvidence, ComplaintTimeline
from backend.app.schemas.complaint import EvidenceVerifyRequest, EvidenceResponse
from backend.app.auth.dependencies import get_current_user, require_any_officer
from backend.app.models.notification import Notification, NotificationType
from backend.app.config import settings

router = APIRouter(prefix="/api/evidence", tags=["Evidence Verification"])

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".pdf"}

@router.post("/upload/{complaint_id}")
async def upload_evidence(
    complaint_id: int,
    file: UploadFile = File(...),
    is_confidential: bool = Form(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Securely uploads evidence file (photograph / document) and associates with grievance.
    Validates file extension, assigns non-colliding UUID filename, and saves metadata.
    """
    comp = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Complaint not found")

    # Authorize upload: complainant or officer
    is_owner = comp.complainant_id == current_user.id
    is_officer = current_user.role in [
        UserRole.DEPT_OFFICER,
        UserRole.GRIEVANCE_CELL,
        UserRole.PRINCIPAL,
        UserRole.SUPER_ADMIN,
    ]
    if not is_owner and not is_officer:
        raise HTTPException(status_code=403, detail="Not authorized to attach evidence to this complaint.")

    # Validate file extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed formats: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Ensure upload directory exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    unique_filename = f"{uuid.uuid4().hex}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{ext}"
    dest_path = os.path.join(settings.UPLOAD_DIR, unique_filename)

    file_size = 0
    content = await file.read()
    file_size = len(content)

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file_size > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds maximum limit of {settings.MAX_UPLOAD_SIZE_MB}MB.",
        )

    with open(dest_path, "wb") as f:
        f.write(content)

    file_url = f"/uploads/{unique_filename}"

    evidence = ComplaintEvidence(
        complaint_id=comp.id,
        file_url=file_url,
        file_name=file.filename,
        file_type=file.content_type,
        file_size_bytes=file_size,
        verification_status="pending_verification",
        is_confidential=is_confidential,
        created_at=datetime.utcnow(),
    )
    db.add(evidence)

    # Log to timeline
    db.add(ComplaintTimeline(
        complaint_id=comp.id,
        action="Evidence Uploaded",
        actor_id=current_user.id,
        remarks=f"Uploaded '{file.filename}' ({round(file_size / 1024, 1)} KB). Pending officer verification.",
        from_status=comp.status,
        to_status=comp.status,
        timestamp=datetime.utcnow(),
    ))

    db.commit()
    db.refresh(evidence)

    return {
        "message": "Evidence uploaded successfully.",
        "evidence_id": evidence.id,
        "file_url": evidence.file_url,
        "verification_status": evidence.verification_status,
    }

@router.post("/verify")
def verify_evidence(
    payload: EvidenceVerifyRequest,
    current_user: User = Depends(require_any_officer),
    db: Session = Depends(get_db),
):
    """
    Authorized officer verifies or rejects submitted photographic/document evidence.
    Verification statuses: 'verified', 'rejected', 'requires_additional_evidence'.
    """
    valid_statuses = {"verified", "rejected", "requires_additional_evidence"}
    if payload.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Status must be one of: {valid_statuses}")

    evidence = db.query(ComplaintEvidence).filter(ComplaintEvidence.id == payload.evidence_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence item not found")

    now = datetime.utcnow()
    evidence.verification_status = payload.status
    evidence.officer_remarks = payload.officer_remarks
    evidence.verified_by_id = current_user.id
    evidence.verified_at = now

    comp = evidence.complaint

    # Update complaint status if initial verification
    if comp.status == "submitted" and payload.status == "verified":
        comp.status = "verified"

    status_display = payload.status.replace("_", " ").title()
    remarks_text = f"Evidence '{evidence.file_name}' marked as {status_display} by {current_user.full_name}."
    if payload.officer_remarks:
        remarks_text += f" Remarks: {payload.officer_remarks}"

    db.add(ComplaintTimeline(
        complaint_id=comp.id,
        action=f"Evidence {status_display}",
        actor_id=current_user.id,
        remarks=remarks_text,
        from_status=comp.status,
        to_status=comp.status,
        timestamp=now,
    ))

    # Notify complainant
    db.add(Notification(
        user_id=comp.complainant_id,
        complaint_id=comp.id,
        title=f"Evidence Verification: {comp.grievance_id}",
        message=f"Evidence for {comp.grievance_id} is marked as '{status_display}'.",
        notification_type=NotificationType.VERIFICATION,
    ))

    db.commit()
    db.refresh(evidence)

    return {
        "message": f"Evidence status updated to {payload.status}.",
        "evidence_id": evidence.id,
        "status": evidence.verification_status,
        "officer_remarks": evidence.officer_remarks,
    }
