"""
Create a SIMPLE LiDAR Pipeline graphic for PowerPoint presentation
Clean, readable, presentation-friendly
"""

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.patches as mpatches

# Set up figure - VERTICAL orientation, compact, narrow
fig, ax = plt.subplots(figsize=(5, 10), dpi=300)
ax.set_xlim(0, 5)
ax.set_ylim(0, 10)
ax.axis('off')

# Use Calibri for consistency
plt.rcParams['font.family'] = 'Calibri'

# Colors
UVA_NAVY = '#00356B'
UVA_RED = '#E03C31'
LIGHT_BLUE = '#E3F2FD'
LIGHT_GREEN = '#E8F5E9'
LIGHT_ORANGE = '#FFF3E0'
LIGHT_PURPLE = '#F3E5F5'
LIGHT_GRAY = '#F5F5F5'
DARK_GRAY = '#2C2C2C'

# Pipeline steps as boxes - VERTICAL layout (top to bottom), full width
steps = [
    {
        'x': 0.3, 'y': 8.2, 'width': 4.4, 'height': 1.5,
        'color': LIGHT_BLUE,
        'title': 'Raw LiDAR',
        'subtitle': '5m point cloud',
        'detail': 'PNOA-IGN'
    },
    {
        'x': 0.3, 'y': 6.4, 'width': 4.4, 'height': 1.5,
        'color': LIGHT_GREEN,
        'title': 'Height Norm.',
        'subtitle': 'PDAL HAG',
        'detail': 'Ground removal'
    },
    {
        'x': 0.3, 'y': 4.6, 'width': 4.4, 'height': 1.5,
        'color': LIGHT_ORANGE,
        'title': 'NRD',
        'subtitle': 'Vertical bins',
        'detail': '20 layers × 2m'
    },
    {
        'x': 0.3, 'y': 2.8, 'width': 4.4, 'height': 1.5,
        'color': LIGHT_PURPLE,
        'title': 'PAD',
        'subtitle': 'Beer-Lambert',
        'detail': 'κ = 0.6'
    },
    {
        'x': 0.3, 'y': 1.0, 'width': 4.4, 'height': 1.5,
        'color': LIGHT_GRAY,
        'title': 'Output',
        'subtitle': '20m grid',
        'detail': '20 layers'
    }
]

# Draw boxes
for step in steps:
    # Box
    box = FancyBboxPatch(
        (step['x'], step['y']), step['width'], step['height'],
        boxstyle="round,pad=0.1",
        edgecolor=UVA_NAVY,
        facecolor=step['color'],
        linewidth=2.5
    )
    ax.add_patch(box)
    
    # Title
    ax.text(step['x'] + step['width']/2, step['y'] + step['height'] - 0.4,
            step['title'],
            fontsize=18, fontweight='bold', color=UVA_NAVY,
            ha='center', va='center')
    
    # Subtitle
    ax.text(step['x'] + step['width']/2, step['y'] + step['height']/2,
            step['subtitle'],
            fontsize=16, color=DARK_GRAY,
            ha='center', va='center')
    
    # Detail
    ax.text(step['x'] + step['width']/2, step['y'] + 0.4,
            step['detail'],
            fontsize=14, color=DARK_GRAY, style='italic',
            ha='center', va='center')

# Draw arrows between boxes - VERTICAL (downward)
arrow_props = dict(
    arrowstyle='->,head_width=0.5,head_length=0.5',
    lw=3,
    color=UVA_RED
)

arrows = [
    (2.5, 8.2, 2.5, 7.9),      # Raw → Height Norm
    (2.5, 6.4, 2.5, 6.1),      # Height Norm → NRD
    (2.5, 4.6, 2.5, 4.3),      # NRD → PAD
    (2.5, 2.8, 2.5, 2.5),      # PAD → Output
]

for x1, y1, x2, y2 in arrows:
    arrow = FancyArrowPatch(
        (x1, y1), (x2, y2),
        **arrow_props
    )
    ax.add_patch(arrow)

# No title or captions - clean graphic only

plt.tight_layout(pad=0)

# Save with minimal margins on all sides
output_path = 'presentation/LiDAR_Pipeline_Simple.png'
plt.savefig(output_path, dpi=300, bbox_inches='tight', 
            facecolor='white', edgecolor='none', pad_inches=0.01)
print(f"✅ Clean LiDAR pipeline saved to: {output_path}")
print(f"📊 Resolution: High-DPI, minimal margins")
print(f"🎨 No title/captions - ready to insert!")

plt.close()

