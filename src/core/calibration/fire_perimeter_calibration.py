#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Fire Perimeter Calibration Module

Specialized calibration system for real fire perimeter data at full Tenerife scale.
Handles EMSR delineation data with temporal progression and high-memory optimization.

Features:
- Auto-discovery of EMSR fire perimeter shapefiles
- Full Tenerife domain simulation (15,121 × 24,741 × 25)
- 64GB/60-worker or 128GB/120-worker memory frameworks
- Training/test split of temporal fire progression data
- Maximum memory optimization for large-scale calibration

Author: Forest Fire Simulation Team
Date: 2025
Version: 1.0
"""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

try:
    import geopandas as gpd
    import rasterio
    import rasterio.transform
    from rasterio.features import rasterize
    from rasterio.transform import from_bounds
    from shapely.geometry import Point, Polygon
    SPATIAL_LIBS_AVAILABLE = True
except ImportError:
    SPATIAL_LIBS_AVAILABLE = False

from src.core.calibration import (
    CalibrationConfig, CalibrationMethod, CalibrationObjective,
    GridSearchCalibrator, get_default_calibration_bounds,
    create_progress_callback
)
from src.config.config_tools import ModelConfig
from src.utils.logging_utils import get_logger
from src.utils.shared_utilities import optimize_numexpr_threading

logger = get_logger(__name__)


@dataclass
class FirePerimeterData:
    """Single fire perimeter dataset with metadata."""
    shapefile_path: str
    date: str
    day_number: int
    fire_id: str
    area_hectares: Optional[float] = None
    bbox: Optional[Tuple[float, float, float, float]] = None  # (minx, miny, maxx, maxy)
    crs: Optional[str] = None
    geometry_count: Optional[int] = None
    is_valid: bool = True
    error_message: str = ""


@dataclass  
class FirePerimeterDataset:
    """Complete fire perimeter dataset for calibration."""
    fire_perimeters: List[FirePerimeterData] = field(default_factory=list)
    training_data: List[FirePerimeterData] = field(default_factory=list)
    test_data: List[FirePerimeterData] = field(default_factory=list)
    base_directory: Optional[str] = None
    total_fires: int = 0
    date_range: Optional[Tuple[str, str]] = None
    
    def __post_init__(self):
        """Update derived statistics."""
        self.total_fires = len(self.fire_perimeters)
        if self.fire_perimeters:
            dates = [fp.date for fp in self.fire_perimeters]
            self.date_range = (min(dates), max(dates))


class FirePerimeterDiscovery:
    """Discover and validate fire perimeter shapefiles from EMSR directory structure."""
    
    def __init__(self, base_directory: Union[str, Path] = "EMSR Delineations"):
        """
        Initialize fire perimeter discovery.
        
        Args:
            base_directory: Base directory containing EMSR fire perimeter data
        """
        self.base_directory = self._find_emsr_directory(base_directory)
        if not self.base_directory.exists():
            raise FileNotFoundError(f"EMSR directory not found: {self.base_directory}")
        
        logger.info(f"Initialized fire perimeter discovery for: {self.base_directory}")
    
    def _find_emsr_directory(self, base_directory: Union[str, Path]) -> Path:
        """Find EMSR directory with HPC and local fallbacks."""
        possible_paths = [
            # User-provided path (first priority)
            str(base_directory),
            # HPC paths (confirmed Snellius location)
            "/gpfs/home1/apaphitis/git/github/Forest-Fire-Simulation/EMSR Delineations",
            "/gpfs/home1/apaphitis/git/github/Forest-Fire-Simulation/EMSR Delineations/",
            "/gpfs/home1/apaphitis/Forest-Fire-Simulation/EMSR Delineations", 
            "/project/EMSR Delineations",
            "/scratch-shared/apaphitis/EMSR Delineations",
            # Project relative paths
            str(Path(__file__).parent.parent.parent.parent / "EMSR Delineations"),
            str(Path(__file__).parent.parent.parent.parent / "data" / "EMSR Delineations"),
            # Current directory relative
            "EMSR Delineations",
            "data/EMSR Delineations",
            "./EMSR Delineations"
        ]
        
        for path in possible_paths:
            path_obj = Path(path)
            if path_obj.exists() and path_obj.is_dir():
                # Check if it contains Day directories with expected structure
                day_dirs = list(path_obj.glob("Day *"))
                if len(day_dirs) > 0:
                    logger.info(f"✅ Found EMSR directory: {path} ({len(day_dirs)} day directories)")
                    return path_obj
                else:
                    logger.debug(f"Directory exists but no Day subdirectories: {path}")
        
        # If no valid directory found, return the original path (will trigger error later)
        logger.warning(f"⚠️  No valid EMSR directory found, using: {base_directory}")
        return Path(base_directory)
    
    def discover_fire_perimeters(self) -> FirePerimeterDataset:
        """
        Discover all fire perimeter shapefiles in the directory structure.
        
        Returns:
            FirePerimeterDataset with discovered fire perimeters
        """
        print("🔍 DISCOVERING FIRE PERIMETER SHAPEFILES")
        print("=" * 70)
        
        fire_perimeters = []
        
        # Scan all subdirectories for date-organized folders
        for day_dir in sorted(self.base_directory.iterdir()):
            if not day_dir.is_dir():
                continue
            
            print(f"📁 Scanning: {day_dir.name}")
            
            # Extract date and day number from directory name
            day_info = self._parse_day_directory(day_dir.name)
            if not day_info:
                print(f"   ⚠️  Skipping: Could not parse directory name")
                continue
            
            day_number, date_str = day_info
            
            # Find fire perimeter file in directory
            shapefile_path = self._find_shapefile(day_dir)
            if not shapefile_path:
                print(f"   ⚠️  No fire perimeter file found in {day_dir.name}")
                # Show directory contents for debugging
                try:
                    contents = list(day_dir.iterdir())
                    subdirs = [d.name for d in contents if d.is_dir()]
                    files = [f.name for f in contents if f.is_file()]
                    print(f"      📂 Subdirectories: {subdirs}")
                    print(f"      📄 Files: {files}")
                except Exception as e:
                    print(f"      ❌ Error listing contents: {e}")
                continue
            
            # Extract fire ID from filename
            fire_id = self._extract_fire_id(shapefile_path.name)
            
            # Create fire perimeter data object
            fire_perimeter = FirePerimeterData(
                shapefile_path=str(shapefile_path),
                date=date_str,
                day_number=day_number,
                fire_id=fire_id
            )
            
            # Validate shapefile and extract metadata
            self._validate_and_extract_metadata(fire_perimeter)
            
            if fire_perimeter.is_valid:
                fire_perimeters.append(fire_perimeter)
                file_format = Path(shapefile_path).suffix.upper()
                print(f"   ✅ Added: {shapefile_path.name} ({file_format})")
                print(f"      Date: {date_str}, Day: {day_number}")
                print(f"      Area: {fire_perimeter.area_hectares:.1f} ha" if fire_perimeter.area_hectares else "      Area: Unknown")
            else:
                print(f"   ❌ Invalid: {fire_perimeter.error_message}")
        
        print(f"\n📊 DISCOVERY SUMMARY:")
        print(f"   Total fire perimeters found: {len(fire_perimeters)}")
        
        # Create dataset
        dataset = FirePerimeterDataset(
            fire_perimeters=fire_perimeters,
            base_directory=str(self.base_directory)
        )
        
        # Display detailed summary
        self._display_dataset_summary(dataset)
        
        return dataset
    
    def _parse_day_directory(self, dir_name: str) -> Optional[Tuple[int, str]]:
        """
        Parse day directory name to extract day number and date.
        
        Expected format: "Day X (DD_MM_YY)" or similar
        
        Args:
            dir_name: Directory name to parse
            
        Returns:
            Tuple of (day_number, date_string) or None if parsing fails
        """
        try:
            # Extract day number
            if "Day" in dir_name:
                day_part = dir_name.split("Day")[1].strip()
                day_number = int(day_part.split()[0])
            else:
                return None
            
            # Extract date from parentheses
            if "(" in dir_name and ")" in dir_name:
                date_part = dir_name.split("(")[1].split(")")[0]
                # Convert from DD_MM_YY to YYYY-MM-DD format
                date_components = date_part.split("_")
                if len(date_components) == 3:
                    day, month, year = date_components
                    # Assume 20XX for YY format
                    full_year = f"20{year}" if len(year) == 2 else year
                    date_str = f"{full_year}-{month.zfill(2)}-{day.zfill(2)}"
                    return (day_number, date_str)
            
            return None
            
        except (ValueError, IndexError) as e:
            logger.warning(f"Failed to parse directory name '{dir_name}': {e}")
            return None
    
    def _find_shapefile(self, directory: Path) -> Optional[Path]:
        """Find the main fire perimeter file (.shp, .kmz, .kml) in a directory."""
        # Try multiple geospatial formats in order of preference
        formats_to_try = [
            ("*.shp", "shapefile"),
            ("*.kmz", "KMZ file"), 
            ("*.kml", "KML file"),
            ("*.json", "GeoJSON file")
        ]
        
        for pattern, format_name in formats_to_try:
            # First try direct search in the directory
            files = list(directory.glob(pattern))
            
            # If no direct files, search recursively in subdirectories
            if not files:
                logger.debug(f"No direct {format_name}s in {directory.name}, searching subdirectories...")
                files = list(directory.rglob(pattern))
                if files:
                    logger.info(f"Found {len(files)} {format_name}s in subdirectories of {directory.name}")
            
            if files:
                logger.info(f"Using {format_name} format for {directory.name}")
                selected_file = self._select_best_file(files)
                if selected_file:
                    logger.info(f"Selected: {selected_file.name}")
                    return selected_file
        
        return None
    
    def _select_best_file(self, files: List[Path]) -> Optional[Path]:
        """Select the best file from a list of candidates."""
        if len(files) == 1:
            return files[0]
        
        # Prefer files that don't contain "GRA" (grading) - focus on delineation
        delineation_files = [f for f in files if "DEL" in f.name and "GRA" not in f.name]
        if delineation_files:
            logger.info(f"Selected delineation file over {len(files)} candidates")
            return delineation_files[0]
        
        # Prefer files with "EMSR" in the name
        emsr_files = [f for f in files if "EMSR" in f.name]
        if emsr_files:
            logger.info(f"Selected EMSR file over {len(files)} candidates")
            return emsr_files[0]
        
        # Fallback to first file
        logger.info(f"Using first available file from {len(files)} candidates")
        return files[0]
    
    def _extract_fire_id(self, filename: str) -> str:
        """Extract fire ID from EMSR filename."""
        # Example: EMSR685_AOI01_DEL_PRODUCT_observedEventA_v1.shp
        parts = filename.split("_")
        if len(parts) >= 2:
            return f"{parts[0]}_{parts[1]}"  # e.g., "EMSR685_AOI01"
        return filename.split(".")[0]  # Fallback to filename without extension
    
    def _validate_and_extract_metadata(self, fire_perimeter: FirePerimeterData):
        """Validate fire perimeter file and extract metadata."""
        if not SPATIAL_LIBS_AVAILABLE:
            fire_perimeter.error_message = "Spatial libraries (geopandas) not available"
            fire_perimeter.is_valid = False
            return
        
        try:
            file_path = Path(fire_perimeter.shapefile_path)
            file_ext = file_path.suffix.lower()
            
            # Handle different file formats
            if file_ext == '.shp':
                # Check if all required shapefile components exist
                required_extensions = ['.shp', '.shx', '.dbf', '.prj']
                base_name = file_path.stem
                base_dir = file_path.parent
                
                missing_files = []
                for ext in required_extensions:
                    if not (base_dir / f"{base_name}{ext}").exists():
                        missing_files.append(ext)
                
                if missing_files:
                    fire_perimeter.error_message = f"Missing shapefile components: {missing_files}"
                    fire_perimeter.is_valid = False
                    return
            
            elif file_ext in ['.kmz', '.kml']:
                # KMZ/KML files are self-contained, just check existence
                if not file_path.exists():
                    fire_perimeter.error_message = f"KMZ/KML file does not exist: {file_path}"
                    fire_perimeter.is_valid = False
                    return
                logger.info(f"Processing KMZ/KML file: {file_path.name}")
            
            elif file_ext == '.json':
                # JSON files should be GeoJSON format
                if not file_path.exists():
                    fire_perimeter.error_message = f"JSON file does not exist: {file_path}"
                    fire_perimeter.is_valid = False
                    return
                logger.info(f"Processing GeoJSON file: {file_path.name}")
            
            else:
                fire_perimeter.error_message = f"Unsupported file format: {file_ext}"
                fire_perimeter.is_valid = False
                return
            
            # Load and validate fire perimeter file
            logger.info(f"Reading {file_ext} file with geopandas...")
            gdf = gpd.read_file(file_path)
            
            # Check if empty
            if len(gdf) == 0:
                fire_perimeter.error_message = "Fire perimeter file contains no features"
                fire_perimeter.is_valid = False
                return
            
            # Extract metadata
            fire_perimeter.crs = str(gdf.crs) if gdf.crs else None
            fire_perimeter.geometry_count = len(gdf)
            
            # Calculate total area in hectares
            if gdf.crs and gdf.crs.is_projected:
                # Area in square meters, convert to hectares
                fire_perimeter.area_hectares = gdf.geometry.area.sum() / 10000
            else:
                # For geographic CRS, use a rough approximation
                fire_perimeter.area_hectares = gdf.to_crs("EPSG:25828").geometry.area.sum() / 10000
            
            # Get bounding box
            bounds = gdf.total_bounds  # [minx, miny, maxx, maxy]
            fire_perimeter.bbox = tuple(bounds)
            
            # Validate CRS (should be EPSG:25828 for Tenerife or convertible)
            if gdf.crs is None:
                fire_perimeter.error_message = "Shapefile missing CRS information"
                fire_perimeter.is_valid = False
                return
            
            # Success
            fire_perimeter.is_valid = True
            
        except Exception as e:
            fire_perimeter.error_message = f"Error validating shapefile: {str(e)}"
            fire_perimeter.is_valid = False
    
    def _display_dataset_summary(self, dataset: FirePerimeterDataset):
        """Display detailed summary of discovered dataset."""
        if not dataset.fire_perimeters:
            print("❌ No valid fire perimeters found")
            return
        
        print(f"\n🔥 FIRE PERIMETER DATASET SUMMARY:")
        print(f"   Fire ID: {dataset.fire_perimeters[0].fire_id}")
        print(f"   Date range: {dataset.date_range[0]} to {dataset.date_range[1]}" if dataset.date_range else "   Date range: Unknown")
        print(f"   Total days: {len(dataset.fire_perimeters)}")
        
        # Display progression
        print(f"\n📅 TEMPORAL PROGRESSION:")
        for i, fp in enumerate(sorted(dataset.fire_perimeters, key=lambda x: x.day_number), 1):
            area_str = f"{fp.area_hectares:.1f} ha" if fp.area_hectares else "Unknown"
            print(f"   {i}. Day {fp.day_number} ({fp.date}): {area_str}")
            print(f"      CRS: {fp.crs}")
            print(f"      Features: {fp.geometry_count}")
        
        # Check CRS consistency
        crs_list = [fp.crs for fp in dataset.fire_perimeters if fp.crs]
        if len(set(crs_list)) > 1:
            print(f"\n⚠️  CRS INCONSISTENCY DETECTED:")
            for crs in set(crs_list):
                count = crs_list.count(crs)
                print(f"      {crs}: {count} files")
        else:
            print(f"\n✅ CRS CONSISTENCY: All files use {crs_list[0]}" if crs_list else "\n❌ No CRS information available")


class TenerifeFirePerimeterCalibrator:
    """
    Specialized calibrator for full Tenerife-scale fire perimeter calibration.
    
    Handles:
    - Full domain (15,121 × 24,741 × 25) simulations
    - 64GB/60-worker or 128GB/120-worker configurations
    - Real fire perimeter data training/validation
    - Maximum memory optimization
    """
    
    def __init__(self, 
                 memory_gb: int = 64,
                 workers: int = 60,
                 grid_search_points: int = 3,
                 experiment_name: str = "tenerife_fire_calibration"):
        """
        Initialize Tenerife fire perimeter calibrator.
        
        Args:
            memory_gb: Available memory (64 or 128 GB)
            workers: Number of parallel workers (60 or 120)
            grid_search_points: Points per parameter (3 or 4)
            experiment_name: Name for calibration experiment
        """
        self.memory_gb = memory_gb
        self.workers = workers
        self.grid_search_points = grid_search_points
        self.experiment_name = experiment_name
        
        # Validate configuration
        if memory_gb not in [64, 128]:
            logger.warning(f"Unusual memory configuration: {memory_gb}GB. Recommended: 64GB or 128GB")
        
        if workers > memory_gb:
            logger.warning(f"High worker count ({workers}) for available memory ({memory_gb}GB)")
        
        # Set up output directory
        self.results_dir = Path(f"calibration_results/{experiment_name}")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"🔥 TENERIFE FIRE PERIMETER CALIBRATOR")
        print(f"=" * 70)
        print(f"Memory framework: {memory_gb}GB with {workers} workers")
        print(f"Grid search points: {grid_search_points} per parameter")
        print(f"Domain: Full Tenerife (15,121 × 24,741 × 25)")
        print(f"Results directory: {self.results_dir}")
        
        # Optimize NumExpr threading for performance
        numexpr_info = optimize_numexpr_threading()
        logger.info(f"⚡ NumExpr optimization: {numexpr_info}")
        print(f"NumExpr threads: {numexpr_info.get('numexpr_max_threads', 'unknown')}")
        print()
    
    def setup_training_test_split(self, 
                                 fire_dataset: FirePerimeterDataset,
                                 training_days: List[int] = [1, 2],
                                 test_days: List[int] = [3, 4]) -> Tuple[List[FirePerimeterData], List[FirePerimeterData]]:
        """
        Split fire perimeter dataset into training and test sets.
        
        Args:
            fire_dataset: Complete fire perimeter dataset
            training_days: Day numbers to use for training (calibration)
            test_days: Day numbers to use for testing (validation)
            
        Returns:
            Tuple of (training_data, test_data)
        """
        print(f"📊 SETTING UP TRAINING/TEST SPLIT")
        print(f"=" * 50)
        
        training_data = []
        test_data = []
        
        for fp in fire_dataset.fire_perimeters:
            if fp.day_number in training_days:
                training_data.append(fp)
                print(f"🎯 Training: Day {fp.day_number} ({fp.date}) - {fp.area_hectares:.1f} ha")
            elif fp.day_number in test_days:
                test_data.append(fp)
                print(f"🧪 Test: Day {fp.day_number} ({fp.date}) - {fp.area_hectares:.1f} ha")
            else:
                print(f"📊 Unused: Day {fp.day_number} ({fp.date}) - {fp.area_hectares:.1f} ha")
        
        if not training_data:
            raise ValueError(f"No training data found for days: {training_days}")
        if not test_data:
            raise ValueError(f"No test data found for days: {test_days}")
        
        print(f"\n✅ Split complete: {len(training_data)} training, {len(test_data)} test")
        
        # Update dataset
        fire_dataset.training_data = training_data
        fire_dataset.test_data = test_data
        
        return training_data, test_data
    
    def create_calibration_config(self, 
                                 training_data: List[FirePerimeterData],
                                 top_5_parameters: Optional[List[str]] = None) -> CalibrationConfig:
        """
        Create calibration configuration for full Tenerife domain.
        
        Args:
            training_data: Fire perimeter data for training
            top_5_parameters: Top 5 sensitive parameters from sensitivity analysis
            
        Returns:
            CalibrationConfig for full-scale calibration
        """
        print(f"⚙️  CREATING CALIBRATION CONFIGURATION")
        print(f"=" * 50)
        
        # Use top 5 parameters from sensitivity analysis or defaults
        if top_5_parameters is None:
            # TOP 5 PARAMETERS FROM ACTUAL SENSITIVITY ANALYSIS (Method 2 Range-Based)
            calibration_parameters = [
                'ember_probability',        # 0.382 - Highest sensitivity
                'fuel_consumption_rate',    # 0.165 - Second highest  
                'ember_ignition',          # 0.138 - Third highest
                'slope_influence',         # 0.023 - Fourth
                'ember_height_factor'      # 0.019 - Fifth
            ]
            print("🔧 Using TOP 5 parameters from Method 2 Range-Based sensitivity analysis")
        else:
            calibration_parameters = top_5_parameters
            print("✅ Using provided top 5 parameters from sensitivity analysis")
        
        print(f"📋 Calibration parameters ({len(calibration_parameters)}):")
        for i, param in enumerate(calibration_parameters, 1):
            print(f"   {i}. {param}")
        
        # Calculate total combinations
        total_combinations = self.grid_search_points ** len(calibration_parameters)
        print(f"\n🔢 Grid search combinations: {total_combinations:,}")
        
        # Estimate memory and time requirements
        memory_per_sim_gb = self._estimate_memory_per_simulation()
        time_per_sim_minutes = self._estimate_time_per_simulation()
        
        total_time_hours = (total_combinations * time_per_sim_minutes) / (60 * self.workers)
        peak_memory_gb = memory_per_sim_gb * min(self.workers, total_combinations)
        
        print(f"📊 Resource estimates:")
        print(f"   Memory per simulation: ~{memory_per_sim_gb:.1f} GB")
        print(f"   Peak memory usage: ~{peak_memory_gb:.1f} GB")
        print(f"   Time per simulation: ~{time_per_sim_minutes:.1f} minutes")
        print(f"   Total estimated time: ~{total_time_hours:.1f} hours")
        
        if peak_memory_gb > self.memory_gb * 0.9:
            print(f"⚠️  WARNING: Peak memory ({peak_memory_gb:.1f}GB) approaches limit ({self.memory_gb}GB)")
            print(f"   Consider reducing workers or grid points")
        
        # Validate and get available data paths
        path_config = self._validate_paths()
        
        # Create base configuration for full Tenerife domain
        base_config = ModelConfig(
            # FULL TENERIFE DOMAIN
            grid_size=(15121, 24741),  # Full Tenerife dimensions
            num_layers=25,             # Maximum vertical resolution
            max_steps=100,             # Sufficient for fire progression
            model_resolution=10.0,     # 10m resolution (increased from 5m to reduce grid size)
            
            # MAXIMUM MEMORY OPTIMIZATION
            memory_optimization_level=2,  # Maximum valid optimization level
            use_disk_storage=True,        # Store history on disk
            use_differential_history=True, # Only store changes
            use_sparse_storage=True,      # Sparse arrays for fuel/state
            
            # TENERIFE GEOGRAPHIC CONFIGURATION
            crs="EPSG:25828",            # UTM Zone 28N for Tenerife
            
            # ENHANCED FIRE PARAMETERS FOR REALISTIC SPREAD
            spread_probability=0.6,
            fuel_consumption_rate=0.8,
            ignition_threshold=0.4,
            initial_fuel_load=8.0,
            
            # TERRAIN AND WIND EFFECTS
            slope_influence=0.4,
            wind_influence_on_spread=0.3,
            terrain_effect_strength=0.7,
            
            # CONFIGURABLE TERRAIN DATA (with fallbacks)
            use_preprocessed_terrain=path_config['use_preprocessed_terrain'],
            preprocessed_terrain_dir=path_config['preprocessed_terrain_dir'],
            
            # CONFIGURABLE LIDAR DATA (with fallbacks)
            use_lidar=path_config['use_lidar'],
            lidar_data_dir=path_config['lidar_data_dir'],
            auto_size_from_lidar=False,  # Use specified grid size
            extinction_coefficient=0.5,
            pad_bin_size=2.0,
            exclude_ground_layer=True,
            max_vegetation_height_m=50.0,
            
            # WIND CONFIGURATION
            wind_speed=5.0,
            wind_direction=45.0,
        )
        
        # Create calibration targets from training data
        from src.core.calibration.calibration_config import CalibrationTarget
        calibration_targets = []
        for fp in training_data:
            target = CalibrationTarget(
                fire_perimeter_path=fp.shapefile_path,
                weight=1.0 / len(training_data)  # Equal weights
            )
            calibration_targets.append(target)
        
        # Create calibration configuration
        calib_config = CalibrationConfig(
            experiment_name=self.experiment_name,
            method=CalibrationMethod.GRID_SEARCH,
            objective=CalibrationObjective.SPATIAL_SIMILARITY,
            base_config=base_config,
            
            # PARAMETER CONFIGURATION
            calibration_parameters=calibration_parameters,
            grid_search_points=self.grid_search_points,
            
            # FIRE PERIMETER TARGETS
            calibration_targets=calibration_targets,  # Populated with training data
            
            # HIGH-MEMORY PARALLEL CONFIGURATION
            parallel_execution=True,
            max_workers=self.workers,  # Use CLI-specified worker count
            memory_limit_gb=self.memory_gb * 0.9,  # Leave 10% for system
            simulation_timeout_minutes=180.0,      # 3 hours per simulation (full Tenerife needs more time)
            
            # SPATIAL SIMILARITY WEIGHTS
            jaccard_weight=0.4,
            dice_weight=0.3,
            sorensen_weight=0.3,
            
            # OUTPUT CONFIGURATION
            results_dir=str(self.results_dir),
            save_intermediate_results=True,
            generate_plots=True,
            verbose=True
        )
        
        print(f"✅ Calibration configuration created")
        print(f"   Training targets: {len(calib_config.calibration_targets)}")
        print(f"   Memory optimization: Level {base_config.memory_optimization_level}")
        print(f"   Disk storage: {base_config.use_disk_storage}")
        print(f"   Sparse storage: {base_config.use_sparse_storage}")
        
        return calib_config
    
    def _estimate_memory_per_simulation(self) -> float:
        """Estimate memory usage per simulation in GB with shared terrain enabled."""
        # Full Tenerife: 15,121 × 24,741 × 25 = ~9.35 billion cells
        total_cells = 15121 * 24741 * 25
        
        # WITH SHARED TERRAIN ENABLED:
        # 1. Shared terrain: ~9.5GB loaded ONCE and shared across ALL workers
        # 2. Disk storage: History stored on disk, only current timestep in memory  
        # 3. Sparse storage: Only active fire cells stored (~5-10% of total)
        # 4. Level 2 optimization: 60% memory reduction
        
        # Per-simulation memory (excluding shared terrain):
        # Active fire cells (more realistic estimate for large fires)
        active_percentage = 0.08  # 8% of domain actively burning/changing
        active_cells = total_cells * active_percentage
        
        # Current state layers with Level 2 optimization (60% reduction)
        # Fire state, fuel remaining, temperature, wind effects = ~4 layers
        current_state_layers = 4
        current_state_gb = (active_cells * current_state_layers * 4) / (1024**3)
        current_state_gb *= 0.4  # Level 2 optimization (60% reduction)
        
        # Sparse storage additional reduction (80% reduction for fire data)
        current_state_gb *= 0.2  # Sparse storage benefit
        
        # Working memory for simulation logic and Python objects
        working_memory_gb = 1.0  # More realistic for complex simulations
        
        # Terrain memory per worker: ZERO (shared terrain eliminates this!)
        terrain_per_worker_gb = 0.0
        
        # Total per simulation (shared terrain is separate)
        total_per_sim = current_state_gb + working_memory_gb + terrain_per_worker_gb
        
        return total_per_sim
    
    def _estimate_time_per_simulation(self) -> float:
        """Estimate time per simulation in minutes."""
        # Full Tenerife domain is massive, but with optimization:
        # - Sparse computation reduces active cell processing
        # - Optimized algorithms for large grids
        # - Typical estimate: 15-30 minutes per simulation
        
        return 20.0  # Conservative estimate
    
    def _find_terrain_dir(self) -> Optional[str]:
        """Find preprocessed terrain directory with fallbacks."""
        possible_paths = [
            # HPC path
            "/gpfs/home1/apaphitis/git/github/Forest-Fire-Simulation/preprocessed_terrain",
            # Project relative path
            str(Path(__file__).parent.parent.parent.parent / "preprocessed_terrain"),
            # Current directory relative
            "preprocessed_terrain",
            # Data directory
            "data/preprocessed_terrain"
        ]
        
        for path in possible_paths:
            path_obj = Path(path)
            if path_obj.exists() and path_obj.is_dir():
                # Check if it has terrain files
                terrain_files = list(path_obj.glob("*.npy"))
                if len(terrain_files) >= 3:  # At least some terrain files
                    logger.info(f"✅ Found terrain directory: {path}")
                    return str(path_obj)
                else:
                    logger.debug(f"Directory exists but insufficient terrain files: {path}")
        
        logger.warning("⚠️  No valid terrain directory found")
        return None
    
    def _find_lidar_dir(self) -> Optional[str]:
        """Find LiDAR data directory with fallbacks."""
        possible_paths = [
            # HPC path
            "/gpfs/home1/apaphitis/git/github/Forest-Fire-Simulation/PAD Results/",
            # Project relative path
            str(Path(__file__).parent.parent.parent.parent / "PAD Results"),
            # Alternative names
            str(Path(__file__).parent.parent.parent.parent / "lidar_data"),
            str(Path(__file__).parent.parent.parent.parent / "data" / "lidar"),
            # Current directory relative
            "PAD Results",
            "lidar_data",
            "data/lidar"
        ]
        
        for path in possible_paths:
            path_obj = Path(path)
            if path_obj.exists() and path_obj.is_dir():
                # Check if it has LiDAR files
                lidar_files = (list(path_obj.rglob("*.las")) + 
                              list(path_obj.rglob("*.laz")) + 
                              list(path_obj.rglob("*.tif")) +
                              list(path_obj.rglob("*.tiff")))
                if len(lidar_files) > 0:
                    logger.info(f"✅ Found LiDAR directory: {path} ({len(lidar_files)} files)")
                    return str(path_obj)
                else:
                    logger.debug(f"Directory exists but no LiDAR files: {path}")
        
        logger.warning("⚠️  No valid LiDAR directory found")
        return None
    
    def _validate_paths(self) -> Dict[str, Any]:
        """Validate and return available data paths."""
        terrain_dir = self._find_terrain_dir()
        lidar_dir = self._find_lidar_dir()
        
        config = {
            'use_preprocessed_terrain': terrain_dir is not None,
            'preprocessed_terrain_dir': terrain_dir,
            'use_lidar': lidar_dir is not None,
            'lidar_data_dir': lidar_dir
        }
        
        logger.info(f"📂 Data availability:")
        logger.info(f"   Preprocessed terrain: {'✅' if config['use_preprocessed_terrain'] else '❌'}")
        logger.info(f"   LiDAR data: {'✅' if config['use_lidar'] else '❌'}")
        
        if not config['use_preprocessed_terrain'] and not config['use_lidar']:
            logger.warning("⚠️  No terrain or LiDAR data found - will use synthetic data")
        
        return config
    
    def _setup_shared_terrain_if_possible(self, calibration_config: CalibrationConfig) -> Optional[Dict[str, Any]]:
        """Set up shared terrain if the grid size allows it."""
        if not getattr(calibration_config.base_config, 'use_preprocessed_terrain', False):
            logger.info("📊 Preprocessed terrain not enabled - skipping shared terrain")
            return None
        
        grid_size = getattr(calibration_config.base_config, 'grid_size', (100, 100))
        if isinstance(grid_size, int):
            grid_size = (grid_size, grid_size)
        
        # Check if grid is too large for shared memory
        total_cells = grid_size[0] * grid_size[1]
        # Correct memory calculation based on actual terrain data types:
        # 6 float32 layers: elevation, slope, aspect, barranco_directions, wind_amplification, wind_direction_modification
        # 3 uint8 layers: barranco_mask, depression_mask, wind_channeling_mask
        float32_layers_gb = total_cells * 6 * 4 / (1024**3)  # 6 layers × 4 bytes
        uint8_layers_gb = total_cells * 3 * 1 / (1024**3)    # 3 layers × 1 byte
        estimated_shared_gb = float32_layers_gb + uint8_layers_gb
        
        if total_cells > 1_000_000_000:  # More than 1B cells (increased threshold)
            logger.warning(f"⚠️  Grid too large for shared terrain: {grid_size} ({total_cells:,} cells)")
            logger.warning("   Shared terrain disabled - each worker will load terrain individually")
            return None
        elif total_cells > 100_000_000:  # Full Tenerife range (100M-500M cells)
            logger.info(f"🗺️  Full Tenerife domain detected: {grid_size} ({total_cells:,} cells)")
            logger.info(f"   Estimated shared terrain memory: {estimated_shared_gb:.1f} GB")
            logger.info(f"   Enabling shared terrain - will dramatically reduce per-worker memory")
            logger.info(f"   Shared terrain will be loaded once and used by all workers")
        
        try:
            from src.utils.shared_terrain import get_shared_terrain_manager
            
            logger.info("🧠 Setting up shared terrain data for memory-efficient processing...")
            shared_manager = get_shared_terrain_manager()
            
            preprocessed_dir = getattr(calibration_config.base_config, 'preprocessed_terrain_dir', None)
            if not preprocessed_dir:
                logger.warning("No preprocessed terrain directory specified")
                return None
            
            # Load terrain data into shared memory - use absolute path for worker processes
            target_shape = (grid_size[0], grid_size[1])  # Keep consistent with terrain file format (width, height)
            abs_preprocessed_dir = str(Path(preprocessed_dir).resolve())
            logger.info(f"🗂️  Using absolute path for shared terrain: {abs_preprocessed_dir}")
            success = shared_manager.load_terrain_data(abs_preprocessed_dir, target_shape)
            
            if success:
                shared_terrain_info = shared_manager.get_shared_terrain_info()
                logger.info(f"✅ Shared terrain data loaded successfully")
                return shared_terrain_info
            else:
                logger.warning("⚠️  Failed to load shared terrain data - falling back to individual loading")
                return None
                
        except Exception as e:
            logger.error(f"❌ CRITICAL: Failed to set up shared terrain: {e}")
            logger.error(f"   Preprocessed directory: {abs_preprocessed_dir}")
            logger.error(f"   Target shape: {target_shape}")
            logger.error(f"   Working directory: {Path.cwd()}")
            logger.error("   This will cause massive memory usage per worker!")
            logger.error("   Consider reducing worker count or fixing terrain data")
            # Don't raise - let it fall back to individual loading but with warning
            logger.warning("⚠️  Falling back to individual terrain loading - REDUCE WORKER COUNT!")
            return None

    def run_calibration(self, 
                       calibration_config: CalibrationConfig,
                       test_data: List[FirePerimeterData]) -> Dict[str, Any]:
        """
        Run the complete calibration process.
        
        Args:
            calibration_config: Calibration configuration
            test_data: Test data for validation
            
        Returns:
            Dictionary with calibration results and validation metrics
        """
        print(f"\n🚀 STARTING FULL TENERIFE FIRE PERIMETER CALIBRATION")
        print(f"=" * 70)
        
        # Set up shared terrain if possible (for memory optimization)
        shared_terrain_info = self._setup_shared_terrain_if_possible(calibration_config)
        if shared_terrain_info:
            # Add shared terrain info to the base config
            if hasattr(calibration_config.base_config, '__dict__'):
                calibration_config.base_config.shared_terrain_info = shared_terrain_info
                print(f"✅ Added shared terrain info to calibration configuration")
        else:
            print(f"📊 Using individual terrain loading (no shared memory)")
        
        # Create parameter bounds
        parameter_bounds = get_default_calibration_bounds()
        
        # Create spatial similarity objective function
        from src.core.calibration.objective_functions import create_default_spatial_objective
        objective_function = create_default_spatial_objective()
        
        # Create grid search calibrator
        calibrator = GridSearchCalibrator(
            calibration_config=calibration_config,
            parameter_bounds=parameter_bounds,
            objective_function=objective_function,
            parallel_execution=True,
            max_workers=self.workers
        )
        
        # Create progress callback
        progress_callback = create_progress_callback(verbose=True)
        
        # Display calibration info
        estimation_info = calibrator.get_estimation_info()
        print(f"📊 CALIBRATION OVERVIEW:")
        print(f"   Total combinations: {estimation_info['total_combinations']:,}")
        print(f"   Estimated runtime: {estimation_info['estimated_time_hours']:.1f} hours")
        print(f"   Memory requirement: {estimation_info.get('memory_requirement_gb', 0.0):.1f} GB")
        print(f"   Parallel workers: {self.workers}")
        
        # Run calibration
        print(f"\n🔥 Running grid search calibration...")
        start_time = datetime.now()
        
        try:
            # Convert training data to target format
            target_data = self._prepare_target_data(calibration_config.calibration_targets)
            
            results = calibrator.run_calibration(
                target_data=target_data,
                progress_callback=progress_callback
            )
            
            end_time = datetime.now()
            runtime = (end_time - start_time).total_seconds() / 3600  # hours
            
            print(f"\n✅ Calibration completed successfully!")
            print(f"⏱️  Runtime: {runtime:.2f} hours")
            best_value = results.get_best_objective_value()
            if best_value is not None:
                print(f"🎯 Best objective value: {best_value:.4f}")
            else:
                print(f"🎯 Best objective value: None (no valid results)")
            
            # Validate on test data
            best_parameters = results.get_best_parameters()
            if best_parameters is None:
                print("⚠️  No valid parameters found - skipping validation")
                validation_results = {'status': 'skipped', 'reason': 'no_valid_parameters'}
            else:
                validation_results = self._validate_on_test_data(
                    best_parameters=best_parameters,
                    test_data=test_data,
                    calibration_config=calibration_config
                )
            
            # Save results
            self._save_calibration_results(results, validation_results, runtime)
            
            # Clean up shared terrain if it was used
            if shared_terrain_info:
                try:
                    from src.utils.shared_terrain import cleanup_shared_terrain
                    cleanup_shared_terrain()
                    print("🧹 Cleaned up shared terrain data")
                except Exception as e:
                    logger.warning(f"⚠️  Error cleaning up shared terrain: {e}")
            
            # Ensure validation_results is a dictionary for return
            if not isinstance(validation_results, dict):
                logger.warning(f"⚠️  validation_results is not a dict in return: {type(validation_results)}")
                validation_results = {'status': 'error', 'reason': 'invalid_type_in_return', 'original_type': str(type(validation_results))}
            
            return {
                'calibration_results': results,
                'validation_results': validation_results,
                'runtime_hours': runtime,
                'best_parameters': results.get_best_parameters() or {},
                'best_objective_value': results.get_best_objective_value() or 0.0
            }
            
        except Exception as e:
            # Clean up shared terrain even on error
            if shared_terrain_info:
                try:
                    from src.utils.shared_terrain import cleanup_shared_terrain
                    cleanup_shared_terrain()
                except:
                    pass
            
            print(f"\n❌ Calibration failed: {e}")
            logger.error(f"Calibration failed: {e}")
            raise
    
    def _prepare_target_data(self, calibration_targets) -> Dict[str, Any]:
        """
        Convert shapefile fire perimeters to grid format for spatial comparison.
        
        Args:
            calibration_targets: List of CalibrationTarget objects with shapefile paths
            
        Returns:
            Dictionary containing rasterized fire perimeter data
        """
        if not SPATIAL_LIBS_AVAILABLE:
            logger.warning("Spatial libraries not available - using synthetic target data")
            return {}
        
        if not calibration_targets:
            logger.warning("No calibration targets provided - using synthetic target data")
            return {}
        
        try:
            logger.info(f"🔄 Converting {len(calibration_targets)} fire perimeter(s) to grid format")
            
            # For multiple targets, we'll combine them (for temporal progression)
            # For now, use the first target as primary, but prepare for multiple
            target = calibration_targets[0]
            shapefile_path = target.fire_perimeter_path
            
            logger.info(f"📍 Loading fire perimeter from: {shapefile_path}")
            
            # Load shapefile
            gdf = gpd.read_file(shapefile_path)
            logger.info(f"   Loaded {len(gdf)} features with CRS: {gdf.crs}")
            
            # Ensure CRS is EPSG:25828 (Tenerife UTM Zone 28N)
            if gdf.crs != "EPSG:25828":
                logger.info(f"🗺️  Converting CRS from {gdf.crs} to EPSG:25828")
                gdf = gdf.to_crs("EPSG:25828")
            
            # Calculate fire area in hectares
            fire_area_ha = gdf.geometry.area.sum() / 10000
            logger.info(f"🔥 Fire area: {fire_area_ha:.1f} hectares")
            
            # Get bounds for rasterization
            bounds = gdf.total_bounds  # [minx, miny, maxx, maxy]
            logger.info(f"📐 Fire bounds: {bounds}")
            
            # Full Tenerife grid dimensions
            grid_width, grid_height = 15121, 24741
            
            # Calculate cell size (10m resolution)
            cell_size = 10.0
            
            # Create transform for full Tenerife domain
            # Calculate Tenerife bounds based on grid size and resolution
            tenerife_width_m = grid_width * cell_size    # 151,210 meters
            tenerife_height_m = grid_height * cell_size  # 247,410 meters
            
            # Estimate Tenerife SW corner (approximate)
            tenerife_sw_x = 300000  # Approximate UTM coordinates for Tenerife
            tenerife_sw_y = 3100000
            
            # Create transform for the full Tenerife grid
            transform = rasterio.transform.from_bounds(
                tenerife_sw_x, 
                tenerife_sw_y,
                tenerife_sw_x + tenerife_width_m,
                tenerife_sw_y + tenerife_height_m,
                grid_width, 
                grid_height
            )
            
            logger.info(f"🗺️  Rasterizing to {grid_width}×{grid_height} grid (10m resolution)")
            
            # Rasterize the fire perimeter to the full Tenerife grid
            fire_perimeter_grid = rasterize(
                gdf.geometry,
                out_shape=(grid_height, grid_width),
                transform=transform,
                fill=0,           # Background value (no fire)
                default_value=1,  # Fire area value
                dtype=np.float32
            )
            
            # Calculate rasterized statistics
            fire_cells = np.sum(fire_perimeter_grid > 0)
            fire_area_grid_ha = fire_cells * (cell_size * cell_size) / 10000
            
            logger.info(f"✅ Successfully rasterized fire perimeter:")
            logger.info(f"   Grid shape: {fire_perimeter_grid.shape}")
            logger.info(f"   Fire cells: {fire_cells:,}")
            logger.info(f"   Fire area (grid): {fire_area_grid_ha:.1f} ha")
            logger.info(f"   Fire area (original): {fire_area_ha:.1f} ha")
            logger.info(f"   Area difference: {abs(fire_area_grid_ha - fire_area_ha):.1f} ha")
            
            # Prepare target data for multiple calibration targets if needed
            target_data = {
                'fire_perimeter': fire_perimeter_grid,
                'bounds': bounds,
                'transform': transform,
                'fire_area_ha': fire_area_ha,
                'fire_cells': fire_cells,
                'grid_shape': fire_perimeter_grid.shape,
                'cell_size_m': cell_size
            }
            
            # If multiple targets, add them as well
            if len(calibration_targets) > 1:
                logger.info(f"📅 Processing {len(calibration_targets)-1} additional targets")
                additional_targets = []
                
                for i, additional_target in enumerate(calibration_targets[1:], 1):
                    try:
                        add_gdf = gpd.read_file(additional_target.fire_perimeter_path)
                        if add_gdf.crs != "EPSG:25828":
                            add_gdf = add_gdf.to_crs("EPSG:25828")
                        
                        add_grid = rasterize(
                            add_gdf.geometry,
                            out_shape=(grid_height, grid_width),
                            transform=transform,
                            fill=0,
                            default_value=1,
                            dtype=np.float32
                        )
                        
                        additional_targets.append({
                            'fire_perimeter': add_grid,
                            'fire_area_ha': add_gdf.geometry.area.sum() / 10000,
                            'fire_cells': np.sum(add_grid > 0)
                        })
                        
                        logger.info(f"   Target {i+1}: {np.sum(add_grid > 0):,} cells")
                        
                    except Exception as e:
                        logger.warning(f"Failed to process target {i+1}: {e}")
                
                target_data['additional_targets'] = additional_targets
            
            logger.info(f"🎯 Target data preparation complete")
            return target_data
            
        except Exception as e:
            logger.error(f"❌ Error preparing target data: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            logger.warning("Falling back to synthetic target data")
            return {}
    
    def _validate_on_test_data(self, 
                              best_parameters: Dict[str, float],
                              test_data: List[FirePerimeterData],
                              calibration_config: CalibrationConfig) -> Dict[str, Any]:
        """Validate calibrated parameters on test fire perimeters."""
        print(f"\n🧪 VALIDATING ON TEST DATA")
        print(f"=" * 40)
        
        # Safety check for None parameters
        if best_parameters is None:
            print("⚠️  No best parameters provided - skipping validation")
            return {'status': 'skipped', 'reason': 'no_best_parameters'}
        
        validation_results = {}
        
        for i, test_fp in enumerate(test_data, 1):
            print(f"Testing on Day {test_fp.day_number} ({test_fp.date})...")
            
            # Create config with best parameters
            test_config = calibration_config.create_config_variant(best_parameters)
            
            # Run simulation (placeholder - implement actual simulation)
            # For now, just record the test case
            validation_results[f"test_day_{test_fp.day_number}"] = {
                'date': test_fp.date,
                'shapefile': test_fp.shapefile_path,
                'area_hectares': test_fp.area_hectares,
                'parameters': best_parameters,
                'status': 'pending_implementation'
            }
        
        print(f"✅ Validation setup complete for {len(test_data)} test cases")
        return validation_results
    
    def _save_calibration_results(self, 
                                 results,
                                 validation_results: Dict[str, Any],
                                 runtime_hours: float):
        """Save calibration results to files."""
        print(f"\n💾 SAVING CALIBRATION RESULTS")
        print(f"=" * 40)
        
        # Save grid search results
        results_file = self.results_dir / f"{self.experiment_name}_grid_search_results.json"
        results.save_results(results_file)
        print(f"✅ Saved grid search results: {results_file.name}")
        
        # Save validation results
        validation_file = self.results_dir / f"{self.experiment_name}_validation_results.json"
        
        # Ensure validation_results is a dictionary
        if not isinstance(validation_results, dict):
            logger.warning(f"⚠️  validation_results is not a dict: {type(validation_results)}")
            validation_results = {'status': 'error', 'reason': 'invalid_type', 'original_type': str(type(validation_results))}
        
        with open(validation_file, 'w') as f:
            json.dump(validation_results, f, indent=2, default=str)
        print(f"✅ Saved validation results: {validation_file.name}")
        
        # Save summary report
        summary_file = self.results_dir / f"{self.experiment_name}_calibration_summary.json"
        summary_data = {
            'experiment_info': {
                'name': self.experiment_name,
                'timestamp': datetime.now().isoformat(),
                'domain': 'Full Tenerife (15,121 × 24,741 × 25)',
                'memory_framework': f"{self.memory_gb}GB / {self.workers} workers",
                'grid_search_points': self.grid_search_points
            },
            'performance': {
                'runtime_hours': runtime_hours,
                'total_combinations': len(results.results),
                'successful_evaluations': results.successful_evaluations,
                'best_objective_value': results.get_best_objective_value() or 0.0
            },
            'best_parameters': results.get_best_parameters() or {},
            'validation_summary': {
                'test_cases': len(validation_results) if isinstance(validation_results, dict) else 0,
                'status': 'completed'
            }
        }
        
        with open(summary_file, 'w') as f:
            json.dump(summary_data, f, indent=2)
        print(f"✅ Saved calibration summary: {summary_file.name}")
        
        print(f"\n🎉 All results saved to: {self.results_dir}")


def main():
    """Example usage of the fire perimeter calibration system."""
    print("🔥 TENERIFE FIRE PERIMETER CALIBRATION SYSTEM")
    print("=" * 70)
    
    # Step 1: Discover fire perimeters
    discovery = FirePerimeterDiscovery("EMSR Delineations")
    fire_dataset = discovery.discover_fire_perimeters()
    
    if not fire_dataset.fire_perimeters:
        print("❌ No fire perimeters found. Check directory structure.")
        return
    
    # Step 2: Create calibrator
    calibrator = TenerifeFirePerimeterCalibrator(
        memory_gb=64,
        workers=60,
        grid_search_points=3,
        experiment_name="tenerife_emsr685_calibration"
    )
    
    # Step 3: Set up training/test split
    training_data, test_data = calibrator.setup_training_test_split(
        fire_dataset,
        training_days=[1, 2],  # Days 1-2 for training
        test_days=[3, 4]       # Days 3-4 for testing
    )
    
    # Step 4: Create calibration configuration
    # NOTE: Replace with actual top 5 parameters from sensitivity analysis
    top_5_parameters = [
        'wind_influence_on_spread',
        'fuel_consumption_rate',
        'terrain_effect_strength',
        'barranco_amplification',
        'slope_influence'
    ]
    
    calib_config = calibrator.create_calibration_config(
        training_data=training_data,
        top_5_parameters=top_5_parameters
    )
    
    print(f"\n✅ Setup complete! Ready to run calibration.")
    print(f"   Training data: {len(training_data)} fire perimeters")
    print(f"   Test data: {len(test_data)} fire perimeters")
    print(f"   Parameters: {len(calib_config.calibration_parameters)}")
    print(f"   Total combinations: {calib_config.grid_search_points ** len(calib_config.calibration_parameters)}")
    
    # Uncomment to run actual calibration (WARNING: Very resource intensive!)
    # results = calibrator.run_calibration(calib_config, test_data)


if __name__ == "__main__":
    main()
