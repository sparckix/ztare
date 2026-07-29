"""Target-conditioned conjecture curricula over governed result cards."""
from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any, Callable, Mapping, Sequence

from jsonschema import Draft202012Validator

from ztare.leanmill.result_cards import (
    resolve_objective_source_text,
    validate_result_card_deck,
)
from ztare.leanmill.theory_ir import content_hash


LEGACY_TARGET_CONJECTURE_WAVE_SCHEMA = "leanmill.target_conjecture_wave.v1"
TARGET_CONJECTURE_WAVE_SCHEMA = "leanmill.target_conjecture_wave.v2"
TARGET_CONJECTURE_ADMISSION_SCHEMA = "leanmill.target_conjecture_admission.v1"
LEGACY_TARGET_STATEMENT_ELABORATION_SCHEMA = (
    "leanmill.target_statement_elaboration_receipt.v1"
)
TARGET_STATEMENT_ELABORATION_SCHEMA = (
    "leanmill.target_statement_elaboration_receipt.v2"
)
TARGET_STATEMENT_CHECKER_OWNER = (
    "ztare.leanmill.solver.autoformalize:default_compile"
)
TARGET_STATEMENT_DIAGNOSTIC_OWNER = (
    "ztare.leanmill.solver.autoformalize:default_compile_diagnose"
)
TARGET_FORMAL_CONTEXT_OWNER = (
    "conjecturer_declared_host_validated_no_import_namespace_guessing"
)
_LEAN_IMPORT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$")
_CANDIDATE_FAMILIES = (
    "hypothesis_minimization",
    "basepoint_characterization",
    "action_kernel_quotient",
    "unary_extraction",
    "forcing_identity",
    "converse_construction",
    "verified_transport",
    "other_target_edge",
)
_EXPECTED_DIRECTIONS = (
    "necessary",
    "sufficient",
    "equivalence",
    "obstruction",
    "converse",
)


def target_conjecture_output_schema(dependency_ids: Sequence[str]) -> dict[str, Any]:
    dependencies = tuple(dict.fromkeys(str(row) for row in dependency_ids if str(row)))
    if not dependencies:
        raise ValueError("target-conditioned conjecturing requires result-card dependencies")
    candidate = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "title",
            "formal_status",
            "candidate_family",
            "mathematical_statement",
            "lean_signature",
            "required_imports",
            "formal_context",
            "dependencies",
            "target_edge",
            "expected_direction",
            "falsification_plan",
            "recurrence_risk",
            "scope_limits",
            "capability_request",
        ],
        "properties": {
            "title": {"type": "string", "minLength": 1},
            "formal_status": {"enum": ["lean_candidate", "language_gap"]},
            "candidate_family": {"enum": list(_CANDIDATE_FAMILIES)},
            "mathematical_statement": {"type": "string", "minLength": 1},
            "lean_signature": {"type": "string"},
            "required_imports": {
                "type": "array",
                "items": {"type": "string", "minLength": 1},
            },
            "formal_context": {
                "type": "object",
                "additionalProperties": False,
                "required": ["open_namespaces", "enclosing_namespace"],
                "properties": {
                    "open_namespaces": {
                        "type": "array",
                        "items": {"type": "string", "minLength": 1},
                    },
                    "enclosing_namespace": {"type": "string"},
                },
            },
            "dependencies": {
                "type": "array",
                "minItems": 1,
                "items": {"enum": list(dependencies)},
            },
            "target_edge": {"type": "string", "minLength": 1},
            "expected_direction": {"enum": list(_EXPECTED_DIRECTIONS)},
            "falsification_plan": {"type": "string", "minLength": 1},
            "recurrence_risk": {"type": "string", "minLength": 1},
            "scope_limits": {"type": "string", "minLength": 1},
            "capability_request": {"type": "string"},
        },
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": ["candidates", "no_candidate_reason"],
        "properties": {
            "candidates": {
                "type": "array",
                "minItems": 0,
                "maxItems": 2,
                "items": candidate,
            },
            "no_candidate_reason": {"type": "string"},
        },
    }


def render_target_conjecture_prompt(
    deck: Mapping[str, Any],
    card: Mapping[str, Any],
    *,
    seed_proof: str,
    source_excerpt_limit: int = 36_000,
) -> str:
    """Reveal one seed proof only inside the durable Conjecturer call."""

    validate_result_card_deck(deck)
    if card not in deck["cards"] or not seed_proof.strip():
        raise ValueError("target-conditioned prompt lacks a deck card or seed proof")
    source_parts: list[str] = []
    remaining = source_excerpt_limit
    for receipt in deck.get("objective_source_receipts") or ():
        if remaining <= 0:
            continue
        path = Path(str(receipt.get("ref") or ""))
        text = resolve_objective_source_text(receipt)
        excerpt = text[:remaining]
        source_parts.append(f"SOURCE {path}:\n{excerpt}")
        remaining -= len(excerpt)
    visible_cards = [
        {
            "card_id": row["card_id"],
            "target_identity": row["target_identity"],
            "lean_statement": row["lean_statement"],
            "statement_sha256": row["statement_sha256"],
        }
        for row in deck["cards"]
    ]
    payload = {
        "deck_sha256": deck["deck_sha256"],
        "objective": deck["objective"],
        "objective_sha256": deck["objective_sha256"],
        "seed_card": {
            "card_id": card["card_id"],
            "target_identity": card["target_identity"],
            "lean_statement": card["lean_statement"],
            "statement_sha256": card["statement_sha256"],
            "seed_proof": seed_proof.strip(),
            "proof_sha256": card["proof_sha256"],
        },
        "visible_card_deck": visible_cards,
        "source_excerpts": "\n\n".join(source_parts),
    }
    return (
        "You are the Conjecturer in a target-conditioned formal-mathematics self-play wave. "
        "Use the frozen objective, the source-bound result cards, and this seed's kernel-checked proof to "
        "propose zero, one, or two precise extensions that could change the objective's characterization "
        "lattice. A replay, restatement, proof shortening, typeclass-only transfer, coordinate renaming, or "
        "known differential-mode consequence has no target credit. Prefer a necessary/sufficient condition, "
        "a converse, a minimal forcing identity, or a discriminating obstruction.\n\n"
        "For `lean_candidate`, return a Lean theorem signature only: binder telescope plus conclusion, with no "
        "theorem name, `:=`, proof, `sorry`, `admit`, or new axiom. List imports and exact card dependencies. "
        "Declare `formal_context` explicitly: list every namespace that must be opened and, only when needed, "
        "the enclosing namespace. An import path is not assumed to be a namespace, so do not rely on implicit "
        "module-to-namespace guessing. "
        "For `language_gap`, leave `lean_signature` empty and name the smallest missing executable capability "
        "in `capability_request`; do not disguise an uncertain proof as a language gap. State how finite-model "
        "or kernel attack could falsify each candidate and its recurrence risk. If no candidate clears this "
        "bar, return an empty list and explain why. Return only the requested JSON object.\n\n"
        "FROZEN TARGET-CURRICULUM PAYLOAD:\n"
        + json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    )


