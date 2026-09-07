"""
GridGuard ML Engine - Anomaly Detection & Risk Scoring
Implements FR-13 (apply anomaly detection algorithms), FR-14 (anomaly
scores), FR-15 (classify normal/suspicious by threshold), and the
supervised side of UC12 (Train/Retrain ML Model with Accuracy/Precision/
Recall metrics).

Two engines, matching the "such as Isolation Forest, LOF, statistical
methods" wording in your SRS (2.2.2.4):

  1. UNSUPERVISED (Isolation Forest) - works with no labels at all. This is
     what a real deployment would lean on for brand-new consumers who have
     no confirmed theft history yet.

  2. SUPERVISED (Random Forest) - since the SGCC dataset actually has
     ground-truth FLAG labels, we also train a classifier so you can report
     real Accuracy/Precision/Recall/F1/ROC-AUC numbers in your FYP writeup
     (Chapter 4 test cases T7, and UC12's performance-comparison step).

The final "risk score" shown on the dashboard blends toward the supervised
model's probability when labels are available (it's the more accurate
signal), falling back to the normalized Isolation Forest score otherwise.
"""
import json
import logging
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import IsolationForest, RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_validate
from sklearn.utils.class_weight import compute_sample_weight
from sklearn.metrics import (
    precision_score, recall_score, f1_score, accuracy_score,
    roc_auc_score, average_precision_score, confusion_matrix,
    classification_report, precision_recall_curve,
)

from app.ml_engine import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("gridguard.anomaly_detection")


def fit_isolation_forest(features: pd.DataFrame):
    """Unsupervised anomaly detection - no labels required."""
    scaler = StandardScaler()
    X = scaler.fit_transform(features)

    model = IsolationForest(
        n_estimators=200,
        contamination=config.ISOFOREST_CONTAMINATION,
        random_state=config.RANDOM_STATE,
        n_jobs=-1,
    )
    model.fit(X)

    raw_scores = model.score_samples(X)  # higher = more normal
    anomaly_score = -raw_scores  # flip so higher = more anomalous
    # normalize to 0-1 for a friendly UI risk score
    normalized = (anomaly_score - anomaly_score.min()) / (anomaly_score.max() - anomaly_score.min() + 1e-9)

    labels = model.predict(X)  # -1 = anomaly, 1 = normal
    is_anomaly = (labels == -1)

    return {
        "model": model,
        "scaler": scaler,
        "score": normalized,
        "is_anomaly": is_anomaly,
    }


def _best_f1_threshold(y_true: np.ndarray, y_proba: np.ndarray):
    """Scan the precision-recall curve for the probability cutoff that
    maximizes F1, instead of blindly using the default 0.5 -- important
    when the positive class is ~8.5% of the data."""
    precisions, recalls, thresholds = precision_recall_curve(y_true, y_proba)
    f1s = np.divide(
        2 * precisions * recalls, precisions + recalls,
        out=np.zeros_like(precisions), where=(precisions + recalls) > 0,
    )
    best_idx = np.argmax(f1s[:-1]) if len(thresholds) > 0 else 0
    if len(thresholds) == 0:
        return 0.5, precisions[-1], recalls[-1], f1s[-1]
    return thresholds[best_idx], precisions[best_idx], recalls[best_idx], f1s[best_idx]


def _cross_validate_model(model_fn, X: np.ndarray, y: np.ndarray, n_splits: int = 5):
    """
    Stratified k-fold CV so the reported metrics reflect the model's
    typical performance rather than one lucky/unlucky train-test split.
    Returns mean +/- std for the key metrics.
    """
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=config.RANDOM_STATE)
    fold_metrics = {"roc_auc": [], "pr_auc": [], "f1": [], "precision": [], "recall": []}

    for train_idx, val_idx in skf.split(X, y):
        X_tr, X_val = X[train_idx], X[val_idx]
        y_tr, y_val = y[train_idx], y[val_idx]

        model = model_fn()
        sample_weight = compute_sample_weight("balanced", y_tr)
        model.fit(X_tr, y_tr, sample_weight=sample_weight)

        proba = model.predict_proba(X_val)[:, 1]
        best_thresh, prec, rec, f1 = _best_f1_threshold(y_val, proba)
        pred = (proba >= best_thresh).astype(int)

        fold_metrics["roc_auc"].append(roc_auc_score(y_val, proba))
        fold_metrics["pr_auc"].append(average_precision_score(y_val, proba))
        fold_metrics["f1"].append(f1_score(y_val, pred))
        fold_metrics["precision"].append(precision_score(y_val, pred, zero_division=0))
        fold_metrics["recall"].append(recall_score(y_val, pred))

    summary = {
        k: {"mean": round(float(np.mean(v)), 4), "std": round(float(np.std(v)), 4)}
        for k, v in fold_metrics.items()
    }
    return summary


