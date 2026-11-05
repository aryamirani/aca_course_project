#!/usr/bin/env python3
"""Figures and summary tables for the report.

Inputs : results/mpki.csv     (trace-driven driver, 20M warmup + 100M measured instructions)
         results/results.csv  (ChampSim timing runs, IPC; optional - IPC figures are skipped if absent)
Outputs: results/figures/*.png, results/summary.md

MPKI is averaged arithmetically across traces, IPC geometrically.
"""
import csv
import math
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
from experiments import GROUPS, TRACES  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "results"
FIG = RES / "figures"

# categorical slots in fixed order (validated: scripts/validate_palette.js, light surface)
COLOR = {"tage": "#2a78d6", "gshare": "#eb6834", "bimodal": "#1baf7a"}
MARKER = {"tage": "o", "gshare": "s", "bimodal": "^"}
LABEL = {"tage": "TAGE", "gshare": "gshare", "bimodal": "bimodal"}
INK, INK2, GRID, SURFACE = "#1f1f1e", "#5f5e58", "#e4e3de", "#fcfcfb"

SHORT = {t: t.split("_")[0].split(".")[1] for t in TRACES}  # 600.perlbench_s-210B -> perlbench

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
    "axes.spines.top": False, "axes.spines.right": False, "font.size": 10, "axes.titlesize": 11,
    "axes.titleweight": "bold", "axes.titlecolor": INK, "legend.frameon": False, "lines.linewidth": 2,
    "lines.markersize": 7,
})


def load(path):
    if not path.exists():
        return []
    return list(csv.DictReader(open(path)))


def family(row):
    p = row["predictor"]
    return "tage" if p == "tage" else ("gshare" if p.startswith("gshare") else "bimodal")


def table(rows, value):
    """config -> trace -> float(value)"""
    t = defaultdict(dict)
    for r in rows:
        if r.get(value):
            t[r["config"]][r["trace"]] = float(r[value])
    return t


def amean(d):
    return sum(d.values()) / len(d)


def gmean(d):
    return math.exp(sum(math.log(v) for v in d.values()) / len(d))


def complete(t, config):
    return config in t and len(t[config]) == len(TRACES)


def save(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / f"{name}.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  {name}.png")


def end_label(ax, x, y, text, color):
    ax.annotate(text, (x, y), xytext=(6, 0), textcoords="offset points", va="center", color=INK, fontsize=9)
    ax.plot([], [], color=color)


def grouped_bars(ax, t, configs, value_fmt, mean_fn, ylabel):
    groups = [SHORT[tr] for tr in TRACES] + ["mean"]
    width = 0.8 / len(configs)
    for i, (cfg, fam) in enumerate(configs):
        vals = [t[cfg][tr] for tr in TRACES] + [mean_fn(t[cfg])]
        xs = [g + (i - (len(configs) - 1) / 2) * width for g in range(len(groups))]
        ax.bar(xs, vals, width=width, color=COLOR[fam], edgecolor=SURFACE, linewidth=1.5,
               label=f"{LABEL[fam]} (mean {value_fmt.format(vals[-1])})")
    ax.set_xticks(range(len(groups)), groups, rotation=30, ha="right")
    ax.set_ylabel(ylabel)
    ax.grid(axis="x", visible=False)
    ax.set_ylim(0, ax.get_ylim()[1] * 1.15)
    ax.legend(loc="upper center", ncols=len(configs), bbox_to_anchor=(0.5, 1.0))


def storage_series(t, fam, mean_fn):
    """(storage_kb, mean) points for one predictor family in the storage group, sorted by size."""
    pts = []
    for cfg in GROUPS["storage"]:
        if FAMILY_OF.get(cfg) == fam and complete(t, cfg):
            pts.append((STORAGE[cfg], mean_fn(t[cfg])))
    return sorted(pts)


def log2_storage_axis(ax):
    ax.set_xscale("log", base=2)
    ticks = [2, 4, 8, 16, 32, 64]
    ax.set_xticks(ticks, [f"{k}" for k in ticks])
    ax.set_xlabel("predictor storage (KB, log scale)")


