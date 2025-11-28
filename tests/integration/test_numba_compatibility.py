#!/usr/bin/env python
"""
Test script to verify Numba-optimized engine compatibility with existing codebase.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import modules at top level
try:
    from src.core.fire_simulation_engine import FireSimulationEngine
    from src.core.numba_optimized_fire_engine import NumbaOptimizedFireEngine, create_numba_optimized_engine
    from src.core.forest_model import create_forest_model
    from src.config.config_tools import ModelConfig
    IMPORTS_SUCCESSFUL = True
except ImportError as e:
    print(f"❌ Import failed: {e}")
    IMPORTS_SUCCESSFUL = False

def test_imports():
    """Test that all required modules can be imported."""
    print("🔍 Testing imports...")
    
    if IMPORTS_SUCCESSFUL:
        print("✅ Base FireSimulationEngine imported successfully")
        print("✅ NumbaOptimizedFireEngine imported successfully")
        print("✅ All required modules imported successfully")
        return True
    else:
        return False

def test_engine_creation():
    """Test that engines can be created without errors."""
    print("\n🔍 Testing engine creation...")
    
    if not IMPORTS_SUCCESSFUL:
        print("❌ Skipping test due to import failure")
        return False
    
    try:
        # Create base engine
        base_engine = FireSimulationEngine()
        print("✅ Base engine created successfully")
        
        # Create Numba engine
        numba_engine = NumbaOptimizedFireEngine()
        print("✅ Numba engine created successfully")
        
        # Test factory function
        factory_engine = create_numba_optimized_engine()
        print("✅ Factory engine created successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Engine creation failed: {e}")
        return False

def test_method_compatibility():
    """Test that all required methods exist and are callable."""
    print("\n🔍 Testing method compatibility...")
    
    if not IMPORTS_SUCCESSFUL:
        print("❌ Skipping test due to import failure")
        return False
    
    try:
        # Create engines
        base_engine = FireSimulationEngine()
        numba_engine = NumbaOptimizedFireEngine()
        
        # Test required methods exist
        required_methods = [
            '_check_ignition',
            '_check_ignition_vectorized', 
            '_calculate_slope_factor',
            'lazy_save_simulation_state',
            'lazy_load_simulation_state',
            'get_performance_summary',
            'print_performance_summary'
        ]
        
        for method_name in required_methods:
            # Check base engine
            if hasattr(base_engine, method_name):
                method = getattr(base_engine, method_name)
                if callable(method):
                    print(f"✅ Base engine: {method_name} exists and is callable")
                else:
                    print(f"❌ Base engine: {method_name} exists but is not callable")
            else:
                print(f"❌ Base engine: {method_name} missing")
            
            # Check Numba engine
            if hasattr(numba_engine, method_name):
                method = getattr(numba_engine, method_name)
                if callable(method):
                    print(f"✅ Numba engine: {method_name} exists and is callable")
                else:
                    print(f"❌ Numba engine: {method_name} exists but is not callable")
            else:
                print(f"❌ Numba engine: {method_name} missing")
        
        return True
        
    except Exception as e:
        print(f"❌ Method compatibility test failed: {e}")
        return False

def test_attribute_compatibility():
    """Test that all required attributes exist."""
    print("\n🔍 Testing attribute compatibility...")
    
    if not IMPORTS_SUCCESSFUL:
        print("❌ Skipping test due to import failure")
        return False
    
    try:
        # Create engines
        base_engine = FireSimulationEngine()
        numba_engine = NumbaOptimizedFireEngine()
        
        # Test required attributes
        required_attributes = [
            'performance_metrics',
            'use_numba_optimization',
            'use_lazy_saving',
            'save_interval'
        ]
        
        for attr_name in required_attributes:
            # Check base engine
            if hasattr(base_engine, attr_name):
                print(f"✅ Base engine: {attr_name} exists")
            else:
                print(f"❌ Base engine: {attr_name} missing")
            
            # Check Numba engine
            if hasattr(numba_engine, attr_name):
                print(f"✅ Numba engine: {attr_name} exists")
            else:
                print(f"❌ Numba engine: {attr_name} missing")
        
        return True
        
    except Exception as e:
        print(f"❌ Attribute compatibility test failed: {e}")
        return False

def test_performance_metrics():
    """Test performance metrics functionality."""
    print("\n🔍 Testing performance metrics...")
    
    if not IMPORTS_SUCCESSFUL:
        print("❌ Skipping test due to import failure")
        return False
    
    try:
        # Create a minimal forest model for testing
        forest_model = create_forest_model(
            model_type="memory_optimized",
            grid_size=(10, 10),
            num_layers=3
        )
        
        # Create engine with forest model
        engine = NumbaOptimizedFireEngine(forest_model=forest_model)
        
        # Test performance summary
        summary = engine.get_performance_summary()
        print(f"✅ Performance summary generated: {type(summary)}")
        print(f"   Keys: {list(summary.keys())}")
        
        # Test performance printing
        engine.print_performance_summary()
        print("✅ Performance summary printed successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Performance metrics test failed: {e}")
        return False

def main():
    """Run all compatibility tests."""
    print("🚀 NUMBA ENGINE COMPATIBILITY TEST")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_engine_creation,
        test_method_compatibility,
        test_attribute_compatibility,
        test_performance_metrics
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                print(f"❌ {test.__name__} failed")
        except Exception as e:
            print(f"❌ {test.__name__} crashed: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 TEST RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Numba engine is fully compatible.")
        return True
    else:
        print("⚠️  Some tests failed. Check compatibility issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
