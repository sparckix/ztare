#!/usr/bin/env python3
"""Queue worker for bounded LeanMill LLM proposal artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any

import leanmill_work_queue as work_queue
from leanmill_factory_config import FACTORY_POLICY as DEFAULT_FACTORY_POLICY, priority_value
from leanmill_source_query_contract import source_queries_from_proposal
from leanmill_source_search_integrator import _queries_pass_gate

REPO = Path(__file__).resolve().parents[4]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from src.ztare.common.llm_runtime import LLMRuntime, resolve_model_id  # noqa: E402
from src.ztare.common.subscription_agent_runtime import (  # noqa: E402
    redact_prompt_command,
    run_subscription_agent_with_recovery,
)
from src.ztare.leanmill.common import read_json, run as common_run, write_json_atomic, write_text_atomic  # noqa: E402
from src.ztare.supervisor.llm_budget_guard import (  # noqa: E402
    LLMBudgetDenied,
    LLMBudgetSession,
)


DEFAULT_DATA_DIR = "analytics/public/leanmill/dashboard_data"
DEFAULT_PROPOSAL_GATE = f"{DEFAULT_DATA_DIR}/llm_proposal_gate.json"
DEFAULT_TRACE_DIR = f"{DEFAULT_DATA_DIR}/llm_proposal_traces"
DEFAULT_ALLOCATOR = f"{DEFAULT_DATA_DIR}/source_family_allocator.json"


def _queue_priority(args: argparse.Namespace, key: str, fallback: int) -> int:
    return priority_value(
        path=getattr(args, "factory_policy", DEFAULT_FACTORY_POLICY),
        namespace="work_queue",
        key=key,
        fallback=fallback,
    )


def _run(cmd: list[str]) -> dict[str, Any]:
    return common_run(cmd, stdout_tail_chars=2000, stderr_tail_chars=2000)


def _read_json(path: str) -> dict[str, Any]:
    obj = read_json(path, default={})
    return obj if isinstance(obj, dict) else {}


def _no_spend_family(allocator_path: str, family: str) -> bool:
    if not family:
        return False
    for rec in _read_json(allocator_path).get("allocations") or []:
        if str(rec.get("family") or "") == family:
            return str(rec.get("recommended_action") or "") == "do_not_spend_until_new_evidence"
    return False


def _extract_json_object_or_list(text: str) -> Any:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass
    decoder = json.JSONDecoder()
    candidates: list[Any] = []
    starts = [idx for idx, ch in enumerate(stripped) if ch in "{["]
    for start in starts:
        try:
            obj, _end = decoder.raw_decode(stripped[start:])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, (dict, list)):
            candidates.append(obj)
    if candidates:
        return candidates[-1]
    if not starts:
        raise ValueError("model output did not contain JSON")
    raise ValueError("model output JSON could not be parsed")


def _read_prompt(payload: dict[str, Any]) -> str:
    if str(payload.get("prompt") or ""):
        return str(payload["prompt"])
    if str(payload.get("prompt_path") or ""):
        return Path(str(payload["prompt_path"])).read_text(errors="ignore")
    family = str(payload.get("family") or "unknown_family")
    proposal_type = str(payload.get("proposal_type") or "repair_template")
    expected = str(payload.get("expected_outcome") or "closure")
    context = json.dumps(payload.get("context") or {}, indent=2, sort_keys=True)
    if proposal_type == "source_request":
        return f"""Return exactly one JSON object for a LeanMill source_request proposal.

Required fields:
family, proposal_type, hypothesis, credit_type, expected_outcome, source_query, target_row_ids.

Hard requirements:
- proposal_type must be "source_request".
- credit_type must be "none".
- expected_outcome must be "source_request".
- source_query must be a list of 3-8 typed query objects.
- Each source_query object must use schema "leanmill-source-query-contract-v1" and kind "declaration_ref", "theorem_shape", or "semantic_search".
- For "declaration_ref", provide decl_name as a namespaced Lean declaration, e.g. "ENNReal.coe_tsum".
- For "theorem_shape", provide query as a compact Lean theorem/lemma shape or statement.
- target_row_ids must be a list of concrete active target/sibling row IDs for the search to bind against.
- Avoid generic requests like "find source" or "needed artifact".
- Do not use LeanMill schema names, station names, receipt fields, or process language as queries.
- The hypothesis must explain which row/family shape the queries target and what source-order/target-context risk to screen.
- Do not claim proof value, ratification, validation, or source credit.

Family: {family}

Context:
{context}
"""
    if proposal_type == "decomposition":
        return f"""Return exactly one JSON object for a LeanMill decomposition proposal.

Required fields:
family, proposal_type, hypothesis, credit_type, expected_outcome.

Hard requirements:
- proposal_type must be "decomposition".
- credit_type must be "none".
- expected_outcome must be "hold" or "retire".
- hypothesis must name the blocked causal edge, the next executable check, and the kill/hold condition.
- Do not claim proof value, ratification, validation, or source credit.

Family: {family}

Context:
{context}
"""
    return f"""Return exactly one JSON object matching the LeanMill proposal gate schema.

Required fields:
family, proposal_type, hypothesis, credit_type, expected_outcome.
For repair_template proposals also include positive_template and negative_control.
For exact_gap or falsifier proposals include formal_statement or gap_statement.

Family: {family}
Proposal type: {proposal_type}
Expected outcome: {expected}
Credit type: {payload.get('credit_type') or 'repair_canary'}

