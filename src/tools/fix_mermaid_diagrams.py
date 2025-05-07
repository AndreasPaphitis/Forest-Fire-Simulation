#!/usr/bin/env python3
"""
Fix Mermaid Diagrams

This script specifically addresses issues with Mermaid diagram rendering in the 
Forest Fire Workflow Diagrams HTML files.
"""

import os
import re
import sys
import webbrowser
from pathlib import Path
from datetime import datetime

def ensure_output_dir(dir_path):
    """Create the output directory if it doesn't exist."""
    os.makedirs(dir_path, exist_ok=True)
    return dir_path

def fix_mermaid_syntax(mermaid_content):
    """Fix common issues in Mermaid diagram syntax."""
    # Fix 1: Replace :::$1 with proper class references
    fixed_content = re.sub(r':::\$1', ':::capability', mermaid_content)
    
    # Fix 2: Replace incorrect HTML entity encoding in class definitions
    fixed_content = re.sub(r'\((\'\S+&lt;br/&gt;.+\')\)', '("$1")', fixed_content)
    
    # Fix 3: Fix arrow syntax
    fixed_content = fixed_content.replace('-.-&gt;', '-->')
    fixed_content = fixed_content.replace('--&gt;', '-->')
    
    # Fix 4: Replace broken class definitions
    fixed_content = re.sub(r'classDef (\w+) (fill:[^,]+),', r'classDef \1 \2,', fixed_content)
    
    # Fix 5: Replace HTML entities with actual characters
    fixed_content = fixed_content.replace('&lt;', '<')
    fixed_content = fixed_content.replace('&gt;', '>')
    fixed_content = fixed_content.replace('&amp;', '&')
    
    # Fix 6: Handle mindmap nodes with HTML entities
    if 'mindmap' in fixed_content:
        # Fix node text with HTML entities
        fixed_content = re.sub(r'\(\((.*?)\)\)', r'["$1"]', fixed_content)
        fixed_content = re.sub(r'\[\[(.*?)\]\]', r'[[$1]]', fixed_content)
    
    # Fix 7: Handle quotes in node text
    fixed_content = re.sub(r'(\(|\[)"(.*?)"(|\]|\))', r'\1\2\3', fixed_content)
    
    # Fix 8: Fix complex class definitions
    fixed_content = re.sub(r'class\s+(\w+)\s+(\w+)', r'class \1 \2', fixed_content)
    
    # Fix 9: Handle flowchart syntax
    if 'flowchart' in fixed_content or 'graph' in fixed_content:
        # Fix node definitions
        fixed_content = re.sub(r'(\w+)\[(.*?)\]', r'\1["$2"]', fixed_content)
        # Fix edge labels
        fixed_content = re.sub(r'-->\|\'(.*?)\'\|', r'-->|$1|', fixed_content)
    
    # Fix 10: Handle sequenceDiagram syntax
    if 'sequenceDiagram' in fixed_content:
        # Fix participant definitions
        fixed_content = re.sub(r'participant\s+(\w+)\s+as\s+(.*?)$', r'participant \1 as "\2"', fixed_content, flags=re.MULTILINE)
    
    # Fix 11: Handle special style markers
    fixed_content = re.sub(r'style\s+(\w+)\s+fill:(.*?),', r'style \1 fill:\2,', fixed_content)
    
    return fixed_content

def update_mermaid_version(html_content):
    """Update the Mermaid version to a more stable one for complex diagrams."""
    # Update to a newer version of Mermaid that handles complex diagrams better
    return html_content.replace(
        '<script src="https://cdn.jsdelivr.net/npm/mermaid@9.1.3/dist/mermaid.min.js"></script>',
        '<script src="https://cdn.jsdelivr.net/npm/mermaid@9.3.0/dist/mermaid.min.js"></script>'
    )

