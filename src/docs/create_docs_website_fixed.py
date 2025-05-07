#!/usr/bin/env python3
"""
Forest Fire Simulation Documentation Website Generator

This script converts the Forest Fire Simulation documentation into a static website
with preserved cross-document links, support for Mermaid diagrams, and a responsive design.

Requirements:
- Python 3.6+
- pip (Python package manager)

Features:
- Preserves all cross-document links
- Supports Mermaid diagrams
- Creates a responsive, searchable website
- Optional local server for testing
- Optional GitHub Pages deployment
- Export to ZIP for easy sharing
- PDF export option for easy distribution

Usage:
    python create_docs_website.py [options]

Options:
    --serve       Start a local server to preview the site
    --deploy      Deploy to GitHub Pages (if in a git repository)
    --output=DIR  Set custom output directory (default: ./site)
    --zip         Create a ZIP archive of the website for sharing
    --pdf         Generate PDF versions of the documentation
    --single-html Create a single HTML file with all documentation
    --help        Show this help message
"""

import os
import sys
import shutil
import subprocess
import argparse
import zipfile
import webbrowser
from pathlib import Path
from datetime import datetime
import re

# Configuration
MKDOCS_CONFIG = """
site_name: Forest Fire Simulation Framework
site_description: Documentation for the Forest Fire Simulation Framework
site_author: Your Name
repo_url: https://github.com/yourusername/forest-fire-simulation
edit_uri: edit/main/docs/

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
      toggle:
        icon: material/toggle-switch-off-outline
        name: Switch to dark mode
    - scheme: slate
      primary: indigo
      accent: indigo
      toggle:
        icon: material/toggle-switch
        name: Switch to light mode

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

CSS_EXTRA = """
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

HOME_PAGE = """
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

## Quick Start

```python
from forest_fire_framework import create_config, run_simulation

# Create basic configuration
config = create_config(
    model_resolution=5.0,
    area_size=(1000, 1000),
    num_layers=10
)

# Run simulation
results = run_simulation(
    pad_data="path/to/forest_data",
    config=config
)
```

## Key Features

- **3D Modeling**: Incorporates vertical forest structure through LiDAR-derived data
- **Memory Optimization**: Handles large-scale simulations through innovative memory management
- **Scientific Models**: Implements established fire spread models based on current research
- **Planning Applications**: Supports forest management and fire planning scenarios

## About the Project

This framework was developed to address the unique challenges of forest fire simulation in the Canary Islands, where:

- **Complex Topography**: Steep volcanic terrain with ravines and cliffs creates unique fire behavior patterns
- **Diverse Microclimates**: Elevation gradients create varied weather conditions within short distances
- **Endemic Forest Ecosystems**: Specialized forests exhibit fire adaptations different from continental species
- **Limited Resources**: The islands face computational resource constraints when implementing large-scale simulations
"""

# Add these sample files for when the actual docs aren't present
SAMPLE_USER_GUIDE = """
# Forest Fire Simulation User Guide

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
"""

SAMPLE_TECH_REF = """
# Forest Fire Simulation Technical Reference

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
"""

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
        "mkdocs",
        "mkdocs-material",
        "pymdown-extensions",
        "mkdocs-minify-plugin",
        "requests"  # Add requests for downloading mermaid.js
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

def create_directory_structure(docs_dir):
    """Create the directory structure for the documentation."""
    print(f"Creating directory structure in {docs_dir}...")
    
    # Create necessary directories
    os.makedirs(os.path.join(docs_dir, "stylesheets"), exist_ok=True)
    os.makedirs(os.path.join(docs_dir, "javascripts"), exist_ok=True)
    
    # Create the mkdocs.yml configuration file
    with open("mkdocs.yml", "w", encoding="utf-8") as f:
        f.write(MKDOCS_CONFIG)
    
    # Create custom CSS
    with open(os.path.join(docs_dir, "stylesheets", "extra.css"), "w", encoding="utf-8") as f:
        f.write(CSS_EXTRA)
    
    # Create index.md (home page)
    with open(os.path.join(docs_dir, "index.md"), "w", encoding="utf-8") as f:
        f.write(HOME_PAGE)
    
    print("Directory structure created successfully.\n")

