#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Parameter Validator Module

Provides tools to validate, track, and report on parameter usage in the simulation.
This helps identify when fallback values are used and verifies that parameters are applied correctly.
"""

import logging
import json
import os
from typing import Dict, Any, Optional, List, Tuple, Set
from dataclasses import dataclass, field

# Set up logging
logger = logging.getLogger(__name__)

@dataclass
class ParameterUsage:
    """Tracks the usage of a single parameter."""
    name: str
    expected_value: Any
    actual_value: Any = None
    source: str = "config"  # Where the parameter came from (config, default, etc.)
    is_fallback: bool = False
    accessed: bool = False
    component: str = ""  # Which component accessed this parameter
    notes: str = ""

@dataclass
class ValidationReport:
    """Contains the results of parameter validation."""
    parameters: Dict[str, ParameterUsage] = field(default_factory=dict)
    unused_parameters: Set[str] = field(default_factory=set)
    fallback_parameters: Set[str] = field(default_factory=set)
    mismatched_parameters: Set[str] = field(default_factory=set)
    
    def add_parameter(self, name: str, expected: Any, source: str = "config") -> None:
        """Add a parameter to track."""
        self.parameters[name] = ParameterUsage(name=name, expected_value=expected, source=source)
        self.unused_parameters.add(name)
    
    def record_usage(self, name: str, actual: Any, component: str, is_fallback: bool = False, notes: str = "") -> None:
        """Record that a parameter was accessed and how it was used."""
        if name in self.parameters:
            param = self.parameters[name]
            param.actual_value = actual
            param.accessed = True
            param.component = component
            param.is_fallback = is_fallback
            param.notes = notes
            
            if is_fallback:
                self.fallback_parameters.add(name)
            
            if self._values_differ(param.expected_value, actual):
                self.mismatched_parameters.add(name)
            
            if name in self.unused_parameters:
                self.unused_parameters.remove(name)
    
    def _values_differ(self, expected: Any, actual: Any) -> bool:
        """Compare values accounting for floating point imprecision and format differences."""
        if isinstance(expected, float) and isinstance(actual, float):
            return abs(expected - actual) > 1e-6
        
        # Handle tuple/list differences
        if (isinstance(expected, (list, tuple)) and 
            isinstance(actual, (list, tuple)) and 
            len(expected) == len(actual)):
            return any(self._values_differ(e, a) for e, a in zip(expected, actual))
        
        return expected != actual
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate a dictionary report of parameter usage."""
        return {
            "summary": {
                "total_parameters": len(self.parameters),
                "used_parameters": len(self.parameters) - len(self.unused_parameters),
                "unused_parameters": len(self.unused_parameters),
                "fallback_parameters": len(self.fallback_parameters),
                "mismatched_parameters": len(self.mismatched_parameters)
            },
            "unused_parameters": sorted(list(self.unused_parameters)),
            "fallback_parameters": sorted(list(self.fallback_parameters)),
            "mismatched_parameters": sorted(list(self.mismatched_parameters)),
            "details": {
                name: {
                    "expected": str(param.expected_value),
                    "actual": str(param.actual_value),
                    "source": param.source,
                    "is_fallback": param.is_fallback,
                    "accessed": param.accessed,
                    "component": param.component,
                    "notes": param.notes
                } for name, param in self.parameters.items()
            }
        }
    
    def save_report(self, filename: str) -> None:
        """Save the validation report to a file."""
        report = self.generate_report()
        os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Parameter validation report saved to {filename}")
    
    def print_summary(self) -> None:
        """Print a summary of parameter usage to the console."""
        summary = self.generate_report()["summary"]
        
        print("\n===== PARAMETER VALIDATION SUMMARY =====")
        print(f"Total parameters: {summary['total_parameters']}")
        print(f"Used parameters: {summary['used_parameters']}")
        print(f"Unused parameters: {summary['unused_parameters']}")
        print(f"Parameters using fallbacks: {summary['fallback_parameters']}")
        print(f"Parameters with mismatched values: {summary['mismatched_parameters']}")
        
        if self.fallback_parameters:
            print("\nParameters using fallback values:")
            for name in sorted(self.fallback_parameters):
                param = self.parameters[name]
                print(f"  - {name}: expected={param.expected_value}, actual={param.actual_value}")
                print(f"    Component: {param.component}")
                if param.notes:
                    print(f"    Note: {param.notes}")
        
        if self.mismatched_parameters:
            print("\nParameters with mismatched values:")
            for name in sorted(self.mismatched_parameters):
                param = self.parameters[name]
                print(f"  - {name}: expected={param.expected_value}, actual={param.actual_value}")
                print(f"    Component: {param.component}")
                if param.notes:
                    print(f"    Note: {param.notes}")
        
        if self.unused_parameters:
            print("\nUnused parameters:")
            for name in sorted(self.unused_parameters):
                print(f"  - {name}")
        
        print("========================================\n")

