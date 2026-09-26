"""One-page A4 PDF. Font: DejaVu Sans shipped inside matplotlib (Cyrillic,
Latin, Greek; no CJK/Arabic — unsupported characters are replaced and noted).
If the page overflows, fonts shrink step by step; if it still does not fit,
raise report_overflow instead of silently cutting text."""
from __future__ import annotations

import datetime as dt
import pathlib

import matplotlib
from fontTools.ttLib import TTFont
from fpdf import FPDF

from . import verdicts as V
from .config import METHODOLOGY_VERSION, RULES
from .http import WitError

FONT_DIR = pathlib.Path(matplotlib.get_data_path()) / "fonts" / "ttf"
REG, BOLD = FONT_DIR / "DejaVuSans.ttf", FONT_DIR / "DejaVuSans-Bold.ttf"
_cmap: set[int] | None = None

L = {
    "uk": {"summary": "Висновок", "table": "Мовні розділи", "basket": "Кошик статей (тема вимірюється набором статей)",
           "more": "ще {n}", "notes": "Що важливо врахувати", "assump": "Припущення", "limits": "Обмеження",
           "footer": "Джерело: Wikimedia Pageviews API (лише перегляди людьми). Методологія v{v}. Дослідження {s}, {ver}. Створено {d}.",
           "lang": "мова", "share": "частка р/р", "views": "перегляди", "dir": "напрям", "conf": "довіра",
           "rank": "місце", "season": "сезонний пік", "replaced": "Деякі символи не підтримуються шрифтом і замінені на «?»."},
    "en": {"summary": "Conclusion", "table": "Language editions", "basket": "Article basket (the topic is measured by a set of articles)",
           "more": "{n} more", "notes": "Important to keep in mind", "assump": "Assumptions", "limits": "Limitations",
           "footer": "Source: Wikimedia Pageviews API (human views only). Methodology v{v}. Study {s}, {ver}. Created {d}.",
           "lang": "language", "share": "share YoY", "views": "views", "dir": "direction", "conf": "confidence",
           "rank": "rank", "season": "seasonal peak", "replaced": "Some characters are not supported by the font and were replaced with '?'."},
}


def _supported() -> set[int]:
    global _cmap
    if _cmap is None:
        _cmap = set(TTFont(str(REG)).getBestCmap().keys())
    return _cmap


class _Safe:
    replaced = False

    @classmethod
    def txt(cls, s: str) -> str:
        cmap = _supported()
        out = []
        for ch in str(s):
            if ord(ch) in cmap or ch in "\n\t":
                out.append(ch)
            else:
                cls.replaced = True
                out.append("?")
        return "".join(out)


def auto_summary(compact: dict) -> str:
    """Summary composed by code from verdicts (fallback when the agent's text is rejected)."""
    parts = list(compact["verdicts"].values())
    if compact.get("ranking"):
        top = compact["ranking"][0]
        parts.append(("Найвище в рейтингу: " if compact.get("_out") == "uk" else "Top of the ranking: ") + top["lang"] + ".")
    return " ".join(parts)


FINAL = {
    "uk": {"pdf": "PDF-звіт", "summary": "Висновок", "rank": "Рейтинг мовних розділів", "trust": "Наскільки довіряти",
           "note": "Важливо", "limit": "Обмеження", "readers": "Звідки читають розділи",
           "next_rank": "Наступний крок: перевірити {top} опитуванням або невеликим тестом реклами. Змінити мови, період, кошик чи ваги можна одним уточненням.",
           "next_one": "Наступний крок: перевірити висновок іншими джерелами (опитування, тест реклами). Змінити мови, період чи кошик можна одним уточненням."},
    "en": {"pdf": "PDF report", "summary": "Conclusion", "rank": "Ranking of language editions", "trust": "How much to trust it",
           "note": "Important", "limit": "Limitation", "readers": "Where the editions are read from",
           "next_rank": "Next step: validate {top} with a survey or a small ad test. Languages, period, basket or weights can be changed with one follow-up.",
           "next_one": "Next step: validate the result with other sources (survey, ad test). Languages, period or basket can be changed with one follow-up."},
}


