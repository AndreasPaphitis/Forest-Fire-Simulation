#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Objective Functions Module

This module implements various objective functions for calibrating the forest fire simulation.
It includes spatial similarity metrics, fire behavior objectives (burned area and spread rate), 
and multi-objective combinations.

Author: Forest Fire Simulation Team
Date: 2025
Version: 1.0
"""

import numpy as np
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Union, Optional, Tuple, Callable
from dataclasses import dataclass
from pathlib import Path

try:
    from src.utils.logging_utils import get_logger
except ImportError:
    try:
        from utils.logging_utils import get_logger
    except ImportError:
        import logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

logger = get_logger(__name__)


def calculate_jaccard_index(predicted: np.ndarray, actual: np.ndarray) -> float:
    """
    Calculate the Jaccard similarity index between predicted and actual fire areas.
    
    Jaccard Index = |A ∩ B| / |A ∪ B|
    
    Args:
        predicted: Binary array of predicted fire locations (1 = burned, 0 = unburned)
        actual: Binary array of actual fire locations (1 = burned, 0 = unburned)
        
    Returns:
        Jaccard index value between 0 and 1 (1 = perfect match)
    """
    # Convert to boolean arrays
    pred_bool = predicted.astype(bool)
    actual_bool = actual.astype(bool)
    
    # Calculate intersection and union
    intersection = np.logical_and(pred_bool, actual_bool).sum()
    union = np.logical_or(pred_bool, actual_bool).sum()
    
    # Handle edge case where both arrays are empty
    if union == 0:
        return 1.0 if intersection == 0 else 0.0
    
    return float(intersection) / float(union)


def calculate_dice_coefficient(predicted: np.ndarray, actual: np.ndarray) -> float:
    """
    Calculate the Sørensen-Dice coefficient between predicted and actual fire areas.
    
    Dice Coefficient = 2 * |A ∩ B| / (|A| + |B|)
    
    Args:
        predicted: Binary array of predicted fire locations
        actual: Binary array of actual fire locations
        
    Returns:
        Dice coefficient value between 0 and 1 (1 = perfect match)
    """
    # Convert to boolean arrays
    pred_bool = predicted.astype(bool)
    actual_bool = actual.astype(bool)
    
    # Calculate intersection and sizes
    intersection = np.logical_and(pred_bool, actual_bool).sum()
    pred_size = pred_bool.sum()
    actual_size = actual_bool.sum()
    
    # Handle edge case where both arrays are empty
    if pred_size + actual_size == 0:
        return 1.0 if intersection == 0 else 0.0
    
    return (2.0 * float(intersection)) / float(pred_size + actual_size)


def calculate_sorensen_coefficient(predicted: np.ndarray, actual: np.ndarray) -> float:
    """
    Calculate the Sørensen similarity coefficient (same as Dice coefficient).
    
    Args:
        predicted: Binary array of predicted fire locations
        actual: Binary array of actual fire locations
        
    Returns:
        Sørensen coefficient value between 0 and 1 (1 = perfect match)
    """
    return calculate_dice_coefficient(predicted, actual)


def calculate_hausdorff_distance(predicted: np.ndarray, actual: np.ndarray) -> float:
    """
    Calculate the Hausdorff distance between fire perimeters.
    
    Args:
        predicted: Binary array of predicted fire locations
        actual: Binary array of actual fire locations
        
    Returns:
        Hausdorff distance (lower is better, 0 = perfect match)
    """
    try:
        from scipy.spatial.distance import directed_hausdorff
        
        # Get coordinates of burned cells
        pred_coords = np.column_stack(np.where(predicted > 0))
        actual_coords = np.column_stack(np.where(actual > 0))
        
        if len(pred_coords) == 0 or len(actual_coords) == 0:
            return float('inf')  # Infinite distance if one set is empty
        
        # Calculate bidirectional Hausdorff distance
        h1 = directed_hausdorff(pred_coords, actual_coords)[0]
        h2 = directed_hausdorff(actual_coords, pred_coords)[0]
        
        return max(h1, h2)
        
    except ImportError:
        logger.warning("SciPy not available, using simplified distance calculation")
        # Fallback: use simple centroid distance
        pred_coords = np.column_stack(np.where(predicted > 0))
        actual_coords = np.column_stack(np.where(actual > 0))
        
        if len(pred_coords) == 0 or len(actual_coords) == 0:
            return 1000.0  # Large penalty for empty predictions
        
        pred_centroid = np.mean(pred_coords, axis=0)
        actual_centroid = np.mean(actual_coords, axis=0)
        
        return np.linalg.norm(pred_centroid - actual_centroid)


def calculate_area_ratio(predicted: np.ndarray, actual: np.ndarray) -> float:
    """
    Calculate the ratio of predicted to actual burned area.
    
    Args:
        predicted: Binary array of predicted fire locations
        actual: Binary array of actual fire locations
        
    Returns:
        Area ratio (1.0 = perfect match, >1 = overprediction, <1 = underprediction)
    """
    pred_area = np.sum(predicted > 0)
    actual_area = np.sum(actual > 0)
    
    if actual_area == 0:
        return float('inf') if pred_area > 0 else 1.0
    
    return float(pred_area) / float(actual_area)


@dataclass
class ObjectiveResult:
    """Result of an objective function evaluation."""
    value: float
    components: Dict[str, float]
    is_valid: bool = True
    error_message: str = ""


class ObjectiveFunction(ABC):
    """Abstract base class for objective functions."""
    
    def __init__(self, name: str, higher_is_better: bool = True):
        """
        Initialize objective function.
        
        Args:
            name: Name of the objective function
            higher_is_better: Whether higher values indicate better performance
        """
        self.name = name
        self.higher_is_better = higher_is_better
        self.call_count = 0
        self.best_value = float('-inf') if higher_is_better else float('inf')
        self.evaluation_history = []
    
    @abstractmethod
    def evaluate(self, 
                 simulation_result: Dict[str, Any], 
                 target_data: Optional[Dict[str, Any]] = None) -> ObjectiveResult:
        """
        Evaluate the objective function.
        
        Args:
            simulation_result: Results from fire simulation
            target_data: Target/reference data for comparison
            
        Returns:
            ObjectiveResult with value and components
        """
        pass
    
    def __call__(self, simulation_result: Dict[str, Any], 
                 target_data: Optional[Dict[str, Any]] = None) -> ObjectiveResult:
        """Make the objective function callable."""
        self.call_count += 1
        result = self.evaluate(simulation_result, target_data)
        
        # Update best value
        if result.is_valid:
            if self.higher_is_better and result.value > self.best_value:
                self.best_value = result.value
            elif not self.higher_is_better and result.value < self.best_value:
                self.best_value = result.value
        
        # Store evaluation history
        self.evaluation_history.append({
            'call_number': self.call_count,
            'value': result.value,
            'is_valid': result.is_valid,
            'components': result.components.copy()
        })
        
        return result
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about objective function evaluations."""
        if not self.evaluation_history:
            return {'call_count': 0, 'best_value': None}
        
        valid_values = [h['value'] for h in self.evaluation_history if h['is_valid']]
        
        if not valid_values:
            return {'call_count': self.call_count, 'best_value': None, 'valid_evaluations': 0}
        
        return {
            'call_count': self.call_count,
            'valid_evaluations': len(valid_values),
            'best_value': self.best_value,
            'mean_value': np.mean(valid_values),
            'std_value': np.std(valid_values),
            'min_value': np.min(valid_values),
            'max_value': np.max(valid_values)
        }