def add_debug_info(html_content):
    """Add debug information to help identify rendering issues."""
    # Find the script tag that initializes Mermaid
    script_pattern = re.search(r'<script>\s*document\.addEventListener\(\'DOMContentLoaded.*?</script>', html_content, flags=re.DOTALL)
    
    if not script_pattern:
        print("Warning: Could not find Mermaid initialization script. Adding new script instead.")
        # If we can't find the script, just insert our new script before the closing </head> tag
        debug_script = """
    <script>
        // Initialize Mermaid with specific configuration for better compatibility
        mermaid.initialize({
            startOnLoad: true,
            theme: 'default',
            logLevel: 'debug',
            securityLevel: 'loose',
            flowchart: {
                useMaxWidth: true,
                htmlLabels: true,
                curve: 'basis'
            },
            sequence: {
                useMaxWidth: true
            },
            gantt: {
                useMaxWidth: true
            },
            mindmap: {
                useMaxWidth: true
            }
        });
        
        // Attempt to render any diagrams that failed initial rendering
        document.addEventListener('DOMContentLoaded', function() {
            // Add a slight delay to ensure DOM is ready
            setTimeout(function() {
                // Try to find and render any unrendered diagrams
                const diagrams = document.querySelectorAll('.mermaid');
                for (let i = 0; i < diagrams.length; i++) {
                    const diagram = diagrams[i];
                    if (!diagram.querySelector('svg')) {
                        console.log('Attempting to re-render diagram:', i + 1);
                        const content = diagram.textContent.trim();
                        try {
                            // Clear and try to render again
                            diagram.innerHTML = '';
                            mermaid.render('mermaid-diagram-' + i, content, function(svgCode) {
                                diagram.innerHTML = svgCode;
                            });
                        } catch (e) {
                            console.error('Error re-rendering diagram:', e);
                            // Add error message to diagram container
                            const errorDiv = document.createElement('div');
                            errorDiv.style.color = 'red';
                            errorDiv.style.padding = '10px';
                            errorDiv.style.border = '1px solid red';
                            errorDiv.style.margin = '10px 0';
                            errorDiv.innerHTML = `<strong>Error rendering diagram:</strong> ${e.message}`;
                            diagram.appendChild(errorDiv);
                        }
                    }
                }
                
                // Hide all loading messages
                var loadingElements = document.querySelectorAll('.loading');
                loadingElements.forEach(function(el) {
                    el.style.display = 'none';
                });
            }, 1000);
        });
        
        // Add error handler for Mermaid
        window.addEventListener('error', function(e) {
            if (e.error && e.error.message && e.error.message.includes('mermaid')) {
                console.error('Mermaid error:', e.error);
                const errorDiv = document.createElement('div');
                errorDiv.style.color = 'red';
                errorDiv.style.padding = '10px';
                errorDiv.style.border = '1px solid red';
                errorDiv.style.margin = '10px 0';
                errorDiv.innerHTML = `<strong>Error rendering diagram:</strong> ${e.error.message}`;
                
                // Try to find the closest diagram container
                const diagrams = document.querySelectorAll('.diagram');
                for (let diag of diagrams) {
                    if (diag.contains(e.target)) {
                        diag.appendChild(errorDiv);
                        break;
                    }
                }
            }
        });
    </script>
    """
        return html_content.replace("</head>", debug_script + "</head>")
    else:
        # Replace the found script with our debug script
        debug_script = """
    <script>
        // Initialize Mermaid with specific configuration for better compatibility
        mermaid.initialize({
            startOnLoad: true,
            theme: 'default',
            logLevel: 'debug',
            securityLevel: 'loose',
            flowchart: {
                useMaxWidth: true,
                htmlLabels: true,
                curve: 'basis'
            },
            sequence: {
                useMaxWidth: true
            },
            gantt: {
                useMaxWidth: true
            },
            mindmap: {
                useMaxWidth: true
            }
        });
        
        // Attempt to render any diagrams that failed initial rendering
        document.addEventListener('DOMContentLoaded', function() {
            // Add a slight delay to ensure DOM is ready
            setTimeout(function() {
                // Try to find and render any unrendered diagrams
                const diagrams = document.querySelectorAll('.mermaid');
                for (let i = 0; i < diagrams.length; i++) {
                    const diagram = diagrams[i];
                    if (!diagram.querySelector('svg')) {
                        console.log('Attempting to re-render diagram:', i + 1);
                        const content = diagram.textContent.trim();
                        try {
                            // Clear and try to render again
                            diagram.innerHTML = '';
                            mermaid.render('mermaid-diagram-' + i, content, function(svgCode) {
                                diagram.innerHTML = svgCode;
                            });
                        } catch (e) {
                            console.error('Error re-rendering diagram:', e);
                            // Add error message to diagram container
                            const errorDiv = document.createElement('div');
                            errorDiv.style.color = 'red';
                            errorDiv.style.padding = '10px';
                            errorDiv.style.border = '1px solid red';
                            errorDiv.style.margin = '10px 0';
                            errorDiv.innerHTML = `<strong>Error rendering diagram:</strong> ${e.message}`;
                            diagram.appendChild(errorDiv);
                        }
                    }
                }
                
                // Hide all loading messages
                var loadingElements = document.querySelectorAll('.loading');
                loadingElements.forEach(function(el) {
                    el.style.display = 'none';
                });
            }, 1000);
        });
        
        // Add error handler for Mermaid
        window.addEventListener('error', function(e) {
            if (e.error && e.error.message && e.error.message.includes('mermaid')) {
                console.error('Mermaid error:', e.error);
                const errorDiv = document.createElement('div');
                errorDiv.style.color = 'red';
                errorDiv.style.padding = '10px';
                errorDiv.style.border = '1px solid red';
                errorDiv.style.margin = '10px 0';
                errorDiv.innerHTML = `<strong>Error rendering diagram:</strong> ${e.error.message}`;
                
                // Try to find the closest diagram container
                const diagrams = document.querySelectorAll('.diagram');
                for (let diag of diagrams) {
                    if (diag.contains(e.target)) {
                        diag.appendChild(errorDiv);
                        break;
                    }
                }
            }
        });
    </script>
    """
        return html_content.replace(script_pattern.group(0), debug_script)

