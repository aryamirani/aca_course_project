#!/usr/bin/env bash
# Fetch ChampSim at the commit this project was built against and link our predictors into it.
set -euo pipefail
cd "$(dirname "$0")"

CHAMPSIM_COMMIT=410cee62d9c429c043ea611325ce00e6c303be2a

if [ ! -d ChampSim ]; then
  git clone https://github.com/ChampSim/ChampSim.git
fi
git -C ChampSim checkout -q "$CHAMPSIM_COMMIT"
git -C ChampSim submodule update --init

for p in predictors/*/; do
  name=$(basename "$p")
  ln -sfn "../../predictors/$name" "ChampSim/branch/$name"
done
echo "ChampSim ready at $CHAMPSIM_COMMIT with predictors: $(ls predictors | tr '\n' ' ')"
