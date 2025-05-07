#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Configuration validation module for the Forest Fire Simulation Framework.

This module provides functions and classes for validating configuration parameters,
ensuring they are within acceptable ranges and conform to required constraints.
"""

import os
import json
import logging
from typing import Any, Dict, List, Tuple, Optional, Union, Set
from enum import Enum

# Import logging utilities
try:
    from logging_utils import get_logger
    logger = get_logger("config_validation")
except ImportError:
    logging.basicConfig(level=logging.INFO, 
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("config_validation")

class ValidationLevel(Enum):
    """Validation level used to determine action on validation failure."""
    WARNING = 0   # Log warning but continue
    ERROR = 1     # Raise exception and abort
    FIX = 2       # Automatically fix the value to nearest valid value

class ValidationResult:
    """Result of a configuration parameter validation."""
    
    def __init__(self, 
                 is_valid: bool, 
                 param_name: str, 
                 value: Any, 
                 message: str = None,
                 fixed_value: Any = None,
                 level: ValidationLevel = ValidationLevel.ERROR):
        """
        Initialize a validation result.
        
        Args:
            is_valid: Whether the parameter value is valid
            param_name: Name of the parameter being validated
            value: The parameter value that was validated
            message: Optional message explaining validation failure
            fixed_value: Value to use if automatic fixing is enabled
            level: Validation level determining action on failure
        """
        self.is_valid = is_valid
        self.param_name = param_name
        self.value = value
        self.message = message
        self.fixed_value = fixed_value
        self.level = level
    
    def __bool__(self):
        """Return whether the validation passed."""
        return self.is_valid
    
    def handle(self):
        """
        Handle the validation result based on the validation level.
        
        Returns:
            The original value if valid, or fixed value if fixing is enabled,
            or raises an exception if error level and invalid.
        """
        if self.is_valid:
            return self.value
        
        # Not valid, handle based on level
        if self.level == ValidationLevel.WARNING:
            logger.warning(f"Parameter '{self.param_name}' validation warning: {self.message}")
            return self.value
        
        elif self.level == ValidationLevel.ERROR:
            error_msg = f"Parameter '{self.param_name}' validation error: {self.message}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        elif self.level == ValidationLevel.FIX:
            logger.warning(f"Parameter '{self.param_name}' auto-fixed: {self.message}")
            return self.fixed_value
        
        # Default fallback
        return self.value

class ParameterValidator:
    """Base class for parameter validators."""
    
    def __init__(self, param_name: str, level: ValidationLevel = ValidationLevel.ERROR):
        """
        Initialize the validator.
        
        Args:
            param_name: Name of the parameter to validate
            level: Validation level to apply
        """
        self.param_name = param_name
        self.level = level
    
    def validate(self, value: Any) -> ValidationResult:
        """
        Validate a parameter value.
        
        Args:
            value: Value to validate
            
        Returns:
            ValidationResult with the result of validation
        """
        # Base implementation always accepts
        return ValidationResult(
            is_valid=True,
            param_name=self.param_name,
            value=value,
            level=self.level
        )

class RangeValidator(ParameterValidator):
    """Validator for numeric parameters with a valid range."""
    
    def __init__(self, 
                 param_name: str, 
                 min_value: Optional[float] = None, 
                 max_value: Optional[float] = None,
                 include_min: bool = True,
                 include_max: bool = True,
                 level: ValidationLevel = ValidationLevel.ERROR):
        """
        Initialize a range validator.
        
        Args:
            param_name: Name of the parameter to validate
            min_value: Minimum allowed value (or None for no minimum)
            max_value: Maximum allowed value (or None for no maximum)
            include_min: Whether the minimum value is included in the valid range
            include_max: Whether the maximum value is included in the valid range
            level: Validation level to apply
        """
        super().__init__(param_name, level)
        self.min_value = min_value
        self.max_value = max_value
        self.include_min = include_min
        self.include_max = include_max
    
    def validate(self, value: Union[int, float]) -> ValidationResult:
        """
        Validate that a numeric value is within the specified range.
        
        Args:
            value: Numeric value to validate
            
        Returns:
            ValidationResult with the result of validation
        """
        # Check if value is numeric
        if not isinstance(value, (int, float)):
            return ValidationResult(
                is_valid=False,
                param_name=self.param_name,
                value=value,
                message=f"Expected numeric value, got {type(value).__name__}",
                level=self.level
            )
        
        # Check minimum value
        if self.min_value is not None:
            if self.include_min and value < self.min_value:
                fixed_value = self.min_value
                return ValidationResult(
                    is_valid=False,
                    param_name=self.param_name,
                    value=value,
                    message=f"Value {value} is less than minimum {self.min_value}",
                    fixed_value=fixed_value,
                    level=self.level
                )
            elif not self.include_min and value <= self.min_value:
                fixed_value = self.min_value + 1 if isinstance(value, int) else self.min_value + 1e-10
                return ValidationResult(
                    is_valid=False,
                    param_name=self.param_name,
                    value=value,
                    message=f"Value {value} is less than or equal to exclusive minimum {self.min_value}",
                    fixed_value=fixed_value,
                    level=self.level
                )
        
        # Check maximum value
        if self.max_value is not None:
            if self.include_max and value > self.max_value:
                fixed_value = self.max_value
                return ValidationResult(
                    is_valid=False,
                    param_name=self.param_name,
                    value=value,
                    message=f"Value {value} is greater than maximum {self.max_value}",
                    fixed_value=fixed_value,
                    level=self.level
                )
            elif not self.include_max and value >= self.max_value:
                fixed_value = self.max_value - 1 if isinstance(value, int) else self.max_value - 1e-10
                return ValidationResult(
                    is_valid=False,
                    param_name=self.param_name,
                    value=value,
                    message=f"Value {value} is greater than or equal to exclusive maximum {self.max_value}",
                    fixed_value=fixed_value,
                    level=self.level
                )
        
        # Value is within range
        return ValidationResult(
            is_valid=True,
            param_name=self.param_name,
            value=value,
            level=self.level
        )

class ChoiceValidator(ParameterValidator):
    """Validator for parameters with a set of valid choices."""
    
    def __init__(self, 
                 param_name: str, 
                 valid_choices: Set[Any],
                 level: ValidationLevel = ValidationLevel.ERROR):
        """
        Initialize a choice validator.
        
        Args:
            param_name: Name of the parameter to validate
            valid_choices: Set of valid choices
            level: Validation level to apply
        """
        super().__init__(param_name, level)
        self.valid_choices = set(valid_choices)
    
    def validate(self, value: Any) -> ValidationResult:
        """
        Validate that a value is one of the valid choices.
        
        Args:
            value: Value to validate
            
        Returns:
            ValidationResult with the result of validation
        """
        if value not in self.valid_choices:
            return ValidationResult(
                is_valid=False,
                param_name=self.param_name,
                value=value,
                message=f"Value {value} is not one of the valid choices: {', '.join(map(str, self.valid_choices))}",
                fixed_value=next(iter(self.valid_choices)) if self.valid_choices else None,
                level=self.level
            )
        
        return ValidationResult(
            is_valid=True,
            param_name=self.param_name,
            value=value,
            level=self.level
        )

class TypeValidator(ParameterValidator):
    """Validator for parameters with a specific type."""
    
    def __init__(self, 
                 param_name: str, 
                 expected_type: Union[type, Tuple[type, ...]],
                 level: ValidationLevel = ValidationLevel.ERROR):
        """
        Initialize a type validator.
        
        Args:
            param_name: Name of the parameter to validate
            expected_type: Expected type or tuple of types
            level: Validation level to apply
        """
        super().__init__(param_name, level)
        self.expected_type = expected_type
    
    def validate(self, value: Any) -> ValidationResult:
        """
        Validate that a value is of the expected type.
        
        Args:
            value: Value to validate
            
        Returns:
            ValidationResult with the result of validation
        """
        if not isinstance(value, self.expected_type):
            type_names = (
                [t.__name__ for t in self.expected_type] 
                if isinstance(self.expected_type, tuple) 
                else [self.expected_type.__name__]
            )
            return ValidationResult(
                is_valid=False,
                param_name=self.param_name,
                value=value,
                message=f"Expected type(s) {', '.join(type_names)}, got {type(value).__name__}",
                level=self.level
            )
        
        return ValidationResult(
            is_valid=True,
            param_name=self.param_name,
            value=value,
            level=self.level
        )

class ConfigurationValidator:
    """
    Validator for configuration parameters.
    
    This class maintains a registry of validators for different parameters
    and provides methods for validating configuration objects.
    """
    
    def __init__(self):
        """Initialize the configuration validator."""
        self.validators = {}
    
    def register_validator(self, validator: ParameterValidator):
        """
        Register a validator for a parameter.
        
        Args:
            validator: Validator to register
        """
        if validator.param_name in self.validators:
            self.validators[validator.param_name].append(validator)
        else:
            self.validators[validator.param_name] = [validator]
    
    def register_range(self, 
                       param_name: str, 
                       min_value: Optional[float] = None, 
                       max_value: Optional[float] = None,
                       include_min: bool = True,
                       include_max: bool = True,
                       level: ValidationLevel = ValidationLevel.ERROR):
        """
        Register a range validator for a parameter.
        
        Args:
            param_name: Name of the parameter to validate
            min_value: Minimum allowed value (or None for no minimum)
            max_value: Maximum allowed value (or None for no maximum)
            include_min: Whether the minimum value is included in the valid range
            include_max: Whether the maximum value is included in the valid range
            level: Validation level to apply
        """
        validator = RangeValidator(
            param_name=param_name,
            min_value=min_value,
            max_value=max_value,
            include_min=include_min,
            include_max=include_max,
            level=level
        )
        self.register_validator(validator)
    
    def register_choice(self, 
                        param_name: str, 
                        valid_choices: Set[Any],
                        level: ValidationLevel = ValidationLevel.ERROR):
        """
        Register a choice validator for a parameter.
        
        Args:
            param_name: Name of the parameter to validate
            valid_choices: Set of valid choices
            level: Validation level to apply
        """
        validator = ChoiceValidator(
            param_name=param_name,
            valid_choices=valid_choices,
            level=level
        )
        self.register_validator(validator)
    
    def register_type(self, 
                      param_name: str, 
                      expected_type: Union[type, Tuple[type, ...]],
                      level: ValidationLevel = ValidationLevel.ERROR):
        """
        Register a type validator for a parameter.
        
        Args:
            param_name: Name of the parameter to validate
            expected_type: Expected type or tuple of types
            level: Validation level to apply
        """
        validator = TypeValidator(
            param_name=param_name,
            expected_type=expected_type,
            level=level
        )
        self.register_validator(validator)
    
    def validate_param(self, param_name: str, value: Any) -> List[ValidationResult]:
        """
        Validate a single parameter against all registered validators.
        
        Args:
            param_name: Name of the parameter to validate
            value: Value to validate
            
        Returns:
            List of ValidationResult objects from all validators
        """
        results = []
        if param_name in self.validators:
            for validator in self.validators[param_name]:
                results.append(validator.validate(value))
        return results
    
    def validate_config(self, config: Dict[str, Any]) -> Dict[str, List[ValidationResult]]:
        """
        Validate a configuration dictionary against all registered validators.
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            Dictionary mapping parameter names to lists of ValidationResult objects
        """
        results = {}
        # Check each parameter in the configuration
        for param_name, value in config.items():
            param_results = self.validate_param(param_name, value)
            if param_results:
                results[param_name] = param_results
        
        return results
    
    def validate_and_fix_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a configuration dictionary and fix invalid values.
        
        Args:
            config: Configuration dictionary to validate and fix
            
        Returns:
            Fixed configuration dictionary
        """
        fixed_config = config.copy()
        
        for param_name, value in config.items():
            if param_name in self.validators:
                for validator in self.validators[param_name]:
                    result = validator.validate(value)
                    if not result.is_valid:
                        # Handle result based on validation level
                        if result.level == ValidationLevel.FIX and result.fixed_value is not None:
                            fixed_config[param_name] = result.fixed_value
                            logger.info(f"Fixed parameter '{param_name}': {value} -> {result.fixed_value}")
                        elif result.level == ValidationLevel.ERROR:
                            # Raise exception for error level
                            error_msg = f"Parameter '{param_name}' validation error: {result.message}"
                            logger.error(error_msg)
                            raise ValueError(error_msg)
                        elif result.level == ValidationLevel.WARNING:
                            # Log warning but keep original value
                            logger.warning(f"Parameter '{param_name}' validation warning: {result.message}")
        
        return fixed_config


