"""Identity-complete birth transition for agent-authored AxiomPack candidates."""
from __future__ import annotations

from copy import deepcopy
import json
from typing import Any, Mapping

from ztare.leanmill.formal_verification_provider import sha256_ref


CANDIDATE_BIRTH_SCHEMA = "leanmill.axiom_pack_candidate_birth.v1"
CANDIDATE_CAPABILITY_BLOCKER_SCHEMA = (
    "leanmill.axiom_pack_candidate_capability_blocker.v1"
)
CANDIDATE_NO_CANDIDATE_SCHEMA = "leanmill.axiom_pack_candidate_no_candidate.v1"


def _digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256_ref(payload)


def _candidate_capability_blocker(
    *,
    stage: str,
    source_receipt_sha256: str,
    missing: list[str],
    failures: list[str] | None = None,
) -> dict[str, Any]:
    def owner(field: str) -> str:
        if field.endswith(".escalation") or field.endswith(".task_manifest"):
            return "axiom_pack_campaign_admission"
        if "semantic" in field:
            return "semantic_fidelity_checker"
        return "typed_axiom_proposer"

    core = {
        "schema": CANDIDATE_CAPABILITY_BLOCKER_SCHEMA,
        "status": "blocked_missing_capability",
        "stage": stage,
        "source_receipt_sha256": source_receipt_sha256,
        "missing_capabilities": [
            {"field": field, "owner": owner(field)} for field in missing
        ],
        "next_required_field": missing[0] if missing else "",
        "failures": list(failures or ()),
        "can_persist_pack": False,
        "promotion_status": "blocked_before_quarantine",
        "frontier_theorem_certificate_consumed": False,
        "proof_credit_eligible": False,
        "theorem_campaign_admissible": False,
    }
    return {**core, "receipt_sha256": _digest(core)}


def _candidate_no_candidate(
    *, source_receipt_sha256: str, reason: str
) -> dict[str, Any]:
    core = {
        "schema": CANDIDATE_NO_CANDIDATE_SCHEMA,
        "status": "no_candidate",
        "stage": "candidate_authoring",
        "source_receipt_sha256": source_receipt_sha256,
        "reason": reason,
        "can_persist_pack": False,
        "next_action": "typed_navigation_feedback",
        "frontier_theorem_certificate_consumed": False,
        "proof_credit_eligible": False,
        "theorem_campaign_admissible": False,
    }
    return {**core, "receipt_sha256": _digest(core)}


def _candidate_base_identity(pack: Any) -> dict[str, Any]:
    """Return the executable base identity carried by a candidate at birth."""

    from ztare.leanmill.axiom_pack import _pack_formal_theory
    from ztare.leanmill.theory_ir import theory_content_hash

    signature, base_axioms, _candidate_axioms = _pack_formal_theory(pack)
    return {
        "extends_theory": pack.extends_theory,
        "mode": "typed" if base_axioms else "explicit_empty",
        "base_theory_resolved": pack.base_theory_resolved is True,
        "signature_sha256": signature.content_hash,
        "base_axiom_sha256s": sorted(axiom.content_hash for axiom in base_axioms),
        "base_theory_digest": theory_content_hash(signature, base_axioms),
    }


