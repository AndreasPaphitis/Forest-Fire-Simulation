#!/usr/bin/env python3
"""
Forest Fire Workflow Diagrams Generator

This specialized script converts the workflow diagrams markdown file to HTML
with proper Mermaid diagram rendering support.
"""

import os
import sys
import subprocess
import shutil
import re
from pathlib import Path
from datetime import datetime

def install_requirements():
    """Install required Python packages."""
    print("Installing required Python packages...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "markdown", "pygments"], 
                       check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("Required packages installed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing packages: {e}")
        return False

def create_output_dir(output_dir):
    """Create output directory for HTML files."""
    print(f"\nCreating output directory: {output_dir}")
    os.makedirs(output_dir, exist_ok=True)
    return True

def generate_toc(md_content):
    """Generate a simple table of contents from markdown headings."""
    toc = []
    lines = md_content.split('\n')
    
    for line in lines:
        if line.startswith('#'):
            level = 0
            while line.startswith('#'):
                level += 1
                line = line[1:]
            
            line = line.strip()
            if not line:  # Skip empty headings
                continue
                
            anchor = line.lower().replace(' ', '-')
            # Clean the anchor
            anchor = re.sub(r'[^\w\-]', '', anchor)
            
            # Create indentation based on heading level
            indent = "&nbsp;" * 4 * (level - 1)
            
            toc.append(f"<li>{indent}<a href=\"#{anchor}\">{line}</a></li>")
    
    return "\n".join(toc)

def process_headings(html_content):
    """Add anchor IDs to headings for TOC navigation."""
    for level in range(6, 0, -1):  # Process h6 to h1
        tag = f'h{level}'
        pattern = f'<{tag}>(.*?)</{tag}>'
        
        def add_anchor(match):
            heading_text = match.group(1)
            anchor_id = heading_text.lower().replace(' ', '-')
            anchor_id = re.sub(r'[^\w\-]', '', anchor_id)
            return f'<{tag} id="{anchor_id}">{heading_text}</{tag}>'
        
        html_content = re.sub(pattern, add_anchor, html_content)
    
    return html_content

def convert_workflow_diagrams(input_file, output_file, print_friendly=False):
    """Convert the workflow diagrams markdown to HTML with Mermaid support."""
    try:
        import markdown
        from markdown.extensions.codehilite import CodeHiliteExtension
        from markdown.extensions.toc import TocExtension
        
        print(f"Converting {input_file} to HTML...")
        
        # Read markdown file
        with open(input_file, 'r', encoding='utf-8') as f:
            md_content = f.read()
        
        # Extract any existing <style> tags from the markdown and preserve them
        custom_css = ""
        style_blocks = re.findall(r'<style>(.*?)</style>', md_content, re.DOTALL)
        for style in style_blocks:
            custom_css += style + "\n"
        
        # First, pre-process the markdown content to handle the mermaid code blocks
        # Look for the original markdown code blocks with mermaid
        mermaid_blocks = re.findall(r'```mermaid\s*([\s\S]*?)```', md_content)
        mermaid_div_replacements = {}

        # Number mermaid diagrams for unique identifiers
        for i, block in enumerate(mermaid_blocks):
            # Clean up the mermaid block
            clean_block = block.strip()
            
            # Fix common Mermaid syntax issues
            # 1. Replace problematic icon syntax
            clean_block = re.sub(r'::icon\((.*?)\)', ':::icon', clean_block)
            
            # 2. Fix class definitions that might cause issues
            clean_block = re.sub(r':::(\w+)\s+', ':::$1 ', clean_block)
            
            # 3. Fix any quotes that might be problematic
            clean_block = clean_block.replace('"', "'")
            
            # 4. Fix any syntax with mindmap that might cause issues
            if 'mindmap' in clean_block:
                # Make sure nodes are properly defined
                clean_block = re.sub(r'\(\((.*?)\)\)', '["$1"]', clean_block)
            
            # Store the cleaned block
            mermaid_div_replacements[f"MERMAID_DIAGRAM_{i}"] = f'<div class="mermaid">\n{clean_block}\n</div>'

        # Convert HTML using the markdown module
        html_content = markdown.markdown(
            md_content,
            extensions=[
                'tables', 
                'fenced_code', 
                CodeHiliteExtension(linenums=True), 
                TocExtension(baselevel=1, title="Table of Contents") 
            ]
        )

        # Process headings for TOC navigation
        html_content = process_headings(html_content)

        # Add a note about broken links in the main documentation
        if 'workflow_diagrams' in input_file.lower():
            # Add warning about cross-document links at the top of the page
            warning_html = """
            <div style="background-color: #fff3cd; color: #856404; padding: 15px; margin: 15px 0; border-radius: 5px; border: 1px solid #ffeeba;">
                <h3 style="margin-top: 0;"><span style="font-size: 1.2em;">⚠️</span> Note about Cross-Document Links</h3>
                <p>Some links between the User Documentation and Technical Reference documents may not work correctly in standalone HTML mode. 
                This is due to differences in heading structure between documents. To improve navigation:</p>
                <ul>
                    <li>Use the navigation links at the top of the page</li>
                    <li>Use the table of contents within each document</li>
                    <li>For PDF versions, use your PDF reader's search functionality</li>
                </ul>
            </div>
            """
            # Insert after the first heading
            html_content = re.sub(r'(<h1.*?</h1>)', r'\1' + warning_html, html_content, count=1)

        # Instead of using regex to find code blocks, replace all mermaid code blocks 
        # with properly formatted div elements using a more reliable approach
        for i, block in enumerate(mermaid_blocks):
            # Create pattern to find the corresponding HTML-encoded code block
            # This looks for both standard code blocks and syntax-highlighted ones
            escaped_block = re.escape(block)
            mermaid_prefix_newline = re.escape("mermaid\n" + block)
            patterns = [
                f'<pre><code>mermaid\\s*{escaped_block}</code></pre>',
                '<pre><code class=".*?">mermaid\\s*' + escaped_block + '</code></pre>',
                f'<pre><code>{mermaid_prefix_newline}</code></pre>',
                '<pre><code class=".*?">' + mermaid_prefix_newline + '</code></pre>'
            ]
            
            # Try each pattern
            replaced = False
            for pattern in patterns:
                if re.search(pattern, html_content, re.DOTALL):
                    html_content = re.sub(pattern, mermaid_div_replacements[f"MERMAID_DIAGRAM_{i}"], html_content, flags=re.DOTALL)
                    replaced = True
                    break
            
            # If none of the patterns matched, just insert the diagram at a suitable point
            if not replaced:
                placeholder = f"MERMAID_DIAGRAM_{i}"
                if placeholder in mermaid_div_replacements:
                    # Insert at a reasonable position (after any heading that might be relevant)
                    html_content = re.sub(
                        r'(</h[1-6]>)', 
                        r'\1\n' + mermaid_div_replacements[placeholder], 
                        html_content, 
                        count=1, 
                        flags=re.DOTALL
                    )

        # Add Mermaid support script
        mermaid_script = """
    <!-- Load Mermaid -->
    <script src="https://cdn.jsdelivr.net/npm/mermaid@9.1.3/dist/mermaid.min.js"></script>
    <script>
        // Define mermaid configuration BEFORE DOMContentLoaded
        mermaid.initialize({
            startOnLoad: false,  // We'll manually initialize
            theme: window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'default',
            flowchart: { useMaxWidth: true, htmlLabels: true },
            securityLevel: 'loose',
            logLevel: 'error'
        });

        document.addEventListener('DOMContentLoaded', function() {
            console.log("DOM loaded, initializing Mermaid");
            
            // Wait a moment to ensure the DOM is fully processed
            setTimeout(function() {
                try {
                    // Select all mermaid elements
                    const mermaidElements = document.querySelectorAll('.mermaid');
                    console.log("Found mermaid elements:", mermaidElements.length);
                    
                    // Manual initialization for each element
                    mermaidElements.forEach((element, index) => {
                        console.log(`Processing diagram ${index}`);
                        // Add a unique ID to each mermaid div for better tracking
                        element.id = `mermaid-diagram-${index}`;
                        
                        // Simply use the init method for v9.1.3
                        try {
                            if (!element.hasAttribute('data-processed')) {
                                mermaid.init(undefined, element);
                            }
                        } catch (e) {
                            console.error(`Error rendering diagram ${index}:`, e);
                            // Display error message for debugging
                            element.innerHTML = `
                                <div style="color:#721c24;background-color:#f8d7da;padding:10px;border:1px solid #f5c6cb;border-radius:5px;margin:10px 0;">
                                    <strong>Diagram rendering error</strong>
                                    <p>Please check syntax or try a different browser</p>
                                </div>`;
                        }
                    });
                    
                    // Ensure all remaining elements are initialized
                    try {
                        mermaid.init();
                    } catch (error) {
                        console.warn("General initialization error:", error);
                    }
                } catch (error) {
                    console.error("Error during Mermaid initialization:", error);
                }
            }, 1000);  // Longer timeout to ensure DOM is ready
        });

        // Add print-friendly styling for diagrams
        const style = document.createElement('style');
        style.textContent = `
            @media print {
                .mermaid {
                    overflow: visible !important;
                    margin-bottom: 20px !important;
                    page-break-inside: avoid !important;
                    background-color: white !important;
                }
                .mermaid svg {
                    max-width: 100% !important;
                    height: auto !important;
                }
            }
        `;
        document.head.appendChild(style);
    </script>
    """
        
        # Add basic styling - with print-friendly options if requested
        if print_friendly:
            css_styles = """
        body { 
            font-family: serif; 
            line-height: 1.6; 
            margin: 1cm;
            color: black;
            font-size: 12pt;
        }
        h1, h2, h3, h4, h5, h6 { 
            margin-top: 1.5em; 
            margin-bottom: 0.5em; 
            color: black;
            page-break-after: avoid;
        }
        h1 { 
            border-bottom: 1px solid black;
            padding-bottom: 0.3em;
            font-size: 18pt;
        }
        h2 { 
            border-bottom: 1px solid #aaa;
            padding-bottom: 0.3em;
            font-size: 16pt;
        }
        h3 { font-size: 14pt; }
        p { margin: 1em 0; }
        a { color: black; text-decoration: underline; }
        code { 
            background-color: #f0f0f0; 
            padding: 2px 4px; 
            border-radius: 3px; 
            font-family: monospace;
            font-size: 90%;
        }
        pre { 
            background-color: #f0f0f0; 
            padding: 12px; 
            border-radius: 5px; 
            overflow-x: auto;
            page-break-inside: avoid;
            border: 1px solid #ddd;
            font-family: monospace;
        }
        pre code { 
            background-color: transparent; 
            padding: 0; 
            border-radius: 0; 
        }
        table { 
            border-collapse: collapse; 
            width: 100%; 
            margin: 1em 0;
            page-break-inside: avoid;
        }
        th, td { 
            border: 1px solid black; 
            padding: 6px 12px; 
            text-align: left; 
        }
        th { 
            background-color: #f2f2f2; 
            font-weight: bold;
        }
        tr:nth-child(even) { background-color: #f8f8f8; }
        blockquote {
            margin: 1em 0;
            padding: 0 1em;
            color: #444;
            border-left: 0.25em solid #ddd;
            page-break-inside: avoid;
        }
        ul, ol {
            padding-left: 2em;
            page-break-inside: avoid;
        }
        .toc {
            background-color: #f8f8f8;
            border: 1px solid #e8e8e8;
            border-radius: 3px;
            padding: 1em;
            margin: 1em 0 2em 0;
            page-break-after: always;
        }
        .toc h2 {
            margin-top: 0;
            border-bottom: none;
        }
        .codehilite { 
            background: #f8f8f8; 
            border-radius: 3px;
            page-break-inside: avoid;
        }
        .codehilite pre { 
            margin: 0; 
            padding: 8px; 
        }
        img { 
            max-width: 100%;
            height: auto;
        }
        hr { 
            border: 0;
            height: 1px;
            background-color: black;
            margin: 1.5em 0;
        }
        footer {
            margin-top: 2em;
            border-top: 1px solid #eee;
            padding-top: 1em;
            font-size: 10pt;
            color: #666;
        }
        @media print {
            .nav { display: none; }
            a { text-decoration: none; }
            a[href]:after { content: " (" attr(href) ")"; color: #666; font-size: 90%; }
            a[href^="#"]:after { content: ""; }
            .toc { page-break-after: always; }
            h1, h2, h3, h4, h5, h6 { page-break-after: avoid; }
            thead { display: table-header-group; }
            img, pre, tr, blockquote, ul, ol { page-break-inside: avoid; }
            p { orphans: 3; widows: 3; }
        }
        .mermaid {
            background-color: white !important;
            text-align: center;
            max-width: 100%;
            margin: 20px auto;
            padding: 10px;
            border-radius: 5px;
            page-break-inside: avoid;
            display: block !important;
            overflow: auto;
        }
        .mermaid svg {
            display: block;
            margin: auto;
            max-width: 100%;
            height: auto !important;
        }
        /* Ensure colored nodes in diagrams are visible in dark mode */
        .node rect, .node circle, .node ellipse, .node polygon, .node path {
            stroke-width: 2px;
        }
        /* Make diagram text readable */
        .mermaid .label {
            font-family: 'Trebuchet MS', 'Lucida Sans Unicode', 'Lucida Grande', 'Lucida Sans', Arial, sans-serif;
            font-size: 14px;
            color: #333;
        }
        .mermaid .cluster rect {
            stroke-width: 2px;
        }
        """ + custom_css
            
            # Hide navigation in print-friendly version
            nav_html = """<div class="print-header">
        <h2 class="print-title">Forest Fire Simulation Framework</h2>
        <p class="print-subtitle">Workflow Diagrams</p>
    </div>"""
        else:
            css_styles = """
        body { 
            font-family: Arial, sans-serif; 
            line-height: 1.6; 
            margin: 0 auto;
            max-width: 800px;
            padding: 20px;
            color: #333;
        }
        h1, h2, h3, h4, h5, h6 { 
            margin-top: 1.5em; 
            margin-bottom: 0.5em; 
            color: #2c3e50;
        }
        h1 { 
            border-bottom: 2px solid #eaecef;
            padding-bottom: 0.3em;
            font-size: 2em;
        }
        h2 { 
            border-bottom: 1px solid #eaecef;
            padding-bottom: 0.3em;
            font-size: 1.5em;
        }
        p { margin: 1em 0; }
        a { color: #0366d6; text-decoration: none; }
        a:hover { text-decoration: underline; }
        code { 
            background-color: #f5f7f9; 
            padding: 2px 4px; 
            border-radius: 3px; 
            font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
            font-size: 85%;
        }
        pre { 
            background-color: #f5f7f9; 
            padding: 16px; 
            border-radius: 5px; 
            overflow-x: auto;
            line-height: 1.45;
            font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
        }
        pre code { 
            background-color: transparent; 
            padding: 0; 
            border-radius: 0; 
        }
        table { 
            border-collapse: collapse; 
            width: 100%; 
            margin: 1em 0;
        }
        th, td { 
            border: 1px solid #dfe2e5; 
            padding: 8px 16px; 
            text-align: left; 
        }
        th { 
            background-color: #f2f2f2; 
            font-weight: 600;
        }
        tr:nth-child(even) { background-color: #f8f8f8; }
        blockquote {
            margin: 1em 0;
            padding: 0 1em;
            color: #6a737d;
            border-left: 0.25em solid #dfe2e5;
        }
        ul, ol {
            padding-left: 2em;
        }
        .toc {
            background-color: #f8f8f8;
            border: 1px solid #e8e8e8;
            border-radius: 3px;
            padding: 1em;
            margin: 1em 0;
        }
        .toc h2 {
            margin-top: 0;
            border-bottom: none;
        }
        .codehilite { 
            background: #f8f8f8; 
            border-radius: 5px;
        }
        .codehilite pre { 
            margin: 0; 
            padding: 10px; 
        }
        .linenos { 
            color: #999;
            padding-right: 10px;
            border-right: 1px solid #e1e4e8;
            text-align: right;
        }
        img { 
            max-width: 100%;
            height: auto;
        }
        hr { 
            border: 0;
            height: 1px;
            background-color: #dfe2e5;
            margin: 1.5em 0;
        }
        /* Navigation */
        .nav {
            display: flex;
            justify-content: space-between;
            margin-bottom: 1em;
            border-bottom: 1px solid #eaecef;
            padding-bottom: 1em;
        }
        .nav a {
            padding: 0.5em 1em;
            background-color: #f1f1f1;
            border-radius: 4px;
        }
        /* Dark mode */
        @media (prefers-color-scheme: dark) {
            body { 
                background-color: #0d1117; 
                color: #c9d1d9;
            }
            h1, h2, h3, h4, h5, h6 { 
                color: #e6edf3;
            }
            h1, h2 { 
                border-bottom-color: #21262d;
            }
            a { color: #58a6ff; }
            code { background-color: #161b22; }
            pre { background-color: #161b22; }
            table { border-color: #30363d; }
            th, td { border-color: #30363d; }
            th { background-color: #161b22; }
            tr:nth-child(even) { background-color: #161b22; }
            blockquote { 
                color: #8b949e;
                border-left-color: #30363d;
            }
            .toc { 
                background-color: #161b22;
                border-color: #30363d;
            }
            .nav a { 
                background-color: #21262d;
                color: #c9d1d9;
            }
            .codehilite { background: #161b22; }
            hr { background-color: #21262d; }
            .mermaid {
                background-color: #161b22 !important;
            }
        }
        .mermaid {
            background-color: white !important;
            text-align: center;
            max-width: 100%;
            margin: 20px auto;
            padding: 10px;
            border-radius: 5px;
            display: block !important;
            overflow: auto;
        }
        .mermaid svg {
            display: block;
            margin: auto;
            max-width: 100%;
            height: auto !important;
        }
        /* Ensure colored nodes in diagrams are visible in dark mode */
        .node rect, .node circle, .node ellipse, .node polygon, .node path {
            stroke-width: 2px;
        }
        /* Make diagram text readable */
        .mermaid .label {
            font-family: 'Trebuchet MS', 'Lucida Sans Unicode', 'Lucida Grande', 'Lucida Sans', Arial, sans-serif;
            font-size: 14px;
            color: #333;
        }
        .mermaid .cluster rect {
            stroke-width: 2px;
        }
        """ + custom_css
            
            # Navigation menu for regular HTML
            nav_html = """<div class="nav">
        <a href="index.html">Back to Index</a>
        <span>
            <a href="Forest_Fire_Simulation_Documentation.html">User Documentation</a>
            <a href="Forest_Fire_Simulation_Technical_Reference.html">Technical Reference</a>
        </span>
    </div>"""
        
        # Add print button if not print-friendly version
        print_button = "" if print_friendly else f"""
    <div style="text-align: right; margin-top: 1em;">
        <a href="{os.path.basename(output_file).replace('.html', '')}_print.html" style="padding: 0.5em 1em; background-color: #eee; border-radius: 4px; text-decoration: none; display: inline-block;">
            <span style="vertical-align: middle;">📄 Print-friendly version</span>
        </a>
    </div>"""
        
        # Combine all HTML elements
        styled_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Forest Fire Workflow Diagrams</title>
    <style>
        {css_styles}
    </style>
    {mermaid_script}
</head>
<body>
    {nav_html}
    
    <h1>Forest Fire Workflow Diagrams</h1>
    {print_button}
    
    <div class="toc">
        <h2>Table of Contents</h2>
        <ul>
            {generate_toc(md_content)}
        </ul>
    </div>
    
    {html_content}
    
    <hr>
    <footer>
        <p><small>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Forest Fire Simulation Framework</small></p>
    </footer>
</body>
</html>"""
        
        # Write HTML file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(styled_html)
        
        print(f"Successfully created {output_file}")
        return True
    except ImportError:
        print("Missing required Python modules. Make sure markdown is installed.")
        return False
    except Exception as e:
        print(f"Error during conversion: {e}")
        return False

def open_in_browser(html_file):
    """Attempt to open the HTML file in the default browser."""
    try:
        import webbrowser
        webbrowser.open('file://' + os.path.abspath(html_file))
        print(f"Opened {html_file} in your default web browser.")
        return True
    except:
        print(f"Unable to open browser automatically. Please open {html_file} manually.")
        return False

def main():
    # Parse command-line arguments if any
    import argparse
    parser = argparse.ArgumentParser(description="Convert Forest Fire Workflow Diagrams to HTML with proper Mermaid support.")
    parser.add_argument("--print", action="store_true", help="Generate print-friendly version for PDF conversion")
    parser.add_argument("--no-browser", action="store_true", help="Don't open the result in browser")
    args = parser.parse_args()
    
    # Setup
    html_dir = "html_docs"
    create_output_dir(html_dir)
    install_requirements()
    
    # Input file
    input_file = "forest_fire_workflow_diagrams.md"
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return False
    
    # Output files
    output_file = os.path.join(html_dir, "forest_fire_workflow_diagrams.html")
    
    # Convert to HTML
    if convert_workflow_diagrams(input_file, output_file):
        print(f"\nWorkflow diagrams successfully converted to HTML:")
        print(f"- {output_file}")
        
        # Create print-friendly version if requested
        if args.print:
            print_output_file = os.path.join(html_dir, "forest_fire_workflow_diagrams_print.html")
            if convert_workflow_diagrams(input_file, print_output_file, print_friendly=True):
                print(f"- {print_output_file} (print-friendly version)")
        
        # Open in browser if not disabled
        if not args.no_browser:
            open_in_browser(output_file)
            
        print("\nTo create a PDF from the HTML:")
        print("1. Open the HTML file in your browser")
        print("2. Use the browser's print function (Ctrl+P or Cmd+P)")
        print("3. Choose 'Save as PDF' as the destination")
        print("4. Click 'Save' to create the PDF")
        
        return True
    else:
        print("Failed to convert workflow diagrams.")
        return False

if __name__ == "__main__":
    print("=" * 80)
    print("Forest Fire Workflow Diagrams Generator")
    print("=" * 80)
    main() 