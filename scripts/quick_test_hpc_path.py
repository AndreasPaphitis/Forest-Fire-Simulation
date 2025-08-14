#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Quick HPC Path Test

Ultra-simple script to test the exact HPC path you provided.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_hpc_path():
    hpc_path = "/gpfs/home1/apaphitis/git/github/Forest-Fire-Simulation/EMSR Delineations/"
    
    print(f"🧪 TESTING HPC PATH:")
    print(f"📁 Path: {hpc_path}")
    
    path_obj = Path(hpc_path)
    print(f"✅ Exists: {path_obj.exists()}")
    print(f"📂 Is directory: {path_obj.is_dir()}")
    
    if path_obj.exists():
        contents = list(path_obj.iterdir())
        print(f"📋 Contents: {len(contents)} items")
        
        day_dirs = [d for d in contents if d.is_dir() and "Day" in d.name]
        print(f"📅 Day directories: {len(day_dirs)}")
        
        for day_dir in sorted(day_dirs):
            shapefiles = list(day_dir.glob("*.shp"))
            print(f"   {day_dir.name}: {len(shapefiles)} shapefiles")
    
    # Test with FirePerimeterDiscovery
    try:
        from src.core.calibration.fire_perimeter_calibration import FirePerimeterDiscovery
        
        print(f"\n🔍 TESTING DISCOVERY:")
        discovery = FirePerimeterDiscovery(hpc_path)
        fire_dataset = discovery.discover_fire_perimeters()
        print(f"🎯 Found: {len(fire_dataset.fire_perimeters)} fire perimeters")
        
        if fire_dataset.fire_perimeters:
            print(f"✅ SUCCESS! Discovery working correctly")
            return True
        else:
            print(f"❌ No fire perimeters found")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_hpc_path()
    if success:
        print(f"\n🎉 HPC PATH TEST: PASSED")
        print(f"You can now run: python scripts/run_tenerife_calibration.py")
    else:
        print(f"\n❌ HPC PATH TEST: FAILED")
