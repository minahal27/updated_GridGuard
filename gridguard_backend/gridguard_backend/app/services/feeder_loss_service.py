"""
GridGuard Backend - Feeder-Level Loss Reconciliation

WHY THIS EXISTS
Per-consumer anomaly detection (app/ml_engine/anomaly_detection.py) catches
an individual meter behaving strangely relative to ITS OWN history. It can
miss a different, arguably more damaging pattern: many meters on the SAME
feeder/transformer all drifting down together in a way that's small per
consumer but adds up to a large aggregate shortfall - the classic signature
of Non-Technical Loss (NTL) at the network level (a tapped line upstream of
the meters, synchronized tampering across a neighbourhood, etc). The
project's own SRS names this directly: NTLs are losses "due to theft...
tampering...not related to physical transmission" - and they show up in the
GAP between what a feeder should be delivering and what its meters actually
bill, not necessarily in any single meter's trace.

WHAT THIS MODULE DOES
For each feeder (a group of consumers sharing a feeder/transformer id):
  1. Sums daily billed kWh across every consumer on that feeder.
  2. Estimates that feeder's own "expected" load from a trailing rolling
     median of ITS OWN recent history (robust to one-off spikes) - so
     "expected" always means "what this specific feeder normally does",
     never a fixed number applied network-wide.
  3. Flags days where billed falls meaningfully short of expected as a
     loss event, and rolls that up into a feeder-level risk category
     (Low/Medium/High) using the same admin-configurable threshold
     pattern already used for consumer-level risk (UC13).

DATA CAVEAT - be upfront about this in the report/demo
The SGCC dataset (like most public smart-meter datasets) has no real
feeder/transformer identifier - only a consumer ID and daily readings. So
when the uploaded file doesn't include a feeder/area/transformer column,
this module SYNTHESIZES a stable grouping (consumers sorted by ID, chunked
into feeders of config.FEEDER_GROUP_SIZE) purely so the feature is
demonstrable end to end. This is consistent with the project's existing
scope (SRS 2.1.2: "historical or simulated data...not integrated with any
physical smart meters") - it's flagged via Feeder.is_synthetic and shown
plainly in the UI, never silently presented as real grid topology. If an
uploaded CSV DOES include a feeder/area/transformer column, that real
grouping is used automatically instead - no code change needed.
"""
import logging
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app import models, config

logger = logging.getLogger("gridguard.feeder_loss_service")

FEEDER_COLUMN_CANDIDATES = ["FEEDER", "FEEDER_ID", "AREA", "TRANSFORMER", "TRANSFORMER_ID", "ZONE"]


def assign_feeders(raw_df: pd.DataFrame, cons_no: np.ndarray):
    """
    Returns (feeder_code_by_cons_no: dict[str, str], is_synthetic: bool).
    Prefers a real feeder/area/transformer column from the uploaded file;
    falls back to a deterministic synthetic grouping (stable across
    re-runs since it's based on sorted consumer ID, not upload row order).
    """
    found_col = None
    for candidate in FEEDER_COLUMN_CANDIDATES:
        for col in raw_df.columns:
            if col.strip().upper() == candidate:
                found_col = col
                break
        if found_col:
            break

    cons_no_str = [str(c) for c in cons_no]

    if found_col:
        lookup = dict(zip(raw_df["CONS_NO"].astype(str), raw_df[found_col].astype(str)))
        feeder_by_cons = {c: (lookup.get(c) or "UNASSIGNED") for c in cons_no_str}
        logger.info("Feeder assignment: using source column '%s'", found_col)
        return feeder_by_cons, False

    ordered = sorted(cons_no_str)
    group_size = config.FEEDER_GROUP_SIZE
    feeder_by_cons = {}
    for i, c in enumerate(ordered):
        group_idx = i // group_size
        feeder_by_cons[c] = f"FDR-{group_idx + 1:03d}"
    logger.info(
        "Feeder assignment: no feeder/area column in source file - synthesized %d groups of ~%d consumers",
        len(set(feeder_by_cons.values())), group_size,
    )
    return feeder_by_cons, True


def get_feeder_thresholds(db: Session) -> dict:
    rows = db.query(models.ThresholdConfig).filter(
        models.ThresholdConfig.threshold_type.in_(["feeder_loss_medium_cutoff", "feeder_loss_high_cutoff"]),
        models.ThresholdConfig.is_active == True,  # noqa: E712
    ).all()
    values = {r.threshold_type: r.threshold_value for r in rows}
    return {
        "feeder_loss_medium_cutoff": values.get(
            "feeder_loss_medium_cutoff", config.DEFAULT_THRESHOLDS["feeder_loss_medium_cutoff"]
        ),
        "feeder_loss_high_cutoff": values.get(
            "feeder_loss_high_cutoff", config.DEFAULT_THRESHOLDS["feeder_loss_high_cutoff"]
        ),
    }


