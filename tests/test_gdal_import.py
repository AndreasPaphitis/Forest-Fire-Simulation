#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
GDAL Import Test Script

This script helps diagnose GDAL import issues and provides solutions.
"""

import sys
import os

def test_gdal_import():
    """Test GDAL import and provide troubleshooting steps."""
    print("🔍 GDAL Import Test")
    print("=" * 50)
    
    # Test 1: Basic import
    print("1️⃣ Testing basic GDAL import...")
    try:
        from osgeo import gdal
        print("✅ GDAL import successful!")
        print(f"   GDAL version: {gdal.VersionInfo()}")
        return True
    except ImportError as e:
        print(f"❌ GDAL import failed: {e}")
        return False

def test_gdal_installation():
    """Test different GDAL installation methods."""
    print("\n2️⃣ Testing GDAL installation methods...")
    
    # Method 1: Try conda installation
    print("   Method 1: Conda installation")
    print("   Run: conda install -c conda-forge gdal")
    
    # Method 2: Try pip installation
    print("   Method 2: Pip installation")
    print("   Run: pip install GDAL")
    
    # Method 3: Try specific GDAL version
    print("   Method 3: Specific GDAL version")
    print("   Run: pip install GDAL==3.4.3")
    
    # Method 4: Try OSGeo4W (Windows)
    print("   Method 4: OSGeo4W (Windows)")
    print("   Download from: https://trac.osgeo.org/osgeo4w/")

def check_python_environment():
    """Check Python environment details."""
    print("\n3️⃣ Python Environment Details:")
    print(f"   Python version: {sys.version}")
    print(f"   Python executable: {sys.executable}")
    print(f"   Python path: {sys.path[:3]}...")  # Show first 3 paths
    
    # Check if we're in a virtual environment
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("   ✅ Virtual environment detected")
    else:
        print("   ℹ️  No virtual environment detected")

def provide_solutions():
    """Provide specific solutions for GDAL installation."""
    print("\n4️⃣ Solutions:")
    print("   If you're using conda:")
    print("   ```bash")
    print("   conda install -c conda-forge gdal")
    print("   ```")
    print()
    print("   If you're using pip:")
    print("   ```bash")
    print("   pip install GDAL")
    print("   ```")
    print()
    print("   If you're on Windows and the above don't work:")
    print("   1. Download OSGeo4W from https://trac.osgeo.org/osgeo4w/")
    print("   2. Install GDAL through OSGeo4W")
    print("   3. Add OSGeo4W to your PATH")
    print()
    print("   Alternative: Use a different GDAL version")
    print("   ```bash")
    print("   pip install GDAL==3.4.3")
    print("   ```")

def test_alternative_imports():
    """Test alternative GDAL import methods."""
    print("\n5️⃣ Testing alternative import methods...")
    
    # Method 1: Direct import
    try:
        import gdal
        print("✅ Direct gdal import successful")
    except ImportError:
        print("❌ Direct gdal import failed")
    
    # Method 2: Try different import paths
    try:
        import osgeo.gdal as gdal
        print("✅ osgeo.gdal import successful")
    except ImportError:
        print("❌ osgeo.gdal import failed")

if __name__ == "__main__":
    print("🔍 GDAL Import Diagnostic Tool")
    print("=" * 60)
    
    # Check Python environment
    check_python_environment()
    
    # Test GDAL import
    gdal_available = test_gdal_import()
    
    if not gdal_available:
        # Test alternative imports
        test_alternative_imports()
        
        # Provide solutions
        test_gdal_installation()
        provide_solutions()
        
        print("\n❌ GDAL is not available in your current environment.")
        print("   Please install GDAL using one of the methods above.")
    else:
        print("\n✅ GDAL is working correctly!")
        print("   You should be able to run the terrain preprocessing script.")
        
        # Test if we can open a file
        print("\n6️⃣ Testing file opening capability...")
        try:
            from osgeo import gdal
            gdal.UseExceptions()
            print("✅ GDAL exceptions enabled")
        except Exception as e:
            print(f"❌ Error enabling GDAL exceptions: {e}") 