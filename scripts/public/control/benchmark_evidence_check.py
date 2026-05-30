#!/usr/bin/env python3
"""Check historical public benchmark evidence used in docs and claim surfaces."""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PYSR_FULL = REPO / "papers/experimental_math_letter/pysr_baseline_full.json"
CONSTRAINT_MEMORY_SUMMARY = (
    REPO / "benchmarks/constraint_memory/runs/20260404_195100/metrics_summary.json"
)


def read_json(path: Path) -> Any:
    if not path.exists():
        raise SystemExit(f"missing benchmark artifact: {path.relative_to(REPO)}")
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"benchmark evidence check failed: {message}")


def check_pysr() -> dict[str, Any]:
    payload = read_json(PYSR_FULL)
    rows = {row["key"]: row for row in payload.get("results", [])}
    required = {"s1", "s2", "s3", "lucky", "hr"}
    missing = sorted(required.difference(rows))
    require(not missing, f"PySR baseline missing rows: {missing}")

    null_verdicts = {key: rows[key]["pysr_gated_verdict"] for key in ["s1", "s2", "s3"]}
    for key, verdict in null_verdicts.items():
        require(verdict.startswith("null-under-gate"), f"expected {key} to null, got {verdict!r}")

    lucky = rows["lucky"]
    lucky_farther = float(lucky["pysr_farther_tail"]["max_abs"])
    lucky_threshold = float(lucky["gate_threshold"])
    require(lucky["pysr_gated_verdict"].startswith("form-passes-gate"), "Lucky should pass")
    require(lucky_farther <= lucky_threshold, "Lucky farther-tail should be within threshold")

    hr = rows["hr"]
    hr_farther = float(hr["pysr_farther_tail"]["max_abs"])
    hr_threshold = float(hr["gate_threshold"])
    require(hr["pysr_gated_verdict"].startswith("null-under-gate"), "HR should null")
    require(hr_farther > hr_threshold, "HR PySR farther-tail should exceed threshold")

    s2_holdout = rows["s2"]["pysr_holdout"]["max_abs"]
    require(isinstance(s2_holdout, float) and math.isnan(s2_holdout), "S2 holdout should be NaN")

    return {
        "artifact": str(PYSR_FULL.relative_to(REPO)),
        "null_under_gate_rows": null_verdicts,
        "lucky": {
            "equation": lucky["pysr_equation"],
            "max_abs_oos": lucky_farther,
            "threshold": lucky_threshold,
        },
        "hardy_ramanujan": {
            "equation": hr["pysr_equation"],
            "max_abs_oos": hr_farther,
            "threshold": hr_threshold,
        },
    }


def check_constraint_memory() -> dict[str, Any]:
    payload = read_json(CONSTRAINT_MEMORY_SUMMARY)
    conditions = payload.get("conditions", {})
    a = conditions.get("A_baseline_soft_judge")
    b = conditions.get("B_deterministic_gates")
    c = conditions.get("C_gates_plus_primitives")
    require(a and b and c, "constraint-memory summary missing benchmark conditions")

    require(float(a["false_accept_rate"]) > 0.0, "baseline should have nonzero false accepts")
    require(float(b["false_accept_rate"]) == 0.0, "deterministic gates should remove false accepts")
    require(float(c["false_accept_rate"]) == 0.0, "gates plus primitives should keep false accepts at zero")
    require(float(c["false_reject_rate"]) == 0.0, "gates plus primitives should not reject good controls")
    require(
        float(c["exploit_detection_rate"]) >= float(a["exploit_detection_rate"]),
        "hardened condition should match or beat baseline exploit detection",
    )

    return {
        "artifact": str(CONSTRAINT_MEMORY_SUMMARY.relative_to(REPO)),
        "baseline_soft_judge": {
            "false_accept_rate": a["false_accept_rate"],
            "false_reject_rate": a["false_reject_rate"],
            "exploit_detection_rate": a["exploit_detection_rate"],
        },
        "deterministic_gates": {
            "false_accept_rate": b["false_accept_rate"],
            "false_reject_rate": b["false_reject_rate"],
            "exploit_detection_rate": b["exploit_detection_rate"],
        },
        "gates_plus_primitives": {
            "false_accept_rate": c["false_accept_rate"],
            "false_reject_rate": c["false_reject_rate"],
            "exploit_detection_rate": c["exploit_detection_rate"],
        },
    }


def build_payload() -> dict[str, Any]:
    return {
        "ok": True,
        "model_free": True,
        "claim_supported": "bounded public benchmark evidence for evaluator hardening",
        "pysr": check_pysr(),
        "constraint_memory": check_constraint_memory(),
        "non_claims": [
            "not a global SOTA claim",
            "not evidence that ZTARE beats all symbolic-regression systems",
            "not evidence that hard-problem campaigns are externally benchmarked",
            "not a benchmark of the current in-loop plus out-of-loop system",
        ],
    }


def main() -> int:
    print(json.dumps(build_payload(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
