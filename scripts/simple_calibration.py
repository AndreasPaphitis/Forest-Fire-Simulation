#!/usr/bin/env python3
"""
Terrain Pre-processing for Calibration - FIXED VERSION
=====================================================

This script subsets the preprocessed terrain data to the fire area and resamples
from 5m to 20m resolution for faster calibration runs.

FIXED: Corrected subsetting logic to ensure proper geographic alignment.

Usage:
    python preprocessed_resampling_fixed.py

Author: Forest Fire Simulation Team
Date: 2025
"""

import os
import sys
import json
import logging
import numpy as np
from pathlib import Path
from scipy.ndimage import zoom
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

def preprocess_terrain_for_calibration():
    """Pre-process terrain by subsetting to fire area and resampling to 20m resolution."""
    
    logger.info("🏔️ TERRAIN PRE-PROCESSING FOR CALIBRATION - FIXED VERSION")
    logger.info("=" * 60)
    
    # Get fire area bounds
    fire_bounds = get_fire_area_bounds()
    if fire_bounds is None:
        logger.error("❌ Cannot proceed without fire area bounds")
        return False
    
    fire_min_x, fire_min_y, fire_max_x, fire_max_y = fire_bounds
    
    # Original terrain directory
    original_terrain_dir = Path("preprocessed_terrain")
    if not original_terrain_dir.exists():
        logger.error(f"❌ Original terrain directory not found: {original_terrain_dir}")
        return False
    
    # Create calibration terrain directory
    calibration_terrain_dir = Path("calibration_terrain")
    calibration_terrain_dir.mkdir(exist_ok=True)
    
    # Load terrain metadata
    metadata_file = original_terrain_dir / "metadata.json"
    if not metadata_file.exists():
        logger.error(f"❌ Terrain metadata not found: {metadata_file}")
        return False
    
    with open(metadata_file, 'r') as f:
        metadata = json.load(f)
    
    # ✅ STEP 1: Validate coordinate systems
    logger.info("�� Step 1: Validating coordinate systems...")
    if not validate_coordinate_systems(fire_bounds, metadata):
        logger.warning("⚠️ Coordinate system validation failed, but continuing...")
    
    # Parse transform matrix
    transform_str = metadata.get('transform', '')
    if not transform_str:
        logger.error("❌ No transform information in metadata")
        return False
    
    lines = transform_str.strip().split('\n')
    if len(lines) < 2:
        logger.error("❌ Invalid transform format")
        return False
    
    line1 = lines[0].replace('|', '').strip().split(',')
    line2 = lines[1].replace('|', '').strip().split(',')
    
    pixel_size_x = float(line1[0].strip())  # Should be 5.0
    pixel_size_y = float(line2[1].strip())  # Should be -5.0
    origin_x = float(line1[2].strip())
    origin_y = float(line2[2].strip())
    
    logger.info(f"📊 Original terrain resolution: {abs(pixel_size_x)}m")
    logger.info(f"�� Terrain origin: ({origin_x}, {origin_y})")
    
    # ✅ FIXED: Use a more robust approach for subsetting
    # Instead of just buffering the fire area, we'll use a larger area to ensure we capture the full fire region
    # and add a substantial buffer for calibration purposes
    
    # Calculate fire area dimensions
    fire_width_m = fire_max_x - fire_min_x
    fire_height_m = fire_max_y - fire_min_y
    
    # Use a larger buffer factor for calibration (50% instead of 10%)
    buffer_factor = 1.5
    buffered_width_m = fire_width_m * buffer_factor
    buffered_height_m = fire_height_m * buffer_factor
    
    # Calculate buffered bounds (centered on fire area)
    center_x = (fire_min_x + fire_max_x) / 2
    center_y = (fire_min_y + fire_max_y) / 2
    buffered_min_x = center_x - buffered_width_m / 2
    buffered_max_x = center_x + buffered_width_m / 2
    buffered_min_y = center_y - buffered_height_m / 2
    buffered_max_y = center_y + buffered_height_m / 2
    
    logger.info(f"�� Buffered fire area: ({buffered_min_x:.1f}, {buffered_min_y:.1f}) to ({buffered_max_x:.1f}, {buffered_max_y:.1f})")
    
    # ✅ FIXED: Correct grid coordinate calculation
    # The Y-axis is inverted in raster data, so we need to handle this correctly
    grid_min_x = int((buffered_min_x - origin_x) / pixel_size_x)
    grid_max_x = int((buffered_max_x - origin_x) / pixel_size_x)
    
    # FIXED: Correct Y-axis calculation for raster data
    # In raster data, Y=0 is at the top and increases downward
    # So we need to invert the Y coordinates
    grid_min_y = int((origin_y - buffered_max_y) / abs(pixel_size_y))
    grid_max_y = int((origin_y - buffered_min_y) / abs(pixel_size_y))
    
    logger.info(f"📍 Grid coordinates: ({grid_min_x}, {grid_min_y}) to ({grid_max_x}, {grid_max_y})")
    
    # ✅ STEP 2: Enhanced grid coordinate validation
    logger.info("🔍 Step 2: Enhanced grid coordinate validation...")
    terrain_shape = (metadata.get('grid_size', [0, 0])[0], metadata.get('grid_size', [0, 0])[1])
    if not validate_grid_coordinates_enhanced(grid_min_x, grid_max_x, grid_min_y, grid_max_y, terrain_shape):
        logger.error("❌ Grid coordinate validation failed")
        return False
    
    # Load and process each terrain file
    terrain_files = {
        'elevation': 'elevation.npy',
        'slope': 'slope.npy', 
        'aspect': 'aspect.npy',
        'barranco_mask': 'barranco_mask.npy',
        'barranco_directions': 'barranco_directions.npy',
        'depression_mask': 'depression_mask.npy',
        'wind_channeling_mask': 'wind_channeling_mask.npy',
        'wind_amplification': 'wind_amplification.npy',
        'wind_direction_modification': 'wind_direction_modification.npy'
    }
    
    target_resolution = 20.0  # Target resolution in meters
    zoom_factor = abs(pixel_size_x) / target_resolution  # 5.0 / 20.0 = 0.25
    
    logger.info(f"�� Target resolution: {target_resolution}m")
    logger.info(f"�� Zoom factor: {zoom_factor} (4x reduction)")
    
    processed_shapes = {}
    
    # ✅ STEP 3: Process terrain files with enhanced validation
    logger.info("�� Step 3: Processing terrain files with enhanced validation...")
    for terrain_name, filename in terrain_files.items():
        file_path = original_terrain_dir / filename
        if file_path.exists():
            logger.info(f"🔄 Processing {terrain_name}...")
            
            # Load terrain data
            terrain_data = np.load(file_path)
            original_shape = terrain_data.shape
            
            # ✅ FIXED: Enhanced subset extraction with bounds checking
            try:
                # Ensure bounds are within terrain
                safe_min_x = max(0, grid_min_x)
                safe_max_x = min(terrain_data.shape[1], grid_max_x)
                safe_min_y = max(0, grid_min_y)
                safe_max_y = min(terrain_data.shape[0], grid_max_y)
                
                # Check if we have a valid subset
                if safe_max_x <= safe_min_x or safe_max_y <= safe_min_y:
                    logger.error(f"❌ Invalid subset bounds for {terrain_name}")
                    logger.error(f"❌ X: {safe_min_x} to {safe_max_x}, Y: {safe_min_y} to {safe_max_y}")
                    return False
                
                subset = terrain_data[safe_min_y:safe_max_y, safe_min_x:safe_max_x]
                
            except IndexError as e:
                logger.error(f"❌ Array indexing failed for {terrain_name}: {e}")
                logger.error(f"❌ Terrain shape: {terrain_data.shape}")
                logger.error(f"❌ Requested indices: [{safe_min_y}:{safe_max_y}, {safe_min_x}:{safe_max_x}]")
                return False
            
            subset_shape = subset.shape
            
            # Resample from 5m to 20m
            resampled = zoom(subset, zoom_factor, order=1)
            final_shape = resampled.shape
            
            # Save processed terrain
            output_path = calibration_terrain_dir / filename
            np.save(output_path, resampled)
            
            processed_shapes[terrain_name] = final_shape
            
            logger.info(f"✅ {terrain_name}: {original_shape} → {subset_shape} → {final_shape}")
        else:
            logger.warning(f"⚠️ {filename} not found, skipping")
    
    # ✅ STEP 4: Create metadata and validate output
    logger.info("📝 Step 4: Creating enhanced metadata...")
    new_metadata = {
        'transform': f"|{target_resolution}, 0.0, {buffered_min_x}|\n|0.0, -{target_resolution}, {buffered_max_y}|",
        'width': list(processed_shapes.values())[0][1] if processed_shapes else 0,
        'height': list(processed_shapes.values())[0][0] if processed_shapes else 0,
        'resolution': target_resolution,
        'original_resolution': abs(pixel_size_x),
        'fire_area_bounds': [float(x) for x in fire_bounds],
        'buffered_bounds': [buffered_min_x, buffered_min_y, buffered_max_x, buffered_max_y],
        'processing_info': {
            'zoom_factor': zoom_factor,
            'buffer_factor': buffer_factor,
            'processed_files': list(processed_shapes.keys()),
            'fix_version': '1.0',
            'fix_description': 'Enhanced subsetting with proper bounds checking and larger buffer'
        }
    }
    
    with open(calibration_terrain_dir / "metadata.json", 'w') as f:
        json.dump(new_metadata, f, indent=2)
    
    # Calculate size reduction
    if processed_shapes:
        final_width, final_height = list(processed_shapes.values())[0]
        original_width = metadata.get('width', 0)
        original_height = metadata.get('height', 0)
        
        size_reduction = (original_width * original_height) / (final_width * final_height)
        
        logger.info(f"🎯 Processing complete!")
        logger.info(f"�� Final terrain size: {final_width}×{final_height} cells")
        logger.info(f"📊 Size reduction: {size_reduction:.1f}x smaller")
        logger.info(f"📊 Memory savings: ~{(1 - 1/size_reduction)*100:.1f}%")
        logger.info(f"📁 Output directory: {calibration_terrain_dir}")
        
        return True
    else:
        logger.error("❌ No terrain files were processed")
        return False

