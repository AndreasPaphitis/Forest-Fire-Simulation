"""
Create a SIMPLE graphic for the objective function rationale - presentation ready
"""

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

# Set up the figure - taller to include penalty explanation
fig, ax = plt.subplots(figsize=(8, 5.5), dpi=300)
ax.set_xlim(0, 10)
ax.set_ylim(0, 6)
ax.axis('off')

# Set font to Calibri (presentation standard)
plt.rcParams['font.family'] = 'Calibri'

# UvA Colors
UVA_NAVY = '#00356B'
UVA_RED = '#E03C31'
LIGHT_BLUE = '#E8F4F8'
LIGHT_ORANGE = '#FFF3E0'
DARK_GRAY = '#2C2C2C'

# Main box
main_box = FancyBboxPatch((0.5, 0.5), 9, 5,
                          boxstyle="round,pad=0.1",
                          edgecolor=UVA_NAVY,
                          facecolor=LIGHT_BLUE,
                          linewidth=2.5,
                          zorder=1)
ax.add_patch(main_box)

# Title
ax.text(5, 5.15, 'Objective Function: Rationale',
        fontsize=18, fontweight='bold', color=UVA_NAVY,
        ha='center', va='center')

# What it measures
ax.text(5, 4.5, 'Dice = spatial overlap (0 = no match, 1 = perfect)',
        fontsize=18, color=DARK_GRAY,
        ha='center', va='center')

ax.text(5, 4.0, 'Minimize error: (1 - Dice) + Penalty',
        fontsize=18, color=DARK_GRAY,
        ha='center', va='center')

# Penalty term explanation box
penalty_box = FancyBboxPatch((1, 2.7), 8, 0.9,
                            boxstyle="round,pad=0.08",
                            edgecolor=UVA_RED,
                            facecolor=LIGHT_ORANGE,
                            linewidth=2,
                            zorder=2)
ax.add_patch(penalty_box)

ax.text(5, 3.4, 'Penalty Term: P = 2(r-2)² if r > 2',
        fontsize=17, fontweight='bold', color=UVA_RED,
        ha='center', va='center')

ax.text(5, 3.0, 'Prevents model from burning > 2× observed area',
        fontsize=16, color=DARK_GRAY,
        ha='center', va='center')

ax.text(5, 2.75, 'Avoids unrealistic model performance',
        fontsize=16, color=DARK_GRAY,
        ha='center', va='center')

# Why we chose it
ax.text(5, 2.1, '• Smoother optimization than Dice alone',
        fontsize=18, color=DARK_GRAY,
        ha='center', va='center')

ax.text(5, 1.6, '• Balances spatial accuracy with physical realism',
        fontsize=18, color=DARK_GRAY,
        ha='center', va='center')

ax.text(5, 1.1, '• Dice is a standard in wildfire model validation',
        fontsize=18, color=DARK_GRAY,
        ha='center', va='center')

plt.tight_layout()

# Save
output_path = 'presentation/Objective_Rationale_Graphic.png'
plt.savefig(output_path, dpi=300, bbox_inches='tight', 
            facecolor='white', edgecolor='none', pad_inches=0.1)
print(f"✅ Rationale graphic saved to: {output_path}")
print(f"📊 Resolution: 2400x1500 pixels (300 DPI)")
print(f"🎨 Ready for PowerPoint!")

plt.close()

