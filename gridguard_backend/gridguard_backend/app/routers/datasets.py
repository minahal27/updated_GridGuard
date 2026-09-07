"""
GridGuard Backend - Datasets Router
UC3: Upload Electricity Consumption Dataset. Processing (the ML pipeline)
runs as a background task since it takes tens of seconds on a full-size
dataset - the client polls GET /datasets/{id} for status.
"""
import shutil
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session

from app import models, schemas, config
from app.database import get_db
from app.dependencies import get_current_user
from app.services import ml_service, log_service

router = APIRouter(prefix="/datasets", tags=["Datasets"])


@router.post("", response_model=schemas.DatasetOut, status_code=201)
def upload_dataset(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    ext = Path(file.filename).suffix.lower()
    if ext not in config.ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{ext}'. Supported formats: {', '.join(config.ALLOWED_UPLOAD_EXTENSIONS)}",
        )

    dest_path = Path(config.UPLOADS_DIR) / f"upload_{file.filename}"
    with open(dest_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    size_mb = dest_path.stat().st_size / (1024 * 1024)
    if size_mb > config.MAX_UPLOAD_SIZE_MB:
        dest_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"File too large ({size_mb:.1f} MB). Max is {config.MAX_UPLOAD_SIZE_MB} MB.")

    dataset = models.Dataset(
        file_name=file.filename,
        file_type=ext.lstrip("."),
        uploaded_by=current_user.id,
        status="uploaded",
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    log_service.log_event(db, event_type="dataset_uploaded", user_id=current_user.id,
                           details=file.filename, related_table="datasets", related_id=dataset.id)

    # Kick off preprocessing + ML pipeline in the background. Note: we do
    # NOT pass the request-scoped `db` session into the background task -
    # FastAPI closes it right after the response is returned (see
    # app/database.py's get_db finally-block), but the background task
    # keeps running well after that. It opens its own session instead.
    background_tasks.add_task(_run_processing_job, dataset.id, str(dest_path))

    return dataset


def _run_processing_job(dataset_id: int, file_path: str):
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        ml_service.process_dataset(db, dataset_id, file_path)
    finally:
        db.close()


@router.get("", response_model=list[schemas.DatasetOut])
def list_datasets(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.Dataset).order_by(models.Dataset.uploaded_at.desc()).all()


@router.get("/{dataset_id}", response_model=schemas.DatasetOut)
def get_dataset(dataset_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    dataset = db.query(models.Dataset).filter(models.Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset
