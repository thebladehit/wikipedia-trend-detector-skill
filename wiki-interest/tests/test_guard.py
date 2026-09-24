from wikitrends import guard

COMPACT = {
    "verdicts": {"uk": "uk: інтерес падає — частка -36% …; 1 з 12 місяців; довіра: висока (9/10)",
                 "tr": "tr: напрям неясний: частка -11%; 3 з 12"},
    "table_md": "| uk | -36% | -52% |",
    "_directions": {"uk": "declining", "tr": "unclear"},
}


def test_numbers_from_analysis_pass():
    assert guard.check("У uk частка теми впала на 36%, а перегляди на 52%.", COMPACT)["status"] == "ok"


def test_rounding_tolerance_and_decimal_comma():
    assert guard.check("Частка впала на 35,6%.", COMPACT)["status"] == "ok"


def test_invented_number_rejected():
    r = guard.check("У tr інтерес виріс на 47%.", COMPACT)
    assert r["status"] == "rejected" and "47%" in r["problems"][0]


def test_willingness_to_pay_rejected_unless_negated():
    assert guard.check("Українці готові платити за курс.", COMPACT)["status"] == "rejected"
    assert guard.check("Це не означає, що люди готові платити.", COMPACT)["status"] == "ok"


def test_direction_contradiction_only_warns():
    r = guard.check("Інтерес у турецькій Вікіпедії зростає.", COMPACT)
    assert r["status"] == "ok" and r["warnings"]


def test_years_and_qids_ignored():
    assert guard.check("За 2025 рік у uk (Q333) частка -36%.", COMPACT)["status"] == "ok"


def test_final_message_contains_only_analysis_content():
    from wikitrends.report import final_message
    compact = {**COMPACT, "ranking": [{"rank": 1, "lang": "vi", "why": "місце 1: частка теми -1%"}],
               "trust": {"vi": "Довіра середня (7/10): непослідовно."},
               "must_mention": ["Тему виміряно кошиком з 9 статей."],
               "readers": {"top_countries": {"uk": "UA 65%", "pt": "BR 74%"}},
               "limitations": ["Перегляди ≠ готовність платити."]}
    msg = final_message(compact, "Найвище vi.", "/tmp/r.pdf", "uk")
    assert "/tmp/r.pdf" in msg and "Довіра середня" in msg and "кошиком" in msg and "BR 74%" in msg
    assert guard.check(msg, compact)["status"] == "ok"


def test_not_equal_sign_counts_as_negation():
    assert guard.check("Перегляди ≠ готовність платити.", COMPACT)["status"] == "ok"
