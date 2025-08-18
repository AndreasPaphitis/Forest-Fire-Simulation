#!/usr/bin/env python3
"""
Test script to run actual fire simulations with different parameter combinations
to identify calibration issues with fire propagation and extinction.
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

def test_simulation_behavior():
    """Test actual simulation behavior with different parameter combinations."""
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger("calibration_test")
    logger.info("🧪 Starting calibration simulation tests...")
    
    # Test different parameter combinations
    test_configs = [
        {
            "name": "Conservative (Low Spread)",
            "spread_probability": 0.4,
            "ignition_threshold": 0.3,
            "fuel_consumption_rate": 0.2,
            "ember_probability": 0.1,
            "expected_behavior": "Limited spread, slow burnout"
        },
        {
            "name": "Aggressive (High Spread)",
            "spread_probability": 0.9,
            "ignition_threshold": 0.05,
            "fuel_consumption_rate": 0.1,
            "ember_probability": 0.5,
            "expected_behavior": "Rapid spread, long burning"
        },
        {
            "name": "Balanced (Current)",
            "spread_probability": 0.8,
            "ignition_threshold": 0.1,
            "fuel_consumption_rate": 0.3,
            "ember_probability": 0.3,
            "expected_behavior": "Moderate spread, reasonable duration"
        },
        {
            "name": "Fast Burnout",
            "spread_probability": 0.7,
            "ignition_threshold": 0.15,
            "fuel_consumption_rate": 0.6,
            "ember_probability": 0.2,
            "expected_behavior": "Good spread, quick burnout"
        },
        {
            "name": "No Spread",
            "spread_probability": 0.2,
            "ignition_threshold": 0.5,
            "fuel_consumption_rate": 0.1,
            "ember_probability": 0.05,
            "expected_behavior": "Minimal spread, long burning"
        }
    ]
    
    results = []
    
    for test_config in test_configs:
        logger.info(f"\n🔬 Testing configuration: {test_config['name']}")
        logger.info(f"   Expected behavior: {test_config['expected_behavior']}")
        
        # Create configuration
        config = ModelConfig(
            grid_size=(30, 30),
            num_layers=5,
            max_steps=15,
            model_resolution=5.0,
            
            # Test parameters
            spread_probability=test_config['spread_probability'],
            ignition_threshold=test_config['ignition_threshold'],
            fuel_consumption_rate=test_config['fuel_consumption_rate'],
            min_fuel_value=0.1,
            max_fuel_value=1.0,
            initial_fuel_load=0.8,
            
            # Environmental factors
            wind_influence_on_spread=0.5,
            slope_influence=0.3,
            reference_wind_speed=10.0,
            
            # Ember parameters
            ember_probability=test_config['ember_probability'],
            ember_distance=5,
            ember_ignition=0.3,
            
            # Memory optimization
            memory_optimization_level=1,
            use_sparse_storage=True,
            
            # Debug mode
            debug=False,
            engine_logging_interval=5
        )
        
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
            
            # Run the full simulation
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
            
            # Analyze results
            result_data = {
                "config_name": test_config['name'],
                "max_burning_cells": max_burning,
                "final_burning_cells": final_burning,
                "steps_active": steps_active,
                "total_spread": total_spread,
                "spread_ratio": total_spread / initial_burning if initial_burning > 0 else 0,
                "burnout_rate": steps_active / config.max_steps if config.max_steps > 0 else 0,
                "total_burned": total_burned
            }
            
            results.append(result_data)
            
            logger.info(f"   Results:")
            logger.info(f"     - Max burning cells: {max_burning}")
            logger.info(f"     - Final burning cells: {final_burning}")
            logger.info(f"     - Steps active: {steps_active}/{config.max_steps}")
            logger.info(f"     - Total spread: {total_spread} cells")
            logger.info(f"     - Spread ratio: {result['spread_ratio']:.2f}")
            
            # Identify issues
            issues = []
            if total_spread < 5:
                issues.append("Very limited spread")
            if steps_active < 3:
                issues.append("Fire extinguished too quickly")
            if final_burning > 0 and steps_active == config.max_steps:
                issues.append("Fire still burning at max steps")
            
            if issues:
                logger.warning(f"   ⚠️  Issues: {', '.join(issues)}")
            else:
                logger.info(f"   ✅ No obvious issues")
                
        except Exception as e:
            logger.error(f"   ❌ Test failed: {e}")
            results.append({
                "config_name": test_config['name'],
                "error": str(e),
                "max_burning_cells": 0,
                "final_burning_cells": 0,
                "steps_active": 0,
                "total_spread": 0,
                "spread_ratio": 0,
                "burnout_rate": 0,
                "fire_progression": []
            })
    
    # Summary analysis
    logger.info("\n📊 CALIBRATION TEST SUMMARY:")
    logger.info("=" * 60)
    
    # Find best performing configuration
    valid_results = [r for r in results if 'error' not in r]
    if valid_results:
        best_spread = max(valid_results, key=lambda x: x['total_spread'])
        best_duration = max(valid_results, key=lambda x: x['steps_active'])
        best_balance = max(valid_results, key=lambda x: x['spread_ratio'] * x['burnout_rate'])
        
        logger.info(f"🏆 Best spread: {best_spread['config_name']} ({best_spread['total_spread']} cells)")
        logger.info(f"⏱️  Best duration: {best_duration['config_name']} ({best_duration['steps_active']} steps)")
        logger.info(f"⚖️  Best balance: {best_balance['config_name']} (ratio: {best_balance['spread_ratio']:.2f}, rate: {best_balance['burnout_rate']:.2f})")
    
    # Identify common issues
    logger.info("\n🔍 COMMON ISSUES IDENTIFIED:")
    logger.info("=" * 40)
    
    low_spread_count = len([r for r in valid_results if r['total_spread'] < 5])
    quick_burnout_count = len([r for r in valid_results if r['steps_active'] < 3])
    no_burnout_count = len([r for r in valid_results if r['final_burning_cells'] > 0 and r['steps_active'] == config.max_steps])
    
    if low_spread_count > 0:
        logger.warning(f"   - {low_spread_count} configurations had very limited spread")
    if quick_burnout_count > 0:
        logger.warning(f"   - {quick_burnout_count} configurations had fires extinguish too quickly")
    if no_burnout_count > 0:
        logger.warning(f"   - {no_burnout_count} configurations had fires that didn't burn out")
    
    # Recommendations
    logger.info("\n💡 RECOMMENDATIONS FOR CALIBRATION:")
    logger.info("=" * 45)
    
    if low_spread_count > len(valid_results) / 2:
        logger.info("   - Increase spread_probability (try 0.7-0.9)")
        logger.info("   - Lower ignition_threshold (try 0.05-0.15)")
        logger.info("   - Increase ember_probability (try 0.3-0.5)")
    
    if quick_burnout_count > len(valid_results) / 2:
        logger.info("   - Lower fuel_consumption_rate (try 0.1-0.3)")
        logger.info("   - Increase min_fuel_value (try 0.05-0.15)")
    
    if no_burnout_count > len(valid_results) / 2:
        logger.info("   - Increase fuel_consumption_rate (try 0.4-0.6)")
        logger.info("   - Lower min_fuel_value (try 0.05-0.1)")
    
    logger.info("\n🎯 Test complete!")

if __name__ == "__main__":
    test_simulation_behavior()
