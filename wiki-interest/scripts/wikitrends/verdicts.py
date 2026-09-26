"""Ready-made sentences (uk/en) so the agent retells, not interprets.
Other output languages get the English texts (see pipeline.texts_language).
Every number here is also exposed in `allowed_numbers` for guard.py."""
from __future__ import annotations

from .config import RULES
from .confidence import LEVEL_NAMES

MONTHS = {
    "uk": ["січень", "лютий", "березень", "квітень", "травень", "червень", "липень", "серпень", "вересень",
           "жовтень", "листопад", "грудень"],
    "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
           "November", "December"],
}

T = {
    "uk": {
        "rising": "інтерес зростає", "declining": "інтерес падає", "flat": "інтерес стабільний (без помітних змін)",
        "unclear": "напрям неясний (зміна непослідовна місяць до місяця):",
        "no_data": "даних недостатньо для порівняння рік до року",
        "share": "частка переглядів теми в мовному розділі {g} за останні {n} міс. проти тих самих місяців роком раніше (без разових спайків)",
        "k": "{k} з {n} місяців вищі, ніж рік тому",
        "conf": "довіра: {c}",
        "season": "сезонний пік: {m}",
        "trough": "сезонний спад: {m} (сезонність не впливає на порівняння рік до року — порівнюються ті самі місяці)",
        "trust": "Довіра {lvl} ({score}/10): {why}.",
        "abs": "в абсолютних переглядах {v}, бо загальний трафік розділу змінився на {p}",
        "proxy": "Увага: для {lang} використано статтю-замінник, яка вимірює близьке, але інше поняття.",
        "missing": "У {lang} немає статті на цю тему — інтерес там не виміряно.",
        "share_vs_abs": "У {lang} частка теми і абсолютні перегляди рухаються в різні боки: частка {g}, перегляди {v} (трафік усього розділу {p}).",
        "low_conf": "Довіра для {lang} — {c}: {why}.",
        "spike": "У {lang} {s} сирого приросту дали короткі спайки; висновки — за очищеним рядом.",
        "divergence": "У {lang} зростання тримається на одній-двох статтях кошика, а не на темі загалом.",
        "late": "У {lang} частина статей з'явилась посеред періоду.",
        "seasonal": "Сезонність у {lang}: пік — {peaks}; спад — {lows}. Це корисно для планування запусків.",
        "basket": "Тему виміряно кошиком з {n} статей: {items} — кошик можна змінити.",
        "levelshift": "У {lang} різкий зсув рівня з {m} (×{r}) без спайку — можлива технічна причина (перейменування, зміна посилань), перевірте.",
    },
    "en": {
        "rising": "interest is rising", "declining": "interest is declining", "flat": "interest is flat (no notable change)",
        "unclear": "direction is unclear (change not consistent month to month):",
        "no_data": "not enough data for a year-over-year comparison",
        "share": "the topic's share of views in this language edition is {g} over the last {n} months vs the same months a year earlier (one-off spikes removed)",
        "k": "{k} of {n} months higher than a year before",
        "conf": "confidence: {c}",
        "season": "seasonal peak: {m}",
        "trough": "seasonal low: {m} (seasonality does not affect the year-over-year comparison — same months are compared)",
        "trust": "Confidence {lvl} ({score}/10): {why}.",
        "abs": "in absolute views {v}, because total traffic of the edition changed by {p}",
        "proxy": "Note: for {lang} a proxy article is used; it measures a related but different concept.",
        "missing": "{lang} has no article on this topic — interest there is not measured.",
        "share_vs_abs": "In {lang} share and absolute views move in opposite directions: share {g}, views {v} (whole edition traffic {p}).",
        "low_conf": "Confidence for {lang} is {c}: {why}.",
        "spike": "In {lang} {s} of the raw increase came from short spikes; conclusions use the cleaned series.",
        "divergence": "In {lang} growth comes from one or two basket articles, not the topic as a whole.",
        "late": "In {lang} some articles appeared during the period.",
        "seasonal": "Seasonality in {lang}: peak — {peaks}; low — {lows}. Useful for planning launches.",
        "basket": "The topic is measured by a basket of {n} articles: {items} — the basket can be changed.",
        "levelshift": "In {lang} there is a sharp level shift from {m} (x{r}) without a spike — possibly technical (rename, link changes); check it.",
    },
}

DIRECTION = {"uk": {"rising": "зростає", "declining": "падає", "flat": "стабільно", "unclear": "неясно"},
             "en": {"rising": "rising", "declining": "declining", "flat": "flat", "unclear": "unclear"}}
LEVEL = LEVEL_NAMES

