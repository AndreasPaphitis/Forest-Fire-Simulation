#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Optimization Factory

This module provides factory functions to create optimized versions of simulation
components while maintaining 100% compatibility with the original implementations.

The factory allows for transparent optimization - existing code can use optimized
components without any changes by simply importing from this module instead.

Key Features:
1. Drop-in replacement for original components
2. Automatic optimization level selection based on grid size
3. Performance monitoring and metrics
4. Graceful fallback to original implementations
5. Runtime optimization toggles

Author: Forest Fire Simulation Team
Date: 2025
Version: 1.0
"""

import logging
from typing import Optional, Union, Dict, Any, Tuple
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)

# Import original implementations
from src.core.fire_simulation_engine import FireSimulationEngine
from src.core.forest_model import MemoryOptimizedForestModel, create_forest_model

# Import optimized implementations
try:
    from src.core.optimized_fire_simulation_engine import OptimizedFireSimulationEngine
    from src.core.optimized_forest_model import OptimizedMemoryOptimizedForestModel
    HAS_OPTIMIZATIONS = True
except ImportError as e:
    logger.warning(f"⚠️  Optimized components not available: {e}")
    HAS_OPTIMIZATIONS = False


class OptimizationConfig:
    """Configuration for optimization behavior."""
    
    def __init__(self):
        # Automatic optimization thresholds
        self.auto_optimize_threshold = 1_000_000  # 1M cells
        self.force_optimize_threshold = 10_000_000  # 10M cells
        
        # Optimization toggles
        self.enable_vectorized_processing = True
        self.enable_batch_updates = True
        self.enable_neighbor_caching = True
        self.enable_optimized_sparse_ops = True
        
        # Performance monitoring
        self.enable_performance_logging = True
        self.log_optimization_decisions = True
        
        # Fallback behavior
        self.graceful_fallback = True
        self.fallback_on_error = True


_global_optimization_config = OptimizationConfig()


def set_optimization_config(config: OptimizationConfig):
    """Set global optimization configuration."""
    global _global_optimization_config
    _global_optimization_config = config
    logger.info("🔧 Global optimization configuration updated")


def get_optimization_config() -> OptimizationConfig:
    """Get current optimization configuration."""
    return _global_optimization_config


def should_use_optimizations(grid_size: Union[int, Tuple[int, int]], num_layers: int = 1) -> Tuple[bool, str]:
    """
    Determine if optimizations should be used based on grid size and configuration.
    
    Args:
        grid_size: Grid size (int or (width, height) tuple)
        num_layers: Number of layers
        
    Returns:
        Tuple of (should_optimize, reason)
    """
    config = get_optimization_config()
    
    # Calculate total cells
    if isinstance(grid_size, tuple):
        width, height = grid_size
        total_cells = width * height * num_layers
    else:
        total_cells = grid_size * grid_size * num_layers
    
    # Check if optimizations are available
    if not HAS_OPTIMIZATIONS:
        return False, "Optimized components not available"
    
    # Force optimization for very large grids
    if total_cells >= config.force_optimize_threshold:
        return True, f"Large grid ({total_cells:,} cells) - forced optimization"
    
    # Auto optimization for medium grids
    if total_cells >= config.auto_optimize_threshold:
        return True, f"Medium grid ({total_cells:,} cells) - auto optimization"
    
    # No optimization for small grids
    return False, f"Small grid ({total_cells:,} cells) - standard implementation"


def create_optimized_fire_simulation_engine(forest_model=None, config=None, force_optimization: Optional[bool] = None):
    """
    Create a fire simulation engine with automatic optimization selection.
    
    Args:
        forest_model: Forest model instance
        config: Configuration
        force_optimization: Override automatic optimization decision
        
    Returns:
        Fire simulation engine (optimized or standard)
    """
    optimization_config = get_optimization_config()
    
    # Determine if we should use optimizations
    if force_optimization is not None:
        use_optimizations = force_optimization
        reason = "Manually forced" if force_optimization else "Manually disabled"
    else:
        # Auto-detect based on forest model size
        if forest_model and hasattr(forest_model, 'width') and hasattr(forest_model, 'height'):
            grid_size = (forest_model.width, forest_model.height)
            num_layers = getattr(forest_model, 'num_layers', 1)
            use_optimizations, reason = should_use_optimizations(grid_size, num_layers)
        else:
            use_optimizations = False
            reason = "Cannot determine grid size"
    
    # Log optimization decision
    if optimization_config.log_optimization_decisions:
        engine_type = "OptimizedFireSimulationEngine" if use_optimizations else "FireSimulationEngine"
        logger.info(f"🚀 Creating {engine_type}: {reason}")
    
    # Create engine
    try:
        if use_optimizations and HAS_OPTIMIZATIONS:
            engine = OptimizedFireSimulationEngine(forest_model, config)
            
            # Configure optimization settings
            if hasattr(engine, 'use_vectorized_processing'):
                engine.use_vectorized_processing = optimization_config.enable_vectorized_processing
            if hasattr(engine, 'use_batch_updates'):
                engine.use_batch_updates = optimization_config.enable_batch_updates
            if hasattr(engine, 'use_neighbor_caching'):
                engine.use_neighbor_caching = optimization_config.enable_neighbor_caching
            if hasattr(engine, 'use_optimized_sparse_ops'):
                engine.use_optimized_sparse_ops = optimization_config.enable_optimized_sparse_ops
            
            return engine
        else:
            return FireSimulationEngine(forest_model, config)
    
    except Exception as e:
        if optimization_config.fallback_on_error:
            logger.warning(f"⚠️  Failed to create optimized engine: {e}")
            logger.warning("   Falling back to standard engine")
            return FireSimulationEngine(forest_model, config)
        else:
            raise


def create_optimized_forest_model(grid_size, num_layers=1, force_optimization: Optional[bool] = None, **kwargs):
    """
    Create a forest model with automatic optimization selection.
    
    Args:
        grid_size: Grid size
        num_layers: Number of layers
        force_optimization: Override automatic optimization decision
        **kwargs: Additional arguments for forest model
        
    Returns:
        Forest model (optimized or standard)
    """
    optimization_config = get_optimization_config()
    
    # Determine if we should use optimizations
    if force_optimization is not None:
        use_optimizations = force_optimization
        reason = "Manually forced" if force_optimization else "Manually disabled"
    else:
        use_optimizations, reason = should_use_optimizations(grid_size, num_layers)
    
    # Log optimization decision
    if optimization_config.log_optimization_decisions:
        model_type = "OptimizedMemoryOptimizedForestModel" if use_optimizations else "MemoryOptimizedForestModel"
        logger.info(f"🌲 Creating {model_type}: {reason}")
    
    # Create forest model
    try:
        if use_optimizations and HAS_OPTIMIZATIONS:
            return OptimizedMemoryOptimizedForestModel(
                grid_size=grid_size,
                num_layers=num_layers,
                **kwargs
            )
        else:
            return MemoryOptimizedForestModel(
                grid_size=grid_size,
                num_layers=num_layers,
                **kwargs
            )
    
    except Exception as e:
        if optimization_config.fallback_on_error:
            logger.warning(f"⚠️  Failed to create optimized forest model: {e}")
            logger.warning("   Falling back to standard model")
            return MemoryOptimizedForestModel(
                grid_size=grid_size,
                num_layers=num_layers,
                **kwargs
            )
        else:
            raise


def create_simulation_components(grid_size, num_layers=1, config=None, force_optimization: Optional[bool] = None):
    """
    Create both forest model and simulation engine with consistent optimization.
    
    Args:
        grid_size: Grid size
        num_layers: Number of layers
        config: Configuration
        force_optimization: Override automatic optimization decision
        
    Returns:
        Tuple of (forest_model, simulation_engine)
    """
    optimization_config = get_optimization_config()
    
    # Determine optimization level
    if force_optimization is not None:
        use_optimizations = force_optimization
        reason = "Manually forced" if force_optimization else "Manually disabled"
    else:
        use_optimizations, reason = should_use_optimizations(grid_size, num_layers)
    
    # Log decision
    if optimization_config.log_optimization_decisions:
        logger.info(f"🏗️  Creating simulation components with optimizations: {use_optimizations}")
        logger.info(f"   Reason: {reason}")
    
    try:
        # Create forest model
        forest_model = create_optimized_forest_model(
            grid_size=grid_size,
            num_layers=num_layers,
            force_optimization=use_optimizations,
            config=config
        )
        
        # Create simulation engine
        simulation_engine = create_optimized_fire_simulation_engine(
            forest_model=forest_model,
            config=config,
            force_optimization=use_optimizations
        )
        
        return forest_model, simulation_engine
    
    except Exception as e:
        if optimization_config.fallback_on_error:
            logger.warning(f"⚠️  Failed to create optimized components: {e}")
            logger.warning("   Falling back to standard components")
            
            # Fall back to standard components
            forest_model = MemoryOptimizedForestModel(
                grid_size=grid_size,
                num_layers=num_layers,
                config=config
            )
            simulation_engine = FireSimulationEngine(forest_model, config)
            
            return forest_model, simulation_engine
        else:
            raise


def get_optimization_status() -> Dict[str, Any]:
    """Get current optimization status and capabilities."""
    config = get_optimization_config()
    
    return {
        'optimizations_available': HAS_OPTIMIZATIONS,
        'configuration': {
            'auto_optimize_threshold': config.auto_optimize_threshold,
            'force_optimize_threshold': config.force_optimize_threshold,
            'enable_vectorized_processing': config.enable_vectorized_processing,
            'enable_batch_updates': config.enable_batch_updates,
            'enable_neighbor_caching': config.enable_neighbor_caching,
            'enable_optimized_sparse_ops': config.enable_optimized_sparse_ops,
            'graceful_fallback': config.graceful_fallback,
            'fallback_on_error': config.fallback_on_error
        },
        'components': {
            'optimized_engine_available': HAS_OPTIMIZATIONS,
            'optimized_forest_model_available': HAS_OPTIMIZATIONS
        }
    }


def log_optimization_status():
    """Log current optimization status."""
    status = get_optimization_status()
    
    logger.debug("🚀 OPTIMIZATION STATUS:")
    logger.debug(f"   Optimizations available: {status['optimizations_available']}")
    logger.debug(f"   Auto-optimize threshold: {status['configuration']['auto_optimize_threshold']:,} cells")
    logger.debug(f"   Force-optimize threshold: {status['configuration']['force_optimize_threshold']:,} cells")
    
    if status['optimizations_available']:
        logger.debug("   Available optimizations:")
        logger.debug(f"     • Vectorized processing: {status['configuration']['enable_vectorized_processing']}")
        logger.debug(f"     • Batch updates: {status['configuration']['enable_batch_updates']}")
        logger.debug(f"     • Neighbor caching: {status['configuration']['enable_neighbor_caching']}")
        logger.debug(f"     • Optimized sparse ops: {status['configuration']['enable_optimized_sparse_ops']}")
    else:
        logger.debug("   No optimizations available - using standard implementations")


# Convenience aliases for backward compatibility
create_forest_model_optimized = create_optimized_forest_model
create_engine_optimized = create_optimized_fire_simulation_engine
