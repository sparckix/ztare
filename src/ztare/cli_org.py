# Licensed under Business Source License 1.1 — see LICENSE-BSL
"""`ztare org` CLI — inspect org/ primitives.

Run as:  python -m src.ztare.cli_org <subcommand>

Subcommands:
    list-roles      list all roles + primary members + budget
    list-members    list all members + substrates + current roles
    list-workers    list all worker membranes
    status          one-shot org health check (registry validation,
                    active sessions, damage signals)
    closure-map     (GP-129 Kauffman pull-forward) enumerate the
                    research cycle and flag non-closure hotspots —
                    steps with only one qualified agent

This is a thin reporter; it does not mutate the org.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Callable

from src.ztare.roles.loader import Registry, load_registry
from src.ztare.sessions.session import active_sessions
from src.ztare.signals.damage import list_recent as list_damage


# ---------------------------------------------------------------------
# Research cycle definition (for closure-map).
# Each step lists (a) a human-readable description, (b) the set of
# role classes qualified to execute that step today. Edit this list
# when the research cycle evolves; the CLI reports hotspots.
# ---------------------------------------------------------------------
RESEARCH_CYCLE: list[dict[str, Any]] = [
    {"step": "seam",      "description": "frame the eigenquestion, debate the framing",
     "qualified_roles":   {"principal", "manager"}},
    {"step": "spec",      "description": "convert the seam into an implementable blueprint",
     "qualified_roles":   {"manager", "engineer"}},
    {"step": "code",      "description": "implement the spec, land tests",
     "qualified_roles":   {"engineer", "manager"}},
    {"step": "review",    "description": "adversarial critique / inversion pass",
     "qualified_roles":   {"reviewer", "engineer", "principal"}},
    {"step": "evidence",  "description": "run experiments, collect evidence",
     "qualified_roles":   {"manager", "engineer"}},
    {"step": "synthesis", "description": "write the findings up for an audience",
     "qualified_roles":   {"manager", "principal"}},
    {"step": "gate",      "description": "sign off on scope / ship / promotion",
     "qualified_roles":   {"principal"}},
]


def _print(obj: Any) -> None:
    if isinstance(obj, str):
        print(obj)
    else:
        print(json.dumps(obj, indent=2, default=str))


def cmd_list_roles(reg: Registry, _args: argparse.Namespace) -> int:
    rows = []
    for r in sorted(reg.roles.values(), key=lambda x: x.role_id):
        primaries = [m.member_id for m in reg.who_fills(r.role_id, primary_only=True)]
        rows.append({
            "role_id": r.role_id,
            "class": r.role_class,
            "primary_members": primaries,
            "daily_cap_usd": r.budget.daily_cap_usd,
            "signs_gates": len(r.signs_gates),
        })
    _print(rows)
    return 0


def cmd_list_members(reg: Registry, _args: argparse.Namespace) -> int:
    rows = []
    for m in sorted(reg.members.values(), key=lambda x: x.member_id):
        roles = [r.role_id for r in reg.roles_of(m.member_id)]
        rows.append({
            "member_id": m.member_id,
            "kind": m.kind,
            "display_name": m.display_name,
            "substrates": [s.name for s in m.substrates],
            "current_roles": roles,
        })
    _print(rows)
    return 0


def cmd_list_workers(reg: Registry, _args: argparse.Namespace) -> int:
    rows = []
    for w in sorted(reg.workers.values(), key=lambda x: x.worker_id):
        rows.append({
            "worker_id": w.worker_id,
            "tool": w.invocation.get("tool_name"),
            "subagent_type": w.invocation.get("subagent_type"),
            "fan_out_ok": w.invocation.get("fan_out_ok"),
            "cost_cap_usd": w.limits.get("single_action_cost_cap_usd"),
        })
    _print(rows)
    return 0


def cmd_status(reg: Registry, _args: argparse.Namespace) -> int:
    live = active_sessions()
    dmg = list_damage(limit=10)
    out = {
        "registry": {
            "roles": len(reg.roles),
            "members": len(reg.members),
            "workers": len(reg.workers),
            "assignments": len(reg.assignments),
        },
        "active_sessions": [
            {"role": s.role_id, "member": s.member_id,
             "substrate": s.substrate, "id": s.session_id}
            for s in live
        ],
        "damage_signals_recent": [
            {"source": d.source, "kind": d.kind,
             "severity": d.severity, "ts": d.timestamp_utc}
            for d in dmg
        ],
        "validation": "OK — load_registry() passed",
    }
    _print(out)
    return 0


def cmd_closure_map(reg: Registry, _args: argparse.Namespace) -> int:
    # For each cycle step: which currently-assigned members cover it?
    # A step is a non-closure hotspot if ≤1 distinct member covers it.
    role_to_members: dict[str, list[str]] = {}
    for r in reg.roles:
        role_to_members[r] = [m.member_id for m in reg.who_fills(r)]

    rows = []
    hotspots = []
    for entry in RESEARCH_CYCLE:
        step = entry["step"]
        qualified = entry["qualified_roles"]
        covering_members: set[str] = set()
        for role_id in qualified:
            covering_members.update(role_to_members.get(role_id, []))
        is_hotspot = len(covering_members) <= 1
        row = {
            "step": step,
            "description": entry["description"],
            "qualified_roles": sorted(qualified),
            "covering_members": sorted(covering_members),
            "coverage": len(covering_members),
            "non_closure_hotspot": is_hotspot,
        }
        rows.append(row)
        if is_hotspot:
            hotspots.append(step)

    _print({
        "cycle": rows,
        "hotspot_count": len(hotspots),
        "hotspot_steps": hotspots,
        "verdict": (
            "no hotspots — cycle is antifragile to single-agent failure"
            if not hotspots else
            f"hotspots: {hotspots} — single-point-of-failure risk "
            "per GP-129 Kauffman prediction #2"
        ),
    })
    return 0


COMMANDS: dict[str, Callable[[Registry, argparse.Namespace], int]] = {
    "list-roles":   cmd_list_roles,
    "list-members": cmd_list_members,
    "list-workers": cmd_list_workers,
    "status":       cmd_status,
    "closure-map":  cmd_closure_map,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ztare org",
        description="Inspect org/ primitives (roles, members, workers, sessions).",
    )
    parser.add_argument(
        "subcommand",
        choices=sorted(COMMANDS.keys()),
        help="what to list / inspect",
    )
    args = parser.parse_args(argv)

    try:
        reg = load_registry()
    except ValueError as exc:
        print(f"registry validation FAILED:\n{exc}", file=sys.stderr)
        return 2

    return COMMANDS[args.subcommand](reg, args)


if __name__ == "__main__":
    sys.exit(main())
