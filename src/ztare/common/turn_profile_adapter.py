from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TURN_PROFILE_SCHEMA = "ztare-turn-profile-v1"


@dataclass(frozen=True)
class TurnProfile:
    turn_id: str
    session_id: str
    created_at_utc: str
    cwd: str
    agent_id: str
    prompt_sha256: str
    cli_startup_s: float | None
    context_ingest_s: float | None
    model_thinking_generation_s: float | None
    tool_exec_s: float | None
    harness_pack_sync_s: float | None
    gates_s: float | None
    total_s: float | None
    input_tokens: int | None
    output_tokens: int | None
    source_prompt_meta: str
    source_rollout: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": TURN_PROFILE_SCHEMA,
            **self.__dict__,
        }


def build_turn_profiles(
    *,
    prompt_debug_root: str | Path,
    rollout_root: str | Path,
    output_path: str | Path,
    limit: int = 5,
) -> dict[str, Any]:
    prompt_rows = _load_prompt_debug_rows(Path(prompt_debug_root))
    rollout_rows = _load_rollout_rows(Path(rollout_root))
    profiles = [_profile_for_prompt(row, rollout_rows) for row in prompt_rows[:limit]]
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for profile in profiles:
            f.write(json.dumps(profile.to_dict(), sort_keys=True) + "\n")
    return {
        "schema": TURN_PROFILE_SCHEMA,
        "count": len(profiles),
        "rows": [profile.to_dict() for profile in profiles],
    }


def format_profile_table(rows: list[dict[str, Any]]) -> str:
    headers = ["turn", "cli_startup", "context_ingest", "model", "tool_exec", "pack_sync", "gates", "total", "tokens"]
    lines = [" | ".join(headers), " | ".join(["---"] * len(headers))]
    for row in rows:
        lines.append(
            " | ".join(
                [
                    str(row.get("turn_id") or ""),
                    _fmt(row.get("cli_startup_s")),
                    _fmt(row.get("context_ingest_s")),
                    _fmt(row.get("model_thinking_generation_s")),
                    _fmt(row.get("tool_exec_s")),
                    _fmt(row.get("harness_pack_sync_s")),
                    _fmt(row.get("gates_s")),
                    _fmt(row.get("total_s")),
                    f"{row.get('input_tokens') or 0}/{row.get('output_tokens') or 0}",
                ]
            )
        )
    return "\n".join(lines)


def _fmt(value: Any) -> str:
    if value is None:
        return "-"
    return f"{float(value):.1f}s"


def _load_prompt_debug_rows(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not root.exists():
        return rows
    for meta_path in sorted(root.glob("*.meta.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(meta, dict):
            continue
        rows.append(
            {
                "meta_path": str(meta_path),
                "created_at_utc": meta.get("created_at_utc"),
                "prompt_sha256": meta.get("prompt_sha256") or "",
                "agent_id": meta.get("agent_id") or "",
                "runtime": meta.get("runtime") or "",
                "prompt_path": meta.get("prompt_path") or "",
            }
        )
    return rows


def _load_rollout_rows(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not root.exists():
        return rows
    for rollout_path in sorted(root.rglob("rollout-*.jsonl")):
        try:
            first = json.loads(rollout_path.read_text(encoding="utf-8").splitlines()[0])
        except Exception:
            continue
        payload = first.get("payload") if isinstance(first, dict) else {}
        if not isinstance(payload, dict):
            continue
        rows.append(
            {
                "rollout_path": str(rollout_path),
                "session_id": str(payload.get("session_id") or payload.get("id") or ""),
                "created_at": str(payload.get("timestamp") or first.get("timestamp") or ""),
                "cwd": str(payload.get("cwd") or ""),
                "thread_source": str(payload.get("thread_source") or ""),
                "events": _collect_rollout_events(rollout_path),
            }
        )
    return rows


def _collect_rollout_events(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                continue
            events.append(row)
    except Exception:
        return []
    return events


def _profile_for_prompt(prompt_row: dict[str, Any], rollout_rows: list[dict[str, Any]]) -> TurnProfile:
    created = _parse_dt(prompt_row.get("created_at_utc")) or datetime.now(timezone.utc)
    rollout = _match_rollout(prompt_row, rollout_rows, created)
    events = rollout.get("events") if rollout else []
    event_times = [_parse_dt((e or {}).get("timestamp")) for e in events if isinstance(e, dict)]
    event_times = [t for t in event_times if t is not None]
    first_event = min(event_times) if event_times else None
    last_event = max(event_times) if event_times else None
    token_events = [e for e in events if isinstance(e, dict) and e.get("type") == "event_msg" and isinstance(e.get("payload"), dict) and e["payload"].get("type") == "token_count"]
    first_token = _parse_dt(token_events[0].get("timestamp")) if token_events else None
    input_tokens = None
    output_tokens = None
    if token_events:
        info = token_events[-1]["payload"].get("info") or {}
        total = info.get("last_token_usage") or info.get("total_token_usage") or {}
        input_tokens = int(total.get("input_tokens") or 0) or None
        output_tokens = int(total.get("output_tokens") or 0) or None
    response_events = [e for e in events if isinstance(e, dict) and e.get("type") == "response_item"]
    first_response = _parse_dt(response_events[0].get("timestamp")) if response_events else None
    tool_calls = [e for e in events if isinstance(e, dict) and e.get("type") == "response_item" and isinstance(e.get("payload"), dict) and e["payload"].get("type") == "function_call"]
    tool_exec_s = None
    if len(tool_calls) >= 2:
        start = _parse_dt(tool_calls[0].get("timestamp"))
        end = _parse_dt(tool_calls[-1].get("timestamp"))
        if start and end:
            tool_exec_s = (end - start).total_seconds()
    model_start = first_response or first_token
    model_end = last_event or first_response or first_token
    return TurnProfile(
        turn_id=Path(str(prompt_row.get("meta_path") or "")).stem,
        session_id=str(rollout.get("session_id") if rollout else ""),
        created_at_utc=str(prompt_row.get("created_at_utc") or ""),
        cwd=str(rollout.get("cwd") if rollout else ""),
        agent_id=str(prompt_row.get("agent_id") or ""),
        prompt_sha256=str(prompt_row.get("prompt_sha256") or ""),
        cli_startup_s=_delta_s(created, first_event),
        context_ingest_s=_delta_s(first_event, first_response or first_token),
        model_thinking_generation_s=_delta_s(model_start, model_end),
        tool_exec_s=tool_exec_s,
        harness_pack_sync_s=None,
        gates_s=None,
        total_s=_delta_s(created, last_event or first_response or first_token),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        source_prompt_meta=str(prompt_row.get("meta_path") or ""),
        source_rollout=str(rollout.get("rollout_path")) if rollout else None,
    )


def _match_rollout(prompt_row: dict[str, Any], rollout_rows: list[dict[str, Any]], created: datetime) -> dict[str, Any] | None:
    prompt_agent = str(prompt_row.get("agent_id") or "")
    for rollout in rollout_rows:
        if prompt_agent and prompt_agent in str(rollout.get("rollout_path") or ""):
            return rollout
    return min(
        rollout_rows,
        key=lambda row: abs(((_parse_dt(row.get("created_at")) or created) - created).total_seconds()),
        default=None,
    )


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except Exception:
        return None


def _delta_s(start: datetime | None, end: datetime | None) -> float | None:
    if not start or not end:
        return None
    return round((end - start).total_seconds(), 3)