def fix_mermaid_diagrams_in_html(html_file):
    """Fix Mermaid diagrams in the HTML file."""
    print(f"Processing HTML file: {html_file}")
    
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Update Mermaid version
    html_content = update_mermaid_version(html_content)
    
    # Find all Mermaid diagram blocks
    mermaid_blocks = re.findall(r'<div class="mermaid">\s*([\s\S]*?)\s*</div>', html_content)
    print(f"Found {len(mermaid_blocks)} Mermaid diagrams")
    
    # Fix each Mermaid block
    for i, block in enumerate(mermaid_blocks):
        print(f"  Fixing diagram {i+1}...")
        fixed_block = fix_mermaid_syntax(block)
        
        # Replace the original block with the fixed one
        # Use a more robust approach to replace the content
        pattern = re.escape(f'<div class="mermaid">\n{block}\n            </div>')
        replacement = f'<div class="mermaid">\n{fixed_block}\n            </div>'
        html_content = re.sub(pattern, replacement, html_content)
    
    # Add debug information after we've processed all blocks
    html_content = add_debug_info(html_content)
    
    # Create a timestamp for the filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Create the output filename
    file_dir = os.path.dirname(html_file)
    file_name = os.path.basename(html_file)
    fixed_file = os.path.join(file_dir, f"{os.path.splitext(file_name)[0]}_fixed.html")
    
    # Create a backup of the original file
    backup_file = os.path.join(file_dir, f"{os.path.splitext(file_name)[0]}_backup_{timestamp}.html")
    with open(backup_file, 'w', encoding='utf-8') as f:
        f.write(html_content.replace("max-width: 900px;", "max-width: 100%;"))
    print(f"Created backup: {backup_file}")
    
    # Write the fixed HTML to a new file
    with open(fixed_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"Created fixed HTML: {fixed_file}")
    
    # Create a print-friendly version
    print_file = os.path.join(file_dir, f"{os.path.splitext(file_name)[0]}_fixed_print.html")
    with open(print_file, 'w', encoding='utf-8') as f:
        f.write(html_content.replace("max-width: 900px;", "max-width: 100%;"))
    
    print(f"Created print-friendly HTML: {print_file}")
    
    return fixed_file

