import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import instaloader

logger = logging.getLogger(__name__)


class RateLimitedError(Exception):
    pass


class ProfileNotFoundError(Exception):
    pass


@dataclass
class PostData:
    shortcode: str
    post_url: str
    thumbnail_url: Optional[str]
    caption: Optional[str]
    post_type: str
    like_count: Optional[int]
    comment_count: Optional[int]
    posted_at: datetime


@dataclass
class ProfileData:
    username: str
    display_name: Optional[str]
    bio: Optional[str]
    follower_count: Optional[int]
    profile_pic_url: Optional[str]
    latest_post_shortcode: Optional[str]


class InstagramService:
    def __init__(self, session_file: str):
        self.session_file = session_file
        self.loader = instaloader.Instaloader(
            download_pictures=False,
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
            quiet=True,
        )
        self._try_load_session()

    def _try_load_session(self) -> None:
        if os.path.exists(self.session_file):
            try:
                self.loader.load_session_from_file(
                    username=None,
                    filename=self.session_file,
                )
                logger.info("Instagram session loaded from %s", self.session_file)
                return
            except Exception as e:
                logger.warning("Could not load session file: %s", e)

        from app.config import settings
        if settings.INSTAGRAM_USERNAME and settings.INSTAGRAM_PASSWORD:
            try:
                self.loader.login(settings.INSTAGRAM_USERNAME, settings.INSTAGRAM_PASSWORD)
                self.loader.save_session_to_file(self.session_file)
                logger.info("Logged in as %s, session saved", settings.INSTAGRAM_USERNAME)
            except Exception as e:
                logger.warning("Instagram login failed: %s", e)

    def get_profile(self, username: str) -> instaloader.Profile:
        try:
            return instaloader.Profile.from_username(self.loader.context, username)
        except instaloader.exceptions.ProfileNotExistsException:
            raise ProfileNotFoundError(f"Profile not found: {username}")
        except instaloader.exceptions.TooManyRequestsException:
            raise RateLimitedError("Rate limited by Instagram")

    def get_profile_metadata(self, username: str) -> ProfileData:
        profile = self.get_profile(username)
        latest_shortcode = None
        try:
            post = next(profile.get_posts())
            latest_shortcode = post.shortcode
        except StopIteration:
            pass
        except Exception:
            pass
        return ProfileData(
            username=profile.username,
            display_name=profile.full_name or None,
            bio=profile.biography or None,
            follower_count=profile.followers,
            profile_pic_url=profile.profile_pic_url,
            latest_post_shortcode=latest_shortcode,
        )

    def get_new_posts(
        self,
        username: str,
        since_shortcode: Optional[str],
        max_posts: int = 12,
    ) -> list[PostData]:
        profile = self.get_profile(username)
        results: list[PostData] = []

        try:
            for post in profile.get_posts():
                if post.shortcode == since_shortcode:
                    break
                results.append(self._post_to_data(post))
                if len(results) >= max_posts:
                    break
        except instaloader.exceptions.TooManyRequestsException:
            raise RateLimitedError("Rate limited by Instagram")
        except Exception as e:
            raise RuntimeError(f"Error fetching posts for {username}: {e}") from e

        return results

    def _post_to_data(self, post: instaloader.Post) -> PostData:
        if post.is_video:
            post_type = "reel" if post.product_type == "clips" else "video"
        elif post.typename == "GraphSidecar":
            post_type = "carousel"
        else:
            post_type = "photo"

        thumbnail_url = None
        try:
            thumbnail_url = post.url
        except Exception:
            pass

        return PostData(
            shortcode=post.shortcode,
            post_url=f"https://www.instagram.com/p/{post.shortcode}/",
            thumbnail_url=thumbnail_url,
            caption=post.caption[:500] if post.caption else None,
            post_type=post_type,
            like_count=post.likes,
            comment_count=post.comments,
            posted_at=post.date_utc,
        )
