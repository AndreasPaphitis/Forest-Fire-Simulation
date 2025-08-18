#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Parameter Count Validation Script

This script validates that the parameter count is consistent between
the sensitivity analysis runner and parameter bounds.

Author: Forest Fire Simulation Team
Date: 2025
Version: 1.0
"""

import sys
from pathlib import Path
from typing import Dict, List, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.core.calibration.parameter_bounds import get_default_calibration_bounds
    from src.utils.logging_utils import get_logger
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this from the project root directory")
    sys.exit(1)

logger = get_logger(__name__)

def validate_parameter_count():
    """Validate parameter count consistency."""
    
    print("🔍 VALIDATING PARAMETER COUNT CONSISTENCY")
    print("=" * 50)
    
    # Get parameter bounds
    bounds = get_default_calibration_bounds()
    bounds_params = list(bounds.keys())
    
    print(f"📊 Parameter Bounds: {len(bounds_params)} parameters")
    print("Parameters in bounds:")
    for i, param in enumerate(bounds_params, 1):
        print(f"  {i:2d}. {param}")
    
    # Get sensitivity runner parameters (simulate the method)
    sensitivity_params = [
        # Core Fire Mechanics
        'spread_probability',
        'fuel_consumption_rate',
        'ignition_threshold',
        'min_fuel_value',
        'max_fuel_value',
        
        # Environmental Interactions
        'wind_influence_on_spread',
        'slope_influence',
        'reference_wind_speed',
        'fuel_moisture_baseline',
        
        # Wind Parameters
        'wind_speed',
        'wind_direction',
        
        # Ember Mechanics
        'ember_probability',
        'ember_distance',
        'ember_ignition',
        'ember_height_factor',
        'ember_wind_factor',
        'ember_rise'
    ]
    
    print(f"\n📊 Sensitivity Runner: {len(sensitivity_params)} parameters")
    print("Parameters in sensitivity runner:")
    for i, param in enumerate(sensitivity_params, 1):
        print(f"  {i:2d}. {param}")
    
    # Check for missing parameters
    missing_in_bounds = [p for p in sensitivity_params if p not in bounds_params]
    missing_in_runner = [p for p in bounds_params if p not in sensitivity_params]
    
    print(f"\n🔍 VALIDATION RESULTS:")
    print(f"   Parameters in bounds: {len(bounds_params)}")
    print(f"   Parameters in runner: {len(sensitivity_params)}")
    
    if len(bounds_params) == len(sensitivity_params):
        print("   ✅ Parameter count matches!")
    else:
        print("   ❌ Parameter count mismatch!")
    
    if missing_in_bounds:
        print(f"   ❌ Missing in bounds: {missing_in_bounds}")
    
    if missing_in_runner:
        print(f"   ❌ Missing in runner: {missing_in_runner}")
    
    if not missing_in_bounds and not missing_in_runner:
        print("   ✅ All parameters are consistent!")
        return True
    else:
        print("   ❌ Parameter inconsistency found!")
        return False

if __name__ == "__main__":
    success = validate_parameter_count()
    sys.exit(0 if success else 1)
