#!/usr/bin/env python
"""
Create Academic-Quality 4-Panel Binary Mask Visualization
For Master's Thesis - EMSR Fire Perimeter Data

This script creates a publication-ready 4-panel figure showing the
progression of fire perimeters across 4 observation days.

Author: Andreas Paphitis
Date: 2025-10-13
"""

import numpy as np
import matplotlib.pyplot as plt
import geopandas as gpd
from rasterio.features import rasterize
from rasterio.transform import from_bounds
from pathlib import Path

# Configure matplotlib for academic quality
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans']
plt.rcParams['font.size'] = 10
plt.rcParams['axes.labelsize'] = 10
plt.rcParams['axes.titlesize'] = 11
plt.rcParams['xtick.labelsize'] = 9
plt.rcParams['ytick.labelsize'] = 9
plt.rcParams['legend.fontsize'] = 9

# Set up paths
EMSR_DIR = Path("data/emsr_delineations")
OUTPUT_DIR = Path("results/figures/thesis")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Define the EMSR files for each day
EMSR_FILES = {
    1: EMSR_DIR / "Day 1 (18_08_23)" / "EMSR685_AOI01_DEL_PRODUCT_observedEventA_v1.shp",
    2: EMSR_DIR / "Day 2 (21_08_23)" / "EMSR685_AOI01_DEL_MONIT01_observedEventA_v1.shp",
    3: EMSR_DIR / "Day 3 (24_08_23)" / "EMSR685_AOI01_DEL_MONIT02_observedEventA_v1.shp",
    4: EMSR_DIR / "Day 4 (26_08_23)" / "EMSR685_AOI01_GRA_PRODUCT_observedEventA_v1.shp"
}

# Dates for labeling
DATES = {
    1: "August 18, 2023",
    2: "August 21, 2023",
    3: "August 24, 2023",
    4: "August 26, 2023"
}


def load_and_rasterize_emsr(shapefile_path, resolution=20.0, target_bounds=None):
    """
    Load EMSR shapefile and convert to binary raster mask.
    
    Args:
        shapefile_path: Path to the shapefile
        resolution: Resolution in meters (default 20m)
        target_bounds: Optional bounds (minx, miny, maxx, maxy)
        
    Returns:
        binary_mask: 2D numpy array (1=burned, 0=unburned)
        transform: Rasterio transform
        bounds: Bounds used
        gdf: GeoDataFrame
    """
    print(f"  Loading {shapefile_path.name}...")
    
    # Read shapefile
    gdf = gpd.read_file(str(shapefile_path))
    
    if gdf.empty:
        raise ValueError(f"Empty shapefile: {shapefile_path}")
    
    # Reproject to UTM Zone 28N (EPSG:32628)
    if gdf.crs.to_epsg() != 32628:
        gdf = gdf.to_crs(epsg=32628)
    
    # Get bounds
    bounds = target_bounds if target_bounds else gdf.total_bounds
    
    # Calculate grid dimensions
    width = int((bounds[2] - bounds[0]) / resolution)
    height = int((bounds[3] - bounds[1]) / resolution)
    
    # Create transform
    transform = from_bounds(bounds[0], bounds[1], bounds[2], bounds[3], width, height)
    
    # Rasterize
    shapes = [(geom, 1) for geom in gdf.geometry if geom is not None]
    binary_mask = rasterize(shapes, out_shape=(height, width), 
                           transform=transform, fill=0, dtype=np.uint8)
    
    burned_area_ha = (np.sum(binary_mask) * resolution * resolution) / 10000
    print(f"    Burned area: {burned_area_ha:.1f} ha")
    
    return binary_mask, transform, bounds, gdf


def get_common_bounds():
    """Get common bounds encompassing all 4 days."""
    all_bounds = []
    
    for day, shapefile_path in EMSR_FILES.items():
        if shapefile_path.exists():
            gdf = gpd.read_file(str(shapefile_path))
            if gdf.crs.to_epsg() != 32628:
                gdf = gdf.to_crs(epsg=32628)
            if not gdf.empty:
                all_bounds.append(gdf.total_bounds)
    
    if not all_bounds:
        raise ValueError("No valid shapefiles found")
    
    all_bounds = np.array(all_bounds)
    common_bounds = (
        all_bounds[:, 0].min(),
        all_bounds[:, 1].min(),
        all_bounds[:, 2].max(),
        all_bounds[:, 3].max()
    )
    
    return common_bounds