def main():
    global FAMILY_OF, STORAGE
    mpki_rows = load(RES / "mpki.csv")
    ipc_rows = load(RES / "results.csv")
    FAMILY_OF = {r["config"]: family(r) for r in mpki_rows + ipc_rows}
    STORAGE = {r["config"]: float(r["storage_kb"]) for r in mpki_rows if r["storage_kb"]}
    mp = table(mpki_rows, "mpki_cond")
    ipc = table(ipc_rows, "ipc")
    md = ["# Result summary", "", "MPKI = conditional-branch mispredictions per 1000 instructions "
          "(trace-driven, 20M warmup + 100M measured). IPC from ChampSim (10M warmup + 10M simulated).", ""]
    print("figures:")

    # 1. baseline MPKI per trace
    base = [("bimodal", "bimodal"), ("gshare", "gshare"), ("tage", "tage")]
    fig, ax = plt.subplots(figsize=(9, 4))
    grouped_bars(ax, mp, base, "{:.2f}", amean, "conditional MPKI")
    ax.set_title("Mispredictions per trace: bimodal (4 KB), gshare (4 KB), TAGE (9 KB)", loc="left")
    save(fig, "01_baseline_mpki")
    md += ["## Baseline MPKI", "", "| trace | bimodal | gshare | TAGE | TAGE vs gshare |", "|---|---|---|---|---|"]
    for tr in TRACES:
        b, g, tg = mp["bimodal"][tr], mp["gshare"][tr], mp["tage"][tr]
        md.append(f"| {SHORT[tr]} | {b:.2f} | {g:.2f} | {tg:.2f} | {100 * (tg - g) / g:+.0f}% |")
    b, g, tg = amean(mp["bimodal"]), amean(mp["gshare"]), amean(mp["tage"])
    md += [f"| **mean** | **{b:.2f}** | **{g:.2f}** | **{tg:.2f}** | **{100 * (tg - g) / g:+.0f}%** |", ""]

    # 2. storage budget
    fig, ax = plt.subplots(figsize=(7, 4))
    md += ["## Storage budget (mean MPKI)", "", "| predictor | storage KB | mean MPKI |", "|---|---|---|"]
    for fam in ["bimodal", "gshare", "tage"]:
        pts = storage_series(mp, fam, amean)
        xs, ys = zip(*pts)
        ax.plot(xs, ys, color=COLOR[fam], marker=MARKER[fam])
        end_label(ax, xs[-1], ys[-1], LABEL[fam], COLOR[fam])
        md += [f"| {LABEL[fam]} | {x:.2f} | {y:.2f} |" for x, y in pts]
    log2_storage_axis(ax)
    ax.set_ylabel("mean conditional MPKI")
    ax.set_ylim(bottom=0)
    ax.set_xlim(right=110)
    ax.set_title("MPKI vs storage: TAGE at 2 KB beats gshare at 64 KB", loc="left")
    save(fig, "02_storage_mpki")
    md.append("")

    # 2b. storage per trace (small multiples)
    fig, axes = plt.subplots(2, 4, figsize=(13, 5.5), sharex=True)
    for ax, tr in zip(axes.flat, TRACES):
        for fam in ["gshare", "tage"]:
            pts = sorted((STORAGE[c], mp[c][tr]) for c in GROUPS["storage"] if FAMILY_OF.get(c) == fam and c in mp)
            xs, ys = zip(*pts)
            ax.plot(xs, ys, color=COLOR[fam], marker=MARKER[fam], markersize=5, label=LABEL[fam])
        ax.set_title(SHORT[tr], loc="left")
        ax.set_xscale("log", base=2)
        ax.set_xticks([2, 8, 32], ["2", "8", "32"])
        ax.set_ylim(bottom=0)
    axes[0, 0].legend(loc="upper right")
    fig.supxlabel("storage (KB, log scale)", color=INK2)
    fig.supylabel("conditional MPKI", color=INK2)
    fig.suptitle("MPKI vs storage, per trace", x=0.01, ha="left", fontweight="bold", color=INK)
    fig.tight_layout()
    save(fig, "03_storage_per_trace")

    # 3. number of tables
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    fixed = [(1, "tage_n1"), (2, "tage_n2"), (3, "tage_n3"), (4, "tage"), (6, "tage_n6"), (8, "tage_n8")]
    xs = [n for n, _ in fixed]
    ys = [amean(mp[c]) for _, c in fixed]
    a1.plot(xs, ys, color=COLOR["tage"], marker="o")
    for (n, c), y in zip(fixed, ys):
        a1.annotate(f"{STORAGE[c]:.1f} KB", (n, y), xytext=(0, 8), textcoords="offset points", ha="center", fontsize=8, color=INK2)
    a1.set_xlabel("number of tagged tables (1K entries each)")
    a1.set_ylabel("mean conditional MPKI")
    a1.set_title("Adding tables (storage grows)", loc="left")
    budget = [(1, "tage_16k_n1"), (2, "tage_16k_n2"), (4, "tage_16k_n4"), (8, "tage_16k_n8"), (16, "tage_16k_n16")]
    bx = [n for n, _ in budget]
    by = [amean(mp[c]) for _, c in budget]
    a2.plot(bx, by, color=COLOR["tage"], marker="o")
    for n, y in zip(bx, by):
        a2.annotate(f"{y:.2f}", (n, y), xytext=(0, 8), textcoords="offset points", ha="center", fontsize=8, color=INK)
    a2.set_xscale("log", base=2)
    a2.set_xticks(bx, [str(n) for n in bx])
    a2.set_xlabel("number of tagged tables (fixed 16 KB total)")
    a2.set_title("Same 16 KB split across more tables", loc="left")
    a1.set_ylim(0, max(ys + by) * 1.12)
    save(fig, "04_num_tables")
    md += ["## Number of tagged tables", "", "| config | tables | storage KB | mean MPKI |", "|---|---|---|---|"]
    md += [f"| {c} | {n} | {STORAGE[c]:.2f} | {amean(mp[c]):.2f} |" for n, c in fixed + budget]
    md.append("")

    # 4. history lengths
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    lmax = [(16, "tage_lmax16"), (32, "tage_lmax32"), (64, "tage_lmax64"), (130, "tage"), (256, "tage_lmax256"),
            (512, "tage_lmax512"), (1024, "tage_lmax1024")]
    xs, ys = [l for l, _ in lmax], [amean(mp[c]) for _, c in lmax]
    a1.plot(xs, ys, color=COLOR["tage"], marker="o")
    best = min(range(len(ys)), key=ys.__getitem__)
    a1.annotate(f"best: Lmax={xs[best]}\nMPKI {ys[best]:.2f}", (xs[best], ys[best]), xytext=(0, -30), textcoords="offset points",
                ha="center", fontsize=8, color=INK)
    a1.set_xscale("log", base=2)
    a1.set_xticks(xs, [str(x) for x in xs])
    a1.set_xlabel("longest history Lmax (Lmin = 5, 4 tables)")
    a1.set_ylabel("mean conditional MPKI")
    a1.set_title("Longest history length", loc="left")
    lmin = [(2, "tage_lmin2"), (5, "tage"), (10, "tage_lmin10"), (20, "tage_lmin20")]
    xs2, ys2 = [l for l, _ in lmin], [amean(mp[c]) for _, c in lmin]
    a2.plot(xs2, ys2, color=COLOR["tage"], marker="o")
    a2.annotate("geometric series", (xs2[-1], ys2[-1]), xytext=(0, -16), textcoords="offset points", ha="right", fontsize=8, color=INK)
    lin = amean(mp["tage_linear"])
    a2.plot([5], [lin], color=COLOR["gshare"], marker="s", linestyle="none")
    a2.annotate(f"linear spacing 5,47,88,130: {lin:.2f}", (5, lin), xytext=(10, 0), textcoords="offset points", va="center",
                fontsize=8, color=INK)
    a2.set_xticks(xs2, [str(x) for x in xs2])
    a2.set_xlabel("shortest history Lmin (Lmax = 130, 4 tables)")
    a2.set_title("Shortest history length and spacing", loc="left")
    a1.set_ylim(0, max(ys + ys2 + [lin]) * 1.12)
    save(fig, "05_history_lengths")
    md += ["## History lengths (4 tables, 9 KB)", "", "| config | lengths | mean MPKI |", "|---|---|---|"]
    hist = {r["config"]: r["hist"] for r in mpki_rows}
    md += [f"| {c} | {hist[c]} | {amean(mp[c]):.2f} |" for _, c in lmax + lmin + [(0, "tage_linear")]]
    md.append("")

    # 5. tag width
    tags = [(4, "tage_tag4"), (6, "tage_tag6"), (8, "tage_tag8"), (9, "tage"), (11, "tage_tag11"), (13, "tage_tag13")]
    fig, ax = plt.subplots(figsize=(6.5, 4))
    xs, ys = [b for b, _ in tags], [amean(mp[c]) for _, c in tags]
    ax.plot(xs, ys, color=COLOR["tage"], marker="o")
    for (b, c), y in zip(tags, ys):
        ax.annotate(f"{y:.2f}\n{STORAGE[c]:.1f} KB", (b, y), xytext=(0, 8), textcoords="offset points", ha="center", fontsize=8, color=INK2)
    ax.set_xticks(xs)
    ax.set_xlabel("partial tag width (bits)")
    ax.set_ylabel("mean conditional MPKI")
    ax.set_ylim(0, max(ys) * 1.25)
    ax.set_title("Partial tag width: aliasing vs storage", loc="left")
    save(fig, "06_tag_bits")
    md += ["## Partial tag width", "", "| tag bits | storage KB | mean MPKI |", "|---|---|---|"]
    md += [f"| {b} | {STORAGE[c]:.2f} | {amean(mp[c]):.2f} |" for b, c in tags]
    md.append("")

    # 6-8. IPC (ChampSim)
    if all(complete(ipc, c) for c in ["bimodal", "gshare", "tage"]):
        fig, ax = plt.subplots(figsize=(9, 4))
        grouped_bars(ax, ipc, base, "{:.3f}", gmean, "IPC")
        ax.set_title("IPC per trace (ChampSim): bimodal, gshare, TAGE", loc="left")
        save(fig, "07_baseline_ipc")
        md += ["## Baseline IPC (ChampSim)", "", "| trace | bimodal | gshare | TAGE | TAGE vs gshare |", "|---|---|---|---|---|"]
        for tr in TRACES:
            b, g, tg = ipc["bimodal"][tr], ipc["gshare"][tr], ipc["tage"][tr]
            md.append(f"| {SHORT[tr]} | {b:.3f} | {g:.3f} | {tg:.3f} | {100 * (tg - g) / g:+.1f}% |")
        b, g, tg = gmean(ipc["bimodal"]), gmean(ipc["gshare"]), gmean(ipc["tage"])
        md += [f"| **geomean** | **{b:.3f}** | **{g:.3f}** | **{tg:.3f}** | **{100 * (tg - g) / g:+.1f}%** |", ""]

    fams = [f for f in ["bimodal", "gshare", "tage"] if len(storage_series(ipc, f, gmean)) >= 2]
    if fams:
        fig, ax = plt.subplots(figsize=(7, 4))
        md += ["## Storage budget (geomean IPC)", "", "| predictor | storage KB | geomean IPC |", "|---|---|---|"]
        for fam in fams:
            pts = storage_series(ipc, fam, gmean)
            xs, ys = zip(*pts)
            ax.plot(xs, ys, color=COLOR[fam], marker=MARKER[fam])
            end_label(ax, xs[-1], ys[-1], LABEL[fam], COLOR[fam])
            md += [f"| {LABEL[fam]} | {x:.2f} | {y:.3f} |" for x, y in pts]
        log2_storage_axis(ax)
        ax.set_xlim(right=110)
        ax.set_ylabel("geomean IPC")
        ax.set_title("IPC vs storage (ChampSim)", loc="left")
        save(fig, "08_storage_ipc")
        md.append("")

    # IPC vs MPKI from the same ChampSim runs, one panel per trace
    cs_mpki = table(ipc_rows, "mpki_cond")
    if ipc:
        fig, axes = plt.subplots(2, 4, figsize=(13, 5.5))
        for ax, tr in zip(axes.flat, TRACES):
            for fam in ["bimodal", "gshare", "tage"]:
                pts = [(cs_mpki[c][tr], ipc[c][tr]) for c in ipc if tr in ipc[c] and FAMILY_OF.get(c) == fam]
                if pts:
                    xs, ys = zip(*pts)
                    ax.scatter(xs, ys, s=22, color=COLOR[fam], marker=MARKER[fam], edgecolors=SURFACE, linewidths=0.8, label=LABEL[fam])
            ax.set_title(SHORT[tr], loc="left")
        axes[0, 0].legend(loc="upper right", fontsize=8)
        fig.supxlabel("conditional MPKI (same ChampSim run)", color=INK2)
        fig.supylabel("IPC", color=INK2)
        fig.suptitle("IPC falls as mispredictions rise (every configuration simulated in ChampSim)", x=0.01, ha="left",
                     fontweight="bold", color=INK)
        fig.tight_layout()
        save(fig, "09_ipc_vs_mpki")

        # sensitivity: IPC change per MPKI change, from a least-squares fit per trace
        md += ["## IPC sensitivity to MPKI (ChampSim, least-squares slope per trace)", "",
               "| trace | runs | IPC at lowest MPKI | IPC at highest MPKI | dIPC/dMPKI |", "|---|---|---|---|---|"]
        for tr in TRACES:
            pts = [(cs_mpki[c][tr], ipc[c][tr]) for c in ipc if tr in ipc[c]]
            if len(pts) < 3:
                continue
            n = len(pts)
            mx, my = sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n
            slope = sum((x - mx) * (y - my) for x, y in pts) / max(1e-12, sum((x - mx) ** 2 for x, _ in pts))
            lo, hi = min(pts), max(pts)
            md.append(f"| {SHORT[tr]} | {n} | {lo[1]:.3f} | {hi[1]:.3f} | {slope:+.4f} |")
        md.append("")

    (RES / "summary.md").write_text("\n".join(md) + "\n")
    print(f"wrote {RES / 'summary.md'}")


if __name__ == "__main__":
    main()
