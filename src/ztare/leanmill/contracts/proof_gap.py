"""Content-bound carrier for repeated Lean proof gaps.

The carrier only decides whether observations may be routed into quarantined
AxiomPack candidate generation.  It cannot grant proof credit, promote an
axiom, mutate a theory, or replace the signed unseen-task shadow evaluation.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any, Iterable, Mapping

from ztare.leanmill.formalization_admission import ADMITTED, FormalizationAdmission
from ztare.leanmill.formal_verification_provider import sha256_ref


REGISTERED_GAP_FAMILY_SCHEMA = "leanmill.registered_gap_family.v1"
PROOF_GAP_RECEIPT_SCHEMA = "leanmill.proof_gap_receipt.v1"
PROOF_GAP_RECEIPT_BUNDLE_SCHEMA = "leanmill.proof_gap_receipt_bundle.v1"
AXIOM_PACK_ESCALATION_SCHEMA = "leanmill.axiom_pack_escalation_eligibility.v1"
EXACT_GAP_OUTCOME = "admitted_and_exact_gap"

_SHA256_REF = re.compile(r"^sha256:[0-9a-f]{64}$")
_FORBIDDEN_FAILURE_MARKERS = (
    "apparatus",
    "budget",
    "cheat",
    "closed",
    "closure",
    "falsif",
    "refut",
    "timeout",
    "timed out",
)


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def _digest(value: Any) -> str:
    encoded = value if isinstance(value, str) else _canonical_json(value)
    return sha256_ref(encoded)


def _require_digest(value: str, *, field_name: str) -> None:
    if not isinstance(value, str) or not _SHA256_REF.fullmatch(value):
        raise ValueError(f"{field_name} must be a canonical sha256 reference")


def _require_text(value: str, *, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{field_name} must be a non-empty canonical string")


def _require_exact_keys(
    value: Mapping[str, Any], required: set[str], *, context: str
) -> None:
    if set(value) != required:
        missing = sorted(required - set(value))
        unknown = sorted(set(value) - required)
        raise ValueError(f"{context} schema mismatch: missing={missing}, unknown={unknown}")


def _normalized_target_signature(source: str, target_name: str) -> str:
    """Normalize only after the canonical Lean declaration extractor runs."""

    from ztare.leanmill.lean_source import extract_signature, strip_comments

    return " ".join(strip_comments(extract_signature(source, target_name) or "").split())


def _target_equivalence_digest(source: str) -> str:
    """Alpha/binder-placement invariant identity via LeanMill's existing cache normalizer.

    This key is used only to *deduplicate* evidence.  Any over-collapse therefore
    blocks an escalation; it cannot create an unsafe eligibility decision.
    """

    from ztare.leanmill.solver.proof_cache import normalize_statement_equiv

    normalized = normalize_statement_equiv(source)
    if not normalized:
        raise ValueError("admitted target has no canonical equivalence key")
    return _digest(normalized)


def _presence_digest(value: Any) -> str:
    if value is None or value == "" or value == {} or value == []:
        return ""
    if isinstance(value, str) and _SHA256_REF.fullmatch(value):
        return value
    return _digest(value)


@dataclass(frozen=True)
class RegisteredGapFamily:
    """Explicit gap-family registration and theory/substrate binding.

    ``registry_digest`` binds the registration artifact.  This object records
    that reference; signature/authority checks belong to the registry reader,
    not this pure routing contract.
    """

    family_id: str
    structure_adapter_id: str
    gap_kind: str
    registry_digest: str
    base_theory_digest: str
    substrate_digest: str
    schema: str = REGISTERED_GAP_FAMILY_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != REGISTERED_GAP_FAMILY_SCHEMA:
            raise ValueError(f"unsupported gap-family schema: {self.schema!r}")
        for name in ("family_id", "structure_adapter_id", "gap_kind"):
            _require_text(getattr(self, name), field_name=name)
        for name in ("registry_digest", "base_theory_digest", "substrate_digest"):
            _require_digest(getattr(self, name), field_name=name)

    def _content(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "family_id": self.family_id,
            "structure_adapter_id": self.structure_adapter_id,
            "gap_kind": self.gap_kind,
            "registry_digest": self.registry_digest,
            "base_theory_digest": self.base_theory_digest,
            "substrate_digest": self.substrate_digest,
        }

    @property
    def family_digest(self) -> str:
        return _digest(self._content())

    def to_json(self) -> dict[str, Any]:
        return {**self._content(), "family_digest": self.family_digest}

    @classmethod
    def from_json(cls, value: Mapping[str, Any]) -> "RegisteredGapFamily":
        if not isinstance(value, Mapping):
            raise ValueError("registered gap family must be a JSON object")
        _require_exact_keys(
            value,
            {
                "schema",
                "family_id",
                "structure_adapter_id",
                "gap_kind",
                "registry_digest",
                "base_theory_digest",
                "substrate_digest",
                "family_digest",
            },
            context="registered gap family",
        )
        scalar_fields = (
            "schema",
            "family_id",
            "structure_adapter_id",
            "gap_kind",
            "registry_digest",
            "base_theory_digest",
            "substrate_digest",
            "family_digest",
        )
        if not all(isinstance(value.get(name), str) for name in scalar_fields):
            raise ValueError("registered gap family scalar fields must be strings")
        result = cls(
            family_id=value["family_id"],
            structure_adapter_id=value["structure_adapter_id"],
            gap_kind=value["gap_kind"],
            registry_digest=value["registry_digest"],
            base_theory_digest=value["base_theory_digest"],
            substrate_digest=value["substrate_digest"],
            schema=value["schema"],
        )
        if value["family_digest"] != result.family_digest:
            raise ValueError("registered gap family digest mismatch")
        return result


@dataclass(frozen=True)
class ProofGapReceipt:
    """A formalization-admission-bound solver observation.

    Semantic eligibility is intentionally checked by
    :func:`evaluate_axiom_pack_escalation`; a receipt may represent a blocked
    observation so callers receive an inspectable reason instead of an
    exception-only path.
    """

    family: RegisteredGapFamily
    formalization_admission: FormalizationAdmission
    outcome: str
    faithful: bool | None
    failure_class_json: str
    budget_killed: bool
    governance_json: str = "null"
    refutation_json: str = "null"
    closure_certificate_json: str = "null"
    schema: str = PROOF_GAP_RECEIPT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != PROOF_GAP_RECEIPT_SCHEMA:
            raise ValueError(f"unsupported proof-gap receipt schema: {self.schema!r}")
        if not isinstance(self.family, RegisteredGapFamily):
            raise ValueError("family must be a RegisteredGapFamily")
        if not isinstance(self.formalization_admission, FormalizationAdmission):
            raise ValueError("formalization_admission must be a FormalizationAdmission")
        if self.formalization_admission.status != ADMITTED:
            raise ValueError("proof-gap receipt requires an admitted formalization")
        _require_text(self.outcome, field_name="outcome")
        if self.faithful not in (True, False, None):
            raise ValueError("faithful must be true, false, or null")
        if type(self.budget_killed) is not bool:
            raise ValueError("budget_killed must be a bool")
        try:
            failure_class = json.loads(self.failure_class_json)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError("failure_class_json must contain canonical JSON") from exc
        if not isinstance(failure_class, dict):
            raise ValueError("failure_class_json must contain a JSON object")
        if self.failure_class_json != _canonical_json(failure_class):
            raise ValueError("failure_class_json must use canonical JSON encoding")
        required_failure_fields = {"class", "error_class", "reason"}
        if not required_failure_fields.issubset(failure_class):
            raise ValueError("failure_class requires class, error_class, and reason")
        if not all(
            isinstance(failure_class[name], str) and failure_class[name].strip()
            for name in required_failure_fields
        ):
            raise ValueError("failure_class fields must be non-empty strings")
        for name in ("governance_json", "refutation_json", "closure_certificate_json"):
            encoded = getattr(self, name)
            try:
                value = json.loads(encoded)
            except (TypeError, json.JSONDecodeError) as exc:
                raise ValueError(f"{name} must contain canonical JSON") from exc
            if encoded != _canonical_json(value):
                raise ValueError(f"{name} must use canonical JSON encoding")
        self._validate_admitted_target()

    def _validate_admitted_target(self) -> None:
        admission = self.formalization_admission
        from ztare.leanmill.lean_source import theorem_names

        names = theorem_names(admission.source_text)
        if not names or names[-1] != admission.target_name:
            raise ValueError("admission target is not the final Lean theorem or lemma")
        signature = _normalized_target_signature(admission.source_text, admission.target_name)
        if not signature or signature != admission.target_signature:
            raise ValueError("admission target signature is not canonically bound to source")

    @property
    def failure_class(self) -> dict[str, Any]:
        return json.loads(self.failure_class_json)

    @property
    def target_equivalence_digest(self) -> str:
        return _target_equivalence_digest(self.formalization_admission.source_text)

    @property
    def governance(self) -> Any:
        return json.loads(self.governance_json)

    @property
    def governance_ref(self) -> str:
        return _presence_digest(self.governance)

    @property
    def refutation(self) -> Any:
        return json.loads(self.refutation_json)

    @property
    def refutation_ref(self) -> str:
        return _presence_digest(self.refutation)

    @property
    def closure_certificate(self) -> Any:
        return json.loads(self.closure_certificate_json)

    @property
    def closure_certificate_ref(self) -> str:
        return _presence_digest(self.closure_certificate)

    def _content(self) -> dict[str, Any]:
        admission = self.formalization_admission
        return {
            "schema": self.schema,
            "family": self.family.to_json(),
            "family_digest": self.family.family_digest,
            "formalization_admission": admission.to_json(),
            "admission_digest": admission.admission_digest,
            "task_digest": admission.task_digest,
            "source_digest": admission.source_digest,
            "target_name": admission.target_name,
            "target_signature_digest": admission.target_signature_digest,
            "target_equivalence_digest": self.target_equivalence_digest,
            "outcome": self.outcome,
            "faithful": self.faithful,
            "failure_class": self.failure_class,
            "budget_killed": self.budget_killed,
            "governance": self.governance,
            "governance_ref": self.governance_ref,
            "refutation": self.refutation,
            "refutation_ref": self.refutation_ref,
            "closure_certificate": self.closure_certificate,
            "closure_certificate_ref": self.closure_certificate_ref,
        }

    @property
    def receipt_digest(self) -> str:
        return _digest(self._content())

    def to_json(self) -> dict[str, Any]:
        return {**self._content(), "receipt_digest": self.receipt_digest}

    @classmethod
    def from_attack_record(
        cls,
        *,
        family: RegisteredGapFamily,
        admission: FormalizationAdmission,
        attack_record: Any,
        governance: Any,
        refutation: Any,
        closure_certificate: Any,
    ) -> "ProofGapReceipt":
        """Bind an ``AttackRecord`` to the exact admitted source and intent."""

        from ztare.leanmill.contracts.kernel import AttackRecord

        if not isinstance(attack_record, AttackRecord):
            raise ValueError("attack_record must be an AttackRecord")
        if attack_record.nl != admission.intent_text:
            raise ValueError("attack intent differs from the admitted intent")
        if attack_record.lean_statement != admission.source_text:
            raise ValueError("attack source differs from the admitted source")
        raw_failure = attack_record.failure_class
        if isinstance(raw_failure, Mapping):
            failure_class = dict(raw_failure)
        else:
            failure_class = {"legacy_failure_class": str(raw_failure or "")}
        return cls(
            family=family,
            formalization_admission=admission,
            outcome=attack_record.outcome,
            faithful=attack_record.faithful,
            failure_class_json=_canonical_json(failure_class),
            budget_killed=attack_record.budget_killed,
            governance_json=_canonical_json(governance),
            refutation_json=_canonical_json(refutation),
            closure_certificate_json=_canonical_json(closure_certificate),
        )

    @classmethod
    def from_firewall_result(
        cls,
        *,
        family: RegisteredGapFamily,
        admission: FormalizationAdmission,
        result: Mapping[str, Any],
    ) -> "ProofGapReceipt":
        """Build from the full firewall result without dropping negative evidence."""

        if not isinstance(result, Mapping):
            raise ValueError("firewall result must be a mapping")
        from ztare.leanmill.contracts.kernel import AttackRecord

        attack = AttackRecord.from_firewall_result(dict(result), nl=admission.intent_text)
        return cls.from_attack_record(
            family=family,
            admission=admission,
            attack_record=attack,
            governance=result.get("governance"),
            refutation=result.get("refutation") or result.get("prior_refutation"),
            closure_certificate=result.get("closure_certificate"),
        )

    @classmethod
    def from_json(cls, value: Mapping[str, Any]) -> "ProofGapReceipt":
        if not isinstance(value, Mapping):
            raise ValueError("proof-gap receipt must be a JSON object")
        required = {
            "schema",
            "family",
            "family_digest",
            "formalization_admission",
            "admission_digest",
            "task_digest",
            "source_digest",
            "target_name",
            "target_signature_digest",
            "target_equivalence_digest",
            "outcome",
            "faithful",
            "failure_class",
            "budget_killed",
            "governance",
            "governance_ref",
            "refutation",
            "refutation_ref",
            "closure_certificate",
            "closure_certificate_ref",
            "receipt_digest",
        }
        _require_exact_keys(value, required, context="proof-gap receipt")
        if not isinstance(value.get("family"), Mapping):
            raise ValueError("family must be a JSON object")
        if not isinstance(value.get("formalization_admission"), Mapping):
            raise ValueError("formalization_admission must be a JSON object")
        if not isinstance(value.get("failure_class"), Mapping):
            raise ValueError("failure_class must be a JSON object")
        if type(value.get("budget_killed")) is not bool:
            raise ValueError("budget_killed must be a bool")
        if value.get("faithful") not in (True, False, None):
            raise ValueError("faithful must be true, false, or null")
        string_fields = required - {
            "family",
            "formalization_admission",
            "failure_class",
            "faithful",
            "budget_killed",
            "governance",
            "refutation",
            "closure_certificate",
        }
        if not all(isinstance(value.get(name), str) for name in string_fields):
            raise ValueError("proof-gap scalar fields must be strings")
        family = RegisteredGapFamily.from_json(value["family"])
        admission = FormalizationAdmission.from_json(value["formalization_admission"])
        result = cls(
            family=family,
            formalization_admission=admission,
            outcome=value["outcome"],
            faithful=value["faithful"],
            failure_class_json=_canonical_json(dict(value["failure_class"])),
            budget_killed=value["budget_killed"],
            governance_json=_canonical_json(value["governance"]),
            refutation_json=_canonical_json(value["refutation"]),
            closure_certificate_json=_canonical_json(value["closure_certificate"]),
            schema=value["schema"],
        )
        expected = result.to_json()
        mismatches = [name for name in required if value.get(name) != expected.get(name)]
        if mismatches:
            raise ValueError(f"proof-gap receipt content mismatch: {sorted(mismatches)}")
        return result


def observe_admitted_proof_gap(
    admission: FormalizationAdmission,
    family: RegisteredGapFamily,
    *,
    solve_fn: Any = None,
    substrate: Any = None,
    provider: str | None = None,
    timeout_s: int = 500,
    mode: str = "dag_search",
    notes: str | None = None,
) -> ProofGapReceipt:
    """Run the canonical solver on one already-frozen admission.

    This is the only solve integration for the repeated-gap carrier.  It does
    not autoformalize, reconstruct, or retrofit an admission: the exact
    ``admission.solve_input()`` positional payload is passed to ``solve_fn``.
    The default is ``solver_core.solve_adhoc``; injection exists for hermetic
    tests and alternate governed executors with the same call contract.
    """

    if not isinstance(admission, FormalizationAdmission) or not admission.admitted:
        raise ValueError("observe_admitted_proof_gap requires an admitted formalization")
    if not isinstance(family, RegisteredGapFamily):
        raise ValueError("family must be a RegisteredGapFamily")
    if type(timeout_s) is not int or timeout_s <= 0:
        raise ValueError("timeout_s must be a positive integer")
    if mode not in {"cascade", "dag_search"}:
        raise ValueError("mode must be cascade or dag_search")
    if solve_fn is None:
        from ztare.leanmill.solver.solver_core import solve_adhoc

        solve_fn = solve_adhoc
    if not callable(solve_fn):
        raise ValueError("solve_fn must be callable")

    solve_input = admission.solve_input()
    result = solve_fn(
        *solve_input.positional_args(),
        provider=provider,
        timeout_s=timeout_s,
        mode=mode,
        substrate=substrate,
        notes=notes,
    )
    if not isinstance(result, Mapping):
        raise ValueError("solve_fn must return a mapping")
    from ztare.leanmill.contracts.kernel import primary_result

    primary = primary_result(dict(result))
    outcome = str(primary.get("outcome") or "")
    if not outcome:
        raise ValueError("solve_fn returned no primary outcome")
    # Reuse the existing kernel-gated refutation extractor; do not create a
    # sibling interpretation of falsified/statement_false solver fields.
    from ztare.leanmill.solver.autoformalize import _solve_refutation

    refutation = _solve_refutation(dict(result))
    firewall_result = {
        "lean_statement": admission.source_text,
        "faithful": True,
        "outcome": f"admitted_and_{outcome}",
        "solved": outcome,
        "failure_class": primary.get("failure_class"),
        "budget_killed": primary.get("budget_killed", False),
        "governance": result.get("governance"),
        "closure_certificate": result.get("closure_certificate"),
        "refutation": refutation,
    }
    return ProofGapReceipt.from_firewall_result(
        family=family,
        admission=admission,
        result=firewall_result,
    )


def _forbidden_failure_signal(failure_class: Mapping[str, Any]) -> bool:
    text = " ".join(str(value).lower() for value in failure_class.values())
    return any(marker in text for marker in _FORBIDDEN_FAILURE_MARKERS)


def evaluate_axiom_pack_escalation(
    receipts: Iterable[ProofGapReceipt | Mapping[str, Any]],
) -> dict[str, Any]:
    """Evaluate repeated-gap evidence for quarantined candidate routing.

    Eligibility requires at least two distinct, admitted target signatures and
    admissions under one explicit family/base/substrate registration.  The
    receipt deliberately leaves the unseen-task and typed-proposal gates
    unsatisfied; those are separate authorities in the existing AxiomPack lane.
    """

    parsed: list[ProofGapReceipt] = []
    violations: list[dict[str, Any]] = []
    for index, value in enumerate(receipts):
        try:
            receipt = value if isinstance(value, ProofGapReceipt) else ProofGapReceipt.from_json(value)
        except (TypeError, ValueError) as exc:
            violations.append(
                {"type": "malformed_receipt", "index": index, "detail": str(exc)[:240]}
            )
            continue
        parsed.append(receipt)
        failure_class = receipt.failure_class
        if receipt.outcome != EXACT_GAP_OUTCOME:
            violations.append({"type": "not_exact_gap", "index": index})
        if receipt.faithful is not True:
            violations.append({"type": "not_faithful", "index": index})
        if failure_class.get("class") != "math":
            violations.append(
                {
                    "type": "not_mathematical_failure",
                    "index": index,
                    "failure_class": failure_class.get("class"),
                }
            )
        if _forbidden_failure_signal(failure_class):
            violations.append({"type": "forbidden_failure_signal", "index": index})
        if receipt.budget_killed:
            violations.append({"type": "budget_killed", "index": index})
        if receipt.refutation_ref:
            violations.append({"type": "refutation_present", "index": index})
        if receipt.closure_certificate_ref:
            violations.append({"type": "closure_present", "index": index})

    receipt_digests = {receipt.receipt_digest for receipt in parsed}
    target_digests = {receipt.target_equivalence_digest for receipt in parsed}
    admission_digests = {
        receipt.formalization_admission.admission_digest for receipt in parsed
    }
    task_digests = {receipt.formalization_admission.task_digest for receipt in parsed}
    family_digests = {receipt.family.family_digest for receipt in parsed}
    base_theory_digests = {receipt.family.base_theory_digest for receipt in parsed}
    substrate_digests = {receipt.family.substrate_digest for receipt in parsed}

    if len(parsed) < 2:
        violations.append({"type": "insufficient_receipts", "required": 2, "observed": len(parsed)})
    if len(receipt_digests) != len(parsed):
        violations.append({"type": "duplicate_receipt"})
    if len(target_digests) < 2:
        violations.append(
            {"type": "insufficient_distinct_targets", "required": 2, "observed": len(target_digests)}
        )
    if len(admission_digests) < 2:
        violations.append(
            {"type": "insufficient_distinct_admissions", "required": 2, "observed": len(admission_digests)}
        )
    if len(task_digests) < 2:
        violations.append(
            {"type": "insufficient_distinct_tasks", "required": 2, "observed": len(task_digests)}
        )
    for kind, values in (
        ("registered_family", family_digests),
        ("base_theory", base_theory_digests),
        ("substrate", substrate_digests),
    ):
        if len(values) != 1:
            violations.append({"type": f"mixed_{kind}", "observed": len(values)})

    eligible = not violations
    core = {
        "schema": AXIOM_PACK_ESCALATION_SCHEMA,
        "status": "eligible_for_candidate_routing" if eligible else "blocked",
        "eligible": eligible,
        "routing_only": True,
        "promotion_status": "quarantined",
        "proof_credit_eligible": False,
        "theorem_campaign_admissible": False,
        "theory_mutation_allowed": False,
        "registered_family_digest": next(iter(family_digests)) if len(family_digests) == 1 else "",
        "base_theory_digest": next(iter(base_theory_digests)) if len(base_theory_digests) == 1 else "",
        "substrate_digest": next(iter(substrate_digests)) if len(substrate_digests) == 1 else "",
        "evidence_receipt_digests": sorted(receipt_digests),
        "distinct_target_count": len(target_digests),
        "distinct_admission_count": len(admission_digests),
        "distinct_task_count": len(task_digests),
        "required_next_gates": [
            {
                "requirement": "signed_unseen_task_manifest",
                "schema": "leanmill.axiom_shadow_task_manifest.v1",
                "satisfied": False,
            },
            {
                "requirement": "typed_axiom_proposals",
                "schema": "leanmill.typed_axiom_proposal.v1",
                "satisfied": False,
            },
        ],
        "violations": violations,
    }
    return {**core, "routing_receipt_digest": _digest(core)}


__all__ = [
    "AXIOM_PACK_ESCALATION_SCHEMA",
    "EXACT_GAP_OUTCOME",
    "PROOF_GAP_RECEIPT_BUNDLE_SCHEMA",
    "PROOF_GAP_RECEIPT_SCHEMA",
    "REGISTERED_GAP_FAMILY_SCHEMA",
    "ProofGapReceipt",
    "RegisteredGapFamily",
    "evaluate_axiom_pack_escalation",
    "observe_admitted_proof_gap",
]
