# Forest Fire Simulation Documentation Scripts Guide

This guide explains the purpose of each documentation script and what it produces.

## Documentation Scripts Overview

| Script | Purpose | Output |
|--------|---------|--------|
| `create_md_to_html.py` | General-purpose script to convert all markdown documents to HTML | All documentation in HTML format |
| `create_workflow_diagrams.py` | Specialized script for rendering workflow diagrams with Mermaid support | Workflow diagrams HTML with properly rendered Mermaid diagrams |
| `create_pdf_docs.py` | Attempts direct PDF conversion of markdown files (requires external dependencies) | PDF files (if dependencies are available) |
| `print_html_to_pdf.bat` | Helper script to open HTML files for printing to PDF | Opens browser for each document to print to PDF |

## Recommended Usage

### For Regular Documentation (User Guide & Technical Reference)

```bash
python create_md_to_html.py --print
```

This will generate HTML files for the main documentation without including the workflow diagrams.

### For Workflow Diagrams with Mermaid Support

```bash
python create_workflow_diagrams.py --print
```

This specialized script properly handles Mermaid diagrams and renders them as interactive diagrams in the HTML output.

### For All Documentation including Workflow Diagrams

```bash
python create_md_to_html.py --include-diagrams --print
```

This will generate HTML for all documentation files including workflow diagrams, but the Mermaid rendering may not be as reliable as using the specialized script.

### For Easy PDF Creation

```bash
print_html_to_pdf.bat
```

This batch file will sequentially open each HTML document for you to save as PDF.

## Generated Files

All HTML files are created in the `html_docs/` directory:

- `Forest_Fire_Simulation_Documentation.html` - User-focused guide
- `Forest_Fire_Simulation_Technical_Reference.html` - Technical implementation details
- `forest_fire_workflow_diagrams.html` - Visual diagrams with Mermaid charts
- Print-friendly versions of each file with `_print.html` suffix
- `index.html` - Landing page with links to all documentation

## Troubleshooting Mermaid Diagrams

If the Mermaid diagrams are not displaying properly:

1. **Use the specialized script**: Always use `create_workflow_diagrams.py` for the workflow diagrams
2. **Check browser compatibility**: Chrome and Edge work best with Mermaid
3. **Enable JavaScript**: Make sure JavaScript is enabled in your browser
4. **Check console**: Open developer tools (F12) to view any error messages
5. **Internet connection**: Mermaid library is loaded from a CDN, so an internet connection is required
6. **Try different browser**: If diagrams don't render in one browser, try another

## PDF Creation Best Practices

When creating PDFs from the HTML files:

1. Use the print-friendly versions (`*_print.html`)
2. In the print dialog, enable:
   - Background graphics
   - Print backgrounds
   - Include images
3. Select "Save as PDF" as the destination
4. Wait for all diagrams to render before printing
5. Use A4 or Letter paper size in portrait orientation

## Known Issues

### Cross-Document Links

Some links between documents may not work correctly. The logs show issues like:

```
Doc file 'Forest_Fire_Simulation_Documentation.md' contains a link 'Forest_Fire_Simulation_Technical_Reference.md#24-method-interrelationships', but
the doc 'Forest_Fire_Simulation_Technical_Reference.md' does not contain an anchor '#24-method-interrelationships'.
```

This happens because:

1. The heading structure in the linked document may have changed
2. The section numbering could be different
3. Special characters in headings affect the generated anchor IDs

### Workarounds for Link Issues

1. **Use the index page**: Navigate via the index page to find content
2. **Use browser search**: Press Ctrl+F to search for keywords
3. **Use the table of contents**: Each document has a comprehensive table of contents
4. **Check warning notice**: A warning notice about cross-document links is displayed at the top of each document
5. **In PDF versions**: Use your PDF reader's search functionality

### Improving Links for Future Versions

If you need to fix these links permanently, consider:

1. Updating the original markdown files to use exact heading text rather than section numbers
2. Adding explicit anchors in the markdown files using HTML syntax (`<a id="unique-anchor"></a>`)
3. Creating a standardized heading scheme across all documents

## Workflow Diagram Scripts

### Creating Workflow Diagrams

To generate workflow diagrams from Markdown:

1. **Main workflow diagrams script**
   ```
   python create_direct_workflow_diagrams.py
   ```
   This script converts `forest_fire_workflow_diagrams.md` to HTML with client-side Mermaid diagram rendering.

2. **Fixing Mermaid diagram rendering issues**
   ```
   python fix_mermaid_diagrams.py
   ```
   This specialized script addresses rendering issues with Mermaid diagrams in the workflow diagrams HTML file. It:
   - Updates to a more compatible Mermaid version (10.8.0)
   - Fixes syntax issues in diagrams
   - Creates standalone individual diagram files for easier debugging
   - Provides better error information for diagram rendering

### Cross-Document Link Fixing

If you encounter issues with broken links between documents (especially between the Documentation and Technical Reference), use:

```
python fix_doc_links.py
```

This script analyzes and fixes broken cross-document links between the main documentation files.

## PDF Generation

To generate PDF documentation:

1. **Main PDF generation script**
   ```
   python create_pdf_docs.py
   ```
   This converts markdown documentation to PDF format.

2. **Print HTML to PDF (alternative)**
   ```
   .\print_html_to_pdf.bat
   ```
   This batch file automates the process of converting HTML to PDF using Chrome in headless mode.

3. **Additional PDF options**
   ```
   .\convert_markdown_to_pdf.bat
   ```
   This offers additional PDF conversion options with customizable parameters.

## Website Generation

To create a documentation website:

```
python create_docs_website.py
```

This script sets up a website with navigation, search, and proper styling using MkDocs. 