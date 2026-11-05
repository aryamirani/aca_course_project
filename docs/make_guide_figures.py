#!/usr/bin/env python3
"""Draw the explanatory diagrams used in docs/GUIDE.md (written to docs/figures/)."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle  # noqa: E402

OUT = Path(__file__).resolve().parent / "figures"

INK = "#1f2328"
MUTED = "#6b7280"
LINE = "#c9ced6"
FILL = "#f3f4f6"
BLUE = "#2a78d6"     # TAGE / correct
ORANGE = "#eb6834"   # gshare / wrong path
GREEN = "#1baf7a"    # bimodal / taken
BG = "#ffffff"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "text.color": INK,
    "figure.facecolor": BG,
    "savefig.facecolor": BG,
})


def canvas(w, h):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.axis("off")
    return fig, ax


def box(ax, x, y, w, h, text="", fc=FILL, ec=LINE, color=INK, size=10, weight="normal", r=0.08, lw=1.2):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}", fc=fc, ec=ec, lw=lw))
    if text:
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", color=color, fontsize=size, weight=weight)


def arrow(ax, x0, y0, x1, y1, color=MUTED, lw=1.4, style="-|>", rad=0.0, ls="-"):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle=style, mutation_scale=12, color=color, lw=lw,
                                 connectionstyle=f"arc3,rad={rad}", linestyle=ls))


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / name, dpi=200, bbox_inches="tight", pad_inches=0.08)
    plt.close(fig)


def pipeline():
    stages = ["F", "D", "E", "M", "W"]
    names = {"F": "Fetch", "D": "Decode", "E": "Execute", "M": "Memory", "W": "Write back"}
    rows = [
        ("i1  add", 1, "ok"),
        ("i2  branch", 2, "branch"),
        ("i3  (guessed path)", 3, "flush"),
        ("i4  (guessed path)", 4, "flush"),
        ("i3  (correct path)", 5, "ok"),
        ("i4  (correct path)", 6, "ok"),
    ]
    ncyc = 10
    fig, ax = canvas(9.4, 4.0)
    x0, y0, cw, ch = 2.4, 0.55, 0.68, 0.46
    for c in range(ncyc):
        ax.text(x0 + c * cw + cw / 2, y0 + len(rows) * ch + 0.18, f"{c + 1}", ha="center", color=MUTED, fontsize=9)
    ax.text(x0 + ncyc * cw / 2, y0 + len(rows) * ch + 0.48, "clock cycle", ha="center", color=MUTED, fontsize=9)
    for r, (label, start, kind) in enumerate(rows):
        y = y0 + (len(rows) - 1 - r) * ch
        ax.text(x0 - 0.12, y + ch / 2, label, ha="right", va="center", fontsize=9.5,
                color=MUTED if kind == "flush" else INK, weight="bold" if kind == "branch" else "normal")
        # wrong-path instructions are flushed when the branch resolves at the end of cycle 4
        n = 5 - start if kind == "flush" else len(stages)
        for s in range(n):
            c = start - 1 + s
            fc = {"ok": "#e8f1fc", "branch": "#fde9e1", "flush": "#eeeeee"}[kind]
            ec = {"ok": BLUE, "branch": ORANGE, "flush": "#b0b0b0"}[kind]
            ax.add_patch(Rectangle((x0 + c * cw + 0.03, y + 0.04), cw - 0.06, ch - 0.08, fc=fc, ec=ec, lw=1))
            ax.text(x0 + c * cw + cw / 2, y + ch / 2, stages[s], ha="center", va="center", fontsize=9,
                    color=MUTED if kind == "flush" else INK)
        if kind == "flush":
            xe = x0 + (start - 1 + n) * cw
            ax.plot([x0 + (start - 1) * cw + 0.05, xe - 0.05], [y + ch / 2, y + ch / 2], color=ORANGE, lw=1.6)
            ax.text(xe + 0.08, y + ch / 2, "thrown away", va="center", fontsize=8.5, color=ORANGE)
    # branch resolves
    xr = x0 + 4 * cw
    ax.plot([xr, xr], [y0 - 0.1, y0 + len(rows) * ch + 0.05], color=ORANGE, lw=1.2, ls="--")
    ax.text(xr + 0.06, y0 - 0.28, "branch outcome known here: the guess was wrong", fontsize=8.5, color=ORANGE)
    legend = "   ".join(f"{k} = {v}" for k, v in names.items())
    ax.text(x0, 0.0, legend, fontsize=8.5, color=MUTED)
    save(fig, "pipeline.png")


def counter():
    fig, ax = canvas(9.4, 2.7)
    labels = ["0\nstrongly\nnot taken", "1\nweakly\nnot taken", "2\nweakly\ntaken", "3\nstrongly\ntaken"]
    xs = [0.9, 3.1, 5.3, 7.5]
    y, w, h = 0.9, 1.3, 1.05
    for i, (x, lab) in enumerate(zip(xs, labels)):
        taken = i >= 2
        box(ax, x, y, w, h, lab, fc="#e6f6ef" if taken else "#fde9e1", ec=GREEN if taken else ORANGE, size=9, r=0.25)
    for i in range(3):
        arrow(ax, xs[i] + w, y + h * 0.72, xs[i + 1], y + h * 0.72, color=GREEN, rad=-0.25)
        ax.text((xs[i] + w + xs[i + 1]) / 2, y + h + 0.22, "taken", ha="center", fontsize=8.5, color=GREEN)
        arrow(ax, xs[i + 1], y + h * 0.28, xs[i] + w, y + h * 0.28, color=ORANGE, rad=-0.25)
        ax.text((xs[i] + w + xs[i + 1]) / 2, y - 0.33, "not taken", ha="center", fontsize=8.5, color=ORANGE)
    ax.text(xs[0] + w + 1.1 - 1.1, 0.2, "predict NOT TAKEN", ha="left", fontsize=9, color=ORANGE, weight="bold")
    ax.text(xs[3] + w, 0.2, "predict TAKEN", ha="right", fontsize=9, color=GREEN, weight="bold")
    save(fig, "counter.png")


def history():
    fig, ax = canvas(9.6, 3.0)
    outcomes = "TTNTNNTTTNTNTTNNTTNTTTNTTNNTNTTTNTNTNTTNTTNTNNTTNT"
    x0, y0, bw = 0.3, 1.95, 0.168
    ax.text(x0, y0 + 0.55, "most recent branch outcomes (newest on the left)  T = taken, N = not taken",
            fontsize=9, color=MUTED)
    for i, o in enumerate(outcomes):
        ax.add_patch(Rectangle((x0 + i * bw, y0), bw - 0.02, 0.32, fc="#e6f6ef" if o == "T" else "#fde9e1",
                               ec="none"))
        ax.text(x0 + i * bw + bw / 2 - 0.01, y0 + 0.16, o, ha="center", va="center", fontsize=7)
    ax.text(x0 + len(outcomes) * bw + 0.1, y0 + 0.16, "… older", va="center", fontsize=9, color=MUTED)
    spans = [("gshare: last 14", 14, ORANGE), ("TAGE T1: last 5", 5, BLUE), ("TAGE T2: last 15", 15, BLUE),
             ("TAGE T3: last 44", 44, BLUE), ("TAGE T4: last 130", 130, BLUE)]
    for k, (lab, n, col) in enumerate(spans):
        y = y0 - 0.32 - k * 0.33
        end = min(n, len(outcomes) + 2.2)
        ax.plot([x0, x0 + end * bw], [y, y], color=col, lw=2.2, solid_capstyle="butt")
        ax.plot([x0, x0], [y - 0.07, y + 0.07], color=col, lw=2)
        if n <= len(outcomes):
            ax.plot([x0 + n * bw, x0 + n * bw], [y - 0.07, y + 0.07], color=col, lw=2)
            ax.text(x0 + n * bw + 0.1, y, lab, va="center", fontsize=8.5, color=col)
        else:
            ax.text(x0 + end * bw + 0.1, y, lab + " (continues off the picture)", va="center", fontsize=8.5,
                    color=col)
    save(fig, "history.png")


def gshare():
    fig, ax = canvas(9.4, 3.3)
    box(ax, 0.2, 2.2, 2.3, 0.6, "branch address (PC)", fc="#eef2f7")
    box(ax, 0.2, 0.7, 2.3, 0.6, "last 14 outcomes", fc="#eef2f7")
    ax.add_patch(plt.Circle((3.6, 1.75), 0.32, fc=BG, ec=INK, lw=1.4))
    ax.text(3.6, 1.75, "XOR", ha="center", va="center", fontsize=8.5, weight="bold")
    arrow(ax, 2.5, 2.5, 3.32, 1.9)
    arrow(ax, 2.5, 1.0, 3.32, 1.6)
    ax.text(4.3, 2.0, "index", fontsize=9, color=MUTED)
    arrow(ax, 3.92, 1.75, 5.05, 1.75)
    tx, ty, tw, rh = 5.1, 0.2, 1.5, 0.26
    vals = ["2", "0", "3", "1", "3", "2", "0", "1", "3", "2", "1"]
    for i, v in enumerate(vals):
        hl = i == 5
        ax.add_patch(Rectangle((tx, ty + i * rh), tw, rh, fc="#fde9e1" if hl else FILL, ec=LINE, lw=0.8))
        ax.text(tx + tw / 2, ty + i * rh + rh / 2, v, ha="center", va="center", fontsize=8,
                weight="bold" if hl else "normal")
    ax.text(tx + tw / 2, ty + len(vals) * rh + 0.12, "table of 2-bit counters\n(16K of them in ChampSim's gshare)",
            ha="center", fontsize=8.5, color=MUTED)
    arrow(ax, tx + tw, ty + 5.5 * rh, 7.4, ty + 5.5 * rh)
    box(ax, 7.45, ty + 5.5 * rh - 0.3, 1.8, 0.6, "counter 2 →\npredict TAKEN", fc="#e6f6ef", ec=GREEN, size=9)
    save(fig, "gshare.png")


def tage():
    fig, ax = canvas(10.0, 5.6)
    box(ax, 0.15, 4.6, 1.9, 0.6, "branch address\n(PC)", fc="#eef2f7", size=9)
    box(ax, 0.15, 3.7, 1.9, 0.6, "global history\n(past outcomes)", fc="#eef2f7", size=9)
    tables = [("T0  base table", "PC only", None), ("T1", "PC + last 5", "hit"), ("T2", "PC + last 15", "miss"),
              ("T3", "PC + last 44", "hit"), ("T4", "PC + last 130", "miss")]
    tx, tw, th = 3.0, 2.6, 0.7
    ys = [0.3, 1.25, 2.2, 3.15, 4.1]
    for (name, src, res), y in zip(tables, ys):
        is_base = res is None
        box(ax, tx, y, tw, th, "", fc="#f5f5f5" if is_base else "#e8f1fc", ec=LINE if is_base else BLUE)
        ax.text(tx + 0.12, y + th - 0.2, name, fontsize=9.5, weight="bold", va="center")
        ax.text(tx + 0.12, y + 0.2, f"index = hash({src})", fontsize=8, color=MUTED, va="center")
        arrow(ax, 2.05, 4.05, tx, y + th / 2, color=LINE, lw=1.0)
        if is_base:
            ax.text(tx + tw + 0.15, y + th / 2, "always gives a guess", fontsize=8.5, va="center", color=MUTED)
        else:
            col = GREEN if res == "hit" else MUTED
            txt = "tag matches ✔" if res == "hit" else "tag differs ✘"
            ax.text(tx + tw + 0.15, y + th / 2, txt, fontsize=8.5, va="center", color=col)
    # entry anatomy
    ex, ey = 0.15, 1.2
    ax.text(ex, ey + 1.05, "one tagged entry (14 bits):", fontsize=8.5, color=MUTED)
    for i, (lab, w) in enumerate([("counter\n3 bits", 0.75), ("tag\n9 bits", 0.75), ("useful\n2 bits", 0.6)]):
        x = ex + sum([0.75, 0.75, 0.6][:i])
        ax.add_patch(Rectangle((x, ey), w, 0.8, fc="#e8f1fc", ec=BLUE, lw=1))
        ax.text(x + w / 2, ey + 0.4, lab, ha="center", va="center", fontsize=8)
    # selection
    sx = 7.6
    box(ax, sx, 2.0, 2.3, 1.5, "", fc="#fff7f2", ec=ORANGE)
    ax.text(sx + 1.15, 3.2, "choose", ha="center", fontsize=9.5, weight="bold")
    ax.text(sx + 1.15, 2.65, "longest matching table\n= T3 (the provider)\nnext one = T1 (alternate)", ha="center",
            va="center", fontsize=8.3)
    for y, res in zip(ys, [None, "hit", "miss", "hit", "miss"]):
        if res != "miss":
            arrow(ax, tx + tw + 1.5, y + 0.35, sx, 2.75, color=GREEN if res else LINE,
                  lw=1.2)
    box(ax, sx + 0.05, 0.45, 2.2, 0.75, "prediction =\nT3's counter", fc="#e6f6ef", ec=GREEN, size=9)
    arrow(ax, sx + 1.15, 2.0, sx + 1.15, 1.2)
    save(fig, "tage.png")


def simulator():
    fig, ax = canvas(10.0, 3.4)
    box(ax, 0.1, 1.9, 1.8, 0.9, "real program\n(e.g. gcc, chess)", fc="#eef2f7", size=9)
    box(ax, 2.4, 1.9, 1.9, 0.9, "trace file\nrecorded instructions", fc="#eef2f7", size=9)
    arrow(ax, 1.9, 2.35, 2.4, 2.35)
    box(ax, 5.0, 2.3, 3.0, 1.0, "ChampSim\nwhole CPU model: pipeline,\ncaches, memory + predictor", fc="#e8f1fc",
        ec=BLUE, size=8.8)
    box(ax, 5.0, 0.6, 3.0, 1.0, "bp_driver (our replay tool)\nbranches only → predictor", fc="#fff7f2",
        ec=ORANGE, size=8.8)
    arrow(ax, 4.3, 2.5, 5.0, 2.8)
    arrow(ax, 4.3, 2.2, 5.0, 1.1)
    box(ax, 8.6, 2.4, 1.3, 0.8, "IPC\n+ MPKI", fc="#e6f6ef", ec=GREEN, size=9, weight="bold")
    box(ax, 8.6, 0.7, 1.3, 0.8, "MPKI", fc="#e6f6ef", ec=GREEN, size=9, weight="bold")
    arrow(ax, 8.0, 2.8, 8.6, 2.8)
    arrow(ax, 8.0, 1.1, 8.6, 1.1)
    ax.text(6.5, 1.95, "slow: minutes per 20M instructions", ha="center", fontsize=8, color=MUTED)
    ax.text(6.5, 0.25, "fast: ~1 s per 120M instructions", ha="center", fontsize=8, color=MUTED)
    save(fig, "simulator.png")


if __name__ == "__main__":
    pipeline()
    counter()
    history()
    gshare()
    tage()
    simulator()
    print(f"wrote diagrams to {OUT}")