def _normalize_lean_signature(signature: str) -> str:
    from ztare.leanmill.solver.proof_cache import normalize_statement_equiv

    return normalize_statement_equiv(signature)


def _validated_formal_context(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != {
        "open_namespaces", "enclosing_namespace"
    }:
        raise ValueError("candidate formal context is malformed")
    raw_opens = value.get("open_namespaces")
    if not isinstance(raw_opens, list):
        raise ValueError("candidate open namespaces must be a list")
    opens = [str(item).strip() for item in raw_opens]
    enclosing = str(value.get("enclosing_namespace") or "").strip()
    if (
        len(set(opens)) != len(opens)
        or any(not _LEAN_IMPORT.fullmatch(item) for item in opens)
        or enclosing and not _LEAN_IMPORT.fullmatch(enclosing)
    ):
        raise ValueError("candidate formal context names are invalid")
    return {
        "open_namespaces": opens,
        "enclosing_namespace": enclosing,
    }


def render_target_candidate_source(
    candidate: Mapping[str, Any],
    *,
    target_name: str,
    require_formal_context: bool,
) -> tuple[str, str]:
    """Render candidate-authored imports/context/signature with a host-owned name."""

    imports_raw = candidate.get("required_imports")
    imports = (
        [str(value).strip() for value in imports_raw]
        if isinstance(imports_raw, list)
        else []
    )
    if not imports or any(not _LEAN_IMPORT.fullmatch(value) for value in imports):
        raise ValueError("candidate declared imports are invalid")
    signature = str(candidate.get("lean_signature") or "").strip()
    if not signature:
        raise ValueError("candidate Lean signature is empty")
    if require_formal_context:
        formal_context = _validated_formal_context(candidate.get("formal_context"))
    else:
        raw_context = candidate.get("formal_context")
        formal_context = (
            _validated_formal_context(raw_context)
            if raw_context is not None
            else {"open_namespaces": [], "enclosing_namespace": ""}
        )
    lines = [*(f"import {value}" for value in imports), ""]
    if formal_context["open_namespaces"]:
        lines.extend(
            [
                *(f"open {value}" for value in formal_context["open_namespaces"]),
                "",
            ]
        )
    enclosing = formal_context["enclosing_namespace"]
    if enclosing:
        lines.extend([f"namespace {enclosing}", ""])
    lines.extend(
        [
            f"theorem {target_name} {signature} := by",
            "  sorry",
        ]
    )
    if enclosing:
        lines.extend(["", f"end {enclosing}"])
    source = "\n".join(lines) + "\n"
    selector = f"{enclosing}.{target_name}" if enclosing else target_name
    return source, selector


def normalize_conjecturer_output(
    deck: Mapping[str, Any],
    card: Mapping[str, Any],
    output: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Validate one role response and assign host-owned candidate identities."""

    validate_result_card_deck(deck)
    dependency_ids = [row["target_identity"] for row in deck["cards"]]
    Draft202012Validator(target_conjecture_output_schema(dependency_ids)).validate(output)
    card_statements = {
        _normalize_lean_signature(str(row["lean_statement"]))
        for row in deck["cards"]
    }
    candidates: list[dict[str, Any]] = []
    for raw in output.get("candidates") or ():
        row = dict(raw)
        row["formal_context"] = _validated_formal_context(
            row.get("formal_context")
        )
        lean_signature = str(row.get("lean_signature") or "").strip()
        capability = str(row.get("capability_request") or "").strip()
        if row["formal_status"] == "lean_candidate":
            if (
                not lean_signature
                or capability
                or ":=" in lean_signature
                or re.search(
                    r"(?<![A-Za-z0-9_])(theorem|lemma|by|sorry|admit|axiom)(?![A-Za-z0-9_])",
                    lean_signature,
                )
            ):
                raise ValueError("Lean candidate is not a proof-free theorem signature")
            normalized = _normalize_lean_signature(lean_signature)
            recurrence = (
                "exact_card_statement"
                if normalized in card_statements
                else "not_exact_card_statement"
            )
        else:
            if lean_signature or not capability:
                raise ValueError("language gap must omit a Lean signature and name a capability")
            normalized = ""
            recurrence = "not_formalized"
        identity_core = {
            "deck_sha256": deck["deck_sha256"],
            "source_card_id": card["card_id"],
            "candidate_family": row["candidate_family"],
            "mathematical_statement": row["mathematical_statement"],
            "normalized_lean_signature": normalized,
            "formal_context": row["formal_context"],
            "target_edge": row["target_edge"],
        }
        core = {
            **row,
            "source_card_id": card["card_id"],
            "source_target_identity": card["target_identity"],
            "normalized_lean_signature": normalized,
            "recurrence_status": recurrence,
            "candidate_id": "target-conjecture:" + content_hash(identity_core),
        }
        candidates.append({**core, "candidate_sha256": content_hash(core)})
    return candidates


def build_target_conjecture_wave(
    deck: Mapping[str, Any],
    per_card_candidates: Sequence[Sequence[Mapping[str, Any]]],
    *,
    call_receipts: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Deduplicate candidates while preserving every seed that proposed them."""

    validate_result_card_deck(deck)
    if len(per_card_candidates) != len(deck["cards"]):
        raise ValueError("target-conjecture outputs do not cover the frozen card deck")
    by_key: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for rows in per_card_candidates:
        for raw in rows:
            row = dict(raw)
            key = str(row.get("normalized_lean_signature") or "").strip()
            if not key:
                key = content_hash({
                    "mathematical_statement": row.get("mathematical_statement"),
                    "capability_request": row.get("capability_request"),
                })
            if key in by_key:
                prior = by_key[key]
                prior["also_proposed_from"] = sorted(set(
                    prior.get("also_proposed_from") or ()
                ) | {str(row.get("source_card_id") or "")})
                continue
            by_key[key] = {**row, "also_proposed_from": []}
            order.append(key)
    candidates = [by_key[key] for key in order]
    core: dict[str, Any] = {
        "schema": TARGET_CONJECTURE_WAVE_SCHEMA,
        "deck_sha256": deck["deck_sha256"],
        "objective_sha256": deck["objective_sha256"],
        "card_count": len(deck["cards"]),
        "candidate_count": len(candidates),
        "candidates": candidates,
        "call_receipts": [dict(row) for row in call_receipts],
        "revision_epoch": 0,
        "predecessor_wave_sha256": "",
        "revision_feedback_sha256": "",
        "abandoned_predecessor_candidate_ids": [],
        "formal_context_owner": TARGET_FORMAL_CONTEXT_OWNER,
        "authority": "agent_proposals_pending_independent_guide_and_verification",
    }
    return {**core, "wave_sha256": content_hash(core)}


def preflight_target_conjecture_wave(
    wave: Mapping[str, Any],
    *,
    lean_root: str | Path,
    compile_fn: Callable[[str, str | Path], bool] | None = None,
) -> dict[str, Any]:
    """Elaborate every proof-free Lean statement before Guide dispatch."""

    wave_schema = str(wave.get("schema") or "")
    if wave_schema not in {
        LEGACY_TARGET_CONJECTURE_WAVE_SCHEMA,
        TARGET_CONJECTURE_WAVE_SCHEMA,
    }:
        raise ValueError("statement preflight input is not a target-conjecture wave")
    wave_core = {key: value for key, value in wave.items() if key != "wave_sha256"}
    if wave.get("wave_sha256") != content_hash(wave_core):
        raise ValueError("statement preflight wave digest mismatch")
    if (
        wave_schema == TARGET_CONJECTURE_WAVE_SCHEMA
        and wave.get("formal_context_owner") != TARGET_FORMAL_CONTEXT_OWNER
    ):
        raise ValueError("statement preflight lacks the formal-context owner")
    if compile_fn is None:
        from ztare.leanmill.solver.autoformalize import default_compile

        compile_fn = default_compile

    rows: list[dict[str, Any]] = []
    for candidate in wave.get("candidates") or ():
        if not isinstance(candidate, Mapping):
            raise TypeError("target-conjecture candidate must be an object")
        candidate_id = str(candidate.get("candidate_id") or "")
        candidate_sha = str(candidate.get("candidate_sha256") or "")
        formal_status = str(candidate.get("formal_status") or "")
        signature = str(candidate.get("lean_signature") or "").strip()
        raw_imports = candidate.get("required_imports")
        imports = (
            tuple(str(value).strip() for value in raw_imports)
            if isinstance(raw_imports, list)
            else ()
        )
        status = "not_applicable"
        reason_code = "language_gap_has_no_lean_statement"
        guide_eligible = formal_status == "language_gap"
        source = ""
        compile_invoked = False
        if formal_status == "lean_candidate":
            if not imports or any(not _LEAN_IMPORT.fullmatch(value) for value in imports):
                status = "rejected"
                reason_code = "declared_imports_invalid"
                guide_eligible = False
            else:
                try:
                    source, _selector = render_target_candidate_source(
                        candidate,
                        target_name="targetConditionedStatementPreflight",
                        require_formal_context=(
                            wave_schema == TARGET_CONJECTURE_WAVE_SCHEMA
                        ),
                    )
                except ValueError:
                    status = "rejected"
                    reason_code = "declared_formal_context_invalid"
                    guide_eligible = False
                else:
                    compile_invoked = True
                    try:
                        result = compile_fn(source, lean_root)
                    except Exception as exc:  # noqa: BLE001 - typed instrument outcome
                        status = "unavailable"
                        reason_code = f"statement_preflight_unavailable:{type(exc).__name__}"
                        guide_eligible = False
                    else:
                        if type(result) is not bool:
                            status = "unavailable"
                            reason_code = "statement_preflight_returned_non_boolean"
                            guide_eligible = False
                        elif result:
                            status = "elaborated"
                            reason_code = "lean_statement_elaborated"
                            guide_eligible = True
                        else:
                            status = "rejected"
                            reason_code = "lean_statement_did_not_elaborate"
                            guide_eligible = False
        row = {
            "candidate_id": candidate_id,
            "candidate_sha256": candidate_sha,
            "formal_status": formal_status,
            "declared_imports": list(imports),
            "signature_sha256": content_hash(signature),
            "probe_source_sha256": content_hash(source) if source else "",
            "compile_invoked": compile_invoked,
            "status": status,
            "reason_code": reason_code,
            "guide_eligible": guide_eligible,
            "checker_owner": TARGET_STATEMENT_CHECKER_OWNER,
        }
        if wave_schema == TARGET_CONJECTURE_WAVE_SCHEMA:
            row["formal_context"] = (
                dict(candidate.get("formal_context") or {})
                if formal_status == "lean_candidate"
                else {"open_namespaces": [], "enclosing_namespace": ""}
            )
        rows.append({**row, "row_sha256": content_hash(row)})
    eligible = [row["candidate_id"] for row in rows if row["guide_eligible"]]
    rejected = [row["candidate_id"] for row in rows if row["status"] == "rejected"]
    unavailable = [
        row["candidate_id"] for row in rows if row["status"] == "unavailable"
    ]
    core = {
        "schema": (
            TARGET_STATEMENT_ELABORATION_SCHEMA
            if wave_schema == TARGET_CONJECTURE_WAVE_SCHEMA
            else LEGACY_TARGET_STATEMENT_ELABORATION_SCHEMA
        ),
        "wave_sha256": str(wave["wave_sha256"]),
        "candidate_count": len(rows),
        "candidate_receipts": rows,
        "guide_eligible_candidate_ids": eligible,
        "rejected_candidate_ids": rejected,
        "unavailable_candidate_ids": unavailable,
        "checker_owner": TARGET_STATEMENT_CHECKER_OWNER,
        "authority": "statement_elaboration_only_no_theorem_truth_credit",
    }
    if wave_schema == TARGET_CONJECTURE_WAVE_SCHEMA:
        core["formal_context_owner"] = TARGET_FORMAL_CONTEXT_OWNER
    return {**core, "receipt_sha256": content_hash(core)}


def _validated_guide_eligible_ids(
    wave: Mapping[str, Any], receipt: Mapping[str, Any]
) -> set[str]:
    wave_schema = str(wave.get("schema") or "")
    expected_receipt_schema = (
        TARGET_STATEMENT_ELABORATION_SCHEMA
        if wave_schema == TARGET_CONJECTURE_WAVE_SCHEMA
        else LEGACY_TARGET_STATEMENT_ELABORATION_SCHEMA
        if wave_schema == LEGACY_TARGET_CONJECTURE_WAVE_SCHEMA
        else ""
    )
    if receipt.get("schema") != expected_receipt_schema:
        raise ValueError("Guide lacks a target-statement elaboration receipt")
    wave_core = {key: value for key, value in wave.items() if key != "wave_sha256"}
    if wave.get("wave_sha256") != content_hash(wave_core):
        raise ValueError("Guide target-conjecture wave digest mismatch")
    required_receipt_fields = {
        "schema", "wave_sha256", "candidate_count", "candidate_receipts",
        "guide_eligible_candidate_ids", "rejected_candidate_ids",
        "unavailable_candidate_ids", "checker_owner", "authority",
        "receipt_sha256",
    }
    if wave_schema == TARGET_CONJECTURE_WAVE_SCHEMA:
        required_receipt_fields.add("formal_context_owner")
    if set(receipt) != required_receipt_fields:
        raise ValueError("target-statement elaboration receipt fields differ")
    core = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    if receipt.get("receipt_sha256") != content_hash(core):
        raise ValueError("target-statement elaboration receipt digest mismatch")
    if receipt.get("wave_sha256") != wave.get("wave_sha256"):
        raise ValueError("target-statement elaboration receipt belongs to another wave")
    if wave_schema == TARGET_CONJECTURE_WAVE_SCHEMA and (
        wave.get("formal_context_owner") != TARGET_FORMAL_CONTEXT_OWNER
        or receipt.get("formal_context_owner") != TARGET_FORMAL_CONTEXT_OWNER
    ):
        raise ValueError("target formal-context owner changed identity")
    candidates = [
        row for row in wave.get("candidates") or () if isinstance(row, Mapping)
    ]
    rows = [
        row
        for row in receipt.get("candidate_receipts") or ()
        if isinstance(row, Mapping)
    ]
    if len(rows) != len(candidates) or int(receipt.get("candidate_count", -1)) != len(
        candidates
    ):
        raise ValueError("target-statement elaboration receipt misses candidates")
    expected_ids = [str(row.get("candidate_id") or "") for row in candidates]
    if [str(row.get("candidate_id") or "") for row in rows] != expected_ids:
        raise ValueError("target-statement elaboration candidate order changed")
    eligible: set[str] = set()
    rejected: set[str] = set()
    unavailable: set[str] = set()
    required_row_fields = {
        "candidate_id", "candidate_sha256", "formal_status",
        "declared_imports", "signature_sha256", "probe_source_sha256",
        "compile_invoked", "status", "reason_code", "guide_eligible",
        "checker_owner", "row_sha256",
    }
    if wave_schema == TARGET_CONJECTURE_WAVE_SCHEMA:
        required_row_fields.add("formal_context")
    for candidate, row in zip(candidates, rows, strict=True):
        if set(row) != required_row_fields:
            raise ValueError("target-statement elaboration row fields differ")
        row_core = {key: value for key, value in row.items() if key != "row_sha256"}
        raw_imports = candidate.get("required_imports")
        expected_imports = (
            [str(value).strip() for value in raw_imports]
            if isinstance(raw_imports, list)
            else []
        )
        formal_status = str(candidate.get("formal_status") or "")
        expected_source = ""
        if formal_status == "lean_candidate":
            try:
                expected_source, _selector = render_target_candidate_source(
                    candidate,
                    target_name="targetConditionedStatementPreflight",
                    require_formal_context=(
                        wave_schema == TARGET_CONJECTURE_WAVE_SCHEMA
                    ),
                )
            except ValueError:
                expected_source = ""
        if (
            row.get("row_sha256") != content_hash(row_core)
            or row.get("candidate_sha256") != candidate.get("candidate_sha256")
            or row.get("checker_owner") != TARGET_STATEMENT_CHECKER_OWNER
            or row.get("formal_status") != formal_status
            or row.get("declared_imports") != expected_imports
            or row.get("signature_sha256")
            != content_hash(str(candidate.get("lean_signature") or "").strip())
            or row.get("probe_source_sha256")
            != (content_hash(expected_source) if expected_source else "")
            or (
                wave_schema == TARGET_CONJECTURE_WAVE_SCHEMA
                and row.get("formal_context") != candidate.get("formal_context")
            )
        ):
            raise ValueError("target-statement elaboration row identity mismatch")
        status = str(row.get("status") or "")
        guide_eligible = row.get("guide_eligible") is True
        if guide_eligible != (status in {"elaborated", "not_applicable"}):
            raise ValueError("target-statement elaboration consequence mismatch")
        if (
            (status == "not_applicable") != (formal_status == "language_gap")
            or status == "elaborated" and row.get("compile_invoked") is not True
            or status not in {"elaborated", "rejected", "unavailable", "not_applicable"}
        ):
            raise ValueError("target-statement elaboration status is incompatible")
        if guide_eligible:
            eligible.add(str(row["candidate_id"]))
        if status == "rejected":
            rejected.add(str(row["candidate_id"]))
        if status == "unavailable":
            unavailable.add(str(row["candidate_id"]))
    if eligible != {
        str(value) for value in receipt.get("guide_eligible_candidate_ids") or ()
    }:
        raise ValueError("target-statement elaboration eligible set mismatch")
    if rejected != {
        str(value) for value in receipt.get("rejected_candidate_ids") or ()
    } or unavailable != {
        str(value) for value in receipt.get("unavailable_candidate_ids") or ()
    }:
        raise ValueError("target-statement elaboration disposition sets mismatch")
    return eligible


def validate_target_statement_elaboration(
    wave: Mapping[str, Any], receipt: Mapping[str, Any]
) -> dict[str, dict[str, Any]]:
    """Replay one statement receipt and expose its candidate-indexed rows."""

    _validated_guide_eligible_ids(wave, receipt)
    return {
        str(row["candidate_id"]): dict(row)
        for row in receipt["candidate_receipts"]
    }


def _statement_diagnostic_category(diagnostic: str) -> str:
    lowered = diagnostic.lower()
    if not lowered.strip():
        return "diagnostic_unavailable"
    if any(token in lowered for token in (
        "unexpected token", "unexpected ')'", "unexpected ']'",
        "unexpected '}'", "invalid parser", "expected token",
    )):
        return "lean_syntax_error"
    if any(token in lowered for token in (
        "unknown identifier", "unknown constant", "invalid field notation",
    )):
        return "lean_name_resolution_error"
    if "failed to synthesize" in lowered or "typeclass" in lowered:
        return "lean_instance_synthesis_error"
    if "type mismatch" in lowered or "application type mismatch" in lowered:
        return "lean_type_mismatch"
    return "lean_elaboration_error"


def build_target_statement_revision_feedback(
    wave: Mapping[str, Any],
    statement_elaboration_receipt: Mapping[str, Any],
    *,
    lean_root: str | Path,
    successor_revision_epoch: int,
    diagnose_fn: Callable[[str, str | Path], str] | None = None,
) -> dict[str, Any]:
    """Return bounded Lean diagnostics without changing rejected statement bytes."""

    indexed = validate_target_statement_elaboration(
        wave, statement_elaboration_receipt
    )
    if type(successor_revision_epoch) is not int or successor_revision_epoch < 1:
        raise ValueError("target statement successor revision epoch must be positive")
    if diagnose_fn is None:
        from ztare.leanmill.solver.autoformalize import default_compile_diagnose

        diagnose_fn = default_compile_diagnose
    candidates = {
        str(row.get("candidate_id") or ""): row
        for row in wave.get("candidates") or ()
        if isinstance(row, Mapping)
    }
    feedback_rows: list[dict[str, Any]] = []
    for candidate_id in statement_elaboration_receipt.get(
        "rejected_candidate_ids"
    ) or ():
        candidate = candidates[str(candidate_id)]
        elaboration = indexed[str(candidate_id)]
        source = ""
        diagnostic = ""
        try:
            source, _selector = render_target_candidate_source(
                candidate,
                target_name="targetConditionedStatementPreflight",
                require_formal_context=(
                    wave.get("schema") == TARGET_CONJECTURE_WAVE_SCHEMA
                ),
            )
        except ValueError as exc:
            diagnostic = f"formal context rejected: {type(exc).__name__}"
        else:
            try:
                raw = diagnose_fn(source, lean_root)
                diagnostic = raw if isinstance(raw, str) else ""
            except Exception as exc:  # noqa: BLE001 - advisory feedback outcome
                diagnostic = f"diagnostic owner unavailable: {type(exc).__name__}"
        bounded = " ".join(diagnostic.replace(str(lean_root), "<lean_root>").split())[
            :2000
        ]
        row = {
            "candidate_id": str(candidate_id),
            "candidate_sha256": str(candidate["candidate_sha256"]),
            "source_wave_sha256": str(wave["wave_sha256"]),
            "source_elaboration_row_sha256": str(elaboration["row_sha256"]),
            "immutable_signature_sha256": str(elaboration["signature_sha256"]),
            "immutable_probe_source_sha256": str(
                elaboration["probe_source_sha256"]
            ),
            "diagnostic_category": _statement_diagnostic_category(bounded),
            "diagnostic_sha256": content_hash(bounded),
            "diagnostic_excerpt": bounded[:600],
            "successor_revision_epoch": successor_revision_epoch,
            "permitted_revision_fields": [
                "lean_signature", "required_imports", "formal_context"
            ],
            "prior_candidate_mutation_permitted": False,
            "next_authority": "target_conjecture_author_revision",
            "diagnostic_owner": TARGET_STATEMENT_DIAGNOSTIC_OWNER,
        }
        feedback_rows.append({**row, "row_sha256": content_hash(row)})
    core = {
        "schema": "leanmill.target_statement_revision_feedback.v1",
        "source_wave_sha256": str(wave["wave_sha256"]),
        "source_elaboration_receipt_sha256": str(
            statement_elaboration_receipt["receipt_sha256"]
        ),
        "successor_revision_epoch": successor_revision_epoch,
        "rejected_candidate_count": len(feedback_rows),
        "candidate_feedback": feedback_rows,
        "status": "revision_requested" if feedback_rows else "no_revision_needed",
        "next_authority": (
            "target_conjecture_author_revision"
            if feedback_rows else "target_guide_or_navigation"
        ),
        "diagnostic_owner": TARGET_STATEMENT_DIAGNOSTIC_OWNER,
        "authority": "feedback_only_prior_statement_bytes_immutable",
    }
    return {**core, "receipt_sha256": content_hash(core)}


def validate_target_statement_revision_feedback(
    wave: Mapping[str, Any],
    statement_elaboration_receipt: Mapping[str, Any],
    feedback: Mapping[str, Any],
) -> dict[str, Any]:
    indexed = validate_target_statement_elaboration(
        wave, statement_elaboration_receipt
    )
    core = {key: value for key, value in feedback.items() if key != "receipt_sha256"}
    rows = feedback.get("candidate_feedback")
    rejected = [
        str(value)
        for value in statement_elaboration_receipt.get("rejected_candidate_ids") or ()
    ]
    if (
        feedback.get("schema") != "leanmill.target_statement_revision_feedback.v1"
        or feedback.get("receipt_sha256") != content_hash(core)
        or feedback.get("source_wave_sha256") != wave.get("wave_sha256")
        or feedback.get("source_elaboration_receipt_sha256")
        != statement_elaboration_receipt.get("receipt_sha256")
        or not isinstance(rows, list)
        or feedback.get("rejected_candidate_count") != len(rows)
        or [str(row.get("candidate_id") or "") for row in rows] != rejected
    ):
        raise ValueError("target statement revision feedback changed identity")
    candidate_by_id = {
        str(row.get("candidate_id") or ""): row
        for row in wave.get("candidates") or ()
        if isinstance(row, Mapping)
    }
    for row in rows:
        row_core = {key: value for key, value in row.items() if key != "row_sha256"}
        candidate_id = str(row.get("candidate_id") or "")
        if (
            row.get("row_sha256") != content_hash(row_core)
            or candidate_id not in candidate_by_id
            or row.get("candidate_sha256")
            != candidate_by_id[candidate_id].get("candidate_sha256")
            or row.get("source_elaboration_row_sha256")
            != indexed[candidate_id].get("row_sha256")
            or row.get("prior_candidate_mutation_permitted") is not False
        ):
            raise ValueError("target statement revision row changed prior identity")
    return dict(feedback)


def target_statement_revision_output_schema(
    rejected_candidate_ids: Sequence[str],
) -> dict[str, Any]:
    ids = tuple(dict.fromkeys(str(value) for value in rejected_candidate_ids))
    if not ids:
        raise ValueError("target statement revision requires rejected candidates")
    revision = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "predecessor_candidate_id", "lean_signature", "required_imports",
            "formal_context", "revision_summary",
        ],
        "properties": {
            "predecessor_candidate_id": {"enum": list(ids)},
            "lean_signature": {"type": "string", "minLength": 1},
            "required_imports": {
                "type": "array", "minItems": 1,
                "items": {"type": "string", "minLength": 1},
            },
            "formal_context": {
                "type": "object",
                "additionalProperties": False,
                "required": ["open_namespaces", "enclosing_namespace"],
                "properties": {
                    "open_namespaces": {
                        "type": "array",
                        "items": {"type": "string", "minLength": 1},
                    },
                    "enclosing_namespace": {"type": "string"},
                },
            },
            "revision_summary": {"type": "string", "minLength": 1},
        },
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": ["revisions", "abandoned_candidate_ids"],
        "properties": {
            "revisions": {"type": "array", "items": revision},
            "abandoned_candidate_ids": {
                "type": "array", "items": {"enum": list(ids)},
            },
        },
    }


