#!/usr/bin/env python3
import re

# Read the original file
with open('create_docs_website.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the create_standalone_version function
start_pattern = r'def create_standalone_version\(site_dir\):'
end_pattern = r'def create_pdf_index_page\(site_dir, pdf_files\):'

# Extract the problematic section
problematic_section = re.search(
    f'{start_pattern}.*?{end_pattern}', 
    content, 
    re.DOTALL
).group(0)

# Create the corrected section
corrected_section = '''def create_standalone_version(site_dir):
    """Create a standalone version of the website with a Python HTTP server script."""
    server_script = """#!/usr/bin/env python3
"""
    server_script += \'\'\'
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
        print("\\nServer stopped")

if __name__ == "__main__":
    main()
\'\'\'

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

def create_pdf_index_page(site_dir, pdf_files):'''

# Replace the problematic section with the corrected version
fixed_content = content.replace(problematic_section, corrected_section)

# Write the fixed content to a new file
with open('create_docs_website_fixed.py', 'w', encoding='utf-8') as f:
    f.write(fixed_content)

print("Fixed file created as create_docs_website_fixed.py")
print("Check if the file is correct, then rename it to create_docs_website.py to use it") 