ASSUMPTIONS = {
    "uk": {
        "clip": "Запитаний період починається раніше за {s} (перший місяць даних pageviews); аналіз починається з {s}.",
        "period": "Період аналізу: {a} … {b} ({n} повних міс.); дані завантажено з {f} для порівняння рік до року і сезонності. Поточний місяць не враховано (неповний).",
        "short": "Період коротший за рік: ріст порівнює ці {n} міс. з тими самими місяцями роком раніше.",
        "basket": "Тема вимірюється кошиком з {n} пов'язаних статей (кандидати з {w}.wikipedia, метод: {m}; лише статті, що є в порівнюваних мовах).",
        "no_basket": "Тема вимірюється лише головною статтею (кошик вимкнено).",
        "views": "Перегляди: лише люди (agent=user), усі способи доступу. До кожної статті додано перегляди до {r} її найпопулярніших редиректів.",
        "weights": "Ваги рейтингу: ріст {g} ({gp}), розмір {s} ({sp}), стабільність {st} ({stp}) (розмір = частка теми в переглядах розділу; стабільність = низька мінливість частки по місяцях без сезонності). Бали відносні — лише між порівнюваними мовами.",
    },
    "en": {
        "clip": "Requested period starts before {s} (first month with pageviews data); analysis starts at {s}.",
        "period": "Period analysed: {a} … {b} ({n} full months); downloaded from {f} for year-over-year comparison and seasonality. The current month is excluded (incomplete).",
        "short": "Period shorter than a year: growth compares these {n} months with the same months a year earlier.",
        "basket": "Topic measured by a basket of {n} related articles (candidates from {w}.wikipedia, method: {m}; only articles existing in the compared languages).",
        "no_basket": "Topic measured by the main article only (basket off).",
        "views": "Views: humans only (agent=user), all access methods. Views of up to {r} most-used redirects are added to each article.",
        "weights": "Ranking weights: growth {g} ({gp}), size {s} ({sp}), stability {st} ({stp}) (size = topic share of the edition's views; stability = low month-to-month variation of the share, seasonality removed). Scores are relative to the compared languages.",
    },
}

READERS_NOTE = {
    "uk": "Звідки читають мовний розділ (Wikimedia top-by-country, приблизні частки): мова ≠ країна.",
    "en": "Where each language edition is read from (Wikimedia top-by-country, rough shares): language ≠ country.",
}

READERS_HIDDEN = {
    "uk": "країну №1 приховано Wikimedia (правила приватності), частки невідомі; далі: {c}",
    "en": "the top country is hidden by Wikimedia (privacy rules), shares unknown; next: {c}",
}

LIMITATIONS = {
    "uk": [
        "Перегляди Wikipedia показують інтерес до теми, а не готовність платити за продукт.",
        "Мовний розділ ≠ країна: читачі розділу живуть у різних країнах, а частина людей читає англійською.",
        "Wikipedia — лише одне джерело; висновок — напрям для подальшої перевірки (опитування, тест реклами), а не рішення.",
        "Частка переглядів нормалізована на весь трафік розділу; трафік Wikipedia загалом змінюється (пошукові AI-відповіді, мобільні застосунки).",
        "Біноміальний тест вважає місяці незалежними; насправді вони пов'язані, тому довіра — евристика, а не статистична значущість.",
    ],
    "en": [
        "Wikipedia pageviews show interest in a topic, not willingness to pay for a product.",
        "A language edition is not a country: readers live in many countries and some read in English.",
        "Wikipedia is one source; the result is a direction for further validation (surveys, ad tests), not a decision.",
        "Views are normalised by total traffic of the edition; Wikipedia traffic itself shifts (AI search answers, apps).",
        "The binomial test treats months as independent; they are not, so confidence is a heuristic, not statistical significance.",
    ],
}


def pct(x: float | None) -> str:
    if x is None:
        return "n/a"
    v = round(x * 100)
    return f"{'+' if v > 0 else ''}{v}%" if v != 0 else "0%"


def month_list(ms: list[int], out: str) -> str:
    return ", ".join(MONTHS[out][m - 1] for m in ms)


def edition(code: str, out: str) -> str:
    return f"{code}.wikipedia"


def verdict(m: dict, out: str) -> str:
    t = T[out]
    parts = [edition(m["lang"], out) + ":"]
    if m["growth_clean"] is None:
        parts.append(t["no_data"] + ";")
    else:
        parts.append(t[m["direction"]] + ("" if m["direction"] == "unclear" else " —"))
        parts.append(t["share"].format(g=pct(m["growth_clean"]), n=m["n"]) + ";")
        parts.append(t["k"].format(k=m["k"], n=m["n"]) + ";")
        if m["growth_views"] is not None and m["project_growth"] is not None and (
                (m["growth_views"] > 0) != (m["growth_clean"] > 0) or abs(m["project_growth"]) > 0.15):
            parts.append(t["abs"].format(v=pct(m["growth_views"]), p=pct(m["project_growth"])) + ";")
    parts.append(t["conf"].format(c=m["confidence"]["label"]))
    # with little data "seasonality" is noise — do not report it
    enough = m["median_monthly_views"] >= RULES["vol_medium_cap"]
    for key, field in (("season", "peaks"), ("trough", "troughs")):
        if enough and m.get("season") and m["season"][field]:
            parts[-1] += ";"
            parts.append(t[key].format(m=month_list(m["season"][field], out)))
    return " ".join(parts).rstrip(";") + "."


