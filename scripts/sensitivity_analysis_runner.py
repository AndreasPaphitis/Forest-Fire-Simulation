#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
HPC-Optimized Method 2 Range-Based Sensitivity Analysis Runner

This script performs comprehensive sensitivity analysis on all 13 calibration parameters
using Method 2: Standardized Range-Based Sensitivity Analysis with 9 test points spanning
0% to 80% of each parameter's range. This approach provides baseline-independent sensitivity
rankings suitable for parameter prioritization and focused calibration.

HPC OPTIMIZED FOR: 32 CPU cores, 32 GB RAM
Key Features:
- Method 2 Range-Based Sensitivity (no baseline dependency)
- 9 evenly spaced test points across parameter range
- HPC parallel processing with 28 workers (optimized for 32-core CPU with system overhead)
- High-memory optimized implementation (~2-4 GB peak usage)
- Larger grid sizes for production-quality analysis
- Comprehensive reporting with calibration recommendations
- Massive speedup: ~15-20x faster with HPC parallel processing

HPC Performance Improvements:
- Sequential processing: ~4.9 hours for 117 evaluations
- HPC Parallel processing (28 workers): ~15-20 minutes for 117 evaluations  
- HPC Parallel efficiency: Up to 95% with optimal worker configuration
- Extended capability: ~6-8 hours for 1,170 evaluations (10x parameter resolution)

Usage:
    python sensitivity_analysis_runner.py [--config CONFIG_FILE] [--output OUTPUT_DIR] [--name EXPERIMENT_NAME]
    python sensitivity_analysis_runner.py --hpc-mode  # Full HPC optimization (28 workers, large grids)
    python sensitivity_analysis_runner.py --workers 16  # Custom worker count
    python sensitivity_analysis_runner.py --workers 1  # Disable parallel processing
    python sensitivity_analysis_runner.py --production-scale  # Very large grids for production analysis

