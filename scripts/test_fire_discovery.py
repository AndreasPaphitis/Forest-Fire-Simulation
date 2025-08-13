#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Simple test script for fire perimeter discovery without spatial dependencies.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

def test_emsr_directory_structure():
    """Test basic EMSR directory structure without spatial libraries."""
    emsr_dir = Path("EMSR Delineations")
    
    if not emsr_dir.exists():
        print(f"❌ EMSR directory not found: {emsr_dir}")
        return False
    
    print(f"🔍 TESTING EMSR DIRECTORY STRUCTURE")
    print(f"=" * 50)
    print(f"Base directory: {emsr_dir}")
    
    day_dirs = []
    for item in emsr_dir.iterdir():
        if item.is_dir() and "Day" in item.name:
            day_dirs.append(item)
    
    print(f"Found {len(day_dirs)} day directories:")
    
    total_shapefiles = 0
    for day_dir in sorted(day_dirs):
        print(f"\n📁 {day_dir.name}:")
        
        # Count files
        shapefiles = list(day_dir.glob("*.shp"))
        other_files = [f for f in day_dir.iterdir() if f.is_file() and f.suffix != '.shp']
        
        print(f"   Shapefiles: {len(shapefiles)}")
        for shp in shapefiles:
            print(f"     - {shp.name}")
            
            # Check for required shapefile components
            base_name = shp.stem
            required_exts = ['.shx', '.dbf', '.prj']
            missing = []
            for ext in required_exts:
                if not (day_dir / f"{base_name}{ext}").exists():
                    missing.append(ext)
            
            if missing:
                print(f"       ⚠️  Missing: {missing}")
            else:
                print(f"       ✅ Complete shapefile")
                total_shapefiles += 1
        
        print(f"   Other files: {len(other_files)}")
        for ext in {f.suffix for f in other_files}:
            count = len([f for f in other_files if f.suffix == ext])
            print(f"     {ext}: {count}")
    
    print(f"\n📊 SUMMARY:")
    print(f"   Total day directories: {len(day_dirs)}")
    print(f"   Complete shapefiles: {total_shapefiles}")
    
    if total_shapefiles >= 2:
        print(f"✅ Sufficient data for training/test split")
        return True
    else:
        print(f"❌ Insufficient complete shapefiles for calibration")
        return False

def test_parse_day_directory():
    """Test day directory name parsing."""
    print(f"\n🔧 TESTING DAY DIRECTORY PARSING")
    print(f"=" * 40)
    
    test_names = [
        "Day 1 (18_08_23)",
        "Day 2 (21_08_23)", 
        "Day 3 (24_08_23)",
        "Day 4 (26_08_23)"
    ]
    
    for name in test_names:
        try:
            # Extract day number
            if "Day" in name:
                day_part = name.split("Day")[1].strip()
                day_number = int(day_part.split()[0])
            else:
                day_number = None
            
            # Extract date
            if "(" in name and ")" in name:
                date_part = name.split("(")[1].split(")")[0]
                date_components = date_part.split("_")
                if len(date_components) == 3:
                    day, month, year = date_components
                    full_year = f"20{year}" if len(year) == 2 else year
                    date_str = f"{full_year}-{month.zfill(2)}-{day.zfill(2)}"
                else:
                    date_str = None
            else:
                date_str = None
            
            print(f"   '{name}' → Day {day_number}, Date: {date_str}")
            
        except Exception as e:
            print(f"   '{name}' → ERROR: {e}")

def estimate_calibration_requirements():
    """Estimate calibration requirements."""
    print(f"\n📊 CALIBRATION REQUIREMENTS ESTIMATION")
    print(f"=" * 50)
    
    # Configuration options
    configs = [
        {"memory_gb": 64, "workers": 60, "grid_points": 3},
        {"memory_gb": 64, "workers": 60, "grid_points": 4},
        {"memory_gb": 128, "workers": 120, "grid_points": 3},
        {"memory_gb": 128, "workers": 120, "grid_points": 4}
    ]
    
    parameters = 5  # Top 5 from sensitivity analysis
    
    for config in configs:
        total_combinations = config["grid_points"] ** parameters
        time_per_sim_minutes = 20.0  # Conservative estimate
        
        # CORRECTED MEMORY CALCULATION:
        # With maximum optimization, memory per simulation is much lower
        memory_per_sim_gb = 0.8      # ~0.8GB per simulation with sparse storage
        shared_terrain_gb = 50.0     # 50GB shared across ALL workers
        
        sequential_hours = (total_combinations * time_per_sim_minutes) / 60
        parallel_hours = sequential_hours / config["workers"]
        
        # Peak memory = shared terrain + (memory per sim × concurrent simulations)
        concurrent_sims = min(config["workers"], total_combinations)
        peak_memory_gb = shared_terrain_gb + (memory_per_sim_gb * concurrent_sims)
        
        print(f"\n🔧 Configuration: {config['memory_gb']}GB / {config['workers']} workers / {config['grid_points']}-point")
        print(f"   Total combinations: {total_combinations:,}")
        print(f"   Sequential time: {sequential_hours:.1f} hours")
        print(f"   Parallel time: {parallel_hours:.1f} hours") 
        print(f"   Peak memory: {peak_memory_gb:.1f} GB")
        
        if peak_memory_gb > config["memory_gb"] * 0.9:
            print(f"   ⚠️  Memory risk: HIGH")
        elif peak_memory_gb > config["memory_gb"] * 0.7:
            print(f"   ⚠️  Memory risk: Moderate")
        else:
            print(f"   ✅ Memory risk: Low")

def main():
    print(f"🔥 TENERIFE FIRE PERIMETER CALIBRATION - BASIC TESTS")
    print(f"=" * 70)
    
    # Test 1: Directory structure
    structure_ok = test_emsr_directory_structure()
    
    # Test 2: Directory name parsing
    test_parse_day_directory()
    
    # Test 3: Calibration requirements
    estimate_calibration_requirements()
    
    print(f"\n🎯 READINESS ASSESSMENT:")
    if structure_ok:
        print(f"✅ EMSR data structure: Valid")
        print(f"✅ Fire perimeter data: Available")
        print(f"📋 Next steps:")
        print(f"   1. Install spatial libraries: geopandas, rasterio, shapely")
        print(f"   2. Run full discovery with: python scripts/run_tenerife_calibration.py --dry-run")
        print(f"   3. Validate CRS consistency (should be EPSG:25828)")
        print(f"   4. Configure memory framework (64GB/60 workers or 128GB/120 workers)")
    else:
        print(f"❌ EMSR data structure: Issues detected")
        print(f"   Check shapefile completeness and directory structure")

if __name__ == "__main__":
    main()
