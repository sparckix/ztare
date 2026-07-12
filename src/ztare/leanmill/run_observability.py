"""Per-run LeanMill observability bundle.

This is a read-only join over the existing run ledgers. It does not execute
Lean, call models, mutate proof state, or decide proof credit. Its job is to
make the recurring integration failures visible from one object.
"""
from __future__ import annotations

from collections import Counter
import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping


REPO = Path(__file__).resolve().parents[3]
QUERIES = REPO / "analytics" / "public" / "queries"
DEFAULT_ATTEMPTS_DB = QUERIES / "solver_lane_attempts.db"
DEFAULT_VERDICTS = QUERIES / "leanmill_verdicts.jsonl"
DEFAULT_BANK_ATTEMPTS = QUERIES / "solver_lane_bank_attempts.jsonl"
DEFAULT_FORMALIZE_ATTEMPTS = QUERIES / "formalize_attempts.jsonl"
DEFAULT_NOTES_TRACE = QUERIES / "leanmill_notes_writeback_trace.jsonl"
DEFAULT_COT_TRACES = QUERIES / "cot_traces.jsonl"
DEFAULT_PROOF_CACHE = QUERIES / "solver_lane_proof_cache.jsonl"
DEFAULT_NO_GOOD_STORE = QUERIES / "solver_lane_no_good_store.jsonl"
DEFAULT_FAITHFULNESS_STORE = QUERIES / "solver_lane_faithfulness_store.jsonl"
DEFAULT_DECOMPOSITION_CACHE = QUERIES / "decomposition_cache.jsonl"
DEFAULT_AXIOM_PACKS = QUERIES / "axiom_pack_candidates.jsonl"


