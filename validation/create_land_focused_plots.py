#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Land-Focused Terrain Validation Plots

This script creates informative validation plots that focus on land areas
rather than the entire DTM which is mostly sea. It generates plots that
are actually useful for understanding the terrain characteristics relevant
to forest fire simulation.

Author: Forest Fire Simulation Team
Date: 2025
Version: 1.0
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import json
import sys

# Set style for better plots
plt.style.use('default')

def load_terrain_data(preprocessed_dir):
    """Load terrain data from preprocessed directory."""
    preprocessed_path = Path(preprocessed_dir)
    
    print(f"📁 Loading terrain data from {preprocessed_path}")
    
    # Load all terrain data
    elevation = np.load(preprocessed_path / "elevation.npy")
    slope = np.load(preprocessed_path / "slope.npy")
    aspect = np.load(preprocessed_path / "aspect.npy")
    barranco_mask = np.load(preprocessed_path / "barranco_mask.npy")
    barranco_directions = np.load(preprocessed_path / "barranco_directions.npy")
    depression_mask = np.load(preprocessed_path / "depression_mask.npy")
    wind_channeling_mask = np.load(preprocessed_path / "wind_channeling_mask.npy")
    wind_amplification = np.load(preprocessed_path / "wind_amplification.npy")
    wind_direction_modification = np.load(preprocessed_path / "wind_direction_modification.npy")
    
    # Load metadata
    metadata_file = preprocessed_path / "metadata.json"
    if metadata_file.exists():
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
    else:
        metadata = {}
    
    return {
        'elevation': elevation,
        'slope': slope,
        'aspect': aspect,
        'barranco_mask': barranco_mask,
        'barranco_directions': barranco_directions,
        'depression_mask': depression_mask,
        'wind_channeling_mask': wind_channeling_mask,
        'wind_amplification': wind_amplification,
        'wind_direction_modification': wind_direction_modification,
        'metadata': metadata
    }