Context:
{context}
"""


def _semantic_query_from_payload(payload: dict[str, Any], prompt: str) -> str:
    context = payload.get("context") if isinstance(payload.get("context"), dict) else {}
    pieces = [
        f"family: {payload.get('family') or context.get('family') or ''}",
        f"proposal_type: {payload.get('proposal_type') or context.get('proposal_type') or ''}",
        f"expected_exit: {payload.get('expected_exit') or context.get('expected_exit') or ''}",
        f"expected_outcome: {payload.get('expected_outcome') or context.get('expected_outcome') or ''}",
    ]
    for key in (
        "target_row_ids",
        "target_rows",
        "row_id",
        "target_theorem_name",
        "goal",
        "goal_block",
        "formal_statement",
        "gap_statement",
        "blocked_edge",
        "recent_probe_feedback",
        "scoreboard_summary",
    ):
        value = payload.get(key, context.get(key))
        if value:
            pieces.append(f"{key}: {json.dumps(value, sort_keys=True, default=str)[:3000]}")
    pieces.append("prompt:")
    pieces.append(prompt[:4000])
    return "\n".join(str(p) for p in pieces if str(p).strip())


def _augment_prompt_with_semantic_premise_shelf(payload: dict[str, Any], prompt: str) -> str:
    proposal_type = str(payload.get("proposal_type") or "")
    expected_outcome = str(payload.get("expected_outcome") or "")
    expected_exit = str(payload.get("expected_exit") or "")
    # Source scouting needs theorem-shaped queries; premise retrieval is useful
    # but should not displace the query contract. Keep the shelf on proof or
    # decomposition routes.
    if (
        proposal_type == "source_request"
        or expected_outcome == "source_request"
        or expected_exit == "source_request"
    ) and expected_exit not in {"family_spec_patch", "repaired_canary"}:
        return prompt
    try:
        from src.ztare.leanmill.semantic_premise_shelf import (
            build_semantic_premise_shelf,
            render_semantic_premise_shelf,
            semantic_premise_shelf_enabled,
        )
    except Exception:
        return prompt
    if not semantic_premise_shelf_enabled():
        return prompt
    shelf = build_semantic_premise_shelf(_semantic_query_from_payload(payload, prompt))
    rendered = render_semantic_premise_shelf(shelf)
    return (
        f"{prompt.rstrip()}\n\n"
        "Additional proof-loop retrieval context:\n"
        f"{rendered}\n\n"
        "Use the shelf only as candidate premise context. It is not proof credit, "
        "not source credit, and does not relax matched negative-control or Governance Gate requirements.\n"
    )


def _sanitize_model_proposal(parsed: Any, payload: dict[str, Any]) -> Any:
    force_credit = str(payload.get("force_credit_type") or "")
    allowed_types = {str(x) for x in (payload.get("allowed_proposal_types") or []) if str(x)}

    def fallback_hypothesis(out: dict[str, Any]) -> str:
        parts: list[str] = []
        for key in ("hypothesis", "blocked_edge", "retire_reason", "exact_gap", "gap_statement", "formal_statement"):
            value = str(out.get(key) or "").strip()
            if value:
                parts.append(value)
        target_rows = out.get("target_row_ids") or out.get("target_rows") or []
        if isinstance(target_rows, str):
            target_rows = [target_rows]
        if isinstance(target_rows, list) and target_rows:
            rows = ", ".join(str(x) for x in target_rows[:6] if str(x))
            if rows:
                parts.append(f"target rows: {rows}")
        next_probe = out.get("next_probe_contract") or {}
        if isinstance(next_probe, dict):
            contract = str(next_probe.get("contract") or next_probe.get("mode") or "").strip()
            if contract:
                parts.append(contract)
        if not parts:
            family = str(out.get("family") or payload.get("family") or "unknown_family")
            ptype = str(out.get("proposal_type") or payload.get("proposal_type") or "decomposition")
            parts.append(f"{family} {ptype} proposal requires bounded downstream validation")
        return " | ".join(parts)

    def sanitize_one(obj: Any) -> Any:
        if not isinstance(obj, dict):
            return obj
        out = dict(obj)
        if not str(out.get("family") or "") and str(payload.get("family") or ""):
            out["family"] = str(payload.get("family"))
        if force_credit:
            out["credit_type"] = force_credit
        if allowed_types and str(out.get("proposal_type") or "") not in allowed_types:
            out["proposal_type"] = "decomposition" if "decomposition" in allowed_types else sorted(allowed_types)[0]
            out["expected_outcome"] = "hold"
            out["hypothesis"] = (
                str(out.get("hypothesis") or "")
                + " [sanitized: proposal_type outside allowed set for source transcript review]"
            ).strip()
        if str(out.get("expected_outcome") or "") not in {"closure", "exact_gap", "falsifier", "source_request", "retire", "hold"}:
            out["expected_outcome"] = "hold"
        if not str(out.get("hypothesis") or "").strip():
            out["hypothesis"] = fallback_hypothesis(out)
        if str(out.get("proposal_type") or "") in {"exact_gap", "falsifier"}:
            has_statement = bool(str(out.get("formal_statement") or out.get("gap_statement") or "").strip())
            if not has_statement and str(out.get("expected_outcome") or "") == "hold":
                out["proposal_type"] = "decomposition"
                out["hypothesis"] = (
                    str(out.get("hypothesis") or "")
                    + " [sanitized: untyped gap/falsifier hold routed as decomposition hold]"
                ).strip()
            elif not has_statement:
                pieces = [
                    str(out.get("missing_interface") or out.get("candidate_lemma") or out.get("candidate_missing_lemma") or "").strip(),
                    str(out.get("next_executable_check") or "").strip(),
                    str(out.get("blocked_edge") or "").strip(),
                    str(out.get("hypothesis") or "").strip(),
                ]
                out["gap_statement"] = " | ".join(piece for piece in pieces if piece)
        return out

    if isinstance(parsed, list):
        return [sanitize_one(obj) for obj in parsed]
    return sanitize_one(parsed)


def _read_json_any(path: str) -> Any:
    return read_json(path)


def _slug(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value).strip("_") or "item"


def _trace_stem(work_id: str) -> str:
    slug = _slug(work_id)
    digest = hashlib.sha256(work_id.encode("utf-8")).hexdigest()[:12]
    if len(slug) > 96:
        slug = slug[:96].rstrip("_")
    return f"{slug}_{digest}"


def _redact_local_paths(text: str) -> str:
    if not text:
        return ""
    return text.replace(str(REPO), "<repo>").replace(str(Path.home()), "$HOME")


def _source_queries_from_proposal(obj: dict[str, Any], *, allow_hypothesis_fallback: bool = False) -> list[Any]:
    if "source_query" in obj or "source_queries" in obj or "queries" in obj:
        return source_queries_from_proposal(obj, allow_hypothesis_fallback=allow_hypothesis_fallback)
    if "query" in obj:
        return source_queries_from_proposal({"source_query": obj.get("query")}, allow_hypothesis_fallback=allow_hypothesis_fallback)
    return source_queries_from_proposal(obj, allow_hypothesis_fallback=allow_hypothesis_fallback)


def _target_rows_from_proposal(obj: dict[str, Any]) -> list[str]:
    raw = obj.get("target_row_ids") or obj.get("target_rows") or []
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw:
        row_id = str(item or "").strip()
        if row_id and row_id not in out:
            out.append(row_id)
    return out[:20]


def _accepted_source_queries(query_quality: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for item in query_quality:
        if not isinstance(item, dict) or not bool(item.get("accepted")):
            continue
        query = str(item.get("normalized_query") or item.get("query") or "").strip()
        if query and query not in out:
            out.append(query)
    return out


def _enqueue_source_search_tasks(args: argparse.Namespace, *, proposal_path: str, parent_work_id: str) -> list[dict[str, Any]]:
    parsed = _read_json_any(proposal_path)
    proposals = parsed if isinstance(parsed, list) else [parsed]
    cx = work_queue.connect(args.queue_db)
    enqueued: list[dict[str, Any]] = []
    for idx, proposal in enumerate(proposals):
        if not isinstance(proposal, dict):
            continue
        if str(proposal.get("proposal_type") or "") != "source_request":
            continue
        family = str(proposal.get("family") or "unknown_family")
        queries = _source_queries_from_proposal(proposal)
        target_row_ids = _target_rows_from_proposal(proposal)
        queries_ok, query_quality = _queries_pass_gate(queries, family)
        accepted_queries = _accepted_source_queries(query_quality)
        rejected_query_quality = [q for q in query_quality if isinstance(q, dict) and not bool(q.get("accepted"))]
        if len(accepted_queries) < 3 or not target_row_ids:
            work_queue.append_event(args.events, {
                "event_type": "source_search_task_not_enqueued_query_gate",
                "work_id": parent_work_id,
                "payload": {
                    "family": family,
                    "proposal_path": proposal_path,
                    "query_count": len(queries),
                    "accepted_query_count": len(accepted_queries),
                    "target_row_count": len(target_row_ids),
                    "query_quality": query_quality,
                    "reason": "source_request_queries_must_be_three_to_eight_theorem_shaped_queries_and_target_rows",
                },
                "artifact_paths": [proposal_path],
            })
            continue
        work_id = f"source_search:{_slug(family)}:{_slug(parent_work_id)}:{idx}"
        payload = {
            "work_id": work_id,
            "station": "source_qualification",
            "family": family,
            "queries": accepted_queries,
            "target_row_ids": target_row_ids,
            "query_quality": [q for q in query_quality if isinstance(q, dict) and bool(q.get("accepted"))],
            "rejected_query_quality": rejected_query_quality,
            "original_query_count": len(queries),
            "parent_work_id": parent_work_id,
            "source_scout_mode": "subscription_public_external" if "external_source_scout" in parent_work_id else "",
            "proposal_path": proposal_path,
            "expected_exit": "qualified_source_or_rejected_with_reason",
            "credit_boundary": {
                "source_search_has_no_proof_credit": True,
                "proof_credit_authority": "governance_gate",
            },
        }
        before = cx.total_changes
        work_queue.enqueue(
            cx,
            kind="source_search_task",
            priority=_queue_priority(args, "source_search_from_llm_proposal", 92),
            payload=payload,
            max_attempts=2,
        )
        if cx.total_changes > before:
            work_queue.append_event(args.events, {
                "event_type": "source_search_task_enqueued",
                "work_id": work_id,
                "payload": {
                    "family": family,
                    "parent_work_id": parent_work_id,
                    "query_count": len(accepted_queries),
                    "raw_query_count": len(queries),
                    "rejected_query_count": len(rejected_query_quality),
                    "target_row_count": len(target_row_ids),
                    "query_gate_mode": "prune_rejected_queries",
                },
                "artifact_paths": [proposal_path],
            })
            enqueued.append({"work_id": work_id, "family": family, "query_count": len(accepted_queries), "target_row_count": len(target_row_ids)})
    return enqueued


def _enqueue_decomposition_followups(args: argparse.Namespace, *, proposal_path: str, parent_work_id: str) -> list[dict[str, Any]]:
    parsed = _read_json_any(proposal_path)
    proposals = parsed if isinstance(parsed, list) else [parsed]
    cx = work_queue.connect(args.queue_db)
    enqueued: list[dict[str, Any]] = []
    for idx, proposal in enumerate(proposals):
        if not isinstance(proposal, dict):
            continue
        if str(proposal.get("proposal_type") or "") != "decomposition":
            continue
        if str(proposal.get("expected_outcome") or "") == "retire":
            continue
        next_probe = proposal.get("next_probe_contract")
        candidate_artifacts = proposal.get("candidate_artifacts") or proposal.get("candidate_checks") or []
        target_rows = _target_rows_from_proposal(proposal)
        if not isinstance(next_probe, dict) and not candidate_artifacts:
            continue
        family = str(proposal.get("family") or "unknown_family")
        work_id = f"family_spec_patch:{_slug(family)}:{_slug(parent_work_id)}:{idx}"
        if cx.execute("SELECT 1 FROM work_items WHERE work_id=? LIMIT 1", (work_id,)).fetchone() is not None:
            continue
        prompt = f"""Convert this validated no-credit LeanMill decomposition proposal into the next bounded family-spec action.

