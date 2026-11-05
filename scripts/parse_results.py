#!/usr/bin/env python3
"""Parse results/raw/*.txt into results/results.csv (one row per configuration x trace)."""
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from experiments import CONFIGS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "results" / "raw"
OUT = ROOT / "results" / "results.csv"

PATTERNS = {
    "ipc": r"CPU 0 cumulative IPC: ([\d.]+)",
    "instructions": r"CPU 0 cumulative IPC: [\d.]+ instructions: (\d+)",
    "accuracy": r"Branch Prediction Accuracy: ([\d.]+)%",
    "mpki_total": r"Branch Prediction Accuracy: [\d.]+% MPKI: ([\d.]+)",
    "mpki_cond": r"BRANCH_CONDITIONAL: ([\d.]+)",
    "storage_kb": r"storage_kb=([\d.]+)",
    "hist": r"hist=\[([\d,]+)\]",
    "tables": r"TAGE config: tables=(\d+)",
    "tag_bits": r"tag_bits=(\d+)",
}

# storage of ChampSim's stock predictors: 16K x 2-bit counters
STOCK_STORAGE_KB = {"champsim_bimodal": 4.0, "champsim_gshare": 4.0}


def parse(path):
    text = path.read_text(errors="ignore")
    if "CPU 0 cumulative IPC" not in text:
        return None
    config, trace = path.stem.split("__")
    binary = CONFIGS.get(config, ("?", {}))[0]
    row = {"config": config, "trace": trace, "predictor": binary.replace("champsim_", "")}
    for key, pat in PATTERNS.items():
        m = re.search(pat, text)
        row[key] = m.group(1) if m else ""
    if not row["storage_kb"]:
        row["storage_kb"] = STOCK_STORAGE_KB.get(binary, "")
    return row


def main():
    rows = [r for p in sorted(RAW.glob("*.txt")) if (r := parse(p))]
    fields = ["config", "trace", "predictor", "ipc", "instructions", "accuracy", "mpki_total", "mpki_cond",
              "storage_kb", "tables", "hist", "tag_bits"]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows to {OUT}")


if __name__ == "__main__":
    main()
