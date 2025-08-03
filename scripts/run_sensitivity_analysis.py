#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Simple launcher for the Grid-Based Sensitivity Analysis Runner

This script provides a simple way to run the sensitivity analysis with 
minimal setup. It imports and executes the main runner script.

Usage:
    python run_sensitivity_analysis.py [--config CONFIG_FILE] [--output OUTPUT_DIR]

Examples:
    # Basic usage with default settings
    python run_sensitivity_analysis.py
    
    # With production config file
    python run_sensitivity_analysis.py --config hpc_deployment/Forest_Fire_Simulation_production_test.json
    
    # Custom output directory
    python run_sensitivity_analysis.py --output my_sensitivity_results
    
    # Quick analysis with fewer parameters
    python run_sensitivity_analysis.py --quick

Author: Forest Fire Simulation Team
Date: 2025
Version: 1.0
"""

if __name__ == "__main__":
    try:
        from sensitivity_analysis_runner import main
        exit_code = main()
        exit(exit_code)
    except ImportError as e:
        print(f"Error: Could not import sensitivity analysis runner: {e}")
        print("Make sure you're running this from the Forest-Fire-Simulation directory")
        exit(1)
    except Exception as e:
        print(f"Error: {e}")
        exit(1) 