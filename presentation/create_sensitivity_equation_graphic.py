"""
Create a small, clean graphic showing the range-based sensitivity equation.
Compact design to fit as an inset or supplement on the calibration slide.
"""

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np

# Set up a compact figure
fig, ax = plt.subplots(figsize=(6, 3), dpi=300)
ax.set_xlim(0, 6)
ax.set_ylim(0, 3)
ax.axis('off')

# Use Calibri for consistency
plt.rcParams['font.family'] = 'Calibri'

# Colors
UVA_NAVY = '#00356B'
LIGHT_BLUE = '#E8F4F8'
DARK_GRAY = '#2C2C2C'

# Main box
box = FancyBboxPatch((0.2, 0.3), 5.6, 2.4,
                     boxstyle="round,pad=0.1",
                     edgecolor=UVA_NAVY,
                     facecolor=LIGHT_BLUE,
                     linewidth=2.5,
                     zorder=1)
ax.add_patch(box)

# Title
ax.text(3, 2.4, 'Range-Based Sensitivity',
        fontsize=16, fontweight='bold', color=UVA_NAVY,
        ha='center', va='center')

# Main equation
ax.text(3, 1.7, r'$S_i = \dfrac{\Delta \mathrm{Output}_i}{\Delta \mathrm{Param}_i} \times \dfrac{1}{\mathrm{Output}_{\mathrm{median}}}$',
        fontsize=18, color=DARK_GRAY,
        ha='center', va='center')

# Explanation line 1
ax.text(3, 1.1, r'$\Delta \mathrm{Output}_i = \max(f) - \min(f)$ across 9 test points',
        fontsize=11, color=DARK_GRAY,
        ha='center', va='center')

# Explanation line 2
ax.text(3, 0.7, r'Higher $S_i$ → parameter $i$ strongly influences fire behavior',
        fontsize=11, color=DARK_GRAY, style='italic',
        ha='center', va='center')

plt.tight_layout()

# Save
output_path = 'presentation/Sensitivity_Equation.png'
plt.savefig(output_path, dpi=300, bbox_inches='tight', 
            facecolor='white', edgecolor='none', pad_inches=0.05)
print(f"✅ Sensitivity equation graphic saved to: {output_path}")
print(f"📐 Compact size: 6×3 inches")
print(f"🎯 Ready to add to your calibration slide!")

plt.close()






