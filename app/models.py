from datetime import datetime
from typing import List, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Creator(Base):
    __tablename__ = "creators"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(200))
    profile_pic_url: Mapped[Optional[str]] = mapped_column(Text)
    bio: Mapped[Optional[str]] = mapped_column(Text)
    follower_count: Mapped[Optional[int]] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    tags: Mapped[Optional[str]] = mapped_column(Text)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    last_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    last_post_shortcode: Mapped[Optional[str]] = mapped_column(String(50))

    posts: Mapped[List["Post"]] = relationship(back_populates="creator", cascade="all, delete-orphan")
    check_logs: Mapped[List["CheckLog"]] = relationship(back_populates="creator", cascade="all, delete-orphan")


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    creator_id: Mapped[int] = mapped_column(ForeignKey("creators.id"), nullable=False, index=True)
    shortcode: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    post_url: Mapped[str] = mapped_column(Text, nullable=False)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(Text)
    caption: Mapped[Optional[str]] = mapped_column(Text)
    post_type: Mapped[str] = mapped_column(String(20), default="photo")
    like_count: Mapped[Optional[int]] = mapped_column(Integer)
    comment_count: Mapped[Optional[int]] = mapped_column(Integer)
    posted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    discovered_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    is_new: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    creator: Mapped["Creator"] = relationship(back_populates="posts")


class CheckLog(Base):
    __tablename__ = "check_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    creator_id: Mapped[int] = mapped_column(ForeignKey("creators.id"), nullable=False, index=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    new_posts_found: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    creator: Mapped["Creator"] = relationship(back_populates="check_logs")
