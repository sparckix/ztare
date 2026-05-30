#!/usr/bin/env python3
"""Create zero-spend Codex-agent audit panels from typed endpoint workmaps.

This is a scheduling/context artifact, not an LLM caller. It reads a structure
instantiation workmap (or any list of typed endpoint records) and emits a
manifest plus per-target prompts that can be handed to Codex subagents. The
goal is breadth-of-attack without external API spend: independent agents audit
distinct constructors and return one of:

  1. compile-safe routing/projection theorem to add,
  2. concrete missing primitive/source object,
  3. no useful move.

The script is deliberately substrate-agnostic. NS Track B is just one caller.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]
DEFAULT_WORKMAP = (
    REPO / "projects" / "ns_millennium_hunt" / "workspace" / "queries"
    / "ns_trackb_instantiation_workmap.json"
)
DEFAULT_OUT_DIR = (
    REPO / "projects" / "ns_millennium_hunt" / "workspace" / "queries"
    / "agent_panels"
)


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def read_records(path: Path) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return [r for r in raw if isinstance(r, dict)]
    for key in ("structures", "targets", "records", "items"):
        val = raw.get(key)
        if isinstance(val, list):
            return [r for r in val if isinstance(r, dict)]
    raise SystemExit(f"could not find list records in {path}")


def endpoint_name(row: dict[str, Any]) -> str:
    return str(row.get("name") or row.get("structure") or row.get("target") or "")


def priority(row: dict[str, Any]) -> float:
    for key in ("closure_priority_score", "leverage_score", "priority", "score"):
        val = row.get(key)
        if isinstance(val, (int, float)):
            return float(val)
    return 0.0


def select_records(
    records: list[dict[str, Any]],
    targets: list[str],
    exclude_regex: str | None,
    top: int,
) -> list[dict[str, Any]]:
    if targets:
        wanted = set(targets)
        selected = [r for r in records if endpoint_name(r) in wanted]
        missing = sorted(wanted - {endpoint_name(r) for r in selected})
        if missing:
            raise SystemExit(f"targets not found in workmap: {', '.join(missing)}")
    else:
        selected = sorted(records, key=priority, reverse=True)
    if exclude_regex:
        rx = re.compile(exclude_regex)
        selected = [r for r in selected if not rx.search(endpoint_name(r))]
    return selected[:top]


def lean_path(row: dict[str, Any]) -> str:
    file_stem = row.get("file")
    if not file_stem:
        return "(unknown)"
    return f"ztare_proofs/ZtareProofs/{file_stem}.lean"


def render_fields(row: dict[str, Any], max_fields: int) -> str:
    fields = row.get("fields") or []
    lines = []
    for field in fields[:max_fields]:
        if isinstance(field, dict):
            lines.append(f"- `{field.get('name')}` : `{field.get('type', '?')}`")
        else:
            lines.append(f"- `{field}`")
    if len(fields) > max_fields:
        lines.append(f"- ... {len(fields) - max_fields} more field(s)")
    return "\n".join(lines) if lines else "- (no fields listed)"


def build_prompt(row: dict[str, Any], repo: Path, max_fields: int) -> str:
    name = endpoint_name(row)
    field_block = render_fields(row, max_fields=max_fields)
    return f"""Repository: {repo}

Read-only typed endpoint constructor audit. Do not edit files.

Target: `{name}`
Primary file: `{lean_path(row)}`
Endpoint exposure: `{row.get('endpoint_exposure', 'unknown')}`
Downstream users: `{row.get('n_downstream_users', 'unknown')}`
Fields: `{row.get('n_fields', len(row.get('fields') or []))}`
Difficulty: `{row.get('difficulty_estimate', 'unknown')}`
Priority: `{priority(row):.2f}`

Fields to inspect:
{field_block}

Task:
Find exactly one of the following and return concise evidence with file/line refs:

1. A compile-safe routing/projection theorem Codex should add. The theorem must
   use existing source objects and should reduce duplicate proof routing without
   adding axioms, new obligations, or decorative wrappers.
2. A concrete missing primitive/source object blocking construction. Name the
   primitive and the existing downstream adapter it would feed.
3. No useful move. Explain why existing routing is already canonical.

Anti-tautology rules:
- Do not treat `P : Prop` as proof of `P`; look for paid proof fields.
- Do not add a structure field when a theorem-level projection is enough.
- Do not weaken the endpoint, change hypotheses, or route through the desired
  conclusion.
