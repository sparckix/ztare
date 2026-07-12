from __future__ import annotations

import json
import os
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from typing import Any, Callable, Iterable

from ztare.common.leaf_workbench_proposals import (
    pending_leaf_workbench_tool_synthesis_proposals,
)
from ztare.common.llm_runtime import LLMRuntime, resolve_model_id
from ztare.common.subscription_agent_runtime import (
    CODEX_SANDBOX_SEALED_COMPLETION,
    SEALED_CLAUDE_DISALLOWED_TOOLS,
    run_subscription_agent_with_recovery,
)
from ztare.research_director.strategy_decision_policy import StrategyDecisionPosition


AGENTS_JSON_ENV = "ZTARE_TOOL_PROPOSAL_REVIEW_AGENTS_JSON"
AGENTS_CSV_ENV = "ZTARE_TOOL_PROPOSAL_REVIEW_AGENTS"
TIMEOUT_ENV = "ZTARE_TOOL_PROPOSAL_REVIEW_TIMEOUT_SECONDS"


@dataclass(frozen=True)
class ToolProposalReviewerSpec:
    actor_id: str
    role_id: str = "role.tool_proposal_reviewer"
    transport: str = "api"
    model: str = ""
    runtime: str = ""
    enabled: bool = True

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


ReviewerDispatcher = Callable[[ToolProposalReviewerSpec, str, Path, int], str]


def default_tool_proposal_reviewer_specs() -> list[ToolProposalReviewerSpec]:
    """Default dormant review panel requested for tool-proposal batch review.

    Nothing calls these agents unless the Strategy Office CLI is explicitly
    invoked with ``--decision-position-agents default``.
    """

    return [
        ToolProposalReviewerSpec(
            actor_id="kimi_api",
            transport="api",
            model=os.environ.get("ZTARE_TOOL_PROPOSAL_REVIEW_KIMI_MODEL", "kimi-k2.6"),
        ),
        ToolProposalReviewerSpec(
            actor_id="deepseek_api",
            transport="api",
            model=os.environ.get("ZTARE_TOOL_PROPOSAL_REVIEW_DEEPSEEK_MODEL", "deepseek-chat"),
        ),
        ToolProposalReviewerSpec(
            actor_id="codex_subscription",
            transport="subscription_cli",
            runtime="codex",
            model=os.environ.get("ZTARE_TOOL_PROPOSAL_REVIEW_CODEX_MODEL", "account-default"),
        ),
        ToolProposalReviewerSpec(
            actor_id="claude_subscription",
            transport="subscription_cli",
            runtime="claude",
            model=os.environ.get("ZTARE_TOOL_PROPOSAL_REVIEW_CLAUDE_MODEL", "account-default"),
        ),
    ]


def reviewer_specs_from_env() -> list[ToolProposalReviewerSpec]:
    raw_json = os.environ.get(AGENTS_JSON_ENV, "").strip()
    if raw_json:
        payload = json.loads(raw_json)
        if not isinstance(payload, list):
            raise ValueError(f"{AGENTS_JSON_ENV} must be a JSON list")
        return [_reviewer_spec_from_mapping(row) for row in payload if isinstance(row, dict)]
    raw_csv = os.environ.get(AGENTS_CSV_ENV, "").strip()
    if raw_csv:
        return [_reviewer_spec_from_csv(part) for part in raw_csv.split(",") if part.strip()]
    return []


def reviewer_specs_for_source(source: str) -> list[ToolProposalReviewerSpec]:
    normalized = str(source or "").strip().lower()
    if normalized in {"", "none", "off"}:
        return []
    if normalized == "env":
        return reviewer_specs_from_env()
    if normalized == "default":
        return default_tool_proposal_reviewer_specs()
    if normalized.startswith("["):
        payload = json.loads(source)
        if not isinstance(payload, list):
            raise ValueError("inline reviewer spec JSON must be a list")
        return [_reviewer_spec_from_mapping(row) for row in payload if isinstance(row, dict)]
    raise ValueError(
        "unsupported decision-position-agents source; expected none, env, default, "
        "or an inline JSON list"
    )


