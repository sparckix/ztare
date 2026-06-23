from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from ztare.common.paths import PROJECTS_DIR
from ztare.orchestration.arbiter import merge_critic_reports, render_markdown
from ztare.orchestration.artifact_bundle import build_stage1_fail_bundle, bundle_to_dict


DEFAULT_CRITICS = ["critic_a", "critic_b"]


def _slugify(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", text).strip("_") or "task"


def _queue_root(project: str) -> Path:
    return PROJECTS_DIR / project / "debate_queue"


def _reports_root(project: str) -> Path:
    return PROJECTS_DIR / project / "debate_reports"


def _task_dir(project: str, task_id: str) -> Path:
    return _queue_root(project) / task_id


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _critic_template(task_id: str, critic: str) -> dict[str, Any]:
    return {
        "task_id": task_id,
        "critic": critic,
        "findings": [],
        "do_not_change": [],
        "next_action": "",
        "requires_human_review": False,
    }


def init_task(project: str, run_id: str | None, critics: list[str]) -> Path:
    bundle = build_stage1_fail_bundle(project, run_id=run_id)
    task_id = _slugify(bundle.task_id)
    task_dir = _task_dir(project, task_id)
    task_dir.mkdir(parents=True, exist_ok=True)

    bundle_dict = bundle_to_dict(bundle)
    _write_json(task_dir / "bundle.json", bundle_dict)

    instructions = [
        f"# Debate Task: {task_id}",
        "",
        "Read `bundle.json` and fill one JSON file per critic.",
        "Required finding fields:",
        "- `id`",
        "- `severity`",
        "- `claim`",
        "- `evidence`",
        "- `proposed_fix`",
        "- `confidence`",
        "",
        "Decision rule:",
        "- Identify whether a reported failure is a gate failure, a thesis/specimen failure, or a benchmark/contract failure.",
        "- Do not weaken target-case detection without explicit justification.",
        "- If two failure types differ, separate them instead of collapsing them into one fix.",
        "",
    ]
    (task_dir / "README.md").write_text("\n".join(instructions), encoding="utf-8")

    for critic in critics:
        template_path = task_dir / f"{critic}.json"
        if not template_path.exists():
            _write_json(template_path, _critic_template(task_id, critic))

    return task_dir


def merge_task(project: str, task_id: str, critics: list[str]) -> tuple[Path, dict[str, Any]]:
    task_dir = _task_dir(project, task_id)
    if not task_dir.exists():
        raise SystemExit(f"Debate task not found: {task_id}")
    bundle = json.loads((task_dir / "bundle.json").read_text(encoding="utf-8"))

    reports: dict[str, dict[str, Any]] = {}
    missing: list[str] = []
    for critic in critics:
        path = task_dir / f"{critic}.json"
        if not path.exists():
            missing.append(critic)
            continue
        reports[critic] = json.loads(path.read_text(encoding="utf-8"))
    if missing:
        raise SystemExit(f"Missing critic report(s): {', '.join(missing)}")

    merged = merge_critic_reports(bundle["task_id"], reports)
    markdown = render_markdown(bundle, merged, critics)

    out_root = _reports_root(project)
    out_root.mkdir(parents=True, exist_ok=True)
    json_path = out_root / f"{task_id}.json"
    md_path = out_root / f"{task_id}.md"
    _write_json(json_path, merged)
    md_path.write_text(markdown, encoding="utf-8")
    return md_path, merged


def show_task(project: str, task_id: str) -> None:
    task_dir = _task_dir(project, task_id)
    if not task_dir.exists():
        raise SystemExit(f"Debate task not found: {task_id}")
    print(task_dir)
    for path in sorted(task_dir.iterdir()):
        print(f"- {path.name}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Simple non-agentic debate orchestrator for evaluator failures."
    )
    parser.add_argument("--project", default="epistemic_engine_v4")
    parser.add_argument("--critics", nargs="*", default=DEFAULT_CRITICS)

    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init-stage1-fail", help="Create a debate task from the current stage-1 fail bundle.")
    init_parser.add_argument("--run-id", default=None)

    merge_parser = subparsers.add_parser("merge", help="Merge critic reports into a decision report.")
    merge_parser.add_argument("task_id")

    show_parser = subparsers.add_parser("show", help="Show files for a debate task.")
    show_parser.add_argument("task_id")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "init-stage1-fail":
        task_dir = init_task(args.project, args.run_id, args.critics)
        print(task_dir)
        return 0
    if args.command == "merge":
        md_path, merged = merge_task(args.project, args.task_id, args.critics)
        print(md_path)
        print(f"decision={merged['decision']}")
        return 0
    if args.command == "show":
        show_task(args.project, args.task_id)
        return 0

    parser.error("Unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