def final_message(compact: dict, summary: str, pdf_path: str, out: str) -> str:
    """Ready message for the user after the PDF: everything comes from the
    analysis, so the agent does not compose free text (where small models add
    outside facts or 'market' wording)."""
    t = FINAL[out]
    lines = [f"**{t['pdf']}:** `{pdf_path}`", "", f"**{t['summary']}:** {summary}"]
    if compact.get("ranking"):
        lines += ["", f"**{t['rank']}:**"] + [f"{r['rank']}. {r['lang']} — {r['why']}" for r in compact["ranking"]]
    lines += ["", f"**{t['trust']}:**"] + [f"- {l}: {v}" for l, v in compact.get("trust", {}).items()]
    # confidence caveats are already in the trust lines above
    notes = [m for m in compact.get("must_mention", []) if not m.startswith(("Довіра для", "Confidence for"))]
    if notes:
        lines += ["", f"**{t['note']}:**"] + [f"- {m}" for m in notes]
    rd = (compact.get("readers") or {}).get("top_countries")
    if rd and len(rd) > 1:
        lines += ["", f"**{t['readers']}:** " + "; ".join(f"{l} — {v}" for l, v in rd.items())]
    if compact.get("limitations"):
        lines += ["", f"**{t['limit']}:** {compact['limitations'][0]}"]
    rk = compact.get("ranking") or []
    lines += ["", t["next_rank"].format(top=" і ".join(r["lang"] for r in rk[:2]) if out == "uk"
                                        else " and ".join(r["lang"] for r in rk[:2])) if rk else t["next_one"]]
    return "\n".join(lines)


class _Page:
    """One A4 page; `scale` shrinks every font/line height when content overflows."""

    def __init__(self, scale: float):
        self.scale = scale
        self.pdf = FPDF(format="A4")
        self.pdf.set_auto_page_break(auto=True, margin=10)
        self.pdf.set_margins(12, 10, 12)
        self.pdf.add_font("DV", "", str(REG))
        self.pdf.add_font("DV", "B", str(BOLD))
        self.pdf.add_page()
        self.width = self.pdf.w - 24

    def fs(self, size: float) -> float:
        return size * self.scale

    def font(self, size: float, bold: bool = False) -> None:
        self.pdf.set_font("DV", "B" if bold else "", self.fs(size))

    def heading(self, text: str, size: float, height: float) -> None:
        self.font(size, bold=True)
        self.pdf.cell(self.width, self.fs(height), _Safe.txt(text), new_x="LMARGIN", new_y="NEXT")

    def paragraph(self, text: str, height: float, **kw) -> None:
        self.pdf.multi_cell(self.width, self.fs(height), _Safe.txt(text), new_x="LMARGIN", new_y="NEXT", **kw)


def _build(compact: dict, analysis: dict, summary: str, title: str, out: str, scale: float, drop_assumptions: bool) -> FPDF:
    page = _Page(scale)
    t = L[out]
    _title(page, compact, title)
    _summary_box(page, t, summary)
    _chart(page, compact)
    _languages_table(page, t, compact, analysis, out)
    _readers_line(page, compact)
    page.pdf.ln(1.5)
    _basket(page, t, compact)
    _notes(page, t, compact, drop_assumptions)
    _footer(page, t, compact)
    return page.pdf


def _title(page: _Page, compact: dict, title: str) -> None:
    page.font(13, bold=True)
    page.paragraph(title, 6)
    page.font(7.5)
    page.pdf.set_text_color(90)
    topic, period = compact["topic"], compact["period"]
    page.paragraph(f"{topic['label']} ({topic['qid']}) — {topic['description']}. {period['from']} … {period['to']}", 4)
    page.pdf.set_text_color(0)
    page.pdf.ln(1.5)


def _summary_box(page: _Page, t: dict, summary: str) -> None:
    page.pdf.set_fill_color(240, 245, 255)
    page.pdf.set_draw_color(42, 111, 219)
    page.font(9, bold=True)
    page.pdf.cell(page.width, page.fs(5.5), _Safe.txt(t["summary"]), border="LTR", fill=True, new_x="LMARGIN", new_y="NEXT")
    page.font(8.5)
    page.paragraph(summary, 4.4, border="LBR", fill=True, padding=(0, 2, 1.5, 2), align="L")
    page.pdf.ln(2)


def _chart(page: _Page, compact: dict) -> None:
    chart = pathlib.Path(compact["files"]["chart"])
    if not chart.exists():
        return
    h = page.width * 3.3 / 8.2 * min(1.0, page.scale + 0.05)
    w = h * 8.2 / 3.3  # keep the chart's aspect ratio
    page.pdf.image(str(chart), x=12 + (page.width - w) / 2, w=w, h=h)
    page.pdf.ln(1)


TABLE_WIDTHS = [0.09, 0.15, 0.11, 0.16, 0.2, 0.2, 0.09]