def verify_axiom_pack_candidate_birth(
    value: Mapping[str, Any] | None,
) -> tuple[bool, list[str]]:
    """Replay the content identity of a typed, quarantined candidate birth."""

    from ztare.leanmill.axiom_authority import pack_digest
    from ztare.leanmill.axiom_pack import AxiomPack, _pack_formal_theory

    row = dict(value or {})
    required = {
        "schema",
        "status",
        "source_receipt",
        "source_receipt_sha256",
        "source_pack_ref",
        "pack_digest",
        "pack",
        "base_identity",
        "typed_candidate_evidence",
        "agent_blueprint_trial",
        "generation",
        "promotion_status",
        "frontier_theorem_certificate_consumed",
        "proof_credit_eligible",
        "theorem_campaign_admissible",
        "receipt_sha256",
    }
    if set(row) != required:
        return False, ["candidate_birth.fields"]
    core = {key: child for key, child in row.items() if key != "receipt_sha256"}
    failures: list[str] = []
    checks = {
        "schema": row.get("schema") == CANDIDATE_BIRTH_SCHEMA,
        "status": row.get("status") == "candidate_born",
        "source_receipt_sha256": isinstance(row.get("source_receipt_sha256"), str)
        and str(row["source_receipt_sha256"]).startswith("sha256:"),
        "receipt_sha256": row.get("receipt_sha256") == _digest(core),
        "promotion_status": row.get("promotion_status") == "quarantined",
        "frontier_theorem_certificate_consumed": row.get(
            "frontier_theorem_certificate_consumed"
        )
        is False,
        "proof_credit_eligible": row.get("proof_credit_eligible") is False,
        "theorem_campaign_admissible": row.get("theorem_campaign_admissible")
        is False,
    }
    failures.extend(
        f"candidate_birth.{name}" for name, passed in checks.items() if not passed
    )
    source_receipt = row.get("source_receipt")
    if not isinstance(source_receipt, Mapping):
        failures.append("candidate_birth.source_receipt")
    elif _digest(dict(source_receipt)) != row.get("source_receipt_sha256"):
        failures.append("candidate_birth.source_receipt_sha256")
    pack_row = row.get("pack")
    if not isinstance(pack_row, Mapping):
        return False, [*failures, "candidate_birth.pack"]
    try:
        pack = AxiomPack.from_json(dict(pack_row))
        _pack_formal_theory(pack)
        expected_base = _candidate_base_identity(pack)
    except (TypeError, ValueError) as exc:
        return False, [*failures, f"candidate_birth.pack:{exc}"]
    if row.get("pack_digest") != pack_digest(pack):
        failures.append("candidate_birth.pack_digest")
    if row.get("source_pack_ref") not in pack.provenance:
        failures.append("candidate_birth.source_pack_ref")
    if row.get("base_identity") != expected_base:
        failures.append("candidate_birth.base_identity")
    evidence = row.get("typed_candidate_evidence")
    if not isinstance(evidence, list) or not evidence:
        failures.append("candidate_birth.typed_candidate_evidence")
    elif isinstance(source_receipt, Mapping):
        result = source_receipt.get("result")
        source_evidence = (
            result.get("typed_axiom_proposals")
            if isinstance(result, Mapping)
            else None
        )
        if evidence != source_evidence:
            failures.append("candidate_birth.typed_candidate_evidence_source")
    trial = row.get("agent_blueprint_trial")
    if not isinstance(trial, Mapping) or trial.get("construction_ready") is not True:
        failures.append("candidate_birth.agent_blueprint_trial")
    generation = row.get("generation")
    if not isinstance(generation, Mapping) or generation.get("ok") is not True:
        failures.append("candidate_birth.generation")
    elif generation.get("candidate_count") != len(pack.candidate_axioms):
        failures.append("candidate_birth.generation.candidate_count")
    return not failures, failures


