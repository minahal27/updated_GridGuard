"""
GridGuard Backend - Reports Router
UC11: Generate and Export Report.
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path

from app import models, schemas
from app.database import get_db
from app.dependencies import get_current_user
from app.services import report_service, log_service

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.post("", response_model=schemas.ReportOut)
def generate_report(
    payload: schemas.ReportRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    dataset = db.query(models.Dataset).filter(models.Dataset.id == payload.dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if dataset.status != "completed":
        raise HTTPException(status_code=409, detail="Dataset must be fully processed before generating a report")

    report = report_service.generate_report(
        db, payload.dataset_id, payload.format, current_user.id,
        risk_filter=payload.risk_filter, consumer_filter=payload.consumer_filter,
    )

    log_service.log_event(
        db, event_type="report_generated", user_id=current_user.id,
        details=f"{payload.format} report for dataset {payload.dataset_id}",
        related_table="reports", related_id=report.id,
    )
    return report


@router.get("/{report_id}/download")
def download_report(report_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    report = db.query(models.Report).filter(models.Report.id == report_id).first()
    if not report or not Path(report.file_path).exists():
        raise HTTPException(status_code=404, detail="Report file not found")

    media_type = "application/pdf" if report.format == "pdf" else "text/csv"
    return FileResponse(report.file_path, media_type=media_type, filename=Path(report.file_path).name)


@router.get("", response_model=list[schemas.ReportOut])
def list_reports(dataset_id: int = None, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    query = db.query(models.Report)
    if dataset_id:
        query = query.filter(models.Report.dataset_id == dataset_id)
    return query.order_by(models.Report.generated_at.desc()).all()
