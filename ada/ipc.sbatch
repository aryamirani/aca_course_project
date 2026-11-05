#!/bin/bash
# Full ChampSim timing sweep (10M warmup + 10M simulated) for IPC -> results/raw/*.txt
# Finished runs are skipped, so resubmitting this job resumes the sweep.
#SBATCH -J tage-ipc
#SBATCH -p u22
#SBATCH -c 10
#SBATCH --mem=16G
#SBATCH -t 2-00:00:00
#SBATCH -o logs/ipc-%j.out
set -euo pipefail
cd $HOME/aca_tage
python3 scripts/run_sweeps.py --warmup 10000000 --sim 10000000 --jobs 10 \
  --groups baseline storage tables_fixed_size tables_fixed_budget max_hist tag_bits min_hist spacing
python3 scripts/parse_results.py
