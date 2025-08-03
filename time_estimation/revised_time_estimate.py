#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revised Preprocessing Time Estimator

Based on actual user experience: way longer than 30 minutes, 2GB RAM peak.
"""

import os

def revised_time_estimate(dtm_path):
    """Revised time estimate based on actual user experience."""
    print("🔍 REVISED DTM Preprocessing Time Estimation")
    print("=" * 60)
    
    # File size
    file_size_bytes = os.path.getsize(dtm_path)
    file_size_mb = file_size_bytes / (1024 * 1024)
    file_size_gb = file_size_mb / 1024
    
    print(f"📁 File size: {file_size_mb:.1f} MB ({file_size_gb:.2f} GB)")
    
    # Estimate dimensions based on file size
    # Assuming 32-bit float data (4 bytes per pixel)
    estimated_pixels = file_size_bytes / 4
    estimated_dimension = int(estimated_pixels ** 0.5)
    
    print(f"📐 Estimated dimensions: ~{estimated_dimension:,} x {estimated_dimension:,} pixels")
    print(f"🎯 Estimated total pixels: {estimated_pixels:,.0f}")
    
    # REVISED Time estimates based on actual experience
    print(f"\n⏱️  REVISED Preprocessing Time Estimates:")
    print(f"   Based on actual user experience:")
    print(f"   - Took 'way longer than 30 minutes'")
    print(f"   - RAM peaked at ~2GB")
    print(f"   - File size: 1.39 GB")
    
    # Calculate time per GB based on user experience
    # If 1.39 GB took "way longer than 30 minutes", let's estimate conservatively:
    time_per_gb = 90  # minutes per GB (conservative estimate)
    
    estimated_minutes = file_size_gb * time_per_gb
    estimated_hours = estimated_minutes / 60
    
    print(f"\n📊 REVISED Estimates:")
    print(f"   Conservative estimate: {estimated_minutes:.0f} minutes ({estimated_hours:.1f} hours)")
    
    # Memory estimate based on actual peak
    print(f"   Actual RAM usage: ~2GB peak (much lower than theoretical)")
    
    # Recommendations based on actual experience
    print(f"\n💡 REVISED Recommendations:")
    print(f"   - Plan for 1-2 hours of processing time")
    print(f"   - Ensure stable power supply")
    print(f"   - Don't interrupt the process once started")
    print(f"   - Consider running overnight")
    print(f"   - Monitor disk space (will create ~1-2GB of output files)")
    
    # Why it's slower than expected
    print(f"\n🔍 Why Slower Than Theoretical:")
    print(f"   - Complex morphological operations (barranco detection)")
    print(f"   - Flow accumulation algorithms (wind channeling)")
    print(f"   - Multiple output file generation")
    print(f"   - GDAL I/O operations on large datasets")
    print(f"   - Memory management overhead")
    
    return estimated_minutes

if __name__ == "__main__":
    dtm_path = r"C:\Users\user\Desktop\UvA\YEAR 2\Thesis\LiDAR\DTM data\Merged_DTM.tif"
    revised_time_estimate(dtm_path) 