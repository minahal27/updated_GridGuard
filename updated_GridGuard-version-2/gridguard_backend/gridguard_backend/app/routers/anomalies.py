"""
GridGuard Backend - Anomalies & Risk Router
UC6: View Anomaly Results
UC8: View Risk Score
UC7: Filter Data by Date Range and Consumer (the consumer/risk-category
part; date-range filtering on the underlying series is handled per-consumer
in routers/consumers.py - anomaly *results* here are dataset-level rows,
one per consumer, not per day, so "date range" doesn't apply the same way).
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.database import get_db
from app.dependencies import get_current_user

router = APIRouter(prefix="/anomalies", tags=["Anomaly Results & Risk"])


def _to_out(result: models.AnomalyResult) -> schemas.AnomalyResultOut:
    return schemas.AnomalyResultOut(
        id=result.id,
        consumer_id=result.consumer_id,
        cons_no=result.consumer.cons_no,
        isoforest_anomaly=result.isoforest_anomaly,
        isoforest_score=result.isoforest_score,
        risk_score=result.risk_score,
        risk_category=result.risk_category,
        risk_source=result.risk_source,
        actual_flag=result.actual_flag,
        detected_at=result.detected_at,
    )


@router.get("/{dataset_id}", response_model=schemas.PaginatedAnomalyResults)
def list_anomaly_results(
    dataset_id: int,
    risk_category: str = Query(default=None, pattern="^(Low|Medium|High)$"),
    consumer_search: str = Query(default=None, description="Substring match on Consumer ID"),
    anomalies_only: bool = Query(default=False, description="Only rows flagged anomalous by Isolation Forest"),
    sort_by: str = Query(default="risk_score", pattern="^(risk_score|isoforest_score|detected_at)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    query = (
        db.query(models.AnomalyResult)
        .options(joinedload(models.AnomalyResult.consumer))
        .join(models.Consumer, models.AnomalyResult.consumer_id == models.Consumer.id)
        .filter(models.AnomalyResult.dataset_id == dataset_id)
    )
    if risk_category:
        query = query.filter(models.AnomalyResult.risk_category == risk_category)
    if consumer_search:
        query = query.filter(models.Consumer.cons_no.ilike(f"%{consumer_search}%"))
    if anomalies_only:
        query = query.filter(models.AnomalyResult.isoforest_anomaly == True)  # noqa: E712

    total = query.count()
    sort_col = getattr(models.AnomalyResult, sort_by)
    items = (
        query.order_by(sort_col.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    if total == 0:
        # UC6 alternate flow: "No Anomaly Results Available"
        pass

    return schemas.PaginatedAnomalyResults(
        total=total, page=page, page_size=page_size, items=[_to_out(r) for r in items],
    )


@router.get("/{dataset_id}/{consumer_id}", response_model=schemas.AnomalyResultOut)
def get_consumer_result(dataset_id: int, consumer_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    result = (
        db.query(models.AnomalyResult)
        .options(joinedload(models.AnomalyResult.consumer))
        .filter(models.AnomalyResult.dataset_id == dataset_id, models.AnomalyResult.consumer_id == consumer_id)
        .first()
    )
    if not result:
        raise HTTPException(status_code=404, detail="No anomaly result found for this consumer")
    return _to_out(result)
