"""Tests for letter rules module."""

import pytest
import threading
import time
from unittest.mock import patch, MagicMock

from hassy_normalizer.rules import (
    apply_letter_rules,
    normalize_word_with_rules,
    is_exception_word,
    get_exceptions_count,
    reload_exceptions,
    clear_rules_cache,
    _get_exceptions
)


class TestLetterRules:
    """Test letter transformation rules."""
    
    def test_gaf_qaf_to_kaf_replacement(self):
        """Test گ/ق → ك replacement."""
        # Mock empty exceptions
        with patch('hassy_normalizer.rules._get_exceptions', return_value=set()):
            assert apply_letter_rules('قال', 0) == 'كال'
            assert apply_letter_rules('گال', 0) == 'كال'
            assert apply_letter_rules('قلب', 0) == 'كلب'
            assert apply_letter_rules('گلب', 0) == 'كلب'
    
    def test_taa_marbuta_to_haa_replacement(self):
        """Test ة → ه tail fix."""
        with patch('hassy_normalizer.rules._get_exceptions', return_value=set()):
            assert apply_letter_rules('مدرسة', 0) == 'مدرسه'
            assert apply_letter_rules('كتابة', 0) == 'كتابه'
            # Should only replace at end
            assert apply_letter_rules('ةمدرس', 0) == 'ةمدرس'
    
    def test_combined_rules(self):
        """Test multiple rules applied together."""
        with patch('hassy_normalizer.rules._get_exceptions', return_value=set()):
            assert apply_letter_rules('قراءة', 0) == 'كراءه'
            assert apply_letter_rules('گتابة', 0) == 'كتابه'
    
    def test_exception_words_skipped(self):
        """Test that exception words are not transformed."""
        exceptions = {'قال', 'قلب'}
        with patch('hassy_normalizer.rules._get_exceptions', return_value=exceptions):
            exc_hash = hash(frozenset(exceptions))
            assert apply_letter_rules('قال', exc_hash) == 'قال'  # Exception
            assert apply_letter_rules('قلب', exc_hash) == 'قلب'  # Exception
            assert apply_letter_rules('قرأ', exc_hash) == 'كرأ'  # Not exception
    
    def test_empty_and_whitespace_words(self):
        """Test handling of empty and whitespace-only words."""
        assert normalize_word_with_rules('') == ''
        assert normalize_word_with_rules('   ') == '   '
        assert normalize_word_with_rules('\t\n') == '\t\n'
    
    def test_normalize_word_with_rules(self):
        """Test the main normalize_word_with_rules function."""
        with patch('hassy_normalizer.rules._get_exceptions', return_value=set()):
            assert normalize_word_with_rules('قال') == 'كال'
            assert normalize_word_with_rules('  قال  ') == 'كال'  # Strips whitespace
    
    def test_is_exception_word(self):
        """Test exception word checking."""
        exceptions = {'قال', 'قلب'}
        with patch('hassy_normalizer.rules._get_exceptions', return_value=exceptions):
            assert is_exception_word('قال') is True
            assert is_exception_word('قلب') is True
            assert is_exception_word('قرأ') is False
    
    def test_get_exceptions_count(self):
        """Test getting exception count."""
        exceptions = {'قال', 'قلب', 'قرأ'}
        with patch('hassy_normalizer.rules._get_exceptions', return_value=exceptions):
            assert get_exceptions_count() == 3
    
    def test_cache_functionality(self):
        """Test that caching works correctly."""
        exceptions = {'قال'}
        
        with patch('hassy_normalizer.rules._get_exceptions', return_value=exceptions) as mock_get:
            exc_hash = hash(frozenset(exceptions))
            
            # First call
            result1 = apply_letter_rules('قرأ', exc_hash)
            # Second call with same parameters should use cache
            result2 = apply_letter_rules('قرأ', exc_hash)
            
            assert result1 == result2 == 'كرأ'
            # _get_exceptions should be called for each normalize_word_with_rules call
            # but apply_letter_rules should be cached
    
    def test_cache_invalidation_on_reload(self):
        """Test that cache is cleared when exceptions are reloaded."""
        # Clear cache first
        clear_rules_cache()
        
        with patch('hassy_normalizer.rules.load_exceptions') as mock_load:
            mock_load.return_value = {'قال'}
            
            # Load exceptions
            _get_exceptions()
            
            # Reload should clear cache
            reload_exceptions()
            
            # Next call should reload
            _get_exceptions()
            
            # Should have been called twice (initial + after reload)
            assert mock_load.call_count >= 2