class SpatialSimilarityObjective(ObjectiveFunction):
    """Objective function based on spatial similarity metrics."""
    
    def __init__(self, 
                 jaccard_weight: float = 0.4,
                 dice_weight: float = 0.3,
                 sorensen_weight: float = 0.3,
                 include_hausdorff: bool = False,
                 hausdorff_weight: float = 0.0):
        """
        Initialize spatial similarity objective.
        
        Args:
            jaccard_weight: Weight for Jaccard index
            dice_weight: Weight for Dice coefficient
            sorensen_weight: Weight for Sørensen coefficient
            include_hausdorff: Whether to include Hausdorff distance
            hausdorff_weight: Weight for Hausdorff distance (if included)
        """
        super().__init__("spatial_similarity", higher_is_better=True)
        
        # Normalize weights
        total_weight = jaccard_weight + dice_weight + sorensen_weight + hausdorff_weight
        self.jaccard_weight = jaccard_weight / total_weight
        self.dice_weight = dice_weight / total_weight
        self.sorensen_weight = sorensen_weight / total_weight
        self.hausdorff_weight = hausdorff_weight / total_weight
        self.include_hausdorff = include_hausdorff
    
    def evaluate(self, 
                 simulation_result: Dict[str, Any], 
                 target_data: Optional[Dict[str, Any]] = None) -> ObjectiveResult:
        """Evaluate spatial similarity between simulation and target."""
        try:
            # Extract simulation results
            if 'forest_model' not in simulation_result:
                return ObjectiveResult(
                    value=0.0,
                    components={},
                    is_valid=False,
                    error_message="No forest_model in simulation result"
                )
            
            forest_model = simulation_result['forest_model']
            
            # Get predicted fire state (combine all layers)
            if hasattr(forest_model, 'state'):
                # Debug: Check the shape and type of the state (only log once per evaluation)
                state_shape = forest_model.state.shape if hasattr(forest_model.state, 'shape') else 'no shape'
                state_type = type(forest_model.state)
                # Only log detailed state info in debug mode to reduce verbosity
                if logger.isEnabledFor(logging.DEBUG):
                    state_repr = str(forest_model.state)[:200]  # First 200 chars
                    logger.debug(f"Forest model state: shape={state_shape}, type={state_type}, repr={state_repr}")
                else:
                    logger.debug(f"Forest model state: shape={state_shape}, type={state_type}")
                
                # Handle different state formats
                if hasattr(forest_model.state, 'shape') and len(forest_model.state.shape) == 3:
                    # Ultra-efficient handling for SparseLayerAccessor - no conversion at all
                    if 'SparseLayerAccessor' in str(type(forest_model.state)):
                        # Direct sparse access - check if any layer has burning cells
                        width, height, num_layers = forest_model.state.shape
                        predicted_2d = np.zeros((width, height), dtype=float)
                        
                        # Access sparse layers directly without any conversion
                        for layer_idx in range(num_layers):
                            try:
                                # Get the sparse matrix directly from the accessor
                                sparse_matrix = forest_model.state.sparse_layers[layer_idx]
                                
                                # Check if this layer has any non-zero elements (burning cells)
                                if sparse_matrix.nnz > 0:
                                    # Get the coordinates of non-zero elements directly
                                    rows, cols = sparse_matrix.nonzero()
                                    
                                    # Mark these positions as burning in our 2D array
                                    for row, col in zip(rows, cols):
                                        if 0 <= row < width and 0 <= col < height:
                                            predicted_2d[row, col] = 1.0
                                            
                            except Exception as e:
                                logger.warning(f"Error accessing layer {layer_idx}: {e}")
                                continue
                        
                        # Any layer burning means the cell is burning (already handled above)
                    else:
                        # Regular 3D array: sum across layers to get 2D fire map
                        predicted_2d = np.sum(forest_model.state == 1, axis=2) > 0  # Any layer burning
                        predicted_2d = predicted_2d.astype(float)
                elif hasattr(forest_model.state, 'shape') and len(forest_model.state.shape) == 2:
                    # 2D array: use directly
                    predicted_2d = (forest_model.state == 1).astype(float)
                else:
                    # Fallback: create empty 2D array
                    logger.warning(f"Unexpected forest model state format: {state_shape}, creating fallback")
                    grid_size = getattr(forest_model, 'grid_size', (100, 100))
                    predicted_2d = np.zeros(grid_size, dtype=float)
            else:
                return ObjectiveResult(
                    value=0.0,
                    components={},
                    is_valid=False,
                    error_message="Forest model has no state attribute"
                )
            
            # Get target data
            if target_data is None or 'fire_perimeter' not in target_data:
                # Use synthetic target for testing
                logger.warning("No target data provided, using synthetic target")
                target_2d = self._create_synthetic_target(predicted_2d.shape)
            else:
                target_2d = target_data['fire_perimeter']
            
            # Ensure arrays are the same size
            if predicted_2d.shape != target_2d.shape:
                return ObjectiveResult(
                    value=0.0,
                    components={},
                    is_valid=False,
                    error_message=f"Shape mismatch: predicted {predicted_2d.shape} vs target {target_2d.shape}"
                )
            
            # Calculate individual metrics
            components = {}
            
            # Jaccard index
            jaccard = calculate_jaccard_index(predicted_2d, target_2d)
            components['jaccard_index'] = jaccard
            
            # Dice coefficient
            dice = calculate_dice_coefficient(predicted_2d, target_2d)
            components['dice_coefficient'] = dice
            
            # Sørensen coefficient (same as Dice)
            sorensen = calculate_sorensen_coefficient(predicted_2d, target_2d)
            components['sorensen_coefficient'] = sorensen
            
            # Optional: Hausdorff distance
            if self.include_hausdorff:
                hausdorff = calculate_hausdorff_distance(predicted_2d, target_2d)
                # Convert to similarity (lower distance = higher similarity)
                hausdorff_similarity = 1.0 / (1.0 + hausdorff / 10.0)  # Normalize
                components['hausdorff_similarity'] = hausdorff_similarity
            
            # Calculate weighted combination
            weighted_value = (
                self.jaccard_weight * jaccard +
                self.dice_weight * dice +
                self.sorensen_weight * sorensen
            )
            
            if self.include_hausdorff:
                weighted_value += self.hausdorff_weight * components['hausdorff_similarity']
            
            # Add additional components for analysis
            components['area_ratio'] = calculate_area_ratio(predicted_2d, target_2d)
            components['predicted_cells'] = np.sum(predicted_2d > 0)
            components['target_cells'] = np.sum(target_2d > 0)
            components['weighted_value'] = weighted_value
            
            return ObjectiveResult(
                value=weighted_value,
                components=components,
                is_valid=True
            )
            
        except Exception as e:
            logger.error(f"Error in spatial similarity evaluation: {e}")
            return ObjectiveResult(
                value=0.0,
                components={},
                is_valid=False,
                error_message=str(e)
            )
    
    def _create_synthetic_target(self, shape: Tuple[int, int]) -> np.ndarray:
        """Create a synthetic target for testing purposes."""
        target = np.zeros(shape)
        
        # Create a circular fire pattern
        center_x, center_y = shape[0] // 2, shape[1] // 2
        radius = min(shape) // 4
        
        y, x = np.ogrid[:shape[0], :shape[1]]
        mask = (x - center_x)**2 + (y - center_y)**2 <= radius**2
        target[mask] = 1.0
        
        return target