# Create a default validator with common parameters
default_validator = ConfigurationValidator()

# Register validators for common parameters
default_validator.register_range("MODEL_RESOLUTION", min_value=0.1, max_value=100.0, level=ValidationLevel.ERROR)
default_validator.register_range("DEFAULT_NUM_LAYERS", min_value=1, max_value=100, level=ValidationLevel.ERROR)
default_validator.register_range("DEFAULT_TILE_SIZE", min_value=16, max_value=1024, level=ValidationLevel.WARNING)
default_validator.register_range("DEFAULT_TILE_OVERLAP", min_value=0, max_value=100, level=ValidationLevel.WARNING)
default_validator.register_range("MAX_STEPS", min_value=1, max_value=10000, level=ValidationLevel.WARNING)
default_validator.register_range("MEMORY_LIMIT_MB", min_value=100, max_value=1000000, level=ValidationLevel.FIX)
default_validator.register_range("HORIZONTAL_SPREAD_PROBABILITY", min_value=0.0, max_value=1.0, level=ValidationLevel.FIX)
default_validator.register_range("VERTICAL_SPREAD_PROBABILITY", min_value=0.0, max_value=1.0, level=ValidationLevel.FIX)
default_validator.register_range("WIND_INFLUENCE", min_value=0.0, max_value=100.0, level=ValidationLevel.WARNING)
default_validator.register_range("SLOPE_INFLUENCE", min_value=0.0, max_value=100.0, level=ValidationLevel.WARNING)
default_validator.register_choice("STORAGE_OPTIMIZATION_LEVEL", {0, 1, 2, 3}, level=ValidationLevel.FIX)
default_validator.register_range("DEFAULT_MEMORY_OPTIMIZATION_LEVEL", min_value=0, max_value=3, level=ValidationLevel.FIX)

