from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, update
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from app.core.database import get_db
from app.core.security import get_current_user, require_analyst
from app.models.user import User
from app.models.alerts import Alert, AlertAssignment, Report, ReportTemplate, NotificationConfig
from app.schemas.common import PaginatedResponse
from pydantic import BaseModel
from typing import Any, Dict
import math

router = APIRouter(prefix="/alerts", tags=["alerts"])


class AlertOut(BaseModel):
    id: int
    title: str
    description: Optional[str]
    severity: str
    module: str
    status: str
    triggered_at: datetime
    resolved_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class ReportCreate(BaseModel):
    title: str
    report_type: str = "sitrep"
    modules: List[str] = []
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    parameters: Optional[Dict[str, Any]] = {}


class NotificationConfigCreate(BaseModel):
    name: str
    channel_type: str
    config: Dict[str, Any]
    min_severity: str = "HIGH"
    modules: Optional[List[str]] = []


@router.get("", response_model=PaginatedResponse[AlertOut])
async def list_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    severity: Optional[str] = None,
    module: Optional[str] = None,
    status: Optional[str] = None,
    since_hours: int = Query(168, ge=1, le=8760),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(hours=since_hours)
    query = select(Alert).where(and_(Alert.is_archived == False, Alert.triggered_at >= since))

    if severity:
        query = query.where(Alert.severity == severity)
    if module:
        query = query.where(Alert.module == module)
    if status:
        query = query.where(Alert.status == status)

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar()
    query = query.order_by(Alert.triggered_at.desc()).offset((page - 1) * page_size).limit(page_size)
    items = (await db.execute(query)).scalars().all()
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size, pages=math.ceil(total / page_size))


@router.post("/{alert_id}/acknowledge", dependencies=[Depends(require_analyst)])
async def acknowledge_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    alert = (await db.execute(select(Alert).where(Alert.id == alert_id))).scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.status = "acknowledged"
    return {"message": "Alert acknowledged"}


@router.post("/{alert_id}/resolve", dependencies=[Depends(require_analyst)])
async def resolve_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    alert = (await db.execute(select(Alert).where(Alert.id == alert_id))).scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.status = "resolved"
    alert.resolved_at = datetime.now(timezone.utc)
    return {"message": "Alert resolved"}


@router.post("/{alert_id}/assign", dependencies=[Depends(require_analyst)])
async def assign_alert(
    alert_id: int,
    assigned_to: int,
    notes: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    assignment = AlertAssignment(
        alert_id=alert_id,
        assigned_to=assigned_to,
        assigned_by=current_user.id,
        notes=notes,
    )
    db.add(assignment)
    return {"message": "Alert assigned"}


@router.get("/reports")
async def list_reports(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Report).order_by(Report.created_at.desc()).limit(50))
    return result.scalars().all()


@router.post("/reports", dependencies=[Depends(require_analyst)])
async def create_report(
    body: ReportCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    report = Report(
        title=body.title,
        report_type=body.report_type,
        modules=body.modules,
        date_from=body.date_from,
        date_to=body.date_to,
        parameters=body.parameters,
        status="pending",
        generated_by=current_user.id,
    )
    db.add(report)
    await db.flush()
    await db.refresh(report)

    from app.tasks.alerts import generate_report
    generate_report.delay(report.id)
    return report


@router.get("/notifications")
async def list_notification_configs(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(NotificationConfig).where(NotificationConfig.is_active == True))
    return result.scalars().all()


@router.post("/notifications", dependencies=[Depends(require_analyst)])
async def create_notification_config(
    body: NotificationConfigCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    config = NotificationConfig(**body.model_dump(), created_by=current_user.id)
    db.add(config)
    await db.flush()
    await db.refresh(config)
    return config


@router.get("/stats")
async def get_stats(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    counts = {}
    for sev in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
        count = (await db.execute(
            select(func.count()).select_from(Alert).where(Alert.severity == sev, Alert.status == "open", Alert.is_archived == False)
        )).scalar()
        counts[sev.lower()] = count
    total_open = sum(counts.values())
    return {"open_by_severity": counts, "total_open": total_open}
