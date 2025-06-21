"""Tests for diff module."""

import pytest
from unittest.mock import patch

from hassy_normalizer.diff import (
    word_diff,
    word_diff_simple,
    format_diff_html,
    format_diff_ansi,
    get_change_stats,
    _tokenize_text,
    _is_word_token
)


class TestTokenization:
    """Test text tokenization functionality."""
    
    def test_tokenize_simple_text(self):
        """Test tokenization of simple text."""
        text = "hello world"
        tokens = _tokenize_text(text)
        assert tokens == ["hello", " ", "world"]
    
    def test_tokenize_with_punctuation(self):
        """Test tokenization with punctuation."""
        text = "hello, world!"
        tokens = _tokenize_text(text)
        assert tokens == ["hello", ",", " ", "world", "!"]
    
    def test_tokenize_arabic_text(self):
        """Test tokenization of Arabic text."""
        text = "قال الرجل"
        tokens = _tokenize_text(text)
        assert tokens == ["قال", " ", "الرجل"]
    
    def test_tokenize_mixed_content(self):
        """Test tokenization of mixed content."""
        text = "قال: hello!"
        tokens = _tokenize_text(text)
        assert tokens == ["قال", ":", " ", "hello", "!"]
    
    def test_tokenize_empty_text(self):
        """Test tokenization of empty text."""
        assert _tokenize_text("") == []
        assert _tokenize_text("   ") == ["   "]
    
    def test_is_word_token(self):
        """Test word token identification."""
        assert _is_word_token("hello") is True
        assert _is_word_token("قال") is True
        assert _is_word_token("hello123") is True
        assert _is_word_token(",") is False
        assert _is_word_token("!") is False
        assert _is_word_token(" ") is False
        assert _is_word_token("") is False


class TestWordDiff:
    """Test word-level diff functionality."""
    
    def test_word_diff_no_changes(self):
        """Test diff when no changes occur."""
        original = "hello world"
        normalized = "hello world"
        
        diff = word_diff(original, normalized)
        
        expected = [
            {"word": "hello", "changed": False},
            {"word": " ", "changed": False},
            {"word": "world", "changed": False}
        ]
        assert diff == expected
    
    def test_word_diff_with_changes(self):
        """Test diff when changes occur."""
        original = "قال الرجل"
        normalized = "كال الرجل"
        
        diff = word_diff(original, normalized)
        
        expected = [
            {"word": "كال", "changed": True},
            {"word": " ", "changed": False},
            {"word": "الرجل", "changed": False}
        ]
        assert diff == expected
    
    def test_word_diff_punctuation_unchanged(self):
        """Test that punctuation changes are not marked as changed."""
        original = "hello, world!"
        normalized = "hello, world!"
        
        diff = word_diff(original, normalized)
        
        # All should be unchanged
        for entry in diff:
            assert entry["changed"] is False
    
    def test_word_diff_simple_function(self):
        """Test word_diff_simple function."""
        with patch('hassy_normalizer.diff.normalize_word') as mock_normalize:
            mock_normalize.side_effect = lambda x: x.replace('ق', 'ك')
            
            text = "قال الرجل"
            diff = word_diff_simple(text)
            
            expected = [
                {"word": "كال", "changed": True},
                {"word": " ", "changed": False},
                {"word": "الرجل", "changed": False}
            ]
            assert diff == expected
    
    def test_word_diff_empty_text(self):
        """Test diff with empty text."""
        assert word_diff("") == []
        assert word_diff_simple("") == []
    
    def test_word_diff_auto_normalize(self):
        """Test that word_diff auto-normalizes when normalized_text is None."""
        with patch('hassy_normalizer.diff.normalize_text') as mock_normalize:
            mock_normalize.return_value = "كال"
            
            diff = word_diff("قال")
            
            mock_normalize.assert_called_once_with("قال")
            assert len(diff) > 0


class TestDiffFormatting:
    """Test diff formatting functionality."""
    
    def test_format_diff_html_no_changes(self):
        """Test HTML formatting with no changes."""
        diff_entries = [
            {"word": "hello", "changed": False},
            {"word": " ", "changed": False},
            {"word": "world", "changed": False}
        ]
        
        html = format_diff_html(diff_entries)
        assert html == "hello world"
    
    def test_format_diff_html_with_changes(self):
        """Test HTML formatting with changes."""
        diff_entries = [
            {"word": "كال", "changed": True},
            {"word": " ", "changed": False},
            {"word": "الرجل", "changed": False}
        ]
        
        html = format_diff_html(diff_entries)
        expected = '<mark class="change">كال</mark> الرجل'
        assert html == expected
    
    def test_format_diff_html_escaping(self):
        """Test HTML escaping in diff formatting."""
        diff_entries = [
            {"word": "<script>", "changed": True},
            {"word": "&", "changed": False},
            {"word": '"test"', "changed": True}
        ]
        
        html = format_diff_html(diff_entries)
        expected = '<mark class="change">&lt;script&gt;</mark>&amp;<mark class="change">&quot;test&quot;</mark>'
        assert html == expected
    
    def test_format_diff_ansi_with_color(self):
        """Test ANSI formatting with color."""
        diff_entries = [
            {"word": "كال", "changed": True},
            {"word": " ", "changed": False},
            {"word": "الرجل", "changed": False}
        ]
        
        ansi = format_diff_ansi(diff_entries, use_color=True)
        assert "\033[43m" in ansi  # Yellow background
        assert "\033[0m" in ansi   # Reset
        assert "كال" in ansi
        assert "الرجل" in ansi
    
    def test_format_diff_ansi_no_color(self):
        """Test ANSI formatting without color."""
        diff_entries = [
            {"word": "كال", "changed": True},
            {"word": " ", "changed": False},
            {"word": "الرجل", "changed": False}
        ]
        
        ansi = format_diff_ansi(diff_entries, use_color=False)
        assert "\033[" not in ansi  # No ANSI codes
        assert ansi == "كال الرجل"


