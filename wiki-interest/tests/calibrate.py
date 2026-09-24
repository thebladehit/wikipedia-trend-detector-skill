"""Threshold calibration on synthetic series (not a unit test; run manually).

  uv run python tests/calibrate.py

Monthly series with realistic noise: multiplicative log-normal month noise,
optional seasonality, occasional spikes, Poisson counts. Reports how often the
direction rule says `rising` when there is no growth (false alarm) and how
often it finds true growth, for several traffic levels."""
import sys

import numpy as np

sys.path.insert(0, "scripts")
from wikitrends import stats  # noqa: E402


def series(rng, level, growth, noise=0.15, season=0.3):
    t = np.arange(36)
    trend = (1 + growth) ** (t / 12)
    seas = 1 + season * np.sin(2 * np.pi * (t % 12) / 12 + rng.uniform(0, 2 * np.pi))
    shock = rng.lognormal(0, noise, 36)
    lam = level * trend * seas * shock
    x = rng.poisson(lam).astype(float)
    if rng.random() < 0.3:  # a month with a news spike
        x[rng.integers(24, 36)] *= rng.uniform(1.5, 3)
    return x


def run(level, growth, n=2000, seed=0):
    rng = np.random.default_rng(seed)
    c = {"rising": 0, "declining": 0, "flat": 0, "unclear": 0}
    for _ in range(n):
        y = stats.yoy(series(rng, level, growth), 12)
        c[stats.direction(y["growth"], y["k"], y["n"], y["p"])] += 1
    return {k: v / n for k, v in c.items()}


print(f"{'views/month':>11} {'true growth':>11} | rising  flat  unclear declining")
for level in (100, 1000, 10000):
    for g in (0.0, 0.1, 0.2, 0.3, -0.2):
        r = run(level, g)
        print(f"{level:>11} {g:>+11.0%} | {r['rising']:6.1%} {r['flat']:5.1%} {r['unclear']:7.1%} {r['declining']:8.1%}")
