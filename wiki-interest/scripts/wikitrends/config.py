"""Paths, constants and all analysis thresholds (RULES) in one place.

RULES is copied into every analysis.json so each result is reproducible and
the thresholds are visible to whoever reads the report.
"""
from __future__ import annotations

import os
import pathlib

METHODOLOGY_VERSION = "1.0"
TOOL_VERSION = "0.1.0"

SKILL_DIR = pathlib.Path(__file__).resolve().parents[2]


def home() -> pathlib.Path:
    """Where cache and studies live. Outside the skill dir on purpose:
    an installed skill may be read-only or shared between projects."""
    p = os.environ.get("WIKI_INTEREST_HOME")
    base = pathlib.Path(p).expanduser() if p else pathlib.Path.home() / ".cache" / "wiki-interest"
    base.mkdir(parents=True, exist_ok=True)
    return base


def runs_dir() -> pathlib.Path:
    d = home() / "runs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def user_agent() -> str:
    contact = os.environ.get("WIKI_INTEREST_CONTACT", "https://github.com/thebladehit/wikipedia-trend-detector-skill")
    return f"wiki-interest/{TOOL_VERSION} ({contact}) python-urllib"


PAGEVIEWS_START = "2015-07"  # first month with pageviews data

RULES = {
    # spikes (Hampel filter on daily views)
    "spike_window_days": 31,
    "spike_mad_k": 5.0,
    "spike_min_abs": 20,
    "spike_seasonal_min_years": 2,
    # direction
    "flat_band": 0.10,  # |growth| <= 10% -> flat
    "binom_alpha": 0.05,  # k of 12 months above last year; p<0.05 <=> k>=10
    # seasonality
    "season_peak_index": 1.2,
    "season_min_years": 2,
    # confidence
    "conf_start": 10,
    "conf_high_min": 8,
    "conf_medium_min": 5,
    "vol_low_cap": 100,  # median monthly views (raw, basket) below -> cap low
    "vol_medium_cap": 300,  # below -> cap medium
    "history_min_months": 24,
    "pen_not_significant": 3,
    "pen_spike_driven": 2,
    "spike_driven_share": 0.30,
    "pen_divergence": 2,
    "pen_low_breadth": 1,
    "low_breadth": 0.5,
    "pen_bot": 2,
    "bot_desktop_pp": 0.30,
    "bot_spike_desktop": 0.90,
    "pen_late_start": 1,
    # ranking
    "weights": {"growth": 0.4, "size": 0.3, "stability": 0.3},
    "rank_pen_low": 0.15,
    "rank_pen_medium": 0.05,
    # topic resolution
    "resolve_dominance": 3.0,
    # basket
    "basket_size": 10,
    "basket_candidates": 50,
    "basket_min_intersection": 5,
    "basket_min_common": 5,
    "basket_hub_ratio": 3.0,  # drop related articles with > 3x the main article's views
    "redirects_per_main": 5,
}
