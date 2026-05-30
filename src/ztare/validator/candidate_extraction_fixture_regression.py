from __future__ import annotations

import json

from src.ztare.validator.candidate_extraction import extract_best_python_candidate


def run_fixture_regression() -> dict[str, object]:
    cases = []

    skeleton_then_real = """Thesis text.

```python
def I_model(features, params=None):
    return ...
```

Real suite:

```python
import math
MODEL_PARAMS = {}
PARAMETER_NAMES = ["a"]
INIT_RANGE = {"a": (0.0, 1.0)}
PARAMETRIC_FORM = "params['a'] * features['x']"
def I_model(features, params=None):
    p = params if params is not None else MODEL_PARAMS
    return p.get("a", 1.0) * features["x"]
```
"""
    r = extract_best_python_candidate(skeleton_then_real)
    cases.append({
        "case_id": "selects_real_block_over_skeleton",
        "passed": (
            r.python_code is not None
            and "PARAMETRIC_FORM" in r.python_code
            and "return ..." not in r.python_code
            and r.auto_repaired
        ),
        "selected_score": r.selected_score,
    })

    unlabeled = """Candidate:

```
MODEL_PARAMS = {}
PARAMETER_NAMES = ["a"]
PARAMETRIC_FORM = "params['a']"
def I_model(features, params=None):
    return 1.0
```
"""
    r = extract_best_python_candidate(unlabeled)
    cases.append({
        "case_id": "accepts_unlabeled_test_model_block",
        "passed": r.python_code is not None and r.num_python_blocks == 0 and r.auto_repaired,
        "selected_score": r.selected_score,
    })

    prose_only = "No code here."
    r = extract_best_python_candidate(prose_only)
    cases.append({
        "case_id": "prose_only_returns_none",
        "passed": r.python_code is None and r.clean_thesis == prose_only,
        "selected_score": r.selected_score,
    })

    return {
        "suite": "candidate_extraction_fixture_regression",
        "all_passed": all(bool(c["passed"]) for c in cases),
        "num_cases": len(cases),
        "num_passed": sum(1 for c in cases if c["passed"]),
        "results": cases,
    }


def main() -> int:
    summary = run_fixture_regression()
    print(json.dumps(summary, indent=2))
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
