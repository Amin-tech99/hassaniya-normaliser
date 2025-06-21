import sys
sys.path.insert(0, 'src')
from hassy_normalizer.normalizer import normalize_word
from hassy_normalizer.rules import get_exceptions_count

with open('test_results.txt', 'w', encoding='utf-8') as f:
    f.write(f'Exception count: {get_exceptions_count()}\n')
    test_word = 'القضية'
    result = normalize_word(test_word)
    f.write(f'Input: {test_word}\n')
    f.write(f'Output: {result}\n')
    f.write(f'Status: {"PASS" if result == test_word else "FAIL"}\n\n')
    
    # Test a few more exception words
    test_words = ['القضية', 'قادية', 'أحق', 'أرقام']
    for word in test_words:
        result = normalize_word(word)
        status = 'PASS' if result == word else 'FAIL'
        f.write(f'{word} -> {result} ({status})\n')

print('Test completed. Results written to test_results.txt')