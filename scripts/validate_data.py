#!/usr/bin/env python3
"""Validate data files for consistency and correctness."""

import json
import sys
from pathlib import Path
from typing import Set, Dict, List


def validate_variants_file(file_path: Path) -> bool:
    """Validate hassaniya_variants.jsonl file.
    
    Checks:
    - Valid JSONL format
    - Required fields (canonical, variants)
    - No duplicate canonical forms
    - No empty variants
    - Canonical forms don't appear in variants lists
    
    Args:
        file_path: Path to the variants JSONL file
        
    Returns:
        True if valid, False otherwise
    """
    print(f"Validating variants file: {file_path}")
    
    if not file_path.exists():
        print(f"ERROR: File not found: {file_path}")
        return False
    
    canonical_forms: Set[str] = set()
    all_variants: Set[str] = set()
    line_number = 0
    errors = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line_number += 1
                line = line.strip()
                
                if not line:  # Skip empty lines
                    continue
                
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError as e:
                    errors.append(f"Line {line_number}: Invalid JSON - {e}")
                    continue
                
                # Check required fields
                if not isinstance(entry, dict):
                    errors.append(f"Line {line_number}: Entry must be a JSON object")
                    continue
                
                if 'canonical' not in entry:
                    errors.append(f"Line {line_number}: Missing 'canonical' field")
                    continue
                
                if 'variants' not in entry:
                    errors.append(f"Line {line_number}: Missing 'variants' field")
                    continue
                
                canonical = entry['canonical']
                variants = entry['variants']
                
                # Validate canonical form
                if not isinstance(canonical, str) or not canonical.strip():
                    errors.append(f"Line {line_number}: 'canonical' must be a non-empty string")
                    continue
                
                # Validate variants
                if not isinstance(variants, list):
                    errors.append(f"Line {line_number}: 'variants' must be a list")
                    continue
                
                if not variants:
                    errors.append(f"Line {line_number}: 'variants' list cannot be empty")
                    continue
                
                # Check for duplicate canonical forms
                if canonical in canonical_forms:
                    errors.append(f"Line {line_number}: Duplicate canonical form '{canonical}'")
                else:
                    canonical_forms.add(canonical)
                
                # Validate each variant
                for i, variant in enumerate(variants):
                    if not isinstance(variant, str) or not variant.strip():
                        errors.append(f"Line {line_number}: Variant {i+1} must be a non-empty string")
                        continue
                    
                    # Check if canonical appears in its own variants
                    if variant == canonical:
                        errors.append(f"Line {line_number}: Canonical form '{canonical}' appears in its own variants")
                    
                    # Track all variants for cross-checking
                    if variant in all_variants:
                        errors.append(f"Line {line_number}: Variant '{variant}' appears multiple times")
                    else:
                        all_variants.add(variant)
    
    except Exception as e:
        errors.append(f"Error reading file: {e}")
    
    # Check for variants that are also canonical forms
    variant_canonical_overlap = all_variants & canonical_forms
    if variant_canonical_overlap:
        for overlap in variant_canonical_overlap:
            errors.append(f"Word '{overlap}' appears as both canonical and variant")
    
    # Report results
    if errors:
        print(f"VALIDATION FAILED: {len(errors)} error(s) found:")
        for error in errors[:20]:  # Limit to first 20 errors
            print(f"  - {error}")
        if len(errors) > 20:
            print(f"  ... and {len(errors) - 20} more errors")
        return False
    
    print(f"✓ Variants file is valid:")
    print(f"  - {line_number} entries processed")
    print(f"  - {len(canonical_forms)} unique canonical forms")
    print(f"  - {len(all_variants)} unique variants")
    return True