def _languages_table(page: _Page, t: dict, compact: dict, analysis: dict, out: str) -> None:
    pdf, w = page.pdf, page.width
    page.heading(t["table"], 9, 5)
    page.font(7.5, bold=True)
    pdf.set_fill_color(235)
    for col, share in zip([t["lang"], t["share"], t["views"], t["dir"], t["conf"], t["season"], t["rank"]], TABLE_WIDTHS):
        pdf.cell(w * share, page.fs(5), _Safe.txt(col), border=1, fill=True)
    pdf.ln()
    page.font(7.5)
    rank_of = {r["lang"]: r["rank"] for r in compact.get("ranking", [])}
    results = analysis["results"]
    for lang in sorted(results, key=lambda l: rank_of.get(l, 0)):
        for cell, share in zip(_table_row(lang, results[lang], rank_of, out), TABLE_WIDTHS):
            pdf.cell(w * share, page.fs(4.6), _Safe.txt(cell)[:40], border=1)
        pdf.ln()
    for lang in compact.get("missing_languages", []):
        pdf.cell(w * TABLE_WIDTHS[0], page.fs(4.6), _Safe.txt(lang), border=1)
        pdf.cell(w * (1 - TABLE_WIDTHS[0]), page.fs(4.6), _Safe.txt(V.T[out]["missing"].format(lang=lang)), border=1)
        pdf.ln()


def _table_row(lang: str, m: dict, rank_of: dict, out: str) -> list[str]:
    # with little data "seasonality" is noise — not shown (same rule as verdicts)
    enough = m["median_monthly_views"] >= RULES["vol_medium_cap"]
    peaks = (V.month_list((m.get("season") or {}).get("peaks", []), out) if enough else "") or "—"
    confidence = f"{V.LEVEL[out][m['confidence']['level']]} ({m['confidence']['score']}/10)"
    return [lang, V.pct(m["growth_clean"]), V.pct(m["growth_views"]), V.DIRECTION[out][m["direction"]],
            confidence, peaks, str(rank_of.get(lang, "—"))]


def _readers_line(page: _Page, compact: dict) -> None:
    readers = compact.get("readers", {})
    if not readers.get("top_countries"):
        return
    page.font(6.8)
    page.pdf.set_text_color(80)
    countries = "; ".join(f"{l} — {v}" for l, v in readers["top_countries"].items())
    page.paragraph(readers["note"] + f" {readers['month']}: " + countries, 3.4, align="L")
    page.pdf.set_text_color(0)


def _basket(page: _Page, t: dict, compact: dict) -> None:
    basket = compact["basket"]
    page.heading(t["basket"], 8, 4.5)
    page.font(7.5)
    more = f" + {t['more'].format(n=basket['more'])}" if basket["more"] else ""
    page.paragraph(", ".join(basket["shown"]) + more, 3.8)
    page.pdf.ln(1)


def _notes(page: _Page, t: dict, compact: dict, drop_assumptions: bool) -> None:
    """must_mention + assumptions (dropped first when space is short) + limitations."""
    page.heading(t["notes"], 8, 4.5)
    page.font(6.8)
    notes = list(compact.get("must_mention", []))
    if not drop_assumptions:
        notes += [f"{t['assump']}: " + a for a in compact.get("assumptions", [])]
    notes += [f"{t['limits']}: " + " ".join(compact.get("limitations", []))]
    if _Safe.replaced:
        notes.append(t["replaced"])
    for note in notes:
        page.paragraph("• " + note, 3.3, align="L")


def _footer(page: _Page, t: dict, compact: dict) -> None:
    page.pdf.ln(1)
    page.font(6.3)
    page.pdf.set_text_color(110)
    page.paragraph(t["footer"].format(v=METHODOLOGY_VERSION, s=compact["study"], ver=compact["version"],
                                      d=dt.date.today().isoformat()), 3.2)


def make_pdf(compact: dict, analysis: dict, summary: str, title: str, out: str, path: pathlib.Path) -> dict:
    for scale, drop in [(1.0, False), (0.92, False), (0.85, False), (0.85, True), (0.78, True)]:
        _Safe.replaced = False
        pdf = _build(compact, analysis, summary, title, out, scale, drop)
        if pdf.pages_count == 1:
            pdf.output(str(path))
            return {"scale": scale, "assumptions_dropped": drop}
    raise WitError("report_overflow", "The report does not fit on one page.",
                   "Shorten --summary to 2-4 sentences (or compare fewer languages) and run `report` again.")
