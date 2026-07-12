"""Typed admission boundary for proposed AxiomPack laws.

Proposal generation and semantic-fidelity review are separate operations.  A
proposal binds a structural-conjecture digest to one frozen theory signature,
one well-typed axiom, and its natural-language intent.  A consumer admits the
proposal only after a role-specific checker signs a fidelity verdict over that
exact content.

This module contains no proposal policy or model dispatch.  A deterministic
grammar, an agent, or a human can all produce the same proposal object.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
import hashlib
import json
import re
from typing import Any, Mapping

from ztare.leanmill.formal_verification_provider import (
    attach_signature,
    build_payload,
    canonical_provider_payload_bytes,
    verify_payload_signature,
)
from ztare.leanmill.theory_ir import (
    AxiomFormula,
    TheorySignature,
    validate_axiom,
)


TYPED_AXIOM_PROPOSAL_SCHEMA = "leanmill.typed_axiom_proposal.v1"
SEMANTIC_FIDELITY_VERDICT_SCHEMA = "leanmill.typed_axiom_semantic_fidelity.v1"
SEMANTIC_FIDELITY_CLAIM_SCHEMA = "leanmill.typed_axiom_semantic_fidelity_claim.v1"
SEMANTIC_FIDELITY_PURPOSE = "typed_axiom_semantic_fidelity"
SEMANTIC_FIDELITY_CHECKER_ROLE = "semantic_fidelity_checker"

_HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_PROPOSAL_KEYS = {
    "schema",
    "source_conjecture_sha256",
    "theory_signature_sha256",
    "theory_signature",
    "axiom_sha256",
    "axiom",
    "nl_intent",
    "kill_condition",
}
_VERDICT_KEYS = {
    "schema",
    "proposal_sha256",
    "authority_role",
    "fidelity_claim",
    "provider_payload",
}
_CLAIM_KEYS = {
    "schema",
    "proposal_sha256",
    "faithful",
    "rationale",
    "evidence_refs",
}
_PROVIDER_KEYS = {
    "schema_version",
    "provider",
    "formal_system",
    "verifier_ref",
    "property_class",
    "subject_ref",
    "subject_digest",
    "claim_ref",
    "certificate_ref",
    "certificate_digest",
    "verdict",
    "verification_summary",
    "assumption_refs",
    "input_refs",
    "output_refs",
    "faithfulness_refs",
    "checker_evidence_refs",
    "counterexample_ref",
    "tenant_id",
    "project_id",
    "run_id",
    "metadata",
}


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _sha256_ref_from_hex(value: str) -> str:
    _require_sha256(value, field_name="sha256")
    return f"sha256:{value}"


def _json_copy(value: Mapping[str, Any]) -> dict[str, Any]:
    return json.loads(_canonical_json(dict(value)))


def _json_source(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    to_json = getattr(value, "to_json", None)
    if callable(to_json):
        return to_json()
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        return to_dict()
    if isinstance(value, Mapping):
        return dict(value)
    return value


def structural_conjecture_digest(source_conjecture: Any) -> str:
    """Hash the canonical JSON form of a structural-conjecture artifact."""

    return _sha256(_json_source(source_conjecture))


def _require_sha256(value: str, *, field_name: str) -> None:
    if not isinstance(value, str) or not _HEX_SHA256.fullmatch(value):
        raise ValueError(f"{field_name} must be a lowercase SHA-256 hex digest")


def _require_exact_keys(
    value: Mapping[str, Any], required: set[str], *, context: str
) -> None:
    missing = required - set(value)
    unknown = set(value) - required
    if missing:
        raise ValueError(f"{context} missing fields: {sorted(missing)}")
    if unknown:
        raise ValueError(f"{context} has unknown fields: {sorted(unknown)}")


@dataclass(frozen=True)
class TypedAxiomProposal:
    source_conjecture_sha256: str
    theory_signature: TheorySignature
    theory_signature_sha256: str
    axiom: AxiomFormula
    axiom_sha256: str
    nl_intent: str
    kill_condition: str
    schema: str = TYPED_AXIOM_PROPOSAL_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != TYPED_AXIOM_PROPOSAL_SCHEMA:
            raise ValueError(f"unsupported typed axiom proposal schema: {self.schema!r}")
        _require_sha256(
            self.source_conjecture_sha256,
            field_name="source_conjecture_sha256",
        )
        _require_sha256(
            self.theory_signature_sha256,
            field_name="theory_signature_sha256",
        )
        _require_sha256(self.axiom_sha256, field_name="axiom_sha256")
        if not isinstance(self.theory_signature, TheorySignature):
            raise ValueError("theory_signature must be a TheorySignature")
        if not isinstance(self.axiom, AxiomFormula):
            raise ValueError("axiom must be an AxiomFormula")
        if self.theory_signature_sha256 != self.theory_signature.content_hash:
            raise ValueError("theory_signature_sha256 does not bind theory_signature")
        if self.axiom_sha256 != self.axiom.content_hash:
            raise ValueError("axiom_sha256 does not bind axiom")
        if not isinstance(self.nl_intent, str) or not self.nl_intent.strip():
            raise ValueError("nl_intent is required")
        if not isinstance(self.kill_condition, str) or not self.kill_condition.strip():
            raise ValueError("kill_condition is required")
        validate_axiom(self.theory_signature, self.axiom)

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "source_conjecture_sha256": self.source_conjecture_sha256,
            "theory_signature_sha256": self.theory_signature_sha256,
            "theory_signature": self.theory_signature.to_json(),
            "axiom_sha256": self.axiom_sha256,
            "axiom": self.axiom.to_json(),
            "nl_intent": self.nl_intent,
            "kill_condition": self.kill_condition,
        }

    @property
    def content_hash(self) -> str:
        return _sha256(self.to_json())

    @classmethod
    def from_json(cls, value: Mapping[str, Any]) -> "TypedAxiomProposal":
        if not isinstance(value, Mapping):
            raise ValueError("typed axiom proposal must be a JSON object")
        _require_exact_keys(value, _PROPOSAL_KEYS, context="typed axiom proposal")
        signature = value["theory_signature"]
        axiom = value["axiom"]
        if not isinstance(signature, Mapping):
            raise ValueError("theory_signature must be a JSON object")
        if not isinstance(axiom, Mapping):
            raise ValueError("axiom must be a JSON object")
        return cls(
            source_conjecture_sha256=value["source_conjecture_sha256"],
            theory_signature=TheorySignature.from_json(signature),
            theory_signature_sha256=value["theory_signature_sha256"],
            axiom=AxiomFormula.from_json(axiom),
            axiom_sha256=value["axiom_sha256"],
            nl_intent=value["nl_intent"],
            kill_condition=value["kill_condition"],
            schema=value["schema"],
        )


@dataclass(frozen=True)
class SignedSemanticFidelityVerdict:
    proposal_sha256: str
    authority_role: str
    fidelity_claim: Mapping[str, Any]
    provider_payload: Mapping[str, Any]
    schema: str = SEMANTIC_FIDELITY_VERDICT_SCHEMA

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "proposal_sha256": self.proposal_sha256,
            "authority_role": self.authority_role,
            "fidelity_claim": _json_copy(self.fidelity_claim),
            "provider_payload": _json_copy(self.provider_payload),
        }

    @classmethod
    def from_json(
        cls, value: Mapping[str, Any]
    ) -> "SignedSemanticFidelityVerdict":
        if not isinstance(value, Mapping):
            raise ValueError("semantic-fidelity verdict must be a JSON object")
        _require_exact_keys(value, _VERDICT_KEYS, context="semantic-fidelity verdict")
        claim = value["fidelity_claim"]
        payload = value["provider_payload"]
        if not isinstance(claim, Mapping):
            raise ValueError("fidelity_claim must be a JSON object")
        if not isinstance(payload, Mapping):
            raise ValueError("provider_payload must be a JSON object")
        return cls(
            proposal_sha256=value["proposal_sha256"],
            authority_role=value["authority_role"],
            fidelity_claim=dict(claim),
            provider_payload=dict(payload),
            schema=value["schema"],
        )


def _coerce_proposal(
    proposal: TypedAxiomProposal | Mapping[str, Any],
) -> TypedAxiomProposal:
    if isinstance(proposal, TypedAxiomProposal):
        return proposal
    return TypedAxiomProposal.from_json(proposal)


def _coerce_verdict(
    verdict: SignedSemanticFidelityVerdict | Mapping[str, Any],
) -> SignedSemanticFidelityVerdict:
    if isinstance(verdict, SignedSemanticFidelityVerdict):
        return verdict
    return SignedSemanticFidelityVerdict.from_json(verdict)


def semantic_fidelity_verdict_digest(
    verdict: SignedSemanticFidelityVerdict | Mapping[str, Any],
) -> str:
    """Content hash of the complete signed verdict transport object."""

    return _sha256(_coerce_verdict(verdict).to_json())


def build_typed_axiom_proposal(
    *,
    theory_signature: TheorySignature | Mapping[str, Any],
    axiom: AxiomFormula | Mapping[str, Any],
    nl_intent: str,
    kill_condition: str,
    source_conjecture: Any | None = None,
    source_conjecture_sha256: str | None = None,
) -> TypedAxiomProposal:
    """Build a proposal from source content or its previously frozen digest."""

    if (source_conjecture is None) == (source_conjecture_sha256 is None):
        raise ValueError(
            "provide exactly one of source_conjecture or source_conjecture_sha256"
        )
    signature = (
        theory_signature
        if isinstance(theory_signature, TheorySignature)
        else TheorySignature.from_json(theory_signature)
    )
    parsed_axiom = (
        axiom if isinstance(axiom, AxiomFormula) else AxiomFormula.from_json(axiom)
    )
    source_digest = (
        structural_conjecture_digest(source_conjecture)
        if source_conjecture is not None
        else str(source_conjecture_sha256)
    )
    return TypedAxiomProposal(
        source_conjecture_sha256=source_digest,
        theory_signature=signature,
        theory_signature_sha256=signature.content_hash,
        axiom=parsed_axiom,
        axiom_sha256=parsed_axiom.content_hash,
        nl_intent=nl_intent,
        kill_condition=kill_condition,
    )


def verify_typed_axiom_proposal(
    proposal: TypedAxiomProposal | Mapping[str, Any],
    *,
    source_conjecture: Any | None = None,
) -> dict[str, Any]:
    failures: list[str] = []
    try:
        parsed = _coerce_proposal(proposal)
    except (TypeError, ValueError) as exc:
        return {
            "valid": False,
            "failures": [f"proposal:{exc}"],
            "proposal_sha256": "",
        }
    if source_conjecture is not None and (
        structural_conjecture_digest(source_conjecture)
        != parsed.source_conjecture_sha256
    ):
        failures.append("source_conjecture_sha256")
    return {
        "valid": not failures,
        "failures": failures,
        "proposal_sha256": parsed.content_hash,
        "source_conjecture_sha256": parsed.source_conjecture_sha256,
        "theory_signature_sha256": parsed.theory_signature_sha256,
        "axiom_sha256": parsed.axiom_sha256,
    }


def _semantic_fidelity_payload(
    proposal: TypedAxiomProposal,
    claim: Mapping[str, Any],
    *,
    verifier_ref: str,
) -> dict[str, Any]:
    refs = list(claim.get("evidence_refs") or [])
    faithful = claim.get("faithful") is True
    return build_payload(
        formal_system="other",
        property_class="math",
        verdict="verified" if faithful else "invalid",
        subject_ref=f"typed-axiom-proposal:{proposal.content_hash}",
        subject_text=_canonical_json(proposal.to_json()),
        claim_ref=f"semantic-fidelity:{proposal.content_hash}",
        certificate_ref=refs[0] if refs else "missing:evidence",
        certificate_text=_canonical_json(dict(claim)),
        verifier_ref=verifier_ref,
        verification_summary=(
            "Typed axiom matches the stated semantic intent and kill condition."
            if faithful
            else "Typed axiom does not match the stated semantic intent or kill condition."
        ),
        faithfulness_refs=refs,
        checker_evidence_refs=refs,
        input_refs=[
            _sha256_ref_from_hex(proposal.source_conjecture_sha256),
            _sha256_ref_from_hex(proposal.theory_signature_sha256),
            _sha256_ref_from_hex(proposal.axiom_sha256),
        ],
        output_refs=[_sha256_ref_from_hex(proposal.content_hash)],
        extra_metadata={
            "purpose": SEMANTIC_FIDELITY_PURPOSE,
            "authority_role": SEMANTIC_FIDELITY_CHECKER_ROLE,
            "proposal_sha256": proposal.content_hash,
            "source_conjecture_sha256": proposal.source_conjecture_sha256,
            "theory_signature_sha256": proposal.theory_signature_sha256,
            "axiom_sha256": proposal.axiom_sha256,
        },
    )


def build_semantic_fidelity_verdict(
    proposal: TypedAxiomProposal | Mapping[str, Any],
    *,
    faithful: bool,
    rationale: str,
    evidence_refs: list[str],
    private_key_pem: str,
    verifier_ref: str,
) -> SignedSemanticFidelityVerdict:
    """Sign a semantic checker verdict over one exact proposal."""

    parsed = _coerce_proposal(proposal)
    if not isinstance(faithful, bool):
        raise ValueError("faithful must be a bool")
    if not isinstance(rationale, str) or not rationale.strip():
        raise ValueError("rationale is required")
    refs = [str(ref) for ref in evidence_refs if str(ref).strip()]
    if not refs:
        raise ValueError("semantic fidelity requires at least one evidence ref")
    if not isinstance(private_key_pem, str) or not private_key_pem.strip():
        raise ValueError("private_key_pem is required")
    if not isinstance(verifier_ref, str) or not verifier_ref.strip():
        raise ValueError("verifier_ref is required")

    claim = {
        "schema": SEMANTIC_FIDELITY_CLAIM_SCHEMA,
        "proposal_sha256": parsed.content_hash,
        "faithful": faithful,
        "rationale": rationale,
        "evidence_refs": refs,
    }
    payload = _semantic_fidelity_payload(
        parsed,
        claim,
        verifier_ref=verifier_ref,
    )
    attach_signature(payload, private_key_pem)
    return SignedSemanticFidelityVerdict(
        proposal_sha256=parsed.content_hash,
        authority_role=SEMANTIC_FIDELITY_CHECKER_ROLE,
        fidelity_claim=claim,
        provider_payload=payload,
    )


def verify_semantic_fidelity_verdict(
    proposal: TypedAxiomProposal | Mapping[str, Any],
    verdict: SignedSemanticFidelityVerdict | Mapping[str, Any],
    *,
    trusted_public_key_pem: str | None,
    source_conjecture: Any | None = None,
    expected_verifier_ref: str | None = None,
) -> dict[str, Any]:
    """Verify proposal structure, source binding, checker role, and signature."""

    failures: list[str] = []
    proposal_check = verify_typed_axiom_proposal(
        proposal, source_conjecture=source_conjecture
    )
    if not proposal_check["valid"]:
        failures.extend(proposal_check["failures"])
    try:
        parsed_proposal = _coerce_proposal(proposal)
    except (TypeError, ValueError) as exc:
        return {
            "allowed": False,
            "signature_verified": False,
            "failures": [*failures, f"proposal:{exc}"],
        }
    try:
        parsed_verdict = _coerce_verdict(verdict)
    except (TypeError, ValueError) as exc:
        return {
            "allowed": False,
            "signature_verified": False,
            "failures": [*failures, f"verdict:{exc}"],
        }

    proposal_digest = parsed_proposal.content_hash
    claim = dict(parsed_verdict.fidelity_claim)
    payload = dict(parsed_verdict.provider_payload)
    try:
        _require_exact_keys(claim, _CLAIM_KEYS, context="semantic-fidelity claim")
    except ValueError as exc:
        failures.append(f"fidelity_claim:{exc}")

    if parsed_verdict.schema != SEMANTIC_FIDELITY_VERDICT_SCHEMA:
        failures.append("verdict_schema")
    if parsed_verdict.proposal_sha256 != proposal_digest:
        failures.append("proposal_sha256")
    if parsed_verdict.authority_role != SEMANTIC_FIDELITY_CHECKER_ROLE:
        failures.append("authority_role")
    if claim.get("schema") != SEMANTIC_FIDELITY_CLAIM_SCHEMA:
        failures.append("fidelity_claim_schema")
    if claim.get("proposal_sha256") != proposal_digest:
        failures.append("fidelity_claim_proposal_sha256")
    if claim.get("faithful") is not True:
        failures.append("semantic_fidelity_not_verified")
    if not isinstance(claim.get("rationale"), str) or not str(
        claim.get("rationale")
    ).strip():
        failures.append("fidelity_rationale")
    refs = claim.get("evidence_refs")
    if not isinstance(refs, list) or not refs or not all(
        isinstance(ref, str) and ref.strip() for ref in refs
    ):
        failures.append("fidelity_evidence_refs")
        refs = []
    verifier_ref = payload.get("verifier_ref")
    if not isinstance(verifier_ref, str) or not verifier_ref.strip():
        failures.append("provider_payload:verifier_ref_missing")
        verifier_ref = ""
    elif expected_verifier_ref is not None and verifier_ref != expected_verifier_ref:
        failures.append("provider_payload:verifier_ref")
    unknown_payload_fields = set(payload) - _PROVIDER_KEYS
    if unknown_payload_fields:
        failures.append(
            f"provider_payload:unknown_fields:{sorted(unknown_payload_fields)}"
        )
    if refs and verifier_ref:
        expected_payload = _semantic_fidelity_payload(
            parsed_proposal,
            claim,
            verifier_ref=verifier_ref,
        )
        try:
            content_bound = canonical_provider_payload_bytes(
                payload
            ) == canonical_provider_payload_bytes(expected_payload)
        except (KeyError, TypeError, ValueError):
            content_bound = False
        if not content_bound:
            failures.append("provider_payload:content_binding")

    signature_verified = False
    if not isinstance(trusted_public_key_pem, str) or not trusted_public_key_pem.strip():
        failures.append("trusted_public_key_missing")
    else:
        try:
            signature_verified = verify_payload_signature(
                payload, trusted_public_key_pem
            )
        except (TypeError, ValueError):
            signature_verified = False
        if not signature_verified:
            failures.append("provider_payload:signature")

    return {
        "allowed": not failures,
        "signature_verified": signature_verified,
        "failures": failures,
        "proposal_sha256": proposal_digest,
        "source_conjecture_sha256": parsed_proposal.source_conjecture_sha256,
        "theory_signature_sha256": parsed_proposal.theory_signature_sha256,
        "axiom_sha256": parsed_proposal.axiom_sha256,
        "authority_role": parsed_verdict.authority_role,
    }


def admit_axiom_template(
    proposal: TypedAxiomProposal | Mapping[str, Any],
    verdict: SignedSemanticFidelityVerdict | Mapping[str, Any],
    *,
    trusted_public_key_pem: str,
    source_conjecture: Any | None = None,
    expected_verifier_ref: str | None = None,
) -> dict[str, Any]:
    """Return an AxiomPack template after the typed fidelity boundary passes."""

    verification = verify_semantic_fidelity_verdict(
        proposal,
        verdict,
        trusted_public_key_pem=trusted_public_key_pem,
        source_conjecture=source_conjecture,
        expected_verifier_ref=expected_verifier_ref,
    )
    if not verification["allowed"]:
        raise ValueError(
            f"typed axiom proposal was not admitted: {verification['failures']}"
        )
    parsed = _coerce_proposal(proposal)
    parsed_verdict = _coerce_verdict(verdict)
    return {
        "name": parsed.axiom.name,
        "statement": parsed.nl_intent,
        "formula": parsed.axiom.formula.to_json(),
        "kill_condition": parsed.kill_condition,
        "source_conjecture_sha256": parsed.source_conjecture_sha256,
        "typed_proposal_sha256": parsed.content_hash,
        "semantic_fidelity_verdict_sha256": semantic_fidelity_verdict_digest(
            parsed_verdict
        ),
        "semantic_fidelity_checker_ref": parsed_verdict.provider_payload[
            "verifier_ref"
        ],
    }


__all__ = [
    "SEMANTIC_FIDELITY_CHECKER_ROLE",
    "SEMANTIC_FIDELITY_CLAIM_SCHEMA",
    "SEMANTIC_FIDELITY_PURPOSE",
    "SEMANTIC_FIDELITY_VERDICT_SCHEMA",
    "SignedSemanticFidelityVerdict",
    "TYPED_AXIOM_PROPOSAL_SCHEMA",
    "TypedAxiomProposal",
    "admit_axiom_template",
    "build_semantic_fidelity_verdict",
    "build_typed_axiom_proposal",
    "semantic_fidelity_verdict_digest",
    "structural_conjecture_digest",
    "verify_semantic_fidelity_verdict",
    "verify_typed_axiom_proposal",
]
