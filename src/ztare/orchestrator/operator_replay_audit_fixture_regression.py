from __future__ import annotations

import json
import tempfile
from pathlib import Path

from src.ztare.orchestrator.operator_replay_audit import proposals_from_sources, write_replay_queue


def run_fixture_regression() -> dict[str, object]:
    cases = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "paper7_excerpt.md"
        source.write_text(
            """
The AQUAL run required an empty-box no-source Krylov background residual gate.
The large-box L=4 boundary test checked whether finite-box walls caused the UDG enhancement.
The rotation angle 45 test attacked tensor anisotropy and octant grid-locking.
The off-core background debt and mu profile must be reported with separator gain.
""",
            encoding="utf-8",
        )
        proposals = proposals_from_sources([source])
        templates = {p.to_record()["metadata"]["replay_template"] for p in proposals}
        cases.append({
            "case_id": "paper7_excerpt_recovers_gravity_operator_moves",
            "passed": {
                "gravity_empty_box_background_gate",
                "gravity_large_box_boundary_gate",
                "gravity_tensor_rotation_gate",
                "background_debt_ladder_gate",
            }.issubset(templates),
            "templates": sorted(templates),
        })

        project_dir = root / "projects" / "gp163d_unified_accel"
        out = write_replay_queue(project_dir, proposals)
        records = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
        cases.append({
            "case_id": "writes_replay_queue_as_typed_records",
            "passed": len(records) == len(proposals) and all(r["schema_version"] == 2 for r in records),
            "num_records": len(records),
        })

        generic_source = root / "generic_excerpt.md"
        generic_source.write_text(
            """
The holdout passed, but the coefficient may drift under farther-tail asymptotic
extrapolation. The prior run also showed an ontology trap / retrieval risk where
a named formula can be recognized instead of derived. We need BIC / MDL and
effective-K checks because score improvement can hide parameter laundering. The
validation split must audit distribution shift by class/regime. Cross-domain
duality claims require a shared primitive and non-shared physics license.
""",
            encoding="utf-8",
        )
        generic = proposals_from_sources([generic_source], project_override="gp154_scaling_law_exponents")
        generic_templates = {p.to_record()["metadata"]["replay_template"] for p in generic}
        cases.append({
            "case_id": "non_pde_replay_templates_are_project_overridable",
            "passed": {
                "generic_farther_tail_asymptotic_gate",
                "generic_retrieval_trap_gate",
                "generic_complexity_laundering_gate",
                "generic_distribution_shift_gate",
                "generic_cross_domain_transfer_license_gate",
            }.issubset(generic_templates)
            and {p.project for p in generic} == {"gp154_scaling_law_exponents"},
            "templates": sorted(generic_templates),
            "projects": sorted({p.project for p in generic}),
        })

        cross = proposals_from_sources([source], project_override="gp154_scaling_law_exponents")
        cross_templates = {p.to_record()["metadata"]["replay_template"] for p in cross}
        cases.append({
            "case_id": "domain_specific_templates_do_not_bleed_into_other_projects",
            "passed": not {
                "gravity_empty_box_background_gate",
                "gravity_large_box_boundary_gate",
                "gravity_tensor_rotation_gate",
            } & cross_templates,
            "templates": sorted(cross_templates),
        })

    return {
        "suite": "operator_replay_audit_fixture_regression",
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
