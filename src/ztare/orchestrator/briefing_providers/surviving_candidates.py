"""Candidate-memory briefing provider: survivors and deterministic near-misses.

General-purpose (any project with a frozen `gate_harness.py` and submission
snapshots — quantitative fits, world models, qualitative discriminators).
The loop's champion/revert flow keeps ONE model; every other gate-passing
or near-passing submission was a live rival that could vanish into prose. This
provider briefs the mutator from a persisted candidate-memory artifact with:

  * full survivors — candidates that pass every deterministic gate;
  * deterministic near-misses — candidates that fail promotion but carry useful
    gate diagnostics such as visible exact rows or rollout depth.

Producer/reader split: gate runners write `workspace/candidate_memory.json`
when they already evaluate a candidate. Prompt assembly reads that artifact;
it does not spend prompt-time compute re-running harnesses.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ztare.common.candidate_memory import (
    admissible_candidate_memory_records,
    candidate_memory_contract_error,
)
from ztare.common.patch_base_identity import load_current_repair_frontier
from ztare.common.activity_meter import summarize_activity_spend
from ztare.common.cegis_membrane import assess_cegis_membrane
from ztare.orchestrator.briefing_providers import section_unavailable
from ztare.orchestrator.mutator_briefing import BriefingContext, BriefingProvider
from ztare.worldmodel.patch_carrier_contract import patch_base_declaration, patch_delta_signature
from ztare.worldmodel.carrier_loader import CurrentCarrierEvidenceIdentity

_CACHE_NAME = "candidate_memory.json"
_CACHE_SCHEMA = "ztare-candidate-memory-v1"
_MAX_CACHE_RECORDS = 64
_MAX_SOURCE_EXCERPT_CHARS = 2200


class SurvivingCandidatesProvider(BriefingProvider):
    name = "surviving_candidates"
    priority = 35
    max_fragment_chars = 5200

    def applies(self, ctx: BriefingContext) -> bool:
        project = Path(getattr(ctx, "project_dir", "") or "")
        if not (project / "gate_harness.py").exists():
            return False
        if _cache_path(project).exists():
            return True
        return bool((ctx.rubric or {}).get("briefing_compute_candidate_memory", False)) \
            and (project / "workspace" / "submissions").exists()

    def fragment(self, ctx: BriefingContext) -> str:
        project = Path(ctx.project_dir)
        try:
            memory_records = _fresh_records(project, _load_records(project, strict=True))
        except _CacheReadError as exc:
            return section_unavailable("DETERMINISTIC CANDIDATE MEMORY", exc)
        records = admissible_candidate_memory_records(
            project,
            memory_records,
        )
        if _worldmodel_contract(ctx):
            records = _records_with_current_repair_frontier(project, records)
        rejected_witnesses = (
            _diagnostic_rejected_witnesses(project, memory_records, records)
            if _worldmodel_contract(ctx)
            else []
        )
        survivors = [
            rec for rec in records
            if rec.get("source_type") == "full_survivor"
        ]
        near_misses = [
            rec for rec in records
            if rec.get("source_type") == "deterministic_near_miss"
        ]
        if not survivors and not near_misses:
            if bool((ctx.rubric or {}).get("briefing_compute_candidate_memory", False)):
                return section_unavailable(
                    "DETERMINISTIC CANDIDATE MEMORY",
                    RuntimeError(
                        "no admissible producer receipt; prompt assembly is read-only "
                        "and cannot re-run candidate gates"
                    ),
                )
            return ""
        lines = [
            "## Deterministic Candidate Memory",
            "- ATTENTION: this is executable counterexample memory from deterministic gates. "
            "Prefer these rows over stale prose when they conflict.",
        ]
        if survivors:
            best = sorted(survivors, key=_record_rank_key, reverse=True)[0]
            lines.append(
                "- BEST FULL SURVIVOR: this candidate already passes every deterministic "
                "gate represented in candidate memory. Treat it as the transition-law "
                "baseline unless the sealed environment or a newer gate receipt refutes it."
            )
            lines.append("  " + _format_full_survivor(best))
            source_block = _format_full_survivor_source(project, best)
            if source_block:
                lines.append(source_block)
        if len(survivors) >= 2:
            lines.append(
                f"- LIVE RIVALS: {len(survivors)} prior submissions STILL pass every "
                "deterministic gate on the current evidence. The next move is a "
                "DISCRIMINATING experiment: state where these rivals make different "
                "predictions and design the observation that separates them."
            )
            for rec in survivors[:6]:
                lines.append(
                    f"  survivor: {rec.get('submission')} (sha {rec.get('sha')})"
                )
        if near_misses:
            lines.append(
                "- NEAR-MISS SURVIVORS: these failed promotion, but their gate "
                "diagnostics carry useful law fragments. Mutate from the best "
                "surviving mechanism; do not restart from prose alone."
            )
            ranked = sorted(near_misses, key=_near_miss_sort_key, reverse=True)
            for rec in ranked[:5]:
                lines.append("  " + _format_near_miss(rec))
            patchable = [rec for rec in ranked if _is_submission_artifact(rec)]
            if not survivors and patchable:
                mode, mode_note = _patch_base_mode(project)
                if mode_note:
                    lines.append(f"- ⚠️  DEGRADED: {mode_note}")
                source_block = _format_patch_base(
                    project,
                    patchable[0],
                    inline_source=_inline_near_miss_source(ctx),
                    mode=mode,
                )
                if source_block:
                    lines.append(source_block)
        if rejected_witnesses:
            lines.append(
                "- DIAGNOSTIC REJECTED WITNESSES: these scored well but violate the "
                "current carrier contract. Use them only to infer the missing "
                "state/action witness; do not copy them as patch bases."
            )
            for rec, reason in rejected_witnesses[:3]:
                lines.append("  " + _format_rejected_witness(rec, reason))
        return "\n".join(lines) + "\n"

    def structured_records(self, ctx: BriefingContext) -> list[dict]:
        project = Path(ctx.project_dir)
        memory_records = _fresh_records(project, _load_records(project))
        records = admissible_candidate_memory_records(
            project,
            memory_records,
        )
        if _worldmodel_contract(ctx):
            records = _records_with_current_repair_frontier(project, records)
        out = sorted(records, key=_record_rank_key, reverse=True)[:8]
        if _worldmodel_contract(ctx):
            for rec, reason in _diagnostic_rejected_witnesses(project, memory_records, records)[:3]:
                row = dict(rec)
                row["record_role"] = "diagnostic_rejected_witness"
                row["contract_rejection_reason"] = reason
                out.append(row)
        return out


def _records_with_current_repair_frontier(
    project: Path,
    admissible_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Bind plural candidate evidence to the receipt-owned repair role."""

    immutable = [rec for rec in admissible_records if _is_submission_artifact(rec)]
    try:
        frontier = load_current_repair_frontier(project)
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return immutable
    full_sha = str(frontier["sha256"])
    def same_carrier(rec: dict[str, Any]) -> bool:
        candidate_sha = str(rec.get("sha") or "").strip()
        return candidate_sha == full_sha

    matching = [
        rec for rec in admissible_records
        if same_carrier(rec)
    ]
    if matching:
        active = dict(max(matching, key=lambda rec: str(rec.get("observed_at_utc") or "")))
    else:
        active = {
            "source_type": "deterministic_near_miss",
            "visible_checked_rows": 0,
            "observed_at_utc": "",
        }
    source = frontier["path"].read_text(encoding="utf-8")
    active.update({
        "sha": full_sha,
        "submission": frontier["source_ref"],
        "source_excerpt": source[:_MAX_SOURCE_EXCERPT_CHARS],
        "source_truncated": len(source) > _MAX_SOURCE_EXCERPT_CHARS,
        "visible_exact_rows": frontier["exact_rows"],
        "visible_wrong_cells": frontier["wrong_cells"],
        "holdout_depth": frontier["holdout_depth"],
        "gate_score": frontier["gate_score"],
        "repair_frontier_role": frontier["role"],
        "repair_frontier_receipt_ref": frontier["receipt_ref"],
        "evidence_epoch_sha256": frontier["evidence_epoch_sha256"],
        "carrier_evidence_identity": CurrentCarrierEvidenceIdentity(
            carrier_ref=str(frontier["source_ref"]),
            carrier_sha256=full_sha,
            evidence_epoch_sha256=str(frontier["evidence_epoch_sha256"]),
            carrier_role="repair_frontier",
        ).to_dict(),
    })
    return [
        rec for rec in immutable
        if not same_carrier(rec)
    ] + [active]


