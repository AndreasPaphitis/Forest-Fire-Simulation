#!/usr/bin/env python3
"""
Test the optimized configuration to verify that the calibration fixes work.
"""

import sys
import os
import logging
import numpy as np
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.config_tools import ModelConfig
from src.core.fire_simulation_engine import FireSimulationEngine
from src.core.forest_model import ForestModel

def test_optimized_configuration():
    """Test the optimized configuration to verify fixes."""
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger("optimized_test")
    logger.info("🧪 Testing optimized configuration...")
    
    # Create optimized configuration
    config = ModelConfig(
        grid_size=(30, 30),
        num_layers=5,
        max_steps=20,
        model_resolution=5.0,
        
        # Optimized parameters based on test results
        spread_probability=0.75,      # Balanced spread
        ignition_threshold=0.08,      # Lower for easier ignition
        fuel_consumption_rate=0.5,    # Higher for proper burnout
        min_fuel_value=0.05,          # Lower for easier burnout
        max_fuel_value=1.0,           # Keep for PAD data
        initial_fuel_load=0.8,        # Good fuel load
        
        # Optimized ember parameters
        ember_probability=0.4,        # Better long-range spread
        ember_ignition=0.3,           # Balanced ignition
        ember_distance=5,             # Keep current
        
        # Environmental factors
        wind_influence_on_spread=0.5,
        slope_influence=0.3,
        reference_wind_speed=10.0,
        
        # Memory optimization
        memory_optimization_level=1,
        use_sparse_storage=True,
        
        # Debug mode
        debug=False,
        engine_logging_interval=5
    )
    
    logger.info("📊 Optimized configuration created:")
    logger.info(f"   - spread_probability: {config.spread_probability}")
    logger.info(f"   - ignition_threshold: {config.ignition_threshold}")
    logger.info(f"   - fuel_consumption_rate: {config.fuel_consumption_rate}")
    logger.info(f"   - min_fuel_value: {config.min_fuel_value}")
    logger.info(f"   - ember_probability: {config.ember_probability}")
    
    try:
        # Create forest model
        forest_model = ForestModel(
            grid_size=config.grid_size,
            num_layers=config.num_layers,
            layer_height_meters=config.layer_height,
            model_resolution=config.model_resolution,
            initial_fuel_load=config.initial_fuel_load,
            config=config
        )
        
        # Set ignition points in the center
        center_x, center_y = config.grid_size[0] // 2, config.grid_size[1] // 2
        ignition_points = [
            (center_x, center_y, 0),
            (center_x + 1, center_y, 0),
            (center_x, center_y + 1, 0)
        ]
        
        for x, y, z in ignition_points:
            if 0 <= x < config.grid_size[0] and 0 <= y < config.grid_size[1] and 0 <= z < config.num_layers:
                forest_model.state[x, y, z] = 1  # BURNING
                forest_model.fuel_load[x, y, z] = 1.0  # Full fuel
        
        # Create simulation engine
        engine = FireSimulationEngine(forest_model, config)
        
        # Run simulation
        logger.info(f"   Running simulation with {len(ignition_points)} ignition points...")
        
        result = engine.run_simulation(
            max_steps=config.max_steps,
            store_history=False,
            stop_when_fire_extinguished=True
        )
        
        # Extract results
        stats = result.get('stats', {})
        max_burning = stats.get('max_active_cells', 0)
        final_burning = stats.get('final_active_cells', 0)
        steps_active = stats.get('steps', 0)
        total_burned = stats.get('total_burned_cells', 0)
        
        # Calculate spread metrics
        initial_burning = len(ignition_points)
        total_spread = max_burning - initial_burning
        
        logger.info(f"   Results:")
        logger.info(f"     - Max burning cells: {max_burning}")
        logger.info(f"     - Final burning cells: {final_burning}")
        logger.info(f"     - Steps active: {steps_active}/{config.max_steps}")
        logger.info(f"     - Total spread: {total_spread} cells")
        logger.info(f"     - Total burned: {total_burned} cells")
        
        # Check if fixes worked
        logger.info(f"\n🎯 FIX VERIFICATION:")
        logger.info("=" * 30)
        
        # Check 1: Fire should spread reasonably
        if total_spread >= 50:
            logger.info("   ✅ FIRE SPREAD: Good spread achieved")
        else:
            logger.warning("   ⚠️  FIRE SPREAD: Limited spread detected")
        
        # Check 2: Fire should burn out within reasonable time
        if final_burning == 0:
            logger.info("   ✅ FIRE BURNOUT: Fire extinguished properly")
        elif steps_active < config.max_steps:
            logger.info("   ✅ FIRE BURNOUT: Fire extinguished before max steps")
        else:
            logger.warning("   ⚠️  FIRE BURNOUT: Fire still burning at max steps")
        
        # Check 3: Reasonable total burned area
        total_cells = config.grid_size[0] * config.grid_size[1] * config.num_layers
        burned_percentage = (total_burned / total_cells) * 100
        
        if 10 <= burned_percentage <= 80:
            logger.info(f"   ✅ BURNED AREA: {burned_percentage:.1f}% - reasonable range")
        else:
            logger.warning(f"   ⚠️  BURNED AREA: {burned_percentage:.1f}% - outside reasonable range")
        
        # Check 4: Good balance between spread and burnout
        if total_spread >= 50 and final_burning < max_burning * 0.5:
            logger.info("   ✅ BALANCE: Good balance between spread and burnout")
        else:
            logger.warning("   ⚠️  BALANCE: Poor balance between spread and burnout")
        
        # Overall assessment
        logger.info(f"\n📊 OVERALL ASSESSMENT:")
        logger.info("=" * 25)
        
        issues = []
        if total_spread < 50:
            issues.append("Limited fire spread")
        if final_burning > max_burning * 0.5:
            issues.append("Poor fire burnout")
        if burned_percentage < 10 or burned_percentage > 80:
            issues.append("Unrealistic burned area")
        
        if not issues:
            logger.info("   🎉 OPTIMIZATION SUCCESSFUL!")
            logger.info("   All calibration issues have been resolved.")
            logger.info("   The simulation now has:")
            logger.info("   - Good fire spread")
            logger.info("   - Proper fire burnout")
            logger.info("   - Realistic burned areas")
            logger.info("   - Balanced behavior")
        else:
            logger.warning("   ⚠️  OPTIMIZATION PARTIALLY SUCCESSFUL")
            logger.warning(f"   Remaining issues: {', '.join(issues)}")
            logger.info("   Further parameter tuning may be needed.")
        
        return len(issues) == 0
        
    except Exception as e:
        logger.error(f"   ❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_optimized_configuration()
    
    if success:
        print("\n🎉 OPTIMIZATION TEST PASSED!")
        print("The calibration parameters have been successfully fixed.")
        print("You can now run calibration with confidence.")
    else:
        print("\n⚠️  OPTIMIZATION TEST PARTIALLY PASSED")
        print("Some issues remain. Consider further parameter adjustments.")
    
    sys.exit(0 if success else 1)
