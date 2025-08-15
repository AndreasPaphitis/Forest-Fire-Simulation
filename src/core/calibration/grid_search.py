#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Grid Search Calibrator Module

This module implements systematic grid search calibration for the forest fire simulation.
It explores the parameter space using a grid of points and evaluates each combination
against the specified objective function.

Author: Forest Fire Simulation Team
Date: 2025
Version: 1.0
"""

import time
import itertools
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
import numpy as np
import json

try:
    from src.utils.logging_utils import get_logger
    from src.core.fire_simulation_engine import FireSimulationEngine
    from src.core.forest_model import create_forest_model
except ImportError:
    try:
        from utils.logging_utils import get_logger
        from core.fire_simulation_engine import FireSimulationEngine
        from core.forest_model import create_forest_model
    except ImportError:
        import logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

logger = get_logger(__name__)


@dataclass
class GridSearchResult:
    """Single result from grid search evaluation."""
    parameter_values: Dict[str, float]
    objective_value: float
    objective_components: Dict[str, float]
    simulation_stats: Dict[str, Any]
    evaluation_time: float
    is_valid: bool = True
    error_message: str = ""


@dataclass
class GridSearchResults:
    """Complete results from grid search calibration."""
    results: List[GridSearchResult] = field(default_factory=list)
    best_result: Optional[GridSearchResult] = None
    parameter_space: Dict[str, List[float]] = field(default_factory=dict)
    total_evaluations: int = 0
    successful_evaluations: int = 0
    total_time: float = 0.0
    convergence_info: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Update statistics after initialization."""
        self._update_statistics()
    
    def _update_statistics(self):
        """Update derived statistics."""
        self.total_evaluations = len(self.results)
        self.successful_evaluations = sum(1 for r in self.results if r.is_valid)
        self.total_time = sum(r.evaluation_time for r in self.results)
        
        # Find best result
        valid_results = [r for r in self.results if r.is_valid]
        if valid_results:
            self.best_result = max(valid_results, key=lambda x: x.objective_value)
    
    def add_result(self, result: GridSearchResult):
        """Add a new result and update statistics."""
        self.results.append(result)
        self._update_statistics()
    
    def get_best_parameters(self) -> Optional[Dict[str, float]]:
        """Get the best parameter configuration."""
        return self.best_result.parameter_values if self.best_result else None
    
    def get_best_objective_value(self) -> Optional[float]:
        """Get the best objective value achieved."""
        return self.best_result.objective_value if self.best_result else None
    
    def get_parameter_sensitivity(self) -> Dict[str, Dict[str, float]]:
        """
        Calculate parameter sensitivity based on grid search results.
        
        NOTE: This is a simplified correlation-based sensitivity analysis.
        For comprehensive sensitivity analysis, use the dedicated SensitivityAnalyzer
        from sensitivity_analysis.py which provides more sophisticated analysis.
        
        Returns:
            Dictionary with sensitivity statistics for each parameter
        """
        if not self.results:
            return {}
        
        valid_results = [r for r in self.results if r.is_valid]
        if not valid_results:
            return {}
        
        sensitivity = {}
        
        # Get all parameter names
        param_names = list(valid_results[0].parameter_values.keys())
        
        for param_name in param_names:
            param_values = [r.parameter_values[param_name] for r in valid_results]
            objective_values = [r.objective_value for r in valid_results]
            
            # Calculate correlation between parameter and objective
            correlation = np.corrcoef(param_values, objective_values)[0, 1]
            if np.isnan(correlation):
                correlation = 0.0
            
            # Calculate range of objective values for this parameter
            param_range = max(param_values) - min(param_values)
            obj_range = max(objective_values) - min(objective_values)
            
            sensitivity[param_name] = {
                'correlation': correlation,
                'parameter_range': param_range,
                'objective_range': obj_range,
                'sensitivity_score': abs(correlation) * obj_range / max(param_range, 1e-10)
            }
        
        return sensitivity
    
    def save_results(self, filepath: Union[str, Path]) -> None:
        """Save results to JSON file."""
        filepath = Path(filepath)
        
        # Convert results to serializable format
        results_data = {
            'parameter_space': self.parameter_space,
            'total_evaluations': self.total_evaluations,
            'successful_evaluations': self.successful_evaluations,
            'total_time': self.total_time,
            'convergence_info': self.convergence_info,
            'results': [
                {
                    'parameter_values': r.parameter_values,
                    'objective_value': r.objective_value,
                    'objective_components': r.objective_components,
                    'simulation_stats': r.simulation_stats,
                    'evaluation_time': r.evaluation_time,
                    'is_valid': r.is_valid,
                    'error_message': r.error_message
                }
                for r in self.results
            ]
        }
        
        if self.best_result:
            results_data['best_result'] = {
                'parameter_values': self.best_result.parameter_values,
                'objective_value': self.best_result.objective_value,
                'objective_components': self.best_result.objective_components
            }
        
        with open(filepath, 'w') as f:
            json.dump(results_data, f, indent=2)
        
        logger.info(f"Saved grid search results to {filepath}")
    
    @classmethod
    def load_results(cls, filepath: Union[str, Path]) -> 'GridSearchResults':
        """Load results from JSON file."""
        filepath = Path(filepath)
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Reconstruct results
        results = []
        for r_data in data['results']:
            result = GridSearchResult(**r_data)
            results.append(result)
        
        # Create GridSearchResults instance
        grid_results = cls(
            results=results,
            parameter_space=data['parameter_space'],
            convergence_info=data.get('convergence_info', {})
        )
        
        logger.info(f"Loaded grid search results from {filepath}")
        return grid_results


