from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from app.core.database import get_db
from app.core.security import get_current_user, require_analyst
from app.models.user import User
from app.models.geoint import GeoItem, AreaOfInterest, GeoAlert
from pydantic import BaseModel
from typing import Any, Dict
import math

router = APIRouter(prefix="/geoint", tags=["geoint"])


class GeoItemCreate(BaseModel):
    title: str
    description: Optional[str] = None
    latitude: float
    longitude: float
    item_type: str = "incident"
    module_source: Optional[str] = None
    severity: str = "INFO"
    metadata: Optional[Dict[str, Any]] = {}
    event_time: Optional[datetime] = None


class AOICreate(BaseModel):
    name: str
    description: Optional[str] = None
    geojson: Dict[str, Any]
    alert_on_match: bool = True
    item_types: Optional[List[str]] = []


class GeoItemOut(BaseModel):
    id: int
    title: str
    description: Optional[str]
    latitude: float
    longitude: float
    item_type: str
    module_source: Optional[str]
    severity: str
    event_time: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/items")
async def list_geo_items(
    item_type: Optional[str] = None,
    since_hours: int = Query(168, ge=1, le=8760),
    limit: int = Query(500, ge=1, le=2000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(hours=since_hours)
    query = select(GeoItem).where(and_(GeoItem.is_archived == False, GeoItem.created_at >= since))
    if item_type:
        query = query.where(GeoItem.item_type == item_type)
    query = query.order_by(GeoItem.created_at.desc()).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/items", dependencies=[Depends(require_analyst)])
async def create_geo_item(
    body: GeoItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = GeoItem(
        **body.model_dump(exclude={"metadata"}),
        metadata_=body.metadata or {},
        created_by=current_user.id,
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)
    return item


@router.get("/aoi")
async def list_aoi(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AreaOfInterest).where(AreaOfInterest.is_active == True))
    return result.scalars().all()


@router.post("/aoi", dependencies=[Depends(require_analyst)])
async def create_aoi(
    body: AOICreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    aoi = AreaOfInterest(**body.model_dump(), created_by=current_user.id)
    db.add(aoi)
    await db.flush()
    await db.refresh(aoi)
    return aoi


@router.delete("/aoi/{aoi_id}", dependencies=[Depends(require_analyst)])
async def delete_aoi(aoi_id: int, db: AsyncSession = Depends(get_db)):
    aoi = (await db.execute(select(AreaOfInterest).where(AreaOfInterest.id == aoi_id))).scalar_one_or_none()
    if not aoi:
        raise HTTPException(status_code=404, detail="AOI not found")
    aoi.is_active = False
    return {"message": "AOI deactivated"}


@router.get("/flights")
async def get_live_flights(
    lat_min: float = Query(5.0),
    lat_max: float = Query(10.0),
    lon_min: float = Query(79.0),
    lon_max: float = Query(82.0),
    current_user: User = Depends(get_current_user),
):
    import httpx
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            r = await client.get(
                "https://opensky-network.org/api/states/all",
                params={"lamin": lat_min, "lamax": lat_max, "lomin": lon_min, "lomax": lon_max},
            )
            if r.status_code == 200:
                data = r.json()
                flights = []
                for s in (data.get("states") or [])[:50]:
                    if s[5] and s[6]:
                        flights.append({
                            "icao24": s[0],
                            "callsign": (s[1] or "").strip(),
                            "origin_country": s[2],
                            "longitude": s[5],
                            "latitude": s[6],
                            "altitude": s[7],
                            "velocity": s[9],
                            "heading": s[10],
                            "on_ground": s[8],
                        })
                return {"flights": flights, "count": len(flights)}
    except Exception as e:
        return {"flights": [], "error": str(e)}
    return {"flights": []}


@router.get("/stats")
async def get_stats(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    total_items = (await db.execute(select(func.count()).select_from(GeoItem).where(GeoItem.is_archived == False))).scalar()
    active_aoi = (await db.execute(select(func.count()).select_from(AreaOfInterest).where(AreaOfInterest.is_active == True))).scalar()
    return {"total_items": total_items, "active_aoi": active_aoi}
