"""Tests for de-elongation add-on."""

from hassy_normalizer import normalizer as nm


def test_collapse_repeated_letters():
    assert nm.normalize_word("معاااااافيه") == "معافيه"
