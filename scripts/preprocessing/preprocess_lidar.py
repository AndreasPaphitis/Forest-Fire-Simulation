#!/usr/bin/env python3
"""
LiDAR Preprocessing Script

This script preprocesses LiDAR/PAD data to NumPy arrays for fast loading
during calibration runs. Uses existing LiDARDataManager architecture.

Author: Forest Fire Simulation Team
Date: 2025
Version: 1.0
"""

import sys
import os
from pathlib import Path
import geopandas as gpd
import logging

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logging_utils import get_logger
from src.utils.lidar_preprocessor import create_lidar_preprocessor_from_fire_bounds

logger = get_logger(__name__)

def get_fire_area_bounds():
    """Get fire area bounds from Day 4 EMSR data (using existing function)."""
    try:
        # Find Day 4 file
        emsr_dir = Path("EMSR Delineations")
        day4_file = None
        
        for day_dir in sorted(emsr_dir.iterdir()):
            if not day_dir.is_dir():
                continue
            
            if "Day 4" in day_dir.name or "26_08_23" in day_dir.name:
                # Look for shapefile
                for file in day_dir.iterdir():
                    if file.suffix == '.shp':
                        day4_file = file
                        break
                if day4_file:
                    break
        
        if not day4_file:
            raise FileNotFoundError("Day 4 EMSR shapefile not found")
        
        logger.info(f"📁 Found Day 4 file: {day4_file}")
        
        # Read shapefile and convert to UTM
        day4_gdf = gpd.read_file(day4_file)
        logger.info(f"📊 Original CRS: {day4_gdf.crs}")
        
        # Convert to UTM (EPSG:25828 for Tenerife)
        day4_gdf_utm = day4_gdf.to_crs('EPSG:25828')
        logger.info(f"📊 Converted to UTM: {day4_gdf_utm.crs}")
        
        # Get bounds
        bounds = day4_gdf_utm.total_bounds  # [minx, miny, maxx, maxy]
        
        # Add 10% buffer (5% on each side) - SAME AS CALIBRATION RUNNER
        fire_min_x, fire_min_y, fire_max_x, fire_max_y = bounds
        fire_width_m = fire_max_x - fire_min_x
        fire_height_m = fire_max_y - fire_min_y
        
        # Apply 10% buffer (same as calibration runner)
        fire_bounds = (
            fire_min_x - (fire_width_m * 0.05),  # 5% buffer on each side
            fire_min_y - (fire_height_m * 0.05),
            fire_max_x + (fire_width_m * 0.05),
            fire_max_y + (fire_height_m * 0.05)
        )
        
        logger.info(f"📍 Original fire bounds: {bounds}")
        logger.info(f"📍 Original fire area size: {fire_width_m:.1f}m × {fire_height_m:.1f}m")
        logger.info(f"📍 Buffered simulation area: ({fire_bounds[0]:.1f}, {fire_bounds[1]:.1f}) to ({fire_bounds[2]:.1f}, {fire_bounds[3]:.1f})")
        logger.info(f"📍 Buffered area size: {(fire_bounds[2] - fire_bounds[0]):.1f}m × {(fire_bounds[3] - fire_bounds[1]):.1f}m (10% buffer)")
        
        return fire_bounds
        
    except Exception as e:
        logger.error(f"❌ Failed to get fire area bounds: {e}")
        raise

def main():
    """Main preprocessing function."""
    logger.info("🚀 LIDAR PREPROCESSING FOR DAY 4 FIRE AREA")
    
    # Get fire bounds
    fire_bounds = get_fire_area_bounds()
    
    # Set paths
    lidar_dir = r"C:\Users\user\Desktop\UvA\YEAR 2\Thesis\LiDAR\Analysis files\Processed\PAD Results"
    output_dir = "preprocessed_lidar"
    
    logger.info(f"📁 LiDAR directory: {lidar_dir}")
    logger.info(f"📁 Output directory: {output_dir}")
    
    try:
        # Create preprocessor
        preprocessor = create_lidar_preprocessor_from_fire_bounds(
            lidar_dir=lidar_dir,
            fire_bounds=fire_bounds,
            output_dir=output_dir,
            resolution=20.0,
            num_layers=25
        )
        
        # Run preprocessing
        preprocessed_data = preprocessor.preprocess_lidar()
        
        logger.info("✅ LiDAR preprocessing completed successfully!")
        logger.info(f"📊 Processed {len(preprocessed_data.layer_data)} layers")
        logger.info(f"📁 Output saved to: {output_dir}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ LiDAR preprocessing failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)