class FireBehaviorObjective(ObjectiveFunction):
    """Objective function based on fire behavior characteristics."""
    
    def __init__(self, 
                 target_burned_area: Optional[float] = None,
                 target_spread_rate: Optional[float] = None):
        """
        Initialize fire behavior objective.
        
        Args:
            target_burned_area: Target total burned area (cells)
            target_spread_rate: Target spread rate (cells per time step)
        """
        super().__init__("fire_behavior", higher_is_better=True)
        self.target_burned_area = target_burned_area
        self.target_spread_rate = target_spread_rate
    
    def evaluate(self, 
                 simulation_result: Dict[str, Any], 
                 target_data: Optional[Dict[str, Any]] = None) -> ObjectiveResult:
        """Evaluate fire behavior characteristics."""
        try:
            components = {}
            score_components = []
            
            # Extract simulation statistics
            stats = simulation_result.get('stats', {})
            
            # Burned area component
            if self.target_burned_area is not None:
                actual_burned = stats.get('total_burned_cells', 0)
                area_error = abs(actual_burned - self.target_burned_area) / max(self.target_burned_area, 1)
                area_score = 1.0 / (1.0 + area_error)
                components['burned_area_score'] = area_score
                components['actual_burned_area'] = actual_burned
                components['target_burned_area'] = self.target_burned_area
                score_components.append(area_score)
            
            # Spread rate component
            if self.target_spread_rate is not None:
                steps = stats.get('steps', 1)
                total_burned = stats.get('total_burned_cells', 0)
                actual_spread_rate = total_burned / max(steps, 1)
                rate_error = abs(actual_spread_rate - self.target_spread_rate) / max(self.target_spread_rate, 1)
                rate_score = 1.0 / (1.0 + rate_error)
                components['spread_rate_score'] = rate_score
                components['actual_spread_rate'] = actual_spread_rate
                components['target_spread_rate'] = self.target_spread_rate
                score_components.append(rate_score)
            
            # Calculate overall score
            if score_components:
                overall_score = np.mean(score_components)
            else:
                overall_score = 0.0
            
            components['overall_score'] = overall_score
            
            return ObjectiveResult(
                value=overall_score,
                components=components,
                is_valid=True
            )
            
        except Exception as e:
            logger.error(f"Error in fire behavior evaluation: {e}")
            return ObjectiveResult(
                value=0.0,
                components={},
                is_valid=False,
                error_message=str(e)
            )





