import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from ztare.pde import cli as pde_cli  # noqa: E402
from ztare import cli as root_cli  # noqa: E402


def test_pde_cli_lists_registry_json(capsys) -> None:
    assert pde_cli.main(["gates", "--op", "pec_l", "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    gate_ids = {entry["gate_id"] for entry in payload["entries"]}

    assert payload["schema"] == "pde-gate-registry-v1"
    assert "G-PDE-ANALYTIC-SUBSTANCE" in gate_ids
    assert "G-PDE-EQUALITY-PROVENANCE" in gate_ids
    assert "G-PDE-OPERATOR-ADMISSIBILITY" in gate_ids


def test_pde_cli_status_reports_subkernel_ready(capsys) -> None:
    assert pde_cli.main(["status", "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"] == "pde-subkernel-status-v1"
    assert payload["ready"] is True
    assert payload["canonical_modules"]["registry"] == "ztare.pde.registry"
    assert payload["canonical_modules"]["ops"] == "ztare.pde.ops"
    assert "leanmill_service" in payload["service_boundaries"]


def test_pde_cli_completion_audit_reports_ready(capsys) -> None:
    assert pde_cli.main(["completion-audit", "--repo-root", ".", "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    check_ids = {row["check_id"] for row in payload["checks"]}

    assert payload["schema"] == "pde-kernel-completion-audit-v1"
    assert payload["passed"] is True
    assert "gate_bundle_summary_contract" in check_ids
    assert "readiness_canary_requires_core_gates" in check_ids


def test_pde_cli_emits_architecture_requirements(capsys) -> None:
    assert pde_cli.main(["requirements", "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    req_ids = {row["requirement_id"] for row in payload["requirements"]}

    assert payload["schema"] == "pde-architecture-requirements-v1"
    assert payload["status_counts"]["implemented"] >= 12
    assert "leanmill.failure.memory.adapter" in req_ids
    assert "pde.formal.surface.map" in req_ids
    assert "pde.physics.equality.plugins" in req_ids


def test_pde_cli_emits_readiness_receipt(capsys) -> None:
    assert pde_cli.main(["readiness", "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    gate_ids = {
        gate["gate_id"]
        for gate in payload["canary_work_order"]["gate_requirements"]
    }

    assert payload["schema"] == "pde-kernel-readiness-receipt-v1"
    assert payload["ready"] is True
    assert payload["target"] == "annular_bandlimited_riesz_l1_psd_trace_payment"
    assert "G-PDE-EQUALITY-PROVENANCE" in gate_ids
    assert "G-PDE-OPERATOR-ADMISSIBILITY" in gate_ids
    assert "G-OWNER-PREIMAGE-PREFIX" in gate_ids


def test_pde_cli_exposes_kernel_facade_verbs(capsys) -> None:
    assert pde_cli.main(["ops", "--op", "pec_l", "--json"]) == 0
    ops_payload = json.loads(capsys.readouterr().out)
    assert ops_payload["entries"][0]["op_id"] == "pec_l"

    assert (
        pde_cli.main(
            [
                "estimates",
                "--target",
                "annular_bandlimited_riesz_l1_psd_trace_payment",
                "--field",
                "projection",
                "--json",
            ]
        )
        == 0
    )
    estimate_payload = json.loads(capsys.readouterr().out)
    assert estimate_payload["skeletons"][0]["id"] == "projection_tail_invoice"

    assert pde_cli.main(["receipts", "--json"]) == 0
    receipt_payload = json.loads(capsys.readouterr().out)
    receipt_ids = {entry["receipt_id"] for entry in receipt_payload["entries"]}
    assert "work_unit:estimate_derivation" in receipt_ids

    assert pde_cli.main(["currency", "--target-currency", "radius_sum", "--json"]) == 0
    currency_payload = json.loads(capsys.readouterr().out)
    assert currency_payload["target_currency"] == "radius_sum"


def test_pde_cli_builds_work_order_json(capsys) -> None:
    assert (
        pde_cli.main(
            [
                "work-order",
                "--target",
                "annular Riesz payment",
                "--op",
                "pec_l",
                "--extra-gate",
                "G-PDE-THEOREM-APPLICABILITY",
                "--json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    gate_ids = {entry["gate_id"] for entry in payload["gate_requirements"]}

    assert payload["schema"] == "pde-leaf-work-order-v1"
    assert "G-PDE-THEOREM-APPLICABILITY" in gate_ids


def test_pde_cli_builds_focused_work_order_json(capsys) -> None:
    assert (
        pde_cli.main(
            [
                "work-order",
                "--target",
                "annular Riesz payment",
                "--op",
                "pec_l",
                "--only-gate",
                "G-PDE-ANALYTIC-SUBSTANCE",
                "--only-gate",
                "G-PDE-OPERATOR-ADMISSIBILITY",
                "--json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    gate_ids = [entry["gate_id"] for entry in payload["gate_requirements"]]

    assert gate_ids == [
        "G-PDE-ANALYTIC-SUBSTANCE",
        "G-PDE-OPERATOR-ADMISSIBILITY",
    ]
    assert any("only_gate_ids supplied" in note for note in payload["notes"])


def test_pde_cli_builds_work_order_with_process_contract_json(capsys) -> None:
    assert (
        pde_cli.main(
            [
                "work-order",
                "--target",
                "active Carleson budget identity",
                "--op",
                "pec_l",
                "--require-process-contract",
                "--pattern-action-contract-ref",
                "pattern.json",
                "--orchestration-contract-ref",
                "orch.json",
                "--pencil-artifact-ref",
                "pencil.md",
                "--json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    refs = {
        item["artifact_key"]: item["artifact_ref"]
        for item in payload["process_requirements"]
    }

    assert refs["pattern_action_contract"] == "pattern.json"
    assert refs["orchestration_contract"] == "orch.json"
    assert refs["pencil_artifact"] == "pencil.md"


def test_pde_cli_runs_gate_json(capsys) -> None:
    payload = {
        "witness_family": "annular low-high packet",
        "target_estimate_or_claim": "raw CZ pays annular Riesz payment",
        "amplitude_scaling": "lambda",
        "support_or_localization": "same annulus",
        "frequency_or_scale_regime": "low-high separated",
        "norm_or_quantity_profile": "pressure L^(3/2) vs trace variation",
        "hypotheses_preserved": ["local CZ estimate"],
        "conclusion_stressed_or_violated": ["annular payment"],
        "failure_mechanism": "unpaid projection leakage",
        "parameter_limit": "lambda -> infinity",
        "claim_boundary_update": "local CZ is not annular payment",
    }
    with tempfile.NamedTemporaryFile("w", suffix=".json") as handle:
        json.dump(payload, handle)
        handle.flush()

        assert (
            pde_cli.main(
                [
                    "run-gate",
                    "--gate-id",
                    "G-PDE-HOSTILE-WITNESS",
                    "--payload-json",
                    handle.name,
                    "--json",
                ]
            )
            == 0
        )

    result = json.loads(capsys.readouterr().out)
    assert result["schema"] == "pde-gate-run-result-v1"
    assert result["passed"] is True
    assert result["gate_id"] == "G-PDE-HOSTILE-WITNESS"


def test_pde_cli_runs_work_order_payload_bundle_json(capsys) -> None:
    work_order = {
        "schema": "pde-leaf-work-order-v1",
        "leaf_id": "pde.leaf.pec_e.hostile",
        "gate_requirements": [
            {"gate_id": "G-PDE-HOSTILE-WITNESS", "runner": "unused"}
        ],
    }
    payloads = {
        "G-PDE-HOSTILE-WITNESS": {
            "witness_family": "annular low-high packet",
            "target_estimate_or_claim": "raw CZ pays annular Riesz payment",
            "amplitude_scaling": "lambda",
            "support_or_localization": "same annulus",
            "frequency_or_scale_regime": "low-high separated",
            "norm_or_quantity_profile": "pressure L^(3/2) vs trace variation",
            "hypotheses_preserved": ["local CZ estimate"],
            "conclusion_stressed_or_violated": ["annular payment"],
            "failure_mechanism": "unpaid projection leakage",
            "parameter_limit": "lambda -> infinity",
            "claim_boundary_update": "local CZ is not annular payment",
        }
    }
    with tempfile.NamedTemporaryFile("w", suffix=".json") as work, tempfile.NamedTemporaryFile(
        "w", suffix=".json"
    ) as payload_file:
        json.dump(work_order, work)
        json.dump(payloads, payload_file)
        work.flush()
        payload_file.flush()

        assert (
            pde_cli.main(
                [
                    "run-work-order",
                    "--work-order-json",
                    work.name,
                    "--payloads-json",
                    payload_file.name,
                    "--json",
                ]
            )
            == 0
        )

    bundle = json.loads(capsys.readouterr().out)
    assert bundle["schema"] == "pde-leaf-gate-run-bundle-v1"
    assert bundle["passed"] is True
    assert bundle["summary"]["gate_count"] == 1
    assert bundle["summary"]["passed_gate_ids"] == ["G-PDE-HOSTILE-WITNESS"]


def test_pde_cli_run_work_order_text_prints_summary(capsys) -> None:
    work_order = {
        "schema": "pde-leaf-work-order-v1",
        "leaf_id": "pde.leaf.pec_l.incomplete",
        "gate_requirements": [
            {
                "gate_id": "G-PDE-EQUALITY-PROVENANCE",
                "runner": "ztare.gates.pde_equality_provenance_gate:run_pde_equality_provenance_gate",
                "input_shape_hint": "{}",
            }
        ],
    }
    payloads = {
        "G-PDE-EQUALITY-PROVENANCE": {
            "equality_target": "A = B",
            "left_stream": "A",
            "right_stream": "B",
            "provenance_kind": "record_field_projection",
            "constructor_or_theorem": "assumed carrier",
            "generated_fields": ["A", "B"],
            "source_binding": "not supplied",
            "anti_proxy_or_anti_laundering_fields": "not supplied",
            "hostile_packet_or_confuser": "proxy stream packet",
            "proof_boundary": "negative fixture",
            "field_projection_only": True,
        }
    }
    with tempfile.NamedTemporaryFile("w", suffix=".json") as work, tempfile.NamedTemporaryFile(
        "w", suffix=".json"
    ) as payload_file:
        json.dump(work_order, work)
        json.dump(payloads, payload_file)
        work.flush()
        payload_file.flush()

        assert (
            pde_cli.main(
                [
                    "run-work-order",
                    "--work-order-json",
                    work.name,
                    "--payloads-json",
                    payload_file.name,
                ]
            )
            == 1
        )

    out = capsys.readouterr().out
    assert "summary: gates=1 passed=0 failed=1 next=1" in out
    assert "rejected_substitutes: field_projection_only" in out


def test_pde_cli_builds_knowledge_context_json(capsys) -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".json") as theorem_db:
        json.dump(
            {
                "annular_profile": {
                    "requires": {"annular_bandlimit": True},
                    "concludes": {"usable": True},
                }
            },
            theorem_db,
        )
        theorem_db.flush()

        assert (
            pde_cli.main(
                [
                    "knowledge",
                    "--target",
                    "annular payment",
                    "--query",
                    "annular bandlimit",
                    "--theorem-db-json",
                    theorem_db.name,
                    "--available-json",
                    "{\"annular_bandlimit\": true}",
                    "--json",
                ]
            )
            == 0
        )

    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"] == "pde-knowledge-context-v1"
    assert payload["theorem_profile_cards"][0]["applicability"]["verdict"] == "MATCH"


def test_pde_cli_builds_formal_surface_map_json(capsys) -> None:
    record = {
        "primitive_id": "weak_solution_energy",
        "status": "lean_statement_only",
        "statement": "theorem weak_solution_energy : True := by trivial",
        "lean_file": "PDE/WeakSolution.lean",
    }
    with tempfile.NamedTemporaryFile("w", suffix=".json") as record_file:
        json.dump(record, record_file)
        record_file.flush()

        assert (
            pde_cli.main(
                [
                    "formal-surface",
                    "--target",
                    "formal PDE surface",
                    "--record-json",
                    record_file.name,
                    "--required",
                    "weak_solution_energy",
                    "--required",
                    "riesz_l1",
                    "--json",
                ]
            )
            == 0
        )

    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"] == "pde-formal-surface-map-v1"
    assert payload["missing_required_primitives"] == ["riesz_l1"]
    assert payload["records"][0]["evidence_complete"] is True


def test_root_cli_exposes_pde_command_in_help_and_completion(capsys) -> None:
    assert root_cli.main(["--help"]) == 0
    assert "pde" in capsys.readouterr().out

    assert root_cli.main(["completion", "bash"]) == 0
    completion = capsys.readouterr().out
    assert "pde)" in completion
    assert "completion-audit" in completion
    assert "readiness" in completion
    assert "knowledge" in completion
    assert "formal-surface" in completion
    assert "ops" in completion
    assert "currency" in completion
    assert "estimates" in completion
    assert "receipts" in completion
