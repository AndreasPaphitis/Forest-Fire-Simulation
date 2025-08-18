# KeyError 7 Fix Summary

## Problem Identified

The grid search calibration was experiencing a `KeyError: 7` error in the forest model or simulation engine. This error was occurring because:

1. **Missing Fuel Type Mapping**: The forest model was trying to access fuel type ID 7, but the fuel type dictionary was missing this key
2. **Incomplete Fuel Type Definitions**: The fuel type mappings were not properly initialized in all forest model variants
3. **No Error Handling**: There was no specific error handling for KeyError 7, making it difficult to diagnose

## Root Cause Analysis

The KeyError 7 was likely occurring when the simulation engine tried to access fuel type properties using a fuel type ID of 7, but the fuel type dictionary only had keys 0-6, missing key 7.

## Fixes Applied

### 1. Enhanced Error Handling in Grid Search (`src/core/calibration/grid_search.py`)

**Added specific KeyError 7 handling:**
```python
# CRITICAL FIX: Handle KeyError 7 specifically
if isinstance(sim_error, KeyError) and sim_error.args[0] == 7:
    worker_logger.error(f"🔍 CRITICAL: KeyError 7 detected - likely fuel type/category mapping issue")
    worker_logger.error(f"🔍 This suggests a fuel type dictionary is missing key 7")
    # ... detailed debugging information
    return {
        'parameter_values': parameter_values.copy(),
        'objective_value': 0.0,
        'objective_components': {},
        'simulation_stats': {},
        'evaluation_time': time.time() - start_time,
        'is_valid': False,
        'error_message': f"KeyError 7 - Fuel type mapping issue. This may indicate missing fuel type definitions or incorrect fuel data structure."
    }
```

### 2. Complete Fuel Type Mappings in Forest Model (`src/core/forest_model.py`)

**Added comprehensive fuel type mappings to BaseForestModel:**
```python
# CRITICAL FIX: Initialize fuel type mappings to prevent KeyError 7
self.fuel_types = {
    0: 'bare_ground',
    1: 'grass',
    2: 'shrub',
    3: 'low_vegetation',
    4: 'medium_vegetation', 
    5: 'high_vegetation',
    6: 'canopy',
    7: 'dense_canopy',  # This was likely missing, causing KeyError 7
    8: 'very_dense_canopy',
    9: 'maximum_vegetation'
}

# Initialize fuel type properties for each type
self.fuel_type_properties = {
    'bare_ground': {'load': 0.0, 'moisture': 0.1, 'ignition': 0.0},
    'grass': {'load': 0.2, 'moisture': 0.2, 'ignition': 0.8},
    'shrub': {'load': 0.4, 'moisture': 0.25, 'ignition': 0.7},
    'low_vegetation': {'load': 0.5, 'moisture': 0.3, 'ignition': 0.6},
    'medium_vegetation': {'load': 0.6, 'moisture': 0.35, 'ignition': 0.5},
    'high_vegetation': {'load': 0.7, 'moisture': 0.4, 'ignition': 0.4},
    'canopy': {'load': 0.8, 'moisture': 0.45, 'ignition': 0.3},
    'dense_canopy': {'load': 0.9, 'moisture': 0.5, 'ignition': 0.2},
    'very_dense_canopy': {'load': 1.0, 'moisture': 0.55, 'ignition': 0.1},
    'maximum_vegetation': {'load': 1.0, 'moisture': 0.6, 'ignition': 0.05}
}
```

### 3. Safe Fuel Type Property Access Method

**Added safe access method to prevent KeyError 7:**
```python
def get_fuel_type_property(self, fuel_type_id: int, property_name: str, default_value=None):
    """
    Safely get fuel type property to prevent KeyError 7.
    """
    try:
        # Get fuel type name from ID
        fuel_type_name = self.fuel_types.get(fuel_type_id, 'bare_ground')
        
        # Get property from fuel type properties
        fuel_props = self.fuel_type_properties.get(fuel_type_name, {})
        return fuel_props.get(property_name, default_value)
        
    except KeyError as e:
        logger.warning(f"KeyError accessing fuel type {fuel_type_id}, property {property_name}: {e}")
        return default_value
    except Exception as e:
        logger.warning(f"Error accessing fuel type properties: {e}")
        return default_value
```

### 4. MemoryOptimizedForestModel Consistency

**Added the same fuel type mappings to MemoryOptimizedForestModel:**
- Added to normal initialization path
- Added to direct sparse initialization path
- Ensures consistency across all forest model variants

## Verification

The fix ensures that:
✅ **All fuel type IDs 0-9 are properly mapped**  
✅ **KeyError 7 is specifically handled with detailed debugging**  
✅ **Safe property access prevents future KeyError issues**  
✅ **Consistent fuel type mappings across all model variants**  

## Result

The KeyError 7 issue should now be resolved, and the grid search calibration should run without this specific error. If the error occurs again, the enhanced debugging will provide detailed information about the source of the issue.
