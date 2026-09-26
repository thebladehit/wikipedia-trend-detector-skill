# Methodology (v1.0)

All thresholds live in `RULES` (`scripts/wikitrends/config.py`) and are copied
into every `analysis.json`, so each result can be reproduced and audited.

## 1. What is measured

- **Topic → Wikidata item.** Search in the query language, the target languages
  and English. Items without any Wikipedia article (papers, Wikidata
  properties) and disambiguation/list items are dropped. The leader by number of
  language editions is picked automatically only if it has ≥ 3× the editions of
  the next candidate (astronomy: 253 vs 2); otherwise the tool asks
  (Mercury: planet 251 vs element 176).
- **Basket of articles, not one page.** Interest in a topic is spread over many
  pages. Candidates: `morelike:` for the main article (English Wikipedia when it
  has the article, otherwise the largest compared edition) ∩ the main article's
  outgoing links. Validated through Wikidata: no disambiguation pages, lists,
  years, papers, no people unless the topic is a person. Only articles present
  in all compared languages are kept (fallback: ≥ 50% of them, with a warning),
  so languages are compared on the same set of concepts. Candidates keep
  relevance order; words shared with the topic title raise priority; generic
  hubs with > 3× the main article's views are dropped (e.g. *COVID-19* for a
  diet topic). Default size 10 including the main article.
- **Redirects.** Up to 5 redirects of the main article are added to it
  (Pageviews counts redirect titles separately).
- **Human views only** (`agent=user`), all access methods, daily granularity.
- **Normalisation.** `share_ppm = views / all human views of the edition × 10⁶`.
  Wikipedia traffic changes a lot by itself (uk.wikipedia: 91.6 M → 50.7 M views
  per month, 2023-01 → 2026-08), so raw growth mixes interest in the topic with
  the edition's traffic trend. The headline is the **share**; raw views and the
  edition's own change are reported next to it.

## 2. Period

- Only complete months; the current month is always excluded.
- Download = analysis period + at least 12 months before it (and ≥ 36 months in
  total) for year-over-year comparison and seasonality. Data starts 2015-07;
  earlier requests are clipped and recorded in `assumptions`.

## 3. Spikes (daily, per article)

Hampel filter: `m` = centred 31-day rolling median, `MAD` = rolling median of
`|x − m|`. A day is a spike if `x > m + 5 × 1.4826 × MAD` **and** `x > m + 20`
(with MAD = 0 only the absolute rule applies — low-traffic pages).

- Spikes in the same calendar month in ≥ 2 years are **seasonality** and kept.
- Other spike days are replaced by `m` → the *cleaned* series.
- Spikes on ≥ 2 basket articles within ±1 day → *news event*.
- `spike_share` = share of the raw YoY increase that came from spike days.

## 4. Growth and direction

For period `P = min(12, analysis months)`:

- `growth = Σ share(last P months) / Σ share(same months a year earlier) − 1`
  on the cleaned series (raw-share and raw-views versions are reported too).
- `k` = months of the last `P` that are above the same month a year earlier;
  exact two-sided binomial test `p(k, P, 0.5)` (cross-checked against
  `scipy.stats.binomtest` for all n ≤ 24). For P = 12: p < 0.05 ⇔ k ≥ 10 or k ≤ 2.

| Direction | Rule |
|---|---|
| `flat` | \|growth\| ≤ 10% |
| `rising` | growth > +10% and p < 0.05 and k > P/2 |
| `declining` | growth < −10% and p < 0.05 and k < P/2 |
| `unclear` | everything else (a change, but inconsistent month to month) |

Comparing the same months removes seasonality from `growth` and `k`.

**Calibration** (`tests/calibrate.py`, 2000 synthetic 36-month series per cell,
±15% monthly log-normal noise, seasonality, random news spikes):

| true growth | rising | flat | unclear | declining |
|---|---|---|---|---|
| 0% | 2% | 77% | 20% | 1% |
| +10% | 21% | 39% | 40% | 0% |
| +20% | 58% | 6% | 36% | 0% |
| +30% | 88% | 0% | 12% | 0% |
| −20% | 0% | 15% | 24% | 61% |

