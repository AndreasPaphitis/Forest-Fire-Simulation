#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test JSON Serialization Fix

This script tests that the JSON serialization fix works for numpy int64 values.
"""

import sys
import os
import numpy as np
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_json_serialization():
    """Test that JSON serialization works with numpy types."""
    print("🧪 TESTING JSON SERIALIZATION FIX")
    print("=" * 50)
    
    try:
        # Import the serialization function
        from src.core.calibration.calibration_utils import _convert_to_serializable
        
        # Create test data with numpy types that would cause the error
        test_data = {
            'numpy_int64': np.int64(42),
            'numpy_float64': np.float64(3.14),
            'numpy_array': np.array([1, 2, 3, 4, 5]),
            'nested_dict': {
                'inner_numpy_int': np.int64(100),
                'inner_numpy_float': np.float64(2.718)
            },
            'list_with_numpy': [
                np.int64(1),
                np.float64(2.5),
                np.array([10, 20, 30])
            ],
            'regular_types': {
                'string': 'test',
                'int': 123,
                'float': 456.789,
                'bool': True
            }
        }
        
        print("✅ Test data created with numpy types")
        
        # Test the serialization function
        serialized_data = _convert_to_serializable(test_data)
        print("✅ Data converted to serializable format")
        
        # Test JSON serialization
        json_string = json.dumps(serialized_data, indent=2)
        print("✅ JSON serialization successful")
        
        # Test JSON deserialization
        deserialized_data = json.loads(json_string)
        print("✅ JSON deserialization successful")
        
        # Verify the data types
        print("\n📊 VERIFICATION:")
        print(f"  Original numpy_int64 type: {type(test_data['numpy_int64'])}")
        print(f"  Serialized numpy_int64 type: {type(serialized_data['numpy_int64'])}")
        print(f"  Deserialized numpy_int64 type: {type(deserialized_data['numpy_int64'])}")
        
        print(f"  Original numpy_array type: {type(test_data['numpy_array'])}")
        print(f"  Serialized numpy_array type: {type(serialized_data['numpy_array'])}")
        print(f"  Deserialized numpy_array type: {type(deserialized_data['numpy_array'])}")
        
        # Test saving to file
        test_file = Path("test_json_serialization.json")
        with open(test_file, 'w') as f:
            json.dump(serialized_data, f, indent=2)
        print(f"✅ File saved successfully: {test_file}")
        
        # Clean up
        test_file.unlink()
        print("✅ Test file cleaned up")
        
        print("\n🎉 ALL TESTS PASSED! JSON serialization fix is working correctly.")
        
    except Exception as e:
        print(f"❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = test_json_serialization()
    sys.exit(0 if success else 1)
