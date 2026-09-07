"""
GridGuard Backend - ML Models Router
UC2: Upload/Select ML Model (the "select active model" flow - direct raw
     model-file upload is intentionally out of scope here: models in this
     system are only ever produced by the training pipeline itself, so
     "upload" happens indirectly via POST /datasets or POST /ml-models/retrain,
     which is safer than accepting an arbitrary pickled model file from a
     client)
UC12: Train/Retrain ML Model
"""
import json
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.dependencies import get_current_user, require_admin
from app.services import ml_service, log_service

router = APIRouter(prefix="/ml-models", tags=["ML Model Management"])


def _to_out(m: models.MLModel) -> schemas.MLModelOut:
    return schemas.MLModelOut(
        id=m.id,
        model_name=m.model_name,
        model_version=m.model_version,
        algorithm_type=m.algorithm_type,
        is_active=m.is_active,
        uploaded_at=m.uploaded_at,
        metrics=json.loads(m.metrics_json) if m.metrics_json else None,
    )


@router.get("", response_model=list[schemas.MLModelOut])
def list_models(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    rows = db.query(models.MLModel).order_by(models.MLModel.uploaded_at.desc()).all()
    return [_to_out(m) for m in rows]


@router.post("/{model_id}/activate", response_model=schemas.MLModelOut)
def set_active_model(model_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    """UC2 Flow B: Select Active ML Model."""
    target = db.query(models.MLModel).filter(models.MLModel.id == model_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Model not found")

    db.query(models.MLModel).filter(models.MLModel.is_active == True).update({"is_active": False})  # noqa: E712
    target.is_active = True
    db.commit()
    db.refresh(target)

    log_service.log_event(
        db, event_type="model_activated", user_id=current_user.id,
        details=f"{target.model_name} v{target.model_version}", related_table="ml_models", related_id=target.id,
    )
    return _to_out(target)


@router.post("/retrain", response_model=schemas.MLModelOut)
def retrain(
    payload: schemas.RetrainRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """
    UC12: kicks off retraining synchronously since a single dataset's
    retrain (~10-30s) is short enough to wait on and the use case expects
    to show the user a before/after performance comparison right away
    (unlike the initial big dataset upload, which is fire-and-forget).
    """
    dataset = db.query(models.Dataset).filter(models.Dataset.id == payload.dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if dataset.status != "completed":
        raise HTTPException(status_code=409, detail="Dataset must be fully processed before retraining")

    try:
        new_model = ml_service.retrain_model(db, payload.dataset_id, payload.model_name, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return _to_out(new_model)
