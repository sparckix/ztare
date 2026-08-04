"""Constraint-to-Isomorphism engine for autonomously surfacing
cross-field structural matches (the next "Barrington") when a system hits a structural ceiling.

WHY THIS IS GENERAL (and an interface, not a per-domain rebuild). `fit/analogy.py` already does the
hard middle — query a frontier LLM with ONLY a domain-stripped structural fingerprint and let a
holdout oracle verify/kill the answer — but it is welded to curve-fit residuals. This module is the
uplevel: the SHARED engine (the contamination-disciplined isomorphism query + the verify-via-oracle
discipline) lives here once; each consumer (leanmill proof search, a research director, the
autoresearch fit loop) plugs in its own domain piece via the `StrangeLoopDomain` Strategy. Same
pattern as `ztare.fit.mdl.MDLLibrary`.

THE THREE STEPS (Step 2 is the engine's; 1 and 3 are the domain's):
  1. abstract_failure   — DOMAIN: turn a concrete failure (a degrading closure rate, a residual
                          surface, a stalled research seam) into a `ConstraintFingerprint`: pure
                          topology / complexity / algebra, ALL domain syntax stripped.
  2. isomorphism query  — ENGINE: ask an LLM, given ONLY that abstract constraint and a domain to
                          push AWAY from, to name established theorems/algorithms/laws from ANY
                          field that solve exactly those constraints. Stripping the semantic gravity
                          is the mechanism: "do barrington" fails because it is orthogonal; "what
                          solves O(1)-width O(log n)-depth composition?" can surface it.
  3. compile_to_test + oracle — DOMAIN: map a surfaced match onto the system's variables, compile it
                          to a testable gate, and score it on a HOLDOUT. A match that does not
                          improve the oracle metric (MDL / closure rate / MRE) is bullshit and is
                          discarded. The loop only "completes" (mutates the architecture) on a
                          holdout-verified improvement.

DISCIPLINE (inherited from the validated GP-164 analogy primitive): the LLM PROPOSES, the oracle
DISPOSES. The query is structural-only (no variable names / charter prose / domain axioms — those
contaminate by letting the model retrieve a known RESULT rather than a known FORM). Every surfaced
match and verdict is auditable. Nothing mutates the live system except via a holdout-verified gate.

CANONICAL INVARIANT (the engine/consumer pattern — same as ztare.fit.mdl.MDLLibrary):
  1. ONE engine per capability = `IsomorphismLoop`. That is the surfaced PRIMITIVE.
  2. A DOMAIN/CONSUMER (`StrangeLoopDomain`) is a Strategy PLUG — specialized by CONFIG/COMPOSITION
     (a query, an oracle_fn, a failure_state, a forbidden_domain), or at most by subclassing the
     GENERAL domain. NEVER a parallel per-subject reimplementation; a consumer is NOT a primitive
     and is not surfaced in the catalog.
  3. The SUBJECT (leanmill, a research seam) is config/INPUT to the general domain, not its own
     domain. There is exactly one level: research-direction / architecture. The engine is an
     RD tool that takes a SYSTEM ceiling as input — it does NOT run inside the solver per proof.
  4. The distance-from-home knob `forbidden_domain` UNIFIES the autoresearch family: None → ANALOGY
     (match any field, incl. adjacent); set → DEANCHOR (forbid home + adjacent → the orthogonal jump).
     `fit/analogy.py` (ANALOGY) and `fit/cold_llm_erdos_seed.py` (DEANCHOR) are two settings of this
     one engine, not two systems.

STATUS: apparatus only. Whether the autonomous loop actually surfaces USEFUL matches (vs. plausible
nonsense) is an open efficacy question — build-to-have-ready, prove it works before trusting it.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
import os
from typing import Any, Callable, Mapping, Optional, Protocol


# ─────────────────────────────────────────────────────────────────────────────
# Typed objects (the contract between the engine and a domain)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ConstraintFingerprint:
    """A domain-STRIPPED statement of why the system is stuck — the search query for Step 2.
    Carries NO domain syntax (no Lean tactics, no variable names, no charter prose): only the
    abstract mathematical shape of the ceiling, so the LLM retrieves structure, not a memorized
    answer for the home domain."""
    constraint_class: str                  # e.g. "bounded-width sequential composition"
    abstract_form: str                     # pure-math statement (topology/complexity/algebra)
    invariants: dict = field(default_factory=dict)   # structural stats (depth, width, monotonicity…)
    forbidden_domain: Optional[str] = None  # the HOME field to push away from (the orthogonal jump)

    def is_contaminated(self, banned_terms: "list[str]") -> bool:
        """Guard: the fingerprint must not leak home-domain vocabulary (which would let the model
        retrieve a known result instead of a structural form). Caller supplies the banned terms."""
        blob = f"{self.constraint_class} {self.abstract_form} {self.invariants}".lower()
        return any(t.lower() in blob for t in banned_terms if t)


_TYPE_ALIASES = {
    "bool": "boolean",
    "boolean": "boolean",
    "int": "integer",
    "integer": "integer",
    "nat": "integer",
    "natural": "integer",
    "float": "real",
    "double": "real",
    "number": "real",
    "numeric": "real",
    "str": "symbol",
    "string": "symbol",
    "text": "symbol",
    "enum": "symbol",
    "set": "set",
    "sequence": "sequence",
    "list": "sequence",
    "tuple": "sequence",
    "mapping": "record",
    "dict": "record",
    "object": "record",
    "relation": "relation",
    "predicate": "predicate",
    "cardinality": "integer",
}


def _normalize_component_type(value: object) -> str:
    raw = str(value or "").strip().lower().replace(" ", "_")
    if not raw:
        return "unknown"
    return _TYPE_ALIASES.get(raw, raw)


def _infer_invariant_type(value: object) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "real"
    if isinstance(value, dict):
        return "record"
    if isinstance(value, (list, tuple, set)):
        return "sequence"
    raw = str(value or "").strip().lower()
    normalized_raw = _normalize_component_type(raw)
    if normalized_raw in {"boolean", "integer", "real", "symbol", "set", "sequence", "record", "relation", "predicate", "complexity_class"}:
        return normalized_raw
    if raw in {"true", "false", "yes", "no"}:
        return "boolean"
    if raw and raw.lstrip("+-").isdigit():
        return "integer"
    try:
        float(raw)
    except (TypeError, ValueError):
        pass
    else:
        return "real"
    if any(token in raw for token in ("o(", "theta(", "omega(", "bounded", "unbounded")):
        return "complexity_class"
    if any(token in raw for token in ("monotone", "ordering", "partial_order")):
        return "relation"
    return "symbol"


@dataclass(frozen=True)
class ConstraintSignature:
    """A serializable, substrate-neutral signature for one side of a transport.

    Components are invariant identifiers mapped to coarse structural types. The
    type vocabulary is intentionally small; domain-specific meaning belongs in
    preservation obligations, not in ad-hoc Python subclasses.
    """

    name: str
    components: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_fingerprint(cls, fp: ConstraintFingerprint, *, name: str = "source") -> "ConstraintSignature":
        return cls(
            name=name,
            components={
                str(key): _infer_invariant_type(value)
                for key, value in (fp.invariants or {}).items()
                if key != "do_not_resurface_refuted_transports"
            },
        )

    @classmethod
    def from_dict(cls, payload: object, *, default_name: str) -> "ConstraintSignature":
        row = payload if isinstance(payload, dict) else {}
        components = row.get("components") if isinstance(row.get("components"), dict) else {}
        return cls(
            name=str(row.get("name") or default_name).strip(),
            components={str(k): _normalize_component_type(v) for k, v in components.items()},
        )

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "components": dict(sorted(self.components.items()))}


@dataclass(frozen=True)
class MorphismValidation:
    valid: bool
    verified: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ConstraintMorphism:
    """Typed transport between two constraint signatures.

    `component_map` maps each source component to a structured entry with at
    least `target`, `source_type`, `target_type`, and `transform`.
    Preservation obligations state what must remain true under the transform;
    they are `pending`, `verified`, or `refuted`. A verified obligation must
    cite a content-addressed receipt and a signed provider verdict.
    `target_discriminator` names the target-side intervention that can reject
    the transport.
    """

    source_signature: ConstraintSignature
    target_signature: ConstraintSignature
    component_map: dict[str, dict[str, Any]] = field(default_factory=dict)
    preservation_obligations: list[dict[str, Any]] = field(default_factory=list)
    information_losses: list[str] = field(default_factory=list)
    inverse_component_map: dict[str, dict[str, Any]] | None = None
    round_trip_obligations: list[dict[str, Any]] = field(default_factory=list)
    target_discriminator: dict[str, Any] = field(default_factory=dict)
    relation: str = "transport"
    declared_content_hash: str = field(default="", repr=False)

    @classmethod
    def from_dict(cls, payload: object) -> "ConstraintMorphism":
        row = payload if isinstance(payload, dict) else {}
        source = ConstraintSignature.from_dict(row.get("source_signature"), default_name="source")
        target = ConstraintSignature.from_dict(row.get("target_signature"), default_name="target")
        raw_map = row.get("component_map") if isinstance(row.get("component_map"), dict) else {}
        component_map = {
            str(key): (dict(value) if isinstance(value, dict) else {"target": str(value)})
            for key, value in raw_map.items()
        }
        raw_inverse = row.get("inverse_component_map")
        inverse = None
        if isinstance(raw_inverse, dict):
            inverse = {
                str(key): (dict(value) if isinstance(value, dict) else {"target": str(value)})
                for key, value in raw_inverse.items()
            }
        raw_obligations = row.get("preservation_obligations")
        if not isinstance(raw_obligations, list):
            raw_obligations = []
        raw_losses = row.get("information_losses")
        if not isinstance(raw_losses, list):
            raw_losses = []
        raw_round_trips = row.get("round_trip_obligations")
        if not isinstance(raw_round_trips, list):
            raw_round_trips = []
        return cls(
            source_signature=source,
            target_signature=target,
            component_map=component_map,
            preservation_obligations=[dict(x) for x in raw_obligations if isinstance(x, dict)],
            information_losses=[str(x).strip() for x in raw_losses if str(x).strip()],
            inverse_component_map=inverse,
            round_trip_obligations=[dict(x) for x in raw_round_trips if isinstance(x, dict)],
            target_discriminator=dict(row.get("target_discriminator") or {})
            if isinstance(row.get("target_discriminator"), dict) else {},
            relation=str(row.get("relation") or "transport").strip().lower(),
            declared_content_hash=str(row.get("content_hash") or "").strip().lower(),
        )

    def to_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        import copy

        row: dict[str, Any] = {
            "schema": "ztare-constraint-morphism-v1",
            "relation": self.relation,
            "source_signature": self.source_signature.to_dict(),
            "target_signature": self.target_signature.to_dict(),
            "component_map": copy.deepcopy(self.component_map),
            "preservation_obligations": copy.deepcopy(self.preservation_obligations),
            "information_losses": list(self.information_losses),
            "inverse_component_map": copy.deepcopy(self.inverse_component_map),
            "round_trip_obligations": copy.deepcopy(self.round_trip_obligations),
            "target_discriminator": copy.deepcopy(self.target_discriminator),
        }
        if include_hash:
            row["content_hash"] = self.content_hash()
        return row

    def content_hash(self) -> str:
        import hashlib
        import json

        canonical = json.dumps(
            self.to_dict(include_hash=False),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()

    def validate(self, *, trusted_public_key_pem: str | None = None) -> MorphismValidation:
        return validate_constraint_morphism(
            self,
            trusted_public_key_pem=trusted_public_key_pem,
        )


_LOW_INFORMATION_COMPONENTS = {
    "a", "b", "c", "x", "y", "z", "foo", "bar", "baz", "banana",
    "component", "counterpart", "field", "item", "mapping", "thing", "target", "value",
}
_SEMANTIC_COMPONENT_CLASSES = (
    frozenset({"arity", "cardinality", "count", "dimension", "number", "rank", "size", "width"}),
    frozenset({"monotone", "monotonicity", "order", "ordered", "ordering", "poset"}),
    frozenset({"break", "boundary", "change", "phase", "regime", "transition"}),
    frozenset({"asymptotic", "boundary", "infinite", "limit", "tail", "unbounded"}),
    frozenset({"sign", "orientation", "polarity", "positive", "negative"}),
    frozenset({"class", "case", "category", "family", "partition"}),
    frozenset({"projection", "image", "preimage", "fiber", "kernel", "quotient"}),
    frozenset({"residual", "defect", "error", "obstruction", "certificate"}),
    frozenset({"depth", "horizon", "length", "step", "time"}),
    frozenset({"bool", "boolean", "guard", "predicate", "condition"}),
)
_VALID_RELATIONS = {"transport", "interpretation", "reduction", "embedding", "quotient", "adjunction", "isomorphism"}
_VALID_OBLIGATION_STATUSES = {"pending", "verified", "refuted"}


def _component_tokens(value: object) -> set[str]:
    import re

    return {token for token in re.findall(r"[a-z0-9]+", str(value or "").lower()) if len(token) > 1}


def _component_name_is_meaningful(value: object) -> bool:
    raw = str(value or "").strip().lower()
    tokens = _component_tokens(raw)
    return bool(tokens) and raw not in _PLACEHOLDER_MAPPINGS and not tokens <= _LOW_INFORMATION_COMPONENTS


def _components_semantically_related(source_key: str, source_value: object, target: object) -> bool:
    source_tokens = _component_tokens(source_key) | _component_tokens(source_value)
    target_tokens = _component_tokens(target)
    if source_tokens & target_tokens:
        return True
    return any(source_tokens & group and target_tokens & group for group in _SEMANTIC_COMPONENT_CLASSES)


def _types_compatible(source_type: object, target_type: object) -> bool:
    source = _normalize_component_type(source_type)
    target = _normalize_component_type(target_type)
    if source == target:
        return True
    return {source, target} <= {"integer", "real"}


def _valid_sha256(value: object) -> bool:
    import re

    return bool(re.fullmatch(r"[0-9a-f]{64}", str(value or "").strip().lower()))


def _receipt_binding_status(reference: object, expected_sha256: object) -> str:
    """Return match, mismatch, or unavailable for a local evidence reference."""

    import hashlib

    if not _valid_sha256(expected_sha256):
        return "mismatch"
    try:
        path = Path(str(reference or "")).expanduser().resolve()
        if not path.is_file():
            return "unavailable"
        return (
            "match"
            if hashlib.sha256(path.read_bytes()).hexdigest()
            == str(expected_sha256).strip().lower()
            else "mismatch"
        )
    except OSError:
        return "unavailable"


def _receipt_binding_matches(reference: object, expected_sha256: object) -> bool:
    return _receipt_binding_status(reference, expected_sha256) == "match"


def _has_provider_verdict(obligation: Mapping[str, Any]) -> bool:
    return any(
        isinstance(obligation.get(field_name), dict)
        for field_name in _PROVIDER_VERDICT_FIELDS
    )


_MORPHISM_AUTHORITY_SCHEMA = "ztare-constraint-morphism-obligation-verdict-v1"
_MORPHISM_AUTHORITY_PURPOSE = "constraint_morphism_obligation"
_PROVIDER_VERDICT_FIELDS = ("provider_verdict", "verification_payload")


def _canonical_json(value: object) -> str:
    import json

    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha256_text(value: str) -> str:
    import hashlib

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _morphism_authority_surface(morphism: ConstraintMorphism) -> dict[str, Any]:
    """Return the stable morphism bytes an obligation authority signs.

    Provider payloads are removed to avoid a signature cycle. Receipt paths,
    evidence digests, obligation states, maps, and discriminators remain bound.
    """

    surface = morphism.to_dict(include_hash=False)
    for field_name in ("preservation_obligations", "round_trip_obligations"):
        for obligation in surface.get(field_name) or []:
            if isinstance(obligation, dict):
                for verdict_field in _PROVIDER_VERDICT_FIELDS:
                    obligation.pop(verdict_field, None)
    return surface


def _morphism_obligation_subject(
    morphism: ConstraintMorphism,
    obligation_kind: str,
    obligation_index: int,
) -> dict[str, Any]:
    kind = str(obligation_kind or "").strip().lower()
    if kind not in {"preservation", "round_trip"}:
        raise ValueError("obligation_kind must be 'preservation' or 'round_trip'")
    rows = (
        morphism.preservation_obligations
        if kind == "preservation"
        else morphism.round_trip_obligations
    )
    if obligation_index < 0 or obligation_index >= len(rows):
        raise ValueError(f"{kind} obligation index is out of range")
    surface = _morphism_authority_surface(morphism)
    return {
        "schema": _MORPHISM_AUTHORITY_SCHEMA,
        "morphism_digest": _sha256_text(_canonical_json(surface)),
        "morphism": surface,
        "obligation_kind": kind,
        "obligation_index": obligation_index,
    }


def build_signed_morphism_obligation_verdict(
    morphism: ConstraintMorphism,
    *,
    obligation_kind: str,
    obligation_index: int,
    private_key_pem: str,
    verifier_ref: str,
) -> dict[str, Any]:
    """Build the provider verdict consumed by authority-aware validation.

    The caller installs the returned payload under the obligation's
    ``provider_verdict`` field. The trust root is intentionally absent from
    both the morphism and the verdict.
    """

    from ztare.leanmill.formal_verification_provider import (
        attach_signature,
        build_payload,
    )

    subject = _morphism_obligation_subject(
        morphism,
        obligation_kind,
        obligation_index,
    )
    kind = subject["obligation_kind"]
    rows = (
        morphism.preservation_obligations
        if kind == "preservation"
        else morphism.round_trip_obligations
    )
    obligation = rows[obligation_index]
    if str(obligation.get("status") or "").strip().lower() != "verified":
        raise ValueError("an authority verdict requires obligation status='verified'")
    receipt_ref = str(obligation.get("receipt_ref") or "").strip()
    receipt_sha256 = str(obligation.get("receipt_sha256") or "").strip().lower()
    if not _receipt_binding_matches(receipt_ref, receipt_sha256):
        raise ValueError("obligation receipt bytes do not match receipt_sha256")
    if not str(private_key_pem or "").strip() or not str(verifier_ref or "").strip():
        raise ValueError("private_key_pem and verifier_ref are required")

    subject_ref = (
        f"constraint-morphism:{subject['morphism_digest']}:{kind}:{obligation_index}"
    )
    claim_ref = f"{subject_ref}:verified"
    payload = build_payload(
        formal_system="other",
        property_class="contract",
        verdict="verified",
        subject_ref=subject_ref,
        subject_text=_canonical_json(subject),
        claim_ref=claim_ref,
        certificate_ref=receipt_ref,
        certificate_text=receipt_sha256,
        verifier_ref=verifier_ref,
        verification_summary="Constraint morphism obligation passed the bound evidence check.",
        faithfulness_refs=[f"sha256:{subject['morphism_digest']}"],
        checker_evidence_refs=[receipt_ref],
        input_refs=[f"sha256:{subject['morphism_digest']}", receipt_sha256],
        output_refs=[claim_ref],
        extra_metadata={
            "purpose": _MORPHISM_AUTHORITY_PURPOSE,
            "authority_schema": _MORPHISM_AUTHORITY_SCHEMA,
            "morphism_digest": subject["morphism_digest"],
            "obligation_kind": kind,
            "obligation_index": obligation_index,
            "evidence_sha256": receipt_sha256,
        },
    )
    return attach_signature(payload, private_key_pem)


def _morphism_obligation_authority_verified(
    morphism: ConstraintMorphism,
    *,
    obligation_kind: str,
    obligation_index: int,
    obligation: dict[str, Any],
    trusted_public_key_pem: str | None,
) -> tuple[bool, str]:
    if not str(trusted_public_key_pem or "").strip():
        return False, "trusted_public_key_missing"
    payload = next(
        (
            obligation.get(field_name)
            for field_name in _PROVIDER_VERDICT_FIELDS
            if isinstance(obligation.get(field_name), dict)
        ),
        None,
    )
    if not isinstance(payload, dict):
        return False, "provider_verdict_missing"

    from ztare.leanmill.formal_verification_provider import (
        PROVIDER,
        SCHEMA_VERSION,
        sha256_ref,
        verify_payload_signature,
    )

    try:
        subject = _morphism_obligation_subject(
            morphism,
            obligation_kind,
            obligation_index,
        )
        kind = subject["obligation_kind"]
        receipt_ref = str(obligation.get("receipt_ref") or "").strip()
        receipt_sha256 = str(obligation.get("receipt_sha256") or "").strip().lower()
        subject_ref = (
            f"constraint-morphism:{subject['morphism_digest']}:{kind}:{obligation_index}"
        )
        claim_ref = f"{subject_ref}:verified"
        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
        failures = []
        expected_fields = {
            "schema_version": SCHEMA_VERSION,
            "provider": PROVIDER,
            "formal_system": "other",
            "property_class": "contract",
            "verdict": "verified",
            "subject_ref": subject_ref,
            "subject_digest": sha256_ref(_canonical_json(subject)),
            "claim_ref": claim_ref,
            "certificate_ref": receipt_ref,
            "certificate_digest": sha256_ref(receipt_sha256),
        }
        for field_name, expected in expected_fields.items():
            if payload.get(field_name) != expected:
                failures.append(field_name)
        expected_metadata = {
            "purpose": _MORPHISM_AUTHORITY_PURPOSE,
            "authority_schema": _MORPHISM_AUTHORITY_SCHEMA,
            "morphism_digest": subject["morphism_digest"],
            "obligation_kind": kind,
            "obligation_index": obligation_index,
            "evidence_sha256": receipt_sha256,
        }
        for field_name, expected in expected_metadata.items():
            if metadata.get(field_name) != expected:
                failures.append(f"metadata.{field_name}")
        if not str(payload.get("verifier_ref") or "").strip():
            failures.append("verifier_ref")
        if not str(payload.get("verification_summary") or "").strip():
            failures.append("verification_summary")
        if payload.get("counterexample_ref") is not None:
            failures.append("counterexample_ref")
        faithfulness_refs = payload.get("faithfulness_refs")
        if not isinstance(faithfulness_refs, list) or (
            f"sha256:{subject['morphism_digest']}" not in faithfulness_refs
        ):
            failures.append("faithfulness_refs")
        checker_evidence_refs = payload.get("checker_evidence_refs")
        if not isinstance(checker_evidence_refs, list) or (
            receipt_ref not in checker_evidence_refs
        ):
            failures.append("checker_evidence_refs")
        if not verify_payload_signature(payload, trusted_public_key_pem):
            failures.append("signature")
    except (KeyError, TypeError, ValueError):
        return False, "provider_verdict_malformed"
    if failures:
        return False, "provider_verdict_" + ",".join(failures)
    return True, ""


def _obligation_for_pair(morphism: ConstraintMorphism, source: str, target: str) -> "dict[str, Any] | None":
    for obligation in morphism.preservation_obligations:
        if str(obligation.get("source") or "") == source and str(obligation.get("target") or "") == target:
            return obligation
    return None


def validate_constraint_morphism(
    morphism: ConstraintMorphism,
    *,
    trusted_public_key_pem: str | None = None,
) -> MorphismValidation:
    """Validate the typed carrier without adjudicating its mathematical claim.

    `valid` means signatures, maps, obligations, losses, inverse data, and the
    target-side discriminator form a coherent test contract. `verified` is
    stronger: every preservation/round-trip obligation is independently
    receipt-backed and signed under the caller's trust root. A pending carrier
    can be tested but cannot be promoted.
    """

    errors: list[str] = []
    warnings: list[str] = []
    source = {
        str(k): _normalize_component_type(v)
        for k, v in (morphism.source_signature.components or {}).items()
    }
    target = {
        str(k): _normalize_component_type(v)
        for k, v in (morphism.target_signature.components or {}).items()
    }
    if not morphism.source_signature.name.strip():
        errors.append("source_signature.name")
    if not morphism.target_signature.name.strip():
        errors.append("target_signature.name")
    if not source:
        errors.append("source_signature.components")
    if not target:
        errors.append("target_signature.components")
    for side, components in (("source", source), ("target", target)):
        for key, component_type in components.items():
            if component_type == "unknown" or not _component_name_is_meaningful(key):
                errors.append(f"{side}_signature.components.{key}")
    if morphism.relation not in _VALID_RELATIONS:
        errors.append(f"relation:{morphism.relation}")
    if morphism.declared_content_hash:
        if not _valid_sha256(morphism.declared_content_hash):
            errors.append("content_hash:malformed")
        elif morphism.declared_content_hash != morphism.content_hash():
            errors.append("content_hash:mismatch")

    for key in sorted(source):
        entry = morphism.component_map.get(key)
        if not isinstance(entry, dict):
            errors.append(f"component_map.{key}:missing")
            continue
        mapped = str(entry.get("target") or "").strip()
        if not _component_name_is_meaningful(mapped):
            errors.append(f"component_map.{key}.target:uninformative")
            continue
        if mapped not in target:
            errors.append(f"component_map.{key}.target:not_in_target_signature")
            continue
        declared_source = _normalize_component_type(entry.get("source_type"))
        declared_target = _normalize_component_type(entry.get("target_type"))
        if declared_source != source[key]:
            errors.append(f"component_map.{key}.source_type:{declared_source}!={source[key]}")
        if declared_target != target[mapped]:
            errors.append(f"component_map.{key}.target_type:{declared_target}!={target[mapped]}")
        transform = str(entry.get("transform") or "").strip()
        if not _component_name_is_meaningful(transform):
            errors.append(f"component_map.{key}.transform")
        obligation = _obligation_for_pair(morphism, key, mapped)
        if obligation is None:
            errors.append(f"preservation_obligation:{key}->{mapped}")
            continue
        predicate = str(obligation.get("predicate") or "").strip()
        status = str(obligation.get("status") or "pending").strip().lower()
        if not _component_name_is_meaningful(predicate):
            errors.append(f"preservation_obligation:{key}->{mapped}:predicate")
        if status not in _VALID_OBLIGATION_STATUSES:
            errors.append(f"preservation_obligation:{key}->{mapped}:status")
        elif status == "refuted":
            errors.append(f"preservation_obligation:{key}->{mapped}:refuted")
        elif status == "verified":
            binding = _receipt_binding_status(
                obligation.get("receipt_ref"), obligation.get("receipt_sha256")
            )
            if binding == "mismatch" or (
                binding == "unavailable" and not _has_provider_verdict(obligation)
            ):
                errors.append(f"preservation_obligation:{key}->{mapped}:receipt_binding")
        else:
            warnings.append(f"preservation_obligation:{key}->{mapped}:pending")
        if not _types_compatible(source[key], target[mapped]) and not transform:
            errors.append(f"component_map.{key}:type_mismatch_without_transform")

    extra_sources = sorted(set(morphism.component_map) - set(source))
    if extra_sources:
        errors.append(f"component_map.extra_sources:{','.join(extra_sources)}")
    mapped_pairs = {
        (str(source_key), str(entry.get("target") or ""))
        for source_key, entry in morphism.component_map.items()
        if isinstance(entry, dict)
    }
    seen_obligation_pairs: set[tuple[str, str]] = set()
    for obligation in morphism.preservation_obligations:
        pair = (str(obligation.get("source") or ""), str(obligation.get("target") or ""))
        if pair not in mapped_pairs:
            errors.append(f"preservation_obligation.extra:{pair[0]}->{pair[1]}")
        if pair in seen_obligation_pairs:
            errors.append(f"preservation_obligation.duplicate:{pair[0]}->{pair[1]}")
        seen_obligation_pairs.add(pair)

    for idx, loss in enumerate(morphism.information_losses):
        if not _component_name_is_meaningful(loss):
            errors.append(f"information_losses.{idx}")

    discriminator = morphism.target_discriminator or {}
    for field_name in ("measurement", "intervention", "reject_if"):
        if not _component_name_is_meaningful(discriminator.get(field_name)):
            errors.append(f"target_discriminator.{field_name}")

    inverse = morphism.inverse_component_map
    if inverse is not None:
        for key in sorted(target):
            entry = inverse.get(key)
            mapped = str(entry.get("target") or "").strip() if isinstance(entry, dict) else ""
            if mapped not in source:
                errors.append(f"inverse_component_map.{key}")
        if not morphism.round_trip_obligations:
            errors.append("round_trip_obligations")
        for idx, obligation in enumerate(morphism.round_trip_obligations):
            direction = str(obligation.get("direction") or "").strip().lower()
            predicate = str(obligation.get("predicate") or "").strip()
            status = str(obligation.get("status") or "pending").strip().lower()
            if not direction:
                errors.append(f"round_trip_obligations.{idx}.direction")
            if not _component_name_is_meaningful(predicate):
                errors.append(f"round_trip_obligations.{idx}.predicate")
            if status not in _VALID_OBLIGATION_STATUSES:
                errors.append(f"round_trip_obligations.{idx}.status")
            elif status == "refuted":
                errors.append(f"round_trip_obligations.{idx}.refuted")
            elif status == "verified":
                binding = _receipt_binding_status(
                    obligation.get("receipt_ref"), obligation.get("receipt_sha256")
                )
                if binding == "mismatch" or (
                    binding == "unavailable" and not _has_provider_verdict(obligation)
                ):
                    errors.append(f"round_trip_obligations.{idx}.receipt_binding")
            else:
                warnings.append(f"round_trip_obligations.{idx}.pending")
    if morphism.relation == "isomorphism":
        if inverse is None:
            errors.append("isomorphism.inverse_component_map")
        if morphism.information_losses:
            errors.append("isomorphism.information_losses")
        directions = {
            str(item.get("direction") or "").strip().lower()
            for item in morphism.round_trip_obligations
            if isinstance(item, dict)
        }
        if not {"source_to_target_to_source", "target_to_source_to_target"} <= directions:
            errors.append("isomorphism.round_trip_directions")

    verified_rows = [
        ("preservation", idx, row)
        for idx, row in enumerate(morphism.preservation_obligations)
    ] + [
        ("round_trip", idx, row)
        for idx, row in enumerate(morphism.round_trip_obligations)
    ]
    verified = not errors and bool(verified_rows)
    for kind, idx, row in verified_rows:
        status = str(row.get("status") or "pending").strip().lower()
        binding = _receipt_binding_status(
            row.get("receipt_ref"), row.get("receipt_sha256")
        )
        if status != "verified" or binding == "mismatch" or (
            binding == "unavailable" and not _has_provider_verdict(row)
        ):
            verified = False
            continue
        authority_ok, authority_failure = _morphism_obligation_authority_verified(
            morphism,
            obligation_kind=kind,
            obligation_index=idx,
            obligation=row,
            trusted_public_key_pem=trusted_public_key_pem,
        )
        if not authority_ok:
            verified = False
            warnings.append(
                f"{kind}_obligations.{idx}:authority_unverified:{authority_failure}"
            )
    return MorphismValidation(valid=not errors, verified=verified, errors=tuple(errors), warnings=tuple(warnings))


@dataclass
class SurfacedIsomorphism:
    """One cross-field candidate the engine surfaced for an abstract constraint."""
    theorem: str                   # the named theorem / algorithm / law
    field: str                     # the field it comes from
    mechanism: str                 # HOW it solves the abstract constraint
    mapping_hint: str = ""         # how its components map back to the system's variables
    raw: str = ""                  # raw LLM text (audit)
    invariant_map: dict = field(default_factory=dict)   # typed invariant→counterpart map (opt-in, #122):
    #   present only when the query ran with typed_mapping=True; a candidate that cannot map EVERY
    #   fingerprint invariant is decorative and is mechanically rejected (validate_typed_mapping)
    enrichment: "float | None" = None   # graded single-hop map coverage (0..1). None = ungraded.
    #   Composite paths require a checked ConstraintMorphism; single-hop scalars are never multiplied.
    morphism: "ConstraintMorphism | dict | None" = None
    transport_validation: dict = field(default_factory=dict)


@dataclass
class SurfacedConjecture:
    """A proposed new correspondence between two fingerprints.

    Unlike `SurfacedIsomorphism`, this is not retrieval of an established dictionary. It is a
    hypothesis that both structures are lowerings of one shared object, with predictions and kill
    conditions that downstream experiment machinery must adjudicate.
    """
    mother_structure: str
    lowerings: dict = field(default_factory=dict)
    novel_predictions: dict = field(default_factory=dict)
    kill_conditions: dict = field(default_factory=dict)
    prior_art_inversion: dict = field(default_factory=dict)
    raw: str = ""
    specificity: "float | None" = None


@dataclass
class IsomorphismVerdict:
    """The holdout-oracle's judgment on a surfaced match once compiled to a testable gate."""
    iso: SurfacedIsomorphism
    metric_before: float
    metric_after: float
    improves: bool
    detail: dict = field(default_factory=dict)

    @property
    def delta(self) -> float:
        return self.metric_after - self.metric_before


