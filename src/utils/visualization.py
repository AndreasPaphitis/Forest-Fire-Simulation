#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Visualization module for Forest Fire Simulation.

This module centralizes all visualization functionality, separating visualization concerns
from the core simulation logic. It provides classes and functions for visualizing
different aspects of forest fire simulations.
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any, Callable

import numpy as np

# Setup logger
logger = logging.getLogger(__name__)

# Try importing visualization libraries, with graceful fallback
try:
    import matplotlib
    import matplotlib.pyplot as plt
    import matplotlib.cm as cm
    from matplotlib.colors import LinearSegmentedColormap
    from mpl_toolkits.mplot3d import Axes3D
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    logger.warning("Matplotlib not available. Visualization functionality will be limited.")
    MATPLOTLIB_AVAILABLE = False

try:
    import imageio
    IMAGEIO_AVAILABLE = True
except ImportError:
    logger.warning("Imageio not available. Animation functionality will be limited.")
    IMAGEIO_AVAILABLE = False

# Custom colormaps for fire visualization
FIRE_CMAP = {
    'red': [(0.0, 0.0, 0.0), (0.2, 0.0, 0.0), (0.4, 0.0, 0.0), (0.6, 1.0, 1.0), (0.8, 1.0, 1.0), (1.0, 0.8, 0.8)],
    'green': [(0.0, 0.5, 0.5), (0.2, 0.7, 0.7), (0.4, 0.4, 0.4), (0.6, 0.8, 0.8), (0.8, 0.0, 0.0), (1.0, 0.0, 0.0)],
    'blue': [(0.0, 0.0, 0.0), (0.2, 0.0, 0.0), (0.4, 0.0, 0.0), (0.6, 0.0, 0.0), (0.8, 0.0, 0.0), (1.0, 0.0, 0.0)]
}

# Status codes for fire cells
CELL_UNBURNT = 0
CELL_BURNING = 1 
CELL_BURNT = 2

