"""
GridGuard ML Engine - Configuration
Central place for paths and tunable parameters, referenced across the
preprocessing / feature engineering / model training modules.
"""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

RAW_DATA_PATH = os.path.join(BASE_DIR, "data", "raw", "consumption_data.csv")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
MODELS_DIR = os.path.join(BASE_DIR, "models")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")

FEATURES_PATH = os.path.join(PROCESSED_DIR, "consumer_features.parquet")
FEATURES_CSV_PATH = os.path.join(PROCESSED_DIR, "consumer_features.csv")
SCORED_CSV_PATH = os.path.join(PROCESSED_DIR, "scored_consumers.csv")

ISOFOREST_MODEL_PATH = os.path.join(MODELS_DIR, "isolation_forest.joblib")
SUPERVISED_MODEL_PATH = os.path.join(MODELS_DIR, "supervised_model.joblib")
SCALER_PATH = os.path.join(MODELS_DIR, "feature_scaler.joblib")
METRICS_PATH = os.path.join(REPORTS_DIR, "model_metrics.json")

# --- Preprocessing ---
# A consumer with more than this fraction of missing readings is dropped
# entirely (too little signal to trust any feature built from it).
MAX_MISSING_RATIO = 0.60

# --- Anomaly detection ---
# Expected proportion of anomalous consumers, used by Isolation Forest.
# Set close to the real theft prevalence in the labelled data (~8.5%) so the
# unsupervised model's contamination assumption stays realistic.
ISOFOREST_CONTAMINATION = 0.085
RANDOM_STATE = 42

# --- Risk scoring thresholds (applied to the model's probability/score) ---
RISK_LOW_MAX = 0.33
RISK_MEDIUM_MAX = 0.66
# anything above RISK_MEDIUM_MAX => High risk

TEST_SIZE = 0.2
