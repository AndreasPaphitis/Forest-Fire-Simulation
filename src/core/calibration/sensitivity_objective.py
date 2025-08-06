#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Sensitivity Analysis Objective Function

This module provides objective functions specifically designed for sensitivity analysis.
Unlike calibration objectives that compare to target data, sensitivity objectives
measure intrinsic fire behavior characteristics that should vary with parameter changes.

Author: Forest Fire Simulation Team
Date: 2025
Version: 1.0
"""

import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

try:
    from src.utils.logging_utils import get_logger
    from src.core.calibration.objective_functions import ObjectiveFunction, ObjectiveResult
except ImportError:
    try:
        from utils.logging_utils import get_logger
        from core.calibration.objective_functions import ObjectiveFunction, ObjectiveResult
    except ImportError:
        import logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

logger = get_logger(__name__)


class SensitivityAnalysisObjective(ObjectiveFunction):
    """
    Objective function designed for sensitivity analysis.
    
    Measures intrinsic fire behavior characteristics that should vary with parameter changes:
    - Total burned area
    - Fire spread rate
    - Fire persistence (duration)
    - Fire intensity distribution
    - Spatial fire dispersion
    """
    
    def __init__(self, 
                 area_weight: float = 0.3,
                 spread_rate_weight: float = 0.3,
                 persistence_weight: float = 0.2,
                 dispersion_weight: float = 0.2):
        """
        Initialize sensitivity analysis objective.
        
        Args:
            area_weight: Weight for total burned area component
            spread_rate_weight: Weight for fire spread rate component
            persistence_weight: Weight for fire persistence component
            dispersion_weight: Weight for spatial dispersion component
        """
        super().__init__("sensitivity_analysis", higher_is_better=True)
        self.area_weight = area_weight
        self.spread_rate_weight = spread_rate_weight
        self.persistence_weight = persistence_weight
        self.dispersion_weight = dispersion_weight
        
        # Normalize weights
        total_weight = area_weight + spread_rate_weight + persistence_weight + dispersion_weight
        if total_weight > 0:
            self.area_weight /= total_weight
            self.spread_rate_weight /= total_weight
            self.persistence_weight /= total_weight
            self.dispersion_weight /= total_weight
    
    def evaluate(self, 
                 simulation_result: Dict[str, Any], 
                 target_data: Optional[Dict[str, Any]] = None) -> ObjectiveResult:
        """
        Evaluate fire behavior characteristics for sensitivity analysis.
        
        Args:
            simulation_result: Dictionary containing simulation results
            target_data: Not used for sensitivity analysis
            
        Returns:
            ObjectiveResult with combined fire behavior score
        """
        try:
            # Extract forest model and state
            forest_model = simulation_result.get('forest_model')
            if not forest_model:
                return ObjectiveResult(
                    value=0.0,
                    components={},
                    is_valid=False,
                    error_message="No forest model in simulation result"
                )
            
            if not hasattr(forest_model, 'state'):
                return ObjectiveResult(
                    value=0.0,
                    components={},
                    is_valid=False,
                    error_message=f"Forest model missing state attribute (type: {type(forest_model).__name__})"
                )
            
            if forest_model.state is None:
                return ObjectiveResult(
                    value=0.0,
                    components={},
                    is_valid=False,
                    error_message="Forest model state is None"
                )
            
            # Get simulation statistics
            stats = simulation_result.get('stats', {})
            
            # Initialize components
            components = {}
            score_components = []
            
            # 1. TOTAL BURNED AREA (normalized by grid size)
            burned_area = self._calculate_burned_area(forest_model, stats)
            components['burned_area'] = burned_area
            score_components.append(burned_area * self.area_weight)
            
            # 2. FIRE SPREAD RATE (cells burned per timestep)
            spread_rate = self._calculate_spread_rate(forest_model, stats)
            components['spread_rate'] = spread_rate
            score_components.append(spread_rate * self.spread_rate_weight)
            
            # 3. FIRE PERSISTENCE (how long fire persists)
            persistence = self._calculate_persistence(forest_model, stats)
            components['persistence'] = persistence
            score_components.append(persistence * self.persistence_weight)
            
            # 4. SPATIAL DISPERSION (how spread out the fire is)
            dispersion = self._calculate_spatial_dispersion(forest_model)
            components['dispersion'] = dispersion
            score_components.append(dispersion * self.dispersion_weight)
            
            # Calculate overall objective (higher values indicate more varied behavior)
            overall_score = sum(score_components)
            components['overall_score'] = overall_score
            
            # Add additional diagnostic information
            components['total_cells'] = self._get_total_cells(forest_model)
            components['burning_cells'] = self._get_burning_cells(forest_model)
            components['steps'] = stats.get('steps', 0)
            
            return ObjectiveResult(
                value=overall_score,
                components=components,
                is_valid=True
            )
            
        except Exception as e:
            logger.error(f"Error in sensitivity analysis evaluation: {e}")
            return ObjectiveResult(
                value=0.0,
                components={},
                is_valid=False,
                error_message=str(e)
            )
    
    def _calculate_burned_area(self, forest_model, stats: Dict[str, Any]) -> float:
        """Calculate normalized burned area."""
        try:
            total_cells = self._get_total_cells(forest_model)
            burned_cells = stats.get('total_burned_cells', 0)
            
            if total_cells > 0:
                return min(burned_cells / total_cells, 1.0)  # Normalize to [0, 1]
            return 0.0
        except:
            return 0.0
    
    def _calculate_spread_rate(self, forest_model, stats: Dict[str, Any]) -> float:
        """Calculate normalized fire spread rate."""
        try:
            total_cells = self._get_total_cells(forest_model)
            burned_cells = stats.get('total_burned_cells', 0)
            steps = max(stats.get('steps', 1), 1)
            
            if total_cells > 0:
                spread_rate = (burned_cells / steps) / total_cells
                return min(spread_rate, 1.0)  # Normalize to [0, 1]
            return 0.0
        except:
            return 0.0
    
    def _calculate_persistence(self, forest_model, stats: Dict[str, Any]) -> float:
        """Calculate fire persistence (normalized by max steps)."""
        try:
            steps = stats.get('steps', 0)
            max_steps = getattr(forest_model.config, 'max_steps', 50) if forest_model.config else 50
            
            if max_steps > 0:
                return min(steps / max_steps, 1.0)  # Normalize to [0, 1]
            return 0.0
        except:
            return 0.0
    
    def _calculate_spatial_dispersion(self, forest_model) -> float:
        """Calculate spatial dispersion of fire (how spread out it is)."""
        try:
            state = forest_model.state
            
            # Handle different state formats
            if hasattr(state, 'shape') and len(state.shape) == 3:
                # 3D array: find all burning/burned cells
                fire_mask = np.any(state == 2, axis=2)  # Burning cells
            elif hasattr(state, 'shape') and len(state.shape) == 2:
                # 2D array
                fire_mask = (state == 2)
            else:
                return 0.0
            
            # Calculate dispersion using standard deviation of fire positions
            if np.any(fire_mask):
                y_coords, x_coords = np.where(fire_mask)
                
                if len(x_coords) > 1:
                    # Calculate coefficient of variation for spatial spread
                    x_std = np.std(x_coords)
                    y_std = np.std(y_coords)
                    x_mean = np.mean(x_coords)
                    y_mean = np.mean(y_coords)
                    
                    # Normalize by grid dimensions
                    grid_height, grid_width = fire_mask.shape
                    x_cv = x_std / max(grid_width, 1)
                    y_cv = y_std / max(grid_height, 1)
                    
                    return min((x_cv + y_cv) / 2, 1.0)  # Average and normalize
                else:
                    return 0.0  # Single point fire has no dispersion
            
            return 0.0
        except:
            return 0.0
    
    def _get_total_cells(self, forest_model) -> int:
        """Get total number of cells in the grid."""
        try:
            if hasattr(forest_model, 'width') and hasattr(forest_model, 'height'):
                return forest_model.width * forest_model.height
            elif hasattr(forest_model, 'state') and hasattr(forest_model.state, 'shape'):
                if len(forest_model.state.shape) >= 2:
                    return forest_model.state.shape[0] * forest_model.state.shape[1]
            return 6400  # Default: 80x80 grid
        except:
            return 6400
    
    def _get_burning_cells(self, forest_model) -> int:
        """Get current number of burning cells."""
        try:
            state = forest_model.state
            
            if hasattr(state, 'shape') and len(state.shape) == 3:
                return np.sum(state == 2)  # Count burning cells across all layers
            elif hasattr(state, 'shape') and len(state.shape) == 2:
                return np.sum(state == 2)  # Count burning cells
            return 0
        except:
            return 0


def create_sensitivity_objective() -> SensitivityAnalysisObjective:
    """Create a default sensitivity analysis objective function."""
    return SensitivityAnalysisObjective(
        area_weight=0.3,
        spread_rate_weight=0.3,
        persistence_weight=0.2,
        dispersion_weight=0.2
    )