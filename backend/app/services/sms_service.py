import os
import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database import utc_now, SessionLocal
from backend.app.models.complaint import SmsLog, Complaint
from backend.app.models.user import User

logger = logging.getLogger("NIEresolve.SMS")

# Pre-approved institutional SMS templates (DLT-compliant format)
SMS_TEMPLATES = {
    "complaint_registered": "Hello {name}, your grievance has been successfully registered on NIEresolve. Complaint ID: {grievance_id}. You can track its progress through the NIEresolve portal.",
    "complaint_resolved": "Your NIEresolve complaint {grievance_id} has been marked as resolved by the concerned authority. Please log in to confirm whether the issue has been fixed.",
    "complaint_escalated": "Alert: Your NIEresolve complaint {grievance_id} has been escalated to {tier} for higher-level administrative intervention.",
    "complaint_reopened": "Update: NIEresolve complaint {grievance_id} has been reopened by the complainant with remarks: '{remarks}'. Action required.",
    "auto_confirmed": "Notification: Complaint {grievance_id} was auto-confirmed as resolved following the 5-day confirmation window.",
    "evidence_requested": "Notice: Additional supporting evidence requested for NIEresolve complaint {grievance_id}. Please upload via portal.",
}

class SmsService:
    @staticmethod
    def send_sms(
        recipient_phone: str,
        event_type: str,
        template_params: Dict[str, Any],
        complaint_id: Optional[int] = None,
        recipient_id: Optional[int] = None,
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """
        Dispatches SMS notification to registered student or faculty mobile number.
        Renders template, checks provider (Twilio, MSG91, or test_logger), records audit log in DB.
        """
        if not recipient_phone:
            logger.warning(f"[SMS] Skipped dispatch: no recipient phone number provided for event '{event_type}'.")
            return {"status": "skipped", "reason": "No phone number registered"}

        # Format template message
        template_str = SMS_TEMPLATES.get(
            event_type,
            "Notification from NIEresolve: Update on complaint {grievance_id}."
        )
        try:
            message_body = template_str.format(**template_params)
        except Exception:
            message_body = template_str

        provider = settings.SMS_PROVIDER.lower()
        delivery_status = "sent"
        error_msg = None

        # 1. Twilio Integration (if configured)
        if provider == "twilio" and settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
            try:
                import urllib.request, urllib.parse, base64, json
                url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Messages.json"
                auth = base64.b64encode(f"{settings.TWILIO_ACCOUNT_SID}:{settings.TWILIO_AUTH_TOKEN}".encode()).decode()
                data = urllib.parse.urlencode({
                    "From": settings.TWILIO_PHONE_NUMBER,
                    "To": recipient_phone,
                    "Body": message_body,
                }).encode()
                req = urllib.request.Request(url, data=data, headers={
                    "Authorization": f"Basic {auth}",
                    "Content-Type": "application/x-www-form-urlencoded",
                })
                with urllib.request.urlopen(req, timeout=10) as resp:
                    resp_data = json.loads(resp.read().decode())
                    delivery_status = resp_data.get("status", "sent")
                    logger.info(f"[SMS - Twilio] Delivered to {recipient_phone}: SID {resp_data.get('sid')}")
            except Exception as e:
                delivery_status = "failed"
                error_msg = str(e)
                logger.error(f"[SMS - Twilio Error] Failed to send SMS to {recipient_phone}: {e}")

        # 2. MSG91 Integration (if configured)
        elif provider == "msg91" and settings.MSG91_AUTH_KEY:
            try:
                import urllib.request, json
                url = "https://control.msg91.com/api/v5/flow/"
                payload = json.dumps({
                    "template_id": settings.MSG91_DLT_TE_ID or "default_dlt_template",
                    "sender": settings.MSG91_SENDER_ID,
                    "short_url": "0",
                    "recipients": [{"mobiles": recipient_phone, **template_params}],
                }).encode()
                req = urllib.request.Request(url, data=payload, headers={
                    "authkey": settings.MSG91_AUTH_KEY,
                    "Content-Type": "application/json",
                })
                with urllib.request.urlopen(req, timeout=10) as resp:
                    delivery_status = "sent"
                    logger.info(f"[SMS - MSG91] Dispatched flow to {recipient_phone}")
            except Exception as e:
                delivery_status = "failed"
                error_msg = str(e)
                logger.error(f"[SMS - MSG91 Error] Failed to send SMS to {recipient_phone}: {e}")

        # 3. Test Mode / Safe Logger (Default in development without active SMS gateway)
        else:
            provider = "test_logger"
            delivery_status = "logged_test_mode"
            print(f"\n[SMS Service - TEST MODE]")
            print(f"  To: {recipient_phone}")
            print(f"  Event: {event_type}")
            print(f"  Message: {message_body}")
            print(f"  Time: {utc_now().isoformat()}\n")

        # Record in database log
        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True

        try:
            log_entry = SmsLog(
                recipient_phone=recipient_phone,
                recipient_id=recipient_id,
                complaint_id=complaint_id,
                message=message_body,
                event_type=event_type,
                provider=provider,
                status=delivery_status,
                error_message=error_msg,
                created_at=utc_now(),
            )
            db.add(log_entry)
            db.commit()
        except Exception as log_err:
            logger.warning(f"[SMS Service] Could not write SMS log to database: {log_err}")
            db.rollback()
        finally:
            if close_db:
                db.close()

        return {
            "status": delivery_status,
            "provider": provider,
            "recipient_phone": recipient_phone,
            "event_type": event_type,
            "error": error_msg,
        }

