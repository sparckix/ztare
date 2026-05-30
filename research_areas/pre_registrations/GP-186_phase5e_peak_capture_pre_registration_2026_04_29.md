# GP-186 Phase 5e Peak-Capture Pre-Registration

Opened: 2026-04-29 10:52:00
Status: active

Hypothesis

The `chiral_torus_knot` Phase 5d fragmentation may reflect a discretization-horizon failure rather than physical loss of coherence. If so, a narrow rerun with peak-state capture should preserve the localized intensification signal while yielding component bounding boxes, local cubes, and strain/rotation diagnostics sufficient for a later targeted micro-grid follow-up.

Eigenquestion

Can we capture enough spatial state at the Phase 5d knot peak to distinguish "real fragmented core" from "grid-limited sub-grid collapse" in the next numerical slice, without paying for another broad search?

Discriminating test

Run the knot branch only at `N=384,512` with `baseline` and `strict_dealias_055`, but save peak-state local cubes and thresholded component boxes at `99%` and `99.5%` of instantaneous `|omega|_max`, plus local strain/rotation diagnostics.

Success criterion

Phase 5e succeeds if every successful run writes:

- standard Phase 5d diagnostics
- peak snapshot summary into JSONL
- compressed sidecar capture with local `u`, `omega`, `|omega|`, threshold masks
- component bounding boxes at `99%` and `99.5%`
- peak local velocity-gradient / strain / rotation tensors

Failure criterion

Phase 5e fails if the peak-capture layer itself is unstable, non-finite, or too memory-heavy to run at the target resolutions on the chosen GPU.

Do-not-do

- Do not widen the ansatz search.
- Do not route into Lean from these numerics.
- Do not claim that capturing local cubes resolves the singularity question by itself.
