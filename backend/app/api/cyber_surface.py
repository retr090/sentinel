from fastapi import APIRouter, Depends, Query, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from app.core.database import get_db
from app.core.security import get_current_user, require_analyst
from app.models.user import User
from app.models.cyber_surface import MonitoredAsset, AssetScan, AssetVulnerability, AssetAlert
from app.schemas.common import PaginatedResponse
from pydantic import BaseModel
import math

router = APIRouter(prefix="/cyber-surface", tags=["cyber-surface"])


class AssetCreate(BaseModel):
    name: str
    asset_type: str  # domain, ip, ip_range
    value: str
    organization: Optional[str] = None
    tags: Optional[List[str]] = []
    scan_interval_hours: int = 24


class AssetOut(BaseModel):
    id: int
    name: str
    asset_type: str
    value: str
    organization: Optional[str]
    risk_grade: Optional[str]
    risk_score: float
    is_active: bool
    last_scanned: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class ScanOut(BaseModel):
    id: int
    asset_id: int
    scan_type: str
    status: str
    changes_detected: bool
    change_summary: Optional[str]
    risk_score: Optional[float]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class VulnOut(BaseModel):
    id: int
    asset_id: int
    cve_id: Optional[str]
    title: Optional[str]
    description: Optional[str]
    severity: Optional[str]
    cvss_score: Optional[float]
    service: Optional[str]
    port: Optional[int]
    is_resolved: bool
    discovered_at: datetime

    class Config:
        from_attributes = True


@router.get("/assets", response_model=PaginatedResponse[AssetOut])
async def list_assets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    asset_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(MonitoredAsset).where(MonitoredAsset.is_active == True)
    if asset_type:
        query = query.where(MonitoredAsset.asset_type == asset_type)
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar()
    query = query.order_by(MonitoredAsset.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    items = (await db.execute(query)).scalars().all()
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size, pages=math.ceil(total / page_size))


@router.post("/assets", response_model=AssetOut, dependencies=[Depends(require_analyst)])
async def create_asset(
    body: AssetCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    existing = (await db.execute(select(MonitoredAsset).where(MonitoredAsset.value == body.value))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Asset already monitored")

    asset = MonitoredAsset(**body.model_dump(), created_by=current_user.id)
    db.add(asset)
    await db.flush()
    await db.refresh(asset)

    background_tasks.add_task(trigger_initial_scan, asset.id)
    return asset


async def trigger_initial_scan(asset_id: int):
    from app.tasks.cyber_surface import scan_asset
    scan_asset.delay(asset_id)


@router.delete("/assets/{asset_id}", dependencies=[Depends(require_analyst)])
async def deactivate_asset(asset_id: int, db: AsyncSession = Depends(get_db)):
    asset = (await db.execute(select(MonitoredAsset).where(MonitoredAsset.id == asset_id))).scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    asset.is_active = False
    return {"message": "Asset deactivated"}


@router.get("/assets/{asset_id}/scans", response_model=List[ScanOut])
async def list_scans(
    asset_id: int,
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AssetScan).where(AssetScan.asset_id == asset_id).order_by(AssetScan.created_at.desc()).limit(limit)
    )
    return result.scalars().all()


@router.post("/assets/{asset_id}/scan", dependencies=[Depends(require_analyst)])
async def trigger_scan(asset_id: int):
    from app.tasks.cyber_surface import scan_asset
    scan_asset.delay(asset_id)
    return {"message": "Scan triggered"}


@router.get("/vulnerabilities", response_model=PaginatedResponse[VulnOut])
async def list_vulnerabilities(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    severity: Optional[str] = None,
    asset_id: Optional[int] = None,
    unresolved_only: bool = True,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(AssetVulnerability).where(AssetVulnerability.is_archived == False)
    if severity:
        query = query.where(AssetVulnerability.severity == severity)
    if asset_id:
        query = query.where(AssetVulnerability.asset_id == asset_id)
    if unresolved_only:
        query = query.where(AssetVulnerability.is_resolved == False)

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar()
    query = query.order_by(AssetVulnerability.discovered_at.desc()).offset((page - 1) * page_size).limit(page_size)
    items = (await db.execute(query)).scalars().all()
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size, pages=math.ceil(total / page_size))


@router.get("/stats")
async def get_stats(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    assets = (await db.execute(select(func.count()).select_from(MonitoredAsset).where(MonitoredAsset.is_active == True))).scalar()
    critical_vulns = (await db.execute(select(func.count()).select_from(AssetVulnerability).where(AssetVulnerability.severity == "CRITICAL", AssetVulnerability.is_resolved == False))).scalar()
    high_vulns = (await db.execute(select(func.count()).select_from(AssetVulnerability).where(AssetVulnerability.severity == "HIGH", AssetVulnerability.is_resolved == False))).scalar()
    alerts_open = (await db.execute(select(func.count()).select_from(AssetAlert).where(AssetAlert.is_acknowledged == False))).scalar()
    return {"assets": assets, "critical_vulns": critical_vulns, "high_vulns": high_vulns, "alerts_open": alerts_open}
