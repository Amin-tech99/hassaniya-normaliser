#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Debug script to investigate normalization issues."""

import sys
sys.path.insert(0, 'src')

from hassy_normalizer import normalize_word, clear_cache
from hassy_normalizer.rules import (
    _get_exceptions, 
    apply_letter_rules, 
    clear_rules_cache,
    reload_exceptions
)

def debug_normalization():
    """Debug the normalization process step by step."""
    print("=== DEBUGGING NORMALIZATION PROCESS ===")
    
    # Clear all caches
    clear_cache()
    clear_rules_cache()
    reload_exceptions()
    
    test_word = "القضية"
    print(f"\nTesting word: {test_word}")
    
    # Check exceptions
    exceptions = _get_exceptions()
    print(f"Total exceptions loaded: {len(exceptions)}")
    print(f"Is '{test_word}' in exceptions: {test_word in exceptions}")
    print(f"Is 'القضيه' in exceptions: {'القضيه' in exceptions}")
    
    # Test apply_letter_rules directly
    print(f"\nDirect apply_letter_rules('{test_word}'): {apply_letter_rules(test_word)}")
    
    # Test normalize_word
    result = normalize_word(test_word)
    print(f"normalize_word('{test_word}'): {result}")
    
    # Check if result matches expected
    expected = test_word  # Should remain unchanged
    if result == expected:
        print("✅ SUCCESS: Word preserved as exception")
    else:
        print(f"❌ FAILURE: Expected '{expected}', got '{result}'")
        
        # Additional debugging
        print("\n--- ADDITIONAL DEBUG INFO ---")
        
        # Check if القضيه variant exists
        haa_variant = "القضيه"
        print(f"Haa variant '{haa_variant}' in exceptions: {haa_variant in exceptions}")
        
        # Test step by step
        print(f"\nStep-by-step analysis:")
        print(f"1. Original word: {test_word}")
        print(f"2. Word in exceptions: {test_word in exceptions}")
        print(f"3. After ق→ك (if not exception): {test_word.replace('ق', 'ك') if test_word not in exceptions else test_word}")
        
        if test_word.endswith('ة'):
            haa_form = test_word[:-1] + 'ه'
            print(f"4. Haa form would be: {haa_form}")
            print(f"5. Haa form in exceptions: {haa_form in exceptions}")
            print(f"6. Should convert ة→ه: {test_word not in exceptions and haa_form not in exceptions}")
    
    print("\n=== DEBUG COMPLETE ===")

if __name__ == "__main__":
    debug_normalization()