def validate_config(config: Dict[str, Any], validator: ConfigurationValidator = None) -> Dict[str, Any]:
    """
    Validate and fix a configuration dictionary.
    
    Args:
        config: Configuration dictionary to validate
        validator: Optional validator to use (if None, uses default_validator)
        
    Returns:
        Fixed configuration dictionary
    """
    if validator is None:
        validator = default_validator
    
    return validator.validate_and_fix_config(config)

def validate_param(param_name: str, value: Any, validator: ConfigurationValidator = None) -> Any:
    """
    Validate and fix a single parameter value.
    
    Args:
        param_name: Name of the parameter to validate
        value: Value to validate
        validator: Optional validator to use (if None, uses default_validator)
        
    Returns:
        Original or fixed parameter value
    """
    if validator is None:
        validator = default_validator
    
    results = validator.validate_param(param_name, value)
    
    for result in results:
        if not result.is_valid:
            return result.handle()
    
    return value

if __name__ == "__main__":
    # Example usage
    test_config = {
        "MODEL_RESOLUTION": 5.0,
        "DEFAULT_NUM_LAYERS": 10,
        "DEFAULT_TILE_SIZE": 256,
        "DEFAULT_TILE_OVERLAP": 8,
        "HORIZONTAL_SPREAD_PROBABILITY": 1.5,  # Invalid, should be fixed to 1.0
        "STORAGE_OPTIMIZATION_LEVEL": 5,  # Invalid, should be fixed to 3
        "MAX_STEPS": 20000  # Warning but not fixed
    }
    
    print("Original config:", test_config)
    
    try:
        fixed_config = validate_config(test_config)
        print("Fixed config:", fixed_config)
    except ValueError as e:
        print("Validation error:", e) 