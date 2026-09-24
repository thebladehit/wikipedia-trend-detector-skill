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
