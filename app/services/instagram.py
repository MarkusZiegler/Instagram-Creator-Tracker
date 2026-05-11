import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
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
    # Instagram mobile API headers — bypasses broken graphql/query get_posts()
    _MOBILE_HEADERS = {
        "X-IG-App-ID": "936619743392459",
        "User-Agent": (
            "Mozilla/5.0 (Linux; Android 11; Pixel 5) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/90.0.4430.91 Mobile Safari/537.36"
        ),
    }

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
            max_connection_attempts=1,
        )
        self._try_load_session()

    def _try_load_session(self) -> None:
        if os.path.exists(self.session_file):
            try:
                import pickle
                with open(self.session_file, "rb") as f:
                    data = pickle.load(f)
                if isinstance(data, dict):
                    # Our format: plain dict {sessionid, csrftoken, ds_user_id}
                    session = self.loader.context._session
                    for key, value in data.items():
                        session.cookies.set(key, value, domain=".instagram.com")
                    logger.info("Instagram session loaded from %s", self.session_file)
                    return
                else:
                    # Instaloader native CookieJar format
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

    def _get_user_info_via_api(self, username: str) -> dict:
        """Fetch profile info via mobile API — avoids graphql/query rate limits."""
        session = self.loader.context._session
        try:
            resp = session.get(
                "https://i.instagram.com/api/v1/users/web_profile_info/",
                headers=self._MOBILE_HEADERS,
                params={"username": username},
                timeout=15,
            )
        except Exception as e:
            raise RuntimeError(f"Network error fetching profile {username}: {e}") from e

        if resp.status_code == 404:
            raise ProfileNotFoundError(f"Profile not found: {username}")
        if resp.status_code == 429:
            raise RateLimitedError("Rate limited by Instagram")
        if resp.status_code in (401, 403):
            raise RateLimitedError("Session expired or unauthorized")
        if resp.status_code != 200:
            raise RuntimeError(f"Instagram returned HTTP {resp.status_code} for @{username}")

        user = resp.json().get("data", {}).get("user")
        if not user:
            raise ProfileNotFoundError(f"Profile not found: {username}")
        return user

    def get_profile_metadata(self, username: str) -> ProfileData:
        user = self._get_user_info_via_api(username)
        user_id = int(user["id"])
        latest_shortcode = None
        try:
            posts = self._fetch_posts_mobile(user_id, since_shortcode=None, max_posts=1)
            if posts:
                latest_shortcode = posts[0].shortcode
        except Exception:
            pass
        return ProfileData(
            username=user.get("username", username),
            display_name=user.get("full_name") or None,
            bio=user.get("biography") or None,
            follower_count=user.get("edge_followed_by", {}).get("count"),
            profile_pic_url=user.get("profile_pic_url") or None,
            latest_post_shortcode=latest_shortcode,
        )

    def get_new_posts(
        self,
        username: str,
        since_shortcode: Optional[str],
        max_posts: int = 12,
    ) -> list[PostData]:
        user = self._get_user_info_via_api(username)
        user_id = int(user["id"])
        return self._fetch_posts_mobile(user_id, since_shortcode, max_posts)

    def _fetch_posts_mobile(
        self,
        user_id: int,
        since_shortcode: Optional[str],
        max_posts: int,
    ) -> list[PostData]:
        session = self.loader.context._session
        url = f"https://i.instagram.com/api/v1/feed/user/{user_id}/"
        results: list[PostData] = []
        next_max_id = None

        while len(results) < max_posts:
            params: dict = {"count": min(max_posts, 12)}
            if next_max_id:
                params["max_id"] = next_max_id

            try:
                resp = session.get(
                    url, headers=self._MOBILE_HEADERS, params=params, timeout=15
                )
            except Exception as e:
                raise RuntimeError(f"Network error fetching posts: {e}") from e

            if resp.status_code == 429:
                raise RateLimitedError("Rate limited by Instagram")
            if resp.status_code in (401, 403):
                raise RateLimitedError("Session expired or unauthorized")
            if resp.status_code != 200:
                raise RuntimeError(f"Instagram returned HTTP {resp.status_code}")

            try:
                data = resp.json()
            except Exception as e:
                raise RuntimeError(f"Invalid JSON response: {e}") from e

            items = data.get("items", [])
            if not items:
                break

            for item in items:
                code = item.get("code") or item.get("shortcode", "")
                if code == since_shortcode:
                    return results
                results.append(self._item_to_post_data(item))
                if len(results) >= max_posts:
                    return results

            if not data.get("more_available"):
                break
            next_max_id = data.get("next_max_id")
            if not next_max_id:
                break

        return results

    def _item_to_post_data(self, item: dict) -> PostData:
        code = item.get("code") or item.get("shortcode", "")
        media_type = item.get("media_type", 1)
        if media_type == 2:
            post_type = "reel" if item.get("product_type") == "clips" else "video"
        elif media_type == 8:
            post_type = "carousel"
        else:
            post_type = "photo"

        thumbnail_url = None
        if "image_versions2" in item:
            candidates = item["image_versions2"].get("candidates", [])
            if candidates:
                thumbnail_url = candidates[0].get("url")

        caption = None
        if item.get("caption"):
            caption = item["caption"].get("text", "")[:500]

        posted_at = datetime.fromtimestamp(item.get("taken_at", 0), tz=timezone.utc)

        return PostData(
            shortcode=code,
            post_url=f"https://www.instagram.com/p/{code}/",
            thumbnail_url=thumbnail_url,
            caption=caption,
            post_type=post_type,
            like_count=item.get("like_count"),
            comment_count=item.get("comment_count"),
            posted_at=posted_at,
        )
