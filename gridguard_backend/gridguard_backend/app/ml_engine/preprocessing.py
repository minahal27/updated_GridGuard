"""
GridGuard ML Engine - Preprocessing
Implements FR-9 (preprocess raw data), FR-10 (handle missing/invalid values),
FR-12 (preprocess time-series for anomaly detection) from the SRS.

The raw SGCC file is "wide": one row per consumer (CONS_NO), a FLAG column
(1 = confirmed theft, 0 = normal), then one column per calendar date holding
that day's kWh reading. The date columns are NOT in chronological order in
the raw file (they're sorted as text, e.g. "2014/1/1", "2014/1/10", "2014/1/11" ...),
so the first job is to put them back in time order before anything else
(rolling windows / trend / drop detection are meaningless on a shuffled axis).
"""
import numpy as np
import pandas as pd
import logging
from datetime import datetime

from app.ml_engine import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("gridguard.preprocessing")

ID_COLS = {"CONS_NO", "FLAG"}


def load_raw_dataset(path: str = config.RAW_DATA_PATH) -> pd.DataFrame:
    """FR-4: read the uploaded electricity consumption dataset (CSV)."""
    logger.info("Loading raw dataset from %s", path)
    df = pd.read_csv(path)
    logger.info("Loaded %d consumers x %d columns", df.shape[0], df.shape[1])
    return df


def _sort_date_columns(df: pd.DataFrame) -> list:
    """Return the date columns in true chronological order."""
    date_cols = [c for c in df.columns if c not in ID_COLS]
    parsed = []
    for c in date_cols:
        try:
            parsed.append((datetime.strptime(c, "%Y/%m/%d"), c))
        except ValueError:
            # Skip any column that isn't a parseable date (defensive; FR-6)
            continue
    parsed.sort(key=lambda x: x[0])
    ordered_cols = [c for _, c in parsed]
    ordered_dates = [d for d, _ in parsed]
    return ordered_cols, ordered_dates


def clean_and_structure(df: pd.DataFrame):
    """
    FR-6: validate uploaded data (correct format / required fields present).
    FR-9/FR-10: clean and structure the time series per consumer.

    Returns:
        cons_no   : np.ndarray of consumer IDs
        flag      : np.ndarray of theft labels (0/1), may contain -1 for
                    unlabeled rows if the dataset doesn't have FLAG
        matrix    : np.ndarray (n_consumers x n_days) of raw readings, NaN
                    where missing, in chronological column order
        dates     : ordered list of datetime objects matching matrix columns
    """
    if "CONS_NO" not in df.columns:
        raise ValueError("Dataset missing required field: CONS_NO")

    ordered_cols, dates = _sort_date_columns(df)
    if not ordered_cols:
        raise ValueError("No valid date columns found in dataset")

    cons_no = df["CONS_NO"].to_numpy()
    flag = df["FLAG"].to_numpy() if "FLAG" in df.columns else np.full(len(df), -1)

    matrix = df[ordered_cols].to_numpy(dtype=float)

    # Treat negative readings as invalid/corrupt (physically impossible for
    # consumption) rather than silently trusting them.
    matrix[matrix < 0] = np.nan

    logger.info(
        "Structured matrix: %d consumers x %d chronological days (%s -> %s)",
        matrix.shape[0], matrix.shape[1], dates[0].date(), dates[-1].date(),
    )
    return cons_no, flag, matrix, dates


def filter_sparse_consumers(cons_no, flag, matrix, max_missing_ratio: float = config.MAX_MISSING_RATIO):
    """
    Drop consumers whose readings are too sparse to build reliable features
    from (FR-10: handle missing data using a predefined cleaning technique --
    here, exclusion beyond a sparsity threshold rather than fabricating most
    of a consumer's history).
    """
    missing_ratio = np.isnan(matrix).mean(axis=1)
    keep = missing_ratio <= max_missing_ratio
    dropped = (~keep).sum()
    logger.info(
        "Dropping %d / %d consumers with >%.0f%% missing readings",
        dropped, len(cons_no), max_missing_ratio * 100,
    )
    return cons_no[keep], flag[keep], matrix[keep], missing_ratio[keep]


def impute_for_feature_computation(matrix: np.ndarray) -> np.ndarray:
    """
    Produces a fully-imputed copy of the matrix used ONLY for computing
    smooth features (rolling means, trend, volatility). The raw missingness
    itself is preserved as its own feature elsewhere (missing_ratio), so
    imputation here doesn't erase that signal -- it just gives the
    rolling/trend math something numeric to work with.

    Strategy: linear interpolation along the time axis, then forward/back
    fill any remaining edge NaNs, then zero-fill anything still left
    (e.g. an all-NaN row, which shouldn't happen after filter_sparse_consumers
    but is handled defensively).
    """
    s = pd.DataFrame(matrix)
    s = s.interpolate(axis=1, limit_direction="both")
    s = s.fillna(0.0)
    return s.to_numpy()


def run(path: str = config.RAW_DATA_PATH):
    """Full preprocessing pipeline entry point."""
    df = load_raw_dataset(path)
    cons_no, flag, matrix, dates = clean_and_structure(df)
    cons_no, flag, matrix, missing_ratio = filter_sparse_consumers(cons_no, flag, matrix)
    imputed = impute_for_feature_computation(matrix)
    return {
        "cons_no": cons_no,
        "flag": flag,
        "raw_matrix": matrix,
        "imputed_matrix": imputed,
        "missing_ratio": missing_ratio,
        "dates": dates,
    }


if __name__ == "__main__":
    result = run()
    print("cons_no:", result["cons_no"].shape)
    print("matrix:", result["raw_matrix"].shape)
    print("theft-labelled:", int((result["flag"] == 1).sum()))
