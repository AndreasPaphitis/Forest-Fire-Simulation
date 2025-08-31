#!/usr/bin/env python3
"""
Day 4 Fire Area Terrain Visualization
====================================

Creates comprehensive visualizations of the corrected Day 4 fire area terrain data,
showing elevation, slope, barranco detection, and wind channeling effects.

Author: Forest Fire Simulation Team
Date: 2025
"""

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import json
import warnings
warnings.filterwarnings('ignore')

# Set style
plt.style.use('default')
sns.set_palette("husl")

def load_terrain_data():
    """Load the corrected Day 4 fire area terrain data."""
    
    print("📁 Loading Day 4 fire area terrain data...")
    
    terrain_dir = Path("preprocessed_terrain")
    
    # Load metadata
    with open(terrain_dir / "metadata.json", 'r') as f:
        metadata = json.load(f)
    
    # Load terrain arrays
    data = {}
    arrays_to_load = [
        'elevation', 'slope', 'aspect', 'barranco_mask', 
        'barranco_directions', 'depression_mask', 'wind_channeling_mask',
        'wind_amplification', 'wind_direction_modification'
    ]
    
    for array_name in arrays_to_load:
        file_path = terrain_dir / f"{array_name}.npy"
        if file_path.exists():
            data[array_name] = np.load(file_path)
            print(f"✅ Loaded {array_name}: {data[array_name].shape}")
        else:
            print(f"❌ Missing {array_name}.npy")
    
    data['metadata'] = metadata
    return data

