#!/usr/bin/env python3
"""
DTM (Digital Terrain Model) Processing Script for Forest Fire Simulation

This script processes multiple DTM datasets covering Tenerife, merging them into
a single file suitable for upload to HPC systems. It handles:
- Discovery of DTM files in directory structures
- Analysis of extents and resolutions
- Merging/mosaicking multiple DTM files
- Cropping to specific areas of interest
- Output optimization for HPC use

Usage:
    python dtm_processor.py --input_dir /path/to/dtm/data --output_file processed_dtm.tif
    python dtm_processor.py --input_dir /path/to/dtm/data --crop_to_lidar /path/to/lidar/data

Author: Forest Fire Simulation Team
Date: 2025
"""

import os
import sys
import argparse
import json
import time
from pathlib import Path
from typing import List, Tuple, Dict, Optional, Any
import logging

import numpy as np
from osgeo import gdal, osr, ogr
import rasterio
from rasterio.merge import merge
from rasterio.mask import mask
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.windows import Window
import geopandas as gpd
from shapely.geometry import box
import warnings

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Suppress some warnings
warnings.filterwarnings("ignore", category=rasterio.errors.NotGeoreferencedWarning)

class DTMProcessor:
    """Processes DTM datasets for forest fire simulation."""
    
    def __init__(self, input_dir: str, output_file: str = None):
        """
        Initialize DTM processor.
        
        Args:
            input_dir: Directory containing DTM files
            output_file: Output file path for processed DTM
        """
        self.input_dir = Path(input_dir)
        self.output_file = output_file
        self.dtm_files = []
        self.dtm_info = {}
        
        # GDAL configurations for better performance
        gdal.SetConfigOption('GDAL_CACHEMAX', '2048')
        gdal.SetConfigOption('GDAL_NUM_THREADS', 'ALL_CPUS')
        gdal.SetConfigOption('GDAL_DISABLE_READDIR_ON_OPEN', 'EMPTY_DIR')
    
    def discover_dtm_files(self, patterns: List[str] = None) -> List[Path]:
        """
        Discover DTM files in the input directory.
        
        Args:
            patterns: File patterns to search for (e.g., ['*.tif', '*.tiff', '*DTM*'])
        
        Returns:
            List of discovered DTM file paths
        """
        if patterns is None:
            patterns = [
                '*DTM*.tif', '*DTM*.tiff',
                '*dtm*.tif', '*dtm*.tiff', 
                '*DEM*.tif', '*DEM*.tiff',
                '*dem*.tif', '*dem*.tiff',
                '*.tif', '*.tiff'  # Fallback to all tif files
            ]
        
        logger.info(f"Searching for DTM files in: {self.input_dir}")
        
        found_files = set()
        
        for pattern in patterns:
            # Search recursively
            matches = list(self.input_dir.rglob(pattern))
            found_files.update(matches)
            logger.info(f"Pattern '{pattern}': found {len(matches)} files")
        
        self.dtm_files = sorted(list(found_files))
        logger.info(f"Total unique DTM files discovered: {len(self.dtm_files)}")
        
        return self.dtm_files
    
    def analyze_dtm_files(self) -> Dict[str, Any]:
        """
        Analyze discovered DTM files for extents, resolutions, and other properties.
        
        Returns:
            Dictionary with analysis results
        """
        if not self.dtm_files:
            logger.warning("No DTM files to analyze. Run discover_dtm_files() first.")
            return {}
        
        logger.info("Analyzing DTM files...")
        
        analysis = {
            'total_files': len(self.dtm_files),
            'valid_files': 0,
            'invalid_files': [],
            'resolutions': set(),
            'crs_list': set(),
            'total_extent': [float('inf'), float('inf'), float('-inf'), float('-inf')],  # min_x, min_y, max_x, max_y
            'file_details': {},
            'estimated_merged_size': None
        }
        
        for i, dtm_file in enumerate(self.dtm_files):
            try:
                with rasterio.open(dtm_file) as src:
                    # Basic properties
                    bounds = src.bounds
                    resolution = src.res
                    crs = src.crs.to_string() if src.crs else 'Unknown'
                    shape = src.shape
                    dtype = src.dtypes[0]
                    nodata = src.nodata
                    
                    # Update analysis
                    analysis['valid_files'] += 1
                    analysis['resolutions'].add(resolution)
                    analysis['crs_list'].add(crs)
                    
                    # Update total extent
                    analysis['total_extent'][0] = min(analysis['total_extent'][0], bounds.left)
                    analysis['total_extent'][1] = min(analysis['total_extent'][1], bounds.bottom)
                    analysis['total_extent'][2] = max(analysis['total_extent'][2], bounds.right)
                    analysis['total_extent'][3] = max(analysis['total_extent'][3], bounds.top)
                    
                    # Store file details
                    analysis['file_details'][str(dtm_file)] = {
                        'bounds': [bounds.left, bounds.bottom, bounds.right, bounds.top],
                        'resolution': resolution,
                        'shape': shape,
                        'crs': crs,
                        'dtype': str(dtype),
                        'nodata': nodata,
                        'file_size_mb': dtm_file.stat().st_size / (1024*1024)
                    }
                    
                    if i % 10 == 0:
                        logger.info(f"Analyzed {i+1}/{len(self.dtm_files)} files...")
                        
            except Exception as e:
                logger.warning(f"Error analyzing {dtm_file}: {e}")
                analysis['invalid_files'].append(str(dtm_file))
        
        # Calculate estimated merged size
        if analysis['valid_files'] > 0 and analysis['resolutions']:
            extent = analysis['total_extent']
            resolution = min(analysis['resolutions'])  # Use finest resolution
            width = int((extent[2] - extent[0]) / resolution[0])
            height = int((extent[3] - extent[1]) / resolution[1])
            analysis['estimated_merged_size'] = {
                'width': width,
                'height': height,
                'resolution': resolution,
                'estimated_file_size_gb': (width * height * 4) / (1024**3)  # Assuming float32
            }
        
        # Convert sets to lists for JSON serialization
        analysis['resolutions'] = list(analysis['resolutions'])
        analysis['crs_list'] = list(analysis['crs_list'])
        
        self.dtm_info = analysis
        logger.info(f"Analysis complete: {analysis['valid_files']} valid files, {len(analysis['invalid_files'])} invalid")
        
        return analysis
    
    def print_analysis_summary(self):
        """Print a summary of the DTM analysis."""
        if not self.dtm_info:
            logger.warning("No analysis data available. Run analyze_dtm_files() first.")
            return
        
        info = self.dtm_info
        
        print("\n" + "="*60)
        print("DTM ANALYSIS SUMMARY")
        print("="*60)
        
        print(f"📁 Input directory: {self.input_dir}")
        print(f"📊 Total files found: {info['total_files']}")
        print(f"✅ Valid DTM files: {info['valid_files']}")
        print(f"❌ Invalid files: {len(info['invalid_files'])}")
        
        if info['invalid_files']:
            print("   Invalid files:")
            for invalid_file in info['invalid_files'][:5]:  # Show first 5
                print(f"   - {Path(invalid_file).name}")
            if len(info['invalid_files']) > 5:
                print(f"   ... and {len(info['invalid_files']) - 5} more")
        
        print(f"\n🌍 Geographic Extent:")
        extent = info['total_extent']
        print(f"   Min X: {extent[0]:.2f}")
        print(f"   Min Y: {extent[1]:.2f}")
        print(f"   Max X: {extent[2]:.2f}")
        print(f"   Max Y: {extent[3]:.2f}")
        print(f"   Width: {extent[2] - extent[0]:.2f} units")
        print(f"   Height: {extent[3] - extent[1]:.2f} units")
        
        print(f"\n📏 Resolutions found:")
        for res in info['resolutions']:
            print(f"   - {res[0]:.6f} x {res[1]:.6f}")
        
        print(f"\n🗺️  Coordinate systems:")
        for crs in info['crs_list']:
            print(f"   - {crs}")
        
        if info['estimated_merged_size']:
            est = info['estimated_merged_size']
            print(f"\n📐 Estimated merged DTM:")
            print(f"   Dimensions: {est['width']:,} x {est['height']:,} pixels")
            print(f"   Resolution: {est['resolution'][0]:.6f} x {est['resolution'][1]:.6f}")
            print(f"   Estimated size: {est['estimated_file_size_gb']:.2f} GB")
        
        print("="*60)
    
    def merge_dtm_files(self, output_file: str = None, target_crs: str = None, 
                       resolution: Tuple[float, float] = None, 
                       crop_bounds: Tuple[float, float, float, float] = None,
                       resampling_method: str = 'bilinear',
                       compression: str = 'LZW',
                       tiled: bool = True,
                       blocksize: int = 512) -> str:
        """
        Merge DTM files into a single raster.
        
        Args:
            output_file: Output file path
            target_crs: Target CRS (e.g., 'EPSG:32628')
            resolution: Target resolution (x, y)
            crop_bounds: Bounding box to crop to (min_x, min_y, max_x, max_y)
            resampling_method: Resampling method for reprojection
            compression: Compression method for output
            tiled: Whether to create tiled output
            blocksize: Block size for tiled output
        
        Returns:
            Path to merged DTM file
        """
        if not self.dtm_files:
            raise ValueError("No DTM files to merge. Run discover_dtm_files() first.")
        
        if output_file is None:
            output_file = self.output_file or "merged_dtm.tif"
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Merging {len(self.dtm_files)} DTM files...")
        logger.info(f"Output file: {output_path}")
        
        # Filter valid files and open them
        valid_files = []
        datasets = []
        
        for dtm_file in self.dtm_files:
            try:
                src = rasterio.open(dtm_file)
                datasets.append(src)
                valid_files.append(dtm_file)
            except Exception as e:
                logger.warning(f"Cannot open {dtm_file}: {e}")
        
        logger.info(f"Successfully opened {len(datasets)} DTM files for merging")
        
        try:
            # Determine target CRS
            if target_crs is None:
                # Use CRS from first dataset
                target_crs = datasets[0].crs
                logger.info(f"Using CRS from first dataset: {target_crs}")
            else:
                logger.info(f"Using specified target CRS: {target_crs}")
            
            # Determine target resolution
            if resolution is None:
                # Use finest resolution found
                resolutions = [src.res for src in datasets]
                resolution = min(resolutions)
                logger.info(f"Using finest resolution found: {resolution}")
            else:
                logger.info(f"Using specified resolution: {resolution}")
            
            # Merge the datasets
            logger.info("Performing merge operation...")
            start_time = time.time()
            
            if crop_bounds:
                logger.info(f"Cropping to bounds: {crop_bounds}")
                # Create a bounding box geometry for cropping
                crop_geom = [box(*crop_bounds)]
                
                # Merge with cropping
                merged_data, merged_transform = merge(
                    datasets,
                    bounds=crop_bounds,
                    res=resolution,
                    resampling=getattr(Resampling, resampling_method.lower())
                )
            else:
                # Merge without cropping
                merged_data, merged_transform = merge(
                    datasets,
                    res=resolution,
                    resampling=getattr(Resampling, resampling_method.lower())
                )
            
            merge_time = time.time() - start_time
            logger.info(f"Merge completed in {merge_time:.2f} seconds")
            
            # Determine output profile
            profile = datasets[0].profile.copy()
            profile.update({
                'driver': 'GTiff',
                'height': merged_data.shape[1],
                'width': merged_data.shape[2],
                'transform': merged_transform,
                'crs': target_crs,
                'dtype': merged_data.dtype,
                'count': 1,
                'compress': compression,
                'tiled': tiled,
                'blockxsize': blocksize,
                'blockysize': blocksize,
                'BIGTIFF': 'YES'  # Support large files
            })
            
            # Write the merged DTM
            logger.info("Writing merged DTM...")
            write_start = time.time()
            
            with rasterio.open(output_path, 'w', **profile) as dst:
                dst.write(merged_data[0], 1)
                
                # Add metadata
                dst.update_tags(
                    DESCRIPTION='Merged DTM for forest fire simulation',
                    SOURCE_FILES=f'{len(valid_files)} DTM files',
                    PROCESSING_DATE=time.strftime('%Y-%m-%d %H:%M:%S'),
                    RESAMPLING_METHOD=resampling_method,
                    RESOLUTION=f'{resolution[0]}x{resolution[1]}'
                )
            
            write_time = time.time() - write_start
            logger.info(f"Writing completed in {write_time:.2f} seconds")
            
            # Report final file info
            output_size_mb = output_path.stat().st_size / (1024*1024)
            logger.info(f"Output file size: {output_size_mb:.2f} MB")
            
            # Get final raster info
            with rasterio.open(output_path) as final:
                logger.info(f"Final dimensions: {final.width} x {final.height}")
                logger.info(f"Final bounds: {final.bounds}")
                logger.info(f"Final CRS: {final.crs}")
                logger.info(f"Final resolution: {final.res}")
        
        finally:
            # Close all datasets
            for dataset in datasets:
                dataset.close()
        
        logger.info(f"✅ DTM merge completed successfully: {output_path}")
        return str(output_path)
    
    def crop_to_lidar_extent(self, lidar_dir: str, output_file: str = None, 
                           buffer_meters: float = 500.0) -> str:
        """
        Crop DTM to match LiDAR data extent with optional buffer.
        
        Args:
            lidar_dir: Directory containing LiDAR files
            output_file: Output file for cropped DTM
            buffer_meters: Buffer around LiDAR extent in meters
        
        Returns:
            Path to cropped DTM file
        """
        from src.utils.lidar_utils import LiDARDataManager
        
        logger.info(f"Calculating LiDAR extent from: {lidar_dir}")
        
        # Get LiDAR extent
        lidar_manager = LiDARDataManager(base_dir=lidar_dir)
        lidar_extent = lidar_manager.get_lidar_extent(lidar_dir)
        
        if not lidar_extent:
            raise ValueError(f"Could not determine LiDAR extent from {lidar_dir}")
        
        logger.info(f"LiDAR extent: {lidar_extent}")
        
        # Add buffer
        min_x, min_y, max_x, max_y = lidar_extent
        crop_bounds = (
            min_x - buffer_meters,
            min_y - buffer_meters,
            max_x + buffer_meters,
            max_y + buffer_meters
        )
        
        logger.info(f"Crop bounds (with {buffer_meters}m buffer): {crop_bounds}")
        
        # Perform merge with cropping
        return self.merge_dtm_files(
            output_file=output_file,
            crop_bounds=crop_bounds
        )
    
    def save_analysis_report(self, output_file: str = None):
        """Save analysis report to JSON file."""
        if not self.dtm_info:
            logger.warning("No analysis data to save. Run analyze_dtm_files() first.")
            return
        
        if output_file is None:
            output_file = "dtm_analysis_report.json"
        
        output_path = Path(output_file)
        
        # Add timestamp to report
        report = self.dtm_info.copy()
        report['analysis_timestamp'] = time.strftime('%Y-%m-%d %H:%M:%S')
        report['input_directory'] = str(self.input_dir)
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Analysis report saved to: {output_path}")
    
    def validate_output(self, dtm_file: str) -> Dict[str, Any]:
        """
        Validate the processed DTM file.
        
        Args:
            dtm_file: Path to DTM file to validate
        
        Returns:
            Validation results dictionary
        """
        logger.info(f"Validating DTM file: {dtm_file}")
        
        validation = {
            'file_exists': False,
            'readable': False,
            'has_crs': False,
            'has_nodata': False,
            'min_elevation': None,
            'max_elevation': None,
            'mean_elevation': None,
            'file_size_mb': None,
            'dimensions': None,
            'resolution': None,
            'bounds': None,
            'issues': []
        }
        
        try:
            dtm_path = Path(dtm_file)
            validation['file_exists'] = dtm_path.exists()
            
            if not validation['file_exists']:
                validation['issues'].append("File does not exist")
                return validation
            
            validation['file_size_mb'] = dtm_path.stat().st_size / (1024*1024)
            
            with rasterio.open(dtm_file) as src:
                validation['readable'] = True
                validation['has_crs'] = src.crs is not None
                validation['has_nodata'] = src.nodata is not None
                validation['dimensions'] = (src.width, src.height)
                validation['resolution'] = src.res
                validation['bounds'] = list(src.bounds)
                
                # Sample elevation statistics
                logger.info("Calculating elevation statistics...")
                
                # Read data in chunks to handle large files
                chunk_size = 1024
                elevations = []
                
                for i in range(0, src.height, chunk_size):
                    for j in range(0, src.width, chunk_size):
                        window = Window(j, i, 
                                      min(chunk_size, src.width - j),
                                      min(chunk_size, src.height - i))
                        chunk = src.read(1, window=window)
                        
                        # Filter out nodata values
                        if src.nodata is not None:
                            valid_data = chunk[chunk != src.nodata]
                        else:
                            valid_data = chunk
                        
                        if len(valid_data) > 0:
                            elevations.extend(valid_data.flatten())
                        
                        # Limit sample size for very large files
                        if len(elevations) > 1000000:  # 1M samples should be enough
                            break
                    if len(elevations) > 1000000:
                        break
                
                if elevations:
                    elevations = np.array(elevations)
                    validation['min_elevation'] = float(elevations.min())
                    validation['max_elevation'] = float(elevations.max())
                    validation['mean_elevation'] = float(elevations.mean())
                
                # Check for issues
                if not validation['has_crs']:
                    validation['issues'].append("No coordinate reference system")
                
                if validation['min_elevation'] is not None and validation['max_elevation'] is not None:
                    if validation['min_elevation'] == validation['max_elevation']:
                        validation['issues'].append("Constant elevation values")
                    
                    if validation['min_elevation'] < -500 or validation['max_elevation'] > 10000:
                        validation['issues'].append("Suspicious elevation values")
                
        except Exception as e:
            validation['issues'].append(f"Error reading file: {e}")
        
        logger.info(f"Validation complete. Issues found: {len(validation['issues'])}")
        return validation


