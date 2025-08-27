#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Sensitivity Analysis Module

This module implements one-at-a-time (OAT) sensitivity analysis for understanding
the impact of individual parameters on simulation outcomes. This is particularly
useful for parameter ranking and understanding model behavior.

Author: Forest Fire Simulation Team
Date: 2025
Version: 1.0
"""

import time
import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from pathlib import Path
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


def _get_arafo_highlands_coordinates(grid_size: Tuple[int, int]) -> Tuple[int, int]:
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


@dataclass
class SensitivityResult:
    """Result for a single parameter sensitivity analysis."""
    parameter_name: str
    baseline_value: float
    test_values: List[float]
    objective_values: List[float]
    objective_changes: List[float]  # Change from baseline
    relative_changes: List[float]   # Relative change from baseline
    sensitivity_index: float        # Overall sensitivity measure
    is_valid: bool = True
    error_message: str = ""


@dataclass
class SensitivityResults:
    """Complete results from sensitivity analysis."""
    results: List[SensitivityResult] = field(default_factory=list)
    baseline_objective: float = 0.0
    parameter_rankings: List[Tuple[str, float]] = field(default_factory=list)
    total_evaluations: int = 0
    total_time: float = 0.0
    analysis_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Update derived statistics after initialization."""
        self._update_rankings()
    
    def _update_rankings(self):
        """Update parameter rankings based on sensitivity indices."""
        rankings = []
        for result in self.results:
            if result.is_valid:
                rankings.append((result.parameter_name, result.sensitivity_index))
        
        # Sort by sensitivity index (descending)
        self.parameter_rankings = sorted(rankings, key=lambda x: x[1], reverse=True)
    
    def add_result(self, result: SensitivityResult):
        """Add a sensitivity result and update rankings."""
        self.results.append(result)
        self._update_rankings()
    
    def get_most_sensitive_parameters(self, top_n: int = 5) -> List[Tuple[str, float]]:
        """Get the top N most sensitive parameters."""
        return self.parameter_rankings[:top_n]
    
    def get_least_sensitive_parameters(self, bottom_n: int = 5) -> List[Tuple[str, float]]:
        """Get the bottom N least sensitive parameters."""
        return self.parameter_rankings[-bottom_n:]
    
    def get_parameter_result(self, parameter_name: str) -> Optional[SensitivityResult]:
        """Get sensitivity result for a specific parameter."""
        for result in self.results:
            if result.parameter_name == parameter_name:
                return result
        return None
    
    def get_sensitivity_summary(self) -> Dict[str, Any]:
        """Get a summary of sensitivity analysis results."""
        valid_results = [r for r in self.results if r.is_valid]
        
        # Always include basic fields even if no valid results
        base_summary = {
            'total_parameters': len(self.results),
            'valid_parameters': len(valid_results),
            'baseline_objective': self.baseline_objective,
            'total_evaluations': self.total_evaluations,
            'total_time': self.total_time
        }
        
        if not valid_results:
            base_summary['status'] = 'No valid results'
            base_summary['mean_sensitivity'] = 0.0
            base_summary['std_sensitivity'] = 0.0
            base_summary['sensitivity_range'] = 0.0
            base_summary['most_sensitive'] = None
            base_summary['least_sensitive'] = None
            return base_summary
        
        sensitivity_indices = [r.sensitivity_index for r in valid_results]
        
        base_summary.update({
            'most_sensitive': self.parameter_rankings[0] if self.parameter_rankings else None,
            'least_sensitive': self.parameter_rankings[-1] if self.parameter_rankings else None,
            'mean_sensitivity': np.mean(sensitivity_indices),
            'std_sensitivity': np.std(sensitivity_indices),
            'sensitivity_range': max(sensitivity_indices) - min(sensitivity_indices) if sensitivity_indices else 0.0,
        })
        
        return base_summary
    
    def save_results(self, filepath: Union[str, Path]) -> None:
        """Save sensitivity analysis results to JSON file."""
        filepath = Path(filepath)
        
        # Convert results to serializable format
        results_data = {
            'baseline_objective': self.baseline_objective,
            'parameter_rankings': self.parameter_rankings,
            'total_evaluations': self.total_evaluations,
            'total_time': self.total_time,
            'analysis_metadata': self.analysis_metadata,
            'results': [
                {
                    'parameter_name': r.parameter_name,
                    'baseline_value': r.baseline_value,
                    'test_values': r.test_values,
                    'objective_values': r.objective_values,
                    'objective_changes': r.objective_changes,
                    'relative_changes': r.relative_changes,
                    'sensitivity_index': r.sensitivity_index,
                    'is_valid': r.is_valid,
                    'error_message': r.error_message
                }
                for r in self.results
            ],
            'summary': self.get_sensitivity_summary()
        }
        
        # Import the serialization function
        from src.core.calibration.calibration_utils import _convert_to_serializable
        
        with open(filepath, 'w') as f:
            json.dump(_convert_to_serializable(results_data), f, indent=2)
        
        logger.info(f"Saved sensitivity analysis results to {filepath}")


