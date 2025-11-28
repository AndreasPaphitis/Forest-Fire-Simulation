#!/usr/bin/env python
"""
Create Binary Mask Visualizations from EMSR Fire Perimeter Polygons

This script loads the EMSR shapefile polygons for Days 1-4 and creates:
1. Individual binary mask visualizations for each day
2. A combined 4-panel figure showing all days
3. Saves the binary masks as PNG files for methodology section

Author: Andreas Paphitis
Date: 2025-10-12
"""

import numpy as np
import matplotlib.pyplot as plt
import geopandas as gpd
from rasterio.features import rasterize
from rasterio.transform import from_bounds
from pathlib import Path
from matplotlib.patches import Rectangle
import matplotlib.patches as mpatches

# Set up paths
EMSR_DIR = Path("EMSR Delineations")
OUTPUT_DIR = Path("Academic_Thesis_Charts")
OUTPUT_DIR.mkdir(exist_ok=True)

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
        resolution: Resolution in meters (default 20m to match simulation)
        target_bounds: Optional bounds to use (minx, miny, maxx, maxy)
        
    Returns:
        binary_mask: 2D numpy array (1=burned, 0=unburned)
        transform: Rasterio transform
        bounds: Bounds used for rasterization
        gdf: GeoDataFrame with the polygon data
    """
    print(f"Loading {shapefile_path.name}...")
    
    # Read shapefile
    gdf = gpd.read_file(str(shapefile_path))
    
    if gdf.empty:
        raise ValueError(f"Empty shapefile: {shapefile_path}")
    
    # Reproject to UTM Zone 28N (EPSG:32628) if needed
    if gdf.crs.to_epsg() != 32628:
        print(f"  Reprojecting from {gdf.crs} to EPSG:32628 (UTM Zone 28N)")
        gdf = gdf.to_crs(epsg=32628)
    
    # Get bounds
    if target_bounds is None:
        bounds = gdf.total_bounds
    else:
        bounds = target_bounds
    
    # Calculate grid dimensions
    width = int((bounds[2] - bounds[0]) / resolution)
    height = int((bounds[3] - bounds[1]) / resolution)
    
    print(f"  Grid size: {width} x {height} cells at {resolution}m resolution")
    
    # Create transform
    transform = from_bounds(bounds[0], bounds[1], bounds[2], bounds[3], width, height)
    
    # Rasterize the geometries (all features = 1, background = 0)
    shapes = [(geom, 1) for geom in gdf.geometry if geom is not None]
    binary_mask = rasterize(shapes, out_shape=(height, width), transform=transform, fill=0, dtype=np.uint8)
    
    burned_area_cells = np.sum(binary_mask)
    burned_area_ha = (burned_area_cells * resolution * resolution) / 10000
    
    print(f"  Burned cells: {burned_area_cells:,}")
    print(f"  Burned area: {burned_area_ha:.1f} ha")
    
    return binary_mask, transform, bounds, gdf


def get_common_bounds():
    """Get common bounds that encompass all 4 days."""
    all_bounds = []
    
    for day, shapefile_path in EMSR_FILES.items():
        if shapefile_path.exists():
            gdf = gpd.read_file(str(shapefile_path))
            # Reproject to UTM Zone 28N
            if gdf.crs.to_epsg() != 32628:
                gdf = gdf.to_crs(epsg=32628)
            if not gdf.empty:
                all_bounds.append(gdf.total_bounds)
    
    if not all_bounds:
        raise ValueError("No valid shapefiles found")
    
    # Get the union of all bounds
    all_bounds = np.array(all_bounds)
    common_bounds = (
        all_bounds[:, 0].min(),  # minx
        all_bounds[:, 1].min(),  # miny
        all_bounds[:, 2].max(),  # maxx
        all_bounds[:, 3].max()   # maxy
    )
    
    print(f"\nCommon bounds: {common_bounds}")
    return common_bounds


def create_individual_mask_visualizations(resolution=20.0):
    """Create individual binary mask visualizations for each day."""
    print("\n" + "="*60)
    print("Creating Individual Binary Mask Visualizations")
    print("="*60)
    
    # Get common bounds for consistent visualization
    common_bounds = get_common_bounds()
    
    masks = {}
    
    for day, shapefile_path in EMSR_FILES.items():
        if not shapefile_path.exists():
            print(f"⚠️  Warning: Shapefile not found for Day {day}")
            continue
        
        # Load and rasterize
        binary_mask, transform, bounds, gdf = load_and_rasterize_emsr(
            shapefile_path, resolution, target_bounds=common_bounds
        )
        
        masks[day] = {
            'mask': binary_mask,
            'transform': transform,
            'bounds': bounds,
            'gdf': gdf
        }
        
        # Create individual visualization
        fig, ax = plt.subplots(figsize=(10, 10))
        
        # Plot binary mask
        im = ax.imshow(binary_mask, cmap='RdYlBu_r', interpolation='nearest',
                      extent=[bounds[0], bounds[2], bounds[1], bounds[3]])
        
        # Add colorbar
        cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label('Binary Mask (1=Burned, 0=Unburned)', fontsize=12)
        
        # Add title and labels
        ax.set_title(f'Day {day} Fire Perimeter Binary Mask\n{DATES[day]}', 
                    fontsize=14, fontweight='bold', pad=20)
        ax.set_xlabel('Easting (m, UTM Zone 28N)', fontsize=12)
        ax.set_ylabel('Northing (m, UTM Zone 28N)', fontsize=12)
        
        # Add grid
        ax.grid(True, alpha=0.3, linestyle='--')
        
        # Add statistics text
        burned_cells = np.sum(binary_mask)
        burned_area_ha = (burned_cells * resolution * resolution) / 10000
        total_cells = binary_mask.size
        
        stats_text = f'Burned Area: {burned_area_ha:.1f} ha\n'
        stats_text += f'Burned Cells: {burned_cells:,}\n'
        stats_text += f'Grid Size: {binary_mask.shape[1]} × {binary_mask.shape[0]}\n'
        stats_text += f'Resolution: {resolution}m'
        
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
               fontsize=10, verticalalignment='top',
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        plt.tight_layout()
        
        # Save figure
        output_file = OUTPUT_DIR / f"EMSR_Day{day}_Binary_Mask.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"[OK] Saved: {output_file}")
        
        plt.close()
    
    return masks


def create_combined_4panel_visualization(masks, resolution=20.0):
    """Create a combined 4-panel visualization of all days."""
    print("\n" + "="*60)
    print("Creating Combined 4-Panel Visualization")
    print("="*60)
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 14))
    axes = axes.flatten()
    
    for idx, day in enumerate([1, 2, 3, 4]):
        ax = axes[idx]
        
        if day not in masks:
            ax.text(0.5, 0.5, f'Day {day}\nData Not Available', 
                   ha='center', va='center', fontsize=14)
            ax.set_title(f'Day {day} - {DATES[day]}', fontsize=12, fontweight='bold')
            continue
        
        mask_data = masks[day]
        binary_mask = mask_data['mask']
        bounds = mask_data['bounds']
        
        # Plot binary mask
        im = ax.imshow(binary_mask, cmap='RdYlBu_r', interpolation='nearest',
                      extent=[bounds[0], bounds[2], bounds[1], bounds[3]])
        
        # Add title
        burned_cells = np.sum(binary_mask)
        burned_area_ha = (burned_cells * resolution * resolution) / 10000
        
        title = f'Day {day} - {DATES[day]}\n'
        title += f'Burned Area: {burned_area_ha:.1f} ha'
        ax.set_title(title, fontsize=11, fontweight='bold', pad=10)
        
        # Add labels
        ax.set_xlabel('Easting (m)', fontsize=10)
        ax.set_ylabel('Northing (m)', fontsize=10)
        
        # Add grid
        ax.grid(True, alpha=0.3, linestyle='--')
        
        # Add colorbar to each subplot
        cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label('Burned', fontsize=9)
    
    # Add main title
    fig.suptitle('EMSR Fire Perimeter Binary Masks - Tenerife Wildfire 2023\n' +
                'Progression of Burned Areas (20m Resolution)', 
                fontsize=14, fontweight='bold', y=0.995)
    
    plt.tight_layout(rect=[0, 0, 1, 0.99])
    
    # Save figure
    output_file = OUTPUT_DIR / "EMSR_Binary_Masks_4Panel_Comparison.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"[OK] Saved: {output_file}")
    
    plt.close()


def create_progressive_overlay_visualization(masks, resolution=20.0):
    """Create a visualization showing progressive fire growth."""
    print("\n" + "="*60)
    print("Creating Progressive Overlay Visualization")
    print("="*60)
    
    fig, ax = plt.subplots(figsize=(12, 12))
    
    # Define colors for each day
    colors = {
        1: '#fee5d9',  # Light red
        2: '#fcae91',  # Medium red
        3: '#fb6a4a',  # Dark red
        4: '#cb181d'   # Very dark red
    }
    
    # Get bounds from Day 4 (largest extent)
    if 4 in masks:
        bounds = masks[4]['bounds']
    else:
        bounds = masks[max(masks.keys())]['bounds']
    
    # Create composite image
    composite = np.zeros(masks[1]['mask'].shape + (3,))
    
    # Plot each day's mask with different colors
    for day in [1, 2, 3, 4]:
        if day not in masks:
            continue
        
        mask = masks[day]['mask']
        color_rgb = plt.cm.colors.hex2color(colors[day])
        
        # Add this day's burned area to composite
        for i in range(3):
            composite[:, :, i] = np.where(mask == 1, color_rgb[i], composite[:, :, i])
    
    # Plot composite
    ax.imshow(composite, extent=[bounds[0], bounds[2], bounds[1], bounds[3]])
    
    # Create legend
    legend_elements = []
    for day in [1, 2, 3, 4]:
        if day in masks:
            burned_cells = np.sum(masks[day]['mask'])
            burned_area_ha = (burned_cells * resolution * resolution) / 10000
            legend_elements.append(
                mpatches.Patch(color=colors[day], 
                             label=f'Day {day} ({DATES[day]}): {burned_area_ha:.1f} ha')
            )
    
    ax.legend(handles=legend_elements, loc='upper right', fontsize=10,
             framealpha=0.9)
    
    # Add title and labels
    ax.set_title('Progressive Fire Growth - EMSR Binary Masks\nTenerife Wildfire 2023', 
                fontsize=14, fontweight='bold', pad=20)
    ax.set_xlabel('Easting (m, UTM Zone 28N)', fontsize=12)
    ax.set_ylabel('Northing (m, UTM Zone 28N)', fontsize=12)
    ax.grid(True, alpha=0.3, linestyle='--')
    
    plt.tight_layout()
    
    # Save figure
    output_file = OUTPUT_DIR / "EMSR_Binary_Masks_Progressive_Overlay.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"[OK] Saved: {output_file}")
    
    plt.close()


def save_binary_masks_as_arrays(masks, resolution=20.0):
    """Save binary masks as numpy arrays for use in simulations."""
    print("\n" + "="*60)
    print("Saving Binary Masks as NumPy Arrays")
    print("="*60)
    
    output_dir = Path("02_processed_data/fire_targets")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for day, mask_data in masks.items():
        binary_mask = mask_data['mask']
        
        # Save as .npy file
        output_file = output_dir / f"emsr_day{day}_binary_mask_20m.npy"
        np.save(output_file, binary_mask)
        print(f"[OK] Saved binary mask: {output_file}")
        
        # Save metadata as JSON
        import json
        metadata = {
            'day': day,
            'date': DATES[day],
            'resolution_m': resolution,
            'grid_shape': binary_mask.shape,
            'burned_cells': int(np.sum(binary_mask)),
            'burned_area_ha': float((np.sum(binary_mask) * resolution * resolution) / 10000),
            'bounds': list(mask_data['bounds']),
            'crs': 'EPSG:32628'
        }
        
        metadata_file = output_dir / f"emsr_day{day}_binary_mask_20m_metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        print(f"[OK] Saved metadata: {metadata_file}")


def main():
    """Main function to create all visualizations."""
    print("\n" + "="*60)
    print("EMSR Binary Mask Visualization Generator")
    print("="*60)
    print("\nThis script will create:")
    print("  1. Individual binary mask visualizations (4 files)")
    print("  2. Combined 4-panel comparison")
    print("  3. Progressive overlay visualization")
    print("  4. NumPy arrays for simulation use")
    print("\n" + "="*60 + "\n")
    
    # Set resolution (20m to match simulation)
    resolution = 20.0
    
    # Create individual visualizations
    masks = create_individual_mask_visualizations(resolution)
    
    # Create combined 4-panel visualization
    create_combined_4panel_visualization(masks, resolution)
    
    # Create progressive overlay
    create_progressive_overlay_visualization(masks, resolution)
    
    # Save binary masks as arrays
    save_binary_masks_as_arrays(masks, resolution)
    
    print("\n" + "="*60)
    print("[SUCCESS] All visualizations created successfully!")
    print("="*60)
    print(f"\nOutput files saved to:")
    print(f"  - Figures: {OUTPUT_DIR.absolute()}")
    print(f"  - Arrays: 02_processed_data/fire_targets/")
    print("\nYou can now use these binary mask visualizations in your methodology section.")


if __name__ == "__main__":
    main()

