import numpy as np

from wikitrends import stats


def test_binomial_matches_scipy_reference_values():
    # scipy.stats.binomtest(k, 12).pvalue reference values
    assert abs(stats.binom_two_sided(9, 12) - 0.14599609375) < 1e-9
    assert abs(stats.binom_two_sided(10, 12) - 0.0385742187) < 1e-9
    assert stats.binom_two_sided(6, 12) == 1.0
    assert abs(stats.binom_two_sided(0, 12) - 0.00048828125) < 1e-9


def test_rising_needs_10_of_12():
    assert stats.direction(0.2, 10, 12, stats.binom_two_sided(10, 12)) == "rising"
    assert stats.direction(0.2, 9, 12, stats.binom_two_sided(9, 12)) == "unclear"
    assert stats.direction(-0.3, 1, 12, stats.binom_two_sided(1, 12)) == "declining"
    assert stats.direction(0.05, 12, 12, 0.0005) == "flat"


def test_hampel_finds_single_spike_and_not_noise():
    rng = np.random.default_rng(1)
    x = rng.poisson(200, 200).astype(float)
    x[100] += 3000
    mask, _ = stats.hampel(x)
    assert mask[100]
    assert mask.sum() <= 2


def test_hampel_low_traffic_uses_absolute_threshold():
    x = np.zeros(100)
    x[50] = 15  # below +20 absolute threshold
    x[70] = 40
    mask, _ = stats.hampel(x)
    assert not mask[50] and mask[70]


def test_seasonal_spikes_are_kept():
    dates = [f"{y}-04-10" for y in (2024, 2025)] + ["2025-06-01"]
    mask = np.array([True, True, True])
    assert stats.seasonal_spike_months(dates, mask) == {4}


def test_yoy_growth_and_k():
    s = np.array([100] * 12 + [130] * 12, dtype=float)
    r = stats.yoy(s, 12)
    assert abs(r["growth"] - 0.3) < 1e-9 and r["k"] == 12


def test_seasonality_detects_repeating_peak():
    months = [f"{y}-{m:02d}" for y in (2023, 2024, 2025) for m in range(1, 13)]
    s = np.array([200.0 if m.endswith("-10") else 100.0 for m in months])
    season = stats.seasonality(months, s)
    assert season["peaks"] == [10]


def test_theil_sen_recovers_trend_despite_seasonality():
    months = [f"{y}-{m:02d}" for y in (2023, 2024, 2025, 2026) for m in range(1, 13)]
    s = np.array([100 * 1.3 ** (i / 12) * (1.5 if m.endswith("-10") else 1.0) for i, m in enumerate(months)])
    season = stats.seasonality(months, s)
    t = stats.theil_sen_annual(months, s, season)
    assert abs(t - 0.3) < 0.03


def test_level_shift():
    s = np.array([100.0] * 12 + [250.0] * 12)
    ls = stats.level_shift(s)
    assert ls["at"] == 12 and abs(ls["ratio"] - 2.5) < 1e-9
