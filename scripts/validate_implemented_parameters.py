#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Parameter Validation Script

This script validates that all 16 implemented parameters have proper bounds defined
for sensitivity analysis and calibration.

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


def validate_implemented_parameters():
    """
    Validate that all 16 implemented parameters have bounds defined.
    """
    
    # DEFINITIVE LIST OF IMPLEMENTED PARAMETERS (from line-by-line analysis)
    implemented_parameters = [
        # Core Fire Mechanics
        'spread_probability',      # Line 906 - Base fire spread probability
        'fuel_consumption_rate',   # Line 824 - Fuel consumption rate
        'ignition_threshold',      # Line 1050 - Ignition probability threshold
        'min_fuel_value',          # Lines 825, 883, 1369 - Minimum fuel for burning
        'max_fuel_value',          # Lines 1014, 1377 - Maximum fuel normalization
        
        # Environmental Interactions
        'wind_influence_on_spread', # Line 990 - Wind effect on fire spread
        'slope_influence',         # Line 1114 - Terrain slope effect
        'reference_wind_speed',    # Line 989 - Reference wind speed for scaling
        'fuel_moisture_baseline',  # Line 1387 - Baseline fuel moisture
        
        # Wind Parameters (Main Fire Spread)
        'wind_speed',              # Lines 920-994 - Wind speed via get_wind_speed_at_cell()
        'wind_direction',          # Lines 926-994 - Wind direction via get_wind_direction_at_cell()
        
        # Ember Mechanics
        'ember_probability',       # Line 1250 - Ember generation probability
        'ember_distance',          # Lines 1284, 1401 - Ember travel distance
        'ember_ignition',          # Line 1374 - Ember ignition probability
        'ember_height_factor',     # Line 1254 - Height factor for ember generation
        'ember_wind_factor',       # Line 1301 - Wind influence on ember direction
        'ember_rise'               # Line 1314 - Ember height change range
    ]
    
    logger.info("🔍 Validating implemented parameters against parameter bounds")
    logger.info("=" * 60)
    
    # Get all parameter bounds
    all_bounds = get_default_calibration_bounds()
    
    # Check each implemented parameter
    found_params = []
    missing_params = []
    invalid_params = []
    
    for param_name in implemented_parameters:
        if param_name in all_bounds:
            bounds = all_bounds[param_name]
            
            # Validate bounds structure
            try:
                min_val = bounds.min_value
                max_val = bounds.max_value
                default_val = bounds.default_value
                
                # Check if bounds are reasonable
                if min_val >= max_val:
                    invalid_params.append((param_name, "min_value >= max_value"))
                elif not (min_val <= default_val <= max_val):
                    invalid_params.append((param_name, "default_value outside bounds"))
                else:
                    found_params.append(param_name)
                    logger.info(f"✅ {param_name:25s}: [{min_val:.3f}, {max_val:.3f}] (default: {default_val:.3f})")
                    
            except AttributeError as e:
                invalid_params.append((param_name, f"Invalid bounds structure: {e}"))
        else:
            missing_params.append(param_name)
            logger.warning(f"❌ {param_name:25s}: NO BOUNDS DEFINED")
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("VALIDATION SUMMARY")
    logger.info("=" * 60)
    
    logger.info(f"✅ Found bounds for: {len(found_params)}/{len(implemented_parameters)} parameters")
    logger.info(f"❌ Missing bounds for: {len(missing_params)} parameters")
    logger.info(f"⚠️  Invalid bounds for: {len(invalid_params)} parameters")
    
    if missing_params:
        logger.warning("\nMISSING PARAMETERS:")
        for param in missing_params:
            logger.warning(f"  - {param}")
    
    if invalid_params:
        logger.warning("\nINVALID PARAMETERS:")
        for param, reason in invalid_params:
            logger.warning(f"  - {param}: {reason}")
    
    if found_params:
        logger.info("\nVALID PARAMETERS:")
        for param in found_params:
            logger.info(f"  ✅ {param}")
    
    # Overall status
    if len(missing_params) == 0 and len(invalid_params) == 0:
        logger.info("\n🎉 ALL PARAMETERS ARE VALID!")
        logger.info("✅ Ready for sensitivity analysis")
        return True
    else:
        logger.warning("\n⚠️  SOME PARAMETERS NEED ATTENTION")
        logger.warning("❌ Cannot proceed with sensitivity analysis until all parameters are valid")
        return False


def main():
    """
    Main function to run parameter validation.
    """
    logger.info("🎯 Parameter Validation Script")
    logger.info("=" * 60)
    
    try:
        success = validate_implemented_parameters()
        
        if success:
            logger.info("\n✅ Validation completed successfully!")
            logger.info("🚀 Ready to run sensitivity analysis")
            sys.exit(0)
        else:
            logger.error("\n❌ Validation failed!")
            logger.error("🔧 Please fix the parameter bounds before running sensitivity analysis")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ Validation script failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)


if __name__ == "__main__":
    main()