def validate_grid_coordinates_enhanced(grid_min_x, grid_max_x, grid_min_y, grid_max_y, terrain_shape):
    """Enhanced validation that grid coordinates are within terrain bounds."""
    terrain_height, terrain_width = terrain_shape
    
    # Check bounds
    if grid_min_x < 0 or grid_max_x > terrain_width:
        logger.error(f"❌ X coordinates out of bounds: {grid_min_x} to {grid_max_x}, terrain width: {terrain_width}")
        return False
    
    if grid_min_y < 0 or grid_max_y > terrain_height:
        logger.error(f"❌ Y coordinates out of bounds: {grid_min_y} to {grid_max_y}, terrain height: {terrain_height}")
        return False
    
    # Check subset size
    subset_width = grid_max_x - grid_min_x
    subset_height = grid_max_y - grid_min_y
    
    if subset_width <= 0 or subset_height <= 0:
        logger.error(f"❌ Invalid subset dimensions: {subset_width}×{subset_height}")
        return False
    
    # Enhanced validation: Check if subset is reasonable size
    if subset_width < 10 or subset_height < 10:
        logger.warning(f"⚠️ Subset is very small: {subset_width}×{subset_height} cells")
        logger.warning(f"⚠️ This might be too small for meaningful calibration")
    
    logger.info(f"✅ Grid coordinates validated: {subset_width}×{subset_height} cells")
    return True

