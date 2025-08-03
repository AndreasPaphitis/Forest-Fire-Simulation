# Git Best Practices for LiDAR/GIS Projects

## 🚫 Never Track These File Types
- **LiDAR Data**: `*.las`, `*.laz`, `*.tif`, `*.tiff`
- **Large Datasets**: `*.h5`, `*.hdf5`, `*.nc`, `*.csv` (if >1MB)
- **Results/Output**: Anything in `results/`, `output/`, `calibration_results/`, `test_output/`
- **Temporary Files**: `*.tmp`, `*.temp`, `__pycache__/`, `*.log`

## ✅ What TO Track
- **Source Code**: `*.py`, `*.sh`, `*.slurm`
- **Small Config Files**: `*.json`, `*.yaml`, `*.txt` (<1MB)
- **Documentation**: `*.md`, `README` files
- **Requirements**: `requirements.txt`, `environment.yml`

## 🔧 Commands to Use Before Committing

### Check What's Staged
```bash
git status --porcelain
```

### Check File Sizes
```bash
git ls-files --cached | ForEach-Object { $size = (Get-Item $_).Length; if ($size -gt 100KB) { Write-Output "$_`: $([math]::Round($size/1KB, 1)) KB" } }
```

### Remove Large Files from Staging
```bash
git reset HEAD path/to/large/file
# or remove from tracking entirely:
git rm --cached path/to/large/file
```

## 🎯 Git LFS Setup (Already Done)
For legitimate large files that need version control:
```bash
git lfs install
git lfs track "*.tif" "*.las" "*.h5"
git add .gitattributes
```

## 📁 Directory Structure Rules
- **data/**: Always ignored (raw datasets)
- **results/**: Always ignored (analysis outputs) 
- **src/**: Track all code files
- **config/**: Track small configs, ignore large parameter sweeps
- **docs/**: Track all documentation

## 🚨 Emergency: Remove Large Files from History
If you accidentally commit large files:
```bash
# Remove from last commit only
git reset --soft HEAD~1
git reset HEAD path/to/large/file
git commit

# For files deep in history (use with caution)
git filter-branch --force --index-filter 'git rm --cached --ignore-unmatch path/to/large/file' --prune-empty --tag-name-filter cat -- --all
```

## 💡 Daily Workflow
1. `git status` - Check what's changed
2. `git add` - Only add intended files
3. `git status` again - Verify before commit
4. Check file sizes if unsure
5. `git commit` - Commit clean code only