#!/usr/bin/env python3
"""Render REPORT.md and docs/GUIDE.md to PDF (pandoc -> LaTeX -> xelatex).

Usage: python3 scripts/make_pdf.py
"""
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DOCS = [
    # source, output, title, subtitle, table of contents
    ("REPORT.md", "REPORT.pdf", "Implementing and Evaluating the TAGE Branch Predictor",
     "Course project P14, Advanced Computer Architecture", False),
    ("docs/GUIDE.md", "docs/GUIDE.pdf", "The Complete Beginner's Guide to the TAGE Project",
     "Everything behind course project P14, explained from scratch", True),
]

META = r"""---
title: "{title}"
subtitle: "{subtitle}"
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
toc-depth: 2
header-includes:
  - \usepackage{{float}}
  - \floatplacement{{figure}}{{H}}
  - \setlength{{\parskip}}{{0.45em}}
  - \setlength{{\parindent}}{{0pt}}
---
"""

# glyphs Charter lacks
GLYPHS = {"→": r"$\rightarrow$", "⊕": r"$\oplus$", "≪": r"$\ll$"}


def prepare_markdown(text, title, subtitle):
    lines = text.splitlines()
    # drop the title block; it comes from META
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
    return META.format(title=title, subtitle=subtitle) + "\n".join(out) + "\n"


def keep_together(tex):
    # forbid page breaks inside short tables: end every longtable row with \\*
    # (long ones may break, so they start right under their heading)
    def fix_table(m):
        if len(re.findall(r" \\\\$", m.group(0), flags=re.M)) > 20:
            return m.group(0)
        return re.sub(r" \\\\$", r" \\\\*", m.group(0), flags=re.M)
    tex = re.sub(r"\\begin\{longtable\}.*?\\end\{longtable\}", fix_table, tex, flags=re.S)
    # and inside code blocks
    tex = tex.replace(r"\begin{verbatim}", r"\par\noindent\begin{minipage}{\linewidth}\begin{verbatim}")
    tex = tex.replace(r"\end{verbatim}", r"\end{verbatim}\end{minipage}")
    # keep headings with what follows: break the page first if less than ~8 lines remain
    tex = tex.replace(r"\begin{document}", NEEDSPACE + r"\begin{document}", 1)
    # (not for a subsection right under a section heading: that would split the two headings)
    lines = tex.split("\n")
    prev = ""
    for i, line in enumerate(lines):
        if re.match(r"\\(sub)?section\{", line) and not (line.startswith(r"\sub") and prev.startswith(r"\section{")):
            lines[i] = r"\Needspace{8\baselineskip}" + line
        if line.strip():
            prev = line
    return "\n".join(lines)


# minimal version of the needspace package, which TeX Live basic lacks
NEEDSPACE = r"""\makeatletter
\newcommand{\Needspace}[1]{\par\begingroup\dimen@=#1\relax\dimen@ii=\pagegoal
  \advance\dimen@ii-\pagetotal\ifdim\dimen@>\dimen@ii\ifdim\dimen@ii>\z@\vfil\fi\penalty-\@M\fi\endgroup}
\makeatother
"""


def build(src, out, title, subtitle, toc):
    src, out = ROOT / src, ROOT / out
    md = prepare_markdown(src.read_text(), title, subtitle)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "doc.md").write_text(md)
        cmd = ["pandoc", str(tmp / "doc.md"), "-s", "-o", str(tmp / "doc.tex")] + (["--toc"] if toc else [])
        subprocess.run(cmd, check=True)
        (tmp / "doc.tex").write_text(keep_together((tmp / "doc.tex").read_text()))
        # run from the source's folder so its relative image paths resolve
        for _ in range(2):
            subprocess.run(["xelatex", "-interaction=nonstopmode", "-halt-on-error", f"-output-directory={tmp}",
                            str(tmp / "doc.tex")], cwd=src.parent, check=True, stdout=subprocess.DEVNULL)
        missing = sorted(set(re.findall(r"Missing character: There is no (\S+)", (tmp / "doc.log").read_text())))
        if missing:
            print(f"warning: {src.name}: font lacks {' '.join(missing)}")
        shutil.copy(tmp / "doc.pdf", out)
    print(f"wrote {out.relative_to(ROOT)}")


def main():
    for doc in DOCS:
        build(*doc)


if __name__ == "__main__":
    main()
