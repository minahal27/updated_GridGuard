"""
GridGuard ML Engine - Training Pipeline
Run this end-to-end script to go from raw CSV -> cleaned features ->
trained models -> scored consumer table + metrics report.

Usage:
    python -m ml_engine.train_pipeline
"""
import os
import time
import logging

from app.ml_engine import config, preprocessing, feature_engineering, anomaly_detection

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("gridguard.pipeline")


def main():
    t0 = time.time()
    os.makedirs(config.PROCESSED_DIR, exist_ok=True)
    os.makedirs(config.MODELS_DIR, exist_ok=True)
    os.makedirs(config.REPORTS_DIR, exist_ok=True)

    logger.info("STEP 1/4 - Preprocessing raw dataset")
    prep = preprocessing.run()

    logger.info("STEP 2/4 - Feature engineering")
    features = feature_engineering.build_features(
        prep["raw_matrix"], prep["imputed_matrix"], prep["missing_ratio"], prep["dates"]
    )
    features.insert(0, "CONS_NO", prep["cons_no"])
    features.to_csv(config.FEATURES_CSV_PATH, index=False)
    try:
        features.to_parquet(config.FEATURES_PATH, index=False)
    except Exception:
        logger.warning("pyarrow not available, skipping parquet output (CSV saved)")

    logger.info("STEP 3/4 - Training anomaly detection models")
    feature_cols = feature_engineering.FEATURE_NAMES
    scored_df, artifacts = anomaly_detection.run_pipeline(
        prep["cons_no"], prep["flag"], features[feature_cols]
    )
    scored_df.to_csv(config.SCORED_CSV_PATH, index=False)
    anomaly_detection.save_artifacts(artifacts)

    logger.info("STEP 4/4 - Done in %.1fs", time.time() - t0)

    print("\n" + "=" * 60)
    print("GridGuard ML Pipeline - Summary")
    print("=" * 60)
    print(f"Consumers processed : {len(scored_df)}")
    print(f"Flagged High risk   : {(scored_df.risk_category == 'High').sum()}")
    print(f"Flagged Medium risk : {(scored_df.risk_category == 'Medium').sum()}")
    print(f"Flagged Low risk    : {(scored_df.risk_category == 'Low').sum()}")
    if artifacts["metrics"]:
        m = artifacts["metrics"]
        cv = m["cross_validation_5fold"]
        tuned = m["held_out_test"]["tuned_threshold"]
        print(f"\nModel: {m['model_type']}")
        print("5-fold CV (mean +/- std):")
        print(f"  ROC-AUC   : {cv['roc_auc']['mean']} (+/-{cv['roc_auc']['std']})")
        print(f"  PR-AUC    : {cv['pr_auc']['mean']} (+/-{cv['pr_auc']['std']})")
        print(f"  F1        : {cv['f1']['mean']} (+/-{cv['f1']['std']})")
        print(f"  Precision : {cv['precision']['mean']} (+/-{cv['precision']['std']})")
        print(f"  Recall    : {cv['recall']['mean']} (+/-{cv['recall']['std']})")
        print(f"\nHeld-out test set (tuned threshold={tuned['threshold']}):")
        print(f"  Accuracy  : {tuned['accuracy']}")
        print(f"  Precision : {tuned['precision']}")
        print(f"  Recall    : {tuned['recall']}")
        print(f"  F1 Score  : {tuned['f1_score']}")
        print(f"  ROC-AUC   : {m['held_out_test']['roc_auc']}")
        print(f"  PR-AUC    : {m['held_out_test']['pr_auc']}")
    print(f"\nScored consumers  -> {config.SCORED_CSV_PATH}")
    print(f"Feature table     -> {config.FEATURES_CSV_PATH}")
    print(f"Model artifacts   -> {config.MODELS_DIR}")
    print(f"Metrics report    -> {config.METRICS_PATH}")


if __name__ == "__main__":
    main()
