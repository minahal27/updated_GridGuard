"""
GridGuard Backend - ML Service
The bridge between the ml_engine package (pure data-science code, no
knowledge of the DB/API) and the rest of the application. This is where
FR-4 through FR-17 actually get wired together end to end:

    upload CSV -> preprocess -> engineer features -> detect anomalies
    -> score risk -> persist results -> generate alerts

Runs as a FastAPI BackgroundTask (see routers/datasets.py) since a full
42k-consumer dataset takes ~30-40s - long enough that the client shouldn't
block on it. The dataset's `status` field is how the frontend polls
progress (uploaded -> processing -> completed/failed).
"""
import json
import logging
import numpy as np
import pandas as pd
from pathlib import Path
from sqlalchemy.orm import Session

from app import models, config
from app.ml_engine import preprocessing, feature_engineering, anomaly_detection
from app.services import log_service, alert_service, feeder_loss_service

logger = logging.getLogger("gridguard.ml_service")


def process_dataset(db: Session, dataset_id: int, file_path: str):
    """
    Full pipeline for a newly uploaded dataset. Designed to be safe to call
    from a background task: it re-fetches its own DB session state and
    updates the Dataset row's status as it progresses, so a failure midway
    leaves the dataset in a legible "failed" state (UC3's alternate flow)
    rather than half-written.
    """
    dataset = db.query(models.Dataset).filter(models.Dataset.id == dataset_id).first()
    if dataset is None:
        logger.error("Dataset %s not found", dataset_id)
        return

    try:
        dataset.status = "processing"
        db.commit()

        # --- 1. Preprocess (FR-6, FR-9, FR-10, FR-12) ---
        df = preprocessing.load_raw_dataset(file_path)
        cons_no, flag, matrix, dates = preprocessing.clean_and_structure(df)
        cons_no, flag, matrix, missing_ratio = preprocessing.filter_sparse_consumers(cons_no, flag, matrix)
        imputed = preprocessing.impute_for_feature_computation(matrix)

        if len(cons_no) == 0:
            raise ValueError("No usable consumer records after cleaning (all consumers too sparse)")

        # --- 2. Feature engineering (FR-11) ---
        features = feature_engineering.build_features(matrix, imputed, missing_ratio, dates)

        # --- 3. Anomaly detection + risk scoring (FR-13, FR-14, FR-15) ---
        # Fetch the admin-configured thresholds (UC13) FIRST, so the
        # risk_category stored on each result and the alerts generated in
        # step 7 are always computed against the same cutoffs - no drift
        # between "labeled High" and "actually alerted".
        thresholds = alert_service.get_active_thresholds(db)
        scored_df, artifacts = anomaly_detection.run_pipeline(
            cons_no, flag, features[feature_engineering.FEATURE_NAMES],
            medium_cutoff=thresholds["risk_medium_cutoff"], high_cutoff=thresholds["risk_high_cutoff"],
        )

        # --- 4. Persist the raw reading matrix as a compact array file ---
        series_dir = Path(config.UPLOADS_DIR)
        series_path = series_dir / f"dataset_{dataset_id}_series.npz"
        np.savez_compressed(series_path, matrix=matrix.astype(np.float32))
        dataset.series_file_path = str(series_path)
        date_strs = [d.strftime("%Y-%m-%d") for d in dates]
        dataset.dates_json = json.dumps(date_strs)

        # Precompute the dashboard's chart data now, while the matrix and
        # scored results are already in memory - see cache_dashboard_extras
        # docstring for why this is what fixes slow dashboard loads.
        cache_dashboard_extras(dataset_id, matrix, date_strs, scored_df["risk_score"].to_numpy())

        # --- 5. Save the trained model as a versioned MLModel record ---
        ml_model_row = _save_model_artifacts(db, artifacts, dataset_id, model_name="GridGuard-Auto")

        # --- 6. Persist consumers + anomaly results ---
        _persist_results(db, dataset, cons_no, scored_df, ml_model_row)

        # --- 6.5. Feeder-level loss reconciliation (network-wide NTL) ---
        # Runs after consumers exist (it stamps Consumer.area with the
        # resolved feeder code) and uses the imputed matrix so daily totals
        # aren't skewed by missing-reading gaps. See feeder_loss_service
        # module docstring for the full rationale.
        feeder_by_cons, feeders_synthetic = feeder_loss_service.assign_feeders(df, cons_no)
        feeder_loss_service.compute_and_persist(
            db, dataset, cons_no, imputed, date_strs, feeder_by_cons, feeders_synthetic
        )

        dataset.record_count = len(cons_no)
        dataset.status = "completed"
        from datetime import datetime as _dt
        dataset.processed_at = _dt.utcnow()
        db.commit()

        # --- 7. Generate alerts for consumers crossing the High-risk threshold (UC9) ---
        alert_service.generate_alerts_for_dataset(db, dataset_id)

        log_service.log_event(
            db, event_type="dataset_processed", user_id=dataset.uploaded_by,
            details=f"Processed {len(cons_no)} consumers, {int((scored_df.risk_category=='High').sum())} high-risk",
            related_table="datasets", related_id=dataset_id,
        )
        logger.info("Dataset %s processed successfully (%d consumers)", dataset_id, len(cons_no))

    except Exception as exc:
        logger.exception("Dataset %s processing failed", dataset_id)
        dataset.status = "failed"
        dataset.error_message = str(exc)
        db.commit()
        log_service.log_event(
            db, event_type="dataset_processing_failed", status="failed", severity="error",
            user_id=dataset.uploaded_by, details=str(exc),
            related_table="datasets", related_id=dataset_id,
        )


