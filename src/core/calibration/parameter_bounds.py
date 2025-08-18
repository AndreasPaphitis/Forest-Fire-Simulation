#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Parameter Bounds Module

This module defines parameter bounds and constraints for calibration.
It provides physically meaningful ranges for all calibration parameters
based on literature review and physical constraints.

Author: Forest Fire Simulation Team
Date: 2025
Version: 1.0
"""

import math
from enum import Enum
from typing import Dict, List, Any, Union, Optional, Tuple
from dataclasses import dataclass, field

try:
    from src.utils.logging_utils import get_logger
except ImportError:
    try:
        from utils.logging_utils import get_logger
    except ImportError:
        import logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

logger = get_logger(__name__)


class CalibrationTier(Enum):
    """Calibration priority tiers based on parameter sensitivity."""
    CRITICAL = 1      # High sensitivity, calibrate first
    MODERATE = 2      # Medium sensitivity, calibrate second  
    LOW = 3          # Low sensitivity, calibrate last
    FIXED = 4        # Fixed parameters (not calibrated)


class ParameterType(Enum):
    """Types of parameters for validation and scaling."""
    PROBABILITY = "probability"        # 0.0 to 1.0
    POSITIVE_FLOAT = "positive_float"  # > 0.0
    NON_NEGATIVE_FLOAT = "non_negative_float"  # >= 0.0
    BOUNDED_FLOAT = "bounded_float"    # min <= x <= max
    INTEGER = "integer"                # Whole numbers
    ANGLE_DEGREES = "angle_degrees"    # 0.0 to 360.0


@dataclass
class ParameterBounds:
    """
    Defines bounds and constraints for a calibration parameter.
    """
    min_value: float
    max_value: float
    default_value: float
    parameter_type: ParameterType
    calibration_tier: CalibrationTier
    physical_interpretation: str = ""
    literature_range: Optional[Tuple[float, float]] = None
    units: str = ""
    suggested_points: int = 5  # For grid search
    log_scale: bool = False   # Use logarithmic scaling
    
    def __post_init__(self):
        """Validate bounds after initialization."""
        if self.min_value >= self.max_value:
            raise ValueError(f"min_value ({self.min_value}) must be < max_value ({self.max_value})")
        
        if not (self.min_value <= self.default_value <= self.max_value):
            raise ValueError(f"default_value ({self.default_value}) must be within bounds [{self.min_value}, {self.max_value}]")
        
        # Type-specific validation
        if self.parameter_type == ParameterType.PROBABILITY:
            if not (0.0 <= self.min_value <= self.max_value <= 1.0):
                raise ValueError("Probability parameters must be in range [0.0, 1.0]")
        
        elif self.parameter_type == ParameterType.POSITIVE_FLOAT:
            if self.min_value <= 0.0:
                raise ValueError("Positive float parameters must have min_value > 0.0")
        
        elif self.parameter_type == ParameterType.NON_NEGATIVE_FLOAT:
            if self.min_value < 0.0:
                raise ValueError("Non-negative float parameters must have min_value >= 0.0")
        
        elif self.parameter_type == ParameterType.ANGLE_DEGREES:
            if not (0.0 <= self.min_value <= self.max_value <= 360.0):
                raise ValueError("Angle parameters must be in range [0.0, 360.0]")
    
    def validate_value(self, value: float) -> bool:
        """Check if a value is within bounds."""
        return self.min_value <= value <= self.max_value
    
    def clip_value(self, value: float) -> float:
        """Clip a value to be within bounds."""
        return max(self.min_value, min(self.max_value, value))
    
    def normalize_value(self, value: float) -> float:
        """Normalize value to [0, 1] range."""
        if self.log_scale:
            log_min = math.log(max(self.min_value, 1e-10))
            log_max = math.log(max(self.max_value, 1e-10))
            log_val = math.log(max(value, 1e-10))
            return (log_val - log_min) / (log_max - log_min)
        else:
            return (value - self.min_value) / (self.max_value - self.min_value)
    
    def denormalize_value(self, normalized_value: float) -> float:
        """Convert normalized [0, 1] value back to parameter range."""
        if self.log_scale:
            log_min = math.log(max(self.min_value, 1e-10))
            log_max = math.log(max(self.max_value, 1e-10))
            log_val = log_min + normalized_value * (log_max - log_min)
            return math.exp(log_val)
        else:
            return self.min_value + normalized_value * (self.max_value - self.min_value)
    
    def generate_grid_points(self, num_points: Optional[int] = None) -> List[float]:
        """Generate evenly spaced points for grid search."""
        if num_points is None:
            num_points = self.suggested_points
        
        if num_points < 2:
            return [self.default_value]
        
        if self.log_scale:
            # Logarithmic spacing
            log_min = math.log(max(self.min_value, 1e-10))
            log_max = math.log(max(self.max_value, 1e-10))
            log_points = [log_min + i * (log_max - log_min) / (num_points - 1) 
                         for i in range(num_points)]
            return [math.exp(lp) for lp in log_points]
        else:
            # Linear spacing
            return [self.min_value + i * (self.max_value - self.min_value) / (num_points - 1) 
                   for i in range(num_points)]


@dataclass
class CalibrationParameter:
    """
    Wrapper for a parameter with its bounds and metadata.
    """
    name: str
    bounds: ParameterBounds
    current_value: Optional[float] = None
    calibrated_value: Optional[float] = None
    sensitivity_score: Optional[float] = None
    
    def __post_init__(self):
        """Set current value to default if not provided."""
        if self.current_value is None:
            self.current_value = self.bounds.default_value
    
    def update_value(self, new_value: float) -> None:
        """Update the current parameter value with validation."""
        if not self.bounds.validate_value(new_value):
            logger.warning(f"Value {new_value} out of bounds for {self.name}, clipping to valid range")
            new_value = self.bounds.clip_value(new_value)
        
        self.current_value = new_value
    
    def set_calibrated_value(self, calibrated_value: float, sensitivity_score: Optional[float] = None) -> None:
        """Set the calibrated value after optimization."""
        self.calibrated_value = calibrated_value
        self.sensitivity_score = sensitivity_score
    
    def get_tier(self) -> CalibrationTier:
        """Get the calibration tier for this parameter."""
        return self.bounds.calibration_tier


def get_default_calibration_bounds() -> Dict[str, ParameterBounds]:
    """
    Get default parameter bounds for all calibration parameters.
    
    Based on literature review and physical constraints from the parameter summary.
    """
    bounds = {
        # ===== GROUP 1: FULL RANGE PARAMETERS =====
        
        'wind_influence_on_spread': ParameterBounds(
            min_value=0.0, max_value=1.0, default_value=0.5,
            parameter_type=ParameterType.PROBABILITY,
            calibration_tier=CalibrationTier.CRITICAL,
            physical_interpretation="Wind effect on fire spread probability",
            literature_range=(0.2, 0.8),
            units="scaling factor",
            suggested_points=5
        ),
        
        'fuel_consumption_rate': ParameterBounds(
            min_value=0.1, max_value=5.0, default_value=1.0,
            parameter_type=ParameterType.POSITIVE_FLOAT,
            calibration_tier=CalibrationTier.CRITICAL,
            physical_interpretation="Rate of fuel consumption during fire spread",
            literature_range=(0.5, 3.0),
            units="fuel units per time step",
            suggested_points=5
        ),
        
        'terrain_effect_strength': ParameterBounds(
            min_value=0.0, max_value=1.0, default_value=0.6,
            parameter_type=ParameterType.PROBABILITY,
            calibration_tier=CalibrationTier.CRITICAL,
            physical_interpretation="Overall terrain effect strength",
            literature_range=(0.3, 0.9),
            units="scaling factor",
            suggested_points=5
        ),
        
        'barranco_amplification': ParameterBounds(
            min_value=1.0, max_value=5.0, default_value=2.0,
            parameter_type=ParameterType.POSITIVE_FLOAT,
            calibration_tier=CalibrationTier.CRITICAL,
            physical_interpretation="Wind speed amplification in barrancos",
            literature_range=(1.5, 3.5),
            units="multiplier",
            suggested_points=5
        ),
        
        'barranco_direction_weight': ParameterBounds(
            min_value=0.0, max_value=1.0, default_value=0.8,
            parameter_type=ParameterType.PROBABILITY,
            calibration_tier=CalibrationTier.CRITICAL,
            physical_interpretation="Wind direction alignment weight in barrancos",
            literature_range=(0.5, 0.95),
            units="weight",
            suggested_points=5
        ),
        
        'slope_influence': ParameterBounds(
            min_value=0.0, max_value=1.0, default_value=0.3,
            parameter_type=ParameterType.PROBABILITY,
            calibration_tier=CalibrationTier.CRITICAL,
            physical_interpretation="Influence of terrain slope on fire spread",
            literature_range=(0.1, 0.6),
            units="scaling factor",
            suggested_points=5
        ),
        
        'ember_height_factor': ParameterBounds(
            min_value=0.0, max_value=1.0, default_value=0.2,
            parameter_type=ParameterType.PROBABILITY,
            calibration_tier=CalibrationTier.CRITICAL,
            physical_interpretation="Height factor for ember generation probability",
            literature_range=(0.1, 0.5),
            units="scaling factor",
            suggested_points=4
        ),
        
        # ===== GROUP 2: CONSTRAINED RANGE PARAMETERS =====
        
        'wind_speed': ParameterBounds(
            min_value=1.0, max_value=20.0, default_value=5.0,
            parameter_type=ParameterType.POSITIVE_FLOAT,
            calibration_tier=CalibrationTier.CRITICAL,
            physical_interpretation="Base wind speed affecting fire spread and ember transport",
            literature_range=(2.0, 15.0),
            units="m/s",
            suggested_points=5
        ),
        
        'wind_direction': ParameterBounds(
            min_value=0.0, max_value=360.0, default_value=0.0,
            parameter_type=ParameterType.ANGLE_DEGREES,
            calibration_tier=CalibrationTier.CRITICAL,
            physical_interpretation="Wind direction in degrees from north",
            literature_range=(0.0, 360.0),
            units="degrees",
            suggested_points=8
        ),
        
        'ember_distance': ParameterBounds(
            min_value=2, max_value=15, default_value=5,
            parameter_type=ParameterType.INTEGER,
            calibration_tier=CalibrationTier.CRITICAL,
            physical_interpretation="Ember travel distance in grid cells",
            literature_range=(2, 15),
            units="cells",
            suggested_points=5
        ),
        
        'ember_probability': ParameterBounds(
            min_value=0.01, max_value=0.25, default_value=0.1,
            parameter_type=ParameterType.PROBABILITY,
            calibration_tier=CalibrationTier.CRITICAL,
            physical_interpretation="Probability of ember generation during fire spread",
            literature_range=(0.02, 0.15),
            units="probability",
            suggested_points=5
        ),
        
        'spread_probability': ParameterBounds(
            min_value=0.2, max_value=0.8, default_value=0.4,
            parameter_type=ParameterType.PROBABILITY,
            calibration_tier=CalibrationTier.CRITICAL,
            physical_interpretation="Base probability of fire spreading between adjacent cells",
            literature_range=(0.2, 0.7),
            units="probability",
            suggested_points=7
        ),
        
        'ember_ignition': ParameterBounds(
            min_value=0.1, max_value=0.6, default_value=0.3,
            parameter_type=ParameterType.PROBABILITY,
            calibration_tier=CalibrationTier.CRITICAL,
            physical_interpretation="Probability of ember successfully igniting fuel",
            literature_range=(0.05, 0.5),
            units="probability",
            suggested_points=5
        ),
        
        'ignition_threshold': ParameterBounds(
            min_value=0.05, max_value=0.3, default_value=0.1,
            parameter_type=ParameterType.PROBABILITY,
            calibration_tier=CalibrationTier.CRITICAL,
            physical_interpretation="Threshold for ignition probability (deterministic)",
            literature_range=(0.05, 0.3),
            units="probability",
            suggested_points=5
        ),
        

    }
    
    logger.info(f"Created default bounds for {len(bounds)} calibration parameters")
    return bounds


def get_calibration_parameters_by_tier(tier: CalibrationTier, 
                                      bounds: Optional[Dict[str, ParameterBounds]] = None) -> List[str]:
    """
    Get parameter names for a specific calibration tier.
    
    Args:
        tier: The calibration tier to filter by
        bounds: Parameter bounds dictionary (uses default if None)
        
    Returns:
        List of parameter names in the specified tier
    """
    if bounds is None:
        bounds = get_default_calibration_bounds()
    
    return [name for name, bound in bounds.items() 
            if bound.calibration_tier == tier]


def validate_parameter_values(parameter_values: Dict[str, float], 
                            bounds: Optional[Dict[str, ParameterBounds]] = None) -> Tuple[bool, List[str]]:
    """
    Validate a set of parameter values against their bounds.
    
    Args:
        parameter_values: Dictionary of parameter names and values
        bounds: Parameter bounds dictionary (uses default if None)
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    if bounds is None:
        bounds = get_default_calibration_bounds()
    
    errors = []
    
    for param_name, param_value in parameter_values.items():
        if param_name not in bounds:
            errors.append(f"Unknown parameter: {param_name}")
            continue
        
        param_bounds = bounds[param_name]
        if not param_bounds.validate_value(param_value):
            errors.append(
                f"Parameter {param_name} value {param_value} outside bounds "
                f"[{param_bounds.min_value}, {param_bounds.max_value}]"
            )
    
    return len(errors) == 0, errors


