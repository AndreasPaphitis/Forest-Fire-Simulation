#!/usr/bin/env python3
"""
Test Dependencies

This script tests if all required dependencies are installed and working.
"""

import sys
import time

def test_dependencies():
    """Test all required dependencies."""
    print("🧪 TESTING DEPENDENCIES")
    print("=" * 40)
    
    dependencies = [
        ('numpy', 'numpy'),
        ('scipy', 'scipy'),
        ('GDAL', 'osgeo.gdal'),
        ('scikit-image', 'skimage'),
        ('matplotlib', 'matplotlib'),
        ('psutil', 'psutil'),
        ('tqdm', 'tqdm'),
        ('pandas', 'pandas'),
        ('rasterio', 'rasterio'),
        ('geopandas', 'geopandas'),
        ('shapely', 'shapely'),
        ('fiona', 'fiona'),
        ('pyproj', 'pyproj'),
        ('imageio', 'imageio'),
        ('imageio-ffmpeg', 'imageio_ffmpeg'),
        ('numba', 'numba'),
        ('pytest', 'pytest'),
        ('black', 'black'),
        ('flake8', 'flake8'),
        ('memory-profiler', 'memory_profiler'),
    ]
    
    results = []
    
    for package_name, import_name in dependencies:
        try:
            __import__(import_name)
            print(f"✅ {package_name}")
            results.append((package_name, True, None))
        except ImportError as e:
            print(f"❌ {package_name}: {e}")
            results.append((package_name, False, str(e)))
        except Exception as e:
            print(f"⚠️  {package_name}: {e}")
            results.append((package_name, False, str(e)))
    
    print("\n📊 SUMMARY:")
    print("=" * 40)
    
    successful = [r for r in results if r[1]]
    failed = [r for r in results if not r[1]]
    
    print(f"✅ Successful: {len(successful)}/{len(dependencies)}")
    print(f"❌ Failed: {len(failed)}/{len(dependencies)}")
    
    if failed:
        print("\n❌ MISSING DEPENDENCIES:")
        for package_name, success, error in failed:
            print(f"   - {package_name}: {error}")
        
        print("\n💡 INSTALLATION COMMANDS:")
        print("pip install -r requirements-minimal.txt")
        print("pip install -r requirements.txt")
    
    return len(failed) == 0

def test_project_imports():
    """Test if project modules can be imported."""
    print("\n🔧 TESTING PROJECT IMPORTS")
    print("=" * 40)
    
    project_modules = [
        'src.config.config_tools',
        'src.core.calibration.grid_search',
        'src.core.calibration.calibration_config',
        'src.core.calibration.parameter_bounds',
        'src.core.calibration.objective_functions',
        'src.core.forest_model',
        'src.core.fire_simulation_engine',
        'src.utils.shared_terrain',
        'src.utils.memory_manager',
    ]
    
    results = []
    
    for module_name in project_modules:
        try:
            __import__(module_name)
            print(f"✅ {module_name}")
            results.append((module_name, True, None))
        except ImportError as e:
            print(f"❌ {module_name}: {e}")
            results.append((module_name, False, str(e)))
        except Exception as e:
            print(f"⚠️  {module_name}: {e}")
            results.append((module_name, False, str(e)))
    
    print("\n📊 PROJECT IMPORTS SUMMARY:")
    print("=" * 40)
    
    successful = [r for r in results if r[1]]
    failed = [r for r in results if not r[1]]
    
    print(f"✅ Successful: {len(successful)}/{len(project_modules)}")
    print(f"❌ Failed: {len(failed)}/{len(project_modules)}")
    
    if failed:
        print("\n❌ FAILED PROJECT IMPORTS:")
        for module_name, success, error in failed:
            print(f"   - {module_name}: {error}")
    
    return len(failed) == 0

def main():
    """Main test function."""
    print("🧪 DEPENDENCY AND IMPORT TEST")
    print("=" * 60)
    
    deps_ok = test_dependencies()
    imports_ok = test_project_imports()
    
    print("\n🎯 FINAL RESULT:")
    print("=" * 40)
    
    if deps_ok and imports_ok:
        print("✅ ALL TESTS PASSED!")
        print("✅ Dependencies are installed correctly")
        print("✅ Project modules can be imported")
        print("✅ Ready to run calibration tests")
        return True
    else:
        print("❌ SOME TESTS FAILED!")
        if not deps_ok:
            print("❌ Missing dependencies - install with pip")
        if not imports_ok:
            print("❌ Project import issues - check Python path")
        return False

if __name__ == "__main__":
    main()
