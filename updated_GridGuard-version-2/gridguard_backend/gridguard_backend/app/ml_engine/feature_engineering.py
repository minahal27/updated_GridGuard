"""
GridGuard ML Engine - Feature Engineering
Implements FR-11: calculate derived features such as rolling averages,
daily totals, and usage trends, from each consumer's cleaned time series.

Every function here is vectorized across ALL consumers at once (operating
along axis=1, the time axis) rather than looping row-by-row in Python --
important at 42k+ consumers x 1000+ days.

The feature set is built around the consumption signatures that the
electricity-theft literature (and your SRS's "sudden increase/decrease,
irregular trends" framing) associates with tampering or theft:
  - abnormally low/flat/zero usage (bypassed or under-registering meter)
  - sudden drops (meter tampering event)
  - high volatility / erratic pattern
  - large gaps in reporting (meter reporting anomalies)
"""
import numpy as np
import pandas as pd
from scipy import stats

FEATURE_NAMES = [
    "mean_consumption",
    "std_consumption",
    "coeff_variation",
    "missing_ratio",
    "zero_ratio",
    "max_drop_pct",
    "max_spike_pct",
    "num_large_drops",
    "trend_slope",
    "rolling7_volatility",
    "skewness",
    "kurtosis",
    "min_to_mean_ratio",
    "autocorr_lag7",
    "weekday_weekend_ratio",
    "missingness_trend",
    "longest_zero_streak",
    "pct_days_below_half_mean",
    "mad_consumption",
]


def _rolling_mean_axis1(matrix: np.ndarray, window: int) -> np.ndarray:
    """Vectorized moving average along axis=1 for every row simultaneously."""
    n, m = matrix.shape
    if m < window:
        return matrix.copy()
    cumsum = np.cumsum(np.insert(matrix, 0, 0, axis=1), axis=1)
    roll = (cumsum[:, window:] - cumsum[:, :-window]) / window
    return roll  # shape: (n, m - window + 1)


def _trend_slope(matrix: np.ndarray) -> np.ndarray:
    """
    Linear-regression slope of consumption over time, per consumer,
    computed for all rows at once via the closed-form least-squares formula
    (avoids an O(n_consumers) Python loop over np.polyfit).
    """
    n, m = matrix.shape
    x = np.arange(m, dtype=float)
    x_mean = x.mean()
    x_centered = x - x_mean
    denom = np.sum(x_centered ** 2)

    y_mean = matrix.mean(axis=1, keepdims=True)
    y_centered = matrix - y_mean
    numer = y_centered @ x_centered  # (n, m) @ (m,) -> (n,)
    slope = numer / denom
    return slope


def _autocorr_lag(matrix: np.ndarray, lag: int = 7) -> np.ndarray:
    """
    Strength of the weekly consumption pattern per consumer. A healthy
    residential/commercial meter usually has a repeating weekly rhythm;
    a weak or negative autocorrelation can indicate an erratic/tampered
    signal (or a meter reporting noise instead of real usage).
    """
    n, m = matrix.shape
    if m <= lag:
        return np.zeros(n)
    mean = matrix.mean(axis=1, keepdims=True)
    centered = matrix - mean
    num = np.sum(centered[:, :-lag] * centered[:, lag:], axis=1)
    denom = np.sum(centered ** 2, axis=1)
    return np.divide(num, denom, out=np.zeros(n), where=denom > 0)


def _weekday_weekend_ratio(matrix: np.ndarray, dates: list) -> np.ndarray:
    """Mean weekday usage vs mean weekend usage (theft/tampering often
    disrupts the normal weekday/weekend rhythm of commercial/residential use)."""
    weekday_idx = np.array([d.weekday() < 5 for d in dates])
    wd_mean = matrix[:, weekday_idx].mean(axis=1)
    we_mean = matrix[:, ~weekday_idx].mean(axis=1)
    return np.divide(wd_mean, we_mean, out=np.ones_like(wd_mean), where=we_mean > 0.01)


def _missingness_trend(raw_matrix: np.ndarray) -> np.ndarray:
    """Change in reporting gaps between the first and second half of the
    observation window - a rising trend can flag a meter that started
    being tampered with or bypassed partway through."""
    m = raw_matrix.shape[1]
    mid = m // 2
    first_missing = np.isnan(raw_matrix[:, :mid]).mean(axis=1)
    second_missing = np.isnan(raw_matrix[:, mid:]).mean(axis=1)
    return second_missing - first_missing


