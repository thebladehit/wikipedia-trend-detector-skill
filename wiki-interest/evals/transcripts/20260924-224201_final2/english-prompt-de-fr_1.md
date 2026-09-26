# english-prompt-de-fr — run 1: PASS

Checks failed: none  
Details: `{}`  
Agent turns: 4, tokens: 100623, time: 24.315 s

## User (turn 1)

Is interest in chess growing in German and French Wikipedia? We are considering a chess learning app.

### Tool call: Skill

```
{"skill": "wiki-interest", "args": "chess German French"}
```

<details><summary>Tool result</summary>

```
Launching skill: wiki-interest
```

</details>

### Tool call: Bash

```
uv run <sandbox>/.claude/skills/wiki-interest/scripts/wit.py run --topic "chess" --langs de,fr --out en
```

<details><summary>Tool result</summary>

```
Installed 13 packages in 27ms
{
 "status": "ok",
 "study": "chess_Q718",
 "version": "v16",
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
  "de": "de (German Wikipedia): interest is declining — the topic's share of views in this language edition is -17% over the last 12 months vs the same months a year earlier (one-off spikes removed); 0 of 12 months higher than a year before; confidence: high (10/10); seasonal peak: December.",
  "fr": "fr (French Wikipedia): interest is declining — the topic's share of views in this language edition is -23% over the last 12 months vs the same months a year earlier (one-off spikes removed); 2 of 12 months higher than a year before; confidence: high (10/10); seasonal low: September (seasonality does not affect the year-over-year comparison — same months are compared)."
 },
 "trust": {
  "de": "Confidence high (10/10): large volume, consistent month to month, not driven by spikes.",
  "fr": "Confidence high (10/10): large volume, consistent month to month, not driven by spikes."
 },
 "must_mention": [
  "Seasonality in de (German Wikipedia): peak — December; low — —. Useful for planning launches.",
  "Seasonality in fr (French Wikipedia): peak — —; low — September. Useful for planning launches.",
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
   "why": "rank 1: topic share -17% YoY, 0 of 12 months above last year, 32 per million views of the edition, month-to-month variation 11%; strongest factor — growth, weakest — topic size; confidence high."
  },
  {
   "lang": "fr",
   "rank": 2,
   "score": 0.3,
   "why": "rank 2: topic share -23% YoY, 2 of 12 months above last year, 35 per million views of the edition, month-to-month variation 19%; strongest factor — topic size, weakest — growth; confidence high."
  }
 ],
 "table_md": "| language | topic share, YoY | views | direction | confidence | rank |\n|---|---|---|---|---|---|\n| de | -17% | -24% | declini
… [2369 chars cut]
```

</details>

### Agent

## Interest in chess: declining in both German and French Wikipedia

**Verdict:**
- **German Wikipedia (de):** Interest is **declining** — the topic's share of views is **−17% year-over-year** over the last 12 months; none of the 12 months were higher than the same month a year earlier. Confidence: **high (10/10)**.
- **French Wikipedia (fr):** Interest is **declining** — the topic's share of views is **−23% year-over-year**; only 2 of 12 months were higher than the same month a year earlier. Confidence: **high (10/10)**.

**Ranking:** Both editions show decline. German (rank 1) declines less steeply (−17%) than French (rank 2, −23%).

**How much to trust it:** Both have high confidence (10/10) because the signal is large and consistent month-to-month, not driven by spikes. This is based on a basket of 10 related articles (chess, fifty-move rule, promotion, king, endgame, and 4 others — the basket can be adjusted).

**Seasonality:** German has a December peak (useful for planning); French has a September low.

**Who reads these editions:** 
- German: mostly from Germany (75%), Austria (8%), Switzerland (5%)
- French: mostly from France (71%), with smaller shares from the US (4%), Belgium (4%)

**Key limitations:**
- Wikipedia pageviews show *interest*, not willingness to pay for a product — validation through surveys or ad tests would help.
- Wikipedia is one signal; this is a direction for further research, not a decision.

**Chart generated** at `~/.cache/wiki-interest-evals/runs/chess_Q718/v16/chart.png`

Would you like me to generate a PDF report to share with stakeholders, or explore other languages or time periods?
