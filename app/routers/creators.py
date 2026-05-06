import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Creator, Post
from app.schemas import CreatorAdd, CreatorOut, CreatorUpdate, PostOut
from app.services.instagram import InstagramService, ProfileNotFoundError, RateLimitedError
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

_ig_service: Optional[InstagramService] = None


def get_ig_service() -> InstagramService:
    global _ig_service
    if _ig_service is None:
        _ig_service = InstagramService(settings.INSTAGRAM_SESSION_FILE)
    return _ig_service


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    creators = db.query(Creator).filter(Creator.is_active == True).order_by(Creator.added_at.desc()).all()
    new_posts = (
        db.query(Post)
        .filter(Post.is_new == True)
        .order_by(Post.posted_at.desc())
        .limit(50)
        .all()
    )
    base_url = str(request.base_url).rstrip("/")
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {"creators": creators, "new_posts": new_posts, "base_url": base_url},
    )


@router.post("/creators", response_model=CreatorOut)
def add_creator(payload: CreatorAdd, db: Session = Depends(get_db)):
    username = payload.username.strip().lstrip("@").lower()
    username = username.rstrip("/").split("/")[-1] if "/" in username else username

    existing = db.query(Creator).filter(Creator.username == username).first()
    if existing:
        if not existing.is_active:
            existing.is_active = True
            db.commit()
            db.refresh(existing)
            return existing
        raise HTTPException(status_code=409, detail=f"@{username} is already tracked")

    try:
        ig = get_ig_service()
        profile = ig.get_profile_metadata(username)
    except ProfileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Instagram profile @{username} not found")
    except RateLimitedError:
        raise HTTPException(status_code=429, detail="Instagram rate limit hit - try again in a few minutes")
    except Exception as e:
        logger.warning("Could not fetch Instagram metadata for %s: %s", username, e)
        profile = None

    creator = Creator(
        username=username,
        display_name=profile.display_name if profile else None,
        bio=profile.bio if profile else None,
        follower_count=profile.follower_count if profile else None,
        profile_pic_url=profile.profile_pic_url if profile else None,
        last_post_shortcode=profile.latest_post_shortcode if profile else None,
        notes=payload.notes,
        tags=payload.tags,
    )
    db.add(creator)
    db.commit()
    db.refresh(creator)
    logger.info("Added creator: @%s", username)
    return creator


@router.post("/creators/add-form")
def add_creator_form(username: str = Form(...), notes: str = Form(""), db: Session = Depends(get_db)):
    from app.schemas import CreatorAdd
    try:
        add_creator(CreatorAdd(username=username, notes=notes or None), db)
    except HTTPException:
        pass
    return RedirectResponse(url="/", status_code=303)


@router.get("/creators/{username}", response_class=HTMLResponse)
def creator_detail(username: str, request: Request, db: Session = Depends(get_db)):
    creator = db.query(Creator).filter(Creator.username == username).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")
    posts = (
        db.query(Post)
        .filter(Post.creator_id == creator.id)
        .order_by(Post.posted_at.desc())
        .limit(50)
        .all()
    )
    return templates.TemplateResponse(
        request,
        "creator_detail.html",
        {"creator": creator, "posts": posts},
    )


@router.put("/creators/{username}", response_model=CreatorOut)
def update_creator(username: str, payload: CreatorUpdate, db: Session = Depends(get_db)):
    creator = db.query(Creator).filter(Creator.username == username).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")
    if payload.notes is not None:
        creator.notes = payload.notes
    if payload.tags is not None:
        creator.tags = payload.tags
    if payload.is_active is not None:
        creator.is_active = payload.is_active
    db.commit()
    db.refresh(creator)
    return creator


@router.delete("/creators/{username}")
def remove_creator(username: str, db: Session = Depends(get_db)):
    creator = db.query(Creator).filter(Creator.username == username).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")
    creator.is_active = False
    db.commit()
    return {"ok": True}


@router.get("/creators/{username}/posts", response_model=list[PostOut])
def creator_posts(username: str, db: Session = Depends(get_db)):
    creator = db.query(Creator).filter(Creator.username == username).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")
    return db.query(Post).filter(Post.creator_id == creator.id).order_by(Post.posted_at.desc()).limit(50).all()