def _save_model_artifacts(db: Session, artifacts: dict, dataset_id: int, model_name: str):
    """Persist the trained model(s) to disk + a DB record (UC2/UC12)."""
    import joblib
    from datetime import datetime

    version = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    model_dir = Path(config.MODELS_STORE_DIR) / f"{model_name}_{version}"
    model_dir.mkdir(parents=True, exist_ok=True)

    iso_path = model_dir / "isolation_forest.joblib"
    scaler_path = model_dir / "scaler.joblib"
    joblib.dump(artifacts["iso_model"], iso_path)
    joblib.dump(artifacts["scaler"], scaler_path)

    algorithm_type = "IsolationForest"
    if artifacts.get("rf_model") is not None:
        sup_path = model_dir / "supervised_model.joblib"
        joblib.dump(artifacts["rf_model"], sup_path)
        algorithm_type = "IsolationForest + HistGradientBoosting"

    # Deactivate any previously active model, this one becomes current
    db.query(models.MLModel).filter(models.MLModel.is_active == True).update({"is_active": False})  # noqa: E712

    ml_model = models.MLModel(
        model_name=model_name,
        model_version=version,
        algorithm_type=algorithm_type,
        file_path=str(model_dir),
        scaler_path=str(scaler_path),
        metrics_json=json.dumps(artifacts["metrics"]) if artifacts.get("metrics") else None,
        training_dataset_id=dataset_id,
        is_active=True,
    )
    db.add(ml_model)
    db.commit()
    db.refresh(ml_model)
    return ml_model


def _persist_results(db: Session, dataset: models.Dataset, cons_no: np.ndarray, scored_df: pd.DataFrame, ml_model_row: models.MLModel):
    """Bulk-insert Consumer + AnomalyResult rows for a processed dataset."""
    consumer_rows = []
    for idx, cid in enumerate(cons_no):
        consumer_rows.append(models.Consumer(
            dataset_id=dataset.id,
            cons_no=str(cid),
            series_row_index=idx,
        ))
    db.bulk_save_objects(consumer_rows, return_defaults=True)
    db.flush()

    # Re-query to get assigned IDs in insertion order (bulk_save_objects with
    # return_defaults populates .id on the objects directly - use that)
    consumer_id_by_row = {c.series_row_index: c.id for c in consumer_rows}

    anomaly_rows = []
    for i, row in scored_df.reset_index(drop=True).iterrows():
        actual_flag = int(row["actual_flag"]) if row["actual_flag"] in (0, 1) else None
        anomaly_rows.append(models.AnomalyResult(
            dataset_id=dataset.id,
            consumer_id=consumer_id_by_row[i],
            model_id=ml_model_row.id,
            isoforest_anomaly=bool(row["isoforest_anomaly"]),
            isoforest_score=float(row["isoforest_score"]),
            risk_score=float(row["risk_score"]),
            risk_category=str(row["risk_category"]),
            risk_source=str(row["risk_source"]),
            actual_flag=actual_flag,
        ))
    db.bulk_save_objects(anomaly_rows)
    db.commit()


def get_consumer_series(dataset: models.Dataset, row_index: int):
    """Load one consumer's daily readings from the dataset's .npz array (UC5)."""
    if not dataset.series_file_path or not Path(dataset.series_file_path).exists():
        return None, None
    with np.load(dataset.series_file_path) as npz:
        row = npz["matrix"][row_index]
    dates = json.loads(dataset.dates_json)
    values = [None if np.isnan(v) else float(v) for v in row]
    return dates, values


