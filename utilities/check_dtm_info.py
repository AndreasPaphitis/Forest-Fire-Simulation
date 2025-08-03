#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
DTM File Information Checker

This script provides detailed information about the DTM file to estimate preprocessing time.
"""

import os
from osgeo import gdal
import numpy as np

def get_dtm_info(dtm_path):
    """Get detailed information about the DTM file."""
    print("🔍 DTM File Analysis")
    print("=" * 50)
    
    # File size
    file_size_mb = os.path.getsize(dtm_path) / (1024 * 1024)
    print(f"📁 File size: {file_size_mb:.1f} MB")
    
    # Open DTM
    ds = gdal.Open(dtm_path)
    if ds is None:
        print("❌ Could not open DTM file")
        return
    
    # Get dimensions
    width = ds.RasterXSize
    height = ds.RasterYSize
    bands = ds.RasterCount
    
    print(f"📐 Dimensions: {width} x {height} pixels")
    print(f"🎯 Number of bands: {bands}")
    
    # Get geotransform (resolution)
    geotransform = ds.GetGeoTransform()
    pixel_width = geotransform[1]
    pixel_height = abs(geotransform[5])
    
    print(f"📏 Pixel resolution: {pixel_width:.2f} x {pixel_height:.2f} meters")
    
    # Calculate area
    area_km2 = (width * height * pixel_width * pixel_height) / 1_000_000
    print(f"🗺️  Area: {area_km2:.2f} km²")
    
    # Get data type
    band = ds.GetRasterBand(1)
    data_type = gdal.GetDataTypeName(band.DataType)
    print(f"💾 Data type: {data_type}")
    
    # Estimate preprocessing time
    total_pixels = width * height
    print(f"\n⏱️  Preprocessing Time Estimates:")
    print(f"   Total pixels to process: {total_pixels:,}")
    
    # Time estimates based on pixel count
    if total_pixels < 1_000_000:  # < 1M pixels
        estimated_time = "30-60 seconds"
    elif total_pixels < 10_000_000:  # < 10M pixels
        estimated_time = "2-5 minutes"
    elif total_pixels < 50_000_000:  # < 50M pixels
        estimated_time = "5-15 minutes"
    elif total_pixels < 100_000_000:  # < 100M pixels
        estimated_time = "15-30 minutes"
    else:  # > 100M pixels
        estimated_time = "30+ minutes"
    
    print(f"   Estimated preprocessing time: {estimated_time}")
    
    # Memory usage estimate
    memory_mb = (total_pixels * 8) / (1024 * 1024)  # Assuming float64
    print(f"   Estimated memory usage: {memory_mb:.1f} MB")
    
    ds = None

if __name__ == "__main__":
    dtm_path = r"C:\Users\user\Desktop\UvA\YEAR 2\Thesis\LiDAR\DTM data\Merged_DTM.tif"
    get_dtm_info(dtm_path) 