# TAGE branch predictor in ChampSim

Course project P14, Advanced Computer Architecture (IIIT Hyderabad), by Arya Mirani.

A simplified TAGE predictor (a bimodal base plus 4 partially tagged tables with geometric history lengths) implemented as a ChampSim branch module. It is compared with bimodal and gshare on 8 SPEC CPU2017 traces, with sweeps over storage budget, number of tables, history lengths and tag width.

**Report:** [REPORT.md](REPORT.md) ([PDF](REPORT.pdf))

## Headline results

| | bimodal (4 KB) | gshare (4 KB) | TAGE (9 KB) |
|---|---|---|---|
| mean conditional MPKI (20M warmup + 100M) | 12.45 | 9.00 | **5.76** |
| geomean IPC (ChampSim, 10M + 10M) | 1.123 | 1.174 | **1.223** |

- TAGE has 36% fewer mispredictions than gshare and 4.2% higher IPC, and is ahead on every trace in MPKI.
- The advantage is not storage: TAGE at 2.25 KB beats gshare at 64 KB in both MPKI and IPC.
- Geometric history spacing beats linear spacing by 7% MPKI. Lmax ≈ 130 and 8–9-bit partial tags are near-optimal.

## Layout

| path | contents |
|---|---|
| `predictors/tage/` | the TAGE implementation (`tage.h`, `tage.cc`) |
| `predictors/gshare_param/`, `predictors/bimodal_param/` | baselines with run-time table sizes, for storage sweeps |
| `configs/` | ChampSim build configs; `all.json` builds all five binaries |
| `tools/bp_driver.cc` | trace-driven driver: replays branches through the same predictor sources, a 120M-instruction run takes seconds instead of tens of minutes |
| `scripts/` | experiment definitions, sweep runners, result parser, plotting, PDF build |
| `ada/` | SLURM jobs used on IIIT's Ada cluster |
| `results/` | `mpki.csv` (360 driver runs), `results.csv` and `raw/` (360 ChampSim runs), `figures/`, `summary.md` |
| `logs/` | Ada job logs |

## Reproducing

```bash
./setup.sh                   # clone ChampSim at the pinned commit and link predictors/ into it
scripts/get_traces.sh        # first 80 MB of each DPC-3 trace
```

The full command sequence (build, both sweeps, figures, PDF) is in Section 7 of the report.

## References

- A. Seznec and P. Michaud, *A Case for (Partially) TAgged GEometric History Length Branch Prediction*, JILP 8, 2006.
- A. Seznec, *A New Case for the TAGE Branch Predictor*, MICRO 2011.
