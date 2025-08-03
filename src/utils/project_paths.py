#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Central module for managing project paths and imports.

This module provides standardized access to project paths and handles the
necessary sys.path modifications to ensure consistent imports across the project.
It removes the need for redundant path handling code in individual modules.
"""

import os
import sys
from pathlib import Path
from typing import Optional, Dict, List, Union

# Detect project root directory
def _detect_project_root() -> Path:
    """
    Detect the project root directory by looking for common markers.
    
    Returns:
        Path to the project root directory
    """
    # Start with this file's directory
    current_file = Path(__file__).resolve()
    
    # If we're in src/utils, go up two levels
    if "src" in current_file.parts and "utils" in current_file.parts:
        return current_file.parents[2]
    
    # Otherwise, look for common markers (src dir, requirements.txt)
    current_dir = current_file.parent
    for _ in range(5):  # Check up to 5 levels up
        if (current_dir / "src").exists() and (current_dir / "requirements.txt").exists():
            return current_dir
        current_dir = current_dir.parent
    
    # If all else fails, assume the current working directory
    return Path.cwd()

# Project root path
PROJECT_ROOT = _detect_project_root()

# Common project directories
SRC_DIR = PROJECT_ROOT / "src"
CONFIG_DIR = PROJECT_ROOT / "config"
LOGS_DIR = PROJECT_ROOT / "logs"
RESULTS_DIR = PROJECT_ROOT / "results"
DATA_DIR = PROJECT_ROOT / "simulation_data"
TESTS_DIR = PROJECT_ROOT / "tests"

# Make sure the directories exist
LOGS_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)

def setup_python_path():
    """
    Add necessary directories to sys.path for proper imports.
    Call this at the beginning of every entry-point script.
    """
    # Add project root and src to path if not already there
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    
    if str(SRC_DIR) not in sys.path:
        sys.path.insert(0, str(SRC_DIR))

# Run setup automatically when the module is imported
setup_python_path()

def get_project_structure() -> Dict[str, Path]:
    """
    Get a dictionary of important project directories.
    
    Returns:
        Dictionary containing paths to important project directories
    """
    return {
        "project_root": PROJECT_ROOT,
        "src_dir": SRC_DIR,
        "config_dir": CONFIG_DIR,
        "logs_dir": LOGS_DIR,
        "results_dir": RESULTS_DIR,
        "data_dir": DATA_DIR,
        "tests_dir": TESTS_DIR,
    }

def get_module_paths() -> Dict[str, Path]:
    """
    Get paths to the main modules in the project.
    
    Returns:
        Dictionary containing paths to main modules
    """
    core_dir = SRC_DIR / "core"
    utils_dir = SRC_DIR / "utils"
    config_dir = SRC_DIR / "config"
    hpc_dir = SRC_DIR / "hpc"
    lidar_dir = SRC_DIR / "LiDAR_preprocessing"
    
    return {
        "core": core_dir,
        "utils": utils_dir,
        "config": config_dir,
        "hpc": hpc_dir,
        "lidar": lidar_dir,
    }

def resolve_path(path_str: str) -> Path:
    """
    Resolve a path string relative to the project root if it's not absolute.
    
    Args:
        path_str: Path string to resolve
        
    Returns:
        Resolved Path object
    """
    path = Path(path_str)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path

def get_results_dir(timestamp: Optional[str] = None) -> Path:
    """
    Get a timestamped results directory.
    
    Args:
        timestamp: Optional timestamp string. If None, current time is used.
        
    Returns:
        Path to the results directory
    """
    if timestamp is None:
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    result_dir = RESULTS_DIR / f"sim_{timestamp}"
    result_dir.mkdir(exist_ok=True, parents=True)
    return result_dir

def get_config_file_path(config_name: str) -> Path:
    """
    Get the path to a configuration file.
    
    Args:
        config_name: Name of the configuration file
        
    Returns:
        Path to the configuration file
    """
    # Ensure the file has the .json extension
    if not config_name.endswith('.json'):
        config_name = f"{config_name}.json"
    
    # First check in the config directory
    config_path = CONFIG_DIR / config_name
    if config_path.exists():
        return config_path
    
    # Then check relative to the current directory
    local_path = Path(config_name)
    if local_path.exists():
        return local_path
    
    # Finally check in the src/config directory
    src_config_path = SRC_DIR / "config" / config_name
    if src_config_path.exists():
        return src_config_path
    
    # Return the config directory path even if the file doesn't exist
    return config_path

# Convenience function for printing paths
def print_project_structure():
    """Print the project structure for debugging."""
    structure = get_project_structure()
    print("Project Structure:")
    for name, path in structure.items():
        exists = "✓" if path.exists() else "✗"
        print(f"  {name:12} [{exists}]: {path}")

if __name__ == "__main__":
    # If run directly, print the project structure for debugging
    print_project_structure() 