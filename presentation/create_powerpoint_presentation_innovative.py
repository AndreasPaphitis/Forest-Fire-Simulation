"""Create Innovative PowerPoint Presentation with Fire Spread Mechanisms"""

from pptx import Presentation
from pptx.util import Inches, Pt
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Import design system and layouts
from design_system_innovative import Colors, Fonts, Layout
from slide_layouts_innovative import (
    create_hero_title_slide,
    create_split_content_slide,
    create_image_overlay_slide,
    create_data_showcase_slide,
    create_comparison_cards_slide,
    create_summary_overlay_slide,
    create_closing_gradient_slide
)

# Define paths
PROJECT_ROOT = Path(__file__).parent.parent
FIGURES_DIR = PROJECT_ROOT / "results" / "figures" / "thesis"
OUTPUT_DIR = PROJECT_ROOT / "presentation"
OUTPUT_FILE = OUTPUT_DIR / "Thesis_Presentation_Innovative_CITED.pptx"


def create_presentation():
    """Create the INNOVATIVE PowerPoint presentation with fire spread mechanisms."""
    
    print("="*70)
    print("Creating INNOVATIVE Thesis Presentation with CITATIONS")
    print("Bold & Creative Design + References")
    print("="*70)
    print()
    
    # Create presentation
    prs = Presentation()
    prs.slide_width = Layout.SLIDE_WIDTH
    prs.slide_height = Layout.SLIDE_HEIGHT
    
    # ========================================================================
    # SLIDE 1: TITLE SLIDE
    # ========================================================================
    print("[1/14] Creating title slide...")
    slide1 = prs.slides.add_slide(prs.slide_layouts[6])
    
    title_text = "High-Resolution Wildfire Modelling:\nIntegrating LiDAR-Derived 3D Fuel Structure"
    subtitle_lines = [
        "Master's Thesis Defense",
        "Andreas Paphitis",
        "University of Amsterdam",
        "Graduate School of Life and Earth Sciences",
        "November 2024"
    ]
    
    create_hero_title_slide(slide1, title_text, subtitle_lines)
    
    # ========================================================================
    # SLIDE 2: BACKGROUND & PROBLEM
    # ========================================================================
    print("[2/14] Creating background slide...")
    slide2 = prs.slides.add_slide(prs.slide_layouts[6])
    
    content_items = [
        ("Climate change: Wildfire seasons extending (+18.7% longer) [Tedim et al., 2018]", Colors.WARNING_ORANGE),
        ("Mediterranean: High-risk region for extreme fire behavior [Copernicus EMS]", Colors.UVA_RED),
        ("Current models: Limited by 2D fuel classifications [1,2,3,4]", Colors.DARK_NAVY),
        ("", Colors.WHITE),
        ("Opportunity: High-resolution LiDAR data now available", Colors.SUCCESS_GREEN),
        ("Solution: 3D Cellular Automata with vertical fuel structure", Colors.SUCCESS_GREEN),
        ("Challenge: Calibration complexity & overfitting risks [6]", Colors.WARNING_ORANGE),
    ]
    
    key_stats = [
        ("Fire Season", "+18.7% longer"),
        ("Study Area", "Tenerife 2023"),
        ("Resolution", "20m, 20 layers")
    ]
    
    create_split_content_slide(slide2, "Background & Problem Statement", content_items, key_stats)
    
    # ========================================================================
    # SLIDE 3: RESEARCH OBJECTIVES
    # ========================================================================
    print("[3/14] Creating objectives slide...")
    slide3 = prs.slides.add_slide(prs.slide_layouts[6])
    
    content_items = [
        ("Research Question 1:", Colors.UVA_RED),
        ("Can LiDAR-derived Plant Area Density (PAD) effectively", Colors.MEDIUM_GRAY),
        ("represent vertical fuel connectivity in fire spread models?", Colors.MEDIUM_GRAY),
        ("", Colors.WHITE),
        ("Research Question 2:", Colors.UVA_RED),
        ("What are the relative contributions of horizontal, vertical,", Colors.MEDIUM_GRAY),
        ("and ember-mediated spread in 3D fire behavior?", Colors.MEDIUM_GRAY),
        ("", Colors.WHITE),
        ("Approach:", Colors.DARK_NAVY),
        ("• Systematic two-stage calibration framework", Colors.MEDIUM_GRAY),
        ("• Temporal split-sample validation (Days 1-4)", Colors.MEDIUM_GRAY),
        ("• Quantification of spread mode contributions", Colors.MEDIUM_GRAY),
    ]
    
    create_split_content_slide(slide3, "Research Objectives", content_items, key_stats=None)
    
    # ========================================================================
    # SLIDE 4: STUDY AREA & METHODOLOGY
    # ========================================================================
    print("[4/14] Creating study area slide...")
    slide4 = prs.slides.add_slide(prs.slide_layouts[6])
    
    content_text = """Study Area: Tenerife, Canary Islands

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
    create_image_overlay_slide(slide4, "Study Area & Methodology Overview", content_text, figure_path)
    
    # ========================================================================
    # SLIDE 5: LIDAR PROCESSING & MODEL ARCHITECTURE
    # ========================================================================
    print("[5/14] Creating LiDAR processing slide...")
    slide5 = prs.slides.add_slide(prs.slide_layouts[6])
    
    content_items = [
        ("LiDAR Processing Pipeline:", Colors.UVA_RED),
        ("• Height normalization using PDAL HAG algorithm [5]", Colors.MEDIUM_GRAY),
        ("• Normalized Relative Density (NRD) calculation [6]", Colors.MEDIUM_GRAY),
        ("• PAD derivation via Beer-Lambert law (κ=0.6) [7]", Colors.MEDIUM_GRAY),
        ("• 20 vertical layers at 2m intervals (0-40m)", Colors.MEDIUM_GRAY),
        ("• Resampling: 5m → 20m resolution (16× reduction)", Colors.MEDIUM_GRAY),
        ("", Colors.WHITE),
        ("3D CA Model Architecture:", Colors.DARK_NAVY),
        ("• Horizontal: Moore neighborhood, slope/wind factors [8]", Colors.MEDIUM_GRAY),
        ("• Vertical: √(fuel_lower × fuel_upper) connectivity [9]", Colors.MEDIUM_GRAY),
        ("• Ember: Exponential decay, wind-biased direction [10]", Colors.MEDIUM_GRAY),
        ("• Terrain: Barranco wind channeling (2.5× amplification)", Colors.MEDIUM_GRAY),
    ]
    
    create_split_content_slide(slide5, "LiDAR Processing & Model Architecture", content_items, key_stats=None)
    
    # ========================================================================
    # SLIDE 6: MODEL STRUCTURE & OPTIMIZATION
    # ========================================================================
    print("[6/14] Creating model structure slide...")
    slide6 = prs.slides.add_slide(prs.slide_layouts[6])
    
    content_items = [
        ("Why Custom 3D CA Model?", Colors.UVA_RED),
        ("1. LiDAR Integration: FARSITE/FlamMap use 2D fuel", Colors.MEDIUM_GRAY),
        ("   classifications, cannot utilize continuous 3D PAD data", Colors.MEDIUM_GRAY),
        ("2. Computational Efficiency: Sparse storage enables", Colors.MEDIUM_GRAY),
        ("   100s of calibration runs (85% memory reduction)", Colors.MEDIUM_GRAY),
        ("3. Region-Specific: Canary Island pine parameters", Colors.MEDIUM_GRAY),
        ("   (not North American models, accounts for calima)", Colors.MEDIUM_GRAY),
        ("", Colors.WHITE),
        ("Key Optimizations:", Colors.DARK_NAVY),
        ("• Sparse matrix storage: 85% memory reduction", Colors.MEDIUM_GRAY),
        ("• Pre-computed terrain: Barranco detection, channeling", Colors.MEDIUM_GRAY),
        ("• Resolution: 5m → 20m (16× reduction, preserves patterns)", Colors.MEDIUM_GRAY),
        ("• Grid: 609×609×20 layers (24.4M cells) efficiently managed", Colors.MEDIUM_GRAY),
    ]
    
    create_split_content_slide(slide6, "Model Structure & Computational Optimization", content_items, key_stats=None)
    
    # ========================================================================
    # SLIDE 7: FIRE SPREAD MECHANISMS
    # ========================================================================
    print("[7/14] Creating fire spread mechanisms slide...")
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
    create_image_overlay_slide(slide7, "Fire Spread Mechanisms", content_text, figure_path)
    
    # ========================================================================
    # SLIDE 8: CALIBRATION APPROACH
    # ========================================================================
    print("[8/14] Creating calibration slide...")
    slide8 = prs.slides.add_slide(prs.slide_layouts[6])
    
    content_text = """Two-Stage Calibration Framework:

