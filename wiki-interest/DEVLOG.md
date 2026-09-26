# DEVLOG — decisions and how each was verified

Development was done with Claude Code (Opus) as the main coding agent; the
skill itself was tested with Claude Code on **Haiku 4.5**. The rule was: *every
claim about external behaviour is verified by a real request, every piece of
statistics by a test with a known answer, every agent behaviour by reading
transcripts by hand.*

## Phase 0 — API walk-through (real requests, 2026-09-24)

Raw responses saved to `tests/fixtures/`, findings in `references/API_NOTES.md`.
Findings that changed the plan:

| Finding | Plan before | Change |
|---|---|---|
| `астрономія` has 3 exact matches (science, Hogwarts class, Wikidata property) | ≥ 2 exact matches → ask the user | pick the leader when it has ≥ 3× more language editions (253 vs 2); Mercury (251 vs 176) still asks |
| Search returns scholarly papers (0 wiki articles) | — | drop items without Wikipedia articles |
| `intermittent fasting` has **no plwiki** article | — | became the `missing_article` scenario from the task |
| `morelike:English language` returns unrelated languages | morelike top-N by views | morelike ∩ main article links |
| API omits zero-view days | — | missing day = 0; cache stores *fetched months*, not only rows |
| Current month returned up to yesterday | — | explicit "last complete month" |
| `prop=pageviews` gives 60-day views for 50 titles in 1 request | 1 REST call per candidate | used for basket ranking |
| uk.wikipedia traffic −45% since 2023 | — | growth is reported as share and raw, both visible |

## Phase 1–4 — code + synthetic tests

- `binom_two_sided` checked against `scipy.stats.binomtest` for all k, n ≤ 24
  (0 mismatches) → scipy dropped from dependencies.
- 19 unit tests on synthetic series with a known answer: flat + spike → flat,
  seasonal without growth → flat, +30%/yr → rising/high, traffic halves → share
  rises while views flat, one article drives the basket → confidence lowered,
  55 views/month → capped low, late article flagged, news spike on two articles,
  school-year seasonality is not a level shift, a real step is found at the
  right month.
- Monthly sums cross-checked with the API's own `monthly` endpoint
  (*Галактика*, uk, 12 months: 8988 = 8988).
- Plan inconsistency found while testing: the plan's scenario said
  "9 of 12 months → rising", but binomial p(9,12) = 0.146; rising needs ≥ 10.

## Independent checks

| Check | Result |
|---|---|
| Our 12-month sums vs the API's own `monthly` endpoint (different code path) | uk *Галактика* 8988 = 8988; cs *Přerušovaný půst* 2198 = 2198; de *Schach* 170 880 vs 169 672 — the difference is exactly the 5 redirects added to the main article (1208 views) |
| Cold cache, 6 languages × 36 months (`chess`) | 125 requests, 26 s, no 429; follow-up `edit --add-langs uk` → 22 new requests, 7 s |
| Threshold calibration, 2000 synthetic series per cell (`tests/calibrate.py`) | false "rising" with no growth ≈ 2%; true +30%/yr found 87%, +20% 58%, rest "unclear" — never the opposite direction |
| PDFs rendered and inspected | 1 language, 2 languages with a missing one, 5 languages, long Ukrainian title; all one page |

## Bugs found on real data (not caught by the first tests)

