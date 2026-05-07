# Licensed under Business Source License 1.1 — see LICENSE-BSL
"""Typed local agent-to-agent channel for persistent role offices.

This is not an MCP replacement. MCP exposes tools/context to an LLM host.
This module records durable communications between role-bearing offices
inside the ZTARE org runtime. External A2A/ACP/MCP adapters can project into
or out of this channel, but the local governance envelope remains canonical.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from src.ztare.common.paths import REPO_ROOT
from src.ztare.orchestration.transition_log import append_transition


CHANNELS_DIR = REPO_ROOT / "org" / "channels"
ROLES_DIR = REPO_ROOT / "org" / "roles"

MessageKind = Literal[
    "inform",
    "request",
    "proposal",
    "handoff",
    "clarification",
    "refusal",
    "status",
]

MessageStatus = Literal["open", "acknowledged", "closed"]


@dataclass(frozen=True)
class AgentMessage:
    schema_version: int
    message_id: str
    thread_id: str
    kind: MessageKind
    from_role: str
    to_role: str
    subject: str
    body: str
    status: MessageStatus
    created_utc: str
    causality_id: str | None = None
    expects_response: bool = False
    expires_utc: str | None = None
    references: list[str] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class ChannelPolicyError(PermissionError):
    """Raised when a role attempts a message outside local channel policy."""


def _safe_role(role_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", role_id.strip())
    if not safe:
        raise ValueError("role_id cannot be empty")
    return safe


def _strip_role_ref(value: str) -> str:
    return value.split(".", 1)[1] if value.startswith("role.") else value


def _extract_yaml_list(text: str, key: str) -> list[str]:
    out: list[str] = []
    in_block = False
    base_indent = 0
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if stripped == f"{key}:":
            in_block = True
            base_indent = indent
            continue
        if in_block:
            if indent <= base_indent and not stripped.startswith("- "):
                break
            if stripped.startswith("- "):
                item = stripped[2:].split("#", 1)[0].strip().strip('"').strip("'")
                if item:
                    out.append(item)
    return out


def _role_path(role_id: str) -> Path:
    return ROLES_DIR / f"{_safe_role(role_id)}.yaml"


def _role_exists(role_id: str) -> bool:
    return _role_path(role_id).exists()


def _role_links(role_id: str) -> set[str]:
    path = _role_path(role_id)
    if not path.exists():
        return set()
    text = path.read_text(encoding="utf-8")
    links = set()
    for key in ("delegates_to", "escalates_to"):
        links.update(_strip_role_ref(item) for item in _extract_yaml_list(text, key))
    return links


def channel_allowed(from_role: str, to_role: str) -> tuple[bool, str]:
    """Conservative local channel policy.

    This is not enterprise RBAC. It prevents obvious side-channel drift until
    the control-plane policy compiler exists.
    """
    sender = _safe_role(from_role)
    receiver = _safe_role(to_role)
    if not _role_exists(sender):
        return False, f"sender role does not exist: {sender}"
    if not _role_exists(receiver):
        return False, f"receiver role does not exist: {receiver}"
    if sender == receiver:
        return True, "self-message"
    if sender == "manager":
        return True, "manager coordination channel"
    if receiver in {"manager", "principal"}:
        return True, "manager/principal escalation channel"
    if receiver in _role_links(sender):
        return True, "receiver is in sender delegates_to/escalates_to"
    if sender in _role_links(receiver):
        return True, "sender is in receiver delegates_to/escalates_to"
    return False, "roles are not linked by delegation/escalation policy"


def _role_inbox(role_id: str) -> Path:
    return CHANNELS_DIR / _safe_role(role_id) / "inbox"


def _role_sent(role_id: str) -> Path:
    return CHANNELS_DIR / _safe_role(role_id) / "sent"


def _message_path(role_id: str, message_id: str) -> Path:
    return _role_inbox(role_id) / f"{message_id}.json"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def send_agent_message(
    *,
    from_role: str,
    to_role: str,
    kind: MessageKind,
    subject: str,
    body: str,
    expects_response: bool = False,
    thread_id: str | None = None,
    causality_id: str | None = None,
    expires_utc: str | None = None,
    references: list[str] | None = None,
    artifacts: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    enforce_policy: bool = True,
) -> AgentMessage:
    """Append one durable A2A-style message to the receiver inbox.

    The same JSON is mirrored into the sender's sent folder for local
    inspectability. Coordination authority still lives in gates/claims; this
    channel is for typed communication and handoff context.
    """
    allowed, policy_reason = channel_allowed(from_role, to_role)
    if enforce_policy and not allowed:
        raise ChannelPolicyError(policy_reason)

    now = datetime.now(timezone.utc).isoformat()
    message_id = f"msg_{uuid.uuid4().hex}"
    message = AgentMessage(
        schema_version=1,
        message_id=message_id,
        thread_id=thread_id or message_id,
        kind=kind,
        from_role=_safe_role(from_role),
        to_role=_safe_role(to_role),
        subject=subject.strip(),
        body=body.strip(),
        status="open",
        created_utc=now,
        causality_id=causality_id,
        expects_response=expects_response,
        expires_utc=expires_utc,
        references=references or [],
        artifacts=artifacts or [],
        metadata={**(metadata or {}), "channel_policy": policy_reason},
    )
    payload = asdict(message)
    _write_json(_role_inbox(message.to_role) / f"{message_id}.json", payload)
    _write_json(_role_sent(message.from_role) / f"{message_id}.json", payload)
    append_transition(
        event="agent.message.sent",
        actor=message.from_role,
        role_id=message.from_role,
        surface="agent_channel",
        subject=message_id,
        causality_id=causality_id or message.thread_id,
        payload={
            "to_role": message.to_role,
            "kind": message.kind,
            "thread_id": message.thread_id,
            "expects_response": message.expects_response,
            "references": message.references,
            "artifacts": message.artifacts,
        },
    )
    return message


def read_agent_message(*, role_id: str, message_id: str) -> AgentMessage | None:
    path = _message_path(role_id, message_id)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return AgentMessage(**data)


def list_agent_messages(
    *,
    role_id: str,
    status: MessageStatus | None = "open",
    limit: int = 50,
) -> list[AgentMessage]:
    inbox = _role_inbox(role_id)
    if not inbox.exists():
        return []
    out: list[AgentMessage] = []
    for path in sorted(inbox.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            msg = AgentMessage(**json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            continue
        if status is None or msg.status == status:
            out.append(msg)
        if len(out) >= limit:
            break
    return out


def update_agent_message_status(
    *,
    role_id: str,
    message_id: str,
    status: MessageStatus,
    actor: str,
    note: str = "",
) -> AgentMessage:
    path = _message_path(role_id, message_id)
    if not path.exists():
        raise FileNotFoundError(f"agent message not found: {message_id}")
    data = json.loads(path.read_text(encoding="utf-8"))
    data["status"] = status
    data.setdefault("metadata", {})
    data["metadata"]["last_status_note"] = note
    data["metadata"]["last_status_actor"] = actor
    data["metadata"]["last_status_utc"] = datetime.now(timezone.utc).isoformat()
    _write_json(path, data)
    sender_mirror = _role_sent(str(data.get("from_role", ""))) / f"{message_id}.json"
    if sender_mirror.exists():
        _write_json(sender_mirror, data)
    append_transition(
        event=f"agent.message.{status}",
        actor=actor,
        role_id=role_id,
        surface="agent_channel",
        subject=message_id,
        causality_id=data.get("causality_id") or data.get("thread_id"),
        payload={"note": note, "from_role": data.get("from_role"), "to_role": data.get("to_role")},
    )
    return AgentMessage(**data)
