#!/usr/bin/env python3
"""
Terrain Data Visualization Script
================================

This script creates high-quality visualizations of preprocessed terrain data
for academic reporting and presentations.

Author: Forest Fire Simulation Project
Date: 2024
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import Rectangle
import os
import json
from pathlib import Path
import argparse
from typing import Optional, Tuple, Dict, Any
from matplotlib_scalebar.scalebar import ScaleBar
from matplotlib.patches import FancyArrow
import gc

# Set matplotlib style for academic publications (optimized for memory)
plt.style.use('default')
plt.rcParams.update({
    'font.size': 11,
    'font.family': 'serif',
    'figure.dpi': 150,  # Reduced from 300
    'savefig.dpi': 150,  # Reduced from 300
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.1,
    'axes.linewidth': 1.5,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'xtick.major.width': 1.5,
    'ytick.major.width': 1.5,
    'xtick.major.size': 5,
    'ytick.major.size': 5,
    'xtick.minor.size': 3,
    'ytick.minor.size': 3,
    'lines.linewidth': 1.5,
    'patch.linewidth': 1.5,
    'figure.facecolor': 'white',
    'axes.facecolor': 'white',
    'axes.edgecolor': 'black',
    'axes.labelcolor': 'black',
    'xtick.color': 'black',
    'ytick.color': 'black',
    'text.color': 'black',
    'legend.frameon': True,
    'legend.fancybox': True,
    'legend.shadow': False,
    'legend.fontsize': 10,
})


class TerrainVisualizer:
    """Class for creating terrain data visualizations."""
    
    def __init__(self, data_dir: str = "preprocessed_terrain", output_dir: str = "visualizations"):
        """
        Initialize the visualizer.
        
        Args:
            data_dir: Directory containing preprocessed terrain data
            output_dir: Directory to save visualization outputs
        """
        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Load metadata if available
        self.metadata = self._load_metadata()
        
        # Define colormaps for different data types
        self.colormaps = {
            'elevation': 'terrain',
            'slope': 'viridis',
            'aspect': 'hsv',
            'barranco': 'Reds',
            'depression': 'Blues',
            'wind_channeling': 'Oranges',
            'wind_amplification': 'Purples',
            'wind_direction': 'twilight'
        }
        
        # Define titles for different data types
        self.titles = {
            'elevation': 'Elevation (m)',
            'slope': 'Slope (degrees)',
            'aspect': 'Aspect (degrees)',
            'barranco_mask': 'Barranco Detection',
            'depression_mask': 'Depression Detection',
            'wind_channeling_mask': 'Wind Channeling',
            'wind_amplification': 'Wind Amplification Factor',
            'wind_direction_modification': 'Wind Direction Modification'
        }
        
    def _load_metadata(self) -> Dict[str, Any]:
        """Load metadata from JSON file if available."""
        metadata_file = self.data_dir / "terrain_metadata.json"
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                return json.load(f)
        return {}
    
    def load_data(self, filename: str) -> Optional[np.ndarray]:
        """
        Load data from .npy file.
        
        Args:
            filename: Name of the .npy file
            
        Returns:
            Loaded numpy array or None if file not found
        """
        filepath = self.data_dir / filename
        if filepath.exists():
            print(f"Loading {filename}...")
            return np.load(filepath)
        else:
            print(f"Warning: {filename} not found")
            return None

    def _cleanup_memory(self):
        """Clean up memory after each plot."""
        plt.close('all')
        gc.collect()
    
    def _save_plot_optimized(self, save_path, title=""):
        """
        Save plot with optimized settings to prevent rendering bottlenecks.
        """
        print(f"   💾 Saving {title}..." if title else "   💾 Saving plot...")
        plt.savefig(save_path, dpi=100, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        plt.close()
        print(f"   ✅ Saved {title}" if title else "   ✅ Saved plot")
        self._cleanup_memory()

    def _get_extent(self) -> list:
        """Get extent from config or use default."""
        extent = None
        config_path = os.path.join(self.data_dir, 'preprocessing_config.json')
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
            if 'extent' in config:
                extent = config['extent']
        if extent is None:
            # Load just elevation to get shape, then unload
            elevation = self.load_data('elevation.npy')
            if elevation is not None:
                shape = elevation.shape
                extent = [0, shape[1], shape[0], 0]
                del elevation
            else:
                extent = [0, 1000, 1000, 0]  # fallback
        return extent

    def _add_academic_map_features(self, ax, extent, title, scalebar_length_m=500, show_north=True, dx=1):
        """Add professional map features with improved formatting."""
        # Add scale bar in center-bottom
        scalebar = ScaleBar(
            dx=dx, 
            units="m", 
            length_fraction=0.2, 
            location='lower center', 
            box_alpha=0.8, 
            color='black', 
            scale_loc='bottom',
            font_properties={'size': 10, 'weight': 'bold'}
        )
        ax.add_artist(scalebar)
        
        # Add north arrow pointing UP (correct direction)
        if show_north:
            # North arrow pointing upward (0 degrees = North)
            arrow_x, arrow_y = 0.92, 0.85  # Position in upper right
            arrow_length = 0.08
            
            # Draw arrow shaft
            ax.annotate('', 
                       xy=(arrow_x, arrow_y + arrow_length), 
                       xytext=(arrow_x, arrow_y),
                       arrowprops=dict(
                           arrowstyle='->', 
                           color='black', 
                           lw=2, 
                           mutation_scale=20
                       ),
                       xycoords='axes fraction')
            
            # Add 'N' label above arrow
            ax.text(arrow_x, arrow_y + arrow_length + 0.02, 'N', 
                   ha='center', va='bottom', fontsize=12, fontweight='bold',
                   transform=ax.transAxes)
        
        # Set axis labels with better formatting
        ax.set_xlabel('Longitude', fontsize=12, fontweight='bold', labelpad=10)
        ax.set_ylabel('Latitude', fontsize=12, fontweight='bold', labelpad=10)
        
        # Format tick labels
        ax.tick_params(axis='both', which='major', labelsize=10)
        
        # Set title with better formatting
        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
        
        # Set extent if provided
        if extent is not None:
            ax.set_xlim(extent[0], extent[1])
            ax.set_ylim(extent[2], extent[3])

    def _plot_barranco_mask(self, mask, extent, save_path):
        """
        Create improved barranco visualization following GIS best practices.
        Shows barranco characteristics with proper classification and legend.
        """
        # Downsample if necessary for visualization
        mask, factor = self._downsample_for_visualization(mask, max_size=3000, is_mask=True)
        
        fig, ax = plt.subplots(figsize=(14, 12))
        
        # Load elevation for context (also downsample if needed)
        elevation = self.load_data('elevation.npy')
        if elevation is not None and elevation.shape != mask.shape:
            # Downsample elevation to match mask
            factor = max(elevation.shape[0] // mask.shape[0], elevation.shape[1] // mask.shape[1])
            if factor > 1:
                from scipy import ndimage
                elevation = ndimage.zoom(elevation, 1/factor, order=1)
        
        if np.sum(mask) == 0:
            # No barrancos detected
            ax.text(0.5, 0.5, 'No barrancos detected in this area', 
                   ha='center', va='center', fontsize=16, color='gray',
                   transform=ax.transAxes)
            ax.set_axis_off()
        else:
            # Count detected barrancos
            num_barrancos = np.sum(mask)
            total_cells = mask.size
            barranco_density = num_barrancos / total_cells * 100
            
            if elevation is not None:
                # Create hillshade effect for better terrain visualization
                from matplotlib.colors import LinearSegmentedColormap
                
                # Show elevation as hillshade background
                elev_normalized = (elevation - np.nanmin(elevation)) / (np.nanmax(elevation) - np.nanmin(elevation))
                hillshade = self._create_hillshade(elevation)
                
                # Display hillshade as background
                ax.imshow(hillshade, cmap='gray', extent=extent, origin='upper', alpha=0.6)
                
                # Overlay elevation with terrain colormap
                elev_img = ax.imshow(elevation, cmap='terrain', extent=extent, origin='upper', alpha=0.4)
                
                # Create barranco visualization with proper classification
                # Use red color scheme for hazards/features (GIS standard)
                barranco_colors = ['#ffffff', '#ffcccc', '#ff9999', '#ff6666', '#ff3333', '#ff0000', '#cc0000']
                barranco_cmap = LinearSegmentedColormap.from_list('barranco', barranco_colors, N=256)
                
                # Apply morphological operations to create better barranco visualization
                from scipy import ndimage
                
                # Dilate barrancos slightly for better visibility
                barranco_dilated = ndimage.binary_dilation(mask, iterations=1)
                
                # Create distance transform for intensity
                distance_transform = ndimage.distance_transform_edt(mask)
                distance_transform = np.clip(distance_transform, 0, 5)  # Limit to 5 cells
                
                # Normalize distance transform
                if np.max(distance_transform) > 0:
                    distance_normalized = distance_transform / np.max(distance_transform)
                else:
                    distance_normalized = distance_transform
                
                # Create barranco overlay with intensity based on distance from center
                barranco_overlay = np.ma.masked_where(~barranco_dilated, distance_normalized)
                barranco_img = ax.imshow(barranco_overlay, cmap=barranco_cmap, extent=extent, 
                                       origin='upper', alpha=0.8, vmin=0, vmax=1)
                
                # Add colorbar with proper labeling
                cbar = plt.colorbar(barranco_img, ax=ax, fraction=0.04, pad=0.02, shrink=0.8)
                cbar.set_label('Barranco Intensity\n(Distance from center)', fontsize=12, fontweight='bold')
                cbar.ax.tick_params(labelsize=10)
                
                # Add elevation colorbar
                cbar2 = plt.colorbar(elev_img, ax=ax, fraction=0.04, pad=0.02, shrink=0.8, location='left')
                cbar2.set_label('Elevation (m)', fontsize=12, fontweight='bold')
                cbar2.ax.tick_params(labelsize=10)
                
                del elevation
            else:
                # Fallback to simple visualization if elevation not available
                # Create classified barranco visualization
                barranco_classified = self._classify_barrancos(mask)
                
                # Use GIS-standard red color scheme for hazards
                colors = ['#ffffff', '#ffcccc', '#ff9999', '#ff6666', '#ff3333', '#ff0000']
                cmap = LinearSegmentedColormap.from_list('barranco_classified', colors, N=6)
                
                im = ax.imshow(barranco_classified, cmap=cmap, extent=extent, origin='upper', alpha=0.8)
                
                # Add colorbar with classification labels
                cbar = plt.colorbar(im, ax=ax, fraction=0.04, pad=0.02, shrink=0.8)
                cbar.set_label('Barranco Classification', fontsize=12, fontweight='bold')
                cbar.ax.tick_params(labelsize=10)
                
                # Set custom tick labels for classification
                cbar.set_ticks([0.5, 1.5, 2.5, 3.5, 4.5, 5.5])
                cbar.set_ticklabels(['None', 'Isolated', 'Small', 'Medium', 'Large', 'Extensive'])
            
            # Add comprehensive statistics box
            stats_text = f"""Barranco Statistics:
