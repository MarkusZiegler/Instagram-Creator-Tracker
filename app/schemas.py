from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class CreatorAdd(BaseModel):
    username: str
    notes: Optional[str] = None
    tags: Optional[str] = None


class CreatorUpdate(BaseModel):
    notes: Optional[str] = None
    tags: Optional[str] = None
    is_active: Optional[bool] = None


class CreatorOut(BaseModel):
    id: int
    username: str
    display_name: Optional[str]
    profile_pic_url: Optional[str]
    bio: Optional[str]
    follower_count: Optional[int]
    is_active: bool
    notes: Optional[str]
    tags: Optional[str]
    added_at: datetime
    last_checked_at: Optional[datetime]

    model_config = {"from_attributes": True}


class PostOut(BaseModel):
    id: int
    creator_id: int
    shortcode: str
    post_url: str
    thumbnail_url: Optional[str]
    caption: Optional[str]
    post_type: str
    like_count: Optional[int]
    comment_count: Optional[int]
    posted_at: datetime
    discovered_at: datetime
    is_new: bool

    model_config = {"from_attributes": True}


class CheckLogOut(BaseModel):
    id: int
    creator_id: int
    checked_at: datetime
    new_posts_found: int
    status: str
    error_message: Optional[str]

    model_config = {"from_attributes": True}


class CheckSummary(BaseModel):
    total_checked: int
    total_new_posts: int
    errors: int
    rate_limited: bool
    digest_sent: bool
