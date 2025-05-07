# Forest Fire Simulation Framework Documentation Tools

This directory contains several scripts to convert the Forest Fire Simulation Framework Markdown documentation into browsable HTML and printable PDF formats.

## Available Scripts

1. **`create_md_to_html.py`** - Converts all Markdown files to HTML
2. **`create_workflow_diagrams.py`** - Specialized script for the workflow diagrams file with Mermaid support
3. **`create_pdf_docs.py`** - Attempts to convert Markdown files directly to PDF (requires external dependencies)
4. **`print_html_to_pdf.bat`** - Helper batch file to open HTML files for printing to PDF

## Quick Start

### Generate HTML Documentation

To generate all HTML documentation including the workflow diagrams:

```bash
python create_md_to_html.py --include-diagrams --print
```

To generate only the workflow diagrams with enhanced Mermaid support:

```bash
python create_workflow_diagrams.py --print
```

This will:
- Convert all markdown files to HTML
- Include the workflow diagrams with proper Mermaid diagram support
- Create both regular and print-friendly versions
- Open the documentation in your default web browser

### Generate PDF Documentation

The easiest way to create PDFs is:

1. First generate the HTML files with the command above
2. Run the helper batch file:
   ```
   print_html_to_pdf.bat
   ```
3. Follow the on-screen instructions to save each document as PDF

## Command Line Options

### create_md_to_html.py

```
--print              Create print-friendly versions suitable for PDF conversion
--include-diagrams   Include the workflow diagrams file with Mermaid diagram support
```

### create_pdf_docs.py

No command line options. This script attempts to convert directly to PDF using multiple methods
(Pandoc, wkhtmltopdf, or WeasyPrint), but requires external dependencies that may not be installed.

## Output Locations

- HTML files are created in the `html_docs/` directory
- PDF files (if using `create_pdf_docs.py`) are created in the `pdf_docs/` directory

## Documentation Files

The documentation consists of the following files:

1. **Forest_Fire_Simulation_Documentation.md** - User-focused guide
2. **Forest_Fire_Simulation_Technical_Reference.md** - Technical implementation details
3. **forest_fire_workflow_diagrams.md** - Visual diagrams with Mermaid charts for presentations

## Note on Mermaid Diagrams

The workflow diagrams file contains interactive Mermaid diagrams. For these to display correctly:

- Use a modern browser with JavaScript enabled
- For best results, use the specialized script: `python create_workflow_diagrams.py`
- When printing to PDF, allow time for diagrams to render before printing
- In the print dialog, ensure these settings are enabled:
  - Background graphics
  - Print backgrounds
  - Include images

If the diagrams are not displaying properly:
- Try refreshing the page (sometimes diagrams need a moment to render)
- Check your browser's JavaScript console for errors
- Make sure your browser can access the internet to load the Mermaid library
- Try a different browser (Chrome and Edge typically work well with Mermaid)

## Troubleshooting

If you encounter issues:

1. **HTML generation fails** - Ensure you have the required Python packages:
   ```
   pip install markdown pygments
   ```

2. **Diagrams don't render** - Check that your browser supports JavaScript and can access the internet to load the Mermaid library

3. **PDF conversion issues** - Try using the browser's print-to-PDF functionality with the print-friendly HTML versions 