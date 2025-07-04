"""Letter-level normalisation rules.

Guarantees:
* Exceptions are respected (القضية stays القضية).
* Hot-reloads if the JSON file changes.
"""

from __future__ import annotations

import json
import logging
import threading
from functools import lru_cache
from time import time
from typing import Optional, Set

from importlib import resources  # std-lib; works in zip/pyinstaller

_LOG = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Locate data file INSIDE the package, independent of working directory
# ---------------------------------------------------------------------------
try:
    _EXC_FILE = (
        resources.files("hassy_normalizer.data")
        .joinpath("exception_words_g_q.json")
        .resolve()
    )
except FileNotFoundError as exc:
    raise RuntimeError(
        "exception_words_g_q.json not found inside hassy_normalizer.data package"
    ) from exc
# ---------------------------------------------------------------------------
# Thread-safe lazy loader with mtime check
# ---------------------------------------------------------------------------
_exceptions: Set[str] = set()
_exceptions_mtime: float = 0.0
_lock = threading.Lock()


def _load_exception_words() -> Set[str]:
    with _EXC_FILE.open(encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list) or not all(isinstance(x, str) for x in data):
        raise ValueError("exception_words_g_q.json must be a JSON array of strings")
    _LOG.info("Loaded %d exception words", len(data))
    return set(data)


def _expand_taa_haa_variants(base_exceptions: Set[str]) -> Set[str]:
    """Expand exception words to include both ة and ه variants.
    
    For each word ending in ة or ه, automatically add the other variant
    to ensure exceptions work regardless of which form is used.
    
    Args:
        base_exceptions: Original set of exception words
        
    Returns:
        Expanded set including both ة and ه variants
    """
    expanded = set(base_exceptions)
    
    for word in base_exceptions:
        if word.endswith('ة'):
            # Add ه variant: القضية -> القضيه
            variant = word[:-1] + 'ه'
            expanded.add(variant)
        elif word.endswith('ه'):
            # Add ة variant: القضيه -> القضية
            variant = word[:-1] + 'ة'
            expanded.add(variant)
    
    _LOG.info("Expanded %d base exceptions to %d total exceptions (including ة/ه variants)", 
              len(base_exceptions), len(expanded))
    return expanded


def load_exceptions() -> Set[str]:
    """Load exception words from JSON file.
    
    This function is provided for testing compatibility.
    
    Returns:
        Set of exception words
    """
    return _load_exception_words()


def _get_exceptions() -> Set[str]:
    global _exceptions_mtime, _exceptions
    with _lock:
        try:
            mtime = _EXC_FILE.stat().st_mtime
            # Reload if file changed OR if forced reload (mtime == 0)
            if mtime > _exceptions_mtime or _exceptions_mtime == 0.0:
                base_exceptions = load_exceptions()  # Use load_exceptions for testability
                # Automatically add ة/ه variants for each exception word
                _exceptions = _expand_taa_haa_variants(base_exceptions)
                _exceptions_mtime = mtime or time()
                apply_letter_rules.cache_clear()
        except Exception as e:
            _LOG.warning("Failed to load exceptions: %s", e)
            _exceptions = set()
            _exceptions_mtime = time()
    return _exceptions


@lru_cache(maxsize=100_000)
def apply_letter_rules(word: str, _hash: Optional[int] = None) -> str:
    """
    Apply letter-level normalisation in two ordered steps:

    1. گ/ق → ك   (skip if word is in the exceptions list)
    2. Final taa-marbuuṭa (ة) → haa (ه)  — always applied last (but respect exceptions)
    """
    exceptions = _get_exceptions()
    original_word = word

    # Step 1  (protected by exceptions)
    if word not in exceptions:
        word = word.replace("گ", "ك").replace("ق", "ك")

    # Step 2 (conditional - respect exceptions for both original and converted forms)
    if word.endswith("ة"):
        # Check if either the original word or the ه-form is in exceptions
        haa_form = word[:-1] + "ه"
        if original_word not in exceptions and haa_form not in exceptions:
            word = haa_form
        # If either form is in exceptions, keep the current form (which may have had ق→ك applied)

    return word


def normalize_word_with_rules(word: str) -> str:
    """Normalize a single word using letter rules.
    
    Args:
        word: Word to normalize
        
    Returns:
        Normalized word
    """
    if not word or not word.strip():
        return word
    
    return apply_letter_rules(word.strip())


def is_exception_word(word: str) -> bool:
    """Check if a word is in the exceptions list.
    
    Args:
        word: Word to check
        
    Returns:
        True if word is an exception
    """
    exceptions = _get_exceptions()
    return word in exceptions


def get_exceptions_count() -> int:
    """Get the number of loaded exception words.
    
    Returns:
        Count of exception words
    """
    exceptions = _get_exceptions()
    return len(exceptions)


def clear_rules_cache() -> None:
    """Clear the letter rules cache.
    
    Useful for testing or when rules need to be recomputed.
    """
    global _exceptions_mtime, _exceptions
    with _lock:
        _exceptions_mtime = 0.0  # Force reload on next access
        _exceptions = set()  # Clear cached exceptions
        apply_letter_rules.cache_clear()
    _LOG.info("Letter rules cache cleared")


def reload_exceptions() -> None:
    """Force reload of exception words from file.
    
    Useful for testing or when the exception file has been updated.
    """
    global _exceptions_mtime, _exceptions
    with _lock:
        _exceptions_mtime = 0.0  # Force reload on next access
        _exceptions = set()  # Clear cached exceptions
        apply_letter_rules.cache_clear()
    _LOG.info("Exception words will be reloaded on next access")


# Startup test - runs once
if not _get_exceptions():
    _LOG.warning("Exception list is EMPTY – check that the JSON file is populated")