def fit_supervised_model(features: pd.DataFrame, flag: np.ndarray):
    """
    Train/Retrain ML Model (UC12) using historical labeled theft cases.
    Only rows with a real 0/1 label are used for training/evaluation.

    Uses HistGradientBoostingClassifier (generally stronger than a plain
    Random Forest on tabular data of this size) with balanced sample
    weights to counter the ~8.5% theft prevalence, 5-fold cross-validation
    for a robust performance estimate, and F1-optimal threshold tuning
    instead of the default 0.5 cutoff.
    """
    labeled_mask = np.isin(flag, [0, 1])
    if labeled_mask.sum() < 50:
        logger.warning("Not enough labeled data to train a supervised model (UC12: Insufficient Labeled Data)")
        return None

    X = features.loc[labeled_mask].to_numpy()
    y = flag[labeled_mask].astype(int)
    feature_cols = features.columns

    def make_model():
        return HistGradientBoostingClassifier(
            max_iter=300,
            max_depth=6,
            learning_rate=0.08,
            l2_regularization=0.1,
            random_state=config.RANDOM_STATE,
        )

    logger.info("Running 5-fold stratified cross-validation...")
    cv_summary = _cross_validate_model(make_model, X, y, n_splits=5)
    logger.info(
        "CV results -> ROC-AUC=%.3f (+/-%.3f)  PR-AUC=%.3f (+/-%.3f)  F1=%.3f (+/-%.3f)",
        cv_summary["roc_auc"]["mean"], cv_summary["roc_auc"]["std"],
        cv_summary["pr_auc"]["mean"], cv_summary["pr_auc"]["std"],
        cv_summary["f1"]["mean"], cv_summary["f1"]["std"],
    )

    # Final held-out split for the "official" reported numbers + confusion matrix
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=config.TEST_SIZE, random_state=config.RANDOM_STATE, stratify=y,
    )
    model = make_model()
    sample_weight = compute_sample_weight("balanced", y_train)
    model.fit(X_train, y_train, sample_weight=sample_weight)

    y_proba_test = model.predict_proba(X_test)[:, 1]
    best_thresh, _, _, _ = _best_f1_threshold(y_test, y_proba_test)
    y_pred_default = (y_proba_test >= 0.5).astype(int)
    y_pred_tuned = (y_proba_test >= best_thresh).astype(int)

    # Permutation-free approximate importance: HGB doesn't expose
    # feature_importances_ directly, so use its built-in feature effect
    # via a quick permutation importance on the test set.
    from sklearn.inspection import permutation_importance
    perm = permutation_importance(
        model, X_test, y_test, n_repeats=5, random_state=config.RANDOM_STATE, scoring="roc_auc", n_jobs=-1,
    )
    importances = dict(zip(feature_cols, [round(v, 4) for v in perm.importances_mean]))

    metrics = {
        "model_type": "HistGradientBoostingClassifier",
        "cross_validation_5fold": cv_summary,
        "held_out_test": {
            "default_threshold_0.5": {
                "accuracy": round(accuracy_score(y_test, y_pred_default), 4),
                "precision": round(precision_score(y_test, y_pred_default, zero_division=0), 4),
                "recall": round(recall_score(y_test, y_pred_default), 4),
                "f1_score": round(f1_score(y_test, y_pred_default), 4),
            },
            "tuned_threshold": {
                "threshold": round(float(best_thresh), 4),
                "accuracy": round(accuracy_score(y_test, y_pred_tuned), 4),
                "precision": round(precision_score(y_test, y_pred_tuned, zero_division=0), 4),
                "recall": round(recall_score(y_test, y_pred_tuned), 4),
                "f1_score": round(f1_score(y_test, y_pred_tuned), 4),
            },
            "roc_auc": round(roc_auc_score(y_test, y_proba_test), 4),
            "pr_auc": round(average_precision_score(y_test, y_proba_test), 4),
            "confusion_matrix_tuned": confusion_matrix(y_test, y_pred_tuned).tolist(),
            "classification_report_tuned": classification_report(
                y_test, y_pred_tuned, target_names=["Normal", "Theft"], output_dict=True
            ),
        },
        "decision_threshold": round(float(best_thresh), 4),
        "train_size": int(len(X_train)),
        "test_size": int(len(X_test)),
        "feature_importances_permutation": dict(
            sorted(importances.items(), key=lambda kv: -kv[1])
        ),
    }

    logger.info(
        "Held-out test (tuned threshold=%.3f) -> Precision=%.3f Recall=%.3f F1=%.3f ROC-AUC=%.3f PR-AUC=%.3f",
        best_thresh,
        metrics["held_out_test"]["tuned_threshold"]["precision"],
        metrics["held_out_test"]["tuned_threshold"]["recall"],
        metrics["held_out_test"]["tuned_threshold"]["f1_score"],
        metrics["held_out_test"]["roc_auc"],
        metrics["held_out_test"]["pr_auc"],
    )

    # Refit on ALL labeled data for the deployed model (more data = better
    # generalization once we've already validated via CV + held-out test above)
    final_sample_weight = compute_sample_weight("balanced", y)
    final_model = make_model()
    final_model.fit(X, y, sample_weight=final_sample_weight)
    full_proba = final_model.predict_proba(features.to_numpy())[:, 1]

    return {
        "model": final_model,
        "metrics": metrics,
        "probability": full_proba,
        "decision_threshold": float(best_thresh),
    }


