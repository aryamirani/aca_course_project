#!/usr/bin/env python3
"""Long-window MPKI sweep with the trace-driven driver (tools/bp_driver).

Uses the same predictor sources and environment-variable parameters as the ChampSim runs, over a
longer window (default 20M warmup + 100M measured instructions). Writes results/mpki.csv.

Branch streams must be extracted first:
    tools/bp_driver extract traces/<t>.champsimtrace.xz traces/branches/<t>.br 120000000
"""
import argparse
import csv
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from experiments import CONFIGS, GROUPS, TRACES  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DRIVER = ROOT / "tools" / "bp_driver"
BRANCHES = ROOT / "traces" / "branches"
OUT = ROOT / "results" / "mpki.csv"

FIELDS = ["config", "trace", "predictor", "mpki_cond", "accuracy", "cond_branches", "cond_miss", "instructions",
          "storage_kb", "tables", "hist", "tag_bits"]


def run_one(config, trace, warmup, measure):
    binary, env = CONFIGS[config]
    predictor = binary.replace("champsim_", "")
    cmd = [str(DRIVER), predictor, str(BRANCHES / f"{trace}.br"), str(warmup), str(measure)]
    out = subprocess.run(cmd, capture_output=True, text=True, env={**os.environ, **env}, check=True).stdout
    row = {"config": config, "trace": trace, "predictor": predictor}
    row.update(dict(re.findall(r"(\w+)=([^\s\]]+)", out.split("RESULT", 1)[1])))
    for key, pat in [("storage_kb", r"storage_kb=([\d.]+)"), ("hist", r"hist=\[([\d,]+)\]"),
                     ("tables", r"tables=(\d+)"), ("tag_bits", r"tag_bits=(\d+)")]:
        m = re.search(pat, out)
        row[key] = m.group(1) if m else ""
    if not row["storage_kb"]:
        row["storage_kb"] = 4.0  # stock bimodal / gshare: 16K x 2-bit counters
    row["predictor"] = predictor
    return {k: row.get(k, "") for k in FIELDS}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--groups", nargs="*", default=list(GROUPS))
    ap.add_argument("--warmup", type=int, default=20_000_000)
    ap.add_argument("--measure", type=int, default=100_000_000)
    ap.add_argument("--jobs", type=int, default=2)
    args = ap.parse_args()

    configs = list(dict.fromkeys(c for g in args.groups for c in GROUPS[g]))
    jobs = [(c, t) for c in configs for t in TRACES]
    print(f"{len(jobs)} driver runs", flush=True)
    rows = []
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for i, row in enumerate(pool.map(lambda j: run_one(*j, args.warmup, args.measure), jobs), 1):
            rows.append(row)
            if i % 20 == 0 or i == len(jobs):
                print(f"[{i}/{len(jobs)}] {row['config']} {row['trace']} mpki={row['mpki_cond']}", flush=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows to {OUT}")


if __name__ == "__main__":
    main()
