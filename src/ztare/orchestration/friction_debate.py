"""Friction-mode debate extension to `debate_orchestrator.py`.

Extends the existing parallel-critic debate substrate with FRICTION mode:
alternating rebuttal rounds (CHAMPION_EXIST / CHAMPION_NONEXIST / arbiter)
per Pattern-001 (`org/patterns/pattern_1_friction_debate.md`).

Like `debate_orchestrator.py`, this module is "non-agentic" — it manages
file-based JSON state in `projects/{project}/orchestration_state/{task_id}/`.
The actual LLM agents are spawned externally (Claude Code, Codex, etc.)
to fill the round files, then the arbiter merges via this module.

Per `org/INTERFACE.md`, this module imports nothing ZTARE-specific from
`org/` — `org/` is the dependency, not the dependent.

Usage:

    # Initialize a friction-mode debate task
    python -m src.ztare.orchestration.friction_debate init \\
        --project ns_millennium_hunt \\
        --task-id "rank_2_existence" \\
        --question "Does any rank-2 multi-Liouvillian solution exist?"

    # After agents fill round_{1..5}.json, merge to verdict
    python -m src.ztare.orchestration.friction_debate merge \\
        --project ns_millennium_hunt \\
        --task-id "rank_2_existence"
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]


def _slugify(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", text).strip("_") or "task"


def _state_root(project: str) -> Path:
    return REPO_ROOT / "projects" / project / "orchestration_state"


def _task_dir(project: str, task_id: str) -> Path:
    return _state_root(project) / _slugify(task_id)


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _round_template(
    task_id: str, round_n: int, role: str, question: str
) -> dict[str, Any]:
    """JSON template for one round of friction debate."""
    role_directives = {
        1: "CHAMPION_EXIST: assume the proposition holds. Construct explicit candidate / proof / mechanism. Use construction freedom.",
        2: "CHAMPION_NONEXIST: rebut. Identify the EXACT step where Round 1 fails. Use construction freedom.",
        3: "CHAMPION_EXIST: respond. Either repair the construction or concede a specific class.",
        4: "CHAMPION_NONEXIST: tighten the verdict.",
        5: "ARBITER: synthesize the joint verdict. Final answer + precise theorem statement OR explicit counterexample.",
    }
    return {
        "task_id": task_id,
        "round": round_n,
        "role": role,
        "directive": role_directives.get(round_n, ""),
        "question": question,
        "claim": "",
        "argument": "",
        "construction_or_counter": "",
        "concedes": False,
        "next_action": "",
        "references_round": None,  # which prior round this responds to
    }


def init_task(project: str, task_id: str, question: str) -> Path:
    """Initialize a friction-mode debate task with 5 round-templates."""
    task_dir = _task_dir(project, task_id)
    task_dir.mkdir(parents=True, exist_ok=True)

    metadata = {
        "task_id": task_id,
        "project": project,
        "pattern_id": "PATTERN-001",
        "pattern_name": "friction_debate",
        "question": question,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "initialized",
    }
    _write_json(task_dir / "metadata.json", metadata)

    # Round role-assignments
    role_map = {
        1: "champion_exist",
        2: "champion_nonexist",
        3: "champion_exist",
        4: "champion_nonexist",
        5: "arbiter",
    }
    for round_n in range(1, 6):
        round_path = task_dir / f"round_{round_n}.json"
        if not round_path.exists():
            _write_json(
                round_path,
                _round_template(task_id, round_n, role_map[round_n], question),
            )

    instructions_md = (
        f"# Friction Debate: {task_id}\n\n"
        f"**Pattern**: PATTERN-001 friction_debate\n"
        f"**Question**: {question}\n\n"
        "## Protocol\n\n"
        "Five rounds with friction enforced:\n\n"
        "1. **Round 1 — CHAMPION_EXIST**: assume the proposition holds. Construct.\n"
        "2. **Round 2 — CHAMPION_NONEXIST**: rebut. Identify exact failure step.\n"
        "3. **Round 3 — CHAMPION_EXIST**: respond.\n"
        "4. **Round 4 — CHAMPION_NONEXIST**: tighten verdict.\n"
        "5. **Round 5 — ARBITER**: joint verdict.\n\n"
        "## State files\n\n"
        "- `metadata.json` — task metadata\n"
        "- `round_1.json` ... `round_5.json` — fill each with structured argument\n"
        "- After all 5 rounds filled, run `merge` to produce `verdict.md`\n"
    )
    (task_dir / "README.md").write_text(instructions_md, encoding="utf-8")
    return task_dir


def merge_task(project: str, task_id: str) -> tuple[Path, dict[str, Any]]:
    """Merge 5 rounds into a verdict.md + verdict.json."""
    task_dir = _task_dir(project, task_id)
    if not task_dir.exists():
        raise SystemExit(f"Friction debate task not found: {task_id}")
    metadata = json.loads((task_dir / "metadata.json").read_text(encoding="utf-8"))

    rounds: list[dict[str, Any]] = []
    missing: list[int] = []
    for round_n in range(1, 6):
        path = task_dir / f"round_{round_n}.json"
        if not path.exists():
            missing.append(round_n)
            continue
        rounds.append(json.loads(path.read_text(encoding="utf-8")))
    if missing:
        raise SystemExit(f"Missing rounds: {missing}")

    # Per DARWIN catch H4 (2026-05-08): support early concession.
    # Scan rounds for first `concedes: True` and short-circuit; otherwise
    # fall through to Round 5 arbiter as the joint verdict.
    joint_verdict_round = 5  # default
    for r in rounds:
        if r.get("concedes") is True:
            joint_verdict_round = r["round"]
            break
    joint_verdict_text = rounds[joint_verdict_round - 1].get("argument", "")
    verdict = {
        "task_id": task_id,
        "project": project,
        "pattern_id": "PATTERN-001",
        "question": metadata["question"],
        "rounds": rounds,
        "joint_verdict_round": joint_verdict_round,
        "joint_verdict": joint_verdict_text,
        "merged_utc": datetime.now(timezone.utc).isoformat(),
    }
    _write_json(task_dir / "verdict.json", verdict)

    md_lines = [
        f"# Friction Debate Verdict — {task_id}",
        "",
        f"**Question**: {metadata['question']}",
        f"**Pattern**: PATTERN-001 friction_debate",
        "",
        "## Round summaries",
        "",
    ]
    for r in rounds:
        md_lines.append(f"### Round {r['round']} — {r['role']}")
        md_lines.append("")
        md_lines.append(f"**Directive**: {r.get('directive', '')}")
        md_lines.append("")
        md_lines.append(f"**Claim**: {r.get('claim', '')}")
        md_lines.append("")
        md_lines.append(f"**Argument**: {r.get('argument', '')}")
        md_lines.append("")
        if r.get("concedes"):
            md_lines.append("**Concedes**: yes")
            md_lines.append("")
    md_lines.append(f"## Joint verdict (from Round {joint_verdict_round})")
    md_lines.append("")
    if joint_verdict_round != 5:
        md_lines.append(
            f"_Note: early concession in Round {joint_verdict_round}; "
            "verdict extracted from concession round, not Round 5 arbiter._"
        )
        md_lines.append("")
    md_lines.append(joint_verdict_text or "(empty)")
    md_path = task_dir / "verdict.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    return md_path, verdict


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Friction-mode debate orchestrator (PATTERN-001)"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    init = sub.add_parser("init", help="Initialize a friction-mode debate")
    init.add_argument("--project", required=True)
    init.add_argument("--task-id", required=True)
    init.add_argument("--question", required=True)

    merge = sub.add_parser("merge", help="Merge filled rounds into a verdict")
    merge.add_argument("--project", required=True)
    merge.add_argument("--task-id", required=True)

    show = sub.add_parser("show", help="Show task files")
    show.add_argument("--project", required=True)
    show.add_argument("--task-id", required=True)

    args = parser.parse_args()
    if args.cmd == "init":
        path = init_task(args.project, args.task_id, args.question)
        print(path)
        return 0
    if args.cmd == "merge":
        md_path, _verdict = merge_task(args.project, args.task_id)
        print(md_path)
        return 0
    if args.cmd == "show":
        task_dir = _task_dir(args.project, args.task_id)
        if not task_dir.exists():
            print(f"task not found: {task_dir}")
            return 1
        for path in sorted(task_dir.iterdir()):
            print(f"- {path.name}")
        return 0
    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