(1000–10000 views/month; at 100 views/month detection is ~10–20 pp lower.)
The rule is deliberately conservative: it rarely claims growth that is not
there, and moderate real growth often lands in `unclear` rather than a wrong
direction.

## 5. Seasonality, trend, level shifts

- **Seasonality:** ratio to a centred 12-month mean, averaged per calendar
  month. Peak: index ≥ 1.2 and ratio ≥ 1.1 in ≥ 2 different years.
  Low: index ≤ 1/1.2 and ratio ≤ 0.9 in ≥ 2 years.
- **Trend (informational):** Theil–Sen slope of log(deseasonalised share) over
  ≥ 36 months → annual %.
- **Level shift:** largest step between 6-month windows on the
  *deseasonalised* series (only when seasonality was detected), scored by
  `min(|log median ratio|, |log mean ratio|)` so that a spike (moves only the
  mean) and a summer drop (removed by deseasonalising) are not flagged.
  Ratio ≥ 1.6 or ≤ 0.6 → warning (possible rename, merge, tracking change).
  *Found on real data:* before deseasonalising, the Ukrainian school-year
  pattern (June–August at half level) was reported as a technical break.
- Seasonality is not reported when the median basket volume is < 300
  views/month (it is noise at that level).
- **Readers of an edition:** `top-by-country` for the last month, top 3.
  Wikimedia hides countries on its privacy protection list (rank 1 is missing
  for tr, vi, ru); then only country names are shown, without shares.

## 6. Confidence

Start at 10; penalties, then caps. 8–10 high, 5–7 medium, < 5 low.

| Rule | Effect |
|---|---|
| Median basket views < 100 / month | cap **low** |
| Median basket views < 300 / month | cap **medium** |
| < 24 months of history | cap **low** |
| Proxy article (different Wikidata item) | cap **medium** |
| Binomial p ≥ 0.05 (inconsistent) | −3 |
| Spikes gave > 30% of the raw increase | −2 |
| Basket total grows, median article does not | −2 |
| < 50% of articles move in the topic's direction | −1 |
| Possible bots: main article desktop share > edition's + 30 pp, or spike days ≥ 90% desktop | −2 |
| An article that is ≥ 5% of the basket appeared during the period | −1 |

The label shows the cap explicitly: `medium (9/10, capped: small volume …)`.

## 7. Ranking (≥ 2 languages)

`score = w_g·norm(growth) + w_s·norm(log share_ppm) + w_st·norm(1/(1+CV)) − penalty`
where CV is the coefficient of variation of the deseasonalised monthly share in
the analysis window (stability = predictable demand; month-over-year
consistency is already part of confidence — an earlier version used k/P here
and ranked an inconsistent decline as "most stable"), `norm` is min-max across
the compared languages, penalty 0.15 for low and
0.05 for medium confidence. Default weights 0.4 / 0.3 / 0.3, changeable with
`--weights`; always written to `assumptions`. Scores are relative: adding a
language can change the others' scores.

Why weights and why these ones: the task says users bring their own criteria of
"promising", so the ranking is a *default*, not a truth. 0.4 / 0.3 / 0.3 means
"growth matters most, size and predictability equally" — a founder's usual
first question. They are not fitted to data (there is no ground truth of
"right" language to fit to). Safeguards: the weights are always printed in
`assumptions`; `ranking.why` names the factor that decided each place; the
user changes them in words ("stability matters more") → `--weights`, and a
follow-up re-ranks from cache. Alternative considered: a Pareto front (no
weights) — honest but often returns "all languages are incomparable", which
does not answer "where to launch first"; listed in the roadmap as an option.

## 8. Guard for agent text

`report --summary` rejects a summary with numbers that do not appear in the
analysis (tolerance: 1 pp for %, 2% otherwise) or with claims of willingness to
pay / market demand. Direction contradictions and "market/country" wording are
warnings only (keyword matching in free text is brittle). After a second
rejection the agent uses `--summary auto` (composed by code from verdicts).
