# EMSR Binary Mask Visualizations - Summary

## Overview

This document summarizes the binary mask visualizations created from the EMSR fire perimeter polygons for the Tenerife wildfire (August 2023). These visualizations can be used in your methodology section to illustrate the preprocessing of fire perimeter data.

## Files Created

### 1. Individual Day Visualizations (4 files)

Located in: `Academic_Thesis_Charts/`

- **EMSR_Day1_Binary_Mask.png** - Day 1 (August 18, 2023): 5,867 ha
- **EMSR_Day2_Binary_Mask.png** - Day 2 (August 21, 2023): 9,559 ha  
- **EMSR_Day3_Binary_Mask.png** - Day 3 (August 24, 2023): 10,943 ha
- **EMSR_Day4_Binary_Mask.png** - Day 4 (August 26, 2023): 12,260 ha

Each visualization shows:
- Binary mask (1=burned, 0=unburned) in red-yellow-blue color scheme
- UTM Zone 28N coordinates (EPSG:32628)
- Statistics: burned area (ha), burned cells, grid size, resolution
- 20m resolution matching your simulation grid

### 2. Combined 4-Panel Comparison

**File:** `EMSR_Binary_Masks_4Panel_Comparison.png`

A 2×2 grid showing all four days side-by-side for easy comparison. This is ideal for showing the temporal progression of the fire in your methodology section.

### 3. Progressive Overlay Visualization

**File:** `EMSR_Binary_Masks_Progressive_Overlay.png`

Shows all four days overlaid with different colors (light red → dark red) to visualize the progressive growth of the fire perimeter. This clearly shows how the fire expanded over time.

### 4. Binary Mask Arrays (for simulation use)

Located in: `02_processed_data/fire_targets/`

For each day (1-4):
- **emsr_day{N}_binary_mask_20m.npy** - NumPy array of the binary mask
- **emsr_day{N}_binary_mask_20m_metadata.json** - Metadata including:
  - Grid dimensions (927 × 1088 cells)
  - Burned area in hectares
  - Bounds in UTM coordinates
  - CRS information (EPSG:32628)
  - Resolution (20m)

## Technical Details

### Processing Steps

1. **Source Data:** EMSR-665 shapefiles (originally in WGS84, EPSG:4326)
2. **Reprojection:** Converted to UTM Zone 28N (EPSG:32628) for metric coordinates
3. **Rasterization:** Converted polygons to 20m resolution raster grids
4. **Common Bounds:** All days use the same spatial extent for consistency
5. **Binary Conversion:** Burned areas = 1, unburned areas = 0

### Grid Specifications

- **Resolution:** 20m (matching your simulation resolution)
- **Grid Size:** 1088 × 927 cells
- **Spatial Extent:** 
  - Easting: 343,535 - 365,302 m
  - Northing: 3,129,831 - 3,148,388 m
- **CRS:** EPSG:32628 (UTM Zone 28N)

### Fire Progression Statistics

| Day | Date | Burned Area (ha) | Burned Cells | % Increase from Day 1 |
|-----|------|------------------|--------------|----------------------|
| 1 | Aug 18, 2023 | 5,867 | 146,676 | - |
| 2 | Aug 21, 2023 | 9,559 | 238,983 | +63% |
| 3 | Aug 24, 2023 | 10,943 | 273,569 | +86% |
| 4 | Aug 26, 2023 | 12,260 | 306,503 | +109% |

## Usage in Methodology Section

### Recommended Figure

Use **EMSR_Binary_Masks_4Panel_Comparison.png** as your main figure in the methodology section. It clearly shows:

1. The progression of the fire over 4 observation dates
2. The binary nature of the masks (burned vs. unburned)
3. The spatial extent and resolution
4. Quantitative information (burned area for each day)

### Updated Caption Text

Here's an updated caption you can use:

```
Figure X: Binary Mask Representation of EMSR Fire Perimeters

Fire perimeter polygons from EMSR-665 were converted to binary raster masks 
at 20m resolution for model calibration and validation. Each panel shows the 
cumulative burned area (red = burned, blue = unburned) for: (a) Day 1 - 
August 18, 2023 (5,867 ha), (b) Day 2 - August 21, 2023 (9,559 ha), 
(c) Day 3 - August 24, 2023 (10,943 ha), (d) Day 4 - August 26, 2023 
(12,260 ha). All data reprojected to UTM Zone 28N (EPSG:32628). Days 1-2 
were used for calibration; Days 3-4 were withheld for independent validation.
```

### Text to Add to Methodology

You can add this paragraph to explain the binary mask creation:

```
The EMSR fire perimeter polygons were converted to binary raster masks through 
a standardized preprocessing workflow. Original vector data in WGS84 geographic 
coordinates (EPSG:4326) were reprojected to UTM Zone 28N (EPSG:32628) to enable 
metric-based calculations. Polygons were then rasterized to 20m resolution 
matching the simulation grid, with burned areas assigned a value of 1 and 
unburned areas assigned 0. All four daily observations were rasterized to a 
common spatial extent (1088 × 927 cells) to ensure consistent spatial alignment 
for model comparison. The resulting binary masks (Figure X) provide the target 
data for calibration (Days 1-2) and validation (Days 3-4).
```

## Alternative Visualizations

### For Showing Fire Growth

Use **EMSR_Binary_Masks_Progressive_Overlay.png** if you want to emphasize the 
progressive expansion of the fire. The color gradient (light → dark red) makes 
it easy to see how the fire grew from Day 1 to Day 4.

### For Detailed Individual Days

Use the individual day files (EMSR_Day{N}_Binary_Mask.png) if you need to show 
specific days in detail, such as in an appendix or supplementary materials.

## Integration with Simulation

The binary mask arrays (.npy files) can be loaded directly in your simulation 
code for calibration and validation:

```python
import numpy as np

# Load Day 1 binary mask
day1_mask = np.load('02_processed_data/fire_targets/emsr_day1_binary_mask_20m.npy')

# Load metadata
import json
with open('02_processed_data/fire_targets/emsr_day1_binary_mask_20m_metadata.json') as f:
    metadata = json.load(f)
    
print(f"Grid shape: {metadata['grid_shape']}")
print(f"Burned area: {metadata['burned_area_ha']} ha")
```

## Reproducibility

The script `create_emsr_binary_masks_visualization.py` can be re-run at any time 
to regenerate these visualizations. It automatically:

- Detects all available EMSR shapefiles
- Reprojects to the correct CRS
- Uses consistent spatial extents
- Generates all visualizations and arrays
- Saves metadata for documentation

## Notes

1. **Resolution Choice:** 20m resolution was chosen to match your simulation grid 
   and balance computational efficiency with spatial accuracy.

2. **CRS Consistency:** All data uses EPSG:32628 (UTM Zone 28N) to match your 
   terrain and LiDAR data.

3. **Common Bounds:** Using a common spatial extent for all days ensures that 
   the binary masks can be directly compared pixel-by-pixel.

4. **Binary vs. Graded:** These are binary masks (burned/unburned). The original 
   EMSR data includes burn severity classes, but for model calibration, binary 
   masks are typically sufficient.

## Questions or Issues?

If you need:
- Different resolution (e.g., 5m, 10m, 50m)
- Different spatial extent
- Additional statistics or visualizations
- Different color schemes

Simply modify the parameters in `create_emsr_binary_masks_visualization.py` and 
re-run the script.

