#!/usr/bin/env python3
"""Test script to check normalizer functionality."""

import sys
sys.path.insert(0, 'src')

try:
    from hassy_normalizer.normalizer import normalize_text, get_stats
    from hassy_normalizer.data_loader import _get_data_file_path
    
    # Test text with known variants
    test_text = "مرحبا بكم في مسجل اللهجة الحسانية"
    
    print("=== Normalizer Test ===")
    print(f"Original text: {test_text}")
    
    # Get normalizer stats
    stats = get_stats()
    print(f"\nNormalizer stats: {stats}")
    
    # Test normalization
    normalized = normalize_text(test_text)
    print(f"Normalized text: {normalized}")
    
    # Check if normalization actually changed anything
    if normalized != test_text:
        print("✓ Normalization applied changes")
    else:
        print("⚠ No changes applied - this might indicate data files are not loaded")
    
    # Check data file accessibility
    print("\n=== Data File Check ===")
    data_files = [
        "hassaniya_variants.jsonl",
        "exception_words_g_q.json",
        "linked_words.json"
    ]
    
    for filename in data_files:
        try:
            filepath = _get_data_file_path(filename)
            exists = filepath.exists()
            size = filepath.stat().st_size if exists else 0
            print(f"{filename}: {'✓' if exists else '✗'} {filepath} ({size} bytes)")
        except Exception as e:
            print(f"{filename}: ✗ Error - {e}")
            
except ImportError as e:
    print(f"Import error: {e}")
except Exception as e:
    print(f"Error: {e}")