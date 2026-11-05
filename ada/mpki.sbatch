#!/bin/bash
# Long-window MPKI sweep (20M warmup + 100M measured) with the trace-driven driver -> results/mpki.csv
#SBATCH -J tage-mpki
#SBATCH -p u22
#SBATCH -c 10
#SBATCH --mem=16G
#SBATCH -t 04:00:00
#SBATCH -o logs/mpki-%j.out
set -euo pipefail
cd $HOME/aca_tage
python3 scripts/run_mpki.py --jobs 10