class TestChangeStats:
    """Test change statistics functionality."""
    
    def test_get_change_stats_no_changes(self):
        """Test stats when no changes occur."""
        diff_entries = [
            {"word": "hello", "changed": False},
            {"word": " ", "changed": False},
            {"word": "world", "changed": False}
        ]
        
        stats = get_change_stats(diff_entries)
        
        expected = {
            "total_words": 2,
            "changed_words": 0,
            "unchanged_words": 2,
            "change_percentage": 0.0
        }
        assert stats == expected
    
    def test_get_change_stats_with_changes(self):
        """Test stats when changes occur."""
        diff_entries = [
            {"word": "كال", "changed": True},
            {"word": " ", "changed": False},
            {"word": "الرجل", "changed": False},
            {"word": " ", "changed": False},
            {"word": "كبير", "changed": True}
        ]
        
        stats = get_change_stats(diff_entries)
        
        expected = {
            "total_words": 3,
            "changed_words": 2,
            "unchanged_words": 1,
            "change_percentage": 66.7
        }
        assert stats == expected
    
    def test_get_change_stats_only_punctuation(self):
        """Test stats with only punctuation."""
        diff_entries = [
            {"word": "!", "changed": False},
            {"word": " ", "changed": False},
            {"word": "?", "changed": True}  # Even if marked changed, shouldn't count
        ]
        
        stats = get_change_stats(diff_entries)
        
        expected = {
            "total_words": 0,
            "changed_words": 0,
            "unchanged_words": 0,
            "change_percentage": 0.0
        }
        assert stats == expected
    
    def test_get_change_stats_empty_diff(self):
        """Test stats with empty diff."""
        stats = get_change_stats([])
        
        expected = {
            "total_words": 0,
            "changed_words": 0,
            "unchanged_words": 0,
            "change_percentage": 0.0
        }
        assert stats == expected
    
    def test_get_change_stats_percentage_rounding(self):
        """Test percentage rounding in stats."""
        # Create a scenario that results in 33.333...%
        diff_entries = [
            {"word": "word1", "changed": True},
            {"word": "word2", "changed": False},
            {"word": "word3", "changed": False}
        ]
        
        stats = get_change_stats(diff_entries)
        assert stats["change_percentage"] == 33.3  # Should be rounded to 1 decimal


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_diff_with_unicode_normalization(self):
        """Test diff with Unicode normalization issues."""
        # Test with different Unicode representations
        original = "café"  # é as single character
        normalized = "cafe\u0301"  # é as e + combining accent
        
        diff = word_diff(original, normalized)
        # Should handle Unicode differences gracefully
        assert len(diff) > 0
    
    def test_diff_with_very_long_text(self):
        """Test diff with very long text."""
        long_text = "word " * 1000
        
        with patch('hassy_normalizer.diff.normalize_text') as mock_normalize:
            mock_normalize.return_value = long_text.replace('word', 'كلمة')
            
            diff = word_diff(long_text)
            
            # Should handle long text without issues
            assert len(diff) > 0
            # Check that all 'word' tokens are marked as changed
            word_entries = [entry for entry in diff if entry["word"] == "كلمة"]
            assert len(word_entries) == 1000
            assert all(entry["changed"] for entry in word_entries)
    
    def test_diff_with_mixed_directions(self):
        """Test diff with mixed text directions (LTR/RTL)."""
        text = "hello قال world"
        
        with patch('hassy_normalizer.diff.normalize_word') as mock_normalize:
            mock_normalize.side_effect = lambda x: x.replace('ق', 'ك')
            
            diff = word_diff_simple(text)
            
            # Should handle mixed directions correctly
            changed_entries = [entry for entry in diff if entry["changed"]]
            assert len(changed_entries) == 1
            assert changed_entries[0]["word"] == "كال"
    
    def test_diff_with_special_whitespace(self):
        """Test diff with various types of whitespace."""
        text = "word1\t\nword2\r\nword3"
        
        tokens = _tokenize_text(text)
        
        # Should preserve all whitespace types
        assert "\t\n" in tokens
        assert "\r\n" in tokens
    
    def test_format_diff_html_with_empty_words(self):
        """Test HTML formatting with empty word entries."""
        diff_entries = [
            {"word": "", "changed": False},
            {"word": "test", "changed": True},
            {"word": "", "changed": True}
        ]
        
        html = format_diff_html(diff_entries)
        expected = '<mark class="change">test</mark><mark class="change"></mark>'
        assert html == expected


if __name__ == '__main__':
    pytest.main([__file__])