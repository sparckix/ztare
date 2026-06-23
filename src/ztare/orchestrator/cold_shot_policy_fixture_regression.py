from __future__ import annotations

from pathlib import Path
import tempfile

from ztare.orchestrator.cold_shot_policy import (
    route_cold_shot_families,
    write_policy_artifacts,
)


def run_cold_shot_policy_fixture_regression() -> dict[str, object]:
    cases: list[dict[str, object]] = []

    r1 = {
        "enable_cold_llm_erdos_seed": True,
        "rubric_mode": "newton",
        "cage_meta": {"class": "nd_features"},
    }
    d1 = route_cold_shot_families(
        project="demo",
        rubric_data=r1,
        lifecycle="pre_iter_1",
    )
    cases.append({
        "case_id": "erdos_flag_selects_de_anchor_only",
        "passed": d1.selected_families == ["de_anchor_seed"],
        "selected": d1.selected_families,
    })

    r2 = {
        "enable_cold_shot_seed": True,
        "rubric_mode": "newton",
        "cage_meta": {"class": "nd_features"},
    }
    d2 = route_cold_shot_families(
        project="demo",
        rubric_data=r2,
        lifecycle="pre_iter_1",
    )
    cases.append({
        "case_id": "physics_seed_requires_lagrangian_or_invariant_mode",
        "passed": "physics_lagrangian_seed" not in d2.selected_families,
        "selected": d2.selected_families,
    })

    r3 = {
        "enable_cold_shot_seed": True,
        "enable_lagrangian_derivation": True,
        "rubric_mode": "newton",
        "rubric_modes": ["invariant_search"],
        "cage_meta": {"class": "physics_law"},
    }
    d3 = route_cold_shot_families(
        project="demo",
        rubric_data=r3,
        lifecycle="pre_iter_1",
    )
    cases.append({
        "case_id": "physics_seed_selects_when_variational_flags_present",
        "passed": d3.selected_families == ["physics_lagrangian_seed"],
        "selected": d3.selected_families,
    })

    r4 = {
        "cold_shot": {
            "mode": "advisory",
            "force_families": ["structural_seed"],
            "disabled_families": ["de_anchor_seed"],
        },
        "enable_cold_llm_erdos_seed": True,
        "cage_meta": {"class": "nd_features"},
    }
    d4 = route_cold_shot_families(
        project="demo",
        rubric_data=r4,
        lifecycle="pre_iter_1",
    )
    cases.append({
        "case_id": "force_and_disable_are_honored",
        "passed": d4.selected_families == ["structural_seed"],
        "selected": d4.selected_families,
    })

    with tempfile.TemporaryDirectory() as td:
        out = write_policy_artifacts(workspace_dir=Path(td), decision=d4)
        cases.append({
            "case_id": "policy_writes_json_and_jsonl",
            "passed": out.exists() and (Path(td) / "cold_shot_runs.jsonl").exists(),
            "policy_path": str(out),
        })

    return {
        "suite": "cold_shot_policy_fixture_regression",
        "passed": all(bool(c.get("passed")) for c in cases),
        "cases": cases,
    }


if __name__ == "__main__":
    import json

    summary = run_cold_shot_policy_fixture_regression()
    print(json.dumps(summary, indent=2, sort_keys=True))
    raise SystemExit(0 if summary["passed"] else 1)