def record_candidate_gate_payload(
    *,
    project_dir: str | Path,
    candidate_path: str | Path | None,
    gate_payload: dict[str, Any],
    artifact_role: str = "behavior_carrier",
    max_records: int = _MAX_CACHE_RECORDS,
) -> None:
    """Persist candidate-memory from an already-run deterministic gate.

    This is intentionally side-effect-light and best-effort. It must not change
    gate semantics; it only preserves useful partial structure for the next
    prompt.
    """
    project = Path(project_dir)
    candidate = Path(candidate_path) if candidate_path is not None else None
    name = candidate.name if candidate is not None else "test_model.py"
    digest = _candidate_digest(candidate, gate_payload)
    submission = _submission_label(project, candidate)
    rec = _record_from_payload(name, digest, gate_payload, submission=submission)
    if rec is None:
        return
    rec["artifact_role"] = str(artifact_role or "behavior_carrier")
    epoch = gate_payload.get("evidence_epoch")
    if isinstance(epoch, dict) and str(epoch.get("epoch_sha256") or "").strip():
        epoch_sha = str(epoch["epoch_sha256"])
        rec["evidence_epoch_sha256"] = epoch_sha
        if len(digest) == 64 and len(epoch_sha) == 64:
            rec["carrier_evidence_identity"] = CurrentCarrierEvidenceIdentity(
                carrier_ref=str(submission or name),
                carrier_sha256=digest,
                evidence_epoch_sha256=epoch_sha,
                carrier_role="evaluated_candidate",
            ).to_dict()
    policy_sha = str(gate_payload.get("evaluation_policy_sha256") or "").strip()
    if policy_sha:
        rec["evaluation_policy_sha256"] = policy_sha
    description_length = gate_payload.get("description_length")
    if isinstance(description_length, int) and description_length > 0:
        rec["description_length"] = description_length
        rec["description_length_unit"] = str(
            gate_payload.get("description_length_unit")
            or "source_token_closure_v1"
        )
    if not rec.get("holdout_witness"):
        rec["holdout_witness"] = _fallback_holdout_witness(project)
    trace_holdout = _holdout_witness_from_gate(
        (gate_payload.get("gates") or {}).get("holdout_rollout_exact", {})
        if isinstance(gate_payload.get("gates"), dict)
        else {},
    ) or rec.get("holdout_witness")
    rec["counterexample_trace"] = _counterexample_trace_from_payload(
        gate_payload,
        holdout_witness=trace_holdout,
    )
    if gate_payload.get("assistance_label"):
        rec["assistance_label"] = str(gate_payload.get("assistance_label"))
    records = _load_records(project)
    membrane = assess_cegis_membrane(
        role=str(gate_payload.get("run_role") or "EVALUATION"),
        withheld_refs=tuple(str(ref) for ref in gate_payload.get("withheld_refs") or ()),
        exposed_refs=tuple(str(ref) for ref in gate_payload.get("exposed_refs") or ()),
        candidate_gate_passed=float(rec.get("gate_score") or 0.0) >= 1.0,
    ).to_dict()
    membrane_keys = (
        "run_role",
        "holdout_exposed_to_proposer",
        "claim_class",
        "fresh_holdout_required",
        "withheld_refs",
        "exposed_withheld_refs",
        "evidence_statuses",
        "supportable_claims",
        "forbidden_claims",
        "membrane_status",
    )
    for key in membrane_keys:
        rec[key] = membrane[key]
    if not str(gate_payload.get("run_role") or "").strip():
        prior = next(
            (
                row
                for row in records
                if str(row.get("sha") or "") == digest
                and str(row.get("submission") or "") == str(submission or "")
                and bool(row.get("fresh_holdout_required"))
            ),
            None,
        )
        if prior is not None:
            for key in membrane_keys:
                rec[key] = prior.get(key)
    rec["activity_meter"] = summarize_activity_spend([gate_payload])
    _attach_source_excerpt(rec, candidate)
    rec["observed_at_utc"] = datetime.now(timezone.utc).isoformat()
    dedup_key = (
        rec.get("sha"),
        rec.get("submission"),
        rec.get("source_type"),
        rec.get("evidence_epoch_sha256"),
        rec.get("evaluation_policy_sha256"),
    )
    records = [
        old for old in records
        if (
            old.get("sha"),
            old.get("submission"),
            old.get("source_type"),
            old.get("evidence_epoch_sha256"),
            old.get("evaluation_policy_sha256"),
        ) != dedup_key
    ]
    records.append(rec)
    records = sorted(records, key=_record_rank_key, reverse=True)[:max_records]
    _write_cache(project, records)


