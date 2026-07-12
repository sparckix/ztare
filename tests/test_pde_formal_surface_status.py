from ztare.pde.formal_surface_status import (
    build_pde_formal_surface_map,
    normalize_pde_formal_surface_record,
    render_pde_formal_surface_map,
)


def test_formal_surface_map_distinguishes_status_and_required_gaps() -> None:
    surface_map = build_pde_formal_surface_map(
        [
            {
                "primitive_id": "sobolev_trace",
                "status": "lean_statement_only",
                "statement": "theorem sobolev_trace : True := by trivial",
                "lean_file": "PDE/SobolevTrace.lean",
            },
            {
                "primitive_id": "annular_riesz_l1",
                "status": "lean_proof_complete",
                "lean_decl": "annular_riesz_l1",
                "lean_file": "PDE/Riesz.lean",
                "compile_result": {"success": True},
            },
            {
                "primitive_id": "validated_tail_bound",
                "status": "numerical_certificate",
                "certificate_artifact": "certs/tail.json",
                "validator": "interval-tail-validator-v1",
            },
        ],
        target="annular operator payment",
        required_primitives=("sobolev_trace", "caccioppoli_energy"),
        source_profile="toy_pde",
    )

    assert surface_map["schema"] == "pde-formal-surface-map-v1"
    assert surface_map["status_counts"] == {
        "lean_proof_complete": 1,
        "lean_statement_only": 1,
        "numerical_certificate": 1,
    }
    assert surface_map["missing_required_primitives"] == ["caccioppoli_energy"]
    assert surface_map["incomplete_records"] == []
    assert "add formal-surface row" in surface_map["next_required_actions"][0]


def test_formal_surface_row_marks_missing_evidence_without_proof_credit() -> None:
    row = normalize_pde_formal_surface_record(
        {
            "primitive_id": "dg_moser_harnack",
            "status": "lean_proof_complete",
            "lean_decl": "dg_moser_harnack",
        }
    )

    assert row["evidence_complete"] is False
    assert row["missing_evidence"] == [
        "lean_file",
        "proof_artifact_or_compile_success",
    ]

    rendered = render_pde_formal_surface_map(
        build_pde_formal_surface_map([row])
    )
    assert "inventory_only_no_proof_credit" in rendered
    assert "dg_moser_harnack" in rendered