class GridSearchCalibrator:
    """
    Grid search calibrator for systematic parameter space exploration.
    """
    
    def __init__(self, 
                 calibration_config,
                 parameter_bounds: Dict[str, Any],
                 objective_function,
                 parallel_execution: bool = True,
                 max_workers: Optional[int] = None):
        """
        Initialize grid search calibrator.
        
        Args:
            calibration_config: Calibration configuration
            parameter_bounds: Dictionary of parameter bounds
            objective_function: Objective function to optimize
            parallel_execution: Whether to use parallel evaluation
            max_workers: Maximum number of parallel workers
        """
        self.config = calibration_config
        self.parameter_bounds = parameter_bounds
        self.objective_function = objective_function
        self.parallel_execution = parallel_execution
        
        # MEMORY OPTIMIZATION: Reduce workers for large grids to prevent memory exhaustion
        if max_workers is None:
            # Calculate grid size to determine appropriate worker count
            grid_size = self._get_grid_size_from_config(calibration_config)
            if isinstance(grid_size, (int, float)):
                total_cells = int(grid_size) ** 2
            else:
                total_cells = int(grid_size[0]) * int(grid_size[1])
            
            # Get number of layers
            num_layers = self._get_num_layers_from_config(calibration_config)
            total_model_cells = total_cells * num_layers
            
            # Detect available memory for intelligent worker allocation
            try:
                import psutil
                available_memory_gb = psutil.virtual_memory().total / (1024**3)
            except ImportError:
                available_memory_gb = 64  # Conservative fallback
            
            if available_memory_gb >= 120:  # High-memory HPC environment
                if total_model_cells > 10_000_000_000:  # 10B+ cells
                    self.max_workers = 20  # Generous parallelism for high-memory systems
                    logger.info(f"Very large grid ({total_model_cells:,} cells) on high-memory system - using 20 workers")
                elif total_model_cells > 1_000_000_000:  # 1B+ cells
                    self.max_workers = 30  # Good parallelism
                    logger.info(f"Large grid ({total_model_cells:,} cells) on high-memory system - using 30 workers")
                else:
                    self.max_workers = 40  # Full parallelism for smaller grids
            elif available_memory_gb >= 60:  # Medium-memory environment
                if total_model_cells > 1_000_000_000:  # 1B+ cells (very large)
                    self.max_workers = 8  # Moderate parallelism
                    logger.info(f"Very large grid detected ({total_model_cells:,} cells) - using 8 workers")
                elif total_model_cells > 100_000_000:  # 100M+ cells (large)
                    self.max_workers = 15  # Good parallelism for medium memory
                    logger.info(f"Large grid detected ({total_model_cells:,} cells) - using 15 workers")
                else:
                    self.max_workers = 20  # Good parallelism for smaller grids
            else:  # Low-memory environment - use original conservative approach
                if total_model_cells > 1_000_000_000:  # 1B+ cells (very large)
                    self.max_workers = 1  # Sequential for massive grids
                    logger.warning(f"Very large grid detected ({total_model_cells:,} cells) - using sequential processing")
                elif total_model_cells > 100_000_000:  # 100M+ cells (large)
                    self.max_workers = 2  # Minimal parallelism for large grids
                    logger.info(f"Large grid detected ({total_model_cells:,} cells) - limiting to 2 workers")
                else:
                    self.max_workers = 4  # Standard parallelism for smaller grids
        else:
            # max_workers is explicitly set via CLI - respect user choice but provide safety warnings
            self.max_workers = max_workers
            
            # Calculate grid size for safety warnings
            grid_size = self._get_grid_size_from_config(calibration_config)
            if isinstance(grid_size, (int, float)):
                total_cells = int(grid_size) ** 2
            else:
                total_cells = int(grid_size[0]) * int(grid_size[1])
            
            num_layers = self._get_num_layers_from_config(calibration_config)
            total_model_cells = total_cells * num_layers
            
            # Detect available system memory for safety warnings
            try:
                import psutil
                available_memory_gb = psutil.virtual_memory().total / (1024**3)
                logger.info(f"Detected {available_memory_gb:.1f}GB system memory")
            except ImportError:
                available_memory_gb = 64  # Conservative fallback
                logger.warning("psutil not available, assuming 64GB memory")
            
            # Provide safety warnings but respect CLI choice
            logger.info(f"🎛️  CLI Override: Using {max_workers} workers as explicitly requested")
            logger.info(f"📊 Grid size: {total_model_cells:,} cells on {available_memory_gb:.1f}GB system")
            
            # Safety warnings based on memory vs grid size
            if available_memory_gb < 60 and total_model_cells > 5_000_000_000:
                logger.warning(f"⚠️  WARNING: Large grid ({total_model_cells:,} cells) on low-memory system ({available_memory_gb:.1f}GB)")
                logger.warning(f"⚠️  Consider reducing workers if you encounter memory issues")
            elif available_memory_gb < 120 and total_model_cells > 10_000_000_000:
                logger.warning(f"⚠️  WARNING: Very large grid ({total_model_cells:,} cells) on medium-memory system ({available_memory_gb:.1f}GB)")
                logger.warning(f"⚠️  Monitor memory usage with {max_workers} workers")
            else:
                logger.info(f"✅ Configuration looks good: {max_workers} workers for {total_model_cells:,} cells on {available_memory_gb:.1f}GB")
            
            # Only force sequential for truly extreme cases on low-memory systems
            if available_memory_gb < 32 and total_model_cells > 10_000_000_000 and max_workers > 1:
                logger.error(f"🚨 CRITICAL: Extremely large grid on very low memory system!")
                logger.error(f"🚨 Forcing sequential execution to prevent system crash")
                self.max_workers = 1
                self.parallel_execution = False
        
        # Initialize parameter space
        self.parameter_space = self._create_parameter_space()
        self.total_combinations = self._calculate_total_combinations()
        
        logger.info(f"Initialized grid search with {self.total_combinations} parameter combinations")
        logger.info(f"Worker configuration: {self.max_workers} workers, parallel={self.parallel_execution}")
    
    def _create_parameter_space(self) -> Dict[str, List[float]]:
        """Create the parameter space grid."""
        parameter_space = {}
        
        for param_name in self.config.get_calibration_parameter_names():
            if param_name not in self.parameter_bounds:
                logger.warning(f"No bounds defined for parameter {param_name}, skipping")
                continue
            
            bounds = self.parameter_bounds[param_name]
            
            # Generate grid points for this parameter
            grid_points = bounds.generate_grid_points(self.config.grid_search_points)
            parameter_space[param_name] = grid_points
            
            logger.debug(f"Parameter {param_name}: {len(grid_points)} points from "
                        f"{min(grid_points):.3f} to {max(grid_points):.3f}")
        
        return parameter_space
    
    def _get_grid_size_from_config(self, calibration_config) -> Union[int, Tuple[int, int]]:
        """Get grid size from calibration config, checking both direct and base_config locations."""
        # Try direct access first
        grid_size = getattr(calibration_config, 'grid_size', None)
        if grid_size is not None:
            return grid_size
        
        # Try base_config access
        if hasattr(calibration_config, 'base_config'):
            grid_size = getattr(calibration_config.base_config, 'grid_size', None)
            if grid_size is not None:
                return grid_size
        
        # Default fallback
        return (100, 100)
    
    def _get_num_layers_from_config(self, calibration_config) -> int:
        """Get number of layers from calibration config, checking both direct and base_config locations."""
        # Try direct access first
        num_layers = getattr(calibration_config, 'num_layers', None)
        if num_layers is not None:
            return num_layers
        
        # Try base_config access
        if hasattr(calibration_config, 'base_config'):
            num_layers = getattr(calibration_config.base_config, 'num_layers', None)
            if num_layers is not None:
                return num_layers
        
        # Default fallback
        return 10
    
    def _calculate_total_combinations(self) -> int:
        """Calculate total number of parameter combinations."""
        if not self.parameter_space:
            return 0
        
        total = 1
        for param_values in self.parameter_space.values():
            total *= len(param_values)
        
        return total
    
    def _generate_parameter_combinations(self):
        """Generate all parameter combinations for grid search."""
        param_names = list(self.parameter_space.keys())
        param_value_lists = [self.parameter_space[name] for name in param_names]
        
        for combination in itertools.product(*param_value_lists):
            yield dict(zip(param_names, combination))
    
    def _evaluate_single_combination(self, 
                                   parameter_values: Dict[str, float],
                                   target_data: Optional[Dict[str, Any]] = None) -> GridSearchResult:
        """Evaluate a single parameter combination."""
        start_time = time.time()
        
        try:
            # Create configuration with these parameter values
            config = self.config.create_config_variant(parameter_values)
            
            # SHARED TERRAIN OPTIMIZATION: Ensure shared terrain info is available for memory efficiency
            if hasattr(self.config.base_config, 'shared_terrain_info') and self.config.base_config.shared_terrain_info:
                config.shared_terrain_info = self.config.base_config.shared_terrain_info
                logger.debug(f"Using shared terrain for memory-efficient model creation")
            
            # MEMORY OPTIMIZATION: Add memory checks and error handling for large models
            grid_size = config.grid_size
            if isinstance(grid_size, (int, float)):
                total_cells = int(grid_size) ** 2
            else:
                total_cells = int(grid_size[0]) * int(grid_size[1])
            total_model_cells = total_cells * config.num_layers
            
            if total_model_cells > 1_000_000_000:  # 1B+ cells
                logger.info(f"Creating memory-optimized model for massive grid ({total_model_cells:,} cells)")
            
            # Create forest model and simulation engine with memory optimization
            forest_model = None
            engine = None
            
            try:
                forest_model = create_forest_model(
                    model_type='memory_optimized',  # Use memory optimized for large domains
                    config=config,
                    grid_size=config.grid_size,
                    num_layers=config.num_layers
                )
                
                engine = FireSimulationEngine(forest_model=forest_model, config=config)
                
            except MemoryError as me:
                logger.error(f"Memory error creating model with {total_model_cells:,} cells: {me}")
                raise MemoryError(f"Insufficient memory for grid size {grid_size} with {config.num_layers} layers")
            except Exception as model_error:
                logger.error(f"Error creating model: {model_error}")
                # Clean up partial objects
                if forest_model:
                    del forest_model
                if engine:
                    del engine
                raise
            
            # Set ignition point at Arafo highlands (realistic location for 2023 Tenerife fire)
            ignition_x, ignition_y = self._get_arafo_highlands_coordinates(config.grid_size)
            
            # CRITICAL FIX: Add safety checks before setting ignition
            try:
                logger.info(f"Setting ignition at Arafo highlands: ({ignition_x}, {ignition_y})")
                logger.info(f"Grid bounds: x=0-{config.grid_size[0]-1}, y=0-{config.grid_size[1]-1}")
                
                # Validate coordinates are within bounds
                if not (0 <= ignition_x < config.grid_size[0] and 0 <= ignition_y < config.grid_size[1]):
                    raise ValueError(f"Ignition coordinates ({ignition_x}, {ignition_y}) out of bounds for grid {config.grid_size}")
                
                forest_model.set_ignition(ignition_x, ignition_y, 0)
                logger.info(f"✅ Ignition set successfully at ({ignition_x}, {ignition_y})")
                
            except Exception as ignition_error:
                logger.error(f"❌ CRITICAL: Failed to set ignition point: {ignition_error}")
                logger.error("This may indicate sparse matrix corruption - aborting simulation")
                raise RuntimeError(f"Ignition setting failed: {ignition_error}")
            
            # CRITICAL FIX: Memory safety check before simulation
            try:
                import gc
                gc.collect()  # Clean up before simulation
                logger.info("🚀 Starting simulation with safety monitoring")
                
                # Run simulation with enhanced error handling
                simulation_result = engine.run_simulation(
                    max_steps=config.max_steps,
                    store_history=False,  # Don't store full history for calibration
                    stop_when_fire_extinguished=True
                )
                logger.info("✅ Simulation completed successfully")
                
            except Exception as sim_error:
                logger.error(f"❌ CRITICAL: Simulation failed: {sim_error}")
                logger.error("This indicates issues during fire propagation")
                raise RuntimeError(f"Simulation execution failed: {sim_error}")
            
            # Evaluate objective function
            objective_result = self.objective_function(simulation_result, target_data)
            
            evaluation_time = time.time() - start_time
            
            # Create result before cleanup
            result = GridSearchResult(
                parameter_values=parameter_values.copy(),
                objective_value=objective_result.value,
                objective_components=objective_result.components.copy(),
                simulation_stats=simulation_result['stats'].copy(),
                evaluation_time=evaluation_time,
                is_valid=objective_result.is_valid,
                error_message=objective_result.error_message
            )
            
            # MEMORY OPTIMIZATION: Explicit cleanup for large models
            if total_model_cells > 100_000_000:  # 100M+ cells
                try:
                    # Clear large objects explicitly
                    if hasattr(forest_model, 'terrain_elevation'):
                        forest_model.terrain_elevation = None
                    if hasattr(forest_model, 'wind_direction'):
                        forest_model.wind_direction = None
                    if hasattr(forest_model, 'wind_speed'):
                        forest_model.wind_speed = None
                    if hasattr(forest_model, 'barranco_mask'):
                        forest_model.barranco_mask = None
                    del forest_model
                    del engine
                    del simulation_result
                except Exception as cleanup_error:
                    logger.warning(f"Error during cleanup: {cleanup_error}")
            
            return result
            
        except Exception as e:
            evaluation_time = time.time() - start_time
            logger.warning(f"Evaluation failed for parameters {parameter_values}: {e}")
            
            # MEMORY OPTIMIZATION: Cleanup on error for large models
            try:
                # Try to clean up any partially created objects
                if 'forest_model' in locals() and forest_model is not None:
                    del forest_model
                if 'engine' in locals() and engine is not None:
                    del engine
                if 'simulation_result' in locals():
                    del simulation_result
            except Exception as cleanup_error:
                logger.debug(f"Error during exception cleanup: {cleanup_error}")
            
            return GridSearchResult(
                parameter_values=parameter_values.copy(),
                objective_value=0.0,
                objective_components={},
                simulation_stats={},
                evaluation_time=evaluation_time,
                is_valid=False,
                error_message=str(e)
            )
    
    def run_calibration(self, 
                       target_data: Optional[Dict[str, Any]] = None,
                       progress_callback: Optional[callable] = None) -> GridSearchResults:
        """
        Run the grid search calibration.
        
        Args:
            target_data: Target data for objective function evaluation
            progress_callback: Optional callback for progress updates
            
        Returns:
            GridSearchResults with all evaluation results
        """
        logger.info(f"Starting grid search calibration with {self.total_combinations} combinations")
        start_time = time.time()
        
        results = GridSearchResults(parameter_space=self.parameter_space.copy())
        
        # MEMORY OPTIMIZATION: Force sequential for massive grids to prevent memory exhaustion
        should_run_parallel = self.parallel_execution and self.total_combinations > 1
        
        # Check grid size and disable parallel execution for very large grids
        grid_size = self._get_grid_size_from_config(self.config)
        if isinstance(grid_size, (int, float)):
            total_cells = int(grid_size) ** 2
        else:
            total_cells = int(grid_size[0]) * int(grid_size[1])
        num_layers = self._get_num_layers_from_config(self.config)
        total_model_cells = total_cells * num_layers
        
        # Detect available memory for intelligent parallel execution decision
        try:
            import psutil
            available_memory_gb = psutil.virtual_memory().total / (1024**3)
        except ImportError:
            available_memory_gb = 64  # Conservative fallback
        
        # Check if workers were explicitly set via CLI (respect user choice)
        # max_workers is passed to constructor when CLI specifies --workers
        cli_override = True  # If we reach this point, max_workers was explicitly provided
        
        # Only force sequential for truly extreme cases, and respect CLI overrides
        if should_run_parallel:
            if cli_override:
                # CLI override - respect user choice but provide warnings
                logger.info(f"🎛️  CLI Override: Respecting user-specified {self.max_workers} workers")
                if available_memory_gb < 32 and total_model_cells > 10_000_000_000:
                    logger.error(f"🚨 CRITICAL: Extremely large grid on very low memory - forcing sequential despite CLI override")
                    should_run_parallel = False
                else:
                    logger.info(f"✅ Proceeding with parallel execution as requested")
            else:
                # Auto-detection mode - use intelligent thresholds
                if available_memory_gb >= 120:  # High-memory HPC environment
                    # Allow parallel processing even for very large grids (up to 20B cells)
                    if total_model_cells > 20_000_000_000:
                        logger.warning(f"Extreme grid size ({total_model_cells:,} cells) - forcing sequential execution")
                        should_run_parallel = False
                    else:
                        logger.info(f"High-memory system ({available_memory_gb:.1f}GB) - allowing parallel execution for {total_model_cells:,} cells")
                elif available_memory_gb >= 60:  # Medium-memory environment
                    if total_model_cells > 5_000_000_000:
                        logger.warning(f"Large grid ({total_model_cells:,} cells) on medium-memory system - forcing sequential execution")
                        should_run_parallel = False
                else:  # Low-memory environment - use original conservative limit
                    if total_model_cells > 1_000_000_000:
                        logger.warning(f"Forcing sequential execution for massive grid ({total_model_cells:,} cells) to prevent memory exhaustion")
                        should_run_parallel = False
        
        if should_run_parallel:
            results = self._run_parallel_calibration(target_data, progress_callback, results)
        else:
            results = self._run_sequential_calibration(target_data, progress_callback, results)
        
        total_time = time.time() - start_time
        logger.info(f"Grid search completed in {total_time:.2f} seconds")
        logger.info(f"Best objective value: {results.get_best_objective_value():.4f}")
        logger.info(f"Best parameters: {results.get_best_parameters()}")
        
        # Store convergence information
        results.convergence_info = {
            'converged': True,  # Grid search always completes
            'total_time': total_time,
            'evaluations_per_second': results.total_evaluations / max(total_time, 1e-6),
            'success_rate': results.successful_evaluations / max(results.total_evaluations, 1)
        }
        
        return results
    
    def _run_sequential_calibration(self, 
                                  target_data: Optional[Dict[str, Any]],
                                  progress_callback: Optional[callable],
                                  results: GridSearchResults) -> GridSearchResults:
        """Run calibration sequentially."""
        for i, param_combination in enumerate(self._generate_parameter_combinations()):
            result = self._evaluate_single_combination(param_combination, target_data)
            results.add_result(result)
            
            # Progress callback
            if progress_callback:
                progress_callback(i + 1, self.total_combinations, result)
            
            # Periodic logging
            if (i + 1) % max(1, self.total_combinations // 20) == 0:
                progress = (i + 1) / self.total_combinations * 100
                best_value = results.get_best_objective_value() or 0.0
                logger.info(f"Progress: {progress:.1f}% ({i + 1}/{self.total_combinations}), "
                           f"Best objective: {best_value:.4f}")
        
        return results
    
    def _run_parallel_calibration(self, 
                                target_data: Optional[Dict[str, Any]],
                                progress_callback: Optional[callable],
                                results: GridSearchResults) -> GridSearchResults:
        """Run calibration in parallel."""
        logger.info(f"Running parallel calibration with {self.max_workers} workers")
        
        # Generate all combinations
        combinations = list(self._generate_parameter_combinations())
        
        # MEMORY OPTIMIZATION: Use ThreadPoolExecutor for large grids to avoid process serialization
        # Check grid size to determine executor type
        grid_size = self._get_grid_size_from_config(self.config)
        if isinstance(grid_size, (int, float)):
            total_cells = int(grid_size) ** 2
        else:
            total_cells = int(grid_size[0]) * int(grid_size[1])
        num_layers = self._get_num_layers_from_config(self.config)
        total_model_cells = total_cells * num_layers
        
        if total_model_cells > 100_000_000:  # 100M+ cells
            # Force ThreadPoolExecutor for large grids to avoid process serialization overhead
            executor_class = ThreadPoolExecutor
            logger.info(f"Using ThreadPoolExecutor for large grid ({total_model_cells:,} cells) to avoid serialization overhead")
        else:
            # Use ProcessPoolExecutor for smaller grids for better CPU utilization
            executor_class = ProcessPoolExecutor if self.total_combinations > 50 else ThreadPoolExecutor
        
        # MEMORY SAFETY: Check available memory before starting parallel execution
        try:
            import psutil
            memory_info = psutil.virtual_memory()
            available_gb = memory_info.available / (1024**3)
            total_gb = memory_info.total / (1024**3)
            used_gb = memory_info.used / (1024**3)
            
            logger.info(f"🧠 Memory status before parallel execution:")
            logger.info(f"   Total: {total_gb:.1f}GB, Used: {used_gb:.1f}GB, Available: {available_gb:.1f}GB")
            
            # Estimate memory per worker (conservative)
            estimated_memory_per_worker_gb = 2.0  # Conservative estimate with shared terrain
            total_estimated_gb = self.max_workers * estimated_memory_per_worker_gb
            
            if total_estimated_gb > available_gb * 0.8:  # Use max 80% of available memory
                logger.warning(f"⚠️  HIGH MEMORY RISK: {total_estimated_gb:.1f}GB estimated vs {available_gb:.1f}GB available")
                logger.warning(f"⚠️  Consider reducing workers to {int(available_gb * 0.8 / estimated_memory_per_worker_gb)}")
            else:
                logger.info(f"✅ Memory looks safe: {total_estimated_gb:.1f}GB estimated vs {available_gb:.1f}GB available")
                
        except ImportError:
            logger.warning("⚠️  psutil not available - cannot check memory status")
        
        with executor_class(max_workers=self.max_workers) as executor:
            # Submit all jobs
            future_to_params = {
                executor.submit(self._evaluate_single_combination, combo, target_data): combo
                for combo in combinations
            }
            
            # Collect results as they complete
            completed = 0
            for future in as_completed(future_to_params):
                try:
                    result = future.result(timeout=self.config.simulation_timeout_minutes * 60)
                    results.add_result(result)
                    completed += 1
                    
                    # Progress callback
                    if progress_callback:
                        progress_callback(completed, self.total_combinations, result)
                    
                    # Periodic logging
                    if completed % max(1, self.total_combinations // 20) == 0:
                        progress = completed / self.total_combinations * 100
                        best_value = results.get_best_objective_value() or 0.0
                        logger.info(f"Progress: {progress:.1f}% ({completed}/{self.total_combinations}), "
                                   f"Best objective: {best_value:.4f}")
                
                except Exception as e:
                    logger.error(f"Evaluation failed: {e}")
                    # Create a failed result
                    failed_result = GridSearchResult(
                        parameter_values=future_to_params[future],
                        objective_value=0.0,
                        objective_components={},
                        simulation_stats={},
                        evaluation_time=0.0,
                        is_valid=False,
                        error_message=str(e)
                    )
                    results.add_result(failed_result)
                    completed += 1
        
        return results
    
    def get_estimation_info(self) -> Dict[str, Any]:
        """Get estimation information about the calibration."""
        # Rough time estimation based on single evaluation
        estimated_time_per_eval = 30.0  # seconds (conservative estimate)
        estimated_total_time = self.total_combinations * estimated_time_per_eval
        
        if self.parallel_execution:
            estimated_total_time /= min(self.max_workers, self.total_combinations)
        
        return {
            'total_combinations': self.total_combinations,
            'parameter_space': {name: len(values) for name, values in self.parameter_space.items()},
            'estimated_time_seconds': estimated_total_time,
            'estimated_time_hours': estimated_total_time / 3600,
            'parallel_execution': self.parallel_execution,
            'max_workers': self.max_workers if self.parallel_execution else 1
        }
    
    def _get_arafo_highlands_coordinates(self, grid_size: Tuple[int, int]) -> Tuple[int, int]:
        """
        Get realistic ignition coordinates for Arafo highlands on Tenerife.
        
        Based on the 2023 Tenerife wildfire that started near Chivisaya viewpoint 
        in Arafo at ~1,200m elevation in the southeastern highlands.
        
        Args:
            grid_size: (width, height) of the simulation grid
            
        Returns:
            (x, y) coordinates for ignition point
        """
        width, height = grid_size
        
        # Arafo is located in the southeastern part of Tenerife
        # Approximate location based on Tenerife geography:
        # - East-southeast of center (about 60-70% across from west to east)
        # - South-southeast of center (about 60-70% down from north to south)
        # - In the highlands (intermediate elevation zone)
        
        # Convert geographic knowledge to grid coordinates
        arafo_x = int(width * 0.65)   # 65% across (southeastern)
        arafo_y = int(height * 0.62)  # 62% down (southeastern highlands)
        
        # Ensure coordinates are within bounds
        arafo_x = max(0, min(arafo_x, width - 1))
        arafo_y = max(0, min(arafo_y, height - 1))
        
        return arafo_x, arafo_y


def create_progress_callback(verbose: bool = True) -> callable:
    """Create a progress callback function for grid search."""
    def callback(completed: int, total: int, result: GridSearchResult):
        if verbose and completed % max(1, total // 10) == 0:
            progress = completed / total * 100
            status = "SUCCESS" if result.is_valid else "FAILED"
            obj_val = result.objective_value if result.is_valid else 0.0
            
            print(f"[{progress:6.1f}%] Evaluation {completed:4d}/{total}: "
                  f"{status} (Objective: {obj_val:.4f})")
    
    return callback


if __name__ == "__main__":
    # Example usage (requires proper imports and setup)
    print("Grid Search Calibrator Example")
    print("=" * 50)
    
    # This would normally require proper calibration config and bounds
    print("This is a demonstration of the GridSearchCalibrator interface.")
    print("To use this module, you need to:")
    print("1. Create a CalibrationConfig")
    print("2. Define parameter bounds") 
    print("3. Create an objective function")
    print("4. Initialize and run the calibrator")
    
    example_estimation = {
        'total_combinations': 3125,  # 5^5 for 5 parameters with 5 points each
        'estimated_time_hours': 2.5,
        'parallel_execution': True,
        'max_workers': 4
    }
    
    print(f"\nExample estimation for {example_estimation['total_combinations']} combinations:")
    print(f"Estimated time: {example_estimation['estimated_time_hours']:.1f} hours")
    print(f"Parallel execution: {example_estimation['parallel_execution']}")
    print(f"Workers: {example_estimation['max_workers']}") 