#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Parameter Validation Utilities

Provides standardized parameter validation for the Forest Fire Simulation Framework.
This centralizes validation logic that was previously scattered across different modules.
"""

import logging
import math
from typing import Any, Dict, List, Optional, Set, Tuple, Union, Callable
from dataclasses import dataclass, field

# Setup logger
logger = logging.getLogger(__name__)

class ParameterValidator:
    """
    Centralized parameter validation.
    
    This class provides methods for validating configuration parameters
    and ensuring they meet the requirements of the simulation.
    """
    
    def __init__(self):
        """Initialize the validator."""
        # Registry of parameter constraints
        self.parameter_constraints = {}
        # Parameter usage tracking
        self.parameter_usage = {}
        # Registry of validation functions
        self.validation_functions = {}
        
        # Register common validation functions
        self._register_validation_functions()
    
    def _register_validation_functions(self):
        """Register built-in validation functions."""
        self.register_validator("positive_int", self.validate_positive_int)
        self.register_validator("non_negative_int", self.validate_non_negative_int)
        self.register_validator("positive_float", self.validate_positive_float)
        self.register_validator("non_negative_float", self.validate_non_negative_float)
        self.register_validator("probability", self.validate_probability)
        self.register_validator("grid_size", self.validate_grid_size)
        self.register_validator("in_range", self.validate_in_range)
        self.register_validator("file_exists", self.validate_file_exists)
        self.register_validator("dir_exists", self.validate_dir_exists)
        self.register_validator("one_of", self.validate_one_of)
        
    def register_validator(self, name: str, func: Callable) -> None:
        """
        Register a validation function.
        
        Args:
            name: Name of the validation function
            func: Validation function that takes (value, context) and returns (is_valid, error_message)
        """
        self.validation_functions[name] = func
        logger.debug(f"Registered validator: {name}")
    
    def register_parameter(self, name: str, constraints: Dict[str, Any]) -> None:
        """
        Register constraints for a parameter.
        
        Args:
            name: Parameter name
            constraints: Dictionary of constraints
        """
        self.parameter_constraints[name] = constraints
        logger.debug(f"Registered constraints for parameter: {name}")
    
    def register_parameters(self, parameters: Dict[str, Dict[str, Any]]) -> None:
        """
        Register multiple parameters at once.
        
        Args:
            parameters: Dictionary mapping parameter names to constraints
        """
        for name, constraints in parameters.items():
            self.register_parameter(name, constraints)
    
    def track_usage(self, name: str, value: Any, source: str, 
                  is_fallback: bool = False, notes: str = "") -> None:
        """
        Track usage of a parameter.
        
        Args:
            name: Parameter name
            value: Parameter value
            source: Source of the parameter (module/function)
            is_fallback: Whether this is a fallback value
            notes: Additional notes about the parameter usage
        """
        if name not in self.parameter_usage:
            self.parameter_usage[name] = []
        
        self.parameter_usage[name].append({
            "value": value,
            "source": source,
            "is_fallback": is_fallback,
            "notes": notes,
            "validated": False
        })
    
    def validate_parameter(self, name: str, value: Any, context: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
        """
        Validate a parameter against its constraints.
        
        Args:
            name: Parameter name
            value: Parameter value
            context: Additional context for validation
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if name not in self.parameter_constraints:
            # No constraints registered, assume valid
            return True, ""
        
        constraints = self.parameter_constraints[name]
        
        # Initialize context if not provided
        context = context or {}
        context["parameter_name"] = name
        
        # Track that validation occurred
        if name in self.parameter_usage and self.parameter_usage[name]:
            self.parameter_usage[name][-1]["validated"] = True
        
        for validator_name, args in constraints.items():
            if validator_name in self.validation_functions:
                # Add args to context
                validation_context = context.copy()
                validation_context["validator_args"] = args
                
                # Call validation function
                is_valid, error = self.validation_functions[validator_name](value, validation_context)
                if not is_valid:
                    return False, error
        
        return True, ""
    
    def create_tracked_parameter(self, name: str, value: Any, default_value: Any, 
                             source: str = "", use_default_if_none: bool = True) -> Any:
        """
        Create a tracked parameter with fallback to default.
        
        Args:
            name: Parameter name
            value: Parameter value (may be None)
            default_value: Default value if value is None
            source: Source of the parameter
            use_default_if_none: Whether to use default if value is None
            
        Returns:
            Value or default_value
        """
        if value is None and use_default_if_none:
            self.track_usage(name, default_value, source, is_fallback=True, 
                           notes=f"Using default value: {default_value}")
            return default_value
        else:
            self.track_usage(name, value, source)
            return value
    
    def save_report(self, filepath: str) -> None:
        """
        Save validation report to a file.
        
        Args:
            filepath: Path to save the report to
        """
        import json
        from pathlib import Path
        
        # Create directory if it doesn't exist
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        report = {
            "parameter_constraints": self.parameter_constraints,
            "parameter_usage": self.parameter_usage
        }
        
        try:
            with open(filepath, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            logger.info(f"Parameter validation report saved to: {filepath}")
        except Exception as e:
            logger.error(f"Error saving parameter validation report: {e}")
    
    def print_summary(self) -> None:
        """Print summary of parameter usage."""
        print("\n===== PARAMETER VALIDATION SUMMARY =====")
        
        # Count parameters
        total_params = len(self.parameter_usage)
        validated_params = 0
        fallback_params = 0
        
        for name, usages in self.parameter_usage.items():
            # Count validated parameters
            if any(usage.get("validated", False) for usage in usages):
                validated_params += 1
            
            # Count fallback parameters
            if any(usage.get("is_fallback", False) for usage in usages):
                fallback_params += 1
        
        print(f"Total parameters tracked: {total_params}")
        print(f"Parameters validated: {validated_params}")
        print(f"Parameters using fallback values: {fallback_params}")
        print("=====================================")
    
    # Built-in validation functions
    
    def validate_positive_int(self, value: Any, context: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate that value is a positive integer."""
        try:
            # Try to convert to int first
            int_value = int(value)
            
            if int_value <= 0:
                return False, f"{context['parameter_name']} must be a positive integer"
            
            return True, ""
        except (ValueError, TypeError):
            return False, f"{context['parameter_name']} must be a valid integer"
    
    def validate_non_negative_int(self, value: Any, context: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate that value is a non-negative integer."""
        try:
            # Try to convert to int first
            int_value = int(value)
            
            if int_value < 0:
                return False, f"{context['parameter_name']} must be a non-negative integer"
            
            return True, ""
        except (ValueError, TypeError):
            return False, f"{context['parameter_name']} must be a valid integer"
    
    def validate_positive_float(self, value: Any, context: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate that value is a positive float."""
        try:
            # Try to convert to float first
            float_value = float(value)
            
            if float_value <= 0:
                return False, f"{context['parameter_name']} must be a positive number"
            
            return True, ""
        except (ValueError, TypeError):
            return False, f"{context['parameter_name']} must be a valid number"
    
    def validate_non_negative_float(self, value: Any, context: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate that value is a non-negative float."""
        try:
            # Try to convert to float first
            float_value = float(value)
            
            if float_value < 0:
                return False, f"{context['parameter_name']} must be a non-negative number"
            
            return True, ""
        except (ValueError, TypeError):
            return False, f"{context['parameter_name']} must be a valid number"
    
    def validate_probability(self, value: Any, context: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate that value is a probability (float between 0 and 1)."""
        try:
            # Try to convert to float first
            float_value = float(value)
            
            if float_value < 0 or float_value > 1:
                return False, f"{context['parameter_name']} must be between 0 and 1"
            
            return True, ""
        except (ValueError, TypeError):
            return False, f"{context['parameter_name']} must be a valid probability (float between 0 and 1)"
    
    def validate_grid_size(self, value: Any, context: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate that value is a valid grid size (int or tuple of ints)."""
        # Handle int case
        if isinstance(value, int):
            if value <= 0:
                return False, f"{context['parameter_name']} must be a positive integer"
            return True, ""
        
        # Handle tuple case
        if isinstance(value, tuple) or isinstance(value, list):
            if len(value) != 2:
                return False, f"{context['parameter_name']} must be an int or a tuple of two ints"
            
            try:
                x, y = int(value[0]), int(value[1])
                if x <= 0 or y <= 0:
                    return False, f"{context['parameter_name']} dimensions must be positive"
                return True, ""
            except (ValueError, TypeError):
                return False, f"{context['parameter_name']} must contain valid integers"
        
        return False, f"{context['parameter_name']} must be an int or tuple of two ints"
    
    def validate_in_range(self, value: Any, context: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate that value is in a specified range."""
        args = context["validator_args"]
        
        try:
            min_val = args.get("min")
            max_val = args.get("max")
            
            if min_val is not None and value < min_val:
                return False, f"{context['parameter_name']} must be at least {min_val}"
            
            if max_val is not None and value > max_val:
                return False, f"{context['parameter_name']} must be at most {max_val}"
            
            return True, ""
        except Exception:
            return False, f"{context['parameter_name']} must be a number in the valid range"
    
    def validate_file_exists(self, value: Any, context: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate that a file exists."""
        if not value:  # Allow empty value if not required
            required = context.get("validator_args", {}).get("required", False)
            if not required:
                return True, ""
            return False, f"{context['parameter_name']} is required"
        
        try:
            from pathlib import Path
            path = Path(value)
            
            if not path.is_file():
                return False, f"File not found: {value}"
            
            return True, ""
        except Exception:
            return False, f"Invalid file path: {value}"
    
    def validate_dir_exists(self, value: Any, context: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate that a directory exists."""
        if not value:  # Allow empty value if not required
            required = context.get("validator_args", {}).get("required", False)
            if not required:
                return True, ""
            return False, f"{context['parameter_name']} is required"
        
        try:
            from pathlib import Path
            path = Path(value)
            
            if not path.is_dir():
                return False, f"Directory not found: {value}"
            
            return True, ""
        except Exception:
            return False, f"Invalid directory path: {value}"
    
    def validate_one_of(self, value: Any, context: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate that value is one of the allowed values."""
        allowed_values = context.get("validator_args", {}).get("values", [])
        
        if value not in allowed_values:
            return False, f"{context['parameter_name']} must be one of: {', '.join(str(v) for v in allowed_values)}"
        
        return True, ""


def verify_extents(source: str, name: str, expected: Any, actual: Any, tolerance: float = 0.001):
    """
    Common function to verify geographical or other extents.
    
    This is a helper function used by the validation system to compare
    expected vs. actual geographical extents.
    
    Args:
        source: Source module/function
        name: Parameter name
        expected: Expected extents
        actual: Actual extents
        tolerance: Tolerance for floating point comparison
    """
    # Get the global validator instance
    global validator
    
    # Convert both to the same format if possible
    try:
        # Handle common extent formats
        expected_points = _normalize_extents(expected)
        actual_points = _normalize_extents(actual)
        
        # Check if they're close enough
        diffs = []
        for (ex, ey), (ax, ay) in zip(expected_points, actual_points):
            x_diff = abs(ex - ax)
            y_diff = abs(ey - ay)
            diffs.append(x_diff)
            diffs.append(y_diff)
        
        max_diff = max(diffs) if diffs else 0
        
        # Track the result
        validator.track_usage(
            name,
            actual,
            source,
            is_fallback=False,
            notes=f"Expected: {expected}; Max difference: {max_diff}"
        )
        
    except Exception as e:
        # If we can't compare them numerically, just log both
        validator.track_usage(
            name,
            actual,
            source,
            is_fallback=False,
            notes=f"Expected: {expected}; Exception during comparison: {str(e)}"
        )

def _normalize_extents(extents):
    """Normalize extents to a list of (x, y) tuples."""
    # Common formats:
    # 1. [xmin, ymin, xmax, ymax]
    # 2. {"minx": x1, "miny": y1, "maxx": x2, "maxy": y2}
    # 3. [(x1, y1), (x2, y2)]
    # 4. {"min": (x1, y1), "max": (x2, y2)}
    
    # Format 1: List/tuple of 4 values
    if isinstance(extents, (list, tuple)) and len(extents) == 4:
        xmin, ymin, xmax, ymax = extents
        return [(xmin, ymin), (xmax, ymax)]
    
    # Format 2: Dict with minx, miny, maxx, maxy
    if isinstance(extents, dict) and all(k in extents for k in ["minx", "miny", "maxx", "maxy"]):
        return [(extents["minx"], extents["miny"]), (extents["maxx"], extents["maxy"])]
    
    # Format 3: List of two (x, y) tuples
    if isinstance(extents, (list, tuple)) and len(extents) == 2 and all(isinstance(p, (list, tuple)) and len(p) == 2 for p in extents):
        return [(extents[0][0], extents[0][1]), (extents[1][0], extents[1][1])]
    
    # Format 4: Dict with min and max points
    if isinstance(extents, dict) and "min" in extents and "max" in extents:
        min_point = extents["min"]
        max_point = extents["max"]
        if isinstance(min_point, (list, tuple)) and isinstance(max_point, (list, tuple)) and len(min_point) == 2 and len(max_point) == 2:
            return [(min_point[0], min_point[1]), (max_point[0], max_point[1])]
    
    # Unknown format, raise error
    raise ValueError(f"Unknown extent format: {extents}")


class ValidationContext:
    """
    Context manager for parameter validation.
    
    This class provides a context manager for validating multiple parameters
    in a single function or method call.
    """
    
    def __init__(self, source: str):
        """
        Initialize the validation context.
        
        Args:
            source: Source of the parameters (module/function)
        """
        self.source = source
        self.errors = []
        self.parameters = {}
    
    def __enter__(self):
        """Enter the context."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context."""
        # If there are validation errors, log them
        if self.errors:
            logger.warning(f"Validation errors in {self.source}: {', '.join(self.errors)}")
        
        # Don't suppress exceptions
        return False
    
    def register_parameter(self, name: str, constraints: Dict[str, Any]):
        """
        Register a parameter with constraints.
        
        Args:
            name: Parameter name
            constraints: Dictionary of constraints
        """
        validator.register_parameter(name, constraints)
        return self
    
    def validate_parameter(self, name: str, value: Any) -> bool:
        """
        Validate a parameter within this context.
        
        Args:
            name: Parameter name
            value: Parameter value
            
        Returns:
            True if valid, False if invalid
        """
        is_valid, error = validator.validate_parameter(name, value)
        
        if not is_valid:
            self.errors.append(error)
        
        self.parameters[name] = {
            "value": value,
            "valid": is_valid,
            "error": error if not is_valid else ""
        }
        
        return is_valid


# Create a global validator instance
validator = ParameterValidator()

class ConfigValidator:
    """
    Consolidated validation class that provides standardized validation methods
    for all configuration parameters used throughout the simulation system.
    
    This class reduces code duplication by centralizing validation logic
    and providing consistent error messages.
    """
    
    @staticmethod
    def validate_grid_size(grid_size: Union[int, Tuple[int, int]], max_size: int = 10000) -> Tuple[bool, str]:
        """Validate grid size parameter."""
        if isinstance(grid_size, int):
            if grid_size <= 0:
                return False, f"Grid size must be positive, got {grid_size}"
            if grid_size > max_size:
                return False, f"Grid size {grid_size} exceeds maximum {max_size}"
            return True, "Valid integer grid size"
        
        elif isinstance(grid_size, (tuple, list)) and len(grid_size) == 2:
            width, height = grid_size
            if not all(isinstance(x, int) and x > 0 for x in grid_size):
                return False, f"Grid dimensions must be positive integers, got {grid_size}"
            if max(grid_size) > max_size:
                return False, f"Grid dimension {max(grid_size)} exceeds maximum {max_size}"
            return True, "Valid tuple grid size"
        
        else:
            return False, f"Grid size must be int or tuple of 2 ints, got {type(grid_size)}"
    
    @staticmethod
    def validate_probability(value: float, param_name: str = "probability") -> Tuple[bool, str]:
        """Validate probability parameter (0-1 range)."""
        if not isinstance(value, (int, float)):
            return False, f"{param_name} must be numeric, got {type(value)}"
        if not 0 <= value <= 1:
            return False, f"{param_name} must be between 0 and 1, got {value}"
        return True, f"Valid {param_name}"
    
    @staticmethod
    def validate_positive_number(value: Union[int, float], param_name: str = "value", 
                                min_value: float = 0, inclusive: bool = False) -> Tuple[bool, str]:
        """Validate positive number parameter."""
        if not isinstance(value, (int, float)):
            return False, f"{param_name} must be numeric, got {type(value)}"
        
        if inclusive and value < min_value:
            return False, f"{param_name} must be >= {min_value}, got {value}"
        elif not inclusive and value <= min_value:
            return False, f"{param_name} must be > {min_value}, got {value}"
        
        return True, f"Valid {param_name}"
    
    @staticmethod
    def validate_range(value: Union[int, float], param_name: str, 
                      min_val: float, max_val: float, inclusive: bool = True) -> Tuple[bool, str]:
        """Validate parameter within a specific range."""
        if not isinstance(value, (int, float)):
            return False, f"{param_name} must be numeric, got {type(value)}"
        
        if inclusive:
            if not min_val <= value <= max_val:
                return False, f"{param_name} must be between {min_val} and {max_val} (inclusive), got {value}"
        else:
            if not min_val < value < max_val:
                return False, f"{param_name} must be between {min_val} and {max_val} (exclusive), got {value}"
        
        return True, f"Valid {param_name}"
    
    @staticmethod
    def validate_memory_config(config_dict: Dict[str, Any]) -> List[str]:
        """
        Validate all memory-related configuration parameters.
        
        Returns:
            List of validation error messages (empty if all valid)
        """
        errors = []
        
        # Grid size validation
        grid_size = config_dict.get('grid_size', (100, 100))
        valid, msg = ConfigValidator.validate_grid_size(grid_size)
        if not valid:
            errors.append(f"grid_size: {msg}")
        
        # Memory optimization level
        mem_level = config_dict.get('memory_optimization_level', 0)
        valid, msg = ConfigValidator.validate_range(mem_level, 'memory_optimization_level', 0, 2, True)
        if not valid:
            errors.append(msg)
        
        # Tile size
        tile_size = config_dict.get('tile_size', 200)
        valid, msg = ConfigValidator.validate_positive_number(tile_size, 'tile_size', 1, False)
        if not valid:
            errors.append(msg)
        
        # Memory percentage
        mem_percent = config_dict.get('max_memory_percent', 75)
        valid, msg = ConfigValidator.validate_range(mem_percent, 'max_memory_percent', 1, 100, True)
        if not valid:
            errors.append(msg)
        
        return errors
    
    @staticmethod
    def validate_fire_behavior_config(config_dict: Dict[str, Any]) -> List[str]:
        """
        Validate all fire behavior configuration parameters.
        
        Returns:
            List of validation error messages (empty if all valid)
        """
        errors = []
        
        # Probability parameters
        prob_params = ['spread_probability', 'vertical_spread', 'downward_spread', 
                      'ember_probability', 'ember_ignition']
        for param in prob_params:
            if param in config_dict:
                valid, msg = ConfigValidator.validate_probability(config_dict[param], param)
                if not valid:
                    errors.append(msg)
        
        # Positive number parameters
        positive_params = ['wind_speed', 'ember_distance']
        for param in positive_params:
            if param in config_dict:
                valid, msg = ConfigValidator.validate_positive_number(config_dict[param], param, 0, True)
                if not valid:
                    errors.append(msg)
        
        # Range parameters (0-1)
        range_01_params = ['wind_influence', 'slope_influence', 'terrain_effect_strength', 'diagonal_factor']
        for param in range_01_params:
            if param in config_dict:
                valid, msg = ConfigValidator.validate_range(config_dict[param], param, 0, 1, True)
                if not valid:
                    errors.append(msg)
        
        return errors

# Add consolidated validation function
def validate_complete_config(config: Union[Dict[str, Any], 'ModelConfig']) -> Tuple[bool, List[str]]:
    """
    Perform comprehensive validation of a complete configuration.
    
    Args:
        config: Configuration dictionary or ModelConfig instance
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    if hasattr(config, 'to_dict'):
        config_dict = config.to_dict()
    else:
        config_dict = config
    
    all_errors = []
    
    # Validate different parameter groups
    all_errors.extend(ConfigValidator.validate_memory_config(config_dict))
    all_errors.extend(ConfigValidator.validate_fire_behavior_config(config_dict))
    
    # Additional validations specific to the combined configuration
    # Check for parameter consistency
    if 'save_interval' in config_dict and 'history_keyframe_interval' in config_dict:
        save_interval = config_dict['save_interval']
        keyframe_interval = config_dict['history_keyframe_interval']
        if save_interval % keyframe_interval != 0:
            all_errors.append(f"save_interval ({save_interval}) should be a multiple of history_keyframe_interval ({keyframe_interval})")
    
    return len(all_errors) == 0, all_errors 