# ---------- Dashboard chart caching ----------
#
# PERFORMANCE NOTE (dashboard load time)
# The network trend and risk histogram used to recompute from scratch on
# EVERY dashboard visit: the trend endpoint reloaded the full reading
# matrix (n_consumers x n_days - ~42k x ~1000 for the SGCC dataset, tens
# to hundreds of MB) from disk and ran nanmean over it, and the histogram
# endpoint re-scanned every AnomalyResult row. Both are cheap once, but
# expensive on every page load.
#
# Fix: compute both ONCE - right when the dataset finishes processing or
# retraining, while the matrix/scored results are already sitting in
# memory anyway - and cache the (tiny) results as JSON files. A dashboard
# visit then just reads a few KB from disk instead of re-crunching
# millions of numbers. Datasets processed before this existed still work:
# the first request recomputes and backfills the cache, every request
# after that is fast.
def _trend_cache_path(dataset_id: int) -> Path:
    return Path(config.UPLOADS_DIR) / f"dataset_{dataset_id}_trend_cache.json"


def _histogram_cache_path(dataset_id: int) -> Path:
    return Path(config.UPLOADS_DIR) / f"dataset_{dataset_id}_histogram_cache.json"


def _compute_trend_from_matrix(matrix: np.ndarray, dates: list, max_points: int = 180):
    daily_avg = np.nanmean(matrix, axis=0)
    dates = list(dates)
    sampled = False
    if len(dates) > max_points:
        sampled = True
        step = int(np.ceil(len(dates) / max_points))
        idx = list(range(0, len(dates), step))
        dates = [dates[i] for i in idx]
        daily_avg = daily_avg[idx]
    values = [None if np.isnan(v) else round(float(v), 3) for v in daily_avg]
    return dates, values, sampled


def _compute_histogram_from_scores(scores, bin_width: float = 0.1):
    n_bins = int(round(1.0 / bin_width))
    counts = [0] * n_bins
    for s in scores:
        if s is None:
            continue
        idx = min(int(s / bin_width), n_bins - 1) if s >= 0 else 0
        counts[idx] += 1
    return [
        {"range_start": round(i * bin_width, 2), "range_end": round((i + 1) * bin_width, 2), "count": counts[i]}
        for i in range(n_bins)
    ]


def cache_dashboard_extras(dataset_id: int, matrix: np.ndarray, date_strs: list, risk_scores) -> None:
    """Call this once right after a dataset finishes processing/retraining
    (matrix + scored results already in memory) to precompute both chart
    payloads. Failures here are logged but never allowed to fail the
    calling pipeline - worst case, charts just fall back to computing
    on-demand the way they used to."""
    try:
        dates_out, values, sampled = _compute_trend_from_matrix(matrix, date_strs)
        _trend_cache_path(dataset_id).write_text(json.dumps({"dates": dates_out, "avg_consumption": values, "sampled": sampled}))

        bins = _compute_histogram_from_scores(list(risk_scores))
        _histogram_cache_path(dataset_id).write_text(json.dumps(bins))
    except Exception:
        logger.exception("Failed to precompute dashboard chart cache for dataset %s (non-fatal)", dataset_id)


def get_network_trend(dataset: models.Dataset, max_points: int = 180):
    """
    Dataset-wide average daily consumption (UC4 dashboard chart).
    Serves from the precomputed cache (see cache_dashboard_extras) when
    available; only falls back to loading the full .npz matrix for
    datasets processed before caching existed, and backfills the cache
    afterwards so it's fast from then on.
    """
    cache_path = _trend_cache_path(dataset.id)
    if cache_path.exists():
        try:
            cached = json.loads(cache_path.read_text())
            return cached["dates"], cached["avg_consumption"], cached["sampled"]
        except Exception:
            logger.warning("Trend cache for dataset %s unreadable, recomputing", dataset.id)

    if not dataset.series_file_path or not Path(dataset.series_file_path).exists():
        return None, None, False

    with np.load(dataset.series_file_path) as npz:
        matrix = npz["matrix"]
    dates = json.loads(dataset.dates_json)
    dates_out, values, sampled = _compute_trend_from_matrix(matrix, dates, max_points)

    try:
        cache_path.write_text(json.dumps({"dates": dates_out, "avg_consumption": values, "sampled": sampled}))
    except Exception:
        pass
    return dates_out, values, sampled