def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(description='Process DTM files for forest fire simulation')
    
    parser.add_argument('--input_dir', '-i', required=True,
                       help='Directory containing DTM files')
    parser.add_argument('--output_file', '-o', 
                       help='Output file for merged DTM')
    parser.add_argument('--crop_to_lidar', 
                       help='Crop DTM to LiDAR extent (provide LiDAR directory)')
    parser.add_argument('--buffer_meters', type=float, default=500.0,
                       help='Buffer around LiDAR extent in meters (default: 500)')
    parser.add_argument('--target_crs',
                       help='Target coordinate reference system (e.g., EPSG:32628)')
    parser.add_argument('--resolution', nargs=2, type=float,
                       help='Target resolution as two floats: x_res y_res')
    parser.add_argument('--resampling', default='bilinear',
                       choices=['nearest', 'bilinear', 'cubic', 'average'],
                       help='Resampling method (default: bilinear)')
    parser.add_argument('--compression', default='LZW',
                       choices=['LZW', 'DEFLATE', 'NONE'],
                       help='Compression method (default: LZW)')
    parser.add_argument('--analyze_only', action='store_true',
                       help='Only analyze files, do not merge')
    parser.add_argument('--validate_output', 
                       help='Validate an existing DTM file')
    parser.add_argument('--save_report',
                       help='Save analysis report to specified file')
    
    args = parser.parse_args()
    
    # Validate output file
    if args.validate_output:
        processor = DTMProcessor(args.input_dir)
        validation = processor.validate_output(args.validate_output)
        
        print("\n" + "="*50)
        print("DTM VALIDATION RESULTS")
        print("="*50)
        print(f"File: {args.validate_output}")
        print(f"Exists: {validation['file_exists']}")
        print(f"Readable: {validation['readable']}")
        print(f"Has CRS: {validation['has_crs']}")
        print(f"File size: {validation['file_size_mb']:.2f} MB")
        if validation['dimensions']:
            print(f"Dimensions: {validation['dimensions'][0]} x {validation['dimensions'][1]}")
        if validation['resolution']:
            print(f"Resolution: {validation['resolution'][0]:.6f} x {validation['resolution'][1]:.6f}")
        if validation['min_elevation'] is not None:
            print(f"Elevation range: {validation['min_elevation']:.2f} to {validation['max_elevation']:.2f} m")
            print(f"Mean elevation: {validation['mean_elevation']:.2f} m")
        
        if validation['issues']:
            print(f"\nIssues found: {len(validation['issues'])}")
            for issue in validation['issues']:
                print(f"  - {issue}")
        else:
            print("\n✅ No issues found")
        
        return
    
    # Initialize processor
    processor = DTMProcessor(args.input_dir, args.output_file)
    
    # Discover and analyze files
    processor.discover_dtm_files()
    analysis = processor.analyze_dtm_files()
    processor.print_analysis_summary()
    
    # Save analysis report if requested
    if args.save_report:
        processor.save_analysis_report(args.save_report)
    
    if args.analyze_only:
        logger.info("Analysis complete. Exiting (analyze_only mode).")
        return
    
    # Determine output file
    if args.crop_to_lidar:
        # Crop to LiDAR extent
        output_file = args.output_file or "dtm_cropped_to_lidar.tif"
        result_file = processor.crop_to_lidar_extent(
            args.crop_to_lidar, 
            output_file, 
            args.buffer_meters
        )
    else:
        # Regular merge
        output_file = args.output_file or "merged_dtm.tif"
        
        # Prepare merge parameters
        resolution = tuple(args.resolution) if args.resolution else None
        
        result_file = processor.merge_dtm_files(
            output_file=output_file,
            target_crs=args.target_crs,
            resolution=resolution,
            resampling_method=args.resampling,
            compression=args.compression
        )
    
    # Validate the result
    logger.info("\nValidating output file...")
    validation = processor.validate_output(result_file)
    
    if validation['issues']:
        logger.warning(f"Validation found {len(validation['issues'])} issues:")
        for issue in validation['issues']:
            logger.warning(f"  - {issue}")
    else:
        logger.info("✅ Output file validation passed")
    
    print(f"\n🎉 DTM processing completed successfully!")
    print(f"📁 Output file: {result_file}")
    print(f"📊 File size: {validation['file_size_mb']:.2f} MB")
    if validation['dimensions']:
        print(f"📐 Dimensions: {validation['dimensions'][0]:,} x {validation['dimensions'][1]:,}")
    if validation['min_elevation'] is not None:
        print(f"🏔️  Elevation range: {validation['min_elevation']:.1f} to {validation['max_elevation']:.1f} m")
    
    print(f"\n📋 Ready for upload to HPC!")


if __name__ == "__main__":
    main() 