"""CLI wrapper for goals_inbox (GP-132) — enables hook-based surfacing.

Usage:
    python -m src.ztare.orchestration.goals_inbox_cli list [--assigned-to role.manager]
    python -m src.ztare.orchestration.goals_inbox_cli show <goal_id>

This CLI's primary purpose is to be invokable from a Claude Code
`SessionStart` hook (or the cron cycle's first step) so that pending
goals are injected into the agent's context on wake — converting
"agent remembers to look at goals/" from honor-system to runtime.
"""

from __future__ import annotations

import argparse
import sys

from src.ztare.orchestration import goals_inbox as gi
from src.ztare.signals import damage


def cmd_list(args: argparse.Namespace) -> int:
    goals = gi.list_pending_goals(assigned_to=args.assigned_to)
    active = gi.list_active_goals()

    if not goals and not active:
        print("[goals-inbox] No pending or active goals.")
        return 0

    if goals:
        print(f"[goals-inbox] {len(goals)} pending goal(s):")
        for g in goals:
            deadline = g.deadline or "no-deadline"
            scope_tag = "AUTO-OK" if g.autonomous_scope_ok else "NEEDS-ESCALATION"
            print(
                f"  [{g.priority.upper():>6}] {g.goal_id:<40} "
                f"deadline={deadline}  cost=${g.estimated_cost_usd:.2f}  "
                f"assigned={g.assigned_to}  {scope_tag}"
            )

    if active:
        print(f"[goals-inbox] {len(active)} active (claimed) goal(s):")
        for g in active:
            print(
                f"  [{g.priority.upper():>6}] {g.goal_id:<40} "
                f"(working on)"
            )

    # Critical-severity signal if any urgent goal is >48h old with no claim
    # (future enhancement: compute from frontmatter)

    # Mark this session as "inspected" by emitting a benign info signal.
    # The enforcement auto-emitter (autoemit.check_goals_inspected) can
    # diff this against session close to detect skipped inspections.
    damage.emit(
        source="goals_inbox_cli.list",
        kind="goals_inspected",
        detail=f"listed {len(goals)} pending, {len(active)} active goals",
        severity="info",
    )
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    goals = gi.list_pending_goals() + gi.list_active_goals()
    for g in goals:
        if g.goal_id == args.goal_id:
            print(f"# {g.goal_id}")
            print(f"# path: {g.path}")
            print(f"# priority: {g.priority}; deadline: {g.deadline}; "
                  f"cost: ${g.estimated_cost_usd}; assigned: {g.assigned_to}; "
                  f"autonomous_scope_ok: {g.autonomous_scope_ok}")
            print("---")
            print(g.body)
            return 0
    print(f"[goals-inbox] goal not found: {args.goal_id}", file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ztare goals",
        description="List or show principal-goals (GP-132)."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="List pending + active goals.")
    p_list.add_argument("--assigned-to", default=None,
                        help="Filter to goals assigned to this role, e.g. role.manager")
    p_list.set_defaults(func=cmd_list)

    p_show = sub.add_parser("show", help="Show a specific goal's body.")
    p_show.add_argument("goal_id")
    p_show.set_defaults(func=cmd_show)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
