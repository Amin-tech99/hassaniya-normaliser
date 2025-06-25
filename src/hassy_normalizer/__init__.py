"""Hassaniya Arabic text normalizer.

A Python library for normalizing Hassaniya Arabic text with variant handling
and letter rules.
"""

__version__ = "0.1.0"

from .normalizer import normalize_text, normalize_word, iter_unknown, get_stats
from .diff import word_diff, word_diff_simple, format_diff_html, get_change_stats

# Alias get_stats to get_normalizer_stats for compatibility
get_normalizer_stats = get_stats

__all__ = [
    "normalize_text",
    "normalize_word", 
    "iter_unknown",
    "get_stats",
    "get_normalizer_stats",
    "word_diff",
    "word_diff_simple",
    "format_diff_html",
    "get_change_stats",
    "__version__",
]