# short-period — run 1: PASS

Checks failed: none  
Details: `{}`  
Agent turns: 4, tokens: 99958, time: 21.959 s

## User (turn 1)

How has interest in chess changed in Polish Wikipedia over the last 6 months?

### Tool call: Skill

```
{"skill": "wiki-interest", "args": "chess Polish Wikipedia 6 months"}
```

<details><summary>Tool result</summary>

```
Launching skill: wiki-interest
```

</details>

### Tool call: Bash

```
uv run <sandbox>/.claude/skills/wiki-interest/scripts/wit.py run --topic "chess" --langs pl --months 6 --out en
```

<details><summary>Tool result</summary>

```
Installed 13 packages in 23ms
{
 "status": "ok",
 "study": "chess_Q718",
 "version": "v15",
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
  "pl": "pl (Polish Wikipedia): interest is declining — the topic's share of views in this language edition is -14% over the last 6 months vs the same months a year earlier (one-off spikes removed); 0 of 6 months higher than a year before; confidence: high (10/10); seasonal peak: January, December; seasonal low: June, July, August (seasonality does not affect the year-over-year comparison — same months are compared)."
 },
 "trust": {
  "pl": "Confidence high (10/10): large volume, consistent month to month, not driven by spikes."
 },
 "must_mention": [
  "Seasonality in pl (Polish Wikipedia): peak — January, December; low — June, July, August. Useful for planning launches.",
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
  "Views: humans only (agent=user), all access methods. Up to 5 redirects of the main article are added to it."
 ],
 "limitations": [
  "Wikipedia pageviews show interest in a topic, not willingness to pay for a product.",
  "A language edition is not a country: readers live in many countries and some read in 
… [1168 chars cut]
```

</details>

### Agent

**Polish Wikipedia: interest in chess is declining**

Over the last 6 months (March–August 2026), chess interest on Polish Wikipedia dropped **14% in topic share** compared to the same months a year earlier. Total pageviews fell **24%**. None of the 6 months showed higher views than the year-before period — the decline was consistent.

**Confidence: high (10/10).** The large, stable volume of views rules out spikes or seasonal noise driving this result.

**Seasonality matters for your planning:** Chess peaks on Polish Wikipedia in January and December, with seasonal lows in June, July, and August. These patterns don't affect the year-over-year decline (same months are always compared), but they shape when readers visit.

**What was measured:** A basket of 10 articles related to chess — chess (primary), promotion, king, endgame, rules of chess, shogi, and 4 more. You can adjust this basket if you'd like to focus on different aspects.

**Readers:** Polish Wikipedia's chess content is read mostly from Poland (87%), with some readers from the US (4%) and Germany (2%).

**Limitations to keep in mind:** Wikipedia pageviews measure interest, not purchasing intent. Wikipedia traffic itself is shifting (AI search, mobile apps), so the decline reflects both topic interest and broader platform trends. This is a direction for validation—pair it with surveys or search trends to confirm.

**Chart:** Saved to `~/.cache/wiki-interest-evals/runs/chess_Q718/v15/chart.png`

Would you like me to generate a PDF report of these findings, or explore chess interest in other language editions for comparison?
