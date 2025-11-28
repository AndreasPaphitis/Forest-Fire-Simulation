"""
Generate FINAL PowerPoint Presentation
Based on Professional Design + Graphs & Event Images
"""

import os
import sys
from pathlib import Path

# Add presentation directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from pptx import Presentation
from pptx.util import Inches, Pt
from presentation.design_system import Colors, Layout
from presentation.slide_layouts import (
    create_title_slide,
    create_two_column_content_slide,
    create_image_focused_slide,
    create_structured_info_slide,
    create_data_visualization_slide,
    create_comparison_slide,
    create_summary_slide,
    create_closing_slide
)

# Define paths
PROJECT_ROOT = Path(__file__).parent.parent
FIGURES_DIR = PROJECT_ROOT / "results" / "figures" / "thesis"
OUTPUT_DIR = PROJECT_ROOT / "presentation"
OUTPUT_FILE = OUTPUT_DIR / "Thesis_Presentation_Final_CITED.pptx"


def create_presentation():
    """Create the FINAL professional PowerPoint presentation with graphs and images."""
    
    print("\n" + "="*70)
    print("Creating FINAL Thesis Presentation with CITATIONS")
    print("Professional Design + Graphs + References")
    print("="*70)
    
    # Initialize presentation
    prs = Presentation()
    prs.slide_width = Layout.SLIDE_WIDTH
    prs.slide_height = Layout.SLIDE_HEIGHT
    
    # ========================================================================
    # SLIDE 1: TITLE SLIDE
    # ========================================================================
    print("\n[1/13] Creating title slide...")
    slide1 = prs.slides.add_slide(prs.slide_layouts[6])  # Blank layout
    
    create_title_slide(
        slide1,
        "Integrating High-Resolution LiDAR Data with\nCellular Automata for Wildfire Spread Prediction",
        [
            "Development, Calibration, and Validation",
            "A Case Study of the 2023 Tenerife Wildfire",
            "",
            "Andreas Paphitis",
            "University of Amsterdam, Graduate School of Life and Earth Sciences",
            "October 2025"
        ]
    )
    
    # ========================================================================
    # SLIDE 2: BACKGROUND & PROBLEM
    # ========================================================================
    print("[2/13] Creating background slide...")
    slide2 = prs.slides.add_slide(prs.slide_layouts[6])
    
    content_items = [
        ("12,000 hectares burned across 12 municipalities [EMSR]", Colors.UVA_RED),
        ("Most severe wildfire in Canary Islands in 40 years", Colors.UVA_RED),
        ("Over 12,000 residents evacuated [Copernicus EMS]", Colors.UVA_RED),
        ("Classified as 'sixth-generation' wildfire [Tedim et al., 2018]", Colors.UVA_RED),
        ("", Colors.WHITE),  # Spacer
        ("Traditional models failed to predict extreme behavior", Colors.WARNING_ORANGE),
        ("Models overlook vertical fire dynamics & ember transport [1,2]", Colors.WARNING_ORANGE),
        ("Operational tools (FARSITE, FlamMap) underperformed [3,4]", Colors.WARNING_ORANGE),
    ]
    
    key_stats = [
        ("Event", "2023 Tenerife Fire"),
        ("Duration", "Aug 15-26, 2023"),
        ("Classification", "6th Generation"),
    ]
    
    create_two_column_content_slide(
        slide2,
        "2023 Tenerife Wildfire: Background & Problem",
        content_items,
        key_stats
    )
    
    # ========================================================================
    # SLIDE 3: RESEARCH OBJECTIVES
    # ========================================================================
    print("[3/13] Creating objectives slide...")
    slide3 = prs.slides.add_slide(prs.slide_layouts[6])
    
    sections = [
        ("Objective 1: LiDAR Integration", [
            "• Integrate high-resolution LiDAR data into CA wildfire model",
            "• 3D fuel structure representation using Plant Area Density (PAD)",
            "• Research Question: How effectively can LiDAR PAD represent vertical fuel connectivity?"
        ]),
        ("Objective 2: Multi-Dimensional Fire Spread", [
            "• Develop framework with multiple fire spread mechanisms",
            "• Horizontal spread, vertical spread, and ember transport",
            "• Research Question: How do spread modes contribute to fire behavior in complex terrain?"
        ]),
    ]
    
    create_structured_info_slide(slide3, "Research Objectives & Questions", sections)
    
    # ========================================================================
    # SLIDE 4: STUDY AREA
    # ========================================================================
    print("[4/13] Creating study area slide...")
    slide4 = prs.slides.add_slide(prs.slide_layouts[6])
    
    content_text = """Location: Tenerife, Canary Islands
    
Key Features:
• Complex terrain with barrancos (deep ravines)
• Elevation: Sea level to 2,400m+
• Canary Island Pine (Pinus canariensis) dominant
• Prone to calima (Saharan dust) events

Fire Event: August 15-26, 2023
• Start: Arafo municipality, ~1,000m elevation
• Spread: Multi-directional across 12 municipalities
• Validation periods: EMSR Days 1-4 (Aug 18, 21, 24, 26)

Methodology:
• Data: 5m LiDAR, 5m DTM, EMSR fire perimeters
• Model: 3D Cellular Automata (20m resolution)
• Calibration: Two-stage framework (sensitivity + grid search)
• Validation: Temporal split-sample approach"""
    
    figure_path = FIGURES_DIR / "EMSR_Binary_Masks_4Panel_Academic.png"
    create_image_focused_slide(slide4, "Study Area & Methodology Overview", content_text, figure_path)
    
    # ========================================================================
    # SLIDE 5: LIDAR PROCESSING
    # ========================================================================
    print("[5/13] Creating LiDAR processing slide...")
    slide5 = prs.slides.add_slide(prs.slide_layouts[6])
    
    sections = [
        ("LiDAR Processing Pipeline", [
            "• Height normalization using PDAL HAG algorithm [5]",
            "• Normalized Relative Density (NRD) calculation [6]",
            "• PAD derivation via Beer-Lambert law (κ=0.6) [7]",
            "• 20 vertical layers at 2m intervals (0-40m)",
            "• Resampling: 5m → 20m resolution (16× reduction)"
        ]),
        ("3D CA Model Architecture", [
            "• Horizontal: Moore neighborhood, slope/wind factors [8]",
            "• Vertical: √(fuel_lower × fuel_upper) connectivity [9]",
            "• Ember: Exponential distance decay, wind-biased direction [10]",
            "• Terrain: Barranco wind channeling (2.5× amplification)"
        ]),
    ]
    
    figure_path = FIGURES_DIR / "Figure_1_LiDAR_Pipeline_Focused.png"
    create_structured_info_slide(slide5, "LiDAR Processing & Model Architecture", sections, figure_path)
    
    # ========================================================================
    # SLIDE 6: MODEL STRUCTURE & OPTIMIZATION
    # ========================================================================
    print("[6/13] Creating model structure slide...")
    slide6 = prs.slides.add_slide(prs.slide_layouts[6])
    
    sections = [
        ("Why Custom 3D CA Model?", [
            "1. LiDAR Integration: FARSITE/FlamMap/Prometheus use 2D fuel",
            "   classifications, cannot utilize continuous 3D PAD data",
            "2. Computational Efficiency: Sparse storage + pre-computed terrain",
            "   → 85% memory reduction, enables 100s of calibration runs",
            "3. Region-Specific: Canary Island pine needs custom parameters",
            "   (not North American fuel models, accounts for calima events)"
        ]),
        ("Key Optimizations", [
            "• Sparse matrix storage: 85% memory reduction vs dense arrays",
            "• Pre-computed terrain: Barranco detection, wind channeling",
            "• Resolution: 5m → 20m (16× reduction, preserves patterns)",
            "• Memory-mapped loading: <2s init vs 30+ s runtime",
            "• Grid: 609×609×20 layers (24.4M cells) efficiently managed"
        ]),
    ]
    
    create_structured_info_slide(slide6, "Model Structure & Computational Optimization", sections)
    
    # ========================================================================
    # SLIDE 7: FIRE SPREAD MECHANISMS
    # ========================================================================
    print("[7/13] Creating fire spread mechanisms slide...")
    slide7 = prs.slides.add_slide(prs.slide_layouts[6])
    
    content_text = """Three Fire Spread Mechanisms:

Horizontal Spread (Surface Fire):
• 8-neighbor Moore connectivity (N, NE, E, SE, S, SW, W, NW)
• Slope multiplicative factor: exp(0.1·slope_degrees)
• Wind multiplier: Higher in wind direction
• Barranco channeling: 2.5× amplification in ravines

Vertical Spread (Crown Fire):
• Layer-to-layer geometric mean: √(PAD_lower × PAD_upper)
• 20 vertical layers at 2m intervals (0-40m)
• Fuel continuity drives vertical propagation

Ember Transport (Spotting):
• Exponential distance decay: exp(-dist/param)
• Wind-biased direction kernel
• Stochastic ignition probability
• Critical for long-distance spread across discontinuities"""
    
    figure_path = FIGURES_DIR / "Figure_Fire_Spread_Mode_Pie_Charts.png"
    create_image_focused_slide(slide7, "Fire Spread Mechanisms", content_text, figure_path)
    
    # ========================================================================
    # SLIDE 8: CALIBRATION APPROACH
    # ========================================================================
    print("[8/13] Creating calibration slide...")
    slide8 = prs.slides.add_slide(prs.slide_layouts[6])
    
    content_text = """Two-Stage Calibration Framework:

Stage 1: Sensitivity Analysis
• Range-based analysis: 9 points × 16 parameters
• Objective: Modified Dice coefficient
• Result: Identified top 4 critical parameters

Stage 2: Grid Search Optimization
• Focused search: 3 points × 4 parameters = 81 combinations
• Calibration target: EMSR Days 1-2 (Aug 18-21)
• Validation target: EMSR Days 3-4 (Aug 24-26)

Computational Efficiency:
• Reduced from 3¹⁶ ≈ 43 million to 81 simulations
• 6 orders of magnitude reduction
• Execution time: ~53 minutes per simulation"""
    
    figure_path = FIGURES_DIR / "Figure_Calibration_Priority_Matrix.png"
    create_data_visualization_slide(
        slide8,
        "Calibration Approach",
        content_text,
        figure_path,
        metrics=None
    )
    
    # ========================================================================
    # SLIDE 9: SENSITIVITY ANALYSIS
    # ========================================================================
    print("[9/14] Creating sensitivity analysis slide...")
    slide9 = prs.slides.add_slide(prs.slide_layouts[6])
    
    content_text = """Parameter Sensitivity Hierarchy:

Top 5 Most Sensitive Parameters:
1. spread_probability: 1.406 (8.7× more sensitive)
2. fuel_consumption_rate: 0.161
3. ember_probability: 0.116
4. ember_ignition: 0.056
5. fuel_moisture_baseline: 0.038

Key Insights:
• spread_probability dominates fire behavior
• Ember system parameters collectively significant (0.172)
• Clear hierarchy enables focused calibration
• Terrain and fuel parameters show secondary importance"""
    
    figure_path = FIGURES_DIR / "Figure_Sensitivity_Parameter_Ranking.png"
    if not figure_path.exists():
        figure_path = FIGURES_DIR / "Figure_Top5_Parameters_Focus.png"
    
    create_data_visualization_slide(
        slide9,
        "Sensitivity Analysis Results",
        content_text,
        figure_path,
        metrics=[
            ("Top Param", "1.406", Colors.UVA_RED),
            ("2nd Param", "0.161", Colors.DARK_NAVY),
            ("Ember Sum", "0.172", Colors.ACCENT_GOLD),
        ]
    )
    
    # ========================================================================
    # SLIDE 10: VALIDATION RESULTS
    # ========================================================================
    print("[10/14] Creating validation slide...")
    slide10 = prs.slides.add_slide(prs.slide_layouts[6])
    
    content_text = """Spatial Performance (Rank 2 Parameters):

Calibration Period:
• Days 1-2: Objective function optimized

Validation Period:
• Day 3: Objective = 0.690
• Day 4: Objective = 0.486
• Improvement: 29.6% (Day 3 → Day 4)

Parameter Selection Rationale:
• Rank 1: Error 0.513, spread_prob = 0.95 (unrealistic)
• Rank 2: Error 0.536, spread_prob = 0.775 (selected)
• Trade-off: Slightly higher error for physical realism

Execution Time:
• ~53 minutes per simulation (20m resolution)"""
    
    figure_path = FIGURES_DIR / "Figure_19_CORRECTED_Spatial_Validation_Maps.png"
    if not figure_path.exists():
        figure_path = FIGURES_DIR / "Figure_12_Validation_Summary.png"
    
    create_data_visualization_slide(
        slide10,
        "Validation Results",
        content_text,
        figure_path,
        metrics=[
            ("Day 3", "0.690", Colors.WARNING_ORANGE),
            ("Day 4", "0.486", Colors.SUCCESS_GREEN),
            ("Δ", "-29.6%", Colors.DARK_NAVY),
        ]
    )
    
    # ========================================================================
    # SLIDE 11: KEY FINDINGS & LIMITATIONS
    # ========================================================================
    print("[11/14] Creating findings slide...")
    slide11 = prs.slides.add_slide(prs.slide_layouts[6])
    
    successes = [
        "Successful LiDAR PAD integration for 3D fuel structure",
        "Systematic calibration framework (43M → 81 simulations)",
        "Horizontal spread: 23.7% contribution, 83% efficiency",
        "Identified critical parameters via sensitivity analysis",
        "Framework demonstrates feasibility of approach",
    ]
    
    warnings = [
        "Vertical spread: Only 3.8% (expected 30-50%)",
        "Ember spread: 43.0% (expected 10-20%)",
        "Ember efficiency: 150.7% indicates overfitting",
        "Compensating errors rather than physical accuracy",
        "Need multi-objective calibration + fuel constraints",
    ]
    
    create_comparison_slide(slide11, "Key Findings & Limitations", successes, warnings)
    
    # ========================================================================
    # SLIDE 12: CONCLUSIONS
    # ========================================================================
    print("[12/14] Creating conclusions slide...")
    slide12 = prs.slides.add_slide(prs.slide_layouts[6])
    
    sections = [
        (1, "Research Questions Addressed", [
            "Q1: LiDAR PAD successfully represents vertical fuel connectivity",
            "     → Framework operational, requires parameter refinement",
            "Q2: Spread modes quantified (H:23.7%, V:3.8%, E:43.0%)",
            "     → Reveals need for improved suppression mechanisms"
        ]),
        (2, "Main Contributions", [
            "• First 3D CA wildfire model with continuous LiDAR PAD integration",
            "• Systematic two-stage calibration framework",
            "• Honest validation revealing overfitting challenges",
            "• Quantitative analysis of fire spread mode contributions"
        ]),
        (3, "Future Work", [
            "• Multi-objective calibration (spatial + mechanistic constraints)",
            "• Fire suppression mechanisms and fuel consumption limits",
            "• Validation against additional fire events",
            "• Integration with weather forecasting systems"
        ]),
    ]
    
    create_summary_slide(slide12, "Conclusions & Future Directions", sections)
    
    # ========================================================================
    # SLIDE 13: ACKNOWLEDGMENTS
    # ========================================================================
    print("[13/14] Creating acknowledgments slide...")
    slide13 = prs.slides.add_slide(prs.slide_layouts[6])
    
    content_lines = [
        "Supervisor: dr. A.C. Seijmonsbergen",
        "Assessor: dr. Yifang Shi",
        "",
        "Data Sources:",
        "• PNOA-IGN (LiDAR point cloud data)",
        "• Copernicus EMSR (Fire perimeter delineations)",
        "• IGN Spain (Digital Terrain Models)",
        "",
        "University of Amsterdam",
        "Graduate School of Life and Earth Sciences",
        "Institute for Biodiversity and Ecosystem Dynamics"
    ]
    
    create_closing_slide(slide13, "Acknowledgments", content_lines, style='acknowledgment')
    
    # ========================================================================
    # SLIDE 14: REFERENCES
    # ========================================================================
    print("[14/15] Creating references slide...")
    slide14 = prs.slides.add_slide(prs.slide_layouts[6])
    
    # Add header
    from presentation.design_system import add_colored_header
    add_colored_header(slide14, "Key References", Colors.DARK_NAVY)
    
    # References content
    references = [
        "[1] Cruz & Alexander (2013). Uncertainty associated with model predictions of surface and crown fire rates of spread. Environmental Modelling & Software.",
        "[2] Sullivan (2009). Wildland surface fire spread modelling, 1990-2007. International Journal of Wildland Fire.",
        "[3] Finney (2004). FARSITE: Fire Area Simulator—Model Development and Evaluation. USDA Forest Service Research Paper RMRS-RP-4.",
        "[4] Finney (2006). An overview of FlamMap fire modeling capabilities. In: Andrews, P.L. & Butler, B.W. (Eds.). Fuels Management.",
        "[5] PDAL Contributors (2023). Point Data Abstraction Library (PDAL). https://pdal.io",
        "[6] MacArthur & Horn (1969). Foliage profile by vertical measurements. Ecology.",
        "[7] Campbell & Norman (1998). An Introduction to Environmental Biophysics. Springer.",
        "[8] Rothermel (1972). A mathematical model for predicting fire spread in wildland fuels. USDA Forest Service Research Paper INT-115.",
        "[9] Van Wagner (1977). Conditions for the start and spread of crown fire. Canadian Journal of Forest Research.",
        "[10] Albini (1979). Spot fire distance from burning trees—a predictive model. USDA Forest Service Research Paper INT-56.",
        "",
        "Data Sources:",
        "• PNOA-IGN: Plan Nacional de Ortofotografía Aérea, Instituto Geográfico Nacional (LiDAR)",
        "• Copernicus EMSR706: Emergency Management Service Rapid Mapping (Fire perimeters)",
        "• IGN España: Instituto Geográfico Nacional España (Digital Terrain Models)"
    ]
    
    # Add references text
    y_pos = Inches(1.2)
    for ref in references:
        ref_box = slide14.shapes.add_textbox(Inches(0.4), y_pos, Inches(9.2), Inches(0.28))
        text_frame = ref_box.text_frame
        text_frame.word_wrap = True
        p = text_frame.paragraphs[0]
        p.text = ref
        if ref.startswith('['):
            p.font.size = Pt(11)
            p.font.color.rgb = Colors.MEDIUM_GRAY
        elif ref.startswith('•') or ref == "Data Sources:":
            p.font.size = Pt(13)
            p.font.bold = (ref == "Data Sources:")
            p.font.color.rgb = Colors.DARK_NAVY if ref == "Data Sources:" else Colors.MEDIUM_GRAY
        else:
            p.font.size = Pt(11)
            p.font.color.rgb = Colors.MEDIUM_GRAY
        y_pos += Inches(0.32) if ref.startswith('[') else Inches(0.35)
    
    # ========================================================================
    # SLIDE 15: QUESTIONS
    # ========================================================================
    print("[15/15] Creating thank you slide...")
    slide15 = prs.slides.add_slide(prs.slide_layouts[6])
    
    content_lines = [
        "",
        "Repository: github.com/AndreasPaphitis/Forest-Fire-Simulation",
        "",
        "Contact: andreas.paphitis@student.uva.nl"
    ]
    
    create_closing_slide(slide15, "Thank You\nQuestions & Discussion", content_lines, style='thankyou')
    
    # ========================================================================
    # SAVE PRESENTATION
    # ========================================================================
    print("\n" + "="*70)
    print("Saving presentation...")
    prs.save(str(OUTPUT_FILE))
    
    print("\n[SUCCESS] FINAL presentation with CITATIONS created!")
    print(f"[FILE] Saved to: {OUTPUT_FILE}")
    print(f"[INFO] Total slides: {len(prs.slides)}")
    print(f"[INFO] Design: Professional (the version you liked best)")
    print(f"\n[INCLUDES]")
    print(f"✓ Professional design (clean, not distracting)")
    print(f"✓ Fire spread mechanisms explained (Slide 7)")
    print(f"✓ IN-TEXT CITATIONS added to avoid plagiarism")
    print(f"✓ REFERENCES SLIDE (Slide 14) with key citations")
    print(f"✓ Fire event images (EMSR 4-panel map)")
    print(f"✓ Sensitivity ranking graph")
    print(f"✓ Validation maps")
    print(f"✓ Fire spread mode pie charts")
    print(f"✓ All key figures from thesis")
    print(f"\n[NEXT STEPS]")
    print(f"1. Review in-text citations and references")
    print(f"2. Verify citations match your thesis bibliography")
    print(f"3. Add any additional citations needed")
    print(f"4. Ready for defense!")
    print("="*70 + "\n")


if __name__ == "__main__":
    create_presentation()

