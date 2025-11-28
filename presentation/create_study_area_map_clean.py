"""
Create CLEAN Professional Study Area Map for Presentation
WHITE BACKGROUND VERSION - Presentation-Ready

This creates a simple, clean map focusing on:
- White background (presentation-friendly)
- Fire progression indicators (without fake terrain)
- Professional cartographic elements
- Tenerife geographic context
- Clean, minimalist design

Author: Andreas Paphitis
Date: 2025
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Rectangle, Circle, Wedge, FancyBboxPatch
from matplotlib.lines import Line2D
from pathlib import Path

# Set up paths
OUTPUT_DIR = Path("presentation")
OUTPUT_FILE = OUTPUT_DIR / "Study_Area_Map_Clean.png"

# Professional color palette
COLORS = {
    'background': '#FFFFFF',      # White
    'land': '#F5F5F5',           # Very light gray
    'fire_day1': '#FFF4E6',      # Pale yellow
    'fire_day2': '#FFB84D',      # Light orange
    'fire_day3': '#FF7F50',      # Coral
    'fire_day4': '#DC143C',      # Crimson
    'ignition': '#FFD700',       # Gold
    'text': '#2C2C2C',           # Dark gray
    'grid': '#DDDDDD',           # Light gray
    'border': '#666666'          # Medium gray
}

def create_tenerife_context_inset(ax_inset):
    """Create simple Tenerife island outline with fire location."""
    # Simplified Tenerife shape
    island_x = np.array([0.1, 0.35, 0.5, 0.7, 0.9, 0.85, 0.9, 0.75, 0.5, 0.3, 0.15, 0.1])
    island_y = np.array([0.5, 0.7, 0.9, 0.85, 0.6, 0.5, 0.3, 0.15, 0.2, 0.25, 0.4, 0.5])
    
    ax_inset.fill(island_x, island_y, color=COLORS['land'], 
                 edgecolor=COLORS['border'], linewidth=2.5)
    
    # Fire location (north-central Tenerife)
    fire_x, fire_y = 0.58, 0.70
    
    # Fire area indicator
    fire_circle = Circle((fire_x, fire_y), 0.08, 
                        facecolor=COLORS['fire_day4'], 
                        edgecolor='black', linewidth=2, alpha=0.9, zorder=10)
    ax_inset.add_patch(fire_circle)
    
    # Ignition point
    ax_inset.plot(fire_x, fire_y, marker='*', markersize=16, 
                 color=COLORS['ignition'], markeredgecolor='black', 
                 markeredgewidth=1.5, zorder=11)
    
    # Labels
    ax_inset.text(0.5, 0.05, 'Tenerife, Canary Islands', 
                 ha='center', va='bottom', fontsize=10, 
                 fontweight='bold', color=COLORS['text'])
    
    ax_inset.text(fire_x + 0.12, fire_y, 'Fire\nArea', 
                 ha='left', va='center', fontsize=8, 
                 fontweight='bold', color=COLORS['fire_day4'])
    
    # Clean up
    ax_inset.set_xlim(0, 1)
    ax_inset.set_ylim(0, 1)
    ax_inset.set_aspect('equal')
    ax_inset.axis('off')


def add_scale_bar(ax):
    """Add professional scale bar."""
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    
    # Position: lower left
    padding = 0.05
    bar_length_km = 5
    bar_length_m = bar_length_km * 1000
    
    # Calculate pixel position
    x_range = xlim[1] - xlim[0]
    y_range = ylim[1] - ylim[0]
    
    x_start = xlim[0] + x_range * padding
    y_pos = ylim[0] + y_range * padding
    
    # Draw main bar
    ax.plot([x_start, x_start + bar_length_m], [y_pos, y_pos],
           linewidth=4, color='black', solid_capstyle='butt', zorder=100)
    
    # Draw ticks
    for offset in [0, bar_length_m/2, bar_length_m]:
        ax.plot([x_start + offset, x_start + offset], 
               [y_pos - y_range*0.01, y_pos + y_range*0.01],
               linewidth=3, color='black', zorder=100)
    
    # Add labels
    ax.text(x_start, y_pos - y_range*0.02, '0', 
           ha='center', va='top', fontsize=10, fontweight='bold')
    ax.text(x_start + bar_length_m, y_pos - y_range*0.02, f'{bar_length_km}', 
           ha='center', va='top', fontsize=10, fontweight='bold')
    ax.text(x_start + bar_length_m/2, y_pos + y_range*0.025, 'km',
           ha='center', va='bottom', fontsize=10, fontweight='bold')


def add_north_arrow(ax):
    """Add professional north arrow."""
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    
    x_range = xlim[1] - xlim[0]
    y_range = ylim[1] - ylim[0]
    
    # Position: upper right
    padding = 0.07
    x_pos = xlim[1] - x_range * padding
    y_pos = ylim[1] - y_range * padding
    
    arrow_len = y_range * 0.06
    
    # Draw arrow
    ax.annotate('', xy=(x_pos, y_pos + arrow_len), xytext=(x_pos, y_pos),
               arrowprops=dict(arrowstyle='->', lw=3, color='black'),
               zorder=100)
    
    # Add 'N' label
    ax.text(x_pos, y_pos + arrow_len + y_range*0.02, 'N',
           ha='center', va='bottom', fontsize=16, fontweight='bold',
           bbox=dict(boxstyle='circle,pad=0.3', facecolor='white',
                    edgecolor='black', linewidth=2), zorder=100)


def create_clean_study_area_map():
    """Create clean, presentation-ready study area map."""
    print("\n" + "="*70)
    print("Creating CLEAN Professional Study Area Map")
    print("="*70 + "\n")
    
    # Create figure
    fig = plt.figure(figsize=(14, 10), facecolor='white', dpi=300)
    
    # Main axes
    ax_main = plt.axes([0.08, 0.08, 0.72, 0.85])
    
    # Inset axes
    ax_inset = plt.axes([0.70, 0.75, 0.22, 0.18])
    
    # Define realistic bounds for Tenerife fire area (UTM Zone 28N)
    minx, maxx = 344000, 366000  # ~22 km wide
    miny, maxy = 3130000, 3148000  # ~18 km tall
    
    # ========== BACKGROUND ==========
    print("📍 Creating clean background...")
    
    # Very light gray background rectangle (represents land)
    land_patch = Rectangle((minx, miny), maxx-minx, maxy-miny,
                           facecolor=COLORS['land'], 
                           edgecolor=COLORS['border'],
                           linewidth=2, zorder=1)
    ax_main.add_patch(land_patch)
    
    # ========== FIRE PROGRESSION ZONES ==========
    print("📍 Adding fire progression zones...")
    
    # Ignition point (Arafo, center-left of domain)
    ign_x = minx + (maxx - minx) * 0.35
    ign_y = miny + (maxy - miny) * 0.52
    
    # Fire progression ellipses (simplified representation)
    # Day 4 (largest, bottom layer)
    fire4 = Wedge((ign_x, ign_y), r=9000, theta1=0, theta2=360,
                 facecolor=COLORS['fire_day4'], edgecolor='white',
                 linewidth=3, alpha=0.7, zorder=10, label='Day 4 (Aug 26)')
    ax_main.add_patch(fire4)
    
    # Day 3
    fire3 = Wedge((ign_x + 500, ign_y - 500), r=6500, theta1=0, theta2=360,
                 facecolor=COLORS['fire_day3'], edgecolor='white',
                 linewidth=3, alpha=0.75, zorder=11, label='Day 3 (Aug 24)')
    ax_main.add_patch(fire3)
    
    # Day 2
    fire2 = Wedge((ign_x, ign_y), r=4000, theta1=0, theta2=360,
                 facecolor=COLORS['fire_day2'], edgecolor='white',
                 linewidth=3, alpha=0.8, zorder=12, label='Day 2 (Aug 21)')
    ax_main.add_patch(fire2)
    
    # Day 1 (smallest, top layer)
    fire1 = Wedge((ign_x, ign_y), r=1800, theta1=0, theta2=360,
                 facecolor=COLORS['fire_day1'], edgecolor='white',
                 linewidth=3, alpha=0.85, zorder=13, label='Day 1 (Aug 18)')
    ax_main.add_patch(fire1)
    
    # ========== IGNITION POINT ==========
    print("📍 Adding ignition point...")
    
    ax_main.plot(ign_x, ign_y, marker='*', markersize=28,
                color=COLORS['ignition'], markeredgecolor='black',
                markeredgewidth=2, zorder=100, label='Ignition Point')
    
    # Ignition label
    label_box = FancyBboxPatch((ign_x + 1500, ign_y + 1500), 6000, 1800,
                              boxstyle="round,pad=200", 
                              facecolor='white', edgecolor='black',
                              linewidth=2, zorder=99)
    ax_main.add_patch(label_box)
    
    ax_main.text(ign_x + 4500, ign_y + 2400,
                'Ignition Point\n(Arafo, ~1000m)',
                fontsize=12, fontweight='bold', color=COLORS['text'],
                ha='center', va='center', zorder=100)
    
    # ========== FIRE AREA ANNOTATIONS ==========
    print("📍 Adding area annotations...")
    
    # Day 4 annotation (outside fire area)
    ax_main.text(maxx - 2000, maxy - 2000,
                '12,260 ha\n(Day 4)',
                fontsize=11, fontweight='bold', color=COLORS['fire_day4'],
                ha='right', va='top',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='white',
                         edgecolor=COLORS['fire_day4'], linewidth=2.5))
    
    # ========== CARTOGRAPHIC ELEMENTS ==========
    print("📍 Adding cartographic elements...")
    
    add_scale_bar(ax_main)
    add_north_arrow(ax_main)
    
    # ========== LEGEND ==========
    print("📍 Creating legend...")
    
    legend_elements = [
        mpatches.Patch(facecolor=COLORS['fire_day1'], edgecolor='white', 
                      linewidth=2, label='Day 1 (Aug 18): 5,867 ha'),
        mpatches.Patch(facecolor=COLORS['fire_day2'], edgecolor='white', 
                      linewidth=2, label='Day 2 (Aug 21): 9,559 ha'),
        mpatches.Patch(facecolor=COLORS['fire_day3'], edgecolor='white', 
                      linewidth=2, label='Day 3 (Aug 24): 10,943 ha'),
        mpatches.Patch(facecolor=COLORS['fire_day4'], edgecolor='white', 
                      linewidth=2, label='Day 4 (Aug 26): 12,260 ha'),
        Line2D([0], [0], marker='*', color='w', 
               markerfacecolor=COLORS['ignition'], markeredgecolor='black',
               markeredgewidth=1.5, markersize=15, label='Ignition Point')
    ]
    
    legend = ax_main.legend(handles=legend_elements, loc='upper left',
                           fontsize=11, framealpha=0.98, edgecolor='black',
                           fancybox=True, shadow=True, title='Fire Progression',
                           title_fontsize=12)
    legend.set_zorder(200)
    
    # ========== AXES CONFIGURATION ==========
    ax_main.set_xlim(minx, maxx)
    ax_main.set_ylim(miny, maxy)
    ax_main.set_xlabel('Easting (m, UTM Zone 28N)', 
                      fontsize=13, fontweight='bold', color=COLORS['text'])
    ax_main.set_ylabel('Northing (m, UTM Zone 28N)', 
                      fontsize=13, fontweight='bold', color=COLORS['text'])
    ax_main.set_title('Study Area: 2023 Tenerife Wildfire\nFire Progression (August 18-26, 2023)',
                     fontsize=17, fontweight='bold', pad=15, color=COLORS['text'])
    
    # Grid
    ax_main.grid(True, alpha=0.3, linestyle='--', color=COLORS['grid'], linewidth=1)
    ax_main.set_axisbelow(True)
    
    # Format tick labels
    ax_main.tick_params(labelsize=11, colors=COLORS['text'])
    ax_main.ticklabel_format(style='plain', useOffset=False)
    
    # ========== TENERIFE INSET ==========
    print("📍 Creating Tenerife context inset...")
    create_tenerife_context_inset(ax_inset)
    
    # ========== SAVE ==========
    print("\n📍 Saving figure...")
    plt.savefig(OUTPUT_FILE, dpi=300, bbox_inches='tight',
               facecolor='white', edgecolor='none')
    
    print(f"\n✅ SUCCESS! Clean study area map created!")
    print(f"📁 Saved to: {OUTPUT_FILE}")
    print(f"📊 Resolution: 300 DPI")
    print(f"🎨 Style: Clean white background, presentation-ready")
    print("\n" + "="*70)
    print("IMPROVEMENTS OVER PREVIOUS VERSION:")
    print("✓ WHITE background (not garish synthetic terrain)")
    print("✓ Clean, professional design")
    print("✓ Fire progression clearly visible")
    print("✓ Geographic context (Tenerife inset)")
    print("✓ Professional cartography (scale, north arrow)")
    print("✓ Presentation-ready (no distracting elements)")
    print("="*70 + "\n")
    
    plt.close()


if __name__ == "__main__":
    create_clean_study_area_map()






