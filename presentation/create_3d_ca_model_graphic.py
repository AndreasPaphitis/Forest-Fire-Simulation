"""
Create a 3D Cellular Automata Model visualization
Shows the vertical layer structure and 3D nature of the fire spread model
"""

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch, Circle
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np

# Set up figure - compact size for 1/3 slide with minimal margins
fig = plt.figure(figsize=(4.5, 5.5), dpi=300)

# Use Calibri for consistency
plt.rcParams['font.family'] = 'Calibri'

# Create subplot with minimal margins
ax = fig.add_subplot(111, projection='3d', computed_zorder=False)
ax.set_position([0, 0.05, 1, 0.95])  # [left, bottom, width, height]

# Colors
UVA_NAVY = '#00356B'
UVA_RED = '#E03C31'
LAYER_BLUE = '#90CAF9'
LAYER_GREEN = '#81C784'
LAYER_ORANGE = '#FFB74D'
FIRE_RED = '#EF5350'
FIRE_ORANGE = '#FF9800'

# Create a simplified 3D grid showing layers
# Show 5 representative layers out of 20 for clarity

layer_heights = [0, 10, 20, 30, 40]  # Heights in meters (0-40m)
layer_colors = [LAYER_BLUE, LAYER_GREEN, LAYER_ORANGE, LAYER_ORANGE, FIRE_ORANGE]
layer_alphas = [0.3, 0.4, 0.5, 0.6, 0.7]

# Grid dimensions (compact for 1/3 slide)
grid_size = 4
x_range = np.linspace(0, 80, grid_size)
y_range = np.linspace(0, 80, grid_size)

# Draw horizontal layers
for i, (height, color, alpha) in enumerate(zip(layer_heights, layer_colors, layer_alphas)):
    # Create mesh for each layer
    X, Y = np.meshgrid(x_range, y_range)
    Z = np.ones_like(X) * height
    
    # Draw the layer surface
    ax.plot_surface(X, Y, Z, color=color, alpha=alpha, edgecolor=UVA_NAVY, 
                    linewidth=0.5, shade=False)
    
    # Add layer label (compact)
    if i < len(layer_heights):
        ax.text(90, 40, height, f'{height}m', fontsize=11, 
                color=UVA_NAVY, fontweight='bold')

# No fire visualization - just show the 3D structure

# Compact label
ax.text(-5, 40, 20, '20 Layers\n(0-40m)', fontsize=12, 
        color=UVA_NAVY, fontweight='bold', ha='center',
        bbox=dict(boxstyle='round,pad=0.4', facecolor='white', 
                 edgecolor=UVA_NAVY, linewidth=1.5))

# Set labels and view (smaller fonts, minimal padding)
ax.set_xlabel('X (m)', fontsize=9, color=UVA_NAVY, labelpad=2)
ax.set_ylabel('Y (m)', fontsize=9, color=UVA_NAVY, labelpad=2)
ax.set_zlabel('Height (m)', fontsize=9, color=UVA_NAVY, labelpad=2)

# Reduce tick label size
ax.tick_params(axis='both', which='major', labelsize=8, pad=1)

# Set limits (compact)
ax.set_xlim(0, 80)
ax.set_ylim(0, 80)
ax.set_zlim(0, 45)

# Set viewing angle for best perspective
ax.view_init(elev=20, azim=45)

# Remove grid for cleaner look
ax.grid(False)

# Set background
ax.xaxis.pane.fill = False
ax.yaxis.pane.fill = False
ax.zaxis.pane.fill = False

plt.tight_layout(pad=0)

# Save with minimal white space
output_path = 'presentation/3D_CA_Model_Graphic.png'
plt.savefig(output_path, dpi=300, bbox_inches='tight', 
            facecolor='white', edgecolor='none', pad_inches=0.02)
print(f"✅ 3D CA model graphic saved to: {output_path}")
print(f"📊 Shows: 20m grid, 20 vertical layers (0-40m)")
print(f"🎨 Clean 3D structure - perfect for presentation!")

plt.close()

