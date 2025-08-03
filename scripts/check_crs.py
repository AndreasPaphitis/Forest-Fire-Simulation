#!/usr/bin/env python3
"""
Check CRS of DTM and LiDAR data files
"""

import sys
from pathlib import Path

try:
    import rasterio
    print("✅ rasterio available")
except ImportError:
    print("❌ rasterio not available")
    sys.exit(1)

def check_file_crs(filepath, description):
    """Check CRS of a single file"""
    try:
        if not filepath.exists():
            print(f"❌ {description}: File not found - {filepath}")
            return None
            
        with rasterio.open(filepath) as src:
            crs = src.crs
            bounds = src.bounds
            print(f"✅ {description}:")
            print(f"   File: {filepath}")
            print(f"   CRS: {crs}")
            print(f"   Bounds: {bounds}")
            return crs
    except Exception as e:
        print(f"❌ {description}: Error reading file - {e}")
        return None

def main():
    print("🔍 Checking CRS of DTM and LiDAR data")
    print("=" * 50)
    
    # Check DTM
    dtm_paths = [
        Path("/gpfs/home1/apaphitis/git/github/Forest-Fire-Simulation/Data/DTM/Merged_DTM.tif"),
        Path("Data/DTM/Merged_DTM.tif"),
        Path("../Data/DTM/Merged_DTM.tif")
    ]
    
    dtm_crs = None
    for dtm_path in dtm_paths:
        dtm_crs = check_file_crs(dtm_path, "DTM")
        if dtm_crs:
            break
    
    print()
    
    # Check LiDAR files
    lidar_dirs = [
        Path("/gpfs/home1/apaphitis/git/github/Forest-Fire-Simulation/Data/LiDAR"),
        Path("/gpfs/home1/apaphitis/git/github/Forest-Fire-Simulation/Data/LIDAR"),
        Path("Data/LiDAR"),
        Path("Data/LIDAR"),
        Path("../Data/LiDAR"),
        Path("../Data/LIDAR")
    ]
    
    lidar_crs = None
    for lidar_dir in lidar_dirs:
        if lidar_dir.exists():
            print(f"📁 Found LiDAR directory: {lidar_dir}")
            # Look for .tif files
            tif_files = list(lidar_dir.glob("**/*.tif"))
            if tif_files:
                print(f"   Found {len(tif_files)} .tif files")
                # Check first few files
                for i, tif_file in enumerate(tif_files[:3]):
                    lidar_crs = check_file_crs(tif_file, f"LiDAR file {i+1}")
                    if lidar_crs:
                        break
                if lidar_crs:
                    break
            else:
                print(f"   No .tif files found in {lidar_dir}")
        else:
            print(f"❌ LiDAR directory not found: {lidar_dir}")
    
    print()
    print("=" * 50)
    print("🎯 SUMMARY:")
    
    if dtm_crs and lidar_crs:
        print(f"DTM CRS:   {dtm_crs}")
        print(f"LiDAR CRS: {lidar_crs}")
        
        if dtm_crs == lidar_crs:
            print("✅ CRS MATCH - No conversion needed")
        else:
            print("⚠️  CRS MISMATCH - Conversion required!")
            print(f"   Need to convert from {lidar_crs} to {dtm_crs}")
    else:
        if not dtm_crs:
            print("❌ Could not determine DTM CRS")
        if not lidar_crs:
            print("❌ Could not determine LiDAR CRS")

if __name__ == "__main__":
    main() 