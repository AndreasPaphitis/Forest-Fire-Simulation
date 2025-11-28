"""
Option 2: Four-Quadrant Layout
Organized view of Data, Model, Calibration, Validation.
"""

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle
import numpy as np

# Set up figure
fig, ax = plt.subplots(figsize=(12, 10), dpi=300)
ax.set_xlim(0, 12)
ax.set_ylim(0, 10)
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

# Title
ax.text(6, 9.5, 'Methodology Overview', fontsize=26, fontweight='bold',
        ha='center', va='center', color=UVA_NAVY)

# Quadrant positions: (x, y, width, height)
quadrants = [
    (0.3, 5.2, 5.7, 3.8, "Data & Model", LIGHT_BLUE),
    (6.3, 5.2, 5.4, 3.8, "Objective Function", LIGHT_GREEN),
    (0.3, 0.5, 5.7, 4.3, "Calibration Framework", LIGHT_ORANGE),
    (6.3, 0.5, 5.4, 4.3, "Validation", LIGHT_PURPLE),
]

for x, y, w, h, title, color in quadrants:
    # Draw box
    box = FancyBboxPatch((x, y), w, h,
                         boxstyle="round,pad=0.15",
                         edgecolor=UVA_NAVY,
                         facecolor=color,
                         linewidth=2.5)
    ax.add_patch(box)
    
    # Title
    ax.text(x + w/2, y + h - 0.4, title, fontsize=18, fontweight='bold',
            ha='center', va='center', color=UVA_NAVY)

# ========== QUADRANT 1: Data & Model ==========
x_base, y_base = 0.8, 7.8
ax.text(x_base, y_base, 'Data Sources:', fontsize=14, fontweight='bold',
        ha='left', va='top', color=DARK_GRAY)
ax.text(x_base, y_base - 0.4, '• LiDAR: 5m → PAD (3D fuel)', fontsize=12,
        ha='left', va='top', color=DARK_GRAY)
ax.text(x_base, y_base - 0.7, '• Terrain: 5m DTM', fontsize=12,
        ha='left', va='top', color=DARK_GRAY)
ax.text(x_base, y_base - 1.0, '• Fire: EMSR 685 delineations', fontsize=12,
        ha='left', va='top', color=DARK_GRAY)

ax.text(x_base, y_base - 1.6, '3D CA Model:', fontsize=14, fontweight='bold',
        ha='left', va='top', color=DARK_GRAY)
ax.text(x_base, y_base - 2.0, '• 20m resolution, 20 layers (0-40m)', fontsize=12,
        ha='left', va='top', color=DARK_GRAY)
ax.text(x_base, y_base - 2.3, '• Horizontal, Vertical, Ember spread', fontsize=12,
        ha='left', va='top', color=DARK_GRAY)

# ========== QUADRANT 2: Objective Function ==========
x_base, y_base = 6.8, 8.3
ax.text(9.5, y_base, r'Minimize: $(1 - \mathrm{Dice}) + P$', fontsize=16,
        ha='center', va='center', color=DARK_GRAY)

ax.text(9.5, y_base - 0.6, r'$\mathrm{Dice} = \dfrac{2|A \cap B|}{|A| + |B|}$', fontsize=14,
        ha='center', va='center', color=DARK_GRAY)

ax.text(9.5, y_base - 1.2, r'$P = 2(r-2)^2$ if $r>2$, else $P=0$', fontsize=12,
        ha='center', va='center', color=DARK_GRAY)

ax.text(x_base, y_base - 1.9, 'Rationale:', fontsize=13, fontweight='bold',
        ha='left', va='top', color=DARK_GRAY)
ax.text(x_base, y_base - 2.2, '• Balances spatial accuracy', fontsize=11,
        ha='left', va='top', color=DARK_GRAY)
ax.text(x_base, y_base - 2.5, '• Penalizes unrealistic spread', fontsize=11,
        ha='left', va='top', color=DARK_GRAY)
ax.text(x_base, y_base - 2.8, '• Standard wildfire validation', fontsize=11,
        ha='left', va='top', color=DARK_GRAY)

# ========== QUADRANT 3: Calibration ==========
x_base, y_base = 0.8, 4.0
ax.text(x_base, y_base, 'Two-Stage Approach:', fontsize=14, fontweight='bold',
        ha='left', va='top', color=DARK_GRAY)

ax.text(x_base + 0.2, y_base - 0.5, 'Stage 1: Sensitivity Analysis', fontsize=13, fontweight='bold',
        ha='left', va='top', color='#F57C00')
ax.text(x_base + 0.2, y_base - 0.85, '• 16 parameters tested', fontsize=11,
        ha='left', va='top', color=DARK_GRAY)
ax.text(x_base + 0.2, y_base - 1.15, '• Range-based screening', fontsize=11,
        ha='left', va='top', color=DARK_GRAY)
ax.text(x_base + 0.2, y_base - 1.45, '• Top 4 parameters selected', fontsize=11,
        ha='left', va='top', color=DARK_GRAY)

ax.text(x_base + 0.2, y_base - 1.95, 'Stage 2: Grid Search', fontsize=13, fontweight='bold',
        ha='left', va='top', color='#1976D2')
ax.text(x_base + 0.2, y_base - 2.3, '• 3 points × 4 parameters = 81 runs', fontsize=11,
        ha='left', va='top', color=DARK_GRAY)
ax.text(x_base + 0.2, y_base - 2.6, '• Modified Dice optimization', fontsize=11,
        ha='left', va='top', color=DARK_GRAY)

ax.text(x_base, y_base - 3.1, 'Training Data: Days 1-2 (Aug 18-21)', fontsize=12,
        ha='left', va='top', color=DARK_GRAY, style='italic')

# ========== QUADRANT 4: Validation ==========
x_base, y_base = 6.8, 4.0
ax.text(x_base, y_base, 'Out-of-Sample Testing:', fontsize=14, fontweight='bold',
        ha='left', va='top', color=DARK_GRAY)

ax.text(x_base, y_base - 0.5, 'Test Period: Days 3-4 (Aug 24-26)', fontsize=12,
        ha='left', va='top', color=DARK_GRAY)

ax.text(x_base, y_base - 1.1, 'Performance Metrics:', fontsize=13, fontweight='bold',
        ha='left', va='top', color=DARK_GRAY)
ax.text(x_base, y_base - 1.45, '• Day 3: Dice = 0.690', fontsize=12,
        ha='left', va='top', color=DARK_GRAY)
ax.text(x_base, y_base - 1.75, '• Day 4: Dice = 0.486', fontsize=12,
        ha='left', va='top', color=DARK_GRAY)
ax.text(x_base, y_base - 2.05, '• Improvement: +29.6%', fontsize=12,
        ha='left', va='top', color=DARK_GRAY)

ax.text(x_base, y_base - 2.6, 'Ensures model generalization', fontsize=12,
        ha='left', va='top', color=DARK_GRAY, style='italic')
ax.text(x_base, y_base - 2.9, 'to unseen fire events', fontsize=12,
        ha='left', va='top', color=DARK_GRAY, style='italic')

plt.tight_layout()
plt.savefig('presentation/Methodology_Quadrants.png', dpi=300, bbox_inches='tight',
            facecolor='white', edgecolor='none', pad_inches=0.1)
print("✅ Option 2: Four-quadrant layout saved!")
plt.close()






