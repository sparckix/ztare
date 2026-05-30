# SPDX-License-Identifier: MIT
"""Pre-dispatch authorization gate for role-daemon tasks.

This is deliberately conservative and local. It does not sandbox execution;
it decides whether a daemon is allowed to dispatch a task at all. Physical
write/network/secret constraints must still be enforced by the runner.
"""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - bare Python product path.
    yaml = None

from src.ztare.common.paths import REPO_ROOT


ROLE_PATH_PREFIXES = (
    "org/",
    "projects/",
    "research_areas/",
    "docs/",
    "src/",
    "scripts/public/",
    "papers/",
    "ztare_workspace/",
    "rubrics/",
    "orbit/",
    "supervisor/",
)


@dataclass(frozen=True)
class AuthorizationDecision:
    allowed: bool
    reason: str
    required_approval: str = "none"
    matched_paths: tuple[str, ...] = ()
    terminal: bool = False


def _coerce_scalar(value: str) -> Any:
    text = value.strip()
    if not text:
        return {}
    if (text.startswith('"') and text.endswith('"')) or (
        text.startswith("'") and text.endswith("'")
    ):
        return text[1:-1]
    lowered = text.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered == "null":
        return None
    try:
        if "." in text:
            return float(text)
        return int(text)
    except ValueError:
        return text


def _minimal_yaml_load(text: str) -> dict[str, Any]:
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw.lstrip().startswith("- "):
            # Lists are not needed except path arrays, which we parse manually.
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        parsed = _coerce_scalar(value)
        parent[key.strip()] = parsed
        if isinstance(parsed, dict):
            stack.append((indent, parsed))
    return root


def _load_role(role_id: str) -> dict[str, Any]:
    path = REPO_ROOT / "org" / "roles" / f"{role_id}.yaml"
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text) if yaml is not None else _minimal_yaml_load(text)
    if not isinstance(data, dict):
        return {}
    # Simple list extraction for authorized_paths/forbidden_paths works even
    # when PyYAML is absent.
    for key in ("authorized_paths", "forbidden_paths"):
        if key not in data or not isinstance(data.get(key), list):
            data[key] = _extract_yaml_list(text, key)
    return data


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


def _path_matches(path: str, pattern: str) -> bool:
    pattern = pattern.strip()
    if pattern == "*":
        return True
    normalized = pattern.rstrip("/")
    return (
        fnmatch.fnmatch(path, normalized)
        or fnmatch.fnmatch(path, normalized + "/*")
        or path == normalized
        or path.startswith(normalized + "/")
    )


def _extract_referenced_paths(text: str) -> tuple[str, ...]:
    candidates = set()
    for match in re.findall(r"`([^`]+)`", text):
        for prefix in ROLE_PATH_PREFIXES:
            if match.startswith(prefix):
                candidates.add(match)
    for match in re.findall(r"\b(?:org|projects|research_areas|docs|src|scripts|papers|ztare_workspace|rubrics|orbit|supervisor)/[A-Za-z0-9_./-]+", text):
        candidates.add(match.rstrip(".,);:"))
    return tuple(sorted(candidates))


def _metadata_paths(metadata: dict[str, Any]) -> tuple[str, ...]:
    values = metadata.get("declared_paths") or metadata.get("touched_paths") or ()
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, (list, tuple)):
        return ()
    out = []
    for value in values:
        text = str(value).strip()
        if text:
            out.append(text)
    return tuple(sorted(set(out)))


def authorize_dispatch(
    *,
    role_id: str,
    candidate_source: str,
    candidate_text: str,
    metadata: dict[str, Any],
    unattended: bool,
) -> AuthorizationDecision:
    """Return whether a daemon may dispatch this candidate."""
    role = _load_role(role_id)
    budget = role.get("budget") if isinstance(role.get("budget"), dict) else {}
    single_cap = budget.get("single_action_cap_usd")

    if candidate_source == "principal-goal" and metadata.get("autonomous_scope_ok") is not True:
        return AuthorizationDecision(
            allowed=False,
            reason="principal task has autonomous_scope_ok=false",
            required_approval="principal",
            terminal=False,
        )

    # Resolved-pending-execution gates carry the principal's prior approval.
    # The original action is already authorized; we are dispatching the
    # already-approved intent. Do NOT open another approval gate — that
    # creates the recursive meta-approval loop the principal saw 2026-05-07.
    if candidate_source == "resolved-pending-execution":
        return AuthorizationDecision(
            allowed=True,
            reason="downstream of already-approved gate; principal authorized upstream",
            required_approval=None,
            terminal=False,
        )

    if candidate_source == "agent-channel":
        return AuthorizationDecision(
            allowed=False,
            reason="agent-channel messages are communication obligations, not execution authority",
            required_approval="principal",
            terminal=False,
        )

    if unattended and candidate_source != "principal-goal":
        return AuthorizationDecision(
            allowed=False,
            reason=f"{candidate_source} candidates cannot execute unattended; convert to principal task or approve via gate",
            required_approval="principal",
            terminal=False,
        )

    paths = tuple(sorted(set(_extract_referenced_paths(candidate_text) + _metadata_paths(metadata))))

    if unattended and "estimated_cost_usd" not in metadata:
        return AuthorizationDecision(
            allowed=False,
            reason="unattended dispatch requires explicit estimated_cost_usd",
            required_approval="principal",
            matched_paths=paths,
            terminal=False,
        )
    if unattended and not paths:
        return AuthorizationDecision(
            allowed=False,
            reason="unattended dispatch requires explicit referenced or declared paths",
            required_approval="principal",
            terminal=False,
        )

    try:
        estimated_cost = float(metadata.get("estimated_cost_usd", 0.0) or 0.0)
    except (TypeError, ValueError):
        estimated_cost = 0.0
    if single_cap is not None and estimated_cost > float(single_cap):
        return AuthorizationDecision(
            allowed=False,
            reason=f"estimated_cost_usd {estimated_cost:.2f} exceeds role single_action_cap_usd {float(single_cap):.2f}",
            required_approval="principal",
            terminal=False,
        )

    forbidden = tuple(role.get("forbidden_paths") or ())
    authorized = tuple(role.get("authorized_paths") or ())
    for path in paths:
        for pattern in forbidden:
            if _path_matches(path, pattern):
                return AuthorizationDecision(
                    allowed=False,
                    reason=f"referenced path {path} matches forbidden_paths rule {pattern}",
                    required_approval="principal",
                    matched_paths=paths,
                    terminal=True,
                )
        if unattended and authorized and "*" not in authorized:
            if not any(_path_matches(path, pattern) for pattern in authorized):
                return AuthorizationDecision(
                    allowed=False,
                    reason=f"referenced path {path} is outside role authorized_paths",
                    required_approval="principal",
                    matched_paths=paths,
                    terminal=True,
                )

    return AuthorizationDecision(
        allowed=True,
        reason="dispatch authorized",
        matched_paths=paths,
    )
