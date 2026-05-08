import asyncio
import logging
import random
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.models import CheckLog, Creator, Post
from app.schemas import CheckSummary
from app.services.instagram import InstagramService, ProfileNotFoundError, RateLimitedError

logger = logging.getLogger(__name__)

_ig_service: InstagramService | None = None


def _get_ig_service() -> InstagramService:
    global _ig_service
    if _ig_service is None:
        _ig_service = InstagramService(settings.INSTAGRAM_SESSION_FILE)
    return _ig_service


async def run_morning_check(db: Session) -> CheckSummary:
    ig = _get_ig_service()
    creators = (
        db.query(Creator)
        .filter(Creator.is_active == True)
        .order_by(Creator.last_checked_at.asc().nullsfirst())
        .all()
    )

    total_checked = 0
    total_new = 0
    errors = 0
    rate_limited = False

    for creator in creators:
        try:
            new_posts = ig.get_new_posts(
                username=creator.username,
                since_shortcode=creator.last_post_shortcode,
                max_posts=settings.MAX_POSTS_PER_CREATOR_PER_CHECK,
            )

            for pd in new_posts:
                existing = db.query(Post).filter(Post.shortcode == pd.shortcode).first()
                if not existing:
                    db.add(Post(
                        creator_id=creator.id,
                        shortcode=pd.shortcode,
                        post_url=pd.post_url,
                        thumbnail_url=pd.thumbnail_url,
                        caption=pd.caption,
                        post_type=pd.post_type,
                        like_count=pd.like_count,
                        comment_count=pd.comment_count,
                        posted_at=pd.posted_at,
                        is_new=True,
                    ))

            if new_posts:
                creator.last_post_shortcode = new_posts[0].shortcode

            creator.last_checked_at = datetime.now(timezone.utc)
            db.add(CheckLog(creator_id=creator.id, new_posts_found=len(new_posts), status="success"))
            db.commit()

            total_checked += 1
            total_new += len(new_posts)
            logger.info("Checked @%s: %d new posts", creator.username, len(new_posts))

            delay = random.uniform(settings.DELAY_BETWEEN_CREATORS_MIN, settings.DELAY_BETWEEN_CREATORS_MAX)
            await asyncio.sleep(delay)

        except RateLimitedError as e:
            db.add(CheckLog(creator_id=creator.id, new_posts_found=0, status="rate_limited",
                            error_message=str(e)))
            db.commit()
            rate_limited = True
            logger.warning("Rate limited after %d creators: %s. Stopping check.", total_checked, e)
            break

        except ProfileNotFoundError:
            db.add(CheckLog(creator_id=creator.id, new_posts_found=0, status="not_found",
                            error_message="Profile not found or private"))
            db.commit()
            errors += 1
            logger.warning("@%s not found or private - skipping (not deactivated)", creator.username)

        except Exception as e:
            db.add(CheckLog(creator_id=creator.id, new_posts_found=0, status="error",
                            error_message=str(e)[:500]))
            db.commit()
            errors += 1
            logger.error("Error checking @%s: %s", creator.username, e)

    return CheckSummary(
        total_checked=total_checked,
        total_new_posts=total_new,
        errors=errors,
        rate_limited=rate_limited,
        digest_sent=False,
    )


async def send_digest_if_needed(db: Session) -> bool:
    from app.services.notifier import send_digest

    new_posts = (
        db.query(Post)
        .filter(Post.is_new == True)
        .order_by(Post.posted_at.desc())
        .all()
    )

    if not new_posts:
        logger.info("No new posts - skipping digest")
        return False

    posts_by_creator: dict[str, list[Post]] = {}
    for post in new_posts:
        key = post.creator.username
        posts_by_creator.setdefault(key, []).append(post)

    sent = send_digest(posts_by_creator)

    if sent:
        for post in new_posts:
            post.is_new = False
        db.commit()
        logger.info("Digest sent, %d posts marked as seen", len(new_posts))

    return sent
