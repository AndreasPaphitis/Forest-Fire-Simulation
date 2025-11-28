"""
Create a clean graphic showing the equations for the three fire spread mechanisms.
Matches the style of the objective function graphic.
"""

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle
import numpy as np

# Set up the figure with high DPI for crisp rendering
fig, ax = plt.subplots(figsize=(12, 6.5), dpi=300)
ax.set_xlim(0, 12)
ax.set_ylim(0, 6.5)
ax.axis('off')

# Use Calibri for consistency
plt.rcParams['font.family'] = 'Calibri'

# Colors matching the fire mechanisms
HORIZONTAL_BLUE = '#1976D2'
VERTICAL_ORANGE = '#F57C00'
EMBER_RED = '#D32F2F'
UVA_NAVY = '#00356B'
LIGHT_BLUE = '#E8F4F8'
LIGHT_ORANGE = '#FFF3E0'
LIGHT_RED = '#FFEBEE'
DARK_GRAY = '#2C2C2C'

# ========== HORIZONTAL SPREAD ==========
y_pos = 6.3
box_height = 1.5

box1 = FancyBboxPatch((0.3, y_pos - box_height), 11.4, box_height,
                      boxstyle="round,pad=0.15",
                      edgecolor=HORIZONTAL_BLUE,
                      facecolor=LIGHT_BLUE,
                      linewidth=3,
                      zorder=1)
ax.add_patch(box1)

# Header
ax.text(6, y_pos - 0.25, 'Horizontal Spread (Surface Fire)',
        fontsize=24, fontweight='bold', color=HORIZONTAL_BLUE,
        ha='center', va='center')

# Main equation
ax.text(6, y_pos - 0.85, r'$P_h = P_{\mathrm{base}} \times f_{\mathrm{fuel}} \times f_{\mathrm{wind}} \times f_{\mathrm{slope}} \times f_{\mathrm{dist}}$',
        fontsize=28, color=DARK_GRAY,
        ha='center', va='center')

# ========== VERTICAL SPREAD ==========
y_pos = 4.5
box_height = 1.5

box2 = FancyBboxPatch((0.3, y_pos - box_height), 11.4, box_height,
                      boxstyle="round,pad=0.15",
                      edgecolor=VERTICAL_ORANGE,
                      facecolor=LIGHT_ORANGE,
                      linewidth=3,
                      zorder=1)
ax.add_patch(box2)

# Header
ax.text(6, y_pos - 0.25, 'Vertical Spread (Crown Fire)',
        fontsize=24, fontweight='bold', color=VERTICAL_ORANGE,
        ha='center', va='center')

# Main equation with connectivity
ax.text(6, y_pos - 0.85, r'$P_v = C_{\mathrm{vert}} \times f_{\mathrm{fuel}}$     where     $C_{\mathrm{vert}} = \sqrt{\mathrm{fuel}_z \times \mathrm{fuel}_{z+1}}$',
        fontsize=26, color=DARK_GRAY,
        ha='center', va='center')

# ========== EMBER TRANSPORT ==========
y_pos = 2.7
box_height = 1.9

box3 = FancyBboxPatch((0.3, y_pos - box_height), 11.4, box_height,
                      boxstyle="round,pad=0.15",
                      edgecolor=EMBER_RED,
                      facecolor=LIGHT_RED,
                      linewidth=3,
                      zorder=1)
ax.add_patch(box3)

# Header
ax.text(6, y_pos - 0.25, 'Ember Transport (Spotting)',
        fontsize=24, fontweight='bold', color=EMBER_RED,
        ha='center', va='center')

# Show as a flow: Generation → Travel → Ignition
# Generation
ax.text(1.8, y_pos - 0.8, r'1. Generation',
        fontsize=20, fontweight='bold', color=EMBER_RED, ha='left', va='center')
ax.text(1.8, y_pos - 1.15, r'$P_{\mathrm{gen}} = P_0 \times f_{\mathrm{height}} \times f_{\mathrm{wind}}$',
        fontsize=22, color=DARK_GRAY, ha='left', va='center')

# Arrow
ax.annotate('', xy=(4.8, y_pos - 0.95), xytext=(4.2, y_pos - 0.95),
            arrowprops=dict(arrowstyle='->', lw=2.5, color=EMBER_RED))

# Travel
ax.text(5.2, y_pos - 0.8, r'2. Travel',
        fontsize=20, fontweight='bold', color=EMBER_RED, ha='left', va='center')
ax.text(5.2, y_pos - 1.15, r'$d \sim \mathrm{Exp}(\lambda)$, wind-biased',
        fontsize=20, color=DARK_GRAY, ha='left', va='center')

# Arrow
ax.annotate('', xy=(7.8, y_pos - 0.95), xytext=(7.2, y_pos - 0.95),
            arrowprops=dict(arrowstyle='->', lw=2.5, color=EMBER_RED))

# Ignition
ax.text(8.2, y_pos - 0.8, r'3. Ignition',
        fontsize=20, fontweight='bold', color=EMBER_RED, ha='left', va='center')
ax.text(8.2, y_pos - 1.15, r'$P_{\mathrm{ign}} = P_0 \times f_{\mathrm{fuel}} \times f_{\mathrm{moisture}}$',
        fontsize=22, color=DARK_GRAY, ha='left', va='center')

# Bottom explanation
ax.text(6, y_pos - 1.65, r'Stochastic spotting: embers generated at height, travel long distance, attempt ignition',
        fontsize=18, color=DARK_GRAY, ha='center', va='center', style='italic')

plt.tight_layout()

# Save with high quality
output_path = 'presentation/Fire_Spread_Equations.png'
plt.savefig(output_path, dpi=300, bbox_inches='tight', 
            facecolor='white', edgecolor='none', pad_inches=0.1)
print(f"✅ Fire spread equations graphic saved to: {output_path}")
print(f"📊 Shows: Horizontal, Vertical, and Ember equations")
print(f"🎨 Color-coded: Blue (horizontal), Orange (vertical), Red (ember)")
print(f"🎯 Ready for PowerPoint!")

plt.close()

