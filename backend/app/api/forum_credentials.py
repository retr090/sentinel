import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.forum_credentials import ForumCredential
from app.services.encryption import encrypt_password

router = APIRouter(prefix="/forums", tags=["forums"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class ForumCredentialCreate(BaseModel):
    forum_id: str
    forum_name: str
    forum_url: str
    username: Optional[str] = None
    password: Optional[str] = None     # plain text — encrypted before storage
    login_url: Optional[str] = None
    forum_software: str = "mybb"
    search_url_pattern: Optional[str] = None
    result_selector: Optional[str] = None
    auto_login: bool = True
    notes: Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _require_admin(current_user):
    if getattr(current_user, "role", "") != "admin":
        raise HTTPException(403, "Admins only")


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/list")
async def list_forums(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ForumCredential).order_by(ForumCredential.created_at))
    forums = result.scalars().all()
    return [
        {
            "forum_id": f.forum_id,
            "forum_name": f.forum_name,
            "forum_url": f.forum_url,
            "username": f.username,
            "forum_software": f.forum_software,
            "auto_login": f.auto_login,
            "is_active": f.is_active,
            "has_password": bool(f.encrypted_password),
            "has_cookies": bool(f.session_cookies),
            "login_attempts": f.login_attempts or 0,
            "last_successful_login": (
                f.last_successful_login.isoformat() if f.last_successful_login else None
            ),
            "last_used": f.last_used.isoformat() if f.last_used else None,
            "notes": f.notes,
        }
        for f in forums
    ]


@router.post("/add")
async def add_forum(
    data: ForumCredentialCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(current_user)

    existing = await db.execute(
        select(ForumCredential).where(ForumCredential.forum_id == data.forum_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, f"Forum '{data.forum_id}' already exists")

    encrypted_pw = None
    if data.password:
        try:
            encrypted_pw = encrypt_password(data.password)
        except Exception as e:
            raise HTTPException(500, f"Encryption error: {e}")

    forum = ForumCredential(
        id=uuid.uuid4(),
        forum_id=data.forum_id,
        forum_name=data.forum_name,
        forum_url=data.forum_url,
        username=data.username,
        encrypted_password=encrypted_pw,
        login_url=data.login_url,
        forum_software=data.forum_software,
        search_url_pattern=data.search_url_pattern,
        result_selector=data.result_selector,
        auto_login=data.auto_login,
        notes=data.notes,
        added_by=str(getattr(current_user, "username", current_user.id)),
        is_active=True,
        session_cookies={},
        login_attempts=0,
    )
    db.add(forum)
    await db.commit()
    await db.refresh(forum)

    return {
        "success": True,
        "forum_id": forum.forum_id,
        "has_password": bool(encrypted_pw),
        "auto_login": forum.auto_login,
        "message": f"{data.forum_name} added. Auto-login will activate on next scan.",
    }


@router.put("/update-password/{forum_id}")
async def update_forum_password(
    forum_id: str,
    body: dict,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(current_user)

    result = await db.execute(
        select(ForumCredential).where(ForumCredential.forum_id == forum_id)
    )
    forum = result.scalar_one_or_none()
    if not forum:
        raise HTTPException(404, "Forum not found")

    new_password = body.get("password", "").strip()
    if not new_password:
        raise HTTPException(400, "Password required")

    try:
        forum.encrypted_password = encrypt_password(new_password)
    except Exception as e:
        raise HTTPException(500, f"Encryption error: {e}")

    forum.session_cookies = {}
    forum.last_successful_login = None
    forum.updated_at = datetime.utcnow()
    await db.commit()

    return {"success": True, "message": "Password updated. Will auto-login on next scan."}


@router.post("/login-now/{forum_id}")
async def trigger_login(
    forum_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Immediately attempt auto-login and return result."""
    _require_admin(current_user)

    result = await db.execute(
        select(ForumCredential).where(ForumCredential.forum_id == forum_id)
    )
    forum = result.scalar_one_or_none()
    if not forum:
        raise HTTPException(404, "Forum not found")

    if not forum.encrypted_password:
        raise HTTPException(400, "No password stored — add password first")

    from app.services.darkweb.forum_auth import auto_login_forum

    success, cookies, error = await auto_login_forum(
        forum_id=forum.forum_id,
        base_url=forum.forum_url,
        forum_software=forum.forum_software or "mybb",
        username=forum.username or "",
        encrypted_password=forum.encrypted_password,
        login_url=forum.login_url,
    )

    if success:
        forum.session_cookies = cookies
        forum.last_successful_login = datetime.utcnow()
        forum.login_attempts = 0
        await db.commit()
        return {
            "success": True,
            "cookies_obtained": len(cookies),
            "cookie_names": list(cookies.keys()),
            "message": "Login successful",
        }
    else:
        forum.login_attempts = (forum.login_attempts or 0) + 1
        await db.commit()
        return {"success": False, "error": error, "message": "Login failed"}


@router.delete("/remove/{forum_id}")
async def remove_forum(
    forum_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(current_user)

    result = await db.execute(
        select(ForumCredential).where(ForumCredential.forum_id == forum_id)
    )
    forum = result.scalar_one_or_none()
    if not forum:
        raise HTTPException(404, "Forum not found")

    await db.delete(forum)
    await db.commit()
    return {"success": True, "message": f"{forum.forum_name} removed"}
