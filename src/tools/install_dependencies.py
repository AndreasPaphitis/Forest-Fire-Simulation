#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Install Dependencies for Markdown to PDF Conversion

This script helps install the required dependencies for the Markdown to PDF conversion:
1. Pandoc - Document conversion tool
2. MiKTeX - LaTeX distribution for PDF generation

The script will:
- Check if dependencies are already installed
- Open download pages for missing dependencies
- Guide the user through the installation process
"""

import os
import sys
import subprocess
import webbrowser
import platform
import time

def check_pandoc():
    """Check if pandoc is installed and in the PATH."""
    try:
        result = subprocess.run(
            ['pandoc', '--version'], 
            capture_output=True, 
            text=True
        )
        return True, result.stdout.splitlines()[0] if result.stdout else "Unknown version"
    except (subprocess.SubprocessError, FileNotFoundError):
        return False, None

def check_latex():
    """Check if pdflatex is installed and in the PATH."""
    try:
        result = subprocess.run(
            ['pdflatex', '--version'], 
            capture_output=True, 
            text=True
        )
        return True, result.stdout.splitlines()[0] if result.stdout else "Unknown version"
    except (subprocess.SubprocessError, FileNotFoundError):
        return False, None

def install_pandoc():
    """Guide the user through installing Pandoc."""
    print("\n" + "="*80)
    print("INSTALLING PANDOC")
    print("="*80)
    
    print("\nPandoc is a document conversion tool that's required for converting Markdown to PDF.")
    
    # Windows-specific instructions
    if sys.platform.startswith('win'):
        print("\nFor Windows:")
        print("1. Download the Pandoc installer from: https://pandoc.org/installing.html")
        print("2. Run the downloaded .msi file")
        print("3. Follow the installation wizard (accept the defaults)")
        print("4. Restart your command prompt/terminal after installation")
        
        # Open download page
        if input("\nWould you like to open the Pandoc download page? (y/n): ").lower() == 'y':
            webbrowser.open("https://github.com/jgm/pandoc/releases/latest")
            print("\nDownload page opened in your browser.")
            print("Please download and install the appropriate version for your system (Windows .msi installer)")
    
    # macOS specific instructions
    elif sys.platform.startswith('darwin'):
        print("\nFor macOS:")
        print("1. Install using Homebrew (recommended): brew install pandoc")
        print("2. Or download the macOS installer from: https://pandoc.org/installing.html")
        
        if input("\nWould you like to open the Pandoc download page? (y/n): ").lower() == 'y':
            webbrowser.open("https://github.com/jgm/pandoc/releases/latest")
    
    # Linux specific instructions
    else:
        print("\nFor Linux:")
        print("1. Install using your package manager:")
        print("   - Ubuntu/Debian: sudo apt install pandoc")
        print("   - Fedora: sudo dnf install pandoc")
        print("   - Arch Linux: sudo pacman -S pandoc")
        print("2. Or download from: https://pandoc.org/installing.html")
    
    input("\nPress Enter to continue after installing Pandoc...")
    
    # Verify installation
    is_installed, version = check_pandoc()
    if is_installed:
        print(f"\n✅ Pandoc installed successfully: {version}")
        return True
    else:
        print("\n❌ Pandoc installation could not be verified.")
        print("   Please ensure Pandoc is installed and in your PATH.")
        print("   You may need to restart your terminal/command prompt.")
        return False

def install_latex():
    """Guide the user through installing a LaTeX distribution."""
    print("\n" + "="*80)
    print("INSTALLING LATEX")
    print("="*80)
    
    print("\nA LaTeX distribution is required for PDF generation.")
    
    # Windows-specific instructions
    if sys.platform.startswith('win'):
        print("\nFor Windows, we recommend MiKTeX:")
        print("1. Download MiKTeX from: https://miktex.org/download")
        print("2. Run the downloaded installer")
        print("3. Choose 'Install missing packages on the fly: Yes'")
        print("4. Follow the installation wizard")
        print("5. Restart your command prompt/terminal after installation")
        
        # Open download page
        if input("\nWould you like to open the MiKTeX download page? (y/n): ").lower() == 'y':
            webbrowser.open("https://miktex.org/download")
            print("\nDownload page opened in your browser.")
            print("Please download and install MiKTeX")
    
    # macOS specific instructions
    elif sys.platform.startswith('darwin'):
        print("\nFor macOS, we recommend MacTeX:")
        print("1. Download MacTeX from: https://tug.org/mactex/")
        print("2. Run the downloaded installer")
        print("3. Follow the installation wizard")
        
        if input("\nWould you like to open the MacTeX download page? (y/n): ").lower() == 'y':
            webbrowser.open("https://tug.org/mactex/")
    
    # Linux specific instructions
    else:
        print("\nFor Linux:")
        print("1. Install using your package manager:")
        print("   - Ubuntu/Debian: sudo apt install texlive-full")
        print("   - Fedora: sudo dnf install texlive-scheme-full")
        print("   - Arch Linux: sudo pacman -S texlive-most")
    
    print("\nNOTE: LaTeX installations are large (1-4GB) and may take some time.")
    input("Press Enter to continue after installing LaTeX...")
    
    # Verify installation
    is_installed, version = check_latex()
    if is_installed:
        print(f"\n✅ LaTeX installed successfully: {version}")
        return True
    else:
        print("\n❌ LaTeX installation could not be verified.")
        print("   Please ensure LaTeX is installed and in your PATH.")
        print("   You may need to restart your terminal/command prompt.")
        return False

def main():
    """Main function to check and install dependencies."""
    print("\n" + "="*80)
    print("MARKDOWN TO PDF DEPENDENCY INSTALLER")
    print("="*80)
    
    print(f"\nSystem: {platform.system()} {platform.release()}")
    print(f"Python: {platform.python_version()}")
    
    print("\nChecking for required dependencies...")
    
    # Check pandoc
    pandoc_installed, pandoc_version = check_pandoc()
    if pandoc_installed:
        print(f"✅ Pandoc: {pandoc_version}")
    else:
        print("❌ Pandoc: Not found")
        if input("Would you like to install Pandoc now? (y/n): ").lower() == 'y':
            pandoc_installed = install_pandoc()
    
    # Check LaTeX
    latex_installed, latex_version = check_latex()
    if latex_installed:
        print(f"✅ LaTeX: {latex_version}")
    else:
        print("❌ LaTeX: Not found")
        if input("Would you like to install LaTeX now? (y/n): ").lower() == 'y':
            latex_installed = install_latex()
    
    # Final status
    print("\n" + "="*80)
    if pandoc_installed and latex_installed:
        print("✅ All dependencies are installed!")
        print("You can now run 'python md_to_pdf.py' to convert Markdown files to PDF.")
    else:
        print("⚠️ Some dependencies are missing or could not be verified:")
        if not pandoc_installed:
            print("   - Pandoc: Not installed or not in PATH")
        if not latex_installed:
            print("   - LaTeX: Not installed or not in PATH")
        print("\nPlease install the missing dependencies and run this script again.")
    print("="*80)
    
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()