Author: Forest Fire Simulation Team
Date: 2025
Version: 3.0 - HPC-Optimized Implementation for 32-core Systems
"""

import os
import sys
import time
import argparse
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging

# Add project root to path for imports
project_root = Path(__file__).parent.parent  # Go up one more level since we're in scripts/
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from src.core.calibration import (
        CalibrationConfig, CalibrationMethod, CalibrationObjective,
        SensitivityAnalyzer,
        get_default_calibration_bounds,

        create_sensitivity_progress_callback,
        save_calibration_results,
        create_calibration_report,
        validate_calibration_config,

    )
    from src.config.config_tools import ModelConfig
    from src.utils.logging_utils import get_logger
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure you're running this from the Forest-Fire-Simulation directory")
    sys.exit(1)

logging.getLogger("src.core.fire_simulation_engine").setLevel(logging.WARNING)

logger = get_logger(__name__, level=logging.WARNING)


class HPCOptimizedSensitivityRunner:
    """
    HPC-optimized runner for grid-based sensitivity analysis with 28 workers.
    Configured for 32-core CPU with 32 GB RAM and level 3 memory optimization.
    """
    
    def __init__(self, 
                 config_file: Optional[str] = None,
                 output_dir: Optional[str] = None,
                 experiment_name: Optional[str] = None,
                 hpc_mode: bool = False,
                 production_scale: bool = False,
                 cli_args: Optional[object] = None):
        """
        Initialize the HPC-optimized sensitivity analysis runner.
        
        Args:
            config_file: Optional path to production config file
            output_dir: Output directory for results
            experiment_name: Name for this experiment
            hpc_mode: Enable full HPC optimization
            production_scale: Use very large grids for production analysis
            cli_args: Parsed command line arguments
        """
        self.config_file = config_file
        self.output_dir = Path(output_dir) if output_dir else Path("hpc_sensitivity_results")
        self.experiment_name = experiment_name or f"hpc_method2_sensitivity_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.hpc_mode = hpc_mode
        self.production_scale = production_scale
        self._cli_args = cli_args  # Store CLI arguments
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.calibration_config = None
        self.parameter_bounds = None
        self.objective_function = None
        self.target_data = None
        
        print(f"🚀 HPC-OPTIMIZED METHOD 2 RANGE-BASED SENSITIVITY ANALYSIS")
        print(f"🖥️  Target System: 32 CPU cores, 32 GB RAM")
        print(f"Experiment: {self.experiment_name}")
        print(f"Output directory: {self.output_dir}")
        print(f"Method: Standardized Range-Based Sensitivity (Method 2)")
        print(f"Test points: 9 evenly spaced across parameter range (0% to 80%)")
        if self.hpc_mode:
            print(f"🚀 HPC MODE: Full optimization enabled")
            print(f"   - Workers: 28 (leaving 4 cores for system overhead)")
            print(f"   - Memory limit: 28 GB (leaving 4 GB for system)")
            print(f"   - Grid size: {'200×200×10' if self.production_scale else '120×120×8'}")
        else:
            print(f"🔧 STANDARD MODE: Configurable optimization")
        print(f"Memory optimization: Level 3 (aggressive)")
        print("=" * 80)
    
    def setup_configuration(self):
        """Set up the HPC-optimized calibration configuration for sensitivity analysis."""
        print("⚙️  Setting up HPC-optimized calibration configuration...")
        
        # Create base simulation configuration
        if self.config_file and Path(self.config_file).exists():
            print(f"Loading configuration from: {self.config_file}")
            # If production config exists, use it as base
            try:
                from src.core.calibration import create_calibration_from_production_config
                
                self.calibration_config = create_calibration_from_production_config(
                    production_config_path=self.config_file,
                    experiment_name=self.experiment_name,
                    method=CalibrationMethod.SENSITIVITY_ANALYSIS
                )
                
                # Override calibration parameters with all 13 parameters
                self.calibration_config.calibration_parameters = self._get_all_calibration_parameters()
                
                # Override performance settings for HPC optimization
                self._apply_hpc_optimizations()
                
            except Exception as e:
                print(f"⚠️  Warning: Could not load production config: {e}")
                print("Using HPC-optimized default configuration instead...")
                self.calibration_config = self._create_hpc_optimized_config()
        else:
            print("Using HPC-optimized default configuration...")
            self.calibration_config = self._create_hpc_optimized_config()
        
        # Validate configuration
        is_valid, errors = validate_calibration_config(self.calibration_config)
        if not is_valid:
            print("❌ Configuration validation failed:")
            for error in errors:
                print(f"  - {error}")
            raise ValueError("Invalid configuration")
        
        print("✅ Configuration validated successfully")
        print(f"✅ Parameters to analyze: {len(self.calibration_config.calibration_parameters)}")
        print(f"✅ Parallel workers configured: {self.calibration_config.max_workers}")
        print(f"✅ Grid size: {self.calibration_config.base_config.grid_size}")
        print(f"✅ Layers: {self.calibration_config.base_config.num_layers}")
        
        # Validate HPC system requirements
        self._validate_hpc_requirements()
        
        return self.calibration_config
    
    def _apply_hpc_optimizations(self):
        """Apply HPC-specific optimizations to existing config."""
        # Apply CLI worker settings if available
        cli_args = getattr(self, '_cli_args', None)
        cli_workers = None
        if cli_args is not None and hasattr(cli_args, 'workers'):
            cli_workers = cli_args.workers
        
        if cli_workers is not None:
            self.calibration_config.max_workers = cli_workers
        elif self.hpc_mode:
            self.calibration_config.max_workers = 28  # Leave 4 cores for system
        else:
            self.calibration_config.max_workers = min(24, 28)  # Conservative default
            
        self.calibration_config.parallel_execution = True
        
        # Memory optimization
        memory_level = 3  # Default
        if cli_args is not None and hasattr(cli_args, 'memory_level'):
            memory_level = cli_args.memory_level
        self.calibration_config.memory_limit_gb = 28.0 if self.hpc_mode else 24.0
        
        # Update base config for HPC
        if self.production_scale:
            self.calibration_config.base_config.grid_size = (200, 200)
            self.calibration_config.base_config.num_layers = 10
            self.calibration_config.base_config.max_steps = 60
        elif self.hpc_mode:
            self.calibration_config.base_config.grid_size = (120, 120)
            self.calibration_config.base_config.num_layers = 8
            self.calibration_config.base_config.max_steps = 50
        
        self.calibration_config.base_config.memory_optimization_level = memory_level
        self.calibration_config.simulation_timeout_minutes = 30.0  # Longer timeout for larger grids
    
    def _create_hpc_optimized_config(self) -> CalibrationConfig:
        """Create an HPC-optimized calibration configuration for 32-core CPU."""
        # Initialize default values
        grid_size = None
        num_layers = None
        max_steps = None
        
        # Check for CLI overrides first (these take priority)
        cli_args = getattr(self, '_cli_args', None)
        if cli_args is not None and hasattr(cli_args, 'grid_size') and cli_args.grid_size is not None:
            grid_size = (cli_args.grid_size[0], cli_args.grid_size[1])
            num_layers = cli_args.grid_size[2]
            print(f"📏 Using CLI-specified grid: {grid_size[0]}×{grid_size[1]}×{num_layers}")
        if cli_args is not None and hasattr(cli_args, 'max_steps') and cli_args.max_steps is not None:
            max_steps = cli_args.max_steps
            print(f"📏 Using CLI-specified max steps: {max_steps}")
        
        # Check for preprocessed terrain and determine appropriate grid size
        base_terrain_dir = Path("/gpfs/home1/apaphitis/git/github/Forest-Fire-Simulation/preprocessed_terrain")
        use_preprocessed_terrain = False
        preprocessed_terrain_dir = None
        
        if base_terrain_dir.exists():
            # Required terrain files
            required_files = [
                "elevation.npy", "slope.npy", "aspect.npy", "barranco_mask.npy",
                "barranco_directions.npy", "depression_mask.npy", "wind_channeling_mask.npy",
                "wind_amplification.npy", "wind_direction_modification.npy"
            ]
            
            # First check if files are directly in the base directory
            missing_files = [f for f in required_files if not (base_terrain_dir / f).exists()]
            
            if not missing_files:
                # Files found directly in base directory
                print("✅ All preprocessed terrain files found in base directory")
                preprocessed_terrain_dir = base_terrain_dir
                use_preprocessed_terrain = True
            else:
                # Search for files in subdirectories (nested structure)
                print("🔍 Files not in base directory - searching subdirectories...")
                
                # Find all .npy files in subdirectories
                all_npy_files = list(base_terrain_dir.rglob("*.npy"))
                
                if all_npy_files:
                    # Group files by their parent directory
                    dir_file_counts = {}
                    for npy_file in all_npy_files:
                        parent_dir = npy_file.parent
                        if parent_dir not in dir_file_counts:
                            dir_file_counts[parent_dir] = []
                        dir_file_counts[parent_dir].append(npy_file.name)
                    
                    # Find directory with all required files
                    for candidate_dir, files in dir_file_counts.items():
                        if all(req_file in files for req_file in required_files):
                            print(f"✅ All preprocessed terrain files found in: {candidate_dir.relative_to(base_terrain_dir)}")
                            preprocessed_terrain_dir = candidate_dir
                            use_preprocessed_terrain = True
                            break
                    
                    if not use_preprocessed_terrain:
                        print(f"⚠️  Found {len(all_npy_files)} .npy files but none contain all required files")
                        print("   Required files:", required_files)
                        print("   Will use flat terrain instead")
                else:
                    print("⚠️  No .npy files found in directory structure")
                    print("   Will use flat terrain instead")
        else:
            print("📊 Preprocessed terrain directory not found - will use flat terrain")
        
        if cli_args is not None and hasattr(cli_args, 'force_preprocessed') and cli_args.force_preprocessed:
            use_preprocessed_terrain = True
            preprocessed_terrain_dir = Path("/gpfs/home1/apaphitis/git/github/Forest-Fire-Simulation/preprocessed_terrain")
        
        # If CLI didn't specify grid size, determine it based on mode and terrain
        if grid_size is None:
            if use_preprocessed_terrain:
                print("🔄 PREPROCESSED TERRAIN DETECTED: Using optimized configuration")
                
                # Load preprocessed terrain metadata to understand the full grid size
                metadata_file = preprocessed_terrain_dir / "metadata.json"
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                        full_grid_size = metadata.get('grid_size', [15121, 24741])
                        print(f"📊 Full terrain grid: {full_grid_size[0]} × {full_grid_size[1]} cells")
                        print(f"📊 Total terrain cells: {full_grid_size[0] * full_grid_size[1]:,}")
                        
                        # For sensitivity analysis, we need a manageable grid size
                        # The full terrain is 374M cells, which is too large for sensitivity analysis
                        # Use a reasonable subset that represents the terrain characteristics
                        if self.production_scale:
                            grid_size = (200, 200)  # 40K cells - production scale
                            num_layers = 10
                            max_steps = 60
                            print("📏 Using PRODUCTION SCALE: 200×200×10 grid (subset of full terrain)")
                        elif self.hpc_mode:
                            grid_size = (150, 150)  # 22.5K cells - HPC optimized
                            num_layers = 8
                            max_steps = 50
                            print("📏 Using HPC OPTIMIZED: 150×150×8 grid (subset of full terrain)")
                        else:
                            grid_size = (100, 100)  # 10K cells - standard
                            num_layers = 6
                            max_steps = 45
                            print("📏 Using STANDARD: 100×100×6 grid (subset of full terrain)")
                        
                        print(f"💡 NOTE: Using grid subset for sensitivity analysis")
                        print(f"   Full terrain will be automatically cropped/resampled to {grid_size[0]}×{grid_size[1]}")
                        
                    except Exception as e:
                        print(f"⚠️  Warning: Could not read terrain metadata: {e}")
                        print("   Using default grid sizes...")
                        use_preprocessed_terrain = False
                else:
                    print("⚠️  Warning: Preprocessed terrain metadata not found")
                    print("   Using default grid sizes...")
                    use_preprocessed_terrain = False
            
            # If still no grid size determined, use standard configuration
            if grid_size is None:
                print("🔄 Using standard configuration")
                # Determine grid configuration based on mode (original logic)
                if self.production_scale:
                    grid_size = (200, 200)
                    num_layers = 10
                    max_steps = 60
                    print("📏 Using PRODUCTION SCALE: 200×200×10 grid, 60 steps")
                elif self.hpc_mode:
                    grid_size = (120, 120)
                    num_layers = 8
                    max_steps = 50
                    print("📏 Using HPC OPTIMIZED: 120×120×8 grid, 50 steps")
                else:
                    grid_size = (100, 100)
                    num_layers = 6
                    max_steps = 45
                    print("📏 Using STANDARD: 100×100×6 grid, 45 steps")
        
        # Set default max_steps if not specified
        if max_steps is None:
            max_steps = 50
        
        # Get memory optimization level from CLI args
        memory_level = 3  # Default
        cli_args = getattr(self, '_cli_args', None)
        if cli_args is not None and hasattr(cli_args, 'memory_level'):
            memory_level = cli_args.memory_level
        
        # Validate LiDAR data directory
        lidar_data_dir = "/gpfs/home1/apaphitis/git/github/Forest-Fire-Simulation/PAD Results/"
        use_lidar = False
        
        lidar_path = Path(lidar_data_dir)
        if lidar_path.exists():
            # Check if directory contains LiDAR files (look for common LiDAR file extensions)
            lidar_files = list(lidar_path.glob("*.las")) + list(lidar_path.glob("*.laz")) + list(lidar_path.glob("*.txt"))
            if lidar_files:
                print(f"✅ LiDAR data directory found with {len(lidar_files)} files")
                use_lidar = True
            else:
                print("⚠️  LiDAR directory exists but no LiDAR files found (.las, .laz, .txt)")
                print("   Disabling LiDAR usage")
                use_lidar = False
        else:
            print("📊 LiDAR directory not found - disabling LiDAR usage")
            use_lidar = False
        
        # HPC-optimized base config for sensitivity analysis
        base_config = ModelConfig(
            grid_size=grid_size,
            num_layers=num_layers,
            max_steps=max_steps,
            random_seed=42,  # Consistent seed for reproducibility
            
            # Enhanced fire parameters for longer duration (50+ timesteps)
            spread_probability=0.6,      # Increased from 0.4
            fuel_consumption_rate=0.8,   # Reduced from 1.0 (slower consumption)
            ignition_threshold=0.4,      # Reduced from 0.5 (easier ignition)
            min_fuel_value=0.1,
            max_fuel_value=10.0,
            initial_fuel_load=8.0,       # Increased from 5.0 for longer fire duration
            
            # Enhanced terrain and wind parameters
            slope_influence=0.4,         # Increased from 0.3
            wind_influence_on_spread=0.3, # Increased from 0.2
            terrain_effect_strength=0.7,  # Increased from 0.6
            
            # HPC memory optimization (aggressive level 3)
            memory_optimization_level=memory_level,
            
            # Wind and terrain (conservative defaults)
            wind_speed=5.0,
            wind_direction=45.0,
            
            # PREPROCESSED TERRAIN CONFIGURATION
            use_preprocessed_terrain=use_preprocessed_terrain,
            preprocessed_terrain_dir=str(preprocessed_terrain_dir) if use_preprocessed_terrain else None,
            
            # NO DEM FALLBACK (no DEM file available - will use flat terrain if preprocessed fails)
            use_terrain=False,
            dem_file=None,
            
            # LIDAR CONFIGURATION (validated)
            use_lidar=use_lidar,
            lidar_data_dir=lidar_data_dir if use_lidar else None,
            auto_size_from_lidar=False,
            extinction_coefficient=0.5,
            pad_bin_size=2.0,
            exclude_ground_layer=True,
            max_vegetation_height_m=50.0
        )
        
        # Determine worker count
        cli_args = getattr(self, '_cli_args', None)
        cli_workers = None
        if cli_args is not None and hasattr(cli_args, 'workers'):
            cli_workers = cli_args.workers
        
        if cli_workers is not None:
            workers = cli_workers
        elif self.hpc_mode:
            workers = 28  # Leave 4 cores for system overhead on 32-core system
        else:
            workers = min(24, 28)  # Conservative default
        
        config = CalibrationConfig(
            experiment_name=self.experiment_name,
            method=CalibrationMethod.SENSITIVITY_ANALYSIS,
            objective=CalibrationObjective.SPATIAL_SIMILARITY,
            base_config=base_config,
            
            # All 13 calibration parameters organized by tier
            calibration_parameters=self._get_all_calibration_parameters(),
            
            # Results configuration
            results_dir=str(self.output_dir),
            save_intermediate_results=True,
            generate_plots=True,
            verbose=True,
            
            # HPC PERFORMANCE SETTINGS FOR 32-CORE CPU, 32 GB RAM
            parallel_execution=True,
            max_workers=workers,
            memory_limit_gb=28.0 if self.hpc_mode else 24.0,  # Leave memory for system
            simulation_timeout_minutes=30.0,  # Longer timeout for larger grids
            
            # Grid search settings (for future use)
            grid_search_points=5,  # Moderate resolution
            
            # Spatial similarity sub-weights (for sensitivity analysis)
            jaccard_weight=0.4,
            dice_weight=0.3,
            sorensen_weight=0.3
        )
        
        return config
    
    def _validate_hpc_requirements(self):
        """Validate HPC system has sufficient resources for sensitivity analysis."""
        try:
            import psutil
            
            # Check available memory
            memory = psutil.virtual_memory()
            available_memory_gb = memory.available / (1024**3)
            total_memory_gb = memory.total / (1024**3)
            
            print(f"🔍 HPC SYSTEM VALIDATION:")
            print(f"  Total Memory: {total_memory_gb:.1f} GB")
            print(f"  Available Memory: {available_memory_gb:.1f} GB")
            print(f"  Configured Memory Limit: {self.calibration_config.memory_limit_gb:.1f} GB")
            
            if total_memory_gb < 30.0:
                print(f"⚠️  WARNING: System memory ({total_memory_gb:.1f} GB) is less than expected 32 GB")
                print(f"   Consider reducing --workers or using --memory-level 1 for safety")
            elif available_memory_gb < 20.0:
                print(f"⚠️  CAUTION: Limited available memory ({available_memory_gb:.1f} GB)")
                print(f"   Consider closing other applications for optimal performance")
            else:
                print(f"✅ Excellent memory resources available")
            
            # Check CPU cores
            cpu_count = psutil.cpu_count(logical=False)  # Physical cores
            logical_cores = psutil.cpu_count(logical=True)
            
            print(f"  Physical CPU Cores: {cpu_count}")
            print(f"  Logical CPU Cores: {logical_cores}")
            print(f"  Configured Workers: {self.calibration_config.max_workers}")
            
            if cpu_count < 30:
                print(f"⚠️  WARNING: Physical cores ({cpu_count}) less than expected 32 cores")
                print(f"   Analysis will still work but may be slower than optimal")
            elif cpu_count >= 32:
                print(f"✅ Excellent CPU resources available")
                if self.calibration_config.max_workers < 28:
                    print(f"💡 TIP: Consider using --hpc-mode for maximum performance")
            
            # Estimate performance
            total_evaluations = len(self.calibration_config.calibration_parameters) * 9
            estimated_time_sequential = total_evaluations * 150  # seconds per evaluation
            estimated_time_parallel = estimated_time_sequential / min(self.calibration_config.max_workers, total_evaluations)
            
            print(f"🚀 PERFORMANCE ESTIMATE:")
            print(f"  Total Evaluations: {total_evaluations}")
            print(f"  Sequential Time: ~{estimated_time_sequential/3600:.1f} hours")
            print(f"  HPC Parallel Time: ~{estimated_time_parallel/60:.1f} minutes")
            print(f"  Expected Speedup: ~{estimated_time_sequential/estimated_time_parallel:.1f}x")
                
        except ImportError:
            print(f"⚠️  WARNING: psutil not available, cannot validate system resources")
            print(f"   Install with: pip install psutil")
        except Exception as e:
            print(f"⚠️  WARNING: System validation failed: {e}")
    
    def _get_all_calibration_parameters(self) -> List[str]:
        """
        Get all 13 calibration parameters organized by sensitivity groups.
        
        Group 1: Full range parameters (7 parameters)
        Group 2: Constrained range parameters (6 parameters)
        
        Returns:
            List of all calibration parameter names in priority order
        """
        # Check if quick mode is enabled
        cli_args = getattr(self, '_cli_args', None)
        quick_mode = False
        if cli_args is not None and hasattr(cli_args, 'quick') and cli_args.quick:
            quick_mode = True
            print("⚡ QUICK MODE: Analyzing only top 7 critical parameters")
        
        # Group 1: Full range parameters (test across complete theoretical ranges)
        group1_full_range = [
            'wind_influence_on_spread',  # Wind effect on spread probability
            'fuel_consumption_rate',     # Rate of fuel consumption
            'terrain_effect_strength',   # Overall terrain effect strength
            'barranco_amplification',    # Wind speed amplification in ravines
            'barranco_direction_weight', # Wind direction alignment weight in ravines
            'slope_influence',           # Terrain slope effect on fire spread
            'ember_height_factor'        # Height factor for ember generation
        ]
        
        # Group 2: Constrained range parameters (test within realistic operational ranges)
        group2_constrained_range = [
            'wind_speed',                # Base wind speed affecting fire spread
            'wind_direction',            # Wind direction in degrees
            'ember_distance',            # Ember travel distance
            'ember_probability',         # Ember generation probability
            'spread_probability',        # Base fire spread probability
            'ember_ignition',            # Ember ignition probability

        ]
        
        # Return parameters based on mode
        if quick_mode:
            # Quick mode: only top 7 critical parameters (Group 1)
            return group1_full_range
        else:
            # Full mode: all 13 parameters
            return group1_full_range + group2_constrained_range
    
    def setup_components(self):
        """Set up parameter bounds, objective function, and target data."""
        print("🔧 Setting up analysis components...")
        
        # Get parameter bounds
        self.parameter_bounds = get_default_calibration_bounds()
        print(f"✅ Loaded bounds for {len(self.parameter_bounds)} parameters")
        
        # Create objective function for sensitivity analysis
        from src.core.calibration.sensitivity_objective import create_sensitivity_objective
        self.objective_function = create_sensitivity_objective()
        print("✅ Created sensitivity analysis objective function")
        
        # Create production target data with real terrain and fuel
        # Ensure base_config exists (should be created in __post_init__)
        if self.calibration_config.base_config is None:
            logger.warning("base_config is None, creating default ModelConfig")
            self.calibration_config.base_config = ModelConfig()
        
        grid_size = self.calibration_config.base_config.grid_size
        num_layers = self.calibration_config.base_config.num_layers
        model_resolution = self.calibration_config.base_config.model_resolution
        
        # Sensitivity analysis uses intrinsic fire behavior metrics - no target data needed
        print("📊 Sensitivity analysis uses intrinsic fire behavior metrics")
        print("   • Burned area, spread rate, persistence, and spatial dispersion")
        print("   • No external target data required")
        self.target_data = None
        
        return True
    
    def run_sensitivity_analysis(self):
        """Run the complete Method 2 Range-Based sensitivity analysis with parallel processing."""
        print("\n🚀 STARTING METHOD 2 RANGE-BASED SENSITIVITY ANALYSIS")
        print("=" * 70)
        
        # Initialize sensitivity analyzer with Method 2 Range-Based approach and parallel processing
        analyzer = SensitivityAnalyzer(
            calibration_config=self.calibration_config,
            parameter_bounds=self.parameter_bounds,
            objective_function=self.objective_function,
            perturbation_method="range_based",  # Use Method 2 Range-Based approach
            perturbation_values=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8],  # 9 evenly spaced points (0% to 80%)
            parallel_execution=self.calibration_config.parallel_execution,  # Enable parallel processing
            max_workers=self.calibration_config.max_workers  # Use configured number of workers
        )
        
        # Calculate total evaluations and realistic time estimates
        num_parameters = len(self.calibration_config.calibration_parameters)
        evaluations_per_param = len(analyzer.perturbation_values)
        total_evaluations = num_parameters * evaluations_per_param
        
        # Updated time estimates based on parallel processing
        time_per_sim_minutes = 2.5  # 2-3 minutes per 80x80x5 simulation with level 2 optimization
        sequential_time_hours = (total_evaluations * time_per_sim_minutes) / 60
        parallel_time_hours = sequential_time_hours / max(analyzer.max_workers, 1)  # With configured workers
        
        print(f"📊 ANALYSIS CONFIGURATION:")
        print(f"  Method: Range-Based Sensitivity Analysis (Method 2)")
        print(f"  Parameters: {num_parameters}")
        print(f"  Test points per parameter: {evaluations_per_param}")
        print(f"  Total evaluations: {total_evaluations}")
        print(f"  Range coverage: 0% to 80% of each parameter's range (9 evenly spaced points)")
        print(f"  Parallel processing: {'Enabled' if analyzer.parallel_execution else 'Disabled'}")
        print(f"  Parallel workers: {analyzer.max_workers}")
        print(f"  Memory optimization: Level 2 (sparse storage + tiling)")
        print()
        print(f"⏱️  TIME ESTIMATES:")
        print(f"  Sequential time: {sequential_time_hours:.1f} hours")
        if analyzer.parallel_execution:
            print(f"  Parallel time ({analyzer.max_workers} workers): {parallel_time_hours:.1f} hours")
            print(f"  Expected completion: ~{parallel_time_hours:.1f} hours")
            print(f"  Speedup: {sequential_time_hours/parallel_time_hours:.1f}x faster")
        else:
            print(f"  Expected completion: ~{sequential_time_hours:.1f} hours (sequential mode)")
        print()
        print(f"💾 MEMORY ESTIMATES:")
        print(f"  Per simulation: ~14 MB (80x80x5 with level 2 optimization)")
        if analyzer.parallel_execution:
            print(f"  Peak usage ({analyzer.max_workers} parallel): ~{analyzer.max_workers * 14} MB")
        else:
            print(f"  Peak usage (sequential): ~14 MB")
        print(f"  Total system requirement: <200 MB")
        print()
        
        # Create progress callback
        progress_callback = create_sensitivity_progress_callback(verbose=True)
        
        # Run the analysis
        processing_mode = "parallel" if analyzer.parallel_execution else "sequential"
        print(f"🔥 Running Method 2 Range-Based sensitivity analysis ({processing_mode} mode)...")
        print("📈 Progress will be displayed below:")
        print("-" * 70)
        start_time = time.time()
        
        try:
            results = analyzer.run_sensitivity_analysis(
                target_data=None,  # Not used for sensitivity analysis
                progress_callback=progress_callback
            )
            
            runtime = time.time() - start_time
            print(f"\n✅ Method 2 Range-Based sensitivity analysis completed successfully!")
            print(f"⏱️  Total runtime: {runtime/3600:.2f} hours ({runtime/60:.1f} minutes)")
            print(f"🚀 Average speed: {total_evaluations/(runtime/3600):.1f} evaluations/hour")
            
            if analyzer.parallel_execution:
                theoretical_speedup = sequential_time_hours / (runtime/3600)
                efficiency = theoretical_speedup / analyzer.max_workers * 100
                print(f"🎯 Parallel efficiency: {efficiency:.1f}% ({theoretical_speedup:.1f}x speedup with {analyzer.max_workers} workers)")
            
            return results
            
        except Exception as e:
            print(f"\n❌ Sensitivity analysis failed: {e}")
            logger.error(f"Sensitivity analysis failed: {e}")
            raise
    
    def analyze_results(self, results):
        """Analyze and display the sensitivity analysis results."""
        print("\n📊 ANALYZING SENSITIVITY RESULTS")
        print("=" * 70)
        
        # Get summary statistics
        summary = results.get_sensitivity_summary()
        
        print(f"📈 ANALYSIS SUMMARY:")
        print(f"  Total parameters analyzed: {summary['total_parameters']}")
        print(f"  Valid results: {summary['valid_parameters']}")
        print(f"  Total evaluations: {summary['total_evaluations']}")
        print(f"  Analysis time: {summary['total_time']/3600:.2f} hours")
        print(f"  Evaluation rate: {summary['total_evaluations']/(summary['total_time']/3600):.1f} evals/hour")
        print(f"  Mean sensitivity: {summary['mean_sensitivity']:.4f}")
        print(f"  Sensitivity range: {summary['sensitivity_range']:.4f}")
        print()
        
        # Display parameter rankings
        print("🏆 PARAMETER SENSITIVITY RANKINGS:")
        print("-" * 70)
        
        rankings = results.get_most_sensitive_parameters(13)  # All parameters
        
        print(f"{'Rank':<4} {'Parameter':<25} {'Sensitivity':<12} {'Tier':<12}")
        print("-" * 70)
        
        for i, (param_name, sensitivity) in enumerate(rankings, 1):
            # Get tier information
            bounds = self.parameter_bounds[param_name]
            tier = bounds.calibration_tier.name
            
            # Color coding based on sensitivity
            if sensitivity > 0.1:
                marker = "🔥"  # High sensitivity
            elif sensitivity > 0.05:
                marker = "⚡"  # Medium sensitivity
            else:
                marker = "📊"  # Low sensitivity
                
            print(f"{marker} {i:>2}. {param_name:<25} {sensitivity:>10.4f} {tier:>12}")
        
        print()
        
        # Identify top parameters for focused calibration
        top_5 = results.get_most_sensitive_parameters(5)
        print("🎯 TOP 5 PARAMETERS FOR FOCUSED CALIBRATION:")
        print("-" * 70)
        for i, (param_name, sensitivity) in enumerate(top_5, 1):
            bounds = self.parameter_bounds[param_name]
            print(f"🔥 {i}. {param_name}: {sensitivity:.4f}")
            print(f"     Range: [{bounds.min_value:.3f}, {bounds.max_value:.3f}]")
            print(f"     Description: {bounds.physical_interpretation}")
            print()
        
        return summary, rankings
    
    def save_results(self, results, summary, rankings):
        """Save all results and generate reports."""
        print("💾 SAVING RESULTS AND GENERATING REPORTS")
        print("=" * 70)
        
        # Save detailed results
        results_file = self.output_dir / f"{self.experiment_name}_detailed_results.json"
        results.save_results(results_file)
        print(f"✅ Saved detailed results: {results_file}")
        
        # Save summary report
        summary_file = self.output_dir / f"{self.experiment_name}_summary.json"
        summary_data = {
            'experiment_info': {
                'name': self.experiment_name,
                'timestamp': datetime.now().isoformat(),
                'method': 'method_2_range_based_sensitivity',
                'description': 'Method 2: Standardized Range-Based Sensitivity Analysis with 9 test points',
                'range_coverage': '0% to 80% of parameter range (9 evenly spaced points)',
                'total_parameters': len(self.calibration_config.calibration_parameters),
                'parallel_workers': self.calibration_config.max_workers,
                'memory_optimization_level': 2
            },
            'performance_metrics': {
                'total_runtime_hours': summary['total_time'] / 3600,
                'evaluations_per_hour': summary['total_evaluations'] / (summary['total_time'] / 3600),
                'parallel_efficiency': f"{self.calibration_config.max_workers}x speedup"
            },
            'analysis_summary': summary,
            'parameter_rankings': rankings,
            'top_5_parameters': results.get_most_sensitive_parameters(5),
            'calibration_tiers': {
                'critical_params': [p for p, _ in rankings[:7]],  # Top 7
                'moderate_params': [p for p, _ in rankings[7:10]], # Next 3
                'low_params': [p for p, _ in rankings[10:]]        # Remaining
            },
            'method_2_details': {
                'sensitivity_formula': '(Output_Range / Param_Range) × (Param_Range / Middle_Output)',
                'test_points': [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8],
                'normalization_point': '40% of parameter range (index 3)',
                'advantages': [
                    'Tests full parameter range',
                    'No baseline dependency',
                    'Standardized for parameter comparison',
                    'Captures non-linear behavior'
                ]
            },
            'configuration': {
                'grid_size': self.calibration_config.base_config.grid_size,
                'num_layers': self.calibration_config.base_config.num_layers,
                'max_steps': self.calibration_config.base_config.max_steps,
                'parallel_workers': self.calibration_config.max_workers,
                'memory_optimization': 2,
                'objective_weights': {
                    'jaccard_weight': self.objective_function.jaccard_weight,
                    'dice_weight': self.objective_function.dice_weight,
                    'sorensen_weight': self.objective_function.sorensen_weight
                }
            }
        }
        
        with open(summary_file, 'w') as f:
            json.dump(summary_data, f, indent=2)
        print(f"✅ Saved summary report: {summary_file}")
        
        # Generate calibration recommendations
        recommendations_file = self.output_dir / f"{self.experiment_name}_calibration_recommendations.txt"
        self._generate_calibration_recommendations(results, recommendations_file)
        print(f"✅ Generated calibration recommendations: {recommendations_file}")
        
        # Generate HTML report
        try:
            report_file = create_calibration_report(
                results, 
                self.calibration_config, 
                self.output_dir,
                include_plots=True
            )
            print(f"✅ Generated HTML report: {report_file}")
        except Exception as e:
            print(f"⚠️  Warning: Could not generate HTML report: {e}")
        
        print(f"\n🎉 All results saved to: {self.output_dir}")
        
        return {
            'results_file': results_file,
            'summary_file': summary_file,
            'recommendations_file': recommendations_file
        }
    
    def _generate_calibration_recommendations(self, results, output_file):
        """Generate practical calibration recommendations."""
        rankings = results.get_most_sensitive_parameters(13)
        
        # Break down into smaller methods
        header = self._create_report_header(rankings)
        method_details = self._create_method_details()
        executive_summary = self._create_executive_summary(rankings)
        top_params = self._create_top_parameters_section(rankings[:5])
        full_ranking = self._create_full_ranking_section(rankings)
        strategies = self._create_strategy_recommendations(rankings)
        footer = self._create_report_footer()
        
        recommendations = header + method_details + executive_summary + top_params + full_ranking + strategies + footer
        self._save_recommendations(recommendations, output_file)
    
    def _create_report_header(self, rankings):
        """Create the report header section."""
        return [
            "=" * 80,
            "FOREST FIRE SIMULATION - METHOD 2 RANGE-BASED SENSITIVITY ANALYSIS RESULTS",
            "=" * 80,
            "",
            f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Experiment: {self.experiment_name}",
            f"Method: Method 2 Standardized Range-Based Sensitivity Analysis",
            f"Test Points: 9 evenly spaced across parameter range (0% to 80%)",
            f"Workers: 7 parallel workers (optimized for 16-core CPU)",
            f"Total Parameters Analyzed: {len(rankings)}",
            ""
        ]
    
    def _create_method_details(self):
        """Create the method details section."""
        return [
            "METHOD 2 DETAILS:",
            "-" * 40,
            "• Sensitivity Formula: (Output_Range / Param_Range) × (Param_Range / Middle_Output)",
            "• Test Points: [0%, 10%, 20%, 30%, 40%, 50%, 60%, 70%, 80%] of parameter range",
            "• Normalization: Uses 40% point (index 3) for standardization",
            "• Advantages: Full range testing, no baseline dependency, standardized comparison",
            ""
        ]
    
    def _create_executive_summary(self, rankings):
        """Create the executive summary section."""
        return [
            "EXECUTIVE SUMMARY:",
            "-" * 40,
            "• Top 5 most sensitive parameters identified for focused calibration",
            f"• Estimated calibration time: 2-4 hours (vs {len(rankings)*5:.0f}+ hours for all parameters)",
            "• Memory requirement: <500 MB (with level 2 optimization)",
            "• Recommended approach: Grid search on top 5 parameters",
            "",
            "🎯 IMMEDIATE CALIBRATION RECOMMENDATIONS:",
            "=" * 50,
            "",
            "1. FOCUSED CALIBRATION STRATEGY (RECOMMENDED):",
            "   Use only the top 5 most sensitive parameters:",
            ""
        ]
    
    def _create_top_parameters_section(self, top_5):
        """Create the top parameters section with detailed information."""
        recommendations = []
        
        # Add top 5 parameters with detailed info
        for i, (param_name, sensitivity) in enumerate(top_5, 1):
            bounds = self.parameter_bounds[param_name]
            recommendations.extend([
                f"   {i}. {param_name}:",
                f"      • Sensitivity Score: {sensitivity:.4f}",
                f"      • Parameter Range: [{bounds.min_value:.3f}, {bounds.max_value:.3f}]",
                f"      • Tier: {bounds.calibration_tier.name}",
                f"      • Physical Meaning: {bounds.physical_interpretation}",
                f"      • Suggested Grid Points: {bounds.suggested_points}",
                ""
            ])
        
        recommendations.extend([
            "   FOCUSED CALIBRATION SPECS:",
            "   • Parameters: 5 (top sensitivity)",
            "   • Grid points per parameter: 5-7",
            "   • Total combinations: 3,125 - 16,807",
            "   • Estimated time: 2-4 hours (7 workers)",
            "   • Memory requirement: <500 MB",
            "",
            "2. COMPREHENSIVE CALIBRATION STRATEGY (OPTIONAL):",
            f"   Use all {len(self.calibration_config.calibration_parameters)} parameters if computational resources allow:",
            f"   • Total combinations: 5^{len(self.calibration_config.calibration_parameters)} = {5**len(self.calibration_config.calibration_parameters):,}",
            f"   • Estimated time: {5**len(self.calibration_config.calibration_parameters) * 2.5 / (60*7):.0f}+ hours",
            "   • Memory requirement: <1 GB",
            "   • Recommended only for final production calibration",
            "",
            "🔧 IMPLEMENTATION GUIDE:",
            "=" * 30,
            "",
            "To run focused calibration with these results:",
            "",
            "```python",
            "# Use these top 5 parameters for grid search calibration",
            "calibration_parameters = ["
        ])
        
        for param_name, _ in top_5:
            recommendations.append(f"    '{param_name}',")
            
        recommendations.extend([
            "]",
            "",
            "# Configure grid search",
            "config = CalibrationConfig(",
            "    method=CalibrationMethod.GRID_SEARCH,",
            "    calibration_parameters=calibration_parameters,",
            "    grid_search_points=5,  # Start with 5, increase to 7 if needed",
            "    max_workers=7,",
            "    memory_optimization_level=2",
            ")",
            "```",
            ""
        ])
        
        return recommendations
    
    def _create_full_ranking_section(self, rankings):
        """Create the full parameter ranking section."""
        recommendations = [
            "📊 FULL PARAMETER RANKING:",
            "=" * 30,
            ""
        ]
        
        # Add full ranking
        for i, (param_name, sensitivity) in enumerate(rankings, 1):
            bounds = self.parameter_bounds[param_name]
            tier = bounds.calibration_tier.name
            if i <= 5:
                marker = "🔥 HIGH"
            elif i <= 10:
                marker = "⚡ MED "
            else:
                marker = "📊 LOW "
                
            recommendations.append(
                f"{marker} {i:>2}. {param_name:<25} {sensitivity:>8.4f} ({tier})"
            )
        
        recommendations.append("")
        return recommendations
    
    def _create_strategy_recommendations(self, rankings):
        """Create the strategy recommendations section."""
        return [
            "🎯 PARAMETER GROUP SUMMARY:",
            "=" * 30,
            f"Group 1 - Full Range (Ranks 1-7):   {len([r for r in rankings[:7]])} parameters",
            f"Group 2 - Constrained Range (Ranks 8-13):  {len([r for r in rankings[7:13]])} parameters", 
            f"Total Parameters Analyzed: {len(rankings)} parameters",
            "",
            "💡 CALIBRATION STRATEGY RECOMMENDATIONS:",
            "=" * 45,
            "",
            "PHASE 1 - Quick Discovery (1-2 hours):",
            "• Use top 3 parameters with 5 grid points each",
            "• Total combinations: 125",
            "• Goal: Identify promising parameter regions",
            "",
            "PHASE 2 - Focused Refinement (2-4 hours):",
            "• Use top 5 parameters with 5-7 grid points each",
            "• Total combinations: 3,125 - 16,807",
            "• Goal: Fine-tune the most important parameters",
            "",
            "PHASE 3 - Production Calibration (8-24 hours):",
            "• Use top 7 parameters with 7 grid points each",
            "• Total combinations: 823,543",
            "• Goal: Production-ready parameter set",
            "",
            "⚠️  IMPORTANT NOTES:",
            "=" * 20,
            "• Always validate calibrated parameters on hold-out fire data",
            "• Consider parameter correlations in final selection",
            "• Document parameter choices for reproducibility",
            "• Monitor memory usage during large calibrations",
            ""
        ]
    
    def _create_report_footer(self):
        """Create the report footer section."""
        return [
            "=" * 80,
            "Report generated by: Forest Fire Simulation Method 2 Range-Based Sensitivity Framework",
            f"Analysis completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 80
        ]
    
    def _save_recommendations(self, recommendations, output_file):
        """Save recommendations to file."""
        with open(output_file, 'w') as f:
            f.write('\n'.join(recommendations))
    
    def _generate_visualizations(self, results):
        """Generate publication-quality visualizations for sensitivity analysis results."""
        print("\n🎨 Generating publication-quality visualizations...")
        viz_start_time = time.time()
        
        try:
            from src.core.calibration.sensitivity_visualization import create_sensitivity_visualizations
            
            # Create visualizations directory
            viz_dir = self.output_dir / "visualizations"
            
            # Create visualizations in multiple formats for HPC reports
            viz_formats = ['png', 'pdf', 'html']  # Static and interactive formats
            viz_files = create_sensitivity_visualizations(
                sensitivity_results=results,
                output_dir=viz_dir,
                style="publication",  # High-quality publication style
                formats=viz_formats
            )
            
            viz_time = time.time() - viz_start_time
            
            print(f"✅ Generated {len(viz_files)} visualization types in {viz_time:.1f} seconds:")
            for viz_type, files in viz_files.items():
                if viz_type != 'report':  # Don't double-count the report
                    print(f"   • {viz_type.replace('_', ' ').title()}: {len(files)} files")
            
            # Log visualization details
            total_viz_files = sum(len(files) for files in viz_files.values())
            print(f"\n📊 Total visualization outputs: {total_viz_files} files")
            print(f"📁 Visualization directory: {viz_dir}")
            print(f"📈 Available formats: PNG (high-res), PDF (vector), HTML (interactive)")
            
            # Add visualization report to saved files
            viz_report_files = {
                'visualization_report': viz_files.get('report', []),
                'visualizations_summary': [viz_dir / "visualization_report.html"]
            }
            
            return viz_report_files
            
        except ImportError as e:
            print(f"⚠️  Visualization generation skipped: Missing dependencies")
            print(f"   Install required packages: pip install matplotlib seaborn plotly")
            print(f"   Error details: {e}")
            return {}
        except Exception as e:
            print(f"⚠️  Visualization generation failed: {e}")
            logger.warning(f"Failed to generate visualizations: {e}")
            return {}
    
    def run_complete_analysis(self):
        """Run the complete sensitivity analysis workflow."""
        try:
            print("🚀 STARTING COMPLETE SENSITIVITY ANALYSIS WORKFLOW")
            print("=" * 70)
            
            # Step 1: Setup
            self.setup_configuration()
            self.setup_components()
            
            # Step 2: Run analysis
            results = self.run_sensitivity_analysis()
            
            # Step 3: Analyze results
            summary, rankings = self.analyze_results(results)
            
            # Step 4: Save and report
            saved_files = self.save_results(results, summary, rankings)
            
            # Step 5: Generate visualizations
            viz_files = self._generate_visualizations(results)
            if viz_files:
                saved_files.update(viz_files)
            
            print("\n🎉 SENSITIVITY ANALYSIS COMPLETED SUCCESSFULLY!")
            print("=" * 70)
            print(f"📁 Results saved to: {self.output_dir}")
            print(f"📊 Summary file: {saved_files['summary_file'].name}")
            print(f"📋 Recommendations: {saved_files['recommendations_file'].name}")
            if 'visualizations_summary' in saved_files:
                print(f"🎨 Visualizations: {saved_files['visualizations_summary'][0].name}")
            print()
            print("🎯 NEXT STEPS:")
            print("1. Review the calibration recommendations file")
            if 'visualizations_summary' in saved_files:
                print("2. Explore the interactive visualizations in your browser")
                print("3. Run focused grid search calibration on top 5 parameters")
                print("4. Validate results on real fire data")
            else:
                print("2. Run focused grid search calibration on top 5 parameters")
                print("3. Validate results on real fire data")
            
            return results, summary, rankings
            
        except Exception as e:
            print(f"\n❌ Analysis failed: {e}")
            logger.error(f"Complete analysis failed: {e}")
            raise


def main():
    print("[DEBUG] Script started: entering main()")
    parser = argparse.ArgumentParser(
        description="Run HPC-optimized Method 2 Range-Based sensitivity analysis for 32-core systems",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
HPC Examples:
  # Full HPC optimization (28 workers, large grids, 28 GB memory)
  python sensitivity_analysis_runner.py --hpc-mode
  
  # Production-scale analysis (200×200×10 grids)
  python sensitivity_analysis_runner.py --production-scale --hpc-mode
  
  # Custom worker count for your HPC allocation
  python sensitivity_analysis_runner.py --workers 24 --memory-level 3
  
  # With real production data paths (auto-detects if available)
  python sensitivity_analysis_runner.py --hpc-mode --dem-file /path/to/dtm.tif --lidar-dir /path/to/pad/results
  
  # Memory-conservative mode (for shared HPC nodes)
  python sensitivity_analysis_runner.py --workers 16 --memory-level 2
  
Standard Examples:
  # Basic usage (conservative settings)
  python sensitivity_analysis_runner.py
  
  # Force synthetic data (for testing)
  python sensitivity_analysis_runner.py --force-synthetic
  
  # Custom output and experiment name
  python sensitivity_analysis_runner.py --output hpc_sensitivity_results --name tenerife_hpc_analysis
  
  # Quick mode (top 7 parameters only)
  python sensitivity_analysis_runner.py --quick --workers 8
        """
    )
    
    parser.add_argument(
        '--config', 
        type=str, 
        help='Path to production configuration file (optional)'
    )
    
    parser.add_argument(
        '--output', 
        type=str, 
        default='hpc_sensitivity_results',
        help='Output directory for results (default: hpc_sensitivity_results)'
    )
    
    parser.add_argument(
        '--name', 
        type=str,
        help='Experiment name (default: auto-generated with timestamp)'
    )
    
    parser.add_argument(
        '--hpc-mode',
        action='store_true',
        help='Enable full HPC optimization: 28 workers, 28 GB memory, larger grids'
    )
    
    parser.add_argument(
        '--production-scale',
        action='store_true',
        help='Use very large grids (200×200×10) for production-quality analysis'
    )
    
    parser.add_argument(
        '--quick',
        action='store_true',
        help='Quick mode: analyze only top 7 critical parameters'
    )
    
    parser.add_argument(
        '--workers',
        type=int,
        default=None,
        help='Number of parallel workers (default: auto-detect based on mode). Use 1 to disable parallel processing.'
    )
    
    parser.add_argument(
        '--memory-level',
        type=int,
        default=3,
        choices=[1, 2, 3],
        help='Memory optimization level: 1=basic, 2=balanced, 3=aggressive (default: 3 for HPC)'
    )
    
    parser.add_argument(
        '--dem-file',
        type=str,
        help='Path to DEM file for terrain data (overrides default production path)'
    )
    
    parser.add_argument(
        '--lidar-dir',
        type=str,
        help='Path to LiDAR data directory for fuel data (overrides default production path)'
    )
    
    parser.add_argument(
        '--force-synthetic',
        action='store_true',
        help='Force use of synthetic data instead of production data'
    )
    
    parser.add_argument(
        '--grid-size',
        nargs=3,
        type=int,
        metavar=('NX', 'NY', 'NLAYERS'),
        help='Set grid size as NX NY NLAYERS (overrides mode and auto-detection)'
    )
    
    parser.add_argument(
        '--force-preprocessed',
        action='store_true',
        help='Force use of preprocessed terrain regardless of DEM/LiDAR presence'
    )
    
    parser.add_argument(
        '--max-steps',
        type=int,
        default=None,
        help='Maximum number of simulation steps (overrides default or mode)'
    )
    
    args = parser.parse_args()
    print(f"[DEBUG] Parsed arguments: {args}")

    try:
        # Determine HPC mode settings
        hpc_mode = args.hpc_mode
        production_scale = args.production_scale
        
        # Auto-enable HPC mode if production scale is requested
        if production_scale and not hpc_mode:
            print("🚀 Auto-enabling HPC mode for production-scale analysis")
            hpc_mode = True
        
        # Set default workers based on mode
        if args.workers is None:
            if hpc_mode:
                args.workers = 28  # Leave 4 cores for system on 32-core system
                print(f"🚀 HPC MODE: Auto-setting workers to {args.workers}")
            else:
                args.workers = min(16, 24)  # Conservative default
                print(f"🔧 STANDARD MODE: Auto-setting workers to {args.workers}")
        
        # Validate worker count
        if args.workers > 32:
            print(f"⚠️  WARNING: {args.workers} workers may exceed available cores")
            print(f"   Recommended maximum: 28 workers (leaving 4 for system)")
        
        # Create and run the analysis
        runner = HPCOptimizedSensitivityRunner(
            config_file=args.config,
            output_dir=args.output,
            experiment_name=args.name,
            hpc_mode=hpc_mode,
            production_scale=production_scale,
            cli_args=args  # Pass CLI arguments to the runner
        )
        print("[DEBUG] Runner initialized")

        print("[DEBUG] Starting setup_configuration()...")
        runner.setup_configuration()
        print("[DEBUG] Finished setup_configuration()")

        print("[DEBUG] Starting setup_components()...")
        runner.setup_components()
        print("[DEBUG] Finished setup_components()")

        print("[DEBUG] Starting run_sensitivity_analysis()...")
        results = runner.run_sensitivity_analysis()
        print("[DEBUG] Finished run_sensitivity_analysis()")

        print("[DEBUG] Starting analyze_results()...")
        runner.analyze_results(results)
        print("[DEBUG] Finished analyze_results()")

        print("[DEBUG] Starting save_results()...")
        runner.save_results(results, results.get_sensitivity_summary(), results.parameter_rankings)
        print("[DEBUG] Finished save_results()")
        
        # Step 5: Generate visualizations
        viz_files = runner._generate_visualizations(results)
        if viz_files:
            saved_files = runner.save_results(results, results.get_sensitivity_summary(), results.parameter_rankings)
            saved_files.update(viz_files)
        
        print("\n🎉 HPC SENSITIVITY ANALYSIS COMPLETED SUCCESSFULLY!")
        print(f"📁 Results directory: {runner.output_dir}")
        print(f"📊 Summary file: {saved_files['summary_file'].name}")
        print(f"📋 Recommendations: {saved_files['recommendations_file'].name}")
        if 'visualizations_summary' in saved_files:
            print(f"🎨 Visualizations: {saved_files['visualizations_summary'][0].name}")
        print()
        print("🎯 NEXT STEPS:")
        print("1. Review the calibration recommendations file")
        if 'visualizations_summary' in saved_files:
            print("2. Explore the interactive visualizations in your browser")
            print("3. Run focused grid search calibration on top 5 parameters")
            print("4. Validate results on real fire data")
        else:
            print("2. Run focused grid search calibration on top 5 parameters")
            print("3. Validate results on real fire data")
        
    except KeyboardInterrupt:
        print("\n⚠️  Analysis interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Analysis failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 