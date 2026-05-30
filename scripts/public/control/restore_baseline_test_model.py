#!/usr/bin/env python3
"""Restore a project's test_model.py to an iter-0 placeholder.

Detects substrate type from the rubric (1D legacy vs N-D feature-dict
GP-156) and writes the appropriate placeholder. Called by `make
wipe-sandbox` after clearing eval state, so the next run starts from
a genuine clean checkpoint instead of re-scoring the prior champion's
form.

Usage:
    python scripts/public/control/restore_baseline_test_model.py <project_name>

The project name resolves to ``projects/<name>/`` and the rubric to
``rubrics/<name>.json`` per the standard layout.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


# 1D legacy substrate placeholder (pre-GP-156): operator authored a
# `def f(t: float) -> float` callable. Trivial constant fails holdout.
ONED_STUB = '''"""Baseline test model — trivial constant. Always fails holdout gate."""


def f(t: float) -> float:
    return 0.0
'''

# N-D feature-dict substrate placeholder (GP-156+): I_model takes a
# features dict and uses a PARAMETRIC_FORM string the apparatus fits.
# Trivial linear form is contract-compliant but scientifically wrong;
# iter-0 scores 0, iter-1 mutator overwrites with a real form.
ND_STUB = '''"""Iter-0 placeholder — operator-blank state for fresh run (N-D feature-dict substrate).

The apparatus mutator overwrites this file each iter via mutate_thesis ->
write_python_suite. This placeholder declares a contract-compliant but
trivially-wrong I_model so iter-0 scores 0 and iter-1 starts from a
clean champion.
"""
import math

PARAMETRIC_FORM = "params['c_A'] * features['x']"
PARAMETER_NAMES = ['c_A']
MODEL_PARAMS = {'c_A': 1.0}


def I_model(features, params=None):
    p = params if params is not None else MODEL_PARAMS
    c_A = p.get('c_A', 1.0)
    x = features.get('x', 0.0)
    return c_A * x


# Canonical aliases — gate harnesses may call f(), model(), or I_model()
f = I_model
model = I_model
'''


def is_nd_substrate(rubric_path: Path) -> bool:
    """Return True if the rubric declares an N-D feature-dict substrate.

    Two signals (either suffices):
      - ``enable_fit_primitive_features: true`` (GP-156 mutator interface)
      - ``cage_meta.class`` in {"nd_features", "feature_dict"}
    """
    if not rubric_path.exists():
        return False
    try:
        rd = json.loads(rubric_path.read_text(encoding="utf-8"))
    except Exception:
        return False
    if rd.get("enable_fit_primitive_features"):
        return True
    cage_meta = rd.get("cage_meta") or {}
    if cage_meta.get("class") in ("nd_features", "feature_dict"):
        return True
    return False


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"Usage: {argv[0]} <project_name>", file=sys.stderr)
        return 2
    project_name = argv[1].strip().rstrip("/")
    if project_name.startswith("projects/"):
        project_name = project_name[len("projects/"):]
    proj_dir = REPO_ROOT / "projects" / project_name
    rubric_path = REPO_ROOT / "rubrics" / f"{project_name}.json"
    if not proj_dir.is_dir():
        print(f"ERROR: {proj_dir} does not exist", file=sys.stderr)
        return 1
    nd = is_nd_substrate(rubric_path)
    test_model_path = proj_dir / "test_model.py"
    test_model_path.write_text(ND_STUB if nd else ONED_STUB, encoding="utf-8")
    label = "N-D feature-dict" if nd else "1D legacy"
    print(f"  test_model.py restored ({label} substrate placeholder)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
