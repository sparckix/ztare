#!/usr/bin/env python3
"""Build the arxiv LaTeX source + PDF from nonmathlib4's cost-of-certainty.md.
Splits the markdown into title/subtitle/abstract/body so pandoc renders a real
paper (title block + \\begin{abstract}), then emits main.tex + main.pdf.
ponytail: pandoc does the md->tex lift; we only slice front-matter and set the
ztare-style article preamble via header include. Add a refs.bib only if we ever
switch from the inline reference list to \\cite."""
import re, subprocess, sys, pathlib

HERE = pathlib.Path(__file__).parent
SRC = pathlib.Path("<operator-home>/nonmathlib4/manuscript/cost-of-certainty.md")
txt = SRC.read_text(encoding="utf-8")
lines = txt.splitlines()

# title = first H1; subtitle = the italic line under it; abstract = between
# "## Abstract" and the first "---"; body = from "## 1." onward.
title = next(l[2:].strip() for l in lines if l.startswith("# "))
subtitle = ""
for l in lines[:6]:
    if l.startswith("*") and l.endswith("*") and len(l) > 2:
        subtitle = l.strip("*").strip()
        break

abs_start = next(i for i, l in enumerate(lines) if l.strip() == "## Abstract") + 1
abs_end = next(i for i in range(abs_start, len(lines)) if lines[i].strip() == "---")
abstract = "\n".join(lines[abs_start:abs_end]).strip()

body_start = next(i for i, l in enumerate(lines) if l.startswith("## 1."))
body = "\n".join(lines[body_start:]).strip()

# pandoc reads abstract/title from a YAML metadata file; keeps them out of body.
meta = HERE / "_meta.yaml"
def yblock(s):  # fold a multi-paragraph string into a YAML block scalar
    return "|\n" + "\n".join("  " + ln for ln in s.splitlines())
meta.write_text(
    f"---\ntitle: {title!r}\n"
    + (f"subtitle: {subtitle!r}\n" if subtitle else "")
    + f"author: Daniel Alami\ndate: July 2026\nabstract: {yblock(abstract)}\n---\n",
    encoding="utf-8",
)
(HERE / "_body.md").write_text(body, encoding="utf-8")

# ztare-style preamble additions + explicit math-operator glyph maps (bulletproof
# regardless of font coverage; letters gamma/pi/l-stroke/o-uml are covered by fontspec).
header = HERE / "_header.tex"
header.write_text(r"""
\usepackage{newunicodechar}
\newunicodechar{·}{\ensuremath{\cdot}}
\newunicodechar{−}{\ensuremath{-}}
\newunicodechar{≤}{\ensuremath{\leq}}
\newunicodechar{≥}{\ensuremath{\geq}}
\newunicodechar{∈}{\ensuremath{\in}}
\newunicodechar{⊆}{\ensuremath{\subseteq}}
\newunicodechar{∃}{\ensuremath{\exists}}
\newunicodechar{∧}{\ensuremath{\wedge}}
\newunicodechar{∨}{\ensuremath{\vee}}
\newunicodechar{→}{\ensuremath{\rightarrow}}
% Greek letters appear inside \texttt code spans (fee γ, prevalence π); the MONO font has no Greek,
% so route them through math mode too (renders in any surrounding font).
\newunicodechar{γ}{\ensuremath{\gamma}}
\newunicodechar{π}{\ensuremath{\pi}}
\usepackage{booktabs}
\usepackage{array}
\usepackage{microtype}
% Long snake_case / camelCase theorem names in narrow table columns overflow. seqsplit lets a monospace
% identifier break anywhere needed (only at line-end, so names that fit stay intact). Applied to TABLE cells
% only (post-processing below), so prose identifiers like `nonmathlib4` never break mid-word.
\usepackage{seqsplit}
% Prose snake_case names (e.g. no_history_enables_round_trip_arbitrage) also overflow at a line-end; allow a
% break after each underscore document-wide. Safe: only underscores break, so `nonmathlib4` stays whole.
\let\origunderscore\_
\renewcommand{\_}{\origunderscore\allowbreak}
% Keep the two wide tables inside the text block.
\let\oldlongtable\longtable
\AtBeginDocument{\setlength{\LTleft}{0pt}\setlength{\LTright}{0pt}}
""", encoding="utf-8")

common = [
    "pandoc", str(meta), str(HERE / "_body.md"),
    "--from", "gfm", "--standalone",
    "--pdf-engine=xelatex",
    "-V", "documentclass=article", "-V", "fontsize=11pt",
    "-V", "geometry:margin=1in",
    "-V", "colorlinks=true", "-V", "linkcolor=blue",
    "-V", "urlcolor=blue", "-V", "citecolor=blue",
    "-V", "linestretch=1.05",
    "-H", str(header),
]
subprocess.run(common + ["-o", str(HERE / "main.tex")], check=True)

# pandoc gives wide GFM tables natural-width `llll` columns → they overflow the text block. Rewrite the two
# longtable colspecs to WRAPPING `p{}` columns (summing < \textwidth) and drop them to \footnotesize. Positional:
# table 1 = "Where this work sits" (4 balanced cols), table 2 = filed results (long theorem + meaning cols).
tex = (HERE / "main.tex").read_text(encoding="utf-8")
def _p(*ws):
    return "{@{}" + "".join(r">{\raggedright\arraybackslash}p{" + f"{w}" + r"\textwidth}" for w in ws) + "@{}}"
_specs = iter([_p(0.16, 0.22, 0.22, 0.32), _p(0.12, 0.28, 0.42, 0.10)])
tex = re.sub(r"\{@\{\}llll@\{\}\}", lambda _m: next(_specs), tex, count=2)
tex = tex.replace(r"\begin{longtable}", r"{\footnotesize\setlength{\tabcolsep}{4pt}\begin{longtable}") \
         .replace(r"\end{longtable}", r"\end{longtable}}")
# make \texttt identifiers wrap INSIDE tables only (prose \texttt like `nonmathlib4` stays unbroken).
tex = re.sub(r"\\begin\{longtable\}.*?\\end\{longtable\}",
             lambda m: re.sub(r"\\texttt\{([^{}]*)\}", r"\\texttt{\\seqsplit{\1}}", m.group(0)),
             tex, flags=re.S)
(HERE / "main.tex").write_text(tex, encoding="utf-8")

# compile the PATCHED source (xelatex twice for the longtable width pass + refs/toc).
for _ in range(2):
    subprocess.run(["xelatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex"],
                   cwd=str(HERE), check=True, stdout=subprocess.DEVNULL)
print("wrote main.tex + main.pdf")
