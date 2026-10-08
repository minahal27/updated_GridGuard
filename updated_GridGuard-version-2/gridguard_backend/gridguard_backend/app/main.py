"""
GridGuard Backend - Application Entrypoint

Run with:
    uvicorn app.main:app --reload

Interactive API docs (Swagger UI) at http://localhost:8000/docs once running.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base, SessionLocal
from app import models, config
from app.security import hash_password
from app.routers import auth, datasets, dashboard, consumers, anomalies, alerts, ml_models, thresholds, logs, reports, feeders

app = FastAPI(
    title="GridGuard API",
    description="Smart Electricity Theft Detection System - backend API implementing the FYP1 SRS use cases (UC1-UC15).",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(datasets.router)
app.include_router(dashboard.router)
app.include_router(consumers.router)
app.include_router(anomalies.router)
app.include_router(alerts.router)
app.include_router(ml_models.router)
app.include_router(thresholds.router)
app.include_router(logs.router)
app.include_router(reports.router)
app.include_router(feeders.router)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    _ensure_performance_indexes()
    _seed_defaults()


def _ensure_performance_indexes():
    """
    Base.metadata.create_all() only creates tables that don't exist yet -
    it does NOT retroactively add indexes to a table that was already
    created (e.g. your existing gridguard.db from before this fix). Large
    datasets (e.g. 42k consumers) were doing full table scans on every
    dashboard/anomaly/alert query that filters by dataset_id. This runs
    on every startup and is a no-op once the indexes already exist
    (IF NOT EXISTS), so it's always safe to leave in place.
    """
    from sqlalchemy import text
    statements = [
        "CREATE INDEX IF NOT EXISTS ix_consumers_dataset_id ON consumers (dataset_id)",
        "CREATE INDEX IF NOT EXISTS ix_anomaly_results_dataset_id ON anomaly_results (dataset_id)",
        "CREATE INDEX IF NOT EXISTS ix_anomaly_results_consumer_id ON anomaly_results (consumer_id)",
        "CREATE INDEX IF NOT EXISTS ix_alerts_anomaly_result_id ON alerts (anomaly_result_id)",
    ]
    with engine.connect() as conn:
        for stmt in statements:
            conn.execute(text(stmt))
        conn.commit()


def _seed_defaults():
    """
    Creates tables on first run (SQLite - no separate migration step needed
    for an FYP-scale deployment) and seeds:
      - a default admin account, so there's always a way in on a fresh DB
      - default anomaly detection thresholds (UC13)
    Safe to run on every startup - it checks for existing rows first.
    """
    db = SessionLocal()
    try:
        if db.query(models.User).count() == 0:
            admin = models.User(
                name="System Administrator",
                email="admin@gridguard.local",
                password_hash=hash_password("ChangeMe123!"),
                role="admin",
            )
            db.add(admin)
            db.commit()
            print("Seeded default admin account: admin@gridguard.local / ChangeMe123!  <-- CHANGE THIS PASSWORD")

        # Seed any threshold types not already present, rather than only
        # seeding when the table is completely empty - otherwise a
        # database that already has the original two thresholds (from
        # before feeder-loss thresholds existed) would never pick up the
        # new ones on upgrade.
        existing_types = {t for (t,) in db.query(models.ThresholdConfig.threshold_type).all()}
        missing = {k: v for k, v in config.DEFAULT_THRESHOLDS.items() if k not in existing_types}
        if missing:
            for key, value in missing.items():
                db.add(models.ThresholdConfig(threshold_type=key, threshold_value=value))
            db.commit()
    finally:
        db.close()


@app.get("/")
def root():
    return {
        "service": "GridGuard API",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}
