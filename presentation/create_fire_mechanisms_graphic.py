#!/usr/bin/env python3
"""
Create combined fire spread mechanisms graphic for presentation.
Shows horizontal, vertical, and ember transport in one integrated view.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyArrowPatch, Circle, FancyBboxPatch
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np

# Set up figure
fig = plt.figure(figsize=(10, 8), dpi=300)

# Use Calibri for consistency
plt.rcParams['font.family'] = 'Calibri'

# Colors
UVA_NAVY = '#00356B'
UVA_RED = '#E03C31'
HORIZONTAL_BLUE = '#1976D2'  # Blue for horizontal
VERTICAL_ORANGE = '#F57C00'  # Orange for vertical
EMBER_RED = '#D32F2F'  # Red for ember
FIRE_YELLOW = '#FFC107'
LAYER_GRAY = '#90A4AE'

# Create 3D subplot
ax = fig.add_subplot(111, projection='3d')

# Grid setup
grid_size = 5
x_range = np.linspace(0, 100, grid_size)
y_range = np.linspace(0, 100, grid_size)
layer_heights = [0, 15, 30]  # Three layers for clarity

# 1. DRAW VERTICAL LAYERS (Foundation)
for i, height in enumerate(layer_heights):
    X, Y = np.meshgrid(x_range, y_range)
    Z = np.ones_like(X) * height
    
    alpha = 0.15 if i == 0 else 0.2  # Ground layer more transparent
    color = LAYER_GRAY if i < 2 else VERTICAL_ORANGE
    
    ax.plot_surface(X, Y, Z, color=color, alpha=alpha, 
                    edgecolor=UVA_NAVY, linewidth=0.5, shade=False)
    
    # Add layer labels (larger)
    ax.text(105, 50, height, f'{height}m', fontsize=13, 
            color=UVA_NAVY, fontweight='bold')

# 2. HORIZONTAL SPREAD (Surface Fire) - 8-neighbor connectivity
center_x, center_y = 50, 50
fire_center_z = 5  # Slightly above ground

# Draw fire source (center cell) - larger for visibility
fire_source = Circle((center_x, center_y), 10, color=FIRE_YELLOW, 
                      edgecolor=EMBER_RED, linewidth=3, zorder=10)
ax.add_patch(fire_source)
from mpl_toolkits.mplot3d import art3d
art3d.pathpatch_2d_to_3d(fire_source, z=fire_center_z, zdir="z")

# 8-neighbor arrows (Moore connectivity)
directions = [
    (0, 1, 'N'), (1, 1, 'NE'), (1, 0, 'E'), (1, -1, 'SE'),
    (0, -1, 'S'), (-1, -1, 'SW'), (-1, 0, 'W'), (-1, 1, 'NW')
]

arrow_length = 18
for dx, dy, label in directions:
    end_x = center_x + dx * arrow_length
    end_y = center_y + dy * arrow_length
    
    # Thicker arrows for cardinal directions (increased for visibility)
    linewidth = 3.5 if dx == 0 or dy == 0 else 2.5
    alpha = 0.9 if dx == 0 or dy == 0 else 0.7
    
    # Draw horizontal spread arrows (larger mutation scale)
    arrow = patches.FancyArrowPatch((center_x, center_y), (end_x, end_y),
                                   arrowstyle='->', mutation_scale=20,
                                   color=HORIZONTAL_BLUE, linewidth=linewidth,
                                   alpha=alpha, zorder=8)
    ax.add_patch(arrow)
    art3d.pathpatch_2d_to_3d(arrow, z=fire_center_z, zdir="z")

# 3. VERTICAL SPREAD (Crown Fire) - Layer-to-layer connections
# Show vertical connections from ground to upper layers
vertical_positions = [(40, 40), (50, 50), (60, 60)]

for vx, vy in vertical_positions:
    for i in range(len(layer_heights) - 1):
        z_start = layer_heights[i] + 2
        z_end = layer_heights[i + 1] - 2
        
        # Vertical arrow (thicker for visibility)
        ax.plot([vx, vx], [vy, vy], [z_start, z_end],
                color=VERTICAL_ORANGE, linewidth=3.5, alpha=0.9, zorder=7)
        
        # Add arrowhead (larger)
        ax.plot([vx], [vy], [z_end], marker='^', color=VERTICAL_ORANGE,
                markersize=12, zorder=7)

# 4. EMBER TRANSPORT (Spotting) - Long-distance parabolic arcs
ember_paths = [
    # (start_x, start_y, end_x, end_y, peak_height)
    (50, 50, 20, 80, 45),
    (50, 50, 85, 70, 40),
    (50, 50, 75, 25, 38),
]

for start_x, start_y, end_x, end_y, peak_height in ember_paths:
    # Create parabolic path
    t = np.linspace(0, 1, 30)
    x_path = start_x + (end_x - start_x) * t
    y_path = start_y + (end_y - start_y) * t
    z_path = fire_center_z + 4 * peak_height * t * (1 - t)  # Parabolic height
    
    # Draw ember path (thicker for visibility)
    ax.plot(x_path, y_path, z_path, color=EMBER_RED, linewidth=3.5,
            alpha=0.8, linestyle='--', zorder=9)
    
    # Add ember endpoint (spot fire) - larger
    ax.plot([end_x], [end_y], [2], marker='o', color=EMBER_RED,
            markersize=10, zorder=9, markeredgecolor=FIRE_YELLOW, 
            markeredgewidth=2.5)

# 5. ANNOTATIONS AND LABELS - STRATEGICALLY POSITIONED FOR MAXIMUM VISIBILITY

# Horizontal spread label - FRONT LEFT, ground level (clear area)
ax.text(20, 5, 2, 'Horizontal\nSpread', fontsize=11, color='white',
        fontweight='bold', ha='left', va='bottom',
        bbox=dict(boxstyle='round,pad=0.4', facecolor=HORIZONTAL_BLUE, 
                 edgecolor='white', linewidth=2, alpha=1.0))

# Vertical spread label - BACK RIGHT, mid-height (clear of all trajectories)
ax.text(85, 95, 28, 'Vertical\nSpread', fontsize=11, color='white',
        fontweight='bold', ha='right', va='center',
        bbox=dict(boxstyle='round,pad=0.4', facecolor=VERTICAL_ORANGE, 
                 edgecolor='white', linewidth=2, alpha=1.0))

# Ember transport label - BACK RIGHT, top (high above everything)
ax.text(10, 95, 50, 'Ember\nTransport', fontsize=11, color='white',
        fontweight='bold', ha='left', va='top',
        bbox=dict(boxstyle='round,pad=0.4', facecolor=EMBER_RED, 
                 edgecolor='white', linewidth=2, alpha=1.0))

# Set labels and view (larger fonts)
ax.set_xlabel('X (m)', fontsize=13, color=UVA_NAVY, labelpad=10, fontweight='bold')
ax.set_ylabel('Y (m)', fontsize=13, color=UVA_NAVY, labelpad=10, fontweight='bold')
ax.set_zlabel('Height (m)', fontsize=13, color=UVA_NAVY, labelpad=10, fontweight='bold')

# Set limits (extended z-axis for better label placement)
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.set_zlim(-5, 52)

# Set viewing angle for best perspective (adjusted to show labels clearly)
ax.view_init(elev=22, azim=40)

# Remove grid for cleaner look
ax.grid(False)

# Set background
ax.xaxis.pane.fill = False
ax.yaxis.pane.fill = False
ax.zaxis.pane.fill = False

# Increase tick label size for visibility
ax.tick_params(axis='both', which='major', labelsize=11, pad=3)

plt.tight_layout(pad=0.1)

# Save
output_path = 'presentation/Fire_Mechanisms_Combined.png'
plt.savefig(output_path, dpi=300, bbox_inches='tight', 
            facecolor='white', edgecolor='none', pad_inches=0.1)
print(f"✅ Fire mechanisms graphic saved to: {output_path}")
print(f"📊 Shows: Horizontal (8-neighbor), Vertical (layers), Ember (arcs)")
print(f"🎨 Color-coded: Blue (horizontal), Orange (vertical), Red (ember)")
print(f"🎯 Ready for PowerPoint hybrid layout!")

plt.close()

