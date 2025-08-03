#!/usr/bin/env bash
###############################################################################
#  S N E L L I U S   Q U I C K‑S T A R T   C H E A T S H E E T  (BEGINNER)
#  ---------------------------------------------------------------------------
#  Copy‑paste one block at a time into your MobaXterm terminal. This is the
#  *simplest* path from “login” → “run a job”.
#
#  ┌──────────────────────────────────────────────────────────────────────┐
#  │  TOOLCHAIN  vs  REQUIREMENTS.TXT  (quick mental model)              │
#  ├──────────────────────────────────────────────────────────────────────┤
#  │ • TOOLCHAIN  = compilers + MPI + math libs provided by SURF via     │
#  │   `module load 2024  &&  module load foss/2024a` (or intel/…).      │
#  │   Think of this as the *operating system for scientists*.          │
#  │                                                                    │
#  │ • requirements.txt = *Python* packages you install into your own    │
#  │   virtual environment with `pip install -r requirements.txt`.       │
#  │   They sit *on top* of the toolchain and may contain C/CUDA wheels  │
#  │   that link against the toolchain.                                  │
#  │                                                                    │
#  │ Change toolchain  ➜  rebuild venv.                                  │
#  │ Update requirements.txt ➜  just rerun pip install.                  │
#  └──────────────────────────────────────────────────────────────────────┘
###############################################################################

###############################################################################
# 0.  L O G   I N
###############################################################################
ssh  user@snellius.surf.nl       # replace “user” with your SURF username

###############################################################################
# 1.  P R O J E C T   V A R I A B L E S   (edit once per project)
###############################################################################
export PROJECT=/project/SC1234          # ← your SURF project path
export PROJDIR=$PROJECT/myproject       # main folder for this research project
export SRCDIR=$PROJDIR/src              # where *one* Git repo will live
export VENVDIR=$HOME/venvs/myproject    # Python virtual‑env location
export STACKYEAR=2024                   # SURF software stack vintage
export TOOLCHAIN=foss/2024a             # compilers/MPI/math‑libs bundle

###############################################################################
# 2A.  F I R S T ‑ T I M E   S E T U P   (run *once*)
###############################################################################
module purge && module load $STACKYEAR && module load $TOOLCHAIN
mkdir -p "$SRCDIR"

git clone https://github.com/you/repo.git "$SRCDIR"

python -m venv "$VENVDIR"
source "$VENVDIR/bin/activate"
pip install --upgrade pip
pip install -r "$SRCDIR/requirements.txt"
deactivate

###############################################################################
# 2B.  A D D   A   N E W   R E P O  (reuse existing venv)
#      – e.g. you want to try different code without rebuilding everything.
###############################################################################
NEWPROJ=$PROJECT/otherproj        # adjust folder & repo URL
mkdir -p "$NEWPROJ/src"

git clone https://github.com/you/other‑repo.git "$NEWPROJ/src"

# If other‑repo needs *extra* Python libs, install them into the same venv:
module purge && module load $STACKYEAR && module load $TOOLCHAIN
source "$VENVDIR/bin/activate"
pip install -r "$NEWPROJ/src/requirements.txt"   # fast if mostly pure‑Python
# (for heavy wheels like PyTorch, wrap the pip line inside an interactive srun)
deactivate

###############################################################################
# 3.  Q U I C K   I N T E R A C T I V E   T E S T   (≤1 h, 16 cores)
###############################################################################
srun -p rome -c 16 -t 1:00:00 --pty bash -c '
  module purge && module load '"$STACKYEAR"' && module load '"$TOOLCHAIN"'
  source '"$VENVDIR"'/bin/activate
  cd $TMPDIR                     # fast local SSD; wiped after job ends
  cp -r '"$SRCDIR"' .            # replace with "$NEWPROJ/src" to test new repo
  python src/myepicprogram.py --steps 100
'

###############################################################################
# 4.  B A T C H   J O B   S C R I P T   (save, then sbatch)
###############################################################################
cat > "$PROJDIR/run.slurm" <<EOF
#!/bin/bash
#SBATCH -J myjob
#SBATCH -p rome
#SBATCH -c 64
#SBATCH -t 24:00:00
#SBATCH --mem=0

module purge && module load $STACKYEAR && module load $TOOLCHAIN
source $VENVDIR/bin/activate

cd \$TMPDIR
cp -r $SRCDIR .                 # or cp -r $NEWPROJ/src .
python src/myepicprogram.py      # <‑‑ edit for the repository you run

mkdir -p $PROJDIR/results/\$SLURM_JOB_ID
cp -r results $PROJDIR/results/\$SLURM_JOB_ID
EOF

###############################################################################
# 5.  S U B M I T   &   M O N I T O R
###############################################################################
sbatch "$PROJDIR/run.slurm"
squeue -u $USER                  # watch the queue
