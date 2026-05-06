import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CheckLog
from app.schemas import CheckSummary, CheckLogOut

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/jobs")


@router.post("/check-now", response_model=CheckSummary)
async def check_now(db: Session = Depends(get_db)):
    from app.services.checker import run_morning_check, send_digest_if_needed
    summary = await run_morning_check(db)
    summary.digest_sent = await send_digest_if_needed(db)
    return summary


@router.post("/test-notify")
async def test_notify(db: Session = Depends(get_db)):
    from app.services.notifier import send_test_email
    send_test_email()
    return {"ok": True, "message": "Test email sent (check logs if SMTP not configured)"}


@router.get("/status", response_model=list[CheckLogOut])
def job_status(limit: int = 20, db: Session = Depends(get_db)):
    return (
        db.query(CheckLog)
        .order_by(CheckLog.checked_at.desc())
        .limit(limit)
        .all()
    )
