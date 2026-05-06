import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings

logger = logging.getLogger(__name__)


async def _morning_job():
    from app.database import SessionLocal
    from app.services.checker import run_morning_check, send_digest_if_needed

    db = SessionLocal()
    try:
        logger.info("Morning check starting...")
        summary = await run_morning_check(db)
        logger.info("Morning check done: %d checked, %d new posts", summary.total_checked, summary.total_new_posts)
        digest_sent = await send_digest_if_needed(db)
        logger.info("Digest sent: %s", digest_sent)
    finally:
        db.close()


def create_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=settings.TIMEZONE)
    scheduler.add_job(
        _morning_job,
        CronTrigger(hour=settings.MORNING_CHECK_HOUR, minute=settings.MORNING_CHECK_MINUTE,
                    timezone=settings.TIMEZONE),
        id="morning_check",
        name="Daily morning Instagram check",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    return scheduler
