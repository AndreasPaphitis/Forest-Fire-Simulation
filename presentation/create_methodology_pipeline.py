"""
Option 3: Simple Flow Diagram
Clean pipeline showing the methodology flow.
"""

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle
import numpy as np

# Set up figure
fig, ax = plt.subplots(figsize=(14, 6), dpi=300)
ax.set_xlim(0, 14)
ax.set_ylim(0, 6)
ax.axis('off')

# Use Calibri
plt.rcParams['font.family'] = 'Calibri'

# Colors
UVA_NAVY = '#00356B'
LIGHT_BLUE = '#E8F4F8'
DARK_GRAY = '#2C2C2C'

# Title
ax.text(7, 5.5, 'Methodology Pipeline', fontsize=22, fontweight='bold',
        ha='center', va='center', color=UVA_NAVY)

# Pipeline stages - simplified boxes
stages = [
    (2, 3, "LiDAR + Terrain\n+ Fire Data"),
    (4.5, 3, "3D CA Model\n(20 layers)"),
    (7, 3, "Sensitivity\n(16→4)"),
    (9.5, 3, "Grid Search\n(81 runs)"),
    (12, 3, "Validation\n(Days 3-4)"),
]

box_width = 1.8
box_height = 1.2

# Draw pipeline
for i, (x, y, label) in enumerate(stages):
    # Choose color alternating
    color = LIGHT_BLUE if i % 2 == 0 else '#E8F5E9'
    
    box = FancyBboxPatch((x - box_width/2, y - box_height/2), box_width, box_height,
                         boxstyle="round,pad=0.1",
                         edgecolor=UVA_NAVY,
                         facecolor=color,
                         linewidth=2.5)
    ax.add_patch(box)
    
    ax.text(x, y, label, fontsize=14, fontweight='bold',
            ha='center', va='center', color=UVA_NAVY)
    
    # Draw arrow to next stage
    if i < len(stages) - 1:
        x_next = stages[i+1][0]
        arrow = FancyArrowPatch((x + box_width/2 + 0.05, y), 
                               (x_next - box_width/2 - 0.05, y),
                               arrowstyle='->', mutation_scale=25,
                               color=UVA_NAVY, linewidth=3)
        ax.add_patch(arrow)

# Details below pipeline
details_y = 1.3
ax.text(2, details_y, "5m resolution\nEMSR 685", fontsize=10,
        ha='center', va='center', color=DARK_GRAY)
ax.text(4.5, details_y, "3 mechanisms:\nH, V, Ember", fontsize=10,
        ha='center', va='center', color=DARK_GRAY)
ax.text(7, details_y, "Range-based\nscreening", fontsize=10,
        ha='center', va='center', color=DARK_GRAY)
ax.text(9.5, details_y, "Modified Dice\nDays 1-2", fontsize=10,
        ha='center', va='center', color=DARK_GRAY)
ax.text(12, details_y, "Out-of-sample\nDice: 0.69, 0.49", fontsize=10,
        ha='center', va='center', color=DARK_GRAY)

# Add efficiency callout
efficiency_box = FancyBboxPatch((5.5, 4.3), 3, 0.6,
                               boxstyle="round,pad=0.05",
                               edgecolor='#FFC107',
                               facecolor='#FFFEF0',
                               linewidth=2)
ax.add_patch(efficiency_box)
ax.text(7, 4.6, 'Efficiency: 43M → 81 simulations', fontsize=11,
        ha='center', va='center', color=DARK_GRAY, fontweight='bold')

plt.tight_layout()
plt.savefig('presentation/Methodology_Pipeline.png', dpi=300, bbox_inches='tight',
            facecolor='white', edgecolor='none', pad_inches=0.1)
print("✅ Option 3: Pipeline diagram saved!")
plt.close()






