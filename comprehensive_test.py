#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
sys.path.insert(0, 'src')

from hassy_normalizer.rules import is_exception_word, get_exceptions_count
from hassy_normalizer.normalizer import normalize_word, normalize_text
from hassy_normalizer.data_loader import load_exceptions

# Test القضية specifically
test_word = 'القضية'
test_word_variant = 'القضيه'

with open('comprehensive_results.txt', 'w', encoding='utf-8') as f:
    f.write('=== Comprehensive Normalization Test ===\n\n')
    
    # Check exception count
    exc_count = get_exceptions_count()
    f.write(f'Total exceptions loaded: {exc_count}\n\n')
    
    # Check if القضية is an exception
    is_exc = is_exception_word(test_word)
    f.write(f'Is "{test_word}" an exception? {is_exc}\n')
    
    # Check if القضيه is an exception
    is_exc_variant = is_exception_word(test_word_variant)
    f.write(f'Is "{test_word_variant}" an exception? {is_exc_variant}\n\n')
    
    # Test normalization
    result = normalize_word(test_word)
    f.write(f'normalize_word("{test_word}") = "{result}"\n')
    f.write(f'Expected: "{test_word}" (should stay unchanged)\n')
    f.write(f'Test PASS: {result == test_word}\n\n')
    
    # Test variant normalization
    result_variant = normalize_word(test_word_variant)
    f.write(f'normalize_word("{test_word_variant}") = "{result_variant}"\n')
    f.write(f'Expected: "{test_word_variant}" (should stay unchanged)\n')
    f.write(f'Test PASS: {result_variant == test_word_variant}\n\n')
    
    # Test text normalization
    text_result = normalize_text(test_word)
    f.write(f'normalize_text("{test_word}") = "{text_result}"\n')
    f.write(f'Expected: "{test_word}" (should stay unchanged)\n')
    f.write(f'Test PASS: {text_result == test_word}\n\n')
    
    # Load raw exceptions to check if القضية is there
    try:
        raw_exceptions = load_exceptions()
        f.write(f'Raw exceptions count: {len(raw_exceptions)}\n')
        f.write(f'القضية in raw exceptions: {test_word in raw_exceptions}\n')
        f.write(f'القضيه in raw exceptions: {test_word_variant in raw_exceptions}\n\n')
        
        # Check first few exceptions
        f.write('First 10 exceptions:\n')
        for i, exc in enumerate(sorted(raw_exceptions)[:10]):
            f.write(f'  {i+1}. {exc}\n')
            
    except Exception as e:
        f.write(f'Error loading raw exceptions: {e}\n')

print('Comprehensive test completed. Check comprehensive_results.txt')