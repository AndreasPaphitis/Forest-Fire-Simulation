#!/usr/bin/env python3
"""
Centralized Chart Styling System
Professional, consistent styling for all sensitivity analysis and validation charts
"""

import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
import plotly.graph_objects as go
import plotly.express as px

class ChartStyler:
    """Centralized styling system for all charts."""
    
    def __init__(self):
        """Initialize the chart styler with professional settings."""
        self.setup_matplotlib_style()
        self.setup_color_palettes()
        self.setup_plotly_style()
    
    def setup_matplotlib_style(self):
        """Configure matplotlib/seaborn global settings."""
        
        # Set the overall style - clean and professional
        sns.set_style("whitegrid", {
            "grid.color": "#e0e0e0",
            "grid.linewidth": 0.8,
            "axes.edgecolor": "#333333",
            "axes.linewidth": 1.2,
            "axes.spines.left": True,
            "axes.spines.bottom": True,
            "axes.spines.top": False,
            "axes.spines.right": False,
        })
        
        # Professional font configuration
        plt.rcParams.update({
            'font.family': 'sans-serif',
            'font.sans-serif': ['Arial', 'DejaVu Sans', 'Liberation Sans', 'sans-serif'],
            'font.size': 11,
            'axes.titlesize': 14,
            'axes.labelsize': 12,
            'xtick.labelsize': 10,
            'ytick.labelsize': 10,
            'legend.fontsize': 11,
            'figure.titlesize': 16,
            'axes.titleweight': 'bold',
            'figure.titleweight': 'bold'
        })
        
        # Line and marker styling
        plt.rcParams.update({
            'lines.linewidth': 2.5,
            'lines.markersize': 8,
            'patch.linewidth': 1.2,
            'axes.linewidth': 1.2,
            'grid.linewidth': 0.8,
            'xtick.major.width': 1.2,
            'ytick.major.width': 1.2,
            'xtick.minor.width': 0.8,
            'ytick.minor.width': 0.8,
        })
        
        # Layout and spacing
        plt.rcParams.update({
            'figure.autolayout': True,
            'figure.constrained_layout.use': True,
            'axes.titlepad': 15,
            'axes.labelpad': 8,
            'xtick.major.pad': 6,
            'ytick.major.pad': 6,
        })
        
        # High-quality output
        plt.rcParams.update({
            'figure.dpi': 100,
            'savefig.dpi': 300,
            'savefig.bbox': 'tight',
            'savefig.pad_inches': 0.1,
            'savefig.facecolor': 'white',
            'savefig.edgecolor': 'none'
        })
    
    def setup_color_palettes(self):
        """Define professional, accessible color palettes."""
        
        # Primary color palette - scientifically inspired
        self.primary_colors = {
            'fire_red': '#d32f2f',      # Strong red for fire/critical
            'ember_orange': '#ff8f00',   # Orange for ember systems
            'forest_green': '#388e3c',   # Green for vegetation/success
            'sky_blue': '#1976d2',       # Blue for analysis/water
            'earth_brown': '#5d4037',    # Brown for terrain/soil
            'ash_gray': '#616161',       # Gray for neutral/secondary
            'gold': '#f57c00',           # Gold for highlights
            'purple': '#7b1fa2'          # Purple for special categories
        }
        
        # Validation-specific colors (Day 3 vs Day 4)
        self.validation_colors = {
            'day3': '#e57373',          # Softer red for Day 3
            'day4': '#64b5f6',          # Softer blue for Day 4
            'day3_dark': '#c62828',     # Darker red for emphasis
            'day4_dark': '#1565c0',     # Darker blue for emphasis
        }
        
        # Sensitivity analysis colors (by importance tier)
        self.sensitivity_colors = {
            'critical': '#d32f2f',      # Red for critical parameters
            'high': '#ff8f00',          # Orange for high sensitivity
            'moderate': '#ffa726',      # Light orange for moderate
            'low': '#66bb6a',           # Green for low sensitivity
            'minimal': '#e0e0e0'        # Gray for minimal impact
        }
        
        # Fire spread mechanism colors
        self.spread_colors = {
            'ember': '#ff5722',         # Red-orange for ember spread
            'horizontal': '#2196f3',    # Blue for horizontal spread
            'vertical': '#4caf50',      # Green for vertical spread
            'other': '#9e9e9e'          # Gray for other mechanisms
        }
        
        # Sequential color maps for heatmaps and continuous data
        self.sequential_colors = {
            'fire_intensity': ['#fff3e0', '#ff8f00', '#d32f2f', '#b71c1c'],
            'performance': ['#e8f5e8', '#66bb6a', '#2e7d32', '#1b5e20'],
            'efficiency': ['#e3f2fd', '#42a5f5', '#1976d2', '#0d47a1']
        }
        
        # Create custom colormaps
        self.create_custom_colormaps()
    
    def create_custom_colormaps(self):
        """Create custom matplotlib colormaps."""
        
        # Fire intensity colormap
        self.fire_cmap = LinearSegmentedColormap.from_list(
            'fire_intensity', self.sequential_colors['fire_intensity'], N=256
        )
        
        # Performance colormap
        self.performance_cmap = LinearSegmentedColormap.from_list(
            'performance', self.sequential_colors['performance'], N=256
        )
        
        # Efficiency colormap
        self.efficiency_cmap = LinearSegmentedColormap.from_list(
            'efficiency', self.sequential_colors['efficiency'], N=256
        )
        
        # Diverging colormap for comparisons
        self.diverging_cmap = LinearSegmentedColormap.from_list(
            'comparison', ['#d32f2f', '#ffffff', '#1976d2'], N=256
        )
    
    def setup_plotly_style(self):
        """Configure plotly styling."""
        
        self.plotly_template = {
            'layout': {
                'font': {
                    'family': 'Arial, sans-serif',
                    'size': 12,
                    'color': '#333333'
                },
                'title': {
                    'font': {'size': 16, 'color': '#1a1a1a'},
                    'x': 0.5,
                    'xanchor': 'center'
                },
                'colorway': [
                    self.primary_colors['fire_red'],
                    self.primary_colors['sky_blue'],
                    self.primary_colors['ember_orange'],
                    self.primary_colors['forest_green'],
                    self.primary_colors['purple'],
                    self.primary_colors['gold'],
                    self.primary_colors['earth_brown'],
                    self.primary_colors['ash_gray']
                ],
                'plot_bgcolor': 'white',
                'paper_bgcolor': 'white',
                'gridcolor': '#e0e0e0',
                'gridwidth': 1,
                'zeroline': False,
                'showgrid': True
            }
        }
    
    def get_color_palette(self, palette_type, n_colors=None):
        """Get a specific color palette."""
        
        if palette_type == 'primary':
            colors = list(self.primary_colors.values())
        elif palette_type == 'validation':
            colors = [self.validation_colors['day3'], self.validation_colors['day4']]
        elif palette_type == 'sensitivity':
            colors = list(self.sensitivity_colors.values())
        elif palette_type == 'spread_mechanisms':
            colors = list(self.spread_colors.values())
        else:
            colors = list(self.primary_colors.values())
        
        if n_colors and n_colors <= len(colors):
            return colors[:n_colors]
        return colors
    
    def apply_matplotlib_style(self, palette_type='primary'):
        """Apply matplotlib styling with specified palette."""
        
        # Set the color palette
        colors = self.get_color_palette(palette_type)
        sns.set_palette(colors)
        
        return colors
    
    def apply_plotly_style(self, fig):
        """Apply plotly styling to a figure."""
        
        fig.update_layout(self.plotly_template['layout'])
        return fig
    
    def create_figure(self, figsize=(12, 8), palette_type='primary'):
        """Create a properly styled matplotlib figure."""
        
        self.apply_matplotlib_style(palette_type)
        fig, ax = plt.subplots(figsize=figsize)
        
        # Apply additional styling to axes
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#333333')
        ax.spines['bottom'].set_color('#333333')
        
        return fig, ax
    
    def style_bar_chart(self, ax, add_value_labels=True, label_format='{:.3f}'):
        """Apply consistent styling to bar charts."""
        
        # Add value labels if requested
        if add_value_labels:
            for container in ax.containers:
                ax.bar_label(container, fmt=label_format, fontweight='bold', 
                           fontsize=10, padding=3)
        
        # Style the axes
        ax.grid(True, alpha=0.3, axis='y')
        ax.set_axisbelow(True)
        
        return ax
    
    def style_line_plot(self, ax, add_markers=True):
        """Apply consistent styling to line plots."""
        
        # Get the lines and style them
        lines = ax.get_lines()
        markers = ['o', 's', '^', 'D', 'v', '<', '>', 'p', '*', 'h']
        
        for i, line in enumerate(lines):
            if add_markers:
                line.set_marker(markers[i % len(markers)])
                line.set_markersize(8)
                line.set_markerfacecolor(line.get_color())
                line.set_markeredgecolor('white')
                line.set_markeredgewidth(1.5)
            line.set_linewidth(2.5)
        
        ax.grid(True, alpha=0.3)
        ax.set_axisbelow(True)
        
        return ax
    
    def style_heatmap(self, ax, colormap='fire_intensity'):
        """Apply consistent styling to heatmaps."""
        
        # Get the appropriate colormap
        if colormap == 'fire_intensity':
            cmap = self.fire_cmap
        elif colormap == 'performance':
            cmap = self.performance_cmap
        elif colormap == 'efficiency':
            cmap = self.efficiency_cmap
        elif colormap == 'diverging':
            cmap = self.diverging_cmap
        else:
            cmap = 'viridis'
        
        return cmap
    
    def save_figure(self, fig, filepath, title=None):
        """Save figure with consistent settings."""
        
        if title:
            fig.suptitle(title, fontsize=16, fontweight='bold', y=0.98)
        
        fig.savefig(filepath, dpi=300, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        plt.close(fig)
    
    def create_plotly_figure(self, title=None):
        """Create a properly styled plotly figure."""
        
        fig = go.Figure()
        fig.update_layout(self.plotly_template['layout'])
        
        if title:
            fig.update_layout(title=title)
        
        return fig

# Global styler instance
styler = ChartStyler()

# Convenience functions for easy use
def apply_style(palette_type='primary'):
    """Quick function to apply styling."""
    return styler.apply_matplotlib_style(palette_type)

def create_styled_figure(figsize=(12, 8), palette_type='primary'):
    """Quick function to create styled figure."""
    return styler.create_figure(figsize, palette_type)

def get_colors(palette_type, n_colors=None):
    """Quick function to get color palette."""
    return styler.get_color_palette(palette_type, n_colors)

def style_chart(ax, chart_type='bar', **kwargs):
    """Quick function to style charts."""
    if chart_type == 'bar':
        return styler.style_bar_chart(ax, **kwargs)
    elif chart_type == 'line':
        return styler.style_line_plot(ax, **kwargs)
    return ax

def save_styled_figure(fig, filepath, title=None):
    """Quick function to save with styling."""
    styler.save_figure(fig, filepath, title)

def create_styled_plotly_figure(title=None):
    """Quick function to create styled plotly figure."""
    return styler.create_plotly_figure(title)
