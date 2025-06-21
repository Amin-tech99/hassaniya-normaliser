"""Main normalization pipeline for Hassaniya Arabic text.

Provides the core normalization functionality with variant lookup
followed by letter rules application.
"""

import logging
import re
import threading
from typing import Dict, Iterator, Set

from .data_loader import load_variants
from .rules import normalize_word_with_rules

logger = logging.getLogger(__name__)

# Thread-safe tracking of unknown variants
_unknown_variants: Set[str] = set()
_unknown_lock = threading.RLock()

# Word tokenization pattern - keeps punctuation separate
_WORD_PATTERN = re.compile(r'\b\w+\b|[^\w\s]', re.UNICODE)


def _get_variants_map() -> Dict[str, str]:
    """Get variants mapping with error handling.
    
    Returns:
        Dictionary mapping variants to canonical forms
    """
    try:
        return load_variants()
    except Exception as e:
        logger.error(f"Failed to load variants: {e}")
        return {}  # Fallback to empty mapping


def _track_unknown_variant(word: str) -> None:
    """Thread-safely track an unknown variant.
    
    Args:
        word: Unknown variant word to track
    """
    with _unknown_lock:
        _unknown_variants.add(word)


def normalize_word(word: str) -> str:
    """Normalize a single word using the full pipeline.
    
    Pipeline order:
    1. Variant lookup - check if word has a known canonical form
    2. Letter rules - apply گ/ق→ك and ة→ه transformations
    
    Args:
        word: Input word to normalize
        
    Returns:
        Normalized word
    """
    if not word or not word.strip():
        return word
    
    original_word = word.strip()
    
    # Step 1: Variant lookup
    variants_map = _get_variants_map()
    if original_word in variants_map:
        canonical = variants_map[original_word]
        logger.debug(f"Variant lookup: '{original_word}' -> '{canonical}'")
        return canonical
    
    # Step 2: Apply letter rules
    normalized = normalize_word_with_rules(original_word)
    
    # Track if this was an unknown variant (not in our mapping)
    if normalized != original_word:
        # Only track if the change came from letter rules, not variant lookup
        if original_word not in variants_map:
            _track_unknown_variant(original_word)
    
    return normalized


def normalize_text(text: str) -> str:
    """Normalize a full text string.
    
    Tokenizes the text and applies normalization to each word while
    preserving punctuation and whitespace.
    
    Args:
        text: Input text to normalize
        
    Returns:
        Normalized text with original formatting preserved
    """
    if not text:
        return text
    
    # Find all tokens (words and punctuation)
    tokens = _WORD_PATTERN.findall(text)
    
    # Normalize each word token
    normalized_tokens = []
    for token in tokens:
        if re.match(r'\w+', token, re.UNICODE):  # It's a word
            normalized_tokens.append(normalize_word(token))
        else:  # It's punctuation or other
            normalized_tokens.append(token)
    
    # Reconstruct text with original spacing
    result = []
    token_iter = iter(normalized_tokens)
    
    # Use regex to split and preserve whitespace
    parts = re.split(r'(\s+)', text)
    token_index = 0
    
    for part in parts:
        if part.isspace():
            result.append(part)  # Preserve whitespace
        else:
            # Replace words in this part
            words_in_part = _WORD_PATTERN.findall(part)
            if words_in_part:
                part_result = part
                for word in words_in_part:
                    if token_index < len(normalized_tokens):
                        normalized_word = normalized_tokens[token_index]
                        part_result = part_result.replace(word, normalized_word, 1)
                        token_index += 1
                result.append(part_result)
            else:
                result.append(part)
    
    return ''.join(result)


def iter_unknown() -> Iterator[str]:
    """Iterate over unknown variants encountered during normalization.
    
    Yields:
        Unknown variant words that were normalized using letter rules
        but don't have explicit variant mappings
    """
    with _unknown_lock:
        # Return a copy to avoid modification during iteration
        unknown_copy = _unknown_variants.copy()
    
    for variant in sorted(unknown_copy):
        yield variant


def get_unknown_count() -> int:
    """Get the count of unknown variants encountered.
    
    Returns:
        Number of unique unknown variants
    """
    with _unknown_lock:
        return len(_unknown_variants)


def clear_unknown() -> None:
    """Clear the set of tracked unknown variants.
    
    Useful for testing or when starting fresh tracking.
    """
    with _unknown_lock:
        _unknown_variants.clear()
    logger.info("Unknown variants tracking cleared")


def get_stats() -> Dict[str, int]:
    """Get normalization statistics.
    
    Returns:
        Dictionary with counts of variants and exceptions loaded,
        and unknown variants encountered
    """
    variants_map = _get_variants_map()
    
    # Import here to avoid circular imports
    from .rules import get_exceptions_count
    
    return {
        "variants_loaded": len(variants_map),
        "exceptions_loaded": get_exceptions_count(),
        "unknown_variants": get_unknown_count(),
    }