class TestThreadSafety:
    """Test thread safety of rules module."""
    
    def test_concurrent_normalization(self):
        """Test that concurrent normalization works correctly."""
        exceptions = {'قال'}
        results = []
        errors = []
        
        def normalize_worker(word_num):
            try:
                with patch('hassy_normalizer.rules._get_exceptions', return_value=exceptions):
                    result = normalize_word_with_rules(f'قرأ{word_num}')
                    results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=normalize_worker, args=(i,))
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=5.0)
        
        # Check results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 10
        
        # All results should follow the same pattern
        for i, result in enumerate(results):
            expected = f'كرأ{i}'
            assert result == expected
    
    def test_concurrent_exception_reload(self):
        """Test that exception reloading is thread-safe."""
        reload_count = 0
        errors = []
        
        def reload_worker():
            nonlocal reload_count
            try:
                with patch('hassy_normalizer.rules.load_exceptions', return_value={'test'}):
                    reload_exceptions()
                    reload_count += 1
                    time.sleep(0.01)  # Small delay to increase chance of race conditions
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads that reload exceptions
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=reload_worker)
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=5.0)
        
        # Check that no errors occurred
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert reload_count == 5


class TestErrorHandling:
    """Test error handling in rules module."""
    
    def test_exception_loading_failure(self):
        """Test handling of exception loading failures."""
        with patch('hassy_normalizer.rules.load_exceptions', side_effect=Exception("Load failed")):
            # Should fallback to empty set
            exceptions = _get_exceptions()
            assert exceptions == set()
    
    def test_normalize_with_load_failure(self):
        """Test normalization continues even if exception loading fails."""
        with patch('hassy_normalizer.rules.load_exceptions', side_effect=Exception("Load failed")):
            # Should still apply rules, just without exceptions
            result = normalize_word_with_rules('قال')
            assert result == 'كال'
    
    def test_clear_cache_safety(self):
        """Test that clearing cache is safe to call multiple times."""
        # Should not raise any exceptions
        clear_rules_cache()
        clear_rules_cache()
        clear_rules_cache()


class TestEdgeCases:
    """Test edge cases and special scenarios."""
    
    def test_unicode_handling(self):
        """Test proper Unicode handling."""
        with patch('hassy_normalizer.rules._get_exceptions', return_value=set()):
            # Test with various Unicode characters
            assert apply_letter_rules('قرآن', 0) == 'كرآن'
            assert apply_letter_rules('مُقدّمة', 0) == 'مُكدّمه'
    
    def test_mixed_scripts(self):
        """Test handling of mixed scripts."""
        with patch('hassy_normalizer.rules._get_exceptions', return_value=set()):
            # Arabic with Latin characters
            result = apply_letter_rules('قال123', 0)
            assert result == 'كال123'
    
    def test_very_long_words(self):
        """Test handling of very long words."""
        with patch('hassy_normalizer.rules._get_exceptions', return_value=set()):
            long_word = 'ق' * 1000 + 'ة'
            result = apply_letter_rules(long_word, 0)
            expected = 'ك' * 1000 + 'ه'
            assert result == expected
    
    def test_special_characters(self):
        """Test handling of special characters and punctuation."""
        with patch('hassy_normalizer.rules._get_exceptions', return_value=set()):
            # Should preserve punctuation
            assert apply_letter_rules('قال!', 0) == 'كال!'
            assert apply_letter_rules('قال؟', 0) == 'كال؟'
            assert apply_letter_rules('"قال"', 0) == '"كال"'


if __name__ == '__main__':
    pytest.main([__file__])