def validate_coordinate_systems(fire_bounds, terrain_metadata):
    """Validate that fire area and terrain coordinate systems align."""
    # Extract terrain bounds from metadata
    terrain_origin_x = float(terrain_metadata['transform'].split('\n')[0].split(',')[2].strip().replace('|', ''))
    terrain_origin_y = float(terrain_metadata['transform'].split('\n')[1].split(',')[2].strip().replace('|', ''))
    terrain_width = terrain_metadata['grid_size'][1] * 5  # 5m resolution
    terrain_height = terrain_metadata['grid_size'][0] * 5
    
    terrain_bounds = [terrain_origin_x, terrain_origin_y, 
                     terrain_origin_x + terrain_width, terrain_origin_y + terrain_height]
    
    # Check if fire area is within terrain bounds
    if (fire_bounds[0] < terrain_bounds[0] or fire_bounds[2] > terrain_bounds[2] or
        fire_bounds[1] < terrain_bounds[1] or fire_bounds[3] > terrain_bounds[3]):
        logger.warning(f"⚠️ Fire area extends outside terrain bounds")
        logger.warning(f"⚠️ Fire: {fire_bounds}")
        logger.warning(f"⚠️ Terrain: {terrain_bounds}")
        return False
    
    return True

def main():
    """Main function."""
    logger.info("🚀 Starting terrain pre-processing for calibration (FIXED VERSION)...")
    
    success = preprocess_terrain_for_calibration()
    
    if success:
        logger.info("✅ Terrain pre-processing completed successfully!")
        logger.info("🎯 You can now run calibration with pre-processed terrain")
    else:
        logger.error("❌ Terrain pre-processing failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()