# 📊 ESSENTIAL THESIS CHARTS & SCRIPTS

## 🎯 **COMPLETE LIST OF CHARTS AND THEIR SCRIPTS**

---

## 📈 **SENSITIVITY ANALYSIS CHARTS (5 Figures)**

### **Script:** `ensure_academic_standards_compliance.py`
**Run command:** `python ensure_academic_standards_compliance.py`

**Produces 5 charts:**
1. **Figure_01_Parameter_Sensitivity_Ranking** (.png & .pdf)
   - Horizontal bar chart ranking all 13 parameters by sensitivity index
   - Shows primary/secondary/tertiary tiers with color coding

2. **Figure_02_Top5_Parameters_Focus** (.png & .pdf)
   - Bar chart focusing on top 5 most sensitive parameters
   - Includes dominance annotation showing spread_probability is 8.7x more sensitive

3. **Figure_03_Sensitivity_Distribution_Analysis** (.png & .pdf)
   - Dual panel: (a) Box plots by tier, (b) Log scale ranking
   - Shows distribution patterns across sensitivity tiers

4. **Figure_04_Mechanistic_Parameter_Grouping** (.png & .pdf)
   - Groups parameters by fire behavior mechanism
   - Shows cumulative sensitivity by mechanism type

5. **Figure_05_Calibration_Priority_Matrix** (.png & .pdf)
   - Bubble chart showing calibration priority vs effort required
   - Log scale with priority zones marked

**Output location:** `Academic_Thesis_Charts/`

---

## 🗺️ **SPATIAL VALIDATION CHART (1 Figure)**

### **Script:** `create_figure19_correct_validation_data.py`
**Run command:** `python create_figure19_correct_validation_data.py`

**Produces 1 chart:**
6. **Figure_19_Spatial_Validation_Maps** (.png & .pdf)
   - Two-panel spatial comparison: Day 3 vs Day 4 validation
   - Shows simulation fire spread overlaid on EMSR observations
   - Includes validation metrics (Dice coefficient, spatial error, etc.)

**Output location:** `Academic_Thesis_Charts/`

---

## 🔄 **LIDAR PIPELINE CHART (1 Figure)**

### **Script:** `scripts/visualization/create_figure1_pipeline_focused.py`
**Run command:** `python scripts/visualization/create_figure1_pipeline_focused.py`

**Produces 1 chart:**
7. **Figure_06_LiDAR_Pipeline_Workflow** (.png & .pdf)
   - Six-panel workflow diagram showing LiDAR preprocessing steps
   - Panels: Point cloud → Height norm → NRD calc → PAD derivation → Efficiency → Volume reduction

**Output location:** `figures/` (but should be moved to `Academic_Thesis_Charts/`)

---

## 🚀 **QUICK GENERATION COMMANDS**

```bash
# Generate all sensitivity charts (Figures 1-5)
python ensure_academic_standards_compliance.py

# Generate spatial validation chart (Figure 19)
python create_figure19_correct_validation_data.py

# Generate LiDAR pipeline chart (Figure 6)
python scripts/visualization/create_figure1_pipeline_focused.py
```

---

## 📁 **EXPECTED OUTPUT FILES**

After running all scripts, you should have:

```
Academic_Thesis_Charts/
├── Figure_Sensitivity_Parameter_Ranking.png
├── Figure_Sensitivity_Parameter_Ranking.pdf
├── Figure_Top5_Parameters_Focus.png
├── Figure_Top5_Parameters_Focus.pdf
├── Figure_Sensitivity_Distribution_Analysis.png
├── Figure_Sensitivity_Distribution_Analysis.pdf
├── Figure_Mechanistic_Parameter_Grouping.png
├── Figure_Mechanistic_Parameter_Grouping.pdf
├── Figure_Calibration_Priority_Matrix.png
├── Figure_Calibration_Priority_Matrix.pdf
├── Figure_19_CORRECTED_Spatial_Validation_Maps.png
└── Figure_19_CORRECTED_Spatial_Validation_Maps.pdf

figures/
├── Figure1_LiDAR_Pipeline_Focused.png
└── Figure1_LiDAR_Pipeline_Focused.pdf
```

---

## ⚠️ **IMPORTANT NOTES**

1. **Dependencies:** Ensure these directories exist with data:
   - `FINAL VALIDATION RESULTS/` (for Figure 19)
   - `EMSR Delineations/` (for Figure 19)
   - `preprocessed_lidar/` (for LiDAR pipeline)
   - `preprocessed_terrain/` (for LiDAR pipeline)

2. **Academic Standards:** All scripts produce title-free, APA-compliant figures

3. **Formats:** Each figure generates both PNG (for viewing) and PDF (for thesis)

4. **Resolution:** All figures are 300 DPI publication quality

---

## 🎯 **SUMMARY**

**Total Charts:** 7 essential figures
**Total Scripts:** 3 scripts  
**Main Script:** `ensure_academic_standards_compliance.py` (produces 5/7 charts)
**All charts are thesis-ready with no titles!** ✅
