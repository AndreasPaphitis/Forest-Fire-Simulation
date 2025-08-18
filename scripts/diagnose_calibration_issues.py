#!/usr/bin/env python3
"""
Diagnostic script to identify calibration issues with fire propagation and extinction.
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
import logging

def diagnose_calibration_issues():
    """Diagnose the specific issues with fire propagation and extinction."""
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger("calibration_diagnostic")
    logger.info("🔍 Starting calibration diagnostic...")
    
    # Create a test configuration
    config = ModelConfig(
        grid_size=(50, 50),
        num_layers=5,
        max_steps=20,
        model_resolution=5.0,
        
        # Test different parameter combinations
        spread_probability=0.8,
        ignition_threshold=0.1,
        fuel_consumption_rate=0.3,
        min_fuel_value=0.1,
        max_fuel_value=1.0,
        
        # Environmental factors
        wind_influence_on_spread=0.5,
        slope_influence=0.3,
        reference_wind_speed=10.0,
        
        # Ember parameters
        ember_probability=0.3,
        ember_distance=5,
        ember_ignition=0.3,
        
        # Memory optimization
        memory_optimization_level=1,
        use_sparse_storage=True,
        
        # Debug mode
        debug=True,
        engine_logging_interval=1
    )
    
    logger.info("📊 Configuration created:")
    logger.info(f"   - Spread probability: {config.spread_probability}")
    logger.info(f"   - Ignition threshold: {config.ignition_threshold}")
    logger.info(f"   - Fuel consumption rate: {config.fuel_consumption_rate}")
    logger.info(f"   - Min fuel value: {config.min_fuel_value}")
    logger.info(f"   - Max fuel value: {config.max_fuel_value}")
    
    # Create forest model
    try:
        forest_model = ForestModel(
            grid_size=config.grid_size,
            num_layers=config.num_layers,
            layer_height_meters=config.layer_height,
            model_resolution=config.model_resolution,
            initial_fuel_load=config.initial_fuel_load,
            config=config
        )
        logger.info("✅ Forest model created successfully")
    except Exception as e:
        logger.error(f"❌ Failed to create forest model: {e}")
        return
    
    # Create fire simulation engine
    try:
        engine = FireSimulationEngine(forest_model, config)
        logger.info("✅ Fire simulation engine created successfully")
    except Exception as e:
        logger.error(f"❌ Failed to create fire simulation engine: {e}")
        return
    
    # Test ignition probability calculation
    logger.info("\n🧪 Testing ignition probability calculation...")
    
    # Test with different scenarios
    test_scenarios = [
        {"name": "High fuel, no wind", "fuel": 1.0, "wind_speed": 0.0, "slope": 0.0},
        {"name": "Low fuel, no wind", "fuel": 0.2, "wind_speed": 0.0, "slope": 0.0},
        {"name": "High fuel, high wind", "fuel": 1.0, "wind_speed": 15.0, "slope": 0.0},
        {"name": "High fuel, uphill", "fuel": 1.0, "wind_speed": 0.0, "slope": 0.5},
        {"name": "High fuel, downhill", "fuel": 1.0, "wind_speed": 0.0, "slope": -0.5},
    ]
    
    for scenario in test_scenarios:
        logger.info(f"\n📋 Testing scenario: {scenario['name']}")
        
        # Simulate the scenario
        base_prob = config.spread_probability
        fuel_factor = scenario['fuel']
        wind_factor = 1.0 + (scenario['wind_speed'] / config.reference_wind_speed) * config.wind_influence_on_spread
        slope_factor = 1.0 + config.slope_influence * scenario['slope']
        distance_factor = 1.0  # Orthogonal spread
        
        ignition_prob = base_prob * fuel_factor * wind_factor * slope_factor * distance_factor
        effective_prob = max(0.0, min(1.0, ignition_prob))
        will_ignite = effective_prob >= config.ignition_threshold
        
        logger.info(f"   - Base probability: {base_prob:.3f}")
        logger.info(f"   - Fuel factor: {fuel_factor:.3f}")
        logger.info(f"   - Wind factor: {wind_factor:.3f}")
        logger.info(f"   - Slope factor: {slope_factor:.3f}")
        logger.info(f"   - Final probability: {effective_prob:.3f}")
        logger.info(f"   - Ignition threshold: {config.ignition_threshold:.3f}")
        logger.info(f"   - Will ignite: {will_ignite}")
        
        if not will_ignite:
            logger.warning(f"   ⚠️  Fire will NOT spread in this scenario!")
    
    # Test burnout calculation
    logger.info("\n🔥 Testing burnout calculation...")
    
    # Test different fuel consumption scenarios
    burnout_scenarios = [
        {"name": "High fuel consumption", "consumption_rate": 0.8, "initial_fuel": 1.0},
        {"name": "Low fuel consumption", "consumption_rate": 0.1, "initial_fuel": 1.0},
        {"name": "Low initial fuel", "consumption_rate": 0.3, "initial_fuel": 0.2},
    ]
    
    for scenario in burnout_scenarios:
        logger.info(f"\n📋 Testing burnout scenario: {scenario['name']}")
        
        initial_fuel = scenario['initial_fuel']
        consumption_rate = scenario['consumption_rate']
        min_fuel = config.min_fuel_value
        
        # Calculate how many steps until burnout
        remaining_fuel = initial_fuel
        steps_to_burnout = 0
        
        while remaining_fuel > min_fuel and steps_to_burnout < 50:
            remaining_fuel -= consumption_rate
            steps_to_burnout += 1
        
        logger.info(f"   - Initial fuel: {initial_fuel:.3f}")
        logger.info(f"   - Consumption rate: {consumption_rate:.3f}")
        logger.info(f"   - Min fuel threshold: {min_fuel:.3f}")
        logger.info(f"   - Steps to burnout: {steps_to_burnout}")
        logger.info(f"   - Final fuel: {max(min_fuel, remaining_fuel):.3f}")
        
        if steps_to_burnout <= 3:
            logger.warning(f"   ⚠️  Fire will burn out too quickly!")
        elif steps_to_burnout > 20:
            logger.info(f"   ✅ Fire will burn for a reasonable duration")
    
    # Test ember generation
    logger.info("\n🌪️ Testing ember generation...")
    
    ember_prob = config.ember_probability
    ember_distance = config.ember_distance
    ember_ignition = config.ember_ignition
    
    logger.info(f"   - Ember probability: {ember_prob:.3f}")
    logger.info(f"   - Ember distance: {ember_distance}")
    logger.info(f"   - Ember ignition probability: {ember_ignition:.3f}")
    
    # Calculate effective ember ignition probability
    effective_ember_ignition = ember_prob * ember_ignition
    logger.info(f"   - Effective ember ignition: {effective_ember_ignition:.3f}")
    
    if effective_ember_ignition < 0.05:
        logger.warning(f"   ⚠️  Ember ignition is too low for effective long-range spread!")
    
    logger.info("\n🎯 DIAGNOSTIC SUMMARY:")
    logger.info("=" * 50)
    
    # Check for potential issues
    issues = []
    
    if config.ignition_threshold > 0.3:
        issues.append("Ignition threshold too high - fires won't spread")
    
    if config.fuel_consumption_rate > 0.5:
        issues.append("Fuel consumption too high - fires burn out too fast")
    
    if config.spread_probability < 0.6:
        issues.append("Spread probability too low - limited fire propagation")
    
    if config.ember_probability * config.ember_ignition < 0.05:
        issues.append("Ember ignition too low - no long-range spread")
    
    if config.min_fuel_value > 0.2:
        issues.append("Min fuel threshold too high - fires extinguish too easily")
    
    if issues:
        logger.error("❌ POTENTIAL ISSUES IDENTIFIED:")
        for issue in issues:
            logger.error(f"   - {issue}")
    else:
        logger.info("✅ No obvious issues identified in current configuration")
    
    # Suggest parameter adjustments
    logger.info("\n💡 SUGGESTED PARAMETER ADJUSTMENTS:")
    logger.info("=" * 50)
    
    if config.ignition_threshold > 0.2:
        logger.info(f"   - Lower ignition_threshold from {config.ignition_threshold} to 0.1")
    
    if config.fuel_consumption_rate > 0.4:
        logger.info(f"   - Lower fuel_consumption_rate from {config.fuel_consumption_rate} to 0.3")
    
    if config.spread_probability < 0.7:
        logger.info(f"   - Increase spread_probability from {config.spread_probability} to 0.8")
    
    if config.ember_probability < 0.2:
        logger.info(f"   - Increase ember_probability from {config.ember_probability} to 0.3")
    
    if config.min_fuel_value > 0.15:
        logger.info(f"   - Lower min_fuel_value from {config.min_fuel_value} to 0.1")
    
    logger.info("\n🔍 Diagnostic complete!")

if __name__ == "__main__":
    diagnose_calibration_issues()
