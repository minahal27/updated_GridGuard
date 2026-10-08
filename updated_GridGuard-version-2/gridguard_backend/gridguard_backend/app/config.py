"""
GridGuard Backend - Configuration
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Local secrets belong in a .env file beside this project, never in source
# code. Environment variables set by the operating system still take
# precedence, so production deployments can use their normal secret store.
load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
DB_DIR = DATA_DIR / "db"
MODELS_STORE_DIR = BASE_DIR / "models_store"
REPORTS_DIR = BASE_DIR / "reports_output"

for d in (UPLOADS_DIR, DB_DIR, MODELS_STORE_DIR, REPORTS_DIR):
    d.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite:///{DB_DIR / 'gridguard.db'}"

# --- Auth (JWT) ---
# NOTE FOR DEPLOYMENT: override this via an environment variable
# (SECRET_KEY) in production - never ship a hardcoded key.
SECRET_KEY = os.environ.get("GRIDGUARD_SECRET_KEY", "dev-only-change-this-secret-key-before-deploying")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8  # 8 hour session, matches "multiple times per day" login frequency in SRS

# --- Dataset upload constraints (FR-4, FR-6) ---
MAX_UPLOAD_SIZE_MB = 250
ALLOWED_UPLOAD_EXTENSIONS = {".csv"}

# --- Default anomaly detection thresholds (UC13) ---
# Seeded into the threshold_configs table on first run; admins can change
# these afterwards through the API.
DEFAULT_THRESHOLDS = {
    "risk_medium_cutoff": 0.5,   # anything >= this and < high cutoff => Medium
    "risk_high_cutoff": 0.7,     # anything >= this => High, triggers an alert
    # Feeder-level loss reconciliation (network-wide NTL detection, see
    # app/services/feeder_loss_service.py) - percentage shortfall of a
    # feeder's billed total vs its own recent baseline.
    "feeder_loss_medium_cutoff": 8.0,
    "feeder_loss_high_cutoff": 15.0,
}

# --- Feeder-level loss reconciliation ---
# How many consumers are grouped into one synthetic feeder when the
# uploaded file has no real feeder/area/transformer column (see
# app/services/feeder_loss_service.py for why/when this applies).
FEEDER_GROUP_SIZE = 250
# Trailing window (days) used to estimate a feeder's "expected" load from
# its own recent history via rolling median - longer smooths out weekly
# noise, shorter reacts faster to genuine seasonal shifts.
FEEDER_BASELINE_WINDOW_DAYS = 28

# --- Email (UC15 / FR-20) ---
# Left unset by default (SMTP is optional) - if not configured, alerts are
# still generated and stored/displayed (UC9's "Email Service Failure"
# alternate flow: the user can still see the alert on the dashboard).
SMTP_HOST = os.environ.get("GRIDGUARD_SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("GRIDGUARD_SMTP_PORT", "587"))
SMTP_USER = os.environ.get("GRIDGUARD_SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("GRIDGUARD_SMTP_PASSWORD", "")
SMTP_FROM_ADDRESS = os.environ.get("GRIDGUARD_SMTP_FROM", "alerts@gridguard.local")
EMAIL_ENABLED = bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD)

# Who alerts actually get emailed TO (separate from SMTP_FROM_ADDRESS,
# which is the sender). If set, every alert goes to this one shared ops
# mailbox - the common real-world setup for a utility's theft desk. If
# left blank, alerts fall back to every active admin account's email
# instead (see alert_service._resolve_alert_recipients).
ALERT_RECIPIENT_OVERRIDE = os.environ.get("GRIDGUARD_ALERT_RECIPIENT", "")

CORS_ORIGINS = os.environ.get("GRIDGUARD_CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
