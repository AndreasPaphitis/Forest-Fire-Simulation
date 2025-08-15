# Comprehensive Forest Fire Simulation Framework - Workflow Documentation

## Abstract

This document presents a comprehensive workflow for the forest fire simulation framework developed for modeling fire behavior in complex terrain environments. The framework integrates LiDAR-derived vegetation data, advanced calibration methods, and high-performance computing to provide accurate fire spread predictions. The workflow encompasses six main phases: data preparation, model calibration, simulation execution, deployment scaling, analysis & visualization, and validation & research integration.

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Data Preparation & Preprocessing](#2-data-preparation--preprocessing)
3. [Model Calibration & Parameter Optimization](#3-model-calibration--parameter-optimization)
4. [Simulation Framework & Execution](#4-simulation-framework--execution)
5. [HPC Deployment & Scaling](#5-hpc-deployment--scaling)
6. [Analysis & Visualization Pipeline](#6-analysis--visualization-pipeline)
7. [Validation & Research Integration](#7-validation--research-integration)
8. [System Integration & Data Flow](#8-system-integration--data-flow)

---

## 1. System Overview

### 1.1 Framework Architecture

```mermaid
graph TB
    subgraph INPUT ["🔗 INPUT DATA SOURCES"]
        direction TB
        LiDAR[("🌲 LiDAR Point Clouds<br/><small>(.laz/.las files)</small>")]
        DEM[("🏔️ Digital Elevation Model<br/><small>(DTM raster data)</small>")]
        EMSR[("🔥 Historical Fire Data<br/><small>(EMSR Perimeters)</small>")]
        Weather[("🌤️ Weather & Wind Data<br/><small>(Meteorological inputs)</small>")]
    end
    
    subgraph PREP ["⚙️ DATA PREPARATION"]
        direction TB
        DP["📊 Data Preprocessing<br/><small>Pipeline orchestration</small>"]
        VA["🌿 Vegetation Analysis<br/><small>PAD Calculation</small>"]
        TA["🗻 Terrain Analysis<br/><small>Wind Effects & Topography</small>"]
    end
    
    subgraph MODEL ["🎯 MODEL DEVELOPMENT"]
        direction TB
        Cal["📐 Calibration<br/><small>Parameter tuning</small>"]
        Val["✅ Validation<br/><small>Historical comparison</small>"]
        Opt["🎪 Optimization<br/><small>Parameter refinement</small>"]
    end
    
    subgraph SIMULATION ["🖥️ SIMULATION SYSTEM"]
        direction TB
        Core["🔥 3D Fire Engine<br/><small>Core simulation logic</small>"]
        Mem["💾 Memory Management<br/><small>Tiling & Resource control</small>"]
        Phys["⚡ Physics Engine<br/><small>Fire spread mechanics</small>"]
    end
    
    subgraph DEPLOY ["🚀 DEPLOYMENT"]
        direction TB
        Local["💻 Local Testing<br/><small>Development environment</small>"]
        HPC["🏛️ HPC Production<br/><small>Supercomputer deployment</small>"]
        Scale["📈 Resource Scaling<br/><small>Performance optimization</small>"]
    end
    
    subgraph OUTPUT ["📊 OUTPUT & ANALYSIS"]
        direction TB
        Vis["🎨 3D Visualization<br/><small>Animation & rendering</small>"]
        Export["💾 Data Export<br/><small>GIS Integration</small>"]
        Research["📄 Research Output<br/><small>Documentation & analysis</small>"]
    end
    
    %% Enhanced data flow connections with styling
    LiDAR -.->|"Raw point cloud data"| DP
    DEM -.->|"Elevation reference"| DP
    EMSR -.->|"Historical validation"| Cal
    Weather -.->|"Environmental conditions"| Core
    
    DP ==>|"Preprocessed data"| VA
    DP ==>|"Terrain data"| TA
    VA ==>|"Vegetation metrics"| Cal
    TA ==>|"Wind modeling"| Core
    
    Cal ==>|"Initial parameters"| Val
    Val ==>|"Validated model"| Opt
    Opt ==>|"Optimized parameters"| Core
    
    Core ==>|"Simulation state"| Mem
    Mem ==>|"Memory-managed data"| Phys
    Phys ==>|"Physical simulation"| Local
    
    Local ==>|"Tested workflow"| HPC
    HPC ==>|"Production results"| Scale
    Scale ==>|"Optimized output"| Vis
    
    Vis ==>|"Visual products"| Export
    Export ==>|"Research data"| Research
    Research -.->|"Feedback loop"| Val
    
    %% Enhanced styling with modern color palette
    classDef inputStyle fill:#E3F2FD,stroke:#1565C0,stroke-width:3px,color:#0D47A1
    classDef processStyle fill:#E8F5E8,stroke:#2E7D32,stroke-width:3px,color:#1B5E20
    classDef modelStyle fill:#FFF3E0,stroke:#EF6C00,stroke-width:3px,color:#BF360C
    classDef systemStyle fill:#FCE4EC,stroke:#C2185B,stroke-width:3px,color:#880E4F
    classDef deployStyle fill:#F3E5F5,stroke:#7B1FA2,stroke-width:3px,color:#4A148C
    classDef outputStyle fill:#E1F5FE,stroke:#0277BD,stroke-width:3px,color:#01579B
    
    %% Subgraph styling
    classDef subgraphStyle fill:#F8F9FA,stroke:#212529,stroke-width:2px
    
    class LiDAR,DEM,EMSR,Weather inputStyle
    class DP,VA,TA processStyle
    class Cal,Val,Opt modelStyle
    class Core,Mem,Phys systemStyle
    class Local,HPC,Scale deployStyle
    class Vis,Export,Research outputStyle
```

### 1.2 Workflow Phases Overview

| Phase | Purpose | Key Activities | Output |
|-------|---------|---------------|--------|
| **Data Preparation** | Transform raw data into simulation-ready format | LiDAR processing, vegetation analysis, terrain modeling | PAD rasters, terrain data, wind maps |
| **Model Calibration** | Optimize parameters against historical data | Grid search, sensitivity analysis, EMSR validation | Calibrated parameter sets |
| **Simulation Execution** | Run fire spread simulations | 3D fire modeling, state tracking, physics simulation | Fire spread results |
| **HPC Deployment** | Scale simulations for production use | Resource allocation, parallel processing, job management | Production-scale results |
| **Analysis & Visualization** | Generate insights and visualizations | 3D rendering, statistical analysis, export generation | Visual outputs, analysis reports |
| **Validation & Research** | Validate results and support research | Accuracy assessment, documentation, publication support | Research deliverables |

---

### 1.3 Alternative Data Flow Visualization

The following Sankey diagram provides an alternative view of how data flows through the forest fire simulation system, emphasizing volume and transformation at each stage:

```mermaid
sankey-beta

    LiDAR Data,Data Preprocessing,15
    DEM Data,Data Preprocessing,10
    Weather Data,Data Preprocessing,5
    EMSR Data,Data Preprocessing,3
    
    Data Preprocessing,Vegetation Analysis,20
    Data Preprocessing,Terrain Analysis,15
    Data Preprocessing,Quality Control,8
    
    Vegetation Analysis,Model Calibration,15
    Terrain Analysis,Model Calibration,10
    Quality Control,Model Calibration,5
    
    Model Calibration,Parameter Optimization,25
    Model Calibration,Validation,15
    
    Parameter Optimization,Fire Simulation Engine,30
    Validation,Fire Simulation Engine,10
    
    Fire Simulation Engine,Memory Management,35
    Memory Management,Physics Engine,35
    
    Physics Engine,Local Testing,20
    Physics Engine,HPC Deployment,15
    
    Local Testing,Production Scaling,15
    HPC Deployment,Production Scaling,20
    
    Production Scaling,3D Visualization,25
    Production Scaling,Data Export,15
    Production Scaling,Analysis Tools,10
    
    3D Visualization,Research Output,20
    Data Export,Research Output,10
    Analysis Tools,Research Output,15
```

### 1.4 Process Flow Timeline

This swimlane diagram shows the temporal relationship and responsibilities across different system components:

```mermaid
gantt
    title Forest Fire Simulation Workflow Timeline
    dateFormat X
    axisFormat %s
    
    section Data Input
    LiDAR Collection        :0, 2
    DEM Processing          :0, 1
    Weather Data            :1, 3
    Historical Fire Data    :0, 1
    
    section Preprocessing
    Height Normalization    :2, 4
    Vegetation Extraction   :3, 6
    Terrain Analysis        :4, 7
    Quality Control         :6, 8
    
    section Model Development
    Initial Calibration     :8, 12
    Parameter Optimization  :10, 15
    Validation Testing      :12, 16
    Sensitivity Analysis    :14, 18
    
    section Simulation
    Local Testing          :16, 20
    HPC Deployment         :18, 22
    Production Runs        :20, 35
    Resource Scaling       :22, 30
    
    section Analysis
    3D Visualization       :25, 40
    Statistical Analysis   :30, 42
    Export Generation      :35, 45
    Research Documentation :40, 50
```

---

## 2. Data Preparation & Preprocessing

### 2.1 LiDAR Processing Pipeline

```mermaid
flowchart TD
    subgraph "Raw Data Input"
        LAZ[("LiDAR Point Cloud<br/>.laz/.las files")]
        DTM[("Digital Terrain Model<br/>Reference surface")]
    end
    
    subgraph "Height Normalization"
        PDAL["Multiple PDAL JSON Configs<br/>Discrete pipeline files"]
        HAG["Height Above Ground<br/>filters.hag_dem or filters.hag_nn"]
        FERRY["Dimension Transfer<br/>filters.ferry HeightAboveGround=>Z"]
    end
    
    subgraph "Vegetation Extraction"
        CLASS["Classification Filter<br/>(Classes 3,4,5)"]
        CLEAN["Artifact Removal<br/>& Quality Control"]
        VEG[("Vegetation Points<br/>Normalized heights")]
    end
    
    subgraph "Density Analysis"
        BIN["Height Binning<br/>(Configurable intervals)"]
        NRD["NRD_calculation.py<br/>Standalone module"]
        PAD["PAD_calculation.py<br/>Standalone module"]
    end
    
    subgraph "Terrain Analysis"
        SLOPE["Slope & Aspect<br/>Via rasterio gradients"]
        BARR["Barranco Detection<br/>Slope threshold (25°) + depression analysis"]
        WIND["Wind Amplification<br/>Channeling masks & factors"]
    end
    
    subgraph "Output Generation"
        RASTER[("PAD Raster Layers<br/>Up to 25 vertical layers")]
        TERRAIN[("Terrain Data<br/>Slope, aspect, wind effects")]
        META[("Processing Metadata<br/>Quality metrics")]
    end
    
    %% Process flow
    LAZ --> PDAL
    DTM --> HAG
    PDAL --> HAG
    HAG --> FERRY
    FERRY --> CLASS
    CLASS --> CLEAN
    CLEAN --> VEG
    
    VEG --> BIN
    BIN --> NRD
    NRD --> PAD
    
    DTM --> SLOPE
    SLOPE --> BARR
    BARR --> WIND
    
    PAD --> RASTER
    WIND --> TERRAIN
    PAD --> META
    
    %% Styling
    classDef input fill:#e3f2fd
    classDef process fill:#f1f8e9
    classDef output fill:#fff8e1
    
    class LAZ,DTM input
    class PDAL,HAG,FERRY,CLASS,CLEAN,BIN,NRD,PAD,SLOPE,BARR,WIND process
    class VEG,RASTER,TERRAIN,META output
```

### 2.2 Data Quality Control Process

```mermaid
stateDiagram-v2
    [*] --> DataValidation
    
    state DataValidation {
        [*] --> FormatCheck
        FormatCheck --> PointDensityCheck
        PointDensityCheck --> ClassificationCheck
        ClassificationCheck --> QualityPassed
        
        FormatCheck --> FormatFailed : Invalid format
        PointDensityCheck --> DensityFailed : < 4 pts/m²
        ClassificationCheck --> ClassFailed : Missing classes
        
        FormatFailed --> DataRejected
        DensityFailed --> DataRejected
        ClassFailed --> DataRejected
        
        QualityPassed --> [*]
        DataRejected --> [*]
    }
    
    DataValidation --> HeightProcessing : Quality Passed
    DataValidation --> [*] : Data Rejected
    
    state HeightProcessing {
        [*] --> Normalization
        Normalization --> ArtifactDetection
        ArtifactDetection --> ArtifactRemoval
        ArtifactRemoval --> HeightValidation
        HeightValidation --> ProcessingComplete
        
        ArtifactDetection --> ProcessingFailed : Excessive artifacts
        HeightValidation --> ProcessingFailed : Invalid heights
        
        ProcessingFailed --> [*]
        ProcessingComplete --> [*]
    }
    
    HeightProcessing --> DensityAnalysis : Processing Complete
    HeightProcessing --> [*] : Processing Failed
    
    state DensityAnalysis {
        [*] --> BinningProcess
        BinningProcess --> ThresholdCheck
        ThresholdCheck --> DensityCalculation
        DensityCalculation --> ValidationCheck
        ValidationCheck --> AnalysisComplete
        
        ThresholdCheck --> InsufficientData : < 0.1% points
        ValidationCheck --> InvalidDensity : PAD > 10 m⁻¹
        
        InsufficientData --> [*]
        InvalidDensity --> [*]
        AnalysisComplete --> [*]
    }
    
    DensityAnalysis --> SimulationReady : Analysis Complete
    DensityAnalysis --> [*] : Analysis Failed
    
    SimulationReady --> [*]
```

### 2.3 Key Processing Parameters

| Component | Parameter | Value | Purpose |
|-----------|-----------|-------|---------|
| **LiDAR Input** | Point Density | >4 pts/m² | Ensure adequate sampling |
| **Height Normalization** | Bin Size | 2.0m | Vertical layer resolution |
| **Vegetation Classes** | Classification Codes | 3,4,5 | Low/Medium/High vegetation |
| **Quality Control** | Z-score Threshold | 2.5σ | Artifact removal |
| **PAD Calculation** | Max Height | 160m | Canopy height limit |
| **Output Resolution** | Horizontal | 5m | Grid cell size |
| **Vertical Layers** | Count | Up to 25 layers | Realistic 3D structure resolution |

### 2.4 Advanced Terrain Feature Detection

#### 2.4.1 Barranco Detection Algorithm

**Literature-Based Implementation**:
- **Slope Threshold**: 25° (literature range: 20-30° for volcanic terrain)
- **Depression Depth**: 3.0m minimum (literature range: 2-5m)  
- **Minimum Area**: 6 cells (literature range: 4-8 cells)

**Detection Process**:
1. **Slope Analysis**: Calculate terrain slope from DEM using rasterio gradients
2. **Threshold Application**: Identify cells exceeding barranco_threshold (25°)
3. **Depression Analysis**: Apply minimum depression depth criteria (3m)
4. **Connectivity Analysis**: Group connected steep areas meeting minimum area requirement
5. **Direction Calculation**: Compute flow directions within barranco systems

**Output Files**: `barranco_mask.npy`, `barranco_directions.npy`, `depression_mask.npy`

#### 2.4.2 Wind Channeling Implementation

**Literature-Based Parameters**:
- **Channeling Strength**: 0.8 (literature range: 0.7-1.0 for barrancos)
- **Amplification Factor**: 2.5x (literature range: 2.0-3.0x wind speed increase)

**Channeling Process**:
1. **Barranco Identification**: Use detected barranco masks as base
2. **Wind Amplification**: Apply 2.5x wind speed multiplier within channels
3. **Direction Modification**: Align wind direction with barranco orientation

**Output Files**: `wind_channeling_mask.npy`, `wind_amplification.npy`, `wind_direction_modification.npy`

**Tenerife Results**: 3,839 cells identified as barranco/wind channeling areas

---

## 3. Model Calibration & Parameter Optimization

### 3.1 Calibration Framework Overview

```mermaid
graph TB
    subgraph "Calibration Inputs"
        HIST[("Historical Fire Data<br/>(EMSR Perimeters)")]
        BOUNDS[("Parameter Bounds<br/>Physical constraints")]
        TARGET[("Target Metrics<br/>Spatial similarity goals")]
    end
    
    subgraph "Parameter Definition"
        TIERS["Parameter Tiers<br/>Primary, Secondary, Fixed"]
        RANGES["Value Ranges<br/>Min/Max constraints"]
        DEPS["Dependencies<br/>Parameter relationships"]
    end
    
    subgraph "Calibration Methods"
        GRID["Grid Search<br/>Systematic exploration"]
        SENS["Sensitivity Analysis<br/>Parameter importance"]
        OPT["Optimization<br/>Best parameter search"]
    end
    
    subgraph "Validation Process"
        SIM["Simulation Execution<br/>Test parameter sets"]
        EVAL["Performance Evaluation<br/>Similarity metrics"]
        SELECT["Parameter Selection<br/>Best performing sets"]
    end
    
    subgraph "Calibration Outputs"
        PARAMS[("Optimized Parameters<br/>Production-ready values")]
        REPORT[("Calibration Report<br/>Method & results analysis")]
        CONFIG[("Production Config<br/>Ready for deployment")]
    end
    
    %% Connections
    HIST --> TIERS
    BOUNDS --> RANGES
    TARGET --> DEPS
    
    TIERS --> GRID
    RANGES --> SENS
    DEPS --> OPT
    
    GRID --> SIM
    SENS --> EVAL
    OPT --> SELECT
    
    SIM --> EVAL
    EVAL --> SELECT
    SELECT --> PARAMS
    
    PARAMS --> REPORT
    REPORT --> CONFIG
    
    %% Feedback loops
    EVAL --> GRID
    SELECT --> SENS
    
    %% Styling
    classDef input fill:#e8eaf6
    classDef process fill:#e0f2f1
    classDef method fill:#fff3e0
    classDef output fill:#fce4ec
    
    class HIST,BOUNDS,TARGET input
    class TIERS,RANGES,DEPS,SIM,EVAL,SELECT process
    class GRID,SENS,OPT method
    class PARAMS,REPORT,CONFIG output
```

### 3.2 Calibration Process Workflow

```mermaid
sequenceDiagram
    participant Setup as Calibration Setup
    participant Bounds as Parameter Bounds
    participant Method as Calibration Method
    participant Sim as Simulation Engine
    participant Eval as Evaluation System
    participant Results as Results Analysis
    
    Note over Setup,Results: Model Calibration Workflow
    
    Setup->>Bounds: Define parameter space
    activate Bounds
    Bounds->>Bounds: Set physical constraints
    Bounds->>Bounds: Define tier priorities
    Bounds->>Method: Parameter configuration
    deactivate Bounds
    
    activate Method
    Note right of Method: Grid Search / Sensitivity Analysis
    
    loop For each parameter combination
        Method->>Sim: Execute simulation
        activate Sim
        Sim->>Sim: Run fire model
        Sim->>Eval: Simulation results
        deactivate Sim
        
        activate Eval
        Eval->>Eval: Calculate spatial similarity
        Eval->>Eval: Compute objective metrics
        Eval->>Method: Performance score
        deactivate Eval
    end
    
    Method->>Results: Calibration data
    deactivate Method
    
    activate Results
    Results->>Results: Rank parameter sets
    Results->>Results: Analyze sensitivity
    Results->>Results: Generate reports
    Results->>Setup: Optimized configuration
    deactivate Results
    
    Note over Setup,Results: Iterative process for parameter refinement
```

### 3.3 Calibration Methods & Objectives

#### 3.3.1 Parameter Tiers

| Tier | Parameters | Calibration Priority | Method |
|------|------------|---------------------|---------|
| **Primary** | spread_probability, wind_influence_on_spread, slope_influence | High - Direct impact | Grid Search + Sensitivity |
| **Secondary** | ignition_threshold, min_fuel_value, ember_probability | Medium - Moderate impact | Sensitivity Analysis |
| **Tertiary** | barranco_amplification, barranco_direction_weight, terrain_effect_strength | Low - Fine-tuning | Limited range testing |
| **Fixed** | model_resolution, layer_height_meters, num_layers | None - System constants | No calibration |

#### 3.3.2 Objective Functions

```mermaid
graph LR
    subgraph "Spatial Similarity Metrics"
        JACC["Jaccard Index<br/>(Area overlap)"]
        DICE["Dice Coefficient<br/>(Shape similarity)"]
        HAUS["Hausdorff Distance<br/>(Boundary accuracy)"]
    end
    
    subgraph "Fire Behavior Metrics"
        RATE["Spread Rate<br/>(Speed accuracy)"]
        DIR["Direction<br/>(Wind effects)"]
        EXTENT["Final Extent<br/>(Total area)"]
    end
    
    subgraph "Combined Objective"
        WEIGHT["Weighted Combination<br/>α·Spatial + β·Behavior"]
        SCORE["Final Score<br/>(0-1 range)"]
    end
    
    JACC --> WEIGHT
    DICE --> WEIGHT
    HAUS --> WEIGHT
    RATE --> WEIGHT
    DIR --> WEIGHT
    EXTENT --> WEIGHT
    
    WEIGHT --> SCORE
    
    %% Styling
    classDef spatial fill:#e3f2fd
    classDef behavior fill:#e8f5e8
    classDef combined fill:#fff3e0
    
    class JACC,DICE,HAUS spatial
    class RATE,DIR,EXTENT behavior
    class WEIGHT,SCORE combined
```

---

## 4. Simulation Framework & Execution

### 4.1 Core Simulation Architecture

```mermaid
graph TB
    subgraph "Simulation Initialization"
        CONFIG["Configuration Loading<br/>Parameters & settings"]
        DATA["Data Integration<br/>PAD, terrain, weather"]
        GRID["3D Grid Setup<br/>Up to 25 layers × 5m resolution"]
    end
    
    subgraph "Physics Engine"
        HORIZ["Horizontal Spread<br/>Wind & slope effects"]
        VERT["Vertical Spread<br/>PAD-based connectivity"]
        EMBER["Ember Transport<br/>Long-distance ignition"]
    end
    
    subgraph "State Management"
        CELLS["Cell State Tracking<br/>Unburned, burning, burned"]
        PROB["Spread Probability<br/>Threshold calculations"]
        FUEL["Fuel Consumption<br/>Available biomass"]
    end
    
    subgraph "Memory Management"
        TILE["Tiling System<br/>Spatial decomposition"]
        OPT["Memory Optimization<br/>Levels 0-2: 1.0x, 0.7x, 0.4x reduction"]
        SPARSE["Sparse Storage<br/>Efficient data structures"]
    end
    
    subgraph "Output Generation"
        TRACK["State Recording<br/>Timestep data"]
        EXPORT["Data Export<br/>GIS-compatible formats"]
        VIS["Visualization Prep<br/>Rendering data"]
    end
    
    %% Process flow
    CONFIG --> DATA
    DATA --> GRID
    GRID --> HORIZ
    
    HORIZ --> VERT
    VERT --> EMBER
    EMBER --> CELLS
    
    CELLS --> PROB
    PROB --> FUEL
    FUEL --> TRACK
    
    GRID --> TILE
    TILE --> OPT
    OPT --> SPARSE
    
    TRACK --> EXPORT
    EXPORT --> VIS
    
    %% Feedback loops
    CELLS --> HORIZ
    TEMP --> VERT
    FUEL --> EMBER
    
    %% Styling
    classDef init fill:#e8eaf6
    classDef physics fill:#e0f2f1
    classDef state fill:#fff3e0
    classDef memory fill:#fce4ec
    classDef output fill:#f3e5f5
    
    class CONFIG,DATA,GRID init
    class HORIZ,VERT,EMBER physics
    class CELLS,PROB,FUEL state
    class TILE,OPT,SPARSE memory
    class TRACK,EXPORT,VIS output
```

### 4.2 Fire Spread Mechanics

**Important Note**: The current implementation uses a **deterministic threshold-based system** rather than random probability comparisons. Fire ignition occurs when calculated spread probability exceeds a fixed `ignition_threshold` (default 0.5).

#### 4.2.1 Deterministic Ignition Process

The fire spread calculation follows this deterministic process:

1. **Probability Calculation**: `P = spread_probability × fuel_factor × wind_factor × slope_factor × distance_factor`
2. **Threshold Comparison**: Ignition occurs if `P ≥ ignition_threshold` 
3. **No Random Elements**: No `random()` calls in ignition decisions
4. **Fixed Fuel Consumption**: Fuel reduces by `fuel_consumption_rate` per timestep
5. **Deterministic Burnout**: Cell burns out when `fuel ≤ min_fuel_value`

**Note**: While core ignition is deterministic, ember transport uses extensive randomization:
- **Ember Generation**: Random probability check (`np.random.random() < ember_prob`)
- **Travel Distance**: Exponential distribution (`np.random.exponential(base_distance)`)  
- **Travel Direction**: Random angle with wind bias (`np.random.uniform(0, 2π)`)
- **Height Changes**: Random vertical movement (`np.random.randint(-2, ember_rise+1)`)
- **Number of Embers**: Random count per cell (`np.random.randint(1, 4)`)

#### 4.2.2 Ember Transport System

**Ember Generation Process**:
1. **Probability Calculation**: Base ember probability × height factor × wind factor
2. **Generation Check**: Random probability test determines if embers are created
3. **Multiple Embers**: 1-3 embers generated per successful event
4. **Distance Calculation**: Exponential distribution for realistic spread patterns
5. **Direction Calculation**: Random base angle with wind direction bias
6. **Height Movement**: Embers can rise (up to `ember_rise` layers) or fall
7. **Target Validation**: Check bounds and attempt ignition at landing site

**Key Parameters**:
- `ember_probability`: Base generation probability (default: 0.1)
- `ember_distance`: Base travel distance in cells (default: 5)
- `ember_height_factor`: Height multiplier effect (default: 0.2)
- `ember_wind_factor`: Wind direction bias strength (default: 0.4)
- `ember_rise`: Maximum upward movement (default: 2 layers)

#### 4.2.3 State Transition Diagram

```mermaid
stateDiagram-v2
    [*] --> Unburned
    
    state Unburned {
        [*] --> IgnitionCheck
        IgnitionCheck --> FuelAvailable : Fuel > min_fuel_value
        IgnitionCheck --> StayUnburned : Insufficient fuel
        FuelAvailable --> ProbabilityCalc : Calculate spread probability
        ProbabilityCalc --> ThresholdTest : P = base × fuel × wind × slope factors
        ThresholdTest --> ReadyToBurn : P ≥ ignition_threshold (0.5)
        ThresholdTest --> StayUnburned : P < ignition_threshold
        StayUnburned --> [*]
        ReadyToBurn --> [*]
    }
    
    Unburned --> Burning : Ignition triggered
    
    state Burning {
        [*] --> ActiveCombustion
        ActiveCombustion --> FuelConsumption
        FuelConsumption --> BurnCheck : Reduce fuel by consumption_rate (1.0)
        BurnCheck --> SpreadAttempt : Fuel > min_fuel_value (0.1)
        BurnCheck --> BurnComplete : Fuel ≤ min_fuel_value
        SpreadAttempt --> EmberGeneration
        EmberGeneration --> ContinueBurning
        ContinueBurning --> ActiveCombustion
        BurnComplete --> [*]
    }
    
    Burning --> Burned : Fuel exhausted
    
    state Burned {
        [*] --> Complete
        Complete --> [*]
    }
    
    Burned --> [*] : Final state
```

### 4.3 Simulation Parameters & Settings

| Category | Parameter | Default Value | Range | Impact |
|----------|-----------|---------------|-------|--------|
| **Fire Physics** | spread_probability | 0.4 | 0.1 - 0.8 | Base probability for spread calculation |
| | ignition_threshold | 0.5 | 0.1 - 1.0 | **Deterministic threshold for ignition** |
| | fuel_consumption_rate | 1.0 | 0.1 - 2.0 | Fixed fuel consumed per timestep |
| | wind_influence_on_spread | 0.5 | 0.0 - 1.0 | Wind effect amplification factor |
| | slope_influence | 0.3 | 0.0 - 1.0 | Topographic influence factor |
| **Environment** | min_fuel_value | 0.1 | 0.01 - 1.0 | Minimum fuel for burning |
| | fuel_moisture_baseline | 0.3 | 0.0 - 0.8 | Base fuel moisture content |
| | initial_fuel_load | 0.0 | 0.0 - 10.0 | Default fuel per cell |
| **Terrain** | barranco_amplification | 2.0 | 1.0 - 5.0 | Canyon wind amplification |
| | terrain_effect_strength | 0.6 | 0.0 - 1.0 | Overall terrain influence |
| **Transport** | ember_probability | 0.1 | 0.01 - 0.25 | Ember generation probability |
| | ember_distance | 5 cells | 2 - 15 cells | Maximum ember travel distance |
| | ember_ignition | 0.3 | 0.1 - 0.8 | Ember ignition probability |
| **Simulation** | max_steps | 20 | 10 - 1000 | Simulation duration |
| | num_layers | 10 | 5 - 25 | Vertical resolution (capped at 25) |

---

## 5. HPC Deployment & Scaling

### 5.1 HPC Deployment Pipeline

```mermaid
flowchart TD
    subgraph "Development Environment"
        LOCAL["Local Development<br/>Testing & debugging"]
        VALID["Configuration Validation<br/>Parameter verification"]
        TEST["Small-scale Testing<br/>Performance validation"]
    end
    
    subgraph "HPC Preparation"
        SLURM["SLURM Job Script<br/>32 cores, 32-128GB memory"]
        MODULE["Module Loading<br/>Python/3.11.3, GDAL/3.7.1, GEOS/3.12.0"]
        CONFIG["Environment Variables<br/>GDAL optimization, NUMEXPR threading"]
    end
    
    subgraph "Resource Allocation"
        NODES["Node Selection<br/>CPU & memory requirements"]
        MEMORY["Memory Planning<br/>Tile size optimization"]
        PARALLEL["Parallelization<br/>Worker distribution"]
    end
    
    subgraph "Job Execution"
        SUBMIT["Job Submission<br/>Queue management"]
        MONITOR["Progress Monitoring<br/>Resource utilization"]
        MANAGE["Job Management<br/>Error handling"]
    end
    
    subgraph "Production Processing"
        LARGE["Large-scale Simulation<br/>Full resolution processing"]
        BATCH["Batch Processing<br/>Multiple scenarios"]
        OPTIM["Performance Optimization<br/>Resource efficiency"]
    end
    
    subgraph "Results Management"
        COLLECT["Results Collection<br/>Output aggregation"]
        TRANSFER["Data Transfer<br/>Storage & archiving"]
        CLEANUP["Resource Cleanup<br/>Temporary file removal"]
    end
    
    %% Process flow
    LOCAL --> VALID
    VALID --> TEST
    TEST --> SLURM
    
    SLURM --> MODULE
    MODULE --> CONFIG
    CONFIG --> NODES
    
    NODES --> MEMORY
    MEMORY --> PARALLEL
    PARALLEL --> SUBMIT
    
    SUBMIT --> MONITOR
    MONITOR --> MANAGE
    MANAGE --> LARGE
    
    LARGE --> BATCH
    BATCH --> OPTIM
    OPTIM --> COLLECT
    
    COLLECT --> TRANSFER
    TRANSFER --> CLEANUP
    
    %% Feedback loops
    TEST --> LOCAL
    MANAGE --> SUBMIT
    OPTIM --> MEMORY
    
    %% Styling
    classDef dev fill:#e8eaf6
    classDef prep fill:#e0f2f1
    classDef resource fill:#fff3e0
    classDef exec fill:#fce4ec
    classDef prod fill:#f3e5f5
    classDef results fill:#e1f5fe
    
    class LOCAL,VALID,TEST dev
    class SLURM,MODULE,CONFIG prep
    class NODES,MEMORY,PARALLEL resource
    class SUBMIT,MONITOR,MANAGE exec
    class LARGE,BATCH,OPTIM prod
    class COLLECT,TRANSFER,CLEANUP results
```

### 5.2 HPC Resource Scaling

```mermaid
graph LR
    subgraph "Local Setup"
        S1["Grid: 100×100×10"]
        S2["Memory: 2GB"]
        S3["Cores: 4"]
        S4["Time: 20 min"]
        S1 --> S2 --> S3 --> S4
    end
    
    subgraph "HPC Sensitivity Analysis"
        H1["Grid: 120×120×8"]
        H2["Memory: 32GB"]
        H3["Cores: 32 (28 workers)"]
        H4["Time: 20-30 min"]
        H1 --> H2 --> H3 --> H4
    end
    
    subgraph "HPC Production"
        P1["Grid: Production scale"]
        P2["Memory: 128GB"]
        P3["Cores: 32"]
        P4["Time: Variable"]
        P1 --> P2 --> P3 --> P4
    end
    
    subgraph "Performance Scaling"
        SCALE["Scaling Factors<br/>Grid: 10000x larger<br/>Memory: 25x larger<br/>Cores: 8x more<br/>Speed: 6x faster"]
    end
    
    S4 --> H1
    H4 --> P1
    P4 --> SCALE
    
    %% Styling
    classDef standard fill:#e3f2fd
    classDef hpc fill:#e8f5e8
    classDef production fill:#fff3e0
    classDef scaling fill:#fce4ec
    
    class S1,S2,S3,S4 standard
    class H1,H2,H3,H4 hpc
    class P1,P2,P3,P4 production
    class SCALE scaling
```

### 5.3 HPC Configuration Specifications

| Configuration | Grid Size | Memory | CPU Cores | Typical Runtime | Use Case |
|---------------|-----------|--------|-----------|-----------------|----------|
| **Local Testing** | 100×100×10 | 1-2GB | 4 | 10-20 min | Development, debugging |
| **Small Production** | 600×600×25 | 8-16GB | 8 | 30-45 min | Quick analysis, validation |
| **HPC Sensitivity** | 120×120×8 | 32GB | 32 (28 workers) | 20-30 min | Parameter analysis |
| **HPC Production** | Configurable | 128GB | 32 | Variable | Production simulations |
| **Tenerife Scale** | 15121×24741×25 | 128GB | 32 | Variable | Full island studies |

---

## 6. Analysis & Visualization Pipeline

### 6.1 Visualization System Architecture

```mermaid
graph TB
    subgraph DATASRC ["📊 DATA SOURCES"]
        direction TB
        SIM[("🔥 Simulation Results<br/><small>State progression & dynamics</small>")]
        GEO[("🗺️ Geospatial Data<br/><small>Terrain & geographic boundaries</small>")]
        META[("⚙️ Metadata<br/><small>Parameters & configuration</small>")]
    end
    
    subgraph MATPLOT ["📈 MATPLOTLIB VISUALIZATION"]
        direction TB
        PLOT2D["📊 2D Plotting<br/><small>Fire state heat maps</small>"]
        PLOT3D["🎯 3D Plotting<br/><small>Volumetric fire views</small>"]
        CMAP["🎨 Custom Colormaps<br/><small>Fire intensity themes</small>"]
    end
    
    subgraph ANIMATION ["🎬 ANIMATION SYSTEM"]
        direction TB
        ANIMATE["🎥 Animation Engine<br/><small>FuncAnimation framework</small>"]
        FRAMES["📸 Frame Generator<br/><small>PNG/JPG sequences</small>"]
        GIF["📱 GIF Export<br/><small>Compressed animations</small>"]
    end
    
    subgraph ANALYSIS ["🔬 ANALYSIS TOOLS"]
        direction TB
        SPATIAL["🗺️ Spatial Analysis<br/><small>Fire patterns & metrics</small>"]
        TEMPORAL["⏱️ Temporal Analysis<br/><small>Time-series statistics</small>"]
        COMPARE["⚖️ Comparison Tools<br/><small>Multi-scenario analysis</small>"]
    end
    
    subgraph EXPORT ["💾 EXPORT & INTEGRATION"]
        direction TB
        PICKLE["🐍 Pickle Export<br/><small>Python serialization</small>"]
        IMAGES["🖼️ Image Export<br/><small>High-res static outputs</small>"]
        JSON["📋 JSON Export<br/><small>Structured metadata</small>"]
    end
    
    subgraph OUTPUT ["📁 FILE OUTPUT"]
        direction TB
        HISTORY["📚 Simulation History<br/><small>Complete timestep archive</small>"]
        RESULTS["📄 Results Summary<br/><small>Final state & statistics</small>"]
        LOGS["📝 Log Files<br/><small>Execution tracking</small>"]
    end
    
    %% Enhanced data flow with different line styles
    SIM ==>|"Real-time data"| PLOT2D
    GEO ==>|"Spatial context"| PLOT3D
    META ==>|"Style parameters"| CMAP
    
    PLOT2D ==>|"2D renders"| ANIMATE
    PLOT3D ==>|"3D frames"| FRAMES
    CMAP ==>|"Styled plots"| GIF
    
    ANIMATE -.->|"Animation data"| SPATIAL
    FRAMES -.->|"Frame sequences"| TEMPORAL
    GIF -.->|"Comparison sets"| COMPARE
    
    SPATIAL ==>|"Analysis results"| PICKLE
    TEMPORAL ==>|"Time series"| IMAGES
    COMPARE ==>|"Comparative data"| JSON
    
    PICKLE ==>|"Archived data"| HISTORY
    IMAGES ==>|"Visual outputs"| RESULTS
    JSON ==>|"Structured logs"| LOGS
    
    %% Modern styling with enhanced colors and contrast
    classDef dataStyle fill:#E8EAF6,stroke:#3F51B5,stroke-width:3px,color:#1A237E
    classDef vizStyle fill:#E0F2F1,stroke:#009688,stroke-width:3px,color:#004D40
    classDef animStyle fill:#FFF3E0,stroke:#FF9800,stroke-width:3px,color:#E65100
    classDef analysisStyle fill:#FCE4EC,stroke:#E91E63,stroke-width:3px,color:#880E4F
    classDef exportStyle fill:#F3E5F5,stroke:#9C27B0,stroke-width:3px,color:#4A148C
    classDef outputStyle fill:#E1F5FE,stroke:#03A9F4,stroke-width:3px,color:#01579B
    
    class SIM,GEO,META dataStyle
    class PLOT2D,PLOT3D,CMAP vizStyle
    class ANIMATE,FRAMES,GIF animStyle
    class SPATIAL,TEMPORAL,COMPARE analysisStyle
    class PICKLE,IMAGES,JSON exportStyle
    class HISTORY,RESULTS,LOGS outputStyle
```

### 6.2 Visualization Output Types

```mermaid
graph TB
    ROOT["🎨 VISUALIZATION OUTPUTS<br/><small>Comprehensive output portfolio</small>"]
    
    subgraph STATIC ["📊 STATIC VISUALIZATIONS"]
        direction TB
        FIREMAPS["🗺️ 2D Fire Maps"]
        RENDERS3D["🏞️ 3D Static Renders"]
        STATPLOTS["📈 Statistical Plots"]
        
        FIREMAPS --> BURNPROG["🔥 Burn Progression Maps<br/><small>Temporal fire spread</small>"]
        FIREMAPS --> EXTENTOV["🎯 Final Extent Overlays<br/><small>Boundary visualization</small>"]
        FIREMAPS --> INTMAPS["🌡️ Intensity Heat Maps<br/><small>Fire severity mapping</small>"]
        
        RENDERS3D --> TERRVIEW["🏔️ Terrain Perspective Views<br/><small>3D landscape context</small>"]
        RENDERS3D --> VERTSTRUC["📏 Vertical Fire Structure<br/><small>Height profiling</small>"]
        RENDERS3D --> MULTIANGLE["🎬 Multi-angle Composites<br/><small>Comprehensive views</small>"]
        
        STATPLOTS --> SPREADRATE["📊 Spread Rate Curves<br/><small>Temporal analysis</small>"]
        STATPLOTS --> PARAMSENS["⚖️ Parameter Sensitivity<br/><small>Model analysis</small>"]
        STATPLOTS --> VALIDATION["✅ Validation Comparisons<br/><small>Accuracy assessment</small>"]
    end
    
    subgraph DYNAMIC ["🎬 DYNAMIC VISUALIZATIONS"]
        direction TB
        REALTIME["⚡ Real-time 3D"]
        ANIMATIONS["📱 Animation Sequences"]
        INTERACTIVE["🌐 Interactive Web"]
        
        REALTIME --> NAVIGATION["🧭 Interactive Navigation<br/><small>User-controlled views</small>"]
        REALTIME --> PARAMS["⚙️ Parameter Adjustment<br/><small>Live model tuning</small>"]
        REALTIME --> SCENARIOS["🔄 Multi-scenario Comparison<br/><small>Comparative analysis</small>"]
        
        ANIMATIONS --> MOVIES["🎥 Fire Progression Movies<br/><small>Animated sequences</small>"]
        ANIMATIONS --> TIMELAPSE["⏰ Time-lapse Evolution<br/><small>Compressed timeline</small>"]
        ANIMATIONS --> MULTIPERSP["📐 Multi-perspective Views<br/><small>Different viewpoints</small>"]
        
        INTERACTIVE --> BROWSERS["🌍 Browser-based Viewers<br/><small>Web accessibility</small>"]
        INTERACTIVE --> EMBEDDED["🔗 Embedded Visualizations<br/><small>Platform integration</small>"]
        INTERACTIVE --> COLLAB["👥 Collaborative Analysis<br/><small>Team-based review</small>"]
    end
    
    subgraph ANALYTICAL ["🔬 ANALYTICAL OUTPUTS"]
        direction TB
        GISINTEG["🗺️ GIS Integration"]
        RESEARCH["📄 Research Deliverables"]
        VALREPORTS["📋 Validation Reports"]
        
        GISINTEG --> QGIS["🎯 QGIS Project Files<br/><small>Open-source compatibility</small>"]
        GISINTEG --> ARCGIS["🏢 ArcGIS Compatibility<br/><small>Enterprise integration</small>"]
        GISINTEG --> SHAPES["📁 Shapefile Exports<br/><small>Standard GIS format</small>"]
        
        RESEARCH --> PUBFIGS["📚 Publication Figures<br/><small>Academic papers</small>"]
        RESEARCH --> PRESENTATIONS["🎤 Presentation Materials<br/><small>Conference content</small>"]
        RESEARCH --> DOCGRAPHICS["📖 Documentation Graphics<br/><small>Technical documentation</small>"]
        
        VALREPORTS --> ACCURACY["🎯 Accuracy Assessments<br/><small>Model performance</small>"]
        VALREPORTS --> PERFMETRICS["📊 Performance Metrics<br/><small>System benchmarks</small>"]
        VALREPORTS --> CALIBRESULTS["⚙️ Calibration Results<br/><small>Parameter optimization</small>"]
    end
    
    ROOT --> STATIC
    ROOT --> DYNAMIC  
    ROOT --> ANALYTICAL
    
    %% Enhanced styling
    classDef rootStyle fill:#4A90E2,stroke:#2E5C8A,stroke-width:4px,color:white
    classDef categoryStyle fill:#7ED321,stroke:#5BA517,stroke-width:3px,color:#2D4A0B
    classDef subcatStyle fill:#F5A623,stroke:#C7851A,stroke-width:2px,color:#8B4513
    classDef itemStyle fill:#E3F2FD,stroke:#2196F3,stroke-width:2px,color:#0D47A1
    
    class ROOT rootStyle
    class FIREMAPS,RENDERS3D,STATPLOTS,REALTIME,ANIMATIONS,INTERACTIVE,GISINTEG,RESEARCH,VALREPORTS categoryStyle
    class BURNPROG,EXTENTOV,INTMAPS,TERRVIEW,VERTSTRUC,MULTIANGLE,SPREADRATE,PARAMSENS,VALIDATION,NAVIGATION,PARAMS,SCENARIOS,MOVIES,TIMELAPSE,MULTIPERSP,BROWSERS,EMBEDDED,COLLAB,QGIS,ARCGIS,SHAPES,PUBFIGS,PRESENTATIONS,DOCGRAPHICS,ACCURACY,PERFMETRICS,CALIBRESULTS itemStyle
```

### 6.3 Analysis & Export Specifications

| Output Type | Format | Resolution | Purpose | Generation Time |
|-------------|--------|------------|---------|-----------------|
| **Fire State Maps** | PNG, JPG | Matplotlib default | Fire progression visualization | 1-5 seconds |
| **Simulation Data** | Python Pickle (.pkl) | Native arrays | Data persistence & analysis | 2-10 seconds |
| **Animations** | GIF (via imageio) | Variable | Process visualization | 30-180 seconds |
| **Metadata** | JSON | Text | Configuration & statistics | <1 second |
| **History Files** | Pickle (.pkl) | Timestep arrays | Complete simulation history | 5-60 seconds |
| **Log Files** | Text (.log, .txt) | Text | Execution tracking & debugging | Continuous |
| **Statistical Data** | JSON, Text | Structured data | Analysis metrics | 1-2 seconds |
| **Terrain Data** | NumPy (.npy) | Native grid | Preprocessed terrain arrays | 10-30 seconds |

---

## 7. Validation & Research Integration

### 7.1 Validation Framework

```mermaid
flowchart TB
    subgraph "Historical Data"
        EMSR[("EMSR Fire Perimeters<br/>Satellite-derived boundaries")]
        DATES[("Fire Event Dates<br/>Temporal progression")]
        WEATHER[("Historical Weather<br/>Wind & conditions")]
    end
    
    subgraph "Simulation Preparation"
        SETUP["Simulation Setup<br/>Historical conditions"]
        IGNITE["Ignition Point Selection<br/>Known fire origins")]
        PARAMS["Parameter Application<br/>Calibrated values")]
    end
    
    subgraph "Validation Simulation"
        RUN["Historical Simulation<br/>Reproduce known fires"]
        TRACK["Progress Tracking<br/>Compare with observations")]
        RECORD["Result Recording<br/>Detailed metrics collection")]
    end
    
    subgraph "Accuracy Assessment"
        SPATIAL["Spatial Accuracy<br/>Boundary comparison"]
        TEMPORAL["Temporal Accuracy<br/>Progression timing"]
        BEHAVIOR["Behavior Accuracy<br/>Spread patterns & rates")]
    end
    
    subgraph "Statistical Analysis"
        METRICS["Similarity Metrics<br/>Jaccard, Dice, Hausdorff"]
        STATS["Statistical Tests<br/>Significance assessment"]
        CONF["Confidence Intervals<br/>Uncertainty quantification")]
    end
    
    subgraph "Validation Results"
        REPORT[("Validation Report<br/>Comprehensive assessment")]
        IMPROVE[("Model Improvements<br/>Parameter refinements")]
        PUBLISH[("Research Publications<br/>Scientific documentation")]
    end
    
    %% Process flow
    EMSR --> SETUP
    DATES --> IGNITE
    WEATHER --> PARAMS
    
    SETUP --> RUN
    IGNITE --> TRACK
    PARAMS --> RECORD
    
    RUN --> SPATIAL
    TRACK --> TEMPORAL
    RECORD --> BEHAVIOR
    
    SPATIAL --> METRICS
    TEMPORAL --> STATS
    BEHAVIOR --> CONF
    
    METRICS --> REPORT
    STATS --> IMPROVE
    CONF --> PUBLISH
    
    %% Feedback loops
    IMPROVE --> PARAMS
    REPORT --> SETUP
    
    %% Styling
    classDef historical fill:#e8eaf6
    classDef prep fill:#e0f2f1
    classDef sim fill:#fff3e0
    classDef assess fill:#fce4ec
    classDef stats fill:#f3e5f5
    classDef results fill:#e1f5fe
    
    class EMSR,DATES,WEATHER historical
    class SETUP,IGNITE,PARAMS prep
    class RUN,TRACK,RECORD sim
    class SPATIAL,TEMPORAL,BEHAVIOR assess
    class METRICS,STATS,CONF stats
    class REPORT,IMPROVE,PUBLISH results
```

### 7.2 EMSR Data Integration Implementation

#### 7.2.1 EMSR Fire Perimeter Discovery

**Auto-Discovery System**:
- **Directory Structure**: Scans `EMSR Delineations/` with day-organized folders
- **File Recognition**: Identifies `.shp` files with EMSR naming conventions
- **Multi-Day Support**: Handles temporal progression (Day 1-4 for Tenerife 2023 fire)
- **Path Flexibility**: HPC and local directory fallbacks

**Discovery Process**:
1. **Directory Scanning**: Parse day directories (`Day 1 (18_08_23)`, etc.)
2. **Date Extraction**: Extract dates and day numbers from folder names
3. **Shapefile Location**: Find fire perimeter shapefiles within each day
4. **Metadata Extraction**: Read fire ID, CRS, and geometry information
5. **Validation**: Verify spatial data integrity and completeness

#### 7.2.2 Historical Fire Data Processing

**Spatial Processing**:
- **CRS Standardization**: Convert all data to EPSG:25828 (Tenerife UTM Zone 28N)
- **Grid Alignment**: Rasterize to full Tenerife domain (15,121 × 24,741 × 5m resolution)
- **Area Calculation**: Compute fire areas in hectares for validation metrics
- **Bounds Verification**: Ensure fire perimeters fit within simulation domain

**Temporal Processing**:
- **Training/Test Split**: Days 1-2 for training, Days 3-4 for testing
- **Progression Tracking**: Model temporal fire growth patterns
- **Multiple Targets**: Support multiple fire events within calibration

**Implementation Parameters**:
- Grid Resolution: 5m × 5m cells
- Domain Size: 75.6km × 123.7km (full Tenerife)
- Memory Requirements: 64-128GB for full-domain processing
- Processing Time: 15-30 minutes per fire perimeter

#### 7.2.3 Calibration Target Generation

**Spatial Similarity Metrics**:
- **Jaccard Index**: Intersection over union of burned areas
- **Dice Coefficient**: 2 × overlap / (area1 + area2)  
- **Sorensen Coefficient**: Alternative similarity measure
- **Hausdorff Distance**: Maximum boundary separation distance

**Objective Function Weights**:
- Spatial Similarity: 60%
- Fire Behavior: 40%
- Component breakdown: Jaccard (40%), Dice (30%), Sorensen (30%)

### 7.3 Research Pipeline Integration

```mermaid
sequenceDiagram
    participant Data as Data Collection
    participant Model as Model Development
    participant Calib as Calibration
    participant Valid as Validation
    participant Research as Research Output
    participant Publish as Publication
    
    Note over Data,Publish: Research Integration Workflow
    
    Data->>Model: Provide LiDAR & terrain data
    activate Model
    Model->>Model: Develop simulation framework
    Model->>Calib: Initial model version
    deactivate Model
    
    activate Calib
    Calib->>Calib: Parameter optimization
    Calib->>Valid: Calibrated model
    deactivate Calib
    
    activate Valid
    Valid->>Valid: Historical validation
    Valid->>Valid: Accuracy assessment
    
    alt Validation Successful
        Valid->>Research: Validated model
        Note right of Valid: Proceed to research applications
    else Validation Failed
        Valid->>Calib: Refinement needed
        Note right of Valid: Iterate calibration
    end
    deactivate Valid
    
    activate Research
    Research->>Research: Scientific analysis
    Research->>Research: Case study applications
    Research->>Research: Results documentation
    Research->>Publish: Research findings
    deactivate Research
    
    activate Publish
    Publish->>Publish: Manuscript preparation
    Publish->>Publish: Peer review process
    Publish->>Data: Publication & data sharing
    deactivate Publish
    
    Note over Data,Publish: Continuous improvement cycle
```

### 7.3 Validation Metrics & Benchmarks

| Metric Category | Measure | Acceptable Range | Excellent Performance | Purpose |
|----------------|---------|------------------|----------------------|---------|
| **Spatial Similarity** | Jaccard Index | 0.60 - 0.75 | > 0.80 | Boundary accuracy |
| | Dice Coefficient | 0.70 - 0.85 | > 0.90 | Shape similarity |
| | Hausdorff Distance | < 100m | < 50m | Boundary precision |
| **Temporal Accuracy** | Progression Correlation | 0.70 - 0.85 | > 0.90 | Time evolution |
| | Peak Spread Time | ±2 hours | ±1 hour | Critical timing |
| **Fire Behavior** | Final Area Ratio | 0.80 - 1.20 | 0.90 - 1.10 | Total extent |
| | Spread Rate Correlation | 0.60 - 0.80 | > 0.85 | Velocity accuracy |
| **Statistical** | R² Correlation | 0.70 - 0.85 | > 0.90 | Overall fit |
| | RMSE (normalized) | < 0.30 | < 0.20 | Prediction error |

---

## 8. System Integration & Data Flow

### 8.1 Complete System Data Flow

```mermaid
graph TB
    subgraph "Data Sources & Inputs"
        L[("LiDAR Data")]
        D[("DEM/DTM")]
        E[("EMSR Data")]
        W[("Weather Data")]
        C[("Configuration")]
    end
    
    subgraph "Preprocessing Layer"
        P1["LiDAR Processing"]
        P2["Terrain Analysis"]
        P3["Historical Analysis"]
        P1 --> P2
        P2 --> P3
    end
    
    subgraph "Model Development"
        M1["Model Configuration"]
        M2["Parameter Definition"]
        M3["Calibration Setup"]
        M1 --> M2 --> M3
    end
    
    subgraph "Calibration & Optimization"
        O1["Grid Search"]
        O2["Sensitivity Analysis"]
        O3["Parameter Selection"]
        O1 --> O2 --> O3
    end
    
    subgraph "Simulation Engine"
        S1["3D Model Setup"]
        S2["Fire Physics"]
        S3["State Evolution"]
        S1 --> S2 --> S3
    end
    
    subgraph "Deployment & Scaling"
        D1["Local Testing"]
        D2["HPC Deployment"]
        D3["Production Scaling"]
        D1 --> D2 --> D3
    end
    
    subgraph "Analysis & Visualization"
        V1["3D Visualization"]
        V2["Statistical Analysis"]
        V3["Export Generation"]
        V1 --> V2 --> V3
    end
    
    subgraph "Validation & Research"
        R1["Historical Validation"]
        R2["Accuracy Assessment"]
        R3["Research Documentation"]
        R1 --> R2 --> R3
    end
    
    %% Data flow connections
    L --> P1
    D --> P2
    E --> P3
    W --> S2
    C --> M1
    
    P3 --> M3
    M3 --> O1
    O3 --> S1
    S3 --> D1
    D3 --> V1
    V3 --> R1
    
    %% Feedback loops
    R2 --> O1
    V2 --> M2
    D2 --> S1
    
    %% Inter-layer connections
    P2 --> S1
    O3 --> D1
    S3 --> V1
    
    %% Styling
    classDef input fill:#e3f2fd
    classDef process fill:#f1f8e9
    classDef model fill:#fff3e0
    classDef optim fill:#fce4ec
    classDef sim fill:#f3e5f5
    classDef deploy fill:#e1f5fe
    classDef viz fill:#e8f5e8
    classDef research fill:#fff8e1
    
    class L,D,E,W,C input
    class P1,P2,P3 process
    class M1,M2,M3 model
    class O1,O2,O3 optim
    class S1,S2,S3 sim
    class D1,D2,D3 deploy
    class V1,V2,V3 viz
    class R1,R2,R3 research
```

### 8.2 Integration Points & Dependencies

```mermaid
graph LR
    subgraph "Critical Dependencies"
        CD1["LiDAR → PAD → Simulation"]
        CD2["EMSR → Calibration → Validation"]
        CD3["Parameters → HPC → Production"]
    end
    
    subgraph "Optional Dependencies"
        OD1["Weather → Simulation (Enhanced)"]
        OD2["Terrain → Visualization (Context)"]
        OD3["Metadata → Documentation (Complete)"]
    end
    
    subgraph "Feedback Loops"
        FL1["Validation → Calibration (Refinement)"]
        FL2["HPC Performance → Memory Management (Optimization)"]
        FL3["Visualization → Analysis (Insights)"]
    end
    
    CD1 --> CD2
    CD2 --> CD3
    
    OD1 -.-> CD1
    OD2 -.-> CD3
    OD3 -.-> FL3
    
    FL1 --> CD2
    FL2 --> CD3
    FL3 --> CD1
    
    %% Styling
    classDef critical fill:#ffcdd2
    classDef optional fill:#c8e6c9
    classDef feedback fill:#fff3c4
    
    class CD1,CD2,CD3 critical
    class OD1,OD2,OD3 optional
    class FL1,FL2,FL3 feedback
```

### 8.3 System Performance & Scaling Summary

| System Component | Local Performance | HPC Performance | Scaling Factor | Bottlenecks |
|------------------|------------------|-----------------|----------------|-------------|
| **Data Preprocessing** | 1-2 hours | 15-30 minutes | 4-8x | I/O bandwidth |
| **Calibration** | 8-12 hours | 45-90 minutes | 8-16x | Parameter space size |
| **Simulation (Small)** | 20-40 minutes | 5-15 minutes | 4-8x | Memory allocation |
| **Simulation (Large)** | 4-8 hours | 1-3 hours | 4-6x | Grid complexity |
| **Visualization** | Real-time | Real-time | 1x | Graphics hardware |
| **Analysis** | 10-30 minutes | 2-8 minutes | 5-15x | Statistical computation |
| **Overall Pipeline** | 12-24 hours | 2-6 hours | 6-12x | Dependencies & I/O |

---

## Conclusion

This comprehensive workflow documentation presents a complete forest fire simulation framework designed for research applications in complex terrain environments. The framework integrates multiple sophisticated components:

1. **Advanced Data Processing**: LiDAR-derived vegetation structure analysis with terrain-aware preprocessing
2. **Rigorous Calibration**: Multi-method parameter optimization with historical fire validation  
3. **Deterministic Fire Physics**: 3D fire simulation with threshold-based ignition and efficient memory management
4. **Comprehensive Analysis**: Multi-format visualization and statistical analysis tools
5. **Research Integration**: Validation workflows and publication-ready documentation

The modular design allows for flexible application across different research contexts while maintaining scientific rigor through calibration and validation against historical fire events. The HPC deployment capability enables large-scale studies while the interactive visualization system supports detailed analysis and communication of results.

This framework provides a solid foundation for advancing fire behavior research and supports the development of improved fire management strategies through accurate, validated simulations of fire behavior in complex natural environments.

---

*This document serves as the comprehensive workflow guide for the forest fire simulation framework developed as part of ongoing research into fire behavior modeling and prediction.*