| # | Symptom (real run) | Cause | Fix + test |
|---|---|---|---|
| 1 | Astronomy uk: "sharp level shift 2025-05 ×0.5, possibly technical" | Ukrainian school-year pattern (summer at half level) looked like a step | search shifts on the deseasonalised series; `test_school_year_seasonality_is_not_a_level_shift` |
| 2 | Shift detected 1–2 months off | ties between median windows + noise | score = min(\|log median ratio\|, \|log mean ratio\|); `test_real_level_shift_is_detected` |
| 3 | Fasting basket: COVID-19, sugar, alcohol, allergy | candidates sorted by views → generic hubs win | keep relevance order; drop hubs with > 3× the main article's views |
| 4 | English basket: Swedish, Finnish, Icelandic… | discovery in pl.wikipedia (`morelike` = "languages") | discover in en.wikipedia when available + prefer candidates sharing a distinctive word with the topic |
| 5 | Declining topic penalised for "only 10% of articles grow" | breadth counted growth, not agreement with the topic | `agreement` = share of articles moving in the topic's direction |
| 6 | `next` JSON broken for Mercury | absolute path with quotes inserted after `json.dumps` | substitute before serialising |
| 7 | Ukrainian question, English PDF body | `--out` guessed from the topic text | SKILL.md: always pass `--out`; `report` warns and suggests `edit --out` |
| 8 | "Portuguese Wikipedia is read mostly in Brazil" written from memory | — | verified: top-by-country 2026-08: BR 74%, PT 9% |
| 9 | Readers of tr/vi Wikipedia: "US 31%, DE 15%" / "US 47%" | rank-1 country hidden by Wikimedia privacy list (checked: rank 1 absent for tr, vi, ru) | shares shown only when top-3 ranks are complete, otherwise names + "top country hidden" |
| 10 | Niche topic (98 views/month): "seasonal low in 5 months" | seasonality on noise | seasonality not reported below `vol_medium_cap` |

## Agent iterations (Haiku 4.5)

See `evals/RESULTS.md` for the numbers. Each iteration: run → read transcripts
by hand → fix in code first, then SKILL.md → rerun.

### Iteration 0 → 1
- **Before:** astronomy case passed automatic checks, but the answer listed
  invented causes ("YouTube, AI answers… seasonal decline that will pass") and
  paraphrased confidence reasons into nonsense ("немає монетизації даних").
- **Fix (code):** a ready `trust` sentence per language; the seasonality clause
  now states that YoY compares the same months so seasonality does not affect
  it. **Fix (SKILL.md):** rule 6 forbids listing possible causes.

### Iteration 1 (10 cases × 1 run): 8/10 automatic pass
Read every transcript by hand:
- `astronomy-uk-trust` FAIL was an **eval bug**: "це не значить, що люди готові
  платити" (correct negation) matched `must_not_include`. Eval made
  negation-aware (same rule as guard).
- `niche-topic` FAIL: Haiku broadened the user's topic to "гравітаційні хвилі",
  got `needs_input` and asked. Safe, but the topic was changed. → SKILL.md:
  topic exactly in the user's words. Direct run of the original wording works
  (low confidence 2/10 with reasons).
- `fasting-pl-cs` PASS but `--out en` for a Ukrainian question (Haiku copied
  the English example) and a nonsense sentence about "volatility". → example
  rewritten in Ukrainian with `--out uk`; rule "`--out` = language of the
  user's message".
