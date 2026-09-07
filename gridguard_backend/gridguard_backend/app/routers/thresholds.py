"""
GridGuard Backend - Thresholds Router
UC13: Configure Anomaly Detection Thresholds.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import datetime

from app import models, schemas
from app.database import get_db
from app.dependencies import require_admin, get_current_user
from app.services import log_service

router = APIRouter(prefix="/thresholds", tags=["Thresholds"])


@router.get("", response_model=list[schemas.ThresholdOut])
def get_thresholds(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    rows = db.query(models.ThresholdConfig).filter(models.ThresholdConfig.is_active == True).all()  # noqa: E712
    return rows


@router.put("", response_model=list[schemas.ThresholdOut])
def update_thresholds(
    payload: schemas.ThresholdUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """UC13 alternate flow 'Invalid Threshold Value' is enforced by the
    Pydantic schema itself (0 < value < 1); a logically impossible ordering
    (medium >= high) is checked explicitly here."""
    if payload.risk_medium_cutoff >= payload.risk_high_cutoff:
        raise HTTPException(status_code=400, detail="Medium-risk cutoff must be lower than High-risk cutoff")

    updated = []
    for key, value in payload.dict().items():
        row = db.query(models.ThresholdConfig).filter(models.ThresholdConfig.threshold_type == key).first()
        if row:
            row.threshold_value = value
            row.updated_by = current_user.id
            row.updated_at = datetime.datetime.utcnow()
        else:
            row = models.ThresholdConfig(threshold_type=key, threshold_value=value, updated_by=current_user.id)
            db.add(row)
        updated.append(row)
    db.commit()
    for row in updated:
        db.refresh(row)

    log_service.log_event(
        db, event_type="threshold_updated", user_id=current_user.id,
        details=str(payload.dict()), related_table="threshold_configs",
    )
    return updated
