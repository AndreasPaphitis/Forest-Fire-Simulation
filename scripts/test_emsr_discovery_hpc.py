#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test EMSR Directory Discovery on HPC

Quick test script to validate EMSR directory discovery logic on Snellius HPC.
This helps debug path issues and verify that fire perimeter shapefiles are found.

Usage:
    python scripts/test_emsr_discovery_hpc.py
    python scripts/test_emsr_discovery_hpc.py --emsr-dir "/gpfs/home1/apaphitis/git/github/Forest-Fire-Simulation/EMSR Delineations"
"""

import os
import sys
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from src.core.calibration.fire_perimeter_calibration import FirePerimeterDiscovery
except ImportError as e:
    print(f"❌ Error importing modules: {e}")
    print("Make sure you're running this from the project root directory")
    sys.exit(1)


def test_emsr_discovery(emsr_dir: str = "EMSR Delineations"):
    """Test EMSR directory discovery with detailed output."""
    print(f"🔍 TESTING EMSR DIRECTORY DISCOVERY")
    print(f"=" * 60)
    
    print(f"📂 Current working directory: {os.getcwd()}")
    print(f"🎯 Looking for EMSR directory: {emsr_dir}")
    print()
    
    try:
        # Test discovery initialization
        print(f"🔧 Initializing FirePerimeterDiscovery...")
        discovery = FirePerimeterDiscovery(emsr_dir)
        
        print(f"✅ Discovery initialized successfully!")
        print(f"📁 Found EMSR directory: {discovery.base_directory}")
        print(f"📏 Directory type: {type(discovery.base_directory)}")
        print(f"🔍 Directory exists: {discovery.base_directory.exists()}")
        print()
        
        # List contents of the directory
        print(f"📋 DIRECTORY CONTENTS:")
        print(f"-" * 30)
        
        if discovery.base_directory.exists():
            contents = list(discovery.base_directory.iterdir())
            print(f"Total items: {len(contents)}")
            print()
            
            # List Day directories
            day_dirs = [d for d in contents if d.is_dir() and d.name.startswith("Day")]
            print(f"📅 Day directories found: {len(day_dirs)}")
            for day_dir in sorted(day_dirs):
                print(f"   📂 {day_dir.name}")
                
                # Check for shapefiles in each day
                shapefiles = list(day_dir.glob("*.shp"))
                print(f"      🗺️  Shapefiles: {len(shapefiles)}")
                for shp in shapefiles:
                    print(f"         • {shp.name}")
            print()
            
            # List other files/directories
            other_items = [d for d in contents if not (d.is_dir() and d.name.startswith("Day"))]
            if other_items:
                print(f"📄 Other items: {len(other_items)}")
                for item in sorted(other_items):
                    item_type = "📂" if item.is_dir() else "📄"
                    print(f"   {item_type} {item.name}")
                print()
        
        # Test actual fire perimeter discovery
        print(f"🔍 TESTING FIRE PERIMETER DISCOVERY:")
        print(f"-" * 40)
        
        fire_dataset = discovery.discover_fire_perimeters()
        
        print(f"🎯 Discovery Results:")
        print(f"   Total fire perimeters found: {len(fire_dataset.fire_perimeters)}")
        
        if fire_dataset.fire_perimeters:
            print(f"   ✅ SUCCESS: Fire perimeters discovered!")
            print()
            
            print(f"📊 PERIMETER DETAILS:")
            for fp in sorted(fire_dataset.fire_perimeters, key=lambda x: x.day_number):
                print(f"   Day {fp.day_number}: {fp.fire_id}")
                print(f"      📁 File: {fp.shapefile_path.name}")
                print(f"      📐 Area: {fp.area_hectares:.1f} ha" if fp.area_hectares else "      📐 Area: Unknown")
                print(f"      🗓️  Date: {fp.date}" if fp.date else "      🗓️  Date: Unknown")
                print(f"      🌍 CRS: {fp.crs}" if fp.crs else "      🌍 CRS: Unknown")
                print()
        else:
            print(f"   ❌ FAILED: No fire perimeters found")
            print(f"   Check that Day directories contain valid .shp files")
        
        return True
        
    except FileNotFoundError as e:
        print(f"❌ EMSR directory not found: {e}")
        print()
        print(f"🔧 TROUBLESHOOTING:")
        print(f"1. Verify the EMSR directory path is correct")
        print(f"2. Check if you're on HPC - use absolute path like:")
        print(f"   /gpfs/home1/apaphitis/git/github/Forest-Fire-Simulation/EMSR Delineations")
        print(f"3. Ensure the directory contains Day subdirectories")
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        print(f"   Type: {type(e).__name__}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Test EMSR directory discovery on HPC",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--emsr-dir',
        type=str,
        default="EMSR Delineations",
        help='Path to EMSR delineations directory'
    )
    
    args = parser.parse_args()
    
    print(f"🧪 EMSR DISCOVERY TEST - HPC VERSION")
    print(f"=" * 70)
    
    # Test with provided directory
    success = test_emsr_discovery(args.emsr_dir)
    
    if success:
        print(f"🎉 TEST COMPLETED SUCCESSFULLY!")
        print(f"   The EMSR directory discovery is working correctly")
        print(f"   You can now run the full calibration")
    else:
        print(f"❌ TEST FAILED")
        print(f"   Fix the EMSR directory path and try again")
        
        # Suggest some HPC paths to try
        print(f"\n💡 TRY THESE HPC PATHS:")
        suggested_paths = [
            "/gpfs/home1/apaphitis/git/github/Forest-Fire-Simulation/EMSR Delineations",
            "/gpfs/home1/apaphitis/git/github/Forest-Fire-Simulation/EMSR Delineations/",
            "/gpfs/home1/apaphitis/Forest-Fire-Simulation/EMSR Delineations",
            "/project/EMSR Delineations",
            "/scratch-shared/apaphitis/EMSR Delineations"
        ]
        
        for path in suggested_paths:
            print(f"   python scripts/test_emsr_discovery_hpc.py --emsr-dir \"{path}\"")


if __name__ == "__main__":
    main()
