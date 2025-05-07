# Forest Fire Simulation Documentation PDF Conversion

This directory contains tools to convert the Forest Fire Simulation Framework documentation from Markdown to PDF format.

## Requirements

Before using the conversion script, you need to install:

1. **Pandoc** - Document conversion tool
   - Download from: https://pandoc.org/installing.html
   - Verify installation with: `pandoc --version`

2. **LaTeX Distribution** - Required for PDF generation
   - For Windows: MiKTeX (https://miktex.org/download)
   - For macOS: MacTeX (https://tug.org/mactex/)
   - For Linux: TeX Live (`sudo apt install texlive-full` or equivalent)
   - Verify installation with: `pdflatex --version`

## Quick Start

To convert the default Markdown files to PDF:

```bash
python md_to_pdf.py
```

This will convert:
- `Forest_Fire_Simulation_Documentation.md`
- `Forest_Fire_Simulation_Technical_Reference.md`

The resulting PDFs will be saved in the same directory as the source files.

## Command Line Options

```bash
python md_to_pdf.py [options]
```

Options:
- `--files` - Comma-separated list of markdown files to convert
- `--output-dir` - Directory to save PDF files (default: same as input)
- `--toc` - Include table of contents (default: yes)
- `--numbered` - Include section numbering (default: yes)
- `--custom-css` - Path to custom CSS file for styling

## Examples

Convert specific files:
```bash
python md_to_pdf.py --files "file1.md,file2.md"
```

Save PDFs to a specific directory:
```bash
python md_to_pdf.py --output-dir "pdf_output"
```

Use custom styling:
```bash
python md_to_pdf.py --custom-css "markdown_pdf_style.css"
```

## Custom Styling

The script includes a default CSS file (`markdown_pdf_style.css`) for better PDF formatting. 
You can modify this file to customize the appearance of your PDF documents.

## Troubleshooting

If you encounter issues:

1. **Missing pandoc**: Install pandoc from https://pandoc.org/installing.html
2. **Missing pdflatex**: Install a LaTeX distribution
3. **Conversion errors**: Check the error messages in the console output

For more complex documents, you may need to install additional LaTeX packages or fonts.

## PDF Features

The generated PDFs include:
- Table of contents
- Section numbering
- Syntax highlighting for code blocks
- Proper handling of images and tables
- A4 paper size with comfortable margins 