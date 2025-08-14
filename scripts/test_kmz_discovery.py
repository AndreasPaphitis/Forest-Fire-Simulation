#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test KMZ Fire Perimeter Discovery

Test the updated discovery logic that handles KMZ files instead of shapefiles.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_kmz_discovery():
    hpc_path = "/gpfs/home1/apaphitis/git/github/Forest-Fire-Simulation/EMSR Delineations"
    
    print(f"🧪 TESTING KMZ FIRE PERIMETER DISCOVERY")
    print(f"=" * 60)
    print(f"📁 Path: {hpc_path}")
    print()
    
    try:
        from src.core.calibration.fire_perimeter_calibration import FirePerimeterDiscovery
        
        print(f"🔍 Running discovery with multi-format support (KMZ, KML, JSON)...")
        discovery = FirePerimeterDiscovery(hpc_path)
        fire_dataset = discovery.discover_fire_perimeters()
        
        print(f"\n🎯 RESULTS:")
        print(f"   Fire perimeters found: {len(fire_dataset.fire_perimeters)}")
        
        if fire_dataset.fire_perimeters:
            print(f"   ✅ SUCCESS! KMZ discovery working!")
            print(f"\n📋 DISCOVERED PERIMETERS:")
            for fp in sorted(fire_dataset.fire_perimeters, key=lambda x: x.day_number):
                file_path = Path(fp.shapefile_path)
                file_format = file_path.suffix.upper()
                print(f"   📅 Day {fp.day_number}: {fp.fire_id}")
                print(f"      📄 File: {file_path.name}")
                print(f"      🗂️  Format: {file_format}")
                print(f"      📐 Valid: {fp.is_valid}")
                if not fp.is_valid:
                    print(f"      ❌ Error: {fp.error_message}")
                print()
        else:
            print(f"   ❌ Still no fire perimeters found")
            print(f"   This suggests a deeper issue with the directory structure")
        
        return len(fire_dataset.fire_perimeters) > 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def analyze_available_formats():
    """Analyze what file formats are available in the EMSR directories."""
    hpc_path = "/gpfs/home1/apaphitis/git/github/Forest-Fire-Simulation/EMSR Delineations"
    
    print(f"\n📊 ANALYZING AVAILABLE FILE FORMATS")
    print(f"=" * 50)
    
    emsr_dir = Path(hpc_path)
    if not emsr_dir.exists():
        print(f"❌ Directory does not exist: {hpc_path}")
        return
    
    day_dirs = [d for d in emsr_dir.iterdir() if d.is_dir() and "Day" in d.name]
    
    format_summary = {}
    
    for day_dir in sorted(day_dirs):
        print(f"\n📂 {day_dir.name}:")
        
        formats_in_day = {}
        for file in day_dir.iterdir():
            if file.is_file():
                ext = file.suffix.lower()
                if ext not in formats_in_day:
                    formats_in_day[ext] = []
                formats_in_day[ext].append(file.name)
        
        for ext, files in formats_in_day.items():
            print(f"   {ext}: {len(files)} files")
            # Show first file as example
            if files:
                print(f"      Example: {files[0]}")
            
            # Track global summary
            if ext not in format_summary:
                format_summary[ext] = 0
            format_summary[ext] += len(files)
    
    print(f"\n📈 OVERALL FORMAT SUMMARY:")
    for ext, count in sorted(format_summary.items()):
        print(f"   {ext}: {count} files total")
    
    print(f"\n💡 RECOMMENDATIONS:")
    if '.kmz' in format_summary:
        print(f"   ✅ KMZ files available - good for fire perimeter data")
    if '.json' in format_summary:
        print(f"   ✅ JSON files available - may contain GeoJSON data")
    if '.shp' not in format_summary:
        print(f"   ⚠️  No shapefile (.shp) format detected")
        print(f"      The discovery system should now handle KMZ/JSON formats")

if __name__ == "__main__":
    analyze_available_formats()
    success = test_kmz_discovery()
    
    if success:
        print(f"\n🎉 KMZ DISCOVERY: WORKING!")
        print(f"   Your EMSR data is now properly discovered")
        print(f"   Ready to run full calibration")
    else:
        print(f"\n❌ KMZ DISCOVERY: ISSUES REMAIN")
        print(f"   Review the error messages above")
        print(f"   May need additional format support or metadata handling")
