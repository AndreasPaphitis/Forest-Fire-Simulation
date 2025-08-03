"""
Error Handling Module

Provides standardized error handling and custom exceptions for the simulation.
"""

import logging
import functools
import traceback
import warnings
from typing import List, Dict, Any, Optional, Union, Callable
import inspect

logger = logging.getLogger(__name__)

# Custom exceptions
class SimulationError(Exception):
    """Base class for all simulation-related exceptions."""
    pass

class ModelError(SimulationError):
    """Exception raised for errors in the forest model."""
    pass

class ConfigurationError(SimulationError):
    """Exception raised for errors in configuration."""
    pass

class DataProcessingError(SimulationError):
    """Exception raised for errors in data processing."""
    pass

class MemoryLimitError(SimulationError):
    """Exception raised for memory-related errors."""
    pass

class FileIOError(SimulationError):
    """Exception raised for I/O-related errors."""
    pass

class ValidationError(SimulationError):
    """Exception raised for validation errors."""
    pass

# Error handling decorators
def handle_errors(func=None, *, reraise=False, default_return=None, error_type=SimulationError, 
                log_level=logging.ERROR, log_traceback=True):
    """
    Decorator for standardized error handling.
    
    Args:
        func: Function to decorate
        reraise: Whether to reraise the exception
        default_return: Value to return on error
        error_type: Type of exception to catch
        log_level: Logging level for errors
        log_traceback: Whether to log traceback
        
    Returns:
        Decorated function
    """
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except error_type as e:
                # Get logger function based on level
                if isinstance(log_level, str):
                    level_name_str = log_level.lower()
                elif isinstance(log_level, int):
                    level_name_str = logging.getLevelName(log_level).lower()
                else: # Fallback for unexpected type
                    logger.warning(f"Unexpected log_level type: {type(log_level)}. Defaulting to 'error'.")
                    level_name_str = "error"
                logger_func = getattr(logger, level_name_str, logger.error)
                
                # Log the error
                func_name = f.__qualname__ if hasattr(f, '__qualname__') else f.__name__
                logger_func(f"Error in {func_name}: {str(e)}")
                
                # Log traceback if requested
                if log_traceback:
                    logger.debug(traceback.format_exc())
                
                # Reraise or return default
                if reraise:
                    raise
                return default_return
            except Exception as e:
                # Get logger function based on level
                # For unexpected errors, always log as error, but respect verbosity of traceback via debug
                logger_func = logger.error # Directly use logger.error for unexpected exceptions
                
                # Log the error
                func_name = f.__qualname__ if hasattr(f, '__qualname__') else f.__name__
                logger_func(f"Error in {func_name}: {str(e)}")
                logger.debug(traceback.format_exc())
                
                # Reraise as SimulationError or return default
                if reraise:
                    raise SimulationError(f"Unexpected error in {f.__name__}: {str(e)}") from e
                return default_return
        return wrapper
    
    if func is None:
        return decorator
    return decorator(func)

def log_errors(func=None, *, level=logging.ERROR, include_traceback=True):
    """
    Decorator to log errors without handling them.
    
    Args:
        func: Function to decorate
        level: Logging level for errors
        include_traceback: Whether to include traceback in log
        
    Returns:
        Decorated function
    """
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                # Get logger function based on level
                if isinstance(level, str):
                    level_name_str = level.lower()
                elif isinstance(level, int):
                    level_name_str = logging.getLevelName(level).lower()
                else: # Fallback for unexpected type
                    logger.warning(f"Unexpected log level type: {type(level)}. Defaulting to 'error'.")
                    level_name_str = "error"
                logger_func = getattr(logger, level_name_str, logger.error)
                
                # Log the error
                func_name = f.__qualname__ if hasattr(f, '__qualname__') else f.__name__
                logger_func(f"Error in {func_name}: {str(e)}")
                
                # Log traceback if requested
                if include_traceback:
                    logger.debug(traceback.format_exc())
                
                # Always reraise the original exception
                raise
        return wrapper
    
    if func is None:
        return decorator
    return decorator(func)

def deprecated(reason: str, version: Optional[str] = None, alternative: Optional[str] = None):
    """
    Decorator to mark functions as deprecated.
    
    Args:
        reason: Reason for deprecation
        version: Version in which the function was deprecated
        alternative: Alternative function to use
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Construct deprecation message
            message = f"Function {func.__name__} is deprecated: {reason}"
            if version:
                message += f" (since version {version})"
            if alternative:
                message += f". Use {alternative} instead"
            
            # Add calling location context to help debugging
            caller_frame = inspect.currentframe().f_back
            if caller_frame:
                frame_info = inspect.getframeinfo(caller_frame)
                message += f" - called from {frame_info.filename}:{frame_info.lineno}"
            
            # Emit deprecation warning
            warnings.warn(
                message,
                category=DeprecationWarning,
                stacklevel=2
            )
            return func(*args, **kwargs)
        return wrapper
    return decorator

class ErrorContext:
    """
    Context manager for standardized error handling.
    
    This class provides a convenient way to handle errors in a specific context
    without having to use decorators.
    
    Example:
        with ErrorContext("Processing tile", reraise=False) as ctx:
            # Code that might raise errors
            result = process_tile(x, y)
            ctx.set_result(result)
        
        if ctx.error:
            # Handle error
            print(f"Error: {ctx.error}")
        else:
            # Use result
            use_result(ctx.result)
    """
    
    def __init__(self, context: str, error_type=Exception, reraise: bool = True, 
                log_level=logging.ERROR, log_traceback: bool = True):
        """
        Initialize the error context.
        
        Args:
            context: Context description for error messages
            error_type: Type of exception to catch
            reraise: Whether to reraise exceptions
            log_level: Logging level for errors
            log_traceback: Whether to log tracebacks
        """
        self.context = context
        self.error_type = error_type
        self.reraise = reraise
        self.log_level = log_level
        self.log_traceback = log_traceback
        self.error = None
        self.result = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # Get logger function based on level
            if isinstance(self.log_level, str):
                level_name_str = self.log_level.lower()
            elif isinstance(self.log_level, int):
                level_name_str = logging.getLevelName(self.log_level).lower()
            else: # Fallback for unexpected type
                logger.warning(f"Unexpected log_level type: {type(self.log_level)}. Defaulting to 'error'.")
                level_name_str = "error"
            logger_func = getattr(logger, level_name_str, logger.error)
            
            # Store the error for later access
            self.error = exc_val
            
            # Log the error
            logger_func(f"Error in {self.context}: {str(exc_val)}")
            
            # Log traceback if requested
            if self.log_traceback:
                logger.debug("".join(traceback.format_tb(exc_tb)))
            
            # Handle based on error type
            if issubclass(exc_type, self.error_type):
                return not self.reraise
            
            # For unexpected errors, wrap in SimulationError if reraising
            if self.reraise:
                raise SimulationError(f"Unexpected error in {self.context}: {str(exc_val)}") from exc_val
            return True
    
    def set_result(self, result):
        """Set the result for later access."""
        self.result = result 