import math

from synth import ANALYSIS, FETCH, article, daily, project
from wikitrends.analyze import analyze_language


def run(arts, proj=None):
    return analyze_language("xx", FETCH, ANALYSIS, arts, proj or project())


def test_flat_with_one_spike_is_flat():
    d = daily(lambda i, m: 500, spikes={"2026-03-10": 40000})
    r = run([article("A", d, main=True)])
    assert r["direction"] == "flat"
    assert r["growth_raw_share"] > 0.1  # the spike inflates raw growth...
    assert abs(r["growth_clean"]) <= 0.1  # ...but not the cleaned one


def test_seasonal_without_growth_is_flat():
    d = daily(lambda i, m: 800 if m[5:] in ("09", "10") else 300)
    r = run([article("A", d, main=True)])
    assert r["direction"] == "flat"
    assert set(r["season"]["peaks"]) >= {9, 10}


def test_steady_growth_30pct_is_rising_high():
    d = daily(lambda i, m: 400 * 1.3 ** (i / 12))
    r = run([article("A", d, main=True)])
    assert r["direction"] == "rising"
    assert 0.2 < r["growth_clean"] < 0.4
    assert r["confidence"]["level"] == "high"


def test_growth_measured_as_share_of_project_traffic():
    # article flat in absolute views, project traffic halves -> share rises
    d = daily(lambda i, m: 400)
    proj = {m: int(1_000_000 * (0.5 if i >= 24 else 1.0)) * 30 for i, m in enumerate(FETCH)}
    r = run([article("A", d, main=True)], proj)
    assert abs(r["growth_views"]) < 0.1
    assert r["growth_clean"] > 0.5
    assert r["project_growth"] < -0.4


def test_one_article_drives_basket_growth_lowers_confidence():
    arts = [article("Main", daily(lambda i, m: 3000 * 1.8 ** (i / 12), seed=1), main=True)]
    arts += [article(f"B{j}", daily(lambda i, m: 300 * 0.9 ** (i / 12), seed=j + 2)) for j in range(5)]
    r = run(arts)
    assert r["growth_clean"] > 0.1
    assert r["median_article_growth"] < 0
    assert r["divergence"]
    assert r["confidence"]["level"] != "high"
    assert any("median article" in x for x in r["confidence"]["reasons"])


def test_tiny_volume_capped_low():
    d = daily(lambda i, m: 55 / 30 * 1.3 ** (i / 12))
    r = run([article("A", d, main=True)])
    assert r["median_monthly_views"] < 100
    assert r["confidence"]["level"] == "low"
    assert r["confidence"]["capped_by"]


def test_article_created_mid_period_flags_late_start():
    d = daily(lambda i, m: 0 if i < 10 else 500)
    r = run([article("A", d, main=True)])
    assert r["late_start"]


def test_news_spike_on_two_articles():
    s = {"2025-11-05": 20000}
    arts = [article("A", daily(lambda i, m: 500, seed=1, spikes=s), main=True),
            article("B", daily(lambda i, m: 400, seed=2, spikes={"2025-11-06": 9000}))]
    r = run(arts)
    assert r["news_events"] and r["news_events"][0]["date"] in ("2025-11-05", "2025-11-06")


def test_school_year_seasonality_is_not_a_level_shift():
    # real pattern of uk astronomy: summer at half level, September peak, no trend
    lvl = {"06": 0.45, "07": 0.4, "08": 0.45, "09": 1.5}
    d = daily(lambda i, m: 400 * lvl.get(m[5:], 1.0))
    r = run([article("A", d, main=True)])
    assert r["level_shift"] is None
    assert set(r["season"]["troughs"]) >= {6, 7, 8}
    assert r["direction"] == "flat"


def test_real_level_shift_is_detected():
    d = daily(lambda i, m: 400 if i < 26 else 1200)
    r = run([article("A", d, main=True)])
    assert r["level_shift"] and r["level_shift"]["month"] == "2025-11"


def test_stability_prefers_steady_demand():
    from wikitrends.rank import rank
    steady = run([article("A", daily(lambda i, m: 500, seed=3), main=True)])
    import numpy as np
    shocks = np.random.default_rng(7).lognormal(0, 0.5, 36)  # irregular, not calendar-bound
    jumpy = run([article("A", daily(lambda i, m: 500 * shocks[i], seed=4), main=True)])
    assert steady["stability"] > jumpy["stability"]
    items = [{"key": k, "growth_clean": 0.0, "share_ppm": 1.0, "k": 6, "n": 12, "stability": r["stability"],
              "confidence": "high"} for k, r in (("steady", steady), ("jumpy", jumpy))]
    ranked = rank(items, {"growth": 0.0, "size": 0.0, "stability": 1.0})
    assert ranked[0]["key"] == "steady"
