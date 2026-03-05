from unittest.mock import patch

from hassy_normalizer import normalize_word


def test_exception_preserves_qaf():
    # Keep qaf for exception words while still applying taa->haa at the end.
    with patch(
        "hassy_normalizer.rules._get_exceptions",
        return_value={"\u0627\u0644\u0642\u0636\u064a\u0629", "\u0627\u0644\u0642\u0636\u064a\u0647"},
    ):
        assert normalize_word("\u0627\u0644\u0642\u0636\u064a\u0629") == "\u0627\u0644\u0642\u0636\u064a\u0647"


def test_regular_word_changes_both():
    with patch("hassy_normalizer.rules._get_exceptions", return_value=set()):
        assert normalize_word("\u0642\u0631\u0627\u0621\u0629") == "\u0643\u0631\u0627\u0621\u0647"
