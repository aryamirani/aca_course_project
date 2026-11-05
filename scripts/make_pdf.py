#!/usr/bin/env python3
"""Render REPORT.md to REPORT.pdf (pandoc -> LaTeX -> xelatex).

Usage: python3 scripts/make_pdf.py
"""
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

META = r"""---
title: "Implementing and Evaluating the TAGE Branch Predictor"
subtitle: "Course project P14, Advanced Computer Architecture"
author: "Arya Mirani"
date: "November 2026"
geometry: "margin=2.2cm"
fontsize: 11pt
mainfont: "Charter"
monofont: "Menlo"
monofontoptions: "Scale=0.85"
colorlinks: true
linkcolor: "blue!50!black"
urlcolor: "blue!50!black"
header-includes:
  - \usepackage{float}
  - \floatplacement{figure}{H}
  - \setlength{\parskip}{0.45em}
  - \setlength{\parindent}{0pt}
---
"""

# glyphs Charter lacks
GLYPHS = {"→": r"$\rightarrow$", "⊕": r"$\oplus$", "≪": r"$\ll$"}


def prepare_markdown(text):
    lines = text.splitlines()
    # drop the title block (title, course line, author); it comes from META
    while lines and not lines[0].startswith("## "):
        lines.pop(0)
    out = []
    in_code = False
    for line in lines:
        if line.startswith("```"):
            in_code = not in_code
        if not in_code:
            line = re.sub(r"^## ", "# ", line)
            line = re.sub(r"^### ", "## ", line)
            for g, rep in GLYPHS.items():
                line = line.replace(g, rep)
            # pandoc needs a blank line between a paragraph and a list
            is_item = re.match(r"^(\s*)([-*]|\d+\.) ", line)
            prev = out[-1] if out else ""
            if is_item and prev.strip() and not re.match(r"^\s*([-*]|\d+\.) ", prev) \
                    and not prev.startswith(" "):
                out.append("")
        out.append(line)
    return META + "\n".join(out) + "\n"


def keep_together(tex):
    # forbid page breaks inside tables: end every longtable row with \\*
    def fix_table(m):
        return re.sub(r" \\\\$", r" \\\\*", m.group(0), flags=re.M)
    tex = re.sub(r"\\begin\{longtable\}.*?\\end\{longtable\}", fix_table, tex, flags=re.S)
    # and inside code blocks
    tex = tex.replace(r"\begin{verbatim}", r"\par\noindent\begin{minipage}{\linewidth}\begin{verbatim}")
    tex = tex.replace(r"\end{verbatim}", r"\end{verbatim}\end{minipage}")
    return tex


def main():
    md = prepare_markdown((ROOT / "REPORT.md").read_text())
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "report.md").write_text(md)
        subprocess.run(["pandoc", str(tmp / "report.md"), "-s", "-o", str(tmp / "report.tex")], check=True)
        tex = keep_together((tmp / "report.tex").read_text())
        # figure paths in REPORT.md are relative to the project root
        tex = tex.replace("{results/figures/", "{" + str(ROOT / "results/figures") + "/")
        (tmp / "report.tex").write_text(tex)
        for _ in range(2):
            subprocess.run(["xelatex", "-interaction=nonstopmode", "-halt-on-error", "report.tex"],
                           cwd=tmp, check=True, stdout=subprocess.DEVNULL)
        shutil.copy(tmp / "report.pdf", ROOT / "REPORT.pdf")
    print(f"wrote {ROOT / 'REPORT.pdf'}")


if __name__ == "__main__":
    main()
