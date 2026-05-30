"""Lightweight command-surface discovery for the org runtime.

The goal is not to be a shell parser. The goal is to make existing repo
commands legible to the daemon so it can prefer them over ad hoc scripts.
"""

from __future__ import annotations

import re
import os
from functools import lru_cache
from pathlib import Path

from src.ztare.common.paths import REPO_ROOT


MAKE_TARGET_RE = re.compile(r"^([A-Za-z0-9_.-]+):", re.MULTILINE)
MAKE_TOKEN_RE = re.compile(r"\bmake\s+([A-Za-z0-9_.-]+)\b")
PYTHON_SCRIPT_RE = re.compile(r"\bpython(?:3)?\s+([A-Za-z0-9_./-]+\.py)\b")
SHELL_SCRIPT_RE = re.compile(r"\b(?:bash|zsh|sh)\s+([A-Za-z0-9_./-]+\.sh)\b")


@lru_cache(maxsize=1)
def list_make_targets(repo_root: Path = REPO_ROOT) -> frozenset[str]:
    makefile = repo_root / "Makefile"
    if not makefile.exists():
        return frozenset()
    text = makefile.read_text(encoding="utf-8", errors="ignore")
    targets = {
        match.group(1)
        for match in MAKE_TARGET_RE.finditer(text)
        if "%" not in match.group(1) and not match.group(1).startswith(".")
    }
    return frozenset(targets)


def _command_surface_roots(repo_root: Path = REPO_ROOT) -> tuple[Path, ...]:
    roots: list[Path] = [repo_root]
    extra = os.environ.get("ZTARE_COMMAND_SURFACE_EXTRA_ROOTS", "")
    for raw in extra.split(os.pathsep):
        if raw.strip():
            roots.append(Path(raw).expanduser())
    sibling_cognitive_firm = repo_root.parent / "cognitive-firm"
    if sibling_cognitive_firm.exists():
        roots.append(sibling_cognitive_firm)

    out: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        try:
            resolved = root.resolve()
        except Exception:  # noqa: BLE001
            resolved = root
        key = str(resolved)
        if key not in seen and root.exists():
            out.append(root)
            seen.add(key)
    return tuple(out)


def _command_path(path: Path, repo_root: Path = REPO_ROOT) -> str:
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return os.path.relpath(path, repo_root).replace(os.sep, "/")


@lru_cache(maxsize=1)
def list_python_entrypoints(repo_root: Path = REPO_ROOT) -> frozenset[str]:
    paths = set()
    for surface_root in _command_surface_roots(repo_root):
        for root_name in ("scripts", "src"):
            root = surface_root / root_name
            if not root.exists():
                continue
            for path in root.rglob("*.py"):
                if ".venv" in path.parts or "__pycache__" in path.parts or ".git" in path.parts:
                    continue
                paths.add(_command_path(path, repo_root))
    return frozenset(paths)


@lru_cache(maxsize=1)
def list_shell_entrypoints(repo_root: Path = REPO_ROOT) -> frozenset[str]:
    paths = set()
    for surface_root in _command_surface_roots(repo_root):
        for root_name in ("scripts", "projects"):
            root = surface_root / root_name
            if not root.exists():
                continue
            for path in root.rglob("*.sh"):
                if (
                    "remote_results" in path.parts
                    or ".venv" in path.parts
                    or "node_modules" in path.parts
                    or ".git" in path.parts
                ):
                    continue
                paths.add(_command_path(path, repo_root))
    return frozenset(paths)


def _append_once(items: list[str], candidate: str) -> None:
    if candidate not in items:
        items.append(candidate)


def _keyword_command_hints(normalized: str) -> list[str]:
    hints: list[str] = []
    if "neural_hunt" in normalized and any(
        token in normalized for token in ("gpu", "oe-eval", "olmes", "h22", "h25")
    ):
        for rel in (
            "projects/neural_hunt/workspace/h25_h22_gpu_smoke_dry_run_commands_2026_05_09.sh",
            "projects/neural_hunt/workspace/h22_olmes_dry_run_commands_2026_05_08.sh",
            "projects/neural_hunt/workspace/h22_olmes_filled_run_commands_2026_05_08.sh",
        ):
            if rel in list_shell_entrypoints():
                hints.append(f"bash {rel}")
    if any(token in normalized for token in ("gp163d", "three_d_gravity_sandbox")) and any(
        token in normalized for token in ("gpu", "remote", "host", "ssh")
    ):
        for rel in (
            "projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/deploy_and_launch_gpu_batch.sh",
            "projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/deploy_and_launch_field_slice.sh",
            "projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/deploy_and_launch_invariance_threshold.sh",
        ):
            if rel in list_shell_entrypoints():
                hints.append(f"bash {rel}")
    return hints


def command_surface_matches(text: str) -> list[str]:
    """Return exact repo commands referenced by a task or prompt body."""
    normalized = text.lower()
    matches: list[str] = []

    for target in sorted(list_make_targets()):
        if f"make {target}".lower() in normalized or target.lower() in normalized:
            candidate = f"make {target}"
            _append_once(matches, candidate)

    for rel in sorted(list_python_entrypoints()):
        basename = Path(rel).name.lower()
        if rel.lower() in normalized or basename in normalized:
            candidate = f"python {rel}"
            _append_once(matches, candidate)

    for rel in sorted(list_shell_entrypoints()):
        basename = Path(rel).name.lower()
        if rel.lower() in normalized or (len(basename) >= 16 and basename in normalized):
            candidate = f"bash {rel}"
            _append_once(matches, candidate)

    for target in MAKE_TOKEN_RE.findall(text):
        candidate = f"make {target}"
        if target in list_make_targets():
            _append_once(matches, candidate)

    for rel in PYTHON_SCRIPT_RE.findall(text):
        rel = rel.rstrip(".,);:")
        candidate = f"python {rel}"
        if rel in list_python_entrypoints():
            _append_once(matches, candidate)

    for rel in SHELL_SCRIPT_RE.findall(text):
        rel = rel.rstrip(".,);:")
        candidate = f"bash {rel}"
        if rel in list_shell_entrypoints():
            _append_once(matches, candidate)

    for candidate in _keyword_command_hints(normalized):
        _append_once(matches, candidate)

    return matches


def command_surface_hint(text: str) -> str:
    matches = command_surface_matches(text)
    if not matches:
        return "No exact repo command matched the task text."
    return "Known repo command surface: " + ", ".join(f"`{m}`" for m in matches)
