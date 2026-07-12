"""Governed-agenda steering — inject the DECISION KERNEL's ranked "what to test next" into the loop's mutation
prompt as a fail-open, rubric-gated DIRECTIVE block, mirroring `compute_dag_steering_context` exactly.

The kernel's `scenarios.agenda.emit_governed_agenda` writes `workspace/governed_agenda.jsonl` — the governed map's
value-of-information + Pareto-frontier ranking of what to resolve next. This renders its top on-frontier rows so
the loop's next mutation PREFERS the highest-value governed experiment. It is DIRECTIVE steering (a prompt block
the agent reads), never control flow: the loop has no experiment executor, and top rows are often real-world tests
it cannot run, so it steers attention and echoes the consumed `agenda_id` to iteration history for auditable
consumption. Default-off (rubric flag `enable_governed_agenda_steering`) so it can never regress a run that doesn't
opt in. Closes the kernel→loop two-lane split (the producer had zero consumers) with no second orchestration path.
"""
from __future__ import annotations

import json
from pathlib import Path


def _load_governed_agenda(workspace_dir: Path) -> "list[dict]":
    path = Path(workspace_dir) / "governed_agenda.jsonl"
    if not path.is_file():
        return []
    rows: "list[dict]" = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except Exception:  # noqa: BLE001 — a malformed line is skipped, never crashes the prompt build
                pass
    return rows


def compute_governed_agenda_steering_context(*, project_dir, rubric_data, workspace_dir) -> str:
    """The governed 'what to test next' as a directive prompt block, or '' (flag off / no agenda / any error —
    fail-open, exactly like DAG steering). Gated by rubric flag `enable_governed_agenda_steering` (default off)."""
    try:
        if not (rubric_data or {}).get("enable_governed_agenda_steering"):
            return ""
        rows = _load_governed_agenda(Path(workspace_dir))
        frontier = [r for r in rows if r.get("on_frontier")][:4] or rows[:4]
        if not frontier:
            return ""
        lines = []
        for r in frontier:
            src = str(r.get("source") or "governed")
            test = str(r.get("test") or "").strip()[:140]
            bits = r.get("bits")
            yield_tag = f" · info-yield {float(bits):.2f}" if isinstance(bits, (int, float)) else ""
            flip_tag = " · would flip the verdict" if r.get("flips_crisp") else ""
            lines.append(f"  - [{src}] {test}{yield_tag}{flip_tag}  (agenda_id={r.get('id')})")
        return (
            "GOVERNED DECISION AGENDA (deterministic kernel — the highest-value things to resolve next, ranked by "
            "value-of-information over the current governed map; a Pareto frontier, not a single score):\n"
            + "\n".join(lines)
            + "\nPrefer addressing the top item in your next mutation where it applies; if you act on one, note its "
            "agenda_id so the consumption is auditable. These are ADVISORY steering, not commands."
        )
    except Exception:  # noqa: BLE001 — never let steering break the loop
        return ""


def _selftest() -> int:
    import tempfile

    fails: "list[str]" = []

    def ok(name: str, cond: bool) -> None:
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    with tempfile.TemporaryDirectory() as d:
        ws = Path(d)
        # flag off → empty even with an agenda present
        (ws / "governed_agenda.jsonl").write_text(
            json.dumps({"id": "implicit:c", "source": "implicit", "test": "gather evidence on X",
                        "bits": 0.5, "on_frontier": True, "flips_crisp": True}) + "\n",
            encoding="utf-8")
        ok("flag OFF → empty (no regression by default)",
           compute_governed_agenda_steering_context(project_dir=d, rubric_data={}, workspace_dir=ws) == "")
        block = compute_governed_agenda_steering_context(
            project_dir=d, rubric_data={"enable_governed_agenda_steering": True}, workspace_dir=ws)
        ok("flag ON → renders the frontier row", "gather evidence on X" in block and "agenda_id=implicit:c" in block)
        ok("directive not command", "ADVISORY" in block)
        # missing file → fail-open empty
        ok("no agenda file → empty (fail-open)",
           compute_governed_agenda_steering_context(
               project_dir=d, rubric_data={"enable_governed_agenda_steering": True},
               workspace_dir=Path(d) / "nope") == "")

    print("GOVERNED-AGENDA-STEERING SELFTEST", "PASSED" if not fails else f"FAILED {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
