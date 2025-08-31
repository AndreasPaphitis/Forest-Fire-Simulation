#!/usr/bin/env python3
"""
Terrain Preprocessing for Day 4 Fire Area - 20m Resolution
========================================================

This script preprocesses terrain data specifically for the Day 4 fire area
at 20m resolution, combining terrain preprocessing with fire area subsetting.

Author: Forest Fire Simulation Team
Date: 2025
"""

import os
import sys
import json
import logging
import numpy as np
from pathlib import Path
import geopandas as gpd
from scipy.ndimage import zoom
import time

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
            
            # Check if this is Day 4
            if "Day 4" in day_dir.name or "26_08_23" in day_dir.name:
                # Look for shapefile or JSON
                for file_path in day_dir.iterdir():
                    if file_path.suffix in ['.shp', '.json']:
                        day4_file = file_path
                        break
                if day4_file:
                    break
        
        if not day4_file:
            raise FileNotFoundError("Day 4 EMSR file not found")
        
        logger.info(f"📍 Using Day 4 file: {day4_file}")
        
        # Load and get bounds
        day4_gdf = gpd.read_file(str(day4_file))
        
        # Convert to UTM coordinates (EPSG:25828) to match LiDAR data
        if day4_gdf.crs != 'EPSG:25828':
            day4_gdf = day4_gdf.to_crs('EPSG:25828')
            logger.info("🔄 Converted Day 4 bounds from WGS84 to UTM (EPSG:25828)")
        
        bounds = day4_gdf.total_bounds  # [minx, miny, maxx, maxy]
        
        # Check if bounds are reasonable
        width_m = bounds[2] - bounds[0]
        height_m = bounds[3] - bounds[1]
        
        logger.info(f"📍 Fire area size: {width_m:.1f}m × {height_m:.1f}m")
        
        if width_m < 100 or height_m < 100:
            logger.warning(f"⚠️ Fire area is very small: {width_m:.1f}m × {height_m:.1f}m")
            logger.warning(f"⚠️ This might be too small for meaningful calibration")
        
        return bounds
        
    except Exception as e:
        logger.error(f"❌ Failed to get fire area bounds: {e}")
        return None