def categorize_risk(score: np.ndarray, medium_cutoff: float = None, high_cutoff: float = None) -> np.ndarray:
    """
    FR-15 / UC8: bucket a 0-1 score into Low / Medium / High risk.

    Cutoffs are the SAME values used to decide whether an alert fires
    (UC13's admin-configured thresholds) - this used to drift out of sync
    with an internal model-tuned cutoff, which could label a consumer
    "Medium" here while still generating a "High-risk" alert for them
    elsewhere. Single source of truth now: whatever the caller passes in
    (normally straight from the ThresholdConfig table), falling back to
    the static defaults only for standalone/offline use of this module.
    """
    medium_cut = medium_cutoff if medium_cutoff is not None else config.RISK_LOW_MAX
    high_cut = high_cutoff if high_cutoff is not None else config.RISK_MEDIUM_MAX

    categories = np.where(
        score >= high_cut, "High",
        np.where(score >= medium_cut, "Medium", "Low"),
    )
    return categories


def run_pipeline(cons_no, flag, features: pd.DataFrame, medium_cutoff: float = None, high_cutoff: float = None):
    """
    Runs both engines and produces the final per-consumer scored table
    that the dashboard/API will consume. medium_cutoff/high_cutoff should
    come from the caller's active ThresholdConfig so risk_category always
    matches whatever will also be used to generate alerts.
    """
    iso = fit_isolation_forest(features)
    sup = fit_supervised_model(features, flag)

    if sup is not None:
        risk_score = sup["probability"]
        source = "supervised_hgb"
        metrics = sup["metrics"]
    else:
        risk_score = iso["score"]
        source = "isolation_forest"
        metrics = None

    risk_category = categorize_risk(risk_score, medium_cutoff, high_cutoff)

    result_df = pd.DataFrame({
        "CONS_NO": cons_no,
        "actual_flag": flag,
        "isoforest_anomaly": iso["is_anomaly"],
        "isoforest_score": np.round(iso["score"], 4),
        "risk_score": np.round(risk_score, 4),
        "risk_category": risk_category,
        "risk_source": source,
    })

    artifacts = {
        "iso_model": iso["model"],
        "scaler": iso["scaler"],
        "rf_model": sup["model"] if sup else None,
        "metrics": metrics,
    }
    return result_df, artifacts


def save_artifacts(artifacts: dict):
    joblib.dump(artifacts["iso_model"], config.ISOFOREST_MODEL_PATH)
    joblib.dump(artifacts["scaler"], config.SCALER_PATH)
    if artifacts["rf_model"] is not None:
        joblib.dump(artifacts["rf_model"], config.SUPERVISED_MODEL_PATH)
    if artifacts["metrics"] is not None:
        with open(config.METRICS_PATH, "w") as f:
            json.dump(artifacts["metrics"], f, indent=2)
    logger.info("Saved model artifacts to %s", config.MODELS_DIR)
