"""
GridGuard Backend - Feeders Router
Network-wide Non-Technical Loss (NTL) detection via feeder-level
consumption reconciliation. See app/services/feeder_loss_service.py for
the full rationale and computation.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
import datetime

from app import models, schemas
from app.database import get_db
from app.dependencies import get_current_user, require_admin
from app.services import feeder_loss_service, log_service

router = APIRouter(prefix="/feeders", tags=["Feeders"])


@router.get("/{dataset_id}", response_model=list[schemas.FeederOut])
def list_feeders(
    dataset_id: int,
    risk_category: str = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """All feeders for a dataset, worst-loss first, so the riskiest
    network segments surface immediately without client-side sorting."""
    query = db.query(models.Feeder).filter(models.Feeder.dataset_id == dataset_id)
    if risk_category:
        query = query.filter(models.Feeder.risk_category == risk_category)
    return query.order_by(models.Feeder.avg_loss_pct.desc()).all()


@router.get("/{dataset_id}/summary", response_model=schemas.FeederSummary)
def feeder_summary(dataset_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Network-wide loss totals, for a dashboard-level 'estimated NTL' card.
    Aggregates in SQL rather than pulling every FeederDailyLoss row into
    Python (~170k rows for the SGCC dataset) - same lesson as the
    dashboard trend/histogram caching fix: push the sum to the database
    engine, don't loop over it in the app."""
    feeders = db.query(models.Feeder).filter(models.Feeder.dataset_id == dataset_id).all()
    if not feeders:
        raise HTTPException(status_code=404, detail="No feeder data for this dataset (has it finished processing?)")

    feeder_ids = [f.id for f in feeders]
    total_billed, total_expected, total_loss = (
        db.query(
            func.coalesce(func.sum(models.FeederDailyLoss.billed_kwh), 0.0),
            func.coalesce(func.sum(models.FeederDailyLoss.expected_kwh), 0.0),
            func.coalesce(func.sum(models.FeederDailyLoss.loss_kwh), 0.0),
        )
        .filter(models.FeederDailyLoss.feeder_id.in_(feeder_ids))
        .first()
    )
    overall_loss_pct = (total_loss / total_expected * 100.0) if total_expected > 0 else 0.0

    return schemas.FeederSummary(
        dataset_id=dataset_id,
        feeder_count=len(feeders),
        is_synthetic=feeders[0].is_synthetic,
        total_billed_kwh=round(total_billed, 1),
        total_expected_kwh=round(total_expected, 1),
        total_loss_kwh=round(total_loss, 1),
        overall_loss_pct=round(overall_loss_pct, 2),
        high_risk_feeders=sum(1 for f in feeders if f.risk_category == "High"),
        medium_risk_feeders=sum(1 for f in feeders if f.risk_category == "Medium"),
        low_risk_feeders=sum(1 for f in feeders if f.risk_category == "Low"),
    )


@router.get("/{dataset_id}/{feeder_id}/trend", response_model=schemas.FeederTrend)
def feeder_trend(
    dataset_id: int, feeder_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    """Billed vs. expected vs. loss% time series for one feeder - the
    chart an analyst drills into after spotting a high-loss feeder."""
    feeder = (
        db.query(models.Feeder)
        .filter(models.Feeder.id == feeder_id, models.Feeder.dataset_id == dataset_id)
        .first()
    )
    if not feeder:
        raise HTTPException(status_code=404, detail="Feeder not found")

    rows = (
        db.query(models.FeederDailyLoss)
        .filter(models.FeederDailyLoss.feeder_id == feeder_id)
        .order_by(models.FeederDailyLoss.date.asc())
        .all()
    )
    return schemas.FeederTrend(
        feeder_id=feeder.id,
        feeder_code=feeder.feeder_code,
        dates=[r.date for r in rows],
        billed_kwh=[r.billed_kwh for r in rows],
        expected_kwh=[r.expected_kwh or 0.0 for r in rows],
        loss_pct=[r.loss_pct for r in rows],
    )


@router.put("/thresholds", response_model=list[schemas.ThresholdOut])
def update_feeder_thresholds(
    payload: schemas.FeederThresholdUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """UC13-style admin control, scoped to feeder-loss cutoffs rather than
    consumer risk score cutoffs (kept as a separate endpoint/schema from
    PUT /thresholds so the two concepts - individual risk vs. network
    loss % - don't get conflated in one payload)."""
    if payload.feeder_loss_medium_cutoff >= payload.feeder_loss_high_cutoff:
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
        db, event_type="feeder_threshold_updated", user_id=current_user.id,
        details=str(payload.dict()), related_table="threshold_configs",
    )
    return updated
