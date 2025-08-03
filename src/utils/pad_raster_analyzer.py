#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PAD Raster Analysis Utility

This script analyzes Plant Area Density (PAD) raster datasets and provides 
detailed information about the structure, size, and memory requirements.

It specifically addresses issues where PAD raster tiles might be incorrectly
treated as separate grids rather than as parts of a single unified grid.

Usage:
    python pad_raster_analyzer.py <lidar_data_dir> [--check-memory]
"""

import os
import sys
import logging
import argparse
from pathlib import Path
from typing import Dict, Any, Optional, Union, Tuple
import re
import math

# Try to import from known location first, then fallback to path manipulation
try:
    from src.utils.lidar_utils import RasterTileManager, LiDARDataManager
except ImportError:
    # Add the parent directory to sys.path to find the modules
    parent_dir = str(Path(__file__).resolve().parent.parent.parent)
    if parent_dir not in sys.path:
        sys.path.append(parent_dir)
    
    try:
        from src.utils.lidar_utils import RasterTileManager, LiDARDataManager
    except ImportError:
        print("ERROR: Could not import the required modules. Make sure you are running this script from the project root directory.")
        sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger("PAD_Analyzer")

def format_size(bytes_size: float) -> str:
    """Format bytes into a human-readable format."""
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    unit_index = 0
    
    while bytes_size >= 1024 and unit_index < len(units) - 1:
        bytes_size /= 1024
        unit_index += 1
    
    return f"{bytes_size:.2f} {units[unit_index]}"

def analyze_pad_structure(data_dir: Union[str, Path], check_memory: bool = False) -> Dict[str, Any]:
    """
    Analyze the structure of PAD raster data.
    
    Args:
        data_dir: Directory containing PAD raster data
        check_memory: Whether to check the memory requirements
        
    Returns:
        Dictionary with analysis results
    """
    data_dir_path = Path(data_dir)
    if not data_dir_path.exists():
        logger.error(f"Directory does not exist: {data_dir_path}")
        return {"error": f"Directory does not exist: {data_dir_path}"}
    
    results = {
        "directory": str(data_dir_path),
        "structure": {
            "exists": True,
            "is_pad_dataset": False,
            "has_layer_dirs": False,
            "total_files": 0,
        },
        "dimensions": {
            "combined_grid_size": (0, 0),
            "total_layers": 0,
            "tiles": {
                "count": 0,
                "avg_size": (0, 0),
            }
        },
        "memory": {}
    }
    
    logger.info(f"Analyzing PAD raster data in: {data_dir_path}")
    
    # Check for PAD structure (either direct rasters or in a 'pad' subdirectory)
    pad_dir = data_dir_path / 'pad' if (data_dir_path / 'pad').exists() else data_dir_path
    
    # Check for layer directories
    has_layer_dirs = any(d.is_dir() and not d.name.startswith('.') for d in pad_dir.iterdir())
    results["structure"]["has_layer_dirs"] = has_layer_dirs
    
    # Check for raster files
    has_raster_files = any(p.suffix.lower() in ('.tif', '.tiff') for p in pad_dir.glob('**/*.*'))
    results["structure"]["is_pad_dataset"] = has_raster_files
    
    if not has_raster_files:
        logger.warning(f"No raster files found in {pad_dir}")
        return results
    
    logger.info("PAD raster dataset detected")
    
    # Create the RasterTileManager to analyze the dataset
    try:
        tile_manager = RasterTileManager(
            base_dir=pad_dir,
            layer_subdirs=has_layer_dirs,
            logger_name="PAD_Analyzer"
        )
        
        # Get summary information from the tile manager
        summary = tile_manager.summarize()
        
        # Populate results from summary
        results["dimensions"]["combined_grid_size"] = summary["combined_grid_size"]
        results["dimensions"]["total_layers"] = summary["layer_count"]
        results["dimensions"]["tiles"]["count"] = summary["total_tiles"]
        results["dimensions"]["tiles"]["avg_size"] = summary["average_tile_size"]
        
        # Add layer-specific information
        results["layers"] = {}
        for layer, tiles in summary.get("tiles_per_layer", {}).items():
            results["layers"][f"layer_{layer}"] = {
                "tile_count": tiles
            }
    except Exception as e:
        logger.warning(f"Error creating RasterTileManager: {e}")
        logger.warning("Using fallback method for analyzing dataset structure")
        
        # Fallback: Manual file counting and structure analysis
        layers = {}
        total_files = 0
        avg_width = 0
        avg_height = 0
        file_dimensions = {}
        
        # Scan for files and extract information from filenames or content
        for layer_dir in [d for d in pad_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]:
            layer_name = layer_dir.name
            layer_num = int(layer_name.split('_')[-1]) if '_' in layer_name else len(layers)
            
            # Count files in this layer
            tif_files = list(layer_dir.glob('*.tif')) + list(layer_dir.glob('*.tiff'))
            file_count = len(tif_files)
            total_files += file_count
            
            layers[layer_num] = {"tile_count": file_count}
            
            # Try to get dimensions from filenames or file content
            for tif_file in tif_files:
                try:
                    # Try reading the file as text to extract dimensions
                    with open(tif_file, 'r') as f:
                        content = f.read()
                        width_match = re.search(r'Width:\s*(\d+)', content)
                        height_match = re.search(r'Height:\s*(\d+)', content)
                        
                        if width_match and height_match:
                            width = int(width_match.group(1))
                            height = int(height_match.group(1))
                            file_dimensions[str(tif_file)] = (width, height)
                            avg_width += width
                            avg_height += height
                except Exception as e:
                    logger.debug(f"Could not read dimensions from {tif_file}: {e}")
                    # Default dimensions if can't be determined
                    file_dimensions[str(tif_file)] = (100, 100)
                    avg_width += 100
                    avg_height += 100
        
        # Calculate average dimensions
        if total_files > 0:
            avg_width /= total_files
            avg_height /= total_files
        
        # Estimate combined grid size based on layer structure and file count
        if layers:
            # Assuming tiles are arranged in a square-ish grid
            tiles_per_layer = total_files / len(layers) if len(layers) > 0 else 0
            grid_side = math.ceil(math.sqrt(tiles_per_layer))
            combined_width = int(grid_side * avg_width)
            combined_height = int(grid_side * avg_height)
            
            results["dimensions"]["combined_grid_size"] = (combined_width, combined_height)
            results["dimensions"]["total_layers"] = len(layers)
            results["dimensions"]["tiles"]["count"] = total_files
            results["dimensions"]["tiles"]["avg_size"] = (int(avg_width), int(avg_height))
            results["layers"] = {f"layer_{k}": v for k, v in layers.items()}
        
    # Calculate memory requirements
    if check_memory or results["dimensions"]["combined_grid_size"][0] * results["dimensions"]["combined_grid_size"][1] > 0:
        width, height = results["dimensions"]["combined_grid_size"]
        layers = results["dimensions"]["total_layers"]
        
        if width > 0 and height > 0 and layers > 0:
            for bytes_per_cell in [4, 8, 16]:
                cells = width * height * layers
                bytes_total = cells * bytes_per_cell
                mb_total = bytes_total / (1024 * 1024)
                
                results["memory"][f"bytes_per_cell_{bytes_per_cell}"] = {
                    "total_cells": cells,
                    "total_bytes": bytes_total,
                    "total_mb": mb_total,
                    "human_readable": format_size(bytes_total)
                }
    
    # Additional warnings and insights
    if results["dimensions"]["combined_grid_size"][0] > 2000 or results["dimensions"]["combined_grid_size"][1] > 2000:
        logger.warning(f"Combined grid size ({results['dimensions']['combined_grid_size']}) exceeds recommended maximum (2000).")
        logger.warning("Consider downsampling or adjusting the target resolution.")
        results["warnings"] = results.get("warnings", []) + [
            f"Grid size {results['dimensions']['combined_grid_size']} exceeds recommended maximum (2000x2000)."
        ]
    
    if "memory" in results and "bytes_per_cell_8" in results["memory"] and results["memory"]["bytes_per_cell_8"]["total_mb"] > 8000:
        logger.warning(f"Estimated memory usage ({results['memory']['bytes_per_cell_8']['total_mb']:.2f} MB) exceeds 8 GB.")
        logger.warning("Consider enabling tiling and disk storage for processing.")
        results["warnings"] = results.get("warnings", []) + [
            f"High memory usage ({results['memory']['bytes_per_cell_8']['total_mb']:.2f} MB) may cause performance issues."
        ]
    
    # Visualization for multi-tile and multi-layer structure
    results["visualization"] = {}
    if results["dimensions"]["total_layers"] > 1:
        grid_width, grid_height = results["dimensions"]["combined_grid_size"]
        if grid_width > 0 and grid_height > 0:
            # Create a very simple text-based visualization
            text_repr = []
            text_repr.append(f"Grid: {grid_width}x{grid_height}, {results['dimensions']['total_layers']} layers")
            text_repr.append("Schematic: Each 'L' represents a layer")
            
            layer_repr = "".join([f"L{l}" for l in range(results["dimensions"]["total_layers"])])
            text_repr.append(f"[{layer_repr}] x ({grid_width}x{grid_height}) cells")
            
            results["visualization"]["text"] = text_repr
    
    return results

def main():
    parser = argparse.ArgumentParser(description="Analyze PAD raster datasets")
    parser.add_argument("data_dir", help="Directory containing PAD raster data")
    parser.add_argument("--check-memory", action="store_true", help="Calculate and report memory requirements")
    parser.add_argument("--output", help="Output file for JSON results")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    
    args = parser.parse_args()
    
    # Analyze the PAD dataset
    results = analyze_pad_structure(args.data_dir, args.check_memory)
    
    # Print analysis results
    width, height = results["dimensions"]["combined_grid_size"]
    total_cells = width * height * results["dimensions"]["total_layers"]
    logger.info("=" * 80)
    logger.info(f"PAD Raster Analysis Results")
    logger.info("=" * 80)
    logger.info(f"Directory: {results['directory']}")
    logger.info(f"Structure: {results['structure']}")
    logger.info(f"Combined Grid Size: {width}x{height} cells")
    logger.info(f"Total Layers: {results['dimensions']['total_layers']}")
    logger.info(f"Total Tiles: {results['dimensions']['tiles']['count']}")
    logger.info(f"Total Cells: {total_cells:,}")
    
    if args.check_memory and "memory" in results:
        logger.info("Memory Requirements:")
        for k, v in results["memory"].items():
            if "human_readable" in v:
                logger.info(f"  {k}: {v['human_readable']}")
    
    if "warnings" in results:
        logger.info("Warnings:")
        for warning in results["warnings"]:
            logger.info(f"  - {warning}")
    
    # Save to output file if specified
    if args.output:
        import json
        try:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2)
            logger.info(f"Results saved to {args.output}")
        except Exception as e:
            logger.error(f"Error saving results to {args.output}: {e}")
    
    logger.info("PAD Raster Analyzer - Analysis complete.")
    logger.info(f"Processed {len(tif_files)} PAD raster files.")
    logger.info(f"Results saved to: {args.output}")
    
    return results

if __name__ == "__main__":
    main() 