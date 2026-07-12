from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


SCHEMA = "ztare-cegis-membrane-assessment-v1"
DISCOVERY = "DISCOVERY"
EVALUATION = "EVALUATION"
HARNESS_DEBUG = "HARNESS_DEBUG"
CANDIDATE_AUTHOR = "CANDIDATE_AUTHOR"
OBSERVED = "observed"
USED_FOR_ABDUCTION = "used_for_abduction"
CONSUMED_COUNTEREXAMPLE = "consumed_counterexample"
FRESH_VERIFIER = "fresh_verifier"

EVIDENCE_STATUSES = frozenset(
    {
        OBSERVED,
        USED_FOR_ABDUCTION,
        CONSUMED_COUNTEREXAMPLE,
        FRESH_VERIFIER,
    }
)


@dataclass(frozen=True)
class CegisMembraneAssessment:
    """Role-relative claim accounting for counterexample-guided search.

    Withheld evidence is not sacred. If a candidate author inspects it, that
    slice becomes counterexample evidence and the next transport claim needs a
    fresh withheld slice. Debuggers/readers may inspect it, but their output
    cannot be used as a clean candidate-promotion claim.
    """

    run_role: str
    holdout_exposed_to_proposer: bool
    claim_class: str
    fresh_holdout_required: bool
    withheld_refs: tuple[str, ...] = ()
    exposed_withheld_refs: tuple[str, ...] = ()
    evidence_statuses: tuple[dict[str, str], ...] = ()
    supportable_claims: tuple[str, ...] = ()
    forbidden_claims: tuple[str, ...] = ()
    membrane_status: str = "unspecified"
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        payload = {"schema": SCHEMA, **asdict(self)}
        # Compatibility for older readers that already consumed the first draft.
        payload["role"] = self.run_role.lower()
        payload["requires_fresh_membrane"] = self.fresh_holdout_required
        return payload


def assess_cegis_membrane(
    *,
    role: str,
    withheld_refs: tuple[str, ...] = (),
    exposed_refs: tuple[str, ...] = (),
    candidate_gate_passed: bool = False,
    terminal_event: bool = False,
) -> CegisMembraneAssessment:
    """Return the strongest claim supported by the role/evidence boundary.

    Roles are intentionally simple strings so callers from ARC, Lean, or future
    substrates do not need a shared enum migration. Recognized values:
    `candidate_author`, `discovery_debugger`, `evaluator`, `reader`.
    """

    exposed = tuple(sorted(set(withheld_refs) & set(exposed_refs)))
    statuses = _evidence_statuses(
        withheld_refs=withheld_refs,
        exposed_withheld_refs=exposed,
        candidate_gate_passed=candidate_gate_passed,
    )
    normalized = _normalize_role(role)
    claims: list[str] = []
    forbidden: list[str] = []
    notes: list[str] = []

    if terminal_event:
        claims.append("level_terminal_event")
        notes.append("terminal authority is separate from transition-law promotion")

    if normalized == DISCOVERY:
        status = "holdout_inspection_allowed"
        claims.append("diagnosis_or_counterexample_evidence")
        claim_class = "law_discovery"
        if exposed:
            claims.append("holdout_informed_discovery")
            forbidden.append("clean_transfer")
            notes.append("inspected withheld refs must be promoted to evidence before reuse")
        return CegisMembraneAssessment(
            run_role=normalized,
            holdout_exposed_to_proposer=bool(exposed),
            claim_class=claim_class,
            fresh_holdout_required=bool(exposed),
            withheld_refs=withheld_refs,
            exposed_withheld_refs=exposed,
            evidence_statuses=statuses,
            supportable_claims=tuple(dict.fromkeys(claims)),
            forbidden_claims=tuple(dict.fromkeys(forbidden)),
            membrane_status=status,
            notes=tuple(notes),
        )

    if normalized == HARNESS_DEBUG:
        status = "debug_membrane_consumed" if exposed else "debug_membrane"
        claims.append("apparatus_diagnosis")
        return CegisMembraneAssessment(
            run_role=normalized,
            holdout_exposed_to_proposer=bool(exposed),
            claim_class="harness_debug",
            fresh_holdout_required=bool(exposed),
            withheld_refs=withheld_refs,
            exposed_withheld_refs=exposed,
            evidence_statuses=statuses,
            supportable_claims=tuple(dict.fromkeys(claims)),
            forbidden_claims=("clean_transfer", "object_level_skill"),
            membrane_status=status,
            notes=tuple(notes),
        )

    if normalized == EVALUATION:
        status = "evaluation_membrane_consumed" if exposed else "evaluation_membrane"
        claim_class = (
            "clean_transfer"
            if candidate_gate_passed and not exposed
            else "level_solve"
            if terminal_event
            else "candidate_evaluation"
        )
        if candidate_gate_passed:
            claims.append("candidate_transport_measured")
        if exposed:
            forbidden.append("clean_transfer")
            notes.append("withheld slice was exposed; the same slice cannot certify clean transfer")
        return CegisMembraneAssessment(
            run_role=normalized,
            holdout_exposed_to_proposer=bool(exposed),
            claim_class=claim_class,
            fresh_holdout_required=bool(exposed),
            withheld_refs=withheld_refs,
            exposed_withheld_refs=exposed,
            evidence_statuses=statuses,
            supportable_claims=tuple(dict.fromkeys(claims)),
            forbidden_claims=tuple(dict.fromkeys(forbidden)),
            membrane_status=status,
            notes=tuple(notes),
        )

    if exposed:
        status = "candidate_author_membrane_consumed"
        claims.append("counterexample_guided_law_acquisition")
        claim_class = "law_discovery"
        forbidden.append("clean_transfer")
        notes.append("same withheld slice cannot certify the repaired candidate")
    else:
        status = "candidate_author_membrane_clean"
        claim_class = "clean_transfer" if candidate_gate_passed else "candidate_attempt"
        if candidate_gate_passed:
            claims.append("candidate_transport_measured")
        else:
            claims.append("candidate_attempt")

    return CegisMembraneAssessment(
        run_role=normalized,
        holdout_exposed_to_proposer=bool(exposed),
        claim_class=claim_class,
        fresh_holdout_required=bool(exposed),
        withheld_refs=withheld_refs,
        exposed_withheld_refs=exposed,
        evidence_statuses=statuses,
        supportable_claims=tuple(dict.fromkeys(claims)),
        forbidden_claims=tuple(dict.fromkeys(forbidden)),
        membrane_status=status,
        notes=tuple(notes),
    )


