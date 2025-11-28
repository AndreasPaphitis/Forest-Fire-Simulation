"""Design System for Innovative Presentation - Bold & Creative"""

from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

class Colors:
    UVA_RED = RGBColor(192, 0, 0)
    DARK_NAVY = RGBColor(0, 40, 85)
    MEDIUM_GRAY = RGBColor(100, 100, 100)
    LIGHT_GRAY = RGBColor(240, 240, 240)
    WHITE = RGBColor(255, 255, 255)
    ACCENT_GOLD = RGBColor(255, 200, 0)
    SUCCESS_GREEN = RGBColor(46, 125, 50)
    WARNING_ORANGE = RGBColor(255, 152, 0)
    NAVY_LIGHT = RGBColor(20, 60, 105)
    CORAL = RGBColor(255, 127, 80)
    TEAL = RGBColor(0, 128, 128)
    PURPLE = RGBColor(106, 27, 154)

class Fonts:
    TITLE_LARGE = Pt(44)
    TITLE_MEDIUM = Pt(36)
    TITLE_SMALL = Pt(32)
    SUBTITLE = Pt(24)
    BODY_LARGE = Pt(20)
    BODY_MEDIUM = Pt(18)
    BODY_SMALL = Pt(16)
    CAPTION = Pt(14)

class Layout:
    SLIDE_WIDTH = Inches(10)
    SLIDE_HEIGHT = Inches(7.5)
    MARGIN_LEFT = Inches(0.5)
    MARGIN_RIGHT = Inches(0.5)
    MARGIN_TOP = Inches(0.8)
    MARGIN_BOTTOM = Inches(0.5)
    CONTENT_WIDTH = SLIDE_WIDTH - MARGIN_LEFT - MARGIN_RIGHT
    CONTENT_HEIGHT = SLIDE_HEIGHT - MARGIN_TOP - MARGIN_BOTTOM
    HEADER_HEIGHT = Inches(0.8)
    SPACING_SMALL = Inches(0.2)
    SPACING_MEDIUM = Inches(0.4)
    ICON_SIZE = Inches(0.3)

def create_gradient_background(slide, color_start, color_stop):
    """Create a subtle gradient background."""
    bg = slide.background
    fill = bg.fill
    fill.gradient()
    fill.gradient_angle = 90.0
    
    # Unpack RGB values directly from RGBColor objects
    start_r, start_g, start_b = color_start
    stop_r, stop_g, stop_b = color_stop
    
    fill.gradient_stops[0].color.rgb = RGBColor(start_r, start_g, start_b)
    fill.gradient_stops[1].color.rgb = RGBColor(stop_r, stop_g, stop_b)

def add_diagonal_accent(slide, color=Colors.UVA_RED):
    """Add a diagonal accent element."""
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(8), Inches(-1),
        Inches(3), Inches(10)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    shape.rotation = 15

def add_circular_overlay(slide, left, top, size, color, opacity=0.3):
    """Add a circular overlay element."""
    circle = slide.shapes.add_shape(
        MSO_SHAPE.OVAL,
        left, top, size, size
    )
    circle.fill.solid()
    circle.fill.fore_color.rgb = color
    circle.fill.transparency = opacity
    circle.line.fill.background()
    return circle

def add_dynamic_header(slide, title_text, bg_color=Colors.UVA_RED, use_diagonal=True):
    """Add a dynamic header with optional diagonal split."""
    if use_diagonal:
        # Main header
        header = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            Inches(0), Inches(0),
            Layout.SLIDE_WIDTH, Inches(1)
        )
        header.fill.solid()
        header.fill.fore_color.rgb = bg_color
        header.line.fill.background()
        
        # Diagonal overlay
        overlay = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            Inches(7), Inches(-0.5),
            Inches(4), Inches(2)
        )
        overlay.fill.solid()
        overlay.fill.fore_color.rgb = Colors.DARK_NAVY
        overlay.line.fill.background()
        overlay.rotation = 15
    else:
        header = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            Inches(0), Inches(0),
            Layout.SLIDE_WIDTH, Inches(0.9)
        )
        header.fill.solid()
        header.fill.fore_color.rgb = bg_color
        header.line.fill.background()
    
    # Title text
    title_box = slide.shapes.add_textbox(
        Inches(0.7), Inches(0.2),
        Inches(7), Inches(0.5)
    )
    text_frame = title_box.text_frame
    p = text_frame.paragraphs[0]
    p.text = title_text
    p.font.size = Fonts.TITLE_SMALL
    p.font.bold = True
    p.font.color.rgb = Colors.WHITE
    p.alignment = PP_ALIGN.LEFT
    
    return header, title_box

def add_rounded_card(slide, left, top, width, height, color=Colors.LIGHT_GRAY):
    """Add a rounded card for content grouping."""
    card = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        left, top, width, height
    )
    card.fill.solid()
    card.fill.fore_color.rgb = color
    card.line.color.rgb = Colors.MEDIUM_GRAY
    card.line.width = Pt(1)
    return card

def add_shadow_effect(shape):
    """Add shadow effect to a shape (placeholder)."""
    # Note: python-pptx has limited shadow support
    # This is a placeholder for potential future enhancement
    pass

def format_title_text(text_frame, text, color=Colors.DARK_NAVY, size=Fonts.TITLE_SMALL, bold=True):
    """Format title text in a text frame."""
    p = text_frame.paragraphs[0]
    p.text = text
    p.font.size = size
    p.font.bold = bold
    p.font.color.rgb = color
    p.alignment = PP_ALIGN.LEFT

def format_body_text(text_frame, text, color=Colors.MEDIUM_GRAY, size=Fonts.BODY_LARGE):
    """Format body text in a text frame."""
    p = text_frame.paragraphs[0]
    p.text = text
    p.font.size = size
    p.font.color.rgb = color
    p.alignment = PP_ALIGN.LEFT
