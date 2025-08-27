#!/usr/bin/env python3
"""
Comprehensive Dependency Checker for Forest Fire Calibration

This script checks ALL dependencies required for the calibration system.
Run this before starting calibration to ensure everything is available.
"""

import sys
import importlib
import subprocess
import platform
from typing import Dict, List, Tuple, Optional

def print_header(title: str):
    """Print a formatted header."""
    print(f"\n{'='*60}")
    print(f"🔍 {title}")
    print(f"{'='*60}")

def print_section(title: str):
    """Print a formatted section."""
    print(f"\n📋 {title}")
    print(f"{'-'*40}")

def print_check(name: str, success: bool, message: str = ""):
    """Print a formatted check result."""
    status = "✅" if success else "❌"
    print(f"{status} {name}: {message}")

def get_package_version(package_name: str) -> Optional[str]:
    """Get package version if available."""
    try:
        module = importlib.import_module(package_name)
        if hasattr(module, '__version__'):
            return module.__version__
        return "unknown"
    except ImportError:
        return None

def check_core_scientific() -> Dict[str, bool]:
    """Check core scientific computing libraries."""
    print_section("Core Scientific Computing")
    
    core_deps = {
        'numpy': 'numpy',
        'scipy': 'scipy',
        'pandas': 'pandas',
        'matplotlib': 'matplotlib',
        'scikit-image': 'skimage',
        'scikit-learn': 'sklearn',
        'numba': 'numba',
        'numexpr': 'numexpr'
    }
    
    results = {}
    for package_name, import_name in core_deps.items():
        try:
            importlib.import_module(import_name)
            version = get_package_version(import_name)
            print_check(package_name, True, f"v{version}")
            results[package_name] = True
        except ImportError as e:
            print_check(package_name, False, f"Missing: {e}")
            results[package_name] = False
    
    return results

def check_geospatial() -> Dict[str, bool]:
    """Check geospatial libraries."""
    print_section("Geospatial Libraries")
    
    geo_deps = {
        'GDAL': 'osgeo.gdal',
        'rasterio': 'rasterio',
        'geopandas': 'geopandas',
        'shapely': 'shapely',
        'fiona': 'fiona',
        'pyproj': 'pyproj'
    }
    
    results = {}
    for package_name, import_name in geo_deps.items():
        try:
            importlib.import_module(import_name)
            version = get_package_version(import_name)
            print_check(package_name, True, f"v{version}")
            results[package_name] = True
        except ImportError as e:
            print_check(package_name, False, f"Missing: {e}")
            results[package_name] = False
    
    return results

def check_system_utilities() -> Dict[str, bool]:
    """Check system utility libraries."""
    print_section("System Utilities")
    
    util_deps = {
        'psutil': 'psutil',
        'tqdm': 'tqdm',
        'pathlib': 'pathlib',
        'multiprocessing': 'multiprocessing',
        'threading': 'threading',
        'concurrent.futures': 'concurrent.futures'
    }
    
    results = {}
    for package_name, import_name in util_deps.items():
        try:
            importlib.import_module(import_name)
            version = get_package_version(import_name)
            print_check(package_name, True, f"v{version}")
            results[package_name] = True
        except ImportError as e:
            print_check(package_name, False, f"Missing: {e}")
            results[package_name] = False
    
    return results

def check_optional_dependencies() -> Dict[str, bool]:
    """Check optional dependencies."""
    print_section("Optional Dependencies")
    
    optional_deps = {
        'laspy': 'laspy',
        'imageio': 'imageio',
        'imageio-ffmpeg': 'imageio_ffmpeg',
        'pytest': 'pytest',
        'black': 'black',
        'flake8': 'flake8',
        'memory-profiler': 'memory_profiler'
    }
    
    results = {}
    for package_name, import_name in optional_deps.items():
        try:
            importlib.import_module(import_name)
            version = get_package_version(import_name)
            print_check(package_name, True, f"v{version} (optional)")
            results[package_name] = True
        except ImportError:
            print_check(package_name, False, "Missing (optional)")
            results[package_name] = False
    
    return results

def check_system_info():
    """Check system information."""
    print_section("System Information")
    
    print_check("Python Version", True, f"{sys.version}")
    print_check("Platform", True, f"{platform.system()} {platform.release()}")
    print_check("Architecture", True, f"{platform.machine()}")
    
    # Check available memory
    try:
        import psutil
        memory = psutil.virtual_memory()
        print_check("System Memory", True, f"{memory.total / (1024**3):.1f}GB total, {memory.available / (1024**3):.1f}GB available")
    except ImportError:
        print_check("System Memory", False, "psutil not available")
    
    # Check CPU cores
    try:
        import multiprocessing
        cores = multiprocessing.cpu_count()
        print_check("CPU Cores", True, f"{cores} cores available")
    except ImportError:
        print_check("CPU Cores", False, "multiprocessing not available")

