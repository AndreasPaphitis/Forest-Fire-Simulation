# Forest Fire Simulation Framework Documentation System

This directory contains scripts, tools, and files for the documentation of the Forest Fire Simulation Framework. This README explains the documentation system architecture, how to use the different tools, and how to maintain the documentation.

## Documentation System Overview

### Main Documentation Files

- **Forest_Fire_Simulation_Documentation.md** - Main user-focused documentation
- **Forest_Fire_Simulation_Technical_Reference.md** - Technical details for developers
- **forest_fire_workflow_diagrams.md** - Visual diagrams of the framework (using Mermaid)
- **config_tools_user_guide.md** - Specific guide for configuration tools

### Documentation Generation System

```
                    ┌───────────────────────┐
                    │  Markdown Files (.md) │
                    └───────────┬───────────┘
                                │
                                ▼
        ┌─────────────────────────────────────────┐
        │ Documentation Generation Scripts         │
        │                                          │
        │  ┌────────────────┐  ┌────────────────┐ │
        │  │   HTML Output  │  │   PDF Output   │ │
        │  └────────────────┘  └────────────────┘ │
        │  ┌────────────────┐  ┌────────────────┐ │
        │  │  Website Gen.  │  │ Workflow Diag. │ │
        │  └────────────────┘  └────────────────┘ │
        └─────────────────────────────────────────┘
                                │
                                ▼
        ┌─────────────────────────────────────────┐
        │           Output Formats                 │
        │                                          │
        │  ┌────────────────┐  ┌────────────────┐ │
        │  │  HTML Files    │  │   PDF Files    │ │
        │  └────────────────┘  └────────────────┘ │
        │  ┌────────────────┐                     │
        │  │   MkDocs Site  │                     │
        │  └────────────────┘                     │
        └─────────────────────────────────────────┘
```

## Documentation Scripts

The documentation system is managed through several specialized Python scripts and batch files:

### Core Documentation Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `create_md_to_html.py` | Converts markdown to HTML | `python create_md_to_html.py` |
| `create_pdf_docs.py` | Generates PDF documentation | `python create_pdf_docs.py` |
| `create_docs_website.py` | Creates MkDocs website | `python create_docs_website.py` |
| `create_direct_workflow_diagrams.py` | Generates workflow diagrams | `python create_direct_workflow_diagrams.py` |

### Helper & Fix Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `fix_mermaid_diagrams.py` | Fixes Mermaid diagram rendering | `python fix_mermaid_diagrams.py` |
| `fix_doc_links.py` | Fixes cross-document links | `python fix_doc_links.py` |
| `print_html_to_pdf.bat` | Converts HTML to PDF using Chrome | `.\print_html_to_pdf.bat` |

## Documentation Workflows

### 1. Updating Documentation

1. Update markdown files as needed
2. Convert to HTML: `python create_md_to_html.py`
3. Generate workflow diagrams: `python create_direct_workflow_diagrams.py`
4. Fix any Mermaid diagram issues: `python fix_mermaid_diagrams.py`
5. Fix cross-document links: `python fix_doc_links.py`
6. Generate PDFs: `python create_pdf_docs.py`

### 2. Building Documentation Website

```bash
python create_docs_website.py
```

This creates a complete website with navigation, search, and proper styling using MkDocs.

### 3. Generating Workflow Diagrams

```bash
python create_direct_workflow_diagrams.py
python fix_mermaid_diagrams.py  # If any rendering issues
```

## Common Issues and Solutions

### Mermaid Diagram Rendering Issues

If Mermaid diagrams are not rendering correctly:

1. Run `python fix_mermaid_diagrams.py` to fix syntax and update to a more compatible version
2. Check the standalone diagrams created in `html_docs/standalone_diagrams/`
3. Use the [Mermaid Live Editor](https://mermaid.live) to debug specific diagrams

### Cross-Document Link Issues

If links between documentation files are broken:

1. Run `python fix_doc_links.py` to automatically fix common issues
2. For persistent issues, manually add HTML anchors to the target section: `<a id="unique-id"></a>`

### PDF Generation Issues

If PDF generation fails:

1. Try the alternative batch file: `.\print_html_to_pdf.bat`
2. Check for Chrome installation (required for headless conversion)
3. Try manual conversion by opening the HTML in a browser and printing to PDF

## File Structure

```
├── Documentation Source Files
│   ├── Forest_Fire_Simulation_Documentation.md
│   ├── Forest_Fire_Simulation_Technical_Reference.md
│   ├── forest_fire_workflow_diagrams.md
│   └── config_tools_user_guide.md
│
├── Core Script Files
│   ├── create_md_to_html.py         # Markdown to HTML conversion
│   ├── create_pdf_docs.py           # PDF generation
│   ├── create_docs_website.py       # MkDocs website
│   ├── create_direct_workflow_diagrams.py  # Workflow diagrams
│   ├── fix_mermaid_diagrams.py      # Mermaid diagram fixes
│   └── fix_doc_links.py             # Cross-document link fixes
│
├── Helper Files
│   ├── print_html_to_pdf.bat        # HTML to PDF batch file
│   ├── markdown_pdf_style.css       # Styling for PDFs
│   └── mkdocs.yml                   # MkDocs configuration
│
└── Output Directories
    ├── html_docs/                   # HTML output
    │   └── diagram_images/          # Diagram images
    ├── site/                        # MkDocs site
    └── docs/                        # MkDocs content
```

## Maintenance Guidelines

### Adding New Diagrams

1. Add Mermaid diagrams to `forest_fire_workflow_diagrams.md`
2. Run the workflow diagram scripts
3. If new diagrams don't render correctly, check the syntax with [Mermaid Live Editor](https://mermaid.live)

### Cross-Document References

When referencing across documents:

1. Use relative links: `[Link text](Other_Document.md#section-id)`
2. Use kebab-case for section IDs (lowercase with hyphens)
3. Run `fix_doc_links.py` to catch any issues

### Documentation Versioning

1. Include version numbers in documentation headers
2. Update the "Last Modified" date when making significant changes
3. Consider keeping an update log at the beginning of each document

## Redundant Scripts and Cleanup

The following scripts are redundant and can be safely deleted:

1. **`create_docs_website_combined.py`**: Already deleted, replaced by more specialized scripts
2. **`create_docs_website_minimal.py`**: Redundant with `create_docs_website.py` which includes all features
3. **`create_docs_website_fixed.py`**: Redundant with `create_docs_website.py` after bug fixes were incorporated
4. **`create_docs_website_backup.py`**: Historical backup, functionality included in main script
5. **`fix_script.py`**: Replaced by `fix_doc_links.py` which has more comprehensive link fixing

### File Organization

Files are now organized into the following structure:

- **Documentation_Source/** - Main markdown files 
- **Documentation_Scripts/** - Core documentation generation scripts
- **Documentation_Helpers/** - Helper utilities and support files
- **Redundant_Scripts/** - Archives of outdated scripts
- **html_docs/** - Generated HTML output

When adding new scripts, please place them in the appropriate directory to maintain organization.

## Workflow Diagrams

### Generating Workflow Diagrams

To generate the workflow diagrams:

1. Use `create_direct_workflow_diagrams.py` to generate the initial HTML
2. Then use `fix_mermaid_diagrams.py` to fix and optimize the Mermaid diagrams

```bash
python create_direct_workflow_diagrams.py
python fix_mermaid_diagrams.py
```

This creates several files:
- `forest_fire_workflow_diagrams_static_fixed.html` - The main fixed version (recommended)
- `forest_fire_workflow_diagrams_static_fixed_print.html` - Print-friendly version
- Standalone diagrams in the `html_docs/standalone_diagrams/` directory

### Troubleshooting Diagrams

If diagrams aren't rendering correctly:

1. Check the standalone diagrams to identify which specific diagrams have issues
2. Try different Mermaid versions in the standalone diagrams 
3. Use browser developer tools (F12) to check for JavaScript errors
4. Make sure JavaScript is enabled in your browser

### Fixing Cross-Document Links

To fix broken links between documentation files:

```bash
python fix_doc_links.py
```

This script:
- Fixes cross-document links between markdown files
- Updates HTML files with corrected anchor links
- Adds navigation links to workflow diagram HTML files

## Future Improvements

- Automated test suite for documentation validity
- CI/CD pipeline for documentation updates
- Integration with version control for documentation
- Interactive diagram support beyond Mermaid
- Multi-language documentation support 