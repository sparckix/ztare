from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from ztare.common.content_bound_evidence import (
    ContentBoundEvidenceError,
    EvidenceAuthority,
    replay_content_bound_evidence,
)
from ztare.common.content_identity import content_sha256
from ztare.leanmill import carried_theorem_ratification as ratification
from ztare.leanmill import filtered_evidence_authority as bridge
from ztare.leanmill.filtered_evidence_authority import (
    FilteredEvidenceAuthorityError,
    make_content_bound_evidence_from_governed_ratification,
    replay_content_bound_evidence_from_governed_ratification,
)
from ztare.leanmill.ratification_policy import (
    TARGET_GOVERNANCE_AUTHORITIES,
    TARGET_GOVERNANCE_AUTHORITY_ROSTER_SHA256,
)
from ztare.leanmill.solver.proof_margin_of_safety import (
    build_conclusion_discrimination_probes,
)


POSED = """import Mathlib

namespace AlienValuation

theorem support_rate : (2 : ℚ) ≤ 4 / 2 := by
  sorry

end AlienValuation
"""
PROOF = "by\n  norm_num"
TARGET = "AlienValuation.support_rate"
GOAL = ": (2 : ℚ) ≤ 4 / 2"


def _toolchain(tag: str = "stable") -> dict[str, object]:
    core: dict[str, object] = {
        "schema": "leanmill.closure_toolchain_identity.v1",
        "project": "alien",
        "lean_toolchain": tag,
        "lean_toolchain_sha256": content_sha256(tag),
        "lean_version": f"Lean {tag}",
        "lean_version_sha256": content_sha256(f"Lean {tag}"),
        "project_file_sha256s": {"lean-toolchain": content_sha256(tag)},
        "package_revisions": {},
        "complete": True,
    }
    return {**core, "identity_sha256": content_sha256(core)}


def _kernel(*_args, **_kwargs) -> dict[str, object]:
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


def _mnc(closure: str, target: str, *_args, **_kwargs) -> dict[str, object]:
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
    identity = _toolchain()
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
        lambda _root: deepcopy(identity),
    )
    monkeypatch.setattr(
        bridge,
        "closure_toolchain_identity",
        lambda _root: deepcopy(identity),
    )


def _ratified_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[dict[str, object], Path, Path]:
    _install_positive_boundary(monkeypatch)
    certificates = tmp_path / "certificates.jsonl"
    parity = tmp_path / "parity.jsonl"
    result = ratification.ratify_carried_theorem(
        TARGET,
        POSED,
        PROOF,
        GOAL,
        lean_root=tmp_path,
        run_id="filtered-authority-test",
        provider_label="test_carried_artifact",
        certificate_ledger=certificates,
        parity_ledger=parity,
    )
    assert result["outcome"] == "closed"
    return result, certificates, parity


def _bridge_kwargs(
    result: dict[str, object],
    certificates: Path,
    parity: Path,
    tmp_path: Path,
) -> dict[str, object]:
    return {
        "certificate_ledger": certificates,
        "governed_record_sha256": result[
            "closure_certificate_record_sha256"
        ],
        "parity_ledger": parity,
        "target": TARGET,
        "expected_signature": GOAL,
        "posed_source": POSED,
        "proof_text": PROOF,
        "goal": GOAL,
        "lean_root": tmp_path,
        "expected_provider": "test_carried_artifact",
    }


def _rewrite_single_record(path: Path, mutate) -> tuple[dict[str, object], str]:
    row = json.loads(path.read_text(encoding="utf-8"))
    mutate(row)
    path.write_text(json.dumps(row, sort_keys=True) + "\n", encoding="utf-8")
    return row, content_sha256(row)


def test_governed_bridge_is_the_only_positive_formal_replay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, certificates, parity = _ratified_fixture(tmp_path, monkeypatch)
    kwargs = _bridge_kwargs(result, certificates, parity, tmp_path)
    receipt = make_content_bound_evidence_from_governed_ratification(**kwargs)

    assert receipt.authority is EvidenceAuthority.FORMAL_KERNEL
    assert receipt.subject_id == TARGET
    assert receipt.conclusion() == {
        "ratified": True,
        "target": TARGET,
        "target_signature_sha256": json.loads(
            receipt.authority_binding_json or "{}"
        )["target_signature_sha256"],
    }
    with pytest.raises(ContentBoundEvidenceError) as error:
        replay_content_bound_evidence(receipt)
    assert error.value.code == "formal_kernel_authority_requires_ratification"
    assert replay_content_bound_evidence_from_governed_ratification(
        receipt,
        **kwargs,
    ) == receipt


@pytest.mark.parametrize(
    ("field", "replacement"),
    (
        ("target", "AlienValuation.other"),
        ("expected_signature", ": True"),
        ("posed_source", POSED + "\n-- crossed source\n"),
        ("proof_text", "by\n  exact True.intro"),
        ("goal", ": True"),
    ),
)
def test_bridge_rejects_cross_theorem_source_proof_and_goal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    replacement: str,
) -> None:
    result, certificates, parity = _ratified_fixture(tmp_path, monkeypatch)
    kwargs = _bridge_kwargs(result, certificates, parity, tmp_path)
    kwargs[field] = replacement
    with pytest.raises(FilteredEvidenceAuthorityError) as error:
        make_content_bound_evidence_from_governed_ratification(**kwargs)
    assert error.value.code == "governed_ratification_replay_failed"


