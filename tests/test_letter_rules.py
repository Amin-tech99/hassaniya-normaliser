from hassy_normalizer import normalize_word

def test_exception_preserves_qaf():
    # pick a *real* qaf-exception from the JSON file
    assert normalize_word("القضية") == "القضيه"  # ق kept, ة→ه applied

def test_regular_word_changes_both():
    assert normalize_word("قناعة") == "كناعه"