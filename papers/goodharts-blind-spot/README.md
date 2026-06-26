# BlindSpot-Bench: Measuring the Oversight Gap Exactly

Clean public source bundle for the paper. The code and the released **BlindSpot-Bench** benchmark are maintained in a separate repository (the source of truth); this directory is the flagship public mirror of the paper itself. The earlier "Goodhart's Blind Spot" version is archived under `old/`.

Files:
- `draft.md`, working markdown draft (canonical text)
- `figures/`, the nine figures referenced in the draft
- `main.tex`, LaTeX source generated from `draft.md` (XeLaTeX)
- `refs.bib`, bibliography
- `main.pdf`, public mirror PDF

One-line summary: a three-layer testbed makes the LLM **oversight gap** (overseer belief minus ground truth) an exactly computed number; under a gamed channel the gap opens as a threshold and **localizes** by probe *stability*, the locus fingerprints the agent (withhold vs. fabricate), it is observable without ground truth, and the pattern reproduces in a second non-economy world and under a non-LLM optimizer.

<!-- AUTO-INDEX:START (managed by scripts/public/gen_folder_index.py, edit prose OUTSIDE this block) -->
<!-- AUTO-INDEX:END -->