class ParameterValidator:
    """Main validator class for tracking parameter usage across the simulation."""
    
    def __init__(self):
        self.report = ValidationReport()
        self.enabled = True
    
    def register_parameters(self, parameters: Dict[str, Any], source: str = "config") -> None:
        """Register parameters to track."""
        for name, value in parameters.items():
            self.report.add_parameter(name, value, source)
    
    def register_parameter(self, name: str, expected_value: Any, source: str = "config") -> None:
        """Register a single parameter to track."""
        self.report.add_parameter(name, expected_value, source)
    
    def track_usage(self, name: str, actual_value: Any, component: str, 
                    is_fallback: bool = False, notes: str = "") -> None:
        """Record that a parameter was accessed."""
        if not self.enabled:
            return
        
        self.report.record_usage(name, actual_value, component, is_fallback, notes)
    
    def create_tracked_parameter(self, name: str, expected_value: Any, fallback_value: Any, 
                                component: str, source: str = "config") -> Any:
        """
        Create a parameter that will be automatically tracked.
        Returns the expected value if it's not None, otherwise the fallback.
        Records the usage appropriately.
        """
        if not self.enabled:
            return expected_value if expected_value is not None else fallback_value
        
        # Register parameter if not already registered
        if name not in self.report.parameters:
            self.report.add_parameter(name, expected_value, source)
        
        # Determine which value to use
        is_fallback = expected_value is None
        actual_value = fallback_value if is_fallback else expected_value
        
        # Record the usage
        self.report.record_usage(
            name=name,
            actual=actual_value,
            component=component,
            is_fallback=is_fallback,
            notes=f"Fallback value: {fallback_value}" if is_fallback else ""
        )
        
        return actual_value
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate a dictionary report of parameter usage."""
        return self.report.generate_report()
    
    def save_report(self, filename: str) -> None:
        """Save the validation report to a file."""
        self.report.save_report(filename)
    
    def print_summary(self) -> None:
        """Print a summary of parameter usage to the console."""
        self.report.print_summary()

# Global validator instance
validator = ParameterValidator()

def validate_extents(expected_bounds: Tuple[float, float, float, float], 
                    actual_bounds: Tuple[float, float, float, float],
                    tolerance: float = 0.1) -> Tuple[bool, str]:
    """
    Validate that the actual extents match the expected extents.
    
    Args:
        expected_bounds: (minx, miny, maxx, maxy) expected coordinates, can be None
        actual_bounds: (minx, miny, maxx, maxy) actual coordinates, can be None
        tolerance: fractional tolerance for differences (0.1 = 10%)
        
    Returns:
        (is_match, message): Boolean indicating if extents match within tolerance, and message
    """
    if expected_bounds is None:
        return True, "Expected bounds not provided; validation skipped."
    if actual_bounds is None:
        return False, "Actual bounds not provided; cannot validate against expected."
        
    # Extract bounds
    exp_minx, exp_miny, exp_maxx, exp_maxy = expected_bounds
    act_minx, act_miny, act_maxx, act_maxy = actual_bounds
    
    # Calculate expected widths and heights
    exp_width = exp_maxx - exp_minx
    exp_height = exp_maxy - exp_miny
    act_width = act_maxx - act_minx
    act_height = act_maxy - act_miny
    
    # Calculate tolerance values
    width_tol = exp_width * tolerance
    height_tol = exp_height * tolerance
    
    # Check if bounds match within tolerance
    if (abs(exp_minx - act_minx) > width_tol or
        abs(exp_miny - act_miny) > height_tol or
        abs(exp_maxx - act_maxx) > width_tol or
        abs(exp_maxy - act_maxy) > height_tol):
        
        message = (
            f"Extent mismatch: Expected {expected_bounds}, got {actual_bounds}\n"
            f"Differences: X: {abs(exp_minx - act_minx):.2f}m (L), {abs(exp_maxx - act_maxx):.2f}m (R), "
            f"Y: {abs(exp_miny - act_miny):.2f}m (B), {abs(exp_maxy - act_maxy):.2f}m (T)"
        )
        return False, message
    
    return True, "Extents match within tolerance"

def validate_grid_size(expected_size: Tuple[int, int], actual_size: Tuple[int, int]) -> Tuple[bool, str]:
    """
    Validate that the actual grid size matches the expected grid size.
    
    Args:
        expected_size: (width, height) expected grid dimensions
        actual_size: (width, height) actual grid dimensions
        
    Returns:
        (is_match, message): Boolean indicating if grid sizes match, and message
    """
    if expected_size != actual_size:
        message = f"Grid size mismatch: Expected {expected_size}, got {actual_size}"
        return False, message
    
    return True, "Grid sizes match"

def validate_resolution(expected_res: float, actual_res: float, 
                       tolerance: float = 0.01) -> Tuple[bool, str]:
    """
    Validate that the actual resolution matches the expected resolution.
    
    Args:
        expected_res: Expected resolution in meters
        actual_res: Actual resolution in meters
        tolerance: Absolute tolerance for difference
        
    Returns:
        (is_match, message): Boolean indicating if resolutions match within tolerance, and message
    """
    if abs(expected_res - actual_res) > tolerance:
        message = f"Resolution mismatch: Expected {expected_res}m, got {actual_res}m"
        return False, message
    
    return True, "Resolutions match within tolerance"

# Functions to help with verification during simulation
def verify_extents(component: str, param_name: str, expected_bounds: Tuple[float, float, float, float], 
                  actual_bounds: Tuple[float, float, float, float]) -> bool:
    """
    Verify and track the extents of a geographical area.
    
    Args:
        component: Name of the component doing the verification
        param_name: Name of the parameter being verified
        expected_bounds: (minx, miny, maxx, maxy) expected coordinates
        actual_bounds: (minx, miny, maxx, maxy) actual coordinates
        
    Returns:
        bool: True if verification passed
    """
    match, message = validate_extents(expected_bounds, actual_bounds)
    
    validator.track_usage(
        name=param_name,
        actual_value=actual_bounds,
        component=component,
        is_fallback=not match,
        notes=message
    )
    
    if not match:
        logger.warning(f"{component}: {message}")
    
    return match

def verify_grid_resolution(component: str, param_name: str, expected_res: float, 
                          actual_res: float) -> bool:
    """
    Verify and track grid resolution.
    
    Args:
        component: Name of the component doing the verification
        param_name: Name of the parameter being verified
        expected_res: Expected resolution in meters
        actual_res: Actual resolution in meters
        
    Returns:
        bool: True if verification passed
    """
    match, message = validate_resolution(expected_res, actual_res)
    
    validator.track_usage(
        name=param_name,
        actual_value=actual_res,
        component=component,
        is_fallback=not match,
        notes=message
    )
    
    if not match:
        logger.warning(f"{component}: {message}")
    
    return match

# Parameter decorator that automatically tracks usage
def track_parameter(param_name: str, component: str):
    """
    Decorator to track parameter usage in a method.
    
    Args:
        param_name: Name of the parameter to track
        component: Name of the component using the parameter
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Get the parameter value if available in kwargs
            if param_name in kwargs:
                value = kwargs[param_name]
                validator.track_usage(param_name, value, component)
            
            # Call the original function
            return func(*args, **kwargs)
        return wrapper
    return decorator

