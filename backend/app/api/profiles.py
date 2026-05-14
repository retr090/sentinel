from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List
from datetime import datetime
from app.core.database import get_db
from app.core.security import get_current_user, require_analyst
from app.models.user import User
from app.models.profile import Profile, ProfileAttribute, ProfileLink, ProfileNote
from app.schemas.common import PaginatedResponse
from pydantic import BaseModel
from typing import Any, Dict
import math

router = APIRouter(prefix="/profiles", tags=["profiles"])


class ProfileCreate(BaseModel):
    name: str
    profile_type: str  # person, org, domain, ip, email
    query_value: str
    analyst_notes: Optional[str] = None


class ProfileNoteCreate(BaseModel):
    content: str


class ProfileOut(BaseModel):
    id: int
    name: str
    profile_type: str
    query_value: str
    risk_score: float
    summary: Optional[str]
    analyst_notes: Optional[str]
    last_updated: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class ProfileDetailOut(ProfileOut):
    raw_data: Optional[Dict[str, Any]]
    attributes: Optional[List[Dict[str, Any]]] = []
    links: Optional[List[Dict[str, Any]]] = []
    notes: Optional[List[Dict[str, Any]]] = []


@router.get("", response_model=PaginatedResponse[ProfileOut])
async def list_profiles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    profile_type: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Profile).where(Profile.is_archived == False)
    if profile_type:
        query = query.where(Profile.profile_type == profile_type)
    if search:
        query = query.where(Profile.name.ilike(f"%{search}%") | Profile.query_value.ilike(f"%{search}%"))

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar()
    query = query.order_by(Profile.last_updated.desc()).offset((page - 1) * page_size).limit(page_size)
    items = (await db.execute(query)).scalars().all()
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size, pages=math.ceil(total / page_size))


@router.post("", response_model=ProfileOut, dependencies=[Depends(require_analyst)])
async def create_profile(
    body: ProfileCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = Profile(
        name=body.name,
        profile_type=body.profile_type,
        query_value=body.query_value,
        analyst_notes=body.analyst_notes,
        created_by=current_user.id,
    )
    db.add(profile)
    await db.flush()
    await db.refresh(profile)

    background_tasks.add_task(run_profile_enrichment, profile.id)
    return profile


async def run_profile_enrichment(profile_id: int):
    from app.tasks.profiles import enrich_profile
    enrich_profile.delay(profile_id)


@router.get("/{profile_id}")
async def get_profile(
    profile_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = (await db.execute(select(Profile).where(Profile.id == profile_id))).scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    attrs = (await db.execute(select(ProfileAttribute).where(ProfileAttribute.profile_id == profile_id))).scalars().all()
    links = (await db.execute(select(ProfileLink).where(ProfileLink.source_profile_id == profile_id))).scalars().all()
    notes = (await db.execute(select(ProfileNote).where(ProfileNote.profile_id == profile_id).order_by(ProfileNote.created_at.desc()))).scalars().all()

    return {
        "profile": profile,
        "attributes": [{"type": a.attr_type, "key": a.attr_key, "value": a.attr_value, "source": a.source} for a in attrs],
        "links": [{"link_type": l.link_type, "target_id": l.target_profile_id, "confidence": l.confidence} for l in links],
        "notes": [{"id": n.id, "content": n.content, "created_at": n.created_at} for n in notes],
    }


@router.post("/{profile_id}/notes", dependencies=[Depends(require_analyst)])
async def add_note(
    profile_id: int,
    body: ProfileNoteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    note = ProfileNote(profile_id=profile_id, content=body.content, created_by=current_user.id)
    db.add(note)
    await db.flush()
    await db.refresh(note)
    return note


@router.post("/{profile_id}/enrich", dependencies=[Depends(require_analyst)])
async def re_enrich_profile(profile_id: int):
    from app.tasks.profiles import enrich_profile
    enrich_profile.delay(profile_id)
    return {"message": "Enrichment triggered"}


@router.get("/stats/summary")
async def get_stats(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    total = (await db.execute(select(func.count()).select_from(Profile).where(Profile.is_archived == False))).scalar()
    by_type = {}
    for ptype in ("person", "org", "domain", "ip", "email"):
        count = (await db.execute(select(func.count()).select_from(Profile).where(Profile.profile_type == ptype, Profile.is_archived == False))).scalar()
        by_type[ptype] = count
    return {"total": total, "by_type": by_type}
