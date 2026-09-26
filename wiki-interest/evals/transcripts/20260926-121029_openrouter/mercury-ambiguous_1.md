# mercury-ambiguous — run 1: FAIL

Checks failed: must_include  
Details: `{"missing_include": ["ртут|бог|елемент"]}`  
Agent turns: 11, tokens: 230424, time: 58.546 s

## User (turn 1)

Чи росте інтерес до Меркурія в українській Вікіпедії?

### Tool call: Skill

```
{"skill": "wiki-interest", "args": "Mercury Ukrainian Wikipedia"}
```

<details><summary>Tool result</summary>

```
Launching skill: wiki-interest
```

</details>

### Tool call: Skill

```
{"args": "run --topic \"Mercury\" --langs uk --out uk", "skill": "wiki-interest"}
```

<details><summary>Tool result</summary>

```
Launching skill: wiki-interest
```

</details>

### Tool call: Skill

```
{"skill": "wiki-interest", "args": "run --topic \"Mercury\" --langs uk --out uk"}
```

<details><summary>Tool result</summary>

```
Launching skill: wiki-interest
```

</details>

### Tool call: Bash

```
uv run <sandbox>/.claude/skills/wiki-interest/scripts/wit.py run --topic "Mercury" --langs uk --out uk
```

<details><summary>Tool result</summary>

```
Installed 13 packages in 25ms
{
 "status": "needs_input",
 "reason": "ambiguous_topic",
 "question": "'Mercury' can mean several things. Which one?",
 "options": [
  {
   "qid": "Q308",
   "label": "Меркурій",
   "description": "найближча до Сонця велика планета Сонячної системи",
   "wikipedias": 251
  },
  {
   "qid": "Q925",
   "label": "ртуть",
   "description": "хімічний елемент з атомним номером 80",
   "wikipedias": 176
  },
  {
   "qid": "Q1150",
   "label": "Меркурій",
   "description": "Roman god of trade, merchants, thieves and travel",
   "wikipedias": 84
  },
  {
   "qid": "Q1231263",
   "label": "Меркюрі",
   "description": "муніципалітет у департаменті Савоя, Франція",
   "wikipedias": 35
  },
  {
   "qid": "Q613883",
   "label": "Mercury",
   "description": "automobile marque of the Ford Motor Company",
   "wikipedias": 27
  },
  {
   "qid": "Q1274643",
   "label": "Phoenix Mercury",
   "description": "American professional women's basketball team",
   "wikipedias": 25
  }
 ],
 "next": "uv run \"<sandbox>/.claude/skills/wiki-interest/scripts/wit.py\" run --qid <QID> --langs uk",
 "api": {
  "requests_made": 0,
  "cache_hits": 3
 }
}
```

</details>

### Agent


</tool_call>

### Tool call: Bash

```
uv run "<sandbox>/.claude/skills/wiki-interest/scripts/wit.py" run --qid Q308 --langs uk
```

<details><summary>Tool result</summary>

