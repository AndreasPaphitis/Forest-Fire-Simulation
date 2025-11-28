"""
Create a clean flow diagram showing the two-stage calibration workflow.
Matches the style of other presentation graphics.
"""

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

# Set up the figure
fig, ax = plt.subplots(figsize=(8, 9), dpi=300)
ax.set_xlim(0, 8)
ax.set_ylim(-0.2, 8.8)
ax.axis('off')

# Use Calibri for consistency
plt.rcParams['font.family'] = 'Calibri'

# Colors
UVA_NAVY = '#00356B'
UVA_RED = '#E03C31'
LIGHT_BLUE = '#E8F4F8'
LIGHT_GREEN = '#E8F5E9'
LIGHT_ORANGE = '#FFF3E0'
DARK_GRAY = '#2C2C2C'
GOLD = '#FFC107'

# ========== STAGE 1: SENSITIVITY ANALYSIS ==========
y_pos = 8.3
box_height = 1.3

box1 = FancyBboxPatch((0.5, y_pos - box_height), 7, box_height,
                      boxstyle="round,pad=0.15",
                      edgecolor=UVA_NAVY,
                      facecolor=LIGHT_BLUE,
                      linewidth=3,
                      zorder=1)
ax.add_patch(box1)

# Stage label
ax.text(0.8, y_pos - 0.2, 'Stage 1',
        fontsize=16, fontweight='bold', color=UVA_NAVY,
        ha='left', va='center')

# Title
ax.text(4, y_pos - 0.25, 'Sensitivity Analysis',
        fontsize=22, fontweight='bold', color=UVA_NAVY,
        ha='center', va='center')

# Details
ax.text(4, y_pos - 0.7, '9 points × 16 parameters = 144 simulations',
        fontsize=16, color=DARK_GRAY,
        ha='center', va='center')

ax.text(4, y_pos - 1.05, 'Objective: Identify most influential parameters',
        fontsize=14, color=DARK_GRAY, style='italic',
        ha='center', va='center')

# ========== ARROW 1 ==========
arrow1 = FancyArrowPatch((4, y_pos - box_height - 0.1), (4, y_pos - box_height - 0.6),
                         arrowstyle='->', mutation_scale=40,
                         color=UVA_NAVY, linewidth=4, zorder=10)
ax.add_patch(arrow1)

# Result label next to arrow
ax.text(5.2, y_pos - box_height - 0.35, 'Top 4 Critical Parameters',
        fontsize=15, fontweight='bold', color=UVA_RED,
        ha='left', va='center',
        bbox=dict(boxstyle='round,pad=0.4', facecolor='white', 
                 edgecolor=UVA_RED, linewidth=2))

# ========== STAGE 2: GRID SEARCH ==========
y_pos = 5.6

box2 = FancyBboxPatch((0.5, y_pos - box_height), 7, box_height,
                      boxstyle="round,pad=0.15",
                      edgecolor=UVA_NAVY,
                      facecolor=LIGHT_GREEN,
                      linewidth=3,
                      zorder=1)
ax.add_patch(box2)

# Stage label
ax.text(0.8, y_pos - 0.2, 'Stage 2',
        fontsize=16, fontweight='bold', color=UVA_NAVY,
        ha='left', va='center')

# Title
ax.text(4, y_pos - 0.25, 'Grid Search Optimization',
        fontsize=22, fontweight='bold', color=UVA_NAVY,
        ha='center', va='center')

# Details
ax.text(4, y_pos - 0.7, '3 points × 4 parameters = 81 simulations',
        fontsize=16, color=DARK_GRAY,
        ha='center', va='center')

ax.text(4, y_pos - 1.05, 'Target: EMSR Days 1-2 (Aug 18-21)',
        fontsize=14, color=DARK_GRAY, style='italic',
        ha='center', va='center')

# ========== ARROW 2 ==========
arrow2 = FancyArrowPatch((4, y_pos - box_height - 0.1), (4, y_pos - box_height - 0.6),
                         arrowstyle='->', mutation_scale=40,
                         color=UVA_NAVY, linewidth=4, zorder=10)
ax.add_patch(arrow2)

# Result label
ax.text(5.2, y_pos - box_height - 0.35, 'Optimized Parameters',
        fontsize=15, fontweight='bold', color=UVA_RED,
        ha='left', va='center',
        bbox=dict(boxstyle='round,pad=0.4', facecolor='white', 
                 edgecolor=UVA_RED, linewidth=2))

# ========== VALIDATION ==========
y_pos = 2.9
box_height = 1.0

box3 = FancyBboxPatch((0.5, y_pos - box_height), 7, box_height,
                      boxstyle="round,pad=0.15",
                      edgecolor=UVA_RED,
                      facecolor=LIGHT_ORANGE,
                      linewidth=3,
                      zorder=1)
ax.add_patch(box3)

# Title
ax.text(4, y_pos - 0.3, 'Validation',
        fontsize=22, fontweight='bold', color=UVA_RED,
        ha='center', va='center')

# Details
ax.text(4, y_pos - 0.7, 'EMSR Days 3-4 (Aug 24-26)',
        fontsize=16, color=DARK_GRAY,
        ha='center', va='center')

# ========== COMPUTATIONAL EFFICIENCY BOX ==========
y_pos = 1.1
box_height = 1.1

efficiency_box = FancyBboxPatch((0.5, y_pos - box_height), 7, box_height,
                                boxstyle="round,pad=0.15",
                                edgecolor=GOLD,
                                facecolor='#FFFEF0',
                                linewidth=3,
                                zorder=1)
ax.add_patch(efficiency_box)

# Title
ax.text(4, y_pos - 0.2, 'Computational Efficiency',
        fontsize=20, fontweight='bold', color=GOLD.replace('C107', '8B00'),
        ha='center', va='center')

# Big number
ax.text(4, y_pos - 0.65, r'$3^{16} \approx 43$ million  →  81 simulations',
        fontsize=18, color=DARK_GRAY,
        ha='center', va='center')

ax.text(4, y_pos - 0.95, '6 orders of magnitude reduction  |  ~53 min per simulation',
        fontsize=14, color=DARK_GRAY, style='italic',
        ha='center', va='center')

plt.tight_layout()

# Save
output_path = 'presentation/Calibration_Workflow.png'
plt.savefig(output_path, dpi=300, bbox_inches='tight', 
            facecolor='white', edgecolor='none', pad_inches=0.1)
print(f"✅ Calibration workflow graphic saved to: {output_path}")
print(f"📊 Shows: Two-stage calibration framework")
print(f"🎨 Flow: Sensitivity → Grid Search → Validation")
print(f"🎯 Ready for PowerPoint!")

plt.close()

