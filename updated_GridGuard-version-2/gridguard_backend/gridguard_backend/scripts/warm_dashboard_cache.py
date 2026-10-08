"""
One-off cache warm-up for existing datasets.

Why this exists: the dashboard trend/histogram caching (see
app/services/ml_service.py -> cache_dashboard_extras) is written the
moment a dataset FINISHES processing or retraining. A dataset you already
processed before this fix has no cache file yet, so its very first
dashboard load after upgrading would still be the old slow path (it
self-heals and writes the cache after that one slow load - see
get_network_trend/get_risk_histogram - so you don't actually need this
script). Run it if you'd rather warm the cache up front, e.g. right
before a demo, so even that first load is fast.

Usage (from the gridguard_backend folder, with your venv active):
    python scripts/warm_dashboard_cache.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal
from app import models
from app.services import ml_service


def main():
    db = SessionLocal()
    try:
        datasets = db.query(models.Dataset).filter(models.Dataset.status == "completed").all()
        if not datasets:
            print("No completed datasets found - nothing to warm up.")
            return

        for dataset in datasets:
            print(f"Dataset #{dataset.id} ({dataset.file_name})...", end=" ", flush=True)
            start = time.time()
            dates, values, sampled = ml_service.get_network_trend(dataset)
            bins = ml_service.get_risk_histogram(db, dataset.id)
            elapsed = time.time() - start
            if dates is None:
                print("skipped (no series file on disk)")
            else:
                print(f"cached ({len(dates)} trend points, {sum(b['count'] for b in bins)} scores) in {elapsed:.1f}s")
    finally:
        db.close()


if __name__ == "__main__":
    main()
