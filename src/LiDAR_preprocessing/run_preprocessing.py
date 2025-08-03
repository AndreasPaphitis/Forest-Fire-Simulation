"""
LiDAR Preprocessing Runner

This script coordinates the entire LiDAR preprocessing pipeline:
1. Height normalization
2. NRD calculation
3. PAD calculation

It provides consistent progress reporting, error handling, and configuration management.
"""

import os
import sys
import time
import argparse
from pathlib import Path
import logging
import concurrent.futures
from datetime import datetime
import json
from typing import Dict, Any, Optional, List, Union, Tuple

# Add parent directory to sys.path to enable relative imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import preprocessing modules
from src.LiDAR_preprocessing.preprocessing_config import (
    PreprocessingConfig, get_config_from_args
)
from src.LiDAR_preprocessing.preprocessing_utils import (
    ensure_directory_exists, create_metadata_record, save_metadata, ProgressTracker
)

# Import specific preprocessing functions
from src.LiDAR_preprocessing.height_normalisation_all import process_laz_files
from src.LiDAR_preprocessing.NRD_calculation import process_directory as process_nrd
from src.LiDAR_preprocessing.PAD_calculation import process_directory as process_pad

# Set up logging using the centralized system
logger = get_logger(__name__)
logger.info("LiDAR preprocessing runner initialized")