def revise_target_conjecture_wave(
    wave: Mapping[str, Any],
    statement_elaboration_receipt: Mapping[str, Any],
    revision_feedback: Mapping[str, Any],
    author_output: Mapping[str, Any],
    *,
    call_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Mint a successor epoch; predecessor candidate bytes remain unchanged."""

    validate_target_statement_revision_feedback(
        wave, statement_elaboration_receipt, revision_feedback
    )
    rejected = tuple(
        str(value)
        for value in statement_elaboration_receipt.get("rejected_candidate_ids") or ()
    )
    Draft202012Validator(target_statement_revision_output_schema(rejected)).validate(
        author_output
    )
    revisions = [dict(row) for row in author_output.get("revisions") or ()]
    abandoned = [str(value) for value in author_output.get("abandoned_candidate_ids") or ()]
    revised_ids = [str(row["predecessor_candidate_id"]) for row in revisions]
    if (
        len(set(revised_ids)) != len(revised_ids)
        or len(set(abandoned)) != len(abandoned)
        or set(revised_ids) & set(abandoned)
        or set(revised_ids) | set(abandoned) != set(rejected)
    ):
        raise ValueError("target statement revision must dispose every rejected candidate once")
    predecessors = {
        str(row.get("candidate_id") or ""): row
        for row in wave.get("candidates") or ()
        if isinstance(row, Mapping)
    }
    successor_candidates: list[dict[str, Any]] = []
    for revision in revisions:
        predecessor = predecessors[str(revision["predecessor_candidate_id"])]
        signature = str(revision["lean_signature"]).strip()
        if (
            ":=" in signature
            or re.search(
                r"(?<![A-Za-z0-9_])(theorem|lemma|by|sorry|admit|axiom)(?![A-Za-z0-9_])",
                signature,
            )
        ):
            raise ValueError("successor revision is not a proof-free Lean signature")
        imports = [str(value).strip() for value in revision["required_imports"]]
        if any(not _LEAN_IMPORT.fullmatch(value) for value in imports):
            raise ValueError("successor revision imports are invalid")
        formal_context = _validated_formal_context(revision["formal_context"])
        base = {
            key: value for key, value in predecessor.items()
            if key not in {
                "candidate_id", "candidate_sha256", "also_proposed_from",
                "normalized_lean_signature", "recurrence_status",
            }
        }
        base.update({
            "lean_signature": signature,
            "required_imports": imports,
            "formal_context": formal_context,
            "normalized_lean_signature": _normalize_lean_signature(signature),
            "recurrence_status": "successor_revision_pending_replay",
            "predecessor_candidate_id": str(revision["predecessor_candidate_id"]),
            "revision_summary": str(revision["revision_summary"]),
        })
        identity_core = {
            "deck_sha256": wave["deck_sha256"],
            "source_card_id": base["source_card_id"],
            "candidate_family": base["candidate_family"],
            "mathematical_statement": base["mathematical_statement"],
            "normalized_lean_signature": base["normalized_lean_signature"],
            "formal_context": formal_context,
            "target_edge": base["target_edge"],
            "predecessor_candidate_id": base["predecessor_candidate_id"],
            "revision_epoch": int(revision_feedback["successor_revision_epoch"]),
        }
        core = {
            **base,
            "candidate_id": "target-conjecture:" + content_hash(identity_core),
        }
        successor_candidates.append({
            **core,
            "candidate_sha256": content_hash(core),
            "also_proposed_from": [],
        })
    wave_core = {
        "schema": TARGET_CONJECTURE_WAVE_SCHEMA,
        "deck_sha256": str(wave["deck_sha256"]),
        "objective_sha256": str(wave["objective_sha256"]),
        "card_count": int(wave["card_count"]),
        "candidate_count": len(successor_candidates),
        "candidates": successor_candidates,
        "call_receipts": [dict(call_receipt)],
        "revision_epoch": int(revision_feedback["successor_revision_epoch"]),
        "predecessor_wave_sha256": str(wave["wave_sha256"]),
        "revision_feedback_sha256": str(revision_feedback["receipt_sha256"]),
        "abandoned_predecessor_candidate_ids": abandoned,
        "formal_context_owner": TARGET_FORMAL_CONTEXT_OWNER,
        "authority": "agent_revisions_pending_independent_guide_and_verification",
    }
    return {**wave_core, "wave_sha256": content_hash(wave_core)}


def validate_target_guide_receipt(
    wave: Mapping[str, Any], receipt: Mapping[str, Any]
) -> tuple[str, ...]:
    """Validate the advisory Guide artifact before it selects executable work."""

    if receipt.get("schema") != "leanmill.eigenquestion_review.v1":
        raise ValueError("target admission lacks an eigenquestion Guide receipt")
    required = {
        "schema", "authority", "runtime", "model", "prompt_sha256",
        "recommended_question_id", "review", "receipt_sha256",
    }
    core = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    if (
        set(receipt) != required
        or receipt.get("authority") != "advisory_only"
        or receipt.get("receipt_sha256") != content_hash(core)
    ):
        raise ValueError("target Guide receipt changed identity")
    review = receipt.get("review")
    if not isinstance(review, Mapping):
        raise ValueError("target Guide review is malformed")
    sequence = tuple(str(value) for value in review.get("portfolio_sequence") or ())
    rankings = review.get("ranked_questions")
    ranked_ids = (
        tuple(str(row.get("question_id") or "") for row in rankings)
        if isinstance(rankings, list)
        and all(isinstance(row, Mapping) for row in rankings)
        else ()
    )
    wave_ids = {
        str(row.get("candidate_id") or "")
        for row in wave.get("candidates") or ()
        if isinstance(row, Mapping)
    }
    if (
        not sequence
        or len(set(sequence)) != len(sequence)
        or set(sequence) != set(ranked_ids)
        or not set(sequence) <= wave_ids
        or receipt.get("recommended_question_id") != sequence[0]
    ):
        raise ValueError("target Guide portfolio changed candidate identity")
    return sequence


def build_target_conjecture_admission(
    wave: Mapping[str, Any],
    statement_elaboration_receipt: Mapping[str, Any],
    *,
    run_tag: str,
    deck_sha256: str,
    replay_receipt_sha256: str,
    guide_receipt: Mapping[str, Any] | None,
    selected_candidate_ids: Sequence[str],
) -> dict[str, Any]:
    """Freeze the Guide selection after statement-level elaboration replay."""

    rows = validate_target_statement_elaboration(
        wave, statement_elaboration_receipt
    )
    selected = tuple(str(value) for value in selected_candidate_ids)
    if not all(str(value).strip() for value in (
        run_tag, deck_sha256, replay_receipt_sha256
    )):
        raise ValueError("target admission identity is incomplete")
    if deck_sha256 != wave.get("deck_sha256"):
        raise ValueError("target admission crossed its result-card deck")
    if len(set(selected)) != len(selected):
        raise ValueError("target admission duplicated a candidate")
    if guide_receipt is None:
        if selected:
            raise ValueError("target admission selected work without Guide review")
        guide_sha = ""
        sequence: tuple[str, ...] = ()
    else:
        sequence = validate_target_guide_receipt(wave, guide_receipt)
        guide_sha = str(guide_receipt["receipt_sha256"])
    sequence_positions = {candidate_id: index for index, candidate_id in enumerate(sequence)}
    if selected and (
        any(candidate_id not in sequence_positions for candidate_id in selected)
        or list(selected) != sorted(selected, key=sequence_positions.__getitem__)
        or any(
            rows.get(candidate_id, {}).get("guide_eligible") is not True
            for candidate_id in selected
        )
    ):
        raise ValueError(
            "target admission includes an unreviewed or unelaborated candidate"
        )
    has_elaborated_statement = any(
        rows[candidate_id]["status"] == "elaborated" for candidate_id in selected
    )
    next_authority = (
        "source_adjacent_candidate_adjudication"
        if has_elaborated_statement
        else "language_expansion_or_target_navigation"
        if selected
        else "target_conjecture_author_revision"
        if statement_elaboration_receipt.get("rejected_candidate_ids")
        else "target_navigation"
    )
    core = {
        "schema": TARGET_CONJECTURE_ADMISSION_SCHEMA,
        "run_tag": str(run_tag),
        "deck_sha256": str(deck_sha256),
        "replay_receipt_sha256": str(replay_receipt_sha256),
        "wave_sha256": str(wave["wave_sha256"]),
        "statement_elaboration_receipt_sha256": str(
            statement_elaboration_receipt["receipt_sha256"]
        ),
        "guide_receipt_sha256": guide_sha,
        "selected_candidate_ids": list(selected),
        "status": "guide_selected" if selected else "no_candidate",
        "next_authority": next_authority,
        "authority": "host_identity_join_only_no_theorem_content",
    }
    return {**core, "receipt_sha256": content_hash(core)}


def validate_target_conjecture_admission(
    wave: Mapping[str, Any],
    statement_elaboration_receipt: Mapping[str, Any],
    guide_receipt: Mapping[str, Any] | None,
    admission: Mapping[str, Any],
) -> dict[str, Any]:
    """Replay the complete wave -> elaboration -> Guide -> admission join."""

    expected = build_target_conjecture_admission(
        wave,
        statement_elaboration_receipt,
        run_tag=str(admission.get("run_tag") or ""),
        deck_sha256=str(admission.get("deck_sha256") or ""),
        replay_receipt_sha256=str(
            admission.get("replay_receipt_sha256") or ""
        ),
        guide_receipt=guide_receipt,
        selected_candidate_ids=tuple(
            str(value) for value in admission.get("selected_candidate_ids") or ()
        ),
    )
    if dict(admission) != expected:
        raise ValueError("target-conjecture admission does not replay")
    return expected


def guide_questions(
    wave: Mapping[str, Any],
    statement_elaboration_receipt: Mapping[str, Any],
) -> list[dict[str, Any]]:
    if wave.get("schema") != TARGET_CONJECTURE_WAVE_SCHEMA:
        raise ValueError("Guide input is not a target-conjecture wave")
    eligible = _validated_guide_eligible_ids(wave, statement_elaboration_receipt)
    return [
        {
            "question_id": row["candidate_id"],
            "question": row["mathematical_statement"],
            "formal_status": row["formal_status"],
            "candidate_family": row["candidate_family"],
            "expected_direction": row["expected_direction"],
            "target_edge": row["target_edge"],
            "falsification_plan": row["falsification_plan"],
            "recurrence_risk": row["recurrence_risk"],
            "scope_limits": row["scope_limits"],
            "source_target_identity": row["source_target_identity"],
        }
        for row in wave.get("candidates") or ()
        if row["candidate_id"] in eligible
    ]


__all__ = [
    "LEGACY_TARGET_CONJECTURE_WAVE_SCHEMA",
    "LEGACY_TARGET_STATEMENT_ELABORATION_SCHEMA",
    "TARGET_CONJECTURE_ADMISSION_SCHEMA",
    "TARGET_CONJECTURE_WAVE_SCHEMA",
    "TARGET_FORMAL_CONTEXT_OWNER",
    "TARGET_STATEMENT_ELABORATION_SCHEMA",
    "TARGET_STATEMENT_CHECKER_OWNER",
    "TARGET_STATEMENT_DIAGNOSTIC_OWNER",
    "build_target_conjecture_admission",
    "build_target_conjecture_wave",
    "build_target_statement_revision_feedback",
    "guide_questions",
    "normalize_conjecturer_output",
    "preflight_target_conjecture_wave",
    "render_target_candidate_source",
    "render_target_conjecture_prompt",
    "revise_target_conjecture_wave",
    "target_conjecture_output_schema",
    "target_statement_revision_output_schema",
    "validate_target_conjecture_admission",
    "validate_target_guide_receipt",
    "validate_target_statement_elaboration",
    "validate_target_statement_revision_feedback",
]