def copy_documentation_files(docs_dir):
    """Copy the documentation files to the docs directory."""
    print("Copying documentation files...")
    
    # List of documentation files to include
    doc_files = [
        "Forest_Fire_Simulation_Documentation.md",
        "Forest_Fire_Simulation_Technical_Reference.md"
    ]
    
    files_found = False
    
    for file in doc_files:
        if os.path.exists(file):
            shutil.copy2(file, os.path.join(docs_dir, file))
            print(f"Copied {file}")
            files_found = True
        else:
            print(f"Warning: {file} not found in the current directory. Creating a sample file.")
            
            # Create sample files if actual docs aren't found
            if file == "Forest_Fire_Simulation_Documentation.md":
                with open(os.path.join(docs_dir, file), "w", encoding="utf-8") as f:
                    f.write(SAMPLE_USER_GUIDE)
            elif file == "Forest_Fire_Simulation_Technical_Reference.md":
                with open(os.path.join(docs_dir, file), "w", encoding="utf-8") as f:
                    f.write(SAMPLE_TECH_REF)
            
            print(f"Created sample {file}")
    
    if not files_found:
        print("Note: No actual documentation files were found. Sample files were created.")
        print("Please replace them with your actual documentation files.")
    
    print("Documentation files processed successfully.\n")
    
    return doc_files

def download_mermaid_js(docs_dir):
    """Download the Mermaid.js library for diagram rendering."""
    print("Setting up Mermaid.js for diagram rendering...")
    
    mermaid_js_path = os.path.join(docs_dir, "javascripts", "mermaid.min.js")
    
    try:
        import requests
        
        mermaid_url = "https://unpkg.com/mermaid@10.2.0/dist/mermaid.min.js"
        print(f"Downloading Mermaid.js from {mermaid_url}...")
        
        try:
            response = requests.get(mermaid_url, timeout=10)
            
            if response.status_code == 200:
                with open(mermaid_js_path, "wb") as f:
                    f.write(response.content)
                print("Mermaid.js downloaded successfully.")
            else:
                raise Exception(f"HTTP status code: {response.status_code}")
                
        except Exception as e:
            print(f"Warning: Failed to download Mermaid.js. Error: {str(e)}")
            print("Using alternative approach...")
            
            # Create a basic initialization script as fallback
            with open(mermaid_js_path, "w", encoding="utf-8") as f:
                f.write('// Mermaid initialization\ndocument.addEventListener("DOMContentLoaded", function() {\n  if (typeof mermaid !== "undefined") {\n    mermaid.initialize({ startOnLoad: true });\n  }\n});')
            print("Created basic Mermaid initialization script.")
    
    except ImportError:
        print("Warning: requests library not available.")
        # Create a basic initialization script as fallback
        with open(mermaid_js_path, "w", encoding="utf-8") as f:
            f.write('// Mermaid initialization\ndocument.addEventListener("DOMContentLoaded", function() {\n  if (typeof mermaid !== "undefined") {\n    mermaid.initialize({ startOnLoad: true });\n  }\n});')
        print("Created basic Mermaid initialization script.")
    
    print("Mermaid.js setup completed.\n")

