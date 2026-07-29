"""Live typed AxiomPack authoring transport and subscription-role runtime."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
from typing import Any, Callable, Mapping

from ztare.leanmill import prompts
from ztare.leanmill.axiom_pack_orchestration import (
    orchestrate_typed_axiom_proposals,
    verify_axiom_pack_escalation_packet,
)
from ztare.leanmill.axiom_yield import verify_shadow_task_manifest
from ztare.leanmill.contracts.axiom_pack_transport import AxiomPackTransportContract
from ztare.leanmill.formal_verification_provider import sha256_ref


TYPED_PRODUCER_VIEW_SCHEMA = "leanmill.axiom_pack_typed_producer_view.v1"
TYPED_PRODUCER_OUTPUT_SCHEMA = "leanmill.axiom_pack_typed_producer_output.v1"
SEMANTIC_CHECKER_OUTPUT_SCHEMA = "leanmill.axiom_pack_semantic_checker_output.v1"


@dataclass(frozen=True)
class LiveTypedAxiomPackProducer:
    """Non-calibration authorities and callbacks for one live authoring call."""

    escalation: Mapping[str, Any]
    task_manifest: Mapping[str, Any]
    trusted_manifest_public_key_pem: str
    trusted_semantic_fidelity_public_key_pem: str
    expected_semantic_fidelity_verifier_ref: str
    proposer_call: Callable[[str], Any]
    semantic_checker_fn: Callable[[Mapping[str, Any]], Mapping[str, Any]]
    proposal_validator: Callable[[Mapping[str, Any]], None] | None = None


def _digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256_ref(payload)


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


def typed_axiom_producer_output_schema(*, max_candidates: int = 8) -> dict[str, Any]:
    """Strict live-producer wire schema; formula semantics are host-validated."""

    if max_candidates < 1:
        raise ValueError("max_candidates must be positive")
    string = {"type": "string"}
    nonempty = {"type": "string", "minLength": 1}
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "schema",
            "outcome",
            "typed_axiom_proposals",
            "no_candidate_reason",
            "language_capability_gap",
        ],
        "properties": {
            "schema": {"type": "string", "const": TYPED_PRODUCER_OUTPUT_SCHEMA},
            "outcome": {
                "type": "string",
                "enum": [
                    "typed_proposals",
                    "no_candidate",
                    "language_capability_gap",
                ],
            },
            "typed_axiom_proposals": {
                "type": "array",
                "maxItems": max_candidates,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "source_conjecture",
                        "theory_signature_sha256",
                        "base_theory_digest",
                        "axiom_formula_json",
                        "nl_intent",
                        "kill_condition",
                    ],
                    "properties": {
                        "source_conjecture": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": [
                                "schema",
                                "name",
                                "statement",
                                "rationale",
                                "kill_condition",
                            ],
                            "properties": {
                                "schema": {
                                    "type": "string",
                                    "const": (
                                        "leanmill.axiom_pack_structural_conjecture.v1"
                                    ),
                                },
                                "name": nonempty,
                                "statement": nonempty,
                                "rationale": nonempty,
                                "kill_condition": nonempty,
                            },
                        },
                        "theory_signature_sha256": nonempty,
                        "base_theory_digest": nonempty,
                        "axiom_formula_json": {"type": "string", "minLength": 2},
                        "nl_intent": nonempty,
                        "kill_condition": nonempty,
                    },
                },
            },
            "no_candidate_reason": string,
            "language_capability_gap": string,
        },
    }


def semantic_checker_output_schema() -> dict[str, Any]:
    """Strict unsigned judgment schema; the host signs accepted judgments."""

    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["faithful", "rationale", "evidence_refs"],
        "properties": {
            "faithful": {"type": "boolean"},
            "rationale": {"type": "string", "minLength": 1},
            "evidence_refs": {
                "type": "array",
                "minItems": 1,
                "items": {"type": "string", "minLength": 1},
            },
        },
    }


def build_typed_axiom_proposer_view(base_blueprint: Any) -> dict[str, Any]:
    """Freeze the executable language and base identity shown to the live author."""

    from ztare.leanmill.axiom_pack import AxiomPackBlueprint
    from ztare.leanmill.theory_ir import (
        AxiomFormula,
        TheorySignature,
        theory_content_hash,
        validate_axioms,
    )

    base = (
        base_blueprint
        if isinstance(base_blueprint, AxiomPackBlueprint)
        else AxiomPackBlueprint.from_json(dict(base_blueprint))
    )
    signature = TheorySignature.from_json(base.theory_signature)
    base_axioms = tuple(AxiomFormula.from_json(row) for row in base.base_axioms)
    validate_axioms(signature, base_axioms)
    if base.base_theory_resolved is not True:
        raise ValueError("typed live producer requires a resolved executable base")
    base_theory_digest = theory_content_hash(signature, base_axioms)
    if not base_theory_digest.startswith("sha256:"):
        base_theory_digest = f"sha256:{base_theory_digest}"
    return {
        "schema": TYPED_PRODUCER_VIEW_SCHEMA,
        "domain": base.domain,
        "research_question": base.nl_statement,
        "semantic_intent": base.semantic_intent,
        "target_structure_family": base.target_structure_family,
        "residuals": list(base.residuals),
        "forbidden_shortcuts": list(base.forbidden_shortcuts),
        "base_theory": {
            "name": base.current_theory,
            "signature": signature.to_json(),
            "theory_signature_sha256": signature.content_hash,
            "base_axioms": [axiom.to_json() for axiom in base_axioms],
            "base_axiom_sha256s": [axiom.content_hash for axiom in base_axioms],
            "base_theory_digest": base_theory_digest,
            "base_theory_resolved": True,
        },
        "formula_ir": {
            "schema": "leanmill.axiom_formula.v1",
            "term_kinds": ["var", "app"],
            "formula_kinds": [
                "true",
                "false",
                "eq",
                "rel",
                "not",
                "and",
                "or",
                "implies",
                "iff",
                "forall",
                "exists",
            ],
        },
    }


def decode_typed_axiom_producer_output(
    raw: Any,
    *,
    proposer_view: Mapping[str, Any],
    max_candidates: int = 8,
) -> dict[str, Any]:
    """Parse the live wire object and validate every agent-authored formula."""

    from jsonschema import Draft202012Validator
    from ztare.leanmill.theory_ir import AxiomFormula, TheorySignature, validate_axiom

    envelope = _parse_json_object(raw)
    if "outcome" not in envelope and any(
        key in envelope
        for key in ("candidate_axiom_templates", "candidates", "conjectures")
    ):
        raise ValueError("prose_only_output_rejected")
    Draft202012Validator(
        typed_axiom_producer_output_schema(max_candidates=max_candidates)
    ).validate(envelope)
    base = proposer_view.get("base_theory")
    if not isinstance(base, Mapping):
        raise ValueError("typed proposer view lacks base_theory")
    signature_row = base.get("signature")
    if not isinstance(signature_row, Mapping):
        raise ValueError("typed proposer view lacks a frozen signature")
    signature = TheorySignature.from_json(signature_row)
    signature_sha = str(base.get("theory_signature_sha256") or "")
    base_digest = str(base.get("base_theory_digest") or "")
    if signature_sha != signature.content_hash or not base_digest:
        raise ValueError("typed proposer view base identity is inconsistent")
    outcome = str(envelope["outcome"])
    submitted = envelope["typed_axiom_proposals"]
    no_candidate_reason = str(envelope["no_candidate_reason"]).strip()
    language_gap = str(envelope["language_capability_gap"]).strip()
    if outcome == "typed_proposals":
        if not submitted or no_candidate_reason or language_gap:
            raise ValueError("typed_proposals outcome fields are inconsistent")
    elif outcome == "no_candidate":
        if submitted or not no_candidate_reason or language_gap:
            raise ValueError("no_candidate outcome fields are inconsistent")
        return {
            "producer_outcome": outcome,
            "outcome_detail": no_candidate_reason,
            "typed_axiom_proposals": [],
        }
    else:
        if submitted or no_candidate_reason or not language_gap:
            raise ValueError("language_capability_gap outcome fields are inconsistent")
        return {
            "producer_outcome": outcome,
            "outcome_detail": language_gap,
            "typed_axiom_proposals": [],
        }

    rows: list[dict[str, Any]] = []
    for index, row in enumerate(submitted):
        if row["theory_signature_sha256"] != signature_sha:
            raise ValueError(f"row.{index}.theory_signature_sha256")
        if row["base_theory_digest"] != base_digest:
            raise ValueError(f"row.{index}.base_theory_digest")
        try:
            axiom_row = json.loads(row["axiom_formula_json"])
        except json.JSONDecodeError as exc:
            raise ValueError(f"row.{index}.axiom_formula_json:{exc.msg}") from exc
        if not isinstance(axiom_row, Mapping):
            raise ValueError(f"row.{index}.axiom_formula_json must encode an object")
        axiom = AxiomFormula.from_json(axiom_row)
        validate_axiom(signature, axiom)
        rows.append(
            {
                "source_conjecture": deepcopy(dict(row["source_conjecture"])),
                "typed_axiom_proposal": {
                    "axiom": axiom.to_json(),
                    "nl_intent": str(row["nl_intent"]),
                    "kill_condition": str(row["kill_condition"]),
                },
            }
        )
    return {
        "producer_outcome": outcome,
        "outcome_detail": "",
        "typed_axiom_proposals": rows,
    }


def render_typed_proposer_prompt(proposer_view: Mapping[str, Any]) -> str:
    return prompts.AXIOM_PACK_TYPED_PROPOSER_PROMPT.format(
        output_schema=json.dumps(
            typed_axiom_producer_output_schema(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ),
        proposer_view=json.dumps(
            dict(proposer_view),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ),
    )


def make_json_proposer(
    call: Callable[[str], Any],
) -> Callable[[Mapping[str, Any]], Mapping[str, Any]]:
    def proposer(view: Mapping[str, Any]) -> Mapping[str, Any]:
        return decode_typed_axiom_producer_output(
            call(render_typed_proposer_prompt(view)), proposer_view=view
        )

    return proposer


def make_contract_proposer(
    call: Callable[[str], Any],
    *,
    transport_contract: AxiomPackTransportContract,
) -> Callable[[Mapping[str, Any]], Mapping[str, Any]]:
    def proposer(view: Mapping[str, Any]) -> Mapping[str, Any]:
        if _digest(dict(view)) != transport_contract.proposer_view_digest:
            raise ValueError("proposer view does not match frozen transport contract")
        return transport_contract.decode(call(transport_contract.render_prompt(view)))

    return proposer


def render_semantic_checker_prompt(
    source_conjecture: Any, typed_axiom_proposal: Any
) -> str:
    return prompts.AXIOM_PACK_SEMANTIC_CHECKER_PROMPT.format(
        check_input=json.dumps(
            {
                "source_conjecture": source_conjecture,
                "typed_axiom_proposal": typed_axiom_proposal,
            },
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
    """Validate an unsigned judgment, then sign it under the host authority."""

    from jsonschema import Draft202012Validator
    from ztare.leanmill.typed_axiom_proposal import build_semantic_fidelity_verdict

    def checker(payload: Mapping[str, Any]) -> Mapping[str, Any]:
        source = payload["source_conjecture"]
        proposal = payload["typed_axiom_proposal"]
        judgment = _parse_json_object(
            call(render_semantic_checker_prompt(source, proposal))
        )
        Draft202012Validator(semantic_checker_output_schema()).validate(judgment)
        verdict = build_semantic_fidelity_verdict(
            proposal,
            faithful=judgment["faithful"] is True,
            rationale=str(judgment["rationale"]).strip(),
            evidence_refs=[str(ref) for ref in judgment["evidence_refs"]],
            private_key_pem=private_key_pem,
            verifier_ref=verifier_ref,
        )
        return {"semantic_fidelity_verdict": verdict.to_json()}

    return checker


def _bind_role_output_schema(
    call: Callable[[str], Any],
    schema: Mapping[str, Any],
    *,
    role: str,
) -> None:
    if not hasattr(call, "output_schema"):
        return
    configured = getattr(call, "output_schema")
    if configured is None:
        setattr(call, "output_schema", deepcopy(dict(schema)))
        return
    if dict(configured) != dict(schema):
        raise ValueError(f"{role} role carries a different output schema")


def _semantic_keypair_matches(private_key_pem: str, public_key_pem: str) -> bool:
    from cryptography.hazmat.primitives import serialization

    private_key = serialization.load_pem_private_key(
        private_key_pem.encode("utf-8"), password=None
    )
    trusted_public_key = serialization.load_pem_public_key(
        public_key_pem.encode("utf-8")
    )
    private_public_der = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    trusted_public_der = trusted_public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_public_der == trusted_public_der


def build_live_typed_axiom_pack_runtime(
    *,
    escalation: Mapping[str, Any],
    task_manifest: Mapping[str, Any],
    trusted_manifest_public_key_pem: str,
    semantic_checker_private_key_pem: str,
    trusted_semantic_fidelity_public_key_pem: str,
    expected_semantic_fidelity_verifier_ref: str,
    proposer_call: Callable[[str], Any],
    semantic_checker_call: Callable[[str], Any],
    proposal_validator: Callable[[Mapping[str, Any]], None] | None = None,
) -> LiveTypedAxiomPackProducer:
    """Construct the non-calibration runtime from frozen campaign authorities."""

    escalation_copy = deepcopy(dict(escalation))
    task_manifest_copy = deepcopy(dict(task_manifest))
    escalation_failures = verify_axiom_pack_escalation_packet(escalation_copy)
    if escalation_failures:
        raise ValueError(
            "live typed producer escalation rejected: "
            + ",".join(escalation_failures)
        )
    manifest_ok, manifest_failures = verify_shadow_task_manifest(
        task_manifest_copy,
        base_theory_digest=str(escalation_copy["base_theory_digest"]),
        trusted_public_key_pem=trusted_manifest_public_key_pem,
    )
    if not manifest_ok:
        raise ValueError(
            "live typed producer task manifest rejected: "
            + ",".join(str(item) for item in manifest_failures)
        )
    if proposer_call is semantic_checker_call:
        raise ValueError("proposer and semantic checker must be separate roles")
    if not str(expected_semantic_fidelity_verifier_ref).strip():
        raise ValueError("semantic checker verifier ref is required")
    if not _semantic_keypair_matches(
        semantic_checker_private_key_pem,
        trusted_semantic_fidelity_public_key_pem,
    ):
        raise ValueError("semantic checker private/public authority mismatch")
    _bind_role_output_schema(
        proposer_call,
        typed_axiom_producer_output_schema(),
        role="live typed proposer",
    )
    _bind_role_output_schema(
        semantic_checker_call,
        semantic_checker_output_schema(),
        role="semantic checker",
    )
    return LiveTypedAxiomPackProducer(
        escalation=escalation_copy,
        task_manifest=task_manifest_copy,
        trusted_manifest_public_key_pem=str(trusted_manifest_public_key_pem),
        trusted_semantic_fidelity_public_key_pem=str(
            trusted_semantic_fidelity_public_key_pem
        ),
        expected_semantic_fidelity_verifier_ref=str(
            expected_semantic_fidelity_verifier_ref
        ),
        proposer_call=proposer_call,
        semantic_checker_fn=make_signed_semantic_checker(
            semantic_checker_call,
            private_key_pem=semantic_checker_private_key_pem,
            verifier_ref=expected_semantic_fidelity_verifier_ref,
        ),
        proposal_validator=proposal_validator,
    )


def run_live_typed_axiom_pack_producer(
    *,
    base_blueprint: Any,
    runtime: LiveTypedAxiomPackProducer,
) -> dict[str, Any]:
    """Execute the live typed authoring door under non-calibration gates."""

    proposer_view = build_typed_axiom_proposer_view(base_blueprint)
    _bind_role_output_schema(
        runtime.proposer_call,
        typed_axiom_producer_output_schema(),
        role="live typed proposer",
    )
    return orchestrate_typed_axiom_proposals(
        escalation=runtime.escalation,
        calibration_only=False,
        proposer_view=proposer_view,
        task_manifest=runtime.task_manifest,
        trusted_manifest_public_key_pem=runtime.trusted_manifest_public_key_pem,
        trusted_semantic_fidelity_public_key_pem=(
            runtime.trusted_semantic_fidelity_public_key_pem
        ),
        expected_semantic_fidelity_verifier_ref=(
            runtime.expected_semantic_fidelity_verifier_ref
        ),
        proposer_fn=make_json_proposer(runtime.proposer_call),
        semantic_checker_fn=runtime.semantic_checker_fn,
        proposal_validator=runtime.proposal_validator,
    )


__all__ = [
    "LiveTypedAxiomPackProducer",
    "SEMANTIC_CHECKER_OUTPUT_SCHEMA",
    "TYPED_PRODUCER_OUTPUT_SCHEMA",
    "TYPED_PRODUCER_VIEW_SCHEMA",
    "build_live_typed_axiom_pack_runtime",
    "build_typed_axiom_proposer_view",
    "decode_typed_axiom_producer_output",
    "make_contract_proposer",
    "make_json_proposer",
    "make_signed_semantic_checker",
    "render_semantic_checker_prompt",
    "render_typed_proposer_prompt",
    "run_live_typed_axiom_pack_producer",
    "semantic_checker_output_schema",
    "typed_axiom_producer_output_schema",
]
