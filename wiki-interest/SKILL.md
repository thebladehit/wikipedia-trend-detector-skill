---
name: wiki-interest
description: Analyzes Wikipedia pageview trends across language editions to estimate audience interest in a topic — growth, how much to trust it, seasonality, ranking of languages — and produces a chart and a one-page PDF report. Use when the user asks whether interest in a topic is growing, compares topics or language audiences for a product, course, app or localization, or wants a report based on Wikipedia/Wikimedia data. Works for requests in any language (e.g. «інтерес до теми», «мовні розділи», «Вікіпедія», «звіт»).
compatibility: Requires uv (https://docs.astral.sh/uv/) and internet access to wikimedia.org / wikidata.org.
---

# Wikipedia interest trends

The code decides, you retell. All numbers, directions, confidence and ranking
come from the tool's JSON. Your job: turn the request into one command, then
retell the ready-made parts.

`<skill>` below = the directory containing this SKILL.md (use its absolute
path). Every command prints one JSON object. Copy follow-up commands from the
JSON (`next`, `next_steps`) — they already contain the full path.

## Hard rules

1. Use only numbers that appear in the JSON. Never compute or estimate new ones.
2. Direction and confidence come from `verdicts` — do not reinterpret
   (flat ≠ growing, unclear ≠ growing).
3. Always convey every item of `must_mention`.
4. `status: needs_input` → ask the user the `question` with the `options`; do not guess.
5. Say «мовний розділ» / "language edition", never «ринок», "market" or "country".
6. Do not explain *why* interest changed (YouTube, AI search, school year, news…):
   the data does not show causes. Do not list "possible reasons". If the user asks
   why, say Wikipedia data cannot tell and suggest how to check.
7. Pageviews ≠ willingness to pay. Present results as a direction for further validation.

## Which command

| Situation | Command |
|---|---|
| New question about a topic | `uv run <skill>/scripts/wit.py run --topic "<topic>" --langs <codes> --out <uk\|en>` |
| Tool asked to pick a meaning (`needs_input`) | ask user, then `run --qid <QID> --langs ...` |
| Follow-up: add/remove languages, period, basket, weights | `edit --study <id> ...` (reuses cache, new version) |
| User wants a PDF / report to share | `report --study <id> --title "<user question>" --summary "<2-4 sentences>"` |
| "What did we compute before?" | `list`, then `show <study>` |
| Errors / first run | `doctor` |

`edit` flags: `--add-langs sk`, `--remove-langs pl`, `--months 36`,
`--basket-remove "<title or QID>"`, `--basket-add Q123,en:Title`,
`--basket none`, `--weights growth=0.2,size=0.3,stability=0.5`,
`--article pl:"<Title>"` (use a specific article for a language; marked as proxy
if it is a different concept), `--out uk`.

## Request → parameters

- `--topic`: the subject **exactly in the user's words** (any language) — do not
  broaden or rephrase it ("гравітаційно-хвильова астрономія" stays as is).
  For "learning X" / "X courses" use the subject itself (e.g. `English language`)
  and tell the user the basket is shown and can be adjusted.
- `--langs`: Wikipedia codes: uk, pl, cs, sk, en, de, fr, es, pt, tr, vi, … .
  "Polish-language" → `pl`. Never map a country to a code on your own; if the user
  names countries, ask which languages they mean.
- `--months`: default 24. "last two years" → 24, "three years" → 36, "last year" → 12.
- `--out`: the language of the **user's message** (not of the topic):
  Ukrainian message → `uk`, otherwise `en`.
- Priorities ("stability matters more than growth") → `--weights`.

## Answer template (keep it short)

1. **Verdict per language** — from `verdicts` (you may shorten, keep numbers exact).
2. **Ranking** (if several languages) — `ranking[].why` as is (do not add your own
   reasons such as "volatility" or "potential"); mention weights from
   `assumptions` and that the user can change them.
3. **How much to trust it** — the `trust` sentence as is; every `must_mention` item
   (also in the final message after making a PDF).
4. **What was measured** — basket `shown` (+ `more`); offer to edit it.
5. **Who reads it** — `readers.top_countries` when languages are compared
   (e.g. pt is read mostly from BR) — helps choose a launch country.
6. **Limitations** — 1-2 most relevant lines from `limitations`.
7. **Files & next step** — chart path; offer a PDF or a follow-up.

You may paste `table_md` as is.

## PDF report

`report` checks your summary: numbers not in the analysis or claims like
"users will pay" → `status: rejected` and no PDF. Fix the text using `allowed`,
and retry once. If it is rejected again, use `--summary auto`. Give the user
the `pdf` path. If `guard_warnings` is not empty, re-read those sentences.
If a warning says the language differs, run the suggested `edit --out`.

## Examples

**«Чи зростає інтерес до астрономії в україномовній Вікіпедії і наскільки можна довіряти?»**
`uv run <skill>/scripts/wit.py run --topic "астрономія" --langs uk --out uk`
→ retell `verdicts.uk`, explain confidence (level + reasons), seasonality
(peak/low months are useful for planning), basket, limitations.

**«Порівняй зростання інтересу до інтервального голодування в польськомовній та чеськомовній Wikipedia за два роки.»**
`uv run <skill>/scripts/wit.py run --topic "intermittent fasting" --langs pl,cs --months 24 --out uk`
→ if `missing_languages` contains `pl`, say plainly that pl has no article so it
is not measured; offer `edit --article pl:"<Title>"` with a related article
(it will be marked proxy). Do not pick an article yourself without asking.

**«Порівняй інтерес до вивчення англійської в uk, pl, tr, vi, pt і зроби звіт: кого досліджувати далі?»**
1. `run --topic "English language" --langs uk,pl,tr,vi,pt --out uk`
2. Answer from `ranking` + `verdicts` + `must_mention`.
3. `report --study <study> --title "<question>" --summary "<2-4 sentences with numbers from the JSON>"`

## When to read references

- `references/METHODOLOGY.md` — the user asks how growth/confidence/ranking is computed.
- `references/LIMITATIONS.md` — the user challenges conclusions or asks what the data can't say.
- `references/API_NOTES.md` — debugging API behaviour.
