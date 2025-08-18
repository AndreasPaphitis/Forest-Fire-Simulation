# DEFINITIVE Calibration Parameter Implementation Analysis

## COMPLETE LINE-BY-LINE ANALYSIS

After thorough line-by-line examination of the fire simulation engine, here is the **definitive** list of all parameters actually used in the simulation.

## ✅ **ALL IMPLEMENTED PARAMETERS** (Found in Code)

### **Core Fire Mechanics**
- ✅ `spread_probability` - **Line 906**: `base_prob = getattr(self.config, 'spread_probability', 0.8)`
- ✅ `fuel_consumption_rate` - **Line 824**: `consumption_rate = getattr(self.config, 'fuel_consumption_rate', 1.0)`
- ✅ `ignition_threshold` - **Line 1050**: `ignition_threshold = getattr(self.config, 'ignition_threshold', 0.1)`
- ✅ `min_fuel_value` - **Lines 825, 883, 1369**: Used in burnout and ignition checks
- ✅ `max_fuel_value` - **Lines 1014, 1377**: Used in fuel normalization

### **Environmental Interactions**
- ✅ `slope_influence` - **Line 1114**: `slope_influence = self.config.slope_influence`
- ✅ `wind_influence_on_spread` - **Line 990**: `wind_influence_factor_config = getattr(self.config, 'wind_influence_on_spread', 0.5)`
- ✅ `reference_wind_speed` - **Line 989**: `reference_speed_for_scaling = getattr(self.config, 'reference_wind_speed', 10.0)`
- ✅ `fuel_moisture_baseline` - **Line 1387**: `baseline_moisture = getattr(self.config, 'fuel_moisture_baseline', 0.3)`

### **Wind Parameters (Used in Main Fire Spread)**
- ✅ `wind_speed` - **Lines 920-994**: Used via `get_wind_speed_at_cell()` in main fire spread calculation
- ✅ `wind_direction` - **Lines 926-994**: Used via `get_wind_direction_at_cell()` in main fire spread calculation

### **Ember Mechanics**
- ✅ `ember_probability` - **Line 1250**: `ember_prob = self.config.ember_probability`
- ✅ `ember_distance` - **Lines 1284, 1401**: Used in ember travel and ignition distance factor
- ✅ `ember_ignition` - **Line 1374**: `ignition_prob = self.config.ember_ignition`
- ✅ `ember_height_factor` - **Line 1254**: Used in ember generation height factor
- ✅ `ember_wind_factor` - **Line 1301**: `wind_strength = self.config.ember_wind_factor`
- ✅ `ember_rise` - **Line 1314**: Used in ember height change calculation

### **Simulation Control Parameters**
- ✅ `max_steps` - **Line 323**: Used in simulation loop control
- ✅ `stop_when_fire_extinguished` - **Line 326**: Used in simulation termination logic
- ✅ `random_seed` - **Line 267**: Used for RNG initialization

## ❌ **PARAMETERS NOT IMPLEMENTED** (Missing from Code)

### **Critical Missing Parameters**
- ❌ `terrain_effect_strength` - **NOT FOUND** in any fire spread calculation
- ❌ `barranco_amplification` - **NOT FOUND** in any fire spread calculation  
- ❌ `barranco_direction_weight` - **NOT FOUND** in any fire spread calculation

## 🔍 **DETAILED CODE ANALYSIS**

### **Main Fire Spread Calculation (`_check_ignition` method)**
```python
# Line 906: Base probability
base_prob = getattr(self.config, 'spread_probability', 0.8)

# Lines 989-990: Wind parameters
reference_speed_for_scaling = getattr(self.config, 'reference_wind_speed', 10.0)
wind_influence_factor_config = getattr(self.config, 'wind_influence_on_spread', 0.5)

# Line 1114: Slope influence
slope_influence = self.config.slope_influence

# Lines 1014, 1377: Fuel parameters
max_fuel = self.config.max_fuel_value

# Line 1050: Ignition threshold
ignition_threshold = getattr(self.config, 'ignition_threshold', 0.1)
```