# ─────────────────────────────────────────────────────────────────────────────
# The Strategy a consumer implements (the per-domain pieces: Steps 1 and 3)
# ─────────────────────────────────────────────────────────────────────────────

class StrangeLoopDomain(Protocol):
    def abstract_failure(self, failure_state: object) -> ConstraintFingerprint:
        """Step 1: fingerprint a concrete ceiling into a domain-stripped ConstraintFingerprint."""
        ...

    def compile_to_test(self, iso: SurfacedIsomorphism, context: object) -> object:
        """Step 3a: map a surfaced theorem onto this system's variables and return a GATE enforcing
        its mechanism. The gate is OPAQUE to the engine — its type is whatever this domain's `oracle`
        knows how to apply (a predicate, a policy/transform, a config delta…). Raise to reject an
        unmappable match."""
        ...

    def oracle(self, gate: "object | None", holdout: object) -> float:
        """Step 3b: score the system on a HOLDOUT under `gate` (None = baseline, no gate). Higher is
        better (closure rate, −MDL, −MRE — the domain's improvement metric). The deterministic judge;
        it owns how the gate is applied."""
        ...

    def banned_terms(self) -> "list[str]":
        """Home-domain vocabulary the fingerprint must NOT contain (contamination guard). Optional —
        a domain may return [] to skip the check."""
        ...


