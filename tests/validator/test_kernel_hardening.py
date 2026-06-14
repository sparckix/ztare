from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_SRC = _REPO / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ztare.common.kernel_hardener import (
    GamingVector,
    load_catalog,
    record_vector,
    run_hardening,
)
from ztare.gates.autoresearch_gaming_gates import (
    detect_autoresearch_gaming_vectors,
    run_autoresearch_gaming_gates,
)
from ztare.gates.semantic_gaming_carrier import (
    detect_semantic_carriers,
    run_semantic_gaming_carrier_gates,
)
from src.ztare.gates.global_gates import run_global_gates
from ztare.validator.autoresearch_hardener import AutoresearchHardener
from ztare.validator.gaming_vector_meta_runner import (
    EXPECTED_PROMOTION_CONTRACT,
    StageSpec,
    _gaming_vector_promotion_contract,
    content_hash,
    ensure_project,
    evidence_path,
)


def test_shared_kernel_hardener_records_and_promotes_only_open_vectors(tmp_path: Path) -> None:
    catalog = tmp_path / "catalog.jsonl"

    class FakeHardener:
        substrate = "autoresearch"

        def __init__(self) -> None:
            self.registered: list[str] = []

        def mine(self, artifacts):
            return [
                GamingVector(
                    name="open_vector",
                    substrate="autoresearch",
                    category="NOVEL:test",
                    mechanism="still escapes",
                    proposed_gate="deterministic test gate",
                ),
                GamingVector(
                    name="fixed_vector",
                    substrate="autoresearch",
                    category="NOVEL:test",
                    mechanism="already covered",
                    already_gated_by="existing_gate",
                ),
            ]

        def reproduce(self, vector: GamingVector) -> bool:
            return not vector.already_gated_by

        def derive_gate(self, vector: GamingVector) -> str:
            return vector.proposed_gate

        def register_gate(self, vector: GamingVector) -> bool:
            self.registered.append(vector.name)
            return True

    hardener = FakeHardener()
    result = run_hardening(hardener, None, promote=True, catalog=catalog)

    assert result["mined"] == 2
    assert result["new_to_catalog"] == 2
    assert result["promoted_gates"] == ["open_vector"]
    assert [row.name for row in load_catalog(catalog)] == ["open_vector", "fixed_vector"]
    assert record_vector(GamingVector("open_vector", "autoresearch", "x", "y"), catalog) is False


def test_autoresearch_gaming_gate_blocks_fixture_shape(tmp_path: Path) -> None:
    source = "Z = 1\nscore = Z + 1\nassert Z > 0\nassert score > 1\n"
    found = {spec.vector for spec in detect_autoresearch_gaming_vectors(source)}

    assert "definitional_tautology_self_confirming_metric" in found

    project = tmp_path / "project"
    project.mkdir()
    (project / "test_model.py").write_text(source, encoding="utf-8")
    results = run_autoresearch_gaming_gates(project)

    assert any(
        result["name"] == "global_project_sweep_definitional_tautology"
        and result["hard_fail"]
        and not result["passed"]
        for result in results
    )


