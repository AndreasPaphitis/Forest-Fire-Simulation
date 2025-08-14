#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test Enhanced EMSR Discovery

Test the updated shapefile discovery logic that searches recursively.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_enhanced_discovery():
    hpc_path = "/gpfs/home1/apaphitis/git/github/Forest-Fire-Simulation/EMSR Delineations"
    
    print(f"🧪 TESTING ENHANCED EMSR DISCOVERY")
    print(f"=" * 60)
    print(f"📁 Path: {hpc_path}")
    print()
    
    try:
        from src.core.calibration.fire_perimeter_calibration import FirePerimeterDiscovery
        
        print(f"🔍 Running discovery with enhanced recursive search...")
        discovery = FirePerimeterDiscovery(hpc_path)
        fire_dataset = discovery.discover_fire_perimeters()
        
        print(f"\n🎯 RESULTS:")
        print(f"   Fire perimeters found: {len(fire_dataset.fire_perimeters)}")
        
        if fire_dataset.fire_perimeters:
            print(f"   ✅ SUCCESS! Enhanced discovery working!")
            print(f"\n📋 DISCOVERED PERIMETERS:")
            for fp in sorted(fire_dataset.fire_perimeters, key=lambda x: x.day_number):
                print(f"   📅 Day {fp.day_number}: {fp.fire_id}")
                print(f"      📄 File: {fp.shapefile_path}")
        else:
            print(f"   ❌ Still no fire perimeters found")
            print(f"   Run the debug script for detailed analysis:")
            print(f"   python scripts/debug_emsr_structure.py")
        
        return len(fire_dataset.fire_perimeters) > 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_enhanced_discovery()
    if success:
        print(f"\n🎉 ENHANCED DISCOVERY: WORKING!")
    else:
        print(f"\n❌ ENHANCED DISCOVERY: STILL FAILED")
        print(f"   Next step: Run debug script to understand directory structure")
