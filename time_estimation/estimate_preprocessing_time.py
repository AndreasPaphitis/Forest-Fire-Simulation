#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Preprocessing Time Estimator

This script estimates preprocessing time based on DTM file size.
"""

import os

def estimate_preprocessing_time(dtm_path):
    """Estimate preprocessing time based on file size."""
    print("🔍 DTM Preprocessing Time Estimation")
    print("=" * 50)
    
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
    
    # Time estimates based on file size and pixel count
    print(f"\n⏱️  Preprocessing Time Estimates:")
    
    if file_size_mb < 100:  # < 100 MB
        estimated_time = "30-60 seconds"
        complexity = "Low"
    elif file_size_mb < 500:  # < 500 MB
        estimated_time = "2-5 minutes"
        complexity = "Medium"
    elif file_size_mb < 1000:  # < 1 GB
        estimated_time = "5-15 minutes"
        complexity = "High"
    elif file_size_mb < 2000:  # < 2 GB
        estimated_time = "15-30 minutes"
        complexity = "Very High"
    else:  # > 2 GB
        estimated_time = "30+ minutes"
        complexity = "Extreme"
    
    print(f"   Estimated time: {estimated_time}")
    print(f"   Complexity: {complexity}")
    
    # Memory usage estimate
    memory_mb = file_size_mb * 3  # Rough estimate for processing overhead
    print(f"   Estimated memory usage: {memory_mb:.1f} MB")
    
    # Recommendations
    print(f"\n💡 Recommendations:")
    if file_size_mb > 1000:
        print("   - Consider running during off-peak hours")
        print("   - Ensure sufficient RAM available")
        print("   - Monitor system resources during processing")
    else:
        print("   - Should complete quickly")
        print("   - No special considerations needed")
    
    return estimated_time

if __name__ == "__main__":
    dtm_path = r"C:\Users\user\Desktop\UvA\YEAR 2\Thesis\LiDAR\DTM data\Merged_DTM.tif"
    estimate_preprocessing_time(dtm_path) 