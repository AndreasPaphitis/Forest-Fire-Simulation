#!/usr/bin/env python3
"""
Forest Fire Simulation Documentation PDF Generator

This script converts the Forest Fire Simulation documentation into PDF files
for easy distribution and offline viewing.

Requirements:
- Python 3.6+
- pip (Python package manager)

Features:
- Converts Markdown documentation to PDF files
- Creates individual PDFs for each document
- Generates a combined comprehensive PDF with all documentation
- Easy to share with non-technical users
- Filtering options for specific documents
- Custom styling options

Usage:
    python create_docs_pdf.py [options]

Options:
    --output=DIR     Set custom output directory (default: ./pdf_docs)
    --zip            Create a ZIP archive of the PDFs for sharing
    --include=PATTERN Only process files matching the pattern (e.g. "*.md")
    --exclude=PATTERN Skip files matching the pattern (e.g. "README.md")
    --no-combined    Skip generation of the combined PDF document
    --title=TEXT     Set a custom title for the combined document
    --version        Show version information
    --help           Show this help message
"""

import os
import sys
import shutil
import subprocess
import argparse
import zipfile
import re
import fnmatch
from pathlib import Path
from datetime import datetime

# Import ReportLab modules at the global scope
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
    from reportlab.platypus import Preformatted, XPreformatted
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
    from reportlab.platypus.flowables import KeepTogether, HRFlowable
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

__version__ = "1.1.0"  # Added versioning for better tracking

def check_dependencies():
    """Check if the required dependencies are installed."""
    try:
        import pip
        return True
    except ImportError:
        print("Error: pip is not installed. Please install pip first.")
        return False

def install_requirements():
    """Install the required packages."""
    requirements = [
        "markdown",
        "reportlab",
        "pillow",  # Required by reportlab for images
    ]
    
    print("Installing required packages...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", *requirements])
        print("Required packages installed successfully.\n")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing packages: {e}")
        print("Try installing them manually with:")
        print(f"pip install {' '.join(requirements)}")
        return False

def get_markdown_files(input_dir, include_pattern=None, exclude_pattern=None):
    """Get markdown files with filtering options."""
    doc_files = []
    
    # List all potential markdown files
    all_files = [f for f in os.listdir(input_dir) if f.endswith(".md")]
    
    # Apply include filter if specified
    if include_pattern:
        filtered_files = []
        patterns = include_pattern.split(',')
        for pattern in patterns:
            pattern = pattern.strip()
            for file in all_files:
                if fnmatch.fnmatch(file, pattern) and file not in filtered_files:
                    filtered_files.append(file)
        all_files = filtered_files
    
    # Apply exclude filter if specified
    if exclude_pattern:
        patterns = exclude_pattern.split(',')
        for pattern in patterns:
            pattern = pattern.strip()
            all_files = [f for f in all_files if not fnmatch.fnmatch(f, pattern)]
    
    # Sort files for consistent order
    all_files.sort()
    
    # Return the filtered list
    return all_files

def convert_markdown_to_html(md_content):
    """Convert markdown to HTML using basic Python string operations."""
    try:
        import markdown
        return markdown.markdown(md_content, extensions=['tables', 'fenced_code'])
    except ImportError:
        # Very basic fallback implementation if markdown module not available
        html = md_content
        
        # Headers
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        
        # Bold and italic
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
        
        # Lists
        html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
        
        # Code blocks - simple version
        html = re.sub(r'```(.+?)```', r'<pre><code>\1</code></pre>', html, flags=re.DOTALL)
        
        # Paragraphs
        paragraphs = []
        for line in html.split('\n\n'):
            if not line.startswith('<h') and not line.startswith('<pre') and not line.strip() == '':
                paragraphs.append(f"<p>{line}</p>")
            else:
                paragraphs.append(line)
        
        html = '\n\n'.join(paragraphs)
        
        return f"<html><body>{html}</body></html>"

