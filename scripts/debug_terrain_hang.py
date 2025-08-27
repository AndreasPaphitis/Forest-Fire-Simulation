#!/usr/bin/env python
"""
Diagnostic script to identify terrain loading hang issues
"""
import sys
import os
import time
import logging
import threading
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_terrain_file_access():
    """Test basic file access to terrain files"""
    print("🔍 Testing terrain file access...")
    
    terrain_dir = Path(r'C:\Users\user\Desktop\UvA\YEAR 2\Thesis\Coding\QGIS python scripts\preprocessed_terrain')
    
    if not terrain_dir.exists():
        print(f"❌ Terrain directory not found: {terrain_dir}")
        return False
    
    print(f"✅ Terrain directory found: {terrain_dir}")
    
    # List terrain files
    terrain_files = list(terrain_dir.glob("*.npy"))
    print(f"📁 Found {len(terrain_files)} terrain files:")
    
    for file in terrain_files:
        try:
            size = file.stat().st_size
            print(f"   {file.name}: {size / (1024*1024):.1f} MB")
        except Exception as e:
            print(f"   ❌ Error reading {file.name}: {e}")
    
    return len(terrain_files) > 0

def test_numpy_import():
    """Test numpy import and basic functionality"""
    print("\n🔍 Testing numpy import...")
    
    try:
        import numpy as np
        print("✅ NumPy imported successfully")
        print(f"   NumPy version: {np.__version__}")
        return True
    except Exception as e:
        print(f"❌ NumPy import failed: {e}")
        return False

def test_single_terrain_load():
    """Test loading a single terrain file"""
    print("\n🔍 Testing single terrain file load...")
    
    terrain_dir = Path(r'C:\Users\user\Desktop\UvA\YEAR 2\Thesis\Coding\QGIS python scripts\preprocessed_terrain')
    elevation_file = terrain_dir / "elevation.npy"
    
    if not elevation_file.exists():
        print(f"❌ Elevation file not found: {elevation_file}")
        return False
    
    print(f"📁 Testing elevation file: {elevation_file}")
    print(f"   File size: {elevation_file.stat().st_size / (1024*1024):.1f} MB")
    
    # Test with timeout
    result = None
    error = None
    
    def load_file():
        nonlocal result, error
        try:
            import numpy as np
            print("   🔄 Starting memory-mapped load...")
            result = np.load(elevation_file, mmap_mode='r')
            print("   ✅ Memory-mapped load completed")
        except Exception as e:
            print(f"   ❌ Load failed: {e}")
            error = e
    
    # Run in thread with timeout
    thread = threading.Thread(target=load_file)
    thread.daemon = True
    thread.start()
    
    print("   ⏱️  Waiting for load to complete (timeout: 60s)...")
    thread.join(timeout=60)
    
    if thread.is_alive():
        print("   ⏰ TIMEOUT: Load is hanging!")
        return False
    elif error:
        print(f"   ❌ Load error: {error}")
        return False
    else:
        print(f"   ✅ Load successful, shape: {result.shape}")
        return True

def test_forest_model_import():
    """Test importing ForestModel"""
    print("\n🔍 Testing ForestModel import...")
    
    try:
        from src.core.forest_model import ForestModel
        print("✅ ForestModel imported successfully")
        return True
    except Exception as e:
        print(f"❌ ForestModel import failed: {e}")
        return False

def test_forest_model_creation():
    """Test creating ForestModel instance"""
    print("\n🔍 Testing ForestModel creation...")
    
    try:
        from src.core.forest_model import ForestModel
        from src.config import ModelConfig
        
        print("   🔄 Creating ModelConfig...")
        config = ModelConfig(
            grid_size=(609, 609),
            use_preprocessed_terrain=True,
            preprocessed_terrain_dir=r'C:\Users\user\Desktop\UvA\YEAR 2\Thesis\Coding\QGIS python scripts\preprocessed_terrain'
        )
        print("   ✅ ModelConfig created")
        
        print("   🔄 Creating ForestModel...")
        model = ForestModel(
            width=609,
            height=609,
            config=config
        )
        print("   ✅ ForestModel created successfully")
        return True
        
    except Exception as e:
        print(f"   ❌ ForestModel creation failed: {e}")
        return False

def main():
    print("🚀 TERRAIN LOADING DIAGNOSTIC")
    print("=" * 50)
    
    tests = [
        ("File Access", test_terrain_file_access),
        ("NumPy Import", test_numpy_import),
        ("Single Terrain Load", test_single_terrain_load),
        ("ForestModel Import", test_forest_model_import),
        ("ForestModel Creation", test_forest_model_creation),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running test: {test_name}")
        print("-" * 30)
        
        start_time = time.time()
        try:
            success = test_func()
            end_time = time.time()
            duration = end_time - start_time
            
            if success:
                print(f"✅ {test_name}: PASSED ({duration:.2f}s)")
                results.append((test_name, "PASSED", duration))
            else:
                print(f"❌ {test_name}: FAILED ({duration:.2f}s)")
                results.append((test_name, "FAILED", duration))
                
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            print(f"💥 {test_name}: ERROR ({duration:.2f}s) - {e}")
            results.append((test_name, "ERROR", duration))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 DIAGNOSTIC SUMMARY")
    print("=" * 50)
    
    for test_name, status, duration in results:
        print(f"{test_name:20} {status:8} {duration:6.2f}s")
    
    # Recommendations
    print("\n💡 RECOMMENDATIONS:")
    
    failed_tests = [name for name, status, _ in results if status != "PASSED"]
    
    if not failed_tests:
        print("✅ All tests passed - terrain loading should work")
        print("   If calibration still hangs, the issue may be elsewhere")
    else:
        print(f"❌ Failed tests: {', '.join(failed_tests)}")
        if "Single Terrain Load" in failed_tests:
            print("   💡 Terrain file loading is hanging - check file integrity")
        if "ForestModel Creation" in failed_tests:
            print("   💡 ForestModel creation is failing - check configuration")

if __name__ == "__main__":
    main()