@dataclass
class ParameterEvaluation:
    """Single parameter-value evaluation for parallel processing."""
    parameter_name: str
    test_value: float
    evaluation_id: str  # Unique identifier for tracking
    
    def __hash__(self):
        return hash(self.evaluation_id)


def _evaluate_single_parameter_value(evaluation: ParameterEvaluation, 
                                     config_dict: Dict[str, Any],
                                     parameter_bounds: Dict[str, Any],
                                     target_data: Optional[Dict[str, Any]],
                                     objective_config: Optional[Dict[str, Any]] = None,
                                     shared_terrain_info: Optional[Dict[str, Any]] = None) -> Tuple[str, float, float, bool, str]:
    """
    Static function for parallel evaluation of a single parameter-value combination.
    
    Args:
        evaluation: Parameter evaluation specification
        config_dict: Configuration dictionary
        parameter_bounds: Parameter bounds dictionary
        target_data: Target data (not used for sensitivity analysis)
        objective_config: Objective function configuration for consistency
        shared_terrain_info: Shared terrain data information for memory efficiency
    
    Returns: (parameter_name, test_value, objective_value, is_valid, error_message)
    """
    try:
        # Import here to avoid pickle issues in parallel processing
        from src.config.config_tools import ModelConfig
        from src.core.fire_simulation_engine import FireSimulationEngine
        from src.core.forest_model import create_forest_model
        from src.core.calibration.sensitivity_objective import create_sensitivity_objective
        
        # Create config variant with parameter at test value
        config_variant_dict = config_dict.copy()
        config_variant_dict[evaluation.parameter_name] = evaluation.test_value
        
        # Force memory optimization level 2 for parallel processing
        config_variant_dict['memory_optimization_level'] = 2
        
        # Add shared terrain info if available
        if shared_terrain_info:
            config_variant_dict['shared_terrain_info'] = shared_terrain_info
        
        # Create ModelConfig from dictionary
        config = ModelConfig(**config_variant_dict)
        
        # Create forest model and simulation engine
        forest_model = create_forest_model(
            model_type='memory_optimized',
            config=config
        )
        
        engine = FireSimulationEngine(forest_model=forest_model, config=config)
        logger.info("🎯 FireSimulationEngine created successfully - proceeding to ignition setup")
        
        # Set ignition point at Arafo highlands (realistic location for 2023 Tenerife fire)
        ignition_x, ignition_y = _get_arafo_highlands_coordinates(config.grid_size)
        
        # CRITICAL FIX: Add safety checks before setting ignition
        try:
            # Validate coordinates are within bounds
            if not (0 <= ignition_x < config.grid_size[0] and 0 <= ignition_y < config.grid_size[1]):
                raise ValueError(f"Ignition coordinates ({ignition_x}, {ignition_y}) out of bounds for grid {config.grid_size}")
            
            forest_model.set_ignition(ignition_x, ignition_y, 0)
            
        except Exception as ignition_error:
            logger.error(f"❌ CRITICAL: Failed to set ignition point: {ignition_error}")
            raise RuntimeError(f"Ignition setting failed: {ignition_error}")
        
        # CRITICAL FIX: Memory safety check before simulation
        try:
            import gc
            gc.collect()  # Clean up before simulation
            
            # Run simulation with enhanced error handling
            simulation_result = engine.run_simulation(
                max_steps=config.max_steps,
                store_history=False,
                stop_when_fire_extinguished=True
            )
            
        except Exception as sim_error:
            logger.error(f"❌ CRITICAL: Simulation failed: {sim_error}")
            raise RuntimeError(f"Simulation execution failed: {sim_error}")
        
        # Evaluate objective function (use consistent configuration)
        if objective_config:
            # Validate objective config structure
            if not isinstance(objective_config, dict):
                logger.warning(f"Invalid objective_config type: {type(objective_config)}. Using default.")
                from src.core.calibration.sensitivity_objective import create_sensitivity_objective
                objective_function = create_sensitivity_objective()
            else:
                try:
                    from src.core.calibration.sensitivity_objective import SensitivityAnalysisObjective
                    objective_function = SensitivityAnalysisObjective(**objective_config)
                except TypeError as e:
                    logger.warning(f"Invalid objective_config parameters: {e}. Using default.")
                    from src.core.calibration.sensitivity_objective import create_sensitivity_objective
                    objective_function = create_sensitivity_objective()
        else:
            from src.core.calibration.sensitivity_objective import create_sensitivity_objective
            objective_function = create_sensitivity_objective()
        objective_result = objective_function.evaluate(simulation_result, target_data)
        
        if objective_result.is_valid:
            return (evaluation.parameter_name, evaluation.test_value, 
                   objective_result.value, True, "")
        else:
            error_msg = f"Invalid objective result: {objective_result.error_message}"
            logger.warning(f"Parameter {evaluation.parameter_name}={evaluation.test_value}: {error_msg}")
            return (evaluation.parameter_name, evaluation.test_value, 
                   0.0, False, error_msg)
            
    except Exception as e:
        error_msg = f"Simulation failed: {str(e)}"
        logger.error(f"Parameter {evaluation.parameter_name}={evaluation.test_value}: {error_msg}")
        return (evaluation.parameter_name, evaluation.test_value, 
               0.0, False, error_msg)