def create_land_focused_plots(data, output_dir):
    """Create informative plots focusing on land areas."""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    print(f"📊 Creating land-focused validation plots...")
    
    # Create land mask (elevation > 0.1m to exclude sea level)
    land_mask = data['elevation'] > 0.1
    land_elevation = data['elevation'][land_mask]
    land_slope = data['slope'][land_mask]
    land_aspect = data['aspect'][land_mask]
    
    print(f"🏔️ Land analysis: {np.sum(land_mask):,} land cells out of {land_mask.size:,} total cells")
    print(f"🌊 Sea analysis: {np.sum(~land_mask):,} sea cells ({np.sum(~land_mask)/land_mask.size*100:.1f}%)")
    
    # 1. Land vs Sea Distribution
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Land/Sea pie chart
    land_sea_counts = [np.sum(land_mask), np.sum(~land_mask)]
    labels = ['Land', 'Sea']
    colors = ['#8B4513', '#4169E1']
    
    ax1.pie(land_sea_counts, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
    ax1.set_title('Land vs Sea Distribution', fontsize=14, fontweight='bold')
    
    # Elevation histogram (land only)
    ax2.hist(land_elevation, bins=50, alpha=0.7, color='#8B4513', edgecolor='black')
    ax2.set_title('Land Elevation Distribution', fontsize=14, fontweight='bold')
    ax2.set_xlabel('Elevation (m)')
    ax2.set_ylabel('Frequency')
    ax2.grid(True, alpha=0.3)
    ax2.axvline(np.median(land_elevation), color='red', linestyle='--', 
                label=f'Median: {np.median(land_elevation):.0f}m')
    ax2.axvline(np.mean(land_elevation), color='orange', linestyle='--', 
                label=f'Mean: {np.mean(land_elevation):.0f}m')
    ax2.legend()
    
    plt.tight_layout()
    plt.savefig(output_path / "land_sea_distribution.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    # 2. Land Terrain Characteristics
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle('Land Terrain Characteristics (Sea Areas Excluded)', fontsize=16, fontweight='bold')
    
    # Land elevation map (zoomed to show detail)
    im1 = axes[0, 0].imshow(data['elevation'], cmap='terrain', alpha=0.8)
    axes[0, 0].set_title(f'Full Elevation Map\n({data["elevation"].shape[0]}×{data["elevation"].shape[1]} cells)')
    axes[0, 0].axis('off')
    plt.colorbar(im1, ax=axes[0, 0], label='Elevation (m)')
    
    # Land-only elevation
    land_elevation_map = data['elevation'].copy()
    land_elevation_map[~land_mask] = np.nan
    im2 = axes[0, 1].imshow(land_elevation_map, cmap='terrain', alpha=0.8)
    axes[0, 1].set_title(f'Land Elevation Only\n({np.sum(land_mask):,} cells)')
    axes[0, 1].axis('off')
    plt.colorbar(im2, ax=axes[0, 1], label='Elevation (m)')
    
    # Land slope distribution
    axes[0, 2].hist(land_slope, bins=50, alpha=0.7, color='green', edgecolor='black')
    axes[0, 2].set_title('Land Slope Distribution', fontweight='bold')
    axes[0, 2].set_xlabel('Slope (°)')
    axes[0, 2].set_ylabel('Frequency')
    axes[0, 2].grid(True, alpha=0.3)
    axes[0, 2].axvline(np.median(land_slope), color='red', linestyle='--', 
                      label=f'Median: {np.median(land_slope):.1f}°')
    axes[0, 2].legend()
    
    # Barranco detection (land only)
    land_barranco = data['barranco_mask'].copy()
    land_barranco[~land_mask] = False
    im3 = axes[1, 0].imshow(land_barranco, cmap='Reds', alpha=0.8)
    axes[1, 0].set_title(f'Barranco Detection (Land Only)\n({np.sum(land_barranco):,} cells)')
    axes[1, 0].axis('off')
    
    # Depression detection (land only)
    land_depression = data['depression_mask'].copy()
    land_depression[~land_mask] = False
    im4 = axes[1, 1].imshow(land_depression, cmap='Blues', alpha=0.8)
    axes[1, 1].set_title(f'Depression Detection (Land Only)\n({np.sum(land_depression):,} cells)')
    axes[1, 1].axis('off')
    
    # Wind channeling (land only)
    land_wind = data['wind_channeling_mask'].copy()
    land_wind[~land_mask] = False
    im5 = axes[1, 2].imshow(land_wind, cmap='YlOrRd', alpha=0.8)
    axes[1, 2].set_title(f'Wind Channeling (Land Only)\n({np.sum(land_wind):,} cells)')
    axes[1, 2].axis('off')
    
    plt.tight_layout()
    plt.savefig(output_path / "land_terrain_characteristics.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    # 3. Feature Analysis
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Terrain Feature Analysis (Land Areas)', fontsize=16, fontweight='bold')
    
    # Feature densities comparison
    land_total = np.sum(land_mask)
    feature_counts = {
        'Barrancos': np.sum(data['barranco_mask'] & land_mask),
        'Depressions': np.sum(data['depression_mask'] & land_mask),
        'Wind Channeling': np.sum(data['wind_channeling_mask'] & land_mask)
    }
    
    feature_densities = {k: v/land_total for k, v in feature_counts.items()}
    
    bars = axes[0, 0].bar(feature_densities.keys(), feature_densities.values(), 
                         color=['red', 'blue', 'orange'], alpha=0.7)
    axes[0, 0].set_title('Feature Densities (Land Areas Only)', fontweight='bold')
    axes[0, 0].set_ylabel('Density (fraction of land cells)')
    axes[0, 0].grid(True, alpha=0.3)
    
    # Add value labels
    for bar, (name, density) in zip(bars, feature_densities.items()):
        height = bar.get_height()
        axes[0, 0].text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                       f'{density:.4f}\n({feature_counts[name]:,} cells)', 
                       ha='center', va='bottom', fontsize=10)
    
    # Slope vs Barranco relationship
    steep_slopes = land_slope > 25  # Using 25° threshold
    barranco_on_steep = np.sum((data['barranco_mask'] & land_mask) & (data['slope'] > 25))
    total_barrancos = np.sum(data['barranco_mask'] & land_mask)
    
    if total_barrancos > 0:
        barranco_steep_ratio = barranco_on_steep / total_barrancos
        axes[0, 1].pie([barranco_steep_ratio, 1-barranco_steep_ratio], 
                      labels=[f'On Steep Slopes\n(≥25°)', 'On Gentle Slopes\n(<25°)'],
                      colors=['red', 'lightcoral'], autopct='%1.1f%%')
        axes[0, 1].set_title(f'Barranco Distribution by Slope\n({barranco_on_steep}/{total_barrancos} barrancos)')
    else:
        axes[0, 1].text(0.5, 0.5, 'No barrancos detected', ha='center', va='center', 
                       transform=axes[0, 1].transAxes, fontsize=12)
        axes[0, 1].set_title('Barranco Distribution by Slope')
    
    # Elevation vs Slope scatter (land only, subsampled for clarity)
    if len(land_elevation) > 10000:
        # Subsample for plotting
        indices = np.random.choice(len(land_elevation), 10000, replace=False)
        plot_elevation = land_elevation[indices]
        plot_slope = land_slope[indices]
    else:
        plot_elevation = land_elevation
        plot_slope = land_slope
    
    scatter = axes[1, 0].scatter(plot_elevation, plot_slope, alpha=0.6, s=1, c=plot_elevation, cmap='terrain')
    axes[1, 0].set_xlabel('Elevation (m)')
    axes[1, 0].set_ylabel('Slope (°)')
    axes[1, 0].set_title('Elevation vs Slope (Land Areas)', fontweight='bold')
    axes[1, 0].grid(True, alpha=0.3)
    plt.colorbar(scatter, ax=axes[1, 0], label='Elevation (m)')
    
    # Statistical summary
    stats_text = f"""Land Terrain Statistics:
    
Total Cells: {land_mask.size:,}
Land Cells: {np.sum(land_mask):,} ({np.sum(land_mask)/land_mask.size*100:.1f}%)
Sea Cells: {np.sum(~land_mask):,} ({np.sum(~land_mask)/land_mask.size*100:.1f}%)

Elevation (Land):
  Min: {np.min(land_elevation):.0f}m
  Max: {np.max(land_elevation):.0f}m
  Mean: {np.mean(land_elevation):.0f}m
  Median: {np.median(land_elevation):.0f}m

Slope (Land):
  Mean: {np.mean(land_slope):.1f}°
  Median: {np.median(land_slope):.1f}°
  Steep (>25°): {np.sum(land_slope > 25):,} ({np.sum(land_slope > 25)/len(land_slope)*100:.1f}%)

Features (Land):
  Barrancos: {feature_counts['Barrancos']:,}
  Depressions: {feature_counts['Depressions']:,}
  Wind Channeling: {feature_counts['Wind Channeling']:,}"""
    
    axes[1, 1].text(0.05, 0.95, stats_text, transform=axes[1, 1].transAxes, 
                   fontsize=10, verticalalignment='top', fontfamily='monospace',
                   bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray", alpha=0.8))
    axes[1, 1].set_title('Statistical Summary', fontweight='bold')
    axes[1, 1].axis('off')
    
    plt.tight_layout()
    plt.savefig(output_path / "feature_analysis.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"✅ Created 3 informative plots:")
    print(f"   📊 land_sea_distribution.png")
    print(f"   🏔️ land_terrain_characteristics.png")
    print(f"   📈 feature_analysis.png")
    
    return output_path

def main():
    """Main function."""
    if len(sys.argv) != 2:
        print("Usage: python create_land_focused_plots.py <preprocessed_terrain_dir>")
        sys.exit(1)
    
    preprocessed_dir = sys.argv[1]
    
    if not Path(preprocessed_dir).exists():
        print(f"❌ Error: Directory not found: {preprocessed_dir}")
        sys.exit(1)
    
    try:
        # Load data
        data = load_terrain_data(preprocessed_dir)
        
        # Create plots
        output_dir = Path(preprocessed_dir) / "validation_plots"
        create_land_focused_plots(data, output_dir)
        
        print(f"🎉 Land-focused validation plots created successfully!")
        
    except Exception as e:
        print(f"❌ Error creating plots: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 