class ForestFireVisualizer:
    """
    Main class for visualizing forest fire simulations.
    
    This class provides methods for creating various visualizations of forest fire
    simulations, including 2D and 3D views, animations, and statistics plots.
    """
    
    def __init__(self, forest_model=None):
        """
        Initialize the visualizer.
        
        Args:
            forest_model: The forest model to visualize. Can be set later.
        """
        self.forest_model = forest_model
        
        # Create custom colormaps
        if MATPLOTLIB_AVAILABLE:
            self.fire_cmap = LinearSegmentedColormap('fire', FIRE_CMAP)
            try:
                # Try the modern way first (matplotlib >= 3.5)
                matplotlib.colormaps.register(self.fire_cmap, force=True)
            except (AttributeError, TypeError):
                try:
                    # Fallback for older matplotlib versions
                    cm.register_cmap(cmap=self.fire_cmap)
                except AttributeError:
                    # If all else fails, just use the colormap without registering
                    logger.warning("Could not register custom colormap. Using default colormaps.")
            except ValueError as e:
                # Colormap already registered, that's fine
                if "already registered" in str(e):
                    logger.debug("Fire colormap already registered")
                else:
                    logger.warning(f"Could not register colormap: {e}")
        
        # Cache commonly used properties
        self._cache = {}
    
    def set_model(self, forest_model):
        """
        Set the forest model to visualize.
        
        Args:
            forest_model: The forest model to visualize
        """
        self.forest_model = forest_model
        self._cache = {}  # Clear cache when model changes
        
    def _ensure_model(self):
        """Ensure that a forest model is set."""
        if self.forest_model is None:
            raise ValueError("Forest model not set. Call set_model() first.")
        
    def _ensure_matplotlib(self):
        """Ensure that matplotlib is available."""
        if not MATPLOTLIB_AVAILABLE:
            raise ImportError("Matplotlib is required for this visualization.")
    
    def _get_fire_states(self, layer=0):
        """
        Get fire states for a specific layer with comprehensive fallback handling.
        
        Args:
            layer: The layer to visualize (default: 0)
            
        Returns:
            Numpy array representing fire states
        """
        self._ensure_model()
        
        # List of possible attribute names in order of preference
        state_attrs = ['state', 'fire_states', 'fire_grid', 'ignition_grid']
        
        for attr_name in state_attrs:
            if hasattr(self.forest_model, attr_name):
                state_data = getattr(self.forest_model, attr_name)
                if state_data is not None:
                    # Handle 3D arrays (x, y, z)
                    if len(state_data.shape) == 3:
                        if layer < state_data.shape[2]:
                            return state_data[:, :, layer]
                        else:
                            logger.warning(f"Layer {layer} exceeds available layers ({state_data.shape[2]}). Using layer 0.")
                            return state_data[:, :, 0]
                    # Handle 2D arrays (assume single layer)
                    elif len(state_data.shape) == 2:
                        if layer == 0:
                            return state_data
                        else:
                            logger.warning(f"Model only has 2D state data. Requested layer {layer}, returning layer 0.")
                            return state_data
                    else:
                        logger.warning(f"Unexpected state data shape: {state_data.shape}")
                        continue
        
        # Try accessor methods
        accessor_methods = ['get_fire_state', 'get_state', 'get_layer_state']
        for method_name in accessor_methods:
            if hasattr(self.forest_model, method_name):
                try:
                    method = getattr(self.forest_model, method_name)
                    result = method(layer) if method_name == 'get_fire_state' else method()
                    if result is not None:
                        return result
                except Exception as e:
                    logger.debug(f"Error calling {method_name}: {e}")
                    continue
        
        raise AttributeError(
            f"Could not find fire state data in the model. "
            f"The model should have one of {state_attrs} attributes "
            f"or one of {accessor_methods} methods. "
            f"Available attributes: {[attr for attr in dir(self.forest_model) if not attr.startswith('_')]}"
        )
    
    def _get_fire_history(self):
        """
        Get fire history data with fallback handling.
        
        Returns:
            List of history entries or None if not available
        """
        # Check for history in the model itself
        history_attrs = ['fire_history', 'history', 'simulation_history']
        for attr_name in history_attrs:
            if hasattr(self.forest_model, attr_name):
                history_data = getattr(self.forest_model, attr_name)
                if history_data is not None and len(history_data) > 0:
                    return history_data
        
        # Check if the model has a parent simulation engine with history
        if hasattr(self.forest_model, 'simulation_engine'):
            engine = self.forest_model.simulation_engine
            if hasattr(engine, 'history') and engine.history:
                return engine.history
        
        logger.debug("No fire history found in model")
        return None
    
    def _get_spread_stats(self):
        """
        Get spread statistics with fallback handling.
        
        Returns:
            Dictionary of spread statistics or None if not available
        """
        stats_attrs = ['spread_stats', 'stats', 'simulation_stats']
        for attr_name in stats_attrs:
            if hasattr(self.forest_model, attr_name):
                stats_data = getattr(self.forest_model, attr_name)
                if stats_data is not None and len(stats_data) > 0:
                    return stats_data
        
        logger.debug("No spread statistics found in model")
        return None
    
    def _get_wind_data(self):
        """
        Get wind data with fallback handling.
        
        Returns:
            Tuple of (wind_speed, wind_direction) or (None, None) if not available
        """
        # Try different attribute combinations
        wind_speed = None
        wind_direction = None
        
        # Method 1: Direct attributes
        speed_attrs = ['wind_speed', 'wind_speed_ms']
        direction_attrs = ['wind_direction', 'wind_direction_deg', 'wind_direction_rad']
        
        for speed_attr in speed_attrs:
            if hasattr(self.forest_model, speed_attr):
                speed_data = getattr(self.forest_model, speed_attr)
                if speed_data is not None:
                    # Handle both scalar and array wind speeds
                    if isinstance(speed_data, (int, float)):
                        wind_speed = speed_data
                    elif hasattr(speed_data, 'mean'):  # numpy array
                        wind_speed = float(speed_data.mean())
                    break
        
        for dir_attr in direction_attrs:
            if hasattr(self.forest_model, dir_attr):
                dir_data = getattr(self.forest_model, dir_attr)
                if dir_data is not None:
                    # Handle both scalar and array wind directions
                    if isinstance(dir_data, (int, float)):
                        wind_direction = dir_data
                        # Convert radians to degrees if needed
                        if 'rad' in dir_attr and abs(wind_direction) <= 2 * np.pi:
                            wind_direction = np.degrees(wind_direction)
                    elif hasattr(dir_data, 'mean'):  # numpy array
                        wind_direction = float(dir_data.mean())
                        # Convert radians to degrees if needed
                        if 'rad' in dir_attr and abs(wind_direction) <= 2 * np.pi:
                            wind_direction = np.degrees(wind_direction)
                    break
        
        return wind_speed, wind_direction
    
    def visualize_fire_state(self, layer=0, title=None, figsize=(10, 8), ax=None):
        """
        Visualize the current fire state for a specific layer.
        
        Args:
            layer: Layer to visualize (default: 0)
            title: Title for the plot (default: None)
            figsize: Figure size as (width, height) in inches (default: (10, 8))
            ax: Matplotlib axis to plot on (creates new figure if None)
            
        Returns:
            Matplotlib figure and axis
        """
        self._ensure_model()
        self._ensure_matplotlib()
        
        # Get the fire state data
        fire_state = self._get_fire_states(layer)
        
        # Create figure and axis if not provided
        if ax is None:
            fig, ax = plt.subplots(figsize=figsize)
        else:
            fig = ax.figure
        
        # Create the heatmap
        cax = ax.imshow(
            fire_state, 
            cmap=self.fire_cmap, 
            interpolation='nearest',
            vmin=0,
            vmax=2
        )
        
        # Add colorbar
        cbar = plt.colorbar(cax, ax=ax)
        cbar.set_ticks([0.33, 1, 1.67])
        cbar.set_ticklabels(['Unburnt', 'Burning', 'Burnt'])
        
        # Set title
        if title is None:
            title = f"Fire State - Layer {layer}"
        ax.set_title(title)
        
        # Add grid
        ax.grid(False)
        
        return fig, ax

    def visualize_3d_fire(self, title=None, figsize=(12, 10), elev=30, azim=45):
        """
        Create a 3D visualization of the fire across all layers.
        
        Args:
            title: Title for the plot
            figsize: Figure size as (width, height) in inches
            elev: Elevation viewing angle
            azim: Azimuth viewing angle
            
        Returns:
            Matplotlib figure and axis
        """
        self._ensure_model()
        self._ensure_matplotlib()
        
        # Create a new figure with 3D projection
        fig = plt.figure(figsize=figsize)
        ax = fig.add_subplot(111, projection='3d')
        
        # Get model dimensions
        model_width = self.forest_model.width if hasattr(self.forest_model, 'width') else self.forest_model.grid_size_x
        model_height = self.forest_model.height if hasattr(self.forest_model, 'height') else self.forest_model.grid_size_y
        model_layers = self.forest_model.num_layers
        
        # Define coordinates for plotting
        x_size, y_size = model_width, model_height
        x = np.arange(0, x_size, 1)
        y = np.arange(0, y_size, 1)
        X, Y = np.meshgrid(x, y)
        
        # Plot each layer
        for layer in range(model_layers):
            # Get fire state
            fire_state = self._get_fire_states(layer)
            
            # Filter for burning and burnt cells
            burning_mask = (fire_state == CELL_BURNING)
            burnt_mask = (fire_state == CELL_BURNT)
            
            # Convert to sparse points for more efficient plotting
            x_burning, y_burning = np.where(burning_mask)
            x_burnt, y_burnt = np.where(burnt_mask)
            
            # Create consistent z-values for this layer
            z_burning = np.full_like(x_burning, layer)
            z_burnt = np.full_like(x_burnt, layer)
            
            # Plot as scatter points with colors
            if len(x_burning) > 0:
                ax.scatter(
                    x_burning, y_burning, z_burning, 
                    c='red', marker='o', s=20, label='Burning' if layer == 0 else None
                )
            
            if len(x_burnt) > 0:
                ax.scatter(
                    x_burnt, y_burnt, z_burnt, 
                    c='black', marker='o', s=20, alpha=0.5, label='Burnt' if layer == 0 else None
                )
        
        # Set axis labels
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_zlabel('Layer')
        
        # Set viewing angle
        ax.view_init(elev=elev, azim=azim)
        
        # Set title
        if title is None:
            title = "3D Fire State"
        ax.set_title(title)
        
        # Add legend (only once)
        ax.legend()
        
        return fig, ax
    
    def visualize_process_contributions(self, figsize=(8, 8), title="Fire Spread Mechanisms", save_path=None):
        """
        Visualize the contribution of different processes to fire spread.
        
        Args:
            figsize: Figure size as (width, height) in inches
            title: Title for the plot
            save_path: Path to save the figure (if None, figure is not saved)
            
        Returns:
            Matplotlib figure and axis
        """
        self._ensure_model()
        self._ensure_matplotlib()
        
        # Use the new helper function to get spread statistics
        stats = self._get_spread_stats()
        
        if not stats:
            logger.warning("Model does not have spread statistics. Cannot visualize process contributions.")
            return None, None
        
        # Extract process contributions
        processes = []
        counts = []
        
        # Extract data from spread_stats
        for key, value in stats.items():
            if key not in ['total_cells', 'steps'] and isinstance(value, (int, float)) and value > 0:
                processes.append(key.replace('_', ' ').title())
                counts.append(value)
        
        if not processes:
            logger.warning("No valid process data found in spread statistics.")
            return None, None
        
        # Create figure and axis
        fig, ax = plt.subplots(figsize=figsize)
        
        # Create pie chart
        wedges, texts, autotexts = ax.pie(
            counts, 
            labels=processes,
            autopct='%1.1f%%',
            shadow=True,
            startangle=90
        )
        
        # Equal aspect ratio ensures that pie is drawn as a circle
        ax.axis('equal')
        
        # Set title
        ax.set_title(title)
        
        # Save if path provided
        if save_path is not None:
            plt.tight_layout()
            plt.savefig(save_path)
        
        return fig, ax
    
    def visualize_fire_spread_stats(self, figsize=(10, 12), save_path=None):
        """
        Visualize fire spread statistics over time.
        
        Args:
            figsize: Figure size as (width, height) in inches
            save_path: Path to save the figure (if None, figure is not saved)
            
        Returns:
            Matplotlib figure and axis
        """
        self._ensure_model()
        self._ensure_matplotlib()
        
        # Use the new helper function to get fire history
        history = self._get_fire_history()
        
        if not history:
            logger.warning("Model does not have fire history. Cannot visualize fire spread statistics.")
            return None, None
        
        # Extract history data
        steps = []
        active_cells = []
        burnt_cells = []
        
        # Process history data with better error handling
        for entry in history:
            if isinstance(entry, dict):
                steps.append(entry.get('step', len(steps)))
                active_cells.append(entry.get('active_cells', 0))
                burnt_cells.append(entry.get('burned_cells', entry.get('burnt_cells', 0)))
            else:
                logger.warning(f"Unexpected history entry format: {type(entry)}")
                continue
        
        if not steps:
            logger.warning("No valid history data found.")
            return None, None
        
        # Create figure with two subplots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=figsize)
        
        # Plot active cells over time
        ax1.plot(steps, active_cells, 'r-', label='Active Cells', linewidth=2)
        ax1.set_xlabel('Simulation Steps')
        ax1.set_ylabel('Number of Burning Cells')
        ax1.set_title('Active Fire Cells Over Time')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        
        # Plot burnt cells over time (cumulative)
        ax2.plot(steps, burnt_cells, 'k-', label='Burnt Cells', linewidth=2)
        ax2.set_xlabel('Simulation Steps')
        ax2.set_ylabel('Number of Burnt Cells')
        ax2.set_title('Cumulative Burnt Cells')
        ax2.grid(True, alpha=0.3)
        ax2.legend()
        
        plt.tight_layout()
        
        # Save if path provided
        if save_path is not None:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        return fig, (ax1, ax2)
    
    def visualize_wind_influence(self, figsize=(10, 6), save_path=None):
        """
        Visualize wind influence on fire spread.
        
        Args:
            figsize: Figure size as (width, height) in inches
            save_path: Path to save the figure (if None, figure is not saved)
            
        Returns:
            Matplotlib figure and axis
        """
        self._ensure_model()
        self._ensure_matplotlib()
        
        # Use the new helper function to get wind data
        wind_speed, wind_direction = self._get_wind_data()
        
        if wind_speed is None or wind_direction is None:
            logger.warning("Model does not have complete wind data. Cannot visualize wind influence.")
            return None, None
        
        # Create figure
        fig, ax = plt.subplots(figsize=figsize)
        
        # Create wind rose or arrow plot
        # For simplicity, we'll use a single arrow to show direction and speed
        center_x, center_y = 0.5, 0.5
        
        # Convert wind direction to vector components
        # Wind direction is meteorological (degrees from north, clockwise)
        # Convert to mathematical (radians from east, counterclockwise)
        wind_angle_rad = np.radians(90 - wind_direction)
        
        # Scale arrow length based on wind speed (normalize to max length of 0.3)
        max_speed = 20.0  # Assume max wind speed for scaling
        arrow_length = min(0.3, 0.3 * wind_speed / max_speed)
        
        u = arrow_length * np.cos(wind_angle_rad)
        v = arrow_length * np.sin(wind_angle_rad)
        
        # Plot arrow
        ax.quiver(center_x, center_y, u, v, angles='xy', scale_units='xy', scale=1, 
                  color='b', width=0.015, headwidth=6, headlength=8, alpha=0.8)
        
        # Set axis properties
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_aspect('equal')
        
        # Add cardinal directions
        ax.text(0.5, 0.05, 'S', ha='center', va='center', fontsize=14, weight='bold')
        ax.text(0.5, 0.95, 'N', ha='center', va='center', fontsize=14, weight='bold')
        ax.text(0.05, 0.5, 'W', ha='center', va='center', fontsize=14, weight='bold')
        ax.text(0.95, 0.5, 'E', ha='center', va='center', fontsize=14, weight='bold')
        
        # Add circle
        circle = plt.Circle((center_x, center_y), 0.4, fill=False, color='gray', 
                           linestyle='--', alpha=0.5)
        ax.add_patch(circle)
        
        # Remove ticks
        ax.set_xticks([])
        ax.set_yticks([])
        
        # Add title and info
        ax.set_title('Wind Influence on Fire Spread', fontsize=16, weight='bold')
        
        # Add wind info box
        info_text = f"Wind Speed: {wind_speed:.1f} m/s\nDirection: {wind_direction:.0f}°"
        ax.text(0.05, 0.05, info_text, ha='left', va='bottom', fontsize=12,
                bbox=dict(boxstyle="round,pad=0.5", fc="white", ec="gray", alpha=0.9))
        
        # Save if path provided
        if save_path is not None:
            plt.tight_layout()
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        return fig, ax
    
    def visualize_fire_spread_animation(self, frame_interval_ms=200, show_stats=True, output_file=None):
        """
        Create an animation of the fire spread over time.
        
        Args:
            frame_interval_ms: Time between frames in milliseconds
            show_stats: Whether to show statistics on the animation
            output_file: Path to save the animation (if None, animation is not saved)
            
        Returns:
            Animation object
        """
        self._ensure_model()
        self._ensure_matplotlib()
        
        # Check if imageio is available for saving animations
        if output_file is not None and not IMAGEIO_AVAILABLE:
            logger.warning("Imageio not available. Cannot save animation.")
            output_file = None
        
        # Use the new helper function to get fire history
        history = self._get_fire_history()
        
        if not history:
            logger.warning("Model does not have fire history. Cannot create animation.")
            return None
        
        # Validate history data
        valid_entries = []
        for entry in history:
            if isinstance(entry, dict) and 'step' in entry:
                valid_entries.append(entry)
        
        if not valid_entries:
            logger.warning("No valid history entries found for animation.")
            return None
        
        history = valid_entries
        logger.info(f"Creating animation with {len(history)} frames")
        
        # Create a figure for the animation
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Function to update the frame
        def update_frame(frame_idx):
            ax.clear()
            
            # Get data for this step
            entry = history[frame_idx]
            step = entry.get('step', frame_idx)
            state = entry.get('state', None)
            
            # If state is not directly in history, try to reconstruct it
            if state is None:
                # Try different methods to get historical state
                if hasattr(self.forest_model, 'get_history_state'):
                    try:
                        state = self.forest_model.get_history_state(step)
                    except Exception as e:
                        logger.debug(f"Error getting history state for step {step}: {e}")
                
                # If still no state, try to load from disk if it's a file path
                if state is None and isinstance(entry.get('state'), str):
                    state_path = entry.get('state')
                    if os.path.exists(state_path):
                        try:
                            state = np.load(state_path)
                        except Exception as e:
                            logger.debug(f"Error loading state from {state_path}: {e}")
                
                # If still no state, use current state as fallback (not ideal for animation)
            if state is None:
                    logger.warning(f"No state data available for step {step}, using current state")
                    try:
                        state = self._get_fire_states(0)
                        # Make it 3D if needed
                        if len(state.shape) == 2:
                            state = state[:, :, np.newaxis]
                    except:
                        logger.error(f"Cannot get any state data for frame {frame_idx}")
                        return
            
            # Handle different state formats
            if isinstance(state, str):
                logger.warning(f"State is a string (likely error message): {state}")
                return
            
            # Ensure state is numpy array
            if not isinstance(state, np.ndarray):
                logger.warning(f"Unexpected state type: {type(state)}")
                return
            
            # Get the appropriate layer to display
            if len(state.shape) == 3:
                display_state = state[:, :, 0]  # Show ground layer
            elif len(state.shape) == 2:
                display_state = state
            else:
                logger.warning(f"Unexpected state shape: {state.shape}")
                return
            
            # Plot the current state
            im = ax.imshow(display_state, cmap=self.fire_cmap, interpolation='nearest', 
                          vmin=0, vmax=2, origin='lower')
            
            # Add title with step information
            ax.set_title(f"Fire Spread Animation - Step {step}", fontsize=14, weight='bold')
            
            # Add statistics if requested
            if show_stats:
                active = entry.get('active_cells', 0)
                burnt = entry.get('burned_cells', entry.get('burnt_cells', 0))
                ax.text(
                    0.02, 0.98, 
                    f"Step: {step}\nActive cells: {active}\nBurnt cells: {burnt}", 
                    transform=ax.transAxes,
                    verticalalignment='top',
                    bbox=dict(boxstyle="round,pad=0.5", fc="white", ec="gray", alpha=0.9),
                    fontsize=10
                )
            
            # Add colorbar legend (only on first frame)
            if frame_idx == 0:
                cbar = plt.colorbar(im, ax=ax, shrink=0.8)
                cbar.set_ticks([0.33, 1, 1.67])
                cbar.set_ticklabels(['Unburnt', 'Burning', 'Burnt'])
            
            return im,
        
        # Create animation
        try:
            from matplotlib.animation import FuncAnimation
            animation = FuncAnimation(
                fig, update_frame, frames=len(history), 
                interval=frame_interval_ms, blit=False, repeat=True
            )
            
            # Save animation if requested
            if output_file is not None:
                try:
                    self._save_animation(animation, output_file, frame_interval_ms)
                    logger.info(f"Animation saved to {output_file}")
                except Exception as e:
                    logger.error(f"Error saving animation: {e}")
            
            return animation
            
        except Exception as e:
            logger.error(f"Error creating animation: {e}")
            return None
    
    def _save_animation(self, animation, output_file, frame_interval_ms):
        """
        Save animation to file with proper format detection and error handling.
        
        Args:
            animation: Matplotlib animation object
            output_file: Output file path
            frame_interval_ms: Frame interval in milliseconds
        """
        # Determine the format from the file extension
        file_ext = os.path.splitext(output_file)[1].lower()
        fps = 1000 / frame_interval_ms
        
        if file_ext == '.gif':
            # Save as GIF using pillow
            try:
                animation.save(output_file, writer='pillow', fps=fps)
            except Exception as e:
                logger.error(f"Error saving GIF with pillow: {e}")
                # Try with imageio if available
                if IMAGEIO_AVAILABLE:
                    self._save_animation_imageio(animation, output_file, fps)
                else:
                    raise
                    
        elif file_ext in ['.mp4', '.avi', '.mov']:
            # Save as video
            try:
                # Try to use ffmpeg writer first
                animation.save(output_file, writer='ffmpeg', fps=fps, bitrate=1800)
            except Exception as e:
                logger.warning(f"FFmpeg writer failed: {e}")
                # Fallback to imageio
                if IMAGEIO_AVAILABLE:
                    self._save_animation_imageio(animation, output_file, fps)
                else:
                    raise Exception("Neither ffmpeg nor imageio available for video output")
        else:
            raise ValueError(f"Unsupported file format for animation: {file_ext}")
    
    def _save_animation_imageio(self, animation, output_file, fps):
        """
        Save animation using imageio as fallback.
        
        Args:
            animation: Matplotlib animation object
            output_file: Output file path
            fps: Frames per second
        """
        if not IMAGEIO_AVAILABLE:
            raise ImportError("Imageio not available for animation saving")
        
        import imageio
        
        # Extract frames from animation
        frames = []
        fig = animation._fig
        
        for i in range(animation.save_count if hasattr(animation, 'save_count') else len(animation._func)):
            # Update the animation to the current frame
            try:
                animation._func(i)
                fig.canvas.draw()
                
                # Convert figure to image array
                buf = fig.canvas.buffer_rgba()
                image = np.asarray(buf)
                frames.append(image)
                
            except Exception as e:
                logger.warning(f"Error extracting frame {i}: {e}")
                continue
        
        if not frames:
            raise Exception("No frames could be extracted from animation")
        
        # Save frames as video/gif
        imageio.mimsave(output_file, frames, fps=fps)