def test_bridge_rejects_stale_toolchain(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, certificates, parity = _ratified_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(
        bridge,
        "closure_toolchain_identity",
        lambda _root: _toolchain("changed"),
    )
    with pytest.raises(FilteredEvidenceAuthorityError) as error:
        make_content_bound_evidence_from_governed_ratification(
            **_bridge_kwargs(result, certificates, parity, tmp_path)
        )
    assert error.value.code == "stale_toolchain_identity"


def test_bridge_rejects_unpersisted_kernel_parity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, certificates, parity = _ratified_fixture(tmp_path, monkeypatch)
    _row, digest = _rewrite_single_record(
        certificates,
        lambda row: row.__setitem__("kernel_parity_record_persisted", False),
    )
    kwargs = _bridge_kwargs(result, certificates, parity, tmp_path)
    kwargs["governed_record_sha256"] = digest
    with pytest.raises(FilteredEvidenceAuthorityError) as error:
        make_content_bound_evidence_from_governed_ratification(**kwargs)
    assert error.value.code == "kernel_parity_not_persisted"


def test_bridge_rejects_failed_governance_kernel(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, certificates, parity = _ratified_fixture(tmp_path, monkeypatch)

    def fail_kernel(row: dict[str, object]) -> None:
        governance = row["governance"]
        assert isinstance(governance, dict)
        kernel = governance["governance_kernel"]
        assert isinstance(kernel, dict)
        kernel["passed"] = False

    _row, digest = _rewrite_single_record(certificates, fail_kernel)
    kwargs = _bridge_kwargs(result, certificates, parity, tmp_path)
    kwargs["governed_record_sha256"] = digest
    with pytest.raises(FilteredEvidenceAuthorityError) as error:
        make_content_bound_evidence_from_governed_ratification(**kwargs)
    assert error.value.code == "governed_ratification_replay_failed"


def test_bridge_rejects_failed_axiom_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, certificates, parity = _ratified_fixture(tmp_path, monkeypatch)

    def fail_axioms(row: dict[str, object]) -> None:
        validation = row["solver_validation"]
        assert isinstance(validation, dict)
        receipts = validation["receipts"]
        assert isinstance(receipts, dict)
        axiom = receipts["axiom_allowlist_receipt"]
        assert isinstance(axiom, dict)
        axiom["passed"] = False

    _row, digest = _rewrite_single_record(certificates, fail_axioms)
    kwargs = _bridge_kwargs(result, certificates, parity, tmp_path)
    kwargs["governed_record_sha256"] = digest
    with pytest.raises(FilteredEvidenceAuthorityError) as error:
        make_content_bound_evidence_from_governed_ratification(**kwargs)
    assert error.value.code == "governed_ratification_replay_failed"


def test_bridge_rejects_tampered_recorded_toolchain_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, certificates, parity = _ratified_fixture(tmp_path, monkeypatch)

    def tamper_toolchain(row: dict[str, object]) -> None:
        toolchain = row["toolchain_identity"]
        assert isinstance(toolchain, dict)
        toolchain["project"] = "crossed"

    _row, digest = _rewrite_single_record(certificates, tamper_toolchain)
    kwargs = _bridge_kwargs(result, certificates, parity, tmp_path)
    kwargs["governed_record_sha256"] = digest
    with pytest.raises(FilteredEvidenceAuthorityError) as error:
        make_content_bound_evidence_from_governed_ratification(**kwargs)
    assert error.value.code == "toolchain_identity_digest_mismatch"


def test_bridge_rejects_tampered_kernel_parity_record(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, certificates, parity = _ratified_fixture(tmp_path, monkeypatch)

    def cross_parity(row: dict[str, object]) -> None:
        row["source_sha256"] = "f" * 64
        core = {key: value for key, value in row.items() if key != "record_sha256"}
        row["record_sha256"] = content_sha256(core)

    parity_row, parity_digest = _rewrite_single_record(parity, cross_parity)
    assert parity_row["record_sha256"] == parity_digest or (
        parity_row["record_sha256"] == content_sha256({
            key: value
            for key, value in parity_row.items()
            if key != "record_sha256"
        })
    )

    def bind_new_parity(row: dict[str, object]) -> None:
        row["kernel_parity_record_sha256"] = parity_row["record_sha256"]

    _certificate, certificate_digest = _rewrite_single_record(
        certificates, bind_new_parity
    )
    kwargs = _bridge_kwargs(result, certificates, parity, tmp_path)
    kwargs["governed_record_sha256"] = certificate_digest
    with pytest.raises(FilteredEvidenceAuthorityError) as error:
        make_content_bound_evidence_from_governed_ratification(**kwargs)
    assert error.value.code == "kernel_parity_crossed_certificate"


def test_bridge_replay_rejects_a_crossed_formal_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, certificates, parity = _ratified_fixture(tmp_path, monkeypatch)
    kwargs = _bridge_kwargs(result, certificates, parity, tmp_path)
    receipt = make_content_bound_evidence_from_governed_ratification(**kwargs)
    crossed = deepcopy(receipt)
    object.__setattr__(crossed, "receipt_sha256", "f" * 64)
    with pytest.raises(FilteredEvidenceAuthorityError) as error:
        replay_content_bound_evidence_from_governed_ratification(
            crossed,
            **kwargs,
        )
    assert error.value.code == "formal_kernel_receipt_mismatch"
