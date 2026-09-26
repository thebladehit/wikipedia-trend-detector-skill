# API notes — verified by real requests

Every statement below was checked with real HTTP requests on 2026-09-24
(raw responses are saved in `tests/fixtures/`). Re-check before relying on
anything that is not listed here.

## Wikidata `wbsearchentities`

- Returns labels **and aliases**, so exact-match filtering is not enough:
  `астрономія` (uk) matches Q333 *astronomy* (253 wiki sitelinks), Q12012641
  *Hogwarts class* (2) and Q21451142 *a Wikidata property* (0).
- Scholarly articles and clinical trials appear in results
  (`intermittent fasting` → 4 of 5 hits are papers). They have 0 wiki sitelinks.
- **Rule used:** keep candidates with ≥ 1 Wikipedia sitelink; auto-pick the
  top candidate by sitelink count when it has ≥ 3× the sitelinks of the next
  exact match. Otherwise → `needs_input`.
  - astronomy: 253 vs 2 → auto Q333
  - Меркурій: Q308 planet 251, Q925 mercury (element) 176, Q1150 god 84 → ask
- Disambiguation items have `P31 = Q4167410` (e.g. Q48397 *Mercury*).

## Wikidata `wbgetentities`

- `props=sitelinks` gives the article title in every language (`ukwiki`, …).
- Missing languages are simply absent: Q1666254 *intermittent fasting* has
  `cswiki`, `ukwiki`, `enwiki`, `viwiki`, but **no `plwiki`**. This is the
  "missing article" case for the task's pl-vs-cs example.
- Up to 50 ids per request.

## MediaWiki `list=search&srsearch=morelike:`

- Quality depends on the topic:
  - uk *Астрономія*: relevant (astrophysics, galaxy, stars, constellations);
    some persons (Tycho Brahe) and individual stars.
  - en *English language*: poor — unrelated languages (Rarámuri, Tonkawa…).
  - cs *Přerušovaný půst*: relevant (diets, obesity, fasting) with some noise.
- Intersection with the main article's outgoing links (`prop=links`) removes
  most noise: for *English language* 14 of 100 morelike results remain, all
  about English/Germanic languages. `prop=links` is paged (`continue`).
- **Rule used:** candidates = morelike ∩ links when the intersection has
  ≥ 5 items, otherwise plain morelike.

## MediaWiki `prop=pageprops` / `prop=pageviews`

- `ppprop=wikibase_item|disambiguation` works for up to 50 titles; missing
  pages have `"missing": true`; `redirects=1` resolves redirects.
- uk *Меркурій* is a disambiguation page (`pageprops.disambiguation`); the
  planet is *Меркурій (планета)*.
- `prop=pageviews&pvipdays=60` returns last-60-day daily views for up to 50
  titles **in one request** (last day may be `null`). Used to rank basket
  candidates cheaply instead of 50 separate REST calls.

## Pageviews REST (`wikimedia.org/api/rest_v1/metrics/pageviews`)

- One `per-article … /daily/START/END` call returns the whole range
  (1096 days in one response). No pagination.
- **Days with 0 views are often omitted** (niche article: 67 of 90 days
  present). Missing day = 0.
- Data starts 2015-07-01; earlier dates are silently truncated (no error).
- Data for the **current month is returned up to yesterday** → partial months
  must be dropped explicitly.
- Unknown article → **HTTP 404** with "we either do not have data" → treat as
  "no data", not as an error.
- Views of a redirect title are counted separately from the target
  (uk redirect *Astronomy* had no views in 2025, so impact is usually small).
- `cache-control: max-age=14400`. 20 parallel requests → all 200; no rate
  limit headers were returned. A descriptive User-Agent is required by
  Wikimedia policy.
- Project traffic changes a lot: uk.wikipedia `user` views fell from 91.6 M
  (2023-01) to 50.7 M (2026-08). **Raw growth of an article can be
  negative while its share of the project grows** — both must be reported.
- Access split (uk, 2026-08): desktop 19.7 M, mobile-web 30.5 M,
  mobile-app 0.45 M.

## `top-by-country/{project}/{access}/{year}/{month}`

- Works (monthly). Views are **buckets** (`"1000000-9999999"`) plus
  `views_ceil`; some ranks are missing (privacy suppression, e.g. rank 6 in
  uk 2026-08). Only suitable for rough shares.
- **Rank 1 is missing for tr, vi, ru** (2026-08): the home country is on
  Wikimedia's privacy protection list. Naive shares of the visible rows gave
  "tr: US 31%, DE 15%" — wrong. The tool shows names without shares when any
  of the top-3 ranks is missing. Verified: pt → BR 74%, PT 9%; uk → UA 65%.
