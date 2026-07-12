"""Bounded provider-callback orchestration for typed AxiomPack proposals.

This module is deliberately model-agnostic.  The caller supplies provider
callbacks from the existing runtime registry; this boundary owns ordering,
payload minimization, manifest verification, and semantic-checker replay.
It emits a quarantined structural-isomorphism receipt consumable by
``blueprint_from_agent_isomorphism_receipt``.
"""
from __future__ import annotations

from copy import deepcopy
import json
from typing import Any, Callable, Mapping

from ztare.leanmill.axiom_yield import verify_shadow_task_manifest
from ztare.leanmill.formal_verification_provider import sha256_ref
from ztare.leanmill import prompts
from ztare.leanmill.typed_axiom_proposal import verify_semantic_fidelity_verdict
from ztare.leanmill.contracts.axiom_pack_transport import AxiomPackTransportContract


ORCHESTRATION_SCHEMA = "leanmill.axiom_pack_typed_orchestration.v1"
RECEIPT_SCHEMA = "leanmill.agent_tool.structural_isomorphism_receipt.v1"
_SENSITIVE_TOKENS = (
    "manifest",
    "heldout",
    "task_bytes",
    "task_id",
    "control",
    "witness",
    "private_key",
    "public_key",
    "checker",
    "verifier",
)


def _parse_json_object(raw: Any) -> dict[str, Any]:
    if isinstance(raw, Mapping):
        return deepcopy(dict(raw))
    text = str(raw or "").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        text = text.rsplit("```", 1)[0].strip()
    decoder = json.JSONDecoder()
    for start, character in enumerate(text):
        if character != "{":
            continue
        try:
            parsed, _end = decoder.raw_decode(text[start:])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    raise ValueError("structured provider returned no JSON object")


def render_typed_proposer_prompt(proposer_view: Mapping[str, Any]) -> str:
    """Render the only prompt a typed proposer needs; callers provide the model."""

    return prompts.AXIOM_PACK_TYPED_PROPOSER_PROMPT.format(
        proposer_view=json.dumps(
            dict(proposer_view), sort_keys=True, separators=(",", ":"), ensure_ascii=True
        )
    )


def make_json_proposer(call: Callable[[str], Any]) -> Callable[[Mapping[str, Any]], Mapping[str, Any]]:
    """Adapt an existing generic text dispatcher to the typed proposer callback."""

    def proposer(view: Mapping[str, Any]) -> Mapping[str, Any]:
        return _parse_json_object(call(render_typed_proposer_prompt(view)))

    return proposer


def make_contract_proposer(
    call: Callable[[str], Any],
    *,
    transport_contract: AxiomPackTransportContract,
) -> Callable[[Mapping[str, Any]], Mapping[str, Any]]:
    """Adapt a constrained shallow wire response to canonical proposal inputs."""

    def proposer(view: Mapping[str, Any]) -> Mapping[str, Any]:
        if _digest(dict(view)) != transport_contract.proposer_view_digest:
            raise ValueError("proposer view does not match frozen transport contract")
        return transport_contract.decode(call(transport_contract.render_prompt(view)))

    return proposer


