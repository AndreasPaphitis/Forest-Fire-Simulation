#!/usr/bin/env python3
"""
Run Terrain Preprocessor with Rasterio

This script runs the terrain preprocessor using the rasterio version
to create preprocessed terrain data for the local calibration test.
"""

import sys
import os
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.utils.terrain_preprocessor_rasterio import create_terrain_preprocessor_rasterio_fixed

def main():
    """Run the terrain preprocessor."""
    print("🚀 RUNNING TERRAIN PREPROCESSOR")
    print("=" * 50)
    
    # Configuration
    dem_file = "C:/Users/user/Desktop/UvA/YEAR 2/Thesis/LiDAR/DTM data/Merged_DTM.tif"
    output_dir = "preprocessed_terrain"
    
    print(f"DEM file: {dem_file}")
    print(f"Output directory: {output_dir}")
    
    # Check if DEM file exists
    if not os.path.exists(dem_file):
        print(f"❌ DEM file not found: {dem_file}")
        return False
    
    # Create preprocessor
    print("🔧 Creating terrain preprocessor...")
    preprocessor = create_terrain_preprocessor_rasterio_fixed(
        dem_file=dem_file,
        output_dir=output_dir,
        barranco_threshold=30.0,
        min_depression_depth=5.0,
        compute_slope_aspect=True,
        detect_barrancos=True,
        compute_wind_channeling=True,
        smooth_wind_fields=False  # Disabled for large datasets
    )
    
    # Preprocess terrain
    print("🔄 Starting terrain preprocessing...")
    try:
        result = preprocessor.preprocess_terrain()
        print(f"✅ Preprocessing completed successfully")
        print(f"📊 Grid size: {result.elevation.shape}")
        print(f"🏞️ Barranco cells: {result.barranco_mask.sum()}")
        print(f"💨 Wind channeling cells: {result.wind_channeling_mask.sum()}")
        print(f"💾 Data saved to: {output_dir}")
        return True
    except Exception as e:
        print(f"❌ Preprocessing failed: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 Terrain preprocessing completed successfully!")
    else:
        print("\n💥 Terrain preprocessing failed!")
        sys.exit(1)