def generate_standard_visualizations(forest_model, output_dir, include_animation=True):
    """
    Generate standard visualizations for a forest fire simulation.
    
    Args:
        forest_model: The forest model to visualize
        output_dir: Directory to save visualizations
        include_animation: Whether to generate animation (can be slow)
        
    Returns:
        Dictionary of saved visualization paths
    """
    # Create output directory
    from pathlib import Path
    output_dir = Path(output_dir) / "visualizations"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create visualizer
    visualizer = ForestFireVisualizer(forest_model)
    
    # Dictionary to track saved files
    saved_files = {}
    
    try:
        # 2D visualization of final state
        fig, ax = visualizer.visualize_fire_state(title="Final Fire State")
        file_path = output_dir / "final_state_2d.png"
        plt.savefig(file_path)
        plt.close(fig)
        saved_files['2d_final_state'] = file_path
        
        # 3D visualization if forest has multiple layers
        if forest_model.num_layers > 1:
            fig, ax = visualizer.visualize_3d_fire(title="3D Fire State")
            file_path = output_dir / "final_state_3d.png"
            plt.savefig(file_path)
            plt.close(fig)
            saved_files['3d_final_state'] = file_path
        
        # Process contributions
        if hasattr(forest_model, 'spread_stats') and forest_model.spread_stats:
            file_path = output_dir / "process_contributions.png"
            fig, ax = visualizer.visualize_process_contributions(save_path=file_path)
            if fig is not None:
                plt.close(fig)
                saved_files['process_contributions'] = file_path
        
        # Fire spread statistics
        if hasattr(forest_model, 'fire_history') and forest_model.fire_history:
            file_path = output_dir / "fire_spread_stats.png"
            fig, ax1, ax2 = visualizer.visualize_fire_spread_stats(save_path=file_path)
            if fig is not None:
                plt.close(fig)
                saved_files['fire_spread_stats'] = file_path
        
        # Wind influence
        if hasattr(forest_model, 'wind_direction') and hasattr(forest_model, 'wind_speed'):
            file_path = output_dir / "wind_influence.png"
            fig, ax = visualizer.visualize_wind_influence(save_path=file_path)
            if fig is not None:
                plt.close(fig)
                saved_files['wind_influence'] = file_path
        
        # Animation if requested
        if include_animation and hasattr(forest_model, 'fire_history') and forest_model.fire_history:
            file_path = output_dir / "fire_spread_animation.mp4"
            animation = visualizer.visualize_fire_spread_animation(output_file=file_path)
            if animation is not None:
                saved_files['animation'] = file_path
    
    except Exception as e:
        logger.error(f"Error generating standard visualizations: {e}")
    
    return saved_files 