Stage 1: Sensitivity Analysis
• Range-based analysis: 9 points × 16 parameters
• Objective: Modified Dice coefficient
• Result: Identified top 4 critical parameters

Stage 2: Grid Search Optimization
• 7³ = 343 combinations on top parameters
• Reduced from 3¹⁶ ≈ 43M to 81 simulations
• 6 orders of magnitude reduction
• Objective: Maximize modified Dice
• Coverage metrics: F1, intersection area

Challenge: Overfitting Risk
• Temporal splits (calibration vs validation days)
• Mechanistic metrics alongside statistical
• Trade-off: Physical realism vs empirical fit

Computational Efficiency:
• ~53 minutes per simulation
• Calibration target: EMSR Days 1-2 (Aug 18-21)
• Validation target: EMSR Days 3-4 (Aug 24-26)"""
    
    figure_path = FIGURES_DIR / "Figure_Calibration_Priority_Matrix.png"
    create_data_showcase_slide(slide8, "Calibration Approach", content_text, figure_path, metrics=None)
    
    # ========================================================================
    # SLIDE 9: SENSITIVITY ANALYSIS RESULTS
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
• Terrain and fuel parameters show secondary importance

Results:
• Identified top 4 parameters for grid search
• Reduced calibration space by 6 orders of magnitude
• Systematic approach to parameter selection"""
    
    figure_path = FIGURES_DIR / "Figure_Sensitivity_Parameter_Ranking.png"
    if not figure_path.exists():
        figure_path = FIGURES_DIR / "Figure_Top5_Parameters_Focus.png"
    
    create_data_showcase_slide(
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
    print("[10/14] Creating validation results slide...")
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

Spread Mode Contributions:
• Horizontal: 23.7% (expected 40-60%)
• Vertical: 3.8% (expected 30-50%)
• Ember: 43.0% (expected 10-20%)

Execution Time:
• ~53 minutes per simulation (20m resolution)"""
    
    figure_path = FIGURES_DIR / "Figure_19_CORRECTED_Spatial_Validation_Maps.png"
    if not figure_path.exists():
        figure_path = FIGURES_DIR / "Figure_12_Validation_Summary.png"
    
    create_data_showcase_slide(
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
    
    create_comparison_cards_slide(slide11, "Key Findings & Limitations", successes, warnings)
    
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
        (2, "Key Contributions", [
            "• First LiDAR-derived 3D CA model for Mediterranean wildfires",
            "• Systematic two-stage calibration framework",
            "• Computational optimizations: 85% memory reduction",
            "• Quantitative assessment of spread mode contributions"
        ]),
        (3, "Future Work", [
            "• Multi-objective calibration (spatial + mechanistic constraints)",
            "• Fire suppression mechanisms and fuel consumption limits",
            "• Validation against additional fire events",
            "• Integration with weather forecasting systems"
        ]),
    ]
    
    create_summary_overlay_slide(slide12, "Conclusions & Future Directions", sections)
    
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
    
    create_closing_gradient_slide(slide13, "Acknowledgments", content_lines, style='acknowledgment')
    
    # ========================================================================
    # SLIDE 14: REFERENCES
    # ========================================================================
    print("[14/15] Creating references slide...")
    slide14 = prs.slides.add_slide(prs.slide_layouts[6])
    
    # Add header using innovative design
    from design_system_innovative import add_dynamic_header
    from pptx.util import Pt
    add_dynamic_header(slide14, "Key References", Colors.DARK_NAVY, use_diagonal=False)
    
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
    y_pos = Inches(1.3)
    for ref in references:
        ref_box = slide14.shapes.add_textbox(Inches(0.5), y_pos, Inches(9), Inches(0.28))
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
    
    create_closing_gradient_slide(slide15, "Thank You\nQuestions & Discussion", content_lines, style='thankyou')
    
    # ========================================================================
    # SAVE PRESENTATION
    # ========================================================================
    print("\n" + "="*70)
    print("Saving presentation...")
    prs.save(str(OUTPUT_FILE))
    
    print()
    print("[SUCCESS] INNOVATIVE presentation with CITATIONS created!")
    print(f"[FILE] Saved to: {OUTPUT_FILE}")
    print(f"[INFO] Total slides: {len(prs.slides)}")
    print("[INFO] Design: Innovative (bold & creative)")
    print()
    print("[INCLUDES]")
    print("✓ Bold & creative design")
    print("✓ Fire spread mechanisms explained (Slide 7)")
    print("✓ IN-TEXT CITATIONS added to avoid plagiarism")
    print("✓ REFERENCES SLIDE (Slide 14) with key citations")
    print("✓ Fire event images (EMSR 4-panel map)")
    print("✓ Sensitivity ranking graph")
    print("✓ Validation maps")
    print("✓ Fire spread mode pie charts")
    print("✓ All key figures from thesis")
    print()
    print("[TWO CHOICES READY WITH CITATIONS]")
    print("1. Thesis_Presentation_Final_CITED.pptx (Professional)")
    print("2. Thesis_Presentation_Innovative_CITED.pptx (Bold & Creative)")
    print("="*70)


if __name__ == "__main__":
    create_presentation()
