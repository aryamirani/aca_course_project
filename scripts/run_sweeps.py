#!/usr/bin/env python3
"""Run every (configuration, trace) pair from experiments.py through ChampSim.

Results go to results/raw/<config>__<trace>.txt. Finished runs are skipped, so the script can
be interrupted and restarted.

    python3 scripts/run_sweeps.py                     # everything
    python3 scripts/run_sweeps.py --groups baseline   # one experiment group
"""
import argparse
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from experiments import CONFIGS, GROUPS, TRACES  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / "ChampSim" / "bin"
TRACE_DIR = ROOT / "traces"
RAW = ROOT / "results" / "raw"


def is_complete(path):
    return path.exists() and "CPU 0 cumulative IPC" in path.read_text(errors="ignore")


def run_one(config, trace, warmup, sim):
    binary, env = CONFIGS[config]
    out = RAW / f"{config}__{trace}.txt"
    if is_complete(out):
        return config, trace, 0.0, "cached"
    cmd = [str(BIN / binary), "--warmup-instructions", str(warmup), "--simulation-instructions", str(sim),
           str(TRACE_DIR / f"{trace}.champsimtrace.xz")]
    start = time.time()
    with open(out, "w") as f:
        f.write(f"# config={config} trace={trace} warmup={warmup} sim={sim} env={env}\n")
        f.flush()
        proc = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, env={**os.environ, **env})
    status = "ok" if proc.returncode == 0 and is_complete(out) else f"FAILED rc={proc.returncode}"
    return config, trace, time.time() - start, status


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--groups", nargs="*", default=list(GROUPS), help="experiment groups to run")
    ap.add_argument("--configs", nargs="*", help="only these configurations (after group selection)")
    ap.add_argument("--traces", nargs="*", default=TRACES)
    ap.add_argument("--warmup", type=int, default=20_000_000)
    ap.add_argument("--sim", type=int, default=50_000_000)
    ap.add_argument("--jobs", type=int, default=7)
    args = ap.parse_args()

    RAW.mkdir(parents=True, exist_ok=True)
    configs = list(dict.fromkeys(c for g in args.groups for c in GROUPS[g]))
    if args.configs:
        configs = [c for c in configs if c in args.configs]
    jobs = [(c, t) for c in configs for t in args.traces]
    print(f"{len(configs)} configs x {len(args.traces)} traces = {len(jobs)} runs, {args.jobs} in parallel", flush=True)

    done = 0
    failures = []
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = [pool.submit(run_one, c, t, args.warmup, args.sim) for c, t in jobs]
        for fut in as_completed(futures):
            config, trace, secs, status = fut.result()
            done += 1
            if status.startswith("FAILED"):
                failures.append((config, trace))
            print(f"[{done}/{len(jobs)}] {config:22s} {trace:24s} {status:8s} {secs:6.0f}s", flush=True)

    if failures:
        print(f"{len(failures)} runs failed: {failures}")
        sys.exit(1)


if __name__ == "__main__":
    main()
