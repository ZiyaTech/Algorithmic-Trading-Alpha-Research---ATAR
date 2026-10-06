#!/usr/bin/env bash
#SBATCH --job-name=atar-demo
#SBATCH --array=0-2
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:20:00
set -euo pipefail
: "${SLURM_ARRAY_TASK_ID:?Run with sbatch --array=0-2}"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
seed=$((2026 + SLURM_ARRAY_TASK_ID))
python -m atar demo --seed "$seed" --output "artifacts/seed-$seed"
