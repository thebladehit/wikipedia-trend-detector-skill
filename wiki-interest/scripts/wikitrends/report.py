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


def _build(compact: dict, analysis: dict, summary: str, title: str, out: str, scale: float, drop_assumptions: bool) -> FPDF:
    t = L[out]
    S = _Safe.txt
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=10)
    pdf.set_margins(12, 10, 12)
    pdf.add_font("DV", "", str(REG))
    pdf.add_font("DV", "B", str(BOLD))
    pdf.add_page()
    W = pdf.w - 24
    fs = lambda x: x * scale  # noqa: E731

    pdf.set_font("DV", "B", fs(13))
    pdf.multi_cell(W, fs(6), S(title), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DV", "", fs(7.5))
    pdf.set_text_color(90)
    per = compact["period"]
    pdf.multi_cell(W, fs(4), S(f"{compact['topic']['label']} ({compact['topic']['qid']}) — {compact['topic']['description']}. "
                                f"{per['from']} … {per['to']}"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0)
    pdf.ln(1.5)

    # summary box
    pdf.set_fill_color(240, 245, 255)
    pdf.set_draw_color(42, 111, 219)
    pdf.set_font("DV", "B", fs(9))
    pdf.cell(W, fs(5.5), S(t["summary"]), border="LTR", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DV", "", fs(8.5))
    pdf.multi_cell(W, fs(4.4), S(summary), border="LBR", fill=True, new_x="LMARGIN", new_y="NEXT", padding=(0, 2, 1.5, 2),
                   align="L")
    pdf.ln(2)

    # chart
    chart = pathlib.Path(compact["files"]["chart"])
    if chart.exists():
        h = W * 3.3 / 8.2 * min(1.0, scale + 0.05)
        pdf.image(str(chart), x=12 + (W - h * 8.2 / 3.3) / 2, w=h * 8.2 / 3.3, h=h)
        pdf.ln(1)

    # table
    pdf.set_font("DV", "B", fs(9))
    pdf.cell(W, fs(5), S(t["table"]), new_x="LMARGIN", new_y="NEXT")
    cols = [t["lang"], t["share"], t["views"], t["dir"], t["conf"], t["season"], t["rank"]]
    widths = [0.09, 0.15, 0.11, 0.16, 0.2, 0.2, 0.09]
    pdf.set_font("DV", "B", fs(7.5))
    pdf.set_fill_color(235)
    for c, w in zip(cols, widths):
        pdf.cell(W * w, fs(5), S(c), border=1, fill=True)
    pdf.ln()
    pdf.set_font("DV", "", fs(7.5))
    rank_of = {r["lang"]: r["rank"] for r in compact.get("ranking", [])}
    res = analysis["results"]
    for lang in sorted(res, key=lambda l: rank_of.get(l, 0)):
        m = res[lang]
        peaks = (V.month_list((m.get("season") or {}).get("peaks", []), out)
                 if m["median_monthly_views"] >= RULES["vol_medium_cap"] else "") or "—"
        row = [lang, V.pct(m["growth_clean"]), V.pct(m["growth_views"]), V.DIRECTION[out][m["direction"]],
               f"{V.LEVEL[out][m['confidence']['level']]} ({m['confidence']['score']}/10)", peaks, str(rank_of.get(lang, "—"))]
        for c, w in zip(row, widths):
            pdf.cell(W * w, fs(4.6), S(c)[:40], border=1)
        pdf.ln()
    for lang in compact.get("missing_languages", []):
        pdf.cell(W * widths[0], fs(4.6), S(lang), border=1)
        pdf.cell(W * (1 - widths[0]), fs(4.6), S(V.T[out]["missing"].format(lang=lang)), border=1)
        pdf.ln()
    rd = compact.get("readers", {})
    if rd.get("top_countries"):
        pdf.set_font("DV", "", fs(6.8))
        pdf.set_text_color(80)
        line = rd["note"] + f" {rd['month']}: " + "; ".join(f"{l} — {v}" for l, v in rd["top_countries"].items())
        pdf.multi_cell(W, fs(3.4), S(line), new_x="LMARGIN", new_y="NEXT", align="L")
        pdf.set_text_color(0)
    pdf.ln(1.5)

    # basket
    b = compact["basket"]
    pdf.set_font("DV", "B", fs(8))
    pdf.cell(W, fs(4.5), S(t["basket"]), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DV", "", fs(7.5))
    txt = ", ".join(b["shown"]) + (f" + {t['more'].format(n=b['more'])}" if b["more"] else "")
    pdf.multi_cell(W, fs(3.8), S(txt), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

    # notes: must_mention + assumptions + limitations
    pdf.set_font("DV", "B", fs(8))
    pdf.cell(W, fs(4.5), S(t["notes"]), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DV", "", fs(6.8))
    notes = list(compact.get("must_mention", []))
    if not drop_assumptions:
        notes += [f"{t['assump']}: " + a for a in compact.get("assumptions", [])]
    notes += [f"{t['limits']}: " + " ".join(compact.get("limitations", []))]
    if _Safe.replaced:
        notes.append(t["replaced"])
    for n in notes:
        pdf.multi_cell(W, fs(3.3), S("• " + n), new_x="LMARGIN", new_y="NEXT", align="L")

    # footer
    pdf.ln(1)
    pdf.set_font("DV", "", fs(6.3))
    pdf.set_text_color(110)
    pdf.multi_cell(W, fs(3.2), S(t["footer"].format(v=METHODOLOGY_VERSION, s=compact["study"], ver=compact["version"],
                                                   d=dt.date.today().isoformat())), new_x="LMARGIN", new_y="NEXT")
    return pdf


def make_pdf(compact: dict, analysis: dict, summary: str, title: str, out: str, path: pathlib.Path) -> dict:
    for scale, drop in [(1.0, False), (0.92, False), (0.85, False), (0.85, True), (0.78, True)]:
        _Safe.replaced = False
        pdf = _build(compact, analysis, summary, title, out, scale, drop)
        if pdf.pages_count == 1:
            pdf.output(str(path))
            return {"scale": scale, "assumptions_dropped": drop}
    raise WitError("report_overflow", "The report does not fit on one page.",
                   "Shorten --summary to 2-4 sentences (or compare fewer languages) and run `report` again.")
