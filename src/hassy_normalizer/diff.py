"""Text difference utilities for Hassaniya normalizer.

Provides word-level diff functionality with precise tokenization
to highlight changes between original and normalized text.
"""

import re
from typing import Dict, List, TypedDict

from .normalizer import normalize_word


class WordDiff(TypedDict):
    """Type definition for word diff entry."""
    word: str
    changed: bool


# Tokenization pattern that keeps punctuation separate
_TOKEN_PATTERN = re.compile(r'\b\w+\b|[^\w\s]|\s+', re.UNICODE)


def _tokenize_text(text: str) -> List[str]:
    """Tokenize text into words, punctuation, and whitespace.
    
    Args:
        text: Input text to tokenize
        
    Returns:
        List of tokens preserving all text elements
    """
    if not text:
        return []
    
    return _TOKEN_PATTERN.findall(text)


def _is_word_token(token: str) -> bool:
    """Check if a token is a word (not punctuation or whitespace).
    
    Args:
        token: Token to check
        
    Returns:
        True if token is a word
    """
    return bool(re.match(r'\w+', token, re.UNICODE))


def word_diff(original_text: str, normalized_text: str = None) -> List[WordDiff]:
    """Generate word-level diff between original and normalized text.
    
    Args:
        original_text: Original text
        normalized_text: Normalized text (if None, will normalize original_text)
        
    Returns:
        List of WordDiff entries showing each token and whether it changed
    """
    if not original_text:
        return []
    
    # Normalize if not provided
    if normalized_text is None:
        from .normalizer import normalize_text
        normalized_text = normalize_text(original_text)
    
    # Tokenize both texts
    original_tokens = _tokenize_text(original_text)
    normalized_tokens = _tokenize_text(normalized_text)
    
    # Create diff entries
    diff_entries: List[WordDiff] = []
    
    # Handle case where token counts might differ (shouldn't happen with our normalizer)
    max_tokens = max(len(original_tokens), len(normalized_tokens))
    
    for i in range(max_tokens):
        original_token = original_tokens[i] if i < len(original_tokens) else ""
        normalized_token = normalized_tokens[i] if i < len(normalized_tokens) else ""
        
        # For display, use the normalized token (or original if normalized is empty)
        display_token = normalized_token if normalized_token else original_token
        
        # Check if this token changed
        changed = original_token != normalized_token
        
        # Only mark as changed if it's actually a word (not whitespace/punctuation)
        if changed and not _is_word_token(original_token):
            changed = False
        
        diff_entries.append(WordDiff(word=display_token, changed=changed))
    
    return diff_entries


def word_diff_simple(text: str) -> List[WordDiff]:
    """Generate word-level diff by comparing each word individually.
    
    This is a simpler approach that normalizes each word separately
    and compares them, which may be more accurate for highlighting
    individual word changes.
    
    Args:
        text: Original text to analyze
        
    Returns:
        List of WordDiff entries showing each token and whether it changed
    """
    if not text:
        return []
    
    tokens = _tokenize_text(text)
    diff_entries: List[WordDiff] = []
    
    for token in tokens:
        if _is_word_token(token):
            # Normalize this word
            normalized_token = normalize_word(token)
            changed = token != normalized_token
            # Use normalized version for display
            diff_entries.append(WordDiff(word=normalized_token, changed=changed))
        else:
            # Keep punctuation and whitespace as-is
            diff_entries.append(WordDiff(word=token, changed=False))
    
    return diff_entries


def format_diff_html(diff_entries: List[WordDiff]) -> str:
    """Format diff entries as HTML with highlighting.
    
    Args:
        diff_entries: List of WordDiff entries
        
    Returns:
        HTML string with <mark class="change"> tags around changed words
    """
    html_parts = []
    
    for entry in diff_entries:
        word = entry["word"]
        # Escape HTML characters
        escaped_word = (
            word.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
        )
        
        if entry["changed"]:
            html_parts.append(f'<mark class="change">{escaped_word}</mark>')
        else:
            html_parts.append(escaped_word)
    
    return "".join(html_parts)


def format_diff_ansi(diff_entries: List[WordDiff], use_color: bool = True) -> str:
    """Format diff entries with ANSI color codes.
    
    Args:
        diff_entries: List of WordDiff entries
        use_color: Whether to use ANSI color codes
        
    Returns:
        String with ANSI color codes for changed words
    """
    if not use_color:
        return "".join(entry["word"] for entry in diff_entries)
    
    # ANSI color codes
    YELLOW_BG = "\033[43m"  # Yellow background
    RESET = "\033[0m"       # Reset formatting
    
    parts = []
    for entry in diff_entries:
        word = entry["word"]
        if entry["changed"]:
            parts.append(f"{YELLOW_BG}{word}{RESET}")
        else:
            parts.append(word)
    
    return "".join(parts)


def get_change_stats(diff_entries: List[WordDiff]) -> Dict[str, int]:
    """Get statistics about changes in diff entries.
    
    Args:
        diff_entries: List of WordDiff entries
        
    Returns:
        Dictionary with word count and change statistics
    """
    total_words = 0
    changed_words = 0
    
    for entry in diff_entries:
        if _is_word_token(entry["word"]):
            total_words += 1
            if entry["changed"]:
                changed_words += 1
    
    return {
        "total_words": total_words,
        "changed_words": changed_words,
        "unchanged_words": total_words - changed_words,
        "change_percentage": round((changed_words / total_words * 100) if total_words > 0 else 0, 1),
    }