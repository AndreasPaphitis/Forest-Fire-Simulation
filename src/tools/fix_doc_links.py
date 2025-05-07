#!/usr/bin/env python3
"""
Fix Document Links

This script analyzes and fixes broken links between the Forest Fire Simulation 
Framework documentation files, with a focus on cross-document links and anchors.
"""

import os
import re
import sys
from datetime import datetime
import shutil

def extract_headings(file_path):
    """Extract all headings from a markdown file and their anchor IDs."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract all headings (level 1-6)
    heading_pattern = re.compile(r'^(#{1,6})\s+(.*?)(?:\s+\{#([^}]+)\})?\s*$', re.MULTILINE)
    headings = heading_pattern.findall(content)
    
    heading_map = {}
    for heading_level, text, custom_id in headings:
        # Create a GitHub/CommonMark style ID if no custom ID
        if not custom_id:
            anchor_id = text.lower()
            # Replace spaces with hyphens
            anchor_id = re.sub(r'\s+', '-', anchor_id)
            # Remove non-alphanumeric characters except hyphens and underscores
            anchor_id = re.sub(r'[^\w\-]', '', anchor_id)
            # Ensure ID starts with a letter or number
            if not anchor_id or not re.match(r'^[a-z0-9]', anchor_id):
                anchor_id = 'section-' + anchor_id
        else:
            anchor_id = custom_id
        
        heading_map[text] = {
            'level': len(heading_level),
            'id': anchor_id
        }
    
    return heading_map

def extract_section_numbers(file_path):
    """Extract section numbers from a markdown file with numbering."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Look for headings with section numbers like "2.3 Method Implementation"
    section_pattern = re.compile(r'^#{1,6}\s+(\d+\.\d+(?:\.\d+)?)\s+(.*?)(?:\s+\{#([^}]+)\})?\s*$', re.MULTILINE)
    sections = section_pattern.findall(content)
    
    section_map = {}
    for section_num, text, custom_id in sections:
        # Store the section number with the text
        section_map[section_num] = {
            'text': text,
            'id': custom_id if custom_id else text.lower().replace(' ', '-')
        }
    
    return section_map

def find_broken_links(source_file, target_file):
    """Find broken cross-document links."""
    with open(source_file, 'r', encoding='utf-8') as f:
        source_content = f.read()
    
    # Extract link patterns for the target file
    target_basename = os.path.basename(target_file)
    link_pattern = re.compile(r'\[(.+?)\]\((' + re.escape(target_basename) + r'#(.+?))\)', re.MULTILINE)
    
    # Find all links
    links = link_pattern.findall(source_content)
    
    # Get heading and section maps from target file
    target_headings = extract_headings(target_file)
    target_sections = extract_section_numbers(target_file)
    
    # Track broken links
    broken_links = []
    
    for link_text, full_link, anchor in links:
        # Check if the anchor exists directly in headings
        anchor_found = False
        
        for heading_text, data in target_headings.items():
            if data['id'] == anchor:
                anchor_found = True
                break
        
        # Check if the anchor is a section number (like #24-method-interrelationships)
        if not anchor_found:
            # Try to extract section number from anchor
            section_match = re.match(r'(\d+)\.(\d+)-', anchor)
            if section_match:
                section_num = f"{section_match.group(1)}.{section_match.group(2)}"
                if section_num in target_sections:
                    anchor_found = True
        
        if not anchor_found:
            broken_links.append({
                'text': link_text,
                'link': full_link,
                'anchor': anchor
            })
    
    return broken_links

