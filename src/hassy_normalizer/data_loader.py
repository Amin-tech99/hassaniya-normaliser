"""Data loading utilities for Hassaniya normalizer.

Provides safe loading of JSON/JSONL data files with validation and caching.
"""

import json
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Set, Tuple

try:
    from importlib.resources import files
except ImportError:
    # Python < 3.9 fallback
    from importlib_resources import files

logger = logging.getLogger(__name__)

# Cache for file modification times
_file_mtimes: Dict[str, float] = {}


def _get_data_file_path(filename: str) -> Path:
    """Get path to data file using importlib.resources.
    
    Args:
        filename: Name of the data file
        
    Returns:
        Path to the data file
    """
    # 1. Environment variable override
    env_dir = os.getenv("HASSY_DATA_DIR")
    if env_dir:
        candidate = Path(env_dir) / filename
        if candidate.exists():
            return candidate

    # 2. Walk up parent directories (max 5 levels) to locate a loose file (useful
    #    during local development where the jsonl sits in the repo root)
    current_dir = Path(__file__).resolve().parent
    for _ in range(5):
        candidate = current_dir / filename
        if candidate.exists():
            return candidate
        current_dir = current_dir.parent

    # 3. Try the packaged data folder (installed package scenario)
    try:
        data_files = files("hassy_normalizer.data")
        candidate = data_files / filename
        if candidate.exists():
            return candidate
    except (ImportError, FileNotFoundError):
        pass

    # 4. Fallback to src-relative "data" folder
    data_path = Path(__file__).parent / "data" / filename
    if data_path.exists():
        return data_path

    # Not found
    raise FileNotFoundError(f"Data file not found: {filename}")


def _validate_variant_entry(entry: Dict) -> None:
    """Validate a single variant entry.
    
    Args:
        entry: Dictionary containing variant data
        
    Raises:
        ValueError: If entry format is invalid
    """
    if not isinstance(entry, dict):
        raise ValueError(f"Entry must be a dictionary, got {type(entry)}")
    
    if "canonical" not in entry:
        raise ValueError("Entry missing 'canonical' field")
    
    if "variants" not in entry:
        raise ValueError("Entry missing 'variants' field")
    
    if not isinstance(entry["canonical"], str):
        raise ValueError("'canonical' must be a string")
    
    if not isinstance(entry["variants"], list):
        raise ValueError("'variants' must be a list")
    
    if not all(isinstance(v, str) for v in entry["variants"]):
        raise ValueError("All variants must be strings")


def _validate_exceptions(exceptions: List[str]) -> None:
    """Validate exception words list.
    
    Args:
        exceptions: List of exception words
        
    Raises:
        ValueError: If format is invalid
    """
    if not isinstance(exceptions, list):
        raise ValueError(f"Exceptions must be a list, got {type(exceptions)}")
    
    if not all(isinstance(word, str) for word in exceptions):
        raise ValueError("All exception words must be strings")


def _check_file_changed(filepath: Path) -> bool:
    """Check if file has been modified since last load.
    
    Args:
        filepath: Path to the file
        
    Returns:
        True if file has changed or is new
    """
    try:
        current_mtime = os.path.getmtime(filepath)
        filepath_str = str(filepath)
        
        if filepath_str not in _file_mtimes:
            _file_mtimes[filepath_str] = current_mtime
            return True
        
        if _file_mtimes[filepath_str] != current_mtime:
            _file_mtimes[filepath_str] = current_mtime
            return True
        
        return False
    except OSError:
        return True


@lru_cache(maxsize=2)
def _load_variants_cached(filepath_str: str, mtime: float) -> Dict[str, str]:
    """Cached loader for variants data.
    
    Args:
        filepath_str: String path to variants file
        mtime: File modification time (for cache invalidation)
        
    Returns:
        Dictionary mapping variants to canonical forms
    """
    filepath = Path(filepath_str)
    variants_map = {}
    
    logger.info(f"Loading variants from {filepath}")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    entry = json.loads(line)
                    _validate_variant_entry(entry)
                    
                    canonical = entry["canonical"]
                    for variant in entry["variants"]:
                        if variant in variants_map:
                            logger.warning(
                                f"Duplicate variant '{variant}' at line {line_num}, "
                                f"overriding previous mapping"
                            )
                        variants_map[variant] = canonical
                        
                except json.JSONDecodeError as e:
                    raise ValueError(f"Invalid JSON at line {line_num}: {e}")
                except ValueError as e:
                    raise ValueError(f"Validation error at line {line_num}: {e}")
    
    except FileNotFoundError:
        raise FileNotFoundError(f"Variants file not found: {filepath}")
    except UnicodeDecodeError as e:
        raise ValueError(f"Encoding error reading {filepath}: {e}")
    
    logger.info(f"Loaded {len(variants_map)} variant mappings")
    return variants_map