def build_website(output_dir):
    """Build the static website using MkDocs."""
    print("Building the static website...")
    
    # Build the website
    build_cmd = ["mkdocs", "build", "--clean"]
    if output_dir:
        build_cmd.extend(["--site-dir", output_dir])
    
    try:
        subprocess.check_call(build_cmd)
        site_dir = output_dir if output_dir else "site"
        print(f"\nWebsite built successfully in the '{site_dir}' directory.")
        
        # Verify the build
        index_path = os.path.join(site_dir, "index.html")
        if os.path.exists(index_path):
            print(f"Verified: {index_path} exists.")
            return True
        else:
            print(f"Error: {index_path} was not created.")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"Error: Failed to build the website. Error code: {e.returncode}")
        print("Detailed error information:")
        try:
            # Try with verbose output for more information
            subprocess.check_call(build_cmd + ["--verbose"], stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e2:
            print(f"Additional error details: {e2}")
        return False
    
    return True

def serve_website():
    """Serve the website locally for preview."""
    print("\nStarting local server for preview...")
    print("The website will be available at http://127.0.0.1:8000/")
    print("Press Ctrl+C to stop the server.")
    
    try:
        subprocess.check_call(["mkdocs", "serve", "--livereload"])
    except subprocess.CalledProcessError as e:
        print(f"Error: Failed to start the local server. Error code: {e.returncode}")
        try:
            # Try with verbose output for more information
            subprocess.check_call(["mkdocs", "serve", "--verbose"], stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e2:
            print(f"Additional error details: {e2}")
        return False
    except KeyboardInterrupt:
        print("\nLocal server stopped.")
    
    return True

def deploy_to_github_pages():
    """Deploy the website to GitHub Pages."""
    print("\nDeploying to GitHub Pages...")
    
    try:
        # Check if in a git repository
        subprocess.check_call(["git", "rev-parse", "--is-inside-work-tree"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Deploy using mkdocs
        subprocess.check_call(["mkdocs", "gh-deploy", "--force"])
        print("Deployment to GitHub Pages completed successfully.")
        
        # Try to get the GitHub Pages URL
        try:
            repo_url = subprocess.check_output(["git", "config", "--get", "remote.origin.url"]).decode().strip()
            if repo_url.endswith(".git"):
                repo_url = repo_url[:-4]
            if "github.com" in repo_url:
                if repo_url.startswith("git@github.com:"):
                    user_repo = repo_url.split("git@github.com:")[1]
                elif repo_url.startswith("https://github.com/"):
                    user_repo = repo_url.split("https://github.com/")[1]
                else:
                    user_repo = None
                
                if user_repo:
                    user, repo = user_repo.split("/")
                    pages_url = f"https://{user}.github.io/{repo}/"
                    print(f"Your website should be available at: {pages_url}")
            
        except subprocess.CalledProcessError:
            print("Could not determine GitHub Pages URL.")
            print("Check your GitHub repository settings to find the URL.")
        
        return True
        
    except subprocess.CalledProcessError:
        print("Error: Not in a git repository or git is not installed.")
        print("To deploy to GitHub Pages, run this script from a git repository.")
        return False

def create_zip_archive(site_dir):
    """Create a ZIP archive of the website for easy sharing."""
    print("\nCreating ZIP archive for sharing...")
    
    try:
        if not os.path.exists(site_dir):
            print(f"Error: Site directory '{site_dir}' not found.")
            return False
        
        # Generate a filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"forest_fire_docs_{timestamp}.zip"
        
        # Create the ZIP file
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(site_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    # Calculate the relative path to preserve directory structure
                    rel_path = os.path.relpath(file_path, site_dir)
                    zipf.write(file_path, rel_path)
        
        zip_full_path = os.path.abspath(zip_filename)
        print(f"ZIP archive created successfully: {zip_full_path}")
        print("\nTo share the documentation:")
        print(f"1. Send the ZIP file '{zip_filename}' to others")
        print("2. Recipients should extract the ZIP file")
        print("3. They can view the website by opening 'index.html' in a web browser")
        
        return True
    
    except Exception as e:
        print(f"Error creating ZIP archive: {str(e)}")
        return False

def add_redirect_page(site_dir):
    """Add an HTML redirect page to ensure proper navigation."""
    redirect_html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="0; url=index.html">
    <title>Redirecting...</title>
    <script>
        window.location.href = "index.html";
    </script>
</head>
<body>
    <p>If you are not redirected automatically, <a href="index.html">click here</a>.</p>
</body>
</html>
"""
    try:
        with open(os.path.join(site_dir, "redirect.html"), "w", encoding="utf-8") as f:
            f.write(redirect_html)
            
        # Also create at root level for GitHub Pages
        with open("redirect.html", "w", encoding="utf-8") as f:
            f.write(redirect_html)
            
        print("Added redirect pages for better navigation.")
        return True
    except Exception as e:
        print(f"Error adding redirect page: {str(e)}")
        return False

def create_standalone_version(site_dir):
    """Create a standalone version of the website with a Python HTTP server script."""
    server_script = """#!/usr/bin/env python3
"""
    server_script += '''
"""
Forest Fire Simulation Documentation Server

This script starts a simple HTTP server to view the documentation.
Just run this script and open http://localhost:8080 in your browser.

Press Ctrl+C to stop the server.
"""

import os
import sys
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler

PORT = 8080

class DocServer(SimpleHTTPRequestHandler):
    """Simple HTTP server with custom headers."""
    
    def end_headers(self):
        # Add CORS headers for local testing
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

def main():
    """Start the server and open the browser."""
    # Change to the directory containing the script
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    print(f"Starting documentation server at http://localhost:{PORT}")
    print("Press Ctrl+C to stop the server")
    
    # Open browser
    webbrowser.open(f"http://localhost:{PORT}")
    
    # Start server
    server = HTTPServer(('', PORT), DocServer)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped")

if __name__ == "__main__":
    main()
'''

    try:
        with open(os.path.join(site_dir, "start_server.py"), "w", encoding="utf-8") as f:
            f.write(server_script)
        
        # Make the script executable on Unix-like systems
        if os.name != 'nt':  # not Windows
            try:
                os.chmod(os.path.join(site_dir, "start_server.py"), 0o755)
            except:
                pass
                
        print("Added standalone server script for easy viewing.")
        print("Recipients can run 'start_server.py' to view the documentation locally.")
        
        # Create a simple HTML launcher that doesn't require Python
        html_launcher = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Documentation Launcher</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            text-align: center;
        }
        .button {
            display: inline-block;
            background-color: #4CAF50;
            color: white;
            padding: 15px 25px;
            text-decoration: none;
            border-radius: 4px;
            font-weight: bold;
            margin: 20px;
            font-size: 18px;
        }
        .button:hover {
            background-color: #45a049;
        }
        .note {
            margin-top: 40px;
            padding: 15px;
            background-color: #f8f9fa;
            border-radius: 5px;
            text-align: left;
        }
    </style>
</head>
<body>
    <h1>Forest Fire Simulation Documentation</h1>
    <p>Click the button below to open the documentation:</p>
    
    <a href="index.html" class="button">Open Documentation</a>
    
    <div class="note">
        <h3>Note:</h3>
        <p>This documentation is designed to be viewed in a web browser. Simply click the button above to open it.</p>
        <p>If you encounter any issues with links not working properly:</p>
        <ul>
            <li>Try using a different web browser</li>
            <li>Use the search function within the documentation to find content</li>
            <li>Contact the administrator for assistance</li>
        </ul>
    </div>
</body>
</html>"""
        
        with open(os.path.join(site_dir, "OPEN_DOCUMENTATION.html"), "w", encoding="utf-8") as f:
            f.write(html_launcher)
            
        print("Added HTML launcher for easy access without running scripts.")
        return True
    except Exception as e:
        print(f"Error creating standalone version: {str(e)}")
        return False

def create_pdf_index_page(site_dir, pdf_files):
    """Create an HTML page listing the available PDFs."""
    if not pdf_files:
        return
    
    html_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Forest Fire Simulation Documentation - PDF Downloads</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        h1 {
            color: #333;
            border-bottom: 1px solid #ddd;
            padding-bottom: 10px;
        }
        .pdf-list {
            margin: 20px 0;
        }
        .pdf-item {
            margin-bottom: 15px;
            padding: 15px;
            background-color: #f5f5f5;
            border-radius: 5px;
        }
        .pdf-item h3 {
            margin-top: 0;
        }
        .download-btn {
            display: inline-block;
            background-color: #4CAF50;
            color: white;
            padding: 10px 15px;
            text-decoration: none;
            border-radius: 4px;
            font-weight: bold;
        }
        .download-btn:hover {
            background-color: #45a049;
        }
        .back-link {
            margin-top: 30px;
        }
    </style>
</head>
<body>
    <h1>Forest Fire Simulation Documentation - PDF Downloads</h1>
    <p>The following PDF versions of the documentation are available for download:</p>
    
    <div class="pdf-list">
"""
    
    # Add each PDF file to the list
    for pdf_file in pdf_files:
        name = os.path.splitext(pdf_file)[0].replace("_", " ")
        
        html_content += f"""
        <div class="pdf-item">
            <h3>{name}</h3>
            <a href="{pdf_file}" class="download-btn" download>Download PDF</a>
        </div>
"""
    
    html_content += """
    </div>
    
    <div class="back-link">
        <a href="index.html">← Back to Documentation Home</a>
    </div>
</body>
</html>
"""
    
    # Write the HTML file
    with open(os.path.join(site_dir, "pdf_downloads.html"), "w", encoding="utf-8") as f:
        f.write(html_content)
    
    # Update the main index.html to include a link to the PDF downloads
    index_path = os.path.join(site_dir, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Add a link to the PDF downloads page before the closing body tag
        pdf_link = """
<div style="text-align: center; margin-top: 30px; padding: 15px; background-color: #f8f9fa; border-radius: 5px;">
    <p><strong>Need offline access?</strong> <a href="pdf_downloads.html">Download PDF versions of the documentation</a></p>
</div>
</body>
"""
        content = content.replace("</body>", pdf_link)
        
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(content)
    
    return True

def create_readme(site_dir):
    """Create a README file with instructions."""
    readme_content = """# Forest Fire Simulation Documentation

## Viewing the Documentation

There are several ways to view this documentation:

### Option 1: Quickest Method (Recommended)
1. Open the `OPEN_DOCUMENTATION.html` file in any web browser
2. Click the button to view the documentation

### Option 2: Direct Access
1. Open the `index.html` file in a web browser

### Option 3: Using the included server script
If links don't work properly with direct file access, you can use the included server:
1. Run the `start_server.py` script (requires Python)
2. A browser window should open automatically to http://localhost:8080
3. If it doesn't open automatically, manually open http://localhost:8080 in your browser
4. Press Ctrl+C in the terminal/command prompt to stop the server when done

## Navigation
- Use the navigation menu on the left to browse different sections
- Use the search bar at the top to find specific content

## Offline Access
- PDF versions of the documentation are included for offline reading
- Find them in the PDFs folder or access via the "PDF Downloads" link in the documentation

## Issues
If you encounter any issues with this documentation, please contact the administrator.
"""

    try:
        with open(os.path.join(site_dir, "README.md"), "w", encoding="utf-8") as f:
            f.write(readme_content)
        print("Added README with viewing instructions.")
        return True
    except Exception as e:
        print(f"Error creating README: {str(e)}")
        return False

def create_single_html_doc(site_dir, doc_files):
    """Create a single HTML file that contains all documentation."""
    print("\nCreating single-file HTML version...")
    
    try:
        import markdown
        from bs4 import BeautifulSoup
        
        combined_markdown = """# Forest Fire Simulation Framework - Complete Documentation

This file contains the complete documentation for the Forest Fire Simulation Framework.

## Table of Contents

"""
        # Generate table of contents
        for i, doc_file in enumerate(doc_files):
            doc_name = os.path.splitext(os.path.basename(doc_file))[0].replace("_", " ")
            combined_markdown += f"{i+1}. [{doc_name}](#{doc_name.lower().replace(' ', '-')})\n"
        
        combined_markdown += "\n---\n\n"
        
        # Add each document
        for doc_file in doc_files:
            doc_path = os.path.join("docs", doc_file)
            if os.path.exists(doc_path):
                doc_name = os.path.splitext(os.path.basename(doc_file))[0].replace("_", " ")
                combined_markdown += f"# {doc_name}\n\n"
                
                with open(doc_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Remove the first title if it exists to avoid duplication
                    if content.startswith('# '):
                        content = content[content.find('\n')+1:].strip()
                    combined_markdown += content + "\n\n---\n\n"
        
        # Convert to HTML
        html_content = markdown.markdown(combined_markdown, extensions=['tables', 'fenced_code'])
        
        # Add styling
        styled_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Forest Fire Simulation - Complete Documentation</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.6;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
        }}
        h1, h2, h3, h4 {{
            color: #1a237e;
            margin-top: 1.5em;
        }}
        h1 {{
            border-bottom: 2px solid #1a237e;
            padding-bottom: 10px;
        }}
        h2 {{
            border-bottom: 1px solid #ddd;
            padding-bottom: 5px;
        }}
        code {{
            background-color: #f5f5f5;
            padding: 2px 4px;
            border-radius: 3px;
            font-family: Consolas, Monaco, 'Andale Mono', monospace;
        }}
        pre {{
            background-color: #f5f5f5;
            padding: 16px;
            border-radius: 5px;
            overflow-x: auto;
        }}
        pre code {{
            background-color: transparent;
            padding: 0;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 8px 12px;
            text-align: left;
        }}
        th {{
            background-color: #f2f2f2;
        }}
        img {{
            max-width: 100%;
            height: auto;
        }}
        a {{
            color: #3949ab;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        hr {{
            border: none;
            border-top: 1px solid #eee;
            margin: 40px 0;
        }}
        .back-to-top {{
            position: fixed;
            bottom: 20px;
            right: 20px;
            background-color: #3949ab;
            color: white;
            padding: 10px 15px;
            border-radius: 5px;
            text-decoration: none;
            opacity: 0.8;
        }}
        .back-to-top:hover {{
            opacity: 1;
        }}
    </style>
</head>
<body>
    {html_content}
    <a href="#" class="back-to-top">↑ Back to Top</a>
    <script>
        // Make external links open in new tabs
        document.querySelectorAll('a').forEach(link => {{
            if (link.hostname !== window.location.hostname && link.hostname !== '') {{
                link.target = '_blank';
                link.rel = 'noopener noreferrer';
            }}
        }});
    </script>
</body>
</html>"""

        output_file = os.path.join(site_dir, "complete_documentation.html")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(styled_html)
            
        print(f"Single-file HTML documentation created: {output_file}")
        
        # Add link to the index.html
        index_path = os.path.join(site_dir, "index.html")
        if os.path.exists(index_path):
            with open(index_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Add a link to the single HTML file before the closing body tag
            html_link = """
<div style="text-align: center; margin-top: 20px; padding: 15px; background-color: #e8eaf6; border-radius: 5px;">
    <p><strong>Want everything in one file?</strong> <a href="complete_documentation.html">View the complete documentation as a single HTML file</a></p>
</div>
</body>
"""
            content = content.replace("</body>", html_link)
            
            with open(index_path, "w", encoding="utf-8") as f:
                f.write(content)
                
        return True
        
    except ImportError:
        print("Could not create single HTML file - missing dependencies.")
        print("To enable this feature, install: pip install markdown beautifulsoup4")
        return False
    except Exception as e:
        print(f"Error creating single HTML file: {str(e)}")
        return False

def main():
    """Main function to control the script workflow."""
    parser = argparse.ArgumentParser(description="Generate a static website from Forest Fire Simulation documentation.")
    parser.add_argument("--serve", action="store_true", help="Start a local server to preview the site")
    parser.add_argument("--deploy", action="store_true", help="Deploy to GitHub Pages (if in a git repository)")
    parser.add_argument("--output", help="Set custom output directory (default: ./site)")
    parser.add_argument("--zip", action="store_true", help="Create a ZIP archive of the website for sharing")
    parser.add_argument("--pdf", action="store_true", help="Generate PDF versions of the documentation")
    parser.add_argument("--single-html", action="store_true", help="Create a single HTML file with all documentation")
    parser.add_argument("--help-custom", action="store_true", help="Show detailed help message")
    
    args = parser.parse_args()
    
    if args.help_custom:
        print(__doc__)
        return
    
    print("=" * 80)
    print("Forest Fire Simulation Documentation Website Generator")
    print("=" * 80)
    
    # Check dependencies
    if not check_dependencies():
        return
    
    # Install required packages
    if not install_requirements():
        print("Warning: Proceeding with potentially incomplete dependencies.")
    
    # Define the docs directory
    docs_dir = "docs"
    
    # Define the output/site directory
    site_dir = args.output if args.output else "site"
    
    # Create directory structure
    create_directory_structure(docs_dir)
    
    # Copy documentation files
    doc_files = copy_documentation_files(docs_dir)
    
    # Preprocess markdown files to fix anchor issues
    preprocess_markdown_files(docs_dir)
    
    # Download Mermaid.js for diagram rendering
    download_mermaid_js(docs_dir)
    
    # Build the website
    if not build_website(args.output):
        print("Error: Website build failed. Please check the errors above.")
        return
    
    # Post-process HTML files to fix any remaining anchor issues
    post_process_html_files(site_dir)
    
    # Add redirect page
    add_redirect_page(site_dir)
    
    # Create standalone version with server script
    create_standalone_version(site_dir)
    
    # Create README
    create_readme(site_dir)
    
    # Generate PDF versions for offline viewing (always do this for better accessibility)
    pdf_success = convert_to_pdf(docs_dir, site_dir)
    
    # Create single HTML file version if requested or by default for better accessibility
    if args.single_html or True:  # Always create it for better accessibility
        create_single_html_doc(site_dir, doc_files)
    
    # Create ZIP archive if requested or by default for easy sharing
    if args.zip or True:  # Always create it for easier sharing
        if not create_zip_archive(site_dir):
            print("Error: Failed to create ZIP archive.")
    
    # Serve the website locally if requested
    if args.serve:
        if not serve_website():
            return
    
    # Deploy to GitHub Pages if requested
    if args.deploy:
        if not deploy_to_github_pages():
            return
    
    print("\nProcess completed successfully!")
    site_dir_abs = os.path.abspath(site_dir)
    print(f"You can find the generated website in: {site_dir_abs}")
    print("\nTo share the documentation with others:")
    print(f"1. Navigate to: {site_dir_abs}")
    print("2. Send the ZIP file to recipients - they can simply extract and open OPEN_DOCUMENTATION.html")
    
    # Open documentation in browser
    webbrowser.open(os.path.join(site_dir_abs, "OPEN_DOCUMENTATION.html"))

if __name__ == "__main__":
    main()