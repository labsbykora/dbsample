"""Configuration file parsing for dbsample utility."""

import json
import os
from typing import Dict, Any, Optional


def load_config_file(config_path: str) -> Dict[str, Any]:
    """Load configuration from JSON or YAML file.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Dictionary of configuration values
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config file is invalid
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        # Try JSON first
        if config_path.endswith('.json'):
            try:
                return json.load(f)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in config file: {e}")
        
        # Try YAML if PyYAML is available
        elif config_path.endswith(('.yaml', '.yml')):
            try:
                import yaml
                return yaml.safe_load(f) or {}
            except ImportError:
                raise ValueError(
                    "YAML config files require PyYAML. Install with: pip install pyyaml"
                )
            except Exception as e:
                raise ValueError(f"Invalid YAML in config file: {e}")
        
        # Auto-detect format
        else:
            content = f.read()
            
            # Try JSON first
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # Try YAML
                try:
                    import yaml
                    return yaml.safe_load(content) or {}
                except ImportError:
                    raise ValueError(
                        "Config file format not recognized. Use .json extension or install PyYAML for YAML support."
                    )
                except Exception:
                    raise ValueError("Config file format not recognized. Use .json or .yaml extension.")


def merge_config_with_cli(config: Dict[str, Any], cli_args: Dict[str, Any]) -> Dict[str, Any]:
    """Merge configuration file values with CLI arguments.
    
    CLI arguments take precedence over config file values.
    
    Args:
        config: Configuration from file
        cli_args: CLI arguments (as dictionary)
        
    Returns:
        Merged configuration dictionary
    """
    merged = config.copy()
    
    # Merge CLI args (they override config file)
    for key, value in cli_args.items():
        # Skip None values from CLI (they mean "not specified")
        if value is not None:
            # Handle special cases
            if key == 'limit' and isinstance(value, tuple):
                # Convert tuple to list for consistency
                merged[key] = list(value) if value else config.get(key, [])
            elif key == 'schema' and isinstance(value, tuple):
                merged[key] = list(value) if value else config.get(key, [])
            elif key == 'exclude_table' and isinstance(value, tuple):
                merged[key] = list(value) if value else config.get(key, [])
            elif key == 'exclude_schema' and isinstance(value, tuple):
                merged[key] = list(value) if value else config.get(key, [])
            elif key == 'exclude_column' and isinstance(value, tuple):
                merged[key] = list(value) if value else config.get(key, [])
            else:
                merged[key] = value
    
    return merged


def normalize_config_keys(config: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize configuration keys to match CLI argument names.
    
    Converts common variations (e.g., 'database' -> 'dbname', 'output' -> 'file')
    to match CLI argument names.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Normalized configuration dictionary
    """
    normalized = config.copy()
    
    # Common key mappings
    key_mappings = {
        'database': 'dbname',
        'output': 'file',
        'output_file': 'file',
        'gzip': 'compress',
        'compression': 'compress',
        'log_level': 'log_level',
        'verbose': 'verbose',
    }
    
    for old_key, new_key in key_mappings.items():
        if old_key in normalized and new_key not in normalized:
            normalized[new_key] = normalized.pop(old_key)
    
    return normalized