class PreprocessingPipeline:
    """
    Manages the entire LiDAR preprocessing pipeline.
    """
    
    def __init__(self, config: Optional[PreprocessingConfig] = None):
        """
        Initialize the preprocessing pipeline.
        
        Args:
            config: Preprocessing configuration
        """
        self.config = config or PreprocessingConfig()
        self.results = {
            "start_time": datetime.now().isoformat(),
            "stages": {},
            "end_time": None,
            "total_duration_seconds": None,
            "success": False
        }
    
    def run_height_normalization(self) -> bool:
        """
        Run the height normalization step.
        
        Returns:
            Success status
        """
        config = self.config.height_normalization
        logger.info(f"Starting height normalization from {config.input_dir} to {config.output_dir}")
        stage_start = time.time()
        
        try:
            ensure_directory_exists(config.output_dir)
            
            # Run normalization
            process_laz_files(
                input_dir=config.input_dir,
                output_dir=config.output_dir,
                num_workers=config.num_workers
            )
            
            # Record results
            stage_end = time.time()
            self.results["stages"]["height_normalization"] = {
                "success": True,
                "start_time": datetime.fromtimestamp(stage_start).isoformat(),
                "end_time": datetime.fromtimestamp(stage_end).isoformat(),
                "duration_seconds": stage_end - stage_start,
                "output_dir": str(config.output_dir)
            }
            return True
            
        except Exception as e:
            logger.error(f"Error in height normalization: {e}")
            stage_end = time.time()
            self.results["stages"]["height_normalization"] = {
                "success": False,
                "error": str(e),
                "start_time": datetime.fromtimestamp(stage_start).isoformat(),
                "end_time": datetime.fromtimestamp(stage_end).isoformat(),
                "duration_seconds": stage_end - stage_start
            }
            return False
    
    def run_nrd_calculation(self) -> bool:
        """
        Run the NRD calculation step.
        
        Returns:
            Success status
        """
        config = self.config.nrd
        logger.info(f"Starting NRD calculation from {config.input_dir} to {config.output_dir}")
        stage_start = time.time()
        
        try:
            ensure_directory_exists(config.output_dir)
            
            # Run NRD calculation
            process_nrd(
                input_dir=config.input_dir,
                output_base_dir=config.output_dir,
                bin_size=config.bin_size,
                vegetation_classes=config.vegetation_classes,
                show_cumulative=config.show_cumulative,
                create_rasters=config.create_rasters,
                raster_resolution=config.raster_resolution,
                handle_negative_heights=config.handle_negative_heights,
                filter_negative_heights=config.filter_negative_heights,
                filter_artifacts=config.filter_artifacts,
                filter_method=config.filter_method,
                z_score_threshold=config.z_score_threshold,
                slope_threshold=config.slope_threshold,
                min_valid_height=config.min_valid_height,
                min_points_percent=config.min_points_percent
            )
            
            # Record results
            stage_end = time.time()
            self.results["stages"]["nrd_calculation"] = {
                "success": True,
                "start_time": datetime.fromtimestamp(stage_start).isoformat(),
                "end_time": datetime.fromtimestamp(stage_end).isoformat(),
                "duration_seconds": stage_end - stage_start,
                "output_dir": str(config.output_dir)
            }
            return True
            
        except Exception as e:
            logger.error(f"Error in NRD calculation: {e}")
            stage_end = time.time()
            self.results["stages"]["nrd_calculation"] = {
                "success": False,
                "error": str(e),
                "start_time": datetime.fromtimestamp(stage_start).isoformat(),
                "end_time": datetime.fromtimestamp(stage_end).isoformat(),
                "duration_seconds": stage_end - stage_start
            }
            return False
    
    def run_pad_calculation(self) -> bool:
        """
        Run the PAD calculation step.
        
        Returns:
            Success status
        """
        config = self.config.pad
        logger.info(f"Starting PAD calculation from {config.input_dir} to {config.output_dir}")
        stage_start = time.time()
        
        try:
            ensure_directory_exists(config.output_dir)
            
            # Run PAD calculation
            process_pad(
                input_dir=config.input_dir,
                output_base_dir=config.output_dir,
                extinction_coefficient=config.extinction_coefficient,
                create_visualizations=config.create_visualizations,
                parallel_processing=config.parallel_processing,
                num_workers=config.max_workers
            )
            
            # Record results
            stage_end = time.time()
            self.results["stages"]["pad_calculation"] = {
                "success": True,
                "start_time": datetime.fromtimestamp(stage_start).isoformat(),
                "end_time": datetime.fromtimestamp(stage_end).isoformat(),
                "duration_seconds": stage_end - stage_start,
                "output_dir": str(config.output_dir)
            }
            return True
            
        except Exception as e:
            logger.error(f"Error in PAD calculation: {e}")
            stage_end = time.time()
            self.results["stages"]["pad_calculation"] = {
                "success": False,
                "error": str(e),
                "start_time": datetime.fromtimestamp(stage_start).isoformat(),
                "end_time": datetime.fromtimestamp(stage_end).isoformat(),
                "duration_seconds": stage_end - stage_start
            }
            return False
    
    def run_full_pipeline(self, skip_completed: bool = False) -> Dict[str, Any]:
        """
        Run the complete preprocessing pipeline.
        
        Args:
            skip_completed: Whether to skip steps that have already completed
            
        Returns:
            Dictionary of results
        """
        pipeline_start = time.time()
        logger.info("Starting full LiDAR preprocessing pipeline")
        overall_success = True
        
        # Step 1: Height normalization
        if not skip_completed or "height_normalization" not in self.results["stages"]:
            height_success = self.run_height_normalization()
            if not height_success:
                logger.warning("Height normalization failed, but continuing with pipeline")
                overall_success = False
                
            # If normalization succeeded, set the output as input for NRD
            if height_success and not self.config.nrd.input_dir:
                logger.info("Setting NRD input to height normalization output")
                vegetation_dir = os.path.join(self.config.height_normalization.output_dir, "vegetation")
                if os.path.exists(vegetation_dir):
                    self.config.nrd.input_dir = vegetation_dir
                else:
                    self.config.nrd.input_dir = self.config.height_normalization.output_dir
        
        # Step 2: NRD calculation
        if not skip_completed or "nrd_calculation" not in self.results["stages"]:
            nrd_success = self.run_nrd_calculation()
            if not nrd_success:
                logger.warning("NRD calculation failed, but continuing with pipeline")
                overall_success = False
                
            # If NRD succeeded, set the output as input for PAD
            if nrd_success and not self.config.pad.input_dir:
                logger.info("Setting PAD input to NRD output")
                self.config.pad.input_dir = self.config.nrd.output_dir
                
        # Step 3: PAD calculation
        if not skip_completed or "pad_calculation" not in self.results["stages"]:
            pad_success = self.run_pad_calculation()
            if not pad_success:
                logger.warning("PAD calculation failed")
                overall_success = False
        
        # Record overall results
        pipeline_end = time.time()
        self.results["end_time"] = datetime.now().isoformat()
        self.results["total_duration_seconds"] = pipeline_end - pipeline_start
        self.results["success"] = overall_success
        
        # Log completion message
        duration_minutes = (pipeline_end - pipeline_start) / 60
        if overall_success:
            logger.info(f"Full preprocessing pipeline completed successfully in {duration_minutes:.2f} minutes")
        else:
            logger.warning(f"Preprocessing pipeline completed with errors in {duration_minutes:.2f} minutes")
        
        return self.results
    
    def save_results(self, output_path: Union[str, Path]) -> None:
        """
        Save pipeline results to a JSON file.
        
        Args:
            output_path: Path to save the results
        """
        with open(output_path, 'w') as f:
            json.dump(self.results, f, indent=4)
        logger.info(f"Pipeline results saved to {output_path}")

