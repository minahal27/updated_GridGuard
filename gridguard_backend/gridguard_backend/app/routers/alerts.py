"""
GridGuard Backend - Alerts Router
UC9: Receive Alerts (listing - generation itself happens automatically in
     services/alert_service.py right after a dataset finishes processing
     or a model is retrained)
UC10: Mark Alerts as Reviewed/Resolved
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
import datetime

from app import models, schemas
from app.database import get_db
from app.dependencies import get_current_user
from app.services import log_service

router = APIRouter(prefix="/alerts", tags=["Alerts"])


def _to_out(alert: models.Alert) -> schemas.AlertOut:
    return schemas.AlertOut(
        id=alert.id,
        consumer_id=alert.consumer_id,
        cons_no=alert.anomaly_result.consumer.cons_no,
        severity=alert.severity,
        status=alert.status,
        message=alert.message,
        created_at=alert.created_at,
        reviewed_by=alert.reviewed_by,
        reviewed_at=alert.reviewed_at,
    )


@router.get("", response_model=list[schemas.AlertOut])
def list_alerts(
    dataset_id: int = Query(default=None),
    status_filter: str = Query(default=None, alias="status", pattern="^(New|Reviewed|Resolved)$"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    query = db.query(models.Alert).options(
        joinedload(models.Alert.anomaly_result).joinedload(models.AnomalyResult.consumer)
    )
    if dataset_id:
        query = query.join(models.AnomalyResult, models.Alert.anomaly_result_id == models.AnomalyResult.id).filter(
            models.AnomalyResult.dataset_id == dataset_id
        )
    if status_filter:
        query = query.filter(models.Alert.status == status_filter)

    alerts = query.order_by(models.Alert.created_at.desc()).all()
    return [_to_out(a) for a in alerts]


@router.patch("/{alert_id}", response_model=schemas.AlertOut)
def update_alert_status(
    alert_id: int,
    payload: schemas.AlertStatusUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    alert = db.query(models.Alert).options(
        joinedload(models.Alert.anomaly_result).joinedload(models.AnomalyResult.consumer)
    ).filter(models.Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = payload.status
    alert.reviewed_by = current_user.id
    alert.reviewed_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(alert)

    log_service.log_event(
        db, event_type="alert_status_updated", user_id=current_user.id,
        details=f"alert {alert_id} -> {payload.status}", related_table="alerts", related_id=alert_id,
    )
    return _to_out(alert)
