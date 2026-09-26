# polish-user — run 1: PASS

Checks failed: none  
Details: `{}`  
Agent turns: 4, tokens: 100299, time: 24.701 s

## User (turn 1)

Czy rośnie zainteresowanie szachami w polskiej Wikipedii?

### Tool call: Skill

```
{"skill": "wiki-interest", "args": "chess Polish Wikipedia"}
```

<details><summary>Tool result</summary>

```
Launching skill: wiki-interest
```

</details>

### Tool call: Bash

```
cd <sandbox>/.claude/skills/wiki-interest && uv run scripts/wit.py run --topic "chess" --langs pl --out pl
```

<details><summary>Tool result</summary>

```
Installed 13 packages in 24ms
{
 "status": "ok",
 "study": "chess_Q718",
 "version": "v22",
 "texts_language": "en (translate words into 'pl', keep every number exactly)",
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
  "pl": "pl.wikipedia: interest is declining — the topic's share of views in this language edition is -21% over the last 12 months vs the same months a year earlier (one-off spikes removed); 0 of 12 months higher than a year before; confidence: high (10/10); seasonal peak: January, December; seasonal low: June, July, August (seasonality does not affect the year-over-year comparison — same months are compared)."
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
 "table_md": "| language | topic share, YoY | views | direction | confidence | rank |\n|---|---|---|---|---|---|\n| pl | -21% | -30% | declining | high (10/10) | — |",
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
  "Period analysed: 2024-09 … 2026-08 (24 full months); downloaded from 2023-09 for year-over-year comparison and seasonality. The current month is excluded (incomplete).",
  "Topic measured by a basket of 10 related articles (candidates from en.wikipedia, method: morelike ∩ links of the main article; only articles existing in the compared languages).",
  "Views: humans only (agent=user), all access methods. Views of up to 5 most-used redirects are added to each article."
 ],
 "limitations": [
  "Wikipedia pageviews show interest in a topic, not willingness to pay for a product.",
  "A language edition is not a country: readers live in many countries and some read in English.",
  "Wikipedia is
… [1142 chars cut]
```

</details>

### Agent

## Zainteresowanie szachami w polskiej Wikipedii

**Nie, zainteresowanie szachami pada.** W polskiej Wikipedii udział wyświetleń szachów zmniejszył się o **21% w ciągu ostatnich 12 miesięcy** w porównaniu z tym samym okresem rok wcześniej. W żaden z 12 miesięcy liczba wyświetleń nie była wyższa niż rok wcześniej.

### Zaufanie do wyniku
Pewność jest **wysoka (10/10)** – duży wolumen danych, konsystentna zmiana z miesiąca na miesiąc, bez wpływu jednorazowych skoków.

### Sezonowość
Temat wykazuje wyraźny wzorzec sezonowy:
- **Szczyty**: styczeń i grudzień
- **Spadki**: czerwiec, lipiec, sierpień

Ta sezonowość nie wpływa na porównanie rok do roku (porównujemy te same miesiące).

### Co zostało zmierzone
Szachy mierzono za pomocą **koszyka 10 artykułów**: szachy, promocja, król, endszpil, reguły szachów, shogi i 4 dodatkowe artykuły. Ten koszyk można zmienić.

### Czytelnicy
Polską Wikipedię o szachach czyta głównie z Polski (**87%**), pozostali z USA (**4%**) i Niemiec (**2%**).

### Ograniczenia pomiaru
- Wyświetlenia to mara zainteresowania, nie chęci do zapłacenia
- Wikipedia to jedno źródło; wynik powinien być weryfikowany dalej (ankiety, testy)
- Zmienia się ogólny ruch w Wikipedii (sztuczna inteligencja, aplikacje)

---

Chciałbyś **raportu PDF** do udostępnienia? Lub porównać szachy z innym językami Wikipedii?