def evidence_promotion_receipt(
    *,
    from_ref: str,
    reason: str = "inspected_by_proposer",
) -> dict[str, Any]:
    return {
        "schema": "ztare-evidence-promotion-v1",
        "from": "holdout",
        "from_ref": from_ref,
        "to": "counterexample_evidence",
        "evidence_status": CONSUMED_COUNTEREXAMPLE,
        "reason": reason,
        "requires_fresh_holdout": True,
    }


def normalize_evidence_statuses(raw: object) -> tuple[dict[str, str], ...]:
    if not isinstance(raw, list):
        return ()
    out: list[dict[str, str]] = []
    for row in raw:
        if isinstance(row, str):
            status = row.strip()
            if status in EVIDENCE_STATUSES:
                out.append({"ref": "*", "status": status})
            continue
        if not isinstance(row, dict):
            continue
        ref = str(row.get("ref") or row.get("source_ref") or "").strip()
        status = str(row.get("status") or row.get("evidence_status") or "").strip()
        if ref and status in EVIDENCE_STATUSES:
            out.append({"ref": ref, "status": status})
    return tuple(out)


def _evidence_statuses(
    *,
    withheld_refs: tuple[str, ...],
    exposed_withheld_refs: tuple[str, ...],
    candidate_gate_passed: bool,
) -> tuple[dict[str, str], ...]:
    exposed = set(exposed_withheld_refs)
    rows: list[dict[str, str]] = []
    for ref in withheld_refs:
        status = CONSUMED_COUNTEREXAMPLE if ref in exposed else FRESH_VERIFIER
        if candidate_gate_passed and ref not in exposed:
            status = FRESH_VERIFIER
        rows.append({"ref": ref, "status": status})
    return tuple(rows)


def select_persona(rubric_data: dict, run_role: str) -> str:
    """Return the epistemic persona string for *run_role*.

    Precedence (highest first):
    1. ``rubric_data["personas"][<role>]`` — role-specific text wins.
    2. ``rubric_data["personas"]["discovery"]`` as fallback when the requested
       role key is absent (logged once; covers HARNESS_DEBUG → discovery branch).
    3. ``rubric_data["persona"]`` — legacy scalar, exact backward-compat.
    4. Empty string.

    When both ``personas`` and ``persona`` are present, ``personas`` wins.
    HARNESS_DEBUG is treated as DISCOVERY for persona selection.
    """
    personas = rubric_data.get("personas")
    if personas and isinstance(personas, dict):
        # normalise role key: HARNESS_DEBUG → discovery
        role_key = "discovery" if run_role.upper() in {DISCOVERY, HARNESS_DEBUG} else "evaluation"
        text = personas.get(role_key)
        if text:
            print(f"[persona] selected {role_key!r} stance for run_role={run_role}")
            return str(text)
        # missing key — fall back to the other key (with logged note)
        fallback_key = "evaluation" if role_key == "discovery" else "discovery"
        fallback = personas.get(fallback_key)
        if fallback:
            print(
                f"[persona] {role_key!r} key absent in 'personas'; "
                f"falling back to {fallback_key!r} for run_role={run_role}"
            )
            return str(fallback)
        # personas dict exists but both keys absent — fall through to legacy
    # legacy scalar fallback
    return str(rubric_data.get("persona") or "")


def _normalize_role(role: str) -> str:
    text = str(role or "").strip().lower()
    if text in {"discovery", "discovery_debugger", "reader", "science"}:
        return DISCOVERY
    if text in {"harness_debug", "debug", "debugger", "conductor_researcher"}:
        return HARNESS_DEBUG
    if text in {"candidate_author", "author", "proposer"}:
        return CANDIDATE_AUTHOR
    return EVALUATION
