#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Standardized logging utilities for the Forest Fire Simulation Framework.

This module provides consistent logging functionality across all components
of the framework, with configurable logging levels, output formats, and destinations.
"""

import os
import sys
import logging
import datetime
from typing import Optional, Union, Dict, Any
from pathlib import Path

# Default log levels for different components
DEFAULT_LOG_LEVELS = {
    "core_simulation_framework": logging.INFO,
    "fire_simulation_engine": logging.INFO,
    "vegetation_data_integration": logging.INFO,
    "run_tiled_simulation": logging.INFO,
    "config_tools": logging.INFO,
    "memory_manager": logging.INFO,
    "disk_storage": logging.INFO,
    "hpc_runner": logging.INFO,
    "fire_simulation": logging.INFO,
}

# Log format templates
LOG_FORMATS = {
    "simple": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "detailed": "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
    "memory": "%(asctime)s - %(name)s - %(levelname)s - MEM:%(memory_usage).2fMB - %(message)s",
    "performance": "%(asctime)s - %(name)s - %(levelname)s - [%(elapsed).4fs] - %(message)s",
}

# Global registry of configured loggers to avoid duplicate configuration
_CONFIGURED_LOGGERS = {}

# Project root path - detect once and cache
_PROJECT_ROOT = None

class MemoryUsageFilter(logging.Filter):
    """Filter that adds memory usage information to log records."""
    
    def filter(self, record):
        """Add memory_usage attribute to the record."""
        if not hasattr(record, 'memory_usage'):
            try:
                import psutil
                process = psutil.Process(os.getpid())
                record.memory_usage = process.memory_info().rss / (1024 * 1024)  # MB
            except (ImportError, Exception):
                record.memory_usage = 0.0
        return True

class ElapsedTimeFilter(logging.Filter):
    """Filter that adds elapsed time information to log records."""
    
    def __init__(self, start_time=None):
        """Initialize with an optional start time."""
        super().__init__()
        self.start_time = start_time or datetime.datetime.now()
    
    def filter(self, record):
        """Add elapsed attribute to the record."""
        if not hasattr(record, 'elapsed'):
            current_time = datetime.datetime.now()
            record.elapsed = (current_time - self.start_time).total_seconds()
        return True

class SimulationLogger:
    """
    Centralized logger for the Forest Fire Simulation Framework.
    
    This class provides consistent logging across all components of the framework,
    with configurable logging levels, formats, and destinations.
    """
    
    def __init__(
        self,
        name: str,
        level: int = None,
        log_format: str = "simple",
        log_file: str = None,
        console: bool = True,
        track_memory: bool = False,
        track_time: bool = False,
    ):
        """
        Initialize a logger for a component of the framework.
        
        Args:
            name: Name of the logger (usually the module name)
            level: Logging level (if None, uses the default for the component)
            log_format: Format to use (simple, detailed, memory, or performance)
            log_file: Path to a log file (if None, no file logging)
            console: Whether to log to console
            track_memory: Whether to track memory usage in logs
            track_time: Whether to track elapsed time in logs
        """
        # Get the default level for this component
        if level is None:
            level = DEFAULT_LOG_LEVELS.get(name.split('.')[0], logging.INFO)
        
        # Create logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # Remove existing handlers to avoid duplicates
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Get the log format
        log_format_str = LOG_FORMATS.get(log_format, LOG_FORMATS["simple"])
        formatter = logging.Formatter(log_format_str)
        
        # Add console handler if requested
        if console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
        
        # Add file handler if requested
        if log_file:
            os.makedirs(os.path.dirname(os.path.abspath(log_file)), exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
        
        # Add memory tracking if requested
        if track_memory:
            memory_filter = MemoryUsageFilter()
            for handler in self.logger.handlers:
                handler.addFilter(memory_filter)
        
        # Add time tracking if requested
        if track_time:
            time_filter = ElapsedTimeFilter()
            for handler in self.logger.handlers:
                handler.addFilter(time_filter)
    
    def get_logger(self):
        """Get the configured logger instance."""
        return self.logger

def get_logger(
    name: str,
    level: int = None,
    log_format: str = "simple",
    log_file: str = None,
    console: bool = True,
    track_memory: bool = False,
    track_time: bool = False,
) -> logging.Logger:
    """
    Get a configured logger for a component of the framework.
    
    Args:
        name: Name of the logger (usually the module name)
        level: Logging level (if None, uses the default for the component)
        log_format: Format to use (simple, detailed, memory, or performance)
        log_file: Path to a log file (if None, no file logging)
        console: Whether to log to console
        track_memory: Whether to track memory usage in logs
        track_time: Whether to track elapsed time in logs
        
    Returns:
        Configured logger instance
    """
    logger = SimulationLogger(
        name, level, log_format, log_file, console, track_memory, track_time
    )
    return logger.get_logger()

def get_project_root() -> Path:
    """
    Get the project root directory.
    
    Returns:
        Path to the project root directory
    """
    global _PROJECT_ROOT
    if _PROJECT_ROOT is None:
        # Start with the current file's directory
        current_file = Path(__file__).resolve()
        
        # Navigate up from src/utils to find project root
        if "src" in current_file.parts and "utils" in current_file.parts:
            # We're in src/utils, so go up two levels
            _PROJECT_ROOT = current_file.parents[2]
        else:
            # Try to find project root by looking for common markers
            current_dir = current_file.parent
            for _ in range(5):  # Check up to 5 levels up
                if (current_dir / "src").exists() and (current_dir / "requirements.txt").exists():
                    _PROJECT_ROOT = current_dir
                    break
                current_dir = current_dir.parent
            
            # If not found, use the script directory's parent as a fallback
            if _PROJECT_ROOT is None:
                # Find the script that's running
                import inspect
                caller_frame = inspect.stack()[-1]
                caller_file = Path(caller_frame.filename).resolve()
                _PROJECT_ROOT = caller_file.parent
    
    return _PROJECT_ROOT

def get_simulation_logger(
    name: str,
    log_dir: Optional[str] = None,
    level: Optional[int] = None,
    log_format: str = "simple",
    console: bool = True,
    track_memory: bool = False,
    track_performance: bool = False,
    use_shared_file: bool = True,
) -> logging.Logger:
    """
    Get a centralized simulation logger with consistent configuration.
    This function should be the primary way to get loggers across the simulation.
    
    Args:
        name: Name of the logger (usually module name or component name)
        log_dir: Directory for log files (if None, uses project_root/logs)
        level: Logging level (if None, uses default based on component name)
        log_format: Format string to use (simple, detailed, memory, performance)
        console: Whether to log to the console
        track_memory: Whether to track memory usage in logs
        track_performance: Whether to track performance metrics in logs
        use_shared_file: Whether to use a shared log file for all components
        
    Returns:
        Configured logger instance
    """
    # Check if we've already configured this logger
    if name in _CONFIGURED_LOGGERS:
        return _CONFIGURED_LOGGERS[name]
    
    # Normalize by using a standard computation of project root
    project_root = get_project_root()
    
    # Set default log directory if not specified
    if log_dir is None:
        log_dir = project_root / "logs"
    else:
        log_dir = Path(log_dir)
    
    # Create log directory if it doesn't exist
    log_dir.mkdir(exist_ok=True, parents=True)
    
    # Generate a timestamp for log files
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Determine log file path
    component_name = name.split('.')[0]
    if use_shared_file:
        # Use shared simulation log file
        log_file = log_dir / f"simulation_{timestamp}.log"
    else:
        # Use component-specific log file
        log_file = log_dir / f"{component_name}_{timestamp}.log"
    
    # Get or create logger
    logger = logging.getLogger(name)
    
    # Get the default level for this component if not specified
    if level is None:
        level = DEFAULT_LOG_LEVELS.get(component_name, logging.INFO)
    
    logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Get the format string
    format_name = log_format
    if track_memory:
        format_name = "memory"
    elif track_performance:
        format_name = "performance"
    
    log_format_str = LOG_FORMATS.get(format_name, LOG_FORMATS["simple"])
    formatter = logging.Formatter(log_format_str)
    
    # Add console handler if requested
    if console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # Add file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Add filters if requested
    if track_memory:
        memory_filter = MemoryUsageFilter()
        for handler in logger.handlers:
            handler.addFilter(memory_filter)
    
    if track_performance:
        performance_filter = ElapsedTimeFilter()
        for handler in logger.handlers:
            handler.addFilter(performance_filter)
    
    # Cache the configured logger
    _CONFIGURED_LOGGERS[name] = logger
    
    return logger

def configure_logging(
    config: Dict[str, Any] = None,
    log_dir: str = "logs",
    default_level: int = logging.INFO,
    console: bool = True,
) -> None:
    """
    Configure logging for all components of the framework.
    
    Args:
        config: Configuration dictionary with component-specific settings
        log_dir: Directory for log files
        default_level: Default logging level
        console: Whether to log to console
    """
    config = config or {}
    
    # Create log directory if it doesn't exist
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
    
    # Update default log levels with config values
    log_levels = DEFAULT_LOG_LEVELS.copy()
    for component, level in config.get("log_levels", {}).items():
        if isinstance(level, str):
            level = getattr(logging, level.upper(), logging.INFO)
        log_levels[component] = level
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(default_level)
    
    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add console handler if requested
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_format = config.get("console_format", "simple")
        console_formatter = logging.Formatter(LOG_FORMATS.get(console_format, LOG_FORMATS["simple"]))
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    
    # Add file handler if log_dir is provided
    if log_dir:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"simulation_{timestamp}.log")
        file_handler = logging.FileHandler(log_file)
        file_format = config.get("file_format", "detailed")
        file_formatter = logging.Formatter(LOG_FORMATS.get(file_format, LOG_FORMATS["detailed"]))
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    # Configure component-specific loggers
    for component, level in log_levels.items():
        component_logger = logging.getLogger(component)
        component_logger.setLevel(level)
        
        # Add component-specific file handler if requested
        if log_dir and config.get("separate_component_logs", False):
            component_log_file = os.path.join(log_dir, f"{component}_{timestamp}.log")
            component_handler = logging.FileHandler(component_log_file)
            component_format = config.get("component_format", "detailed")
            component_formatter = logging.Formatter(LOG_FORMATS.get(component_format, LOG_FORMATS["detailed"]))
            component_handler.setFormatter(component_formatter)
            component_logger.addHandler(component_handler)
            component_logger.propagate = False  # Don't propagate to root

def setup_global_logging(
    log_dir: Optional[Union[str, Path]] = None,
    default_level: int = logging.INFO,
    log_format: str = "detailed",
    console: bool = True,
    track_memory: bool = False
) -> None:
    """
    Set up logging for the entire application in a centralized way.
    This should be called once at the beginning of the application.
    
    Args:
        log_dir: Directory for log files (if None, uses project_root/logs)
        default_level: Default logging level for all components
        log_format: Format to use (simple, detailed, memory, performance)
        console: Whether to log to console
        track_memory: Whether to track memory usage in all logs
    """
    # Get project root and set up log directory
    project_root = get_project_root()
    
    if log_dir is None:
        log_dir = project_root / "logs"
    else:
        log_dir = Path(log_dir)
    
    log_dir.mkdir(exist_ok=True, parents=True)
    
    # Generate a timestamp for shared log files
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    main_log_file = log_dir / f"simulation_{timestamp}.log"
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(default_level)
    
    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create formatters
    format_str = LOG_FORMATS.get(log_format, LOG_FORMATS["detailed"])
    formatter = logging.Formatter(format_str)
    
    # Add console handler
    if console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # Add shared file handler
    file_handler = logging.FileHandler(main_log_file)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # Add memory tracking if requested
    if track_memory:
        memory_filter = MemoryUsageFilter()
        for handler in root_logger.handlers:
            handler.addFilter(memory_filter)
    
    # Store the main log file path for reference
    global _MAIN_LOG_FILE
    _MAIN_LOG_FILE = main_log_file
    
    # Configure component-specific loggers
    for component, level in DEFAULT_LOG_LEVELS.items():
        component_logger = logging.getLogger(component)
        component_logger.setLevel(level)
    
    # Log the setup completion
    init_logger = logging.getLogger("logging_utils")
    init_logger.info(f"Global logging system initialized. Main log file: {main_log_file}")
    init_logger.info(f"Project root identified as: {project_root}")

def example_usage():
    """Example of how to use this module."""
    # Basic usage
    logger = get_logger(__name__)
    logger.info("This is a basic log message")
    
    # Memory tracking
    memory_logger = get_logger("memory_example", log_format="memory", track_memory=True)
    memory_logger.info("This log includes memory usage")
    
    # Performance tracking
    perf_logger = get_logger("performance_example", log_format="performance", track_time=True)
    perf_logger.info("Starting operation")
    import time
    time.sleep(1)
    perf_logger.info("Operation completed")
    
    # Configure all logging
    configure_logging(
        config={
            "log_levels": {"core_simulation_framework": "DEBUG"},
            "console_format": "simple",
            "file_format": "detailed",
            "separate_component_logs": True,
        },
        log_dir="simulation_logs"
    )
    
    # Get component logger after configuration
    core_logger = logging.getLogger("core_simulation_framework")
    core_logger.debug("This is a debug message from core_simulation_framework")
    
    # Use the centralized logger
    sim_logger = get_simulation_logger("simulation_test")
    sim_logger.info("This is a message from the centralized logger")
    
    # Set up global logging
    setup_global_logging(track_memory=True)
    
    # Get a logger after global setup
    global_logger = get_simulation_logger("after_global_setup")
    global_logger.info("This message should appear in the shared log file")

if __name__ == "__main__":
    example_usage() 