#!/usr/bin/env python3
"""
Diagnose Geographic Bounds Filtering Issue

This script investigates why geographic bounds filtering is only finding 3 layers
when there should be more layers available in the area.
"""

import sys
import os
from pathlib import Path
import logging

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.lidar_utils import LiDARDataManager
import geopandas as gpd

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_fire_area_bounds():
    """Get fire area bounds from Day 4 EMSR data."""
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
        
        # Add 10% buffer (5% on each side)
        fire_min_x, fire_min_y, fire_max_x, fire_max_y = bounds
        fire_width_m = fire_max_x - fire_min_x
        fire_height_m = fire_max_y - fire_min_y
        
        # Apply 10% buffer
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

def diagnose_lidar_detection():
    """Diagnose LiDAR layer detection with and without geographic bounds."""
    
    # Get fire area bounds
    fire_bounds = get_fire_area_bounds()
    
    # Initialize LiDAR manager
    lidar_data_dir = "preprocessed_lidar"
    lidar_manager = LiDARDataManager(lidar_data_dir)
    
    logger.info(f"\n🔍 Testing layer detection WITHOUT geographic bounds:")
    available_layers = lidar_manager._detect_available_layers(lidar_data_dir)
    max_layers = lidar_manager.get_max_available_layers(lidar_data_dir)
    
    logger.info(f"   - Available layers dict: {len(available_layers)} entries")
    logger.info(f"   - Available layer indices: {list(available_layers.keys()) if available_layers else 'None'}")
    logger.info(f"   - Max layers detected: {max_layers}")
    
    if available_layers:
        for layer_idx in sorted(available_layers.keys()):
            height_meters = layer_idx * 2
            file_count = len(available_layers[layer_idx])
            logger.info(f"   - Layer {layer_idx} (height {height_meters}m): {file_count} files")
    
    # Test layer detection WITH geographic bounds (fire area)
    logger.info(f"\n🔍 Testing layer detection WITH geographic bounds:")
    
    # Set geographic bounds for fire area
    lidar_manager.geo_bounds = fire_bounds
    
    available_layers_bounded = lidar_manager._detect_available_layers(lidar_data_dir)
    max_layers_bounded = lidar_manager.get_max_available_layers(lidar_data_dir)
    
    logger.info(f"   - Geographic bounds: {fire_bounds}")
    logger.info(f"   - Available layers (bounded): {len(available_layers_bounded)} entries")
    logger.info(f"   - Available layer indices (bounded): {list(available_layers_bounded.keys()) if available_layers_bounded else 'None'}")
    logger.info(f"   - Max layers detected (bounded): {max_layers_bounded}")
    
    if available_layers_bounded:
        for layer_idx in sorted(available_layers_bounded.keys()):
            height_meters = layer_idx * 2
            file_count = len(available_layers_bounded[layer_idx])
            logger.info(f"   - Layer {layer_idx} (height {height_meters}m): {file_count} files")
    
    # Test with different buffer sizes
    logger.info(f"\n🔍 Testing with different buffer sizes:")
    
    for buffer_percent in [5, 10, 20, 50]:
        fire_min_x, fire_min_y, fire_max_x, fire_max_y = fire_bounds
        fire_width_m = fire_max_x - fire_min_x
        fire_height_m = fire_max_y - fire_min_y
        
        # Apply buffer
        buffered_bounds = (
            fire_min_x - (fire_width_m * buffer_percent / 100.0),
            fire_min_y - (fire_height_m * buffer_percent / 100.0),
            fire_max_x + (fire_width_m * buffer_percent / 100.0),
            fire_max_y + (fire_height_m * buffer_percent / 100.0)
        )
        
        lidar_manager.geo_bounds = buffered_bounds
        available_layers_buffered = lidar_manager._detect_available_layers(lidar_data_dir)
        
        logger.info(f"   - {buffer_percent}% buffer: {len(available_layers_buffered)} layers")
        if available_layers_buffered:
            layer_indices = list(available_layers_buffered.keys())
            logger.info(f"     Layer indices: {layer_indices}")

def main():
    """Main diagnostic function."""
    logger.info("🔍 DIAGNOSING GEOGRAPHIC BOUNDS FILTERING ISSUE")
    logger.info("=" * 60)
    
    try:
        diagnose_lidar_detection()
    except Exception as e:
        logger.error(f"❌ Diagnostic failed: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()
