#!/usr/bin/env python3

import sys
sys.path.insert(0, 'src')

from hassy_normalizer.normalizer import normalize_word
from hassy_normalizer.rules import is_exception_word, apply_letter_rules

test_word = 'القضية'
print(f'Testing word: {test_word}')
print(f'Is exception: {is_exception_word(test_word)}')
print(f'Letter rules result: {apply_letter_rules(test_word)}')
print(f'Full normalization: {normalize_word(test_word)}')
print(f'Expected (from test): القضيه')