def create_calibration_parameters(parameter_names: List[str],
                                bounds: Optional[Dict[str, ParameterBounds]] = None) -> Dict[str, CalibrationParameter]:
    """
    Create CalibrationParameter objects for the specified parameters.
    
    Args:
        parameter_names: List of parameter names to create
        bounds: Parameter bounds dictionary (uses default if None)
        
    Returns:
        Dictionary mapping parameter names to CalibrationParameter objects
    """
    if bounds is None:
        bounds = get_default_calibration_bounds()
    
    parameters = {}
    
    for param_name in parameter_names:
        if param_name not in bounds:
            logger.warning(f"No bounds defined for parameter: {param_name}")
            continue
        
        parameters[param_name] = CalibrationParameter(
            name=param_name,
            bounds=bounds[param_name]
        )
    
    logger.info(f"Created {len(parameters)} calibration parameters")
    return parameters


def get_tier_description(tier: CalibrationTier) -> str:
    """Get a human-readable description of a calibration tier."""
    descriptions = {
        CalibrationTier.CRITICAL: "High sensitivity parameters - calibrate first with fine resolution",
        CalibrationTier.MODERATE: "Medium sensitivity parameters - calibrate second",
        CalibrationTier.LOW: "Low sensitivity parameters - calibrate last with coarse resolution",
        CalibrationTier.FIXED: "Fixed parameters - not calibrated"
    }
    return descriptions.get(tier, "Unknown tier")


if __name__ == "__main__":
    # Example usage
    print("Parameter Bounds Example")
    print("=" * 50)
    
    # Get default bounds
    bounds = get_default_calibration_bounds()
    
    # Print summary by tier
    for tier in CalibrationTier:
        if tier == CalibrationTier.FIXED:
            continue
        
        params = get_calibration_parameters_by_tier(tier, bounds)
        print(f"\n{tier.name} Parameters ({len(params)}):")
        print(get_tier_description(tier))
        
        for param_name in params:
            bound = bounds[param_name]
            print(f"  {param_name}: [{bound.min_value:.3f}, {bound.max_value:.3f}] "
                  f"(default: {bound.default_value:.3f}) - {bound.physical_interpretation}")
    
    # Example parameter validation
    print("\n" + "=" * 50)
    print("Parameter Validation Example")
    
    test_values = {
        'spread_probability': 0.35,
        'fuel_consumption_rate': 1.5,
        'invalid_parameter': 1.0  # This should cause an error
    }
    
    is_valid, errors = validate_parameter_values(test_values, bounds)
    print(f"Validation result: {'PASS' if is_valid else 'FAIL'}")
    if errors:
        for error in errors:
            print(f"  Error: {error}") 