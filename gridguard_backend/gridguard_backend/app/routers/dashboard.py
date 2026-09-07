"""
GridGuard Backend - Dashboard Router
UC4: View Dashboard - summary statistics for a processed dataset.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app import models, schemas
from app.database import get_db
from app.dependencies import get_current_user
from app.services import ml_service

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/{dataset_id}", response_model=schemas.DashboardSummary)
def dashboard_summary(dataset_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    dataset = db.query(models.Dataset).filter(models.Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if dataset.status != "completed":
        raise HTTPException(status_code=409, detail=f"Dataset is not ready yet (status: {dataset.status})")

    total_consumers = db.query(func.count(models.Consumer.id)).filter(models.Consumer.dataset_id == dataset_id).scalar()

    risk_counts = dict(
        db.query(models.AnomalyResult.risk_category, func.count(models.AnomalyResult.id))
        .filter(models.AnomalyResult.dataset_id == dataset_id)
        .group_by(models.AnomalyResult.risk_category)
        .all()
    )

    total_anomalies = db.query(func.count(models.AnomalyResult.id)).filter(
        models.AnomalyResult.dataset_id == dataset_id, models.AnomalyResult.isoforest_anomaly == True,  # noqa: E712
    ).scalar()

    unresolved_alerts = (
        db.query(func.count(models.Alert.id))
        .join(models.AnomalyResult, models.Alert.anomaly_result_id == models.AnomalyResult.id)
        .filter(models.AnomalyResult.dataset_id == dataset_id, models.Alert.status != "Resolved")
        .scalar()
    )

    active_model = db.query(models.MLModel).filter(models.MLModel.is_active == True).first()  # noqa: E712

    return schemas.DashboardSummary(
        dataset_id=dataset_id,
        total_consumers=total_consumers or 0,
        total_anomalies=total_anomalies or 0,
        high_risk_count=risk_counts.get("High", 0),
        medium_risk_count=risk_counts.get("Medium", 0),
        low_risk_count=risk_counts.get("Low", 0),
        unresolved_alerts=unresolved_alerts or 0,
        active_model=f"{active_model.model_name} v{active_model.model_version}" if active_model else None,
    )


@router.get("/{dataset_id}/trend", response_model=schemas.NetworkTrend)
def network_trend(dataset_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Network-wide average daily consumption, for the dashboard trend chart."""
    dataset = db.query(models.Dataset).filter(models.Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if dataset.status != "completed":
        raise HTTPException(status_code=409, detail=f"Dataset is not ready yet (status: {dataset.status})")

    dates, values, sampled = ml_service.get_network_trend(dataset)
    if dates is None:
        raise HTTPException(status_code=404, detail="Consumption series not available for this dataset")

    return schemas.NetworkTrend(dataset_id=dataset_id, dates=dates, avg_consumption=values, sampled=sampled)


@router.get("/{dataset_id}/risk-histogram", response_model=schemas.RiskHistogram)
def risk_histogram(dataset_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Risk score distribution across all consumers, for the dashboard histogram."""
    dataset = db.query(models.Dataset).filter(models.Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if dataset.status != "completed":
        raise HTTPException(status_code=409, detail=f"Dataset is not ready yet (status: {dataset.status})")

    bins = ml_service.get_risk_histogram(db, dataset_id)
    return schemas.RiskHistogram(dataset_id=dataset_id, bins=bins)
