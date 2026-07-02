"""Compression-progress ("worth another pass?") verdict for an autoresearch project.

Single source of truth so the CLI and the forensic workbench stay in parity — the workbench shells out to
`ztare autoresearch compression-progress`, it does NOT re-implement this. Advisory only; it does not steer
the loop (the loop acts on information yield) and it is NOT the judge score (which this project treats as
gameable).

The signal is Herrmann-Schmidhuber compression progress: a lower-is-better complexity proxy that should DROP
as the program genuinely tightens its explanation. When it keeps dropping, another pass is likely productive;
when it has been flat for several iterations, you're into diminishing returns.

Complexity proxy = a two-part MDL of the champion probability DAG (see `compression_progress.dag_description_length`):
structure bits + the outcome's surprisal. Universal — every project has a probability DAG.

Data sources (read-only, in priority order):
  * live: `workspace/iteration_telemetry.jsonl` rows carry `compression_progress.complexity` (new runs).
  * ex-post: `history/*_dag.json` per-iteration DAG snapshots — so EXISTING runs (logged before the live
    proxy shipped) still get the verdict, computed retroactively from the same two-part MDL.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from ztare.validator.core.compression_progress import (
    CompressionObservation,
    dag_description_length,
    evaluate_compression_progress,
    observations_from_rows,
)

# recommendation → the human "worth another pass?" verdict the ICP actually faces.
_VERDICT = {
    "continue": ("Worth another pass", "ok",
                 "The last iteration still made the explanation simpler — the search is compressing."),
    "watch": ("Maybe — watch it", "neutral",
              "No improvement in the last iteration, but not yet a flat stretch."),
    "measure_before_continuing": ("Measure first", "warn",
                                  "Recent moves were different but didn't simplify anything — check the novelty is real before spending another pass."),
    "narrow_or_pivot": ("Diminishing returns", "warn",
                        "Several iterations with no simpler explanation — narrow the question or change approach rather than repeat."),
    "no_signal": ("Not enough history yet", "muted",
                  "Needs at least two iterations with a usable complexity reading."),
}

_HOW = ("Complexity is a two-part MDL of the champion probability DAG — the bits to describe its structure "
        "plus the surprisal of its conclusion; it drops when added structure buys enough explanatory power to "
        "pay for itself. “Compression progress” is that number falling. We count iterations since the "
        "last fall: a few flat ones mean diminishing returns. Advisory, computed from run history — not the "
        "judge score (which this tool treats as gameable).")

_ITER_RE = re.compile(r"_iter(\d+)_")


def dag_observations_from_history(history_dir: Path) -> list[CompressionObservation]:
    """Ex-post: one observation per `history/*_dag.json`, in chronological (filename-timestamp) order, with
    complexity = the DAG's two-part MDL. Index is a running chronological counter so stagnation = iterations
    since the last compression drop. Shared with the workbench so the CLI verdict and the History card compute
    the same series (one kernel path, no re-implementation)."""
    files = sorted(history_dir.glob("*_dag.json"), key=lambda p: p.name)
    obs: list[CompressionObservation] = []
    for i, path in enumerate(files):
        try:
            dag = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        dl = dag_description_length(dag) if isinstance(dag, dict) else None
        if dl is None:
            continue
        m = _ITER_RE.search(path.name)
        obs.append(CompressionObservation(
            iteration_index=len(obs),
            complexity=dl,
            family="dag_mdl",
            label=f"iter{m.group(1)}" if m else path.name,
        ))
    return obs


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if isinstance(obj, dict) and obj.get("record_type") == "iteration":
            rows.append(obj)
    return rows


def build_compression_progress(project: str, repo_root: Path) -> dict[str, Any]:
    proot = repo_root / "projects" / project
    live = observations_from_rows(_read_jsonl(proot / "workspace" / "iteration_telemetry.jsonl"))
    live_usable = [o for o in live if o.complexity is not None]
    source = "iteration_telemetry"
    observations = live
    if len(live_usable) < 2:                       # existing runs: fall back to per-iteration DAG snapshots
        expost = dag_observations_from_history(proot / "history")
        if len(expost) >= 2:
            observations, source = expost, "history_dag_expost"

    decision = evaluate_compression_progress(observations)
    headline, tone, detail = _VERDICT.get(decision.recommendation, _VERDICT["no_signal"])
    return {
        "ok": True,
        "schema": "ztare-compression-progress-v1",
        "project": project,
        "source": source,
        "verdict": {
            "headline": headline,
            "tone": tone,
            "detail": detail,
            "how_computed": _HOW,
        },
        "recommendation": decision.recommendation,
        "usable_observations": decision.usable_observations,
        "family": decision.family,
        "best_complexity": decision.best_complexity,
        "latest_complexity": decision.latest_complexity,
        "stagnation_length": decision.stagnation_length,
        "compression_drop_count": decision.compression_drop_count,
        "rationale": decision.rationale,
    }


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ztare autoresearch compression-progress")
    parser.add_argument("--project", required=True, help="Project slug.")
    parser.add_argument("--json", action="store_true", help="Emit JSON (default and only format).")
    args = parser.parse_args(argv)
    if not args.project:
        print("ztare: compression-progress requires --project <slug>", file=sys.stderr)
        return 2
    print(json.dumps(build_compression_progress(args.project, _repo_root()), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
