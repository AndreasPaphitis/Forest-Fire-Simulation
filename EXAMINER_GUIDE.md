# Examiner Guide - Wildfire Model Research

## 🎯 Research Overview
This repository contains a complete wildfire simulation framework integrating LiDAR data with cellular automata modeling, applied to the 2023 Tenerife wildfire.

## 📁 Directory Structure (Clean & Navigable)

```
wildfire-model/
├── wildfire_model/           # 🐍 Main Python package (clean code)
│   ├── core/                # Fire simulation engine
│   ├── preprocessing/        # LiDAR & terrain processing  
│   ├── calibration/         # Model calibration
│   ├── validation/          # Model validation
│   ├── visualization/       # Plotting & animation
│   └── utils/              # Helper functions
├── data/                    # 📊 Research data
│   ├── raw/                # Original data (LiDAR, terrain, fire perimeters)
│   └── processed/          # Analysis-ready data
├── results/                 # 📈 Research outputs
│   ├── calibration/        # Calibration results
│   ├── validation/         # Validation results  
│   ├── figures/            # Generated figures
│   └── tables/             # Generated tables
├── scripts/                 # 🔧 Workflow scripts
│   ├── preprocessing/      # Data processing scripts
│   ├── calibration/        # Calibration scripts
│   ├── validation/         # Validation scripts
│   └── analysis/           # Analysis scripts
├── docs/                    # 📚 Documentation
│   ├── guides/             # User guides
│   └── methodology/        # Research methodology
└── tests/                   # 🧪 Test suite
```

## 🔬 Key Research Components

### 1. **Core Model** (`wildfire_model/core/`)
- 3D cellular automata fire spread
- Horizontal, vertical, and ember spread mechanisms
- Real-time fire progression simulation

### 2. **LiDAR Integration** (`wildfire_model/preprocessing/`)
- Point cloud processing and normalization
- Vegetation structure analysis
- Plant Area Density (PAD) derivation

### 3. **Model Calibration** (`wildfire_model/calibration/`)
- Sensitivity analysis framework
- Grid search optimization
- Multi-objective parameter estimation

### 4. **Validation Framework** (`wildfire_model/validation/`)
- Temporal split-sample validation
- Spatial accuracy metrics (Dice, Area Ratio)
- Mechanistic validation metrics

## 📊 Key Results to Review

### Calibration Results
- **Location:** `results/calibration/`
- **Key Files:** 
  - `ultra_clean_calibration_*.json` - Calibration results
  - `sensitivity_analysis_*.json` - Parameter sensitivity

### Validation Results  
- **Location:** `results/validation/`
- **Key Files:**
  - `validation_results_summary.json` - Validation metrics
  - `final/` - Final validation results

### Generated Figures
- **Location:** `results/figures/thesis/`
- **Key Files:**
  - `Table_*.png` - Research tables
  - `Figure_*.png` - Research figures

## 🚀 Quick Start for Examiners

### 1. **Install Dependencies**
```bash
pip install -r requirements.txt
pip install -e .
```

### 2. **Run Basic Simulation**
```python
from wildfire_model import FireSimulation
sim = FireSimulation()
results = sim.run()
```

### 3. **View Results**
- Check `results/validation/final/` for validation metrics
- Review `results/figures/thesis/` for visual outputs
- Examine `results/calibration/` for parameter optimization

## 📋 Research Methodology

### Data Sources
- **LiDAR:** PNOA-IGN (0.5 pts/m² resolution)
- **Fire Perimeters:** Copernicus EMSR-665
- **Terrain:** IGN Digital Terrain Model
- **Study Area:** Tenerife, Canary Islands

### Validation Approach
1. **Temporal Split:** Calibrate on early fire progression, validate on later
2. **Spatial Accuracy:** Dice similarity and area ratio metrics
3. **Mechanistic Validation:** Vertical spread, ember contribution, spread efficiency

### Key Findings
- Model achieves good spatial accuracy (Dice > 0.6)
- Identifies parameter sensitivity hierarchy
- Reveals potential overfitting issues
- Provides mechanistic insights into fire behavior

## 🔍 Code Quality & Reproducibility

### FAIR Principles Compliance
- ✅ **Findable:** Clear structure, comprehensive documentation
- ✅ **Accessible:** Open source (MIT license), clear installation
- ✅ **Interoperable:** Standard formats, modular design
- ✅ **Reusable:** Well-documented, tested, examples provided

### Testing
- Unit tests: `tests/unit/`
- Integration tests: `tests/integration/`
- Run tests: `pytest tests/`

### Documentation
- API docs: Auto-generated from docstrings
- User guides: `docs/guides/`
- Methodology: `docs/methodology/`

## 📞 Contact
**Andreas Paphitis**  
Email: a.paphitis@student.uva.nl  
Institution: University of Amsterdam

---
*This guide provides a quick overview for examiners. For detailed technical documentation, see the individual module docstrings and `docs/` directory.*




