```
Exit code 1
{
 "status": "error",
 "code": "bad_args",
 "message": "the following arguments are required: --out",
 "hint": "See `uv run \"<sandbox>/.claude/skills/wiki-interest/scripts/wit.py\" run --help`."
}
```

</details>

### Tool call: Bash

```
uv run "<sandbox>/.claude/skills/wiki-interest/scripts/wit.py" run --qid Q308 --langs uk --out uk
```

<details><summary>Tool result</summary>

```
{
 "status": "ok",
 "study": "mercury_Q308",
 "version": "v2",
 "texts_language": "uk",
 "topic": {
  "label": "Меркурій",
  "qid": "Q308",
  "description": "найближча до Сонця велика планета Сонячної системи",
  "how": "qid given"
 },
 "period": {
  "from": "2024-09",
  "to": "2026-08",
  "months": 24
 },
 "verdicts": {
  "uk": "uk.wikipedia: інтерес падає — частка переглядів теми в мовному розділі -36% за останні 12 міс. проти тих самих місяців роком раніше (без разових спайків); 0 з 12 місяців вищі, ніж рік тому; в абсолютних переглядах -54%, бо загальний трафік розділу змінився на -25%; довіра: висока (10/10); сезонний пік: лютий, грудень; сезонний спад: травень, червень, липень, серпень, вересень (сезонність не впливає на порівняння рік до року — порівнюються ті самі місяці)."
 },
 "trust": {
  "uk": "Довіра висока (10/10): великий обсяг, послідовно місяць до місяця, не через спайки."
 },
 "must_mention": [
  "Сезонність у uk.wikipedia: пік — лютий, грудень; спад — травень, червень, липень, серпень, вересень. Це корисно для планування запусків.",
  "Тему виміряно кошиком з 10 статей: Меркурій, Дослідження Меркурія, планета, магнітне поле Меркурія, атмосфера Меркурія … — кошик можна змінити."
 ],
 "readers": {
  "month": "2026-08",
  "top_countries": {
   "uk": "UA 65%, US 11%, PL 4%"
  },
  "note": "Звідки читають мовний розділ (Wikimedia top-by-country, приблизні частки): мова ≠ країна."
 },
 "ranking": [],
 "table_md": "| мова | частка теми, рік до року | перегляди | напрям | довіра | місце |\n|---|---|---|---|---|---|\n| uk | -36% | -54% | падає | висока (10/10) | — |",
 "basket": {
  "size": 10,
  "shown": [
   "Меркурій",
   "Дослідження Меркурія",
   "планета",
   "магнітне поле Меркурія",
   "атмосфера Меркурія",
   "Церера"
  ],
  "more": 4,
  "removed": []
 },
 "warnings": [],
 "assumptions": [
  "Період аналізу: 2024-09 … 2026-08 (24 повних міс.); дані завантажено з 2023-09 для порівняння рік до року і сезонності. Поточний місяць не враховано (неповний).",
  "Тема вимірюється кошиком з 10 пов'язаних статей (кандидати з en.wikipedia, метод: morelike ∩ links of the main article; лише статті, що є в порівнюваних мовах).",
  "Перегляди: лише люди (agent=user), усі способи доступу. До головної статті додано до 5 її редиректів."
 ],
 "limitations": [
  "Перегляди Wikipedia показують інтерес до теми, а не готовність платити за продукт.",
  "Мовний розділ ≠ країна: читачі розділу живуть у різних країнах, а частина людей читає англійською.",
  "Wikip
… [1186 chars cut]
```

</details>

### Agent

**Вердикт (uk):** інтерес до Меркурія (планета) в українській Вікіпедії **падає** — частка переглядів теми -36% за останні 12 місяців порівняно з тими ж місяцями минулого року (без разових спайків); 0 з 12 місяців вище, ніж рік тому; в абсолютних переглядах -54% (загальний трафік розділу змінився на -25%). Довіра: висока (10/10).  
**Сезонність:** пік — лютий, грудень; спад — травень, червень, липень, серпень, вересень (сезонність не впливає на порівняння рік до року, бо порівнюються ті самі місяці).  

**Як вимірювали:** тема вимірюється кошиком з 10 пов’язаних статей. У кошику показано: Меркурій, Дослідження Меркурія, планета, магнітне поле Меркурія, атмосфера Меркурія, Церера (ще 4 статті не показано). Кошик можна змінити.  

**Хто читає:** за даними за серпень 2026 р. український розділ читають głównie з України (65%), Сполучених Штатів (11%) та Польщі (4%).  

**Обмеження:**  
- Перегляди Wikipedia показують інтерес до теми, а не готовність платити за продукт.  
- Мовний розділ ≠ країна: читачі розділу живуть у різних країнах, а частина людей читає англійською.  

**Файли та далі:**  
- Графік тренду: `~/.cache/wiki-interest-evals/runs/mercury_Q308/v2/chart.png`  
- Можна отримати звіт у форматі PDF:  
  `uv run "<sandbox>/.claude/skills/wiki-interest/scripts/wit.py" report --study mercury_Q308 --summary "Інтерес до Меркурія (планета) в українській Вікіпедії падає на 36% у частці переглядів та на 54% в абсолютних переглядах за останній рік. Довіра висока (10/10). Сезонний пік — лютий і грудень, спад — литень‑вересень."`  
- Можна змінити мови, період, кошик або ваги: `edit --study mercury_Q308 …` (дивітьсь `next_steps` у JSON).  

> Усі числа, напрями та формулювання взято без змін з JSON‑виводу інструменту `wiki-interest`. Прогнозування причин змін або рекомендації щодо дій не надано — дані служат лише напрямком для подальшої перевірки.
