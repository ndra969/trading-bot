"""
Configuration Hasher Utility.

Provides SHA256 hashing for configuration dictionaries.
Ensures consistent hashing for configuration versioning.
"""

import hashlib
import json
from typing import Any


def hash_config(config: dict) -> str:
    """
    Generate SHA256 hash of configuration dictionary.

    Args:
        config: Configuration dictionary to hash

    Returns:
        64-character hexadecimal SHA256 hash

    Example:
        >>> config = {"risk": {"max_risk": 1.0}, "trading": {"symbols": ["EURUSD"]}}
        >>> hash_config(config)
        'a1b2c3d4e5f6...'
    """
    # Sort keys recursively for consistent hashing
    sorted_config = _sort_dict_recursively(config)

    # Convert to JSON string with sorted keys
    config_str = json.dumps(sorted_config, sort_keys=True, separators=(",", ":"))

    # Generate SHA256 hash
    hash_object = hashlib.sha256(config_str.encode("utf-8"))
    return hash_object.hexdigest()


def _sort_dict_recursively(obj: Any) -> Any:
    """
    Recursively sort dictionary keys for consistent hashing.

    Args:
        obj: Object to sort (dict, list, or primitive)

    Returns:
        Sorted object
    """
    if isinstance(obj, dict):
        return {k: _sort_dict_recursively(v) for k, v in sorted(obj.items())}
    if isinstance(obj, list):
        return [_sort_dict_recursively(item) for item in obj]
    return obj


def verify_config_hash(config: dict, expected_hash: str) -> bool:
    """
    Verify that configuration matches expected hash.

    Args:
        config: Configuration dictionary
        expected_hash: Expected SHA256 hash

    Returns:
        True if hash matches, False otherwise

    Example:
        >>> config = {"risk": {"max_risk": 1.0}}
        >>> hash_val = hash_config(config)
        >>> verify_config_hash(config, hash_val)
        True
    """
    actual_hash = hash_config(config)
    return actual_hash == expected_hash


def compare_configs(config1: dict, config2: dict) -> dict:
    """
    Compare two configuration dictionaries.

    Args:
        config1: First configuration
        config2: Second configuration

    Returns:
        Dictionary with differences:
        {
            "same_hash": bool,
            "hash1": str,
            "hash2": str,
            "added": list,
            "removed": list,
            "modified": list
        }
    """
    hash1 = hash_config(config1)
    hash2 = hash_config(config2)

    differences = {
        "same_hash": hash1 == hash2,
        "hash1": hash1,
        "hash2": hash2,
        "added": [],
        "removed": [],
        "modified": [],
    }

    if hash1 == hash2:
        return differences

    # Find added and modified keys
    for key in config2:
        if key not in config1:
            differences["added"].append(key)
        elif config1[key] != config2[key]:
            differences["modified"].append(
                {
                    "key": key,
                    "old_value": config1[key],
                    "new_value": config2[key],
                }
            )

    # Find removed keys
    for key in config1:
        if key not in config2:
            differences["removed"].append(key)

    return differences
