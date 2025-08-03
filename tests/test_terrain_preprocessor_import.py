#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test Terrain Preprocessor Import

This script tests if the terrain preprocessor can import GDAL correctly.
"""

import sys
import os

def test_direct_gdal_import():
    """Test direct GDAL import."""
    print("1️⃣ Testing direct GDAL import...")
    try:
        from osgeo import gdal
        print("✅ Direct GDAL import successful")
        return True
    except ImportError as e:
        print(f"❌ Direct GDAL import failed: {e}")
        return False

def test_terrain_preprocessor_import():
    """Test terrain preprocessor import."""
    print("\n2️⃣ Testing terrain preprocessor import...")
    try:
        from src.utils.terrain_preprocessor import TerrainPreprocessor, GDAL_AVAILABLE
        print(f"✅ Terrain preprocessor import successful")
        print(f"   GDAL_AVAILABLE: {GDAL_AVAILABLE}")
        return GDAL_AVAILABLE
    except ImportError as e:
        print(f"❌ Terrain preprocessor import failed: {e}")
        return False

def test_terrain_preprocessor_function():
    """Test terrain preprocessor function import."""
    print("\n3️⃣ Testing terrain preprocessor function import...")
    try:
        from src.utils.terrain_preprocessor import create_terrain_preprocessor
        print("✅ create_terrain_preprocessor import successful")
        return True
    except ImportError as e:
        print(f"❌ create_terrain_preprocessor import failed: {e}")
        return False

def test_gdal_availability_in_module():
    """Test GDAL availability when imported through the module."""
    print("\n4️⃣ Testing GDAL availability in module...")
    try:
        # Import the module and check GDAL_AVAILABLE
        import src.utils.terrain_preprocessor as tp
        print(f"✅ Module import successful")
        print(f"   GDAL_AVAILABLE: {tp.GDAL_AVAILABLE}")
        
        if not tp.GDAL_AVAILABLE:
            print("❌ GDAL_AVAILABLE is False in the module")
            return False
        else:
            print("✅ GDAL_AVAILABLE is True in the module")
            return True
            
    except Exception as e:
        print(f"❌ Module import failed: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Terrain Preprocessor Import Test")
    print("=" * 60)
    
    # Test 1: Direct GDAL import
    gdal_direct = test_direct_gdal_import()
    
    # Test 2: Terrain preprocessor import
    tp_import = test_terrain_preprocessor_import()
    
    # Test 3: Function import
    func_import = test_terrain_preprocessor_function()
    
    # Test 4: GDAL availability in module
    gdal_module = test_gdal_availability_in_module()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS")
    print("=" * 60)
    print(f"Direct GDAL import: {'✅ PASS' if gdal_direct else '❌ FAIL'}")
    print(f"Terrain preprocessor import: {'✅ PASS' if tp_import else '❌ FAIL'}")
    print(f"Function import: {'✅ PASS' if func_import else '❌ FAIL'}")
    print(f"GDAL in module: {'✅ PASS' if gdal_module else '❌ FAIL'}")
    
    if all([gdal_direct, tp_import, func_import, gdal_module]):
        print("\n🎉 All tests passed! Terrain preprocessing should work.")
    else:
        print("\n❌ Some tests failed. There may be an import issue.")
        
        if not gdal_module and gdal_direct:
            print("\n🔧 SOLUTION: The issue is that GDAL_AVAILABLE is False in the module.")
            print("   This suggests the import is happening at module load time when")
            print("   the path might not be set up correctly.") 