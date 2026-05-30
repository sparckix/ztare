#!/usr/bin/env python3
"""Run a small public demo of ZTARE's evaluation-failure discipline.

The demo is intentionally model-free and fast. It runs three restored
case-study reproducers and checks for the expected demotion/catch signal in
each output. The goal is not to represent the current frontier engine or
exercise the full live LLM loop; it is to give a new reader one reliable
command that shows the repo's core epistemic style: green-looking checks can
pass while the real structural question fails.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
PYTHON = os.environ.get("PYTHON", sys.executable)


CASES = [
    {
        "name": "rank_deficient_bootstrap",
        "path": "papers/case_studies/rank_deficient_reproducer.py",
        "must_contain": [
            "Check 1 passed, Check 2 failed.",
            "alpha/beta ratio (identifiable combination)",
        ],
        "lesson": "Bootstrap-under-noise can be basin stability, not identifiability.",
    },
    {
        "name": "evidence_grid_underdetermination",
        "path": "papers/case_studies/evidence_grid_underdetermination_reproducer.py",
        "must_contain": [
            "Both forms PASS the standard battery",
            "Only Form B (Planck) PASSES the farther-tail discriminator.",
        ],
        "lesson": "A holdout can generalize within the wrong structural family.",
    },
    {
        "name": "evidence_enrichment_saturation",
        "path": "papers/case_studies/evidence_enrichment_saturation_reproducer.py",
        "must_contain": [
            "Gate verdict -- Weibull: PASS",
            "A discriminator calibrated for hypothesis pair A",
        ],
        "lesson": "Evidence enrichment can change the hypothesis pair.",
    },
]


def run_case(case: dict[str, object]) -> dict[str, object]:
    path = REPO / str(case["path"])
    env = dict(os.environ)
    env["PYTHONWARNINGS"] = "ignore::RuntimeWarning"
    proc = subprocess.run(
        [PYTHON, str(path)],
        cwd=REPO,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    output = proc.stdout + "\n" + proc.stderr
    missing = [needle for needle in case["must_contain"] if needle not in output]
    ok = proc.returncode == 0 and not missing
    return {
        "name": case["name"],
        "ok": ok,
        "returncode": proc.returncode,
        "path": case["path"],
        "lesson": case["lesson"],
        "missing": missing,
        "stderr_lines": [line for line in proc.stderr.splitlines() if line.strip()],
    }


def main() -> int:
    results = [run_case(case) for case in CASES]
    ok = all(result["ok"] for result in results)
    payload = {
        "ok": ok,
        "demo": "model_free_evaluation_failure_demo",
        "cases": results,
        "interpretation": (
            "The demo passes when each small reproducer surfaces the intended "
            "form-vs-intent failure rather than merely running without error."
        ),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
