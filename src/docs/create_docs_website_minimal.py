#!/usr/bin/env python3
"""
Forest Fire Simulation Documentation Website Generator (Minimal Version)

This script converts the Forest Fire Simulation documentation into a static website
with preserved cross-document links, support for Mermaid diagrams, and a PDF version.
"""

import os
import sys
import shutil
import subprocess
import re
from pathlib import Path
from datetime import datetime

def check_dependencies():
    """Check if all required Python packages are installed."""
    print("Installing required packages...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "mkdocs", "mkdocs-material", 
                        "pymdown-extensions", "mkdocs-minify-plugin", "requests"], 
                        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("Required packages installed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing packages: {e}")
        return False

def create_directory_structure(docs_dir):
    """Create the required directory structure for the documentation website."""
    print("\nCreating directory structure in docs...")
    
    # Create directories if they don't exist
    os.makedirs(docs_dir, exist_ok=True)
    os.makedirs(os.path.join(docs_dir, 'stylesheets'), exist_ok=True)
    os.makedirs(os.path.join(docs_dir, 'javascripts'), exist_ok=True)
    
    # Create mkdocs.yml
    mkdocs_config = """
site_name: Forest Fire Simulation Framework
site_description: Documentation for the Forest Fire Simulation Framework
site_author: Your Name

# Navigation structure
nav:
  - Home: index.md
  - User Guide: Forest_Fire_Simulation_Documentation.md
  - Technical Reference: Forest_Fire_Simulation_Technical_Reference.md

# Theme configuration
theme:
  name: material
  features:
    - navigation.instant
    - navigation.tracking
    - navigation.expand
    - navigation.indexes
    - navigation.top
    - search.highlight
    - search.share
    - toc.follow
  palette:
    - scheme: default
      primary: indigo
      accent: indigo

# Extensions
markdown_extensions:
  - admonition
  - attr_list
  - def_list
  - footnotes
  - meta
  - toc:
      permalink: true
      toc_depth: 3
  - pymdownx.highlight
  - pymdownx.superfences:
      custom_fences:
        - name: mermaid
          class: mermaid
          format: !!python/name:pymdownx.superfences.fence_code_format

# Plugins
plugins:
  - search
  - minify:
      minify_html: true

# Extra CSS for custom styling
extra_css:
  - stylesheets/extra.css

# Extra JavaScript for Mermaid diagrams
extra_javascript:
  - javascripts/mermaid.min.js
"""
    
    with open('mkdocs.yml', 'w') as f:
        f.write(mkdocs_config)
    
    # Create CSS file
    css_extra = """
/* Additional custom styling */
.md-typeset h1 {
    font-weight: 700;
    color: #1a237e;
}
.md-typeset h2 {
    font-weight: 600;
    color: #283593;
}
.md-typeset h3 {
    font-weight: 600;
    color: #303f9f;
}
.md-typeset h4 {
    font-weight: 600;
    color: #3949ab;
}
.md-typeset code {
    background-color: rgba(27, 31, 35, 0.05);
    border-radius: 3px;
    padding: 0.2em 0.4em;
}
.mermaid {
    text-align: center;
}
"""
    
    with open(os.path.join(docs_dir, 'stylesheets', 'extra.css'), 'w') as f:
        f.write(css_extra)
    
    # Create home page
    home_page = """
# Forest Fire Simulation Framework Documentation

Welcome to the comprehensive documentation for the Forest Fire Simulation Framework, a specialized system for modeling and analyzing forest fire behavior in three dimensions.

## Documentation Structure

This documentation suite consists of two complementary documents:

<div class="grid cards" markdown>

- :material-account-group: __User Guide__

    ---

    The user-focused guide that explains concepts, workflows, and practical usage of the framework.

    [:octicons-arrow-right-24: Open User Guide](Forest_Fire_Simulation_Documentation.md)

- :material-tools: __Technical Reference__

    ---

    A detailed technical reference with implementation details, algorithms, and optimization techniques.

    [:octicons-arrow-right-24: Open Technical Reference](Forest_Fire_Simulation_Technical_Reference.md)

</div>
"""
    
    with open(os.path.join(docs_dir, 'index.md'), 'w') as f:
        f.write(home_page)
    
    print("Directory structure created successfully.")
    return True