# The Step-2 query signature: (fingerprint, n) -> surfaced matches. Injected so the engine is
# testable with a mock and wired to the real LLM in production.
IsomorphismQuery = Callable[[ConstraintFingerprint, int], "list[SurfacedIsomorphism]"]


# ─────────────────────────────────────────────────────────────────────────────
# The engine
# ─────────────────────────────────────────────────────────────────────────────

class IsomorphismLoop:
    """The shared constraint-to-isomorphism orchestrator. Construct with a domain (Steps 1 & 3) and a query
    (Step 2; defaults to the LLM query). `run` executes failure → fingerprint → cross-field query →
    compile → holdout-verify, returning the verdicts. Only matches that IMPROVE the oracle survive."""

    def __init__(self, domain: StrangeLoopDomain, query: "IsomorphismQuery | None" = None):
        self.domain = domain
        self._query = query  # None → resolve the default LLM query lazily on first run

    def query(self, fp: ConstraintFingerprint, n: int) -> "list[SurfacedIsomorphism]":
        if self._query is None:
            self._query = default_llm_query
        return self._query(fp, n)

    def run(self, failure_state: object, holdout: object, *,
            n_candidates: int = 5, context: object = None,
            strict_contamination: bool = True) -> "list[IsomorphismVerdict]":
        # Step 1 — abstract the failure (domain).
        fp = self.domain.abstract_failure(failure_state)
        banned = []
        try:
            banned = list(self.domain.banned_terms() or [])
        except Exception:
            banned = []
        if strict_contamination and banned and fp.is_contaminated(banned):
            raise ValueError(
                f"contaminated fingerprint: leaks home-domain term(s) {banned} — Step 2 would "
                "retrieve a memorized result, not a structural form. Strip the vocabulary.")
        # Step 2 — surface cross-field structural matches (engine).
        isos = self.query(fp, n_candidates) or []
        # Step 3 — compile each match to a gate and holdout-verify (domain).
        baseline = self.domain.oracle(None, holdout)
        verdicts: list[IsomorphismVerdict] = []
        for iso in isos:
            try:
                test = self.domain.compile_to_test(iso, context)
            except Exception as e:
                verdicts.append(IsomorphismVerdict(iso, baseline, baseline, False,
                                                   {"unmappable": repr(e)[:160]}))
                continue
            after = self.domain.oracle(test, holdout)
            verdicts.append(IsomorphismVerdict(iso, baseline, after, after > baseline,
                                               {"compiled": True}))
        verdicts.sort(key=lambda v: -v.delta)
        return verdicts

    def best(self, failure_state: object, holdout: object, **kw) -> "IsomorphismVerdict | None":
        """The single best holdout-verified mutation, or None if nothing improved the oracle."""
        v = [x for x in self.run(failure_state, holdout, **kw) if x.improves]
        return v[0] if v else None


