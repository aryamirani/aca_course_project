#!/usr/bin/env bash
# Build the trace-driven driver against the same predictor sources ChampSim uses.
# Needs ChampSim's vcpkg dependencies installed first (for fmt).
set -euo pipefail
cd "$(dirname "$0")/.."

V=$(ls -d ChampSim/vcpkg_installed/*/ | grep -v '/vcpkg/$' | head -1)
${CXX:-c++} -std=c++17 -O3 -IChampSim/inc -I"$V/include" tools/bp_driver.cc \
  ChampSim/branch/tage/tage.cc ChampSim/branch/gshare/gshare.cc ChampSim/branch/bimodal/bimodal.cc \
  ChampSim/branch/gshare_param/gshare_param.cc ChampSim/branch/bimodal_param/bimodal_param.cc \
  "$V/lib/libfmt.a" -o tools/bp_driver
echo "built tools/bp_driver"