• Total Barrancos: {num_barrancos:,} cells
• Area Coverage: {barranco_density:.2f}%
• Density: {num_barrancos/total_cells*10000:.1f} per 10k cells
• Spatial Distribution: {'Clustered' if self._is_clustered(mask) else 'Random'}"""
            
            ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
                       fontsize=11, verticalalignment='top', 
                   bbox=dict(boxstyle='round,pad=0.5', facecolor='white', 
                           alpha=0.95, edgecolor='black', linewidth=1))
        
        # Add map features
        self._add_academic_map_features(ax, extent, 'Barranco (Gully) Distribution Map', dx=5)
        
        plt.tight_layout()
        self._save_plot_optimized(save_path, "Barranco Distribution Map")

    def _plot_wind_channeling(self, mask, elevation, extent, save_path):
        """
        Create improved wind channeling visualization showing actual amplification values.
        Uses GIS best practices with proper classification and legend.
        """
        fig, ax = plt.subplots(figsize=(14, 12))
        
        # Load wind amplification data if available
        wind_amplification = self.load_data('wind_amplification.npy')
        
        if np.sum(mask) == 0:
            # No wind channeling detected
            ax.text(0.5, 0.5, 'No wind channeling effects detected', 
                   ha='center', va='center', fontsize=16, color='gray',
                   transform=ax.transAxes)
            ax.set_axis_off()
        else:
        # Show elevation as background
            if elevation is not None:
                # Create hillshade for better terrain context
                hillshade = self._create_hillshade(elevation)
                ax.imshow(hillshade, cmap='gray', extent=extent, origin='upper', alpha=0.5)
                
                # Overlay elevation
                elev_img = ax.imshow(elevation, cmap='terrain', extent=extent, origin='upper', alpha=0.4)
                
                # Add elevation colorbar
                cbar_elev = plt.colorbar(elev_img, ax=ax, fraction=0.04, pad=0.02, shrink=0.8, location='left')
                cbar_elev.set_label('Elevation (m)', fontsize=12, fontweight='bold')
                cbar_elev.ax.tick_params(labelsize=10)
            
                    # Create wind channeling visualization
        if wind_amplification is not None:
            # Use actual wind amplification values
            wind_data = wind_amplification.copy()
            wind_data[~mask] = np.nan  # Mask non-channeling areas
            
            # Create classification for wind amplification
            wind_classified = self._classify_wind_amplification(wind_data)
            
            # Use GIS-standard blue color scheme for wind/air features
            from matplotlib.colors import LinearSegmentedColormap
            colors = ['#ffffff', '#e6f3ff', '#b3d9ff', '#80bfff', '#4da6ff', '#1a8cff', '#0066cc']
            cmap = LinearSegmentedColormap.from_list('wind_channeling', colors, N=7)
            
            wind_img = ax.imshow(wind_classified, cmap=cmap, extent=extent, origin='upper', alpha=0.8)
            
            # Add wind channeling colorbar
            cbar = plt.colorbar(wind_img, ax=ax, fraction=0.04, pad=0.02, shrink=0.8)
            cbar.set_label('Wind Amplification Factor', fontsize=12, fontweight='bold')
            cbar.ax.tick_params(labelsize=10)
            
            # Set custom tick labels for classification
            cbar.set_ticks([0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5])
            cbar.set_ticklabels(['None', '1.0x', '1.5x', '2.0x', '2.5x', '3.0x', '3.5x+'])
            
            # Calculate statistics
            valid_amplification = wind_data[mask]
            avg_amplification = np.nanmean(valid_amplification)
            max_amplification = np.nanmax(valid_amplification)
            min_amplification = np.nanmin(valid_amplification)
            
            del wind_amplification
            else:
                # Fallback to binary mask if amplification data not available
                wind_img = ax.imshow(np.ma.masked_where(~mask, mask), 
                                   cmap='Blues', extent=extent, origin='upper', alpha=0.7)
                
                # Add simple colorbar
                cbar = plt.colorbar(wind_img, ax=ax, fraction=0.04, pad=0.02, shrink=0.8)
                cbar.set_label('Wind Channeling Presence', fontsize=12, fontweight='bold')
                cbar.ax.tick_params(labelsize=10)
                
                # Set binary labels
                cbar.set_ticks([0.25, 0.75])
                cbar.set_ticklabels(['Absent', 'Present'])
                
                avg_amplification = 1.0  # Default for binary mask
                max_amplification = 1.0
                min_amplification = 1.0
            
            # Add comprehensive statistics
            num_channeling = np.sum(mask)
            total_cells = mask.size
            channeling_density = num_channeling / total_cells * 100
            
            stats_text = f"""Wind Channeling Statistics:
• Affected Cells: {num_channeling:,} cells
• Area Coverage: {channeling_density:.2f}%
• Avg Amplification: {avg_amplification:.2f}x
• Range: {min_amplification:.2f}x - {max_amplification:.2f}x
• Primary Cause: {'Barrancos' if self._is_barranco_driven(mask) else 'Terrain'}"""
            
            ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
                   fontsize=11, verticalalignment='top', 
                   bbox=dict(boxstyle='round,pad=0.5', facecolor='white', 
                           alpha=0.95, edgecolor='black', linewidth=1))
        
        # Add map features
        self._add_academic_map_features(ax, extent, 'Wind Channeling Effects Map', dx=5)
        
        plt.tight_layout()
        self._save_plot_optimized(save_path, "Wind Channeling Effects Map")

    def _plot_standard(self, data, extent, save_path, title, cmap, cbar_label):
        """
        Create standard plot with rendering optimizations for large datasets.
        """
        # Calculate optimal rendering size to prevent bottlenecks
        max_render_size = 2000  # Maximum size for matplotlib rendering
        original_shape = data.shape
        
        if data.shape[0] > max_render_size or data.shape[1] > max_render_size:
            print(f"⚠️  Large dataset detected ({data.shape[0]}×{data.shape[1]}), optimizing for rendering...")
            
            # Calculate downsampling factor for rendering
            factor = max(data.shape[0] // max_render_size, data.shape[1] // max_render_size)
            
            # Downsample data for rendering
            from scipy import ndimage
            data_render = ndimage.zoom(data, 1/factor, order=1)
            
            print(f"   Rendering at {data_render.shape[0]}×{data_render.shape[1]} (factor: 1/{factor})")
        else:
            data_render = data
            factor = 1
        
        # Create figure with optimized settings
        fig, ax = plt.subplots(figsize=(12, 10), dpi=100)  # Lower DPI for faster rendering
        
        # Optimize colormap for large datasets
        if cmap == 'hsv' and data_render.size > 1000000:
            # Use a simpler colormap for very large aspect datasets
            print("   ⚡ Using optimized colormap for large aspect dataset")
            cmap = 'twilight'  # Faster alternative to hsv
        
        # Render the image
        im = ax.imshow(data_render, cmap=cmap, extent=extent, origin='upper', interpolation='nearest')
        
        # Add colorbar with optimized settings
        cbar = plt.colorbar(im, ax=ax, fraction=0.025, pad=0.02, shrink=0.6)
        cbar.set_label(cbar_label, fontsize=10, fontweight='bold')
        cbar.ax.tick_params(labelsize=8)
        
        # Add map features
        self._add_academic_map_features(ax, extent, title, dx=5)
        
        # Optimize layout
        plt.tight_layout()
        
        # Save with optimized settings
        print(f"   💾 Saving {title}...")
        plt.savefig(save_path, dpi=100, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        plt.close()
        
        print(f"   ✅ Saved {title}")
        self._cleanup_memory()

    def _plot_depression_mask(self, mask, extent, save_path):
        """
        Create improved depression visualization following GIS best practices.
        Shows depression characteristics with proper classification and legend.
        """
        fig, ax = plt.subplots(figsize=(14, 12))
        
        # Load elevation for context
        elevation = self.load_data('elevation.npy')
        
        if np.sum(mask) == 0:
            # No depressions detected
            ax.text(0.5, 0.5, 'No topographic depressions detected in this area', 
                   ha='center', va='center', fontsize=16, color='gray',
                   transform=ax.transAxes)
            ax.set_axis_off()
        else:
            # Count detected depressions
            num_depressions = np.sum(mask)
            total_cells = mask.size
            depression_density = num_depressions / total_cells * 100
            
            if elevation is not None:
                # Create hillshade effect for better terrain visualization
                from matplotlib.colors import LinearSegmentedColormap
                
                # Show elevation as hillshade background
                hillshade = self._create_hillshade(elevation)
                ax.imshow(hillshade, cmap='gray', extent=extent, origin='upper', alpha=0.6)
                
                # Overlay elevation with terrain colormap
                elev_img = ax.imshow(elevation, cmap='terrain', extent=extent, origin='upper', alpha=0.4)
                
                # Create depression visualization with proper classification
                # Use blue color scheme for water/negative features (GIS standard)
                depression_colors = ['#ffffff', '#e6f3ff', '#b3d9ff', '#80bfff', '#4da6ff', '#1a8cff', '#0066cc', '#004499']
                depression_cmap = LinearSegmentedColormap.from_list('depression', depression_colors, N=256)
                
                # Apply morphological operations to create better depression visualization
                from scipy import ndimage
                
                # Dilate depressions slightly for better visibility
                depression_dilated = ndimage.binary_dilation(mask, iterations=1)
                
                # Create distance transform for intensity
                distance_transform = ndimage.distance_transform_edt(mask)
                distance_transform = np.clip(distance_transform, 0, 5)  # Limit to 5 cells
                
                # Normalize distance transform
                if np.max(distance_transform) > 0:
                    distance_normalized = distance_transform / np.max(distance_transform)
                else:
                    distance_normalized = distance_transform
                
                # Create depression overlay with intensity based on distance from center
                depression_overlay = np.ma.masked_where(~depression_dilated, distance_normalized)
                depression_img = ax.imshow(depression_overlay, cmap=depression_cmap, extent=extent, 
                                         origin='upper', alpha=0.8, vmin=0, vmax=1)
                
                # Add colorbar with proper labeling
                cbar = plt.colorbar(depression_img, ax=ax, fraction=0.04, pad=0.02, shrink=0.8)
                cbar.set_label('Depression Intensity\n(Distance from center)', fontsize=12, fontweight='bold')
                cbar.ax.tick_params(labelsize=10)
                
                # Add elevation colorbar
                cbar2 = plt.colorbar(elev_img, ax=ax, fraction=0.04, pad=0.02, shrink=0.8, location='left')
                cbar2.set_label('Elevation (m)', fontsize=12, fontweight='bold')
                cbar2.ax.tick_params(labelsize=10)
                
                del elevation
            else:
                # Fallback to simple visualization if elevation not available
                # Create classified depression visualization
                depression_classified = self._classify_depressions(mask)
                
                # Use GIS-standard blue color scheme for water/negative features
                colors = ['#ffffff', '#e6f3ff', '#b3d9ff', '#80bfff', '#4da6ff', '#1a8cff', '#0066cc']
                cmap = LinearSegmentedColormap.from_list('depression_classified', colors, N=7)
                
                im = ax.imshow(depression_classified, cmap=cmap, extent=extent, origin='upper', alpha=0.8)
                
                # Add colorbar with classification labels
                cbar = plt.colorbar(im, ax=ax, fraction=0.04, pad=0.02, shrink=0.8)
                cbar.set_label('Depression Classification', fontsize=12, fontweight='bold')
                cbar.ax.tick_params(labelsize=10)
                
                # Set custom tick labels for classification
                cbar.set_ticks([0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5])
                cbar.set_ticklabels(['None', 'Shallow', 'Small', 'Medium', 'Large', 'Deep', 'Extensive'])
            
            # Add comprehensive statistics box
            stats_text = f"""Depression Statistics:
• Total Depressions: {num_depressions:,} cells
• Area Coverage: {depression_density:.2f}%
• Density: {num_depressions/total_cells*10000:.1f} per 10k cells
• Spatial Distribution: {'Clustered' if self._is_clustered(mask) else 'Random'}
• Average Size: {self._calculate_average_depression_size(mask):.1f} cells"""
            
            ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
                   fontsize=11, verticalalignment='top', 
                   bbox=dict(boxstyle='round,pad=0.5', facecolor='white', 
                           alpha=0.95, edgecolor='black', linewidth=1))
        
        # Add map features
        self._add_academic_map_features(ax, extent, 'Topographic Depression Distribution Map', dx=5)
        
        plt.tight_layout()
        self._save_plot_optimized(save_path, "Topographic Depression Map")

    def _plot_wind_direction_modification(self, data, extent, save_path):
        """
        Create improved wind direction modification visualization following GIS best practices.
        Shows wind direction changes with proper circular colormap and legend.
        """
        fig, ax = plt.subplots(figsize=(14, 12))
        
        # Load elevation for context
        elevation = self.load_data('elevation.npy')
        
        if np.all(data == 0):
            # No wind direction modifications
            ax.text(0.5, 0.5, 'No wind direction modifications detected', 
                   ha='center', va='center', fontsize=16, color='gray',
                   transform=ax.transAxes)
            ax.set_axis_off()
        else:
            # Show elevation as background if available
            if elevation is not None:
                # Create hillshade for better terrain context
                hillshade = self._create_hillshade(elevation)
                ax.imshow(hillshade, cmap='gray', extent=extent, origin='upper', alpha=0.5)
                
                # Overlay elevation
                elev_img = ax.imshow(elevation, cmap='terrain', extent=extent, origin='upper', alpha=0.3)
                
                # Add elevation colorbar
                cbar_elev = plt.colorbar(elev_img, ax=ax, fraction=0.04, pad=0.02, shrink=0.8, location='left')
                cbar_elev.set_label('Elevation (m)', fontsize=12, fontweight='bold')
                cbar_elev.ax.tick_params(labelsize=10)
            
            # Create wind direction visualization
            # Use circular colormap for directional data (GIS standard)
            from matplotlib.colors import LinearSegmentedColormap
            
            # Create custom circular colormap for wind directions
            # Red = 0°, Green = 90°, Blue = 180°, Purple = 270°
            wind_colors = ['#ff0000', '#ffff00', '#00ff00', '#00ffff', '#0000ff', '#ff00ff', '#ff0000']
            wind_cmap = LinearSegmentedColormap.from_list('wind_direction', wind_colors, N=256)
            
            # Normalize data to 0-360 range
            wind_data = data.copy()
            wind_data = np.mod(wind_data, 360)  # Ensure 0-360 range
            
            # Create masked array for non-zero values only
            wind_masked = np.ma.masked_where(wind_data == 0, wind_data)
            
            # Display wind direction modification
            wind_img = ax.imshow(wind_masked, cmap=wind_cmap, extent=extent, origin='upper', 
                               alpha=0.8, vmin=0, vmax=360)
            
            # Add wind direction colorbar with degree labels
            cbar = plt.colorbar(wind_img, ax=ax, fraction=0.04, pad=0.02, shrink=0.8)
            cbar.set_label('Wind Direction Modification (degrees)', fontsize=12, fontweight='bold')
            cbar.ax.tick_params(labelsize=10)
            
            # Set custom tick labels for cardinal directions
            cbar.set_ticks([0, 45, 90, 135, 180, 225, 270, 315, 360])
            cbar.set_ticklabels(['N (0°)', 'NE (45°)', 'E (90°)', 'SE (135°)', 
                               'S (180°)', 'SW (225°)', 'W (270°)', 'NW (315°)', 'N (360°)'])
            
            # Calculate statistics
            non_zero_data = wind_data[wind_data != 0]
            if len(non_zero_data) > 0:
                mean_direction = np.mean(non_zero_data)
                std_direction = np.std(non_zero_data)
                max_change = np.max(np.abs(wind_data))
                min_change = np.min(wind_data[wind_data != 0])
                
                # Add comprehensive statistics box
                stats_text = f"""Wind Direction Statistics:
• Modified Cells: {len(non_zero_data):,} cells
• Mean Direction: {mean_direction:.1f}° ({self._degrees_to_cardinal(mean_direction)})
• Std Deviation: {std_direction:.1f}°
• Range: {min_change:.1f}° to {max_change:.1f}°
• Primary Cause: {'Barrancos' if self._is_barranco_driven_wind_direction(data) else 'Terrain'}"""
                
                ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
                       fontsize=11, verticalalignment='top', 
                       bbox=dict(boxstyle='round,pad=0.5', facecolor='white', 
                               alpha=0.95, edgecolor='black', linewidth=1))
            
            # Add wind direction arrows for key areas
            self._add_wind_direction_arrows(ax, wind_data, extent)
        
        # Add map features
        self._add_academic_map_features(ax, extent, 'Wind Direction Modification Map', dx=5)
        
        plt.tight_layout()
        self._save_plot_optimized(save_path, "Wind Direction Modification Map")

    def _degrees_to_cardinal(self, degrees):
        """
        Convert degrees to cardinal direction.
        """
        directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
                     'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
        index = round(degrees / 22.5) % 16
        return directions[index]

    def _is_barranco_driven_wind_direction(self, wind_data):
        """
        Determine if wind direction modifications are primarily driven by barrancos.
        """
        barranco_mask = self.load_data('barranco_mask.npy')
        
        if barranco_mask is None:
            return False
        
        # Calculate overlap
        wind_modified = wind_data != 0
        overlap = np.sum(wind_modified & barranco_mask)
        total_modified = np.sum(wind_modified)
        
        if total_modified == 0:
            return False
        
        # If more than 70% of wind direction modifications overlap with barrancos
        return overlap / total_modified > 0.7

    def _add_wind_direction_arrows(self, ax, wind_data, extent):
        """
        Add wind direction arrows to the map for key areas.
        """
        # Sample wind directions at regular intervals
        height, width = wind_data.shape
        step = max(1, min(height, width) // 20)  # Sample every 20th cell
        
        arrows_x = []
        arrows_y = []
        arrows_u = []
        arrows_v = []
        
        for i in range(0, height, step):
            for j in range(0, width, step):
                if wind_data[i, j] != 0:
                    # Convert to image coordinates
                    x = extent[0] + (j / width) * (extent[1] - extent[0])
                    y = extent[3] - (i / height) * (extent[3] - extent[2])
                    
                    # Convert wind direction to vector components
                    direction_rad = np.radians(wind_data[i, j])
                    u = np.cos(direction_rad) * 0.01  # Scale factor
                    v = np.sin(direction_rad) * 0.01
                    
                    arrows_x.append(x)
                    arrows_y.append(y)
                    arrows_u.append(u)
                    arrows_v.append(v)
        
        # Add arrows if we have any
        if arrows_x:
            ax.quiver(arrows_x, arrows_y, arrows_u, arrows_v, 
                     color='red', alpha=0.7, scale=50, width=0.002,
                     headwidth=3, headlength=4)

    def _plot_wind_amplification(self, data, extent, save_path):
        """
        Create improved wind amplification visualization following GIS best practices.
        Shows actual amplification values with proper classification and legend.
        """
        fig, ax = plt.subplots(figsize=(14, 12))
        
        # Load elevation for context
        elevation = self.load_data('elevation.npy')
        
        if np.all(data == 1.0):
            # No wind amplification (all values are 1.0)
            ax.text(0.5, 0.5, 'No wind amplification detected\n(all values = 1.0x)', 
                   ha='center', va='center', fontsize=16, color='gray',
                   transform=ax.transAxes)
            ax.set_axis_off()
        else:
            # Show elevation as background if available
            if elevation is not None:
                # Create hillshade for better terrain context
                hillshade = self._create_hillshade(elevation)
                ax.imshow(hillshade, cmap='gray', extent=extent, origin='upper', alpha=0.5)
                
                # Overlay elevation
                elev_img = ax.imshow(elevation, cmap='terrain', extent=extent, origin='upper', alpha=0.3)
                
                # Add elevation colorbar
                cbar_elev = plt.colorbar(elev_img, ax=ax, fraction=0.04, pad=0.02, shrink=0.8, location='left')
                cbar_elev.set_label('Elevation (m)', fontsize=12, fontweight='bold')
                cbar_elev.ax.tick_params(labelsize=10)
            
            # Create wind amplification visualization
            # Use GIS-standard blue color scheme for wind/air features
            from matplotlib.colors import LinearSegmentedColormap
            
            # Create custom colormap for wind amplification
            # White = 1.0x, Light blue = 1.5x, Blue = 2.0x, Dark blue = 3.0x+
            amplification_colors = ['#ffffff', '#e6f3ff', '#b3d9ff', '#80bfff', '#4da6ff', '#1a8cff', '#0066cc', '#004499', '#002266']
            amplification_cmap = LinearSegmentedColormap.from_list('wind_amplification', amplification_colors, N=256)
            
            # Normalize data to 1.0-4.0 range for better visualization
            wind_data = data.copy()
            wind_data = np.clip(wind_data, 1.0, 4.0)  # Clip to reasonable range
            
            # Create masked array for non-standard values (not 1.0)
            wind_masked = np.ma.masked_where(wind_data == 1.0, wind_data)
            
            # Display wind amplification
            wind_img = ax.imshow(wind_masked, cmap=amplification_cmap, extent=extent, origin='upper', 
                               alpha=0.8, vmin=1.0, vmax=4.0)
            
            # Add wind amplification colorbar
            cbar = plt.colorbar(wind_img, ax=ax, fraction=0.04, pad=0.02, shrink=0.8)
            cbar.set_label('Wind Amplification Factor', fontsize=12, fontweight='bold')
            cbar.ax.tick_params(labelsize=10)
            
            # Set custom tick labels for amplification values
            cbar.set_ticks([1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0])
            cbar.set_ticklabels(['1.0x', '1.5x', '2.0x', '2.5x', '3.0x', '3.5x', '4.0x+'])
            
            # Calculate statistics
            non_standard_data = wind_data[wind_data != 1.0]
            if len(non_standard_data) > 0:
                mean_amplification = np.mean(non_standard_data)
                max_amplification = np.max(wind_data)
                min_amplification = np.min(wind_data)
                std_amplification = np.std(non_standard_data)
                
                # Count cells with different amplification levels
                cells_1_5x = np.sum((wind_data >= 1.5) & (wind_data < 2.0))
                cells_2_0x = np.sum((wind_data >= 2.0) & (wind_data < 2.5))
                cells_2_5x = np.sum((wind_data >= 2.5) & (wind_data < 3.0))
                cells_3_0x = np.sum(wind_data >= 3.0)
                
                # Add comprehensive statistics box
                stats_text = f"""Wind Amplification Statistics:
• Amplified Cells: {len(non_standard_data):,} cells
• Mean Amplification: {mean_amplification:.2f}x
• Range: {min_amplification:.2f}x - {max_amplification:.2f}x
• Std Deviation: {std_amplification:.2f}x
• Distribution:
  - 1.5-2.0x: {cells_1_5x:,} cells
  - 2.0-2.5x: {cells_2_0x:,} cells
  - 2.5-3.0x: {cells_2_5x:,} cells
  - 3.0x+: {cells_3_0x:,} cells"""
                
                ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
                       fontsize=11, verticalalignment='top', 
                       bbox=dict(boxstyle='round,pad=0.5', facecolor='white', 
                               alpha=0.95, edgecolor='black', linewidth=1))
            
            # Add wind direction arrows for high amplification areas
            self._add_amplification_arrows(ax, wind_data, extent)
        
        # Add map features
        self._add_academic_map_features(ax, extent, 'Wind Amplification Map', dx=5)
        
        plt.tight_layout()
        self._save_plot_optimized(save_path, "Wind Amplification Map")

    def _add_amplification_arrows(self, ax, wind_data, extent):
        """
        Add wind direction arrows to high amplification areas.
        """
        # Sample high amplification areas
        high_amp_mask = wind_data >= 2.0  # Areas with 2.0x or higher amplification
        
        if not np.any(high_amp_mask):
            return
        
        # Load wind direction data if available
        wind_direction = self.load_data('wind_direction_modification.npy')
        
        if wind_direction is None:
            return
        
        # Sample arrows at regular intervals in high amplification areas
        height, width = wind_data.shape
        step = max(1, min(height, width) // 15)  # Sample every 15th cell
        
        arrows_x = []
        arrows_y = []
        arrows_u = []
        arrows_v = []
        
        for i in range(0, height, step):
            for j in range(0, width, step):
                if high_amp_mask[i, j] and wind_direction[i, j] != 0:
                    # Convert to image coordinates
                    x = extent[0] + (j / width) * (extent[1] - extent[0])
                    y = extent[3] - (i / height) * (extent[3] - extent[2])
                    
                    # Convert wind direction to vector components
                    direction_rad = np.radians(wind_direction[i, j])
                    u = np.cos(direction_rad) * 0.015  # Scale factor
                    v = np.sin(direction_rad) * 0.015
                    
                    arrows_x.append(x)
                    arrows_y.append(y)
                    arrows_u.append(u)
                    arrows_v.append(v)
        
        # Add arrows if we have any
        if arrows_x:
            ax.quiver(arrows_x, arrows_y, arrows_u, arrows_v, 
                     color='red', alpha=0.8, scale=30, width=0.003,
                     headwidth=4, headlength=5)

    def run_visualization(self, create_summary: bool = False, create_individual: bool = True, simple_mode: bool = False) -> None:
        """
        Main entry point for generating all visualizations and statistics.
        
        Args:
            create_summary: Whether to create summary plots
            create_individual: Whether to create individual plots
            simple_mode: Skip complex analyses for very large datasets
        """
        print("Starting terrain data visualization...")
        print(f"Data directory: {self.data_dir}")
        print(f"Output directory: {self.output_dir}")
        
        if simple_mode:
            print("🔧 SIMPLE MODE: Skipping complex analyses for performance")

        # Get extent once
        extent = self._get_extent()
        print(f"Using extent: {extent}")

        # Individual plots - load data one at a time
        if create_individual:
            print("\nCreating individual plots...")
            
            # Elevation
            data = self.load_data('elevation.npy')
            if data is not None:
                self._plot_standard(data, extent, os.path.join(self.output_dir, 'elevation.png'), 'Map of Elevation', 'terrain', 'Elevation (m)')
                del data
            
            # Slope
            data = self.load_data('slope.npy')
            if data is not None:
                self._plot_standard(data, extent, os.path.join(self.output_dir, 'slope.png'), 'Map of Slope', 'viridis', 'Slope (degrees)')
                del data
            
            # Aspect
            data = self.load_data('aspect.npy')
            if data is not None:
                self._plot_standard(data, extent, os.path.join(self.output_dir, 'aspect.png'), 'Map of Aspect', 'hsv', 'Aspect (degrees)')
                del data
            
            # Barranco mask
            data = self.load_data('barranco_mask.npy')
            if data is not None:
                self._plot_barranco_mask(data, extent, os.path.join(self.output_dir, 'barranco_mask.png'))
                del data
            
            # Depression mask
            data = self.load_data('depression_mask.npy')
            if data is not None:
                self._plot_depression_mask(data, extent, os.path.join(self.output_dir, 'depression_mask.png'))
                del data
            
            # Wind channeling (needs elevation for background)
            mask_data = self.load_data('wind_channeling_mask.npy')
            elev_data = self.load_data('elevation.npy')
            if mask_data is not None and elev_data is not None:
                self._plot_wind_channeling(mask_data, elev_data, extent, os.path.join(self.output_dir, 'wind_channeling_mask.png'))
                del mask_data, elev_data
            
            # Wind amplification (improved visualization)
            data = self.load_data('wind_amplification.npy')
            if data is not None:
                self._plot_wind_amplification(data, extent, os.path.join(self.output_dir, 'wind_amplification.png'))
                del data
            
            # Wind direction modification
            data = self.load_data('wind_direction_modification.npy')
            if data is not None:
                self._plot_wind_direction_modification(data, extent, os.path.join(self.output_dir, 'wind_direction_modification.png'))
                del data
        
        # Create summary plot (disabled by default to save memory)
        if create_summary:
            print("\nCreating summary plot...")
            # This would load all data at once - disabled for memory optimization
            print("Summary plot disabled for memory optimization")
        
        # Create statistics report
        print("\nCreating statistics report...")
        self._create_statistics_report()
        
        print(f"\nVisualization complete! Check the '{self.output_dir}' directory for outputs.")

    def _create_statistics_report(self):
        """Create statistics report by loading data one at a time."""
        report_lines = ["TERRAIN DATA STATISTICS REPORT", "=" * 40, ""]
        
        files_to_analyze = [
            'elevation.npy', 'slope.npy', 'aspect.npy', 'barranco_mask.npy',
            'depression_mask.npy', 'wind_channeling_mask.npy', 'wind_amplification.npy',
            'wind_direction_modification.npy'
        ]
        
        for filename in files_to_analyze:
            name = filename.replace('.npy', '')
            data = self.load_data(filename)
            if data is not None:
                report_lines.append(f"Dataset: {name}")
                report_lines.append("-" * 20)
                
                # Basic statistics
                valid_data = data[~np.isnan(data)]
                if len(valid_data) > 0:
                    report_lines.append(f"Shape: {data.shape}")
                    report_lines.append(f"Valid cells: {len(valid_data)}")
                    report_lines.append(f"NaN cells: {np.isnan(data).sum()}")
                    report_lines.append(f"Min: {valid_data.min():.4f}")
                    report_lines.append(f"Max: {valid_data.max():.4f}")
                    report_lines.append(f"Mean: {valid_data.mean():.4f}")
                    report_lines.append(f"Std: {valid_data.std():.4f}")
                    
                    if 'mask' in name:
                        true_count = np.sum(data == 1)
                        false_count = np.sum(data == 0)
                        report_lines.append(f"True values: {true_count}")
                        report_lines.append(f"False values: {false_count}")
                        report_lines.append(f"Percentage detected: {(true_count/len(valid_data)*100):.2f}%")
                else:
                    report_lines.append("No valid data found")
                
                report_lines.append("")
                del data
                self._cleanup_memory()
        
        # Save report
        report_path = self.output_dir / "terrain_statistics.txt"
        with open(report_path, 'w') as f:
            f.write('\n'.join(report_lines))
        print(f"Saved statistics report: {report_path}")

    def _create_hillshade(self, elevation, azimuth=315, altitude=45):
        """
        Create hillshade effect for better terrain visualization.
        Optimized for large datasets.
        """
        from scipy import ndimage
        
        # Early termination for very large datasets
        if elevation.size > 1000000:  # 1M cells
            print("   ⚡ Skipping hillshade calculation for large dataset (performance optimization)")
            return np.ones_like(elevation) * 0.5  # Return neutral gray
        
        # Calculate gradients
        dx = ndimage.sobel(elevation, axis=1)
        dy = ndimage.sobel(elevation, axis=0)
        
        # Calculate slope and aspect
        slope = np.arctan(np.sqrt(dx**2 + dy**2))
        aspect = np.arctan2(dy, dx)
        
        # Convert azimuth and altitude to radians
        azimuth_rad = np.radians(azimuth)
        altitude_rad = np.radians(altitude)
        
        # Calculate hillshade
        hillshade = (np.sin(altitude_rad) * np.sin(slope) + 
                    np.cos(altitude_rad) * np.cos(slope) * 
                    np.cos(azimuth_rad - aspect))
        
        # Normalize to 0-1 range
        hillshade = (hillshade - np.min(hillshade)) / (np.max(hillshade) - np.min(hillshade))
        
        return hillshade

    def _classify_barrancos(self, mask):
        """
        Classify barrancos based on connectivity and size.
        Optimized for large datasets.
        """
        from scipy import ndimage
        
        # Early termination for very large datasets
        if mask.size > 1000000:  # 1M cells
            print("   ⚡ Skipping barranco classification for large dataset (performance optimization)")
            return np.zeros_like(mask, dtype=int)
        
        # Label connected components
        labeled, num_features = ndimage.label(mask)
        
        if num_features == 0:
            return np.zeros_like(mask, dtype=int)
        
        # Early termination for too many features
        if num_features > 5000:
            print(f"   ⚡ Skipping barranco classification for {num_features} features (performance optimization)")
            return np.zeros_like(mask, dtype=int)
        
        # Calculate area of each component
        areas = ndimage.sum(mask, labeled, range(1, num_features + 1))
        
        # Create classification array
        classified = np.zeros_like(mask, dtype=int)
        
        for i, area in enumerate(areas):
            if area < 10:
                classified[labeled == i + 1] = 1  # Isolated
            elif area < 50:
                classified[labeled == i + 1] = 2  # Small
            elif area < 200:
                classified[labeled == i + 1] = 3  # Medium
            elif area < 500:
                classified[labeled == i + 1] = 4  # Large
            else:
                classified[labeled == i + 1] = 5  # Extensive
        
        return classified

    def _classify_wind_amplification(self, wind_data):
        """
        Classify wind amplification values into meaningful categories.
        """
        classified = np.zeros_like(wind_data, dtype=int)
        
        # Create classification based on amplification values
        classified[wind_data >= 1.0] = 1  # 1.0x
        classified[wind_data >= 1.5] = 2  # 1.5x
        classified[wind_data >= 2.0] = 3  # 2.0x
        classified[wind_data >= 2.5] = 4  # 2.5x
        classified[wind_data >= 3.0] = 5  # 3.0x
        classified[wind_data >= 3.5] = 6  # 3.5x+
        
        return classified

    def _is_clustered(self, mask):
        """
        Determine if features are clustered or randomly distributed.
        Optimized for large datasets with early termination.
        """
        from scipy import ndimage
        
        # Early termination for very large datasets
        if mask.size > 1000000:  # 1M cells
            print("   ⚡ Skipping clustering analysis for large dataset (performance optimization)")
            return False
        
        # Calculate nearest neighbor distances
        labeled, num_features = ndimage.label(mask)
        
        if num_features < 2:
            return False
        
        # Early termination for too many features
        if num_features > 1000:
            print(f"   ⚡ Skipping clustering analysis for {num_features} features (performance optimization)")
            return False
        
        # Get centroids of features
        centroids = ndimage.center_of_mass(mask, labeled, range(1, num_features + 1))
        centroids = np.array(centroids)
        
        # Optimized distance calculation using vectorized operations
        if len(centroids) > 100:
            # For large numbers of features, use sampling
            sample_size = min(100, len(centroids))
            indices = np.random.choice(len(centroids), sample_size, replace=False)
            centroids = centroids[indices]
            print(f"   ⚡ Using {sample_size} sample features for clustering analysis")
        
        # Calculate distances more efficiently
        distances = []
        for i, centroid in enumerate(centroids):
            # Calculate distances to all other centroids at once
            other_centroids = centroids[np.arange(len(centroids)) != i]
            if len(other_centroids) > 0:
                dists = np.sqrt(np.sum((other_centroids - centroid)**2, axis=1))
                distances.append(np.min(dists))
        
        if not distances:
            return False
        
        avg_distance = np.mean(distances)
        
        # Simple clustering test: if average distance is small relative to grid size
        grid_size = np.sqrt(mask.size)
        return avg_distance < grid_size * 0.1

    def _is_barranco_driven(self, wind_mask):
        """
        Determine if wind channeling is primarily driven by barrancos.
        """
        barranco_mask = self.load_data('barranco_mask.npy')
        
        if barranco_mask is None:
            return False
        
        # Calculate overlap
        overlap = np.sum(wind_mask & barranco_mask)
        total_wind = np.sum(wind_mask)
        
        if total_wind == 0:
            return False
        
        # If more than 70% of wind channeling overlaps with barrancos
        return overlap / total_wind > 0.7

    def _classify_depressions(self, mask):
        """
        Classify depressions based on connectivity and size.
        Optimized for large datasets.
        """
        from scipy import ndimage
        
        # Early termination for very large datasets
        if mask.size > 1000000:  # 1M cells
            print("   ⚡ Skipping depression classification for large dataset (performance optimization)")
            return np.zeros_like(mask, dtype=int)
        
        # Label connected components
        labeled, num_features = ndimage.label(mask)
        
        if num_features == 0:
            return np.zeros_like(mask, dtype=int)
        
        # Early termination for too many features
        if num_features > 5000:
            print(f"   ⚡ Skipping depression classification for {num_features} features (performance optimization)")
            return np.zeros_like(mask, dtype=int)
        
        # Calculate area of each component
        areas = ndimage.sum(mask, labeled, range(1, num_features + 1))
        
        # Create classification array
        classified = np.zeros_like(mask, dtype=int)
        
        for i, area in enumerate(areas):
            if area < 5:
                classified[labeled == i + 1] = 1  # Shallow
            elif area < 20:
                classified[labeled == i + 1] = 2  # Small
            elif area < 100:
                classified[labeled == i + 1] = 3  # Medium
            elif area < 300:
                classified[labeled == i + 1] = 4  # Large
            elif area < 800:
                classified[labeled == i + 1] = 5  # Deep
            else:
                classified[labeled == i + 1] = 6  # Extensive
        
        return classified

    def _calculate_average_depression_size(self, mask):
        """
        Calculate the average size of depression features.
        """
        from scipy import ndimage
        
        # Label connected components
        labeled, num_features = ndimage.label(mask)
        
        if num_features == 0:
            return 0.0
        
        # Calculate area of each component
        areas = ndimage.sum(mask, labeled, range(1, num_features + 1))
        
        return np.mean(areas)

    def _downsample_for_visualization(self, data, max_size=3000, is_mask=False):
        """
        Downsample data for visualization if it's too large.
        
        Args:
            data: Input data array
            max_size: Maximum size for visualization
            is_mask: Whether this is a binary mask (affects interpolation order)
            
        Returns:
            tuple: (downsampled_data, downsampling_factor)
        """
        if data.shape[0] <= max_size and data.shape[1] <= max_size:
            return data, 1
        
        print(f"⚠️  Large dataset detected ({data.shape[0]}×{data.shape[1]}), downsampling for visualization...")
        
        # Calculate downsampling factor
        factor = max(data.shape[0] // max_size, data.shape[1] // max_size)
        
        # Downsample data
        from scipy import ndimage
        if is_mask:
            # Use nearest neighbor interpolation for masks
            data_downsampled = ndimage.zoom(data.astype(float), 1/factor, order=0) > 0.5
        else:
            # Use linear interpolation for continuous data
            data_downsampled = ndimage.zoom(data, 1/factor, order=1)
        
        print(f"   Downsampled to {data_downsampled.shape[0]}×{data_downsampled.shape[1]} (factor: 1/{factor})")
        
        return data_downsampled, factor


def main():
    """Main function to run the visualization script."""
    parser = argparse.ArgumentParser(description='Visualize preprocessed terrain data')
    parser.add_argument('--data-dir', default='preprocessed_terrain', 
                       help='Directory containing terrain data (default: preprocessed_terrain)')
    parser.add_argument('--output-dir', default='visualizations', 
                       help='Output directory for visualizations (default: visualizations)')
    parser.add_argument('--summary-only', action='store_true', 
                       help='Create only summary plot')
    parser.add_argument('--individual-only', action='store_true', 
                       help='Create only individual plots')
    parser.add_argument('--simple-mode', action='store_true',
                       help='Skip complex analyses for very large datasets (performance optimization)')
    
    args = parser.parse_args()
    
    # Create visualizer
    visualizer = TerrainVisualizer(args.data_dir, args.output_dir)
    
    # Determine what to create
    create_summary = args.summary_only
    create_individual = not args.summary_only
    
    # Run visualization
    visualizer.run_visualization(create_summary=create_summary, create_individual=create_individual, simple_mode=args.simple_mode)


if __name__ == "__main__":
    main() 