# ─────────────────────────────────────────────────────────────────────────────
# Default Step-2 query — reuses the validated LLM runtime + contamination discipline
# ─────────────────────────────────────────────────────────────────────────────

def _build_query_prompt(fp: ConstraintFingerprint, n: int, *, typed_mapping: bool = False,
                        mode: str = "solve") -> str:
    # forbidden_domain is the distance-from-home knob that UNIFIES the autoresearch family:
    #   None  → ANALOGY direction (fit/analogy.py): match from ANY field, including adjacent.
    #   set   → DEANCHOR direction (fit/cold_llm_erdos_seed.py): forbid the home field AND directly
    #           adjacent fields to force a far, non-canonical match (the orthogonal jump).
    # #122 opt-ins (DEFAULT path is byte-identical — both flags off reproduce the prior prompt):
    #   typed_mapping → demand an explicit invariant→counterpart map per candidate (decorative
    #                   analogies die at the schema, not at human review);
    #   mode="impossibility" → ask for NO-GO/impossibility results instead of solutions (an
    #                   impossibility transport kills a doomed approach — the cheapest research value).
    away = (f"\nDo NOT answer from {fp.forbidden_domain} OR any field directly adjacent to it — that "
            "is the home framing that produced this ceiling, and the point is to surface what the "
            "home discipline would not. Reach into structurally-distant fields." if fp.forbidden_domain else "")
    if mode == "completion":
        # STRUCTURE-COMPLETION (2026-07-03): for seams with an UNKNOWN component
        # ("the termination/win/closing condition is unknown"), a solve query is
        # a category error — nothing is being solved; a piece is MISSING. Ask
        # instead: in which fields is this partial structure a STANDARD, fully
        # understood pattern, and what is its canonical completion there?
        ask = (f"The structure above is PARTIAL: one component (named in the constraint class) is "
               f"unknown. Name up to {n} fields where this exact partial structure is a STANDARD, "
               "fully-characterized pattern, and state the CANONICAL COMPLETION it has there. For "
               "each, return strict JSON with keys: `theorem` (the standard pattern's name), `field`, "
               "`mechanism` (the canonical form of the missing component in that field), `mapping_hint` "
               "(the sharp, falsifiable prediction this completion makes for a generic system with "
               "these invariants — what to test, and what outcome refutes it).")
    elif mode == "correspondence":
        # LANGLANDS DIRECTION (2026-07-03): not retrieval — a DICTIONARY. Demand
        # a named correspondence between this structure class and a partner
        # category, transport the OBJECT through it, read the unknown property
        # off the partner side, and transport the answer BACK as a prediction.
        learned = _learned_dictionary_hint()
        ask = (f"Name up to {n} established CORRESPONDENCES / DUALITIES / EQUIVALENCES (functors, "
               "dictionaries between categories — e.g. dynamics<->automata, geometry<->algebra, "
               "logic<->machines, games<->fixed points) under which the structure above is the image "
               "of a well-understood partner object. For each, return strict JSON with keys: "
               "`theorem` (the correspondence's name), `field` (the partner category), `mechanism` "
               "(WHAT the partner object is and what the unknown component corresponds to on the "
               "partner side, computed there), `mapping_hint` (the back-transported, falsifiable "
               "prediction for a generic system with these invariants)." + learned)
    elif mode == "impossibility":
        ask = (f"Name up to {n} established IMPOSSIBILITY / NO-GO THEOREMS or hardness results from any "
               "field showing that some natural approach to exactly these constraints CANNOT work "
               "(lower bounds, conservation obstructions, undecidability, no-free-lunch results). For "
               "each, return strict JSON with keys: `theorem`, `field`, `mechanism` (WHAT the result "
               "forbids and WHY), `mapping_hint` (which approach to a generic system with these "
               "invariants it would rule out).")
    else:
        ask = (f"Name up to {n} established THEOREMS, ALGORITHMS, or PHYSICAL LAWS from any field "
               "(group theory, complexity, cryptography, physics, information theory, topology, …) that "
               "SOLVE or OPTIMIZE exactly these constraints. For each, return strict JSON with keys: "
               "`theorem`, `field`, `mechanism` (how it resolves the abstract constraint), `mapping_hint` "
               "(how its components would map onto a generic system with these invariants).")
    typed = ""
    if typed_mapping and fp.invariants:
        _keys = [k for k in fp.invariants if k != "do_not_resurface_refuted_transports"]
        _source_signature = ConstraintSignature.from_fingerprint(fp, name="query_source").to_dict()
        typed = ("\nAdditionally each candidate MUST include `invariant_map` and `constraint_morphism`. "
                 f"Map EVERY source invariant {_keys}. Each invariant_map value must be a meaningful "
                 "target component, not a placeholder. The constraint_morphism object must contain "
                 f"`source_signature` exactly {_source_signature} and a `target_signature` "
                 "(`{name, components:{id:type}}`), "
                 "`component_map` entries `{target,source_type,target_type,transform}`, one "
                 "`preservation_obligations` row `{source,target,predicate,status:'pending'}` per map, "
                 "an explicit `information_losses` list, optional `inverse_component_map` plus "
                 "`round_trip_obligations`, and a `target_discriminator` with `measurement`, "
                 "`intervention`, and `reject_if`. Omit candidates that cannot fill this contract.")
    return (
        "You are given ONLY an abstract structural constraint — no domain, no variable names, no "
        "context about where it came from. This is deliberate: name the STRUCTURE, not a memorized "
        "answer for any particular application.\n\n"
        f"CONSTRAINT CLASS: {fp.constraint_class}\n"
        f"ABSTRACT FORM: {fp.abstract_form}\n"
        f"STRUCTURAL INVARIANTS: {fp.invariants}\n"
        f"{away}\n\n"
        f"{ask}{typed} Return a JSON "
        "list. Retrieve the STRUCTURE that fits; do not invent, and do not return a result claimed "
        "to already solve the caller's specific problem.")


