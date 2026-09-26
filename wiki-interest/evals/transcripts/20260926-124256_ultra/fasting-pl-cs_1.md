# fasting-pl-cs — run 1: PASS

Checks failed: none  
Details: `{}`  
Agent turns: 4, tokens: 91098, time: 27.335 s

## User (turn 1)

Порівняй зростання інтересу до інтервального голодування в польськомовній та чеськомовній Wikipedia за останні два роки.

### Tool call: Skill

```
{"skill": "wiki-interest", "args": "Compare growth of interest in intermittent fasting in Polish and Czech Wikipedia over the last two years"}
```

<details><summary>Tool result</summary>

```
Launching skill: wiki-interest
```

</details>

### Tool call: Bash

```
uv run <sandbox>/.claude/skills/wiki-interest/scripts/wit.py run --topic "intermittent fasting" --langs pl,cs --months 24 --out uk
```

<details><summary>Tool result</summary>

```
Installed 13 packages in 25ms
{
 "status": "ok",
 "study": "intermittent-fasting_Q1666254",
 "version": "v32",
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
… [1792 chars cut]
```

</details>

### Agent

## Результати порівняння

### 📊 Вердикт за мовами

| Мова | Зміна частки переглядів (рік до року) | Напрям | Довіра |
|------|----------------------------------------|--------|--------|
| **cs (чеська)** | **−30%** | 📉 падає | висока (10/10) |
| **pl (польська)** | — | ❌ **не виміряно** | — |

### ⚠️ Важливо
**У польській Вікіпедії немає статті на тему «Інтервальне голодування» (Q1666254)** — тому інтерес там не виміряно. Якщо потрібно оцінити інтерес через пов'язану статтю (позначена як *proxy*), можна задати її через `edit --article pl:"<Назва>"`.

### 📈 Деталі для čeština (cs)
- **Частка теми в мовному розділі зменшилася на 30%** за останні 12 місяців проти тих самих місяців рік тому
- Перегляди падають послідовно: **1 з 12 місяців** вищими за рік тому
- **Сезонність**: пік — **березень**, спад — **липень–жовтень** (під час порівняння рік до року сезонність не впливає — порівнюються ті самі місяці)
- Читачі: **CZ 80%, US 5%, SK 5%**

### 🧮 Що вимірювалося
Тема охоплює **кошик з 10 статей** (показано 6):
- Інтервальне голодування, піст, reducing diet, Низьковуглеводна дієта, high-protein diet, схуднення (+ 4 інші)

### ⚠️ Обмеження (must mention)
1. Перегляди Вікіпедії показують інтерес до теми, **не готовність платити**.
2. Мовний розділ ≠ країна: читачі живуть у різних країнах.
3. Висновок — **напрям для перевірки** (опитування, тест реклами), а не рішення.

### 📁 Файли
- **Графік**: `~/.cache/wiki-interest-evals/runs/intermittent-fasting_Q1666254/v32/chart.png`
- **Аналіз**: `~/.cache/wiki-interest-evals/runs/intermittent-fasting_Q1666254/v32/analysis.json`

---

**Наступний крок:** Якщо хочете виміряти польський інтерес через пов'язану статтю (наприклад, «post» або іншу), скажіть, яку саме — і я запущу `edit --article pl:"..."`. Також можна зробити PDF-звіт.