def create_comprehensive_visualization(data):
    """Create a comprehensive 9-panel visualization of the Day 4 fire area terrain."""
    
    print("🎨 Creating comprehensive Day 4 fire area terrain visualization...")
    
    # Create figure with 3x3 subplots
    fig, axes = plt.subplots(3, 3, figsize=(20, 16))
    fig.suptitle('Day 4 Fire Area Terrain Analysis (Corrected Subset)', fontsize=20, fontweight='bold')
    
    # Panel A: Elevation Map
    ax1 = axes[0, 0]
    elevation = data['elevation']
    im1 = ax1.imshow(elevation, cmap='terrain', aspect='auto')
    plt.colorbar(im1, ax=ax1, label='Elevation (m)')
    ax1.set_title('A) Elevation Distribution', fontsize=14, fontweight='bold')
    ax1.set_xlabel('X (cells)')
    ax1.set_ylabel('Y (cells)')
    
    # Add elevation statistics
    elevation_stats = f"Range: {np.min(elevation):.0f} - {np.max(elevation):.0f}m\nMean: {np.mean(elevation):.0f}m"
    ax1.text(0.02, 0.98, elevation_stats, transform=ax1.transAxes, fontsize=10, 
             verticalalignment='top', bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))
    
    # Panel B: Slope Distribution
    ax2 = axes[0, 1]
    slope = data['slope']
    im2 = ax2.imshow(slope, cmap='RdYlBu_r', aspect='auto')
    plt.colorbar(im2, ax=ax2, label='Slope (°)')
    ax2.set_title('B) Slope Distribution', fontsize=14, fontweight='bold')
    ax2.set_xlabel('X (cells)')
    ax2.set_ylabel('Y (cells)')
    
    # Add slope statistics
    steep_slopes = np.sum(slope >= 25)
    slope_stats = f"Mean: {np.mean(slope):.1f}°\nSteep (>25°): {steep_slopes:,} cells"
    ax2.text(0.02, 0.98, slope_stats, transform=ax2.transAxes, fontsize=10, 
             verticalalignment='top', bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))
    
    # Panel C: Aspect Distribution
    ax3 = axes[0, 2]
    aspect = data['aspect']
    im3 = ax3.imshow(aspect, cmap='hsv', aspect='auto')
    plt.colorbar(im3, ax=ax3, label='Aspect (°)')
    ax3.set_title('C) Aspect Distribution', fontsize=14, fontweight='bold')
    ax3.set_xlabel('X (cells)')
    ax3.set_ylabel('Y (cells)')
    
    # Panel D: Barranco Detection
    ax4 = axes[1, 0]
    barranco_mask = data['barranco_mask']
    # Create overlay with elevation background
    elevation_normalized = (elevation - np.min(elevation)) / (np.max(elevation) - np.min(elevation))
    ax4.imshow(elevation_normalized, cmap='gray', alpha=0.7, aspect='auto')
    ax4.imshow(barranco_mask, cmap='Reds', alpha=0.8, aspect='auto')
    ax4.set_title('D) Barranco Detection', fontsize=14, fontweight='bold')
    ax4.set_xlabel('X (cells)')
    ax4.set_ylabel('Y (cells)')
    
    # Add barranco statistics
    barranco_count = np.sum(barranco_mask)
    barranco_coverage = barranco_count / barranco_mask.size * 100
    barranco_stats = f"Barrancos: {barranco_count:,} cells\nCoverage: {barranco_coverage:.3f}%"
    ax4.text(0.02, 0.98, barranco_stats, transform=ax4.transAxes, fontsize=10, 
             verticalalignment='top', bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))
    
    # Panel E: Depression Detection
    ax5 = axes[1, 1]
    depression_mask = data['depression_mask']
    # Create overlay with elevation background
    ax5.imshow(elevation_normalized, cmap='gray', alpha=0.7, aspect='auto')
    ax5.imshow(depression_mask, cmap='Blues', alpha=0.6, aspect='auto')
    ax5.set_title('E) Depression Detection', fontsize=14, fontweight='bold')
    ax5.set_xlabel('X (cells)')
    ax5.set_ylabel('Y (cells)')
    
    # Add depression statistics
    depression_count = np.sum(depression_mask)
    depression_coverage = depression_count / depression_mask.size * 100
    depression_stats = f"Depressions: {depression_count:,} cells\nCoverage: {depression_coverage:.1f}%"
    ax5.text(0.02, 0.98, depression_stats, transform=ax5.transAxes, fontsize=10, 
             verticalalignment='top', bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))
    
    # Panel F: Wind Channeling Effects
    ax6 = axes[1, 2]
    wind_channeling_mask = data['wind_channeling_mask']
    wind_amplification = data['wind_amplification']
    # Create overlay with elevation background
    ax6.imshow(elevation_normalized, cmap='gray', alpha=0.7, aspect='auto')
    ax6.imshow(wind_channeling_mask, cmap='Oranges', alpha=0.8, aspect='auto')
    ax6.set_title('F) Wind Channeling Effects', fontsize=14, fontweight='bold')
    ax6.set_xlabel('X (cells)')
    ax6.set_ylabel('Y (cells)')
    
    # Add wind channeling statistics
    wind_count = np.sum(wind_channeling_mask)
    wind_coverage = wind_count / wind_channeling_mask.size * 100
    wind_stats = f"Wind channels: {wind_count:,} cells\nCoverage: {wind_coverage:.3f}%"
    ax6.text(0.02, 0.98, wind_stats, transform=ax6.transAxes, fontsize=10, 
             verticalalignment='top', bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))
    
    # Panel G: Wind Amplification Distribution
    ax7 = axes[2, 0]
    # Only show wind amplification where it's > 1.0
    wind_amp_display = wind_amplification.copy()
    wind_amp_display[wind_amp_display <= 1.0] = np.nan
    im7 = ax7.imshow(wind_amp_display, cmap='Reds', aspect='auto', vmin=1.0, vmax=2.5)
    plt.colorbar(im7, ax=ax7, label='Wind Amplification Factor')
    ax7.set_title('G) Wind Amplification Factors', fontsize=14, fontweight='bold')
    ax7.set_xlabel('X (cells)')
    ax7.set_ylabel('Y (cells)')
    
    # Add wind amplification statistics
    max_amp = np.nanmax(wind_amp_display)
    mean_amp = np.nanmean(wind_amp_display)
    amp_stats = f"Max: {max_amp:.2f}x\nMean: {mean_amp:.2f}x"
    ax7.text(0.02, 0.98, amp_stats, transform=ax7.transAxes, fontsize=10, 
             verticalalignment='top', bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))
    
    # Panel H: Barranco Directions
    ax8 = axes[2, 1]
    barranco_directions = data['barranco_directions']
    # Only show directions where barrancos exist
    directions_display = barranco_directions.copy()
    directions_display[~barranco_mask] = np.nan
    im8 = ax8.imshow(directions_display, cmap='hsv', aspect='auto')
    plt.colorbar(im8, ax=ax8, label='Flow Direction (°)')
    ax8.set_title('H) Barranco Flow Directions', fontsize=14, fontweight='bold')
    ax8.set_xlabel('X (cells)')
    ax8.set_ylabel('Y (cells)')
    
    # Panel I: Terrain Statistics Summary
    ax9 = axes[2, 2]
    ax9.axis('off')
    
    # Calculate statistics
    grid_size = data['metadata']['grid_size']
    resolution = data['metadata']['resolution']
    fire_bounds = data['metadata']['fire_area_bounds']
    buffered_bounds = data['metadata']['buffered_bounds']
    
    # Calculate areas
    fire_width = fire_bounds[2] - fire_bounds[0]
    fire_height = fire_bounds[3] - fire_bounds[1]
    fire_area_km2 = fire_width * fire_height / 1e6
    
    buffered_width = buffered_bounds[2] - buffered_bounds[0]
    buffered_height = buffered_bounds[3] - buffered_bounds[1]
    buffered_area_km2 = buffered_width * buffered_height / 1e6
    
    grid_area_km2 = grid_size[0] * grid_size[1] * resolution * resolution / 1e6
    
    # Create summary text
    summary_text = [
        "DAY 4 FIRE AREA TERRAIN SUMMARY",
        "",
        f"Grid Size: {grid_size[0]}×{grid_size[1]} cells",
        f"Resolution: {resolution}m",
        f"Grid Area: {grid_area_km2:.1f} km²",
        "",
        f"Fire Area: {fire_area_km2:.1f} km²",
        f"Buffered Area: {buffered_area_km2:.1f} km²",
        "",
        f"Elevation Range: {np.min(elevation):.0f} - {np.max(elevation):.0f}m",
        f"Mean Slope: {np.mean(slope):.1f}°",
        f"Steep Slopes (>25°): {steep_slopes:,} cells",
        "",
        f"Barrancos: {barranco_count:,} cells ({barranco_coverage:.3f}%)",
        f"Depressions: {depression_count:,} cells ({depression_coverage:.1f}%)",
        f"Wind Channels: {wind_count:,} cells ({wind_coverage:.3f}%)",
        "",
        f"Max Wind Amplification: {max_amp:.2f}x",
        f"Mean Wind Amplification: {mean_amp:.2f}x"
    ]
    
    # Display summary
    for i, text in enumerate(summary_text):
        y_pos = 0.95 - i * 0.045
        color = 'red' if 'DAY 4' in text else 'black'
        fontweight = 'bold' if 'DAY 4' in text else 'normal'
        ax9.text(0.5, y_pos, text, ha='center', va='center', fontsize=10, 
                color=color, fontweight=fontweight, transform=ax9.transAxes)
    
    ax9.set_title('I) Terrain Statistics Summary', fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    return fig

def create_elevation_profile_visualization(data):
    """Create elevation profile and slope distribution visualizations."""
    
    print("📊 Creating elevation profile visualizations...")
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Day 4 Fire Area - Elevation and Slope Analysis', fontsize=18, fontweight='bold')
    
    elevation = data['elevation']
    slope = data['slope']
    
    # Panel A: Elevation Histogram
    ax1 = axes[0, 0]
    ax1.hist(elevation.flatten(), bins=50, alpha=0.7, color='skyblue', edgecolor='black')
    ax1.set_xlabel('Elevation (m)')
    ax1.set_ylabel('Frequency')
    ax1.set_title('A) Elevation Distribution', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    
    # Add statistics
    elevation_stats = f"Mean: {np.mean(elevation):.0f}m\nStd: {np.std(elevation):.0f}m\nMin: {np.min(elevation):.0f}m\nMax: {np.max(elevation):.0f}m"
    ax1.text(0.02, 0.98, elevation_stats, transform=ax1.transAxes, fontsize=10, 
             verticalalignment='top', bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))
    
    # Panel B: Slope Histogram
    ax2 = axes[0, 1]
    ax2.hist(slope.flatten(), bins=50, alpha=0.7, color='lightcoral', edgecolor='black')
    ax2.set_xlabel('Slope (°)')
    ax2.set_ylabel('Frequency')
    ax2.set_title('B) Slope Distribution', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    
    # Add statistics
    steep_slopes = np.sum(slope >= 25)
    slope_stats = f"Mean: {np.mean(slope):.1f}°\nStd: {np.std(slope):.1f}°\nSteep (>25°): {steep_slopes:,} cells"
    ax2.text(0.02, 0.98, slope_stats, transform=ax2.transAxes, fontsize=10, 
             verticalalignment='top', bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))
    
    # Panel C: Elevation vs Slope Scatter
    ax3 = axes[1, 0]
    # Sample data for scatter plot (too many points otherwise)
    sample_size = min(10000, elevation.size)
    indices = np.random.choice(elevation.size, sample_size, replace=False)
    sample_elevation = elevation.flatten()[indices]
    sample_slope = slope.flatten()[indices]
    
    scatter = ax3.scatter(sample_elevation, sample_slope, alpha=0.6, s=1, c=sample_elevation, cmap='terrain')
    ax3.set_xlabel('Elevation (m)')
    ax3.set_ylabel('Slope (°)')
    ax3.set_title('C) Elevation vs Slope Relationship', fontsize=14, fontweight='bold')
    ax3.grid(True, alpha=0.3)
    plt.colorbar(scatter, ax=ax3, label='Elevation (m)')
    
    # Panel D: Terrain Feature Summary
    ax4 = axes[1, 1]
    ax4.axis('off')
    
    # Calculate feature statistics
    barranco_mask = data['barranco_mask']
    depression_mask = data['depression_mask']
    wind_channeling_mask = data['wind_channeling_mask']
    
    barranco_count = np.sum(barranco_mask)
    depression_count = np.sum(depression_mask)
    wind_count = np.sum(wind_channeling_mask)
    
    total_cells = elevation.size
    
    # Create feature summary
    features = ['Barrancos', 'Depressions', 'Wind Channels', 'Steep Slopes']
    counts = [barranco_count, depression_count, wind_count, steep_slopes]
    percentages = [count/total_cells*100 for count in counts]
    
    # Create bar chart
    bars = ax4.bar(features, percentages, color=['red', 'blue', 'orange', 'green'], alpha=0.7)
    ax4.set_ylabel('Coverage (%)')
    ax4.set_title('D) Terrain Feature Coverage', fontsize=14, fontweight='bold')
    ax4.grid(True, alpha=0.3, axis='y')
    
    # Add value labels on bars
    for bar, count, pct in zip(bars, counts, percentages):
        height = bar.get_height()
        ax4.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                f'{count:,}\n({pct:.3f}%)', ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    return fig

def save_visualizations():
    """Save all visualizations."""
    
    print("🎨 Creating Day 4 fire area terrain visualizations...")
    
    # Load data
    data = load_terrain_data()
    
    # Create comprehensive visualization
    fig1 = create_comprehensive_visualization(data)
    fig1.savefig("Day4_Fire_Area_Terrain_Comprehensive.png", dpi=300, bbox_inches='tight', facecolor='white')
    fig1.savefig("Day4_Fire_Area_Terrain_Comprehensive.pdf", bbox_inches='tight', facecolor='white')
    plt.close(fig1)
    print("✅ Saved comprehensive terrain visualization")
    
    # Create elevation profile visualization
    fig2 = create_elevation_profile_visualization(data)
    fig2.savefig("Day4_Fire_Area_Elevation_Analysis.png", dpi=300, bbox_inches='tight', facecolor='white')
    fig2.savefig("Day4_Fire_Area_Elevation_Analysis.pdf", bbox_inches='tight', facecolor='white')
    plt.close(fig2)
    print("✅ Saved elevation analysis visualization")
    
    # Print summary statistics
    print(f"\n📊 DAY 4 FIRE AREA TERRAIN SUMMARY:")
    print(f"Grid size: {data['metadata']['grid_size'][0]}×{data['metadata']['grid_size'][1]} cells")
    print(f"Resolution: {data['metadata']['resolution']}m")
    print(f"Elevation range: {np.min(data['elevation']):.0f} - {np.max(data['elevation']):.0f}m")
    print(f"Mean slope: {np.mean(data['slope']):.1f}°")
    print(f"Barrancos: {np.sum(data['barranco_mask']):,} cells")
    print(f"Depressions: {np.sum(data['depression_mask']):,} cells")
    print(f"Wind channels: {np.sum(data['wind_channeling_mask']):,} cells")
    
    print(f"\n✅ Visualizations saved:")
    print(f"   - Day4_Fire_Area_Terrain_Comprehensive.png/pdf")
    print(f"   - Day4_Fire_Area_Elevation_Analysis.png/pdf")

if __name__ == "__main__":
    save_visualizations()
