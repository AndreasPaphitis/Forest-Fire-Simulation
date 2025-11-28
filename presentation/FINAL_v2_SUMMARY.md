# Final Presentation v2 - Summary

## What's New

Successfully added **Slide 7: Fire Spread Mechanisms** as requested!

### New Slide Details

**Slide 7: Fire Spread Mechanisms**
- **Layout**: Image-focused (content on left, figure on right)
- **Content**: Explains all three fire spread mechanisms in detail:
  1. **Horizontal Spread (Surface Fire)**
     - 8-neighbor Moore connectivity
     - Slope multiplicative factor: exp(0.1·slope_degrees)
     - Wind multiplier effects
     - Barranco channeling: 2.5× amplification
  
  2. **Vertical Spread (Crown Fire)**
     - Layer-to-layer geometric mean: √(PAD_lower × PAD_upper)
     - 20 vertical layers at 2m intervals (0-40m)
     - Fuel continuity drives vertical propagation
  
  3. **Ember Transport (Spotting)**
     - Exponential distance decay
     - Wind-biased direction kernel
     - Stochastic ignition probability
     - Critical for long-distance spread

- **Figure**: Fire spread mode pie charts showing contribution breakdown
- **Position**: Between "Model Structure & Optimization" (Slide 6) and "Calibration Approach" (Slide 8)

## Complete Slide Structure (14 slides)

1. **Title Slide** - Introduction
2. **Background & Problem** - Climate crisis context
3. **Research Objectives** - Two main research questions
4. **Study Area & Methodology** - Tenerife 2023 fire + EMSR 4-panel map
5. **LiDAR Processing & Model Architecture** - Pipeline diagram
6. **Model Structure & Computational Optimization** - Rationale for custom CA
7. **Fire Spread Mechanisms** ⭐ **NEW** - Detailed mechanism breakdown
8. **Calibration Approach** - Two-stage framework + priority matrix
9. **Sensitivity Analysis Results** - Parameter ranking graph
10. **Validation Results** - Spatial validation maps
11. **Key Findings & Limitations** - Achievements vs challenges
12. **Conclusions & Future Directions** - Research questions answered
13. **Acknowledgments** - Supervisor, data sources, university
14. **Thank You / Questions** - Contact info

## Files Generated

- **Presentation**: `Thesis_Presentation_Final_v2.pptx`
- **Design System**: `design_system.py` (restored)
- **Slide Layouts**: `slide_layouts.py` (restored)
- **Generator Script**: `create_powerpoint_presentation_final.py` (updated)

## Design Features Maintained

✓ Professional academic design (your preferred style)
✓ UvA colors (red, navy, gray)
✓ Clean, not distracting layout
✓ All figures included (maps, graphs, charts)
✓ Consistent formatting throughout
✓ Ready for 10-minute presentation

## Technical Updates

- Fixed all slide numbering after new slide insertion
- Corrected slide variable references (slide6, slide7, slide8, etc.)
- Updated print statements to show [7/13] correctly
- Saved as v2 to avoid overwriting open file

## Ready for Presentation!

All nuances of the fire spread mechanisms are now captured, as requested. The slide provides clear explanations of:
- How each mechanism works mathematically
- Physical parameters involved
- Relative importance of each mechanism
- Supporting visualization from thesis

The presentation maintains the professional, clean design you preferred while adding the technical depth you needed for the fire spread mechanisms.








