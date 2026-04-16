"""GP-070 Goal Orchestrator — CLI (C-20, C-22, C-23) + Slice B (C-21, C-26).

Commands:
  ztare goal advance <slug> --to <next_stage> [--artifacts <path>...] [--git-commit]
  ztare goal resume <slug> [--acknowledge-drift] [--git-commit]
  ztare goal status [<slug>]
  ztare goal create <name> --type <target_type> --description <desc>
  ztare goal validate <config_path>

Usage:
  python -m src.ztare.orchestration.cli <command> [args]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from src.ztare.orchestration.core import (
    GoalConfig,
    GoalState,
    GoalStatus,
    validate_transition,
)
from src.ztare.orchestration.config_parser import (
    list_available_goal_types,
    load_goal_config,
    parse_goal_config,
)
from src.ztare.orchestration.gate_escalation import write_gate_escalation
from src.ztare.orchestration.persistence import (
    GOALS_ROOT,
    append_transition,
    check_artifact_drift,
    check_consistency,
    goal_dir,
    goal_lock,
    hash_artifacts,
    read_state,
    read_transitions,
    write_state,
)
from src.ztare.orchestration.adapters.dispatch import (
    dispatch,
    stage_guidance,
)


def _output(data: dict) -> None:
    print(json.dumps(data, indent=2))


# ---------------------------------------------------------------------------
# C-26: CLAUDE.md auto-maintenance of ## Active Goals section
# ---------------------------------------------------------------------------

_AGENTS_MD = Path("AGENTS.md")
_GOALS_HEADER = "## Active Goals"
_GOALS_FENCE_START = "<!-- GP-070 active goals start -->"
_GOALS_FENCE_END = "<!-- GP-070 active goals end -->"


def _update_claude_md() -> None:
    """Maintain the Active Goals section in CLAUDE.md (C-26)."""
    goals = []
    if GOALS_ROOT.exists():
        for gd in sorted(GOALS_ROOT.iterdir()):
            if not gd.is_dir():
                continue
            state = read_state(gd.name)
            if state and state.status in (GoalStatus.ACTIVE, GoalStatus.GATE_PENDING):
                config, _ = load_goal_config(state.target_type)
                stage_def = config.stage_by_name(state.current_stage) if config else None
                guidance = stage_guidance(state, stage_def, config) if stage_def and config else ""
                goals.append((state, guidance))

    if not goals:
        block = ""
    else:
        lines = [_GOALS_FENCE_START, "", _GOALS_HEADER, ""]
        for state, guidance in goals:
            status = state.status.value.upper()
            lines.append(f"- **{state.name}** (`{state.slug}`)")
            lines.append(f"  - Stage: `{state.current_stage}` — Status: `{status}`")
            if guidance:
                for gl in guidance.split("\n"):
                    lines.append(f"  - {gl.strip()}")
            lines.append("")
        lines.append(_GOALS_FENCE_END)
        block = "\n".join(lines)

    if not _AGENTS_MD.exists():
        return

    content = _AGENTS_MD.read_text()

    if _GOALS_FENCE_START in content:
        import re
        start_idx = content.index(_GOALS_FENCE_START)
        end_idx = content.index(_GOALS_FENCE_END, start_idx) + len(_GOALS_FENCE_END)
        content = content[:start_idx] + block + content[end_idx:]
    elif block:
        content = content.rstrip() + "\n\n" + block + "\n"

    _AGENTS_MD.write_text(content)


# ---------------------------------------------------------------------------
# C-22: --git-commit flag
# ---------------------------------------------------------------------------

def _git_commit(slug: str, action: str, stage: str) -> None:
    """Auto-commit transition to git (C-22). Opt-in via --git-commit."""
    try:
        gd = goal_dir(slug)
        subprocess.run(
            ["git", "add", str(gd / "state.json"), str(gd / "transitions.jsonl")],
            capture_output=True, check=True,
        )
        if _AGENTS_MD.exists():
            subprocess.run(["git", "add", str(_AGENTS_MD)], capture_output=True)
        msg = f"goal({slug}): {action} → {stage}"
        subprocess.run(
            ["git", "commit", "-m", msg],
            capture_output=True, check=True,
        )
    except subprocess.CalledProcessError:
        pass


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_create(args: argparse.Namespace) -> int:
    config, errors = load_goal_config(args.type)
    if errors:
        _output({"error": "config_invalid", "details": errors})
        return 1

    assert config is not None
    state = GoalState.create(
        name=args.name,
        description=args.description,
        config=config,
        owner=args.owner or "",
    )

    gd = goal_dir(state.slug)
    gd.mkdir(parents=True, exist_ok=True)

    with goal_lock(state.slug):
        if (gd / "state.json").exists():
            _output({"error": "goal_exists", "slug": state.slug})
            return 1
        append_transition(
            state.slug,
            from_stage="",
            to_stage=state.current_stage,
            action="goal_created",
            reason=f"Goal '{state.name}' created with type '{config.target_type}'",
        )
        write_state(state.slug, state)

    _update_claude_md()

    entry_def = config.stage_by_name(state.current_stage)
    guidance = stage_guidance(state, entry_def, config) if entry_def else ""

    _output({
        "created": True,
        "slug": state.slug,
        "current_stage": state.current_stage,
        "stage_description": entry_def.description if entry_def else "",
        "guidance": guidance,
    })
    return 0


def cmd_advance(args: argparse.Namespace) -> int:
    slug = args.slug

    consistency_error = check_consistency(slug)
    if consistency_error:
        _output({"error": "audit_integrity_violation", "details": consistency_error})
        return 2

    config, errors = load_goal_config(args.type) if args.type else (None, [])
    if not args.type:
        state = read_state(slug)
        if state is None:
            _output({"error": "goal_not_found", "slug": slug})
            return 1
        config, errors = load_goal_config(state.target_type)

    if errors or config is None:
        _output({"error": "config_invalid", "details": errors})
        return 1

    with goal_lock(slug):
        state = read_state(slug)
        if state is None:
            _output({"error": "goal_not_found", "slug": slug})
            return 1

        if state.status == GoalStatus.GATE_PENDING:
            _output({
                "accepted": False,
                "reason": f"Goal is gate-pending at stage '{state.current_stage}'. Use 'resume' to clear.",
                "current_stage": state.current_stage,
            })
            return 1

        if config.is_terminal(state.current_stage):
            _output({
                "accepted": False,
                "reason": f"Goal is at terminal stage '{state.current_stage}'.",
                "current_stage": state.current_stage,
            })
            return 1

        proposed = args.to or config.next_stage_default(state.current_stage)
        if not proposed:
            _output({
                "accepted": False,
                "reason": "No next stage specified and no default available.",
                "current_stage": state.current_stage,
            })
            return 1

        validation_error = validate_transition(config, state.current_stage, proposed)
        if validation_error:
            _output({
                "accepted": False,
                "reason": validation_error,
                "current_stage": state.current_stage,
            })
            return 1

        next_stage_def = config.stage_by_name(proposed)
        artifact_paths = [Path(p) for p in (args.artifacts or [])]
        art_hashes = hash_artifacts(artifact_paths) if artifact_paths else {}

        is_gate = next_stage_def.is_gate if next_stage_def else False

        append_transition(
            slug,
            from_stage=state.current_stage,
            to_stage=proposed,
            action="advance",
            reason=args.reason or "",
            artifact_hashes=art_hashes,
        )

        state.current_stage = proposed
        if is_gate:
            state.status = GoalStatus.GATE_PENDING
            state.gate_pending_reason = next_stage_def.gate_description if next_stage_def else ""
            state.gate_escalation_hashes = art_hashes

            write_state(slug, state)

            write_gate_escalation(
                goal_slug=slug,
                goal_name=state.name,
                stage=proposed,
                gate_description=state.gate_pending_reason,
                artifact_hashes=art_hashes,
            )
        else:
            state.status = GoalStatus.ACTIVE
            state.gate_pending_reason = None
            write_state(slug, state)

    _update_claude_md()

    if hasattr(args, "git_commit") and args.git_commit:
        _git_commit(slug, "advance", proposed)

    # Dispatch guidance for the new stage (Slice B item 2)
    guidance = stage_guidance(state, next_stage_def, config) if next_stage_def else ""

    _output({
        "accepted": True,
        "current_stage": proposed,
        "next_stage_description": next_stage_def.description if next_stage_def else "",
        "gate_pending": is_gate,
        "gate_description": state.gate_pending_reason if is_gate else None,
        "guidance": guidance,
    })
    return 0


def cmd_resume(args: argparse.Namespace) -> int:
    slug = args.slug

    consistency_error = check_consistency(slug)
    if consistency_error:
        _output({"error": "audit_integrity_violation", "details": consistency_error})
        return 2

    state = read_state(slug)
    if state is None:
        _output({"error": "goal_not_found", "slug": slug})
        return 1

    config, errors = load_goal_config(state.target_type)
    if errors or config is None:
        _output({"error": "config_invalid", "details": errors})
        return 1

    if state.status != GoalStatus.GATE_PENDING:
        _output({
            "accepted": False,
            "reason": f"Goal is not gate-pending (status: {state.status.value}).",
            "current_stage": state.current_stage,
        })
        return 1

    with goal_lock(slug):
        state = read_state(slug)
        if state is None or state.status != GoalStatus.GATE_PENDING:
            _output({"error": "state_changed", "details": "Re-read state differs."})
            return 1

        current_hashes = hash_artifacts(
            [Path(p) for p in state.gate_escalation_hashes.keys()]
        )
        has_drift, drifted_files = check_artifact_drift(slug, current_hashes)

        stage_def = config.stage_by_name(state.current_stage)
        strict = stage_def.strict_gate_mode if stage_def else False

        if has_drift and strict and not args.acknowledge_drift:
            _output({
                "accepted": False,
                "reason": "Artifact drift detected in strict gate mode. Use --acknowledge-drift to proceed.",
                "drifted_files": drifted_files,
                "current_stage": state.current_stage,
            })
            return 1

        next_stage = config.next_stage_default(state.current_stage)

        append_transition(
            slug,
            from_stage=state.current_stage,
            to_stage=next_stage or state.current_stage,
            action="gate_resume",
            reason=f"Operator cleared gate at '{state.current_stage}'",
            artifact_hashes=current_hashes,
            artifact_drift=has_drift,
            drifted_files=drifted_files,
        )

        if next_stage:
            state.current_stage = next_stage

        next_def = config.stage_by_name(state.current_stage)
        is_next_gate = next_def.is_gate if next_def else False

        if is_next_gate:
            state.status = GoalStatus.GATE_PENDING
            state.gate_pending_reason = next_def.gate_description if next_def else ""
            state.gate_escalation_hashes = {}
            write_state(slug, state)
            write_gate_escalation(
                goal_slug=slug,
                goal_name=state.name,
                stage=state.current_stage,
                gate_description=state.gate_pending_reason,
            )
        else:
            state.status = GoalStatus.ACTIVE
            state.gate_pending_reason = None
            state.gate_escalation_hashes = {}
            write_state(slug, state)

    _update_claude_md()

    if hasattr(args, "git_commit") and args.git_commit:
        _git_commit(slug, "gate_resume", state.current_stage)

    next_def = config.stage_by_name(state.current_stage) if state else None
    is_next_gate = next_def.is_gate if next_def else False
    guidance = stage_guidance(state, next_def, config) if next_def and config else ""

    _output({
        "accepted": True,
        "current_stage": state.current_stage,
        "next_stage_description": next_def.description if next_def else "",
        "artifact_drift": has_drift,
        "drifted_files": drifted_files,
        "gate_pending": is_next_gate,
        "guidance": guidance,
    })
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    if args.slug:
        state = read_state(args.slug)
        if state is None:
            _output({"error": "goal_not_found", "slug": args.slug})
            return 1

        config, _ = load_goal_config(state.target_type)
        stage_def = config.stage_by_name(state.current_stage) if config else None
        transitions = read_transitions(args.slug)
        guidance = stage_guidance(state, stage_def, config) if stage_def and config else ""

        _output({
            "slug": state.slug,
            "name": state.name,
            "target_type": state.target_type,
            "current_stage": state.current_stage,
            "stage_description": stage_def.description if stage_def else "",
            "status": state.status.value,
            "gate_pending_reason": state.gate_pending_reason,
            "created_at": state.created_at,
            "transition_count": len(transitions),
            "guidance": guidance,
        })
        return 0

    if not GOALS_ROOT.exists():
        _output({"goals": []})
        return 0

    goals = []
    for gd in sorted(GOALS_ROOT.iterdir()):
        if not gd.is_dir():
            continue
        state = read_state(gd.name)
        if state:
            goals.append({
                "slug": state.slug,
                "name": state.name,
                "status": state.status.value,
                "current_stage": state.current_stage,
            })
    _output({"goals": goals})
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    config_path = Path(args.config_path)
    config, errors = parse_goal_config(config_path)
    if errors:
        _output({"valid": False, "errors": errors})
        return 1
    _output({
        "valid": True,
        "target_type": config.target_type if config else "",
        "stages": config.stage_names() if config else [],
        "entry_stage": config.entry_stage if config else "",
        "terminal_stages": config.terminal_stages if config else [],
    })
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="ztare-goal",
        description="GP-070 Goal Orchestrator CLI",
    )
    sub = parser.add_subparsers(dest="command")

    p_create = sub.add_parser("create", help="Create a new goal")
    p_create.add_argument("name")
    p_create.add_argument("--type", required=True)
    p_create.add_argument("--description", default="")
    p_create.add_argument("--owner", default="")

    p_advance = sub.add_parser("advance", help="Propose a stage transition")
    p_advance.add_argument("slug")
    p_advance.add_argument("--to", default=None)
    p_advance.add_argument("--type", default=None)
    p_advance.add_argument("--artifacts", nargs="*")
    p_advance.add_argument("--reason", default="")
    p_advance.add_argument("--git-commit", action="store_true", help="Auto-commit transition to git (C-22)")

    p_resume = sub.add_parser("resume", help="Clear a gate after operator review")
    p_resume.add_argument("slug")
    p_resume.add_argument("--acknowledge-drift", action="store_true")
    p_resume.add_argument("--git-commit", action="store_true", help="Auto-commit transition to git (C-22)")

    p_status = sub.add_parser("status", help="Check goal status")
    p_status.add_argument("slug", nargs="?", default=None)

    p_validate = sub.add_parser("validate", help="Validate a goal-type config")
    p_validate.add_argument("config_path")

    args = parser.parse_args()

    if args.command == "create":
        return cmd_create(args)
    elif args.command == "advance":
        return cmd_advance(args)
    elif args.command == "resume":
        return cmd_resume(args)
    elif args.command == "status":
        return cmd_status(args)
    elif args.command == "validate":
        return cmd_validate(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