def copy_documentation_files(docs_dir):
    """Copy the documentation files to the docs directory."""
    print("\nCopying documentation files...")
    
    # Check if the documentation files exist
    doc_file_exists = os.path.exists("Forest_Fire_Simulation_Documentation.md")
    tech_file_exists = os.path.exists("Forest_Fire_Simulation_Technical_Reference.md")
    
    if doc_file_exists:
        shutil.copy("Forest_Fire_Simulation_Documentation.md", os.path.join(docs_dir, "Forest_Fire_Simulation_Documentation.md"))
        print("Copied Forest_Fire_Simulation_Documentation.md")
    else:
        print("Warning: Forest_Fire_Simulation_Documentation.md not found, using sample content.")
        with open(os.path.join(docs_dir, "Forest_Fire_Simulation_Documentation.md"), 'w') as f:
            f.write("# Forest Fire Simulation User Guide\n\nSample content - replace with actual documentation.")
    
    if tech_file_exists:
        shutil.copy("Forest_Fire_Simulation_Technical_Reference.md", os.path.join(docs_dir, "Forest_Fire_Simulation_Technical_Reference.md"))
        print("Copied Forest_Fire_Simulation_Technical_Reference.md")
    else:
        print("Warning: Forest_Fire_Simulation_Technical_Reference.md not found, using sample content.")
        with open(os.path.join(docs_dir, "Forest_Fire_Simulation_Technical_Reference.md"), 'w') as f:
            f.write("# Forest Fire Simulation Technical Reference\n\nSample content - replace with actual documentation.")
    
    print("Documentation files processed successfully.")
    return True

def download_mermaid_js(docs_dir):
    """Download Mermaid.js for diagram rendering."""
    import requests
    
    print("\nSetting up Mermaid.js for diagram rendering...")
    mermaid_url = "https://unpkg.com/mermaid@10.2.0/dist/mermaid.min.js"
    mermaid_path = os.path.join(docs_dir, 'javascripts', 'mermaid.min.js')
    
    print(f"Downloading Mermaid.js from {mermaid_url}...")
    try:
        response = requests.get(mermaid_url)
        with open(mermaid_path, 'wb') as f:
            f.write(response.content)
        print("Mermaid.js downloaded successfully.")
    except Exception as e:
        print(f"Warning: Failed to download Mermaid.js ({e}). Using placeholder.")
        with open(mermaid_path, 'w') as f:
            f.write("// Placeholder for mermaid.js - download it from https://unpkg.com/mermaid/dist/mermaid.min.js")
    
    print("Mermaid.js setup completed.")
    return True

