#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Debug EMSR Directory Structure

Deep exploration script to understand the actual structure of EMSR directories on HPC.
This will help us fix the shapefile discovery logic.

Usage:
    python scripts/debug_emsr_structure.py
    python scripts/debug_emsr_structure.py --emsr-dir "/path/to/EMSR Delineations"
"""

import os
import sys
import argparse
from pathlib import Path

def explore_directory_structure(emsr_path: str):
    """Deep exploration of EMSR directory structure."""
    print(f"🔍 DEEP EMSR DIRECTORY EXPLORATION")
    print(f"=" * 70)
    
    emsr_dir = Path(emsr_path)
    print(f"📂 Base directory: {emsr_dir}")
    print(f"✅ Exists: {emsr_dir.exists()}")
    print(f"📁 Is directory: {emsr_dir.is_dir()}")
    print()
    
    if not emsr_dir.exists():
        print(f"❌ Directory does not exist!")
        return
    
    # List all Day directories
    day_dirs = [d for d in emsr_dir.iterdir() if d.is_dir() and "Day" in d.name]
    print(f"📅 Found {len(day_dirs)} Day directories:")
    
    for day_dir in sorted(day_dirs):
        print(f"\n📂 {day_dir.name}")
        print(f"   📁 Path: {day_dir}")
        
        # Explore contents recursively
        explore_day_directory(day_dir, level=1)

def explore_day_directory(day_dir: Path, level: int = 1, max_level: int = 3):
    """Recursively explore a Day directory."""
    indent = "   " * level
    
    try:
        contents = list(day_dir.iterdir())
        print(f"{indent}📋 Contents: {len(contents)} items")
        
        # Categorize contents
        subdirs = [item for item in contents if item.is_dir()]
        files = [item for item in contents if item.is_file()]
        
        # Show files directly in Day directory
        shapefiles = [f for f in files if f.suffix.lower() == '.shp']
        other_files = [f for f in files if f.suffix.lower() != '.shp']
        
        if shapefiles:
            print(f"{indent}🗺️  Shapefiles (DIRECT): {len(shapefiles)}")
            for shp in shapefiles:
                print(f"{indent}   • {shp.name}")
        
        if other_files:
            print(f"{indent}📄 Other files: {len(other_files)}")
            for f in other_files[:5]:  # Show first 5
                print(f"{indent}   • {f.name}")
            if len(other_files) > 5:
                print(f"{indent}   ... and {len(other_files) - 5} more")
        
        # Explore subdirectories
        if subdirs and level < max_level:
            print(f"{indent}📂 Subdirectories: {len(subdirs)}")
            for subdir in subdirs:
                print(f"{indent}   📁 {subdir.name}/")
                
                # Look for shapefiles in subdirectory
                try:
                    sub_contents = list(subdir.iterdir())
                    sub_shapefiles = [f for f in sub_contents if f.is_file() and f.suffix.lower() == '.shp']
                    sub_files = [f for f in sub_contents if f.is_file()]
                    sub_dirs = [d for d in sub_contents if d.is_dir()]
                    
                    if sub_shapefiles:
                        print(f"{indent}      🗺️  Shapefiles: {len(sub_shapefiles)}")
                        for shp in sub_shapefiles:
                            print(f"{indent}         • {shp.name}")
                    
                    if sub_files and not sub_shapefiles:
                        print(f"{indent}      📄 Files: {len(sub_files)}")
                        for f in sub_files[:3]:
                            print(f"{indent}         • {f.name}")
                    
                    if sub_dirs:
                        print(f"{indent}      📂 More subdirs: {len(sub_dirs)}")
                        # Recursively explore one more level
                        if level + 1 < max_level:
                            for sub_subdir in sub_dirs[:2]:  # Explore first 2
                                print(f"{indent}         📁 {sub_subdir.name}/")
                                explore_day_directory(sub_subdir, level + 2, max_level)
                
                except PermissionError:
                    print(f"{indent}      ❌ Permission denied")
                except Exception as e:
                    print(f"{indent}      ❌ Error: {e}")
        
        elif subdirs:
            print(f"{indent}📂 Subdirectories: {len(subdirs)} (not explored - max level reached)")
            for subdir in subdirs:
                print(f"{indent}   📁 {subdir.name}/")
    
    except PermissionError:
        print(f"{indent}❌ Permission denied accessing {day_dir}")
    except Exception as e:
        print(f"{indent}❌ Error exploring {day_dir}: {e}")

def find_all_shapefiles(emsr_path: str):
    """Find ALL shapefiles in EMSR directory structure."""
    print(f"\n🔍 COMPREHENSIVE SHAPEFILE SEARCH")
    print(f"=" * 50)
    
    emsr_dir = Path(emsr_path)
    
    # Use recursive glob to find ALL .shp files
    all_shapefiles = list(emsr_dir.rglob("*.shp"))
    
    print(f"🗺️  Total shapefiles found: {len(all_shapefiles)}")
    
    if all_shapefiles:
        print(f"\n📋 SHAPEFILE INVENTORY:")
        
        # Group by Day directory
        day_groups = {}
        for shp in all_shapefiles:
            # Find the Day directory this shapefile belongs to
            day_dir = None
            for parent in shp.parents:
                if "Day" in parent.name and parent.parent == emsr_dir:
                    day_dir = parent.name
                    break
            
            if day_dir:
                if day_dir not in day_groups:
                    day_groups[day_dir] = []
                day_groups[day_dir].append(shp)
            else:
                if "Other" not in day_groups:
                    day_groups["Other"] = []
                day_groups["Other"].append(shp)
        
        for day, shapefiles in sorted(day_groups.items()):
            print(f"\n📅 {day}: {len(shapefiles)} shapefiles")
            for shp in shapefiles:
                # Show relative path from Day directory if possible
                try:
                    if day != "Other":
                        day_path = emsr_dir / day
                        rel_path = shp.relative_to(day_path)
                        print(f"   🗺️  {rel_path}")
                    else:
                        print(f"   🗺️  {shp.name} (in {shp.parent.name})")
                except:
                    print(f"   🗺️  {shp.name}")
        
        # Suggest pattern for discovery
        print(f"\n💡 SUGGESTED DISCOVERY PATTERN:")
        if any('/' in str(shp.relative_to(emsr_dir)) for shp in all_shapefiles):
            print("   Shapefiles are in SUBDIRECTORIES - use recursive search!")
            print("   Change from: directory.glob('*.shp')")
            print("   To: directory.rglob('*.shp')")
        else:
            print("   Shapefiles are directly in Day directories - current search should work")

def main():
    parser = argparse.ArgumentParser(
        description="Debug EMSR directory structure to fix shapefile discovery"
    )
    
    parser.add_argument(
        '--emsr-dir',
        type=str,
        default="/gpfs/home1/apaphitis/git/github/Forest-Fire-Simulation/EMSR Delineations",
        help='Path to EMSR delineations directory'
    )
    
    args = parser.parse_args()
    
    print(f"🐛 EMSR STRUCTURE DEBUG TOOL")
    print(f"=" * 70)
    
    # Explore directory structure
    explore_directory_structure(args.emsr_dir)
    
    # Find all shapefiles
    find_all_shapefiles(args.emsr_dir)
    
    print(f"\n🎯 NEXT STEPS:")
    print(f"1. Review the shapefile locations above")
    print(f"2. Update _find_shapefile() method accordingly")
    print(f"3. Test with updated discovery logic")

if __name__ == "__main__":
    main()
