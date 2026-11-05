#!/bin/bash
# Build ChampSim (all predictor binaries) and the trace-driven driver on an Ada compute node,
# then extract the branch-only streams used by the MPKI sweep.
#SBATCH -J tage-build
#SBATCH -p u22
#SBATCH -c 10
#SBATCH --mem=16G
#SBATCH -t 01:30:00
#SBATCH -o logs/build-%j.out
set -euo pipefail
ROOT=$HOME/aca_tage
cd $ROOT/ChampSim

./vcpkg/bootstrap-vcpkg.sh -disableMetrics
./vcpkg/vcpkg install
./config.sh ../configs/all.json
make -j10
ls -la bin

cd $ROOT
V=ChampSim/vcpkg_installed/x64-linux
g++ -std=c++17 -O3 -IChampSim/inc -I$V/include tools/bp_driver.cc ChampSim/branch/tage/tage.cc ChampSim/branch/gshare/gshare.cc \
  ChampSim/branch/bimodal/bimodal.cc ChampSim/branch/gshare_param/gshare_param.cc ChampSim/branch/bimodal_param/bimodal_param.cc \
  $V/lib/libfmt.a -o tools/bp_driver

mkdir -p traces/branches
ls traces/*.champsimtrace.xz | xargs -P 8 -I{} sh -c 'b=$(basename {} .champsimtrace.xz); tools/bp_driver extract {} traces/branches/$b.br 120000000 | sed "s/^/$b: /"'
echo BUILD_DONE
