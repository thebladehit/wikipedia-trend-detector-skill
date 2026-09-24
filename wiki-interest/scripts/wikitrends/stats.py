"""Pure statistics on numpy arrays. No I/O — everything here is unit-tested
on synthetic series with a known answer (tests/test_stats.py)."""
from __future__ import annotations

import math

import numpy as np

from .config import RULES


# ---------- spikes ----------

def rolling_median(x: np.ndarray, window: int) -> np.ndarray:
    half = window // 2
    padded = np.pad(x.astype(float), half, mode="constant", constant_values=np.nan)
    view = np.lib.stride_tricks.sliding_window_view(padded, window)
    return np.nanmedian(view, axis=1)


def hampel(x: np.ndarray, window: int | None = None, k: float | None = None, min_abs: float | None = None):
    """Return (spike_mask, rolling_median). Spike: x > m + k*1.4826*MAD and x > m + min_abs.
    With MAD == 0 (low traffic) only the absolute threshold applies."""
    window = window or RULES["spike_window_days"]
    k = RULES["spike_mad_k"] if k is None else k
    min_abs = RULES["spike_min_abs"] if min_abs is None else min_abs
    m = rolling_median(x, window)
    mad = rolling_median(np.abs(x - m), window)
    thr = np.where(mad > 0, m + k * 1.4826 * mad, m)
    mask = (x > thr) & (x > m + min_abs)
    return mask, m


def seasonal_spike_months(dates: list[str], mask: np.ndarray, min_years: int | None = None) -> set[int]:
    """Calendar months (1..12) where spikes happen in >= min_years different years:
    that is seasonality (e.g. exam season), not noise — keep it."""
    min_years = min_years or RULES["spike_seasonal_min_years"]
    years_by_month: dict[int, set[int]] = {}
    for d, s in zip(dates, mask):
        if s:
            years_by_month.setdefault(int(d[5:7]), set()).add(int(d[:4]))
    return {m for m, ys in years_by_month.items() if len(ys) >= min_years}


def clean_spikes(dates: list[str], x: np.ndarray):
    """Return (cleaned series, spike_mask of removed days, seasonal months kept)."""
    mask, m = hampel(x)
    seasonal = seasonal_spike_months(dates, mask)
    if seasonal:
        keep = np.array([int(d[5:7]) in seasonal for d in dates])
        mask = mask & ~keep
    cleaned = np.where(mask, m, x)
    return cleaned, mask, seasonal


# ---------- growth & direction ----------

def binom_two_sided(k: int, n: int, p: float = 0.5) -> float:
    """Exact two-sided binomial test (same definition as scipy.stats.binomtest)."""
    if n == 0:
        return 1.0
    probs = [math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(n + 1)]
    pk = probs[k]
    return min(1.0, sum(q for q in probs if q <= pk * (1 + 1e-7)))


def yoy(series: np.ndarray, period: int) -> dict:
    """Compare the last `period` months with the same months one year earlier.
    series: monthly values, oldest first; needs len >= period + 12."""
    if len(series) < period + 12 or period < 1:
        return {"growth": None, "k": None, "n": 0, "p": None}
    last = series[-period:]
    prev = series[-period - 12:-12]
    s_prev = float(np.sum(prev))
    growth = float(np.sum(last)) / s_prev - 1 if s_prev > 0 else None
    k = int(np.sum(last > prev))
    return {"growth": growth, "k": k, "n": period, "p": binom_two_sided(k, period)}


def direction(growth: float | None, k: int | None, n: int, p: float | None) -> str:
    if growth is None:
        return "unclear"
    band = RULES["flat_band"]
    if abs(growth) <= band:
        return "flat"
    sig = p is not None and p < RULES["binom_alpha"]
    if growth > band and sig and k > n / 2:
        return "rising"
    if growth < -band and sig and k < n / 2:
        return "declining"
    return "unclear"


def spike_share_of_growth(raw: np.ndarray, clean: np.ndarray, period: int) -> float:
    """Share of the raw year-over-year increase that came from spike days."""
    if len(raw) < period + 12:
        return 0.0
    dr = float(np.sum(raw[-period:]) - np.sum(raw[-period - 12:-12]))
    dc = float(np.sum(clean[-period:]) - np.sum(clean[-period - 12:-12]))
    if dr <= 0:
        return 0.0
    return float(min(1.0, max(0.0, (dr - dc) / dr)))


# ---------- seasonality & trend ----------

def seasonality(months: list[str], series: np.ndarray) -> dict | None:
    """Classical ratio-to-moving-average: value / centred 12-month mean.
    index[month] = mean ratio. Peak month: index >= season_peak_index and the
    ratio is >= 1.1 in >= season_min_years different years (it repeats)."""
    if len(series) < 24:
        return None
    ratios: dict[int, list[float]] = {i: [] for i in range(1, 13)}
    for i in range(6, len(series) - 5):
        mean = float(np.mean(series[i - 6:i + 6]))
        if mean > 0:
            ratios[int(months[i][5:7])].append(float(series[i]) / mean)
    if any(not r for r in ratios.values()):
        return None
    index = {mo: float(np.mean(r)) for mo, r in ratios.items()}
    peaks = [mo for mo, r in ratios.items()
             if index[mo] >= RULES["season_peak_index"] and sum(x >= 1.1 for x in r) >= RULES["season_min_years"]]
    troughs = [mo for mo, r in ratios.items()
               if index[mo] <= 1 / RULES["season_peak_index"] and sum(x <= 0.9 for x in r) >= RULES["season_min_years"]]
    return {"index": index, "peaks": sorted(peaks), "troughs": sorted(troughs),
            "amplitude": float(max(index.values()) / max(min(index.values()), 1e-9))}


def theil_sen_annual(months: list[str], series: np.ndarray, season: dict | None) -> float | None:
    """Robust trend of log(deseasonalised series); annual % change. Needs >= 36 months."""
    if len(series) < 36 or np.any(series <= 0):
        return None
    idx = season["index"] if season else {i: 1.0 for i in range(1, 13)}
    y = np.log(np.array([v / max(idx[int(m[5:7])], 1e-9) for m, v in zip(months, series)]))
    t = np.arange(len(y))
    i, j = np.triu_indices(len(y), k=1)
    slope = float(np.median((y[j] - y[i]) / (t[j] - t[i])))
    return math.exp(12 * slope) - 1


def level_shift(series: np.ndarray, window: int = 6) -> dict | None:
    """Largest step between medians of `window` months before/after a point.
    A step without spikes or seasonality often has a technical cause
    (renamed article, tracking change, app/search integration)."""
    if len(series) < 2 * window + 1:
        return None
    best = None
    for i in range(window, len(series) - window + 1):
        before = float(np.median(series[i - window:i]))
        after = float(np.median(series[i:i + window]))
        if before <= 0:
            continue
        ratio = after / before
        m_before, m_after = float(np.mean(series[i - window:i])), float(np.mean(series[i:i + window]))
        if ratio <= 0 or m_before <= 0 or m_after <= 0:
            continue
        # both the median ratio (robust to spikes) and the mean ratio (sharpest
        # exactly at the step) must be large; a spike moves only the mean
        score = min(abs(math.log(ratio)), abs(math.log(m_after / m_before)))
        if best is None or score > best["score"]:
            best = {"at": i, "ratio": ratio, "score": score}
    return best


def median_growth(per_article: list[float | None]) -> tuple[float | None, float | None]:
    """(median growth over articles, breadth = share of articles growing)."""
    vals = [g for g in per_article if g is not None]
    if not vals:
        return None, None
    return float(np.median(vals)), float(np.mean([g > 0 for g in vals]))