def _learned_dictionary_hint(limit: int = 8) -> str:
    """Load survived conjectural correspondences as advice for correspondence mode."""
    raw_path = os.environ.get(
        "ZTARE_RESEARCH_ISOMORPHISM_DICTIONARY",
        "analytics/queries/research_isomorphism_dictionary.jsonl",
    )
    path = Path(raw_path)
    try:
        lines = [l for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    except OSError:
        return ""
    if not lines:
        return ""
    import json
    entries = []
    for line in lines[-limit:]:
        try:
            row = json.loads(line)
        except Exception:
            continue
        entries.append({
            "correspondence": row.get("mother_structure") or row.get("correspondence"),
            "left": row.get("left_constraint_class"),
            "right": row.get("right_constraint_class"),
            "predictions": row.get("novel_predictions"),
        })
    if not entries:
        return ""
    return (
        "\n\nPreviously falsification-surviving conjectural dictionaries are now allowed as "
        "correspondence entries. You may use them only when their lowerings fit the fingerprint; do "
        "not cite them as source-field proof. Learned dictionary entries:\n"
        + json.dumps(entries, ensure_ascii=True)[:4000]
    )


def _fingerprint_block(label: str, fp: ConstraintFingerprint) -> str:
    return (
        f"{label} CONSTRAINT CLASS: {fp.constraint_class}\n"
        f"{label} ABSTRACT FORM: {fp.abstract_form}\n"
        f"{label} STRUCTURAL INVARIANTS: {fp.invariants}\n"
        f"{label} FORBIDDEN/HOME FIELD: {fp.forbidden_domain or ''}"
    )


def _build_conjecture_prompt(left: ConstraintFingerprint, right: ConstraintFingerprint, n: int) -> str:
    """Prompt for the Langlands-style generative move: propose a new dictionary, not a retrieved one."""
    return (
        "You are given TWO abstract structural fingerprints from separate research seams. Do not retrieve "
        "a known theorem that solves either side. Instead, propose up to "
        f"{n} conjectural correspondences: each says both fingerprints are lowerings of one shared "
        "mother structure. The proposal is useful only if it produces novel, falsifiable predictions on "
        "BOTH sides that neither side's local theory alone would force.\n\n"
        f"{_fingerprint_block('LEFT', left)}\n\n"
        f"{_fingerprint_block('RIGHT', right)}\n\n"
        "Return a JSON list. Each object must have exactly these semantic fields: "
        "`mother_structure` (a concise name for the shared abstract object, invented if needed), "
        "`lowerings` (object with `left` and `right`, each mapping the side's invariant keys/components "
        "to components of the mother structure), `novel_predictions` (object with `left` and `right`; "
        "each side is a list of prediction objects with keys `prediction`, `measurement`, `intervention`, "
        "`horizon`, `expected_observation`, and `novelty_reason`), and `kill_conditions` (object with "
        "`left` and `right`; each side is a list of objects with keys `refuter`, `gate`, and `receipt`), "
        "and `prior_art_inversion` with non-empty `search_queries` (list), `comparison_axes` (list), "
        "and `kill_if_matched` (string). This last object is a required search plan, not evidence that "
        "the correspondence is new; downstream work must execute it and bind a source receipt before "
        "using novelty language. "
        "Use bounded horizons and observable measurements; vague benefits are invalid. "
        "Do not claim the correspondence is established. Do not use source-side plausibility as evidence "
        "for either target prediction."
    )


def _dispatch_text(prompt: str, *, provider: str = "gemini", model: "str | None" = None,
                   timeout_s: int = 180) -> str:
    return _dispatch_text_with_receipt(
        prompt,
        provider=provider,
        model=model,
        timeout_s=timeout_s,
    )[0]


def _dispatch_text_with_receipt(
    prompt: str,
    *,
    provider: str = "gemini",
    model: "str | None" = None,
    timeout_s: int = 180,
) -> "tuple[str, dict]":
    """Provider-flexible text dispatch for the structural-only query. PROVIDER POLICY (repo rule):
    gemini / deepseek go via API (`LLMRuntime`, allowed); codex (OpenAI) / claude (Anthropic) go ONLY
    via the SUBSCRIPTION CLI (`subscription_agent_runtime`), never the metered API. The isomorphism loop
    legitimately needs this provider flexibility for its structural query; other consumers use the
    runtime they need directly (warm-agent architecture for agentic work, `LLMRuntime` for API
    completions) rather than reaching through this module. The receipt is for debug surfaces; production
    callers should still treat empty text as no candidate."""
    provider = (provider or "gemini").lower()
    dispatch_id = _sha256_text(
        _canonical_json({"provider": provider, "model": model, "prompt": prompt})
    )
    artifact_root: Path | None = Path(
        os.environ.get(
            "ZTARE_CONSTRAINT_ISOMORPHISM_ARTIFACT_DIR",
            "/tmp/ztare_constraint_isomorphism_dispatches",
        )
    )
    artifact_setup_error = ""
    try:
        artifact_root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        artifact_setup_error = f"{type(exc).__name__}:{exc}"
        fallback = Path("/tmp/ztare_constraint_isomorphism_dispatches")
        try:
            fallback.mkdir(parents=True, exist_ok=True)
            artifact_root = fallback
        except OSError as fallback_exc:
            artifact_setup_error += (
                f";fallback:{type(fallback_exc).__name__}:{fallback_exc}"
            )
            artifact_root = None
    prompt_path = (
        artifact_root / f"{dispatch_id}.prompt.txt" if artifact_root else None
    )
    stdout_path = (
        artifact_root / f"{dispatch_id}.stdout.txt" if artifact_root else None
    )
    receipt_path = (
        artifact_root / f"{dispatch_id}.receipt.json" if artifact_root else None
    )

    def finish(text: str, row: dict) -> "tuple[str, dict]":
        import json as _json
        import uuid as _uuid

        status = (
            "transport_failed"
            if row.get("exception_type") or row.get("returncode") not in (0, None)
            else "text_returned"
            if text
            else "no_text"
        )
        frozen = {
            **row,
            "dispatch_id": dispatch_id,
            "prompt_sha256": _sha256_text(prompt),
            "status": status,
            "prompt_ref": str(prompt_path) if prompt_path else "",
            "stdout_ref": str(stdout_path) if stdout_path else "",
            "receipt_ref": str(receipt_path) if receipt_path else "",
        }
        if artifact_setup_error:
            frozen["artifact_setup_error"] = artifact_setup_error
        try:
            for path, value in (
                (prompt_path, prompt),
                (stdout_path, text),
                (receipt_path, _json.dumps(frozen, sort_keys=True, indent=2) + "\n"),
            ):
                if path is None:
                    continue
                temporary = path.with_name(path.name + f".{_uuid.uuid4().hex}.tmp")
                temporary.write_text(value, encoding="utf-8")
                os.replace(temporary, path)
        except OSError as exc:
            frozen["artifact_error"] = f"{type(exc).__name__}:{exc}"
        return text, frozen

    try:
        import json as _json

        if receipt_path is None or stdout_path is None:
            raise OSError("dispatch artifact persistence is unavailable")
        prior = _json.loads(receipt_path.read_text(encoding="utf-8"))
        if (
            prior.get("status") == "text_returned"
            and prior.get("prompt_sha256") == _sha256_text(prompt)
            and stdout_path.is_file()
        ):
            return stdout_path.read_text(encoding="utf-8"), {
                **prior,
                "replayed": True,
            }
    except (OSError, ValueError, TypeError):
        pass

    receipt: dict = {
        "provider": provider,
        "model": model,
        "transport": "subscription_cli" if provider in ("codex", "claude") else "api",
        "returncode": None,
        "stdout_chars": 0,
        "stderr_chars": 0,
        "stderr_head": "",
        "exception_type": "",
        "exception_message": "",
        "command": [],
    }
    if provider in ("codex", "claude"):
        from pathlib import Path as _P
        repo = _P(__file__).resolve().parents[3]
        try:
            from ztare.common.subscription_agent_runtime import (
                CODEX_SANDBOX_SEALED_COMPLETION,
                redact_prompt_command,
                run_subscription_agent_with_recovery,
            )
        except Exception:
            try:
                from ztare.common.subscription_agent_runtime import (
                    CODEX_SANDBOX_SEALED_COMPLETION,
                    redact_prompt_command,
                    run_subscription_agent_with_recovery,
                )
            except Exception as exc:  # noqa: BLE001
                receipt["exception_type"] = type(exc).__name__
                receipt["exception_message"] = str(exc)[:500]
                return finish("", receipt)
        try:
            codex_model_env = "ZTARE_CODEX_AGENT_MODEL"
            prior_model_env: str | None = None
            scoped_model_env = "ZTARE_CONSTRAINT_ISOMORPHISM_CODEX_MODEL"
            if provider == "codex" and model:
                prior_model_env = os.environ.get(scoped_model_env)
                os.environ[scoped_model_env] = model
                codex_model_env = scoped_model_env
            run = run_subscription_agent_with_recovery(
                runtime=provider, prompt=prompt, agent_id="constraint_isomorphism::query",
                repo=repo, session_state=None, timeout_seconds=timeout_s,
                codex_model_env=codex_model_env,
                codex_sandbox=(
                    CODEX_SANDBOX_SEALED_COMPLETION
                    if provider == "codex"
                    else "workspace-write"
                ),
                claude_disallowed_tools=["WebSearch", "WebFetch"])
            if provider == "codex" and model:
                if prior_model_env is None:
                    os.environ.pop(scoped_model_env, None)
                else:
                    os.environ[scoped_model_env] = prior_model_env
            result = getattr(run, "result", None)
            text = (getattr(result, "stdout", "") or "") if result is not None else ""
            stderr = (getattr(result, "stderr", "") or "") if result is not None else ""
            command = [str(x) for x in (getattr(run, "final_command", ()) or ())]
            receipt.update({
                "returncode": int(getattr(result, "returncode", -1)) if result is not None else None,
                "stdout_chars": len(text),
                "stderr_chars": len(stderr),
                "stderr_head": stderr[:1000],
                "command": redact_prompt_command(command, "<prompt>") if command else [],
                "recovery_note": getattr(run, "recovery_note", None),
            })
            return finish(text, receipt)
        except Exception as exc:  # noqa: BLE001
            if provider == "codex" and model:
                try:
                    if prior_model_env is None:
                        os.environ.pop(scoped_model_env, None)
                    else:
                        os.environ[scoped_model_env] = prior_model_env
                except Exception:
                    pass
            receipt["exception_type"] = type(exc).__name__
            receipt["exception_message"] = str(exc)[:500]
            return finish("", receipt)
    # API providers (gemini/deepseek allowed). Fallback stays within the same family → never a
    # metered OpenAI/Anthropic call.
    try:
        from ztare.common.llm_runtime import LLMRuntime
    except Exception:
        try:
            from ztare.common.llm_runtime import LLMRuntime
        except Exception as exc:  # noqa: BLE001
            receipt["exception_type"] = type(exc).__name__
            receipt["exception_message"] = str(exc)[:500]
            return finish("", receipt)
    # Resolve through the central registry (MODEL_MAP, policy-overridable via principal.yaml `model_map`) so a
    # stale version id is retargeted in ONE place, not hardcoded here.
    def _rid(alias: str, default: str) -> str:
        try:
            from ztare.common.llm_runtime import resolve_model_id
            return resolve_model_id(alias)
        except Exception:  # noqa: BLE001
            return default
    mid = model or (_rid("deepseek", "deepseek-chat") if provider == "deepseek" else _rid("gemini", "gemini-3.1-pro-preview"))
    fb = () if provider == "deepseek" else (_rid("gemini-lite", "gemini-3.1-flash-lite-preview"),)
    try:
        resp = LLMRuntime().call_text(prompt, model_id=mid, fallback_model_ids=fb,
                                      max_tokens=2000, request_label="constraint_isomorphism_query",
                                      timeout_seconds=timeout_s)
        text = getattr(resp, "text", "") or ""
        receipt.update({
            "model": mid,
            "stdout_chars": len(text),
            "effective_model_id": getattr(resp, "effective_model_id", None),
            "model_id_used": getattr(resp, "model_id_used", None),
            "returncode": 0,
        })
        return finish(text, receipt)
    except Exception as exc:  # noqa: BLE001
        receipt["model"] = mid
        receipt["exception_type"] = type(exc).__name__
        receipt["exception_message"] = str(exc)[:500]
        return finish("", receipt)


def _parse_isomorphisms(text: str) -> "list[SurfacedIsomorphism]":
    """Parse one provider response without dispatching or validating a target fingerprint."""

    import json
    import re as _re
    if not text:
        return []
    m = _re.search(r"\[.*\]", text, _re.S)
    if not m:
        return []
    try:
        items = json.loads(m.group(0))
    except Exception:
        return []
    out: list[SurfacedIsomorphism] = []
    for it in items if isinstance(items, list) else []:
        if not isinstance(it, dict):
            continue
        raw_morphism = it.get("constraint_morphism", it.get("morphism"))
        morphism = ConstraintMorphism.from_dict(raw_morphism) if isinstance(raw_morphism, dict) else None
        out.append(SurfacedIsomorphism(
            theorem=str(it.get("theorem", "")).strip(),
            field=str(it.get("field", "")).strip(),
            mechanism=str(it.get("mechanism", "")).strip(),
            mapping_hint=str(it.get("mapping_hint", "")).strip(),
            raw=json.dumps(it)[:400],
            invariant_map=it.get("invariant_map") if isinstance(it.get("invariant_map"), dict) else {},
            morphism=morphism))
    return [o for o in out if o.theorem]


def default_llm_query(fp: ConstraintFingerprint, n: int = 5, *, provider: str = "gemini",
                      model: "str | None" = None, typed_mapping: bool = False,
                      mode: str = "solve") -> "list[SurfacedIsomorphism]":
    """Production Step-2: query a frontier LLM with the structural-only prompt and parse the JSON.
    Provider-flexible (gemini API default `gemini-3.1-pro-preview`; codex/claude via subscription CLI;
    deepseek API) — see `_dispatch_text`. Returns [] (never raises) on any runtime/parse failure.
    #122 opt-ins (defaults reproduce the prior behavior byte-for-byte): `typed_mapping` demands an
    invariant→counterpart map per candidate; `mode="impossibility"` asks for no-go results instead."""
    prompt = _build_query_prompt(fp, n, typed_mapping=typed_mapping, mode=mode)
    return _parse_isomorphisms(_dispatch_text(prompt, provider=provider, model=model))


def prediction_specificity(conj: SurfacedConjecture) -> float:
    """Deterministic specificity score for conjectures.

    This deliberately does not score plausibility. It ranks predictions/kill conditions that
    name bounded, inspectable consequences instead of vague downstream benefit.
    """
    import re

    preds = conj.novel_predictions if isinstance(conj.novel_predictions, dict) else {}
    kills = conj.kill_conditions if isinstance(conj.kill_conditions, dict) else {}
    rows: list[tuple[object, object]] = []
    for side in ("left", "right"):
        ps = preds.get(side) or []
        ks = kills.get(side) or []
        if isinstance(ps, str):
            ps = [ps]
        if isinstance(ks, str):
            ks = [ks]
        for idx, pred in enumerate(ps):
            kill = ks[idx] if idx < len(ks) else ""
            rows.append((pred, kill))
    if not rows:
        return 0.0

    def _text_and_fields(x) -> "tuple[str, set[str]]":
        if isinstance(x, dict):
            fields = {str(k) for k, v in x.items() if str(v).strip()}
            return " ".join(str(v) for v in x.values()), fields
        return str(x), set()

    def row_score(pred, kill) -> float:
        pred, pred_fields = _text_and_fields(pred)
        kill, kill_fields = _text_and_fields(kill)
        blob = f"{pred} {kill}".lower()
        score = 0.0
        if len(pred.strip()) >= 24 and len(kill.strip()) >= 16:
            score += 0.25
        if re.search(r"\b\d+(/\d+)?\b|[<>=]|<=|>=", blob):
            score += 0.25
        if any(w in blob for w in ("action", "step", "transition", "state", "cell", "bound", "within", "before", "after")):
            score += 0.25
        if any(w in blob for w in ("refute", "kill", "fail", "reject", "falsify", "contradict")):
            score += 0.25
        if {"measurement", "intervention", "horizon", "expected_observation"} <= pred_fields:
            score += 0.25
        if {"refuter", "gate"} <= kill_fields:
            score += 0.25
        return min(1.0, score)

    return sum(row_score(p, k) for p, k in rows) / len(rows)


def _parse_conjectures(text: str) -> "list[SurfacedConjecture]":
    import json
    import re as _re

    if not text:
        return []
    m = _re.search(r"\[.*\]", text, _re.S)
    if not m:
        return []
    try:
        items = json.loads(m.group(0))
    except Exception:
        return []
    out: list[SurfacedConjecture] = []
    for it in items if isinstance(items, list) else []:
        if not isinstance(it, dict):
            continue
        mother = str(it.get("mother_structure", "")).strip()
        if not mother:
            continue
        c = SurfacedConjecture(
            mother_structure=mother,
            lowerings=it.get("lowerings") if isinstance(it.get("lowerings"), dict) else {},
            novel_predictions=it.get("novel_predictions") if isinstance(it.get("novel_predictions"), dict) else {},
            kill_conditions=it.get("kill_conditions") if isinstance(it.get("kill_conditions"), dict) else {},
            prior_art_inversion=(
                it.get("prior_art_inversion")
                if isinstance(it.get("prior_art_inversion"), dict)
                else {}
            ),
            raw=json.dumps(it)[:800],
        )
        c.specificity = prediction_specificity(c)
        out.append(c)
    return out


def default_llm_conjecture_query(left: ConstraintFingerprint, right: ConstraintFingerprint, n: int = 5, *,
                                provider: str = "gemini",
                                model: "str | None" = None) -> "list[SurfacedConjecture]":
    """Production query for a proposed new correspondence between two fingerprints."""
    prompt = _build_conjecture_prompt(left, right, n)
    return _parse_conjectures(_dispatch_text(prompt, provider=provider, model=model))


_PLACEHOLDER_MAPPINGS = {"", "n/a", "none", "null", "-", "?", "tbd", "todo", "unset"}


def _mapped_invariant_keys(fp: ConstraintFingerprint) -> "set[str]":
    """The fingerprint invariants a candidate is required to map (the no-good feedback key is exempt —
    it is a do-not-resurface hint, not structure to transport)."""
    return {k for k in fp.invariants if k != "do_not_resurface_refuted_transports"}


def _legacy_mapping_entry_valid(key: str, source_value: object, value: object) -> bool:
    """Validate old `invariant_map` entries without pretending they are morphisms.

    Structured entries can declare types and a transform. Plain strings remain
    readable for old ledgers but must share a structural token/class with the
    source invariant; arbitrary labels such as `x` or `banana` fail.
    """

    if isinstance(value, dict):
        target = value.get("target")
        if not _component_name_is_meaningful(target):
            return False
        source_type = _infer_invariant_type(source_value)
        declared_source = value.get("source_type")
        declared_target = value.get("target_type")
        if declared_source is not None and _normalize_component_type(declared_source) != source_type:
            return False
        if declared_target is not None:
            target_type = _normalize_component_type(declared_target)
            transform = str(value.get("transform") or "").strip()
            if not _types_compatible(source_type, target_type) and not _component_name_is_meaningful(transform):
                return False
        return True
    return _component_name_is_meaningful(value) and _components_semantically_related(key, source_value, value)


def _invariant_covered(invariant_map: "dict | None", key: str, source_value: object = None) -> bool:
    """Per-key coverage check SHARED by the hard gate (validate_typed_mapping) and the graded score
    (enrichment_degree): a key counts only if the candidate maps it to a non-empty, non-placeholder
    value. Extracted so both read coverage the same way (no duplicated parsing)."""
    v = (invariant_map or {}).get(key)
    if v is None:
        return False
    return _legacy_mapping_entry_valid(key, source_value, v)


def enrichment_degree(iso: SurfacedIsomorphism, fp: ConstraintFingerprint) -> float:
    """DETERMINISTIC graded-transport score: the fraction of the fingerprint's invariant keys this
    candidate covers with a real (non-empty, non-placeholder) `invariant_map` entry — the same per-key
    check the hard gate uses. NO LLM / embedding / semantic scalar (rejected as unauditable): pure typed
    coverage. 1.0 = every invariant mapped (what the hard gate demands); a lower value is a PARTIAL
    transport. Empty fingerprint (no keys to cover) → 1.0."""
    keys = _mapped_invariant_keys(fp)
    if not keys:
        return 1.0
    return sum(_invariant_covered(iso.invariant_map, k, fp.invariants.get(k)) for k in keys) / len(keys)


def validate_typed_mapping(isos: "list[SurfacedIsomorphism]", fp: ConstraintFingerprint,
                           min_degree: float = 1.0) -> "tuple[list[SurfacedIsomorphism], list[SurfacedIsomorphism]]":
    """MECHANICAL decorative-analogy filter (#122): keep candidates whose typed-map coverage
    (enrichment_degree) is at least `min_degree`. Default 1.0 = the original hard gate (map EVERY
    fingerprint invariant, minus the no-good feedback key). A caller passing e.g. 0.5 accepts PARTIAL
    transports. Survivors get their score stamped on `.enrichment`. Returns (kept, rejected) — the
    rejected list is retained for the audit trail, never silently dropped."""
    keys = _mapped_invariant_keys(fp)
    kept, rejected = [], []
    for iso in isos:
        typed_morphism_valid = False
        if iso.morphism is not None:
            morphism = iso.morphism if isinstance(iso.morphism, ConstraintMorphism) else ConstraintMorphism.from_dict(iso.morphism)
            iso.morphism = morphism
            validation = validate_constraint_morphism(morphism)
            expected = ConstraintSignature.from_fingerprint(fp, name=morphism.source_signature.name)
            source_matches = (
                set(expected.components) == set(morphism.source_signature.components)
                and all(
                    _normalize_component_type(morphism.source_signature.components.get(key)) == expected.components[key]
                    for key in expected.components
                )
            )
            if not source_matches:
                validation = MorphismValidation(
                    valid=False,
                    verified=False,
                    errors=validation.errors + ("source_signature:fingerprint_mismatch",),
                    warnings=validation.warnings,
                )
            iso.transport_validation = {
                **validation.to_dict(),
                "status": "verified" if validation.verified else ("schema_valid" if validation.valid else "rejected"),
                "morphism_hash": morphism.content_hash(),
            }
            if not validation.valid:
                rejected.append(iso)
                continue
            typed_morphism_valid = True
            if not iso.invariant_map:
                iso.invariant_map = {
                    key: str(entry.get("target") or "")
                    for key, entry in morphism.component_map.items()
                }
        deg = (
            (len(keys & set(iso.morphism.component_map)) / len(keys) if keys else 1.0)
            if typed_morphism_valid and isinstance(iso.morphism, ConstraintMorphism)
            else enrichment_degree(iso, fp)
        )
        if deg >= min_degree:
            iso.enrichment = deg
            if not iso.transport_validation:
                iso.transport_validation = {
                    "status": "legacy_typed_mapping",
                    "valid": True,
                    "verified": False,
                    "warnings": ("no_constraint_morphism",),
                }
            kept.append(iso)
        else:
            iso.transport_validation = {
                **iso.transport_validation,
                "status": "rejected",
                "valid": False,
                "verified": False,
                "errors": tuple(iso.transport_validation.get("errors") or ()) + ("semantic_invariant_coverage",),
            }
            rejected.append(iso)
    return kept, rejected


def second_order_fingerprint(fp: ConstraintFingerprint,
                             first_round: "list[SurfacedIsomorphism]") -> ConstraintFingerprint:
    """SECOND-ORDER DEANCHOR (#122): banning the home FIELD is not enough — the first round's answers
    reveal which latent neighborhoods the fingerprint's own nouns pull toward. Forbid the first
    round's FIELDS too, forcing the next query into structurally more distant structure. Returns a NEW
    fingerprint (the original is never mutated)."""
    fields = sorted({i.field for i in first_round if i.field})
    extra = ("; ALSO do not answer from any of these already-surfaced fields: " + ", ".join(fields)
             if fields else "")
    return ConstraintFingerprint(
        constraint_class=fp.constraint_class,
        abstract_form=fp.abstract_form,
        invariants=dict(fp.invariants),
        forbidden_domain=(fp.forbidden_domain or "the home field") + extra)


def signatures_compatible(left: ConstraintSignature, right: ConstraintSignature) -> bool:
    """Whether two signatures can be joined without an implicit rename or cast."""

    return (
        set(left.components) == set(right.components)
        and all(
            _normalize_component_type(left.components[key])
            == _normalize_component_type(right.components[key])
            for key in left.components
        )
    )


def _compose_map_entries(first: dict[str, dict[str, Any]], second: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    composed: dict[str, dict[str, Any]] = {}
    for source, first_entry in first.items():
        if not isinstance(first_entry, dict):
            raise ValueError(f"first component map entry {source!r} is not structured")
        middle = str(first_entry.get("target") or "").strip()
        second_entry = second.get(middle)
        if not isinstance(second_entry, dict):
            raise ValueError(f"second morphism does not map bridge component {middle!r}")
        target = str(second_entry.get("target") or "").strip()
        if not target:
            raise ValueError(f"second component map entry {middle!r} has no target")
        composed[source] = {
            "target": target,
            "source_type": _normalize_component_type(first_entry.get("source_type")),
            "target_type": _normalize_component_type(second_entry.get("target_type")),
            "transform": " |> ".join(
                part for part in (
                    str(first_entry.get("transform") or "").strip(),
                    str(second_entry.get("transform") or "").strip(),
                ) if part
            ),
            "via": middle,
        }
    return composed


def compose_constraint_morphisms(first: ConstraintMorphism, second: ConstraintMorphism) -> ConstraintMorphism:
    """Compose A->B and B->C after validating both carriers and the B signature.

    Composition creates fresh, pending A->C preservation and round-trip
    obligations. Proofs for each hop are evidence for the construction, but do
    not by themselves verify the composite target-side claim.
    """

    first_validation = validate_constraint_morphism(first)
    second_validation = validate_constraint_morphism(second)
    if not first_validation.valid:
        raise ValueError(f"first morphism invalid: {list(first_validation.errors)}")
    if not second_validation.valid:
        raise ValueError(f"second morphism invalid: {list(second_validation.errors)}")
    if not signatures_compatible(first.target_signature, second.source_signature):
        raise ValueError("bridge signature mismatch")

    component_map = _compose_map_entries(first.component_map, second.component_map)
    first_hash = first.content_hash()
    second_hash = second.content_hash()
    obligations = [
        {
            "source": source,
            "target": entry["target"],
            "predicate": f"composite preserves {source} through bridge component {entry['via']}",
            "status": "pending",
            "check": {
                "first_morphism_hash": first_hash,
                "second_morphism_hash": second_hash,
            },
        }
        for source, entry in component_map.items()
    ]
    inverse = None
    round_trips: list[dict[str, Any]] = []
    relation = "transport"
    if first.inverse_component_map is not None and second.inverse_component_map is not None:
        inverse = _compose_map_entries(second.inverse_component_map, first.inverse_component_map)
        if first.relation == second.relation == "isomorphism":
            relation = "isomorphism"
            round_trips = [
                {
                    "direction": direction,
                    "predicate": "composed forward and inverse maps return the original component",
                    "status": "pending",
                    "check": {
                        "first_morphism_hash": first_hash,
                        "second_morphism_hash": second_hash,
                    },
                }
                for direction in ("source_to_target_to_source", "target_to_source_to_target")
            ]
    discriminator = dict(second.target_discriminator)
    discriminator["upstream_morphism_hash"] = first_hash
    discriminator["second_morphism_hash"] = second_hash
    composed = ConstraintMorphism(
        source_signature=first.source_signature,
        target_signature=second.target_signature,
        component_map=component_map,
        preservation_obligations=obligations,
        information_losses=list(dict.fromkeys(first.information_losses + second.information_losses)),
        inverse_component_map=inverse,
        round_trip_obligations=round_trips,
        target_discriminator=discriminator,
        relation=relation,
    )
    validation = validate_constraint_morphism(composed)
    if not validation.valid:
        raise ValueError(f"composed morphism invalid: {list(validation.errors)}")
    return composed


def compose_transports(fp: ConstraintFingerprint, first_hop: "list[SurfacedIsomorphism]",
                       query: "IsomorphismQuery", n: int = 4,
                       rejected_sink: "list[SurfacedIsomorphism] | None" = None) -> "list[SurfacedIsomorphism]":
    """COMPOSITIONAL TWO-HOP TRANSPORT (A~C via B). Langlands-scale connections are found by
    COMPOSING two partial matches: the shared abstraction between the seam A and a distant field C
    is itself a bridge structure B surfaced in the first hop. Single-hop stops at B; this hops
    again. For each first-hop candidate B (cap 3), build a BRIDGE fingerprint asking what solves
    B's mechanism — deanchored from BOTH the home field AND B's field — while CARRYING the original
    bridge signature when B carries a typed morphism. A and C are joined only by
    `compose_constraint_morphisms`, which checks both hops and source/target compatibility.
    Legacy candidates remain visible as explicitly unverified advice, with no multiplied score.
    Mixed or invalid typed/legacy paths are rejected instead of scalar-laundered."""
    seen = {(b.theorem, b.field) for b in first_hop}
    out: "list[SurfacedIsomorphism]" = []
    for b in first_hop[:3]:
        first_morphism = b.morphism if isinstance(b.morphism, ConstraintMorphism) else (
            ConstraintMorphism.from_dict(b.morphism) if isinstance(b.morphism, dict) else None
        )
        if first_morphism is not None and not validate_constraint_morphism(first_morphism).valid:
            b.transport_validation = {
                "status": "rejected",
                "errors": validate_constraint_morphism(first_morphism).errors,
            }
            if rejected_sink is not None:
                rejected_sink.append(b)
            continue
        bridge_invariants = (
            dict(first_morphism.target_signature.components)
            if first_morphism is not None else dict(fp.invariants)
        )
        bridge = ConstraintFingerprint(
            constraint_class=f"the {b.theorem} mechanism ({b.mechanism}), abstracted from {b.field}",
            abstract_form=fp.abstract_form,
            invariants=bridge_invariants,
            forbidden_domain=", ".join(p for p in (fp.forbidden_domain, b.field) if p) or None)
        for iso in query(bridge, n) or []:
            key = (iso.theorem, iso.field)
            if key in seen:
                continue
            second_morphism = iso.morphism if isinstance(iso.morphism, ConstraintMorphism) else (
                ConstraintMorphism.from_dict(iso.morphism) if isinstance(iso.morphism, dict) else None
            )
            composed = None
            if first_morphism is not None and second_morphism is not None:
                try:
                    composed = compose_constraint_morphisms(first_morphism, second_morphism)
                except ValueError as exc:
                    iso.transport_validation = {"status": "rejected", "errors": (str(exc),)}
                    if rejected_sink is not None:
                        rejected_sink.append(iso)
                    continue
            elif first_morphism is not None or second_morphism is not None:
                iso.transport_validation = {"status": "rejected", "errors": ("mixed_typed_legacy_path",)}
                if rejected_sink is not None:
                    rejected_sink.append(iso)
                continue

            seen.add(key)
            candidate = SurfacedIsomorphism(
                theorem=iso.theorem,
                field=iso.field,
                mechanism=iso.mechanism,
                mapping_hint=f"via {b.theorem} ({b.field}): " + (iso.mapping_hint or ""),
                raw=iso.raw,
                invariant_map=(
                    {source: entry["target"] for source, entry in composed.component_map.items()}
                    if composed is not None else dict(iso.invariant_map or {})
                ),
                enrichment=1.0 if composed is not None else None,
                morphism=composed,
                transport_validation=(
                    {
                        **validate_constraint_morphism(composed).to_dict(),
                        "status": "schema_valid_composition",
                        "morphism_hash": composed.content_hash(),
                    }
                    if composed is not None else {
                        "status": "unverified_legacy_composition",
                        "valid": False,
                        "verified": False,
                        "warnings": ("no_constraint_morphism",),
                    }
                ),
            )
            out.append(candidate)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Self-test — a MOCK domain + MOCK query prove the orchestration with no LLM / no Lean.
# It encodes the canonical worked example: a "context dilution as length grows" ceiling, whose
# abstract form is bounded-width sequential composition; the mock query surfaces Barrington-style
# bounded-width composition; compiling it to a "prune context to bound width" gate IMPROVES the
# oracle — i.e. the loop rediscovers the MDL-library lever from the failure. (A useless match does
# NOT improve the oracle and is dropped.)
# ─────────────────────────────────────────────────────────────────────────────

def _self_test() -> int:
    fails = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    class _MockDomain:
        """A toy proof-search-like domain: 'width' (context size) grows with build-up length and
        dilutes closure. A gate that BOUNDS width improves the holdout closure rate; an irrelevant
        gate does not."""
        def abstract_failure(self, fs):
            return ConstraintFingerprint(
                constraint_class="bounded-resource sequential composition",
                abstract_form="capability degrades as sequence length L grows while working width W "
                              "grows unbounded; need expressive composition at bounded W",
                invariants={"width_grows_with_length": True, "depth": "O(L)", "target_width": "O(1)"},
                forbidden_domain="theorem-proving")

        def compile_to_test(self, iso, context):
            # The gate is a POLICY this domain's oracle applies per item (opaque to the engine).
            mech = (iso.mechanism + " " + iso.theorem + " " + iso.mapping_hint).lower()
            if "width" in mech or "bound" in mech or "prune" in mech:
                # the useful match → a policy that PRUNES width to the target (the MDL-library action)
                return lambda item: dict(item, width=min(item["width"], item["target_width"]))
            if "unmappable" in mech:
                raise ValueError("cannot map this match onto the system")
            return lambda item: item  # irrelevant match → identity policy (changes nothing)

        def oracle(self, gate, holdout):
            # closure rate over holdout; only a gate that actually bounds width rescues long items.
            closed = 0
            for item in holdout:
                eff = item if gate is None else gate(item)
                closed += 1 if eff["width"] <= item["needs_width"] else 0
            return closed / max(1, len(holdout))

        def banned_terms(self):
            return ["lean", "tactic", "mathlib", "proof"]

    # holdout: short items close either way; long items only close once width is bounded.
    holdout = [{"width": 1, "needs_width": 1, "target_width": 1},
               {"width": 5, "needs_width": 1, "target_width": 1},
               {"width": 9, "needs_width": 1, "target_width": 1}]

    def mock_query(fp, n):
        return [
            SurfacedIsomorphism("Barrington's theorem", "complexity theory",
                                "bounded-width branching programs compute richly via composition; "
                                "bound the working width and compose in depth",
                                "width←provisioned context; prune to bound it"),
            SurfacedIsomorphism("Noether's theorem", "physics",
                                "a continuous symmetry yields a conserved quantity",
                                "maps to invariants under a group action"),
            SurfacedIsomorphism("Unmappable thing", "x", "unmappable", "x"),
        ]

    loop = IsomorphismLoop(_MockDomain(), query=mock_query)
    verdicts = loop.run(failure_state=None, holdout=holdout, n_candidates=3)
    ok("returns_a_verdict_per_candidate", len(verdicts) == 3)
    best = loop.best(failure_state=None, holdout=holdout, n_candidates=3)
    ok("best_is_the_width_bounding_match", best is not None and "Barrington" in best.iso.theorem)
    ok("best_improves_oracle", best is not None and best.improves and best.delta > 0)
    irrelevant = [v for v in verdicts if "Noether" in v.iso.theorem][0]
    ok("irrelevant_match_does_not_improve", not irrelevant.improves and irrelevant.delta == 0)
    unmappable = [v for v in verdicts if "Unmappable" in v.iso.theorem][0]
    ok("unmappable_match_flagged", "unmappable" in unmappable.detail and not unmappable.improves)

    # contamination guard fires on a leaked home-domain term
    class _LeakyDomain(_MockDomain):
        def abstract_failure(self, fs):
            fp = super().abstract_failure(fs)
            fp.abstract_form += " (this is a Lean tactic proof problem)"  # leaks 'lean'/'tactic'/'proof'
            return fp
    leaked = False
    try:
        IsomorphismLoop(_LeakyDomain(), query=mock_query).run(None, holdout)
    except ValueError:
        leaked = True
    ok("contamination_guard_fires_on_leak", leaked)

    # a domain with NO matches surfaced → best() is None (nothing rediscovered)
    none_best = IsomorphismLoop(_MockDomain(), query=lambda fp, n: []).best(None, holdout)
    ok("no_matches_returns_none", none_best is None)

    # ── #122 opt-ins: default path BYTE-PARITY + the three new mechanisms ──
    _fp = ConstraintFingerprint("c", "a", {"inv1": 1, "inv2": "x"}, forbidden_domain="ITP")
    _base = _build_query_prompt(_fp, 3)
    ok("default prompt has NO #122 blocks (parity)",
       "invariant_map" not in _base and "IMPOSSIBILITY" not in _base)
    _typed = _build_query_prompt(_fp, 3, typed_mapping=True)
    ok("typed prompt demands the invariant map for every key",
       "invariant_map" in _typed and "inv1" in _typed and "inv2" in _typed)
    _imp = _build_query_prompt(_fp, 3, mode="impossibility")
    ok("impossibility prompt asks for no-go results", "IMPOSSIBILITY / NO-GO" in _imp
       and "SOLVE or OPTIMIZE" not in _imp)
    _good = SurfacedIsomorphism("T1", "f1", "m", invariant_map={
        "inv1": {"target": "source cardinality", "source_type": "integer", "target_type": "integer", "transform": "identity"},
        "inv2": {"target": "source symbol", "source_type": "symbol", "target_type": "symbol", "transform": "identity"},
    })
    _bad = SurfacedIsomorphism("T2", "f2", "m", invariant_map={
        "inv1": {"target": "source cardinality", "source_type": "integer", "target_type": "integer", "transform": "identity"},
    })   # inv2 unmapped
    kept, rej = validate_typed_mapping([_good, _bad], _fp)
    ok("typed validation: full map kept, partial map REJECTED (auditable)",
       [k.theorem for k in kept] == ["T1"] and [r.theorem for r in rej] == ["T2"])
    _fp2 = second_order_fingerprint(_fp, [_good, _bad])
    ok("second-order deanchor forbids first-round fields, original unmutated",
       "f1" in _fp2.forbidden_domain and "f2" in _fp2.forbidden_domain
       and _fp.forbidden_domain == "ITP")
    # no-good feedback key is exempt from the typed-coverage requirement
    _fp3 = ConstraintFingerprint("c", "a", {"inv1": 1, "do_not_resurface_refuted_transports": ["x"]})
    k3, _ = validate_typed_mapping([SurfacedIsomorphism("T3", "f", "m", invariant_map={
        "inv1": {"target": "source cardinality", "source_type": "integer", "target_type": "integer", "transform": "identity"},
    })], _fp3)
    ok("feedback key exempt from typed coverage", len(k3) == 1)

    # ── two-hop compositional transport (A~C via B): pure orchestration over the query ──
    _seam = ConstraintFingerprint("seam", "af", {"inv1": 1}, forbidden_domain="fluid PDE")
    _B = SurfacedIsomorphism("Heat-kernel bound", "spectral geometry", "gaussian off-diagonal decay", "orig")
    _C = SurfacedIsomorphism("LT ripple", "coding theory", "peeling decoder", "chint")
    _bridges = []

    def _bridge_q(bfp, k):
        _bridges.append(bfp)
        return [_B, _C]   # _B duplicates first_hop → must be deduped out

    _two = compose_transports(_seam, [_B], _bridge_q, n=3)
    ok("two-hop bridge forbids BOTH the home and the bridge field",
       bool(_bridges) and "fluid PDE" in _bridges[0].forbidden_domain
       and "spectral geometry" in _bridges[0].forbidden_domain)
    ok("two-hop bridge carries the ORIGINAL seam invariants (validates vs seam, not B)",
       _bridges[0].invariants == {"inv1": 1})
    ok("two-hop bridge names B's mechanism + field in the constraint class",
       "Heat-kernel bound" in _bridges[0].constraint_class
       and "spectral geometry" in _bridges[0].constraint_class)
    ok("two-hop result annotated 'via B', deduped against first_hop",
       len(_two) == 1 and _two[0].theorem == "LT ripple"
       and _two[0].mapping_hint == "via Heat-kernel bound (spectral geometry): chint")

    # ── enrichment degree (graded transport): deterministic typed-map coverage ──
    _efp = ConstraintFingerprint("c", "a", {"k1": 1, "k2": 2})
    _e0 = SurfacedIsomorphism("E0", "f", "m", invariant_map={})               # 0/2
    _e1 = SurfacedIsomorphism("E1", "f", "m", invariant_map={
        "k1": {"target": "first cardinality", "source_type": "integer", "target_type": "integer", "transform": "identity"},
    })       # 1/2
    _e2 = SurfacedIsomorphism("E2", "f", "m", invariant_map={
        "k1": {"target": "first cardinality", "source_type": "integer", "target_type": "integer", "transform": "identity"},
        "k2": {"target": "second cardinality", "source_type": "integer", "target_type": "integer", "transform": "identity"},
    })  # 2/2
    ok("enrichment_degree grades 0/2, 1/2, 2/2 typed-map coverage",
       enrichment_degree(_e0, _efp) == 0.0 and enrichment_degree(_e1, _efp) == 0.5
       and enrichment_degree(_e2, _efp) == 1.0)
    _kd, _rd = validate_typed_mapping([_e1], _efp)               # default min_degree=1.0
    _kp, _rp = validate_typed_mapping([_e1], _efp, min_degree=0.5)
    ok("min_degree default rejects a half-mapped candidate; 0.5 admits it with score attached",
       not _kd and [r.theorem for r in _rd] == ["E1"]
       and [k.theorem for k in _kp] == ["E1"] and _kp[0].enrichment == 0.5)

    # ── legacy two-hop scores do not become evidence for the composite path ──
    _bh = SurfacedIsomorphism("Bridge", "spectral geometry", "mech", "orig", enrichment=0.5)
    _ch = SurfacedIsomorphism("Cee", "coding theory", "mech2", "chint", enrichment=0.4)
    _mul = compose_transports(
        ConstraintFingerprint("s", "a", {"inv1": 1}, forbidden_domain="pde"),
        [_bh], lambda bfp, k: [_ch], n=2)
    ok("legacy two-hop remains unverified and does not multiply scalar scores",
       len(_mul) == 1 and _mul[0].enrichment is None
       and _mul[0].transport_validation.get("status") == "unverified_legacy_composition")

    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())
