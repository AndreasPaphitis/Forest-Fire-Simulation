"""
Create a PowerPoint slide with the four-quadrant methodology layout.
"""

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor

# Create presentation
prs = Presentation()
prs.slide_width = Inches(10)
prs.slide_height = Inches(7.5)

# Add blank slide
blank_slide_layout = prs.slide_layouts[6]  # Blank layout
slide = prs.slides.add_slide(blank_slide_layout)

# Colors
UVA_NAVY = RGBColor(0, 53, 107)
LIGHT_BLUE = RGBColor(232, 244, 248)
LIGHT_GREEN = RGBColor(232, 245, 233)
LIGHT_ORANGE = RGBColor(255, 243, 224)
LIGHT_PURPLE = RGBColor(243, 229, 245)
DARK_GRAY = RGBColor(44, 44, 44)
UVA_RED = RGBColor(224, 60, 49)

# ========== TITLE ==========
title_box = slide.shapes.add_shape(
    1,  # Rectangle
    Inches(0), Inches(0), Inches(10), Inches(0.8)
)
title_box.fill.solid()
title_box.fill.fore_color.rgb = UVA_RED
title_box.line.color.rgb = UVA_RED

title_frame = title_box.text_frame
title_frame.text = "Methodology Overview"
title_frame.paragraphs[0].font.size = Pt(32)
title_frame.paragraphs[0].font.bold = True
title_frame.paragraphs[0].font.color.rgb = RGBColor(255, 255, 255)
title_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
title_frame.vertical_anchor = 1  # Middle

# ========== QUADRANT 1: Data & Model (Top Left) ==========
q1 = slide.shapes.add_shape(
    1,  # Rectangle
    Inches(0.3), Inches(1.0), Inches(4.7), Inches(3.0)
)
q1.fill.solid()
q1.fill.fore_color.rgb = LIGHT_BLUE
q1.line.color.rgb = UVA_NAVY
q1.line.width = Pt(2)

q1_frame = q1.text_frame
q1_frame.word_wrap = True
q1_frame.margin_top = Inches(0.1)
q1_frame.margin_left = Inches(0.15)

# Q1 Title
p = q1_frame.paragraphs[0]
p.text = "Data & Model"
p.font.size = Pt(20)
p.font.bold = True
p.font.color.rgb = UVA_NAVY
p.space_after = Pt(10)

# Q1 Content
text_content = [
    ("Data Sources:", True),
    ("• LiDAR: 5m → PAD (3D fuel structure)", False),
    ("• Terrain: 5m DTM", False),
    ("• Fire: EMSR 685 delineations", False),
    ("", False),
    ("3D CA Model:", True),
    ("• 20m resolution, 20 layers (0-40m)", False),
    ("• 3 spread mechanisms:", False),
    ("  Horizontal, Vertical, Ember", False),
]

for text, is_bold in text_content:
    p = q1_frame.add_paragraph()
    p.text = text
    p.font.size = Pt(14)
    p.font.bold = is_bold
    p.font.color.rgb = DARK_GRAY
    p.space_after = Pt(4)

# ========== QUADRANT 2: Objective Function (Top Right) ==========
q2 = slide.shapes.add_shape(
    1,  # Rectangle
    Inches(5.2), Inches(1.0), Inches(4.5), Inches(3.0)
)
q2.fill.solid()
q2.fill.fore_color.rgb = LIGHT_GREEN
q2.line.color.rgb = UVA_NAVY
q2.line.width = Pt(2)

q2_frame = q2.text_frame
q2_frame.word_wrap = True
q2_frame.margin_top = Inches(0.1)
q2_frame.margin_left = Inches(0.15)

# Q2 Title
p = q2_frame.paragraphs[0]
p.text = "Objective Function"
p.font.size = Pt(20)
p.font.bold = True
p.font.color.rgb = UVA_NAVY
p.alignment = PP_ALIGN.CENTER
p.space_after = Pt(10)

# Q2 Equation
p = q2_frame.add_paragraph()
p.text = "Minimize: (1 - Dice) + P"
p.font.size = Pt(18)
p.font.bold = True
p.font.color.rgb = DARK_GRAY
p.alignment = PP_ALIGN.CENTER
p.space_after = Pt(8)

p = q2_frame.add_paragraph()
p.text = "Dice = 2|A∩B| / (|A|+|B|)"
p.font.size = Pt(14)
p.font.color.rgb = DARK_GRAY
p.alignment = PP_ALIGN.CENTER
p.space_after = Pt(6)

p = q2_frame.add_paragraph()
p.text = "P = 2(r-2)² if r>2, else P=0"
p.font.size = Pt(12)
p.font.color.rgb = DARK_GRAY
p.alignment = PP_ALIGN.CENTER
p.space_after = Pt(12)

# Rationale
p = q2_frame.add_paragraph()
p.text = "Rationale:"
p.font.size = Pt(14)
p.font.bold = True
p.font.color.rgb = DARK_GRAY
p.space_after = Pt(4)

rationale_items = [
    "• Balances spatial accuracy",
    "• Prevents unrealistic spread",
    "• Standard in wildfire validation"
]