def create_standalone_diagrams(html_file):
    """Create standalone HTML files for each diagram."""
    print(f"\nCreating standalone diagrams from {html_file}...")
    
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Find all diagram containers with titles and content
    diagram_pattern = re.compile(r'<div class="diagram-container" id="diagram-(\d+)">\s*<h2 class="diagram-title">(.*?)</h2>\s*<div class="diagram">.*?<div class="mermaid">\s*([\s\S]*?)\s*</div>\s*</div>\s*</div>', re.DOTALL)
    diagrams = diagram_pattern.findall(html_content)
    
    # Create an output directory for standalone diagrams
    output_dir = os.path.join(os.path.dirname(html_file), "standalone_diagrams")
    ensure_output_dir(output_dir)
    
    # Define the Mermaid versions to test with
    versions = ["9.3.0", "9.1.3", "8.14.0", "10.8.0"]
    
    # Create individual diagrams
    for num, title, content in diagrams:
        # Clean up the title for use in a filename
        clean_title = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '_').lower()
        
        # Base filename for this diagram
        base_filename = f"diagram_{num}_{clean_title}"
        standalone_file = os.path.join(output_dir, f"{base_filename}.html")
        
        # Create version-specific files
        for version in versions:
            version_file = os.path.join(output_dir, f"{base_filename}_{version}.html")
            
            with open(version_file, 'w', encoding='utf-8') as f:
                # Fix: Make sure all format parameters are properly numbered
                html_template = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Diagram {0}: {1} (Mermaid {2})</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@{2}/dist/mermaid.min.js"></script>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 0 auto;
            max-width: 900px;
            padding: 20px;
            color: #333;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        h1 {{
            color: #1a237e;
            text-align: center;
        }}
        .diagram-container {{
            background-color: white;
            padding: 2em;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            margin: 2em 0;
            width: 100%;
            max-width: 800px;
        }}
        .mermaid {{
            text-align: center;
        }}
        .version-info {{
            background-color: #e3f2fd;
            padding: 5px 10px;
            border-radius: 4px;
            margin-bottom: 20px;
            font-size: 0.9em;
        }}
        .other-versions {{
            margin-top: 20px;
            border-top: 1px solid #eee;
            padding-top: 15px;
        }}
        .other-versions a {{
            margin: 0 10px;
            text-decoration: none;
            color: #1a237e;
        }}
        .other-versions a:hover {{
            text-decoration: underline;
        }}
    </style>
    <script>
        mermaid.initialize({{
            startOnLoad: true,
            theme: 'default',
            flowchart: {{
                useMaxWidth: true,
                htmlLabels: true,
                curve: 'basis'
            }},
            securityLevel: 'loose',
            logLevel: 'debug'
        }});
    </script>
</head>
<body>
    <h1>{1}</h1>
    <div class="version-info">Using Mermaid version: {2}</div>
    <div class="diagram-container">
        <div class="mermaid">
{3}
        </div>
    </div>
    <div class="other-versions">
        <p>Try other Mermaid versions:</p>
        {4}
    </div>
</body>
</html>"""

                # Generate other version links
                version_links = []
                for v in versions:
                    if v != version:
                        version_links.append(f'<a href="{base_filename}_{v}.html">{v}</a>')
                all_version_links = "\n        ".join(version_links)
                
                # Format the HTML template
                html_content = html_template.format(
                    num,         # {0}
                    title,       # {1}
                    version,     # {2}
                    content,     # {3}
                    all_version_links # {4}
                )
                
                f.write(html_content)
        
        # Create main index file for this diagram
        with open(standalone_file, 'w', encoding='utf-8') as f:
            html_template = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Diagram {0}: {1}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 0 auto;
            max-width: 800px;
            padding: 20px;
        }}
        h1 {{
            color: #1a237e;
            text-align: center;
        }}
        .versions {{
            display: flex;
            flex-direction: column;
            gap: 20px;
            margin-top: 30px;
        }}
        .version {{
            border: 1px solid #eee;
            border-radius: 8px;
            padding: 20px;
        }}
        h2 {{
            margin-top: 0;
            color: #303f9f;
        }}
        iframe {{
            width: 100%;
            height: 600px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }}
    </style>
</head>
<body>
    <h1>Diagram {0}: {1}</h1>
    <p>This page shows the diagram rendered with different Mermaid versions to help identify which version works best.</p>
    
    <div class="versions">
        {2}
    </div>
</body>
</html>"""
            
            # Create version blocks
            version_blocks = []
            for v in versions:
                version_blocks.append(f'<div class="version"><h2>Mermaid {v}</h2><iframe src="{base_filename}_{v}.html"></iframe></div>')
            all_version_blocks = "\n        ".join(version_blocks)
            
            # Format the HTML template
            html_content = html_template.format(
                num,              # {0}
                title,            # {1}
                all_version_blocks # {2}
            )
            
            f.write(html_content)
        
        print(f"  Created standalone diagram: {standalone_file}")
    
    # Create main index file for all diagrams
    index_file = os.path.join(output_dir, "index.html")
    with open(index_file, 'w', encoding='utf-8') as f:
        html_template = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Forest Fire Workflow Diagrams - Individual Diagrams</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 0 auto;
            max-width: 900px;
            padding: 20px;
            color: #333;
        }}
        h1 {{
            color: #1a237e;
            border-bottom: 2px solid #eaecef;
            padding-bottom: 0.3em;
        }}
        .diagrams-list {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 30px;
        }}
        .diagram-card {{
            border: 1px solid #eee;
            border-radius: 8px;
            padding: 15px;
            background-color: #f9f9f9;
            transition: transform 0.2s;
        }}
        .diagram-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }}
        .diagram-card h2 {{
            margin-top: 0;
            font-size: 1.2em;
            color: #303f9f;
        }}
        .diagram-card a {{
            text-decoration: none;
            color: #1a237e;
            display: block;
            padding: 8px 0;
        }}
        .diagram-card a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <h1>Forest Fire Workflow Diagrams - Individual Diagrams</h1>
    <p>This page provides access to each diagram individually, with multiple rendering options to help fix any rendering issues.</p>
    
    <div class="diagrams-list">
        {0}
    </div>
