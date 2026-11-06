from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db, utc_now
from backend.app.models.user import User, UserRole
from backend.app.models.announcement import InstitutionalAnnouncement
from backend.app.models.scholarship import ScholarshipAnnouncement
from backend.app.schemas.ticker import TickerAnnouncementItem, TickerAnnouncementCreate
from backend.app.auth.dependencies import get_current_user, get_optional_current_user, require_admin

router = APIRouter(prefix="/api/announcements", tags=["Institutional Announcements & Ticker"])

@router.get("/ticker", response_model=List[TickerAnnouncementItem])
def get_ticker_announcements(
    token_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns public and institutional announcement updates for the continuous News Ticker.
    Seamlessly integrates:
    1. Scholarship announcements (verification schedules, seal/signature camps, deadlines)
    2. Institutional campus updates (examination, safety, placement, facilities)
    Ordered by urgency (urgent notices first) and publication timestamp.
    """
    ticker_items: List[TickerAnnouncementItem] = []

    # 1. Scholarship Announcements (Part D Integration)
    sch_announcements = (
        db.query(ScholarshipAnnouncement)
        .filter(ScholarshipAnnouncement.status == "published")
        .order_by(ScholarshipAnnouncement.is_urgent.desc(), ScholarshipAnnouncement.created_at.desc())
        .limit(10)
        .all()
    )

    for sa in sch_announcements:
        pub_dt = sa.published_at or sa.created_at or utc_now()
        # Formulate informative ticker message with appointment/verification context
        event_str = ""
        if sa.event_location or sa.event_time_window:
            loc = sa.event_location or "Scholarship Section Room 104"
            time_w = f" ({sa.event_time_window})" if sa.event_time_window else ""
            event_str = f" [Scheduled: {loc}{time_w}]"

        msg_body = sa.description
        if len(msg_body) > 180:
            msg_body = msg_body[:177] + "..."

        full_message = f"{msg_body}{event_str}"

        # Extract primary destination link if available
        first_url = None
        if sa.links_and_documents:
            lines = [line.strip() for line in sa.links_and_documents.splitlines() if line.strip().startswith("http")]
            if lines:
                first_url = lines[0]

        ticker_items.append(
            TickerAnnouncementItem(
                id=sa.id + 10000, # Namespaced ID
                title=f"{sa.scholarship_name}: {sa.title}",
                message=full_message,
                category="Scholarship",
                publication_date=pub_dt.strftime("%d %b %Y"),
                publication_time=pub_dt.strftime("%I:%M %p"),
                priority="High" if sa.is_urgent else "Normal",
                is_urgent=bool(sa.is_urgent),
                is_active=True,
                destination_route="scholarships",
                destination_url=first_url,
                created_at=pub_dt,
            )
        )

    # 2. General Institutional Announcements
    general_announcements = (
        db.query(InstitutionalAnnouncement)
        .filter(InstitutionalAnnouncement.is_active == True)
        .order_by(InstitutionalAnnouncement.is_urgent.desc(), InstitutionalAnnouncement.created_at.desc())
        .limit(10)
        .all()
    )

    for ga in general_announcements:
        pub_dt = ga.published_at or ga.created_at or utc_now()
        ticker_items.append(
            TickerAnnouncementItem(
                id=ga.id,
                title=ga.title,
                message=ga.message,
                category=ga.category,
                publication_date=pub_dt.strftime("%d %b %Y"),
                publication_time=pub_dt.strftime("%I:%M %p"),
                priority=ga.priority,
                is_urgent=bool(ga.is_urgent),
                is_active=bool(ga.is_active),
                destination_route=ga.destination_route or "dashboard",
                destination_url=ga.destination_url,
                created_at=pub_dt,
            )
        )

    # Sort: Urgent first, then newest first
    ticker_items.sort(key=lambda x: (not x.is_urgent, -x.created_at.timestamp()))
    return ticker_items

@router.get("/all", response_model=List[TickerAnnouncementItem])
def get_all_announcements(
    token_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """Returns complete list of announcements for the ALL UPDATES destination view."""
    return get_ticker_announcements(token_user=token_user, db=db)

@router.post("", response_model=TickerAnnouncementItem, status_code=status.HTTP_201_CREATED)
def create_institutional_announcement(
    payload: TickerAnnouncementCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Super Admin endpoint to publish general institutional announcements across the ticker."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to publish announcements."
        )
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.PRINCIPAL, UserRole.GRIEVANCE_CELL]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Super Admin or Institutional Authorities can publish campus announcements."
        )

    now = utc_now()
    ann = InstitutionalAnnouncement(
        title=payload.title.strip(),
        message=payload.message.strip(),
        category=payload.category.strip(),
        priority=payload.priority.strip(),
        is_urgent=payload.is_urgent,
        is_active=payload.is_active,
        destination_route=payload.destination_route,
        destination_url=payload.destination_url,
        author_id=current_user.id,
        published_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(ann)
    db.commit()
    db.refresh(ann)

    return TickerAnnouncementItem(
        id=ann.id,
        title=ann.title,
        message=ann.message,
        category=ann.category,
        publication_date=ann.published_at.strftime("%d %b %Y"),
        publication_time=ann.published_at.strftime("%I:%M %p"),
        priority=ann.priority,
        is_urgent=bool(ann.is_urgent),
        is_active=bool(ann.is_active),
        destination_route=ann.destination_route,
        destination_url=ann.destination_url,
        created_at=ann.created_at,
    )