def fix_broken_links(source_file, target_file, broken_links, target_sections):
    """Fix broken links in the source file."""
    if not broken_links:
        return 0
    
    with open(source_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Create a backup of the original file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f"{os.path.splitext(source_file)[0]}_backup_{timestamp}.md"
    with open(backup_file, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Created backup: {backup_file}")
    
    fixed_count = 0
    target_basename = os.path.basename(target_file)
    
    # Common anchor mappings - these are manually determined based on document analysis
    anchor_mappings = {
        # Method Interrelationships
        "24-method-interrelationships": "method-interrelationships",
        
        # API Reference
        "64-api-reference": "api-reference",
        
        # Environmental Data Integration
        "310-environmental-data-integration": "environmental-data-integration",
        
        # Error Handling Framework
        "39-comprehensive-error-handling-framework": "comprehensive-error-handling-framework",
        
        # Configuration Reference
        "61-configuration-reference": "simulation-parameters",
        "61-simulation-parameters": "simulation-parameters",
        
        # Error Handling Implementation
        "52-error-handling-implementation": "error-handling-implementation"
    }
    
    for link in broken_links:
        anchor = link['anchor']
        
        # Try to map the anchor to a valid one
        if anchor in anchor_mappings:
            new_anchor = anchor_mappings[anchor]
            print(f"  Mapping: {anchor} -> {new_anchor}")
            
            # Replace the broken link with the mapped anchor
            old_link = f"[{link['text']}]({target_basename}#{anchor})"
            new_link = f"[{link['text']}]({target_basename}#{new_anchor})"
            content = content.replace(old_link, new_link)
            fixed_count += 1
        else:
            # Check if the anchor starts with a section number
            section_match = re.match(r'(\d+)\.(\d+)-', anchor)
            if section_match:
                section_num = f"{section_match.group(1)}.{section_match.group(2)}"
                
                # Look for a matching section in the target document
                if section_num in target_sections:
                    new_anchor = target_sections[section_num]['id'].lower().replace(' ', '-')
                    print(f"  Found section match: {section_num} -> {new_anchor}")
                    
                    # Replace the broken link
                    old_link = f"[{link['text']}]({target_basename}#{anchor})"
                    new_link = f"[{link['text']}]({target_basename}#{new_anchor})"
                    content = content.replace(old_link, new_link)
                    fixed_count += 1
    
    # Write the updated content back to the file
    with open(source_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return fixed_count

def update_html_documentation_links():
    """Update links in HTML documentation files."""
    html_dir = "html_docs"
    updated_files = 0
    
    if not os.path.exists(html_dir):
        print(f"HTML docs directory {html_dir} not found.")
        return updated_files
    
    # List of files to check and update
    html_files = [
        os.path.join(html_dir, "Forest_Fire_Simulation_Documentation.html"),
        os.path.join(html_dir, "Forest_Fire_Simulation_Technical_Reference.html"),
        os.path.join(html_dir, "forest_fire_workflow_diagrams.html"),
        os.path.join(html_dir, "forest_fire_workflow_diagrams_static.html"),
        os.path.join(html_dir, "forest_fire_workflow_diagrams_static_fixed.html"),
        os.path.join(html_dir, "index.html")
    ]
    
    # Update each file if it exists
    for html_file in html_files:
        if os.path.exists(html_file):
            print(f"Updating links in {html_file}...")
            
            # Create a backup
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = f"{os.path.splitext(html_file)[0]}_backup_{timestamp}.html"
            shutil.copy2(html_file, backup_file)
            
            # Read the file
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Update known broken anchors
            anchor_mappings = {
                "#24-method-interrelationships": "#method-interrelationships",
                "#64-api-reference": "#api-reference",
                "#310-environmental-data-integration": "#environmental-data-integration",
                "#39-comprehensive-error-handling-framework": "#comprehensive-error-handling-framework",
                "#61-configuration-reference": "#simulation-parameters",
                "#61-simulation-parameters": "#simulation-parameters",
                "#52-error-handling-implementation": "#error-handling-implementation"
            }
            
            # Apply fixed anchors
            for old_anchor, new_anchor in anchor_mappings.items():
                if old_anchor in content:
                    content = content.replace(old_anchor, new_anchor)
                    print(f"  Fixed anchor: {old_anchor} -> {new_anchor}")
            
            # Fix unrecognized relative links (placeholder links)
            placeholder_link_fixes = {
                'link_to_docs': 'https://forestfire.domain.com/docs',
                'link_to_issues': 'https://forestfire.domain.com/issues',
                'link_to_forum': 'https://forestfire.domain.com/forum'
            }
            
            for old_link, new_link in placeholder_link_fixes.items():
                old_pattern = f'href="{old_link}"'
                new_pattern = f'href="{new_link}"'
                if old_pattern in content:
                    content = content.replace(old_pattern, new_pattern)
                    print(f"  Fixed placeholder link: {old_link} -> {new_link}")
            
            # Write the updated content
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            updated_files += 1
    
    return updated_files

def fix_workflow_diagram_links():
    """Fix links in the workflow diagrams HTML files."""
    html_dir = "html_docs"
    
    # Main workflow files
    workflow_files = [
        os.path.join(html_dir, "forest_fire_workflow_diagrams.html"),
        os.path.join(html_dir, "forest_fire_workflow_diagrams_static.html"),
        os.path.join(html_dir, "forest_fire_workflow_diagrams_static_fixed.html")
    ]
    
    fixed_count = 0
    
    for html_file in workflow_files:
        if os.path.exists(html_file):
            print(f"Updating links in {html_file}...")
            
            # Create a backup
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = f"{os.path.splitext(html_file)[0]}_backup_{timestamp}.html"
            shutil.copy2(html_file, backup_file)
            
            # Read the file
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Add links to main documentation files
            nav_links = """
<div class="navigation-links">
    <a href="index.html">Home</a> | 
    <a href="Forest_Fire_Simulation_Documentation.html">Documentation</a> | 
    <a href="Forest_Fire_Simulation_Technical_Reference.html">Technical Reference</a>
</div>
"""
            # Add before closing body tag if it doesn't exist already
            if '<div class="navigation-links">' not in content:
                content = content.replace('</body>', f'{nav_links}</body>')
                fixed_count += 1
            
            # Update standalone diagram links if needed
            standalone_dir = os.path.join(html_dir, "standalone_diagrams")
            
            if os.path.exists(standalone_dir) and "standalone_diagrams" not in content:
                standalone_link = """
<div class="standalone-diagrams-link">
    <p><a href="standalone_diagrams/index.html">View Individual Diagrams</a> - Useful for troubleshooting</p>
</div>
"""
                # Add after the heading
                if '<h1' in content:
                    content = content.replace('</h1>', '</h1>' + standalone_link)
                    fixed_count += 1
            
            # Write the updated content
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(content)
    
    return fixed_count

def main():
    # Define the files to check
    doc_file = "Forest_Fire_Simulation_Documentation.md"
    tech_ref_file = "Forest_Fire_Simulation_Technical_Reference.md"
    
    if not os.path.exists(doc_file) or not os.path.exists(tech_ref_file):
        print("Error: Required markdown files not found.")
        return False
    
    print("=" * 80)
    print("Forest Fire Documentation Link Fixer")
    print("=" * 80)
    
    # Extract section maps for lookups
    print(f"Analyzing {tech_ref_file}...")
    tech_sections = extract_section_numbers(tech_ref_file)
    print(f"Found {len(tech_sections)} numbered sections")
    
    print(f"Analyzing {doc_file}...")
    doc_sections = extract_section_numbers(doc_file)
    print(f"Found {len(doc_sections)} numbered sections")
    
    # Find broken links in both directions
    print("\nChecking for broken links...")
    doc_to_tech_broken = find_broken_links(doc_file, tech_ref_file)
    tech_to_doc_broken = find_broken_links(tech_ref_file, doc_file)
    
    print(f"Found {len(doc_to_tech_broken)} broken links from Documentation to Technical Reference")
    print(f"Found {len(tech_to_doc_broken)} broken links from Technical Reference to Documentation")
    
    # Fix broken links
    print("\nAttempting to fix broken links...")
    fixed_doc = fix_broken_links(doc_file, tech_ref_file, doc_to_tech_broken, tech_sections)
    fixed_tech = fix_broken_links(tech_ref_file, doc_file, tech_to_doc_broken, doc_sections)
    
    # Update HTML files
    print("\nUpdating HTML documentation files...")
    updated_html = update_html_documentation_links()
    print(f"Updated {updated_html} HTML files")
    
    # Fix workflow diagram links
    print("\nFixing workflow diagram links...")
    fixed_workflow = fix_workflow_diagram_links()
    print(f"Added {fixed_workflow} navigation improvements to workflow diagrams")
    
    print("\nSummary:")
    print(f"Fixed {fixed_doc} links in {doc_file}")
    print(f"Fixed {fixed_tech} links in {tech_ref_file}")
    
    # Add a note about redundant scripts
    print("\nRedundant scripts that can be deleted:")
    print("- create_docs_website_combined.py (already deleted)")
    print("- create_docs_website_minimal.py (redundant with create_docs_website.py)")
    print("- create_docs_website_fixed.py (redundant with create_docs_website.py)")
    print("- create_docs_website_backup.py (redundant with create_docs_website.py)")
    print("- fix_script.py (redundant with fix_doc_links.py)")
    
    print("\nLink fixing complete!")
    return True

if __name__ == "__main__":
    main() 