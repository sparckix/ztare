from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from ztare.leanmill import carried_theorem_ratification as ratification
from ztare.leanmill.governed_ratification import (
    resolve_content_addressed_ratification_record,
    validate_governed_ratification_record,
)
from ztare.leanmill.ratification_policy import (
    FINAL_RATIFICATION_AUTHORITIES,
    TARGET_GOVERNANCE_AUTHORITIES,
    TARGET_GOVERNANCE_AUTHORITY_ROSTER_SHA256,
)
from ztare.leanmill.solver.proof_margin_of_safety import (
    build_conclusion_discrimination_probes,
)


POSED = """import Mathlib

namespace Demo

theorem target : True := by
  sorry

end Demo
"""
PROOF = "by\n  trivial"
TARGET = "Demo.target"
GOAL = ": True"


def _kernel(*_args, **_kwargs) -> dict:
    return {
        "available": True,
        "passed": True,
        "flags": [],
        "confirmed": [],
        "unavailable_organs": [],
        "policy_profile": "target_ratification",
        "required_authorities": sorted(TARGET_GOVERNANCE_AUTHORITIES),
        "authority_disposition": {
            authority: "passed" for authority in TARGET_GOVERNANCE_AUTHORITIES
        },
        "authority_roster_sha256": TARGET_GOVERNANCE_AUTHORITY_ROSTER_SHA256,
        "detail": {"statement_integrity": {"ok": True}},
    }


def _mnc(closure: str, target: str, *_args, **_kwargs) -> dict:
    evidence, _positive, _negative = build_conclusion_discrimination_probes(
        closure, target
    )
    return {
        **evidence,
        "status": "pass",
        "passed": True,
        "discriminating": True,
        "differential": "confirmed",
        "positive_compiled": True,
        "negative_compiled": False,
        "interpretation": "positive compiles; negated conclusion does not",
    }


def _install_positive_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ratification, "ensure_elan_on_path", lambda: None)
    monkeypatch.setattr(
        ratification,
        "run_lake_compile_source",
        lambda *_args, **_kwargs: (True, "compiled"),
    )
    monkeypatch.setattr(ratification, "conclusion_discrimination_control", _mnc)
    monkeypatch.setattr(
        ratification,
        "audit_axioms_subset",
        lambda *_args, **_kwargs: (True, False, ["propext"]),
    )
    monkeypatch.setattr(ratification, "run_anti_laundering_kernel", _kernel)
    monkeypatch.setattr(
        ratification,
        "closure_toolchain_identity",
        lambda _root: {
            "schema": "leanmill.closure_toolchain_identity.v1",
            "complete": True,
            "identity_sha256": "a" * 64,
        },
    )


def test_ratifies_and_persists_one_content_bound_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_positive_boundary(monkeypatch)
    certificate_ledger = tmp_path / "certificates.jsonl"
    parity_ledger = tmp_path / "parity.jsonl"

    result = ratification.ratify_carried_theorem(
        TARGET,
        POSED,
        PROOF,
        GOAL,
        lean_root=tmp_path,
        run_id="ratify-test",
        provider_label="test_carried_artifact",
        certificate_ledger=certificate_ledger,
        parity_ledger=parity_ledger,
    )

    primary = result["results"][0]
    assert primary["outcome"] == "closed"
    assert result["provider_calls"] == 0
    assert result["governance_ratification_eligible"] is True
    assert primary["providers_tried"] == [{
        "provider": "test_carried_artifact",
        "outcome": "compiled",
        "compile_ok": True,
        "provider_wallclock_s": primary["provider_wallclock_s"],
        "agent_kind": "preverified_champion",
    }]

    _path, record = resolve_content_addressed_ratification_record(
        certificate_ledger,
        result["closure_certificate_record_sha256"],
    )
    validate_governed_ratification_record(
        record,
        target=TARGET,
        expected_signature=GOAL,
        posed_source=POSED,
        proof_text=PROOF,
        goal=GOAL,
        expected_provider="test_carried_artifact",
    )
    assert len(certificate_ledger.read_text().splitlines()) == 1
    assert len(parity_ledger.read_text().splitlines()) == 1


def test_authority_unavailability_cannot_mint_certificate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_positive_boundary(monkeypatch)
    monkeypatch.setattr(
        ratification,
        "run_anti_laundering_kernel",
        lambda *_args, **_kwargs: {
            "available": False,
            "passed": None,
            "flags": ["governance_organ_unavailable"],
            "confirmed": [],
            "unavailable_organs": ["statement_integrity"],
            "detail": {},
        },
    )
    ledger = tmp_path / "certificates.jsonl"
    result = ratification.ratify_carried_theorem(
        TARGET,
        POSED,
        PROOF,
        GOAL,
        lean_root=tmp_path,
        certificate_ledger=ledger,
        parity_ledger=tmp_path / "parity.jsonl",
    )

    assert result["results"][0]["outcome"] == "governance_unavailable"
    assert result["governance_ratification_eligible"] is False
    assert not ledger.exists()


def test_compile_failure_still_emits_complete_authority_algebra(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ratification, "ensure_elan_on_path", lambda: None)
    monkeypatch.setattr(
        ratification,
        "run_lake_compile_source",
        lambda *_args, **_kwargs: (False, "type mismatch"),
    )
    result = ratification.ratify_carried_theorem(
        TARGET,
        POSED,
        PROOF,
        GOAL,
        lean_root=tmp_path,
    )

    validation = result["results"][0]["contract_validation"]
    assert result["results"][0]["outcome"] == "failed_compile"
    assert set(validation["final_required_authorities"]) == (
        FINAL_RATIFICATION_AUTHORITIES
    )
    assert set(validation["final_authority_disposition"]) == (
        FINAL_RATIFICATION_AUTHORITIES
    )
    assert set(validation["receipts"]).issuperset({
        "kernel_compile_receipt",
        "matched_negative_control_receipt",
        "axiom_allowlist_receipt",
        "governance_kernel_receipt",
    })


def test_target_identity_is_required_before_compile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        ratification,
        "run_lake_compile_source",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("compile must follow target binding")
        ),
    )
    with pytest.raises(ValueError, match="absent or ambiguous"):
        ratification.ratify_carried_theorem(
            "Demo.missing",
            POSED,
            PROOF,
            GOAL,
            lean_root=tmp_path,
        )


def test_import_surface_excludes_proof_search_and_rd() -> None:
    code = """
import json, sys
import ztare.leanmill.carried_theorem_ratification
forbidden = [
    name for name in sys.modules
    if name in {
        'ztare.leanmill.solver.solver_core',
        'ztare.leanmill.solver.contract',
        'ztare.leanmill.solver.deterministic',
        'ztare.leanmill.solver.llm_provers',
        'ztare.leanmill.solver.governed_dag_search',
        'ztare.leanmill.solver.agentic_leaf',
        'ztare.leanmill.solver.prompts',
        'ztare.leanmill.prompts',
    }
    or name.startswith('ztare.leanmill.providers')
    or name.startswith('ztare.research_director')
]
print(json.dumps(sorted(forbidden)))
"""
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=True,
        env={**__import__("os").environ, "PYTHONPATH": "src"},
    )
    assert json.loads(proc.stdout) == []