Rules:
- This task has no proof credit and cannot ratify closure, exact gap, or falsifier value.
- Do not edit scoreboards, registries, governance reports, or research logs.
- Prefer a narrow patch to `analytics/public/leanmill/repair_families/{family}.yaml` only if the proposal contains enough executable positive/negative-control detail to improve a reusable family-spec probe.
- If the proposal is not executable enough for a spec patch, return exactly one JSON object with `exit_kind:"operator_required"` or `exit_kind:"retired"`, `credit_type:"none"`, and the blocked edge.
- Preserve matched negative-control ideas and target-row constraints.

Family: {family}
Parent proposal work: {parent_work_id}
Target rows: {json.dumps(target_rows, sort_keys=True)}
Proposal artifact: {proposal_path}

Validated decomposition proposal:
{json.dumps(proposal, indent=2, sort_keys=True)}
"""
        payload = {
            "work_id": work_id,
            "station": "repair_registry",
            "family": family,
            "runtime": "codex",
            "agent_id": "leanmill_codex_family_spec_patch",
            "expected_exit": "family_spec_patch",
            "task": prompt,
            "allowed_paths": [
                "analytics/public/leanmill/repair_families",
                "analytics/public/leanmill/dashboard_data",
                "scripts/public/control",
                "/tmp/rung1",
            ],
            "max_iterations": 3,
            "max_wall_time_s": 1200,
            "proof_affecting": False,
            "requires_negative_control": False,
            "parent_work_id": parent_work_id,
            "proposal_path": proposal_path,
            "target_row_ids": target_rows,
            "credit_boundary": {
                "credit_type": "none",
                "proof_credit_authority": "governance_gate",
                "worker_can_self_ratify": False,
            },
        }
        before = cx.total_changes
        work_queue.enqueue(
            cx,
            kind="agent_repair_task",
            priority=_queue_priority(args, "decomposition_followup_agent", 235),
            payload=payload,
            max_attempts=1,
        )
        if cx.total_changes > before:
            work_queue.append_event(args.events, {
                "event_type": "decomposition_followup_agent_enqueued",
                "work_id": work_id,
                "payload": {
                    "family": family,
                    "parent_work_id": parent_work_id,
                    "proposal_path": proposal_path,
                    "expected_exit": "family_spec_patch",
                    "target_row_count": len(target_rows),
                },
                "artifact_paths": [proposal_path],
            })
            enqueued.append({"work_id": work_id, "family": family, "target_row_count": len(target_rows)})
    return enqueued


def _enqueue_gap_or_falsifier_governance(args: argparse.Namespace, *, proposal_path: str, parent_work_id: str) -> list[dict[str, Any]]:
    parsed = _read_json_any(proposal_path)
    proposals = parsed if isinstance(parsed, list) else [parsed]
    cx = work_queue.connect(args.queue_db)
    trace_dir = Path(args.trace_dir)
    trace_dir.mkdir(parents=True, exist_ok=True)
    enqueued: list[dict[str, Any]] = []
    for idx, proposal in enumerate(proposals):
        if not isinstance(proposal, dict):
            continue
        proposal_type = str(proposal.get("proposal_type") or "")
        if proposal_type not in {"exact_gap", "falsifier"}:
            continue
        family = str(proposal.get("family") or "unknown_family")
        candidate_kind = proposal_type
        candidate_path = trace_dir / f"{_trace_stem(parent_work_id)}_governance_{candidate_kind}_{idx}.json"
        candidate = {
            "schema": "leanmill-governance-candidate-v1",
            "candidate_kind": candidate_kind,
            "target_kind": "llm_proposal",
            "expected_outcome": candidate_kind,
            "family": family,
            "source_agent_work_id": parent_work_id,
            "artifact_paths": [proposal_path],
            "formal_statement": str(proposal.get("formal_statement") or ""),
            "gap_statement": str(proposal.get("gap_statement") or proposal.get("hypothesis") or ""),
            "blocked_edge": str(proposal.get("blocked_edge") or ""),
            "evidence": {
                "proposal_path": proposal_path,
                "parent_work_id": parent_work_id,
                "proposal_type": proposal_type,
                "candidate_artifacts": proposal.get("candidate_artifacts") or proposal.get("candidate_checks") or [],
                "target_row_ids": _target_rows_from_proposal(proposal),
            },
            "proof_credit_authority": "governance_gate",
            "candidate_note": (
                "LLM proposal candidate only. This is not proof credit unless the "
                "Governance Gate accepts the candidate under its shape and replay rules."
            ),
        }
        write_json_atomic(candidate_path, candidate)
        kind = "govern_exact_gap" if candidate_kind == "exact_gap" else "govern_falsifier"
        work_id = f"{kind}:{_slug(family)}:{_slug(parent_work_id)}:{idx}"
        before = cx.total_changes
        work_queue.enqueue(
            cx,
            kind=kind,
            priority=_queue_priority(args, "agent_output_ingester_direct_governance", 910),
            payload={
                "work_id": work_id,
                "family": family,
                "candidate": str(candidate_path),
                "candidate_path": str(candidate_path),
                "source_agent_work_id": parent_work_id,
                "proposal_path": proposal_path,
                "proof_credit_authority": "governance_gate",
                "expected_exit": f"governed_{candidate_kind}_or_rejected",
            },
            max_attempts=1,
        )
        if cx.total_changes > before:
            work_queue.append_event(args.events, {
                "event_type": "llm_proposal_governance_candidate_enqueued",
                "work_id": work_id,
                "payload": {
                    "family": family,
                    "parent_work_id": parent_work_id,
                    "proposal_path": proposal_path,
                    "candidate_kind": candidate_kind,
                    "candidate_path": str(candidate_path),
                },
                "artifact_paths": [proposal_path, str(candidate_path)],
            })
            enqueued.append({"work_id": work_id, "family": family, "candidate_kind": candidate_kind, "candidate_path": str(candidate_path)})
    return enqueued


def _call_codex_cli_fallback(
    args: argparse.Namespace,
    *,
    payload: dict[str, Any],
    prompt: str,
    work_id: str,
    failure_reason: str,
) -> dict[str, Any]:
    if not args.allow_codex_cli_fallback:
        return {
            "ok": False,
            "exit_kind": "llm_api_failed",
            "reason": failure_reason,
            "model_called": False,
            "codex_cli_fallback_attempted": False,
            "artifact_paths": [],
        }
    fallback_prompt = f"""Return the LeanMill proposal JSON requested below.