def collect_tool_proposal_review_positions(
    project_dir: str | Path,
    *,
    specs: Iterable[ToolProposalReviewerSpec],
    limit: int | None = None,
    dispatcher: ReviewerDispatcher | None = None,
    timeout_seconds: int | None = None,
) -> list[StrategyDecisionPosition]:
    """Collect reviewer positions for pending cold tool proposals.

    Reviewers only produce StrategyDecisionPosition rows. Card promotion still
    goes through ``submit_strategy_card_batch``.
    """

    project = Path(project_dir)
    rows = pending_leaf_workbench_tool_synthesis_proposals(project, limit=limit)
    if not rows:
        return []
    prompt = render_tool_proposal_review_prompt(rows)
    timeout = timeout_seconds if timeout_seconds is not None else _env_int(TIMEOUT_ENV, 300)
    positions: list[StrategyDecisionPosition] = []
    absent: list[dict[str, Any]] = []
    call = dispatcher or dispatch_tool_proposal_reviewer
    refs = [f"proposal_sha256:{row.get('proposal_sha256')}" for row in rows if row.get("proposal_sha256")]
    with ThreadPoolExecutor(max_workers=max(1, len(list(specs)))) as pool:
        futures = {}
        active_specs = [spec for spec in specs if spec.enabled]
        for spec in active_specs:
            futures[pool.submit(call, spec, prompt, project, timeout)] = spec
        for fut, spec in futures.items():
            try:
                raw = fut.result(timeout=timeout)
            except TimeoutError:
                absent.append({"actor_id": spec.actor_id, "reason": "timeout"})
                continue
            except Exception as exc:  # noqa: BLE001
                absent.append({"actor_id": spec.actor_id, "reason": f"{type(exc).__name__}: {exc}"})
                continue
            positions.append(_position_from_reviewer_output(spec, raw, rows))
    for item in absent:
        positions.append(
            StrategyDecisionPosition(
                actor_id=str(item["actor_id"]),
                role_id="role.tool_proposal_reviewer",
                position="abstain",
                rationale=str(item["reason"]),
                evidence_refs=refs,
                metadata={"absent": True, "reason": item["reason"]},
            )
        )
    return positions


def render_tool_proposal_review_prompt(rows: list[dict[str, Any]]) -> str:
    items = []
    for row in rows:
        proposal = row.get("proposal") if isinstance(row.get("proposal"), dict) else {}
        items.append(
            {
                "proposal_sha256": row.get("proposal_sha256"),
                "source_ref": row.get("source_ref"),
                "status": row.get("status"),
                "tool_synthesis_status": row.get("tool_synthesis_status"),
                "proposed_capability_id": proposal.get("proposed_capability_id"),
                "gap_statement": proposal.get("gap_statement"),
                "target_artifact": proposal.get("target_artifact"),
                "input_contract": proposal.get("input_contract"),
                "output_contract": proposal.get("output_contract"),
                "evaluator": proposal.get("evaluator"),
                "safety_invariant": proposal.get("safety_invariant"),
                "rollback_condition": proposal.get("rollback_condition"),
            }
        )
    payload = json.dumps(items, indent=2, sort_keys=True, default=str)
    return (
        "You are reviewing cold leaf workbench capability proposals for possible "
        "Strategy Office tool_synthesis promotion.\n"
        "Approve only when the proposal is paired with a lowerability obstruction, "
        "names a mutable sensor/workbench surface, includes a bounded evaluator, "
        "and would reduce repeated candidate-search failure without weakening "
        "replay, holdout, or terminal authority.\n"
        "Reject convenience tools, stale registered capabilities, hard-kernel edits, "
        "hidden-data access, or proposals that should remain ordinary candidate work.\n\n"
        "Return STRICT JSON only:\n"
        "{\"position\":\"approve|reject|abstain|veto\","
        "\"rationale\":\"...\","
        "\"evidence_refs\":[\"proposal_sha256:...\"]}\n\n"
        "Pending proposals:\n"
        f"{payload}\n"
    )


def dispatch_tool_proposal_reviewer(
    spec: ToolProposalReviewerSpec,
    prompt: str,
    project: Path,
    timeout_seconds: int,
) -> str:
    transport = str(spec.transport or "api").strip().lower()
    if transport in {"api", "llm"}:
        model = resolve_model_id(spec.model or spec.actor_id)
        response = LLMRuntime().call_text(
            prompt,
            model_id=model,
            max_tokens=1200,
            timeout_seconds=timeout_seconds,
            request_label=f"tool_proposal_review:{spec.actor_id}",
        )
        return response.text or ""
    if transport in {"subscription", "subscription_cli", "agent"}:
        runtime = (spec.runtime or spec.actor_id or "codex").strip().lower()
        if runtime not in {"codex", "claude"}:
            raise ValueError(f"unsupported subscription reviewer runtime: {runtime}")
        with _scoped_reviewer_model_env(spec):
            run = run_subscription_agent_with_recovery(
                runtime=runtime,
                prompt=prompt,
                agent_id=f"tool_proposal_review::{spec.actor_id}",
                repo=project,
                session_state=None,
                timeout_seconds=timeout_seconds,
                codex_model_env="ZTARE_TOOL_PROPOSAL_REVIEW_CODEX_MODEL_ACTIVE",
                codex_sandbox=CODEX_SANDBOX_SEALED_COMPLETION,
                claude_disallowed_tools=SEALED_CLAUDE_DISALLOWED_TOOLS,
            )
        result = run.result
        return result.stdout or ""
    raise ValueError(f"unsupported reviewer transport: {spec.transport!r}")


