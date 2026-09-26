# english-report — run 1: FAIL

Checks failed: commands, must_include, files  
Details: `{"missing_commands": ["wit.py report"], "missing_include": ["pdf|PDF"]}`  
Agent turns: 4, tokens: 103426, time: 36.855 s

## User (turn 1)

Ми створюємо застосунок для вивчення мов. Порівняй інтерес до вивчення англійської в українській, польській, турецькій, в'єтнамській і португальській Вікіпедії та підготуй короткий звіт у PDF: які аудиторії варто дослідити наступними й чому?

### Tool call: Skill

```
{"skill": "wiki-interest", "args": "topic: \"English language learning\" languages: \"uk,pl,tr,vi,pt\""}
```

<details><summary>Tool result</summary>

```
Launching skill: wiki-interest
```

</details>

### Tool call: Bash

```
cd <sandbox>/.claude/skills/wiki-interest && uv run scripts/wit.py run --topic "English language learning" --langs uk,pl,tr,vi,pt --out uk
```

<details><summary>Tool result</summary>

```
Installed 13 packages in 25ms
{
 "status": "ok",
 "study": "english-as-a-second-or-foreign-language_Q130192",
 "version": "v2",
 "texts_language": "uk",
 "topic": {
  "label": "English as a second or foreign language",
  "qid": "Q130192",
  "description": "use of English by speakers with different native languages",
  "how": "exact match, 14 language editions"
 },
 "period": {
  "from": "2024-09",
  "to": "2026-08",
  "months": 24
 },
 "verdicts": {
  "tr": "tr.wikipedia: інтерес стабільний (без помітних змін) — частка переглядів теми в мовному розділі 0% за останні 12 міс. проти тих самих місяців роком раніше (без разових спайків); 6 з 12 місяців вищі, ніж рік тому; в абсолютних переглядах -19%, бо загальний трафік розділу змінився на -16%; довіра: середня (6/10)."
 },
 "trust": {
  "tr": "Довіра середня (6/10): непослідовно: лише 6 з 12 місяців вищі, ніж рік тому; частина статей з'явилась посеред періоду; невеликий обсяг: медіана 143 переглядів/міс (< 300)."
 },
 "must_mention": [
  "У uk.wikipedia немає статті на цю тему — інтерес там не виміряно.",
  "У pl.wikipedia немає статті на цю тему — інтерес там не виміряно.",
  "У vi.wikipedia немає статті на цю тему — інтерес там не виміряно.",
  "У pt.wikipedia немає статті на цю тему — інтерес там не виміряно.",
  "Довіра для tr.wikipedia — середня: непослідовно: лише 6 з 12 місяців вищі, ніж рік тому; частина статей з'явилась посеред періоду.",
  "Тему виміряно кошиком з 3 статей: English as a second or foreign language, мовна освіта, bilingual education — кошик можна змінити."
 ],
 "readers": {
  "month": "2026-08",
  "top_countries": {
   "tr": "країну №1 приховано Wikimedia (правила приватності), частки невідомі; далі: US, DE, NL"
  },
  "note": "Звідки читають мовний розділ (Wikimedia top-by-country, приблизні частки): мова ≠ країна."
 },
 "ranking": [],
 "table_md": "| мова | частка теми, рік до року | перегляди | напрям | довіра | місце |\n|---|---|---|---|---|---|\n| tr | 0% | -19% | стабільно | середня (6/10) | — |",
 "basket": {
  "size": 3,
  "shown": [
   "English as a second or foreign language",
   "мовна освіта",
   "bilingual education"
  ],
  "more": 0,
  "removed": []
 },
 "warnings": [
  {
   "code": "missing_article",
   "text": "uk: no Wikipedia article for English as a second or foreign language (Q130192). Nothing is substituted automatically.",
   "next": "To measure a related article instead (marked as proxy): uv run \"<tmp>/wit-eval
… [3980 chars cut]
```

</details>

### Agent

## Результати: дуже мало даних для порівняння

Аналіз показує **критичне обмеження**: 

**🔴 Статей немає** — у українській, польській, в'єтнамській та португальській Вікіпедії відсутні статті про "English as a second or foreign language", тому інтерес там не виміряно.

**🟡 Тільки турецька** — турецька Вікіпедія має дані, але:
- Інтерес **стабільний** (0% змін рік до року)
- Довіра **середня** (6/10): деякі статті з'явилися посередині періоду, обсяг малий
- Читачі: переважно з US, DE, NL (але точна країна прихована для приватності)

## Як рухатися далі для застосунку

**Пропоную два варіанти:**

**1. Використати проксі-статті** — замість точного матчу додати релевантні статті, що вже існують:
   - 📄 "English language" (базова тема)
   - 📄 "Foreign language" 
   - 📄 "Language acquisition"
   
   Це дасть сигнал про інтерес до англійської мови в кожному регіоні.

**2. Шукати інший кут** — замість "вивчення англійської" проаналізувати:
   - "English language" (загальна тема)
   - "Second language acquisition"
   - Трафік до статей про мови взагалі

Який підхід вам цікавіший? Я можу перезапустити аналіз з іншими статтями як проксі або змінити фокус теми.