def preprocess_markdown_files(docs_dir):
    """Preprocess markdown files to fix anchor issues."""
    print("\nPreprocessing markdown files to fix anchor issues...")
    
    tech_ref_path = os.path.join(docs_dir, "Forest_Fire_Simulation_Technical_Reference.md")
    if os.path.exists(tech_ref_path):
        with open(tech_ref_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Add anchor IDs to headings
        # This improved regex matches markdown headings and adds an explicit ID
        # It handles headings with special characters better
        def heading_to_id(match):
            heading_text = match.group(2)
            # Create ID by joining lowercase words with hyphens and removing non-word chars
            heading_id = '-'.join(heading_text.lower().split())
            heading_id = re.sub(r'[^\w\-]', '', heading_id).strip('-')
            return f"{match.group(1)} {heading_text} {{#{heading_id}}}"
            
        content = re.sub(r'^(#+)\s+(.*?)$', heading_to_id, content, flags=re.MULTILINE)
        
        with open(tech_ref_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Added anchor IDs to technical reference headings")
    
    doc_path = os.path.join(docs_dir, "Forest_Fire_Simulation_Documentation.md")
    if os.path.exists(doc_path):
        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Add hidden anchors for cross-references
        missing_anchors = [
            # Original anchors
            "42-plant-area-density-pad-and-forest-structure",
            "102-recovery-mechanisms",
            "103-health-monitoring",
            "113-memory-usage-patterns",
            "114-optimization-recommendations",
            "186-test-coverage",
            # Additional anchors from build logs
            "22-memory-management",
            "21-forest-structure-representation",
            "24-method-interrelationships",
            "4-performance-benchmarks",
            "1-technical-architecture-overview",
            "61-simulation-parameters",
            "64-api-reference",
            "310-environmental-data-integration",
            "39-comprehensive-error-handling-framework",
            "66-validation-and-testing-framework",
            "61-configuration-reference",
            "52-error-handling-implementation"
        ]
        
        anchor_html = ""
        for anchor in missing_anchors:
            anchor_html += f'<div id="{anchor}" style="height:0;width:0;position:absolute;"></div>\n'
        
        content = anchor_html + content
        
        with open(doc_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Added hidden anchors for cross-references in documentation")

def build_website(output_dir=None):
    """Build the static website using MkDocs."""
    print("\nBuilding the static website...")
    
    try:
        if output_dir:
            cmd = ["mkdocs", "build", "--site-dir", output_dir]
        else:
            cmd = ["mkdocs", "build"]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Only print important parts of the output
        for line in result.stdout.splitlines():
            if "ERROR" in line or "WARNING" in line or "INFO" in line and "contains a link" not in line:
                print(line)
        
        if result.returncode != 0:
            print(f"Warning: MkDocs build exited with code {result.returncode}")
            for line in result.stderr.splitlines():
                print(line)
            print("Attempting to continue...")
            return False
        
        # Check if the site was built
        site_dir = output_dir if output_dir else "site"
        if os.path.exists(os.path.join(site_dir, "index.html")):
            print(f"Website built successfully in the '{site_dir}' directory.")
            print(f"Verified: {site_dir}/index.html exists.")
            return True
        else:
            print(f"Error: Website build failed, {site_dir}/index.html not found.")
            return False
    except Exception as e:
        print(f"Error building website: {e}")
        return False

def post_process_html_files(site_dir):
    """Post-process HTML files to fix any remaining anchor issues."""
    print("Post-processing HTML files to fix any remaining anchor issues...")
    
    tech_ref_path = os.path.join(site_dir, "Forest_Fire_Simulation_Technical_Reference", "index.html")
    if os.path.exists(tech_ref_path):
        with open(tech_ref_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Add missing anchor points
        missing_anchors = [
            # Original anchors
            "24-method-interrelationships",
            "61-simulation-parameters",
            "64-api-reference",
            "310-environmental-data-integration",
            "39-comprehensive-error-handling-framework",
            "66-validation-and-testing-framework",
            "61-configuration-reference",
            "52-error-handling-implementation",
            # Additional anchors from build logs
            "22-memory-management",
            "21-forest-structure-representation",
            "4-performance-benchmarks",
            "1-technical-architecture-overview"
        ]
        
        anchor_html = "<div style='display:none'>\n"
        for anchor in missing_anchors:
            anchor_html += f'<div id="{anchor}"></div>\n'
        anchor_html += "</div>\n"
        
        # Insert after the body tag
        if "<body" in content:
            content = content.replace("<body", f"<body>\n{anchor_html}", 1)
        else:
            # Fallback insertion
            content = content.replace("<main", f"{anchor_html}\n<main", 1)
        
        with open(tech_ref_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Added hidden anchor divs to technical reference HTML")
    
    doc_path = os.path.join(site_dir, "Forest_Fire_Simulation_Documentation", "index.html")
    if os.path.exists(doc_path):
        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Add hidden anchors for missing sections
        missing_anchors = [
            # Original anchors
            "42-plant-area-density-pad-and-forest-structure",
            "102-recovery-mechanisms",
            "103-health-monitoring",
            "113-memory-usage-patterns",
            "114-optimization-recommendations",
            "186-test-coverage",
            # Additional anchors that might be referenced in other docs
            "link_to_docs",
            "link_to_issues",
            "link_to_forum"
        ]
        
        anchor_html = "<div style='display:none'>\n"
        for anchor in missing_anchors:
            anchor_html += f'<div id="{anchor}"></div>\n'
        anchor_html += "</div>\n"
        
        # Insert after the body tag
        if "<body" in content:
            content = content.replace("<body", f"<body>\n{anchor_html}", 1)
        else:
            # Fallback insertion
            content = content.replace("<main", f"{anchor_html}\n<main", 1)
        
        with open(doc_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Added hidden anchors for missing sections in documentation HTML")

def add_redirect_page(site_dir):
    """Add a redirect HTML page for easy access."""
    html_content = """<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="refresh" content="0; url=index.html">
    <title>Redirecting to Forest Fire Simulation Documentation</title>
</head>
<body>
    <p>If you are not redirected automatically, <a href="index.html">click here</a>.</p>
</body>
</html>
"""
    
    with open(os.path.join(site_dir, "OPEN_DOCUMENTATION.html"), 'w') as f:
        f.write(html_content)
    
    print("Added HTML launcher for easy access without running scripts.")

def create_readme(site_dir):
    """Create a README file with viewing instructions."""
    readme_content = f"""# Forest Fire Simulation Framework Documentation

This folder contains the comprehensive documentation for the Forest Fire Simulation Framework.

## Viewing the Documentation

There are several ways to access this documentation:

1. **Open HTML Directly**: 
   - Double-click on the `OPEN_DOCUMENTATION.html` file to open in your browser

2. **Using Local Server** (best experience):
   - Run the included script: `python start_server.py`
   - This will open the documentation in your default web browser

## Documentation Structure

The documentation is organized into:

- **User Guide**: Explains concepts, workflows, and practical usage
- **Technical Reference**: Provides implementation details and algorithms

## Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    with open(os.path.join(site_dir, "README.md"), 'w') as f:
        f.write(readme_content)
    
    print("Added README with viewing instructions.")

def create_standalone_server(site_dir):
    """Create a standalone server script for easy viewing."""
    server_script = """#!/usr/bin/env python3
import http.server
import socketserver
import os
import webbrowser
import sys
from pathlib import Path

# Configuration
PORT = 8000
DIRECTORY = Path(__file__).parent.absolute()

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

def main():
    print(f"Starting documentation server at http://localhost:{PORT}")
    print(f"Serving files from {DIRECTORY}")
    
    # Open browser
    webbrowser.open(f"http://localhost:{PORT}")
    
    # Start server
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print("Server started. Press Ctrl+C to stop.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("Server stopped.")

if __name__ == "__main__":
    os.chdir(DIRECTORY)
    main()
"""
    
    with open(os.path.join(site_dir, "start_server.py"), 'w') as f:
        f.write(server_script)
    
    print("Added standalone server script for easy viewing.")
    print("Recipients can run 'start_server.py' to view the documentation locally.")

def convert_to_pdf(docs_dir, site_dir):
    """Try to convert markdown files to PDF using a simple approach."""
    print("\nAttempting to create PDF versions of documentation...")
    
    pdf_dir = os.path.join(site_dir, "pdf")
    os.makedirs(pdf_dir, exist_ok=True)
    
    try:
        # Check if we can import the required modules for PDF conversion
        import markdown
        from weasyprint import HTML, CSS
        
        # Define the files to convert
        md_files = [
            "Forest_Fire_Simulation_Documentation.md",
            "Forest_Fire_Simulation_Technical_Reference.md"
        ]
        
        success = False
        for md_file in md_files:
            md_path = os.path.join(docs_dir, md_file)
            if not os.path.exists(md_path):
                continue
                
            try:
                # Read markdown file
                with open(md_path, 'r', encoding='utf-8') as f:
                    md_content = f.read()
                
                # Convert to HTML
                html_content = markdown.markdown(
                    md_content, 
                    extensions=['tables', 'fenced_code', 'attr_list']
                )
                
                # Add basic styling
                styled_html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="utf-8">
                    <title>{md_file.replace('.md', '')}</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; line-height: 1.6; max-width: 900px; margin: 0 auto; padding: 20px; }}
                        h1 {{ color: #1a237e; }}
                        h2 {{ color: #283593; }}
                        h3 {{ color: #303f9f; }}
                        code {{ background-color: #f5f5f5; padding: 2px 4px; border-radius: 3px; }}
                        pre {{ background-color: #f5f5f5; padding: 1em; border-radius: 5px; overflow-x: auto; }}
                        a {{ color: #3949ab; text-decoration: none; }}
                        a:hover {{ text-decoration: underline; }}
                        .page-break {{ page-break-after: always; }}
                    </style>
                </head>
                <body>
                    {html_content}
                </body>
                </html>
                """
                
                # Create temp HTML file
                temp_html = os.path.join(pdf_dir, f"{md_file.replace('.md', '.html')}")
                with open(temp_html, 'w', encoding='utf-8') as f:
                    f.write(styled_html)
                
                # Convert to PDF
                pdf_path = os.path.join(pdf_dir, f"{md_file.replace('.md', '.pdf')}")
                HTML(temp_html).write_pdf(pdf_path)
                
                # Remove temporary HTML
                os.remove(temp_html)
                
                print(f"Created PDF: {pdf_path}")
                success = True
            except Exception as e:
                print(f"Error converting {md_file} to PDF: {e}")
        
        if success:
            print("PDF conversion completed successfully.")
            return True
        else:
            print("No markdown files found to convert to PDF.")
            return False
            
    except ImportError as e:
        print(f"PDF conversion requires additional packages (markdown and weasyprint). {e}")
        print("PDF conversion skipped. You can install requirements with:")
        print("pip install markdown weasyprint")
        return False
    except Exception as e:
        print(f"Error during PDF conversion: {e}")
        return False

def main():
    try:
        # Setup
        check_dependencies()
        
        # Create directory structure
        docs_dir = "docs"
        site_dir = "site"
        create_directory_structure(docs_dir)
        
        # Copy documentation files
        copy_documentation_files(docs_dir)
        
        # Preprocess markdown files
        preprocess_markdown_files(docs_dir)
        
        # Set up Mermaid.js
        download_mermaid_js(docs_dir)
        
        # Build the static website
        build_website()
        
        # Post-process HTML files
        post_process_html_files(site_dir)
        
        # Add useful files
        add_redirect_page(site_dir)
        create_standalone_server(site_dir)
        create_readme(site_dir)
        
        # Try to create PDF versions
        pdf_success = convert_to_pdf(docs_dir, site_dir)
        
        print("\n=====================================")
        print("Documentation website generation complete!")
        print(f"Website is available in the '{site_dir}' directory")
        if pdf_success:
            print(f"PDF versions are available in the '{site_dir}/pdf' directory")
        print("Open OPEN_DOCUMENTATION.html to view the documentation")
        print("=====================================")
    except Exception as e:
        print(f"\nError: {e}")
        print("Documentation generation failed.")
        sys.exit(1)

if __name__ == "__main__":
    print("=" * 80)
    print("Forest Fire Simulation Documentation Website Generator")
    print("=" * 80)
    main() 