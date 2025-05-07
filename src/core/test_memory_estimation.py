#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Unit tests for memory estimation functions in the Forest Fire Simulation Framework.
Tests that ensure the memory estimation functions work correctly and consistently.
"""

import unittest
import os
import sys
import numpy as np

# Add parent directory to path to import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the functions to test
from config_tools import estimate_memory, ModelConfig
from run_tiled_simulation import estimate_memory_requirements

class TestMemoryEstimation(unittest.TestCase):
    """Test class for memory estimation functions."""
    
    def setUp(self):
        """Set up test configurations."""
        # Create a basic configuration for testing
        self.config = ModelConfig()
        self.config.num_layers = 3
        self.config.bytes_per_cell = 15
        self.grid_width = 1000
        self.grid_height = 1000
        
    def test_estimate_memory_basic(self):
        """Test the basic functionality of estimate_memory."""
        # Run the estimation
        result = estimate_memory(self.config, self.grid_width, self.grid_height)
        
        # Check that the result is a dictionary with expected keys
        self.assertIsInstance(result, dict)
        self.assertIn('total_memory_mb', result)
        self.assertIn('grid_memory_mb', result)
        
        # Calculate expected memory for grid: width * height * layers * bytes_per_cell
        expected_bytes = self.grid_width * self.grid_height * self.config.num_layers * self.config.bytes_per_cell
        expected_mb = expected_bytes / (1024 * 1024)
        
        # Check that the grid memory is close to expected (allowing for some overhead)
        self.assertAlmostEqual(result['grid_memory_mb'], expected_mb, delta=expected_mb * 0.1)
        
        # Total memory should be at least the grid memory
        self.assertGreaterEqual(result['total_memory_mb'], result['grid_memory_mb'])
    
    def test_wrapper_function_compatibility(self):
        """Test that the wrapper function returns compatible results."""
        # Get results from both functions
        direct_result = estimate_memory(self.config, self.grid_width, self.grid_height)
        wrapper_result = estimate_memory_requirements(self.grid_width, self.grid_height, self.config.num_layers)
        
        # Check that both results have total memory information
        self.assertIn('total_memory_mb', direct_result)
        self.assertIn('total_mb', wrapper_result)
        
        # The total memory values should be reasonably close
        direct_total = direct_result['total_memory_mb']
        wrapper_total = wrapper_result['total_mb']
        
        # Calculate the difference as a percentage
        if direct_total > 0:
            difference_percent = abs(direct_total - wrapper_total) / direct_total * 100
            # Should be within 10% of each other
            self.assertLess(difference_percent, 10, 
                           f"Memory estimates differ by {difference_percent:.2f}%: direct={direct_total:.2f}MB, wrapper={wrapper_total:.2f}MB")
    
    def test_different_grid_sizes(self):
        """Test memory estimation with different grid sizes."""
        grid_sizes = [
            (100, 100),    # Small
            (1000, 1000),  # Medium
            (5000, 5000),  # Large
        ]
        
        for width, height in grid_sizes:
            with self.subTest(width=width, height=height):
                # Get memory estimate
                result = estimate_memory(self.config, width, height)
                
                # Calculate expected memory
                expected_bytes = width * height * self.config.num_layers * self.config.bytes_per_cell
                expected_mb = expected_bytes / (1024 * 1024)
                
                # Verify the estimate is reasonable
                self.assertAlmostEqual(result['grid_memory_mb'], expected_mb, delta=expected_mb * 0.1)
    
    def test_different_layer_counts(self):
        """Test memory estimation with different layer counts."""
        layer_counts = [1, 5, 10, 20]
        
        for layers in layer_counts:
            with self.subTest(layers=layers):
                # Update the config
                self.config.num_layers = layers
                
                # Get memory estimate
                result = estimate_memory(self.config, self.grid_width, self.grid_height)
                
                # Calculate expected memory
                expected_bytes = self.grid_width * self.grid_height * layers * self.config.bytes_per_cell
                expected_mb = expected_bytes / (1024 * 1024)
                
                # Verify the estimate is reasonable
                self.assertAlmostEqual(result['grid_memory_mb'], expected_mb, delta=expected_mb * 0.1)
    
    def test_zero_or_negative_dimensions(self):
        """Test handling of invalid dimensions."""
        invalid_dimensions = [
            (0, 100),    # Zero width
            (100, 0),    # Zero height
            (-10, 100),  # Negative width
            (100, -10),  # Negative height
        ]
        
        for width, height in invalid_dimensions:
            with self.subTest(width=width, height=height):
                # The function should either handle these gracefully or raise a meaningful error
                try:
                    result = estimate_memory(self.config, width, height)
                    # If no exception, the result should indicate minimal memory usage
                    self.assertGreaterEqual(result['total_memory_mb'], 0)
                except (ValueError, AssertionError) as e:
                    # If exception is raised, it should be a meaningful error
                    self.assertIn(("width" if width <= 0 else "height"), str(e).lower())

if __name__ == '__main__':
    unittest.main() 