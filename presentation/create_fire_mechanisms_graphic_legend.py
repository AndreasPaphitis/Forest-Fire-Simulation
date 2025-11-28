#!/usr/bin/env python3
"""
Create combined fire spread mechanisms graphic with SIDE LEGEND.
Clean 3D visualization with legend box on the right.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyArrowPatch, Circle, Rectangle
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d import art3d
import numpy as np

# Set up figure with extra width for legend
fig = plt.figure(figsize=(14, 8), dpi=300)

# Use Calibri for consistency
plt.rcParams['font.family'] = 'Calibri'

# Colors
UVA_NAVY = '#00356B'
HORIZONTAL_BLUE = '#1976D2'
VERTICAL_ORANGE = '#F57C00'
EMBER_RED = '#D32F2F'
FIRE_YELLOW = '#FFC107'
LAYER_GRAY = '#90A4AE'

# Create 3D subplot (takes up left 70% of figure)
ax = fig.add_subplot(121, projection='3d')

# Grid setup
grid_size = 5
x_range = np.linspace(0, 100, grid_size)
y_range = np.linspace(0, 100, grid_size)
layer_heights = [0, 15, 30]

# 1. DRAW VERTICAL LAYERS
for i, height in enumerate(layer_heights):
    X, Y = np.meshgrid(x_range, y_range)
    Z = np.ones_like(X) * height
    
    alpha = 0.15 if i == 0 else 0.2
    color = LAYER_GRAY if i < 2 else VERTICAL_ORANGE
    
    ax.plot_surface(X, Y, Z, color=color, alpha=alpha, 
                    edgecolor=UVA_NAVY, linewidth=0.5, shade=False)
    
    # Layer labels on the right
    ax.text(105, 50, height, f'{height}m', fontsize=12, 
            color=UVA_NAVY, fontweight='bold')

# 2. HORIZONTAL SPREAD - 8-neighbor connectivity
center_x, center_y = 50, 50
fire_center_z = 5

# Fire source
fire_source = Circle((center_x, center_y), 10, facecolor=FIRE_YELLOW, 
                      edgecolor=EMBER_RED, linewidth=3, zorder=10)
ax.add_patch(fire_source)
art3d.pathpatch_2d_to_3d(fire_source, z=fire_center_z, zdir="z")

# 8-neighbor arrows
directions = [
    (0, 1), (1, 1), (1, 0), (1, -1),
    (0, -1), (-1, -1), (-1, 0), (-1, 1)
]

arrow_length = 18
for dx, dy in directions:
    end_x = center_x + dx * arrow_length
    end_y = center_y + dy * arrow_length
    
    linewidth = 3.5 if dx == 0 or dy == 0 else 2.5
    alpha = 0.9 if dx == 0 or dy == 0 else 0.7
    
    arrow = patches.FancyArrowPatch((center_x, center_y), (end_x, end_y),
                                   arrowstyle='->', mutation_scale=20,
                                   color=HORIZONTAL_BLUE, linewidth=linewidth,
                                   alpha=alpha, zorder=8)
    ax.add_patch(arrow)
    art3d.pathpatch_2d_to_3d(arrow, z=fire_center_z, zdir="z")

# 3. VERTICAL SPREAD - Layer connections
vertical_positions = [(40, 40), (50, 50), (60, 60)]

for vx, vy in vertical_positions:
    for i in range(len(layer_heights) - 1):
        z_start = layer_heights[i] + 2
        z_end = layer_heights[i + 1] - 2
        
        ax.plot([vx, vx], [vy, vy], [z_start, z_end],
                color=VERTICAL_ORANGE, linewidth=3.5, alpha=0.9, zorder=7)
        
        ax.plot([vx], [vy], [z_end], marker='^', color=VERTICAL_ORANGE,
                markersize=12, zorder=7)

# 4. EMBER TRANSPORT - Parabolic arcs
ember_paths = [
    (50, 50, 20, 80, 45),
    (50, 50, 85, 70, 40),
    (50, 50, 75, 25, 38),
]

for start_x, start_y, end_x, end_y, peak_height in ember_paths:
    t = np.linspace(0, 1, 30)
    x_path = start_x + (end_x - start_x) * t
    y_path = start_y + (end_y - start_y) * t
    z_path = fire_center_z + 4 * peak_height * t * (1 - t)
    
    ax.plot(x_path, y_path, z_path, color=EMBER_RED, linewidth=3.5,
            alpha=0.8, linestyle='--', zorder=9)
    
    ax.plot([end_x], [end_y], [2], marker='o', color=EMBER_RED,
            markersize=10, zorder=9, markeredgecolor=FIRE_YELLOW, 
            markeredgewidth=2.5)

# Configure 3D plot
ax.set_xlabel('X (m)', fontsize=12, color=UVA_NAVY, labelpad=8, fontweight='bold')
ax.set_ylabel('Y (m)', fontsize=12, color=UVA_NAVY, labelpad=8, fontweight='bold')
ax.set_zlabel('Height (m)', fontsize=12, color=UVA_NAVY, labelpad=8, fontweight='bold')

ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.set_zlim(0, 50)

ax.view_init(elev=22, azim=40)
ax.grid(False)
ax.xaxis.pane.fill = False
ax.yaxis.pane.fill = False
ax.zaxis.pane.fill = False
ax.tick_params(axis='both', which='major', labelsize=10)

# ====== CREATE LEGEND ON THE RIGHT ======
ax_legend = fig.add_subplot(122)
ax_legend.axis('off')

# Title
ax_legend.text(0.5, 0.95, 'Fire Spread Mechanisms', 
              fontsize=20, fontweight='bold', ha='center', 
              color=UVA_NAVY)

# Legend entries with colored boxes
y_start = 0.78
box_height = 0.18
spacing = 0.02

# 1. Horizontal Spread
rect1 = Rectangle((0.1, y_start), 0.8, box_height, 
                  facecolor=HORIZONTAL_BLUE, edgecolor='white', 
                  linewidth=3, transform=ax_legend.transAxes)
ax_legend.add_patch(rect1)
ax_legend.text(0.5, y_start + box_height/2 + 0.03, 'Horizontal Spread', 
              fontsize=18, fontweight='bold', ha='center', va='center',
              color='white', transform=ax_legend.transAxes)
ax_legend.text(0.5, y_start + box_height/2 - 0.03, '(Surface Fire)', 
              fontsize=14, ha='center', va='center',
              color='white', style='italic', transform=ax_legend.transAxes)

# 2. Vertical Spread
y_pos = y_start - box_height - spacing
rect2 = Rectangle((0.1, y_pos), 0.8, box_height, 
                  facecolor=VERTICAL_ORANGE, edgecolor='white', 
                  linewidth=3, transform=ax_legend.transAxes)
ax_legend.add_patch(rect2)
ax_legend.text(0.5, y_pos + box_height/2 + 0.03, 'Vertical Spread', 
              fontsize=18, fontweight='bold', ha='center', va='center',
              color='white', transform=ax_legend.transAxes)
ax_legend.text(0.5, y_pos + box_height/2 - 0.03, '(Crown Fire)', 
              fontsize=14, ha='center', va='center',
              color='white', style='italic', transform=ax_legend.transAxes)

# 3. Ember Transport
y_pos = y_pos - box_height - spacing
rect3 = Rectangle((0.1, y_pos), 0.8, box_height, 
                  facecolor=EMBER_RED, edgecolor='white', 
                  linewidth=3, transform=ax_legend.transAxes)
ax_legend.add_patch(rect3)
ax_legend.text(0.5, y_pos + box_height/2 + 0.03, 'Ember Transport', 
              fontsize=18, fontweight='bold', ha='center', va='center',
              color='white', transform=ax_legend.transAxes)
ax_legend.text(0.5, y_pos + box_height/2 - 0.03, '(Spotting)', 
              fontsize=14, ha='center', va='center',
              color='white', style='italic', transform=ax_legend.transAxes)

# Add details below
y_details = 0.25
ax_legend.text(0.5, y_details, '8-Neighbor Connectivity', 
              fontsize=13, ha='center', color=HORIZONTAL_BLUE,
              fontweight='bold', transform=ax_legend.transAxes)
ax_legend.text(0.5, y_details - 0.06, '20 Vertical Layers (0-40m)', 
              fontsize=13, ha='center', color=VERTICAL_ORANGE,
              fontweight='bold', transform=ax_legend.transAxes)
ax_legend.text(0.5, y_details - 0.12, 'Wind-Biased Long Distance', 
              fontsize=13, ha='center', color=EMBER_RED,
              fontweight='bold', transform=ax_legend.transAxes)

plt.tight_layout(pad=0.5)

# Save
output_path = 'presentation/Fire_Mechanisms_Combined.png'
plt.savefig(output_path, dpi=300, bbox_inches='tight', 
            facecolor='white', edgecolor='none', pad_inches=0.1)
print(f"✅ Fire mechanisms graphic saved to: {output_path}")
print(f"📊 Clean 3D visualization with side legend")
print(f"🎨 Color-coded legend: Blue, Orange, Red")
print(f"🎯 Perfect for PowerPoint!")

plt.close()


