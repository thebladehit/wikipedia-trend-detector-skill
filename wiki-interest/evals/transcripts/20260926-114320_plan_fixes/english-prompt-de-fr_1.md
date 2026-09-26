# english-prompt-de-fr — run 1: PASS

Checks failed: none  
Details: `{}`  
Agent turns: 4, tokens: 100951, time: 30.951 s

## User (turn 1)

Is interest in chess growing in German and French Wikipedia? We are considering a chess learning app.

### Tool call: Skill

```
{"skill": "wiki-interest", "args": "chess German French Wikipedia"}
```

<details><summary>Tool result</summary>

```
Launching skill: wiki-interest
```

</details>

### Tool call: Bash

```
cd <sandbox>/.claude/skills/wiki-interest && uv run scripts/wit.py run --topic "chess" --langs de,fr --out en
```

<details><summary>Tool result</summary>

```
Installed 13 packages in 25ms
{
 "status": "ok",
 "study": "chess_Q718",
 "version": "v21",
 "texts_language": "en",
 "topic": {
  "label": "chess",
  "qid": "Q718",
  "description": "strategy board game",
  "how": "exact match, 202 language editions"
 },
 "period": {
  "from": "2024-09",
  "to": "2026-08",
  "months": 24
 },
 "verdicts": {
  "de": "de.wikipedia: interest is declining — the topic's share of views in this language edition is -17% over the last 12 months vs the same months a year earlier (one-off spikes removed); 0 of 12 months higher than a year before; confidence: high (10/10); seasonal peak: December.",
  "fr": "fr.wikipedia: interest is declining — the topic's share of views in this language edition is -24% over the last 12 months vs the same months a year earlier (one-off spikes removed); 1 of 12 months higher than a year before; confidence: high (10/10); seasonal low: September (seasonality does not affect the year-over-year comparison — same months are compared)."
 },
 "trust": {
  "de": "Confidence high (10/10): large volume, consistent month to month, not driven by spikes.",
  "fr": "Confidence high (10/10): large volume, consistent month to month, not driven by spikes."
 },
 "must_mention": [
  "Seasonality in de.wikipedia: peak — December; low — —. Useful for planning launches.",
  "Seasonality in fr.wikipedia: peak — —; low — September. Useful for planning launches.",
  "The topic is measured by a basket of 10 articles: chess, fifty-move rule, promotion, king, endgame … — the basket can be changed."
 ],
 "readers": {
  "month": "2026-08",
  "top_countries": {
   "de": "DE 75%, AT 8%, CH 5%",
   "fr": "FR 71%, US 4%, BE 4%"
  },
  "note": "Where each language edition is read from (Wikimedia top-by-country, rough shares): language ≠ country."
 },
 "ranking": [
  {
   "lang": "de",
   "rank": 1,
   "score": 0.7,
   "why": "rank 1: topic share -17% YoY, 0 of 12 months above last year, 31 per million views of the edition, month-to-month variation 11%; strongest factor — growth, weakest — topic size; confidence high."
  },
  {
   "lang": "fr",
   "rank": 2,
   "score": 0.3,
   "why": "rank 2: topic share -24% YoY, 1 of 12 months above last year, 35 per million views of the edition, month-to-month variation 19%; strongest factor — topic size, weakest — growth; confidence high."
  }
 ],
 "table_md": "| language | topic share, YoY | views | direction | confidence | rank |\n|---|---|---|---|---|---|\n| de | -17% | -24% | declining | high (
… [2368 chars cut]
```

</details>

### Agent

Based on Wikipedia pageview data from the last 24 months, **interest in chess is declining in both German and French language editions** — though the situation differs:

**German Wikipedia:** Interest is down 17% year-over-year (0 of 12 recent months exceeded the prior year), confidence high. French Wikipedia is declining more steeply at -24% (1 of 12 months higher than last year), also high confidence. Seasonally, December is a peak month in German Wikipedia, while September is typically quieter in French.

**Ranking:** German performs slightly better than French — less steep decline and more stable month-to-month traffic — but both show the same direction: declining interest relative to the Wikipedia edition's overall traffic.

**How much to trust this:** Both measurements are highly reliable (confidence 10/10) because the topic gets substantial, consistent views with no significant spikes distorting the trend.

**Reader geography:** German readers (75% from Germany, 8% Austria, 5% Switzerland) and French readers (71% from France, 4% US, 4% Belgium) — a useful signal for localization if you go forward.

**What was measured:** A basket of 10 chess-related articles (chess, fifty-move rule, promotion, king, endgame, endgame tablebase, plus 4 others). You can adjust this basket if you want to focus on specific chess topics.

**Important caveats:** Wikipedia pageviews show topic awareness, not willingness to pay for a learning app. The decline might reflect shifting patterns in how people search for information (AI search engines, YouTube), not declining chess interest itself. You'd want to validate with surveys or ad tests before committing.

Would you like me to generate a PDF report for your team, or explore additional languages or time periods?