def check_critical_functionality():
    """Check critical functionality for calibration."""
    print_section("Critical Functionality Tests")
    
    # Test SciPy sparse matrices
    try:
        from scipy.sparse import csr_matrix, dok_matrix, lil_matrix
        test_matrix = csr_matrix((10, 10))
        print_check("SciPy Sparse Matrices", True, "CSR, DOK, LIL available")
    except ImportError as e:
        print_check("SciPy Sparse Matrices", False, f"Critical for memory optimization: {e}")
    
    # Test GDAL functionality
    try:
        from osgeo import gdal
        gdal_version = gdal.VersionInfo()
        print_check("GDAL Functionality", True, f"v{gdal_version}")
    except ImportError as e:
        print_check("GDAL Functionality", False, f"Critical for LiDAR processing: {e}")
    
    # Test multiprocessing
    try:
        import multiprocessing
        from concurrent.futures import ProcessPoolExecutor
        print_check("Multiprocessing", True, "ProcessPoolExecutor available")
    except ImportError as e:
        print_check("Multiprocessing", False, f"Critical for parallel calibration: {e}")
    
    # Test shared memory
    try:
        from multiprocessing import shared_memory
        print_check("Shared Memory", True, "Available for terrain sharing")
    except ImportError as e:
        print_check("Shared Memory", False, f"May limit terrain optimization: {e}")

def generate_requirements():
    """Generate requirements.txt content."""
    print_section("Requirements.txt Content")
    
    requirements = [
        "# Core Scientific Computing",
        "numpy>=1.21.0,<2.0.0",
        "scipy>=1.7.0,<2.0.0",
        "pandas>=1.3.0,<2.0.0",
        "matplotlib>=3.5.0,<4.0.0",
        "scikit-image>=0.18.0,<1.0.0",
        "scikit-learn>=1.0.0,<2.0.0",
        "numba>=0.56.0,<1.0.0",
        "numexpr>=2.8.0,<3.0.0",
        "",
        "# Geospatial Libraries",
        "GDAL>=3.4.0,<4.0.0",
        "rasterio>=1.3.0,<2.0.0",
        "geopandas>=0.10.0,<1.0.0",
        "shapely>=1.8.0,<2.0.0",
        "fiona>=1.8.0,<2.0.0",
        "pyproj>=3.3.0,<4.0.0",
        "",
        "# System Utilities",
        "psutil>=5.8.0,<6.0.0",
        "tqdm>=4.62.0,<5.0.0",
        "",
        "# Optional Dependencies",
        "laspy>=2.0.0,<3.0.0",
        "imageio>=2.15.0,<3.0.0",
        "imageio-ffmpeg>=0.4.0,<1.0.0",
        "pytest>=6.2.0,<7.0.0",
        "black>=22.0.0,<23.0.0",
        "flake8>=4.0.0,<5.0.0",
        "memory-profiler>=0.60.0,<1.0.0"
    ]
    
    print("Copy this to requirements.txt:")
    print("\n".join(requirements))

def main():
    """Main dependency check function."""
    print_header("FOREST FIRE CALIBRATION DEPENDENCY CHECKER")
    
    # Run all checks
    core_results = check_core_scientific()
    geo_results = check_geospatial()
    util_results = check_system_utilities()
    optional_results = check_optional_dependencies()
    
    check_system_info()
    check_critical_functionality()
    
    # Summary
    print_header("SUMMARY")
    
    all_results = {**core_results, **geo_results, **util_results}
    critical_results = {k: v for k, v in all_results.items() if k in ['numpy', 'scipy', 'GDAL', 'multiprocessing']}
    
    total_checks = len(all_results)
    passed_checks = sum(all_results.values())
    critical_passed = sum(critical_results.values())
    
    print(f"📊 Overall: {passed_checks}/{total_checks} dependencies available")
    print(f"🚨 Critical: {critical_passed}/{len(critical_results)} critical dependencies available")
    
    # Check if calibration can run
    if critical_passed == len(critical_results):
        print_check("Calibration Ready", True, "All critical dependencies available!")
    else:
        print_check("Calibration Ready", False, "Missing critical dependencies!")
        missing_critical = [k for k, v in critical_results.items() if not v]
        print(f"   Missing: {', '.join(missing_critical)}")
    
    # Installation instructions
    if critical_passed < len(critical_results):
        print_header("INSTALLATION INSTRUCTIONS")
        print("To install missing dependencies:")
        print("1. pip install -r requirements.txt")
        print("2. For GDAL issues:")
        print("   - Windows: conda install -c conda-forge gdal")
        print("   - Linux: sudo apt-get install gdal-bin libgdal-dev")
        print("   - macOS: brew install gdal")
    
    generate_requirements()

if __name__ == "__main__":
    main()