def materialize_typed_axiom_pack_candidate(
    *,
    base_blueprint: Any,
    source_receipt: Mapping[str, Any],
    trusted_semantic_fidelity_public_key_pem: str | None,
    expected_semantic_fidelity_verifier_ref: str | None,
) -> dict[str, Any]:
    """Create one identity-complete quarantined pack from checked typed proposals."""

    from dataclasses import replace

    from ztare.leanmill.axiom_authority import pack_digest
    from ztare.leanmill.axiom_pack import (
        AxiomPackBlueprint,
        blueprint_from_agent_isomorphism_receipt,
        generate_candidate_axiom_pack,
    )

    receipt = deepcopy(dict(source_receipt))
    source_receipt_sha256 = _digest(receipt)
    result = receipt.get("result") if isinstance(receipt.get("result"), Mapping) else {}
    typed_rows = result.get("typed_axiom_proposals")
    if receipt.get("status") == "no_candidates":
        return _candidate_no_candidate(
            source_receipt_sha256=source_receipt_sha256,
            reason=str(result.get("outcome_detail") or "no executable candidate authored"),
        )
    if receipt.get("status") == "language_capability_gap":
        missing = result.get("missing_capabilities")
        missing_fields = (
            [str(value) for value in missing]
            if isinstance(missing, list) and missing
            else ["producer_output.typed_axiom_proposals[*].axiom_formula_json"]
        )
        return _candidate_capability_blocker(
            stage="executable_language",
            source_receipt_sha256=source_receipt_sha256,
            missing=missing_fields,
            failures=[str(result.get("outcome_detail") or "formula IR unavailable")],
        )
    if receipt.get("status") != "ok":
        return _candidate_capability_blocker(
            stage="source_receipt",
            source_receipt_sha256=source_receipt_sha256,
            missing=["producer_receipt.status=ok"],
            failures=[f"source_receipt_status:{receipt.get('status') or 'missing'}"],
        )
    orchestration = receipt.get("orchestration")
    if isinstance(orchestration, Mapping) and orchestration.get("calibration_only") is True:
        return _candidate_capability_blocker(
            stage="producer_identity",
            source_receipt_sha256=source_receipt_sha256,
            missing=["producer_receipt.orchestration.calibration_only=false"],
            failures=["calibration_receipt_cannot_birth_campaign_candidate"],
        )
    if not isinstance(typed_rows, list) or not typed_rows:
        return _candidate_capability_blocker(
            stage="executable_language",
            source_receipt_sha256=source_receipt_sha256,
            missing=["producer_output.result.typed_axiom_proposals"],
            failures=["prose_only_candidate_output"],
        )
    if not trusted_semantic_fidelity_public_key_pem:
        return _candidate_capability_blocker(
            stage="semantic_fidelity_authority",
            source_receipt_sha256=source_receipt_sha256,
            missing=["candidate_birth.trusted_semantic_fidelity_public_key_pem"],
        )

    trial = blueprint_from_agent_isomorphism_receipt(
        base_blueprint,
        receipt,
        trusted_semantic_fidelity_public_key_pem=(
            trusted_semantic_fidelity_public_key_pem
        ),
        expected_semantic_fidelity_verifier_ref=(
            expected_semantic_fidelity_verifier_ref
        ),
    )
    if trial.get("construction_ready") is not True:
        admission = trial.get("typed_candidate_admission")
        rejected = admission.get("rejected") if isinstance(admission, Mapping) else []
        return _candidate_capability_blocker(
            stage="typed_candidate_admission",
            source_receipt_sha256=source_receipt_sha256,
            missing=["producer_output.result.typed_axiom_proposals[*].admitted"],
            failures=[json.dumps(rejected, sort_keys=True, separators=(",", ":"))],
        )

    source_pack_ref = f"axiom-pack-proposal:{source_receipt_sha256.removeprefix('sha256:')}"
    blueprint = AxiomPackBlueprint.from_json(trial["blueprint"])
    blueprint = replace(
        blueprint,
        provenance=[*blueprint.provenance, source_pack_ref],
    )
    trial = {**trial, "blueprint": blueprint.to_json()}
    pack, generation = generate_candidate_axiom_pack(
        blueprint,
        isomorphism_receipt=receipt,
        trusted_semantic_fidelity_public_key_pem=(
            trusted_semantic_fidelity_public_key_pem
        ),
    )
    if generation.get("ok") is not True:
        return _candidate_capability_blocker(
            stage="pack_generation",
            source_receipt_sha256=source_receipt_sha256,
            missing=["candidate_birth.executable_pack"],
            failures=[
                str(value)
                for value in generation.get("typed_blueprint_construction", {}).get(
                    "failures", ()
                )
            ],
        )

    core = {
        "schema": CANDIDATE_BIRTH_SCHEMA,
        "status": "candidate_born",
        "source_receipt": receipt,
        "source_receipt_sha256": source_receipt_sha256,
        "source_pack_ref": source_pack_ref,
        "pack_digest": pack_digest(pack),
        "pack": pack.to_json(),
        "base_identity": _candidate_base_identity(pack),
        "typed_candidate_evidence": deepcopy(list(typed_rows)),
        "agent_blueprint_trial": trial,
        "generation": generation,
        "promotion_status": "quarantined",
        "frontier_theorem_certificate_consumed": False,
        "proof_credit_eligible": False,
        "theorem_campaign_admissible": False,
    }
    born = {**core, "receipt_sha256": _digest(core)}
    ok, failures = verify_axiom_pack_candidate_birth(born)
    if not ok:
        return _candidate_capability_blocker(
            stage="candidate_birth_replay",
            source_receipt_sha256=source_receipt_sha256,
            missing=["candidate_birth.identity_complete"],
            failures=failures,
        )
    return born


__all__ = [
    "CANDIDATE_BIRTH_SCHEMA",
    "CANDIDATE_CAPABILITY_BLOCKER_SCHEMA",
    "CANDIDATE_NO_CANDIDATE_SCHEMA",
    "materialize_typed_axiom_pack_candidate",
    "verify_axiom_pack_candidate_birth",
]