# Context manager for coordinated parameter validation
class ValidationContext:
    """Context manager for validating a group of parameters together."""
    
    def __init__(self, name: str):
        self.name = name
        self.parameters = {}
    
    def __enter__(self):
        return self
    
    def register_parameter(self, name: str, expected_value: Any, actual_value: Any = None):
        """Register a parameter to validate in this context."""
        self.parameters[name] = {
            "expected": expected_value,
            "actual": actual_value,
            "validated": False
        }
        
        return self
    
    def validate_parameter(self, name: str, actual_value: Any):
        """Validate that a parameter matches its expected value."""
        if name not in self.parameters:
            logger.warning(f"{self.name}: Validating unregistered parameter {name}")
            return False
        
        param = self.parameters[name]
        param["actual"] = actual_value
        param["validated"] = True
        
        is_match = param["expected"] == actual_value
        
        validator.track_usage(
            name=name,
            actual_value=actual_value,
            component=self.name,
            is_fallback=not is_match,
            notes=f"Expected: {param['expected']}, Actual: {actual_value}"
        )
        
        return is_match
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Report on validation when exiting the context."""
        # Check if all parameters were validated
        unvalidated = [name for name, param in self.parameters.items() if not param["validated"]]
        
        if unvalidated:
            logger.warning(f"{self.name}: Parameters not validated: {', '.join(unvalidated)}")
        
        return False  # Don't suppress exceptions 