class SensitivityAnalyzer:
    """
    Range-based sensitivity analyzer for forest fire simulation parameters.
    
    Uses Method 2: Standardized Range-Based Sensitivity Analysis
    - Tests parameters at 9 evenly spaced points across their full range
    - Calculates standardized sensitivity as (output_range / param_range) normalized by middle output
    - Provides clear parameter ranking without baseline dependency
    """
    
    def __init__(self, 
                 calibration_config,
                 parameter_bounds: Dict[str, Any],
                 objective_function,
                 perturbation_method: str = "range_based",
                 perturbation_values: Optional[List[float]] = None,
                 parallel_execution: bool = True,
                 max_workers: Optional[int] = None):
        """
        Initialize range-based sensitivity analyzer.
        
        Args:
            calibration_config: Calibration configuration
            parameter_bounds: Dictionary of parameter bounds
            objective_function: Objective function to evaluate
            perturbation_method: Method for parameter perturbation (default: "range_based")
            perturbation_values: Positions across parameter range (default: 9 evenly spaced points)
            parallel_execution: Whether to use parallel processing
            max_workers: Number of parallel workers (uses config.max_workers if None)
        """
        self.config = calibration_config
        self.parameter_bounds = parameter_bounds
        if objective_function is None:
            from src.core.calibration.sensitivity_objective import create_sensitivity_objective
            self.objective_function = create_sensitivity_objective()
        else:
            self.objective_function = objective_function
        self.perturbation_method = "range_based"  # Force Method 2
        
        # Set default perturbation values for Method 2: 9 evenly spaced points (0%, 10%, 20%, ..., 80%)
        if perturbation_values is None:
            self.perturbation_values = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
        else:
            self.perturbation_values = perturbation_values
        
        # Parallel processing settings
        self.parallel_execution = parallel_execution and hasattr(calibration_config, 'max_workers')
        self.max_workers = max_workers or getattr(calibration_config, 'max_workers', 7)
        
        self.baseline_config = None
        
        logger.info(f"Initialized Method 2 Range-Based Sensitivity Analyzer")
        logger.info(f"Parameters to analyze: {len(self.config.get_calibration_parameter_names())}")
        logger.info(f"Test points per parameter: {len(self.perturbation_values)}")
        
        total_evaluations = len(self.config.get_calibration_parameter_names()) * len(self.perturbation_values)
        logger.info(f"Total evaluations: {total_evaluations}")
        
        if self.parallel_execution:
            logger.info(f"🚀 Parallel sensitivity analysis enabled with {self.max_workers} workers")
        else:
            logger.info("📊 Sequential sensitivity analysis (parallel disabled)")
    
    def run_sensitivity_analysis(self, 
                                target_data: Optional[Dict[str, Any]] = None,
                                progress_callback: Optional[callable] = None) -> SensitivityResults:
        """
        Run one-at-a-time sensitivity analysis for all parameters.
        
        Args:
            target_data: Target data for objective function evaluation
            progress_callback: Optional callback for progress updates
            
        Returns:
            SensitivityResults with analysis for all parameters
        """
        logger.info("🚀 Starting parallel sensitivity analysis" if self.parallel_execution else "📊 Starting sequential sensitivity analysis")
        start_time = time.time()
        
        # Initialize results
        results = SensitivityResults()
        
        # Get baseline objective value
        baseline_objective = self._evaluate_baseline(target_data)
        results.baseline_objective = baseline_objective
        
        if baseline_objective is None:
            logger.error("❌ Failed to evaluate baseline configuration")
            return results
        
        logger.info(f"✅ Baseline objective value: {baseline_objective:.4f}")
        
        # Generate all parameter-value combinations
        evaluations = self._generate_all_evaluations()
        total_evaluations = len(evaluations)
        
        logger.info(f"📊 Total evaluations: {total_evaluations}")
        if self.parallel_execution:
            logger.info(f"🔧 Workers: {self.max_workers}")
        
        # Convert config to dictionary for parallel processing
        config_dict = self.config.base_config.__dict__.copy()
        
        # Parallel or sequential evaluation
        if self.parallel_execution and total_evaluations > 1:
            evaluation_results = self._run_parallel_evaluations(
                evaluations, config_dict, target_data, progress_callback
            )
        else:
            evaluation_results = self._run_sequential_evaluations(
                evaluations, config_dict, target_data, progress_callback
            )
        
        # Group results by parameter and calculate sensitivity indices
        self._process_evaluation_results(evaluation_results, baseline_objective, results)
        
        # Finalize results
        total_time = time.time() - start_time
        results.total_time = total_time
        results.total_evaluations = total_evaluations
        
        results.analysis_metadata = {
            'perturbation_method': self.perturbation_method,
            'perturbation_values': self.perturbation_values,
            'parallel_execution': self.parallel_execution,
            'max_workers': self.max_workers,
            'total_time': total_time,
            'evaluations_per_second': total_evaluations / max(total_time, 1e-6)
        }
        
        logger.info(f"✅ Sensitivity analysis completed in {total_time:.2f} seconds")
        if self.parallel_execution:
            logger.info(f"🚀 Speed: {total_evaluations/(total_time/3600):.1f} evaluations/hour")
        
        self._log_sensitivity_summary(results)
        
        return results
    
    def _generate_all_evaluations(self) -> List[ParameterEvaluation]:
        """Generate all parameter-value combinations for parallel processing."""
        evaluations = []
        
        for param_name in self.config.get_calibration_parameter_names():
            if param_name not in self.parameter_bounds:
                continue
                
            bounds = self.parameter_bounds[param_name]
            baseline_value = bounds.min_value + 0.4 * (bounds.max_value - bounds.min_value)
            test_values = self._generate_test_values(param_name, baseline_value, bounds)
            
            for i, test_value in enumerate(test_values):
                evaluation_id = f"{param_name}_{i}_{test_value:.6f}"
                evaluations.append(ParameterEvaluation(
                    parameter_name=param_name,
                    test_value=test_value,
                    evaluation_id=evaluation_id
                ))
        
        return evaluations
    
    def _run_parallel_evaluations(self, evaluations, config_dict, target_data, progress_callback):
        """Run evaluations in parallel using ProcessPoolExecutor."""
        logger.info(f"🔄 Running {len(evaluations)} evaluations in parallel...")
        
        evaluation_results = []
        
        # Create objective function configuration for consistent parallel processing
        objective_config = {
            'area_weight': self.objective_function.area_weight,
            'spread_rate_weight': self.objective_function.spread_rate_weight,
            'persistence_weight': self.objective_function.persistence_weight,
            'dispersion_weight': self.objective_function.dispersion_weight
        }
        
        # Get shared terrain info if available from config_dict or base config
        shared_terrain_info = config_dict.get('shared_terrain_info', None)
        if not shared_terrain_info and hasattr(self.config, 'base_config'):
            shared_terrain_info = getattr(self.config.base_config, 'shared_terrain_info', None)
        
        # Validate shared terrain info before starting workers to prevent deadlocks
        if shared_terrain_info:
            try:
                # Quick validation that shared memory blocks exist
                shared_names = shared_terrain_info.get('shared_names', {})
                if not shared_names or not shared_terrain_info.get('is_loaded', False):
                    logger.warning("⚠️  Shared terrain info provided but appears invalid. Disabling for safety.")
                    shared_terrain_info = None
                else:
                    logger.info(f"✅ Validated shared terrain with {len(shared_names)} blocks")
            except Exception as e:
                logger.warning(f"⚠️  Error validating shared terrain: {e}. Disabling for safety.")
                shared_terrain_info = None
        
        try:
            with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all jobs
                future_to_eval = {
                    executor.submit(_evaluate_single_parameter_value, 
                                   eval_item, config_dict, self.parameter_bounds, target_data, objective_config, shared_terrain_info): eval_item
                    for eval_item in evaluations
                }
                
                # Collect results as they complete
                completed = 0
                for future in as_completed(future_to_eval, timeout=3600):  # 1-hour total timeout
                    try:
                        result = future.result(timeout=5400)  # 1.5 hour timeout per evaluation
                        evaluation_results.append(result)
                        completed += 1
                        
                        # Progress callback
                        if progress_callback and completed % max(1, len(evaluations) // 20) == 0:
                            progress = completed / len(evaluations) * 100
                            logger.info(f"📈 Progress: {progress:.1f}% ({completed}/{len(evaluations)})")
                    
                    except TimeoutError:
                        eval_item = future_to_eval[future]
                        logger.error(f"❌ Timeout for {eval_item.parameter_name}={eval_item.test_value}")
                        evaluation_results.append((eval_item.parameter_name, eval_item.test_value, 0.0, False, "Evaluation timeout"))
                        completed += 1
                        future.cancel()  # Try to cancel the timed-out task
                    
                    except Exception as e:
                        eval_item = future_to_eval[future]
                        logger.warning(f"⚠️  Evaluation failed for {eval_item.parameter_name}={eval_item.test_value}: {e}")
                        evaluation_results.append((eval_item.parameter_name, eval_item.test_value, 0.0, False, str(e)))
                        completed += 1
                        
        except KeyboardInterrupt:
            logger.warning("🛑 Sensitivity analysis interrupted by user")
            # Cleanup shared memory if interrupted
            try:
                from src.utils.shared_terrain import cleanup_shared_terrain
                cleanup_shared_terrain()
                logger.info("🧹 Cleaned up shared memory after interruption")
            except Exception as cleanup_error:
                logger.warning(f"⚠️  Error cleaning up after interruption: {cleanup_error}")
            raise
        except Exception as e:
            logger.error(f"❌ Critical error in parallel evaluation: {e}")
            # Cleanup shared memory on critical error
            try:
                from src.utils.shared_terrain import cleanup_shared_terrain
                cleanup_shared_terrain()
                logger.info("🧹 Cleaned up shared memory after error")
            except Exception as cleanup_error:
                logger.warning(f"⚠️  Error cleaning up after critical error: {cleanup_error}")
            raise
        
        return evaluation_results
    
    def _run_sequential_evaluations(self, evaluations, config_dict, target_data, progress_callback):
        """Run evaluations sequentially (fallback)."""
        logger.info(f"📊 Running {len(evaluations)} evaluations sequentially...")
        
        evaluation_results = []
        
        # Create objective function configuration for consistent sequential processing
        objective_config = {
            'area_weight': self.objective_function.area_weight,
            'spread_rate_weight': self.objective_function.spread_rate_weight,
            'persistence_weight': self.objective_function.persistence_weight,
            'dispersion_weight': self.objective_function.dispersion_weight
        }
        
        # Get shared terrain info if available from config_dict or base config
        shared_terrain_info = config_dict.get('shared_terrain_info', None)
        if not shared_terrain_info and hasattr(self.config, 'base_config'):
            shared_terrain_info = getattr(self.config.base_config, 'shared_terrain_info', None)
        
        for i, evaluation in enumerate(evaluations):
            result = _evaluate_single_parameter_value(evaluation, config_dict, self.parameter_bounds, target_data, objective_config, shared_terrain_info)
            evaluation_results.append(result)
            
            # Progress callback
            if progress_callback and (i + 1) % max(1, len(evaluations) // 20) == 0:
                progress = (i + 1) / len(evaluations) * 100
                logger.info(f"📈 Progress: {progress:.1f}% ({i + 1}/{len(evaluations)})")
        
        return evaluation_results
    
    def _process_evaluation_results(self, evaluation_results, baseline_objective, results):
        """Group evaluation results by parameter and calculate sensitivity indices."""
        # Group results by parameter
        param_results = {}
        for param_name, test_value, objective_value, is_valid, error_msg in evaluation_results:
            if param_name not in param_results:
                param_results[param_name] = {
                    'test_values': [],
                    'objective_values': [],
                    'valid_count': 0,
                    'errors': []
                }
            
            param_results[param_name]['test_values'].append(test_value)
            param_results[param_name]['objective_values'].append(objective_value)
            
            if is_valid:
                param_results[param_name]['valid_count'] += 1
            else:
                param_results[param_name]['errors'].append(error_msg)
        
        # Calculate sensitivity for each parameter
        for param_name, param_data in param_results.items():
            bounds = self.parameter_bounds[param_name]
            baseline_value = bounds.min_value + 0.4 * (bounds.max_value - bounds.min_value)
            
            # Calculate sensitivity metrics
            objective_changes = [obj_val - baseline_objective for obj_val in param_data['objective_values']]
            relative_changes = [change / max(abs(baseline_objective), 1e-10) for change in objective_changes]
            
            # Calculate Method 2 standardized range-based sensitivity index
            sensitivity_index = self._calculate_sensitivity_index(
                param_data['test_values'], 
                param_data['objective_values'], 
                baseline_value, 
                baseline_objective
            )
            
            # Create sensitivity result
            sensitivity_result = SensitivityResult(
                parameter_name=param_name,
                baseline_value=baseline_value,
                test_values=param_data['test_values'],
                objective_values=param_data['objective_values'],
                objective_changes=objective_changes,
                relative_changes=relative_changes,
                sensitivity_index=sensitivity_index,
                is_valid=param_data['valid_count'] > 0,
                error_message="; ".join(param_data['errors']) if param_data['errors'] else ""
            )
            
            results.add_result(sensitivity_result)
    
    def _evaluate_baseline(self, target_data: Optional[Dict[str, Any]]) -> Optional[float]:
        """
        Evaluate reference configuration for Method 2 Range-Based Sensitivity.
        
        For Method 2, we create a reference configuration with all parameters 
        set to their middle values for normalization purposes.
        """
        try:
            # Create a reference config with all parameters set to their center values
            center_params = {}
            for param_name in self.config.calibration_parameters:
                if param_name in self.parameter_bounds:
                    bounds = self.parameter_bounds[param_name]
                    center_value = bounds.min_value + 0.4 * (bounds.max_value - bounds.min_value)  # Use 40% point as reference
                    center_params[param_name] = center_value
            
            self.baseline_config = self.config.create_config_variant(center_params)
            
            # Create and run simulation with reference config
            simulation_result = self._run_simulation_with_config(self.baseline_config)
            
            # Evaluate objective
            objective_result = self.objective_function.evaluate(simulation_result, target_data)
            if objective_result.is_valid:
                return objective_result.value
            else:
                logger.error(f"Reference evaluation failed: {objective_result.error_message}")
                return None
        except Exception as e:
            logger.error(f"Failed to evaluate reference configuration: {e}")
            return None
    
    def _analyze_parameter(self, 
                         parameter_name: str, 
                         baseline_objective: float,
                         target_data: Optional[Dict[str, Any]]) -> SensitivityResult:
        """
        Analyze sensitivity for a single parameter using Method 2 Range-Based approach.
        
        Tests the parameter at 9 evenly spaced points across its full range
        and calculates standardized range-based sensitivity.
        """
        try:
            # Get parameter bounds and set middle value as baseline for consistency
            if parameter_name not in self.parameter_bounds:
                return SensitivityResult(
                    parameter_name=parameter_name,
                    baseline_value=0.0,
                    test_values=[],
                    objective_values=[],
                    objective_changes=[],
                    relative_changes=[],
                    sensitivity_index=0.0,
                    is_valid=False,
                    error_message=f"No bounds defined for parameter {parameter_name}"
                )
            
            bounds = self.parameter_bounds[parameter_name]
            # For Method 2, use middle of range as baseline reference
            baseline_value = bounds.min_value + 0.4 * (bounds.max_value - bounds.min_value)  # 40% point
            
            # Generate test values using Method 2 approach
            test_values = self._generate_test_values(parameter_name, baseline_value, bounds)
            
            # Evaluate objective for each test value
            objective_values = []
            
            for test_value in test_values:
                try:
                    # Create config variant with parameter at test value
                    param_values = {parameter_name: test_value}
                    test_config = self.config.create_config_variant(param_values)
                    
                    # Run simulation
                    simulation_result = self._run_simulation_with_config(test_config)
                    
                    # Evaluate objective
                    objective_result = self.objective_function.evaluate(simulation_result, target_data)
                    
                    if objective_result.is_valid:
                        objective_values.append(objective_result.value)
                    else:
                        objective_values.append(baseline_objective)  # Fallback to reference
                        logger.warning(f"Invalid objective for {parameter_name}={test_value}, using reference")
                
                except Exception as e:
                    logger.warning(f"Evaluation failed for {parameter_name}={test_value}: {e}")
                    objective_values.append(baseline_objective)  # Fallback to reference
            
            # Calculate sensitivity metrics for Method 2
            objective_changes = [obj_val - baseline_objective for obj_val in objective_values]
            relative_changes = [change / max(abs(baseline_objective), 1e-10) for change in objective_changes]
            
            # Calculate Method 2 standardized range-based sensitivity index
            sensitivity_index = self._calculate_sensitivity_index(
                test_values, objective_values, baseline_value, baseline_objective
            )
            
            return SensitivityResult(
                parameter_name=parameter_name,
                baseline_value=baseline_value,
                test_values=test_values,
                objective_values=objective_values,
                objective_changes=objective_changes,
                relative_changes=relative_changes,
                sensitivity_index=sensitivity_index,
                is_valid=True
            )
            
        except Exception as e:
            logger.error(f"Failed to analyze parameter {parameter_name}: {e}")
            return SensitivityResult(
                parameter_name=parameter_name,
                baseline_value=0.0,
                test_values=[],
                objective_values=[],
                objective_changes=[],
                relative_changes=[],
                sensitivity_index=0.0,
                is_valid=False,
                error_message=str(e)
            )
    
    def _generate_test_values(self, parameter_name: str, baseline_value: float, bounds) -> List[float]:
        """
        Generate test values for Method 2 Range-Based Sensitivity Analysis.
        
        Creates 9 evenly spaced test points across the parameter's full range:
        min_value + 0%, 10%, 20%, 30%, 40%, 50%, 60%, 70%, 80% of (max_value - min_value)
        
        Args:
            parameter_name: Name of parameter being tested
            baseline_value: Not used in Method 2, kept for interface compatibility  
            bounds: Parameter bounds object
            
        Returns:
            List of 9 test values spanning the parameter range
        """
        test_values = []
        param_range = bounds.max_value - bounds.min_value
        
        for position in self.perturbation_values:
            # Calculate test value at this position in the range
            test_value = bounds.min_value + position * param_range
            
            # Ensure value is within bounds (should be by construction, but safety check)
            test_value = bounds.clip_value(test_value)
            test_values.append(test_value)
        
        logger.debug(f"Generated {len(test_values)} test values for {parameter_name}: "
                    f"[{test_values[0]:.3f}, ..., {test_values[-1]:.3f}]")
        
        return test_values
    
    def _calculate_sensitivity_index(self, 
                                   test_values: List[float], 
                                   objective_values: List[float],
                                   baseline_value: float,
                                   baseline_objective: float) -> float:
        """
        Calculate Method 2 Standardized Range-Based Sensitivity Index.
        
        Formula: Sensitivity = (Output_Range / Param_Range) × (Param_Range / Middle_Output)
        
        This measures how much the output changes relative to the parameter range,
        standardized by the typical output magnitude for parameter comparison.
        
        Args:
            test_values: List of parameter values tested
            objective_values: List of corresponding objective function outputs
            baseline_value: Reference parameter value (middle of range)
            baseline_objective: Reference objective value (for fallback)
            
        Returns:
            Standardized sensitivity index (higher = more sensitive)
        """
        if not objective_values or len(objective_values) < 2:
            return 0.0
        
        # Calculate output range across all test points
        output_min = min(objective_values)
        output_max = max(objective_values)
        output_range = output_max - output_min
        
        # Calculate parameter range tested
        param_min = min(test_values)
        param_max = max(test_values)
        param_range = param_max - param_min
        
        if param_range == 0:
            return 0.0
        
        # Calculate raw sensitivity (output change per unit parameter change)
        raw_sensitivity = output_range / param_range
        
        # Find middle output value for normalization (use median for robust estimation)
        if len(objective_values) >= 3:
            # Use median for robust middle value estimation
            middle_output = np.median(objective_values)
        else:
            middle_output = baseline_objective  # Fallback to reference value
        
        # Standardize sensitivity by typical output magnitude
        if abs(middle_output) > 1e-10:
            standardized_sensitivity = abs(raw_sensitivity) / abs(middle_output)
        else:
            # If middle output is near zero, use range-based normalization
            output_magnitude = max(abs(output_min), abs(output_max), 1e-10)
            standardized_sensitivity = abs(raw_sensitivity) / output_magnitude
        
        logger.debug(f"Method 2 Sensitivity Calculation:")
        logger.debug(f"  Output range: {output_range:.6f} ({output_min:.6f} to {output_max:.6f})")
        logger.debug(f"  Param range: {param_range:.6f} ({param_min:.6f} to {param_max:.6f})")
        logger.debug(f"  Raw sensitivity: {raw_sensitivity:.6f}")
        logger.debug(f"  Middle output: {middle_output:.6f}")
        logger.debug(f"  Standardized sensitivity: {standardized_sensitivity:.6f}")
        
        return standardized_sensitivity
    
    def _run_simulation_with_config(self, config) -> Dict[str, Any]:
        """Run a simulation with the given configuration."""
        # Force memory optimization level 2 for sensitivity analysis
        config.memory_optimization_level = 2
        
        # Create forest model with memory optimization and simulation engine
        forest_model = create_forest_model(
            model_type='memory_optimized',  # Use memory optimized model to ensure level 2 optimizations are applied
            config=config,
            grid_size=config.grid_size,
            num_layers=config.num_layers
        )
        
        engine = FireSimulationEngine(forest_model=forest_model, config=config)
        logger.info("🎯 FireSimulationEngine created successfully - proceeding to ignition setup")
        
        # Set ignition point at Arafo highlands (realistic location for 2023 Tenerife fire)
        ignition_x, ignition_y = _get_arafo_highlands_coordinates(config.grid_size)
        
        # CRITICAL FIX: Add safety checks before setting ignition
        try:
            # Validate coordinates are within bounds
            if not (0 <= ignition_x < config.grid_size[0] and 0 <= ignition_y < config.grid_size[1]):
                raise ValueError(f"Ignition coordinates ({ignition_x}, {ignition_y}) out of bounds for grid {config.grid_size}")
            
            forest_model.set_ignition(ignition_x, ignition_y, 0)
            
        except Exception as ignition_error:
            logger.error(f"❌ CRITICAL: Failed to set ignition point: {ignition_error}")
            raise RuntimeError(f"Ignition setting failed: {ignition_error}")
        
        # CRITICAL FIX: Memory safety check before simulation
        try:
            import gc
            gc.collect()  # Clean up before simulation
            
            # Run simulation with enhanced error handling
            simulation_result = engine.run_simulation(
                max_steps=config.max_steps,
                store_history=False,
                stop_when_fire_extinguished=True
            )
            
        except Exception as sim_error:
            logger.error(f"❌ CRITICAL: Simulation failed: {sim_error}")
            raise RuntimeError(f"Simulation execution failed: {sim_error}")
        
        return simulation_result
    
    def _log_sensitivity_summary(self, results: SensitivityResults):
        """Log a summary of sensitivity analysis results."""
        summary = results.get_sensitivity_summary()
        
        logger.info("=== SENSITIVITY ANALYSIS SUMMARY ===")
        logger.info(f"Total parameters analyzed: {summary['total_parameters']}")
        logger.info(f"Valid analyses: {summary['valid_parameters']}")
        baseline_obj = summary.get('baseline_objective')
        if baseline_obj is not None:
            logger.info(f"Baseline objective: {baseline_obj:.4f}")
        else:
            logger.warning("Baseline objective is None - simulation may have failed")
        
        if summary.get('most_sensitive'):
            most_sensitive = summary['most_sensitive']
            logger.info(f"Most sensitive parameter: {most_sensitive[0]} (index: {most_sensitive[1]:.4f})")
        
        if summary.get('least_sensitive'):
            least_sensitive = summary['least_sensitive']
            logger.info(f"Least sensitive parameter: {least_sensitive[0]} (index: {least_sensitive[1]:.4f})")
        
        logger.info(f"Mean sensitivity index: {summary.get('mean_sensitivity', 0.0):.4f}")
        logger.info(f"Sensitivity range: {summary.get('sensitivity_range', 0.0):.4f}")
        
        # Log top 5 most sensitive parameters
        logger.info("Top 5 most sensitive parameters:")
        for i, (param_name, sensitivity) in enumerate(results.get_most_sensitive_parameters(5)):
            logger.info(f"  {i+1}. {param_name}: {sensitivity:.4f}")


def create_sensitivity_progress_callback(verbose: bool = True) -> callable:
    """Create a progress callback function for sensitivity analysis."""
    def callback(completed: int, total: int, result: SensitivityResult):
        if verbose:
            status = "SUCCESS" if result.is_valid else "FAILED"
            sensitivity = result.sensitivity_index if result.is_valid else 0.0
            
            print(f"[{completed:2d}/{total}] {result.parameter_name:25s}: "
                  f"{status:7s} (Sensitivity: {sensitivity:.4f})")
    
    return callback


if __name__ == "__main__":
    # Example usage (requires proper imports and setup)
    print("Sensitivity Analyzer Example")
    print("=" * 50)
    
    print("This is a demonstration of the SensitivityAnalyzer interface.")
    print("To use this module, you need to:")
    print("1. Create a CalibrationConfig")
    print("2. Define parameter bounds")
    print("3. Create an objective function")
    print("4. Initialize and run the analyzer")
    
    # Example sensitivity results
    example_results = [
        ("spread_probability", 0.156),
        ("fuel_consumption_rate", 0.134),
        ("ignition_threshold", 0.089),
        ("min_fuel_value", 0.067),
        ("slope_influence", 0.045),
        ("wind_influence_on_spread", 0.032),
        ("ember_probability", 0.018)
    ]
    
    print(f"\nExample sensitivity ranking:")
    for i, (param_name, sensitivity) in enumerate(example_results):
        print(f"  {i+1}. {param_name:25s}: {sensitivity:.4f}")
    
    print(f"\nInterpretation:")
    print(f"- Higher values indicate greater sensitivity")
    print(f"- Focus calibration efforts on top-ranked parameters")
    print(f"- Low-sensitivity parameters can use default values") 