#!/usr/bin/env python3
"""Debug script to test exception loading."""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

with open('test_output.txt', 'w', encoding='utf-8') as f:
    try:
        from hassy_normalizer.rules import _get_exceptions, apply_letter_rules, is_exception_word
        from hassy_normalizer.data_loader import load_exceptions
        from hassy_normalizer import normalize_text
        
        f.write("=== Exception Loading Debug ===\n")
        
        # Test 1: Load exceptions directly
        f.write("\n1. Loading exceptions directly:\n")
        try:
            exceptions = load_exceptions()
            f.write(f"   Loaded {len(exceptions)} exception words\n")
            f.write(f"   First 5: {list(exceptions)[:5]}\n")
        except Exception as e:
            f.write(f"   ERROR: {e}\n")
        
        # Test 2: Get exceptions via rules
        f.write("\n2. Getting exceptions via rules:\n")
        try:
            exceptions = _get_exceptions()
            f.write(f"   Got {len(exceptions)} exception words\n")
            f.write(f"   First 5: {list(exceptions)[:5]}\n")
        except Exception as e:
            f.write(f"   ERROR: {e}\n")
        
        # Test 3: Test specific words
        f.write("\n3. Testing specific words:\n")
        test_words = ['ءواثق', 'قادية', 'أحق', 'test']
        
        for word in test_words:
            try:
                is_exception = is_exception_word(word)
                letter_rules_result = apply_letter_rules(word)
                normalized = normalize_text(word)
                
                f.write(f"   Word: {word}\n")
                f.write(f"     Is exception: {is_exception}\n")
                f.write(f"     Letter rules: {letter_rules_result}\n")
                f.write(f"     Full normalize: {normalized}\n")
                f.write(f"     Changed: {normalized != word}\n")
                f.write("\n")
            except Exception as e:
                f.write(f"   ERROR testing {word}: {e}\n")
        
        f.write("=== Debug Complete ===\n")
        
    except Exception as e:
        f.write(f"FATAL ERROR: {e}\n")
        import traceback
        f.write(traceback.format_exc())

print("Debug complete, check test_output.txt")