def render_semantic_checker_prompt(source_conjecture: Any, typed_axiom_proposal: Any) -> str:
    return prompts.AXIOM_PACK_SEMANTIC_CHECKER_PROMPT.format(
        check_input=json.dumps(
            {"source_conjecture": source_conjecture, "typed_axiom_proposal": typed_axiom_proposal},
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
    )


def make_signed_semantic_checker(
    call: Callable[[str], Any],
    *,
    private_key_pem: str,
    verifier_ref: str,
) -> Callable[[Mapping[str, Any]], Mapping[str, Any]]:
    """Adapt a generic judge to a code-signed semantic checker callback."""

    from ztare.leanmill.typed_axiom_proposal import build_semantic_fidelity_verdict

    def checker(payload: Mapping[str, Any]) -> Mapping[str, Any]:
        source = payload["source_conjecture"]
        proposal = payload["typed_axiom_proposal"]
        judgment = _parse_json_object(call(render_semantic_checker_prompt(source, proposal)))
        verdict = build_semantic_fidelity_verdict(
            proposal,
            faithful=judgment.get("faithful") is True,
            rationale=str(judgment.get("rationale") or "").strip(),
            evidence_refs=[str(ref) for ref in judgment.get("evidence_refs") or []],
            private_key_pem=private_key_pem,
            verifier_ref=verifier_ref,
        )
        return {"semantic_fidelity_verdict": verdict.to_json()}

    return checker


def _canonicalize_proposer_proposal(
    source: Any,
    proposal: Any,
    proposer_view: Mapping[str, Any],
) -> Any:
    if not isinstance(proposal, Mapping):
        return proposal
    if {"schema", "source_conjecture_sha256", "theory_signature", "axiom"}.issubset(proposal):
        return dict(proposal)
    if not {"axiom", "nl_intent", "kill_condition"}.issubset(proposal):
        return dict(proposal)
    from ztare.leanmill.theory_ir import AxiomFormula, TheorySignature
    from ztare.leanmill.typed_axiom_proposal import build_typed_axiom_proposal

    signature_row = proposer_view.get("base_theory", {}).get("signature")
    if not isinstance(signature_row, Mapping):
        raise ValueError("proposer view lacks a frozen theory signature")
    built = build_typed_axiom_proposal(
        source_conjecture=source,
        theory_signature=TheorySignature.from_json(signature_row),
        axiom=AxiomFormula.from_json(proposal["axiom"]),
        nl_intent=str(proposal["nl_intent"]),
        kill_condition=str(proposal["kill_condition"]),
    )
    return built.to_json()


def _digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256_ref(payload)


def _sensitive_keys(value: Any, path: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key).lower()
            if any(token in key_text for token in _SENSITIVE_TOKENS):
                found.append(f"{path}.{key}" if path else str(key))
            found.extend(_sensitive_keys(child, f"{path}.{key}" if path else str(key)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_sensitive_keys(child, f"{path}[{index}]"))
    return found


def _verify_escalation_packet(packet: Mapping[str, Any]) -> list[str]:
    failures: list[str] = []
    if packet.get("schema") != "leanmill.axiom_pack_escalation_eligibility.v1":
        failures.append("escalation_schema")
    if packet.get("eligible") is not True:
        failures.append("escalation_not_eligible")
    if packet.get("routing_only") is not True:
        failures.append("routing_only_required")
    if packet.get("theory_mutation_allowed") is not False:
        failures.append("theory_mutation_forbidden")
    if packet.get("promotion_status") != "quarantined":
        failures.append("promotion_status")
    if packet.get("proof_credit_eligible") is not False:
        failures.append("proof_credit_forbidden")
    if packet.get("theorem_campaign_admissible") is not False:
        failures.append("campaign_admission_forbidden")
    required = packet.get("required_next_gates")
    if not isinstance(required, list):
        failures.append("required_next_gates")
    else:
        required_names = {
            str(row.get("requirement"))
            for row in required
            if isinstance(row, Mapping)
        }
        if "signed_unseen_task_manifest" not in required_names:
            failures.append("manifest_gate_missing")
        if "typed_axiom_proposals" not in required_names:
            failures.append("proposal_gate_missing")
        if any(
            isinstance(row, Mapping)
            and str(row.get("requirement"))
            in {"signed_unseen_task_manifest", "typed_axiom_proposals"}
            and row.get("satisfied") is not False
            for row in required
        ):
            failures.append("next_gate_already_satisfied")
    digest = packet.get("routing_receipt_digest")
    if not isinstance(digest, str):
        failures.append("routing_receipt_digest_missing")
    else:
        core = {key: value for key, value in packet.items() if key != "routing_receipt_digest"}
        if digest != _digest(core):
            failures.append("routing_receipt_digest")
    for field in ("base_theory_digest", "substrate_digest", "registered_family_digest"):
        if not isinstance(packet.get(field), str) or not packet[field].startswith("sha256:"):
            failures.append(field)
    return failures


def _rejected(
    *,
    stage: str,
    failures: list[str],
    escalation: Mapping[str, Any] | None,
    manifest_digest: str = "",
    proposer_view_digest: str = "",
    proposer_output_digest: str = "",
    rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "schema": ORCHESTRATION_SCHEMA,
        "ok": False,
        "stage": stage,
        "failures": failures,
        "escalation_digest": escalation.get("routing_receipt_digest", ""),
        "manifest_digest": manifest_digest,
        "proposer_view_digest": proposer_view_digest,
        "proposer_output_digest": proposer_output_digest,
        "receipt": {
            "schema": RECEIPT_SCHEMA,
            "status": "rejected",
            "mode": "conjecture",
            "trial_source": "typed_proposer_checker",
            "canonical_engine": "ztare.research_director.research_isomorphism",
            "result": {
                "candidate_count": len(rows or []),
                "typed_axiom_proposals": rows or [],
            },
            "proof_credit_eligible": False,
            "theorem_campaign_admissible": False,
            "can_mutate_substrate": False,
            "allowed_use": "quarantined_candidate_generation",
            "orchestration": {
                "schema": ORCHESTRATION_SCHEMA,
                "status": "rejected",
                "stage": stage,
                "failures": failures,
                "manifest_digest": manifest_digest,
                "proposer_view_digest": proposer_view_digest,
                "proposer_output_digest": proposer_output_digest,
            },
        },
    }


def orchestrate_typed_axiom_proposals(
    *,
    escalation: Mapping[str, Any] | None,
    proposer_view: Mapping[str, Any],
    task_manifest: Mapping[str, Any],
    trusted_manifest_public_key_pem: str,
    trusted_semantic_fidelity_public_key_pem: str,
    expected_semantic_fidelity_verifier_ref: str,
    proposer_fn: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    semantic_checker_fn: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    proposal_validator: Callable[[Mapping[str, Any]], None] | None = None,
    calibration_only: bool = False,
) -> dict[str, Any]:
    """Run the provider-independent typed proposal boundary.

    The manifest is verified before ``proposer_fn`` runs.  Neither callback
    receives the manifest or the trust keys.  A callback may use any existing
    model/provider runtime, but its output must satisfy the typed schemas.
    """

    escalation = dict(escalation or {})
    if calibration_only:
        metadata = task_manifest.get("metadata")
        manifest_core = metadata.get("manifest") if isinstance(metadata, Mapping) else None
        base_digest = manifest_core.get("base_theory_digest") if isinstance(manifest_core, Mapping) else ""
        escalation = {
            "base_theory_digest": base_digest,
            "routing_receipt_digest": "calibration-only",
        }
        valid_calibration_digest = (
            isinstance(base_digest, str)
            and (
                base_digest.startswith("sha256:")
                or (len(base_digest) == 64 and all(char in "0123456789abcdef" for char in base_digest))
            )
        )
        failures = [] if valid_calibration_digest else ["calibration_manifest_base_digest"]
    else:
        failures = _verify_escalation_packet(escalation)
    if failures:
        return _rejected(stage="escalation", failures=failures, escalation=escalation)
    if not isinstance(proposer_view, Mapping):
        return _rejected(
            stage="proposer_view", failures=["proposer_view_object_required"], escalation=escalation
        )
    sensitive = _sensitive_keys(proposer_view)
    if sensitive:
        return _rejected(
            stage="proposer_view",
            failures=[f"sensitive_proposer_fields:{','.join(sensitive[:8])}"],
            escalation=escalation,
        )
    proposer_view_copy = deepcopy(dict(proposer_view))
    proposer_view_digest = _digest(proposer_view_copy)
    manifest_ok, manifest_failures = verify_shadow_task_manifest(
        task_manifest,
        base_theory_digest=str(escalation["base_theory_digest"]),
        trusted_public_key_pem=trusted_manifest_public_key_pem,
    )
    manifest_digest = str(
        task_manifest.get("metadata", {}).get("manifest_digest")
        if isinstance(task_manifest.get("metadata"), Mapping)
        else ""
    )
    if not manifest_ok:
        return _rejected(
            stage="manifest", failures=manifest_failures, escalation=escalation,
            manifest_digest=manifest_digest, proposer_view_digest=proposer_view_digest,
        )
    try:
        proposer_output = proposer_fn(deepcopy(proposer_view_copy))
    except Exception as exc:  # noqa: BLE001
        return _rejected(
            stage="proposer", failures=[f"provider_exception:{type(exc).__name__}"],
            escalation=escalation, manifest_digest=manifest_digest,
            proposer_view_digest=proposer_view_digest,
        )
    if not isinstance(proposer_output, Mapping):
        return _rejected(
            stage="proposer", failures=["proposer_output_object_required"],
            escalation=escalation, manifest_digest=manifest_digest,
            proposer_view_digest=proposer_view_digest,
        )
    proposer_output = dict(proposer_output)
    proposer_output_digest = _digest(proposer_output)
    output_sensitive = _sensitive_keys(proposer_output)
    if output_sensitive:
        return _rejected(
            stage="proposer", failures=[f"sensitive_proposer_output:{','.join(output_sensitive[:8])}"],
            escalation=escalation, manifest_digest=manifest_digest,
            proposer_view_digest=proposer_view_digest, proposer_output_digest=proposer_output_digest,
        )
    submitted = proposer_output.get("typed_axiom_proposals")
    if not isinstance(submitted, list) or not submitted:
        return _rejected(
            stage="proposer", failures=["typed_proposals_required", "prose_only_output_rejected"],
            escalation=escalation, manifest_digest=manifest_digest,
            proposer_view_digest=proposer_view_digest, proposer_output_digest=proposer_output_digest,
        )
    rows: list[dict[str, Any]] = []
    row_failures: list[str] = []
    preflight_rows: list[tuple[int, Any, Mapping[str, Any]]] = []
    for index, row in enumerate(submitted):
        if not isinstance(row, Mapping):
            row_failures.append(f"row.{index}.object_required")
            continue
        if set(row) != {"source_conjecture", "typed_axiom_proposal"}:
            row_failures.append(f"row.{index}.fields")
            continue
        source = row["source_conjecture"]
        try:
            proposal = _canonicalize_proposer_proposal(
                source, row["typed_axiom_proposal"], proposer_view_copy
            )
        except (TypeError, ValueError) as exc:
            row_failures.append(f"row.{index}.proposal_canonicalization:{exc}")
            continue
        if proposal_validator is not None:
            try:
                proposal_validator(proposal)
            except (TypeError, ValueError) as exc:
                row_failures.append(f"row.{index}.proposal_policy:{exc}")
                continue
        preflight_rows.append((index, source, proposal))

    # Validate the entire batch before invoking any paid semantic checker. A
    # malformed late row must not spend checker calls on earlier rows.
    if row_failures or len(preflight_rows) != len(submitted):
        return _rejected(
            stage="proposer_preflight", failures=row_failures or ["proposal_rows_rejected"],
            escalation=escalation, manifest_digest=manifest_digest,
            proposer_view_digest=proposer_view_digest, proposer_output_digest=proposer_output_digest,
        )

    for index, source, proposal in preflight_rows:
        try:
            checker_output = semantic_checker_fn(
                {"source_conjecture": deepcopy(source), "typed_axiom_proposal": deepcopy(proposal)}
            )
        except Exception as exc:  # noqa: BLE001
            row_failures.append(f"row.{index}.checker_exception:{type(exc).__name__}")
            continue
        verdict = checker_output.get("semantic_fidelity_verdict") if isinstance(checker_output, Mapping) else None
        if not isinstance(verdict, Mapping):
            row_failures.append(f"row.{index}.semantic_fidelity_verdict_required")
            continue
        check = verify_semantic_fidelity_verdict(
            proposal,
            verdict,
            trusted_public_key_pem=trusted_semantic_fidelity_public_key_pem,
            source_conjecture=source,
            expected_verifier_ref=expected_semantic_fidelity_verifier_ref,
        )
        if not check.get("allowed"):
            row_failures.extend(f"row.{index}.{failure}" for failure in check.get("failures", []))
            continue
        rows.append({
            "source_conjecture": deepcopy(source),
            "typed_axiom_proposal": deepcopy(proposal),
            "semantic_fidelity_verdict": deepcopy(dict(verdict)),
        })
    if row_failures or len(rows) != len(submitted):
        return _rejected(
            stage="semantic_checker", failures=row_failures or ["proposal_rows_rejected"],
            escalation=escalation, manifest_digest=manifest_digest,
            proposer_view_digest=proposer_view_digest, proposer_output_digest=proposer_output_digest,
            rows=rows,
        )
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "status": "ok",
        "mode": "conjecture",
        "trial_source": "typed_proposer_checker",
        "canonical_engine": "ztare.research_director.research_isomorphism",
        "result": {
            "candidate_count": len(rows),
            "typed_axiom_proposals": rows,
        },
        "proof_credit_eligible": False,
        "theorem_campaign_admissible": False,
        "can_mutate_substrate": False,
        "allowed_use": "quarantined_candidate_generation",
        "orchestration": {
            "schema": ORCHESTRATION_SCHEMA,
            "status": "ok",
            "manifest_digest": manifest_digest,
            "escalation_digest": escalation["routing_receipt_digest"],
            "proposer_view_digest": proposer_view_digest,
            "proposer_output_digest": proposer_output_digest,
            "semantic_fidelity_checker_ref": expected_semantic_fidelity_verifier_ref,
            "calibration_only": calibration_only,
        },
    }
    return {
        "schema": ORCHESTRATION_SCHEMA,
        "ok": True,
        "stage": "complete",
        "calibration_only": calibration_only,
        "failures": [],
        "manifest_digest": manifest_digest,
        "proposer_view_digest": proposer_view_digest,
        "proposer_output_digest": proposer_output_digest,
        "receipt": receipt,
    }


def recover_valid_quarantined_rows(
    orchestration: Mapping[str, Any],
    *,
    trusted_semantic_fidelity_public_key_pem: str,
    expected_semantic_fidelity_verifier_ref: str,
    proposal_validator: Callable[[Mapping[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Revalidate row-complete bytes from a rejected batch without any provider call."""
    if orchestration.get("schema") != ORCHESTRATION_SCHEMA or orchestration.get("ok") is not False:
        raise ValueError("row recovery requires a rejected typed orchestration")
    receipt = orchestration.get("receipt")
    result = receipt.get("result") if isinstance(receipt, Mapping) else None
    rows = result.get("typed_axiom_proposals") if isinstance(result, Mapping) else None
    if not isinstance(rows, list) or not rows:
        raise ValueError("rejected orchestration contains no checked proposal rows")
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        failures: list[str] = []
        if not isinstance(row, Mapping):
            failures.append("row_not_object")
        else:
            source = row.get("source_conjecture")
            proposal = row.get("typed_axiom_proposal")
            verdict = row.get("semantic_fidelity_verdict")
            if not isinstance(proposal, Mapping) or not isinstance(verdict, Mapping):
                failures.append("typed_proposal_or_verdict_missing")
            else:
                if proposal_validator is not None:
                    try:
                        proposal_validator(proposal)
                    except (TypeError, ValueError) as exc:
                        failures.append(f"proposal_policy:{exc}")
                check = verify_semantic_fidelity_verdict(
                    proposal,
                    verdict,
                    trusted_public_key_pem=trusted_semantic_fidelity_public_key_pem,
                    source_conjecture=source,
                    expected_verifier_ref=expected_semantic_fidelity_verifier_ref,
                )
                failures.extend(str(item) for item in check.get("failures", ()))
        if failures:
            rejected.append({"row_index": index, "failures": failures})
        else:
            accepted.append(deepcopy(dict(row)))
    core = {
        "schema": "leanmill.axiom_pack_row_recovery.v1",
        "status": "recovered_quarantined_rows" if accepted else "no_valid_rows",
        "source_orchestration_digest": _digest(dict(orchestration)),
        "accepted_count": len(accepted),
        "rejected_count": len(rejected),
        "accepted_rows": accepted,
        "rejected_rows": rejected,
        "provider_calls": 0,
        "proof_credit_eligible": False,
        "theorem_campaign_admissible": False,
        "can_mutate_substrate": False,
        "required_next_step": "fresh frontier campaign admission and boundary verification",
    }
    return {**core, "receipt_sha256": _digest(core)}


__all__ = [
    "ORCHESTRATION_SCHEMA",
    "make_contract_proposer",
    "make_json_proposer",
    "make_signed_semantic_checker",
    "orchestrate_typed_axiom_proposals",
    "recover_valid_quarantined_rows",
    "render_semantic_checker_prompt",
    "render_typed_proposer_prompt",
]