### **Fuel Consumption (`_check_burnout` method)**
```python
# Line 824: Fuel consumption rate
consumption_rate = getattr(self.config, 'fuel_consumption_rate', 1.0)

# Line 825: Minimum fuel threshold
min_fuel = getattr(self.config, 'min_fuel_value', 0.1)
```

### **Ember Processing (`_process_embers` method)**
```python
# Line 1250: Ember generation probability
ember_prob = self.config.ember_probability

# Line 1254: Height factor
height_factor = 1.0 + (z / self.forest_model.num_layers) * self.config.ember_height_factor

# Line 1284: Ember travel distance
base_distance = self.config.ember_distance

# Line 1301: Wind influence on embers
wind_strength = self.config.ember_wind_factor

# Line 1314: Ember height change
height_change = np.random.randint(-2, self.config.ember_rise + 1)
```

### **Ember Ignition (`_check_ember_ignition` method)**
```python
# Line 1369: Minimum fuel for ignition
min_fuel = self.config.min_fuel_value

# Line 1374: Ember ignition probability
ignition_prob = self.config.ember_ignition

# Line 1377: Fuel normalization
fuel_factor = min(1.0, self.forest_model.fuel_load[x, y, z] / self.config.max_fuel_value)

# Line 1387: Baseline moisture
baseline_moisture = getattr(self.config, 'fuel_moisture_baseline', 0.3)

# Line 1401: Distance factor
distance_factor = max(0.3, 1.0 - (distance / (self.config.ember_distance * 2)))
```

## 📊 **CORRECTED PARAMETER LIST FOR SENSITIVITY ANALYSIS**

```python
calibration_parameters = [
    # Core Fire Mechanics
    'spread_probability',      # ✅ Line 906 - Base fire spread probability
    'fuel_consumption_rate',   # ✅ Line 824 - Fuel consumption rate
    'ignition_threshold',      # ✅ Line 1050 - Ignition probability threshold
    'min_fuel_value',          # ✅ Lines 825, 883, 1369 - Minimum fuel for burning
    'max_fuel_value',          # ✅ Lines 1014, 1377 - Maximum fuel normalization
    
    # Environmental Interactions
    'wind_influence_on_spread', # ✅ Line 990 - Wind effect on fire spread
    'slope_influence',         # ✅ Line 1114 - Terrain slope effect
    'reference_wind_speed',    # ✅ Line 989 - Reference wind speed for scaling
    'fuel_moisture_baseline',  # ✅ Line 1387 - Baseline fuel moisture
    
    # Wind Parameters (Main Fire Spread)
    'wind_speed',              # ✅ Lines 920-994 - Wind speed via get_wind_speed_at_cell()
    'wind_direction',          # ✅ Lines 926-994 - Wind direction via get_wind_direction_at_cell()
    
    # Ember Mechanics
    'ember_probability',       # ✅ Line 1250 - Ember generation probability
    'ember_distance',          # ✅ Lines 1284, 1401 - Ember travel distance
    'ember_ignition',          # ✅ Line 1374 - Ember ignition probability
    'ember_height_factor',     # ✅ Line 1254 - Height factor for ember generation
    'ember_wind_factor',       # ✅ Line 1301 - Wind influence on ember direction
    'ember_rise'               # ✅ Line 1314 - Ember height change range
]
```

## ❌ **REMOVE FROM CALIBRATION** (Not Implemented)
- `terrain_effect_strength` - **NOT IMPLEMENTED**
- `barranco_amplification` - **NOT IMPLEMENTED**  
- `barranco_direction_weight` - **NOT IMPLEMENTED**

## 🎯 **CONCLUSION**

**This is the definitive list** based on line-by-line code analysis. All parameters listed above are **actually used** in the fire simulation engine and should be included in sensitivity analysis.

**Total: 16 implemented parameters** that actually affect the simulation.

**Immediate action**: Update your calibration framework to use only these 16 parameters for accurate sensitivity analysis and calibration.