def create_default_spatial_objective() -> SpatialSimilarityObjective:
    """Create a default spatial similarity objective with balanced weights."""
    return SpatialSimilarityObjective(
        jaccard_weight=0.4,
        dice_weight=0.3,
        sorensen_weight=0.3
    )





if __name__ == "__main__":
    # Example usage
    print("Objective Functions Example")
    print("=" * 50)
    
    # Create synthetic test data
    predicted = np.zeros((20, 20))
    predicted[8:12, 8:12] = 1  # Small square fire
    
    actual = np.zeros((20, 20))
    actual[7:13, 7:13] = 1  # Slightly larger overlapping fire
    
    # Test individual metrics
    print("Individual Metrics:")
    print(f"Jaccard Index: {calculate_jaccard_index(predicted, actual):.3f}")
    print(f"Dice Coefficient: {calculate_dice_coefficient(predicted, actual):.3f}")
    print(f"Sørensen Coefficient: {calculate_sorensen_coefficient(predicted, actual):.3f}")
    print(f"Area Ratio: {calculate_area_ratio(predicted, actual):.3f}")
    
    # Test objective function
    print("\nObjective Function Test:")
    spatial_obj = create_default_spatial_objective()
    
    # Create mock simulation result
    mock_forest_model = type('MockModel', (), {'state': np.stack([predicted] * 5, axis=2)})()
    mock_result = {'forest_model': mock_forest_model}
    mock_target = {'fire_perimeter': actual}
    
    result = spatial_obj.evaluate(mock_result, mock_target)
    print(f"Spatial Similarity Score: {result.value:.3f}")
    print(f"Components: {result.components}") 