def _cache_path(project: Path) -> Path:
    return project / "workspace" / _CACHE_NAME


class _CacheReadError(Exception):
    """The candidate-memory cache exists but is unreadable/unparseable.

    Distinct from "no cache" (absent file → []). A corrupt cache must NOT be
    coerced into an empty record set, which would silently OMIT the whole
    candidate-memory section; ``fragment`` surfaces this as a banner instead.
    """


def _load_records(project: Path, *, strict: bool = False) -> list[dict[str, Any]]:
    path = _cache_path(project)
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        if strict:
            raise _CacheReadError(f"candidate_memory.json unreadable: {exc}") from exc
        return []
    if not isinstance(payload, dict) or payload.get("schema") != _CACHE_SCHEMA:
        if strict:
            raise _CacheReadError(
                "candidate_memory.json has wrong schema or is not an object"
            )
        return []
    records = payload.get("records") or []
    return [rec for rec in records if isinstance(rec, dict)]


def _fresh_records(project: Path, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [rec for rec in records if not _record_source_stale(project, rec)]


def _diagnostic_rejected_witnesses(
    project: Path,
    memory_records: list[dict[str, Any]],
    admissible_records: list[dict[str, Any]],
) -> list[tuple[dict[str, Any], str]]:
    admissible_keys = {
        (rec.get("submission"), rec.get("sha"), rec.get("source_type"))
        for rec in admissible_records
    }
    out: list[tuple[dict[str, Any], str]] = []
    for rec in memory_records:
        if not _is_submission_artifact(rec):
            continue
        key = (rec.get("submission"), rec.get("sha"), rec.get("source_type"))
        if key in admissible_keys:
            continue
        reason = candidate_memory_contract_error(project, rec)
        if not reason:
            continue
        if int(rec.get("visible_exact_rows") or 0) <= 0:
            continue
        out.append((rec, _compress_contract_reason(reason)))
    return sorted(out, key=lambda item: _near_miss_sort_key(item[0]), reverse=True)


def _compress_contract_reason(reason: str) -> str:
    text = " ".join(str(reason or "").split())
    if "temporal admissibility" in text or "adapter replay index" in text:
        return "reads adapter replay index; must be re-expressed as state/action evidence"
    if "global`/`nonlocal" in text or "module-scope" in text:
        return "uses replay-order mutable state; must be re-expressed as pure state/action evidence"
    if "full 64-hex" in text:
        return "legacy patch-base hash prefix; use gate-supplied full sha256 in new carriers"
    return text[:220]


def _record_source_stale(project: Path, rec: dict[str, Any]) -> bool:
    submission = str(rec.get("submission") or "")
    if not submission:
        return False
    path = project / submission
    if not path.exists() or not path.is_file():
        return False
    try:
        current = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    except Exception:
        return False
    cached = str(rec.get("sha") or "")[:12]
    return bool(cached) and current != cached


def _artifact_full_sha(project: Path, submission: str) -> str:
    raw = Path(str(submission or ""))
    if raw.is_absolute() or ".." in raw.parts:
        return ""
    path = (project / raw).resolve()
    try:
        path.relative_to(project.resolve())
    except ValueError:
        return ""
    if not path.is_file():
        return ""
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except Exception:
        return ""


def _is_submission_artifact(rec: dict[str, Any]) -> bool:
    submission = str(rec.get("submission") or "")
    raw = Path(submission)
    return (
        not raw.is_absolute()
        and ".." not in raw.parts
        and len(raw.parts) >= 3
        and raw.parts[:2] == ("workspace", "submissions")
    )


def _worldmodel_contract(ctx: BriefingContext) -> bool:
    rubric = ctx.rubric or {}
    return (
        rubric.get("substrate_class") == "interactive_environment"
        or rubric.get("fit_expression_grammar") == "grid_dsl"
        or rubric.get("fit_score_mode") == "discrete_exact"
    )


def _submission_label(project: Path, candidate: Path | None) -> str | None:
    if candidate is None:
        return None
    project = project.resolve()
    try:
        return str(candidate.resolve().relative_to(project))
    except ValueError:
        pass
    try:
        source = candidate.read_bytes()
    except OSError:
        return None
    digest = hashlib.sha256(source).hexdigest()
    suffix = candidate.suffix if candidate.suffix else ".py"
    destination = project / "workspace" / "submissions" / f"gated_{digest}{suffix}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        try:
            if destination.read_bytes() != source:
                return None
        except OSError:
            return None
    else:
        destination.write_bytes(source)
    return str(destination.relative_to(project))


def _write_cache(project: Path, records: list[dict[str, Any]]) -> None:
    path = _cache_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": _CACHE_SCHEMA,
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "records": records[:_MAX_CACHE_RECORDS],
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _candidate_digest(candidate: Path | None, gate_payload: dict[str, Any]) -> str:
    if candidate is not None:
        try:
            return hashlib.sha256(candidate.read_bytes()).hexdigest()
        except Exception:
            pass
    sha = gate_payload.get("gated_sha256")
    return str(sha or "unknown")


def _record_from_payload(name: str, digest: str, payload: dict[str, Any],
                         *, submission: str | None = None) -> "dict | None":
    gates = payload.get("gates") or {}
    if not isinstance(gates, dict):
        if isinstance(gates, list):
            gates = {
                str(g.get("name") or i): g
                for i, g in enumerate(gates)
                if isinstance(g, dict)
            }
        else:
            return None
    gate_values = [g for g in gates.values() if isinstance(g, dict)]
    if gate_values and all(_gate_passed(g) for g in gate_values):
        visible = gates.get("visible_replay_exact") or {}
        holdout = gates.get("holdout_rollout_exact") or {}
        diagnostics = visible.get("diagnostics") or {}
        holdout_witness = _holdout_witness_from_gate(holdout)
        return {
            "source_type": "full_survivor",
            "submission": submission or f"workspace/submissions/{name}",
            "sha": digest,
            "gate_score": float(payload.get("score") or 0.0),
            "passed_gates": len(gate_values),
            "total_gates": len(gate_values),
            "visible_exact_rows": int(diagnostics.get("exact_rows") or 0),
            "visible_checked_rows": int(diagnostics.get("checked_rows") or 0),
            "visible_wrong_rows": int(diagnostics.get("wrong_rows") or 0),
            "visible_wrong_cells": int(diagnostics.get("wrong_cell_count") or 0),
            "holdout_depth": int(holdout.get("value") or 0),
            "holdout_witness": holdout_witness,
            "counterexample_trace": _counterexample_trace_from_payload(
                payload,
                holdout_witness=holdout_witness,
            ),
        }
    rec = _near_miss_record(name, digest, {"score": payload.get("score"), "gates": gates})
    if rec is not None:
        rec["source_type"] = "deterministic_near_miss"
        if submission:
            rec["submission"] = submission
    return rec


def _attach_source_excerpt(rec: dict[str, Any], candidate: Path | None) -> None:
    if candidate is None:
        return
    try:
        text = candidate.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return
    if not text.strip():
        return
    rec["source_excerpt"] = text[:_MAX_SOURCE_EXCERPT_CHARS]
    rec["source_truncated"] = len(text) > _MAX_SOURCE_EXCERPT_CHARS


def _near_miss_record(name: str, digest: str, payload: dict) -> "dict | None":
    gates = payload.get("gates") or {}
    if not isinstance(gates, dict) or not gates:
        return None
    visible = gates.get("visible_replay_exact") or {}
    holdout = gates.get("holdout_rollout_exact") or {}
    diagnostics = visible.get("diagnostics") or {}
    holdout_witness = _holdout_witness_from_gate(holdout)
    passed = sum(1 for g in gates.values() if isinstance(g, dict) and g.get("pass"))
    total = sum(1 for g in gates.values() if isinstance(g, dict))
    if passed <= 0 and not diagnostics:
        return None
    return {
        "submission": f"workspace/submissions/{name}",
        "sha": digest,
        "gate_score": float(payload.get("score") or 0.0),
        "passed_gates": passed,
        "total_gates": total,
        "visible_exact_rows": int(diagnostics.get("exact_rows") or 0),
        "visible_checked_rows": int(diagnostics.get("checked_rows") or 0),
        "visible_wrong_rows": int(diagnostics.get("wrong_rows") or 0),
        "visible_wrong_cells": int(diagnostics.get("wrong_cell_count") or 0),
        "holdout_depth": int(holdout.get("value") or 0),
        "first_mismatch": str(diagnostics.get("first_mismatch") or visible.get("detail") or "")[:240],
        "mismatch_signature": diagnostics.get("first_mismatch_signature") if isinstance(diagnostics.get("first_mismatch_signature"), dict) else None,
        "mismatch_classes": diagnostics.get("mismatch_classes") if isinstance(diagnostics.get("mismatch_classes"), list) else [],
        "holdout_witness": holdout_witness,
        "counterexample_trace": _counterexample_trace_from_payload(
            payload,
            holdout_witness=holdout_witness,
        ),
    }


def _gate_passed(gate: dict) -> bool:
    return bool(gate.get("passed", gate.get("pass", False)))


def _record_rank_key(rec: dict) -> tuple:
    return (
        1 if rec.get("source_type") == "full_survivor" else 0,
        *_near_miss_sort_key(rec),
        str(rec.get("observed_at_utc") or ""),
    )


def _near_miss_sort_key(rec: dict) -> tuple:
    return (
        int(rec.get("visible_exact_rows") or 0),
        int(rec.get("holdout_depth") or 0),
        float(rec.get("gate_score") or 0.0),
        -int(rec.get("visible_wrong_cells") or 0),
    )


def _format_near_miss(rec: dict) -> str:
    checked = rec.get("visible_checked_rows") or "?"
    first = rec.get("first_mismatch") or "first mismatch unavailable"
    sig = _format_signature(rec.get("mismatch_signature"))
    sig_suffix = f", signature={sig}" if sig else ""
    classes = _format_mismatch_classes(rec.get("mismatch_classes"))
    classes_suffix = f", classes={classes}" if classes else ""
    witness = _format_holdout_witness(rec.get("holdout_witness"))
    if not witness:
        witness = _format_holdout_witness(_trace_holdout_witness(rec.get("counterexample_trace")))
    witness_suffix = f", holdout={witness}" if witness else ""
    return (
        f"near-miss: {rec['submission']} (sha {rec['sha']}), "
        f"visible {rec.get('visible_exact_rows', 0)}/{checked}, "
        f"wrong_rows={rec.get('visible_wrong_rows', 0)}, "
        f"wrong_cells={rec.get('visible_wrong_cells', 0)}, "
        f"holdout_depth={rec.get('holdout_depth', 0)}, "
        f"first={first}{sig_suffix}{classes_suffix}{witness_suffix}"
    )


def _format_full_survivor(rec: dict) -> str:
    checked = rec.get("visible_checked_rows") or "?"
    summary = str(rec.get("summary") or "").strip()
    summary_suffix = f", summary={summary}" if summary else ""
    label = str(rec.get("assistance_label") or "").strip()
    label_suffix = f", label={label}" if label else ""
    return (
        f"full-survivor: {rec.get('submission')} (sha {rec.get('sha')}), "
        f"gates={rec.get('passed_gates', 0)}/{rec.get('total_gates', 0)}, "
        f"score={rec.get('gate_score', 0)}, "
        f"visible {rec.get('visible_exact_rows', 0)}/{checked}, "
        f"wrong_cells={rec.get('visible_wrong_cells', 0)}, "
        f"holdout_depth={rec.get('holdout_depth', 0)}{label_suffix}{summary_suffix}"
    )


def _format_rejected_witness(rec: dict, reason: str) -> str:
    checked = rec.get("visible_checked_rows") or "?"
    first = rec.get("first_mismatch") or "first mismatch unavailable"
    return (
        f"rejected-witness: {rec.get('submission')} (sha {rec.get('sha')}), "
        f"visible {rec.get('visible_exact_rows', 0)}/{checked}, "
        f"wrong_cells={rec.get('visible_wrong_cells', 0)}, "
        f"holdout_depth={rec.get('holdout_depth', 0)}, "
        f"contract_reject={reason}, first={first}"
    )


def _holdout_witness_from_gate(holdout: Any) -> dict[str, Any] | None:
    if not isinstance(holdout, dict):
        return None
    witness = holdout.get("holdout_witness")
    return witness if isinstance(witness, dict) else None


def _counterexample_trace_from_payload(
    payload: dict[str, Any],
    *,
    holdout_witness: dict[str, Any] | None,
) -> dict[str, Any]:
    gates = payload.get("gates") or {}
    if isinstance(gates, list):
        gates = {
            str(g.get("name") or i): g
            for i, g in enumerate(gates)
            if isinstance(g, dict)
        }
    visible = gates.get("visible_replay_exact") if isinstance(gates, dict) else {}
    diagnostics = visible.get("diagnostics") if isinstance(visible, dict) else {}
    signature = diagnostics.get("first_mismatch_signature")
    return {
        "schema": "ztare-counterexample-trace-v1",
        "quotient": "first_visible_replay_mismatch",
        "coordinate_contract": {
            "cell_basis": "row_col",
            "bbox_basis": "row_min_col_min_row_max_col_max",
        },
        "failed_gates": [
            f"{g.get('name', name)}: {g.get('value', '?')}"
            for name, g in (gates.items() if isinstance(gates, dict) else [])
            if isinstance(g, dict) and not _gate_passed(g)
        ],
        "gated_file": payload.get("gated_file"),
        "gated_sha256": payload.get("gated_sha256"),
        "checked_rows": diagnostics.get("checked_rows"),
        "exact_rows": diagnostics.get("exact_rows"),
        "wrong_rows": diagnostics.get("wrong_rows"),
        "wrong_cell_count": diagnostics.get("wrong_cell_count"),
        "evidence_ref": diagnostics.get("evidence_ref") or "",
        "first_mismatch": diagnostics.get("first_mismatch") or "",
        "first_mismatch_signature": signature if isinstance(signature, dict) else {},
        "mismatch_classes": diagnostics.get("mismatch_classes")
        if isinstance(diagnostics.get("mismatch_classes"), list) else [],
        "holdout_witness": holdout_witness or {},
    }


def _trace_holdout_witness(trace: Any) -> dict[str, Any] | None:
    if not isinstance(trace, dict):
        return None
    witness = trace.get("holdout_witness")
    return witness if isinstance(witness, dict) else None


def _fallback_holdout_witness(project: Path) -> dict[str, Any] | None:
    path = project / "workspace" / "latest_level_transfer_probe.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    rows = payload.get("local_rows")
    if not isinstance(rows, list):
        return None
    for row in rows:
        if not isinstance(row, dict):
            continue
        action = row.get("action")
        witnesses = row.get("component_patch_witnesses")
        if not isinstance(witnesses, list):
            continue
        for witness in witnesses:
            if not isinstance(witness, dict):
                continue
            diff_cells = witness.get("diff_cells")
            if not isinstance(diff_cells, list) or not diff_cells:
                continue
            divergent_cells = [
                {
                    "row": cell.get("row"),
                    "col": cell.get("col"),
                    "predicted": cell.get("predicted"),
                    "actual": cell.get("observed"),
                }
                for cell in diff_cells
                if isinstance(cell, dict)
            ]
            if not divergent_cells:
                continue
            t = row.get("t")
            if t is None:
                t = witness.get("t", 19)
            return {
                "step_index": 0,
                "t": t,
                "action": action,
                "entry_context_note": f"holdout starts mid-episode at its first row t={t}",
                "divergent_cells": divergent_cells,
            }
    return None


def _format_signature(sig: Any) -> str:
    if not isinstance(sig, dict):
        return ""
    hints = sig.get("color_displacement_hints")
    if not isinstance(hints, list) or not hints:
        return ""
    non_background = [
        hint for hint in hints
        if isinstance(hint, dict) and hint.get("color") != 0
    ]
    if non_background:
        hints = non_background
    parts = []
    for hint in hints[:3]:
        if not isinstance(hint, dict):
            continue
        delta = hint.get("actual_minus_predicted")
        if not isinstance(delta, list) or len(delta) != 2:
            continue
        parts.append(
            f"color {hint.get('color')} actual=predicted+({delta[0]},{delta[1]}) "
            f"over {hint.get('count')} cells"
        )
    return "; ".join(parts)


def _format_mismatch_classes(classes: Any) -> str:
    if not isinstance(classes, list):
        return ""
    parts = []
    for row in classes[:3]:
        if not isinstance(row, dict):
            continue
        sig = row.get("signature")
        shape = ""
        if isinstance(sig, dict):
            bbox = sig.get("bbox")
            pairs = sig.get("pair_counts")
            pair_s = ""
            if isinstance(pairs, list) and pairs:
                p0 = pairs[0]
                if isinstance(p0, dict):
                    pair_s = (
                        f" {p0.get('predicted')}->{p0.get('real')}"
                        f"x{p0.get('count')}"
                    )
            shape = f"bbox={bbox}{pair_s}" if bbox else pair_s.strip()
        loc = f"row={row.get('first_row')} t={row.get('t')} a={row.get('action')}"
        parts.append(f"n={row.get('count')} {loc} {shape}".strip())
    return " | ".join(parts)


def _format_holdout_witness(witness: Any) -> str:
    if not isinstance(witness, dict) or not witness:
        return ""
    cells = witness.get("divergent_cells")
    if isinstance(cells, list):
        cell_terms = []
        for cell in cells[:4]:
            if not isinstance(cell, dict):
                continue
            cell_terms.append(
                f"(row={cell.get('row')},col={cell.get('col')}) "
                f"predicted {cell.get('predicted')} actual {cell.get('actual')}"
            )
        cells_text = "; ".join(cell_terms)
    else:
        cells_text = ""
    note = str(witness.get("entry_context_note") or "").strip()
    note_suffix = f" note={note}" if note else ""
    return (
        f"step={witness.get('step_index')} t={witness.get('t')} action={witness.get('action')}"
        f"{note_suffix}"
        f"{('; ' + cells_text) if cells_text else ''}"
    )


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _root_artifact_notice(project: Path, rec: dict) -> str:
    source = str(rec.get("source_excerpt") or "").strip()
    if not source:
        return ""
    lines = []
    root_model = project / "test_model.py"
    try:
        root_bytes = root_model.read_bytes()
    except Exception:
        root_bytes = b""
    if root_bytes:
        root_sha = hashlib.sha256(root_bytes).hexdigest()[:12]
        if root_sha != str(rec.get("sha") or "")[:12]:
            lines.append(
                f"- Lower-authority root artifact: `test_model.py` currently has sha {root_sha}, "
                f"not the patch-base sha {rec.get('sha')}. Treat root `test_model.py` as "
                "workspace residue unless it is explicitly rewritten from this patch base."
            )
    current = _read_text(project / "current_iteration.md")
    anchor = source[:240]
    submission = str(rec.get("submission") or "")
    if current.strip() and anchor not in current and submission not in current:
        lines.append(
            "- Lower-authority prose artifact: `current_iteration.md` does not contain the "
            "patch-base carrier. If it conflicts with the deterministic candidate memory, "
            "follow the candidate memory."
        )
    if not lines:
        return ""
    return "\nArtifact authority notice:\n" + "\n".join(lines) + "\n"


def _inline_near_miss_source(ctx: BriefingContext) -> bool:
    rubric = ctx.rubric or {}
    if "briefing_inline_near_miss_source" in rubric:
        return bool(rubric.get("briefing_inline_near_miss_source"))
    return not (
        rubric.get("substrate_class") == "interactive_environment"
        or rubric.get("fit_expression_grammar") == "grid_dsl"
    )


def _format_patch_base(
    project: Path,
    rec: dict,
    *,
    inline_source: bool = True,
    mode: str = "mandatory",
) -> str:
    source = str(rec.get("source_excerpt") or "")[:_MAX_SOURCE_EXCERPT_CHARS]
    if inline_source and not source.strip():
        return ""
    suffix = "\n# ... source excerpt truncated ..." if rec.get("source_truncated") or len(str(rec.get("source_excerpt") or "")) > len(source) else ""
    sig = _format_signature(rec.get("mismatch_signature"))
    sig_line = f"\nFirst-mismatch signature: {sig}\n" if sig else ""
    classes = _format_mismatch_classes(rec.get("mismatch_classes"))
    classes_line = f"\nMismatch quotient classes: {classes}\n" if classes else ""
    authority_notice = _root_artifact_notice(project, rec)
    if mode == "diagnostic":
        title = "Diagnostic Patch Base"
        directive = (
            "Use this carrier as a diagnostic baseline for replay regressions. "
            "If a skill-acquisition card that blocks this run lane names a newer "
            "non-replay gate, "
            "that card is the work order; mutate this carrier only when it helps "
            "satisfy that card's required_next_gate."
        )
    else:
        title = "Mandatory Patch Base"
        directive = (
            "Use this carrier as the patch base. A new mechanism must explicitly "
            "explain why it beats this exact program on the first mismatch; "
            "otherwise edit this program."
        )
    header = (
        f"\n### {title}\n"
        f"Best executable near-miss: {rec.get('submission')} "
        f"(visible {rec.get('visible_exact_rows', 0)}/{rec.get('visible_checked_rows') or '?'}, "
        f"wrong_cells={rec.get('visible_wrong_cells', 0)}). "
        f"{directive}"
        f"{sig_line}{classes_line}\n"
        f"{authority_notice}"
    )
    if not inline_source:
        submission = str(rec.get("submission") or "")
        sha = _artifact_full_sha(project, submission) or str(rec.get("sha") or "").strip()
        patch_base_decl = patch_base_declaration(submission, sha)
        return (
            header
            + f"Patch base file: `{rec.get('submission')}`\n"
            + "Patch-base composition surface: use this declaration and define "
            f"only the minimal `{patch_delta_signature()}`. "
            "The gate loads the base by hash; do not inspect, copy, edit, or "
            "reconstruct the carrier from workspace prose.\n"
            f"`{patch_base_decl}`\n"
        )
    return header + "```python\n" + f"{source.rstrip()}{suffix}\n" + "```\n"


def _patch_base_mode(project: Path) -> "tuple[str, str]":
    """Demote replay near-misses when a blocking skill card owns the next gate.

    Candidate memory is replay-local. When the Strategy Office has an open
    card whose required gate is not a replay-diagnostics gate, forcing the
    mutator to edit the replay near-miss can route attention away from the
    active counterexample. The near-miss remains useful evidence, but it stops
    being the work-order carrier.

    Returns ``(mode, note)``. ``mode`` is "mandatory" or "diagnostic". A read
    failure on the office ledger means we do NOT know whether an open card owns
    a non-replay gate — so we must NOT assert the stronger "mandatory" verdict.
    We degrade to "diagnostic" and return a note so the section can banner the
    unreadable ledger rather than silently over-claiming the patch base.
    """
    ledger = project / "workspace" / "strategy_experiments.jsonl"
    if not ledger.exists():
        return "mandatory", ""
    try:
        from ztare.common.strategy_card_roles import active_strategy_cards

        cards = active_strategy_cards(ledger)
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        return (
            "diagnostic",
            f"strategy_experiments.jsonl unreadable ({type(exc).__name__}: {exc}); "
            "patch base degraded from mandatory to diagnostic because open-card "
            "ownership of the next gate could not be determined",
        )
    from ztare.common.strategy_card_roles import blocking_strategy_cards

    for card in blocking_strategy_cards(cards, project_dir=project):
        plan = card.get("action_plan") if isinstance(card, dict) else None
        if not isinstance(plan, dict):
            continue
        gate = plan.get("required_next_gate")
        command = str((gate or {}).get("command") or "")
        if command and "replay" not in command:
            return "diagnostic", ""
    return "mandatory", ""


def _format_full_survivor_source(project: Path, rec: dict) -> str:
    source = str(rec.get("source_excerpt") or "")[:_MAX_SOURCE_EXCERPT_CHARS]
    if not source.strip():
        return ""
    suffix = "\n# ... source excerpt truncated ..." if rec.get("source_truncated") or len(str(rec.get("source_excerpt") or "")) > len(source) else ""
    authority_notice = _root_artifact_notice(project, rec)
    return (
        "\n### Mandatory Deterministic Baseline\n"
        f"Best executable full survivor: {rec.get('submission')} "
        f"(visible {rec.get('visible_exact_rows', 0)}/{rec.get('visible_checked_rows') or '?'}, "
        f"holdout_depth={rec.get('holdout_depth', 0)}, "
        f"wrong_cells={rec.get('visible_wrong_cells', 0)}). "
        "Do not mutate a weaker near-miss unless this survivor is explicitly refuted by "
        "a newer gate receipt or by sealed-environment planning evidence.\n"
        f"{authority_notice}"
        "```python\n"
        f"{source.rstrip()}{suffix}\n"
        "```\n"
    )