</body>
</html>"""
        
        # Generate diagram cards
        diagram_cards = []
        for num, title, _ in diagrams:
            clean_title = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '_').lower()
            base_filename = f"diagram_{num}_{clean_title}"
            diagram_cards.append(f'<div class="diagram-card"><h2>Diagram {num}: {title}</h2><a href="{base_filename}.html">View this diagram</a></div>')
        
        all_diagram_cards = "\n        ".join(diagram_cards)
        
        # Format the HTML template
        html_content = html_template.format(all_diagram_cards)
        
        f.write(html_content)
    
    print(f"Created {len(diagrams)} standalone diagram files in {output_dir}")
    print(f"Created index file: {index_file}")
    return output_dir, index_file

def open_in_browser(html_file):
    """Open the HTML file in the default browser."""
    try:
        webbrowser.open('file://' + os.path.abspath(html_file))
        print(f"Opened {html_file} in your default web browser.")
        return True
    except:
        print(f"Unable to open browser automatically. Please open {html_file} manually.")
        return False

def main():
    # Set up paths
    html_dir = "html_docs"
    
    # Define the workflow diagrams HTML file
    default_html_file = os.path.join(html_dir, "forest_fire_workflow_diagrams_static.html")
    
    # Check if the file exists
    if not os.path.exists(default_html_file):
        print(f"Error: {default_html_file} not found.")
        
        # Look for an alternative workflow diagrams file
        alt_file = os.path.join(html_dir, "forest_fire_workflow_diagrams.html")
        if os.path.exists(alt_file):
            print(f"Found alternative file: {alt_file}")
            default_html_file = alt_file
        else:
            print(f"Error: No workflow diagrams HTML file found in {html_dir}")
            return False
    
    # Fix the Mermaid diagrams in the HTML file
    fixed_file = fix_mermaid_diagrams_in_html(default_html_file)
    
    # Create standalone diagrams
    output_dir, index_file = create_standalone_diagrams(fixed_file)
    
    # Open the fixed file in a browser
    open_in_browser(fixed_file)
    
    # Also open the index of standalone diagrams
    print("\nOpening index of standalone diagrams...")
    open_in_browser(index_file)
    
    print("\nProcess complete!")
    print("-" * 50)
    print("If you're still having issues with diagram rendering:")
    print("1. Check the standalone diagrams in the 'standalone_diagrams' folder")
    print("2. Try different Mermaid versions for each diagram")
    print("3. Use the Mermaid Live Editor (https://mermaid.live) to debug diagrams")
    print("4. The fixed HTML uses Mermaid 9.3.0 which has better compatibility with complex diagrams")
    print("-" * 50)
    
    return True

if __name__ == "__main__":
    print("=" * 80)
    print("Forest Fire Workflow Diagrams - Mermaid Fixer")
    print("=" * 80)
    main() 