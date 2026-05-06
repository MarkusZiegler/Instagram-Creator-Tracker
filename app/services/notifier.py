import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader

from app.config import settings

if TYPE_CHECKING:
    from app.models import Post

logger = logging.getLogger(__name__)

_jinja_env = Environment(loader=FileSystemLoader("app/templates"))


def send_digest(posts_by_creator: dict[str, list["Post"]]) -> bool:
    if not settings.SMTP_USERNAME or not settings.NOTIFY_EMAIL:
        _log_digest(posts_by_creator)
        return False

    total_posts = sum(len(p) for p in posts_by_creator.values())
    creator_count = len(posts_by_creator)
    subject = f"Instagram Updates – {total_posts} neue Posts von {creator_count} Creator{'n' if creator_count != 1 else ''}"

    try:
        html_body = _render_html(posts_by_creator)
        plain_body = _render_plain(posts_by_creator)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.SMTP_USERNAME
        msg["To"] = settings.NOTIFY_EMAIL
        msg.attach(MIMEText(plain_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            smtp.sendmail(settings.SMTP_USERNAME, settings.NOTIFY_EMAIL, msg.as_string())

        logger.info("Digest sent to %s (%d posts from %d creators)", settings.NOTIFY_EMAIL, total_posts, creator_count)
        return True

    except Exception as e:
        logger.error("Failed to send digest email: %s", e)
        return False


def send_test_email() -> bool:
    if not settings.SMTP_USERNAME or not settings.NOTIFY_EMAIL:
        logger.info("TEST DIGEST: SMTP not configured - would send test email to %s", settings.NOTIFY_EMAIL)
        return False
    return send_digest({"test_account": []})


def _render_html(posts_by_creator: dict[str, list["Post"]]) -> str:
    template = _jinja_env.get_template("email/digest.html")
    return template.render(posts_by_creator=posts_by_creator, settings=settings)


def _render_plain(posts_by_creator: dict[str, list["Post"]]) -> str:
    lines = ["Instagram Updates\n" + "=" * 40]
    for username, posts in posts_by_creator.items():
        lines.append(f"\n@{username} – {len(posts)} neue Posts")
        for post in posts[:5]:
            lines.append(f"  {post.posted_at.strftime('%d.%m.%Y')} – {post.post_url}")
            if post.caption:
                lines.append(f"  {post.caption[:120]}...")
    return "\n".join(lines)


def _log_digest(posts_by_creator: dict[str, list["Post"]]) -> None:
    logger.info("DIGEST (SMTP not configured):\n%s", _render_plain(posts_by_creator))