def get_risk_histogram(db: Session, dataset_id: int, bin_width: float = 0.1):
    """
    Risk score distribution across all consumers, for the dashboard
    histogram. Serves from the precomputed cache when available (see
    cache_dashboard_extras); falls back to a DB scan + backfills the
    cache for datasets processed before caching existed.
    """
    cache_path = _histogram_cache_path(dataset_id)
    if cache_path.exists():
        try:
            return json.loads(cache_path.read_text())
        except Exception:
            logger.warning("Histogram cache for dataset %s unreadable, recomputing", dataset_id)

    scores = [
        r[0] for r in
        db.query(models.AnomalyResult.risk_score).filter(models.AnomalyResult.dataset_id == dataset_id).all()
    ]
    bins = _compute_histogram_from_scores(scores, bin_width)
    try:
        cache_path.write_text(json.dumps(bins))
    except Exception:
        pass
    return bins


def retrain_model(db: Session, dataset_id: int, model_name: str, triggered_by: int):
    """
    UC12: retrain the supervised model on a (possibly updated/re-labeled)
    dataset. Re-runs the same feature engineering + training used at
    upload time, saves the result as a new versioned MLModel, and rescoring
    the dataset's existing AnomalyResult rows with the new model.
    """
    dataset = db.query(models.Dataset).filter(models.Dataset.id == dataset_id).first()
    if dataset is None or dataset.status != "completed":
        raise ValueError("Dataset not found or not yet processed")

    # Re-derive features from the stored series array + consumers (rather
    # than re-reading the original upload) so retraining still works even
    # if the source CSV has since been moved or deleted.
    with np.load(dataset.series_file_path) as npz:
        matrix = npz["matrix"].astype(float)
    dates = [pd.Timestamp(d) for d in json.loads(dataset.dates_json)]

    consumers = sorted(dataset.consumers, key=lambda c: c.series_row_index)
    cons_no = np.array([c.cons_no for c in consumers])
    # actual_flag from the most recent anomaly results (captures any manual re-labeling done via alerts review)
    flag_map = {ar.consumer_id: ar.actual_flag for ar in db.query(models.AnomalyResult).filter(models.AnomalyResult.dataset_id == dataset_id)}
    flag = np.array([flag_map.get(c.id) if flag_map.get(c.id) is not None else -1 for c in consumers])

    missing_ratio = np.isnan(matrix).mean(axis=1)
    imputed = preprocessing.impute_for_feature_computation(matrix)
    features = feature_engineering.build_features(matrix, imputed, missing_ratio, dates)

    thresholds = alert_service.get_active_thresholds(db)
    scored_df, artifacts = anomaly_detection.run_pipeline(
        cons_no, flag, features[feature_engineering.FEATURE_NAMES],
        medium_cutoff=thresholds["risk_medium_cutoff"], high_cutoff=thresholds["risk_high_cutoff"],
    )

    ml_model_row = _save_model_artifacts(db, artifacts, dataset_id, model_name=model_name)

    # Refresh the dashboard chart cache too - risk scores just changed, so
    # the old histogram would be stale (the trend cache doesn't actually
    # change on retrain since raw readings didn't change, but recomputing
    # both together keeps this one call site simple).
    cache_dashboard_extras(dataset_id, matrix, json.loads(dataset.dates_json), scored_df["risk_score"].to_numpy())

    # Rescore existing AnomalyResult rows with the freshly trained model
    consumer_id_by_cons_no = {c.cons_no: c.id for c in consumers}
    for _, row in scored_df.iterrows():
        cid = consumer_id_by_cons_no[row["CONS_NO"]]
        existing = db.query(models.AnomalyResult).filter(
            models.AnomalyResult.dataset_id == dataset_id,
            models.AnomalyResult.consumer_id == cid,
        ).first()
        if existing:
            existing.model_id = ml_model_row.id
            existing.isoforest_anomaly = bool(row["isoforest_anomaly"])
            existing.isoforest_score = float(row["isoforest_score"])
            existing.risk_score = float(row["risk_score"])
            existing.risk_category = str(row["risk_category"])
            existing.risk_source = str(row["risk_source"])
    db.commit()

    alert_service.generate_alerts_for_dataset(db, dataset_id)

    log_service.log_event(
        db, event_type="model_retrained", user_id=triggered_by,
        details=f"Retrained on dataset {dataset_id} -> model {ml_model_row.model_name} v{ml_model_row.model_version}",
        related_table="ml_models", related_id=ml_model_row.id,
    )
    return ml_model_row
