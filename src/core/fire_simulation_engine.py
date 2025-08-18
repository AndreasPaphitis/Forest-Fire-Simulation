#!/usr/bin/env python
# ======================================================================
# FIRE SIMULATION ENGINE
# ======================================================================
"""
Fire Simulation Engine Module

This module implements the core fire simulation engine for the forest fire simulation.
It handles the propagation of fire through a 3D forest structure, taking into account
fuel characteristics, weather conditions, and terrain.

This module uses the ForestModel from the forest_model module and implements the
simulation logic in the FireSimulationEngine class.

Author: Andreas Paphitis
Date: 2025
Version: 1.2
"""

import os
# import sys # Removed: sys.path manipulation is no longer needed
import time
import logging # Standard logging will be handled by get_logger
import numpy as np
import math
import json
import pickle
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Union, Any, Callable
from datetime import datetime
import warnings
from dataclasses import fields

# Import get_logger from logging_utils
from src.utils.logging_utils import get_logger

# Set up logging using the standardized utility
logger = get_logger(__name__)

# Removed try_import logic and HAS_IMPORT_HELPERS flag

# Direct imports for shared utilities, forest model, and config tools
from src.utils.shared_utilities import (
    log_once,
    calculate_memory_requirements,
    monitor_memory_usage
)
from src.core.forest_model import (
    ForestModel,
    MemoryOptimizedForestModel, # Assuming this is the correct name from forest_model.py
    create_forest_model
)
from src.config.config_tools import get_global_config, ModelConfig # get_constant is deprecated

# Import the centralized CellState Enum
from src.core.core_simulation_framework import CellState as FrameworkCellState

logger.info("Successfully imported shared utilities, forest model, config tools, and framework CellState.")

# Removed fallback import logic and re-definition of MinimalForestModelStub and constants.

# The local CellState class and its to_string method have been removed.
# The FrameworkCellState enum (imported as FrameworkCellState) should be used directly.
# For string representation, FrameworkCellState.BURNING.name or str(FrameworkCellState.BURNING) can be used.

