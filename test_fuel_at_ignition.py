#!/usr/bin/env python3
"""
Test script to verify fuel loading and ignition functionality.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.config.config_tools import ModelConfig
from src.core.forest_model import ForestModel
from src.core.fire_simulation_engine import FireSimulationEngine
from src.core.calibration.objective_functions import FrameworkCellState

def test_lidar_loading():
    """Test LiDAR data loading."""
    print("🔍 Testing LiDAR data loading...")
    
    try:
        config = ModelConfig()
        config.preprocessed_lidar_dir = "preprocessed_lidar"
        config.grid_size = (609, 609)
        config.num_layers = 20
        config.use_lidar = True
        
        print(f"🔍 ForestModel: Config has preprocessed_lidar_dir: {hasattr(config, 'preprocessed_lidar_dir')}")
        if hasattr(config, 'preprocessed_lidar_dir'):
            print(f"🔍 ForestModel: LiDAR directory: {config.preprocessed_lidar_dir}")
        
        model = ForestModel(config=config)
        
        # Check if LiDAR data was loaded
        if hasattr(model, 'fuel_load_layers') and model.fuel_load_layers:
            print(f"✅ LiDAR data loaded: {len(model.fuel_load_layers)} layers")
            return True
        else:
            print("❌ No LiDAR data found")
            return False
            
    except Exception as e:
        print(f"❌ Error in LiDAR test: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_forest_model_initialization():
    """Test forest model initialization."""
    print("🌲 Testing forest model initialization...")
    
    try:
        config = ModelConfig()
        config.preprocessed_lidar_dir = "preprocessed_lidar"
        config.grid_size = (609, 609)
        config.num_layers = 20
        config.use_lidar = True
        
        model = ForestModel(config=config)
        
        print(f"✅ Forest model created: {type(model)}")
        print(f"✅ Grid size: {model.width} x {model.height} x {model.num_layers}")
        print(f"✅ Sparse storage: {getattr(model, 'use_sparse_storage', False)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in forest model test: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ignition_setting():
    """Test setting ignition and checking active cells."""
    print("🔥 Testing ignition setting...")
    
    try:
        config = ModelConfig()
        config.preprocessed_lidar_dir = "preprocessed_lidar"
        config.grid_size = (609, 609)
        config.num_layers = 20
        config.use_lidar = True
        
        model = ForestModel(config=config)
        
        # Set ignition point to Arafo highlands
        ignition_x = int(model.width * 0.65)  # 65% of grid width
        ignition_y = int(model.height * 0.62)  # 62% of grid height
        
        print(f"🔥 Setting ignition at ({ignition_x}, {ignition_y}, 0)")
        
        # Check fuel at ignition point
        if hasattr(model, 'fuel_load_layers') and 0 in model.fuel_load_layers:
            fuel_value = model.fuel_load_layers[0][ignition_x, ignition_y]
            print(f"🔥 Fuel at ignition point (395, 377): {fuel_value}")
        
        # Set ignition
        model.set_ignition(ignition_x, ignition_y, 0)
        
        # Check active cells
        active_cells = model.get_active_cells()
        print(f"Active cells after ignition: {len(active_cells)}")
        
        if active_cells:
            print("✅ Ignition successful - active cells found")
            for cell in active_cells[:5]:  # Show first 5
                print(f"  Active cell: {cell}")
        else:
            print("❌ No active cells after ignition")
            
            # Check fuel at ignition point
            if hasattr(model, 'fuel_load_layers') and 0 in model.fuel_load_layers:
                fuel_value = model.fuel_load_layers[0][ignition_x, ignition_y]
                print(f"Fuel at ignition point: {fuel_value}")
                
                # Check ignition threshold
                ignition_threshold = getattr(config, 'ignition_threshold', 0.08)
                print(f"Ignition threshold: {ignition_threshold}")
                
                if fuel_value < ignition_threshold:
                    print(f"❌ Fuel value ({fuel_value}) below ignition threshold ({ignition_threshold})")
                else:
                    print(f"✅ Fuel value ({fuel_value}) above ignition threshold ({ignition_threshold})")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in ignition test: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_fire_spread():
    """Test fire spread over a few simulation steps."""
    print("🔥 Testing fire spread...")
    
    try:
        config = ModelConfig()
        config.preprocessed_lidar_dir = "preprocessed_lidar"
        config.grid_size = (609, 609)
        config.num_layers = 20
        config.use_lidar = True
        config.max_steps = 10  # Limit to 10 steps for testing
        
        model = ForestModel(config=config)
        
        # Set ignition point
        ignition_x = int(model.width * 0.65)
        ignition_y = int(model.height * 0.62)
        model.set_ignition(ignition_x, ignition_y, 0)
        
        # Create simulation engine
        engine = FireSimulationEngine(forest_model=model, config=config)
        
        print(f"🔥 Starting simulation with {len(engine.active_cells)} initial active cells")
        
        # Run a few steps
        for step in range(5):
            print(f"🔥 Step {step + 1}: {len(engine.active_cells)} active cells")
            
            # Process one step
            engine._process_step()
            
            # Check if fire is spreading
            if len(engine.active_cells) > 1:
                print(f"✅ Fire is spreading! {len(engine.active_cells)} active cells")
                return True
            elif len(engine.active_cells) == 0:
                print(f"❌ Fire went out at step {step + 1}")
                return False
        
        print(f"⚠️ Fire not spreading significantly after 5 steps")
        return False
        
    except Exception as e:
        print(f"❌ Error in fire spread test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 Starting fuel and ignition tests...")
    print("=" * 50)
    
    # Run tests
    tests = [
        ("LiDAR Loading", test_lidar_loading),
        ("Forest Model Initialization", test_forest_model_initialization),
        ("Ignition Setting", test_ignition_setting),
        ("Fire Spread", test_fire_spread),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name} test...")
        print("-" * 30)
        result = test_func()
        results.append((test_name, result))
        print(f"{'✅ PASSED' if result else '❌ FAILED'}: {test_name}")
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY:")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {status}: {test_name}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
    else:
        print("⚠️ Some tests failed - check the output above")
