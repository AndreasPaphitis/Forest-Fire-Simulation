"""
Create a SIMPLE, clean graphic of the Modified Dice Coefficient objective function
for PowerPoint presentation.
"""

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np

# Set up the figure with high DPI for crisp rendering
fig, ax = plt.subplots(figsize=(8, 4), dpi=300)
ax.set_xlim(0, 10)
ax.set_ylim(0, 5)
ax.axis('off')

# UvA Colors
UVA_NAVY = '#00356B'
LIGHT_BLUE = '#E8F4F8'
DARK_GRAY = '#2C2C2C'

# Simple box with clean border
main_box = FancyBboxPatch((0.5, 0.5), 9, 4,
                          boxstyle="round,pad=0.1",
                          edgecolor=UVA_NAVY,
                          facecolor=LIGHT_BLUE,
                          linewidth=2.5,
                          zorder=1)
ax.add_patch(main_box)

# Title - simple and clean
ax.text(5, 4.1, 'Objective Function',
        fontsize=18, fontweight='bold', color=UVA_NAVY,
        ha='center', va='center')

# Main equation - large and clear
ax.text(5, 3.2, r'$\mathrm{Minimize:}\quad (1 - \mathrm{Dice}) + P$',
        fontsize=24, fontweight='bold', color=DARK_GRAY,
        ha='center', va='center')

# Dice formula
ax.text(5, 2.3, r'$\mathrm{Dice} = \dfrac{2|A \cap B|}{|A| + |B|}$',
        fontsize=22, color=DARK_GRAY,
        ha='center', va='center')

# Penalty formula
ax.text(5, 1.5, r'$P = 2(r-2)^2 \quad \mathrm{if} \; r > 2, \; \mathrm{else} \; P = 0$',
        fontsize=16, color=DARK_GRAY,
        ha='center', va='center')

# Simple legend at bottom
ax.text(5, 0.85, r'$A$: Predicted   |   $B$: Observed (EMSR)   |   $r = |A|/|B|$: Area ratio',
        fontsize=12, color=DARK_GRAY,
        ha='center', va='center')

plt.tight_layout()

# Save with transparent background and high quality
output_path = 'presentation/Objective_Function_Graphic.png'
plt.savefig(output_path, dpi=300, bbox_inches='tight', 
            facecolor='white', edgecolor='none', pad_inches=0.1)
print(f"✅ Simple graphic saved to: {output_path}")
print(f"📊 Resolution: 2400x1200 pixels (300 DPI)")
print(f"🎨 Clean and minimal - ready for PowerPoint!")

plt.close()