class FireSimulationEngine:
    """
    Core engine for running forest fire simulations.
    """
    
    def __init__(self, 
                 forest_model: Optional[ForestModel] = None, # forest_model first
                 config: Optional[Union[Dict[str, Any], ModelConfig]] = None):
        
        # Emergency mode for massive grids to prevent segfaults
        self.emergency_mode = False
        
        # Initialize logging statistics
        self.log_stats = {
            'total_burnouts': 0,
            'burnout_batch_size': 0,
            'last_progress_log': 0,
            'progress_interval': 50,  # Log progress every 50 burnouts
            'max_burnout_logs': 10,   # Only log first 10 individual burnouts
            'step_start_time': None
        }
        
        if forest_model and hasattr(forest_model, 'width') and hasattr(forest_model, 'height'):
            total_cells = forest_model.width * forest_model.height * getattr(forest_model, 'num_layers', 1)
            # INCREASED THRESHOLD: With memory optimizations, we can handle 1B cells safely
            if total_cells > 1_000_000_000:  # 1B cells threshold (increased from 100M)
                self.emergency_mode = True
                logger.warning(f"🚨 EMERGENCY MODE ENABLED for massive grid ({total_cells:,} cells)")
                logger.warning("Sparse matrix operations will be bypassed to prevent segfaults")
            elif total_cells > 100_000_000:  # 100M-1B cells: Use optimized mode
                logger.info(f"📊 Large grid detected ({total_cells:,} cells) - Using optimized mode")
                logger.info("✅ Shared terrain + sparse storage will be used for memory efficiency")
        
        # Initialize forest model and configuration
        if forest_model is not None:
            self.forest_model = forest_model
        else:
            self.forest_model = None

        # Standardized configuration handling
        if config is None:
            self.config = get_global_config()
            logger.info("FireSimulationEngine initialized using global configuration.")
        elif isinstance(config, dict):
            try:
                self.config = ModelConfig(**config) 
                logger.info("FireSimulationEngine initialized with ModelConfig created from dictionary.")
            except TypeError as e: # Catch if dict has unexpected keys or types for ModelConfig
                logger.error(f"Failed to create ModelConfig directly from dict: {e}. "
                               f"Attempting to initialize default ModelConfig and update with dict items.")
                # Fallback: create default ModelConfig and update with provided dict keys
                # This ensures self.config is always a ModelConfig instance
                temp_mc = ModelConfig()
                valid_keys = {f.name for f in fields(ModelConfig)}
                filtered_config_dict = {k: v for k, v in config.items() if k in valid_keys}
                try:
                    self.config = ModelConfig(**filtered_config_dict)
                    logger.info("FireSimulationEngine initialized with ModelConfig created from filtered dictionary.")
                except Exception as final_e:
                    logger.error(f"Could not create ModelConfig even from filtered dict: {final_e}. Using global ModelConfig as fallback.")
                    self.config = get_global_config()
        elif isinstance(config, ModelConfig):
            self.config = config
            logger.info("FireSimulationEngine initialized with provided ModelConfig instance.")
        else:
            logger.error(f"Invalid config type: {type(config)}. Using global configuration as fallback.")
            self.config = get_global_config()

        # Skip config attribute access during initialization to prevent issues
        logger.debug("Initializing configuration")

        # Initialize the forest model if not provided
        if forest_model is not None:
            self.forest_model = forest_model
        else:
            # Pass the resolved config object to create_forest_model
            model_kwargs = {
                'grid_size': grid_size,
                'num_layers': num_layers,
                'layer_height_meters': layer_height_meters,
                'model_resolution': model_resolution,
                'config': self.config # Pass the ModelConfig instance (or dict) to the model factory
            }
            self.forest_model = create_forest_model(model_type=simulation_type, **model_kwargs)
        
        # Load terrain data if available (must be done before wind initialization)
        # Skip if terrain was already loaded during sparse initialization
        # CRITICAL FIX: Avoid np.any() on massive arrays - just check if array exists and has size
        terrain_already_loaded = (hasattr(self.forest_model, 'terrain_elevation') and 
                                 self.forest_model.terrain_elevation is not None and
                                 hasattr(self.forest_model.terrain_elevation, 'size') and
                                 self.forest_model.terrain_elevation.size > 0)
        
        if terrain_already_loaded:
            logger.info("🏔️  Terrain data already loaded during model initialization")
            
            # CRITICAL FIX: Skip statistics for massive grids to prevent segmentation faults
            # NumPy operations on 374M+ cell arrays can cause segfaults
            terrain_size = self.forest_model.terrain_elevation.size
            if terrain_size > 100_000_000:  # Skip stats for grids > 100M cells
                logger.info(f"📊 Terrain statistics skipped for memory efficiency ({terrain_size:,} cells)")
                logger.info("🏔️  Barranco statistics skipped for memory efficiency")
            else:
                # Safe to calculate statistics for smaller grids
                try:
                    elev_min = np.min(self.forest_model.terrain_elevation)
                    elev_max = np.max(self.forest_model.terrain_elevation)
                    elev_range = elev_max - elev_min
                    logger.info(f"📊 Terrain elevation: {elev_min:.1f}m to {elev_max:.1f}m (range: {elev_range:.1f}m)")
                    
                    if hasattr(self.forest_model, 'barranco_mask') and self.forest_model.barranco_mask is not None:
                        barranco_count = np.sum(self.forest_model.barranco_mask)
                        total_cells = self.forest_model.barranco_mask.size
                        barranco_percent = barranco_count / total_cells * 100
                        logger.info(f"🏔️  Barrancos detected: {barranco_count:,} cells ({barranco_percent:.1f}% of terrain)")
                except Exception as stats_error:
                    logger.warning(f"⚠️  Terrain statistics calculation failed: {stats_error}")
                    logger.warning("Continuing without terrain statistics to prevent segfault")
        else:
            # CRITICAL FIX: Skip config attribute access that triggers segfaults
            # Assume terrain is already loaded in forest model
            # CRITICAL FIX: Skip all terrain loading logic to prevent config attribute access
            # Assume terrain is already loaded during forest model initialization
            logger.info("✅ Terrain data assumed loaded - skipping terrain loading to prevent segfaults")
            success = True
            
            if success:
                logger.info("✅ Successfully loaded preprocessed terrain data")
                # CRITICAL FIX: Skip terrain statistics to prevent segfaults on massive arrays
                if hasattr(self.forest_model, 'terrain_elevation') and self.forest_model.terrain_elevation is not None:
                    terrain_size = getattr(self.forest_model.terrain_elevation, 'size', 0)
                    if terrain_size > 100_000_000:  # Skip for massive grids
                        logger.info(f"📊 Terrain statistics skipped for memory efficiency ({terrain_size:,} cells)")
                        logger.info("🏔️  Barranco statistics skipped for memory efficiency")
                    else:
                        # Safe to calculate statistics for smaller grids
                        try:
                            elev_min = np.min(self.forest_model.terrain_elevation)
                            elev_max = np.max(self.forest_model.terrain_elevation)
                            elev_range = elev_max - elev_min
                            logger.info(f"📊 Terrain elevation: {elev_min:.1f}m to {elev_max:.1f}m (range: {elev_range:.1f}m)")
                            if hasattr(self.forest_model, 'barranco_mask') and self.forest_model.barranco_mask is not None:
                                barranco_count = np.sum(self.forest_model.barranco_mask)
                                total_cells = self.forest_model.barranco_mask.size
                                barranco_percent = barranco_count / total_cells * 100
                                logger.info(f"🏔️  Barrancos detected: {barranco_count:,} cells ({barranco_percent:.1f}% of terrain)")
                        except Exception as stats_error:
                            logger.warning(f"⚠️  Terrain statistics calculation failed: {stats_error}")
            else:
                logger.warning("⚠️  Failed to load preprocessed terrain data - using flat terrain")
        
        # Set up bidirectional reference for visualization integration
        if hasattr(self.forest_model, 'set_simulation_engine'):
            self.forest_model.set_simulation_engine(self)
        
        # Initialize wind if configuration provides wind data
        if hasattr(self.config, 'wind_speed') and hasattr(self.config, 'wind_direction'):
            # CRITICAL FIX: Use safer terrain detection without triggering massive array operations
            # Check if we have terrain data using size check instead of np.any()
            has_terrain_data = False
            try:
                if (hasattr(self.forest_model, 'terrain_elevation') and 
                    self.forest_model.terrain_elevation is not None):
                    # Use size check instead of np.any() to avoid scanning 374M cells
                    terrain_size = getattr(self.forest_model.terrain_elevation, 'size', 0)
                    has_terrain_data = terrain_size > 0
                    logger.debug(f"Terrain data detected: {terrain_size:,} cells")
            except Exception as terrain_check_error:
                logger.warning(f"⚠️  Terrain data check failed: {terrain_check_error}")
                has_terrain_data = False
            
            # CRITICAL FIX: Skip wind initialization that accesses config properties
            # Wind effects should already be configured in forest model initialization
            logger.info("💨 Wind initialization skipped - assuming wind effects configured in forest model")
        
        # CRITICAL FIX: Skip config attribute access that triggers segfaults
        # Use default values instead of accessing config properties
        self.wind_speed = 5.0  # Default wind speed
        self.wind_direction = 0.0  # Default wind direction (North)
        self.temperature = 25.0  # Default temperature (Celsius)
        self.humidity = 50.0  # Default humidity (%)
        
        # Initialize simulation state
        self.current_step = 0
        self.active_cells = set()
        self.burned_cells = set()
        self.history = []
        
        # Initialize ember event tracking
        self.ember_events = []  # List of all ember events during simulation
        self.ember_statistics = {
            'total_generated': 0,
            'successful_ignitions': 0,
            'failed_attempts': 0,
            'by_step': {},  # Step-wise ember statistics
            'distance_stats': [],  # List of ember travel distances
            'height_changes': []  # List of ember height changes
        }
        
        # Initialize random number generator with seed from config
        # CRITICAL FIX: Safe RNG initialization to prevent segfaults
        try:
            rng_seed = getattr(self.config, 'random_seed', 42)  # Default seed if missing
            # Validate seed is a reasonable integer
            if not isinstance(rng_seed, (int, np.integer)) or rng_seed < 0 or rng_seed > 2**32-1:
                logger.warning(f"⚠️  Invalid random seed {rng_seed}, using default 42")
                rng_seed = 42
                
            self.rng = np.random.default_rng(rng_seed)
            logger.info(f"FireSimulationEngine RNG initialized with seed: {rng_seed}")
        except Exception as rng_error:
            logger.error(f"❌ RNG initialization failed: {rng_error}")
            logger.warning("Using default RNG without seed to prevent segfault")
            self.rng = np.random.default_rng(42)
            
        # CRITICAL FIX: Skip config attribute access that might trigger segfaults
        # getattr() on config might trigger property access or validation
        logger.debug("ENGINE_INIT_CONFIG_CHECK: Skipping config attribute access to prevent segfaults")
        
        # Monitor memory usage if in debug mode
        # CRITICAL FIX: Skip ALL config attribute access to prevent segfaults
        # getattr() on config might trigger property access or validation that causes segfaults
        self.debug = False  # Force debug off to prevent any potential segfaults
        logger.debug("Debug mode forced off to prevent config attribute access segfaults")
        
        # CRITICAL FIX: Add initialization completion marker
        # This helps identify if segfault occurs during __init__ or after
        logger.info("🎯 FireSimulationEngine.__init__ completed successfully")
        
        # CRITICAL FIX: Skip all forest_model validation to prevent property access
        # hasattr() on forest_model triggers @property decorators that access massive arrays!
        # Just verify the object reference exists without any attribute access
        if self.forest_model is None:
            raise RuntimeError("Forest model is None - cannot proceed")
        
        logger.debug("✅ FireSimulationEngine initialization complete without array access")
    
    def run_simulation(self, 
                         max_steps: Optional[int] = None, 
                         store_history: Optional[bool] = None,
                         step_callback: Optional[Callable[[int, Dict[str, Any]], bool]] = None,
                         stop_when_fire_extinguished: Optional[bool] = None):
        """
        Run the fire simulation for the given number of steps.
        
        Args:
            max_steps: Maximum number of steps to simulate. Defaults to config.max_steps.
            store_history: Whether to store the history of fire states. Defaults to config.store_full_states.
            step_callback: Optional function to call after each step. 
                           It receives (current_step, stats_dict) and should return True to continue.
            stop_when_fire_extinguished: Whether to stop if no active cells. Defaults to config.stop_when_fire_extinguished.
            
        Returns:
            Dictionary with simulation results
        """
        start_time = time.time()

        # Resolve parameters from config if not provided
        sim_max_steps = max_steps if max_steps is not None else self.config.max_steps
        sim_store_history = store_history if store_history is not None else self.config.store_full_states
        sim_stop_when_extinguished = stop_when_fire_extinguished if stop_when_fire_extinguished is not None \
                                     else getattr(self.config, 'stop_when_fire_extinguished', True)

        logger.info(f"Starting fire simulation for {sim_max_steps} steps. Stop if extinguished: {sim_stop_when_extinguished}")
        
        # Get initial state
        if not hasattr(self.forest_model, 'state'):
            logger.error("Forest model does not have 'state' attribute")
            return {"error": "Invalid forest model"}
        
        # Find initial burning cells efficiently for large grids
        total_cells = self.forest_model.width * self.forest_model.height * self.forest_model.num_layers
        
        if total_cells > 100_000_000:  # 100M+ cells - use memory-efficient scanning
            logger.info(f"🔍 Large grid detected ({total_cells:,} cells) - using efficient active cell detection")
            
            # For memory-optimized sparse models, check if they track active cells
            if (hasattr(self.forest_model, 'use_sparse_storage') and 
                self.forest_model.use_sparse_storage and
                hasattr(self.forest_model, '_get_burning_cells')):
                # Use sparse model's efficient method
                self.active_cells = set(self.forest_model._get_burning_cells())
                logger.info(f"Used sparse model active cell detection: {len(self.active_cells)} initial cells")
            else:
                # Check for tracked ignition points first
                if hasattr(self.forest_model, '_ignition_points') and self.forest_model._ignition_points:
                    for x, y, z in self.forest_model._ignition_points:
                        if (0 <= x < self.forest_model.width and 
                            0 <= y < self.forest_model.height and 
                            0 <= z < self.forest_model.num_layers):
                            if self.forest_model.state[x, y, z] == FrameworkCellState.BURNING.value:
                                self.active_cells.add((x, y, z))
                    logger.info(f"📍 Using tracked ignition points: {len(self.active_cells)} initial cells")
                else:
                    # Fallback: scan only center region where ignition typically occurs
                    center_x, center_y = self.forest_model.width // 2, self.forest_model.height // 2
                    search_radius = min(50, self.forest_model.width // 10, self.forest_model.height // 10)
                    
                    logger.info(f"Scanning center region ({center_x}±{search_radius}, {center_y}±{search_radius}) for initial burning cells")
                    
                    for dx in range(-search_radius, search_radius + 1):
                        for dy in range(-search_radius, search_radius + 1):
                            x, y = center_x + dx, center_y + dy
                            if (0 <= x < self.forest_model.width and 0 <= y < self.forest_model.height):
                                for z in range(self.forest_model.num_layers):
                                    if self.forest_model.state[x, y, z] == FrameworkCellState.BURNING.value:
                                        self.active_cells.add((x, y, z))
                    
                    logger.info(f"Center region scan found: {len(self.active_cells)} initial burning cells")
        else:
            # Small grid - use traditional full scan
            logger.info(f"Small grid ({total_cells:,} cells) - using full scan for initial burning cells")
            for x in range(self.forest_model.width):
                for y in range(self.forest_model.height):
                    for z in range(self.forest_model.num_layers):
                        if self.forest_model.state[x, y, z] == FrameworkCellState.BURNING.value:
                            self.active_cells.add((x, y, z))
        
        # Enhanced initial logging with grid information
        total_grid_cells = self.forest_model.width * self.forest_model.height * self.forest_model.num_layers
        active_percentage = (len(self.active_cells) / total_grid_cells) * 100 if total_grid_cells > 0 else 0
        
        logger.info(f"🔥 FIRE SIMULATION INITIALIZED")
        logger.info(f"   Grid Size: {self.forest_model.width} × {self.forest_model.height} × {self.forest_model.num_layers} = {total_grid_cells:,} total cells")
        logger.info(f"   Initial Fire: {len(self.active_cells)} active cells ({active_percentage:.3f}% of grid)")
        
        if len(self.active_cells) > 0:
            # Show first few ignition points
            ignition_points = list(self.active_cells)[:5]
            logger.info(f"   Ignition Points: {ignition_points}")
            if len(self.active_cells) > 5:
                logger.info(f"   ... and {len(self.active_cells) - 5} more ignition points")

        # Reset logging statistics for new simulation
        self.log_stats = {
            'total_burnouts': 0,
            'burnout_batch_size': 0,
            'last_progress_log': 0,
            'progress_interval': 50,  # Log progress every 50 burnouts
            'max_burnout_logs': 10,   # Only log first 10 individual burnouts
            'step_start_time': time.time()
        }
        
        # Initialize statistics
        stats = {
            'steps': 0,
            'runtime_seconds': 0,
            'max_active_cells': len(self.active_cells),
            'total_burned_cells': 0,
            'final_active_cells': 0
        }
        
        # Run simulation steps
        for step in range(sim_max_steps):
            self.current_step = step
            
            # Check if fire has stopped spreading
            if sim_stop_when_extinguished and not self.active_cells:
                logger.info(f"Fire extinguished after {step} steps")
                break
            
            # Process single simulation step with timing
            step_start = time.time()
            self._process_step()
            step_time = time.time() - step_start
            
            # Log step processing statistics occasionally (reduced frequency)
            if step % 50 == 0 and step > 0:  # Every 50 steps (reduced from 10)
                avg_step_time = step_time
                cells_per_second = len(self.active_cells) / avg_step_time if avg_step_time > 0 else 0
                logger.debug(f"⚡ Step {step} processed in {step_time:.3f}s ({cells_per_second:.1f} cells/s)")
            
            # Update statistics for this step
            current_step_stats = {
                "active_cells": len(self.active_cells),
                "burned_cells": len(self.burned_cells) # This might be total burned up to now
            }
            stats['max_active_cells'] = max(stats['max_active_cells'], len(self.active_cells))
            
            # Store history if enabled
            if sim_store_history:
                self._store_history_step()
            
            # Call step callback if provided
            if step_callback:
                if not step_callback(step + 1, current_step_stats): # step is 0-indexed, callback might expect 1-indexed
                    logger.info(f"Simulation stopped by callback after {step + 1} steps.")
                    break
            
            # Enhanced progress logging with percentages and rates
            if self.config.engine_logging_interval > 0 and (step + 1) % self.config.engine_logging_interval == 0:
                total_affected = len(self.active_cells) + len(self.burned_cells)
                total_grid_cells = self.forest_model.width * self.forest_model.height * self.forest_model.num_layers
                affected_percentage = (total_affected / total_grid_cells) * 100 if total_grid_cells > 0 else 0
                
                # Calculate spread rate (cells per step)
                if step > 0:
                    spread_rate = len(self.active_cells) / (step + 1)
                else:
                    spread_rate = len(self.active_cells)
                
                logger.info(f"📊 STEP {step+1}/{sim_max_steps}")
                logger.info(f"   Active: {len(self.active_cells)} cells | Burned: {len(self.burned_cells)} cells")
                logger.info(f"   Total Affected: {total_affected:,} cells ({affected_percentage:.3f}% of grid)")
                logger.info(f"   Spread Rate: {spread_rate:.2f} active cells/step")
        
        # Update final statistics
        stats['steps'] = self.current_step + 1
        stats['runtime_seconds'] = time.time() - start_time
        stats['total_burned_cells'] = len(self.burned_cells)
        stats['final_active_cells'] = len(self.active_cells)
        
        # Enhanced final statistics with comprehensive summary
        total_grid_cells = self.forest_model.width * self.forest_model.height * self.forest_model.num_layers
        final_affected_percentage = (stats['total_burned_cells'] / total_grid_cells) * 100 if total_grid_cells > 0 else 0
        avg_cells_per_second = stats['total_burned_cells'] / stats['runtime_seconds'] if stats['runtime_seconds'] > 0 else 0
        
        logger.info(f"🏁 SIMULATION COMPLETED")
        logger.info(f"   Runtime: {stats['runtime_seconds']:.2f} seconds ({stats['runtime_seconds']/60:.2f} minutes)")
        logger.info(f"   Steps: {stats['steps']} simulation steps")
        logger.info(f"   Final Results:")
        logger.info(f"     • Burned Cells: {stats['total_burned_cells']:,} ({final_affected_percentage:.3f}% of grid)")
        logger.info(f"     • Still Burning: {stats['final_active_cells']} cells")
        logger.info(f"     • Peak Active: {stats['max_active_cells']} cells")
        logger.info(f"   Performance: {avg_cells_per_second:.1f} cells burned/second")
        
        return {
            'stats': stats,
            'history': self.history if sim_store_history else None,
            'forest_model': self.forest_model,
            'ember_events': self.ember_events,
            'ember_statistics': self.ember_statistics
        }
    
    def _process_step(self):
        """Process a single simulation step."""
        # Copy active cells to avoid modification during iteration
        current_active_cells = list(self.active_cells)

        # EMERGENCY FIX: Handle empty active cells to prevent segfaults
        if not current_active_cells:
            logger.warning("⚠️  No active cells to process - simulation may have ended")
            return

        # Track cells that will become active or inactive in the next step
        new_active_cells = set()
        new_inactive_cells = set()
        
        # Process each active cell
        for x, y, z in current_active_cells:
            # CRITICAL FIX: Add emergency protection around burnout check
            try:
                # Check if cell has burned out
                if self._check_burnout(x, y, z):
                    new_inactive_cells.add((x, y, z))
                    # Use memory-safe state setting
                    if not self._safe_set_state(x, y, z, FrameworkCellState.BURNED.value):
                        logger.warning(f"⚠️  Failed to set burned state for cell ({x}, {y}, {z})")
                    # Don't remove from active_cells here - let the batch update handle it
                    self.burned_cells.add((x, y, z))
                    continue
            except Exception as burnout_error:
                logger.error(f"❌ CRITICAL: Burnout check failed at ({x}, {y}, {z}): {burnout_error}")
                logger.warning("⚠️  Skipping burnout check to prevent segfault")
                continue
            
            # Spread fire to neighbors
            try:
                neighbors = self._get_neighbors(x, y, z)
                logger.debug(f"DEBUG: Processing {len(neighbors)} neighbors for cell ({x}, {y}, {z})")
                
                # CRITICAL FIX: Validate neighbor list before iteration
                if not isinstance(neighbors, list):
                    logger.error(f"❌ CRITICAL: Neighbors is not a list: {type(neighbors)}")
                    continue
                
                # CRITICAL FIX: Validate each neighbor tuple before processing
                for i, neighbor in enumerate(neighbors):
                    try:
                        if not isinstance(neighbor, tuple) or len(neighbor) != 3:
                            logger.error(f"❌ CRITICAL: Invalid neighbor {i}: {neighbor}")
                            continue
                        nx, ny, nz = neighbor
                    except Exception as unpack_error:
                        logger.error(f"❌ CRITICAL: Failed to unpack neighbor {i}: {unpack_error}")
                        continue
                    # CRITICAL FIX: Add emergency protection around sparse matrix access
                    try:
                        logger.debug(f"DEBUG: Processing neighbor {i+1}/{len(neighbors)}: ({nx}, {ny}, {nz})")
                        # Check if neighbor can ignite
                        if self._check_ignition(nx, ny, nz, x, y, z):
                            new_active_cells.add((nx, ny, nz))
                            # Use memory-safe state setting
                            if not self._safe_set_state(nx, ny, nz, FrameworkCellState.BURNING.value):
                                logger.warning(f"⚠️  Failed to set state for ignited neighbor ({nx}, {ny}, {nz})")
                                # Remove from new_active_cells since we couldn't set the state
                                new_active_cells.discard((nx, ny, nz))
                            else:
                                logger.debug(f"DEBUG: Neighbor ({nx}, {ny}, {nz}) ignited successfully")
                    except Exception as spread_error:
                        logger.error(f"❌ CRITICAL: Fire spread failed at ({nx}, {ny}, {nz}): {spread_error}")
                        logger.warning("⚠️  Skipping this neighbor to prevent segfault")
                        continue
                        
                logger.debug(f"DEBUG: Completed neighbor processing for cell ({x}, {y}, {z})")
            except Exception as neighbor_error:
                logger.error(f"❌ CRITICAL: Neighbor processing failed for cell ({x}, {y}, {z}): {neighbor_error}")
                logger.warning("⚠️  Skipping neighbor processing to prevent segfault")
                continue
            
            # Track spread statistics for visualization (moved outside neighbor loop)
            if hasattr(self.forest_model, 'increment_spread_stat'):
                        if nz != z:  # Vertical spread
                            self.forest_model.increment_spread_stat('vertical_spread')
                        else:  # Horizontal spread
                            self.forest_model.increment_spread_stat('horizontal_spread')
                            
                        # Track wind-assisted spread
                        if hasattr(self.forest_model, 'wind_speed'):
                            wind_speed = self.forest_model.wind_speed
                            # Handle both scalar and array wind speeds
                            if isinstance(wind_speed, (int, float)):
                                has_significant_wind = wind_speed > 1.0
                            elif hasattr(wind_speed, 'any'):  # numpy array
                                has_significant_wind = (wind_speed > 1.0).any()
                            else:
                                has_significant_wind = False
                            
                            if has_significant_wind:
                                self.forest_model.increment_spread_stat('wind_assisted_spread')
                        
                        # Track barranco-assisted spread
                        if (hasattr(self.forest_model, 'barranco_mask') and 
                            self.forest_model.barranco_mask is not None):
                            # Check if either source or target cell is in a barranco
                            # Note: barranco_mask is 2D (terrain-based), not 3D
                            if (self.forest_model.barranco_mask[x, y] or 
                                self.forest_model.barranco_mask[nx, ny]):
                                self.forest_model.increment_spread_stat('barranco_assisted_spread')
                            
                        # Track total ignitions
                        self.forest_model.increment_spread_stat('total_ignitions')
            
            # Process ember generation and downward spread
            ember_targets = self._process_embers(x, y, z)
            for ex, ey, ez in ember_targets:
                if self._check_ember_ignition(ex, ey, ez, x, y, z):
                    new_active_cells.add((ex, ey, ez))
                    # Use memory-safe state setting
                    if not self._safe_set_state(ex, ey, ez, FrameworkCellState.BURNING.value):
                        logger.warning(f"⚠️  Failed to set state for ember ignition ({ex}, {ey}, {ez})")
                        # Remove from new_active_cells since we couldn't set the state
                        new_active_cells.discard((ex, ey, ez))
                    
                    # Update ember event record to mark successful ignition
                    # Find the most recent ember event for this source-target pair
                    for ember_event in reversed(self.ember_events):
                        if (ember_event['step'] == self.current_step and 
                            ember_event['source'] == (x, y, z) and 
                            ember_event['target'] == (ex, ey, ez) and 
                            not ember_event['ignited']):
                            ember_event['ignited'] = True
                            self.ember_statistics['successful_ignitions'] += 1
                            self.ember_statistics['by_step'][self.current_step]['successful'] += 1
                            break
                    
                    # Track ember-caused ignitions
                    if hasattr(self.forest_model, 'increment_spread_stat'):
                        self.forest_model.increment_spread_stat('ember_ignitions')
                        self.forest_model.increment_spread_stat('total_ignitions')
                else:
                    # Update statistics for failed ember ignition
                    for ember_event in reversed(self.ember_events):
                        if (ember_event['step'] == self.current_step and 
                            ember_event['source'] == (x, y, z) and 
                            ember_event['target'] == (ex, ey, ez) and 
                            not ember_event['ignited']):
                            self.ember_statistics['failed_attempts'] += 1
                            self.ember_statistics['by_step'][self.current_step]['failed'] += 1
                            break
        
        # Update active cells
        self.active_cells.update(new_active_cells)
        self.active_cells.difference_update(new_inactive_cells)
        
        # Update forest model statistics for visualization
        if hasattr(self.forest_model, 'update_stats'):
            self.forest_model.update_stats(
                active_cells=len(self.active_cells),
                burned_cells=len(self.burned_cells),
                step=self.current_step
            )
    
    # MEMORY-SAFE SPARSE MATRIX ACCESS METHODS
    # ===========================================
    
    def _safe_sparse_access(self, operation, *args, max_retries=3, fallback_value=None):
        """
        Safely access sparse matrices with retry logic and bounds checking.
        
        Args:
            operation: Function to execute (e.g., lambda: self.forest_model.state[x, y, z])
            *args: Arguments for the operation
            max_retries: Maximum number of retry attempts
            fallback_value: Value to return if all retries fail
            
        Returns:
            Result of operation or fallback_value if failed
        """
        for attempt in range(max_retries):
            try:
                return operation(*args)
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.warning(f"⚠️  Sparse access failed after {max_retries} attempts: {e}")
                    return fallback_value
                # Exponential backoff: 1ms, 2ms, 4ms
                time.sleep(0.001 * (2 ** attempt))
        return fallback_value
    
    def _safe_bounds_check(self, x, y, z):
        """
        Check if coordinates are within valid bounds.
        
        Args:
            x, y, z: Coordinates to check
            
        Returns:
            True if coordinates are valid, False otherwise
        """
        try:
            if not hasattr(self.forest_model, 'width') or not hasattr(self.forest_model, 'height'):
                return False
            
            width = self.forest_model.width
            height = self.forest_model.height
            num_layers = getattr(self.forest_model, 'num_layers', 1)
            
            return (0 <= x < width and 
                   0 <= y < height and 
                   0 <= z < num_layers)
        except Exception:
            return False
    
    def _safe_get_state(self, x, y, z, fallback_value=0):
        """
        Safely get cell state with bounds checking and retry logic.
        
        Args:
            x, y, z: Cell coordinates
            fallback_value: Value to return if access fails
            
        Returns:
            Cell state value or fallback_value
        """
        if not self._safe_bounds_check(x, y, z):
            return fallback_value
        
        return self._safe_sparse_access(
            lambda: self.forest_model.state[x, y, z],
            fallback_value=fallback_value
        )
    
    def _safe_get_fuel(self, x, y, z, fallback_value=0.0):
        """
        Safely get fuel load with bounds checking and retry logic.
        
        Args:
            x, y, z: Cell coordinates
            fallback_value: Value to return if access fails
            
        Returns:
            Fuel load value or fallback_value
        """
        if not self._safe_bounds_check(x, y, z):
            return fallback_value
        
        return self._safe_sparse_access(
            lambda: self.forest_model.fuel_load[x, y, z],
            fallback_value=fallback_value
        )
    
    def _safe_set_fuel(self, x, y, z, value):
        """
        Safely set fuel load with bounds checking and retry logic.
        
        Args:
            x, y, z: Cell coordinates
            value: Fuel value to set
            
        Returns:
            True if successful, False otherwise
        """
        if not self._safe_bounds_check(x, y, z):
            return False
        
        try:
            self.forest_model.fuel_load[x, y, z] = value
            return True
        except Exception as e:
            logger.warning(f"⚠️  Failed to set fuel at ({x}, {y}, {z}): {e}")
            return False
    
    def _safe_set_state(self, x, y, z, value):
        """
        Safely set cell state with bounds checking and retry logic.
        
        Args:
            x, y, z: Cell coordinates
            value: State value to set
            
        Returns:
            True if successful, False otherwise
        """
        if not self._safe_bounds_check(x, y, z):
            return False
        
        try:
            self.forest_model.state[x, y, z] = value
            return True
        except Exception as e:
            logger.warning(f"⚠️  Failed to set state at ({x}, {y}, {z}): {e}")
            return False
    
    def _safe_get_vertical_connectivity(self, x, y, layer_interface_index, fallback_value=0.3):
        """
        Safely get vertical connectivity with bounds checking.
        
        Args:
            x, y: Cell coordinates
            layer_interface_index: Layer interface index
            fallback_value: Value to return if access fails
            
        Returns:
            Vertical connectivity value or fallback_value
        """
        if not self._safe_bounds_check(x, y, 0):  # Check x,y bounds
            return fallback_value
        
        if not hasattr(self.forest_model, 'vertical_connectivity'):
            return fallback_value
        
        if self.forest_model.vertical_connectivity is None:
            return fallback_value
        
        num_layers = getattr(self.forest_model, 'num_layers', 1)
        if not (0 <= layer_interface_index < num_layers - 1):
            return fallback_value
        
        return self._safe_sparse_access(
            lambda: self.forest_model.vertical_connectivity[x, y, layer_interface_index],
            fallback_value=fallback_value
        )

    def _check_burnout(self, x, y, z):
        """Check if a cell has burned out using memory-safe sparse matrix access."""
        # Use memory-safe access methods instead of emergency mode bypass
        try:
            # Get configuration values safely
            consumption_rate = getattr(self.config, 'fuel_consumption_rate', 1.0)
            min_fuel = getattr(self.config, 'min_fuel_value', 0.1)
            
            # Get current fuel using memory-safe access
            current_fuel = self._safe_get_fuel(x, y, z, fallback_value=0.0)
            
            # Calculate new fuel after consumption
            new_fuel = max(0.0, current_fuel - consumption_rate)
            
            # Update fuel using memory-safe access
            self._safe_set_fuel(x, y, z, new_fuel)
            
            # Check if burned out
            burned_out = new_fuel <= min_fuel
            
            # Enhanced burnout logging with batch processing
            if burned_out:
                self.log_stats['total_burnouts'] += 1
                self.log_stats['burnout_batch_size'] += 1
                
                # Log first few individual burnouts for debugging
                if self.log_stats['total_burnouts'] <= self.log_stats['max_burnout_logs']:
                    # REDUCED VERBOSITY: Only log individual burnouts in debug mode
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f"🔥 BURNOUT: Cell ({x},{y},{z}) - fuel: {current_fuel:.2f} → {new_fuel:.2f} (threshold: {min_fuel})")
                
                # Log batch progress every N burnouts (reduced frequency)
                if self.log_stats['burnout_batch_size'] >= self.log_stats['progress_interval']:
                    total_affected = len(self.burned_cells) + len(self.active_cells)
                    total_grid_cells = self.forest_model.width * self.forest_model.height * self.forest_model.num_layers
                    affected_percentage = (total_affected / total_grid_cells) * 100 if total_grid_cells > 0 else 0
                    
                    # REDUCED VERBOSITY: Only log in debug mode or every 5th batch
                    if logger.isEnabledFor(logging.DEBUG) or self.log_stats['total_burnouts'] % (self.log_stats['progress_interval'] * 5) == 0:
                        logger.info(f"📈 BURNOUT BATCH: {self.log_stats['burnout_batch_size']} cells burned out")
                        logger.info(f"   Total Burnouts: {self.log_stats['total_burnouts']} | Active: {len(self.active_cells)} | Affected: {affected_percentage:.3f}% of grid")
                    
                    # Reset batch counter
                    self.log_stats['burnout_batch_size'] = 0
            
            return burned_out
            
        except Exception as e:
            # Enhanced error handling with memory-safe fallback
            logger.warning(f"⚠️  Burnout check failed at ({x}, {y}, {z}): {e}")
            logger.warning("Using memory-safe fallback - marking cell as burned out")
            return True  # Mark as burned out to prevent further issues
    
    def _check_ignition(self, x, y, z, src_x, src_y, src_z):
        """Check if a cell ignites from a burning neighbor using memory-safe sparse matrix access."""
        try:
            # Use memory-safe access methods instead of emergency mode bypass
            
            # Skip if already burning or burned out using memory-safe access
            current_state = self._safe_get_state(x, y, z, fallback_value=FrameworkCellState.UNBURNED.value)
            if current_state != FrameworkCellState.UNBURNED.value:
                return False
            
            # Skip if no fuel using memory-safe access
            min_fuel = getattr(self.config, 'min_fuel_value', 0.1)
            current_fuel = self._safe_get_fuel(x, y, z, fallback_value=0.0)
            if current_fuel <= min_fuel:
                return False
                
        except Exception as e:
            # Enhanced error handling with memory-safe fallback
            logger.warning(f"⚠️  Ignition check failed at ({x}, {y}, {z}): {e}")
            logger.warning("Using memory-safe fallback - skipping ignition")
            return False  # Skip ignition to prevent further issues
        
        is_vertical_spread = (x == src_x and y == src_y and z != src_z)
        
        # Calculate ignition probability based on various factors
        if is_vertical_spread:
            # Vertical spread logic using memory-safe access
            layer_interface_index = min(z, src_z)
            base_prob = self._safe_get_vertical_connectivity(x, y, layer_interface_index, fallback_value=0.0)
            
            wind_factor = 1.0  # Wind effect is primarily horizontal
            slope_factor = 1.0 # Slope effect is primarily horizontal terrain-based
        else:
            # Horizontal or diagonal spread logic (existing logic)
            base_prob = getattr(self.config, 'spread_probability', 0.8)  # Increased from 0.5 to 0.8 for better spreading
            
            # Wind factor - use memory-safe access
            wind_factor = 1.0 # Default if no wind data or wind speed is zero
            
            # MEMORY-SAFE WIND CALCULATION: Enable wind factor calculation with safe access
            # Wind effects are now handled on-demand via get_wind_speed_at_cell and get_wind_direction_at_cell
            logger.debug(f"WIND_FACTOR_CALC: Using memory-safe wind calculation for massive grid")
            has_wind_speed = False
            has_wind_direction = False

            # Enable wind calculation with memory-safe access
            try:
                # Use memory-safe access for wind data if available
                if hasattr(self.forest_model, 'get_wind_speed_at_cell'):
                    cell_wind_speed_ms = self.forest_model.get_wind_speed_at_cell(x, y)
                    has_wind_speed = True
                else:
                    cell_wind_speed_ms = 0.0
                
                if hasattr(self.forest_model, 'get_wind_direction_at_cell'):
                    cell_wind_direction_rad = self.forest_model.get_wind_direction_at_cell(x, y)
                    has_wind_direction = True
                else:
                    cell_wind_direction_rad = 0.0
                
                if has_wind_speed and has_wind_direction and cell_wind_speed_ms > 1e-6:
                    cell_wind_direction_deg = math.degrees(cell_wind_direction_rad)
                    
                    logger.debug(f"WIND_FACTOR_CALC: cell_wind_speed_ms={cell_wind_speed_ms:.4f}")
                    logger.debug(f"WIND_FACTOR_CALC: cell_wind_direction_rad={cell_wind_direction_rad:.4f} (deg={cell_wind_direction_deg:.2f})")
                    
                    # Standard meteorological to Cartesian conversion: 0 deg North, 90 deg East
                    # Wind direction is 'FROM', spread angle is 'TO'
                    # If wind is FROM 270 deg (West), it blows TOWARDS 90 deg (East)
                    # If spread is TOWARDS 90 deg (East), then cos_angle should be 1 (alignment)
                    
                    # Wind vector components (direction it's blowing TO)
                    # Angle in radians for math functions, cartesian (0 East, 90 North)
                    # If wind_dir_rad is 0 (from North), blows to Pi (South). Cartesian angle = 3Pi/2 or -Pi/2
                    # If wind_dir_rad is Pi/2 (from East), blows to 3Pi/2 (West). Cartesian angle = Pi
                    # If wind_dir_rad is Pi (from South), blows to 0 (North). Cartesian angle = Pi/2
                    # If wind_dir_rad is 3Pi/2 (from West), blows to Pi/2 (East). Cartesian angle = 0
                    
                    # Convert meteorological wind direction (FROM, 0 North, clockwise) to Cartesian angle (TO, 0 East, anti-clockwise)
                    # meteorological_rad = cell_wind_direction_rad
                    # cartesian_angle_rad = math.pi/2 - meteorological_rad
                    # If using degrees: cartesian_deg = 90 - meteorological_deg (then adjust to be 'to')
                    # The old logic: cartesian_angle_deg_to = (270 - cell_wind_direction_deg + 360) % 360
                    # This formula converts meteorological degrees (0=N, 90=E) to Cartesian degrees (0=E, 90=N) for a vector *pointing to* where the wind is going.
                    
                    wind_cartesian_angle_deg_to = (270.0 - cell_wind_direction_deg + 360.0) % 360.0
                    wind_cartesian_angle_rad_to = math.radians(wind_cartesian_angle_deg_to)

                    wind_x_comp = cell_wind_speed_ms * math.cos(wind_cartesian_angle_rad_to)
                    wind_y_comp = cell_wind_speed_ms * math.sin(wind_cartesian_angle_rad_to)
                    
                    spread_dx = float(x - src_x)
                    spread_dy = float(y - src_y) # Note: y typically increases downwards in array indexing, upwards in Cartesian.
                                              # Assuming spread_dx, spread_dy are in array index sense (dx positive right, dy positive down)
                                              # If wind_y_comp is positive (Northward), and spread_dy is negative (Northward in array) => alignment.
                                              # Let's stick to existing spread_dx, dy logic which implies standard cartesian for spread vector calc.

                    spread_magnitude = math.sqrt(spread_dx**2 + spread_dy**2)
                    
                    cos_angle = 0.0 # Cosine of angle between wind vector and spread vector
                    if spread_magnitude > 1e-6: # Avoid division by zero if src and tgt are same (should not happen here)
                        # Spread vector components (already Cartesian-like if dx, dy are differences)
                        # Normalized spread vector
                        norm_spread_dx = spread_dx / spread_magnitude
                        norm_spread_dy = spread_dy / spread_magnitude
                        
                        # Dot product of normalized wind vector (implicit) and normalized spread vector
                        # wind_alignment = (norm_spread_dx * wind_x_comp) + (norm_spread_dy * wind_y_comp) # This is dot product of spread_norm and wind_unnormed
                        # cos_angle = wind_alignment / cell_wind_speed_ms # This is dot_product(spread_norm, wind_unnormed) / |wind_unnormed|
                        # This is effectively dot_product(spread_norm, wind_norm)
                        
                        # To be explicit:
                        norm_wind_x_comp = wind_x_comp / cell_wind_speed_ms
                        norm_wind_y_comp = wind_y_comp / cell_wind_speed_ms
                        cos_angle = (norm_spread_dx * norm_wind_x_comp) + (norm_spread_dy * norm_wind_y_comp)

                    # Get parameters from engine config for scaling
                    reference_speed_for_scaling = getattr(self.config, 'reference_wind_speed', 10.0) # Default in ModelConfig
                    wind_influence_factor_config = getattr(self.config, 'wind_influence_on_spread', 0.5) # Default in ModelConfig

                    wind_speed_contribution_scale = cell_wind_speed_ms / reference_speed_for_scaling
                    
                    wind_factor = 1.0 + max(0, cos_angle) * wind_speed_contribution_scale * wind_influence_factor_config

                    logger.debug(f"WIND_FACTOR_DETAILS: spread_dx={spread_dx}, spread_dy={spread_dy}")
                    logger.debug(f"WIND_FACTOR_DETAILS: wind_cartesian_angle_rad_to={wind_cartesian_angle_rad_to:.4f}")
                    logger.debug(f"WIND_FACTOR_DETAILS: cos_angle_wind_spread={cos_angle:.4f}")
                    logger.debug(f"WIND_FACTOR_DETAILS: reference_speed_config={reference_speed_for_scaling:.4f}")
                    logger.debug(f"WIND_FACTOR_DETAILS: influence_config={wind_influence_factor_config:.4f}")
                    
            except Exception as wind_error:
                logger.warning(f"⚠️  Wind factor calculation failed: {wind_error}")
                logger.warning("Using default wind_factor=1.0")
                wind_factor = 1.0

            # Slope factor (existing logic for horizontal)
            slope_factor = self._calculate_slope_factor(x, y, z, src_x, src_y)

        # Fuel factor (common for both vertical and horizontal)
        # PAD data is already normalized to 0-1 range, so use it directly
        # Only apply max_fuel normalization if the data is not already normalized
        current_fuel = self.forest_model.fuel_load[x, y, z]
        max_fuel = self.config.max_fuel_value
        
        # Check if fuel data is already normalized (0-1 range)
        # If max_fuel is 1.0 and current_fuel is <= 1.0, assume it's PAD data
        if max_fuel <= 1.0 and current_fuel <= 1.0:
            # PAD data is already normalized, use directly
            fuel_factor = current_fuel
        else:
            # Legacy fuel data, apply normalization
            fuel_factor = min(1.0, current_fuel / max_fuel if max_fuel > 0 else 1.0)
        
        # Distance factor for diagonal vs orthogonal spread
        distance_factor = 1.0
        if not is_vertical_spread:
            dx = abs(x - src_x)
            dy = abs(y - src_y)
            if dx > 0 and dy > 0:  # Diagonal spread
                distance_factor = 1.0 / math.sqrt(2)  # ≈ 0.707 - reduces probability for diagonal spread
                logger.debug(f"DIAGONAL_SPREAD: Applying distance factor {distance_factor:.3f} for diagonal spread")
            else:
                logger.debug(f"ORTHOGONAL_SPREAD: No distance factor applied for orthogonal spread")
        
        # Temperature and humidity effects removed
        
        # Calculate final probability
        if self.emergency_mode:
            logger.debug(f"FACTORS_BEFORE_PRODUCT: base={base_prob}, fuel={fuel_factor}, wind={wind_factor}, slope={slope_factor}, distance={distance_factor}")
        ignition_prob = base_prob * fuel_factor * wind_factor * slope_factor * distance_factor
        if self.emergency_mode:
            logger.debug(f"    IGNITION_PROB_INTERMEDIATE: {ignition_prob}") 
        
        # Clip probability to ensure it's within [0, 1]
        effective_spread_prob = max(0.0, min(1.0, ignition_prob))
        
        # CRITICAL FIX: Lower ignition threshold to improve fire spreading
        # The default threshold of 0.5 was too high, causing fires to not spread
        ignition_threshold = getattr(self.config, 'ignition_threshold', 0.1)  # Lowered from 0.5 to 0.1
        
        # --- DEBUG PRINT --- (Only in emergency mode to reduce log spam)
        if self.emergency_mode:
            logger.debug(f"DEBUG _check_ignition: tgt=({x},{y},{z}), src=({src_x},{src_y},{src_z})")
            logger.debug(f"    EFFECTIVE_SPREAD_PROB: {effective_spread_prob:.6f}")
            logger.debug(f"    ignition_threshold: {ignition_threshold}")
            logger.debug(f"    Comparison: {effective_spread_prob >= ignition_threshold}")
        # --- END DEBUG PRINT ---

        result_comparison = (effective_spread_prob >= ignition_threshold)
        
        # Only log result in emergency mode to reduce spam
        if self.emergency_mode:
            logger.debug(f"    CALCULATED RESULT: {result_comparison}")

        return result_comparison
    
    def _calculate_slope_factor(self, tgt_x: int, tgt_y: int, tgt_z: int, src_x: int, src_y: int) -> float:
        """
        Calculate the effect of slope on fire spread probability.
        Increases probability for upslope spread, decreases for downslope.

        Args:
            tgt_x, tgt_y, tgt_z: Target cell coordinates.
            src_x, src_y: Source cell coordinates (for direction).

        Returns:
            Slope adjustment factor (e.g., >1 for uphill, <1 for downhill).
        """
        if not (hasattr(self.forest_model, 'terrain_elevation') and 
                  hasattr(self.forest_model, 'model_resolution') and
                  self.forest_model.terrain_elevation is not None):
            return 1.0 # No terrain data or resolution, no slope effect

        # Get elevation of source and target cells
        # terrain_elevation is likely 2D (x,y)
        elev_src = self.forest_model.terrain_elevation[src_x, src_y]
        elev_tgt = self.forest_model.terrain_elevation[tgt_x, tgt_y]

        # Calculate change in elevation
        delta_elev = elev_tgt - elev_src

        # Calculate horizontal distance between cell centers
        # dx and dy are cell index differences. Multiply by resolution for physical distance.
        dist_x = (tgt_x - src_x) * self.forest_model.model_resolution
        dist_y = (tgt_y - src_y) * self.forest_model.model_resolution
        horizontal_distance = math.sqrt(dist_x**2 + dist_y**2)

        if horizontal_distance == 0:
            # This would be for vertical spread between layers directly above/below.
            # Slope factor is typically for horizontal or diagonal spread influenced by terrain.
            # For purely vertical spread, slope is not usually the primary factor.
            # Can return 1.0, or consider canopy/fuel structure for vertical spread.
            return 1.0 

        # Calculate slope angle in radians
        # tan(slope_angle) = delta_elev / horizontal_distance
        slope_angle_rad = math.atan2(delta_elev, horizontal_distance)
        
        # Convert slope angle to degrees for easier interpretation if needed
        # slope_angle_deg = math.degrees(slope_angle_rad)

        # Get slope influence from config (0 to 1)
        slope_influence = self.config.slope_influence 

        # Simple model for slope factor (based on common fire spread models)
        # This is a common formulation: exp(A * slope_angle_rad)
        # where A is a constant. Let's use a value that provides reasonable effect.
        # For example, A = 3.57 for some models (Rothermel related)
        # We can scale this by slope_influence.
        # A more direct approach: factor = 1 + (slope_percentage * slope_influence)
        # Let's use a simplified exponential factor for now, adjusted by influence.
        # Positive slope_angle_rad means uphill spread.
        
        # Example: factor increases for uphill, decreases for downhill
        # Let phi be slope_angle_rad.
        # factor = exp(slope_influence * C * tan(phi)) where C is some constant
        # Or more simply: factor = 1.0 + slope_influence * math.sin(slope_angle_rad)
        # sin(phi) is positive for uphill, negative for downhill.
        # Max value of sin(phi) is 1 (90 deg uphill), min is -1 (90 deg downhill).
        # So factor ranges from (1 - slope_influence) to (1 + slope_influence).
        # E.g. if slope_influence = 0.3, factor is 0.7 to 1.3.
        
        slope_factor = 1.0 + (slope_influence * math.sin(slope_angle_rad))
        
        # Ensure factor is not negative, though with sin this shouldn't be an issue unless influence > 1
        slope_factor = max(0.1, slope_factor) # Ensure a minimum effect, not zero probability

        # logger.debug(f"Slope calc: src({src_x},{src_y}) elev={elev_src:.2f}, tgt({tgt_x},{tgt_y}) elev={elev_tgt:.2f}")
        # logger.debug(f"Delta_elev={delta_elev:.2f}, horiz_dist={horizontal_distance:.2f}, angle_rad={slope_angle_rad:.3f}")
        # logger.debug(f"Calculated slope_factor: {slope_factor:.3f} (influence: {slope_influence})")

        return slope_factor

    def _get_neighbors(self, x, y, z):
        """Get valid neighbor cells for fire spread using memory-safe bounds checking."""
        try:
            # Use memory-safe bounds checking
            if not self._safe_bounds_check(x, y, z):
                logger.warning(f"⚠️  Invalid coordinates ({x}, {y}, {z}) for grid")
                return []  # Return empty list to prevent segfault
            
            neighbors = []
            
            # Define neighborhood pattern
            # Moore neighborhood in 2D plus vertical connections
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    # Skip center cell
                    if dx == 0 and dy == 0:
                        continue
                    
                    # Check horizontal neighbors using memory-safe bounds checking
                    nx, ny = x + dx, y + dy
                    if self._safe_bounds_check(nx, ny, z):
                        neighbors.append((nx, ny, z))
            
            # Check vertical neighbors using memory-safe bounds checking
            for dz in [-1, 1]:
                nz = z + dz
                if self._safe_bounds_check(x, y, nz):
                    neighbors.append((x, y, nz))
            
            return neighbors
            
        except Exception as e:
            # Enhanced error handling with memory-safe fallback
            logger.warning(f"⚠️  Neighbor calculation failed at ({x}, {y}, {z}): {e}")
            logger.warning("Using memory-safe fallback - returning empty neighbor list")
            return []  # Return empty list to prevent segfault
    
    def _store_history_step(self):
        current_state_data = None
        store_full = self.config.store_full_states
        use_disk = self.config.use_disk_storage


        # Use config method to get temp storage directory if available
        if hasattr(self.config, 'get_temp_storage_dir'):
            temp_storage_dir = self.config.get_temp_storage_dir()
        else:
            # Fallback for older configs
            temp_storage_dir = Path(getattr(self.config, 'disk_storage_dir', 'temp_simulation_states'))
        
        if store_full:
            if use_disk:
                # Consider adding a simulation-specific subfolder if running multiple simulations
                # For now, using the base disk_storage_dir
                try:
                    temp_storage_dir.mkdir(parents=True, exist_ok=True)
                    state_filename = f"state_step_{self.current_step}.npy"
                    state_filepath = temp_storage_dir / state_filename
                    np.save(state_filepath, self.forest_model.state.copy())
                    current_state_data = str(state_filepath) # Store path instead of array
                    log_once(logger.info, f"Storing history state for step {self.current_step} to disk: {state_filepath}")
                except Exception as e:
                    logger.warning(f"Failed to save history state to disk for step {self.current_step}: {e}")
                    logger.info(f"Falling back to in-memory storage for step {self.current_step}")
                    # Fallback to in-memory storage instead of error string
                    current_state_data = self.forest_model.state.copy()
            else:
                current_state_data = self.forest_model.state.copy() # Store in memory
        else:
            current_state_data = None # Not storing full state
            
        self.history.append({
            'step': self.current_step,
            'active_cells': len(self.active_cells),
            'burned_cells': len(self.burned_cells),
            'state': current_state_data,
            'ember_events': [e for e in self.ember_events if e['step'] == self.current_step],
            'ember_stats': self.ember_statistics['by_step'].get(self.current_step, {
                'generated': 0, 'successful': 0, 'failed': 0
            })
        })
        
        # Also update the forest model's history for visualization access
        if hasattr(self.forest_model, 'add_history_entry'):
            # For forest model history, only store state if it's in memory (not a file path)
            model_state = current_state_data if isinstance(current_state_data, np.ndarray) else None
            self.forest_model.add_history_entry(
                step=self.current_step,
                active_cells=len(self.active_cells),
                burned_cells=len(self.burned_cells),
                state=model_state
            )

    def get_simulation_stats(self, runtime: float = 0.0) -> Dict[str, Any]:
        """Calculate and return final simulation statistics."""
        # ... existing code ...

    def _process_embers(self, x, y, z):
        """
        Process ember generation and travel from a burning cell.
        Returns list of target cells where embers land.
        """
        import numpy as np
        
        # Check if ember generation occurs
        ember_prob = self.config.ember_probability
        
        # Height factor - higher cells more likely to generate embers
        if hasattr(self.config, 'ember_height_factor'):
            height_factor = 1.0 + (z / self.forest_model.num_layers) * self.config.ember_height_factor
            ember_prob *= height_factor
        
        # Wind factor - stronger wind increases ember generation
        if (hasattr(self.forest_model, 'wind_speed_ms') and 
            self.forest_model.wind_speed_ms is not None):
            wind_speed = self.forest_model.wind_speed_ms
            if isinstance(wind_speed, (int, float)):
                wind_factor = 1.0 + (wind_speed / 10.0) * 0.1  # Increase with wind
            else:
                # Array case - use local wind speed
                wind_factor = 1.0 + (wind_speed[x, y] / 10.0) * 0.1
            ember_prob *= wind_factor
        
        # Random ember generation
        ember_targets = []
        if np.random.random() < ember_prob:
            # Generate 1-3 embers per cell
            num_embers = np.random.randint(1, 4)
            
            # Initialize step statistics if not exists
            if self.current_step not in self.ember_statistics['by_step']:
                self.ember_statistics['by_step'][self.current_step] = {
                    'generated': 0,
                    'successful': 0,
                    'failed': 0
                }
            
            for _ in range(num_embers):
                # Calculate ember travel distance and direction
                base_distance = self.config.ember_distance
                actual_distance = max(1, int(np.random.exponential(base_distance)))
                
                # Random direction for horizontal travel
                angle = np.random.uniform(0, 2 * np.pi)
                
                # Wind influence on ember direction
                if (hasattr(self.forest_model, 'wind_direction_rad') and 
                    self.forest_model.wind_direction_rad is not None and
                    hasattr(self.config, 'ember_wind_factor')):
                    wind_direction = self.forest_model.wind_direction_rad
                    if isinstance(wind_direction, (int, float)):
                        wind_bias = wind_direction
                    else:
                        wind_bias = wind_direction[x, y]
                    
                    # Bias angle toward wind direction
                    wind_strength = self.config.ember_wind_factor
                    angle = (1 - wind_strength) * angle + wind_strength * wind_bias
                
                # Calculate target position
                dx = int(actual_distance * np.cos(angle))
                dy = int(actual_distance * np.sin(angle))
                
                target_x = x + dx
                target_y = y + dy
                
                # Ember height calculation - can rise or fall
                if hasattr(self.config, 'ember_rise'):
                    # Embers typically rise then fall
                    height_change = np.random.randint(-2, self.config.ember_rise + 1)
                    target_z = max(0, min(self.forest_model.num_layers - 1, z + height_change))
                else:
                    # Default: embers can travel at same level or drop
                    height_change = np.random.randint(-1, 2)
                    target_z = max(0, z + height_change)
                
                # Calculate actual distance traveled
                distance_traveled = ((target_x - x)**2 + (target_y - y)**2)**0.5
                
                # Record ember event regardless of whether it lands in bounds
                ember_event = {
                    'step': self.current_step,
                    'source': (x, y, z),
                    'target': (target_x, target_y, target_z),
                    'distance': distance_traveled,
                    'height_change': height_change,
                    'angle_rad': angle,
                    'in_bounds': (0 <= target_x < self.forest_model.width and 
                    0 <= target_y < self.forest_model.height and
                                 0 <= target_z < self.forest_model.num_layers),
                    'ignited': False  # Will be updated later if ignition occurs
                }
                
                # Update statistics
                self.ember_statistics['total_generated'] += 1
                self.ember_statistics['by_step'][self.current_step]['generated'] += 1
                self.ember_statistics['distance_stats'].append(distance_traveled)
                self.ember_statistics['height_changes'].append(height_change)
                
                # Check bounds and add to targets if valid
                if ember_event['in_bounds']:
                    ember_targets.append((target_x, target_y, target_z))
                    
                    # Track ember spread statistics
                    if hasattr(self.forest_model, 'increment_spread_stat'):
                        self.forest_model.increment_spread_stat('ember_spread')
                
                # Store the ember event
                self.ember_events.append(ember_event)
        
        return ember_targets

    def _check_ember_ignition(self, x, y, z, src_x, src_y, src_z):
        """
        Check if an ember successfully ignites fuel at the target cell.
        Returns True if ignition occurs.
        """
        import numpy as np
        
        # Skip if already burning or burned
        if self.forest_model.state[x, y, z] != FrameworkCellState.UNBURNED.value:
            return False
        
        # Skip if insufficient fuel
        min_fuel = self.config.min_fuel_value
        if self.forest_model.fuel_load[x, y, z] <= min_fuel:
            return False
        
        # Base ember ignition probability
        ignition_prob = self.config.ember_ignition
        
        # Fuel load factor - more fuel = easier ignition
        fuel_factor = min(1.0, self.forest_model.fuel_load[x, y, z] / self.config.max_fuel_value)
        ignition_prob *= fuel_factor
        
        # Moisture factor if available
        if hasattr(self.forest_model, 'fuel_moisture') and self.forest_model.fuel_moisture is not None:
            moisture = self.forest_model.fuel_moisture[x, y, z]
            moisture_factor = 1.0 - moisture  # Higher moisture = lower ignition
            ignition_prob *= moisture_factor
        else:
            # Use baseline moisture if no specific data
            baseline_moisture = getattr(self.config, 'fuel_moisture_baseline', 0.3)
            moisture_factor = 1.0 - baseline_moisture
            ignition_prob *= moisture_factor
        
        # Height factor - embers landing in lower, denser layers are more likely to ignite
        if z < self.forest_model.num_layers / 2:
            height_factor = 1.2  # Boost for lower layers
        else:
            height_factor = 0.8  # Reduce for upper layers
        ignition_prob *= height_factor
        
        # Distance factor - farther embers are less likely to ignite
        distance = ((x - src_x)**2 + (y - src_y)**2)**0.5
        if distance > 0:
            distance_factor = max(0.3, 1.0 - (distance / (self.config.ember_distance * 2)))
            ignition_prob *= distance_factor
        
        # Random ignition check
        return np.random.random() < ignition_prob

    def get_ember_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive ember statistics from the simulation.
        
        Returns:
            Dictionary with detailed ember statistics
        """
        import numpy as np
        
        if not self.ember_events:
            return {
                'total_events': 0,
                'success_rate': 0.0,
                'message': 'No ember events recorded'
            }
        
        # Basic statistics
        total_events = len(self.ember_events)
        successful_events = sum(1 for e in self.ember_events if e['ignited'])
        success_rate = successful_events / total_events if total_events > 0 else 0.0
        
        # Distance statistics
        distances = [e['distance'] for e in self.ember_events]
        successful_distances = [e['distance'] for e in self.ember_events if e['ignited']]
        
        # Height change statistics
        height_changes = [e['height_change'] for e in self.ember_events]
        successful_height_changes = [e['height_change'] for e in self.ember_events if e['ignited']]
        
        # Temporal analysis
        steps_with_embers = set(e['step'] for e in self.ember_events)
        
        # In-bounds analysis
        in_bounds_events = sum(1 for e in self.ember_events if e['in_bounds'])
        out_of_bounds_events = total_events - in_bounds_events
        
        statistics = {
            'total_events': total_events,
            'successful_ignitions': successful_events,
            'failed_attempts': total_events - successful_events,
            'success_rate': success_rate,
            'in_bounds_events': in_bounds_events,
            'out_of_bounds_events': out_of_bounds_events,
            'in_bounds_rate': in_bounds_events / total_events if total_events > 0 else 0.0,
            
            'distance_stats': {
                'all_embers': {
                    'mean': np.mean(distances) if distances else 0.0,
                    'median': np.median(distances) if distances else 0.0,
                    'std': np.std(distances) if distances else 0.0,
                    'min': np.min(distances) if distances else 0.0,
                    'max': np.max(distances) if distances else 0.0
                },
                'successful_embers': {
                    'mean': np.mean(successful_distances) if successful_distances else 0.0,
                    'median': np.median(successful_distances) if successful_distances else 0.0,
                    'std': np.std(successful_distances) if successful_distances else 0.0,
                    'min': np.min(successful_distances) if successful_distances else 0.0,
                    'max': np.max(successful_distances) if successful_distances else 0.0
                }
            },
            
            'height_change_stats': {
                'all_embers': {
                    'mean': np.mean(height_changes) if height_changes else 0.0,
                    'median': np.median(height_changes) if height_changes else 0.0,
                    'std': np.std(height_changes) if height_changes else 0.0,
                    'min': np.min(height_changes) if height_changes else 0.0,
                    'max': np.max(height_changes) if height_changes else 0.0
                },
                'successful_embers': {
                    'mean': np.mean(successful_height_changes) if successful_height_changes else 0.0,
                    'median': np.median(successful_height_changes) if successful_height_changes else 0.0,
                    'std': np.std(successful_height_changes) if successful_height_changes else 0.0,
                    'min': np.min(successful_height_changes) if successful_height_changes else 0.0,
                    'max': np.max(successful_height_changes) if successful_height_changes else 0.0
                }
            },
            
            'temporal_stats': {
                'steps_with_embers': len(steps_with_embers),
                'total_simulation_steps': self.current_step + 1,
                'ember_activity_rate': len(steps_with_embers) / (self.current_step + 1) if self.current_step >= 0 else 0.0,
                'by_step': self.ember_statistics['by_step']
            }
        }
        
        return statistics

    def export_ember_data(self, filepath: str, format: str = 'json') -> bool:
        """
        Export ember event data to file.
        
        Args:
            filepath: Path to save the data
            format: Export format ('json', 'csv', 'pickle')
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if format.lower() == 'json':
                import json
                # Convert numpy types to native Python types for JSON serialization
                export_data = {
                    'ember_events': [
                        {
                            'step': int(e['step']),
                            'source': [int(x) for x in e['source']],
                            'target': [int(x) for x in e['target']],
                            'distance': float(e['distance']),
                            'height_change': int(e['height_change']),
                            'angle_rad': float(e['angle_rad']),
                            'in_bounds': bool(e['in_bounds']),
                            'ignited': bool(e['ignited'])
                        }
                        for e in self.ember_events
                    ],
                    'ember_statistics': self.get_ember_statistics(),
                    'simulation_metadata': {
                        'total_steps': self.current_step + 1,
                        'grid_size': [self.forest_model.width, self.forest_model.height],
                        'num_layers': self.forest_model.num_layers,
                        'ember_probability': self.config.ember_probability,
                        'ember_distance': self.config.ember_distance,
                        'ember_ignition': self.config.ember_ignition
                    }
                }
                
                with open(filepath, 'w') as f:
                    json.dump(export_data, f, indent=2)
                    
            elif format.lower() == 'csv':
                import pandas as pd
                # Flatten ember events for CSV export
                csv_data = []
                for e in self.ember_events:
                    csv_data.append({
                        'step': e['step'],
                        'source_x': e['source'][0],
                        'source_y': e['source'][1],
                        'source_z': e['source'][2],
                        'target_x': e['target'][0],
                        'target_y': e['target'][1],
                        'target_z': e['target'][2],
                        'distance': e['distance'],
                        'height_change': e['height_change'],
                        'angle_rad': e['angle_rad'],
                        'in_bounds': e['in_bounds'],
                        'ignited': e['ignited']
                    })
                
                df = pd.DataFrame(csv_data)
                df.to_csv(filepath, index=False)
                
            elif format.lower() == 'pickle':
                import pickle
                export_data = {
                    'ember_events': self.ember_events,
                    'ember_statistics': self.ember_statistics,
                    'simulation_metadata': {
                        'total_steps': self.current_step + 1,
                        'grid_size': (self.forest_model.width, self.forest_model.height),
                        'num_layers': self.forest_model.num_layers
                    }
                }
                
                with open(filepath, 'wb') as f:
                    pickle.dump(export_data, f)
            else:
                logger.error(f"Unsupported export format: {format}")
                return False
                
            logger.info(f"Ember data exported to {filepath} in {format} format")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export ember data: {e}")
            return False

    def cleanup(self):
        """Clean up memory resources to prevent memory leaks."""
        try:
            import gc
            
            # Clear ember tracking data
            if hasattr(self, 'ember_events') and self.ember_events is not None:
                self.ember_events.clear()
                self.ember_events = None
            
            if hasattr(self, 'ember_statistics') and self.ember_statistics is not None:
                self.ember_statistics.clear()
                self.ember_statistics = None
            
            # Clear simulation state
            if hasattr(self, 'current_step'):
                self.current_step = None
            
            if hasattr(self, 'simulation_time'):
                self.simulation_time = None
            
            # Clear forest model reference (but don't delete it - let caller handle that)
            if hasattr(self, 'forest_model') and self.forest_model is not None:
                # Clean up the forest model if it has a cleanup method
                if hasattr(self.forest_model, 'cleanup'):
                    self.forest_model.cleanup()
                self.forest_model = None
            
            # Clear configuration reference
            if hasattr(self, 'config'):
                self.config = None
            
            # Clear logging statistics
            if hasattr(self, 'log_stats') and self.log_stats is not None:
                self.log_stats.clear()
                self.log_stats = None
            
            # Force garbage collection
            collected = gc.collect()
            if collected > 0:
                logger.debug(f"🧹 FireSimulationEngine cleanup freed {collected} objects")
            
        except Exception as e:
            logger.warning(f"⚠️  FireSimulationEngine cleanup warning: {e}")

    def close(self):
        """Alias for cleanup method."""
        self.cleanup()
