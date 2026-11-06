import asyncio
from datetime import datetime
from backend.app.database import SessionLocal
from backend.app.services.escalation_service import EscalationService
from backend.app.services.complaint_service import ComplaintService

class EscalationScheduler:
    def __init__(self, check_interval_seconds: int = 3600):
        self.check_interval_seconds = check_interval_seconds
        self._running = False
        self._task = None

    async def _loop(self):
        print(f"[EscalationScheduler] Background escalation & auto-confirmation monitor started (Interval: {self.check_interval_seconds}s).")
        while self._running:
            try:
                db = SessionLocal()
                try:
                    # 1. 15-day Tier escalation check
                    res = EscalationService.check_and_run_escalations(db)
                    if res["escalated_to_tier2"] or res["escalated_to_tier3"]:
                        print(f"[EscalationScheduler] Automated Escalation Executed: Tier 2={res['escalated_to_tier2']}, Tier 3={res['escalated_to_tier3']}")

                    # 2. 5-day Resolution Auto-Confirmation check
                    auto_conf = ComplaintService.check_and_run_auto_confirmations(db)
                    if auto_conf["total_processed"] > 0:
                        print(f"[EscalationScheduler] 5-Day Auto-Confirmation Executed: {auto_conf['total_processed']} cases resolved.")
                finally:
                    db.close()
            except Exception as e:
                print(f"[EscalationScheduler] Error during scheduled monitor check: {e}")

            await asyncio.sleep(self.check_interval_seconds)

    def start(self):
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._loop())

    def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            print("[EscalationScheduler] Background escalation monitor stopped.")

escalation_scheduler = EscalationScheduler()