def compute_and_persist(
    db: Session,
    dataset: models.Dataset,
    cons_no: np.ndarray,
    matrix: np.ndarray,        # imputed matrix, n_consumers x n_days, same row order as cons_no
    date_strs: list,
    feeder_by_cons: dict,
    is_synthetic: bool,
):
    """
    Aggregates the (already-imputed) reading matrix by feeder, computes a
    rolling-median expected baseline per feeder, and persists Feeder +
    FeederDailyLoss rows. Also stamps each Consumer.area with its feeder
    code (that field already existed in the schema for exactly this - see
    the original ERD - so no migration is needed on an existing database).

    Must run AFTER Consumer rows exist for this dataset (i.e. after
    ml_service._persist_results), since it updates Consumer.area in place.
    """
    thresholds = get_feeder_thresholds(db)
    medium_cutoff = thresholds["feeder_loss_medium_cutoff"]
    high_cutoff = thresholds["feeder_loss_high_cutoff"]

    cons_no_str = [str(c) for c in cons_no]
    feeder_codes = [feeder_by_cons.get(c, "UNASSIGNED") for c in cons_no_str]
    unique_feeders = sorted(set(feeder_codes))
    feeder_index = {code: i for i, code in enumerate(unique_feeders)}
    row_group = np.array([feeder_index[c] for c in feeder_codes])

    n_feeders = len(unique_feeders)
    n_days = matrix.shape[1]
    feeder_totals = np.zeros((n_feeders, n_days), dtype=float)
    for g in range(n_feeders):
        feeder_totals[g] = matrix[row_group == g].sum(axis=0)

    # Clear any prior feeder rows for this dataset (defensive - only
    # matters if this ever gets called twice for the same dataset, e.g. a
    # future re-upload-in-place flow; normal processing calls this once).
    old_feeder_ids = [
        fid for (fid,) in db.query(models.Feeder.id).filter(models.Feeder.dataset_id == dataset.id).all()
    ]
    if old_feeder_ids:
        db.query(models.FeederDailyLoss).filter(models.FeederDailyLoss.feeder_id.in_(old_feeder_ids)).delete(
            synchronize_session=False
        )
        db.query(models.Feeder).filter(models.Feeder.dataset_id == dataset.id).delete(synchronize_session=False)
        db.flush()

    feeder_rows = []
    for code in unique_feeders:
        count = int((row_group == feeder_index[code]).sum())
        feeder_rows.append(models.Feeder(
            dataset_id=dataset.id, feeder_code=code, is_synthetic=is_synthetic, consumer_count=count,
        ))
    db.bulk_save_objects(feeder_rows, return_defaults=True)
    db.flush()
    feeder_id_by_code = {f.feeder_code: f.id for f in feeder_rows}

    window = config.FEEDER_BASELINE_WINDOW_DAYS
    daily_loss_rows = []

    for code in unique_feeders:
        series = pd.Series(feeder_totals[feeder_index[code]])
        # Trailing baseline: "expected today" is the median of the
        # PRECEDING window (shift(1) so today's own value never leaks
        # into its own expectation). Early days with no trailing window
        # yet fall back to the feeder's overall median.
        expected = series.rolling(window=window, min_periods=max(7, window // 4)).median().shift(1)
        expected = expected.fillna(series.median())

        actual = series.to_numpy()
        expected_arr = expected.to_numpy()
        loss_kwh = np.maximum(0.0, expected_arr - actual)
        with np.errstate(divide="ignore", invalid="ignore"):
            loss_pct = np.where(expected_arr > 0, (loss_kwh / expected_arr) * 100.0, 0.0)

        fid = feeder_id_by_code[code]
        event_days = int((loss_pct >= medium_cutoff).sum())
        avg_loss = float(np.mean(loss_pct)) if n_days else 0.0
        peak_loss = float(np.max(loss_pct)) if n_days else 0.0
        risk_category = "High" if avg_loss >= high_cutoff else ("Medium" if avg_loss >= medium_cutoff else "Low")

        for d in range(n_days):
            daily_loss_rows.append(models.FeederDailyLoss(
                feeder_id=fid, date=date_strs[d],
                billed_kwh=round(float(actual[d]), 2),
                expected_kwh=round(float(expected_arr[d]), 2),
                loss_kwh=round(float(loss_kwh[d]), 2),
                loss_pct=round(float(loss_pct[d]), 2),
            ))

        feeder_row = next(f for f in feeder_rows if f.feeder_code == code)
        feeder_row.avg_loss_pct = round(avg_loss, 2)
        feeder_row.peak_loss_pct = round(peak_loss, 2)
        feeder_row.loss_event_days = event_days
        feeder_row.risk_category = risk_category

    db.bulk_save_objects(daily_loss_rows)

    # Stamp each consumer's feeder code onto the pre-existing `area` field
    # (already part of the schema - see models.Consumer) so the consumer
    # detail page can show/link which feeder a consumer belongs to.
    consumers = db.query(models.Consumer).filter(models.Consumer.dataset_id == dataset.id).all()
    for c in consumers:
        code = feeder_by_cons.get(str(c.cons_no))
        if code:
            c.area = code

    db.commit()
    logger.info(
        "Feeder loss reconciliation: %d feeders (%s) for dataset %s",
        n_feeders, "synthetic grouping" if is_synthetic else "source file grouping", dataset.id,
    )
