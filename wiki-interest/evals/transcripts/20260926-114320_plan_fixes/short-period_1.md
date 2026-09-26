# short-period — run 1: PASS

Checks failed: none  
Details: `{}`  
Agent turns: 4, tokens: 100550, time: 27.564 s

## User (turn 1)

How has interest in chess changed in Polish Wikipedia over the last 6 months?

### Tool call: Skill

```
{"skill": "wiki-interest", "args": "topic: chess, language: Polish, timeframe: 6 months"}
```

<details><summary>Tool result</summary>

```
Launching skill: wiki-interest
```

</details>

### Tool call: Bash

```
cd <sandbox>/.claude/skills/wiki-interest && uv run scripts/wit.py run --topic "chess" --langs pl --months 6 --out en
```

<details><summary>Tool result</summary>

```
Installed 13 packages in 25ms
{
 "status": "ok",
 "study": "chess_Q718",
 "version": "v20",
 "texts_language": "en",
 "topic": {
  "label": "chess",
  "qid": "Q718",
  "description": "strategy board game",
  "how": "exact match, 202 language editions"
 },
 "period": {
  "from": "2026-03",
  "to": "2026-08",
  "months": 6
 },
 "verdicts": {
  "pl": "pl.wikipedia: interest is declining — the topic's share of views in this language edition is -14% over the last 6 months vs the same months a year earlier (one-off spikes removed); 0 of 6 months higher than a year before; confidence: high (10/10); seasonal peak: January, December; seasonal low: June, July, August (seasonality does not affect the year-over-year comparison — same months are compared)."
 },
 "trust": {
  "pl": "Confidence high (10/10): large volume, consistent month to month, not driven by spikes."
 },
 "must_mention": [
  "Seasonality in pl.wikipedia: peak — January, December; low — June, July, August. Useful for planning launches.",
  "The topic is measured by a basket of 10 articles: chess, promotion, king, endgame, rules of chess … — the basket can be changed."
 ],
 "readers": {
  "month": "2026-08",
  "top_countries": {
   "pl": "PL 87%, US 4%, DE 2%"
  },
  "note": "Where each language edition is read from (Wikimedia top-by-country, rough shares): language ≠ country."
 },
 "ranking": [],
 "table_md": "| language | topic share, YoY | views | direction | confidence | rank |\n|---|---|---|---|---|---|\n| pl | -14% | -24% | declining | high (10/10) | — |",
 "basket": {
  "size": 10,
  "shown": [
   "chess",
   "promotion",
   "king",
   "endgame",
   "rules of chess",
   "shogi"
  ],
  "more": 4,
  "removed": []
 },
 "warnings": [],
 "assumptions": [
  "Period analysed: 2026-03 … 2026-08 (6 full months); downloaded from 2023-09 for year-over-year comparison and seasonality. The current month is excluded (incomplete).",
  "Period shorter than a year: growth compares these 6 months with the same months a year earlier.",
  "Topic measured by a basket of 10 related articles (candidates from en.wikipedia, method: morelike ∩ links of the main article; only articles existing in the compared languages).",
  "Views: humans only (agent=user), all access methods. Views of up to 5 most-used redirects are added to each article."
 ],
 "limitations": [
  "Wikipedia pageviews show interest in a topic, not willingness to pay for a product.",
  "A language edition is not a country: readers live in many countries a
… [1185 chars cut]
```

</details>

### Agent

Interest in chess on Polish Wikipedia has **declined significantly** over the last 6 months:

**Verdict:** Chess's share of pageviews on Polish Wikipedia fell **14% year-over-year** (comparing March–August 2026 to the same months in 2025). None of the six months showed higher traffic than the previous year. Confidence is **high (10/10)** — the volume is large, trends are consistent month-to-month, and the decline isn't driven by one-off spikes.

**Seasonality matters for context:** Chess shows a strong seasonal pattern on pl.wikipedia:
- **Peak months:** January, December  
- **Low months:** June, July, August

This natural rhythm doesn't affect the year-over-year comparison (same months are compared), but it's useful if you're planning anything chess-related.

**What was measured:** The analysis tracks a basket of 10 related articles: *chess*, *promotion*, *king*, *endgame*, *rules of chess*, *shogi*, and 4 others. You can adjust this basket if you want to focus on different aspects (e.g., chess players, tournaments).

**Readers:** The Polish-language edition is read mostly from Poland (87%), with smaller portions from the US (4%) and Germany (2%).

**How much to trust it:** The decline is real and confident, but remember: Wikipedia pageviews reflect curiosity and information-seeking, not necessarily deeper behavior change. This is a direction for further validation—consider surveys or other sources to understand whether the decline reflects reduced interest or just a shift in where people find chess content.

Would you like a PDF report, or would you like to explore a different time period or add other language editions for comparison?
