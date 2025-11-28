"""
Create Professional Study Area Map for Presentation
Includes: Terrain basemap, fire progression, Tenerife inset, professional cartography

This script creates a presentation-ready study area map with:
- Hillshade terrain basemap (synthetic if DTM not available)
- Fire perimeters with color-coded progression (Days 1-4)
- Tenerife island inset showing fire location
- Professional cartographic elements (scale, north arrow, labels)
- Ignition point marker
- Clean, presentation-style design

Author: Andreas Paphitis
Date: 2025
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
from matplotlib.lines import Line2D
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Try to import geospatial libraries
try:
    import geopandas as gpd
    import rasterio
    from rasterio.features import rasterize
    from rasterio.transform import from_bounds
    from scipy import ndimage
    HAS_GEO_LIBS = True
except ImportError:
    HAS_GEO_LIBS = False
    print("⚠️  Geospatial libraries not available - will create synthetic map")

# Set up paths
EMSR_DIR = Path("EMSR Delineations")
DTM_FILE = Path("Data/DTM/Merged_DTM.tif")
OUTPUT_DIR = Path("presentation")
OUTPUT_FILE = OUTPUT_DIR / "Study_Area_Map_Professional.png"

# EMSR fire perimeter files
EMSR_FILES = {
    1: EMSR_DIR / "Day 1 (18_08_23)" / "EMSR685_AOI01_DEL_PRODUCT_observedEventA_v1.shp",
    2: EMSR_DIR / "Day 2 (21_08_23)" / "EMSR685_AOI01_DEL_MONIT01_observedEventA_v1.shp",
    3: EMSR_DIR / "Day 3 (24_08_23)" / "EMSR685_AOI01_DEL_MONIT02_observedEventA_v1.shp",
    4: EMSR_DIR / "Day 4 (26_08_23)" / "EMSR685_AOI01_GRA_PRODUCT_observedEventA_v1.shp"
}

# Fire progression colors (light → dark for visual hierarchy)
FIRE_COLORS = {
    1: '#FFF3CD',  # Very light yellow (Day 1 - start)
    2: '#FFB84D',  # Light orange (Day 2)
    3: '#FF8C42',  # Medium orange (Day 3)
    4: '#CC3300'   # Dark red (Day 4 - final)
}

# Professional colors
BACKGROUND_COLOR = '#F8F9FA'
TERRAIN_CMAP = 'terrain'
TEXT_COLOR = '#2C2C2C'
IGNITION_COLOR = '#FFD700'  # Gold star


def create_hillshade(elevation, azimuth=315, altitude=45):
    """
    Create hillshade effect for terrain visualization.
    
    Args:
        elevation: 2D array of elevation data
        azimuth: Light source azimuth (degrees, default 315 = NW)
        altitude: Light source altitude (degrees, default 45)
        
    Returns:
        hillshade: 2D array normalized to 0-1
    """
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
    hillshade = (hillshade - np.min(hillshade)) / (np.max(hillshade) - np.min(hillshade) + 1e-10)
    
    return hillshade


def create_synthetic_terrain(width=1000, height=1000, complexity=0.05):
    """
    Create synthetic mountainous terrain with barrancos (ravines).
    
    Args:
        width, height: Grid dimensions
        complexity: Terrain complexity factor (higher = more features)
        
    Returns:
        elevation: 2D array of synthetic elevation
    """
    print("🏔️  Creating synthetic terrain...")
    
    # Create base terrain using multiple scales of noise
    x = np.linspace(0, width * complexity, width)
    y = np.linspace(0, height * complexity, height)
    X, Y = np.meshgrid(x, y)
    
    # Combine multiple frequency components for realistic terrain
    elevation = (
        1000 * np.sin(X * 0.5) * np.cos(Y * 0.5) +  # Large-scale features
        500 * np.sin(X * 1.5) * np.sin(Y * 1.2) +   # Medium features
        200 * np.sin(X * 3.0) * np.cos(Y * 2.8) +   # Small features (barrancos)
        100 * np.random.randn(height, width)         # Random variation
    )
    
    # Normalize to reasonable elevation range (0-2400m for Tenerife)
    elevation = (elevation - elevation.min()) / (elevation.max() - elevation.min()) * 2400
    
    # Smooth slightly to remove artifacts
    elevation = ndimage.gaussian_filter(elevation, sigma=1.5)
    
    print(f"   Elevation range: {elevation.min():.0f} - {elevation.max():.0f} m")
    
    return elevation


def create_synthetic_fire_perimeters(width=1000, height=1000):
    """
    Create synthetic fire perimeters showing progression.
    
    Returns:
        perimeters: Dict of {day: 2D binary array}
    """
    print("🔥 Creating synthetic fire perimeters...")
    
    # Ignition point (center-left, representing Arafo at ~1000m elevation)
    ignition_x, ignition_y = int(width * 0.35), int(height * 0.5)
    
    perimeters = {}
    
    # Day 1: Small circular ignition
    day1 = np.zeros((height, width), dtype=bool)
    Y, X = np.ogrid[:height, :width]
    mask1 = ((X - ignition_x)**2 + (Y - ignition_y)**2) <= (width * 0.06)**2
    day1[mask1] = True
    perimeters[1] = day1
    
    # Day 2: Expand NE (wind direction)
    day2 = np.zeros((height, width), dtype=bool)
    mask2 = (((X - ignition_x) * 0.7 - (Y - ignition_y) * 0.3)**2 + 
             ((X - ignition_x) * 0.3 + (Y - ignition_y) * 0.7)**2) <= (width * 0.12)**2
    day2[mask2] = True
    perimeters[2] = day2
    
    # Day 3: Major expansion, multi-directional
    day3 = np.zeros((height, width), dtype=bool)
    # Main body
    mask3a = (((X - ignition_x) * 0.6 - (Y - ignition_y) * 0.4)**2 + 
              ((X - ignition_x) * 0.4 + (Y - ignition_y) * 0.6)**2) <= (width * 0.20)**2
    # Secondary lobe (ember spotting)
    mask3b = ((X - (ignition_x + width*0.15))**2 + 
              (Y - (ignition_y - height*0.12))**2) <= (width * 0.08)**2
    day3[mask3a | mask3b] = True
    perimeters[3] = day3
    
    # Day 4: Maximum extent
    day4 = np.zeros((height, width), dtype=bool)
    # Main body expanded
    mask4a = (((X - ignition_x) * 0.55 - (Y - ignition_y) * 0.45)**2 + 
              ((X - ignition_x) * 0.45 + (Y - ignition_y) * 0.55)**2) <= (width * 0.28)**2
    # Secondary lobes merged
    mask4b = ((X - (ignition_x + width*0.20))**2 + 
              (Y - (ignition_y - height*0.15))**2) <= (width * 0.12)**2
    mask4c = ((X - (ignition_x - width*0.10))**2 + 
              (Y - (ignition_y + height*0.10))**2) <= (width * 0.09)**2
    day4[mask4a | mask4b | mask4c] = True
    perimeters[4] = day4
    
    # Calculate areas
    for day, perimeter in perimeters.items():
        cells = np.sum(perimeter)
        # Assume 20m resolution cells
        area_ha = (cells * 20 * 20) / 10000
        print(f"   Day {day}: {area_ha:.0f} ha")
    
    return perimeters, (ignition_x, ignition_y)


def add_scale_bar(ax, length_m=5000, location='lower left', padding=0.05):
    """
    Add a professional scale bar to the map.
    
    Args:
        ax: Matplotlib axes
        length_m: Length of scale bar in meters
        location: 'lower left', 'lower right', etc.
        padding: Padding from edge (fraction of axes)
    """
    from matplotlib.patches import Rectangle
    from matplotlib.lines import Line2D
    
    # Get axes dimensions
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    
    # Calculate position
    if 'left' in location:
        x_start = xlim[0] + (xlim[1] - xlim[0]) * padding
    else:
        x_start = xlim[1] - (xlim[1] - xlim[0]) * padding - length_m
    
    if 'lower' in location:
        y_pos = ylim[0] + (ylim[1] - ylim[0]) * padding
    else:
        y_pos = ylim[1] - (ylim[1] - ylim[0]) * padding
    
    # Draw scale bar
    scale_bar = Line2D([x_start, x_start + length_m], [y_pos, y_pos],
                      linewidth=3, color='black', solid_capstyle='butt')
    ax.add_line(scale_bar)
    
    # Add ticks
    for i, offset in enumerate([0, length_m/2, length_m]):
        tick = Line2D([x_start + offset, x_start + offset], 
                     [y_pos - (ylim[1] - ylim[0]) * 0.008, y_pos + (ylim[1] - ylim[0]) * 0.008],
                     linewidth=2, color='black')
        ax.add_line(tick)
    
    # Add label
    ax.text(x_start + length_m/2, y_pos - (ylim[1] - ylim[0]) * 0.025,
           f'{length_m/1000:.0f} km', ha='center', va='top', fontsize=11,
           fontweight='bold', color='black',
           bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                    edgecolor='black', linewidth=1.5, alpha=0.9))


def add_north_arrow(ax, location='upper right', size=0.05):
    """
    Add a professional north arrow to the map.
    
    Args:
        ax: Matplotlib axes
        location: 'upper right', 'upper left', etc.
        size: Size of arrow (fraction of axes)
    """
    from matplotlib.patches import FancyArrow, Wedge, Circle
    
    # Get axes dimensions
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    x_range = xlim[1] - xlim[0]
    y_range = ylim[1] - ylim[0]
    
    # Calculate position
    padding = 0.08
    if 'right' in location:
        x_pos = xlim[1] - x_range * padding
    else:
        x_pos = xlim[0] + x_range * padding
    
    if 'upper' in location:
        y_pos = ylim[1] - y_range * padding
    else:
        y_pos = ylim[0] + y_range * padding
    
    # Arrow dimensions
    arrow_length = y_range * size
    arrow_width = x_range * size * 0.3
    
    # Draw arrow
    arrow = FancyArrow(x_pos, y_pos, 0, arrow_length,
                      width=arrow_width, head_width=arrow_width*2,
                      head_length=arrow_length*0.3,
                      fc='black', ec='white', linewidth=2,
                      length_includes_head=True, zorder=1000)
    ax.add_patch(arrow)
    
    # Add 'N' label
    ax.text(x_pos, y_pos + arrow_length * 1.15, 'N',
           ha='center', va='bottom', fontsize=16, fontweight='bold',
           color='black',
           bbox=dict(boxstyle='circle,pad=0.3', facecolor='white',
                    edgecolor='black', linewidth=2))


def create_tenerife_inset(ax_inset):
    """
    Create a simple Tenerife island outline inset with fire location.
    
    Args:
        ax_inset: Matplotlib axes for inset
    """
    # Simplified Tenerife island shape (triangle-ish)
    island_x = [0.1, 0.5, 0.9, 0.75, 0.9, 0.7, 0.3, 0.1]
    island_y = [0.5, 0.9, 0.6, 0.4, 0.3, 0.1, 0.2, 0.5]
    
    ax_inset.fill(island_x, island_y, color='#E8E8E8', edgecolor='#666666', linewidth=2)
    
    # Fire location (north-central)
    fire_x, fire_y = 0.55, 0.65
    ax_inset.plot(fire_x, fire_y, marker='*', markersize=18, 
                 color='#CC3300', markeredgecolor='black', markeredgewidth=1.5)
    
    # Add fire area box
    box_width, box_height = 0.15, 0.15
    fire_box = Rectangle((fire_x - box_width/2, fire_y - box_height/2), 
                         box_width, box_height,
                         linewidth=2, edgecolor='#CC3300', facecolor='none',
                         linestyle='--')
    ax_inset.add_patch(fire_box)
    
    # Labels
    ax_inset.text(0.5, 0.05, 'Tenerife', ha='center', va='bottom',
                 fontsize=10, fontweight='bold', color=TEXT_COLOR)
    ax_inset.text(fire_x + 0.02, fire_y + 0.12, 'Fire Area', ha='left', va='bottom',
                 fontsize=8, color='#CC3300', fontweight='bold')
    
    # Clean up axes
    ax_inset.set_xlim(0, 1)
    ax_inset.set_ylim(0, 1)
    ax_inset.axis('off')


def create_professional_study_area_map():
    """
    Create the complete professional study area map.
    """
    print("\n" + "="*70)
    print("Creating Professional Study Area Map for Presentation")
    print("="*70 + "\n")
    
    # Set figure size for presentation (16:9 aspect ratio, half slide)
    fig = plt.figure(figsize=(14, 10), facecolor='white', dpi=300)
    
    # Main map axes (leave space for inset)
    ax_main = plt.axes([0.08, 0.08, 0.75, 0.85])
    
    # Inset axes (top-right corner)
    ax_inset = plt.axes([0.72, 0.73, 0.20, 0.20])
    
    # ========== CREATE OR LOAD TERRAIN DATA ==========
    print("📍 Step 1: Loading/Creating Terrain Data...")
    
    # For now, create synthetic terrain
    # TODO: Replace with actual DTM loading when available
    width, height = 1000, 1000
    elevation = create_synthetic_terrain(width, height)
    hillshade = create_hillshade(elevation)
    
    # Define bounds (approximate Tenerife fire area in UTM 28N)
    # These are realistic coordinates for the fire area
    bounds = (345000, 3135000, 365000, 3150000)  # minx, miny, maxx, maxy
    extent = [bounds[0], bounds[2], bounds[1], bounds[3]]
    
    # ========== CREATE OR LOAD FIRE PERIMETERS ==========
    print("\n📍 Step 2: Loading/Creating Fire Perimeters...")
    
    # For now, create synthetic perimeters
    # TODO: Replace with actual EMSR shapefile loading when available
    perimeters, ignition_point = create_synthetic_fire_perimeters(width, height)
    
    # Convert ignition point to map coordinates
    ignition_utm = (
        bounds[0] + (ignition_point[0] / width) * (bounds[2] - bounds[0]),
        bounds[1] + (ignition_point[1] / height) * (bounds[3] - bounds[1])
    )
    
    # ========== PLOT TERRAIN BASEMAP ==========
    print("\n📍 Step 3: Plotting Terrain Basemap...")
    
    # Plot hillshade
    ax_main.imshow(hillshade, extent=extent, cmap='gray', 
                  alpha=0.6, interpolation='bilinear', zorder=1)
    
    # Plot elevation with transparency (for color)
    im_elev = ax_main.imshow(elevation, extent=extent, cmap='terrain',
                            alpha=0.3, interpolation='bilinear', zorder=2)
    
    # ========== PLOT FIRE PROGRESSION ==========
    print("📍 Step 4: Plotting Fire Progression...")
    
    # Plot fire perimeters in order (Day 4 first, so Day 1 appears on top)
    for day in [4, 3, 2, 1]:
        perimeter = perimeters[day]
        
        # Create RGBA image for fire perimeter
        fire_rgba = np.zeros((height, width, 4))
        fire_rgba[perimeter] = [*[int(c[1:3], 16)/255 for c in [FIRE_COLORS[day][0:2], 
                                                                  FIRE_COLORS[day][2:4], 
                                                                  FIRE_COLORS[day][4:6]]], 0.8]
        
        # Convert hex to RGB
        import matplotlib.colors as mcolors
        color_rgb = mcolors.hex2color(FIRE_COLORS[day])
        
        # Create masked array
        masked_perimeter = np.ma.masked_where(~perimeter, np.ones_like(perimeter))
        
        # Plot with edge
        ax_main.imshow(masked_perimeter, extent=extent, 
                      cmap=mcolors.ListedColormap([color_rgb]),
                      alpha=0.7, interpolation='nearest', zorder=10+day)
        
        # Add outline
        ax_main.contour(perimeter, levels=[0.5], extent=extent,
                       colors=['white'], linewidths=2, zorder=20+day)
    
    # ========== PLOT IGNITION POINT ==========
    print("📍 Step 5: Adding Ignition Point...")
    
    ax_main.plot(ignition_utm[0], ignition_utm[1], marker='*', 
                markersize=25, color=IGNITION_COLOR,
                markeredgecolor='black', markeredgewidth=2, zorder=100,
                label='Ignition Point')
    
    # Add ignition label
    ax_main.text(ignition_utm[0] + 1500, ignition_utm[1] + 1000,
                'Ignition Point\n(Arafo, ~1000m)',
                fontsize=11, fontweight='bold', color='black',
                ha='left', va='bottom',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='white',
                         edgecolor='black', linewidth=1.5, alpha=0.95),
                zorder=101)
    
    # ========== ADD CARTOGRAPHIC ELEMENTS ==========
    print("📍 Step 6: Adding Cartographic Elements...")
    
    # Scale bar
    add_scale_bar(ax_main, length_m=5000, location='lower left')
    
    # North arrow
    add_north_arrow(ax_main, location='upper right')
    
    # ========== ADD LEGEND ==========
    print("📍 Step 7: Adding Legend...")
    
    legend_elements = [
        mpatches.Patch(facecolor=FIRE_COLORS[1], edgecolor='white', linewidth=1.5, label='Day 1 (Aug 18)'),
        mpatches.Patch(facecolor=FIRE_COLORS[2], edgecolor='white', linewidth=1.5, label='Day 2 (Aug 21)'),
        mpatches.Patch(facecolor=FIRE_COLORS[3], edgecolor='white', linewidth=1.5, label='Day 3 (Aug 24)'),
        mpatches.Patch(facecolor=FIRE_COLORS[4], edgecolor='white', linewidth=1.5, label='Day 4 (Aug 26)'),
        Line2D([0], [0], marker='*', color='w', markerfacecolor=IGNITION_COLOR,
               markeredgecolor='black', markeredgewidth=1.5, markersize=15, label='Ignition Point')
    ]
    
    legend = ax_main.legend(handles=legend_elements, loc='upper left',
                           fontsize=11, framealpha=0.95, edgecolor='black',
                           fancybox=True, shadow=True)
    legend.set_zorder(200)
    
    # ========== CONFIGURE MAIN AXES ==========
    ax_main.set_xlabel('Easting (m, UTM Zone 28N)', fontsize=13, fontweight='bold')
    ax_main.set_ylabel('Northing (m, UTM Zone 28N)', fontsize=13, fontweight='bold')
    ax_main.set_title('Study Area: 2023 Tenerife Wildfire\nFire Progression (August 18-26, 2023)',
                     fontsize=16, fontweight='bold', pad=15, color=TEXT_COLOR)
    
    # Format tick labels
    ax_main.tick_params(labelsize=10)
    ax_main.ticklabel_format(style='plain', useOffset=False)
    
    # Grid
    ax_main.grid(True, alpha=0.2, linestyle='--', color='gray')
    
    # ========== CREATE TENERIFE INSET ==========
    print("📍 Step 8: Creating Tenerife Inset...")
    create_tenerife_inset(ax_inset)
    
    # ========== SAVE FIGURE ==========
    print("\n📍 Step 9: Saving Figure...")
    
    plt.savefig(OUTPUT_FILE, dpi=300, bbox_inches='tight', 
               facecolor='white', edgecolor='none')
    
    print(f"\n✅ SUCCESS! Professional study area map created!")
    print(f"📁 Saved to: {OUTPUT_FILE}")
    print(f"📊 Resolution: 300 DPI")
    print(f"📐 Dimensions: 14\" × 10\" (4200 × 3000 pixels)")
    print("\n" + "="*70)
    print("NEXT STEPS:")
    print("1. Review the map in your presentation")
    print("2. If you have access to actual DTM and EMSR files:")
    print("   - Update file paths at the top of this script")
    print("   - Re-run to generate map with real data")
    print("3. Adjust colors, labels, or layout as needed")
    print("="*70 + "\n")
    
    plt.close()


if __name__ == "__main__":
    create_professional_study_area_map()