def test_autoresearch_gaming_gate_disable_requires_reason(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()

    missing_reason = run_autoresearch_gaming_gates(
        project,
        {"disable_autoresearch_gaming_gates": True},
    )
    assert missing_reason == [
        {
            "name": "global_autoresearch_gaming_vectors",
            "passed": False,
            "actual": "disabled_without_reason",
            "threshold": "non-empty disable_autoresearch_gaming_gates_reason",
            "reason": "disable_autoresearch_gaming_gates requires an explicit reason",
            "penalty": 0,
            "hard_fail": True,
            "source": "autoresearch_gaming_gates",
        }
    ]

    with_reason = run_autoresearch_gaming_gates(
        project,
        {
            "disable_autoresearch_gaming_gates": True,
            "disable_autoresearch_gaming_gates_reason": "non-Python literature review substrate",
        },
    )
    assert with_reason[0]["passed"] is True
    assert with_reason[0]["actual"] == "disabled"
    assert "non-Python literature review substrate" in with_reason[0]["reason"]


def test_semantic_carrier_routes_scope_overclaim(tmp_path: Path) -> None:
    thesis = "This local mapping of received-token states proves whole-system silent failure safety."
    evidence = "The evidence only tests a local component, but the claim is end-to-end."

    found = {spec.vector for spec in detect_semantic_carriers(thesis, evidence, "")}
    assert "scope_overclaim_local_to_systemic" in found

    project = tmp_path / "project"
    project.mkdir()
    results = run_semantic_gaming_carrier_gates(project, thesis_text=thesis, evidence_text=evidence)

    assert any(
        result["name"] == "global_semantic_scope_overclaim_carrier"
        and result["hard_fail"]
        and not result["passed"]
        for result in results
    )


def test_semantic_carrier_disable_requires_reason(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()

    missing_reason = run_semantic_gaming_carrier_gates(
        project,
        {"disable_semantic_gaming_carrier": True},
    )
    assert missing_reason == [
        {
            "name": "global_semantic_gaming_carrier",
            "passed": False,
            "actual": "disabled_without_reason",
            "threshold": "non-empty disable_semantic_gaming_carrier_reason",
            "reason": "disable_semantic_gaming_carrier requires an explicit reason",
            "penalty": 0,
            "hard_fail": True,
            "source": "semantic_gaming_carrier",
        }
    ]

    with_reason = run_semantic_gaming_carrier_gates(
        project,
        {
            "disable_semantic_gaming_carrier": True,
            "disable_semantic_gaming_carrier_reason": "semantic review delegated to external signed receipt",
        },
    )
    assert with_reason[0]["passed"] is True
    assert with_reason[0]["actual"] == "disabled"
    assert "external signed receipt" in with_reason[0]["reason"]


def test_global_gates_run_under_src_package_import(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "test_model.py").write_text("MODEL_PARAMS = {}\n", encoding="utf-8")

    payload = run_global_gates(
        project,
        {
            "disable_autoresearch_gaming_gates": True,
            "disable_autoresearch_gaming_gates_reason": "import-context regression guard",
            "disable_semantic_gaming_carrier": True,
            "disable_semantic_gaming_carrier_reason": "import-context regression guard",
        },
        thesis_text="Bounded calibration claim.",
        evidence_text="Small calibration evidence surface.",
    )

    assert payload["source"] == "global_gates"
    assert payload["harness_invoked"] is True


def test_autoresearch_hardener_uses_incremental_manifest(tmp_path: Path) -> None:
    artifact = tmp_path / "debate.md"
    manifest = tmp_path / "mine_manifest.jsonl"
    artifact.write_text(
        "The thesis assumes uniqueness but provides no proof of uniqueness.",
        encoding="utf-8",
    )

    hardener = AutoresearchHardener()
    old_manifest = hardener.mine_manifest_path
    hardener.mine_manifest_path = manifest
    try:
        first = hardener.mine([artifact], incremental=True)
        second = hardener.mine([artifact], incremental=True)
    finally:
        hardener.mine_manifest_path = old_manifest

    assert any(vector.name == "uniqueness_gap" for vector in first)
    assert second == []
    assert manifest.exists()


def test_gaming_vector_promotion_contract_requires_scoped_receipt(
    tmp_path: Path,
    monkeypatch,
) -> None:
    catalog = tmp_path / "gaming_vector_catalog.jsonl"
    monkeypatch.setenv("ZTARE_GAMING_VECTOR_CATALOG", str(catalog))
    vector = GamingVector(
        name="definitional_tautology_self_confirming_metric",
        substrate="autoresearch",
        category="NOVEL:non_falsifiable_self_confirmation",
        mechanism="self-confirming metric",
        status="open",
    )
    catalog.write_text(json.dumps(vector.to_dict()) + "\n", encoding="utf-8")
    ensure_project(tmp_path)

    artifact = tmp_path / "fixture.py"
    artifact.write_text("Z = 1\nscore = Z + 1\nassert Z > 0\nassert score > 1\n", encoding="utf-8")
    receipt = {
        "vector": vector.name,
        "substrate": "autoresearch",
        "promotion_path": f"gaming_vector:autoresearch:{vector.name}",
        "evidence_mode": "deterministic_detector",
        "exposing_artifacts": [{"path": str(artifact), "sha": content_hash(artifact)}],
        "runtime_enforcement": {"name": "global_project_sweep_definitional_tautology", "wired": True},
        "regression": {"exposing_fixture_blocked": True, "good_controls_passed": True},
        "scope": {"vector_only": True},
        "test_result": {"passed": True},
        "promotion_recommendation": True,
    }
    evidence_path(tmp_path, vector.name).write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    stage = StageSpec(
        name="promote_test",
        item_number=1,
        priority="P0",
        contract_name=EXPECTED_PROMOTION_CONTRACT,
        details={
            "substrate": "autoresearch",
            "vector": vector.name,
            "evidence_path": f"evidence/{vector.name}.json",
            "promotion_path": f"gaming_vector:autoresearch:{vector.name}",
        },
    )

    assert _gaming_vector_promotion_contract(tmp_path, stage).verdict == "pass"

    receipt["promotion_path"] = "gaming_vector:autoresearch:wrong"
    evidence_path(tmp_path, vector.name).write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")

    assert _gaming_vector_promotion_contract(tmp_path, stage).verdict == "fail"
