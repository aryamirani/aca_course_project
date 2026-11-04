#!/usr/bin/env bash
# Download the first 80 MB of each DPC-3 SPEC CPU2017 trace used in this project.
# 80 MB of a .xz trace holds well over the 120M instructions the experiments read,
# and the trace readers stream it, so the truncated tail is never reached.
set -euo pipefail
cd "$(dirname "$0")/.."

BASE=https://dpc3.compas.cs.stonybrook.edu/champsim-traces/speccpu
BYTES=$((80 * 1024 * 1024 - 1))
TRACES="600.perlbench_s-210B 602.gcc_s-734B 605.mcf_s-665B 623.xalancbmk_s-700B
625.x264_s-18B 631.deepsjeng_s-928B 641.leela_s-800B 657.xz_s-3167B"

mkdir -p traces
for t in $TRACES; do
  f=traces/$t.champsimtrace.xz
  [ -s "$f" ] && { echo "have $f"; continue; }
  echo "fetching $f"
  curl -fsSL -r "0-$BYTES" -o "$f" "$BASE/$t.champsimtrace.xz"
done
