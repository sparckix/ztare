"""Pure read-only surfacing of a project's run ATTRIBUTION — what rubric/scenario drove it, its score trend,
and any recorded gate outcomes — for the workbench authoring mirror. Reads ONLY existing run artifacts; no LLM
calls, no runs, nothing recomputed. Every field is optional and defensive: a datum absent from the source files
is OMITTED (with a note in `notes`), never fabricated (the provenance ethos).

Sources (verified against real `projects/*` runs before writing this):
  * `champion_eval_results.json` / `latest_eval_results.json` -> `score_contract.rubric_name`, top-level `score`.
    No project anywhere in this repo persists a per-dimension score breakdown here — only the aggregate score.
  * `workspace/eval_history.jsonl` -> one row per (run_id, iteration): `run_id`, `iteration`, `score`,
    `gate_verdicts` ({name: bool} — observed empty in every real run) and `failed_gate_ids` (a list of gate
    names that FAILED; passing gates are never individually named). `workspace/loop_events.jsonl` was also
    inspected but carries topological-pivot events, not gate outcomes, so gates are read from eval_history.
  * `workspace/scenarios/<name>/verdict.md` (rare — a rendered `markdown` Renderer summary) -> the scenario
    name plus a `Verdict:` line. Most projects don't have one (the mainline run never persists the scenario
    name back into the project directory).
  * `synthesis/claim_card.json` (rare, schema `ztare-claim-card-v1`) -> a literal top-level `verdict` field.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional


def _read_json(path: Path) -> "Optional[dict]":
    """Best-effort JSON object read. Missing/malformed/non-object -> None, never a crash."""
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _read_jsonl(path: Path) -> "list[dict]":
    """Best-effort JSONL read, in file order. Missing file or unparsable lines are skipped, never fatal."""
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    rows: "list[dict]" = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


_VERDICT_MD_RE = re.compile(r"^\s*-?\s*\*\*(Verdict|scenario):\*\*\s*(.+?)\s*$", re.MULTILINE)


def _read_scenario_verdict_md(scenarios_dir: Path) -> "dict[str, str]":
    """Best-effort read of `workspace/scenarios/<name>/verdict.md` (see scenarios/providers/markdown_renderer.py
    for the render shape). Absent for most projects; returns {} rather than guessing."""
    if not scenarios_dir.is_dir():
        return {}
    for sub in sorted(p for p in scenarios_dir.iterdir() if p.is_dir()):
        md = sub / "verdict.md"
        if not md.is_file():
            continue
        try:
            text = md.read_text(encoding="utf-8")
        except OSError:
            continue
        fields = dict(_VERDICT_MD_RE.findall(text))
        if fields:
            fields.setdefault("scenario", sub.name)  # the directory name IS the scenario name
            return fields
    return {}


def scenario_attribution(project: str, repo_root) -> "dict[str, Any]":
    """Pure read over `<repo_root>/projects/<project>`'s EXISTING run artifacts. Never raises: an unknown or
    never-run project simply comes back with `has_run=False` and notes explaining every omission."""
    notes: "list[str]" = []
    proj_dir = Path(repo_root) / "projects" / project
    ws = proj_dir / "workspace"

    eval_history = _read_jsonl(ws / "eval_history.jsonl")
    has_run = bool(eval_history)
    if not has_run:
        notes.append("no workspace/eval_history.jsonl (or it is empty) — project has not run")

    champion = _read_json(proj_dir / "champion_eval_results.json")
    latest = _read_json(proj_dir / "latest_eval_results.json")
    eval_for_meta = champion or latest

    # rubric — the literal 'score_contract.rubric_name' every real eval_results.json carries.
    rubric: "Optional[str]" = None
    if eval_for_meta is not None:
        rubric = (eval_for_meta.get("score_contract") or {}).get("rubric_name") or None
    else:
        notes.append("no champion_eval_results.json / latest_eval_results.json — rubric not recoverable")

    # scenario — only a rendered workspace/scenarios/<name>/verdict.md names it; the mainline run never
    # persists the scenario name back into the project dir, and rubric name != scenario name in general.
    verdict_md = _read_scenario_verdict_md(ws / "scenarios")
    scenario = verdict_md.get("scenario")
    if scenario is None:
        notes.append("no workspace/scenarios/<name>/verdict.md — scenario name not recoverable")

    # last_run_id — eval_history.jsonl is append-only chronological; the last row is the most recent run.
    last_run_id = eval_history[-1].get("run_id") if eval_history else None

    # score_latest — latest_eval_results.json's top-level score is the freshest single number; fall back to
    # the last eval_history row if that file is missing.
    score_latest: "Optional[float]" = None
    if latest is not None and "score" in latest:
        score_latest = latest.get("score")
    elif eval_history:
        score_latest = eval_history[-1].get("score")
    else:
        notes.append("no latest_eval_results.json / eval_history rows — score_latest not recoverable")

    # score_baseline — the iteration==0 row's score; falls back to the earliest recorded row if no row is
    # literally tagged iteration 0 (a re-run project can start its history mid-sequence).
    score_baseline: "Optional[float]" = None
    iter0_rows = [r for r in eval_history if r.get("iteration") == 0]
    if iter0_rows:
        score_baseline = iter0_rows[0].get("score")
    elif eval_history:
        score_baseline = eval_history[0].get("score")
        notes.append("no iteration==0 row in eval_history — score_baseline is the earliest recorded row instead")
    else:
        notes.append("no eval_history rows — score_baseline not recoverable")

    # dimensions_scored — no project anywhere in this repo persists a per-dimension score in eval_results.json
    # (only the aggregate 'score'); a rubric's dimension NAMES live in rubrics/<rubric>.json but carry no
    # per-run score, so pairing them would be fabricating the number. Left empty.
    dimensions_scored: "list[dict[str, Any]]" = []
    if eval_for_meta is not None:
        notes.append("no per-dimension score breakdown in eval_results — only an aggregate 'score' is persisted")

    # gates — eval_history's gate_verdicts dict is honored when populated; every real run inspected left it
    # empty and recorded failures only via failed_gate_ids (passing gates are never individually named there).
    gates: "list[dict[str, Any]]" = []
    if eval_history:
        row = eval_history[-1]
        gv = row.get("gate_verdicts") or {}
        if isinstance(gv, dict) and gv:
            gates = [{"name": k, "outcome": "pass" if v else "fail"} for k, v in gv.items()]
        else:
            failed = row.get("failed_gate_ids") or []
            gates = [{"name": g, "outcome": "fail"} for g in failed]
            if not failed:
                notes.append("latest eval_history row has no gate_verdicts/failed_gate_ids — "
                              "no gate outcome is recorded for it")

    # verdict — no qualitative verdict lives in the mainline eval artifacts (only a numeric score).
    # claim_card.json (rare, structured) is preferred over verdict.md (rare, rendered markdown) when both exist.
    claim_card = _read_json(proj_dir / "synthesis" / "claim_card.json")
    verdict: "Optional[str]" = None
    if claim_card is not None and claim_card.get("verdict"):
        verdict = claim_card.get("verdict")
    elif verdict_md.get("Verdict"):
        verdict = verdict_md.get("Verdict")
    else:
        notes.append("no synthesis/claim_card.json or workspace/scenarios/<name>/verdict.md — "
                      "verdict not recoverable")

    # baseline_verdict — no per-iteration qualitative verdict is ever persisted (claim_card / verdict.md are
    # single latest-synthesis artifacts, not per-iteration); only the numeric score_baseline is recoverable.
    baseline_verdict: "Optional[str]" = None
    if has_run:
        notes.append("no per-iteration qualitative verdict artifact exists — baseline_verdict is not "
                      "recoverable (only the numeric score_baseline is)")

    return {
        "has_run": has_run,
        "scenario": scenario,
        "rubric": rubric,
        "last_run_id": last_run_id,
        "dimensions_scored": dimensions_scored,
        "gates": gates,
        "verdict": verdict,
        "baseline_verdict": baseline_verdict,
        "score_latest": score_latest,
        "score_baseline": score_baseline,
        "notes": notes,
    }


def _selftest() -> int:
    from ztare.common.paths import PROJECTS_DIR

    fails: "list[str]" = []

    def ok(name: str, cond: bool) -> None:
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    repo_root = PROJECTS_DIR.parent

    # (a) a nonexistent project never crashes.
    res = scenario_attribution("__definitely_not_a_real_project__", repo_root)
    ok("nonexistent project: has_run is False", res["has_run"] is False)
    ok("nonexistent project: no crash, dict shape intact",
       set(res.keys()) == {"has_run", "scenario", "rubric", "last_run_id", "dimensions_scored", "gates",
                            "verdict", "baseline_verdict", "score_latest", "score_baseline", "notes"})
    ok("nonexistent project: score_latest/baseline are None", res["score_latest"] is None and res["score_baseline"] is None)
    ok("nonexistent project: notes explain the gap", any("eval_history" in n for n in res["notes"]))

    # (b) a real run'd project (checked into this repo's projects/ fixtures) surfaces real data.
    candidate = "ops_root_cause_diagnosis_demo"
    if (PROJECTS_DIR / candidate / "workspace" / "eval_history.jsonl").exists():
        real = scenario_attribution(candidate, repo_root)
        ok(f"'{candidate}': has_run is True", real["has_run"] is True)
        ok(f"'{candidate}': rubric recovered", real["rubric"] == "ops_root_cause_diagnosis_demo")
        ok(f"'{candidate}': last_run_id recovered", real["last_run_id"] is not None)
        ok(f"'{candidate}': score_latest recovered", isinstance(real["score_latest"], (int, float)))
        ok(f"'{candidate}': score_baseline recovered", isinstance(real["score_baseline"], (int, float)))
        print("  attribution:", json.dumps(real, indent=2))
    else:
        print(f"  [SKIP] '{candidate}' not present in this checkout — (b) not exercised")

    print("ATTRIBUTION SELFTEST", "PASSED" if not fails else f"FAILED {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
