#!/usr/bin/env python3
"""Enqueue family-spec patch tasks from strict C-supply static failures.

This is the bridge between static-failure mining and Path-C consumable memory:
strict no-signal rows that match a family signature are not C-discriminating
until the family spec contains a clean positive + matched negative-control pair.
This script creates no proof credit; it only asks a scoped agent to patch YAML.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any

try:
    from ztare.leanmill.contracts import source_family_match
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "src"))
    from ztare.leanmill.contracts import source_family_match

import leanmill_family_specs as family_specs
import leanmill_work_queue as work_queue
import leanmill_runtime_router as runtime_router
import leanmill_operator_contracts as operator_contracts
import leanmill_learning_feedback_contract as learning_feedback
from leanmill_factory_config import FACTORY_POLICY, priority_value
from leanmill_paths import DATA_DIR

DEFAULT_SELECTION = f"{DATA_DIR}/c_supply_batch_c_discriminating_slice.json"
DEFAULT_CHECKPOINT = f"{DATA_DIR}/c_supply_batch_checkpoint.jsonl"
DEFAULT_ROW_CONTEXT = f"{DATA_DIR}/c_supply_batch_row_context.json"
DEFAULT_SPEC_DIR = family_specs.DEFAULT_SPEC_DIR
DEFAULT_OUT = f"{DATA_DIR}/c_supply_template_backfill_plan.json"
DEFAULT_POPULATION_ELO = f"{DATA_DIR}/leanmill_population_elo.json"
STRICT_NO_SIGNAL = {"tested_no_positive_signal"}
REQUIRED_STATIC_FAILURE_ARMS = ("public_tool_static", "governed_public_tool_static")



_LEAN_DECL_RE = re.compile(
    r"(?m)^\s*(?:@[^\n]*\n\s*)*(?:(?:public|private|protected|noncomputable)\s+)*(?:theorem|lemma)\s+([A-Za-z_][A-Za-z0-9_'.]*)"
)


def _target_theorem_name_from_source(source_file: str, row_id: str) -> str:
    if not source_file:
        return ""
    path = Path(source_file)
    if not path.exists() or not path.is_file():
        return ""
    try:
        text = path.read_text(errors="ignore")
    except OSError:
        return ""
    matches = list(_LEAN_DECL_RE.finditer(text))
    if not matches:
        return ""
    declared: list[tuple[str, str]] = []
    for idx, match in enumerate(matches):
        name = str(match.group(1) or "")
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        declared.append((name, text[match.end():end]))
    sorry_names = [name for name, body in declared if re.search(r"(?<![A-Za-z0-9_'])sorry(?![A-Za-z0-9_'])", body)]
    candidates = sorry_names or [name for name, _ in declared]
    if len(candidates) == 1:
        return candidates[0]
    row = str(row_id or "")
    row_matches = [name for name in candidates if name and (name in row or name.split(".")[-1] in row)]
    if len(row_matches) == 1:
        return row_matches[0]
    if row_matches:
        return sorted(row_matches, key=lambda x: (-len(x), x))[0]
    return ""


def _read_json(path: str | Path) -> Any:
    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(errors="ignore"))
    except json.JSONDecodeError:
        return None


def _read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in p.read_text(errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            out.append(obj)
    return out


def _priority_base(args: argparse.Namespace, key: str, fallback: int) -> int:
    return priority_value(
        path=getattr(args, "factory_policy", FACTORY_POLICY),
        namespace="formula_bases",
        key=key,
        fallback=fallback,
    )


def _population_family_priors(path: str | Path | None = None) -> dict[str, dict[str, Any]]:
    obj = _read_json(path or DEFAULT_POPULATION_ELO)
    ratings = obj.get("ratings") if isinstance(obj, dict) else []
    out: dict[str, dict[str, Any]] = {}
    if not isinstance(ratings, list):
        return out
    for row in ratings:
        if not isinstance(row, dict):
            continue
        contestant = str(row.get("contestant") or "")
        if not contestant.startswith("family:"):
            continue
        family = contestant.split(":", 1)[1]
        if not family:
            continue
        out[family] = {
            "contestant": contestant,
            "rating": row.get("rating"),
            "p_ucb_priority": row.get("p_ucb_priority"),
            "games": row.get("games"),
            "wins": row.get("wins"),
            "losses": row.get("losses"),
            "ties": row.get("ties"),
            "cold_start": row.get("cold_start"),
        }
    return out


def _prior_score(priors: dict[str, dict[str, Any]], family: str) -> float:
    row = priors.get(family) or {}
    for key in ("p_ucb_priority", "rating"):
        try:
            return float(row.get(key))
        except (TypeError, ValueError):
            continue
    return 1000.0


def _family_order_key(family: str, candidates_by_family: dict[str, list[dict[str, Any]]], priors: dict[str, dict[str, Any]]) -> tuple[float, int, str]:
    return (-_prior_score(priors, family), -len(candidates_by_family.get(family) or []), family)


def _row_id(row: dict[str, Any]) -> str:
    return str(row.get("row_id") or row.get("id") or row.get("target_id") or "")


def _iter_rows(obj: Any) -> list[dict[str, Any]]:
    if isinstance(obj, list):
        return [x for x in obj if isinstance(x, dict)]
    if not isinstance(obj, dict):
        return []
    rows: list[dict[str, Any]] = []
    for key in ("rows", "results", "row_results", "qualified_rows", "corpus"):
        vals = obj.get(key)
        if isinstance(vals, list):
            rows.extend(x for x in vals if isinstance(x, dict))
    return rows


def _slug(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value).strip("_") or "item"


def _spec_index(spec_dir: str | Path) -> tuple[dict[str, dict[str, Any]], dict[str, set[str]]]:
    specs = family_specs.load_specs(spec_dir)
    by_family = {str(spec.get("family") or ""): spec for spec in specs if str(spec.get("family") or "")}
    rows_by_family: dict[str, set[str]] = {}
    for family, spec in by_family.items():
        rows_by_family[family] = {
            str(t.get("row_id") or "")
            for t in (spec.get("templates") or [])
            if isinstance(t, dict) and str(t.get("row_id") or "")
        }
    return by_family, rows_by_family


def _source_demands(selection: dict[str, Any]) -> list[dict[str, Any]]:
    demands = []
    for req in selection.get("source_demand_requests") or []:
        if not isinstance(req, dict):
            continue
        if str(req.get("recommended_action") or "") != "source_similar_static_fail_rows":
            continue
        family = str(req.get("family") or "")
        if family:
            demands.append(req)
    return demands


def _rows_not_requiring_template_backfill(selection: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for key in ("selected_rows", "rows"):
        for row in selection.get(key) or []:
            if not isinstance(row, dict):
                continue
            row_id = str(row.get("row_id") or "")
            if not row_id:
                continue
            status = str(row.get("c_discriminating_evidence_status") or "")
            if row.get("probe_credit_ready") is True or status == "c_discriminating_probe_verified":
                out.add(row_id)
    return out


HARD_SELECTOR_DISQUALIFIERS = {
    "static_tool_positive",
    "static_harness_infra_hold",
    "static_ambiguous_non_positive",
    "target_not_executable",
}
HARD_SELECTOR_DISQUALIFIER_PREFIXES = (
    "family_spec_probe_terminal_nonuseful:",
)


def _current_selection_top_family_by_row(selection: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key in ("selected_rows", "rows"):
        for row in selection.get(key) or []:
            if not isinstance(row, dict):
                continue
            row_id = str(row.get("row_id") or row.get("id") or row.get("target_id") or "")
            if not row_id:
                continue
            top = str(row.get("best_static_family_match") or "")
            if not top:
                families = row.get("matched_families") or []
                if isinstance(families, str):
                    families = [families]
                if len(families) == 1:
                    top = str(families[0] or "")
            if top:
                out[row_id] = top
    return out


def _current_selection_disqualified_rows(selection: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for row in selection.get("rows") or []:
        if not isinstance(row, dict):
            continue
        row_id = str(row.get("row_id") or "")
        reasons = {str(r) for r in (row.get("rejection_reasons") or []) if str(r)}
        has_hard_prefix = any(
            reason.startswith(prefix)
            for reason in reasons
            for prefix in HARD_SELECTOR_DISQUALIFIER_PREFIXES
        )
        if row_id and row.get("eligible") is not True and (reasons.intersection(HARD_SELECTOR_DISQUALIFIERS) or has_hard_prefix):
            out.add(row_id)
    for row in selection.get("static_conflict_rows") or []:
        if isinstance(row, dict) and str(row.get("row_id") or ""):
            out.add(str(row.get("row_id") or ""))
        elif isinstance(row, str) and row:
            out.add(row)
    return out


NONUSEFUL_PROBE_EXITS = learning_feedback.NONUSEFUL_PROBE_EXITS


def _queue_disqualified_pairs(queue_db: str | Path) -> set[tuple[str, str]]:
    """Rows with terminal family-spec probe evidence must not be re-templated blind.

    The C-supply selector is a moving view; queue history is the durable memory
    that a family/row pair has already been tried and found non-useful.
    """
    if not queue_db:
        return set()
    path = Path(queue_db)
    if not path.exists() or not path.is_file():
        return set()
    try:
        cx = sqlite3.connect(str(path))
        cx.row_factory = sqlite3.Row
        rows = cx.execute(
            """
            SELECT work_id, status, payload_json
            FROM work_items
            WHERE kind='repair_canary_probe'
              AND status IN ('done','failed','retired','dead_letter')
            """
        ).fetchall()
    except sqlite3.Error:
        return set()
    out: set[tuple[str, str]] = set()
    for row in rows:
        try:
            payload = json.loads(row["payload_json"] or "{}")
        except json.JSONDecodeError:
            continue
        if str(payload.get("probe_lane") or "") != "family_spec":
            continue
        family = str(payload.get("family") or "")
        if not family:
            continue
        row_outcomes = payload.get("row_outcomes") or []
        if isinstance(row_outcomes, dict):
            row_outcomes = list(row_outcomes.values())
        if not isinstance(row_outcomes, list) or not row_outcomes:
            shard = payload.get("family_spec_shard") or {}
            row_id = str(shard.get("row_id") or "") if isinstance(shard, dict) else ""
            row_outcomes = [{"row_id": row_id, "learning_unit_exit": payload.get("learning_unit_exit") or payload.get("exit_kind")}]
        for outcome in row_outcomes:
            if not isinstance(outcome, dict):
                continue
            row_id = str(outcome.get("row_id") or "")
            exit_kind = str(outcome.get("learning_unit_exit") or payload.get("learning_unit_exit") or payload.get("exit_kind") or "")
            if row_id and exit_kind in NONUSEFUL_PROBE_EXITS:
                out.add((family, row_id))
    return out




def _tail_text(value: Any, limit: int = 900) -> str:
    text = str(value or "")
    return text[-limit:] if len(text) > limit else text


def _probe_failure_evidence_from_payload(payload: dict[str, Any], *, row_id: str = "", limit: int = 3) -> list[dict[str, Any]]:
    root = Path(str(payload.get("root") or ""))
    rows_dir = root / "rows"
    if not rows_dir.exists() or not rows_dir.is_dir():
        return []
    out: list[dict[str, Any]] = []
    for path in sorted(rows_dir.glob("*.json")):
        if len(out) >= limit:
            break
        obj = _read_json(path)
        if not isinstance(obj, dict):
            continue
        obj_row_id = str(obj.get("row_id") or "")
        if row_id and obj_row_id and obj_row_id != row_id:
            continue
        for rec in obj.get("results") or []:
            if len(out) >= limit:
                break
            if not isinstance(rec, dict) or rec.get("closed"):
                continue
            repl_errors = rec.get("repl_errors") if isinstance(rec.get("repl_errors"), list) else []
            out.append({
                "row_id": obj_row_id or row_id or rec.get("row_id"),
                "candidate": rec.get("candidate"),
                "action_family": rec.get("action_family"),
                "driver_path": rec.get("driver_path"),
                "body_tail": _tail_text(rec.get("body") or rec.get("body_tail")),
                "stdout_tail": _tail_text(rec.get("stdout") or rec.get("stdout_tail")),
                "stderr_tail": _tail_text(rec.get("stderr") or rec.get("stderr_tail")),
                "repl_error_tail": _tail_text("\n".join(str(err.get("data") or err) if isinstance(err, dict) else str(err) for err in repl_errors)),
                "error_class": rec.get("error_class"),
            })
    return learning_feedback.compact_failure_evidence(out, limit=limit)


def _queue_probe_feedback_by_family(queue_db: str | Path, *, limit_per_family: int = 5) -> dict[str, list[dict[str, Any]]]:
    """Recent probe feedback that should change the next template attempt.

    This is not proof credit. It is the causal feedback channel from governed
    probe/drain outcomes back into C-supply generation so agents do not replay
    invalid canaries or zero-yield family/row attempts as if nothing happened.
    """
    if not queue_db:
        return {}
    path = Path(queue_db)
    if not path.exists() or not path.is_file():
        return {}
    try:
        cx = sqlite3.connect(str(path))
        cx.row_factory = sqlite3.Row
        rows = cx.execute(
            """
            SELECT work_id, status, payload_json, updated_at
            FROM work_items
            WHERE kind='repair_canary_probe'
              AND status IN ('done','failed','retired','dead_letter')
            ORDER BY updated_at DESC
            LIMIT 400
            """
        ).fetchall()
    except sqlite3.Error:
        return {}
    out: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        try:
            payload = json.loads(row["payload_json"] or "{}")
        except json.JSONDecodeError:
            continue
        if str(payload.get("probe_lane") or "") != "family_spec":
            continue
        family = str(payload.get("family") or "")
        if not family:
            continue
        row_outcomes = payload.get("row_outcomes") or []
        if isinstance(row_outcomes, dict):
            row_outcomes = list(row_outcomes.values())
        if not isinstance(row_outcomes, list) or not row_outcomes:
            shard = payload.get("family_spec_shard") or {}
            row_id = str(shard.get("row_id") or "") if isinstance(shard, dict) else ""
            row_outcomes = [{
                "row_id": row_id,
                "learning_unit_exit": payload.get("learning_unit_exit") or payload.get("exit_kind"),
                "negative_control_invalid_fail_count": payload.get("negative_control_invalid_fail_count"),
                "negative_control_fail_count": payload.get("negative_control_fail_count"),
                "negative_control_unexpected_pass_count": payload.get("negative_control_unexpected_pass_count"),
            }]
        for outcome in row_outcomes:
            if not isinstance(outcome, dict):
                continue
            row_id = str(outcome.get("row_id") or "")
            exit_kind = str(outcome.get("learning_unit_exit") or payload.get("learning_unit_exit") or payload.get("exit_kind") or "")
            if exit_kind not in NONUSEFUL_PROBE_EXITS and int(outcome.get("negative_control_invalid_fail_count") or 0) <= 0:
                continue
            rec = learning_feedback.feedback_entry(
                source_probe_work_id=str(row["work_id"]),
                row_id=row_id,
                exit_kind=exit_kind,
                negative_control_invalid_fail_count=int(outcome.get("negative_control_invalid_fail_count") or 0),
                negative_control_fail_count=int(outcome.get("negative_control_fail_count") or 0),
                negative_control_unexpected_pass_count=int(outcome.get("negative_control_unexpected_pass_count") or 0),
                scoreboard=str(payload.get("scoreboard") or ""),
                feedback_action="do_not_replay_invalid_template_shape; repair positive/negative pair or choose a different row/family edge",
                failure_evidence=_probe_failure_evidence_from_payload(payload, row_id=row_id),
            )
            bucket = out.setdefault(family, [])
            if len(bucket) < max(1, int(limit_per_family)):
                bucket.append(rec)
    return out

def _strict_static_fail_rows(records: list[dict[str, Any]]) -> tuple[set[str], dict[str, dict[str, Any]]]:
    """Rows eligible for template backfill must have a full static miss.

    Public-only failures are provisional; governed static may still close them.
    Template generation is expensive and can pollute C-supply if it starts from
    a row that later becomes a static positive, so require both static arms to
    finish with strict no-signal and no closure-shaped evidence.
    """
    outcomes: dict[str, dict[str, Any]] = {}
    for rec in records:
        row_id = str(rec.get("row_id") or "")
        arm = str(rec.get("arm") or "")
        if not row_id or arm not in REQUIRED_STATIC_FAILURE_ARMS:
            continue
        current = outcomes.setdefault(row_id, {"arms": {}, "has_positive_signal": False})
        current["arms"][arm] = rec
        exit_kind = str(rec.get("learning_exit") or "")
        if exit_kind not in STRICT_NO_SIGNAL:
            current["has_positive_signal"] = True
        for key in (
            "proof",
            "proof_term",
            "tactic",
            "raw_tactic",
            "governed_tactic",
            "closure_candidate",
            "ratified_closure",
        ):
            if rec.get(key):
                current["has_positive_signal"] = True
    strict_rows: set[str] = set()
    for row_id, info in outcomes.items():
        arms = info.get("arms") or {}
        if info.get("has_positive_signal"):
            continue
        if all(str((arms.get(arm) or {}).get("learning_exit") or "") in STRICT_NO_SIGNAL for arm in REQUIRED_STATIC_FAILURE_ARMS):
            strict_rows.add(row_id)
    return strict_rows, outcomes


def _candidate_rows(
    records: list[dict[str, Any]],
    rows_by_id: dict[str, dict[str, Any]],
    existing_spec_rows: dict[str, set[str]],
    rows_not_requiring_template_backfill: set[str] | None = None,
    current_selection_disqualified_rows: set[str] | None = None,
    current_selection_top_family_by_row: dict[str, str] | None = None,
    queue_disqualified_pairs: set[tuple[str, str]] | None = None,
    min_candidate_hit_count: int = 2,
    match_policy: source_family_match.SourceFamilyMatchPolicy | None = None,
) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, dict[str, dict[str, Any]]] = {}
    match_policy = match_policy or source_family_match.SourceFamilyMatchPolicy(min_hit_count=max(1, int(min_candidate_hit_count)))
    strict_static_fail_rows, _static_outcomes = _strict_static_fail_rows(records)
    rows_not_requiring_template_backfill = rows_not_requiring_template_backfill or set()
    current_selection_disqualified_rows = current_selection_disqualified_rows or set()
    current_selection_top_family_by_row = current_selection_top_family_by_row or {}
    queue_disqualified_pairs = queue_disqualified_pairs or set()
    for rec in records:
        if str(rec.get("arm") or "") != "public_tool_static":
            continue
        if str(rec.get("learning_exit") or "") not in STRICT_NO_SIGNAL:
            continue
        if not bool(rec.get("supply_candidate")):
            continue
        row_id = str(rec.get("row_id") or "")
        if row_id not in strict_static_fail_rows:
            continue
        if row_id in rows_not_requiring_template_backfill or row_id in current_selection_disqualified_rows:
            continue
        row = rows_by_id.get(row_id)
        if not row:
            continue
        source_file = str(row.get("source_file") or row.get("sorried_file") or "")
        if source_file and not Path(source_file).exists():
            continue
        current_top_family = current_selection_top_family_by_row.get(row_id, "")
        matches = [
            match for match in source_family_match.eligible_matches(rec.get("family_matches") or [], match_policy)
            if (not current_top_family or str(match.get("family") or "") == current_top_family)
            and (str(match.get("family") or ""), row_id) not in queue_disqualified_pairs
            and row_id not in existing_spec_rows.get(str(match.get("family") or ""), set())
        ]
        if not matches:
            continue
        matches.sort(
            key=lambda match: (
                -float(match.get("confidence") or 0.0),
                -int(match.get("hit_count") or 0),
                str(match.get("family") or ""),
            )
        )
        match = matches[0]
        family = str(match.get("family") or "")
        item = {
            "row_id": row_id,
            "source_file": source_file,
            "target_theorem_name": row.get("target_theorem_name") or _target_theorem_name_from_source(source_file, row_id),
            "confidence": float(match.get("confidence") or 0.0),
            "hit_count": int(match.get("hit_count") or 0),
            "matched_features": match.get("matched_features") or [],
            "generic_features_ignored": match.get("generic_features_ignored") or [],
            "template_design_rows": match.get("template_design_rows") or [],
            "static_exit": rec.get("learning_exit"),
            "attempt_count": rec.get("attempt_count"),
            "family_match_rank": 1,
            "candidate_family_selection": "current_slice_top_family_then_highest_confidence",
            "source_family_match_policy": match_policy.as_receipt(),
        }
        out.setdefault(family, {})[row_id] = item
    return {
        family: sorted(items.values(), key=lambda x: (-float(x.get("confidence") or 0.0), -int(x.get("hit_count") or 0), str(x.get("row_id") or "")))
        for family, items in out.items()
    }


def _contract_upgrade_retirement(payload: dict[str, Any]) -> bool:
    return (
        str(payload.get("exit_kind") or "") == "retired_for_contract_upgrade"
        or bool(payload.get("contract_upgrade_required"))
        or str(payload.get("reason") or "") == "c_supply_template_backfill_task_missing_operator_contract_regenerate_under_current_contract"
    )


def _open_or_recent(cx: Any, *, family: str, cooldown_s: int) -> bool:
    threshold = int(time.time()) - max(0, int(cooldown_s))
    rows = cx.execute(
        """
        SELECT status, payload_json, updated_at
        FROM work_items
        WHERE kind='agent_repair_task'
          AND status IN ('queued','claimed','running','done','failed','retired','dead_letter')
        """,
    ).fetchall()
    for row in rows:
        try:
            payload = json.loads(row["payload_json"] or "{}")
        except json.JSONDecodeError:
            continue
        if str(payload.get("family") or "") != family or str(payload.get("family_spec_patch_mode") or "") != "c_supply_template_backfill":
            continue
        if _contract_upgrade_retirement(payload):
            continue
        if str(row["status"] or "") in {"queued", "claimed", "running"}:
            return True
        if int(row["updated_at"] or 0) < threshold:
            continue
        return True
    return False


def _job_for(args: argparse.Namespace, *, family: str, spec: dict[str, Any], demand: dict[str, Any], candidates: list[dict[str, Any]], run_id: str, planned_runtime_counts: dict[str, int], probe_feedback: list[dict[str, Any]] | None = None, population_prior: dict[str, Any] | None = None) -> dict[str, Any]:
    target_path = str(spec.get("_path") or Path(args.spec_dir) / f"{_slug(family)}.yaml")
    chosen = candidates[: max(1, int(args.rows_per_family))]
    population_prior = population_prior or {}
    candidate_rows = [str(c.get("row_id") or "") for c in chosen if str(c.get("row_id") or "")]
    route_key = f"c_supply_template_backfill:{family}:{','.join(candidate_rows)}"
    routing_receipt = runtime_router.select_runtime(
        requested_runtime=args.agent_runtime,
        queue_db=args.queue_db,
        policy_path=args.factory_policy,
        policy_profile=args.policy_profile,
        route_key=route_key,
        planned_counts=planned_runtime_counts,
        events_path=args.events,
    )
    selected_runtime = str(routing_receipt.get("selected_runtime") or args.agent_runtime)
    planned_runtime_counts[selected_runtime] = planned_runtime_counts.get(selected_runtime, 0) + 1
    contract_id = f"leanmill-c-supply-template-backfill:{family}:{run_id}"
    demand_with_feedback = {**demand, "recent_probe_feedback": learning_feedback.compact_feedback_entries(list(probe_feedback or []), limit=5)}
    if population_prior:
        demand_with_feedback["population_elo_routing_prior"] = population_prior
    operator_contract = operator_contracts.c_supply_template_backfill_contract(
        family=family,
        candidate_rows=chosen,
        target_path=target_path,
        source_demand=demand_with_feedback,
        contract_id=contract_id,
    )
    task = (
        "Patch the target LeanMill repair-family YAML only. Convert one or two listed strict static-no-signal, "
        "family-matched candidate rows into real reusable family-spec templates. For each row you touch, add a positive "
        "template and a substantively matched negative_control template, following the existing family style. Do not add "
        "placeholders, do not duplicate positive bodies as negatives, do not claim proof value, and do not edit any file "
        "except the target YAML. The positive template must not call the candidate target theorem itself; if the "
        "candidate source declaration is still sorry-backed or target_theorem_name is listed, using that name in the "
        "positive body is a self-reference and must be rejected. The negative_control must be a substantive family-ingredient "
        "removal/reversal, not just an ill-typed or under-applied theorem call. If no listed row can be safely templated, do not edit; emit terminal JSON with "
        "exit_kind operator_required or retired, attempted_routes, and the concrete blocked_edge. "
        "Follow the compact operator_contract exactly: it is the program counter and evidence contract for this task. "
        "If recent_probe_feedback is present, treat it as causal feedback from governed probes: do not replay an invalid "
        "negative-control shape, syntax/notation failure, or previously non-useful family/row edge without a concrete repair. "
        f"Target YAML: {target_path}. Source-demand request: {json.dumps(demand_with_feedback, sort_keys=True)}. "
        f"Candidate rows: {json.dumps(chosen, sort_keys=True)}"
    )
    contract_hash = hashlib.sha256(json.dumps(operator_contract, sort_keys=True).encode("utf-8")).hexdigest()[:12]
    work_id = f"family_spec_c_supply_backfill:{family}:{run_id}:{contract_hash}"
    return {
        "kind": "agent_repair_task",
        "priority": int(_priority_base(args, "c_supply_template_backfill", 230) + sum(int(c.get("hit_count") or 0) for c in chosen) + max(-20, min(20, (_prior_score({family: population_prior}, family) - 1000.0) / 10.0))),
        "work_id": work_id,
        "payload": {
            "work_id": work_id,
            "runtime": selected_runtime,
            "agent_id": f"leanmill_{selected_runtime}_c_supply_template_backfill",
            "runtime_routing_receipt": routing_receipt,
            "population_elo_routing_prior": population_prior,
            "station": "repair_registry",
            "family": family,
            "task": task,
            "operator_contract": operator_contract,
            "expected_exit": "family_spec_patch",
            "allowed_paths": [target_path, "/tmp/rung1"],
            "allowed_read_paths": [target_path, "/tmp/rung1"],
            "allowed_write_paths": [target_path],
            "requires_negative_control": True,
            "negative_control": "Every added C-supply row must include a matched negative_control template for the same row that should fail when the family-specific bridge/direction/source ingredient is removed or reversed.",
            "proof_affecting": False,
            "max_iterations": args.agent_max_iterations,
            "max_wall_time_s": args.agent_max_wall_time_s,
            "family_spec_patch_target": target_path,
            "family_spec_patch_mode": "c_supply_template_backfill",
            "c_supply_selection": args.selection,
            "c_supply_checkpoint": args.checkpoint,
            "c_supply_row_context": args.row_context,
            "c_supply_spec_dir": args.spec_dir,
            "c_supply_candidate_rows": candidate_rows,
            "c_supply_candidates": chosen,
            "c_supply_source_demand": demand_with_feedback,
            "recent_probe_feedback": learning_feedback.compact_feedback_entries(list(probe_feedback or []), limit=5),
            "replenish_group": f"family_spec_c_supply_backfill:{family}",
        },
        "artifact_paths": [target_path, args.selection, args.checkpoint, args.row_context],
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    selection = _read_json(args.selection) or {}
    row_context = _read_json(args.row_context) or {}
    rows_by_id = {_row_id(row): row for row in _iter_rows(row_context) if _row_id(row)}
    specs_by_family, existing_spec_rows = _spec_index(args.spec_dir)
    rows_not_requiring_template_backfill = _rows_not_requiring_template_backfill(selection)
    current_selection_disqualified_rows = _current_selection_disqualified_rows(selection)
    current_selection_top_family_by_row = _current_selection_top_family_by_row(selection)
    queue_disqualified_pairs = _queue_disqualified_pairs(args.queue_db)
    probe_feedback_by_family = _queue_probe_feedback_by_family(args.queue_db)
    checkpoint_records = _read_jsonl(args.checkpoint)
    strict_static_fail_rows, static_outcomes = _strict_static_fail_rows(checkpoint_records)
    match_policy = source_family_match.policy_from_factory_policy(
        _read_json(args.factory_policy) or {},
        profile=str(getattr(args, "policy_profile", "") or ""),
        fallback_min_hit_count=max(2, int(getattr(args, "min_candidate_hit_count", 2))),
    )
    candidates_by_family = _candidate_rows(
        checkpoint_records,
        rows_by_id,
        existing_spec_rows,
        rows_not_requiring_template_backfill,
        current_selection_disqualified_rows,
        current_selection_top_family_by_row,
        queue_disqualified_pairs,
        max(2, int(getattr(args, "min_candidate_hit_count", 2))),
        match_policy,
    )
    population_priors = _population_family_priors()
    run_id = args.run_id or str(int(time.time()))
    jobs = []
    skipped = []
    planned_runtime_counts: dict[str, int] = {}
    demand_by_family = {str(req.get("family") or ""): req for req in _source_demands(selection)}
    families: list[str] = sorted(demand_by_family, key=lambda fam: _family_order_key(fam, candidates_by_family, population_priors))
    if bool(args.include_all_candidate_families):
        for family in sorted(candidates_by_family, key=lambda fam: _family_order_key(fam, candidates_by_family, population_priors)):
            if family not in demand_by_family:
                families.append(family)
    seen_families: set[str] = set()
    used_batch_rows: set[str] = set()
    for family in families:
        if not family or family in seen_families:
            continue
        seen_families.add(family)
        demand = demand_by_family.get(family, {
            "family": family,
            "recommended_action": "backfill_templates_from_strict_static_fail_candidates",
            "source_query_intent": "Convert already-mined strict static-no-signal family-matched rows into reusable positive+negative-control family-spec pairs.",
        })
        spec = specs_by_family.get(family)
        candidates = candidates_by_family.get(family) or []
        if not spec:
            skipped.append({"family": family, "reason": "missing_family_spec"})
            continue
        if not candidates:
            skipped.append({"family": family, "reason": "no_strict_no_signal_candidates"})
            continue
        unique_candidates = [c for c in candidates if str(c.get("row_id") or "") not in used_batch_rows]
        if not unique_candidates:
            skipped.append({"family": family, "reason": "candidate_rows_already_planned_in_batch"})
            continue
        job = _job_for(
            args,
            family=family,
            spec=spec,
            demand=demand,
            candidates=unique_candidates,
            run_id=run_id,
            planned_runtime_counts=planned_runtime_counts,
            probe_feedback=probe_feedback_by_family.get(family) or [],
            population_prior=population_priors.get(family) or {},
        )
        contract_check = operator_contracts.validate_operator_contract(job["payload"])
        if contract_check.get("status") != "pass":
            skipped.append({
                "family": family,
                "reason": "operator_contract_preflight_failed",
                "candidate_rows": job["payload"].get("c_supply_candidate_rows") or [],
                "contract_failures": contract_check.get("failures") or [],
            })
            continue
        used_batch_rows.update(str(row_id) for row_id in (job["payload"].get("c_supply_candidate_rows") or []) if str(row_id))
        jobs.append(job)
        if len(jobs) >= int(args.max_jobs):
            break
    enqueued = 0
    skip_counts: dict[str, int] = {}
    enqueued_jobs = []
    if args.enqueue and jobs:
        cx = work_queue.connect(args.queue_db)
        for job in jobs:
            family = str(job["payload"].get("family") or "")
            if _open_or_recent(cx, family=family, cooldown_s=int(args.cooldown_s)) and not args.retry_existing:
                skip_counts["open_or_recent_same_family"] = skip_counts.get("open_or_recent_same_family", 0) + 1
                continue
            work_queue.enqueue(cx, kind=job["kind"], priority=int(job["priority"]), payload=job["payload"], max_attempts=max(1, int(args.agent_max_attempts)))
            work_queue.append_event(args.events, {
                "event_type": "c_supply_template_backfill_enqueued",
                "work_id": job["work_id"],
                "payload": {"family": family, "candidate_rows": job["payload"].get("c_supply_candidate_rows")},
                "artifact_paths": job["artifact_paths"],
            })
            enqueued += 1
            enqueued_jobs.append({"work_id": job["work_id"], "family": family, "candidate_rows": job["payload"].get("c_supply_candidate_rows")})
            if args.max_enqueued and enqueued >= int(args.max_enqueued):
                break
    result = {
        "schema": "leanmill-c-supply-template-backfill-plan-v1",
        "run_id": run_id,
        "dry_run": not args.enqueue,
        "selection": args.selection,
        "checkpoint": args.checkpoint,
        "row_context": args.row_context,
        "selection_status": selection.get("status"),
        "selection_selected_count": selection.get("selected_count"),
        "selection_eligible_count": selection.get("eligible_count"),
        "job_count": len(jobs),
        "jobs": jobs,
        "skipped": skipped,
        "skip_counts": skip_counts,
        "enqueued": enqueued,
        "enqueued_jobs": enqueued_jobs,
        "rows_not_requiring_template_backfill_count": len(rows_not_requiring_template_backfill),
        "current_selection_disqualified_row_count": len(current_selection_disqualified_rows),
        "queue_disqualified_pair_count": len(queue_disqualified_pairs),
        "probe_feedback_family_count": len(probe_feedback_by_family),
        "probe_feedback_counts_by_family": {family: len(vals) for family, vals in sorted(probe_feedback_by_family.items())},
        "current_selection_top_family_row_count": len(current_selection_top_family_by_row),
        "candidate_family_count": len(candidates_by_family),
        "min_candidate_hit_count": max(2, int(getattr(args, "min_candidate_hit_count", 2))),
        "source_family_match_policy": match_policy.as_receipt(),
        "strict_static_fail_row_count": len(strict_static_fail_rows),
        "static_outcome_row_count": len(static_outcomes),
        "population_elo_path": DEFAULT_POPULATION_ELO,
        "population_elo_family_prior_count": len(population_priors),
        "candidate_counts_by_family": {family: len(vals) for family, vals in sorted(candidates_by_family.items())},
        "planned_runtime_counts": planned_runtime_counts,
        "agent_max_attempts": max(1, int(args.agent_max_attempts)),
        "credit_boundary": "no proof credit; family-spec patch receipt and later governance probes decide value",
    }
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def _self_test() -> int:
    import tempfile

    def ns(**overrides: Any) -> argparse.Namespace:
        base = {
            "selection": str(sel),
            "checkpoint": str(ck),
            "row_context": str(rows),
            "spec_dir": str(spec_dir),
            "queue_db": str(root / "q.sqlite"),
            "events": str(root / "events.jsonl"),
            "out": None,
            "run_id": "x",
            "max_jobs": 2,
            "rows_per_family": 2,
            "agent_runtime": "balanced",
            "factory_policy": str(root / "missing_policy.json"),
            "policy_profile": "",
            "agent_max_iterations": 3,
            "agent_max_wall_time_s": 1200,
            "enqueue": False,
            "max_enqueued": 0,
            "cooldown_s": 0,
            "retry_existing": False,
            "include_all_candidate_families": True,
            "min_candidate_hit_count": 2,
            "agent_max_attempts": 2,
        }
        base.update(overrides)
        return argparse.Namespace(**base)

    def static_record(row_id: str, arm: str, matches: list[dict[str, Any]], *, exit_kind: str = "tested_no_positive_signal", supply_candidate: bool = True, **extra: Any) -> str:
        rec: dict[str, Any] = {
            "row_id": row_id,
            "arm": arm,
            "learning_exit": exit_kind,
            "supply_candidate": supply_candidate,
            "family_matches": matches,
        }
        rec.update(extra)
        return json.dumps(rec) + "\n"

    def strict_pair(row_id: str, matches: list[dict[str, Any]], *, governed_exit: str = "tested_no_positive_signal", governed_extra: dict[str, Any] | None = None) -> str:
        return (
            static_record(row_id, "public_tool_static", matches)
            + static_record(row_id, "governed_public_tool_static", matches, exit_kind=governed_exit, **(governed_extra or {}))
        )

    with tempfile.TemporaryDirectory(prefix="leanmill_c_supply_backfill_") as td:
        root = Path(td)
        spec_dir = root / "specs"
        spec_dir.mkdir()
        (spec_dir / "fam.yaml").write_text("""
