# fasting-pl-cs — run 1: PASS

Checks failed: none  
Details: `{}`  
Agent turns: 11, tokens: 190949, time: 48.09 s

## User (turn 1)

Порівняй зростання інтересу до інтервального голодування в польськомовній та чеськомовній Wikipedia за останні два роки.

### Tool call: Skill

```
{"args": "topic: intermittent fasting languages: pl, cs timeframe: last 2 years", "skill": "wiki-interest"}
```

<details><summary>Tool result</summary>

```
Launching skill: wiki-interest
```

</details>

### Tool call: Skill

```
{"args": "topic: intermittent fasting langs: pl, cs months: 24 out: uk", "skill": "wiki-interest"}
```

<details><summary>Tool result</summary>

```
Launching skill: wiki-interest
```

</details>

### Tool call: Skill

```
{"skill": "wiki-interest", "args": "topic: intermittent fasting langs: pl, cs months: 24 out: uk"}
```

<details><summary>Tool result</summary>

```
Launching skill: wiki-interest
```

</details>

### Tool call: Skill

```
{"skill": "wiki-interest", "args": "topic: intermittent fasting langs: pl, cs months: 24 out: uk"}
```

<details><summary>Tool result</summary>

```
Launching skill: wiki-interest
```

</details>

### Tool call: Bash

```
cd <sandbox>/.claude/skills/wiki-interest && uv run scripts/wit.py run --topic "intermittent fasting" --langs pl,cs --months 24 --out uk
```

<details><summary>Tool result</summary>

```
Installed 13 packages in 25ms
{
 "status": "ok",
 "study": "intermittent-fasting_Q1666254",
 "version": "v31",
 "texts_language": "uk",
 "topic": {
  "label": "Інтервальне голодування",
  "qid": "Q1666254",
  "description": "a diet that cycles between a period of fasting and non-fasting",
  "how": "exact match, 31 language editions"
 },
 "period": {
  "from": "2024-09",
  "to": "2026-08",
  "months": 24
 },
 "verdicts": {
  "cs": "cs.wikipedia: інтерес падає — частка переглядів теми в мовному розділі -30% за останні 12 міс. проти тих самих місяців роком раніше (без разових спайків); 1 з 12 місяців вищі, ніж рік тому; довіра: висока (10/10); сезонний пік: березень; сезонний спад: липень, серпень, вересень, жовтень (сезонність не впливає на порівняння рік до року — порівнюються ті самі місяці)."
 },
 "trust": {
  "cs": "Довіра висока (10/10): великий обсяг, послідовно місяць до місяця, не через спайки."
 },
 "must_mention": [
  "У pl.wikipedia немає статті на цю тему — інтерес там не виміряно.",
  "Сезонність у cs.wikipedia: пік — березень; спад — липень, серпень, вересень, жовтень. Це корисно для планування запусків.",
  "Тему виміряно кошиком з 10 статей: Інтервальне голодування, піст, reducing diet, Низьковуглеводна дієта, high-protein diet … — кошик можна змінити."
 ],
 "readers": {
  "month": "2026-08",
  "top_countries": {
   "cs": "CZ 80%, US 5%, SK 5%"
  },
  "note": "Звідки читають мовний розділ (Wikimedia top-by-country, приблизні частки): мова ≠ країна."
 },
 "ranking": [],
 "table_md": "| мова | частка теми, рік до року | перегляди | напрям | довіра | місце |\n|---|---|---|---|---|---|\n| cs | -30% | -40% | падає | висока (10/10) | — |",
 "basket": {
  "size": 10,
  "shown": [
   "Інтервальне голодування",
   "піст",
   "reducing diet",
   "Низьковуглеводна дієта",
   "high-protein diet",
   "схуднення"
  ],
  "more": 4,
  "removed": []
 },
 "warnings": [
  {
   "code": "missing_article",
   "text": "pl: no Wikipedia article for Інтервальне голодування (Q1666254). Nothing is substituted automatically.",
   "next": "To measure a related article instead (marked as proxy): uv run \"<sandbox>/.claude/skills/wiki-interest/scripts/wit.py\" edit --study intermittent-fasting_Q1666254 --article pl:\"<Title>\""
  }
 ],
 "assumptions": [
  "Період аналізу: 2024-09 … 2026-08 (24 повних міс.); дані завантажено з 2023-09 для порівняння рік до року і сезонності. Поточний місяць не враховано (непов
… [1768 chars cut]
```

</details>

### Agent

**Вердикт за мовинами**  
- **cs.wikipedia**: інтерес падає — частка переглядів теми -30 % за останні 12 місяців порівняно з тими ж місяцями року раніше (без разових спайків); 1 з 12 місяців вище, ніж рік тому; довіра: висока (10/10); сезонний пік: березень; сезонний спад: липень, серпень, вересень, жовтень (сезонність не впливає на порівняння рік до року — порівнюються ті самі місяці).  
- **pl.wikipedia**: у розділі немає статті «Інтервальне голодування» — інтерес там не вимірюється.

**Довіра**  
Довіра висока (10/10): великий обсяг, послідовно місяць до місяця, не через спайки.

**Що вимірювалося**  
Тема вимірюється кошиком із 10 статей:  
- Показані: «Інтервальне голодування», «піст», «reducing diet», «Низьковуглеводна дієта», «high-protein diet», «схуднення» тощо.  
- Єс ще 4 статі у кошику (загалом 10). Кошик можна змінити.

**Хто читає**  
За даними на серпень 2026 р.:  
- Читачі cs.wikipedia чекають převážно з Чеської республіки (CZ ≈ 80 %), Сполучених Штатів (US ≈ 5 %) та Словаччини (SK ≈ 5 %).  
(Мова ≠ країна — частина читачів може перебувати за кордоном або читати іншими мовами.)

**Обмеження**  
- Перегляди Wikipedia показують інтерес до теми, а не готовність платити за продукт.  
- Мовний розділ ≠ країна: читачі розділу живуть у різних країнах, а частина людей читає англійською.  
(Повний список обмежень — у вихідному JSON.)

**Файли та наступний крок**  
- Графік трендів: `~/.cache/wiki-interest-evals/runs/intermittent-fasting_Q1666254/v31/chart.png`  
- Якщо потрібен PDF‑звіт, можна запустити:  
  ```bash
  uv run "<sandbox>/.claude/skills/wiki-interest/scripts/wit.py" report --study intermittent-fasting_Q1666254 --summary "<2-4 речення з числами вище>"
  ```  
- Щось змінити (додати мови, период, кошик, ваги):  
  ```bash
  uv run "<sandbox>/.claude/skills/wiki-interest/scripts/wit.py" edit --study intermittent-fasting_Q1666254 --add-langs sk --months 36 --weights growth=0.2,size=0.3,stability=0.5
  ```

**Примітка**  
Оскільки у польській Вікіпедії немає статті «Інтервальне голодування», порівняння зростання можливе лише для чеськомовного розділу. Для отримання даних про pl можна вказати альтернативну статтю‑проксі (наприклад, «фізична активність» або «здоровий спосіб життя») за допомогою параметра `--article pl:"<Назва>"`.
