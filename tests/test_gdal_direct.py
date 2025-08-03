#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Direct GDAL Test
"""

import sys
import os

def test_gdal_direct():
    """Test GDAL import directly."""
    print("🔍 Testing GDAL import directly...")
    
    try:
        from osgeo import gdal
        print("✅ GDAL import successful!")
        print(f"   GDAL version: {gdal.VersionInfo()}")
        
        # Test opening a file
        dtm_path = "C:/Users/user/Desktop/UvA/YEAR 2/Thesis/LiDAR/DTM data/Merged_DTM.tif"
        if os.path.exists(dtm_path):
            print(f"✅ DTM file exists: {dtm_path}")
            
            dataset = gdal.Open(dtm_path)
            if dataset is not None:
                print(f"✅ Successfully opened DTM file")
                print(f"   Dimensions: {dataset.RasterXSize} x {dataset.RasterYSize}")
                print(f"   Bands: {dataset.RasterCount}")
                dataset = None
            else:
                print("❌ Could not open DTM file with GDAL")
        else:
            print(f"❌ DTM file not found: {dtm_path}")
            
        return True
        
    except ImportError as e:
        print(f"❌ GDAL import failed: {e}")
        return False

if __name__ == "__main__":
    test_gdal_direct() 