def _longest_zero_streak(raw_matrix: np.ndarray) -> np.ndarray:
    """Longest run of consecutive zero-consumption days - a flat-lined
    meter is one of the clearest tampering/bypass signatures."""
    mask = (raw_matrix == 0).astype(np.int32)
    n, m = mask.shape
    run = np.zeros_like(mask)
    run[:, 0] = mask[:, 0]
    for i in range(1, m):
        run[:, i] = (run[:, i - 1] + 1) * mask[:, i]
    return run.max(axis=1)


def build_features(raw_matrix: np.ndarray, imputed_matrix: np.ndarray, missing_ratio: np.ndarray, dates: list = None) -> pd.DataFrame:
    """
    Build the per-consumer feature table.

    raw_matrix      : original readings with NaN for missing (used for
                       missing/zero ratios so imputed zeros don't distort them)
    imputed_matrix  : gap-filled series (used for smooth features: rolling
                       volatility, trend, spikes/drops)
    missing_ratio   : precomputed from preprocessing (kept consistent)
    """
    mean_c = np.nanmean(raw_matrix, axis=1)
    std_c = np.nanstd(raw_matrix, axis=1)
    cv = np.divide(std_c, mean_c, out=np.zeros_like(std_c), where=mean_c > 0)

    valid_counts = np.sum(~np.isnan(raw_matrix), axis=1)
    zero_ratio = np.divide(
        np.nansum(raw_matrix == 0, axis=1), valid_counts,
        out=np.zeros_like(mean_c), where=valid_counts > 0,
    )

    # Day-over-day percentage change on the imputed series
    diffs = np.diff(imputed_matrix, axis=1)
    prev = imputed_matrix[:, :-1]
    with np.errstate(divide="ignore", invalid="ignore"):
        pct_change = np.where(prev > 0.01, diffs / prev, 0.0)
    max_drop_pct = np.nanmin(pct_change, axis=1)   # most negative = biggest drop
    max_spike_pct = np.nanmax(pct_change, axis=1)  # most positive = biggest spike
    num_large_drops = np.sum(pct_change < -0.5, axis=1)  # count of >50% single-day drops

    trend_slope = _trend_slope(imputed_matrix)

    roll7 = _rolling_mean_axis1(imputed_matrix, window=7)
    rolling7_volatility = np.std(roll7, axis=1)

    skewness = stats.skew(imputed_matrix, axis=1, nan_policy="omit")
    kurtosis = stats.kurtosis(imputed_matrix, axis=1, nan_policy="omit")

    min_c = np.nanmin(raw_matrix, axis=1)
    min_to_mean_ratio = np.divide(min_c, mean_c, out=np.zeros_like(mean_c), where=mean_c > 0)

    autocorr_lag7 = _autocorr_lag(imputed_matrix, lag=7)
    weekday_weekend_ratio = (
        _weekday_weekend_ratio(imputed_matrix, dates) if dates is not None else np.ones_like(mean_c)
    )
    missingness_trend = _missingness_trend(raw_matrix)
    longest_zero_streak = _longest_zero_streak(raw_matrix)

    low_mask = raw_matrix < (0.5 * mean_c[:, None])
    pct_days_below_half_mean = np.divide(
        np.nansum(low_mask, axis=1), valid_counts, out=np.zeros_like(mean_c), where=valid_counts > 0,
    )

    median_c = np.nanmedian(raw_matrix, axis=1, keepdims=True)
    mad_consumption = np.nanmedian(np.abs(raw_matrix - median_c), axis=1)

    features = pd.DataFrame({
        "mean_consumption": mean_c,
        "std_consumption": std_c,
        "coeff_variation": cv,
        "missing_ratio": missing_ratio,
        "zero_ratio": zero_ratio,
        "max_drop_pct": max_drop_pct,
        "max_spike_pct": max_spike_pct,
        "num_large_drops": num_large_drops,
        "trend_slope": trend_slope,
        "rolling7_volatility": rolling7_volatility,
        "skewness": np.nan_to_num(skewness),
        "kurtosis": np.nan_to_num(kurtosis),
        "min_to_mean_ratio": min_to_mean_ratio,
        "autocorr_lag7": autocorr_lag7,
        "weekday_weekend_ratio": weekday_weekend_ratio,
        "missingness_trend": missingness_trend,
        "longest_zero_streak": longest_zero_streak,
        "pct_days_below_half_mean": pct_days_below_half_mean,
        "mad_consumption": mad_consumption,
    })

    # Any residual inf/NaN (edge cases: e.g. a near-constant series) -> 0
    features = features.replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return features
