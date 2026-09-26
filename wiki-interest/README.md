# wiki-interest — Agent Skill

An [Agent Skill](https://agentskills.io/specification) that lets an AI agent
answer questions like *"Is interest in astronomy growing in Ukrainian
Wikipedia, and how much can we trust it?"* or *"Which language audiences
should our English-learning app research next?"* from
[Wikimedia pageview data](https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/reference/page-views.html),
with a chart and a one-page PDF report.

Built for founders of B2C products choosing topics and languages, and for
agents on small, cheap models (tested on Claude Haiku 4.5).

## Install & try

Requires [uv](https://docs.astral.sh/uv/) (it installs Python 3.11+ and the
pinned dependencies on first run) and internet access.

```bash
# make the skill available to Claude Code (project or ~/.claude/skills)
cp -r wiki-interest ~/.claude/skills/

# or run the CLI directly
uv run wiki-interest/scripts/wit.py doctor
uv run wiki-interest/scripts/wit.py run --topic "астрономія" --langs uk --out uk
uv run wiki-interest/scripts/wit.py report --study astronomy_Q333 --summary auto
```

Data and cache go to `~/.cache/wiki-interest` (override with
`WIKI_INTEREST_HOME`). Set `WIKI_INTEREST_CONTACT` to your e-mail/URL for the
User-Agent (Wikimedia policy).

## Principle: the code decides, the model retells

A small model is good at mapping a request to a command and retelling text,
and bad at statistics and at not inventing numbers. So everything that is a
*decision* lives in code:

```
request ──► agent ──► wit.py run ──► resolve topic (Wikidata, ambiguity → ask)
                                   ├► basket of related articles (morelike ∩ links, validated)
                                   ├► fetch daily views (SQLite cache, closed months forever)
                                   ├► per language: spikes → growth of share → direction
                                   │                seasonality → confidence → ranking
                                   └► compact JSON: verdicts, trust, must_mention, table,
                                      warnings (+ ready `next` commands), assumptions, limitations
agent ──► retells ready sentences ──► report --summary "…" ──► guard (numbers, claims) ──► PDF
```

| Task requirement | Where |
|---|---|
| Agent Skills format, `SKILL.md` + own code doing the data work | `SKILL.md`, `scripts/wikitrends/` (≈ 2.4k lines: API client, cache, statistics, charts, PDF, guard) |
| No binaries, reproducible env, everything in the skill dir | PEP 723 header in `scripts/wit.py` (+ `wit.py.lock`), `uv run`; fonts come from matplotlib |
| Charts + shareable one-page report | `charts.py` (PNG), `report.py` (A4 PDF, never silently truncated) |
| Evaluate results, verify conclusions | confidence rules, spikes/seasonality/level-shift/bot checks, basket agreement, guard on agent text |
| Repeated and related requests | studies with versions (`edit`, `list`, `show`), cache → follow-ups cost ~0 requests |
| Assumptions & limitations visible | every result carries `assumptions` + `limitations`; PDF prints them |
| Works on a cheap model | compact JSON, ready sentences, one command per request; evals on Haiku 4.5 (`evals/`) |
| How to grow further | [Roadmap](#roadmap) |
| How AI tools were used / verified | [DEVLOG.md](DEVLOG.md) |

## Commands

| Command | What it does |
|---|---|
| `run --topic T --langs uk,pl [--months 24] [--out uk]` | new study |
| `edit --study ID [--add-langs sk] [--months 36] [--basket-remove X] [--weights …] [--article pl:Title] [--out uk]` | follow-up, new version, cached data reused |
| `report --study ID --summary "…" [--title "…"]` | guard-checked one-page PDF (`--summary auto` = composed by code) |
| `resolve --topic T --langs …  [--basket]` | only find the Wikidata item / basket |
| `list`, `show ID` | previous studies, no network |
| `doctor` | dependencies, API access, User-Agent |

## Methodology (short)

- **Topic = basket of ~10 related articles** present in all compared languages
  (not one page); the basket is shown and editable.
- **Share of the edition's traffic** is the headline metric (Wikipedia traffic
  itself fell ~45% in uk since 2023); raw views are shown next to it.
- **Growth** = last 12 months vs the same months a year earlier on a
  spike-cleaned series; **consistency** = months above last year + exact
  binomial test; **direction** rising / declining / flat / unclear.
- **Confidence** = 10 points minus penalties (inconsistency, spike-driven,
  one-article growth, bots, late articles) with caps (volume, history, proxy).
- **Ranking** of languages with user-adjustable weights.

Details and every threshold: [references/METHODOLOGY.md](references/METHODOLOGY.md).

## How it was verified

| What | How |
|---|---|
| API behaviour | real requests, saved as fixtures ([API_NOTES](references/API_NOTES.md)) |
| Statistics | 36 tests (synthetic series with a known answer, guard, topic resolution on saved real responses, HTTP retries); binomial test == scipy for n ≤ 24; threshold calibration: false "rising" ≈ 2% |
| Data pipeline | our sums == API monthly endpoint for 3 articles in uk/cs/de (de differs exactly by the added redirects); cold cache 6 langs × 36 months: 125 requests, 26 s, no 429 |
| PDF | rendered and inspected (Cyrillic, 1 and 5 languages, long title) |
| Agent behaviour | `evals/run_evals.py`: Claude Code + Haiku 4.5, 10 cases incl. multi-turn follow-ups, 4 iterations; final 28/30, then 10/10 after `final_message` (~$0.05 and ~30 s per case); every failure read by hand ([RESULTS](evals/RESULTS.md)) |

```bash
cd wiki-interest
uv run --group dev pytest            # unit tests
uv run evals/run_evals.py --runs 3   # agent evals (needs `claude` CLI)
```

## Limitations

- Pageviews show interest, not willingness to pay; a language edition is not a country.
- The automatic basket is a heuristic (works well for astronomy/diets; for
  "learning English" it measures the English language as a subject) — the
  agent shows it and the user can edit it.
- Direction checks of the guard are keyword-based and only warn.
- Free text written by the model is the main risk: every place where Haiku was allowed to add its own sentence eventually produced an outside fact or "market" wording. Hence `report` returns a complete `final_message` (incl. the next step) that is sent as is.
- Full scenario verified on Haiku 4.5 and on a free OpenRouter model (Nemotron Ultra 550B, 3/3 incl. the Mercury question); a smaller free model (Nemotron Super) keeps the numbers right but breaks rules (picks "Mercury" itself) — see [evals/RESULTS.md](evals/RESULTS.md). One run per case on free models (daily limits).
- Wikipedia is one signal; results are a direction for validation, not a decision.
  See [references/LIMITATIONS.md](references/LIMITATIONS.md).

## Roadmap

How to take it from single questions to bigger research, in order of value:

1. **Topic screening, not just checking.** `wit.py scan --langs uk --category
   Q…`: rank all articles of a Wikidata class / WikiProject by growth. Needs
   bulk data → monthly **pageview dumps** instead of per-article API calls.
2. **Storage for scale.** SQLite → DuckDB/Parquet over dumps; parallel fetch
   with one shared rate limiter; output only top-N to the agent.
3. **Better baskets.** Wikidata graph (subclass/part-of), Wikimedia topic
   classification (ORES/LiftWing `articletopic`), user-saved baskets.
4. **Audience size.** Reader countries are already shown (`top-by-country`,
   hidden countries handled); next: weight languages by reachable population
   and offer a "by country" view built from these shares.
5. **External signals** — Google Trends, app-store search, audience size →
   an explicit opportunity score with the same "code decides" contract.
6. **Monitoring** — `wit.py monitor` on cron / GitHub Actions, alerts when a
   saved study changes direction; no LLM needed.
7. **Backend + MCP.** Move data and heavy compute to a service; the skill
   becomes a thin client, the same tools are exposed over MCP.
8. **Ranking without weights** as an option: a Pareto front (trust × growth) for users who do not want to set priorities; weights stay the default because they give a single order.
9. **Evals in CI** on every change of `SKILL.md` or thresholds; threshold
   calibration on thousands of synthetic series (false "rising" rate).
