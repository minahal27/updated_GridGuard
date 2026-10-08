"""
Backfill feeder-level loss reconciliation for datasets that were already
processed BEFORE this feature existed - so an existing completed dataset
(like a 31k-consumer upload) doesn't need a full re-upload/reprocess
(which would needlessly re-run ML model training) just to get feeder
data. Re-derives the same cons_no/matrix the original processing run
would have, using the original uploaded file (still on disk in
data/uploads/), then runs only the feeder reconciliation step.

Usage (from the gridguard_backend folder, with your venv active):
    python scripts/backfill_feeder_loss.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal
from app import models, config
from app.ml_engine import preprocessing
from app.services import feeder_loss_service


def main():
    db = SessionLocal()
    try:
        datasets = db.query(models.Dataset).filter(models.Dataset.status == "completed").all()
        if not datasets:
            print("No completed datasets found.")
            return

        for dataset in datasets:
            already_done = db.query(models.Feeder).filter(models.Feeder.dataset_id == dataset.id).count() > 0
            if already_done:
                print(f"Dataset #{dataset.id} ({dataset.file_name}) - feeder data already exists, skipping.")
                continue

            upload_path = Path(config.UPLOADS_DIR) / f"upload_{dataset.file_name}"
            if not upload_path.exists():
                print(f"Dataset #{dataset.id} ({dataset.file_name}) - original upload file not found, skipping.")
                continue

            print(f"Dataset #{dataset.id} ({dataset.file_name}) - computing feeder loss data...", end=" ", flush=True)
            df = preprocessing.load_raw_dataset(str(upload_path))
            cons_no, flag, matrix, dates = preprocessing.clean_and_structure(df)
            cons_no, flag, matrix, missing_ratio = preprocessing.filter_sparse_consumers(cons_no, flag, matrix)
            imputed = preprocessing.impute_for_feature_computation(matrix)
            date_strs = [d.strftime("%Y-%m-%d") for d in dates]

            # cons_no here is guaranteed to line up with each Consumer's
            # series_row_index for this dataset - both are produced by the
            # same deterministic preprocessing steps against the same
            # source file, in the same order.
            feeder_by_cons, is_synthetic = feeder_loss_service.assign_feeders(df, cons_no)
            feeder_loss_service.compute_and_persist(
                db, dataset, cons_no, imputed, date_strs, feeder_by_cons, is_synthetic
            )
            print("done.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
