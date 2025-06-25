"""Hassaniya Arabic text normalizer.

A Python library for normalizing Hassaniya Arabic text with variant handling
and letter rules.
"""

__version__ = "0.1.0"

from .normalizer import normalize_text, normalize_word, iter_unknown, get_stats
from .diff import word_diff

__all__ = [
    "normalize_text",
    "normalize_word", 
    "iter_unknown",
    "get_stats",
    "word_diff",
    "__version__",
]