FACTORS = {"uk": {"growth": "ріст", "size": "розмір аудиторії теми", "stability": "стабільність"},
           "en": {"growth": "growth", "size": "topic size", "stability": "stability"}}
WHY = {
    "uk": "місце {rank}: частка теми {g} рік до року, {k} з {n} міс. вищі за торішні, частка в розділі {ppm} на млн переглядів, мінливість по місяцях {cv}; найсильніший фактор — {best}, найслабший — {worst}; довіра {lvl}.",
    "en": "rank {rank}: topic share {g} YoY, {k} of {n} months above last year, {ppm} per million views of the edition, month-to-month variation {cv}; strongest factor — {best}, weakest — {worst}; confidence {lvl}.",
}


def why(r: dict, m: dict, out: str) -> str:
    f = FACTORS[out]
    best = max(r["parts"], key=r["parts"].get)
    worst = min(r["parts"], key=r["parts"].get)
    return WHY[out].format(rank=r["rank"], g=pct(m["growth_clean"]), k=m["k"], n=m["n"], ppm=f"{m['share_ppm']:.0f}", cv=f"{m['cv']:.0%}" if m.get("cv") is not None else "n/a",
                           best=f[best], worst=f[worst], lvl=LEVEL_NAMES[out][m["confidence"]["level"]])


def trust(m: dict, out: str) -> str:
    c = m["confidence"]
    why = "; ".join(c["capped_by"] + c["reasons"])
    return T[out]["trust"].format(lvl=LEVEL_NAMES[out][c["level"]], score=c["score"], why=why)


TABLE_HEADER = {"uk": "| мова | частка теми, рік до року | перегляди | напрям | довіра | місце |",
                "en": "| language | topic share, YoY | views | direction | confidence | rank |"}


def table_md(results: dict, ranking: list[dict], out: str) -> str:
    """Markdown table the agent can paste as is; rows in ranking order."""
    rank_of = {r["key"]: r["rank"] for r in ranking}
    rows = [TABLE_HEADER[out], "|---|---|---|---|---|---|"]
    for lang, m in sorted(results.items(), key=lambda kv: rank_of.get(kv[0], 0)):
        rows.append(f"| {lang} | {pct(m['growth_clean'])} | {pct(m['growth_views'])} | {DIRECTION[out][m['direction']]} | "
                    f"{LEVEL[out][m['confidence']['level']]} ({m['confidence']['score']}/10) | {rank_of.get(lang, '—')} |")
    return "\n".join(rows)


def basket_note(items: list[dict], out: str) -> list[str]:
    """must_mention line about what was measured (only when there is a real basket)."""
    if len(items) <= 1:
        return []
    shown = ", ".join(it["label"] for it in items[:5]) + (" …" if len(items) > 5 else "")
    return [T[out]["basket"].format(n=len(items), items=shown)]


def must_mention(results: dict, missing: list[str], out: str) -> list[str]:
    t = T[out]
    msgs = []
    for lang in missing:
        msgs.append(t["missing"].format(lang=edition(lang, out)))
    for lang, m in results.items():
        e = edition(lang, out)
        if m["proxy"]:
            msgs.append(t["proxy"].format(lang=e))
        c = m["confidence"]
        if c["level"] != "high":
            why = "; ".join((c["capped_by"] or c["reasons"])[:2])
            msgs.append(t["low_conf"].format(lang=e, c=LEVEL_NAMES[out][c["level"]], why=why))
        if m["growth_clean"] is not None and m["growth_views"] is not None and \
                (m["growth_clean"] > 0.1 and m["growth_views"] < 0 or m["growth_clean"] < -0.1 and m["growth_views"] > 0):
            msgs.append(t["share_vs_abs"].format(lang=e, g=pct(m["growth_clean"]), v=pct(m["growth_views"]),
                                                 p=pct(m["project_growth"])))
        if m["divergence"]:
            msgs.append(t["divergence"].format(lang=e))
        season = m.get("season") or {}
        if m["median_monthly_views"] >= RULES["vol_medium_cap"] and (season.get("peaks") or season.get("troughs")):
            msgs.append(t["seasonal"].format(lang=e, peaks=month_list(season.get("peaks", []), out) or "—",
                                             lows=month_list(season.get("troughs", []), out) or "—"))
        if m["level_shift"]:
            msgs.append(t["levelshift"].format(lang=e, m=m["level_shift"]["month"], r=f"{m['level_shift']['ratio']:.1f}"))
    return msgs