- If a source route is already present, prefer naming the exact projection over
  adding another wrapper.

Return format:
End with exactly one fenced JSON block that matches this schema. You may include
short prose before it, but the JSON block is what the harvester reads.

```json
{{
  "target": "{name}",
  "verdict": "compile_safe_projection | missing_primitive | no_useful_move",
  "useful": true,
  "summary": "one sentence",
  "patch_kind": "theorem_alias | projection_def | constructor | none",
  "insertion_point": "path:line or empty",
  "lean_code": "optional Lean snippet, empty if not applicable",
  "missing_primitive": "name of missing primitive/source object, empty if not applicable",
  "downstream_adapter": "existing adapter/theorem this would feed, empty if not applicable",
  "references": ["path:line"],
  "risk": "tautology/self-reference risk, or 'low'"
}}
```
"""


def write_panel(
    selected: list[dict[str, Any]],
    out_root: Path,
    slug: str,
    repo: Path,
    max_fields: int,
) -> Path:
    panel_dir = out_root / f"{utc_stamp()}_{slug}"
    panel_dir.mkdir(parents=True, exist_ok=True)
    jobs = []
    prompt_md = ["# Typed Endpoint Agent Panel", ""]
    for i, row in enumerate(selected, 1):
        name = endpoint_name(row)
        prompt = build_prompt(row, repo=repo, max_fields=max_fields)
        prompt_path = panel_dir / f"{i:02d}_{name}.prompt.md"
        prompt_path.write_text(prompt, encoding="utf-8")
        job = {
            "job_id": f"{i:02d}_{name}",
            "target": name,
            "file": row.get("file"),
            "lean_path": lean_path(row),
            "endpoint_exposure": row.get("endpoint_exposure"),
            "n_downstream_users": row.get("n_downstream_users"),
            "n_fields": row.get("n_fields"),
            "priority": priority(row),
            "difficulty": row.get("difficulty_estimate"),
            "prompt_path": str(prompt_path.relative_to(REPO)),
            "status": "not_started",
            "codex_verdict": "",
            "result_summary": "",
        }
        jobs.append(job)
        prompt_md.extend([
            f"## {i}. `{name}`",
            "",
            f"- Prompt: `{prompt_path.relative_to(REPO)}`",
            f"- File: `{lean_path(row)}`",
            f"- Priority: `{priority(row):.2f}`",
            "",
            "Expected agent verdict: `compile_safe_projection | missing_primitive | no_useful_move`",
            "",
        ])
    manifest = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "repo": str(repo),
        "panel_slug": slug,
        "n_jobs": len(jobs),
        "jobs": jobs,
        "interpretation_rule": {
            "promote_opt_in_panel": ">=3 useful jobs out of 5",
            "hold": "0-1 useful jobs out of 5",
            "ambiguous": "2 useful jobs out of 5",
        },
    }
    (panel_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")
    (panel_dir / "prompts.md").write_text("\n".join(prompt_md), encoding="utf-8")
    return panel_dir


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Generate zero-spend Codex-agent typed endpoint audit panels")
    ap.add_argument("--workmap", type=Path, default=DEFAULT_WORKMAP)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    ap.add_argument("--slug", default="typed_endpoint_panel")
    ap.add_argument("--top", type=int, default=5)
    ap.add_argument("--target", action="append", default=[],
                    help="target structure name; repeatable")
    ap.add_argument("--targets", nargs="*", default=[],
                    help="target structure names")
    ap.add_argument("--exclude-regex",
                    help="regex for endpoint names to exclude")
    ap.add_argument("--max-fields", type=int, default=16)
    args = ap.parse_args()

    records = read_records(args.workmap)
    targets = list(args.target) + list(args.targets)
    selected = select_records(
        records,
        targets=targets,
        exclude_regex=args.exclude_regex,
        top=args.top,
    )
    panel_dir = write_panel(
        selected,
        out_root=args.out_dir,
        slug=args.slug,
        repo=REPO,
        max_fields=args.max_fields,
    )
    print(f"wrote panel: {panel_dir.relative_to(REPO)}")
    print(f"jobs: {len(selected)}")
    for row in selected:
        print(f"  - {endpoint_name(row)} ({lean_path(row)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