def convert_to_pdf(input_dir, output_dir, include_pattern=None, exclude_pattern=None, 
                create_combined=True, custom_title=None):
    """Convert markdown files to PDF."""
    print("\nGenerating PDF versions of documentation...")
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Find all markdown files in the input directory with filtering
    doc_files = get_markdown_files(input_dir, include_pattern, exclude_pattern)
    
    if not doc_files:
        print(f"No markdown files found in {input_dir} matching the specified criteria")
        print("Creating sample markdown files for demonstration...")
        create_sample_docs(input_dir)
        # Refresh the list of markdown files
        doc_files = get_markdown_files(input_dir)
    else:
        print(f"Found {len(doc_files)} markdown files to convert")
    
    try:
        # Check if ReportLab is available
        if not REPORTLAB_AVAILABLE:
            print("Error: ReportLab is not installed or available.")
            print("Please install required packages:")
            print("  pip install reportlab markdown pillow")
            return False
        
        try:
            import markdown
        except ImportError:
            print("Error: markdown module is not installed.")
            print("Please install it with: pip install markdown")
            return False
        
        # Try to use nice fonts if available, fallback to defaults if not
        try:
            # Register fonts
            pdfmetrics.registerFont(TTFont('Arial', 'Arial.ttf'))
            pdfmetrics.registerFont(TTFont('ArialBold', 'Arial_Bold.ttf'))
            font_name = 'Arial'
        except:
            font_name = 'Helvetica'
            print("Note: Using default fonts. For better looking PDFs, ensure Arial.ttf is available.")
        
        # Page setup for better text fitting
        page_width, page_height = letter
        margin = 72  # 1 inch margins (72 points = 1 inch)
        text_width = page_width - (2 * margin)
        
        # Create custom styles with better typography and spacing
        styles = getSampleStyleSheet()
        
        # Document Title
        if 'DocTitle' not in styles:
            styles.add(ParagraphStyle(
                name='DocTitle',
                fontName=font_name,
                fontSize=24,
                spaceAfter=24,
                spaceBefore=36,
                leading=32,  # Line height
                alignment=TA_CENTER,
                textColor=colors.darkblue
            ))
        
        # Heading styles with better spacing
        if 'DocHeading1' not in styles:
            styles.add(ParagraphStyle(
                name='DocHeading1',
                fontName=font_name,
                fontSize=20,
                spaceAfter=14,
                spaceBefore=18,
                leading=24,
                textColor=colors.darkblue,
                allowWidows=0,
                allowOrphans=0
            ))
        if 'DocHeading2' not in styles:
            styles.add(ParagraphStyle(
                name='DocHeading2',
                fontName=font_name,
                fontSize=16,
                spaceAfter=12,
                spaceBefore=16,
                leading=20,
                textColor=colors.darkblue,
                allowWidows=0,
                allowOrphans=0
            ))
        if 'DocHeading3' not in styles:
            styles.add(ParagraphStyle(
                name='DocHeading3',
                fontName=font_name,
                fontSize=14,
                spaceAfter=10,
                spaceBefore=14,
                leading=18,
                textColor=colors.darkblue,
                allowWidows=0,
                allowOrphans=0
            ))
            
        # Improve normal text style for better readability and to prevent text overflow
        improved_normal = ParagraphStyle(
            'ImprovedNormal',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=11,
            leading=16,  # Better line spacing
            spaceBefore=8,
            spaceAfter=8,
            alignment=TA_JUSTIFY,  # Justified text for better appearance
            wordWrap='CJK',  # Improved word wrapping
            allowWidows=0,   # Don't allow single lines at the bottom of a page
            allowOrphans=0,   # Don't allow single lines at the top of a page
            firstLineIndent=0,  # No indentation for first line
            rightIndent=0  # No right indentation
        )
        styles.add(improved_normal)
        
        # Bullet and numbered list styles with better indentation
        if 'BulletItem' not in styles:
            styles.add(ParagraphStyle(
                name='BulletItem',
                parent=styles['ImprovedNormal'],
                fontSize=11,
                leading=16,
                leftIndent=36,
                spaceBefore=4,
                spaceAfter=4,
                bulletIndent=18,
                firstLineIndent=0,
                wordWrap='CJK',  # Better wrapping for list items
                allowWidows=0,
                allowOrphans=0
            ))
            
        if 'NumberItem' not in styles:
            styles.add(ParagraphStyle(
                name='NumberItem',
                parent=styles['ImprovedNormal'],
                fontSize=11,
                leading=16,
                leftIndent=36,
                spaceBefore=4,
                spaceAfter=4,
                bulletIndent=18,
                firstLineIndent=0,
                wordWrap='CJK',  # Better wrapping for list items
                allowWidows=0,
                allowOrphans=0
            ))
            
        # Secondary-level list items (for nested lists)
        if 'BulletItem2' not in styles:
            styles.add(ParagraphStyle(
                name='BulletItem2',
                parent=styles['BulletItem'],
                leftIndent=72,
                bulletIndent=54,
                firstLineIndent=0,
            ))
            
        if 'NumberItem2' not in styles:
            styles.add(ParagraphStyle(
                name='NumberItem2',
                parent=styles['NumberItem'],
                leftIndent=72,
                bulletIndent=54,
                firstLineIndent=0,
            ))
            
        # Improved code block style
        if 'CodeBlock' not in styles:
            styles.add(ParagraphStyle(
                name='CodeBlock',
                fontName='Courier',
                fontSize=9,
                leading=12,
                leftIndent=36,
                rightIndent=36,
                spaceBefore=12,
                spaceAfter=12,
                backColor=colors.lightgrey,
                borderWidth=0.5,
                borderColor=colors.grey,
                borderPadding=8,
                borderRadius=4,
                wordWrap='CJK',  # Better wrapping for code
                allowWidows=0,
                allowOrphans=0
            ))
            
        # Quote style for blockquotes
        if 'BlockQuote' not in styles:
            styles.add(ParagraphStyle(
                name='BlockQuote',
                fontName=font_name,
                fontSize=10,
                leading=14,
                leftIndent=48,
                rightIndent=48,
                spaceBefore=12,
                spaceAfter=12,
                textColor=colors.dimgrey,
                borderColor=colors.lightgrey,
                borderWidth=1,
                borderPadding=12,
                borderRadius=4,
                wordWrap='CJK',  # Better wrapping for quotes
                allowWidows=0,
                allowOrphans=0
            ))
            
        if 'DiagramNote' not in styles:
            styles.add(ParagraphStyle(
                name='DiagramNote',
                fontName=font_name,
                fontSize=10,
                leading=14,
                spaceAfter=8,
                spaceBefore=8,
                leftIndent=36,
                rightIndent=36,
                textColor=colors.darkblue,
                backColor=colors.lightgrey,
                borderWidth=0.5,
                borderColor=colors.lightgrey,
                borderPadding=6,
                wordWrap='CJK',  # Better wrapping
                allowWidows=0,
                allowOrphans=0
            ))
            
        if 'FooterNote' not in styles:
            styles.add(ParagraphStyle(
                name='FooterNote',
                fontName=font_name,
                fontSize=8,
                textColor=colors.darkgrey,
                alignment=TA_CENTER
            ))
            
        # Caption style for images
        if 'Caption' not in styles:
            styles.add(ParagraphStyle(
                name='Caption',
                fontName=font_name,
                fontSize=9,
                leading=12,
                textColor=colors.darkgrey,
                alignment=TA_CENTER,
                spaceBefore=4,
                spaceAfter=12,
                allowWidows=0,
                allowOrphans=0
            ))
        
        # Add page numbers and other elements to each page
        def add_page_number(canvas, doc):
            canvas.saveState()
            # Add header on each page (except the first page)
            if doc.page > 1:
                canvas.setFont(font_name, 9)
                canvas.setFillColor(colors.darkgrey)
                header_text = "Forest Fire Simulation Framework"
                canvas.drawString(doc.leftMargin, doc.height + doc.topMargin - 20, header_text)
                canvas.line(doc.leftMargin, doc.height + doc.topMargin - 30, 
                           doc.width + doc.leftMargin, doc.height + doc.topMargin - 30)
            
            # Add page number
            page_num = canvas.getPageNumber()
            canvas.setFont(font_name, 9)
            canvas.setFillColor(colors.darkgrey)
            text = f"Page {page_num}"
            canvas.drawRightString(doc.width + doc.leftMargin, 30, text)
            
            # Add footer with generation info
            footer_text = f"Generated on {datetime.now().strftime('%Y-%m-%d')} - Forest Fire Simulation Documentation"
            canvas.setFont(font_name, 8)
            canvas.drawCentredString(doc.width/2 + doc.leftMargin, 15, footer_text)
            
            # Add bottom line
            canvas.line(doc.leftMargin, 40, doc.width + doc.leftMargin, 40)
            
            canvas.restoreState()
        
        # Process each file
        pdf_created = False
        all_elements = []  # For combined PDF
        
        for file in doc_files:
            md_path = os.path.join(input_dir, file)
            pdf_name = os.path.splitext(file)[0] + ".pdf"
            pdf_path = os.path.join(output_dir, pdf_name)
            
            if os.path.exists(md_path):
                print(f"Converting {file} to PDF...")
                
                # Read markdown content
                try:
                    with open(md_path, "r", encoding="utf-8") as md_file:
                        md_content = md_file.read()
                except UnicodeDecodeError:
                    print(f"Warning: Encoding issue with {file}. Trying alternative encoding...")
                    try:
                        with open(md_path, "r", encoding="latin-1") as md_file:
                            md_content = md_file.read()
                    except:
                        print(f"Error: Could not read {file}. Skipping...")
                        continue
                
                # Document title detection for better organization
                doc_title = os.path.splitext(file)[0].replace("_", " ")
                lines = md_content.split("\n")
                for line in lines:
                    if line.startswith("# "):
                        doc_title = line[2:].strip()
                        break
                
                # Create PDF document with page number handler
                doc = SimpleDocTemplate(
                    pdf_path, 
                    pagesize=letter, 
                    rightMargin=60,  # Adjusted margins for better text fitting
                    leftMargin=60, 
                    topMargin=60, 
                    bottomMargin=60,
                    title=doc_title,
                    author="Forest Fire Simulation Framework",
                    showBoundary=0
                )
                
                # Content elements
                elements = []
                
                # Pre-process content to handle Mermaid diagrams and other special blocks
                md_content = re.sub(r'```mermaid(.*?)```', r'_[Mermaid diagram not rendered in PDF version]_\n', md_content, flags=re.DOTALL)
                
                # Process markdown content and convert to reportlab elements
                lines = md_content.split("\n")
                i = 0
                
                # If no title found, use the filename
                if not doc_title:
                    doc_title = os.path.splitext(file)[0].replace("_", " ")
                
                in_list = False
                list_items = []
                list_type = None
                in_blockquote = False
                blockquote_lines = []
                
                while i < len(lines):
                    line = lines[i].strip()
                    
                    # Skip problematic content
                    if '<br>' in line or '</br>' in line:
                        elements.append(Paragraph("A diagram or special content was here (not rendered in PDF)", styles["DiagramNote"]))
                        i += 1
                        continue
                    
                    # Handle YAML frontmatter by skipping it
                    if i == 0 and line == '---':
                        # Skip until we find the closing '---'
                        i += 1
                        while i < len(lines) and lines[i].strip() != '---':
                            i += 1
                        i += 1  # Skip the closing '---'
                        continue
                    
                    # Process block quote
                    if line.startswith(">"):
                        if not in_blockquote:
                            in_blockquote = True
                            blockquote_lines = []
                        
                        # Remove the '>' marker and add the content
                        quote_text = line[1:].strip()
                        blockquote_lines.append(quote_text)
                        i += 1
                        continue
                    elif in_blockquote:
                        # End of blockquote
                        blockquote_text = " ".join(blockquote_lines)
                        try:
                            elements.append(Paragraph(blockquote_text, styles["BlockQuote"]))
                        except:
                            elements.append(Paragraph("Blockquote content omitted due to formatting issues", styles["DiagramNote"]))
                        in_blockquote = False
                        blockquote_lines = []
                    
                    # Process lists
                    if line.startswith("- ") or line.startswith("* ") or line.startswith("+ "):
                        if not in_list or list_type != "bullet":
                            # End any previous list
                            if in_list:
                                add_list_to_elements(list_items, list_type, elements, styles)
                            # Start new bullet list
                            in_list = True
                            list_type = "bullet"
                            list_items = []
                        
                        # Calculate indentation level based on leading spaces
                        indent = len(line) - len(line.lstrip())
                        line = line.strip()
                        
                        # Add item to list
                        item_text = line[2:].strip()
                        
                        # Check for nested lists in the next lines
                        nested_items = []
                        nested_type = None
                        j = i + 1
                        current_indent = indent
                        
                        # Look ahead for nested items
                        while j < len(lines) and lines[j].strip():
                            next_line = lines[j]
                            next_indent = len(next_line) - len(next_line.lstrip())
                            next_line = next_line.strip()
                            
                            # If this line is indented more than the parent, it's part of a nested list
                            if next_indent > current_indent:
                                if next_line.startswith(("- ", "* ", "+ ")):
                                    if nested_type is None or nested_type == "bullet":
                                        nested_type = "bullet"
                                        nested_items.append(next_line[2:].strip())
                                elif re.match(r"^\d+\.\s", next_line):
                                    if nested_type is None or nested_type == "number":
                                        nested_type = "number"
                                        nested_items.append(re.sub(r"^\d+\.\s", "", next_line).strip())
                                j += 1
                            else:
                                # Not part of this nested list
                                break
                        
                        # If we found nested items, create a dict with the parent and nested lists
                        if nested_items:
                            list_items.append({
                                'text': item_text,
                                'nested_list': {
                                    'items': nested_items,
                                    'type': nested_type
                                }
                            })
                            # Skip the lines we've processed
                            i = j - 1
                        else:
                            # No nested items
                            list_items.append(item_text)
                            i += 1
                        continue
                    elif re.match(r"^\d+\.\s", line):
                        if not in_list or list_type != "number":
                            # End any previous list
                            if in_list:
                                add_list_to_elements(list_items, list_type, elements, styles)
                            # Start new numbered list
                            in_list = True
                            list_type = "number"
                            list_items = []
                        
                        # Calculate indentation level based on leading spaces
                        indent = len(line) - len(line.lstrip())
                        line = line.strip()
                        
                        # Add item to list
                        item_text = re.sub(r"^\d+\.\s", "", line).strip()
                        
                        # Check for nested lists in the next lines
                        nested_items = []
                        nested_type = None
                        j = i + 1
                        current_indent = indent
                        
                        # Look ahead for nested items
                        while j < len(lines) and lines[j].strip():
                            next_line = lines[j]
                            next_indent = len(next_line) - len(next_line.lstrip())
                            next_line = next_line.strip()
                            
                            # If this line is indented more than the parent, it's part of a nested list
                            if next_indent > current_indent:
                                if next_line.startswith(("- ", "* ", "+ ")):
                                    if nested_type is None or nested_type == "bullet":
                                        nested_type = "bullet"
                                        nested_items.append(next_line[2:].strip())
                                elif re.match(r"^\d+\.\s", next_line):
                                    if nested_type is None or nested_type == "number":
                                        nested_type = "number"
                                        nested_items.append(re.sub(r"^\d+\.\s", "", next_line).strip())
                                j += 1
                            else:
                                # Not part of this nested list
                                break
                        
                        # If we found nested items, create a dict with the parent and nested lists
                        if nested_items:
                            list_items.append({
                                'text': item_text,
                                'nested_list': {
                                    'items': nested_items,
                                    'type': nested_type
                                }
                            })
                            # Skip the lines we've processed
                            i = j - 1
                        else:
                            # No nested items
                            list_items.append(item_text)
                            i += 1
                        continue
                    elif in_list and line.strip() == "":
                        # Empty line might continue the list, so check the next line
                        if i + 1 < len(lines):
                            next_line = lines[i + 1].strip()
                            if (list_type == "bullet" and (next_line.startswith("- ") or next_line.startswith("* ") or next_line.startswith("+ "))) or \
                               (list_type == "number" and re.match(r"^\d+\.\s", next_line)):
                                # This is just an empty line within the list, skip it
                                i += 1
                                continue
                        
                        # End of list
                        add_list_to_elements(list_items, list_type, elements, styles)
                        in_list = False
                        list_type = None
                        list_items = []
                    elif in_list:
                        # End of list without a blank line
                        add_list_to_elements(list_items, list_type, elements, styles)
                        in_list = False
                        list_type = None
                        list_items = []
                    
                    if line.startswith("# "):
                        # Main title
                        title = line[2:].strip()
                        elements.append(Paragraph(title, styles["DocTitle"]))
                    elif line.startswith("## "):
                        # H2 heading
                        heading = line[3:].strip()
                        elements.append(Paragraph(heading, styles["DocHeading1"]))
                    elif line.startswith("### "):
                        # H3 heading
                        heading = line[4:].strip()
                        elements.append(Paragraph(heading, styles["DocHeading2"]))
                    elif line.startswith("#### "):
                        # H4 heading
                        heading = line[5:].strip()
                        elements.append(Paragraph(heading, styles["DocHeading3"]))
                    elif line.startswith("```"):
                        # Check if this is a Mermaid diagram or other special block
                        if line.startswith("```mermaid"):
                            elements.append(Paragraph("[Mermaid diagram not rendered in PDF]", styles["DiagramNote"]))
                            # Skip until end of code block
                            while i < len(lines) and not lines[i].strip() == "```":
                                i += 1
                        else:
                            # Regular code block
                            code_lines = []
                            language = line[3:].strip()  # Capture language for syntax highlighting
                            i += 1  # Skip the opening ```
                            while i < len(lines) and not lines[i].startswith("```"):
                                code_lines.append(lines[i])
                                i += 1
                            code_text = "\n".join(code_lines)
                            
                            # Create a proper code block with background color and border
                            try:
                                # For short code snippets, use Preformatted
                                if len(code_lines) < 15 and max(len(line) for line in code_lines) < 80:
                                    elements.append(Preformatted(code_text, styles["CodeBlock"]))
                                else:
                                    # For longer code, ensure proper wrapping and splitting if needed
                                    from reportlab.platypus import XPreformatted
                                    elements.append(XPreformatted(code_text, styles["CodeBlock"]))
                            except:
                                # Fallback if there's an issue
                                elements.append(Preformatted(code_text, styles["CodeBlock"]))
                            
                            # Add more space after code blocks
                            elements.append(Spacer(1, 8))
                    elif line.startswith("![") and "](" in line and line.endswith(")"):
                        # Image embedding
                        match = re.match(r"!\[(.*?)\]\((.*?)\)", line)
                        if match:
                            alt_text, img_path = match.groups()
                            try:
                                # Check if image exists and is accessible
                                img_path = img_path.strip()
                                full_img_path = os.path.join(input_dir, img_path)
                                if os.path.exists(full_img_path):
                                    # Add the image with a maximum width constraint
                                    img = Image(full_img_path)
                                    
                                    # Calculate appropriate image size with better handling of large images
                                    avail_width = doc.width * 0.85  # Max 85% of available width
                                    if img.drawWidth > avail_width:
                                        ratio = avail_width / img.drawWidth
                                        img.drawWidth = avail_width
                                        img.drawHeight *= ratio
                                    
                                    # Center the image by wrapping it in a table
                                    from reportlab.platypus import Table
                                    t = Table([[img]], colWidths=[doc.width])
                                    t.setStyle([('ALIGN', (0, 0), (0, 0), 'CENTER'),
                                               ('VALIGN', (0, 0), (0, 0), 'MIDDLE')])
                                    
                                    # Add some space before the image
                                    elements.append(Spacer(1, 12))
                                    elements.append(t)
                                    
                                    # Add a caption if available
                                    if alt_text:
                                        elements.append(Paragraph(f"{alt_text}", styles["Caption"]))
                                    
                                    # Add some space after the image + caption
                                    elements.append(Spacer(1, 12))
                                else:
                                    elements.append(Paragraph(f"[Image not found: {img_path}]", styles["DiagramNote"]))
                            except Exception as e:
                                elements.append(Paragraph(f"[Image could not be processed: {e}]", styles["DiagramNote"]))
                    elif not line:
                        # Empty line, add a small spacer if needed
                        if i > 0 and lines[i-1].strip():  # Only add spacer if previous line wasn't empty
                            elements.append(Spacer(1, 6))
                    elif line.startswith("---") or line.startswith("***") or line.startswith("___"):
                        # Horizontal rule with better styling
                        elements.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey, spaceBefore=6, spaceAfter=6))
                    elif line.startswith("|") and i + 1 < len(lines) and lines[i+1].strip().startswith("|"):
                        # This looks like a table
                        try:
                            # Parse table rows
                            table_rows = []
                            
                            # Parse header row
                            header_cells = [cell.strip() for cell in line.strip('|').split('|')]
                            
                            # Skip if this isn't actually a table
                            if len(header_cells) <= 1:
                                # Not a table, treat as normal text
                                elements.append(Paragraph(line, styles["ImprovedNormal"]))
                                i += 1
                                continue
                                
                            # Process header cells with formatting
                            header_row = []
                            for cell in header_cells:
                                # Format header text
                                cell = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", cell)
                                cell = re.sub(r"\*(.*?)\*", r"<i>\1</i>", cell)
                                header_row.append(Paragraph(cell, styles["ImprovedNormal"]))
                            
                            table_rows.append(header_row)
                            
                            # Skip the separator row (line with | ------- | ------ |)
                            i += 1
                            
                            # Process data rows
                            i += 1  # Move to the first data row
                            while i < len(lines) and lines[i].strip().startswith('|'):
                                row = lines[i]
                                cells = [cell.strip() for cell in row.strip('|').split('|')]
                                
                                # Format cells and create row
                                data_row = []
                                for cell in cells:
                                    # Format cell text
                                    cell = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", cell)
                                    cell = re.sub(r"\*(.*?)\*", r"<i>\1</i>", cell)
                                    cell = re.sub(r"`(.*?)`", r'<font face="Courier" color="#333333">\1</font>', cell)
                                    data_row.append(Paragraph(cell, styles["ImprovedNormal"]))
                                
                                # Ensure rows have consistent width
                                while len(data_row) < len(header_row):
                                    data_row.append(Paragraph('', styles["ImprovedNormal"]))
                                if len(data_row) > len(header_row):
                                    data_row = data_row[:len(header_row)]
                                
                                table_rows.append(data_row)
                                i += 1
                            
                            # Create the table
                            # Calculate reasonable column widths
                            col_count = len(header_row)
                            col_width = (doc.width - 60) / col_count  # Account for padding/margins
                            
                            # Create and style the table
                            table = Table(table_rows, colWidths=[col_width] * col_count)
                            
                            # Apply styles for better appearance
                            table.setStyle([
                                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                                ('TEXTCOLOR', (0, 0), (-1, 0), colors.darkblue),
                                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                                ('PADDING', (0, 0), (-1, -1), 6),
                            ])
                            
                            # Add some space before the table
                            elements.append(Spacer(1, 12))
                            elements.append(table)
                            # Add some space after the table
                            elements.append(Spacer(1, 12))
                            
                            # We've already advanced i within the loop
                        except Exception as e:
                            # If table processing fails, add a note
                            elements.append(Paragraph(f"[Table could not be processed: {str(e)}]", styles["DiagramNote"]))
                            # Move to next line
                            i += 1
                    else:
                        # Regular paragraph
                        paragraph_lines = [line]
                        j = i + 1
                        # Collect lines until we hit an empty line or special markup
                        while j < len(lines) and lines[j].strip() and not lines[j].strip().startswith(("#", "```", "-", "*", "+", "!", "---", "<", ">", "1.")):
                            paragraph_lines.append(lines[j].strip())
                            j += 1
                        i = j - 1  # Set i to the last line we processed
                        
                        paragraph_text = " ".join(paragraph_lines)
                        
                        # Skip lines with complicated markup that might cause rendering errors
                        if '<' in paragraph_text and '>' in paragraph_text:
                            # Check if this looks like HTML or a diagram
                            if re.search(r'<[a-zA-Z]+(\s+[^>]+)?>', paragraph_text):
                                elements.append(Paragraph("[Complex content not rendered in PDF]", styles["DiagramNote"]))
                                i += 1
                                continue
                        
                        # Enhanced formatting
                        paragraph_text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", paragraph_text)  # Bold
                        paragraph_text = re.sub(r"\*(.*?)\*", r"<i>\1</i>", paragraph_text)      # Italic
                        paragraph_text = re.sub(r"__(.+?)__", r"<b>\1</b>", paragraph_text)      # Bold with underscore
                        paragraph_text = re.sub(r"_(.+?)_", r"<i>\1</i>", paragraph_text)        # Italic with underscore
                        paragraph_text = re.sub(r"`(.*?)`", r'<font face="Courier" color="#333333">\1</font>', paragraph_text)  # Better inline code
                        paragraph_text = re.sub(r"~~(.*?)~~", r"<strike>\1</strike>", paragraph_text)  # Strikethrough
                        
                        # Special character handling
                        paragraph_text = paragraph_text.replace("&", "&amp;")
                        
                        # Safer link handling to prevent PDF errors
                        def link_replacement(m):
                            link_text = m.group(1)
                            link_url = m.group(2)
                            
                            # Handle cross-document links
                            if link_url.endswith('.md'):
                                # This is a link to another document
                                # Extract the document name without extension
                                target_doc = os.path.splitext(os.path.basename(link_url))[0]
                                
                                # Create a description with the target document name
                                pdf_name = f"{target_doc}.pdf"
                                return f'<b>{link_text}</b> <i>(See document: {target_doc.replace("_", " ")})</i>'
                            
                            # Check if this is an anchor/fragment link
                            if link_url.startswith('#'):
                                # For section references within document
                                section_name = link_url[1:].replace('-', ' ').title()
                                return f'<b>{link_text}</b> <i>(See section: {section_name})</i>'
                            
                            # Check for potential problematic URLs
                            if ':' not in link_url and not link_url.startswith('/'):
                                # This might be a relative link without a scheme
                                if link_url.endswith(('.pdf', '.html', '.txt')):
                                    # It's a file link
                                    return f'<b>{link_text}</b> <i>(file: {link_url})</i>'
                                else:
                                    # Might be an anchor link or something else
                                    return f'<b>{link_text}</b>'
                            
                            # External link with proper scheme
                            try:
                                # Format as a clickable link in the PDF
                                return f'<link href="{link_url}"><u><font color="blue">{link_text}</font></u></link>'
                            except:
                                # If anything goes wrong, just show the text
                                return f'<b>{link_text}</b>'
                        
                        # Apply the link replacement
                        paragraph_text = re.sub(r"\[(.*?)\]\((.*?)\)", link_replacement, paragraph_text)
                        
                        try:
                            elements.append(Paragraph(paragraph_text, styles["ImprovedNormal"]))
                        except:
                            # If there's an error with the paragraph, try a simplified version
                            simplified_text = re.sub(r"<.*?>", "", paragraph_text)  # Remove all HTML tags
                            try:
                                elements.append(Paragraph(simplified_text, styles["ImprovedNormal"]))
                            except:
                                elements.append(Paragraph("Content omitted due to formatting issues", styles["DiagramNote"]))
                    
                    i += 1
                
                # Check if we were in a list at the end of the document
                if in_list:
                    add_list_to_elements(list_items, list_type, elements, styles)
                
                # Check if we were in a blockquote at the end of the document
                if in_blockquote:
                    blockquote_text = " ".join(blockquote_lines)
                    try:
                        elements.append(Paragraph(blockquote_text, styles["BlockQuote"]))
                    except:
                        elements.append(Paragraph("Blockquote content omitted due to formatting issues", styles["DiagramNote"]))
                
                # Build the PDF with page numbers
                try:
                    doc.build(elements, onFirstPage=add_page_number, onLaterPages=add_page_number)
                    print(f"Created {pdf_name}")
                    pdf_created = True
                    
                    # Add to combined elements for the complete PDF (if requested)
                    if create_combined and len(doc_files) > 1:
                        # Add title page for this section
                        title = doc_title
                        if all_elements:  # Not the first document
                            all_elements.append(PageBreak())
                        all_elements.append(Paragraph(title, styles["DocTitle"]))
                        all_elements.append(Spacer(1, 24))
                        
                        # We need to re-process the markdown content for the combined document
                        # since the elements list can't be easily copied between documents
                        try:
                            with open(md_path, "r", encoding="utf-8") as md_file:
                                md_content = md_file.read()
                                
                            # Process again for the combined PDF
                            lines = md_content.split("\n")
                            i = 0
                            in_list = False
                            list_items = []
                            list_type = None
                            in_blockquote = False
                            blockquote_lines = []
                            
                            # Skip the first heading as we've already added it
                            if lines and lines[0].startswith("# "):
                                i = 1
                                # Skip any blank lines after the title
                                while i < len(lines) and not lines[i].strip():
                                    i += 1
                            
                            while i < len(lines):
                                line = lines[i].strip()
                                
                                # Skip problematic content
                                if '<br>' in line or '</br>' in line:
                                    all_elements.append(Paragraph("A diagram or special content was here (not rendered in PDF)", styles["DiagramNote"]))
                                    i += 1
                                    continue
                                
                                # Handle YAML frontmatter by skipping it
                                if i == 0 and line == '---':
                                    # Skip until we find the closing '---'
                                    i += 1
                                    while i < len(lines) and lines[i].strip() != '---':
                                        i += 1
                                    i += 1  # Skip the closing '---'
                                    continue
                                
                                # Process block quote
                                if line.startswith(">"):
                                    if not in_blockquote:
                                        in_blockquote = True
                                        blockquote_lines = []
                                    
                                    # Remove the '>' marker and add the content
                                    quote_text = line[1:].strip()
                                    blockquote_lines.append(quote_text)
                                    i += 1
                                    continue
                                elif in_blockquote:
                                    # End of blockquote
                                    blockquote_text = " ".join(blockquote_lines)
                                    try:
                                        all_elements.append(Paragraph(blockquote_text, styles["BlockQuote"]))
                                    except:
                                        all_elements.append(Paragraph("Blockquote content omitted due to formatting issues", styles["DiagramNote"]))
                                    in_blockquote = False
                                    blockquote_lines = []
                                
                                # Process lists
                                if line.startswith("- ") or line.startswith("* ") or line.startswith("+ "):
                                    if not in_list or list_type != "bullet":
                                        # End any previous list
                                        if in_list:
                                            add_list_to_elements(list_items, list_type, all_elements, styles)
                                        # Start new bullet list
                                        in_list = True
                                        list_type = "bullet"
                                        list_items = []
                                    
                                    # Calculate indentation level based on leading spaces
                                    indent = len(line) - len(line.lstrip())
                                    line = line.strip()
                                    
                                    # Add item to list
                                    item_text = line[2:].strip()
                                    
                                    # Check for nested lists in the next lines
                                    nested_items = []
                                    nested_type = None
                                    j = i + 1
                                    current_indent = indent
                                    
                                    # Look ahead for nested items
                                    while j < len(lines) and lines[j].strip():
                                        next_line = lines[j]
                                        next_indent = len(next_line) - len(next_line.lstrip())
                                        next_line = next_line.strip()
                                        
                                        # If this line is indented more than the parent, it's part of a nested list
                                        if next_indent > current_indent:
                                            if next_line.startswith(("- ", "* ", "+ ")):
                                                if nested_type is None or nested_type == "bullet":
                                                    nested_type = "bullet"
                                                    nested_items.append(next_line[2:].strip())
                                            elif re.match(r"^\d+\.\s", next_line):
                                                if nested_type is None or nested_type == "number":
                                                    nested_type = "number"
                                                    nested_items.append(re.sub(r"^\d+\.\s", "", next_line).strip())
                                            j += 1
                                        else:
                                            # Not part of this nested list
                                            break
                                    
                                    # If we found nested items, create a dict with the parent and nested lists
                                    if nested_items:
                                        list_items.append({
                                            'text': item_text,
                                            'nested_list': {
                                                'items': nested_items,
                                                'type': nested_type
                                            }
                                        })
                                        # Skip the lines we've processed
                                        i = j - 1
                                    else:
                                        # No nested items
                                        list_items.append(item_text)
                                        i += 1
                                    continue
                                elif re.match(r"^\d+\.\s", line):
                                    if not in_list or list_type != "number":
                                        # End any previous list
                                        if in_list:
                                            add_list_to_elements(list_items, list_type, all_elements, styles)
                                        # Start new numbered list
                                        in_list = True
                                        list_type = "number"
                                        list_items = []
                                    
                                    # Calculate indentation level based on leading spaces
                                    indent = len(line) - len(line.lstrip())
                                    line = line.strip()
                                    
                                    # Add item to list
                                    item_text = re.sub(r"^\d+\.\s", "", line).strip()
                                    
                                    # Check for nested lists in the next lines
                                    nested_items = []
                                    nested_type = None
                                    j = i + 1
                                    current_indent = indent
                                    
                                    # Look ahead for nested items
                                    while j < len(lines) and lines[j].strip():
                                        next_line = lines[j]
                                        next_indent = len(next_line) - len(next_line.lstrip())
                                        next_line = next_line.strip()
                                        
                                        # If this line is indented more than the parent, it's part of a nested list
                                        if next_indent > current_indent:
                                            if next_line.startswith(("- ", "* ", "+ ")):
                                                if nested_type is None or nested_type == "bullet":
                                                    nested_type = "bullet"
                                                    nested_items.append(next_line[2:].strip())
                                            elif re.match(r"^\d+\.\s", next_line):
                                                if nested_type is None or nested_type == "number":
                                                    nested_type = "number"
                                                    nested_items.append(re.sub(r"^\d+\.\s", "", next_line).strip())
                                            j += 1
                                        else:
                                            # Not part of this nested list
                                            break
                                    
                                    # If we found nested items, create a dict with the parent and nested lists
                                    if nested_items:
                                        list_items.append({
                                            'text': item_text,
                                            'nested_list': {
                                                'items': nested_items,
                                                'type': nested_type
                                            }
                                        })
                                        # Skip the lines we've processed
                                        i = j - 1
                                    else:
                                        # No nested items
                                        list_items.append(item_text)
                                        i += 1
                                    continue
                                elif in_list and line.strip() == "":
                                    # Empty line might continue the list, so check the next line
                                    if i + 1 < len(lines):
                                        next_line = lines[i + 1].strip()
                                        if (list_type == "bullet" and (next_line.startswith("- ") or next_line.startswith("* ") or next_line.startswith("+ "))) or \
                                           (list_type == "number" and re.match(r"^\d+\.\s", next_line)):
                                            # This is just an empty line within the list, skip it
                                            i += 1
                                            continue
                                    
                                    # End of list
                                    add_list_to_elements(list_items, list_type, all_elements, styles)
                                    in_list = False
                                    list_type = None
                                    list_items = []
                                elif in_list:
                                    # End of list without a blank line
                                    add_list_to_elements(list_items, list_type, all_elements, styles)
                                    in_list = False
                                    list_type = None
                                    list_items = []
                                
                                if line.startswith("# "):
                                    # Skip main title as we've already added it
                                    pass
                                elif line.startswith("## "):
                                    # H2 heading
                                    heading = line[3:].strip()
                                    all_elements.append(Paragraph(heading, styles["DocHeading1"]))
                                elif line.startswith("### "):
                                    # H3 heading
                                    heading = line[4:].strip()
                                    all_elements.append(Paragraph(heading, styles["DocHeading2"]))
                                elif line.startswith("#### "):
                                    # H4 heading
                                    heading = line[5:].strip()
                                    all_elements.append(Paragraph(heading, styles["DocHeading3"]))
                                elif line.startswith("```"):
                                    # Check if this is a Mermaid diagram or other special block
                                    if line.startswith("```mermaid"):
                                        all_elements.append(Paragraph("[Mermaid diagram not rendered in PDF]", styles["DiagramNote"]))
                                        # Skip until end of code block
                                        while i < len(lines) and not lines[i].strip() == "```":
                                            i += 1
                                    else:
                                        # Regular code block
                                        code_lines = []
                                        language = line[3:].strip()  # Capture language for syntax highlighting
                                        i += 1  # Skip the opening ```
                                        while i < len(lines) and not lines[i].startswith("```"):
                                            code_lines.append(lines[i])
                                            i += 1
                                        code_text = "\n".join(code_lines)
                                        
                                        # Create a proper code block with background color and border
                                        try:
                                            # For short code snippets, use Preformatted
                                            if len(code_lines) < 15 and max(len(line) for line in code_lines) < 80:
                                                all_elements.append(Preformatted(code_text, styles["CodeBlock"]))
                                            else:
                                                # For longer code, ensure proper wrapping and splitting if needed
                                                from reportlab.platypus import XPreformatted
                                                all_elements.append(XPreformatted(code_text, styles["CodeBlock"]))
                                        except:
                                            # Fallback if there's an issue
                                            all_elements.append(Preformatted(code_text, styles["CodeBlock"]))
                                
                                elif line.startswith("![") and "](" in line and line.endswith(")"):
                                    # Image embedding
                                    match = re.match(r"!\[(.*?)\]\((.*?)\)", line)
                                    if match:
                                        alt_text, img_path = match.groups()
                                        try:
                                            # Check if image exists and is accessible
                                            img_path = img_path.strip()
                                            full_img_path = os.path.join(input_dir, img_path)
                                            if os.path.exists(full_img_path):
                                                # Add the image with a maximum width constraint
                                                img = Image(full_img_path)
                                                
                                                # Calculate appropriate image size with better handling of large images
                                                avail_width = doc.width * 0.85  # Max 85% of available width
                                                if img.drawWidth > avail_width:
                                                    ratio = avail_width / img.drawWidth
                                                    img.drawWidth = avail_width
                                                    img.drawHeight *= ratio
                                                
                                                # Center the image by wrapping it in a table
                                                from reportlab.platypus import Table
                                                t = Table([[img]], colWidths=[doc.width])
                                                t.setStyle([('ALIGN', (0, 0), (0, 0), 'CENTER'),
                                                           ('VALIGN', (0, 0), (0, 0), 'MIDDLE')])
                                                
                                                # Add some space before the image
                                                all_elements.append(Spacer(1, 12))
                                                all_elements.append(t)
                                                
                                                # Add a caption if available
                                                if alt_text:
                                                    all_elements.append(Paragraph(f"{alt_text}", styles["Caption"]))
                                                
                                                # Add some space after the image + caption
                                                all_elements.append(Spacer(1, 12))
                                            else:
                                                all_elements.append(Paragraph(f"[Image not found: {img_path}]", styles["DiagramNote"]))
                                        except Exception as e:
                                            all_elements.append(Paragraph(f"[Image could not be processed: {e}]", styles["DiagramNote"]))
                                elif not line:
                                    # Empty line, add a small spacer if needed
                                    if i > 0 and lines[i-1].strip():  # Only add spacer if previous line wasn't empty
                                        all_elements.append(Spacer(1, 6))
                                elif line.startswith("---") or line.startswith("***") or line.startswith("___"):
                                    # Horizontal rule with better styling
                                    all_elements.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey, spaceBefore=6, spaceAfter=6))
                                else:
                                    # Regular paragraph
                                    paragraph_lines = [line]
                                    j = i + 1
                                    # Collect lines until we hit an empty line or special markup
                                    while j < len(lines) and lines[j].strip() and not lines[j].strip().startswith(("#", "```", "-", "*", "+", "!", "---", "<", ">", "1.")):
                                        paragraph_lines.append(lines[j].strip())
                                        j += 1
                                    i = j - 1  # Set i to the last line we processed
                                    
                                    paragraph_text = " ".join(paragraph_lines)
                                    
                                    # Skip lines with complicated markup that might cause rendering errors
                                    if '<' in paragraph_text and '>' in paragraph_text:
                                        # Check if this looks like HTML or a diagram
                                        if re.search(r'<[a-zA-Z]+(\s+[^>]+)?>', paragraph_text):
                                            all_elements.append(Paragraph("[Complex content not rendered in PDF]", styles["DiagramNote"]))
                                            i += 1
                                            continue
                                    
                                    # Enhanced formatting
                                    paragraph_text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", paragraph_text)  # Bold
                                    paragraph_text = re.sub(r"\*(.*?)\*", r"<i>\1</i>", paragraph_text)      # Italic
                                    paragraph_text = re.sub(r"__(.+?)__", r"<b>\1</b>", paragraph_text)      # Bold with underscore
                                    paragraph_text = re.sub(r"_(.+?)_", r"<i>\1</i>", paragraph_text)        # Italic with underscore
                                    paragraph_text = re.sub(r"`(.*?)`", r'<font face="Courier" color="#333333">\1</font>', paragraph_text)  # Better inline code
                                    paragraph_text = re.sub(r"~~(.*?)~~", r"<strike>\1</strike>", paragraph_text)  # Strikethrough
                                    
                                    # Special character handling
                                    paragraph_text = paragraph_text.replace("&", "&amp;")
                                    
                                    # Safer link handling to prevent PDF errors
                                    def link_replacement(m):
                                        link_text = m.group(1)
                                        link_url = m.group(2)
                                        
                                        # Handle cross-document links
                                        if link_url.endswith('.md'):
                                            # This is a link to another document
                                            # Extract the document name without extension
                                            target_doc = os.path.splitext(os.path.basename(link_url))[0]
                                            
                                            # Create a description with the target document name
                                            pdf_name = f"{target_doc}.pdf"
                                            return f'<b>{link_text}</b> <i>(See document: {target_doc.replace("_", " ")})</i>'
                                        
                                        # Check if this is an anchor/fragment link
                                        if link_url.startswith('#'):
                                            # For section references within document
                                            section_name = link_url[1:].replace('-', ' ').title()
                                            return f'<b>{link_text}</b> <i>(See section: {section_name})</i>'
                                        
                                        # Check for potential problematic URLs
                                        if ':' not in link_url and not link_url.startswith('/'):
                                            # This might be a relative link without a scheme
                                            if link_url.endswith(('.pdf', '.html', '.txt')):
                                                # It's a file link
                                                return f'<b>{link_text}</b> <i>(file: {link_url})</i>'
                                            else:
                                                # Might be an anchor link or something else
                                                return f'<b>{link_text}</b>'
                                        
                                        # External link with proper scheme
                                        try:
                                            # Format as a clickable link in the PDF
                                            return f'<link href="{link_url}"><u><font color="blue">{link_text}</font></u></link>'
                                        except:
                                            # If anything goes wrong, just show the text
                                            return f'<b>{link_text}</b>'
                                    
                                    # Apply the link replacement
                                    paragraph_text = re.sub(r"\[(.*?)\]\((.*?)\)", link_replacement, paragraph_text)
                                    
                                    try:
                                        all_elements.append(Paragraph(paragraph_text, styles["ImprovedNormal"]))
                                    except:
                                        # If there's an error with the paragraph, try a simplified version
                                        simplified_text = re.sub(r"<.*?>", "", paragraph_text)  # Remove all HTML tags
                                        try:
                                            all_elements.append(Paragraph(simplified_text, styles["ImprovedNormal"]))
                                        except:
                                            all_elements.append(Paragraph("Content omitted due to formatting issues", styles["DiagramNote"]))
                                
                                i += 1
                            
                            # Check if we were in a list at the end of the document
                            if in_list:
                                add_list_to_elements(list_items, list_type, all_elements, styles)
                            
                            # Check if we were in a blockquote at the end of the document
                            if in_blockquote:
                                blockquote_text = " ".join(blockquote_lines)
                                try:
                                    all_elements.append(Paragraph(blockquote_text, styles["BlockQuote"]))
                                except:
                                    all_elements.append(Paragraph("Blockquote content omitted due to formatting issues", styles["DiagramNote"]))
                                    
                        except Exception as e:
                            all_elements.append(Paragraph(f"[Error including content from {file}: {str(e)}]", styles["DiagramNote"]))
                except Exception as e:
                    print(f"Error building PDF for {file}: {e}")
        
        # Create combined PDF with bookmarks for navigation
        if create_combined and pdf_created and len(doc_files) > 1:
            print("Creating combined documentation PDF...")
            
            combined_pdf = SimpleDocTemplate(
                os.path.join(output_dir, "Complete_Documentation.pdf"), 
                pagesize=letter, 
                rightMargin=60, 
                leftMargin=60, 
                topMargin=60, 
                bottomMargin=60,
                title="Forest Fire Simulation Framework - Complete Documentation",
                author="Forest Fire Simulation Framework",
                showBoundary=0
            )
            
            # Create a cover page
            cover_elements = []
            
            # Use custom title if provided, otherwise use default
            title = "Forest Fire Simulation Framework"
            if custom_title:
                title = custom_title
                
            cover_elements.append(Paragraph(title, styles["DocTitle"]))
            cover_elements.append(Spacer(1, 36))
            cover_elements.append(Paragraph("Complete Documentation", styles["DocHeading1"]))
            cover_elements.append(Spacer(1, 72))
            cover_elements.append(Paragraph(f"Generated on {datetime.now().strftime('%Y-%m-%d')}", styles["ImprovedNormal"]))
            
            # Add cover and table of contents
            final_elements = []
            final_elements.extend(cover_elements)
            final_elements.append(PageBreak())
            
            # Add table of contents
            final_elements.append(Paragraph("Table of Contents", styles["DocTitle"]))
            final_elements.append(Spacer(1, 24))
            
            for file in doc_files:
                # Extract document title if possible
                md_path = os.path.join(input_dir, file)
                title = os.path.splitext(file)[0].replace("_", " ")
                
                try:
                    with open(md_path, "r", encoding="utf-8") as md_file:
                        first_line = md_file.readline().strip()
                        if first_line.startswith("# "):
                            title = first_line[2:].strip()
                except:
                    pass  # Keep the default title if file can't be read
                
                final_elements.append(Paragraph(f"• {title}", styles["ImprovedNormal"]))
                final_elements.append(Spacer(1, 8))
            
            final_elements.append(PageBreak())
            
            # Add a special "How to Navigate" page to explain cross-document references
            final_elements.append(Paragraph("How to Navigate This Documentation", styles["DocTitle"]))
            final_elements.append(Spacer(1, 24))
            
            final_elements.append(Paragraph("Understanding Cross-Document References", styles["DocHeading1"]))
            final_elements.append(Spacer(1, 12))
            
            nav_text = """
            This PDF combines multiple documents into one comprehensive reference. 
            Throughout the text, you'll find cross-document references in the following format:
            """
            final_elements.append(Paragraph(nav_text, styles["ImprovedNormal"]))
            final_elements.append(Spacer(1, 12))
            
            # Example references
            final_elements.append(Paragraph("• <b>Link text</b> <i>(See document: Document Name)</i> - This indicates a reference to another document in this collection.", styles["BulletItem"]))
            final_elements.append(Paragraph("• <b>Link text</b> <i>(See section: Section Name)</i> - This indicates a reference to a section within the current document.", styles["BulletItem"]))
            final_elements.append(Paragraph("• <u><font color=\"blue\">External links</font></u> - Blue underlined text indicates clickable links to websites or external resources.", styles["BulletItem"]))
            
            final_elements.append(Spacer(1, 24))
            
            final_elements.append(Paragraph("Document Structure", styles["DocHeading1"]))
            final_elements.append(Spacer(1, 12))
            
            # Document structure explanation with all document titles
            structure_text = """
            This documentation consists of the following documents, which have been combined in this PDF:
            """
            final_elements.append(Paragraph(structure_text, styles["ImprovedNormal"]))
            final_elements.append(Spacer(1, 12))
            
            for file in doc_files:
                # Extract document title and briefly describe it
                md_path = os.path.join(input_dir, file)
                title = os.path.splitext(file)[0].replace("_", " ")
                
                try:
                    with open(md_path, "r", encoding="utf-8") as md_file:
                        content = md_file.read()
                        first_line = content.split('\n')[0].strip()
                        if first_line.startswith("# "):
                            title = first_line[2:].strip()
                            
                        # Create a brief description of the document
                        desc = "Contains project documentation."
                        if "technical" in file.lower():
                            desc = "Technical reference with implementation details and specifications."
                        elif "guide" in file.lower() or "documentation" in file.lower():
                            desc = "User guide explaining concepts, workflows, and usage."
                        elif "readme" in file.lower():
                            desc = "Overview and general information about the project."
                        elif "workflow" in file.lower() or "diagram" in file.lower():
                            desc = "Workflow diagrams and visual representations of processes."
                        elif "config" in file.lower() or "tool" in file.lower():
                            desc = "Configuration tools and utilities documentation."
                except:
                    desc = "Contains project documentation."
                
                final_elements.append(Paragraph(f"• <b>{title}</b> - {desc}", styles["BulletItem"]))
                
            final_elements.append(PageBreak())
            
            # Add all document content
            final_elements.extend(all_elements)
            
            try:
                # Build combined PDF with page numbers and bookmarks
                # We'll create a canvas handler that adds bookmarks
                doc_titles = []
                for file in doc_files:
                    # Extract document title
                    md_path = os.path.join(input_dir, file)
                    title = os.path.splitext(file)[0].replace("_", " ")
                    try:
                        with open(md_path, "r", encoding="utf-8") as md_file:
                            first_line = md_file.readline().strip()
                            if first_line.startswith("# "):
                                title = first_line[2:].strip()
                    except:
                        pass  # Keep the default title if file can't be read
                    doc_titles.append(title)
                
                # Custom canvas handler for adding bookmarks
                def add_bookmarks_handler(canvas, doc):
                    # Call the original page number handler
                    add_page_number(canvas, doc)
                    
                    # Add bookmarks on first page initialization
                    if hasattr(canvas, 'bookmarks_added'):
                        return
                    
                    # Add top-level bookmarks
                    canvas.bookmarkPage('cover')
                    canvas.addOutlineEntry('Cover', 'cover', 0)
                    
                    canvas.bookmarkPage('toc')
                    canvas.addOutlineEntry('Table of Contents', 'toc', 0)
                    
                    canvas.bookmarkPage('navigation')
                    canvas.addOutlineEntry('How to Navigate', 'navigation', 0)
                    
                    # Add document bookmarks
                    for i, title in enumerate(doc_titles):
                        bookmark_key = f'doc{i}'
                        canvas.bookmarkPage(bookmark_key)
                        canvas.addOutlineEntry(title, bookmark_key, 0)
                    
                    # Flag that we've added bookmarks
                    canvas.bookmarks_added = True
                
                # Build the PDF with bookmarks
                combined_pdf.build(final_elements, onFirstPage=add_bookmarks_handler, onLaterPages=add_bookmarks_handler)
                print("Created Complete_Documentation.pdf")
            except Exception as e:
                print(f"Error building combined PDF: {e}")
                import traceback
                traceback.print_exc()
        
        # Check if any PDFs were created
        if pdf_created:
            print("\nPDF conversion completed successfully.")
            print(f"PDFs are available in: {os.path.abspath(output_dir)}")
            return True
        else:
            print("\nNo PDFs were created.")
            return False
            
    except ImportError as e:
        print(f"Error: {e}")
        print("Missing required packages. Try installing:")
        print("  pip install reportlab markdown pillow")
        return False
    except Exception as e:
        print(f"PDF conversion failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
def add_list_to_elements(list_items, list_type, elements, styles, level=1):
    """Helper function to add a list to the elements."""
    # Make sure we're using the globally imported Paragraph class
    from reportlab.platypus import Paragraph as ParagraphClass
    
    if not list_items:
        return
    
    # Choose the appropriate style based on the list level
    style_name = f"{'Bullet' if list_type == 'bullet' else 'Number'}Item{'' if level == 1 else str(level)}"
    
    # Make sure the style exists - fallback to level 1 if not
    if style_name not in styles:
        style_name = f"{'Bullet' if list_type == 'bullet' else 'Number'}Item"
    
    for i, item in enumerate(list_items):
        # Check if this item has a nested list
        nested_list_match = False
        nested_list_items = []
        nested_list_type = None
        
        # Process item to extract potential nested list
        if isinstance(item, dict) and 'text' in item and 'nested_list' in item:
            item_text = item['text']
            nested_list_items = item['nested_list']['items']
            nested_list_type = item['nested_list']['type']
            nested_list_match = True
        else:
            item_text = item
        
        # Process formatting within list items
        item_text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", item_text)  # Bold
        item_text = re.sub(r"\*(.*?)\*", r"<i>\1</i>", item_text)      # Italic
        item_text = re.sub(r"__(.+?)__", r"<b>\1</b>", item_text)      # Bold with underscore
        item_text = re.sub(r"_(.+?)_", r"<i>\1</i>", item_text)        # Italic with underscore
        item_text = re.sub(r"`(.*?)`", r'<font face="Courier" color="#333333">\1</font>', item_text)  # Inline code
        
        try:
            # Add the list item with the appropriate bullet or number
            bullet_text = "• " if list_type == "bullet" else f"{i+1}. "
            elements.append(ParagraphClass(f"{bullet_text}{item_text}", styles[style_name]))
            
            # Add any nested list
            if nested_list_match and nested_list_items:
                add_list_to_elements(nested_list_items, nested_list_type, elements, styles, level+1)
                
        except:
            # If there's an error with the paragraph, use a simplified version
            elements.append(ParagraphClass(f"• List item" if list_type == "bullet" else f"{i+1}. List item", styles[style_name]))
    
    # Add a small space after the list
    elements.append(Spacer(1, 8))

def create_sample_docs(input_dir):
    """Create sample markdown files for demonstration."""
    if not os.path.exists(input_dir):
        os.makedirs(input_dir, exist_ok=True)
    
    # Sample user guide
    with open(os.path.join(input_dir, "Forest_Fire_Simulation_Documentation.md"), "w", encoding="utf-8") as f:
        f.write("""# Forest Fire Simulation User Guide

This is a sample user guide. Replace with your actual documentation.

## Introduction

The Forest Fire Simulation Framework is designed to help researchers and forest managers
simulate and analyze forest fire behavior in three dimensions.

## Getting Started

1. Install the framework
2. Configure your simulation
3. Run the simulation
4. Analyze results

## Basic Usage

```python
from forest_fire_framework import Simulation

sim = Simulation(area="my_forest_area.geojson")
sim.run()
sim.visualize()
```
""")
    
    # Sample technical reference
    with open(os.path.join(input_dir, "Forest_Fire_Simulation_Technical_Reference.md"), "w", encoding="utf-8") as f:
        f.write("""# Forest Fire Simulation Technical Reference

This is a sample technical reference. Replace with your actual documentation.

## Algorithms

The simulation uses a cellular automaton approach with the following key components:

1. Fire spread model based on Rothermel's equations
2. 3D forest structure model
3. Weather influence module

## Data Structures

The framework uses optimized data structures to handle large-scale simulations.

## Performance Considerations

Memory usage and computational requirements are affected by:

1. Spatial resolution
2. Temporal resolution
3. Area size
4. Number of vegetation layers
""")

def create_zip_archive(pdf_dir):
    """Create a ZIP archive of the PDFs for easy sharing."""
    print("\nCreating ZIP archive for sharing...")
    
    try:
        if not os.path.exists(pdf_dir):
            print(f"Error: PDF directory '{pdf_dir}' not found.")
            return False
        
        # Check if directory contains PDFs
        pdf_files = [f for f in os.listdir(pdf_dir) if f.endswith(".pdf")]
        if not pdf_files:
            print(f"No PDF files found in {pdf_dir}")
            return False
        
        # Generate a filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"forest_fire_docs_pdf_{timestamp}.zip"
        
        # Create the ZIP file
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            print(f"Adding {len(pdf_files)} PDF files to ZIP archive...")
            for root, dirs, files in os.walk(pdf_dir):
                for file in files:
                    if file.endswith(".pdf"):
                        file_path = os.path.join(root, file)
                        # Calculate the relative path to preserve directory structure
                        rel_path = os.path.relpath(file_path, os.path.dirname(pdf_dir))
                        zipf.write(file_path, rel_path)
        
        zip_full_path = os.path.abspath(zip_filename)
        print(f"ZIP archive created successfully: {zip_full_path}")
        print("\nTo share the documentation:")
        print(f"1. Send the ZIP file '{zip_filename}' to others")
        print("2. Recipients can view the PDFs with any PDF reader")
        
        return True
    
    except Exception as e:
        print(f"Error creating ZIP archive: {str(e)}")
        return False

def main():
    """Main function to control the script workflow."""
    parser = argparse.ArgumentParser(description="Generate PDF documents from Forest Fire Simulation documentation.")
    parser.add_argument("--output", help="Set custom output directory (default: ./pdf_docs)")
    parser.add_argument("--zip", action="store_true", help="Create a ZIP archive of the PDFs for sharing")
    parser.add_argument("--include", help="Only process files matching the pattern (e.g. '*.md' or 'doc*.md,README.md')")
    parser.add_argument("--exclude", help="Skip files matching the pattern (e.g. 'README.md' or 'test*.md,temp*.md')")
    parser.add_argument("--no-combined", action="store_true", help="Skip generation of the combined PDF document")
    parser.add_argument("--title", help="Set a custom title for the combined document")
    parser.add_argument("--version", action="store_true", help="Show version information")
    parser.add_argument("--help-custom", action="store_true", help="Show detailed help message")
    
    args = parser.parse_args()
    
    if args.help_custom:
        print(__doc__)
        return
    
    if args.version:
        print(f"Forest Fire Simulation Documentation PDF Generator v{__version__}")
        return
    
    print("=" * 80)
    print("Forest Fire Simulation Documentation PDF Generator")
    print("=" * 80)
    
    # Check dependencies
    if not check_dependencies():
        return
    
    # Install required packages
    if not install_requirements():
        print("Warning: Proceeding with potentially incomplete dependencies.")
    
    # Define the input directory (current directory)
    input_dir = "."
    
    # Define the output directory
    output_dir = args.output if args.output else "pdf_docs"
    
    # Convert markdown files to PDF
    if not convert_to_pdf(
        input_dir=input_dir, 
        output_dir=output_dir,
        include_pattern=args.include,
        exclude_pattern=args.exclude,
        create_combined=not args.no_combined,
        custom_title=args.title
    ):
        print("Error: PDF conversion failed. Please check the errors above.")
        return
    
    # Create ZIP archive if requested
    if args.zip:
        if not create_zip_archive(output_dir):
            print("Error: Failed to create ZIP archive.")
    
    print("\nProcess completed successfully!")
    output_dir_abs = os.path.abspath(output_dir)
    print(f"You can find the generated PDFs in: {output_dir_abs}")
    
    # Show command for creating ZIP
    if not args.zip:
        print("\nTo create a ZIP archive of the PDFs for sharing, run:")
        print(f"  python {sys.argv[0]} --zip")
    
    # Try to open the PDF directory
    try:
        # Use the appropriate command based on the OS
        if sys.platform == 'win32':
            os.startfile(output_dir_abs)
        elif sys.platform == 'darwin':  # macOS
            subprocess.call(['open', output_dir_abs])
        else:  # Linux and other Unix-like systems
            subprocess.call(['xdg-open', output_dir_abs])
        print("\nOpened the PDF directory for you.")
    except:
        print("\nCould not open the PDF directory automatically.")
        print(f"Please navigate to: {output_dir_abs}")

if __name__ == "__main__":
    main() 