"""
GridGuard Backend - System Logs Router
UC14: View System Logs.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
import datetime

from app import models, schemas
from app.database import get_db
from app.dependencies import require_admin

router = APIRouter(prefix="/logs", tags=["System Logs"])


@router.get("", response_model=list[schemas.SystemLogOut])
def view_logs(
    event_type: str = Query(default=None),
    severity: str = Query(default=None, pattern="^(info|warning|error)$"),
    since: str = Query(default=None, description="YYYY-MM-DD - only logs on/after this date"),
    limit: int = Query(default=200, le=1000),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    query = db.query(models.SystemLog)
    if event_type:
        query = query.filter(models.SystemLog.event_type == event_type)
    if severity:
        query = query.filter(models.SystemLog.severity == severity)
    if since:
        since_dt = datetime.datetime.fromisoformat(since)
        query = query.filter(models.SystemLog.created_at >= since_dt)

    logs = query.order_by(models.SystemLog.created_at.desc()).limit(limit).all()
    return logs
