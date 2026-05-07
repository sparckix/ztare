# Licensed under Business Source License 1.1 — see LICENSE-BSL
"""Local A2A-style projection for persistent role offices.

This is deliberately a projection, not the authority layer. Role YAML,
mandates, channels, gates, and claims remain canonical. These cards make role
offices discoverable to future A2A/ACP adapters without granting execution
authority.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - product smoke path.
    yaml = None

from src.ztare.common.paths import REPO_ROOT


ROLES_DIR = REPO_ROOT / "org" / "roles"
CHANNELS_DIR = REPO_ROOT / "org" / "channels"
CARD_DIR = REPO_ROOT / "ztare_workspace" / "a2a" / "agent_cards"
LOGICAL_CHANNELS_DIR = Path("org") / "channels"


@dataclass(frozen=True)
class AgentCard:
    schema_version: int
    protocol_hint: str
    role_id: str
    name: str
    description: str
    inbox_path: str
    mandate_path: str
    authorized_paths: list[str]
    forbidden_paths: list[str]
    delegates_to: list[str]
    escalates_to: list[str]
    message_kinds: list[str]
    authority_note: str


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


def _clean_yaml_scalar(value: str) -> str | None:
    value = value.split("#", 1)[0].strip().strip('"').strip("'")
    if value in {"", "null", "Null", "NULL", "~"}:
        return None
    return value


def _extract_block_scalar(text: str, key: str) -> str | None:
    lines = text.splitlines()
    for idx, raw in enumerate(lines):
        stripped = raw.strip()
        if not stripped.startswith(f"{key}:"):
            continue
        _, value = raw.split(":", 1)
        if value.strip().split("#", 1)[0].strip() not in {">", "|"}:
            return _clean_yaml_scalar(value)
        chunks: list[str] = []
        base_indent: int | None = None
        for follower in lines[idx + 1:]:
            follower_stripped = follower.strip()
            if not follower_stripped or follower_stripped.startswith("#"):
                continue
            indent = len(follower) - len(follower.lstrip(" "))
            if base_indent is None:
                base_indent = indent
            if indent < base_indent:
                break
            chunks.append(follower_stripped)
        return " ".join(chunks).strip() or None
    return None


def _load_role(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        data = yaml.safe_load(text) or {}
    else:
        data = {}
        for raw in text.splitlines():
            if ":" not in raw or raw.lstrip().startswith("- "):
                continue
            key, value = raw.split(":", 1)
            data[key.strip()] = _clean_yaml_scalar(value)
        description = _extract_block_scalar(text, "description")
        if description is not None:
            data["description"] = description
    if not isinstance(data, dict):
        data = {}
    for key in ("authorized_paths", "forbidden_paths", "delegates_to", "escalates_to"):
        if key not in data or not isinstance(data.get(key), list):
            data[key] = _extract_yaml_list(text, key)
    return data


def build_agent_card(role_id: str) -> AgentCard:
    path = ROLES_DIR / f"{role_id}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"role not found: {role_id}")
    role = _load_role(path)
    mandate_path = role.get("mandate_path")
    if mandate_path is None:
        mandate_path = "" if "mandate_path" in role else f"org/mandates/{role_id}_mandate.md"
    return AgentCard(
        schema_version=1,
        protocol_hint="a2a_projection_v0_local",
        role_id=role_id,
        name=str(role.get("display_name") or role_id),
        description=str(role.get("description") or ""),
        inbox_path=str(LOGICAL_CHANNELS_DIR / role_id / "inbox"),
        mandate_path=str(mandate_path),
        authorized_paths=list(role.get("authorized_paths") or []),
        forbidden_paths=list(role.get("forbidden_paths") or []),
        delegates_to=list(role.get("delegates_to") or []),
        escalates_to=list(role.get("escalates_to") or []),
        message_kinds=[
            "inform",
            "request",
            "proposal",
            "handoff",
            "clarification",
            "refusal",
            "status",
        ],
        authority_note=(
            "This card is discoverability only. Messages create obligations, "
            "not execution authority. Execution still requires authorization, "
            "gate if needed, claim, runner constraints, transition log, and closure."
        ),
    )


def build_all_agent_cards(*, roles_dir: Path | None = None) -> list[AgentCard]:
    if roles_dir is None:
        roles_dir = ROLES_DIR
    if not roles_dir.exists():
        return []
    cards = []
    for path in sorted(roles_dir.glob("*.yaml")):
        cards.append(build_agent_card(path.stem))
    return cards


def write_agent_cards(*, out_dir: Path = CARD_DIR) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for card in build_all_agent_cards():
        path = out_dir / f"{card.role_id}.json"
        path.write_text(json.dumps(asdict(card), indent=2, sort_keys=True), encoding="utf-8")
        paths.append(path)
    return paths