def _read_json_object(
    path: str | Path,
    *,
    warning_key: str,
    warnings: list[str],
) -> dict[str, Any]:
    """Read one observability artifact without treating malformed input as state."""

    candidate = Path(path)
    if not candidate.is_file():
        return {}
    try:
        value = json.loads(candidate.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        warnings.append(f"invalid_{warning_key}")
        return {}
    if not isinstance(value, dict):
        warnings.append(f"invalid_{warning_key}")
        return {}
    return value


def _read_jsonl_objects(
    path: str | Path,
    *,
    warning_key: str,
    warnings: list[str],
) -> list[dict[str, Any]]:
    """Read a ledger without constructing any writer or recovery object."""

    candidate = Path(path)
    if not candidate.is_file():
        return []
    try:
        lines = candidate.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        warnings.append(f"unreadable_{warning_key}")
        return []
    rows: list[dict[str, Any]] = []
    malformed = False
    for line in lines:
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            malformed = True
            continue
        if isinstance(value, dict):
            rows.append(value)
        else:
            malformed = True
    if malformed:
        warnings.append(f"invalid_{warning_key}_row")
    return rows


def _read_jsonl(path: str | Path | None, *, limit: int = 20000) -> list[dict[str, Any]]:
    if not path:
        return []
    p = Path(path)
    if not p.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:  # noqa: BLE001
        return []
    for line in lines[-max(1, int(limit)):]:
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _nested_statement_target(row: dict[str, Any]) -> str:
    sid = row.get("statement_id")
    if isinstance(sid, dict) and sid.get("target_name"):
        return str(sid.get("target_name") or "")
    verdict = row.get("verdict")
    if isinstance(verdict, dict):
        sid = verdict.get("statement_id")
        if isinstance(sid, dict) and sid.get("target_name"):
            return str(sid.get("target_name") or "")
    return ""


def _top(counter: Counter, n: int = 8) -> dict[str, int]:
    return {str(k): int(v) for k, v in counter.most_common(n)}


def _has_statement_id(row: dict[str, Any]) -> bool:
    sid = row.get("statement_id")
    if isinstance(sid, dict) and any(sid.values()):
        return True
    verdict = row.get("verdict")
    if isinstance(verdict, dict):
        sid = verdict.get("statement_id")
        return isinstance(sid, dict) and any(sid.values())
    return False


def _statement_payload(row: dict[str, Any]) -> str:
    for key in ("statement", "goal", "lean_statement", "closed_prop", "target_statement"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _metadata_debt(rows: list[dict[str, Any]]) -> dict[str, Any]:
    missing = [r for r in rows if not _has_statement_id(r)]
    backfillable = [r for r in missing if _statement_payload(r)]
    examples = []
    for row in missing[:5]:
        examples.append({
            "schema": str(row.get("schema") or "legacy"),
            "key": str(row.get("key") or "")[:80],
            "source": str(row.get("source") or "")[:80],
            "kind": str(row.get("kind") or row.get("failure_class") or "")[:80],
            "has_statement_payload": bool(_statement_payload(row)),
        })
    return {
        "missing_statement_id": len(missing),
        "backfillable_statement_id": len(backfillable),
        "missing_statement_payload": len(missing) - len(backfillable),
        "examples": examples,
    }


def _authority(row: dict[str, Any], default: str = "") -> str:
    val = row.get("cache_authority") or row.get("authority") or default
    return str(val or "")


def _proof_credit_eligible(row: dict[str, Any]) -> bool:
    return row.get("proof_credit_eligible") is True


def _staged_index_candidates(
    *,
    lean_root: str | Path | None,
    staged_index_path: str | Path | None,
    limit: int = 32,
) -> list[Path]:
    if staged_index_path:
        return [Path(staged_index_path)]
    if not lean_root:
        return []
    root = Path(lean_root)
    scratch = root / ".solver_scratch"
    candidates: list[Path] = []
    direct = scratch / "checkpoints" / "_staged_index.jsonl"
    if direct.exists():
        candidates.append(direct)
    if scratch.exists():
        candidates.extend(sorted(
            scratch.glob("*/checkpoints/_staged_index.jsonl"),
            key=lambda p: p.stat().st_mtime if p.exists() else 0,
            reverse=True,
        )[:max(0, limit - len(candidates))])
    seen: set[str] = set()
    uniq: list[Path] = []
    for path in candidates:
        key = str(path.resolve()) if path.exists() else str(path)
        if key not in seen:
            seen.add(key)
            uniq.append(path)
    return uniq


def _run_tag_rows(rows: list[dict[str, Any]], run_tag: str) -> int:
    return sum(1 for r in rows if run_tag and str(r.get("run_tag") or "") == run_tag)


def _summarize_proof_cache(path: str | Path, run_tag: str) -> dict[str, Any]:
    rows = _read_jsonl(path)
    metadata_debt = _metadata_debt(rows)
    import re
    from ztare.leanmill.solver.proof_cache import _RUN_LOCAL_DEP_RE
    dependency_rows = 0
    orphaned_environment_rows = 0
    malformed_payload_rows = 0
    for row in rows:
        raw_proof = str(row.get("proof") or "")
        malformed_payload_rows += int(raw_proof.lstrip().startswith((":=", "```")))
        proof = re.sub(r"(?m)^\s*#print\s+axioms\b.*$", "", raw_proof)
        dependencies = set(_RUN_LOCAL_DEP_RE.findall(proof))
        if dependencies:
            dependency_rows += 1
            source = str(row.get("statement") or "")
            orphaned_environment_rows += int(any(name not in source for name in dependencies))
    return {
        "total": len(rows),
        "run_tag_rows": _run_tag_rows(rows, run_tag),
        "scope": "cross_run_store",
        "by_schema": _top(Counter(str(r.get("schema") or "legacy") for r in rows)),
        "by_authority": _top(Counter(_authority(r, "proof_credit") for r in rows)),
        "proof_credit_eligible": sum(1 for r in rows if _proof_credit_eligible(r)),
        "with_statement_id": sum(1 for r in rows if _has_statement_id(r)),
        "missing_statement_id": sum(1 for r in rows if not _has_statement_id(r)),
        "expr_key_rows": sum(1 for r in rows if str(r.get("key") or "").startswith("H:")),
        "text_key_rows": sum(1 for r in rows if r.get("key") and not str(r.get("key") or "").startswith("H:")),
        "by_source": _top(Counter(str(r.get("source") or "") for r in rows if r.get("source"))),
        "environment_bound_rows": sum(1 for r in rows if r.get("environment_hash")),
        "legacy_environment_rows": sum(1 for r in rows if not r.get("environment_hash")),
        "dependency_bearing_rows": dependency_rows,
        "orphaned_environment_rows": orphaned_environment_rows,
        "malformed_payload_rows": malformed_payload_rows,
        "phase": "proof_credit_reuse",
        "environment": "kernel_checked_then_reverify_on_use",
        "metadata_debt": metadata_debt,
    }


def _summarize_staged_reuse(
    *,
    lean_root: str | Path | None,
    staged_index_path: str | Path | None,
    run_tag: str,
) -> dict[str, Any]:
    index_paths = _staged_index_candidates(lean_root=lean_root, staged_index_path=staged_index_path)
    rows: list[dict[str, Any]] = []
    missing_body = 0
    active = 0
    for index in index_paths:
        scoped = _read_jsonl(index)
        for row in scoped:
            rr = dict(row)
            rr["_index_path"] = str(index)
            rows.append(rr)
            body = str(row.get("body_path") or "")
            if not body:
                continue
            body_path = Path(body)
            if not body_path.is_absolute():
                body_path = index.parent / body
            if body_path.exists():
                active += 1
            else:
                missing_body += 1
    return {
        "total": len(rows),
        "run_tag_rows": _run_tag_rows(rows, run_tag),
        "scope": "explicit_index" if staged_index_path else "lean_root_scan",
        "active_rows": active,
        "missing_body_rows": missing_body,
        "index_paths": [str(p) for p in index_paths],
        "by_schema": _top(Counter(str(r.get("schema") or "legacy") for r in rows)),
        "by_authority": _top(Counter(_authority(r, "affordance") for r in rows)),
        "proof_credit_eligible": sum(1 for r in rows if _proof_credit_eligible(r)),
        "with_statement_id": sum(1 for r in rows if _has_statement_id(r)),
        "by_target": _top(Counter(str(r.get("target") or r.get("target_name") or "") for r in rows if r.get("target") or r.get("target_name"))),
        "phase": "near_complete_seed",
        "environment": "leaf_final_verify_required",
    }


def _summarize_no_good(path: str | Path, run_tag: str) -> dict[str, Any]:
    rows = _read_jsonl(path)
    metadata_debt = _metadata_debt(rows)
    return {
        "total": len(rows),
        "run_tag_rows": _run_tag_rows(rows, run_tag),
        "scope": "cross_run_store",
        "by_failure_class": _top(Counter(str(r.get("failure_class") or "") for r in rows)),
        "statement_false": sum(1 for r in rows if str(r.get("failure_class") or "") == "statement_false"),
        "with_statement_id": sum(1 for r in rows if _has_statement_id(r)),
        "missing_statement_id": sum(1 for r in rows if not _has_statement_id(r)),
        "by_source": _top(Counter(str(r.get("source") or "") for r in rows if r.get("source"))),
        "phase": "refutation_memory",
        "environment": "kernel_confirmed_no_good",
        "metadata_debt": metadata_debt,
    }


def _summarize_faithfulness(path: str | Path, run_tag: str) -> dict[str, Any]:
    rows = _read_jsonl(path)
    metadata_debt = _metadata_debt(rows)
    return {
        "total": len(rows),
        "run_tag_rows": _run_tag_rows(rows, run_tag),
        "scope": "cross_run_store",
        "by_kind": _top(Counter(str(r.get("kind") or r.get("verdict") or "") for r in rows)),
        "with_statement_id": sum(1 for r in rows if _has_statement_id(r)),
        "missing_statement_id": sum(1 for r in rows if not _has_statement_id(r)),
        "by_source": _top(Counter(str(r.get("source") or "") for r in rows if r.get("source"))),
        "phase": "formalization_firewall",
        "environment": "substrate_faithfulness_check",
        "metadata_debt": metadata_debt,
    }


def _summarize_decomposition_cache(path: str | Path, run_tag: str) -> dict[str, Any]:
    rows = _read_jsonl(path)
    lemma_counts: list[int] = []
    for row in rows:
        lemmas = row.get("lemmas")
        if isinstance(lemmas, list):
            lemma_counts.append(len(lemmas))
    avg_lemmas = round(sum(lemma_counts) / len(lemma_counts), 2) if lemma_counts else 0.0
    return {
        "total": len(rows),
        "run_tag_rows": _run_tag_rows(rows, run_tag),
        "scope": "cross_run_store",
        "with_statement_id": sum(1 for r in rows if _has_statement_id(r)),
        "avg_lemmas": avg_lemmas,
        "phase": "planner_reuse",
        "environment": "child_proofs_reverify",
        "by_schema": _top(Counter(str(r.get("schema") or "legacy") for r in rows)),
    }


def _summarize_axiom_packs(path: str | Path, run_tag: str) -> dict[str, Any]:
    rows = _read_jsonl(path)
    packs: list[dict[str, Any]] = []
    warnings: list[str] = []
    for row in rows:
        pack = row.get("pack") if isinstance(row.get("pack"), dict) else row
        if isinstance(pack, dict):
            packs.append(pack)
        if row.get("proof_credit_eligible") is True or pack.get("proof_credit_eligible") is True:
            warnings.append("axiom_pack_grants_proof_credit")
        if row.get("theorem_campaign_admissible") is True or pack.get("theorem_campaign_admissible") is True:
            warnings.append("axiom_pack_theorem_admissible_without_ratification")
    stress_rows = [r.get("stress") for r in rows if isinstance(r.get("stress"), dict)]
    cheap_ok = 0
    yield_completed = 0
    for stress in stress_rows:
        route = stress.get("compute_route") if isinstance(stress.get("compute_route"), dict) else {}
        if route.get("cheap_filter_ok") is True:
            cheap_ok += 1
        if route.get("yield_test_completed") is True:
            yield_completed += 1
    return {
        "schema": "leanmill.axiom_pack_observability.v1",
        "total": len(rows),
        "run_tag_rows": _run_tag_rows(rows, run_tag),
        "scope": "quarantined_research_lane",
        "by_status": _top(Counter(str(p.get("promotion_status") or "unknown") for p in packs)),
        "by_domain": _top(Counter(str(p.get("domain") or "") for p in packs if p.get("domain"))),
        "cheap_filter_ok": cheap_ok,
        "yield_test_completed": yield_completed,
        "proof_credit_eligible_rows": sum(1 for p in packs if p.get("proof_credit_eligible") is True),
        "theorem_campaign_admissible_rows": sum(1 for p in packs if p.get("theorem_campaign_admissible") is True),
        "candidate_axiom_count": sum(len(p.get("candidate_axioms") or []) for p in packs),
        "warnings": sorted(set(warnings)),
        "phase": "axiom_pack_discovery",
        "environment": "quarantined_no_proof_credit",
    }


def _identity_match(expected: Any, observed: Any) -> bool | None:
    if not str(expected or "") or not str(observed or ""):
        return None
    return str(expected) == str(observed)


def _frontier_budget_projection(
    directory: Path,
    *,
    warnings: list[str],
) -> dict[str, Any]:
    """Reduce durable budget bytes without instantiating the mutable ledger."""

    row = _read_json_object(
        directory / "budget.json", warning_key="frontier_budget", warnings=warnings
    )
    if not row:
        return {"status": "missing"}
    raw_caps = row.get("hard_caps")
    if not isinstance(raw_caps, Mapping):
        warnings.append("invalid_frontier_budget_caps")
        raw_caps = {}
    hard_caps: dict[str, int] = {}
    for key, value in raw_caps.items():
        try:
            hard_caps[str(key)] = max(0, int(value))
        except (TypeError, ValueError):
            warnings.append("invalid_frontier_budget_caps")
    ledger_path = directory / "budget.events.jsonl"
    rows = _read_jsonl_objects(
        ledger_path, warning_key="frontier_budget_ledger", warnings=warnings
    )
    reservations: dict[str, dict[str, Any]] = {}
    usage: Counter[str] = Counter()
    phase_usage: dict[str, Counter[str]] = {}
    digest_mismatches = 0
    elapsed_ms: int | None = None
    wall_clock_state = "not_recorded"
    user_stop = False
    for event in rows:
        event_digest = str(event.get("budget_digest") or "")
        if event_digest and event_digest != str(row.get("budget_digest") or ""):
            digest_mismatches += 1
        event_type = str(event.get("event_type") or "")
        if event_type == "resources_reserved":
            reservation_id = str(event.get("reservation_id") or "")
            if reservation_id:
                reservations[reservation_id] = event
        elif event_type in {"reservation_committed", "reservation_released"}:
            reservation_id = str(event.get("reservation_id") or "")
            reservation = reservations.pop(reservation_id, None)
            if reservation is None:
                warnings.append("frontier_budget_orphaned_reservation_completion")
                continue
            if event_type != "reservation_committed":
                continue
            phase = str(reservation.get("phase") or "unknown")
            phase_totals = phase_usage.setdefault(phase, Counter())
            actual = event.get("actual_resources")
            if not isinstance(actual, Mapping):
                warnings.append("invalid_frontier_budget_commit")
                continue
            for key, value in actual.items():
                try:
                    amount = int(value)
                except (TypeError, ValueError):
                    warnings.append("invalid_frontier_budget_commit")
                    continue
                if amount < 0 or str(key) not in hard_caps:
                    warnings.append("invalid_frontier_budget_commit")
                    continue
                usage[str(key)] += amount
                phase_totals[str(key)] += amount
        elif event_type == "wall_clock_frozen":
            try:
                elapsed_ms = max(0, int(event.get("elapsed_ms")))
                wall_clock_state = "frozen"
            except (TypeError, ValueError):
                warnings.append("invalid_frontier_budget_wall_clock")
        elif event_type == "wall_clock_resumed":
            elapsed_ms = None
            wall_clock_state = "active_or_unmeasured"
        elif event_type in {"user_stop_requested", "operator_stop_requested"}:
            user_stop = True
    if digest_mismatches:
        warnings.append("frontier_budget_ledger_digest_mismatch")
    reserved: Counter[str] = Counter()
    outstanding_actions: list[dict[str, Any]] = []
    for reservation in reservations.values():
        resources: dict[str, int] = {}
        raw_resources = reservation.get("resources")
        if isinstance(raw_resources, Mapping):
            for key, value in raw_resources.items():
                try:
                    amount = int(value)
                except (TypeError, ValueError):
                    continue
                if amount > 0 and str(key) in hard_caps:
                    resources[str(key)] = amount
                    reserved[str(key)] += amount
        outstanding_actions.append(
            {
                "action_id": str(reservation.get("action_id") or ""),
                "phase": str(reservation.get("phase") or ""),
                "resources": resources,
                "reserved_at_ms": reservation.get("at_ms"),
            }
        )
    stop = _read_json_object(
        directory / "budget_stop_receipt.json",
        warning_key="frontier_budget_stop_receipt",
        warnings=warnings,
    )
    stop_digest_match = _identity_match(row.get("budget_digest"), stop.get("budget_digest"))
    if stop and stop_digest_match is False:
        warnings.append("frontier_budget_stop_digest_mismatch")
    return {
        "status": "available",
        "preset": str(row.get("preset") or ""),
        "budget_digest": str(row.get("budget_digest") or ""),
        "wall_clock_s": row.get("wall_clock_s"),
        "allocation_policy": str(row.get("allocation_policy") or ""),
        "hard_caps": hard_caps,
        "stop_rule": dict(row.get("stop_rule") or {}),
        "ledger": {
            "status": "available" if ledger_path.is_file() else "missing",
            "event_count": len(rows),
            "usage": {key: int(usage[key]) for key in sorted(hard_caps)},
            "phase_usage": {
                phase: {key: int(value) for key, value in sorted(totals.items()) if value}
                for phase, totals in sorted(phase_usage.items())
                if any(totals.values())
            },
            "remaining_hard_caps": {
                key: max(0, cap - int(usage[key]) - int(reserved[key]))
                for key, cap in sorted(hard_caps.items())
            },
            "outstanding_reservation_count": len(outstanding_actions),
            "outstanding_actions": sorted(
                outstanding_actions,
                key=lambda item: (str(item["reserved_at_ms"] or ""), item["action_id"]),
            ),
            "wall_clock_state": wall_clock_state,
            "elapsed_ms_when_frozen": elapsed_ms,
            "user_stop_requested": user_stop,
        },
        "stop_receipt": {
            "status": "recorded" if stop else "absent",
            "reason": str(stop.get("reason") or "") if stop else "",
            "budget_digest_matches_contract": stop_digest_match,
        },
    }


def _frontier_journal_projection(
    directory: Path,
    *,
    warnings: list[str],
) -> dict[str, Any]:
    """Summarize root and sealed-lineage journals through their replay parser."""

    from ztare.leanmill.theory_campaign_journal import TheoryCampaignJournal

    paths = [("root", directory / "events.jsonl")]
    paths.extend(
        (f"lineage:{path.stem}", path)
        for path in sorted((directory / "lineage_journals").glob("*.events.jsonl"))
    )
    rows: list[tuple[str, list[Any]]] = []
    invalid = False
    for label, path in paths:
        if not path.is_file():
            continue
        try:
            events = list(TheoryCampaignJournal(path).replay())
        except (OSError, ValueError):
            warnings.append(f"invalid_frontier_journal:{label}")
            invalid = True
            continue
        rows.append((label, events))
    events = [event for _label, journal_rows in rows for event in journal_rows]
    event_types = Counter(event.event_type for event in events)
    evidence_statuses = Counter(event.evidence_status for event in events)
    finalist_subjects = {
        subject
        for event in events
        if event.event_type == "finalist_frozen"
        for subject in event.subject_ids
    }
    return {
        "status": "invalid" if invalid else "available" if rows else "not_started",
        "event_count": len(events),
        "latest_epoch": max((event.epoch for event in events), default=None),
        "by_event_type": _top(event_types),
        "by_evidence_status": _top(evidence_statuses),
        "finalist_subject_count": len(finalist_subjects),
        "campaign_ids": sorted({event.campaign_id for event in events}),
        "context_hashes": sorted({event.context_hash for event in events}),
        "root_event_count": next((len(items) for label, items in rows if label == "root"), 0),
        "lineage_journals": [
            {
                "journal_ref": label.removeprefix("lineage:"),
                "event_count": len(items),
                "latest_epoch": max((event.epoch for event in items), default=None),
            }
            for label, items in rows
            if label != "root"
        ],
    }


def _frontier_lineage_projection(
    blueprint: Mapping[str, Any], run: Mapping[str, Any], journal: Mapping[str, Any]
) -> dict[str, Any]:
    contract = blueprint.get("navigator_contract")
    contract = contract if isinstance(contract, Mapping) else {}
    try:
        configured_count = max(1, int(contract.get("host_isolated_lineages", 1)))
    except (TypeError, ValueError):
        configured_count = 1
    navigation = run.get("navigation")
    navigation = navigation if isinstance(navigation, Mapping) else {}
    lineage_ids: set[str] = set()
    for row in navigation.get("lineages") or ():
        if isinstance(row, Mapping) and str(row.get("lineage_id") or ""):
            lineage_ids.add(str(row["lineage_id"]))
    for finalist in navigation.get("finalists") or ():
        if not isinstance(finalist, Mapping):
            continue
        program = finalist.get("theory_program")
        if isinstance(program, Mapping) and str(program.get("lineage_id") or ""):
            lineage_ids.add(str(program["lineage_id"]))
    isolation = navigation.get("isolation_receipt")
    isolation = isolation if isinstance(isolation, Mapping) else {}
    for lineage_id in isolation.get("lineage_ids") or ():
        if str(lineage_id):
            lineage_ids.add(str(lineage_id))
    journals = journal.get("lineage_journals")
    journal_count = len(journals) if isinstance(journals, list) else 0
    return {
        "strategy": "host_isolated" if configured_count > 1 else "single",
        "configured_count": configured_count,
        "observed_lineage_count": len(lineage_ids),
        "lineage_journal_count": journal_count,
        "isolation_receipt_present": bool(isolation),
        "finalist_count": len(navigation.get("finalists") or ()),
    }


def _frontier_ownership_projection(
    directory: Path,
    run: Mapping[str, Any],
    campaign_manifest: Mapping[str, Any],
    *,
    warnings: list[str],
) -> dict[str, Any]:
    """Expose a derived heartbeat view without granting it lease authority."""

    lease = _read_json_object(
        directory / "lease.json", warning_key="frontier_lease", warnings=warnings
    )
    owner = ""
    work_id = ""
    lease_until: Any = None
    heartbeat: Any = None
    source = ""
    for label, row in (("lease", lease), ("run", run), ("campaign_manifest", campaign_manifest)):
        if not isinstance(row, Mapping):
            continue
        candidate = row.get("owner") or row.get("owner_id") or row.get("claimed_by") or row.get("worker_id")
        if candidate and not owner:
            owner, source = str(candidate), label
        candidate_work_id = row.get("work_id") or row.get("claimed_work_id") or row.get("lease_id")
        if candidate_work_id and not work_id:
            work_id = str(candidate_work_id)
        if lease_until is None and row.get("lease_until") is not None:
            lease_until = row.get("lease_until")
        if heartbeat is None:
            heartbeat = (
                row.get("heartbeat_at")
                or row.get("heartbeat_ms")
                or row.get("last_heartbeat")
                or row.get("heartbeat")
            )
    lease_state = ""
    if lease:
        if lease.get("released") is True:
            lease_state = "released"
        elif lease.get("stale") is True:
            lease_state = "stale"
        else:
            lease_state = str(
                lease.get("lease_state") or lease.get("state") or lease.get("status") or "recorded"
            )
    return {
        "status": "observational" if owner or lease_until is not None or heartbeat is not None else "unavailable",
        "authority": "derived_heartbeat_non_authoritative" if lease else "attempt_metadata_non_authoritative",
        "owner": owner,
        "work_id": work_id,
        "lease_state": lease_state or "unavailable",
        "lease_until": lease_until,
        "heartbeat": heartbeat,
        "source": source,
    }


def summarize_frontier_attempt(attempt_dir: str | Path | None) -> dict[str, Any]:
    """Pure read projection of one AxiomPack frontier-attempt directory.

    It intentionally keeps frontier campaign lifecycle distinct from solver proof
    flows. The projection reads durable artifacts only and never instantiates a
    budget ledger, runner, or provider.
    """

    if not attempt_dir:
        return {
            "schema": "leanmill.frontier_attempt_observability.v1",
            "projection_status": "not_requested",
            "attempt_dir": "",
            "warnings": [],
        }
    directory = Path(attempt_dir)
    if not directory.is_dir():
        return {
            "schema": "leanmill.frontier_attempt_observability.v1",
            "projection_status": "missing",
            "attempt_dir": str(directory),
            "warnings": ["missing_frontier_attempt_dir"],
        }
    warnings: list[str] = []
    campaign = _read_json_object(
        directory / "campaign.json", warning_key="frontier_campaign", warnings=warnings
    )
    blueprint = _read_json_object(
        directory / "blueprint.json", warning_key="frontier_blueprint", warnings=warnings
    )
    run = _read_json_object(
        directory / "run.json", warning_key="frontier_run", warnings=warnings
    )
    campaign_manifest = _read_json_object(
        directory / "campaign_manifest.json",
        warning_key="frontier_campaign_manifest",
        warnings=warnings,
    )
    context_paths = [
        ("formal", directory / "formal_context.json"),
        ("evidence", directory / "evidence_context.json"),
    ]
    present_contexts = [(kind, path) for kind, path in context_paths if path.is_file()]
    if len(present_contexts) > 1:
        warnings.append("multiple_frontier_context_snapshots")
    context_kind, context_path = present_contexts[0] if present_contexts else ("", directory / "context.json")
    context = _read_json_object(
        context_path, warning_key="frontier_context", warnings=warnings
    ) if present_contexts else {}
    packet = campaign.get("packet") if isinstance(campaign.get("packet"), Mapping) else {}
    manifest = packet.get("visible_context_manifest") if isinstance(packet.get("visible_context_manifest"), Mapping) else {}
    context_hash = str(context.get("context_hash") or "")
    campaign_id = str(packet.get("campaign_id") or campaign_manifest.get("campaign_id") or "")
    journal = _frontier_journal_projection(directory, warnings=warnings)
    budget = _frontier_budget_projection(directory, warnings=warnings)
    boundary_result = _read_json_object(
        directory / "boundary_result.json", warning_key="frontier_boundary_result", warnings=warnings
    )
    boundary_completion = _read_json_object(
        directory / "boundary_completion.json", warning_key="frontier_boundary_completion", warnings=warnings
    )
    governance_recheck = _read_json_object(
        directory / "boundary_governance_recheck.json",
        warning_key="frontier_boundary_governance_recheck",
        warnings=warnings,
    )
    retirement = _read_json_object(
        directory / "retirement.json", warning_key="frontier_retirement", warnings=warnings
    )

    binding_status = "unassessed"
    if campaign and packet and blueprint and context_hash:
        try:
            from ztare.leanmill.frontier_campaign import validate_campaign_artifact_binding

            validate_campaign_artifact_binding(
                campaign,
                blueprint_id=str(blueprint.get("blueprint_id") or ""),
                context_hash=context_hash,
                expected_packet_digest=str(run.get("packet_digest") or ""),
            )
            binding_status = "valid"
        except (TypeError, ValueError):
            binding_status = "invalid"
            warnings.append("frontier_packet_binding_invalid")
    elif campaign:
        binding_status = "incomplete_artifacts"
    signature_status = "unavailable"
    public_key = directory / "campaign_signer_public.pem"
    if campaign and public_key.is_file():
        try:
            from ztare.leanmill.frontier_campaign import verify_campaign_artifact_signature

            signature_status = (
                "verified" if verify_campaign_artifact_signature(
                    campaign,
                    public_key_pem=public_key.read_text(encoding="utf-8"),
                    expected_signer_ref=str(campaign.get("signer_ref") or ""),
                ) else "invalid"
            )
        except (OSError, ValueError):
            signature_status = "invalid"
        if signature_status == "invalid":
            warnings.append("frontier_packet_signature_invalid")

    packet_context_match = _identity_match(context_hash, manifest.get("context_hash"))
    run_context_match = _identity_match(context_hash, run.get("context_hash"))
    run_packet_match = _identity_match(campaign.get("packet_digest"), run.get("packet_digest"))
    run_budget_match = _identity_match(
        budget.get("budget_digest"), run.get("budget_digest")
    )
    journal_context_match = (
        all(value == context_hash for value in journal.get("context_hashes") or ())
        if context_hash and journal.get("context_hashes") else None
    )
    journal_campaign_match = (
        all(value == campaign_id for value in journal.get("campaign_ids") or ())
        if campaign_id and journal.get("campaign_ids") else None
    )
    boundary_context_match = _identity_match(context_hash, boundary_result.get("context_hash"))
    for warning, value in (
        ("frontier_packet_context_mismatch", packet_context_match),
        ("frontier_run_context_mismatch", run_context_match),
        ("frontier_run_packet_mismatch", run_packet_match),
        ("frontier_run_budget_mismatch", run_budget_match),
        ("frontier_journal_context_mismatch", journal_context_match),
        ("frontier_journal_campaign_mismatch", journal_campaign_match),
        ("frontier_boundary_context_mismatch", boundary_context_match),
    ):
        if value is False:
            warnings.append(warning)
    navigation = run.get("navigation") if isinstance(run.get("navigation"), Mapping) else {}
    context_epoch = navigation.get("context_epoch")
    if context_epoch is None:
        context_epoch = journal.get("latest_epoch")
    boundary_status = (
        str(boundary_completion.get("status") or "")
        or str(boundary_result.get("status") or "")
        or "not_started"
    )
    lifecycle_status = (
        "retired" if retirement
        else boundary_status if boundary_status != "not_started"
        else str(run.get("status") or "prepared")
    )
    epoch_terminal_statuses = {
        "frontier_no_candidate",
        "frontier_navigation_exhausted",
        "frontier_language_expansion_requested",
        "budget_stopped",
    }
    run_status = str(run.get("status") or "")
    return {
        "schema": "leanmill.frontier_attempt_observability.v1",
        "projection_status": "available",
        "attempt_dir": str(directory),
        "attempt_identity": {
            "attempt_id": str(run.get("attempt_id") or directory.name),
            "campaign_id": campaign_id,
            "run_digest": str(run.get("run_digest") or ""),
            "packet_digest": str(campaign.get("packet_digest") or ""),
            "blueprint_id": str(blueprint.get("blueprint_id") or run.get("blueprint_id") or ""),
        },
        "frozen_packet": {
            "status": "available" if packet else "missing",
            "schema": str(packet.get("schema") or ""),
            "binding_status": binding_status,
            "signature_status": signature_status,
            "frozen": packet.get("frozen"),
            "mode": str(packet.get("mode") or ""),
            "packet_digest_matches_run": run_packet_match,
        },
        "context": {
            "status": "available" if context else "missing",
            "kind": context_kind,
            "schema": str(context.get("schema") or ""),
            "context_hash": context_hash,
            "snapshot_sha256": str(context.get("snapshot_sha256") or ""),
            "epoch": context_epoch,
            "claim_scope": str(manifest.get("claim_scope") or ""),
            "exact": manifest.get("context_exact"),
            "packet_matches_snapshot": packet_context_match,
            "run_matches_snapshot": run_context_match,
        },
        "ownership": _frontier_ownership_projection(
            directory, run, campaign_manifest, warnings=warnings
        ),
        "lineages": _frontier_lineage_projection(blueprint, run, journal),
        "budget": budget,
        "journal": journal,
        "boundary": {
            "status": boundary_status,
            "query_count": len(boundary_result.get("query_results") or ()),
            "stop_reason": str(boundary_result.get("stop_reason") or ""),
            "result_sha256": str(boundary_result.get("result_sha256") or ""),
            "completion_sha256": str(boundary_completion.get("completion_sha256") or ""),
            "context_matches_snapshot": boundary_context_match,
            "governance_recheck": {
                "status": str(governance_recheck.get("status") or "absent"),
                "proved_attributed_count": governance_recheck.get("proved_attributed_count", 0),
            },
        },
        "terminal_state": {
            "lifecycle_status": lifecycle_status,
            "run_status": run_status or "absent",
            "epoch_terminal": run_status in epoch_terminal_statuses,
            "campaign_retired": bool(retirement),
            "source": "retirement" if retirement else "boundary" if boundary_status != "not_started" else "run",
        },
        "warnings": sorted(set(warnings)),
    }


def _summarize_cache_surfaces(
    *,
    proof_cache_path: str | Path,
    no_good_path: str | Path,
    faithfulness_path: str | Path,
    decomposition_cache_path: str | Path,
    lean_root: str | Path | None,
    staged_index_path: str | Path | None,
    run_tag: str,
) -> dict[str, Any]:
    proof_cache = _summarize_proof_cache(proof_cache_path, run_tag)
    staged = _summarize_staged_reuse(lean_root=lean_root, staged_index_path=staged_index_path, run_tag=run_tag)
    no_good = _summarize_no_good(no_good_path, run_tag)
    faithfulness = _summarize_faithfulness(faithfulness_path, run_tag)
    decomposition = _summarize_decomposition_cache(decomposition_cache_path, run_tag)
    authority_totals = Counter()
    for surface in (proof_cache, staged):
        for auth, count in (surface.get("by_authority") or {}).items():
            authority_totals[str(auth)] += int(count)
    phase_env = [
        {
            "surface": "proof_cache",
            "phase": proof_cache["phase"],
            "environment": proof_cache["environment"],
            "authority": "proof_credit",
        },
        {
            "surface": "staged_reuse",
            "phase": staged["phase"],
            "environment": staged["environment"],
            "authority": "affordance",
        },
        {
            "surface": "no_good",
            "phase": no_good["phase"],
            "environment": no_good["environment"],
            "authority": "governance_memory",
        },
        {
            "surface": "faithfulness",
            "phase": faithfulness["phase"],
            "environment": faithfulness["environment"],
            "authority": "affordance",
        },
        {
            "surface": "decomposition_cache",
            "phase": decomposition["phase"],
            "environment": decomposition["environment"],
            "authority": "affordance_until_children_close",
        },
    ]
    warnings: list[str] = []
    proof_debt = proof_cache.get("metadata_debt") if isinstance(proof_cache.get("metadata_debt"), dict) else {}
    if proof_cache.get("by_schema", {}).get("legacy", 0) and proof_debt.get("missing_statement_id", 0):
        warnings.append("proof_cache_legacy_rows_present")
    if proof_cache.get("missing_statement_id", 0):
        warnings.append("proof_cache_rows_missing_statement_id")
    if proof_cache.get("orphaned_environment_rows", 0):
        warnings.append("proof_cache_orphaned_environment_rows")
    if proof_cache.get("malformed_payload_rows", 0):
        warnings.append("proof_cache_malformed_payload_rows")
    if staged.get("proof_credit_eligible", 0):
        warnings.append("staged_reuse_rows_marked_proof_credit_eligible")
    if staged.get("missing_body_rows", 0):
        warnings.append("staged_reuse_missing_body_rows")
    if no_good.get("missing_statement_id", 0):
        warnings.append("no_good_rows_missing_statement_id")
    if faithfulness.get("missing_statement_id", 0):
        warnings.append("faithfulness_rows_missing_statement_id")
    return {
        "schema": "leanmill.cache_observability.v1",
        "proof_cache": proof_cache,
        "staged_reuse": staged,
        "no_good": no_good,
        "faithfulness": faithfulness,
        "decomposition_cache": decomposition,
        "authority_totals": dict(authority_totals),
        "phase_env_matrix": phase_env,
        "warnings": warnings,
    }


def _summarize_formalize(path: str | Path, run_tag: str) -> dict[str, Any]:
    rows = [r for r in _read_jsonl(path) if not run_tag or r.get("run_tag") == run_tag]
    return {
        "total": len(rows),
        "by_outcome": _top(Counter(str(r.get("outcome") or "") for r in rows)),
        "by_phase": _top(Counter(str(r.get("phase") or "") for r in rows)),
        "unique_render_hashes": len({r.get("render_hash") for r in rows if r.get("render_hash")}),
        "top_reasons": _top(Counter(str(r.get("reason") or "")[:120] for r in rows if r.get("reason"))),
    }


def _summarize_notes(path: str | Path, run_tag: str) -> dict[str, Any]:
    rows = [r for r in _read_jsonl(path) if not run_tag or r.get("run_tag") == run_tag]
    return {
        "total": len(rows),
        "by_kind": _top(Counter(str(r.get("kind") or "") for r in rows)),
    }


def _summarize_cot(path: str | Path, run_tag: str) -> dict[str, Any]:
    rows = [r for r in _read_jsonl(path) if not run_tag or r.get("run_tag") == run_tag]
    return {
        "total": len(rows),
        "by_runtime": _top(Counter(str(r.get("runtime") or "") for r in rows)),
        "gaps": _top(Counter(str(r.get("gap") or "")[:120] for r in rows if r.get("gap"))),
    }


def _summarize_bank(path: str | Path, run_tag: str, substrate_path: str = "") -> dict[str, Any]:
    all_rows = _read_jsonl(path)
    scoped = [r for r in all_rows if run_tag and r.get("run_tag") == run_tag]
    unscoped = [r for r in all_rows if not r.get("run_tag")]
    if not scoped and substrate_path:
        scoped = [
            r for r in unscoped
            if str(r.get("context") or (r.get("mutation") or {}).get("context_path") or "") == substrate_path
        ]
    reasons = Counter()
    stages = Counter()
    changed = 0
    for row in scoped:
        stages[str(row.get("stage") or (row.get("mutation") or {}).get("stage") or "")] += 1
        result = row.get("result") if isinstance(row.get("result"), dict) else (row.get("mutation") or {}).get("result")
        if isinstance(result, dict):
            reasons[str(result.get("reason") or "")] += 1
        if row.get("changed") is True or (row.get("mutation") or {}).get("changed") is True:
            changed += 1
    return {
        "total": len(scoped),
        "by_stage": _top(stages),
        "by_reason": _top(reasons),
        "changed_count": changed,
        "unscoped_rows_seen": len(unscoped),
        "scope": "run_tag" if any(r.get("run_tag") == run_tag for r in scoped) else (
            "substrate_path_fallback" if scoped else "none"
        ),
    }


def _attempt_flow_events(path: str | Path, run_tag: str) -> list[dict[str, Any]]:
    if not run_tag:
        return []
    db = Path(path)
    if not db.exists():
        return []
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        cols = [r[1] for r in con.execute("PRAGMA table_info(attempts)")]
        needed = [c for c in ("row_id", "attempt_at", "move", "outcome", "error_class", "notes", "run_tag") if c in cols]
        if "run_tag" not in needed:
            con.close()
            return []
        rows = con.execute(
            f"SELECT {', '.join(needed)} FROM attempts WHERE run_tag = ? ORDER BY attempt_at",
            [run_tag],
        ).fetchall()
        con.close()
    except Exception:  # noqa: BLE001
        return []
    idx = {name: i for i, name in enumerate(needed)}
    events: list[dict[str, Any]] = []
    for row in rows:
        target = str(row[idx["row_id"]] if "row_id" in idx else "" or "")
        if not target:
            continue
        move = str(row[idx["move"]] if "move" in idx else "" or "")
        outcome = str(row[idx["outcome"]] if "outcome" in idx else "" or "")
        note = str(row[idx["notes"]] if "notes" in idx else "" or "")
        env = "solver_attempt"
        low = f"{move} {note}".lower()
        if "warm" in low:
            env = "campaign_warm_repl"
        elif "cold" in low or "lake env" in low:
            env = "lake_env_lean"
        elif "pool" in low:
            env = "proposal_pool"
        events.append({
            "target": target,
            "ts": str(row[idx["attempt_at"]] if "attempt_at" in idx else "" or ""),
            "state": "attempt",
            "phase": "prove",
            "environment": env,
            "source": "attempts_db",
            "detail": {
                "move": move,
                "outcome": outcome,
                "error_class": str(row[idx["error_class"]] if "error_class" in idx else "" or ""),
            },
        })
    return events


def _verdict_environment(provenance: str, kind: str) -> str:
    p = (provenance or "").lower()
    if "campaign_file_env" in p or kind.startswith("substrate_"):
        return "lake_env_lean_from_byte_zero"
    if "no_good_store" in p:
        return "no_good_store"
    if "statement_false" in p or "falsify" in p or "refutation" in p:
        return "falsify_kernel"
    if "closure_certificate" in p or "solve_adhoc" in p:
        return "governance_certificate"
    return "typed_verdict_ledger"


def _verdict_flow_events(path: str | Path, run_tag: str) -> list[dict[str, Any]]:
    try:
        from ztare.leanmill.verdict_store import iter_verdict_rows
        rows = iter_verdict_rows(path, run_tag=run_tag)
    except Exception:  # noqa: BLE001
        rows = []
    events: list[dict[str, Any]] = []
    for row in rows:
        verdict = row.get("verdict") if isinstance(row.get("verdict"), dict) else {}
        target = _nested_statement_target(row)
        extra = row.get("extra") if isinstance(row.get("extra"), dict) else {}
        target = target or str(extra.get("target_name") or "")
        if not target:
            continue
        kind = str(verdict.get("kind") or "")
        provenance = str(verdict.get("provenance") or "")
        events.append({
            "target": target,
            "ts": float(row.get("ts") or 0.0),
            "state": "typed_verdict",
            "phase": "adjudicate",
            "environment": _verdict_environment(provenance, kind),
            "source": "verdicts_jsonl",
            "detail": {
                "kind": kind,
                "provenance": provenance,
            },
        })
    return events


def _bank_flow_events(path: str | Path, run_tag: str, substrate_path: str = "") -> list[dict[str, Any]]:
    all_rows = _read_jsonl(path)
    scoped = [r for r in all_rows if run_tag and r.get("run_tag") == run_tag]
    if not scoped and substrate_path:
        scoped = [
            r for r in all_rows
            if not r.get("run_tag")
            and str(r.get("context") or (r.get("mutation") or {}).get("context_path") or "") == substrate_path
        ]
    events: list[dict[str, Any]] = []
    for row in scoped:
        target = str(row.get("target") or (row.get("mutation") or {}).get("target_name") or "")
        if not target:
            continue
        result = row.get("result") if isinstance(row.get("result"), dict) else (row.get("mutation") or {}).get("result")
        if not isinstance(result, dict):
            result = {}
        events.append({
            "target": target,
            "ts": float(row.get("ts") or 0.0),
            "state": "substrate_mutation",
            "phase": "bank",
            "environment": "persisted_substrate_file_then_cold_reverify",
            "source": "bank_attempts_jsonl",
            "detail": {
                "stage": str(row.get("stage") or (row.get("mutation") or {}).get("stage") or ""),
                "reason": str(result.get("reason") or ""),
                "changed": bool(row.get("changed") or (row.get("mutation") or {}).get("changed")),
            },
        })
    return events


def _cache_flow_events(cache_surfaces: dict[str, Any], raw_rows: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    surface_env = {
        "proof_cache": ("reuse", "kernel_checked_then_reverify_on_use"),
        "no_good": ("refutation_memory", "kernel_confirmed_no_good"),
        "faithfulness": ("formalization_firewall", "substrate_faithfulness_check"),
        "decomposition_cache": ("planner_reuse", "child_proofs_reverify"),
        "staged_reuse": ("near_complete_seed", "leaf_final_verify_required"),
    }
    for surface, rows in raw_rows.items():
        phase, env = surface_env.get(surface, ("reuse", "cache_store"))
        for row in rows:
            target = _nested_statement_target(row)
            if not target:
                target = str(row.get("target") or row.get("target_name") or "")
            if not target:
                continue
            events.append({
                "target": target,
                "ts": float(row.get("ts") or 0.0),
                "state": "cache_surface",
                "phase": phase,
                "environment": env,
                "source": surface,
                "detail": {
                    "authority": str(row.get("cache_authority") or ""),
                    "proof_credit_eligible": row.get("proof_credit_eligible"),
                    "failure_class": str(row.get("failure_class") or ""),
                    "kind": str(row.get("kind") or row.get("verdict") or ""),
                },
            })
    return events


def _raw_cache_rows_for_flows(
    *,
    proof_cache_path: str | Path,
    no_good_path: str | Path,
    faithfulness_path: str | Path,
    decomposition_cache_path: str | Path,
    lean_root: str | Path | None,
    staged_index_path: str | Path | None,
) -> dict[str, list[dict[str, Any]]]:
    staged_rows: list[dict[str, Any]] = []
    for index in _staged_index_candidates(lean_root=lean_root, staged_index_path=staged_index_path):
        staged_rows.extend(_read_jsonl(index))
    return {
        "proof_cache": _read_jsonl(proof_cache_path),
        "no_good": _read_jsonl(no_good_path),
        "faithfulness": _read_jsonl(faithfulness_path),
        "decomposition_cache": _read_jsonl(decomposition_cache_path),
        "staged_reuse": staged_rows,
    }


def _summarize_proof_flows(
    *,
    attempts_db: str | Path,
    run_tag: str,
    verdicts_path: str | Path,
    bank_attempts_path: str | Path,
    substrate_path: str,
    cache_surfaces: dict[str, Any],
    proof_cache_path: str | Path,
    no_good_path: str | Path,
    faithfulness_path: str | Path,
    decomposition_cache_path: str | Path,
    lean_root: str | Path | None,
    staged_index_path: str | Path | None,
) -> dict[str, Any]:
    raw_cache = _raw_cache_rows_for_flows(
        proof_cache_path=proof_cache_path,
        no_good_path=no_good_path,
        faithfulness_path=faithfulness_path,
        decomposition_cache_path=decomposition_cache_path,
        lean_root=lean_root,
        staged_index_path=staged_index_path,
    )
    events = []
    events.extend(_attempt_flow_events(attempts_db, run_tag))
    events.extend(_verdict_flow_events(verdicts_path, run_tag))
    events.extend(_bank_flow_events(bank_attempts_path, run_tag, substrate_path=substrate_path))
    events.extend(_cache_flow_events(cache_surfaces, raw_cache))
    flows: dict[str, dict[str, Any]] = {}
    for event in events:
        target = str(event.get("target") or "")
        if not target:
            continue
        flow = flows.setdefault(target, {
            "target": target,
            "events": [],
            "by_state": Counter(),
            "by_environment": Counter(),
        })
        flow["events"].append(event)
        flow["by_state"][str(event.get("state") or "")] += 1
        flow["by_environment"][str(event.get("environment") or "")] += 1
    for flow in flows.values():
        flow["events"].sort(key=lambda e: str(e.get("ts") or ""))
        flow["by_state"] = dict(flow["by_state"])
        flow["by_environment"] = dict(flow["by_environment"])
    warnings: list[str] = []
    attempted = {e["target"] for e in events if e.get("source") == "attempts_db"}
    verdict_targets = {e["target"] for e in events if e.get("source") == "verdicts_jsonl"}
    bank_targets = {e["target"] for e in events if e.get("source") == "bank_attempts_jsonl"}
    if attempted and not verdict_targets:
        warnings.append("attempted_targets_without_typed_verdict_events")
    missing_bank = sorted(t for t in verdict_targets if t not in bank_targets)
    if missing_bank:
        warnings.append("typed_verdict_targets_without_bank_events")
    return {
        "schema": "leanmill.proof_flow_observability.v1",
        "total_targets": len(flows),
        "targets": dict(sorted(flows.items())),
        "warnings": warnings,
    }


def _summarize_env_transitions(
    *,
    manifest: dict[str, Any],
    typed_verdicts: dict[str, Any],
    bank: dict[str, Any],
    formalize: dict[str, Any],
    cache_surfaces: dict[str, Any],
) -> dict[str, Any]:
    authority_modes = manifest.get("authority_modes") if isinstance(manifest.get("authority_modes"), dict) else {}
    verdict_kinds = typed_verdicts.get("by_kind") if isinstance(typed_verdicts.get("by_kind"), dict) else {}
    bank_reasons = bank.get("by_reason") if isinstance(bank.get("by_reason"), dict) else {}
    formalize_phases = formalize.get("by_phase") if isinstance(formalize.get("by_phase"), dict) else {}
    cache_matrix = cache_surfaces.get("phase_env_matrix") if isinstance(cache_surfaces.get("phase_env_matrix"), list) else []
    chain = [
        {
            "state": "formalize",
            "environment": "model_render_then_firewall",
            "evidence": {"formalize_rows": formalize.get("total", 0), "phases": formalize_phases},
        },
        {
            "state": "warm_verify",
            "environment": "campaign_warm_repl",
            "evidence": {"typed_verdict_kinds": verdict_kinds},
        },
        {
            "state": "substrate_append",
            "environment": "persisted_substrate_file",
            "evidence": {"bank_rows": bank.get("total", 0), "bank_reasons": bank_reasons},
        },
        {
            "state": "cold_full_file_compile",
            "environment": "lake_env_lean_from_byte_zero",
            "evidence": {
                "bank_env_ratify": str(authority_modes.get("bank_env_ratify") or ""),
                "substrate_unavailable": int(verdict_kinds.get("substrate_unavailable", 0) or 0),
                "substrate_broken": int(verdict_kinds.get("substrate_broken", 0) or 0),
            },
        },
        {
            "state": "reuse_credit_or_affordance",
            "environment": "cross_run_cache_surfaces",
            "evidence": {
                "authority_totals": cache_surfaces.get("authority_totals", {}),
                "phase_env_matrix": cache_matrix,
            },
        },
    ]
    warnings: list[str] = []
    if manifest and str(authority_modes.get("bank_env_ratify") or "") != "1":
        warnings.append("bank_env_ratify_not_enabled")
    if bank.get("total", 0) and not (
        int(verdict_kinds.get("substrate_unavailable", 0) or 0)
        or int(verdict_kinds.get("substrate_broken", 0) or 0)
        or "banked" in bank_reasons
        or "reordered_compile_ok" in bank_reasons
        or "eof_compile_ok" in bank_reasons
        or "reverted_noncompile" in bank_reasons
    ):
        warnings.append("bank_rows_without_clear_env_parity_outcome")
    if typed_verdicts.get("total", 0) == 0:
        warnings.append("no_typed_env_verdicts")
    return {
        "schema": "leanmill.env_transition_observability.v1",
        "chain": chain,
        "warnings": warnings,
    }


def _operator_readout(
    *,
    attempts: dict[str, Any],
    verdicts: dict[str, Any],
    bank: dict[str, Any],
    formalize: dict[str, Any],
    cache_surfaces: dict[str, Any],
    env_transitions: dict[str, Any],
    proof_flows: dict[str, Any],
    warnings: list[str],
) -> dict[str, Any]:
    """Small operator-facing triage over the joined ledgers.

    This is a read model only: it names the first thing to inspect, with the
    evidence already present in the bundle.
    """
    verdict_kinds = verdicts.get("by_kind") if isinstance(verdicts.get("by_kind"), dict) else {}
    bank_reasons = bank.get("by_reason") if isinstance(bank.get("by_reason"), dict) else {}
    failures = attempts.get("by_failure_class") if isinstance(attempts.get("by_failure_class"), dict) else {}
    cache_warnings = cache_surfaces.get("warnings") if isinstance(cache_surfaces.get("warnings"), list) else []
    env_warnings = env_transitions.get("warnings") if isinstance(env_transitions.get("warnings"), list) else []
    flow_warnings = proof_flows.get("warnings") if isinstance(proof_flows.get("warnings"), list) else []

    evidence = {
        "attempts": {
            "total": attempts.get("total", 0),
            "closed": attempts.get("closed", 0),
            "ratified": attempts.get("ratified", 0),
            "by_failure_class": failures,
        },
        "typed_verdicts": verdict_kinds,
        "bank_reasons": bank_reasons,
        "formalize": {
            "total": formalize.get("total", 0),
            "unique_render_hashes": formalize.get("unique_render_hashes", 0),
            "top_reasons": formalize.get("top_reasons", {}),
        },
        "warnings": warnings,
    }

    if int(attempts.get("closed", 0) or 0) or int(attempts.get("ratified", 0) or 0):
        return {
            "schema": "leanmill.operator_readout.v1",
            "status": "productive",
            "primary_bottleneck": "none",
            "why": "closures or ratified closures are present",
            "next_action": "inspect any remaining warnings before promotion",
            "evidence": evidence,
        }
    if int(verdict_kinds.get("substrate_broken", 0) or 0) or int(bank_reasons.get("reverted_noncompile", 0) or 0):
        return {
            "schema": "leanmill.operator_readout.v1",
            "status": "blocked",
            "primary_bottleneck": "substrate_env_parity",
            "why": "a proof passed one environment but failed the substrate append or full-file verdict",
            "next_action": "open bank_attempts for before/after hashes and compile the named substrate from byte zero",
            "evidence": evidence,
        }
    if int(verdict_kinds.get("substrate_unavailable", 0) or 0):
        return {
            "schema": "leanmill.operator_readout.v1",
            "status": "blocked",
            "primary_bottleneck": "verify_environment_unavailable",
            "why": "the substrate checker could not run, so compile verdicts are inconclusive",
            "next_action": "fix lake/toolchain/search-path resolution before interpreting proof failures",
            "evidence": evidence,
        }
    if int(attempts.get("total", 0) or 0) == 0:
        return {
            "schema": "leanmill.operator_readout.v1",
            "status": "blocked",
            "primary_bottleneck": "no_attempt_rows",
            "why": "the run manifest exists but no scoped attempt rows were found",
            "next_action": "check run_tag, run_scratch, and attempts DB path binding",
            "evidence": evidence,
        }
    if int(formalize.get("total", 0) or 0) and int(formalize.get("unique_render_hashes", 0) or 0) <= 1:
        return {
            "schema": "leanmill.operator_readout.v1",
            "status": "stuck",
            "primary_bottleneck": "formalization_same_render",
            "why": "formalization retries are not changing the rendered Lean statement",
            "next_action": "inspect formalize_attempts top_reasons and blueprint revision feedback",
            "evidence": evidence,
        }
    if flow_warnings or env_warnings or cache_warnings:
        return {
            "schema": "leanmill.operator_readout.v1",
            "status": "needs_inspection",
            "primary_bottleneck": "observability_warning",
            "why": "joined ledgers disagree or contain legacy rows",
            "next_action": "inspect warnings in cache_surfaces, env_transitions, and proof_flows",
            "evidence": evidence,
        }
    if failures:
        top_failure, top_count = Counter(failures).most_common(1)[0]
        return {
            "schema": "leanmill.operator_readout.v1",
            "status": "stuck",
            "primary_bottleneck": str(top_failure),
            "why": f"dominant scoped failure class count={top_count}",
            "next_action": "open the latest attempt tails for the dominant failure class",
            "evidence": evidence,
        }
    return {
        "schema": "leanmill.operator_readout.v1",
        "status": "needs_inspection",
        "primary_bottleneck": "unclear",
        "why": "the joined ledgers did not produce a dominant signal",
        "next_action": "inspect proof_flows targets chronologically",
        "evidence": evidence,
    }


def build_observability_bundle(
    *,
    run_tag: str = "",
    attempts_db: str | Path = DEFAULT_ATTEMPTS_DB,
    manifest_path: str | Path | None = None,
    lean_root: str | Path | None = None,
    verdicts_path: str | Path = DEFAULT_VERDICTS,
    bank_attempts_path: str | Path = DEFAULT_BANK_ATTEMPTS,
    formalize_attempts_path: str | Path = DEFAULT_FORMALIZE_ATTEMPTS,
    notes_trace_path: str | Path = DEFAULT_NOTES_TRACE,
    cot_traces_path: str | Path = DEFAULT_COT_TRACES,
    proof_cache_path: str | Path = DEFAULT_PROOF_CACHE,
    no_good_path: str | Path = DEFAULT_NO_GOOD_STORE,
    faithfulness_path: str | Path = DEFAULT_FAITHFULNESS_STORE,
    decomposition_cache_path: str | Path = DEFAULT_DECOMPOSITION_CACHE,
    staged_index_path: str | Path | None = None,
    axiom_packs_path: str | Path = DEFAULT_AXIOM_PACKS,
    frontier_attempt_dir: str | Path | None = None,
) -> dict[str, Any]:
    from ztare.leanmill.run_diagnostics import summarize_run
    from ztare.leanmill.verdict_store import summarize_verdicts

    attempts = summarize_run(
        db_path=attempts_db,
        run_tag=run_tag or None,
        manifest_path=manifest_path,
        lean_root=lean_root,
        verdict_path=verdicts_path,
    )
    manifest = attempts.get("run_manifest") if isinstance(attempts.get("run_manifest"), dict) else {}
    substrate = manifest.get("substrate") if isinstance(manifest.get("substrate"), dict) else {}
    substrate_path = str(substrate.get("path") or "")
    verdicts = summarize_verdicts(verdicts_path, run_tag=run_tag)
    bank = _summarize_bank(bank_attempts_path, run_tag, substrate_path=substrate_path)
    formalize = _summarize_formalize(formalize_attempts_path, run_tag)
    notes = _summarize_notes(notes_trace_path, run_tag)
    cot = _summarize_cot(cot_traces_path, run_tag)
    cache_surfaces = _summarize_cache_surfaces(
        proof_cache_path=proof_cache_path,
        no_good_path=no_good_path,
        faithfulness_path=faithfulness_path,
        decomposition_cache_path=decomposition_cache_path,
        lean_root=lean_root,
        staged_index_path=staged_index_path,
        run_tag=run_tag,
    )
    axiom_packs = _summarize_axiom_packs(axiom_packs_path, run_tag)
    frontier_attempt = summarize_frontier_attempt(frontier_attempt_dir)
    env_transitions = _summarize_env_transitions(
        manifest=manifest,
        typed_verdicts=verdicts,
        bank=bank,
        formalize=formalize,
        cache_surfaces=cache_surfaces,
    )
    proof_flows = _summarize_proof_flows(
        attempts_db=attempts_db,
        run_tag=run_tag,
        verdicts_path=verdicts_path,
        bank_attempts_path=bank_attempts_path,
        substrate_path=substrate_path,
        cache_surfaces=cache_surfaces,
        proof_cache_path=proof_cache_path,
        no_good_path=no_good_path,
        faithfulness_path=faithfulness_path,
        decomposition_cache_path=decomposition_cache_path,
        lean_root=lean_root,
        staged_index_path=staged_index_path,
    )
    warnings: list[str] = []
    if not manifest:
        warnings.append("missing_run_manifest")
    if attempts.get("total", 0) == 0:
        warnings.append("no_attempt_rows")
    if bank.get("unscoped_rows_seen", 0) and bank.get("scope") != "run_tag":
        warnings.append("bank_attempt_rows_without_run_tag_present")
    if formalize.get("total", 0) and formalize.get("unique_render_hashes", 0) <= 1:
        warnings.append("formalize_attempts_same_render_hash")
    if verdicts.get("total", 0) == 0:
        warnings.append("no_typed_verdict_rows")
    warnings.extend(f"cache:{w}" for w in cache_surfaces.get("warnings", []))
    warnings.extend(f"env:{w}" for w in env_transitions.get("warnings", []))
    warnings.extend(f"flow:{w}" for w in proof_flows.get("warnings", []))
    warnings.extend(f"axiom_pack:{w}" for w in axiom_packs.get("warnings", []))
    warnings.extend(f"frontier:{w}" for w in frontier_attempt.get("warnings", []))
    operator_readout = _operator_readout(
        attempts={
            "headline": attempts.get("headline", ""),
            "total": attempts.get("total", 0),
            "closed": attempts.get("closed", 0),
            "ratified": attempts.get("ratified", 0),
            "by_failure_class": attempts.get("by_failure_class", {}),
            "watch": attempts.get("watch", []),
            "error": attempts.get("error", ""),
            "dispatch_budget": attempts.get("dispatch_budget", {}),
        },
        verdicts=verdicts,
        bank=bank,
        formalize=formalize,
        cache_surfaces=cache_surfaces,
        env_transitions=env_transitions,
        proof_flows=proof_flows,
        warnings=warnings,
    )
    return {
        "schema": "leanmill.run_observability_bundle.v1",
        "run_tag": run_tag,
        "sources": {
            "attempts_db": str(attempts_db),
            "manifest_path": str(manifest_path or ""),
            "verdicts_path": str(verdicts_path),
            "bank_attempts_path": str(bank_attempts_path),
            "formalize_attempts_path": str(formalize_attempts_path),
            "notes_trace_path": str(notes_trace_path),
            "cot_traces_path": str(cot_traces_path),
            "proof_cache_path": str(proof_cache_path),
            "no_good_path": str(no_good_path),
            "faithfulness_path": str(faithfulness_path),
            "decomposition_cache_path": str(decomposition_cache_path),
            "staged_index_path": str(staged_index_path or ""),
            "axiom_packs_path": str(axiom_packs_path),
            "frontier_attempt_dir": str(frontier_attempt_dir or ""),
        },
        "manifest": manifest,
        "attempts": {
            "headline": attempts.get("headline", ""),
            "total": attempts.get("total", 0),
            "closed": attempts.get("closed", 0),
            "ratified": attempts.get("ratified", 0),
            "by_failure_class": attempts.get("by_failure_class", {}),
            "watch": attempts.get("watch", []),
            "error": attempts.get("error", ""),
        },
        "typed_verdicts": verdicts,
        "bank_mutations": bank,
        "formalize_attempts": formalize,
        "notes_writebacks": notes,
        "cot_traces": cot,
        "cache_surfaces": cache_surfaces,
        "axiom_packs": axiom_packs,
        "frontier_attempt": frontier_attempt,
        "env_transitions": env_transitions,
        "proof_flows": proof_flows,
        "operator_readout": operator_readout,
        "warnings": warnings,
    }


def render_bundle(bundle: dict[str, Any]) -> str:
    cache = bundle.get("cache_surfaces", {}) if isinstance(bundle.get("cache_surfaces"), dict) else {}
    proof_debt = ((cache.get("proof_cache") or {}).get("metadata_debt") or {}) if isinstance(cache.get("proof_cache"), dict) else {}
    no_good_debt = ((cache.get("no_good") or {}).get("metadata_debt") or {}) if isinstance(cache.get("no_good"), dict) else {}
    faithfulness_debt = ((cache.get("faithfulness") or {}).get("metadata_debt") or {}) if isinstance(cache.get("faithfulness"), dict) else {}
    frontier = bundle.get("frontier_attempt", {}) if isinstance(bundle.get("frontier_attempt"), dict) else {}
    lines = [
        f"[leanmill-observability] run_tag={bundle.get('run_tag') or '<none>'}",
        f"  attempts: {bundle.get('attempts', {}).get('headline', '')} "
        f"total={bundle.get('attempts', {}).get('total', 0)} "
        f"closed={bundle.get('attempts', {}).get('closed', 0)} "
        f"ratified={bundle.get('attempts', {}).get('ratified', 0)}",
        f"  verdicts: {bundle.get('typed_verdicts', {}).get('by_kind', {})}",
        f"  bank: {bundle.get('bank_mutations', {}).get('by_reason', {})} "
        f"scope={bundle.get('bank_mutations', {}).get('scope', '')}",
        f"  formalize: total={bundle.get('formalize_attempts', {}).get('total', 0)} "
        f"unique_render_hashes={bundle.get('formalize_attempts', {}).get('unique_render_hashes', 0)}",
        f"  notes: {bundle.get('notes_writebacks', {}).get('by_kind', {})}",
        f"  cot: total={bundle.get('cot_traces', {}).get('total', 0)} "
        f"gaps={bundle.get('cot_traces', {}).get('gaps', {})}",
        f"  cache: authority_totals={bundle.get('cache_surfaces', {}).get('authority_totals', {})} "
        f"warnings={bundle.get('cache_surfaces', {}).get('warnings', [])}",
        f"  cache metadata debt: proof_cache backfillable={proof_debt.get('backfillable_statement_id', 0)} "
        f"missing_payload={proof_debt.get('missing_statement_payload', 0)}; "
        f"no_good backfillable={no_good_debt.get('backfillable_statement_id', 0)} "
        f"missing_payload={no_good_debt.get('missing_statement_payload', 0)}; "
        f"faithfulness backfillable={faithfulness_debt.get('backfillable_statement_id', 0)} "
        f"missing_payload={faithfulness_debt.get('missing_statement_payload', 0)}",
        f"  axiom_packs: total={bundle.get('axiom_packs', {}).get('total', 0)} "
        f"by_status={bundle.get('axiom_packs', {}).get('by_status', {})} "
        f"warnings={bundle.get('axiom_packs', {}).get('warnings', [])}",
        f"  env: warnings={bundle.get('env_transitions', {}).get('warnings', [])}",
        f"  flows: targets={bundle.get('proof_flows', {}).get('total_targets', 0)} "
        f"warnings={bundle.get('proof_flows', {}).get('warnings', [])}",
        f"  operator: status={bundle.get('operator_readout', {}).get('status', '')} "
        f"bottleneck={bundle.get('operator_readout', {}).get('primary_bottleneck', '')} "
        f"next={bundle.get('operator_readout', {}).get('next_action', '')}",
    ]
    if frontier.get("projection_status") != "not_requested":
        lines.insert(
            -3,
            f"  frontier: status={frontier.get('projection_status', '')} "
            f"lifecycle={(frontier.get('terminal_state') or {}).get('lifecycle_status', '')} "
            f"boundary={(frontier.get('boundary') or {}).get('status', '')} "
            f"warnings={frontier.get('warnings', [])}",
        )
    if bundle.get("warnings"):
        lines.append("  warnings: " + ", ".join(bundle["warnings"]))
    return "\n".join(lines)


def _main() -> int:
    ap = argparse.ArgumentParser(description="Build a read-only LeanMill run observability bundle")
    ap.add_argument("--run-tag", default="")
    ap.add_argument("--attempts-db", default=str(DEFAULT_ATTEMPTS_DB))
    ap.add_argument("--manifest", default=None)
    ap.add_argument("--lean-root", default=None)
    ap.add_argument("--verdicts", default=str(DEFAULT_VERDICTS))
    ap.add_argument("--bank-attempts", default=str(DEFAULT_BANK_ATTEMPTS))
    ap.add_argument("--formalize-attempts", default=str(DEFAULT_FORMALIZE_ATTEMPTS))
    ap.add_argument("--notes-trace", default=str(DEFAULT_NOTES_TRACE))
    ap.add_argument("--cot-traces", default=str(DEFAULT_COT_TRACES))
    ap.add_argument("--proof-cache", default=str(DEFAULT_PROOF_CACHE))
    ap.add_argument("--no-good", default=str(DEFAULT_NO_GOOD_STORE))
    ap.add_argument("--faithfulness", default=str(DEFAULT_FAITHFULNESS_STORE))
    ap.add_argument("--decomposition-cache", default=str(DEFAULT_DECOMPOSITION_CACHE))
    ap.add_argument("--staged-index", default=None)
    ap.add_argument("--axiom-packs", default=str(DEFAULT_AXIOM_PACKS))
    ap.add_argument("--frontier-attempt", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    bundle = build_observability_bundle(
        run_tag=args.run_tag,
        attempts_db=args.attempts_db,
        manifest_path=args.manifest,
        lean_root=args.lean_root,
        verdicts_path=args.verdicts,
        bank_attempts_path=args.bank_attempts,
        formalize_attempts_path=args.formalize_attempts,
        notes_trace_path=args.notes_trace,
        cot_traces_path=args.cot_traces,
        proof_cache_path=args.proof_cache,
        no_good_path=args.no_good,
        faithfulness_path=args.faithfulness,
        decomposition_cache_path=args.decomposition_cache,
        staged_index_path=args.staged_index,
        axiom_packs_path=args.axiom_packs,
        frontier_attempt_dir=args.frontier_attempt,
    )
    print(json.dumps(bundle, indent=2, sort_keys=True) if args.json else render_bundle(bundle))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