for item in rationale_items:
    p = q2_frame.add_paragraph()
    p.text = item
    p.font.size = Pt(12)
    p.font.color.rgb = DARK_GRAY
    p.space_after = Pt(3)

# ========== QUADRANT 3: Calibration (Bottom Left) ==========
q3 = slide.shapes.add_shape(
    1,  # Rectangle
    Inches(0.3), Inches(4.2), Inches(4.7), Inches(3.0)
)
q3.fill.solid()
q3.fill.fore_color.rgb = LIGHT_ORANGE
q3.line.color.rgb = UVA_NAVY
q3.line.width = Pt(2)

q3_frame = q3.text_frame
q3_frame.word_wrap = True
q3_frame.margin_top = Inches(0.1)
q3_frame.margin_left = Inches(0.15)

# Q3 Title
p = q3_frame.paragraphs[0]
p.text = "Calibration Framework"
p.font.size = Pt(20)
p.font.bold = True
p.font.color.rgb = UVA_NAVY
p.space_after = Pt(10)

# Q3 Content
p = q3_frame.add_paragraph()
p.text = "Two-Stage Approach:"
p.font.size = Pt(14)
p.font.bold = True
p.font.color.rgb = DARK_GRAY
p.space_after = Pt(6)

p = q3_frame.add_paragraph()
p.text = "Stage 1: Sensitivity Analysis"
p.font.size = Pt(14)
p.font.bold = True
p.font.color.rgb = RGBColor(245, 124, 0)  # Orange
p.space_after = Pt(4)

stage1_items = [
    "  • 16 parameters tested",
    "  • Range-based screening",
    "  • Top 4 parameters selected"
]

for item in stage1_items:
    p = q3_frame.add_paragraph()
    p.text = item
    p.font.size = Pt(12)
    p.font.color.rgb = DARK_GRAY
    p.space_after = Pt(3)

p = q3_frame.add_paragraph()
p.text = "Stage 2: Grid Search"
p.font.size = Pt(14)
p.font.bold = True
p.font.color.rgb = RGBColor(25, 118, 210)  # Blue
p.space_after = Pt(4)

stage2_items = [
    "  • 3 points × 4 params = 81 runs",
    "  • Modified Dice optimization"
]

for item in stage2_items:
    p = q3_frame.add_paragraph()
    p.text = item
    p.font.size = Pt(12)
    p.font.color.rgb = DARK_GRAY
    p.space_after = Pt(3)

p = q3_frame.add_paragraph()
p.text = ""
p.space_after = Pt(4)

p = q3_frame.add_paragraph()
p.text = "Training: Days 1-2 (Aug 18-21)"
p.font.size = Pt(12)
p.font.italic = True
p.font.color.rgb = DARK_GRAY

# ========== QUADRANT 4: Validation (Bottom Right) ==========
q4 = slide.shapes.add_shape(
    1,  # Rectangle
    Inches(5.2), Inches(4.2), Inches(4.5), Inches(3.0)
)
q4.fill.solid()
q4.fill.fore_color.rgb = LIGHT_PURPLE
q4.line.color.rgb = UVA_NAVY
q4.line.width = Pt(2)

q4_frame = q4.text_frame
q4_frame.word_wrap = True
q4_frame.margin_top = Inches(0.1)
q4_frame.margin_left = Inches(0.15)

# Q4 Title
p = q4_frame.paragraphs[0]
p.text = "Validation"
p.font.size = Pt(20)
p.font.bold = True
p.font.color.rgb = UVA_NAVY
p.space_after = Pt(10)

# Q4 Content
p = q4_frame.add_paragraph()
p.text = "Out-of-Sample Testing:"
p.font.size = Pt(14)
p.font.bold = True
p.font.color.rgb = DARK_GRAY
p.space_after = Pt(6)

p = q4_frame.add_paragraph()
p.text = "Test Period:"
p.font.size = Pt(13)
p.font.bold = True
p.font.color.rgb = DARK_GRAY
p.space_after = Pt(3)

p = q4_frame.add_paragraph()
p.text = "Days 3-4 (Aug 24-26)"
p.font.size = Pt(12)
p.font.color.rgb = DARK_GRAY
p.space_after = Pt(8)

p = q4_frame.add_paragraph()
p.text = "Performance Metrics:"
p.font.size = Pt(13)
p.font.bold = True
p.font.color.rgb = DARK_GRAY
p.space_after = Pt(4)

metrics = [
    "• Day 3: Dice = 0.690",
    "• Day 4: Dice = 0.486",
    "• Improvement: +29.6%"
]

for metric in metrics:
    p = q4_frame.add_paragraph()
    p.text = metric
    p.font.size = Pt(12)
    p.font.color.rgb = DARK_GRAY
    p.space_after = Pt(3)

p = q4_frame.add_paragraph()
p.text = ""
p.space_after = Pt(8)

p = q4_frame.add_paragraph()
p.text = "Ensures model generalization\nto unseen fire events"
p.font.size = Pt(12)
p.font.italic = True
p.font.color.rgb = DARK_GRAY

# Save
prs.save('presentation/Methodology_Overview_Slide.pptx')
print("✅ PowerPoint slide created: Methodology_Overview_Slide.pptx")
print("📊 Four-quadrant layout with all methodology details")
print("🎯 Ready to insert into your presentation!")






