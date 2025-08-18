#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Vertical Fire Spread Test Script

This script tests if vertical fire spread is working properly in the simulation.

Author: Forest Fire Simulation Team
Date: 2025
Version: 1.0
"""

import sys
import numpy as np
from pathlib import Path
from typing import Dict, List, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.core.forest_model import ForestModel
    from src.core.fire_simulation_engine import FireSimulationEngine
    from src.config.config_tools import ModelConfig
    from src.utils.logging_utils import get_logger
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this from the project root directory")
    sys.exit(1)

logger = get_logger(__name__)

def test_vertical_fire_spread():
    """Test vertical fire spread functionality."""
    
    print("🔥 TESTING VERTICAL FIRE SPREAD")
    print("=" * 50)
    
    # Create a small test configuration
    config = ModelConfig(
        grid_size=(20, 20),
        num_layers=5,
        model_resolution=5.0,
        max_steps=50,
        memory_optimization_level=1
    )
    
    # Create forest model
    print("📊 Creating forest model...")
    forest_model = ForestModel(
        grid_size=(20, 20),
        num_layers=5,
        config=config
    )
    
    # Check if vertical connectivity was calculated
    print("🔍 Checking vertical connectivity...")
    if hasattr(forest_model, 'vertical_connectivity'):
        vc = forest_model.vertical_connectivity
        print(f"   ✅ Vertical connectivity shape: {vc.shape}")
        print(f"   📊 Vertical connectivity range: {np.min(vc):.3f} to {np.max(vc):.3f}")
        print(f"   📊 Vertical connectivity mean: {np.mean(vc):.3f}")
        
        # Check if it's not all default values
        if np.allclose(vc, 0.5):
            print("   ⚠️  Warning: Vertical connectivity appears to be default values")
        else:
            print("   ✅ Vertical connectivity appears to be calculated properly")
    else:
        print("   ❌ No vertical connectivity found!")
        return False
    
    # Create simulation engine
    print("🚀 Creating simulation engine...")
    engine = FireSimulationEngine(forest_model=forest_model, config=config)
    
    # Set ignition in middle layer
    ignition_x, ignition_y, ignition_z = 10, 10, 2  # Middle layer
    print(f"🔥 Setting ignition at ({ignition_x}, {ignition_y}, {ignition_z})")
    forest_model.set_ignition(ignition_x, ignition_y, ignition_z)
    
    # Run simulation
    print("⏱️  Running simulation...")
    result = engine.run_simulation(max_steps=20, store_history=True)
    
    # Analyze results
    print("📊 Analyzing results...")
    stats = result['stats']
    print(f"   Total steps: {stats['steps']}")
    print(f"   Final active cells: {stats['final_active_cells']}")
    print(f"   Total burned cells: {stats['total_burned_cells']}")
    
    # Check for vertical spread
    if hasattr(forest_model, 'spread_stats'):
        spread_stats = forest_model.spread_stats
        vertical_spread = spread_stats.get('vertical_spread', 0)
        horizontal_spread = spread_stats.get('horizontal_spread', 0)
        total_spread = spread_stats.get('total_ignitions', 0)
        
        print(f"   🔥 Spread Statistics:")
        print(f"      Vertical spread events: {vertical_spread}")
        print(f"      Horizontal spread events: {horizontal_spread}")
        print(f"      Total ignitions: {total_spread}")
        
        if vertical_spread > 0:
            print("   ✅ Vertical fire spread is working!")
            vertical_percentage = (vertical_spread / total_spread * 100) if total_spread > 0 else 0
            print(f"   📊 Vertical spread percentage: {vertical_percentage:.1f}%")
        else:
            print("   ❌ No vertical fire spread detected!")
            print("   🔍 This could indicate an issue with vertical connectivity")
            return False
    else:
        print("   ⚠️  No spread statistics available")
    
    # Check final state for vertical spread
    print("🔍 Checking final state for vertical spread...")
    state = forest_model.state
    burning_cells = np.where(state == 1)  # Assuming 1 is BURNING
    
    if len(burning_cells[0]) > 0:
        print(f"   📊 Found {len(burning_cells[0])} burning cells in final state")
        
        # Check if fire spread to different layers
        unique_layers = np.unique(burning_cells[2])
        print(f"   📊 Fire spread to {len(unique_layers)} different layers: {unique_layers}")
        
        if len(unique_layers) > 1:
            print("   ✅ Vertical fire spread confirmed!")
            return True
        else:
            print("   ⚠️  Fire only spread in one layer")
            return False
    else:
        print("   ❌ No burning cells in final state")
        return False

def main():
    """Main test function."""
    print("🎯 VERTICAL FIRE SPREAD TEST")
    print("=" * 60)
    
    try:
        success = test_vertical_fire_spread()
        
        if success:
            print("\n✅ VERTICAL FIRE SPREAD TEST PASSED!")
            print("   Vertical fire spread is working properly")
        else:
            print("\n❌ VERTICAL FIRE SPREAD TEST FAILED!")
            print("   Vertical fire spread is not working")
            print("   This may affect sensitivity analysis results")
        
        return success
        
    except Exception as e:
        print(f"\n❌ TEST FAILED WITH ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
