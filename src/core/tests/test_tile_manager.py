#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Unit tests for the TileManager class in the Forest Fire Simulation Framework.
Tests various aspects of tile management, memory usage estimation, and tile activation/deactivation.
"""

import unittest
import os
import sys
import numpy as np
import tempfile
import shutil

# Add parent directory to path to import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the classes to test
from core_simulation_framework import TileManager, DiskStorageManager

class TestTileManager(unittest.TestCase):
    """Test class for the TileManager."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Basic configuration for a small grid
        self.grid_width = 1000
        self.grid_height = 1000
        self.tile_size = 200
        self.overlap = 10
        self.num_layers = 3
        self.memory_limit = 100  # MB, deliberately small for testing

        # Create a temporary directory for storage
        self.temp_dir = tempfile.mkdtemp()
        
        # Create tile manager
        self.tile_manager = TileManager(
            grid_width=self.grid_width,
            grid_height=self.grid_height,
            tile_size=self.tile_size,
            overlap=self.overlap,
            memory_limit_mb=self.memory_limit,
            num_layers=self.num_layers
        )
        
        # Create sample tile data (3D array)
        self.sample_data = np.zeros((self.tile_size, self.tile_size, self.num_layers), dtype=np.float32)
        
    def tearDown(self):
        """Clean up test fixtures."""
        # Remove temporary directory
        shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """Test correct initialization of TileManager."""
        # Check grid dimensions
        self.assertEqual(self.tile_manager.width, self.grid_width)
        self.assertEqual(self.tile_manager.height, self.grid_height)
        
        # Check tile dimensions
        self.assertEqual(self.tile_manager.tile_size, self.tile_size)
        self.assertEqual(self.tile_manager.overlap, self.overlap)
        
        # Check memory settings
        self.assertEqual(self.tile_manager.memory_limit_mb, self.memory_limit)
        self.assertEqual(self.tile_manager.num_layers, self.num_layers)
        
        # Check derived properties
        expected_tiles_x = (self.grid_width + self.tile_size - 1) // self.tile_size
        expected_tiles_y = (self.grid_height + self.tile_size - 1) // self.tile_size
        self.assertEqual(self.tile_manager.tiles_x, expected_tiles_x)
        self.assertEqual(self.tile_manager.tiles_y, expected_tiles_y)
        self.assertEqual(self.tile_manager.total_tiles, expected_tiles_x * expected_tiles_y)
        
        # Check initial state
        self.assertEqual(len(self.tile_manager.active_tiles), 0)
        self.assertEqual(self.tile_manager.current_memory_usage_mb, 0)
    
    def test_memory_estimation(self):
        """Test the memory estimation for tiles."""
        # Get the estimated memory per tile
        estimated_memory = self.tile_manager._estimate_tile_memory_mb()
        
        # Calculate expected memory: tile_size^2 * num_layers * bytes_per_value / (1024^2)
        # Assuming 4 bytes per float32 value
        expected_memory = (self.tile_size ** 2) * self.num_layers * 4 / (1024 ** 2)
        
        # Should be close to expected (allow for some overhead)
        self.assertAlmostEqual(estimated_memory, expected_memory, delta=expected_memory * 0.2)
    
    def test_tile_activation_deactivation(self):
        """Test activating and deactivating tiles."""
        # Activate a tile
        tile_x, tile_y = 0, 0
        result = self.tile_manager.activate_tile(tile_x, tile_y, self.sample_data)
        
        # Check that activation was successful
        self.assertTrue(result)
        self.assertIn((tile_x, tile_y), self.tile_manager.active_tiles)
        self.assertGreater(self.tile_manager.current_memory_usage_mb, 0)
        
        # Update tile data
        new_data = np.ones((self.tile_size, self.tile_size, self.num_layers), dtype=np.float32)
        update_result = self.tile_manager.update_tile_data(tile_x, tile_y, new_data)
        self.assertTrue(update_result)
        
        # Check that the data was updated
        tile_data = self.tile_manager.get_tile_data(tile_x, tile_y)
        np.testing.assert_array_equal(tile_data, new_data)
        
        # Deactivate the tile
        deactivate_result = self.tile_manager.deactivate_tile(tile_x, tile_y)
        self.assertTrue(deactivate_result)
        self.assertNotIn((tile_x, tile_y), self.tile_manager.active_tiles)
        self.assertEqual(self.tile_manager.current_memory_usage_mb, 0)
    
    def test_memory_limit_enforcement(self):
        """Test that memory limits are enforced."""
        # Calculate how many tiles should fit in memory
        tile_memory = self.tile_manager._estimate_tile_memory_mb()
        max_tiles = int(self.memory_limit / tile_memory)
        
        # Add more tiles than should fit
        for i in range(max_tiles + 5):  # Add 5 more than should fit
            x, y = i % self.tile_manager.tiles_x, i // self.tile_manager.tiles_x
            if x < self.tile_manager.tiles_x and y < self.tile_manager.tiles_y:
                self.tile_manager.activate_tile(x, y, self.sample_data)
        
        # Check that memory limit is respected
        self.assertLessEqual(self.tile_manager.current_memory_usage_mb, self.memory_limit * 1.1)  # Allow 10% margin
        self.assertLessEqual(len(self.tile_manager.active_tiles), max_tiles + 1)  # +1 for rounding

    def test_integration_with_disk_storage(self):
        """Test integration with DiskStorageManager."""
        # Create a disk storage manager
        storage_manager = DiskStorageManager(
            storage_dir=self.temp_dir,
            max_memory_mb=20  # Small cache for testing
        )
        
        # Create load/unload callbacks
        def load_callback(tile_x, tile_y):
            key = f"tile_{tile_x}_{tile_y}"
            try:
                return storage_manager.retrieve(key)
            except KeyError:
                return np.zeros((self.tile_size, self.tile_size, self.num_layers), dtype=np.float32)
        
        def unload_callback(tile_x, tile_y, tile_data):
            key = f"tile_{tile_x}_{tile_y}"
            storage_manager.store(key, tile_data)
        
        # Create a new tile manager with callbacks
        tile_manager = TileManager(
            grid_width=self.grid_width,
            grid_height=self.grid_height,
            tile_size=self.tile_size,
            overlap=self.overlap,
            memory_limit_mb=self.memory_limit,
            num_layers=self.num_layers,
            on_tile_load=load_callback,
            on_tile_unload=unload_callback
        )
        
        # Activate and update a tile
        tile_x, tile_y = 1, 1
        tile_manager.activate_tile(tile_x, tile_y)
        
        # Create some unique data for this tile
        unique_data = np.ones((self.tile_size, self.tile_size, self.num_layers), dtype=np.float32) * 5
        tile_manager.update_tile_data(tile_x, tile_y, unique_data)
        
        # Deactivate the tile - should trigger unload callback
        tile_manager.deactivate_tile(tile_x, tile_y)
        
        # Activate it again - should trigger load callback
        tile_manager.activate_tile(tile_x, tile_y)
        
        # Verify that the data was preserved
        loaded_data = tile_manager.get_tile_data(tile_x, tile_y)
        np.testing.assert_array_equal(loaded_data, unique_data)
    
    def test_invalid_tile_coordinates(self):
        """Test handling of invalid tile coordinates."""
        # Test with negative coordinates
        result = self.tile_manager.activate_tile(-1, 0)
        self.assertFalse(result)
        
        # Test with coordinates beyond grid bounds
        result = self.tile_manager.activate_tile(self.tile_manager.tiles_x, 0)
        self.assertFalse(result)
        
        # Test get_tile_data with invalid coordinates
        data = self.tile_manager.get_tile_data(self.tile_manager.tiles_x + 1, 0)
        self.assertIsNone(data)
        
        # Test update_tile_data with invalid coordinates
        result = self.tile_manager.update_tile_data(-1, -1, self.sample_data)
        self.assertFalse(result)
    
    def test_neighboring_tiles(self):
        """Test getting neighboring tiles."""
        # Test center tile neighbors
        tile_x, tile_y = 1, 1
        neighbors = self.tile_manager.get_neighboring_tiles(tile_x, tile_y)
        
        # Should have 8 neighbors (including diagonals)
        expected_neighbors = [
            (0, 0), (1, 0), (2, 0),
            (0, 1),         (2, 1),
            (0, 2), (1, 2), (2, 2)
        ]
        
        # Convert to set for easy comparison
        self.assertEqual(set(neighbors), set(expected_neighbors))
        
        # Test edge tile neighbors
        tile_x, tile_y = 0, 0
        neighbors = self.tile_manager.get_neighboring_tiles(tile_x, tile_y)
        
        # Should have 3 neighbors (right, below, and diagonal)
        expected_neighbors = [(1, 0), (0, 1), (1, 1)]
        
        # Convert to set for easy comparison
        self.assertEqual(set(neighbors), set(expected_neighbors))

    def test_activate_region(self):
        """Test activating a region of tiles."""
        # Define a region
        x, y = 100, 100
        width, height = 300, 300
        
        # Activate the region
        self.tile_manager.activate_region(x, y, width, height)
        
        # Calculate which tiles should be activated
        start_tile_x = x // self.tile_size
        start_tile_y = y // self.tile_size
        end_tile_x = (x + width - 1) // self.tile_size
        end_tile_y = (y + height - 1) // self.tile_size
        
        expected_tiles = set()
        for tx in range(start_tile_x, end_tile_x + 1):
            for ty in range(start_tile_y, end_tile_y + 1):
                if tx < self.tile_manager.tiles_x and ty < self.tile_manager.tiles_y:
                    expected_tiles.add((tx, ty))
        
        # Check that all expected tiles are active
        for tx, ty in expected_tiles:
            self.assertIn((tx, ty), self.tile_manager.active_tiles)

if __name__ == '__main__':
    unittest.main() 