def validate_exceptions_file(file_path: Path) -> bool:
    """Validate exception_words_g_q.json file.
    
    Checks:
    - Valid JSON format
    - Array of strings
    - No empty strings
    - No duplicates
    
    Args:
        file_path: Path to the exceptions JSON file
        
    Returns:
        True if valid, False otherwise
    """
    print(f"Validating exceptions file: {file_path}")
    
    if not file_path.exists():
        print(f"ERROR: File not found: {file_path}")
        return False
    
    errors = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Check if it's a list
        if not isinstance(data, list):
            errors.append("File must contain a JSON array")
            return False
        
        seen_words: Set[str] = set()
        
        for i, word in enumerate(data):
            # Check if each item is a string
            if not isinstance(word, str):
                errors.append(f"Item {i+1}: Must be a string, got {type(word).__name__}")
                continue
            
            # Check for empty strings
            if not word.strip():
                errors.append(f"Item {i+1}: Empty or whitespace-only string")
                continue
            
            # Check for duplicates
            if word in seen_words:
                errors.append(f"Item {i+1}: Duplicate word '{word}'")
            else:
                seen_words.add(word)
    
    except json.JSONDecodeError as e:
        errors.append(f"Invalid JSON format: {e}")
    except Exception as e:
        errors.append(f"Error reading file: {e}")
    
    # Report results
    if errors:
        print(f"VALIDATION FAILED: {len(errors)} error(s) found:")
        for error in errors[:20]:  # Limit to first 20 errors
            print(f"  - {error}")
        if len(errors) > 20:
            print(f"  ... and {len(errors) - 20} more errors")
        return False
    
    print(f"✓ Exceptions file is valid:")
    print(f"  - {len(data)} exception words")
    print(f"  - {len(seen_words)} unique words")
    return True


def validate_data_consistency(variants_file: Path, exceptions_file: Path) -> bool:
    """Validate consistency between variants and exceptions files.
    
    Checks:
    - Exception words don't appear as canonical forms
    - Exception words don't appear as variants
    
    Args:
        variants_file: Path to variants JSONL file
        exceptions_file: Path to exceptions JSON file
        
    Returns:
        True if consistent, False otherwise
    """
    print("Validating data consistency...")
    
    errors = []
    
    try:
        # Load exceptions
        with open(exceptions_file, 'r', encoding='utf-8') as f:
            exceptions = set(json.load(f))
        
        # Load variants
        canonical_forms = set()
        all_variants = set()
        
        with open(variants_file, 'r', encoding='utf-8') as f:
            for line_number, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    entry = json.loads(line)
                    canonical = entry.get('canonical', '')
                    variants = entry.get('variants', [])
                    
                    if canonical:
                        canonical_forms.add(canonical)
                    
                    for variant in variants:
                        if isinstance(variant, str):
                            all_variants.add(variant)
                            
                except json.JSONDecodeError:
                    continue  # Skip invalid lines (already caught by other validation)
        
        # Check for overlaps
        exception_canonical_overlap = exceptions & canonical_forms
        if exception_canonical_overlap:
            for word in exception_canonical_overlap:
                errors.append(f"Exception word '{word}' also appears as canonical form")
        
        exception_variant_overlap = exceptions & all_variants
        if exception_variant_overlap:
            for word in exception_variant_overlap:
                errors.append(f"Exception word '{word}' also appears as variant")
    
    except Exception as e:
        errors.append(f"Error during consistency check: {e}")
    
    # Report results
    if errors:
        print(f"CONSISTENCY CHECK FAILED: {len(errors)} error(s) found:")
        for error in errors[:10]:  # Limit to first 10 errors
            print(f"  - {error}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more errors")
        return False
    
    print("✓ Data consistency check passed")
    return True


def main() -> int:
    """Main validation function.
    
    Returns:
        0 if all validations pass, 1 otherwise
    """
    print("=== Hassaniya Normalizer Data Validation ===")
    
    # Find data files
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    data_dir = project_root / "src" / "hassy_normalizer" / "data"
    
    variants_file = data_dir / "hassaniya_variants.jsonl"
    exceptions_file = data_dir / "exception_words_g_q.json"
    
    print(f"Project root: {project_root}")
    print(f"Data directory: {data_dir}")
    print()
    
    # Run validations
    all_valid = True
    
    # Validate individual files
    if not validate_variants_file(variants_file):
        all_valid = False
    print()
    
    if not validate_exceptions_file(exceptions_file):
        all_valid = False
    print()
    
    # Validate consistency between files
    if all_valid:  # Only run consistency check if individual files are valid
        if not validate_data_consistency(variants_file, exceptions_file):
            all_valid = False
        print()
    
    # Final result
    if all_valid:
        print("🎉 All data validation checks passed!")
        return 0
    else:
        print("❌ Data validation failed!")
        return 1


if __name__ == '__main__':
    sys.exit(main())