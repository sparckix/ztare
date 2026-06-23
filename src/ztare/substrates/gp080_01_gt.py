"""GP-080 GT module — re-exports from gp080_tacrolimus_gt (Division A artifact).

Opaque slug: gp080_01_gt. Rubric points here; actual parameters live in
gp080_tacrolimus_gt.py (Division A, GT-aware). This file is Division B-safe
because it exposes no domain names or parameter values — only the callable API.
"""
from ztare.substrates.gp080_tacrolimus_gt import (  # noqa: F401
    evidence_grid,
    f_dominant,
    f_true,
    holdout_grid,
)