def _reviewer_spec_from_mapping(row: dict[str, Any]) -> ToolProposalReviewerSpec:
    actor_id = str(row.get("actor_id") or row.get("agent_id") or row.get("name") or "").strip()
    if not actor_id:
        raise ValueError("tool proposal reviewer spec requires actor_id")
    transport = str(row.get("transport") or row.get("backend") or "api")
    runtime = str(row.get("runtime") or "")
    if transport in {"subscription", "subscription_cli", "agent"} and not runtime:
        runtime = actor_id.split("_", 1)[0]
    return ToolProposalReviewerSpec(
        actor_id=actor_id,
        role_id=str(row.get("role_id") or row.get("role") or "role.tool_proposal_reviewer"),
        transport=transport,
        model=str(row.get("model") or row.get("model_id") or ""),
        runtime=runtime,
        enabled=bool(row.get("enabled", True)),
    )


def _reviewer_spec_from_csv(part: str) -> ToolProposalReviewerSpec:
    fields = [field.strip() for field in part.split(":")]
    actor_id = fields[0] if fields else ""
    transport = fields[1] if len(fields) > 1 and fields[1] else "api"
    model = fields[2] if len(fields) > 2 else ""
    runtime = fields[3] if len(fields) > 3 else ""
    if transport in {"subscription", "subscription_cli", "agent"} and not runtime:
        runtime = actor_id.split("_", 1)[0]
    return ToolProposalReviewerSpec(
        actor_id=actor_id,
        transport=transport,
        model=model,
        runtime=runtime,
    )


def _position_from_reviewer_output(
    spec: ToolProposalReviewerSpec,
    raw: str,
    rows: list[dict[str, Any]],
) -> StrategyDecisionPosition:
    refs = [f"proposal_sha256:{row.get('proposal_sha256')}" for row in rows if row.get("proposal_sha256")]
    try:
        payload = _parse_json_object(raw)
        position = str(payload.get("position") or "").strip().lower()
        if position not in {"approve", "reject", "abstain", "recuse", "veto"}:
            raise ValueError(f"invalid position {position!r}")
        rationale = str(payload.get("rationale") or payload.get("reason") or "").strip()
        if not rationale:
            raise ValueError("missing rationale")
        evidence_refs = [str(ref) for ref in payload.get("evidence_refs") or refs]
        metadata = {
            "transport": spec.transport,
            "runtime": spec.runtime,
            "model": spec.model,
            "raw_chars": len(raw or ""),
        }
    except Exception as exc:  # noqa: BLE001
        position = "abstain"
        rationale = f"reviewer output was not a valid decision position: {type(exc).__name__}: {str(exc)[:160]}"
        evidence_refs = refs
        metadata = {
            "transport": spec.transport,
            "runtime": spec.runtime,
            "model": spec.model,
            "parse_error": type(exc).__name__,
            "raw_head": (raw or "")[:400],
        }
    return StrategyDecisionPosition(
        actor_id=spec.actor_id,
        role_id=spec.role_id,
        position=position,
        rationale=rationale,
        evidence_refs=evidence_refs,
        metadata=metadata,
    )


def _parse_json_object(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise
        payload = json.loads(text[start : end + 1])
    if not isinstance(payload, dict):
        raise ValueError("reviewer output must be a JSON object")
    return payload


@contextmanager
def _scoped_reviewer_model_env(spec: ToolProposalReviewerSpec):
    changes: dict[str, str | None] = {}
    if spec.runtime == "codex" and spec.model:
        changes["ZTARE_TOOL_PROPOSAL_REVIEW_CODEX_MODEL_ACTIVE"] = os.environ.get(
            "ZTARE_TOOL_PROPOSAL_REVIEW_CODEX_MODEL_ACTIVE"
        )
        os.environ["ZTARE_TOOL_PROPOSAL_REVIEW_CODEX_MODEL_ACTIVE"] = spec.model
    if spec.runtime == "claude" and spec.model:
        changes["ZTARE_CLAUDE_AGENT_MODEL"] = os.environ.get("ZTARE_CLAUDE_AGENT_MODEL")
        os.environ["ZTARE_CLAUDE_AGENT_MODEL"] = spec.model
    try:
        yield
    finally:
        for key, previous in changes.items():
            if previous is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = previous


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        parsed = int(raw)
    except ValueError:
        return default
    return parsed if parsed > 0 else default