def setup_argparse() -> argparse.ArgumentParser:
    """Set up command line argument parsing."""
    parser = argparse.ArgumentParser(description='LiDAR Preprocessing Pipeline Runner')
    
    # Basic arguments
    parser.add_argument('--config', type=str, help='Path to configuration file')
    parser.add_argument('--output_report', type=str, default='preprocessing_results.json',
                        help='Path to save pipeline results')
    parser.add_argument('--skip_completed', action='store_true',
                        help='Skip steps that have already completed')
    
    # Pipeline stages
    parser.add_argument('--height_norm_only', action='store_true',
                        help='Only run height normalization')
    parser.add_argument('--nrd_only', action='store_true',
                        help='Only run NRD calculation')
    parser.add_argument('--pad_only', action='store_true',
                        help='Only run PAD calculation')
    
    # Add all the config arguments from preprocessing_config
    parser.add_argument('--workers', type=int, help='Number of parallel workers')
    parser.add_argument('--bin_size', type=float, help='Vertical bin size in meters')
    
    # Height normalization arguments
    parser.add_argument('--input_dir', type=str, help='Input directory for height normalization')
    parser.add_argument('--output_dir', type=str, help='Output directory for height normalization')
    
    # NRD calculation arguments
    parser.add_argument('--nrd_input', type=str, help='Input directory for NRD calculation')
    parser.add_argument('--nrd_output', type=str, help='Output directory for NRD results')
    parser.add_argument('--raster_resolution', type=float, help='Raster resolution in meters')
    
    # PAD calculation arguments
    parser.add_argument('--pad_input', type=str, help='Input directory for PAD calculation')
    parser.add_argument('--pad_output', type=str, help='Output directory for PAD results')
    parser.add_argument('--extinction_coefficient', type=float,
                        help='Extinction coefficient for PAD calculation')
    
    return parser

def main():
    """Main entry point for the script."""
    parser = setup_argparse()
    args = parser.parse_args()
    
    # Get configuration
    try:
        config = get_config_from_args()
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return 1
    
    # Create pipeline
    pipeline = PreprocessingPipeline(config)
    
    # Determine which steps to run
    if args.height_norm_only:
        logger.info("Running height normalization only")
        success = pipeline.run_height_normalization()
    elif args.nrd_only:
        logger.info("Running NRD calculation only")
        success = pipeline.run_nrd_calculation()
    elif args.pad_only:
        logger.info("Running PAD calculation only")
        success = pipeline.run_pad_calculation()
    else:
        logger.info("Running full preprocessing pipeline")
        pipeline.run_full_pipeline(skip_completed=args.skip_completed)
        success = pipeline.results["success"]
    
    # Save results
    try:
        pipeline.save_results(args.output_report)
    except Exception as e:
        logger.error(f"Error saving results: {e}")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 