Return exactly one JSON object or JSON list. Do not edit files. Do not run tools. Do not claim proof value.
The JSON must satisfy the requested LeanMill proposal schema in the prompt below.

Request:
{prompt}
"""
    run = run_subscription_agent_with_recovery(
        runtime="codex",
        prompt=fallback_prompt,
        agent_id="leanmill_codex_cli_llm_fallback",
        repo=REPO,
        session_state=None,
        timeout_seconds=args.codex_cli_fallback_timeout_s,
        codex_model_env="ZTARE_CODEX_LLM_FALLBACK_MODEL",
        default_codex_model=args.codex_cli_fallback_model,
        codex_sandbox="read-only",
    )
    trace_dir = Path(args.trace_dir)
    trace_dir.mkdir(parents=True, exist_ok=True)
    stem = _trace_stem(work_id)
    raw_path = trace_dir / f"{stem}_codex_cli_fallback_raw.txt"
    proposal_path = trace_dir / f"{stem}_codex_cli_fallback_proposal.json"
    command_ref = f"<prompt:{work_id}:codex-cli-fallback>"
    write_text_atomic(
        raw_path,
        "\n".join([
            "runtime=codex_cli_fallback",
            f"returncode={run.result.returncode}",
            f"initial_command={_redact_local_paths(' '.join(redact_prompt_command(run.initial_command, command_ref)))}",
            f"final_command={_redact_local_paths(' '.join(redact_prompt_command(run.final_command, command_ref)))}",
            f"recovery_note={run.recovery_note or ''}",
            "",
            "--- stdout ---",
            _redact_local_paths(run.result.stdout or ""),
            "",
            "--- stderr ---",
            _redact_local_paths(run.result.stderr or ""),
        ]),
    )
    if run.result.returncode != 0:
        return {
            "ok": False,
            "exit_kind": "codex_cli_fallback_failed",
            "reason": failure_reason,
            "codex_cli_fallback_attempted": True,
            "codex_cli_returncode": run.result.returncode,
            "model_called": False,
            "artifact_paths": [str(raw_path)],
        }
    try:
        parsed = _sanitize_model_proposal(_extract_json_object_or_list(run.result.stdout or ""), payload)
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "exit_kind": "codex_cli_fallback_parse_failed",
            "reason": f"{failure_reason}; fallback_parse_error={type(exc).__name__}: {exc}",
            "codex_cli_fallback_attempted": True,
            "model_called": False,
            "artifact_paths": [str(raw_path)],
        }
    write_json_atomic(proposal_path, parsed)
    return {
        "ok": True,
        "model_called": False,
        "codex_cli_fallback_attempted": True,
        "codex_cli_fallback_used": True,
        "codex_cli_model": args.codex_cli_fallback_model,
        "api_failure_reason": failure_reason,
        "proposal_path": str(proposal_path),
        "artifact_paths": [str(raw_path), str(proposal_path)],
    }


def _call_model(args: argparse.Namespace, payload: dict[str, Any], work_id: str) -> dict[str, Any]:
    prompt = _augment_prompt_with_semantic_premise_shelf(payload, _read_prompt(payload))
    if not args.allow_paid_llm:
        if not args.allow_codex_cli_fallback:
            return {
                "ok": True,
                "exit_kind": "operator_required",
                "reason": "model call requires --allow-paid-llm",
                "model_called": False,
                "codex_cli_fallback_attempted": False,
                "artifact_paths": [],
            }
        return _call_codex_cli_fallback(
            args,
            payload=payload,
            prompt=prompt,
            work_id=work_id,
            failure_reason="model call requires --allow-paid-llm",
        )
    model_family = str(payload.get("model_family") or args.model_family)
    model_id = str(payload.get("model_id") or resolve_model_id(model_family))
    try:
        payload_requested_max_tokens = int(payload.get("max_output_tokens") or 0)
    except (TypeError, ValueError):
        payload_requested_max_tokens = 0
    max_tokens = int(args.max_output_tokens)
    budget = LLMBudgetSession(
        allow_paid=True,
        max_total_cost_usd=args.max_total_cost_usd,
        role_id=args.role_id,
        session_id=args.session_id,
        action="leanmill_llm_proposal",
    )
    try:
        estimate = budget.preflight(
            prompt=prompt,
            model_name=model_id,
            max_output_tokens=max_tokens,
            label=work_id,
        )
    except LLMBudgetDenied as exc:
        return _call_codex_cli_fallback(args, payload=payload, prompt=prompt, work_id=work_id, failure_reason=f"budget_denied: {exc}")
    try:
        response = LLMRuntime().call_text(
            prompt,
            model_id=model_id,
            max_tokens=max_tokens,
            retries=args.retries,
            timeout_seconds=args.timeout_s,
            request_label=work_id,
        )
    except Exception as exc:  # noqa: BLE001
        return _call_codex_cli_fallback(
            args,
            payload=payload,
            prompt=prompt,
            work_id=work_id,
            failure_reason=f"api_runtime_error:{type(exc).__name__}: {exc}",
        )
    actual_cost = budget.record_response(
        usage=response.usage,
        fallback_estimate=estimate,
        label=work_id,
    )
    trace_dir = Path(args.trace_dir)
    trace_dir.mkdir(parents=True, exist_ok=True)
    stem = _trace_stem(work_id)
    raw_path = trace_dir / f"{stem}_raw.txt"
    proposal_path = trace_dir / f"{stem}_proposal.json"
    write_text_atomic(raw_path, response.text)
    try:
        parsed = _sanitize_model_proposal(_extract_json_object_or_list(response.text), payload)
    except ValueError as exc:
        fallback = _call_codex_cli_fallback(
            args,
            payload=payload,
            prompt=prompt,
            work_id=work_id,
            failure_reason=f"api_output_unparseable:{exc}",
        )
        if fallback.get("ok"):
            return fallback
        return {
            "ok": False,
            "exit_kind": "llm_api_unparseable",
            "reason": str(exc),
            "model_called": True,
            "model_id": model_id,
            "effective_model_id": response.effective_model_id,
            "max_output_tokens": max_tokens,
            "payload_requested_max_output_tokens": payload_requested_max_tokens,
            "payload_output_token_downgrade_ignored": bool(payload_requested_max_tokens and payload_requested_max_tokens < max_tokens),
            "estimated_cost_usd": estimate.estimated_cost_usd,
            "actual_cost_usd": actual_cost,
            "artifact_paths": [str(raw_path), *(fallback.get("artifact_paths") or [])],
        }
    write_json_atomic(proposal_path, parsed)
    return {
        "ok": True,
        "model_called": True,
        "model_id": model_id,
        "effective_model_id": response.effective_model_id,
        "max_output_tokens": max_tokens,
        "payload_requested_max_output_tokens": payload_requested_max_tokens,
        "payload_output_token_downgrade_ignored": bool(payload_requested_max_tokens and payload_requested_max_tokens < max_tokens),
        "estimated_cost_usd": estimate.estimated_cost_usd,
        "actual_cost_usd": actual_cost,
        "proposal_path": str(proposal_path),
        "artifact_paths": [str(raw_path), str(proposal_path)],
    }


def proposal_gate(args: argparse.Namespace, payload: dict[str, Any], work_id: str) -> dict[str, Any]:
    proposal_path = str(payload.get("proposal_path") or "")
    artifacts: list[str] = []
    if not proposal_path and isinstance(payload.get("proposal"), dict):
        trace_dir = Path(args.trace_dir)
        trace_dir.mkdir(parents=True, exist_ok=True)
        proposal_path = str(trace_dir / f"{_trace_stem(work_id)}_proposal.json")
        write_json_atomic(proposal_path, payload["proposal"])
        artifacts.append(proposal_path)
    model_result: dict[str, Any] = {}
    if not proposal_path:
        model_result = _call_model(args, payload, work_id)
        artifacts.extend(model_result.get("artifact_paths") or [])
        if not model_result.get("ok"):
            return {**model_result, "artifact_paths": artifacts}
        proposal_path = str(model_result.get("proposal_path") or "")
    if not proposal_path:
        return {
            "ok": True,
            "exit_kind": "operator_required",
            "reason": "no proposal_path or inline proposal supplied",
            "model_called": bool(model_result.get("model_called")),
            "artifact_paths": artifacts,
        }
    result = _run([
        sys.executable,
        "scripts/public/control/leanmill/llm_proposal_gate.py",
        "--proposals", proposal_path,
        "--out", args.gate_out,
    ])
    artifacts.extend([proposal_path, args.gate_out])
    return {
        "ok": result["returncode"] == 0,
        "exit_kind": "proposal_validated" if result["returncode"] == 0 else "proposal_rejected",
        "model_called": bool(model_result.get("model_called")),
        "model": {k: v for k, v in model_result.items() if k not in {"ok", "artifact_paths"}},
        "result": result,
        "source_search_enqueued": _enqueue_source_search_tasks(args, proposal_path=proposal_path, parent_work_id=work_id)
        if result["returncode"] == 0 else [],
        "decomposition_followup_enqueued": _enqueue_decomposition_followups(args, proposal_path=proposal_path, parent_work_id=work_id)
        if result["returncode"] == 0 else [],
        "governance_candidate_enqueued": _enqueue_gap_or_falsifier_governance(args, proposal_path=proposal_path, parent_work_id=work_id)
        if result["returncode"] == 0 else [],
        "artifact_paths": artifacts,
    }


def _is_source_review_item(item: dict[str, Any]) -> bool:
    if str(item.get("kind") or "") != "llm_proposal_validate":
        return False
    payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
    if str(payload.get("expected_outcome") or "") == "source_request":
        return True
    if str(payload.get("proposal_type") or "") == "source_request":
        return True
    allowed = {str(x) for x in (payload.get("allowed_proposal_types") or []) if str(x)}
    return "source_request" in allowed and bool(payload.get("source_agent_work_id"))


def _claim_proposal_item(
    args: argparse.Namespace,
    cx: Any,
    *,
    source_review_only: bool = False,
) -> dict[str, Any] | None:
    kinds = ["llm_proposal_validate", "canary_propose", "source_request_propose", "decomposition_propose"]
    if source_review_only:
        return work_queue.claim_matching(
            cx,
            worker_id=args.worker_id,
            kinds=["llm_proposal_validate"],
            lease_s=args.lease_s,
            scan_limit=1000,
            predicate=_is_source_review_item,
        )
    return work_queue.claim(cx, worker_id=args.worker_id, kinds=kinds, lease_s=args.lease_s)


def _process_claimed_item(args: argparse.Namespace, cx: Any, item: dict[str, Any]) -> dict[str, Any]:
    work_queue.update_status(cx, work_id=item["work_id"], status="running")
    work_queue.append_event(args.events, {"event_type": "llm_proposal_worker_started", "work_id": item["work_id"], "payload": item})
    payload = item.get("payload") or {}
    family = str(payload.get("family") or "")
    try:
        if _no_spend_family(args.allocator, family):
            result = {
                "ok": True,
                "exit_kind": "retired_no_spend_until_new_evidence",
                "reason": "source_family_allocator_recommended_do_not_spend_until_new_evidence",
                "model_called": False,
                "artifact_paths": [args.allocator],
            }
            status = "retired"
        else:
            result = proposal_gate(args, payload, item["work_id"])
            status = "done" if result["ok"] else "failed"
    except Exception as exc:  # noqa: BLE001
        result = {
            "ok": False,
            "exit_kind": "proposal_worker_exception",
            "reason": f"{type(exc).__name__}: {exc}",
            "model_called": False,
            "artifact_paths": [],
        }
        status = "failed"
    work_queue.update_status(cx, work_id=item["work_id"], status=status, payload_update=result)
    work_queue.append_event(args.events, {
        "event_type": f"llm_proposal_worker_{status}",
        "work_id": item["work_id"],
        "payload": result,
        "artifact_paths": result.get("artifact_paths") or [],
    })
    return {"claimed": True, "work_id": item["work_id"], "status": status, "ok": result["ok"], "model_called": bool(result.get("model_called"))}


def work_once(args: argparse.Namespace) -> dict[str, Any]:
    cx = work_queue.connect(args.queue_db)
    item = _claim_proposal_item(args, cx)
    if not item:
        return {"claimed": False}
    return _process_claimed_item(args, cx, item)


def work_once_source_review(args: argparse.Namespace) -> dict[str, Any]:
    cx = work_queue.connect(args.queue_db)
    item = _claim_proposal_item(args, cx, source_review_only=True)
    if not item:
        return {"claimed": False}
    return _process_claimed_item(args, cx, item)


def daemon_loop(args: argparse.Namespace) -> dict[str, Any]:
    started = int(time.time())
    completed = 0
    idle_ticks = 0
    last_result: dict[str, Any] = {}
    while True:
        if args.max_tasks and completed >= args.max_tasks:
            break
        if args.max_idle_s and completed == 0 and int(time.time()) - started >= args.max_idle_s:
            break
        try:
            result = work_once(args)
        except Exception as exc:  # noqa: BLE001
            result = {
                "claimed": False,
                "ok": False,
                "daemon_error": f"{type(exc).__name__}: {exc}",
            }
            work_queue.append_event(args.events, {
                "event_type": "llm_proposal_daemon_error",
                "work_id": "",
                "payload": result,
            })
        last_result = result
        if result.get("claimed"):
            completed += 1
            idle_ticks = 0
            print(json.dumps({"daemon": args.worker_id, "task_result": result}, sort_keys=True), flush=True)
            continue
        idle_ticks += 1
        print(json.dumps({"daemon": args.worker_id, "idle": True, "idle_ticks": idle_ticks}, sort_keys=True), flush=True)
        time.sleep(max(1, int(args.idle_sleep_s)))
    return {
        "daemon": args.worker_id,
        "completed_tasks": completed,
        "last_result": last_result,
        "claim_kinds": ["llm_proposal_validate", "canary_propose", "source_request_propose", "decomposition_propose"],
    }


def _self_test() -> int:
    assert DEFAULT_TRACE_DIR.endswith("llm_proposal_traces")
    assert len(_trace_stem("x" * 400)) < 120
    parsed = _extract_json_object_or_list('```json\n{"family":"fam"}\n```')
    assert parsed["family"] == "fam"
    parsed = _extract_json_object_or_list(
        'diagnostic {not json} final {"proposal_type":"decomposition","family":"fam","credit_type":"none","expected_outcome":"hold"}'
    )
    assert parsed["proposal_type"] == "decomposition"
    assert _source_queries_from_proposal({"proposal_type": "source_request", "family": "fam", "source_query": ["a", "a", "b"]}) == ["a", "b"]
    assert _accepted_source_queries([
        {"query": "bad", "accepted": False},
        {"query": "Matrix gram PosDef LinearIndependent", "accepted": True},
    ]) == ["Matrix gram PosDef LinearIndependent"]
    assert _is_source_review_item({
        "kind": "llm_proposal_validate",
        "payload": {"expected_outcome": "source_request", "source_agent_work_id": "scout"},
    })
    assert not _is_source_review_item({
        "kind": "decomposition_propose",
        "payload": {"expected_outcome": "hold", "source_agent_work_id": "scout"},
    })
    ok, _quality = _queries_pass_gate(
        [
            "Matrix gram PosDef LinearIndependent",
            "LinearIndependent gram matrix positive definite",
            "orthonormal Gram matrix PosDef",
        ],
        "gram_posdef_linear_independent_planner",
    )
    assert ok
    bad, _quality = _queries_pass_gate(["find siblings for family"], "gram_posdef_linear_independent_planner")
    assert not bad
    sanitized = _sanitize_model_proposal({
        "family": "route_c_missing_lemma",
        "proposal_type": "exact_gap",
        "expected_outcome": "hold",
        "credit_type": "none",
        "missing_interface": "missing_atom",
    }, {"allowed_proposal_types": ["exact_gap", "falsifier", "decomposition"]})
    assert sanitized["proposal_type"] == "decomposition" and sanitized["expected_outcome"] == "hold", sanitized
    sanitized_gap = _sanitize_model_proposal({
        "family": "route_c_missing_lemma",
        "proposal_type": "exact_gap",
        "expected_outcome": "exact_gap",
        "credit_type": "none",
        "missing_interface": "missing_atom",
    }, {"allowed_proposal_types": ["exact_gap", "falsifier", "decomposition"]})
    assert sanitized_gap["proposal_type"] == "exact_gap" and sanitized_gap.get("gap_statement"), sanitized_gap
    assert callable(daemon_loop)
    blocked = _call_codex_cli_fallback(
        argparse.Namespace(allow_codex_cli_fallback=False),
        payload={},
        prompt="{}",
        work_id="w",
        failure_reason="blocked",
    )
    assert blocked["exit_kind"] == "llm_api_failed"
    import tempfile
    with tempfile.TemporaryDirectory(prefix="leanmill_llm_proposal_governance_") as td:
        root = Path(td)
        proposal = root / "proposal.json"
        proposal.write_text(json.dumps({
            "family": "route_c_missing_lemma",
            "proposal_type": "exact_gap",
            "hypothesis": "missing typed interface",
            "credit_type": "none",
            "expected_outcome": "exact_gap",
            "gap_statement": "Need a typed missing lemma statement.",
            "blocked_edge": "candidate lemma name is untyped",
        }) + "\n")
        args = argparse.Namespace(
            queue_db=str(root / "queue.sqlite"),
            events=str(root / "events.jsonl"),
            trace_dir=str(root / "traces"),
            factory_policy=str(root / "missing_policy.json"),
        )
        enq = _enqueue_gap_or_falsifier_governance(args, proposal_path=str(proposal), parent_work_id="route_c_gap:demo")
        assert len(enq) == 1 and enq[0]["candidate_kind"] == "exact_gap", enq
        cx = work_queue.connect(str(root / "queue.sqlite"))
        row = cx.execute("SELECT kind,payload_json FROM work_items WHERE kind='govern_exact_gap'").fetchone()
        assert row is not None, enq
    with tempfile.TemporaryDirectory(prefix="leanmill_llm_source_review_claim_") as td:
        root = Path(td)
        cx = work_queue.connect(str(root / "queue.sqlite"))
        work_queue.enqueue(cx, kind="decomposition_propose", priority=999, payload={"expected_outcome": "hold"})
        source_wid = work_queue.enqueue(cx, kind="llm_proposal_validate", priority=1, payload={
            "expected_outcome": "source_request",
            "source_agent_work_id": "source_scout",
            "allowed_proposal_types": ["source_request", "decomposition"],
        })
        claim = _claim_proposal_item(
            argparse.Namespace(worker_id="source-review", lease_s=60),
            cx,
            source_review_only=True,
        )
        assert claim and claim["work_id"] == source_wid, claim
    print("leanmill_llm_proposal_worker self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue-db", default=work_queue.DEFAULT_DB)
    ap.add_argument("--events", default=work_queue.DEFAULT_EVENTS)
    ap.add_argument("--worker-id", default="llm-proposal-worker-local")
    ap.add_argument("--lease-s", type=int, default=600)
    ap.add_argument("--gate-out", default=DEFAULT_PROPOSAL_GATE)
    ap.add_argument("--trace-dir", default=DEFAULT_TRACE_DIR)
    ap.add_argument("--allocator", default=DEFAULT_ALLOCATOR)
    ap.add_argument("--factory-policy", default=DEFAULT_FACTORY_POLICY)
    ap.add_argument("--allow-paid-llm", action="store_true")
    ap.add_argument("--max-total-cost-usd", type=float, default=0.0)
    ap.add_argument("--model-family", default="gpt4.1-mini")
    ap.add_argument("--max-output-tokens", type=int, default=1200)
    ap.add_argument("--timeout-s", type=int, default=180)
    ap.add_argument("--retries", type=int, default=1)
    ap.add_argument("--allow-codex-cli-fallback", action="store_true")
    ap.add_argument("--codex-cli-fallback-model", default="gpt-5.4-mini")
    ap.add_argument("--codex-cli-fallback-timeout-s", type=int, default=240)
    ap.add_argument("--role-id", default="research_director")
    ap.add_argument("--session-id", default="leanmill_24x7")
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--idle-sleep-s", type=int, default=15)
    ap.add_argument("--max-tasks", type=int, default=0)
    ap.add_argument("--max-idle-s", type=int, default=0)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    if args.daemon:
        print(json.dumps(daemon_loop(args), sort_keys=True))
        return 0
    result = work_once(args)
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("ok", True) is not False else 1


if __name__ == "__main__":
    raise SystemExit(main())
