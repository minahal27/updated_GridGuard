"""
GridGuard Backend - Consumers Router
UC5: View Time-Series Graph
UC7: Filter Data by Date Range and Consumer (the date-range part is
applied here after loading the consumer's series; the consumer-ID part is
just the path parameter / search query below).
"""
import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.dependencies import get_current_user
from app.services import ml_service

router = APIRouter(prefix="/consumers", tags=["Consumers"])


@router.get("/{dataset_id}/search")
def search_consumers(
    dataset_id: int,
    q: str = Query(default="", description="Consumer ID substring to search for"),
    limit: int = Query(default=20, le=100),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    query = db.query(models.Consumer).filter(models.Consumer.dataset_id == dataset_id)
    if q:
        query = query.filter(models.Consumer.cons_no.ilike(f"%{q}%"))
    consumers = query.limit(limit).all()
    return [{"consumer_id": c.id, "cons_no": c.cons_no} for c in consumers]


@router.get("/{dataset_id}/{consumer_id}/timeseries", response_model=schemas.ConsumerTimeSeries)
def get_timeseries(
    dataset_id: int,
    consumer_id: int,
    start_date: str = Query(default=None, description="YYYY-MM-DD"),
    end_date: str = Query(default=None, description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    dataset = db.query(models.Dataset).filter(models.Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    consumer = db.query(models.Consumer).filter(
        models.Consumer.id == consumer_id, models.Consumer.dataset_id == dataset_id
    ).first()
    if not consumer:
        raise HTTPException(status_code=404, detail="Consumer not found in this dataset")

    dates, values = ml_service.get_consumer_series(dataset, consumer.series_row_index)
    if dates is None:
        raise HTTPException(status_code=404, detail="Consumption series not available for this dataset")

    points = list(zip(dates, values))

    # UC7: filter by date range, applied in-memory on this consumer's series
    if start_date:
        start = datetime.date.fromisoformat(start_date)
        points = [(d, v) for d, v in points if datetime.date.fromisoformat(d) >= start]
    if end_date:
        end = datetime.date.fromisoformat(end_date)
        points = [(d, v) for d, v in points if datetime.date.fromisoformat(d) <= end]

    if not points:
        raise HTTPException(status_code=404, detail="No records found for the selected date range")

    # Anomaly highlighting: flag days with an unusually large drop/spike
    # relative to this consumer's own mean, so the frontend can mark points
    # on the chart (UC5's "highlight anomalies on the graph").
    valid_values = [v for _, v in points if v is not None]
    mean_v = sum(valid_values) / len(valid_values) if valid_values else 0
    anomaly_dates = []
    prev = None
    for d, v in points:
        if v is not None and prev is not None and prev > 0.01:
            pct_change = (v - prev) / prev
            if abs(pct_change) > 0.6 or (mean_v > 0 and v < 0.15 * mean_v):
                anomaly_dates.append(d)
        prev = v if v is not None else prev

    return schemas.ConsumerTimeSeries(
        cons_no=consumer.cons_no,
        consumer_id=consumer.id,
        points=[schemas.TimeSeriesPoint(date=d, value=v) for d, v in points],
        anomaly_dates=anomaly_dates,
    )