@lru_cache(maxsize=2)
def _load_exceptions_cached(filepath_str: str, mtime: float) -> Set[str]:
    """Cached loader for exception words.
    
    Args:
        filepath_str: String path to exceptions file
        mtime: File modification time (for cache invalidation)
        
    Returns:
        Set of exception words
    """
    filepath = Path(filepath_str)
    
    logger.info(f"Loading exceptions from {filepath}")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            exceptions_list = json.load(f)
            _validate_exceptions(exceptions_list)
            
    except FileNotFoundError:
        raise FileNotFoundError(f"Exceptions file not found: {filepath}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {filepath}: {e}")
    except UnicodeDecodeError as e:
        raise ValueError(f"Encoding error reading {filepath}: {e}")
    
    exceptions_set = set(exceptions_list)
    logger.info(f"Loaded {len(exceptions_set)} exception words")
    return exceptions_set


def load_variants() -> Dict[str, str]:
    """Load variant mappings from JSONL file.
    
    Returns:
        Dictionary mapping variant words to canonical forms
        
    Raises:
        FileNotFoundError: If variants file not found
        ValueError: If file format is invalid
    """
    filepath = _get_data_file_path("hassaniya_variants.jsonl")
    
    # Check if file changed and clear cache if needed
    if _check_file_changed(filepath):
        _load_variants_cached.cache_clear()
    
    mtime = os.path.getmtime(filepath)
    return _load_variants_cached(str(filepath), mtime)


def load_exceptions() -> Set[str]:
    """Load exception words from JSON file.
    
    Returns:
        Set of words that should not have letter rules applied
        
    Raises:
        FileNotFoundError: If exceptions file not found
        ValueError: If file format is invalid
    """
    filepath = _get_data_file_path("exception_words_g_q.json")
    
    # Check if file changed and clear cache if needed
    if _check_file_changed(filepath):
        _load_exceptions_cached.cache_clear()
    
    mtime = os.path.getmtime(filepath)
    return _load_exceptions_cached(str(filepath), mtime)


@lru_cache(maxsize=2)
def _load_link_fixes_cached(filepath_str: str, mtime: float) -> Dict[str, str]:
    """Cached loader for link fixes data.
    
    Args:
        filepath_str: String path to link fixes file
        mtime: File modification time (for cache invalidation)
        
    Returns:
        Dictionary mapping wrong forms to correct forms
    """
    filepath = Path(filepath_str)
    
    logger.info(f"Loading link fixes from {filepath}")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            link_fixes_list = json.load(f)
            
        if not isinstance(link_fixes_list, list):
            raise ValueError(f"Link fixes must be a list, got {type(link_fixes_list)}")
        
        link_fixes_map = {}
        for item in link_fixes_list:
            if not isinstance(item, dict):
                raise ValueError(f"Each link fix entry must be a dictionary, got {type(item)}")
            if "wrong" not in item or "correct" not in item:
                raise ValueError("Each link fix entry must have 'wrong' and 'correct' fields")
            if not isinstance(item["wrong"], str) or not isinstance(item["correct"], str):
                raise ValueError("'wrong' and 'correct' fields must be strings")
            
            link_fixes_map[item["wrong"]] = item["correct"]
            
    except FileNotFoundError:
        logger.info(f"Link fixes file not found: {filepath}, using empty mapping")
        return {}
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {filepath}: {e}")
    except UnicodeDecodeError as e:
        raise ValueError(f"Encoding error reading {filepath}: {e}")
    
    logger.info(f"Loaded {len(link_fixes_map)} link fix mappings")
    return link_fixes_map


def load_link_fixes() -> Dict[str, str]:
    """Load link fix mappings from JSON file.
    
    Returns:
        Dictionary mapping wrong forms to correct forms
        
    Raises:
        ValueError: If file format is invalid
    """
    filepath = _get_data_file_path("linked_words.json")
    
    # Check if file changed and clear cache if needed
    if _check_file_changed(filepath):
        _load_link_fixes_cached.cache_clear()
    
    try:
        mtime = os.path.getmtime(filepath)
    except OSError:
        # File doesn't exist, return empty dict
        return {}
    
    return _load_link_fixes_cached(str(filepath), mtime)


def get_link_fixes() -> Dict[str, str]:
    """Get link fixes mapping with error handling.
    
    Returns:
        Dictionary mapping wrong forms to correct forms
    """
    try:
        return load_link_fixes()
    except Exception as e:
        logger.error(f"Failed to load link fixes: {e}")
        return {}  # Fallback to empty mapping


def clear_cache() -> None:
    """Clear all data loading caches.
    
    Useful for testing or when data files are updated externally.
    """
    _load_variants_cached.cache_clear()
    _load_exceptions_cached.cache_clear()
    _load_link_fixes_cached.cache_clear()
    _file_mtimes.clear()
    logger.info("Data loading caches cleared")