def preprocess_terrain_for_day4_fire_area():
    """Preprocess terrain data for Day 4 fire area at 20m resolution."""
    
    logger.info("🏔️ TERRAIN PREPROCESSING FOR DAY 4 FIRE AREA - 20M RESOLUTION")
    logger.info("=" * 70)
    
    # Get fire area bounds
    fire_bounds = get_fire_area_bounds()
    if fire_bounds is None:
        logger.error("❌ Cannot proceed without fire area bounds")
        return False
    
    fire_min_x, fire_min_y, fire_max_x, fire_max_y = fire_bounds
    
    # Calculate buffered area for preprocessing
    fire_width_m = fire_max_x - fire_min_x
    fire_height_m = fire_max_y - fire_min_y
    
    # Use a larger buffer factor for preprocessing (100% buffer)
    buffer_factor = 2.0
    buffered_width_m = fire_width_m * buffer_factor
    buffered_height_m = fire_height_m * buffer_factor
    
    # Calculate buffered bounds (centered on fire area)
    center_x = (fire_min_x + fire_max_x) / 2
    center_y = (fire_min_y + fire_max_y) / 2
    buffered_min_x = center_x - buffered_width_m / 2
    buffered_max_x = center_x + buffered_width_m / 2
    buffered_min_y = center_y - buffered_height_m / 2
    buffered_max_y = center_y + buffered_height_m / 2
    
    logger.info(f"📍 Buffered preprocessing area: ({buffered_min_x:.1f}, {buffered_min_y:.1f}) to ({buffered_max_x:.1f}, {buffered_max_y:.1f})")
    
    # Create output directory
    output_dir = Path(r"C:\Users\user\Desktop\UvA\YEAR 2\Thesis\Coding\QGIS python scripts\preprocessed_terrain")
    output_dir.mkdir(exist_ok=True)
    
    # Import terrain preprocessor - FIXED: Use the working import path
    try:
        sys.path.append(str(Path(__file__).parent / "src"))
        from src.utils.terrain_preprocessor_rasterio_fixed import create_terrain_preprocessor_rasterio_fixed
    except ImportError as e:
        logger.error(f"❌ Failed to import terrain preprocessor: {e}")
        return False
    
    # DEM file path
    dem_file = "C:/Users/user/Desktop/UvA/YEAR 2/Thesis/LiDAR/DTM data/Merged_DTM.tif"
    
    if not os.path.exists(dem_file):
        logger.error(f"❌ DEM file not found: {dem_file}")
        return False
    
    logger.info(f"📁 DEM file: {dem_file}")
    logger.info(f"📁 Output directory: {output_dir}")
    
    # Create preprocessor with Day 4 fire area configuration - FIXED: Use exact same parameters as working script
    logger.info("🔧 Creating terrain preprocessor for Day 4 fire area...")
    
    preprocessor = create_terrain_preprocessor_rasterio_fixed(
        dem_file=dem_file,
        output_dir=str(output_dir),
        
        # Geographic bounds for Day 4 fire area
        geo_bounds=(buffered_min_x, buffered_min_y, buffered_max_x, buffered_max_y),
        crs="EPSG:25828",
        
        # FIXED: Use exact same parameters as the working preprocess_terrain.py script
        barranco_threshold=25.0,  # Literature-based: 20-30° for volcanic terrain
        min_depression_depth=3.0,  # Literature-based: 2-5m for volcanic terrain
        min_depression_area=6,  # Literature-based: 4-8 cells minimum area
        smoothing_kernel_size=3,  # Wind field smoothing
        wind_channeling_strength=0.8,  # Literature-based: 0.7-1.0 for barrancos
        barranco_amplification=2.5,  # Literature-based: 2.0-3.0 wind amplification
        
        # Processing options - FIXED: Use exact same as working script
        compute_slope_aspect=True,
        detect_barrancos=True,
        compute_wind_channeling=True,
        smooth_wind_fields=False,  # Disabled for large datasets
        
        # Output options - FIXED: Use exact same as working script
        save_intermediate=False,
        compression=True,
        format="numpy",
        
        # Memory management - FIXED: Use exact same as working script
        memory_limit_gb=8.0  # Memory limit for processing
    )
    
    # Preprocess the terrain
    logger.info("🔄 Starting terrain preprocessing for Day 4 fire area...")
    start_time = time.time()
    
    try:
        preprocessed_data = preprocessor.preprocess_terrain()
        preprocessing_time = time.time() - start_time
        
        logger.info(f"✅ Terrain preprocessing completed in {preprocessing_time:.2f} seconds")
        logger.info(f"📊 Original grid size: {preprocessed_data.elevation.shape}")
        
    except Exception as e:
        logger.error(f"❌ Terrain preprocessing failed: {e}")
        return False
    
    # Now resample to 20m resolution
    logger.info("🔄 Resampling to 20m resolution...")
    
    # Calculate zoom factor (assuming original is 5m resolution)
    original_resolution = 5.0  # meters
    target_resolution = 20.0   # meters
    zoom_factor = original_resolution / target_resolution  # 5.0 / 20.0 = 0.25
    
    logger.info(f"📊 Zoom factor: {zoom_factor} (4x reduction)")
    
    # Resample all terrain data
    resampled_data = {}
    
    terrain_arrays = {
        'elevation': preprocessed_data.elevation,
        'slope': preprocessed_data.slope,
        'aspect': preprocessed_data.aspect,
        'barranco_mask': preprocessed_data.barranco_mask,
        'barranco_directions': preprocessed_data.barranco_directions,
        'depression_mask': preprocessed_data.depression_mask,
        'wind_channeling_mask': preprocessed_data.wind_channeling_mask,
        'wind_amplification': preprocessed_data.wind_amplification,
        'wind_direction_modification': preprocessed_data.wind_direction_modification
    }
    
    for name, array in terrain_arrays.items():
        if array is not None:
            logger.info(f"🔄 Resampling {name}...")
            
            # Use different interpolation for different data types
            if name in ['barranco_mask', 'depression_mask', 'wind_channeling_mask']:
                # Use nearest neighbor for boolean masks
                resampled = zoom(array, zoom_factor, order=0)
                # Convert back to boolean
                resampled = resampled > 0.5
            else:
                # Use linear interpolation for continuous data
                resampled = zoom(array, zoom_factor, order=1)
            
            resampled_data[name] = resampled
            logger.info(f"✅ {name}: {array.shape} → {resampled.shape}")
    
    # Save resampled data
    logger.info("💾 Saving resampled terrain data...")
    
    for name, array in resampled_data.items():
        output_path = output_dir / f"{name}.npy"
        np.save(output_path, array)
        logger.info(f"✅ Saved {name}.npy")
    
    # Create metadata
    logger.info("📝 Creating metadata...")
    
    # Calculate new bounds for 20m resolution
    final_width = resampled_data['elevation'].shape[1]
    final_height = resampled_data['elevation'].shape[0]
    
    # Calculate new transform for 20m resolution
    new_transform = f"|{target_resolution}, 0.0, {buffered_min_x}|\n|0.0, -{target_resolution}, {buffered_max_y}|"
    
    metadata = {
        'dem_file': dem_file,
        'output_dir': str(output_dir),
        'processing_date': time.strftime("%Y-%m-%d %H:%M:%S"),
        'grid_size': [final_height, final_width],
        'crs': "EPSG:25828",
        'transform': new_transform,
        'resolution': target_resolution,
        'original_resolution': original_resolution,
        'fire_area_bounds': [float(x) for x in fire_bounds],
        'buffered_bounds': [buffered_min_x, buffered_min_y, buffered_max_x, buffered_max_y],
        'processing_info': {
            'zoom_factor': zoom_factor,
            'buffer_factor': buffer_factor,
            'processed_files': list(resampled_data.keys()),
            'preprocessing_time_seconds': preprocessing_time,
            'fix_version': '1.0',
            'fix_description': 'Day 4 fire area preprocessing with 20m resolution'
        }
    }
    
    with open(output_dir / "metadata.json", 'w') as f:
        json.dump(metadata, f, indent=2)
    
    # Calculate size reduction
    original_cells = preprocessed_data.elevation.size
    final_cells = resampled_data['elevation'].size
    size_reduction = original_cells / final_cells
    
    logger.info(f"🎯 Processing complete!")
    logger.info(f"📊 Final terrain size: {final_width}×{final_height} cells")
    logger.info(f"📊 Resolution: {target_resolution}m")
    logger.info(f"📊 Size reduction: {size_reduction:.1f}x smaller")
    logger.info(f"📊 Memory savings: ~{(1 - 1/size_reduction)*100:.1f}%")
    logger.info(f"📁 Output directory: {output_dir}")
    
    # Display statistics
    if 'elevation' in resampled_data:
        elev_data = resampled_data['elevation']
        logger.info(f"📊 Elevation range: {np.min(elev_data):.1f}m to {np.max(elev_data):.1f}m")
    
    if 'barranco_mask' in resampled_data:
        barranco_count = np.sum(resampled_data['barranco_mask'])
        logger.info(f"💚 Barranco cells: {barranco_count}")
    
    if 'wind_channeling_mask' in resampled_data:
        wind_count = np.sum(resampled_data['wind_channeling_mask'])
        logger.info(f"💨 Wind channeling cells: {wind_count}")
    
    return True

def main():
    """Main function."""
    logger.info("🚀 Starting Day 4 fire area terrain preprocessing...")
    
    success = preprocess_terrain_for_day4_fire_area()
    
    if success:
        logger.info("✅ Day 4 fire area terrain preprocessing completed successfully!")
        logger.info("🎯 You can now use this terrain data for calibration")
        logger.info("📁 Data location: day4_fire_area_terrain_20m/")
    else:
        logger.error("❌ Day 4 fire area terrain preprocessing failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()