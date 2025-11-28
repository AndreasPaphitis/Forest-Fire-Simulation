"""
Option 1: Visual Workflow Graphic
Shows the methodology as a linear flow with stages.
"""

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

# Set up figure
fig, ax = plt.subplots(figsize=(14, 8), dpi=300)
ax.set_xlim(0, 14)
ax.set_ylim(0, 8)
ax.axis('off')

# Use Calibri
plt.rcParams['font.family'] = 'Calibri'

# Colors
UVA_NAVY = '#00356B'
LIGHT_BLUE = '#E8F4F8'
LIGHT_GREEN = '#E8F5E9'
LIGHT_ORANGE = '#FFF3E0'
LIGHT_PURPLE = '#F3E5F5'
DARK_GRAY = '#2C2C2C'

# Stage positions
stages = [
    (1.5, 5.5, "Data\nCollection", LIGHT_BLUE),
    (4.5, 5.5, "3D CA\nModel", LIGHT_GREEN),
    (7.5, 5.5, "Sensitivity\nAnalysis", LIGHT_ORANGE),
    (10.5, 5.5, "Grid Search\nCalibration", LIGHT_PURPLE),
]

box_width = 2.2
box_height = 1.5

# Draw stages
for x, y, label, color in stages:
    box = FancyBboxPatch((x - box_width/2, y - box_height/2), box_width, box_height,
                         boxstyle="round,pad=0.1",
                         edgecolor=UVA_NAVY,
                         facecolor=color,
                         linewidth=2.5)
    ax.add_patch(box)
    ax.text(x, y, label, fontsize=16, fontweight='bold',
            ha='center', va='center', color=UVA_NAVY)

# Draw arrows between stages
arrow_y = 5.5
for i in range(len(stages) - 1):
    x_start = stages[i][0] + box_width/2
    x_end = stages[i+1][0] - box_width/2
    arrow = FancyArrowPatch((x_start + 0.1, arrow_y), (x_end - 0.1, arrow_y),
                           arrowstyle='->', mutation_scale=30,
                           color=UVA_NAVY, linewidth=3)
    ax.add_patch(arrow)

# Details below each stage
details = [
    (1.5, 4.2, "• LiDAR: 5m → PAD\n• Terrain: 5m DTM\n• Fire: EMSR 685"),
    (4.5, 4.2, "• 20m resolution\n• 20 layers (0-40m)\n• 3 mechanisms"),
    (7.5, 4.2, "• 16 parameters\n• Range-based\n• Top 4 selected"),
    (10.5, 4.2, "• 81 combinations\n• Days 1-2 training\n• Modified Dice"),
]

for x, y, text in details:
    ax.text(x, y, text, fontsize=12, ha='center', va='top',
            color=DARK_GRAY)

# Validation box at bottom
val_box = FancyBboxPatch((5, 1.5), 4, 1.3,
                        boxstyle="round,pad=0.1",
                        edgecolor=UVA_NAVY,
                        facecolor='#FFFEF0',
                        linewidth=2.5)
ax.add_patch(val_box)
ax.text(7, 2.5, 'Validation', fontsize=16, fontweight='bold',
        ha='center', va='center', color=UVA_NAVY)
ax.text(7, 1.9, 'Out-of-sample: Days 3-4 (Aug 24-26)', fontsize=12,
        ha='center', va='center', color=DARK_GRAY)

# Arrow to validation
arrow_to_val = FancyArrowPatch((10.5, 4.7), (7, 2.8),
                              arrowstyle='->', mutation_scale=30,
                              color=UVA_NAVY, linewidth=3,
                              connectionstyle="arc3,rad=.3")
ax.add_patch(arrow_to_val)

# Title
ax.text(7, 7.5, 'Methodology Workflow', fontsize=24, fontweight='bold',
        ha='center', va='center', color=UVA_NAVY)

plt.tight_layout()
plt.savefig('presentation/Methodology_Workflow.png', dpi=300, bbox_inches='tight',
            facecolor='white', edgecolor='none', pad_inches=0.1)
print("✅ Option 1: Workflow graphic saved!")
plt.close()