family: fam
status: seed_only
residual_match:
  head_patterns: [foo]
templates:
  - id: old_pos
    row_id: old
    test_kind: positive
    body_lines: [trivial]
  - id: old_neg
    row_id: old
    test_kind: negative_control
    body_lines: [exact False.elim]
""")
        (spec_dir / "fam2.yaml").write_text("""
family: fam2
status: seed_only
residual_match:
  head_patterns: [foo]
templates: []
""")
        source = root / "r1.lean"
        source.write_text("theorem r1 : True := by trivial\n")
        r2 = root / "r2.lean"
        r2.write_text("theorem r2 : True := by trivial\n")
        rows = root / "rows.json"
        rows.write_text(json.dumps({"rows": [{"row_id": "r1", "source_file": str(source)}, {"row_id": "r2", "source_file": str(r2)}]}) + "\n")
        ck = root / "ck.jsonl"
        sel = root / "sel.json"
        fam_match = [{"family": "fam", "status": "candidate_family", "has_negative_controls": True, "confidence": 0.9, "hit_count": 3}]
        fam2_match = [{"family": "fam2", "status": "candidate_family", "has_negative_controls": True, "confidence": 0.9, "hit_count": 3}]
        both_matches = [
            {"family": "fam", "status": "candidate_family", "has_negative_controls": True, "confidence": 0.9, "hit_count": 3},
            {"family": "fam2", "status": "candidate_family", "has_negative_controls": True, "confidence": 0.8, "hit_count": 2},
        ]
        sel.write_text(json.dumps({"status": "blocked_insufficient_c_discriminating_rows", "selected_count": 15, "eligible_count": 15, "source_demand_requests": [{"family": "fam", "recommended_action": "source_similar_static_fail_rows"}, {"family": "fam2", "recommended_action": "source_similar_static_fail_rows"}]}) + "\n")

        ck.write_text(static_record("r1", "public_tool_static", fam_match))
        public_only_blocked = build(ns(run_id="public_only"))
        assert public_only_blocked["job_count"] == 0, public_only_blocked
        assert public_only_blocked["strict_static_fail_row_count"] == 0, public_only_blocked

        ck.write_text(strict_pair("r1", fam_match))
        result = build(ns(run_id="strict"))
        assert result["job_count"] == 1, result
        assert result["jobs"][0]["payload"]["c_supply_candidate_rows"] == ["r1"], result
        assert result["jobs"][0]["payload"]["runtime"] in {"codex", "claude"}, result
        assert result["jobs"][0]["payload"]["operator_contract"]["source_cue_check_status"] == "pass", result
        assert "recent_probe_feedback" in result["jobs"][0]["payload"]["operator_contract"]["source_demand"], result
        assert result["jobs"][0]["payload"]["allowed_write_paths"] == [result["jobs"][0]["payload"]["family_spec_patch_target"]], result
        assert result["jobs"][0]["payload"]["runtime_routing_receipt"]["schema"] == "leanmill-agent-runtime-routing-receipt-v1", result
        assert "population_elo_routing_prior" in result["jobs"][0]["payload"], result

        ck.write_text(strict_pair("r1", fam_match, governed_exit="ratified_closure", governed_extra={"governed_tactic": "exact trivial"}))
        governed_positive_blocked = build(ns(run_id="governed_positive"))
        assert governed_positive_blocked["job_count"] == 0, governed_positive_blocked
        assert governed_positive_blocked["strict_static_fail_row_count"] == 0, governed_positive_blocked

        ck.write_text(strict_pair("r1", both_matches))
        batch_deduped = build(ns(run_id="batch"))
        assert batch_deduped["job_count"] == 1, batch_deduped
        assert batch_deduped["jobs"][0]["payload"]["family"] == "fam", batch_deduped

        dominant_matches = [
            {"family": "fam2", "status": "candidate_family", "has_negative_controls": True, "confidence": 0.95, "hit_count": 4},
            {"family": "fam", "status": "candidate_family", "has_negative_controls": True, "confidence": 0.9, "hit_count": 3},
        ]
        ck.write_text(strict_pair("r1", dominant_matches))
        dominant_family = build(ns(run_id="dominant"))
        assert dominant_family["job_count"] == 1, dominant_family
        assert dominant_family["jobs"][0]["payload"]["family"] == "fam2", dominant_family
        assert dominant_family["jobs"][0]["payload"]["c_supply_candidates"][0]["candidate_family_selection"] == "current_slice_top_family_then_highest_confidence", dominant_family

        sel.write_text(json.dumps({"status": "blocked_insufficient_c_discriminating_rows", "rows": [{"row_id": "r1", "eligible": False, "best_static_family_match": "fam", "rejection_reasons": ["no_positive_family_template"]}], "source_demand_requests": [{"family": "fam", "recommended_action": "source_similar_static_fail_rows"}, {"family": "fam2", "recommended_action": "source_similar_static_fail_rows"}]}) + "\n")
        top_family_filtered = build(ns(run_id="top"))
        assert top_family_filtered["job_count"] == 1, top_family_filtered
        assert top_family_filtered["jobs"][0]["payload"]["family"] == "fam", top_family_filtered
        assert top_family_filtered["current_selection_top_family_row_count"] == 1, top_family_filtered

        global DEFAULT_POPULATION_ELO
        old_population_elo = DEFAULT_POPULATION_ELO
        try:
            DEFAULT_POPULATION_ELO = str(root / "population_elo.json")
            sel.write_text(json.dumps({"status": "blocked_insufficient_c_discriminating_rows", "source_demand_requests": [{"family": "fam", "recommended_action": "source_similar_static_fail_rows"}, {"family": "fam2", "recommended_action": "source_similar_static_fail_rows"}]}) + "\n")
            ck.write_text(strict_pair("r1", fam_match) + strict_pair("r2", fam2_match))
            Path(DEFAULT_POPULATION_ELO).write_text(json.dumps({"ratings": [{"contestant": "family:fam", "rating": 990.0, "p_ucb_priority": 990.0, "games": 3}, {"contestant": "family:fam2", "rating": 1010.0, "p_ucb_priority": 1100.0, "games": 1}]}) + "\n")
            elo_ordered = build(ns(run_id="elo", rows_per_family=1))
            assert elo_ordered["jobs"][0]["payload"]["family"] == "fam2", elo_ordered
            assert elo_ordered["jobs"][0]["payload"]["population_elo_routing_prior"]["contestant"] == "family:fam2", elo_ordered
        finally:
            DEFAULT_POPULATION_ELO = old_population_elo

        ck.write_text(strict_pair("r1", fam_match))
        sel.write_text(json.dumps({"status": "blocked_pending_probe_or_static_sweep", "selected_rows_order": ["r1"], "rows": [{"row_id": "r1", "eligible": True, "c_discriminating_evidence_status": "c_discriminating_structural_candidate_pending_probe"}], "source_demand_requests": [{"family": "fam", "recommended_action": "source_similar_static_fail_rows"}]}) + "\n")
        pending_probe_allowed = build(ns(run_id="pending_probe"))
        assert pending_probe_allowed["job_count"] == 1, pending_probe_allowed

        sel.write_text(json.dumps({"status": "blocked_insufficient_c_discriminating_rows", "selected_rows_order": ["r1"], "rows": [{"row_id": "r1", "eligible": True, "probe_credit_ready": True, "c_discriminating_evidence_status": "c_discriminating_probe_verified"}], "source_demand_requests": [{"family": "fam", "recommended_action": "source_similar_static_fail_rows"}]}) + "\n")
        duplicate_blocked = build(ns(run_id="duplicate"))
        assert duplicate_blocked["job_count"] == 0, duplicate_blocked

        sel.write_text(json.dumps({"status": "blocked_insufficient_c_discriminating_rows", "rows": [{"row_id": "r1", "eligible": False, "rejection_reasons": ["static_tool_positive"]}], "source_demand_requests": [{"family": "fam", "recommended_action": "source_similar_static_fail_rows"}]}) + "\n")
        current_selector_blocked = build(ns(run_id="selector"))
        assert current_selector_blocked["job_count"] == 0, current_selector_blocked
        assert current_selector_blocked["current_selection_disqualified_row_count"] == 1, current_selector_blocked

        sel.write_text(json.dumps({"status": "blocked_insufficient_c_discriminating_rows", "rows": [{"row_id": "r1", "eligible": False, "rejection_reasons": ["family_spec_probe_terminal_nonuseful:probe_no_positive_signal"]}], "source_demand_requests": [{"family": "fam", "recommended_action": "source_similar_static_fail_rows"}]}) + "\n")
        terminal_nonuseful_blocked = build(ns(run_id="terminal"))
        assert terminal_nonuseful_blocked["job_count"] == 0, terminal_nonuseful_blocked
        assert terminal_nonuseful_blocked["current_selection_disqualified_row_count"] == 1, terminal_nonuseful_blocked

        sel.write_text(json.dumps({"status": "blocked_insufficient_c_discriminating_rows", "rows": [{"row_id": "r1", "eligible": False, "best_static_family_match": "fam", "rejection_reasons": ["no_positive_family_template"]}], "source_demand_requests": [{"family": "fam", "recommended_action": "source_similar_static_fail_rows"}]}) + "\n")
        template_blocker_allowed = build(ns(run_id="template"))
        assert template_blocker_allowed["job_count"] == 1, template_blocker_allowed
        assert template_blocker_allowed["current_selection_disqualified_row_count"] == 0, template_blocker_allowed

        qdb = str(root / "q.sqlite")
        qcx = work_queue.connect(qdb)
        probe_payload = {
            "probe_lane": "family_spec",
            "family": "fam",
            "learning_unit_exit": "tested_no_positive_signal",
            "row_outcomes": [{"row_id": "r1", "learning_unit_exit": "tested_no_positive_signal"}],
        }
        work_queue.enqueue(qcx, kind="repair_canary_probe", priority=1, payload={"work_id": "probe:fam:r1", **probe_payload})
        work_queue.update_status(qcx, work_id="probe:fam:r1", status="done", payload_update=probe_payload)
        queue_memory_blocked = build(ns(run_id="queue", queue_db=qdb))
        assert queue_memory_blocked["job_count"] == 0, queue_memory_blocked
        assert queue_memory_blocked["queue_disqualified_pair_count"] == 1, queue_memory_blocked
        qcx = work_queue.connect(qdb)
        work_queue.enqueue(qcx, kind="agent_repair_task", priority=1, payload={
            "work_id": "open-template:fam",
            "family": "fam",
            "family_spec_patch_mode": "c_supply_template_backfill",
        })
        qcx.close()
        ck.write_text(strict_pair("r2", fam_match))
        rows.write_text(json.dumps({"rows": [{"row_id": "r2", "source_file": str(r2)}]}) + "\n")
        sel.write_text(json.dumps({"status": "blocked_insufficient_c_discriminating_rows", "source_demand_requests": [{"family": "fam", "recommended_action": "source_similar_static_fail_rows"}]}) + "\n")
        open_job_blocked = build(ns(run_id="open_job", queue_db=qdb, enqueue=True, cooldown_s=0, max_enqueued=1))
        assert open_job_blocked["enqueued"] == 0, open_job_blocked
        assert open_job_blocked["skip_counts"].get("open_or_recent_same_family") == 1, open_job_blocked
        assert _contract_upgrade_retirement({"exit_kind": "retired_for_contract_upgrade"})
        assert _contract_upgrade_retirement({"contract_upgrade_required": True})
        assert not _contract_upgrade_retirement({"exit_kind": "operator_required"})
    print("leanmill_c_supply_template_backfill self-test PASS")
    return 0

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selection", default=DEFAULT_SELECTION)
    ap.add_argument("--checkpoint", default=DEFAULT_CHECKPOINT)
    ap.add_argument("--row-context", default=DEFAULT_ROW_CONTEXT)
    ap.add_argument("--spec-dir", default=DEFAULT_SPEC_DIR)
    ap.add_argument("--queue-db", default=work_queue.DEFAULT_DB)
    ap.add_argument("--events", default=work_queue.DEFAULT_EVENTS)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--run-id", default="")
    ap.add_argument("--max-jobs", type=int, default=8)
    ap.add_argument("--rows-per-family", type=int, default=2)
    ap.add_argument("--agent-runtime", choices=["balanced", "codex", "claude"], default="balanced")
    ap.add_argument("--factory-policy", default=FACTORY_POLICY)
    ap.add_argument("--policy-profile", default="")
    ap.add_argument("--agent-max-iterations", type=int, default=3)
    ap.add_argument("--agent-max-wall-time-s", type=int, default=1200)
    ap.add_argument("--agent-max-attempts", type=int, default=2)
    ap.add_argument("--enqueue", action="store_true")
    ap.add_argument("--max-enqueued", type=int, default=0)
    ap.add_argument("--cooldown-s", type=int, default=3600)
    ap.add_argument("--retry-existing", action="store_true")
    ap.add_argument("--include-all-candidate-families", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--min-candidate-hit-count", type=int, default=2)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    result = build(args)
    print(json.dumps({
        "out": args.out,
        "dry_run": result["dry_run"],
        "job_count": result["job_count"],
        "enqueued": result["enqueued"],
        "skip_counts": result["skip_counts"],
        "candidate_counts_by_family": result["candidate_counts_by_family"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