def create_academic_4panel_figure():
    """
    Create publication-ready 4-panel figure with academic formatting.
    """
    print("\n" + "="*70)
    print("Creating Academic 4-Panel Binary Mask Visualization")
    print("="*70)
    
    # Get common bounds
    print("\nCalculating common spatial bounds...")
    common_bounds = get_common_bounds()
    resolution = 20.0
    
    # Load all masks
    print("\nLoading and processing binary masks:")
    masks = {}
    for day, shapefile_path in EMSR_FILES.items():
        if not shapefile_path.exists():
            print(f"  ⚠️  Warning: Shapefile not found for Day {day}")
            continue
        
        binary_mask, transform, bounds, gdf = load_and_rasterize_emsr(
            shapefile_path, resolution, target_bounds=common_bounds
        )
        
        masks[day] = {
            'mask': binary_mask,
            'transform': transform,
            'bounds': bounds,
            'gdf': gdf
        }
    
    # Create figure with proper spacing
    print("\nGenerating 4-panel figure...")
    fig = plt.figure(figsize=(12, 10))
    
    # Create grid with better spacing
    gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.25,
                          left=0.08, right=0.95, top=0.95, bottom=0.08)
    
    panel_labels = ['(a)', '(b)', '(c)', '(d)']
    
    for idx, day in enumerate([1, 2, 3, 4]):
        ax = fig.add_subplot(gs[idx // 2, idx % 2])
        
        if day not in masks:
            ax.text(0.5, 0.5, f'Day {day}\nData Not Available', 
                   ha='center', va='center', fontsize=12)
            ax.set_title(f'{panel_labels[idx]} Day {day}', 
                        fontsize=11, fontweight='bold', loc='left')
            continue
        
        mask_data = masks[day]
        binary_mask = mask_data['mask']
        bounds = mask_data['bounds']
        
        # Calculate burned area
        burned_cells = np.sum(binary_mask)
        burned_area_ha = (burned_cells * resolution * resolution) / 10000
        
        # Plot with academic colormap (Reds for burned areas)
        # Invert mask so burned=1 shows as red, unburned=0 shows as white
        im = ax.imshow(binary_mask, cmap='Reds', interpolation='nearest',
                      extent=[bounds[0], bounds[2], bounds[1], bounds[3]],
                      vmin=0, vmax=1, alpha=0.9)
        
        # Add panel label and title with date
        title_text = f'{panel_labels[idx]} Day {day} – {DATES[day]}'
        ax.set_title(title_text, fontsize=10, fontweight='bold', 
                    loc='left', pad=8)
        
        # Add burned area as subtitle
        ax.text(0.98, 0.98, f'{burned_area_ha:,.0f} ha', 
               transform=ax.transAxes, fontsize=9,
               verticalalignment='top', horizontalalignment='right',
               bbox=dict(boxstyle='round,pad=0.4', facecolor='white', 
                        edgecolor='gray', linewidth=0.5, alpha=0.9))
        
        # Axis labels
        ax.set_xlabel('Easting (m)', fontsize=9)
        ax.set_ylabel('Northing (m)', fontsize=9)
        
        # Subtle grid
        ax.grid(True, alpha=0.15, linestyle='-', linewidth=0.5, color='gray')
        
        # Format tick labels
        ax.ticklabel_format(style='plain', axis='both')
        
        # Add colorbar to rightmost panels only
        if idx % 2 == 1:  # Right column
            cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
            cbar.set_label('Burned', fontsize=9, rotation=270, labelpad=15)
            cbar.set_ticks([0, 1])
            cbar.set_ticklabels(['No', 'Yes'])
            cbar.ax.tick_params(labelsize=8)
    
    # Add overall title (concise and professional)
    fig.suptitle('Fire Perimeter Progression – Tenerife Wildfire', 
                fontsize=12, fontweight='bold', y=0.98)
    
    # Save as both PNG and PDF
    print("\nSaving figures...")
    
    # High-resolution PNG
    png_file = OUTPUT_DIR / "EMSR_Binary_Masks_4Panel_Academic.png"
    plt.savefig(png_file, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"  [OK] Saved PNG: {png_file}")
    
    # Vector PDF for publication
    pdf_file = OUTPUT_DIR / "EMSR_Binary_Masks_4Panel_Academic.pdf"
    plt.savefig(pdf_file, format='pdf', bbox_inches='tight', facecolor='white')
    print(f"  [OK] Saved PDF: {pdf_file}")
    
    plt.close()
    
    print("\n" + "="*70)
    print("[SUCCESS] Academic figure created successfully!")
    print("="*70)
    print(f"\nOutput files:")
    print(f"  - {png_file.name} (for digital viewing)")
    print(f"  - {pdf_file.name} (for publication/printing)")
    print("\nThis figure is now ready for your thesis methodology section.")
    print("="*70 + "\n")


if __name__ == "__main__":
    create_academic_4panel_figure()