- `english-report` PASS but the recommendation invented reasons ("lowest
  volatility", "volume just adjusted") and skipped `must_mention`. Root cause in
  code: `ranking.why` was English and number-free ("strongest factor:
  growth"), so the model filled the gap. → `why` is now a localized sentence
  with the numbers behind the rank; SKILL.md: use `why` as is.
- `followup-weights` PASS but exposed a **methodology flaw**: "stability" was
  k-of-12 (consistency of growth), so a language with an inconsistent decline
  looked "most stable". → stability = 1/(1+CV) of the deseasonalised share;
  consistency stays in confidence. Test `test_stability_prefers_steady_demand`.
- Also observed (not fixed, model limitation): wrong comparison of two
  numbers in prose ("share fell more than views" when −40% vs −55%).
- Added in this iteration: reader composition per edition (`readers`).

### Iteration 2 (10 cases × 3 runs): 27/30
Changes tested: localized `ranking.why` with numbers, stability = 1/(1+CV),
topic taken literally, `--out` = language of the user's message, readers.
- `niche-topic` 3/3 (was 0/1): topic kept literally, low confidence explained.
- `astronomy` run 3: answer dropped *what was measured* (the basket).
  → code: the basket goes into `must_mention`.
- `followup-weights` run 2: "stability 50%" — correct meaning, but only 0.5 was
  in the JSON. → code: weights printed as `0.5 (50%)`.
- `followup-weights` run 3: "найбільший **ринок** приховано" — Haiku paraphrased
  "top country" into the forbidden word. Model limitation, noted; guard warns
  on such wording in PDF summaries.

### Iteration 3 (3 affected cases × 3): 6/9 — a regression, read by hand
- `english-report` run 2 was an **eval bug**: the command was
  `".../wit.py" report` (quoted path) and the substring check missed it; PDF
  was produced. → quotes normalised in the checker.
- `astronomy` 1/3: once the basket became mandatory, Haiku started dropping
  seasonality — an attention trade-off in small models: what is not in
  `must_mention` gets lost. → code: seasonality (if volume is enough) is a
  one-line `must_mention` item.

### Iteration 4 (2 cases × 3): 6/6
Lesson: for a small model, *every* fact that must reach the user has to be a
ready sentence in `must_mention`; instructions in SKILL.md alone are not
reliable (compare rule 3 "convey must_mention" — followed consistently — with
the answer template, which was followed partially).

### Final regression (10 cases × 3, final code): 28/30
Both failures are in `english-report`, in free text written *after* the PDF:
an outside number (Brazil's population) and "market"/country wording for vi.
Next iteration: `report` returns a ready final message so nothing is composed
freely after the report.

### Iteration 5–6 (english-report × 3 each): `report` returns `final_message`
- Iteration 5: `report` returns a ready message (PDF path, summary, ranking
  with reasons, trust per language, must_mention, readers, limitation). Haiku
  sent it in 3/3 runs, but the one "next step" sentence it was still allowed to
  add went wrong twice: "(Singapore, Japan)" for vi (misread hidden-country
  data) and "у нових ринках". The eval regex only knew «ринок», not «ринках» —
  widened.
- Also found by a new unit test: guard did not treat "≠" as negation
  (`\b` does not match around a symbol), so "Перегляди ≠ готовність
  платити" would have been rejected. Fixed.
- Iteration 6: the next step is generated by code too; the agent adds nothing.
  3/3 pass, and all three messages end with the code-generated next step.

## How AI tools were used

- **Claude Code (Opus)** wrote the code, tests, references and this log,
  working through PLAN.md phase by phase.
- **Nothing it claimed about the outside world was trusted without a check:**
  API behaviour → real requests (fixtures); statistics → synthetic series with
  known answers + scipy cross-check + calibration; data → independent API
  endpoint; readers claim ("pt = Brazil") → real request, which also exposed
  the hidden-country trap.
- **Claude Code (Haiku 4.5)** was the test subject; its transcripts were read
  by hand after every run. Automatic checks found 2 eval bugs of their own
  (negation, quoted path) — which is why transcripts are always read.

### Language handling simplified (after review)
- Removed `guess_lang` (guessing the topic's language by letters) and
  `LANG_NAMES` (human names of editions). Checked by real requests that they
  were not needed: Wikidata search matches labels in other languages
  (`jejum intermitente` with de,fr → Q1666254; `астрономія` with pl,cs → Q333).
  Editions are now written as `pl.wikipedia`.
- `--out` is required: the agent passes the user's language. Texts exist in
  uk/en; other languages get English texts + `texts_language` telling the
  agent to translate words and keep numbers.
- Languages to analyse must come from the user; if missing (or countries are
  named), the agent asks and proposes an assumption instead of running.
- `topic_not_found` → hint to retry with the English name.
- New eval cases `no-languages-ask` and `polish-user`: 11/12 overall; the one
  fail is a model typo ("Dovira" in Latin letters), content was correct.

### Readability refactor (no functional change)
Long functions split into named steps: `pipeline.run` (8 numbered steps +
helpers), `basket.build` (candidates → validation → coverage → ordering →
hubs; meta returned instead of a fake `_basket_meta` warning), `analyze_language`
(per-article processing, agreement, deseasonalising, stability, bot signal),
`report._build` (one function per PDF section), `cli` (edit/report helpers,
doctor checks), `guard.check`, `resolve`, `confidence.assess` (caps vs
penalties), `http.get_json` (cache / retries / single request), `charts.plot`.
How "no functional change" was verified:
- golden snapshot of 14 CLI scenarios (stdout JSON, full analysis.json,
  extracted PDF text) taken before the refactor: 14/14 identical after every step
  (it caught one regression immediately: `cli resolve` still unpacked 2 values);
- old vs new `http.get_json` on 11 failure scenarios (5xx, 429, 404, network):
  identical results, errors and sleeps; new `tests/test_http.py`;
- old vs new `confidence.assess` on 20 000 random metric sets: 0 differences;
- unit tests 36/36, skill validator, 2 Haiku eval cases pass.
