"""Chart: index of the topic's share of views (first 12 months = 100), one
line per language; news spikes as points; seasonal peaks shaded (1 language)."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

COLORS = ["#2a6fdb", "#e0663d", "#2e9e6b", "#8a5cd1", "#c9a227", "#d14d8a"]
TXT = {
    "uk": {"title": "Інтерес до «{t}»: частка переглядів, індекс (перші 12 міс. = 100)", "y": "індекс частки", "news": "новинний спайк",
           "window": "період аналізу", "more": "показано топ-6 з {n} мов"},
    "en": {"title": "Interest in “{t}”: share of views, index (first 12 months = 100)", "y": "share index", "news": "news spike",
           "window": "analysis period", "more": "top 6 of {n} languages shown"},
}


def plot(results: dict, fetch_months: list[str], analysis_months: list[str], topic: str, path, out: str,
         ranking: list[dict] | None = None) -> None:
    t = TXT[out]
    order = [r["key"] for r in ranking] if ranking else list(results)
    shown = order[:6]
    x = np.arange(len(fetch_months))
    fig, ax = plt.subplots(figsize=(8.2, 3.3), dpi=160)
    for i, lang in enumerate(shown):
        s = np.array(results[lang]["series"]["share_clean"], dtype=float)
        raw = np.array(results[lang]["series"]["share_raw"], dtype=float)
        base = s[:12].mean() if s[:12].mean() > 0 else (s[s > 0].mean() if (s > 0).any() else 1)
        c = COLORS[i % len(COLORS)]
        ax.plot(x, s / base * 100, color=c, lw=2, label=lang)
        ax.plot(x, raw / base * 100, color=c, lw=0.8, alpha=0.35)
        ev_months = {e["date"][:7] for e in results[lang].get("news_events", [])}
        pts = [fetch_months.index(m) for m in ev_months if m in fetch_months]
        if pts:
            ax.scatter(pts, (raw / base * 100)[pts], color=c, s=18, zorder=3,
                       label=t["news"] if i == 0 else None, edgecolors="white", linewidths=0.6)
    if len(shown) == 1:
        season = results[shown[0]].get("season") or {}
        for j, m in enumerate(fetch_months):
            if int(m[5:7]) in season.get("peaks", []):
                ax.axvspan(j - 0.5, j + 0.5, color="#c9a227", alpha=0.12, lw=0)
    a0 = fetch_months.index(analysis_months[0])
    ax.axvspan(a0 - 0.5, len(fetch_months) - 0.5, color="#888", alpha=0.06, lw=0, label=t["window"])
    ax.axhline(100, color="#999", lw=0.6, ls="--")
    step = max(1, len(fetch_months) // 9)
    ax.set_xticks(x[::step])
    ax.set_xticklabels(fetch_months[::step], fontsize=7)
    ax.tick_params(axis="y", labelsize=7)
    ax.set_ylabel(t["y"], fontsize=8)
    ax.set_title(t["title"].format(t=topic), fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(fontsize=7, ncol=min(4, len(shown) + 2), frameon=False, loc="upper left")
    if len(order) > 6:
        ax.text(1, -0.18, t["more"].format(n=len(order)), transform=ax.transAxes, ha="right", fontsize=7, color="#666")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
