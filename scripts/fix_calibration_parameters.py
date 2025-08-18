#!/usr/bin/env python3
"""
Fix calibration parameters based on test results to address burnout and propagation issues.
"""

import sys
import os
import logging
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.config_tools import ModelConfig
from src.core.calibration.parameter_bounds import get_default_calibration_bounds

def fix_calibration_parameters():
    """Fix calibration parameters based on test results."""
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger("calibration_fix")
    logger.info("🔧 Fixing calibration parameters based on test results...")
    
    # Get current parameter bounds
    current_bounds = get_default_calibration_bounds()
    
    logger.info("\n📊 CURRENT PARAMETER BOUNDS:")
    logger.info("=" * 50)
    
    # Show current critical parameters
    critical_params = [
        'spread_probability',
        'ignition_threshold', 
        'fuel_consumption_rate',
        'min_fuel_value',
        'ember_probability',
        'ember_ignition'
    ]
    
    for param in critical_params:
        if param in current_bounds:
            bounds = current_bounds[param]
            logger.info(f"   {param}:")
            logger.info(f"     - Min: {bounds.min_value}")
            logger.info(f"     - Max: {bounds.max_value}")
            logger.info(f"     - Default: {bounds.default_value}")
            logger.info(f"     - Type: {bounds.parameter_type}")
    
    # Based on test results, here are the fixes needed:
    logger.info("\n🔍 ISSUES IDENTIFIED FROM TESTS:")
    logger.info("=" * 40)
    logger.info("   1. Fires don't burn out (4/5 configurations)")
    logger.info("   2. Fuel consumption rate too low")
    logger.info("   3. Min fuel value too high")
    logger.info("   4. Some configurations have limited spread")
    
    logger.info("\n💡 RECOMMENDED FIXES:")
    logger.info("=" * 30)
    
    # Fix 1: Increase fuel consumption rate for proper burnout
    logger.info("   1. INCREASE fuel_consumption_rate:")
    logger.info("      - Current range: 0.1 - 0.5")
    logger.info("      - Recommended range: 0.3 - 0.8")
    logger.info("      - Reason: Fires need to burn out within simulation time")
    
    # Fix 2: Lower min fuel value for easier burnout
    logger.info("   2. LOWER min_fuel_value:")
    logger.info("      - Current range: 0.05 - 0.2")
    logger.info("      - Recommended range: 0.02 - 0.1")
    logger.info("      - Reason: Lower threshold for cell burnout")
    
    # Fix 3: Adjust spread probability for better propagation
    logger.info("   3. ADJUST spread_probability:")
    logger.info("      - Current range: 0.4 - 0.95")
    logger.info("      - Recommended range: 0.6 - 0.9")
    logger.info("      - Reason: Ensure adequate fire spread")
    
    # Fix 4: Lower ignition threshold for easier ignition
    logger.info("   4. LOWER ignition_threshold:")
    logger.info("      - Current range: 0.02 - 0.2")
    logger.info("      - Recommended range: 0.01 - 0.15")
    logger.info("      - Reason: Easier fire ignition")
    
    # Fix 5: Increase ember probability for long-range spread
    logger.info("   5. INCREASE ember_probability:")
    logger.info("      - Current range: 0.05 - 0.5")
    logger.info("      - Recommended range: 0.2 - 0.6")
    logger.info("      - Reason: Better long-range fire spread")
    
    logger.info("\n🎯 SPECIFIC PARAMETER ADJUSTMENTS:")
    logger.info("=" * 45)
    
    # Create optimized parameter bounds
    optimized_bounds = {
        'spread_probability': {
            'min_value': 0.6,
            'max_value': 0.9,
            'default_value': 0.75,
            'reason': 'Balanced spread - not too aggressive, not too conservative'
        },
        'ignition_threshold': {
            'min_value': 0.01,
            'max_value': 0.15,
            'default_value': 0.08,
            'reason': 'Lower threshold for easier ignition'
        },
        'fuel_consumption_rate': {
            'min_value': 0.3,
            'max_value': 0.8,
            'default_value': 0.5,
            'reason': 'Higher consumption for proper burnout'
        },
        'min_fuel_value': {
            'min_value': 0.02,
            'max_value': 0.1,
            'default_value': 0.05,
            'reason': 'Lower threshold for cell burnout'
        },
        'ember_probability': {
            'min_value': 0.2,
            'max_value': 0.6,
            'default_value': 0.4,
            'reason': 'Better long-range spread'
        },
        'ember_ignition': {
            'min_value': 0.15,
            'max_value': 0.5,
            'default_value': 0.3,
            'reason': 'Balanced ember ignition'
        }
    }
    
    for param, values in optimized_bounds.items():
        logger.info(f"   {param}:")
        logger.info(f"     - Range: {values['min_value']} - {values['max_value']}")
        logger.info(f"     - Default: {values['default_value']}")
        logger.info(f"     - Reason: {values['reason']}")
    
    logger.info("\n🔧 IMPLEMENTATION STEPS:")
    logger.info("=" * 30)
    logger.info("   1. Update parameter_bounds.py with new ranges")
    logger.info("   2. Update ModelConfig defaults")
    logger.info("   3. Test with new parameters")
    logger.info("   4. Run calibration with optimized bounds")
    
    logger.info("\n✅ Calibration parameter analysis complete!")
    
    return optimized_bounds

def create_optimized_config():
    """Create an optimized configuration based on test results."""
    
    logger = logging.getLogger("calibration_fix")
    logger.info("\n🎯 CREATING OPTIMIZED CONFIGURATION:")
    logger.info("=" * 40)
    
    # Create optimized configuration
    optimized_config = ModelConfig(
        # Core fire parameters (optimized based on tests)
        spread_probability=0.75,      # Balanced spread
        ignition_threshold=0.08,      # Lower for easier ignition
        fuel_consumption_rate=0.5,    # Higher for proper burnout
        min_fuel_value=0.05,          # Lower for easier burnout
        max_fuel_value=1.0,           # Keep for PAD data
        
        # Ember parameters (optimized)
        ember_probability=0.4,        # Better long-range spread
        ember_ignition=0.3,           # Balanced ignition
        ember_distance=5,             # Keep current
        
        # Environmental factors (keep current)
        wind_influence_on_spread=0.5,
        slope_influence=0.3,
        reference_wind_speed=10.0,
        
        # Simulation settings
        max_steps=20,
        grid_size=(50, 50),
        num_layers=5,
        model_resolution=5.0,
        
        # Memory optimization
        memory_optimization_level=1,
        use_sparse_storage=True
    )
    
    logger.info("✅ Optimized configuration created with:")
    logger.info(f"   - spread_probability: {optimized_config.spread_probability}")
    logger.info(f"   - ignition_threshold: {optimized_config.ignition_threshold}")
    logger.info(f"   - fuel_consumption_rate: {optimized_config.fuel_consumption_rate}")
    logger.info(f"   - min_fuel_value: {optimized_config.min_fuel_value}")
    logger.info(f"   - ember_probability: {optimized_config.ember_probability}")
    
    return optimized_config

if __name__ == "__main__":
    # Analyze and fix parameters
    optimized_bounds = fix_calibration_parameters()
    
    # Create optimized configuration
    optimized_config = create_optimized_config()
    
    print("\n🎉 Calibration parameter fix complete!")
    print("Next steps:")
    print("1. Update parameter_bounds.py with the recommended ranges")
    print("2. Update ModelConfig defaults")
    print("3. Test the optimized configuration")
    print("4. Run calibration with the new parameters")
