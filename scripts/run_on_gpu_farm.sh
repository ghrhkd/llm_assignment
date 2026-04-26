#!/bin/bash
# ============================================================
# HKU GPU Farm Deployment Script
# Usage: sbatch scripts/run_on_gpu_farm.sh
# ============================================================

#SBATCH --job-name=ai-wardrobe
#SBATCH --partition=gpu          # use HKU's GPU partition (check available: sinfo)
#SBATCH --gres=gpu:1             # request 1 GPU
#SBATCH --mem=24G
#SBATCH --cpus-per-task=4
#SBATCH --time=08:00:00          # max 8 hours
#SBATCH --output=logs/wardrobe_%j.log

set -e

echo "=== AI Wardrobe Assistant — HKU GPU Farm ==="
echo "Job ID: $SLURM_JOB_ID"
echo "Node:   $SLURMD_NODENAME"
echo "GPU:    $(nvidia-smi --query-gpu=name --format=csv,noheader)"

# ── 1. Load modules (adjust to HKU's available modules) ──────────
module load python/3.11
module load cuda/12.1           # or whatever CUDA version is available

# ── 2. Set up virtual environment ────────────────────────────────
VENV_DIR="$HOME/venvs/ai-wardrobe"
if [ ! -d "$VENV_DIR" ]; then
    python -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"

# ── 3. Install dependencies ───────────────────────────────────────
pip install --quiet -r requirements.txt

# ── 4. (Optional) Install local IDM-VTON for GPU inference ───────
# Uncomment if you want to run IDM-VTON locally instead of Replicate API:
#
# if [ ! -d "IDM-VTON" ]; then
#     git clone https://github.com/yisol/IDM-VTON.git
#     pip install -r IDM-VTON/requirements.txt
# fi
# export TRYON_BACKEND=local_idmvton

# ── 5. Load your .env ─────────────────────────────────────────────
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

# ── 6. Launch with public share link ─────────────────────────────
# Gradio share=True creates a temporary public URL (valid 72h)
mkdir -p logs
GRADIO_SHARE=true python main.py

echo "=== Job finished ==="
