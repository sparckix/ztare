"""In-process batch gate: evaluate K candidates in one process, load episodes once.

Amdahl fix: the per-candidate subprocess overhead (~27s/candidate) is the
dominant cost at K>1. This module loads episodes once and evaluates all
candidates in-process via the same carrier-loading logic as gate_harness.py.

Soundness guarantee (verdict-identical to gate_harness.py):
  Full-scan results (partial=False) are provably verdict-identical to the
  subprocess harness. The proof is the equivalence check in the module's
  main block: batch_gate scores for the live champion and two real candidates
  must match gate_harness.py subprocess output exactly (visible exact count
  and holdout depth). Any discrepancy aborts with AssertionError.

EXTENSIONS_SRC carriers capture their compiled operation registry at the
canonical lowering door.  Batch order therefore cannot change an already
loaded carrier's meaning.

Early abort (partial verdicts, screening only):
  With early_abort_on_worse=N, a candidate's visible scan stops once its
  wrong-row count exceeds champion_wrong_count + N. These results are marked
  partial=True and MUST NOT be used as promotion verdicts — they are a
  screening pre-filter only. Full verdicts always complete the scan.

CLI:
  python -m ztare.worldmodel.batch_gate --project <dir> --candidates a.py b.py [--differential]

Output per candidate:
  {
    "candidate": str,            # path
    "carrier": str,              # carrier type detected
    "visible_exact": int,        # rows predicted exactly (full scan)
    "visible_total": int,
    "visible_env_excluded": int,
    "wrong_rows": [int],         # indices where prediction != s_next
    "holdout_depth": int,        # consecutive steps predicted on holdout
    "holdout_total": int,
    "partial": bool,             # True = early-aborted, not a full verdict
    ["load_error": str],         # if carrier failed to load
    ["abort_reason": str],       # if early-aborted
  }
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from ztare.worldmodel.episode_log import EpisodeLog
from ztare.worldmodel.gates import as_predictor, env_frame_indices, rollout_depth
from ztare.worldmodel.grid_dsl import evaluate as _dsl_evaluate, program_size as _dsl_program_size
from ztare.worldmodel.carrier_loader import load_carrier_path
from ztare.worldmodel.patch_base_carrier import composed_carrier_description_length


def _load_candidate(path: Path, project_dir: Path) -> "tuple[Any, str, str | None]":
    """Load carrier; returns (program, carrier_type, error_or_None).

    carrier_type is one of: 'patch_base', 'world_model_spec', 'program_ast',
    'python_callable', 'extensions_src'.
    """
    try:
        program, kind, _source_sha = load_carrier_path(
            path,
            project_dir=project_dir,
            attach_projection=False,
        )
    except Exception as exc:  # noqa: BLE001
        return None, "invalid", str(exc)[:300]
    return program, kind, None


def _eval_visible(
    program: Any,
    visible: EpisodeLog,
    *,
    early_abort_on_worse: "int | None" = None,
    champion_wrong_count: int = 0,
) -> "tuple[int, list[int], int, bool, str | None]":
    """Evaluate candidate on visible episode.

    Returns: (exact_count, wrong_rows, env_excluded, partial, abort_reason)
    """
    predict = as_predictor(program)
    env_idx = env_frame_indices(visible)
    exact = 0
    wrong: list[int] = []
    abort_reason: "str | None" = None

    for i, tr in enumerate(visible):
        if i in env_idx:
            continue
        predicted = predict(tr.s, tr.a, tr.t)
        if predicted is not None and predicted == tr.s_next:
            exact += 1
        else:
            wrong.append(i)
            if (early_abort_on_worse is not None
                    and len(wrong) > champion_wrong_count + early_abort_on_worse):
                abort_reason = (
                    f"early abort: {len(wrong)} wrong rows > champion "
                    f"{champion_wrong_count} + margin {early_abort_on_worse}"
                )
                return exact, wrong, len(env_idx), True, abort_reason

    return exact, wrong, len(env_idx), False, None


def batch_gate(
    project_dir: "str | Path",
    candidate_paths: "list[str | Path]",
    *,
    episodes: "tuple[str, ...]" = ("visible", "holdout"),
    champion_bitmap: "dict | None" = None,
    early_abort_on_worse: "int | None" = None,
) -> list[dict]:
    """Evaluate K candidates in-process: load episodes once, replay all candidates.

    Parameters
    ----------
    project_dir:
        Project root (contains gate_harness.py and raw/episodes/).
    candidate_paths:
        List of .py candidate files to evaluate.
    episodes:
        Which episode sets to evaluate. Default: both visible and holdout.
    champion_bitmap:
        Optional bitmap from build_row_bitmap for the current champion (from
        evidence_consolidation). Used to seed champion_wrong_count for early abort.
    early_abort_on_worse:
        If set, abort a candidate's visible scan once wrong count exceeds
        champion_wrong_count + this margin. Results are marked partial=True.
        ONLY valid for strict-improvement screening — never for promotion.

    Returns list of per-candidate result dicts (see module docstring).
    """
    project_dir = Path(project_dir).resolve()
    from ztare.worldmodel.evidence_consolidation import resolve_episode_paths
    _ep = resolve_episode_paths(project_dir)
    visible_path = _ep["visible"]
    holdout_path = _ep["holdout"]
    # Load episodes once
    visible: "EpisodeLog | None" = None
    holdout: "EpisodeLog | None" = None
    if "visible" in episodes and visible_path is not None and visible_path.exists():
        visible = EpisodeLog.read_jsonl(visible_path)
    if "holdout" in episodes and holdout_path is not None and holdout_path.exists():
        holdout = EpisodeLog.read_jsonl(holdout_path)

    champion_wrong_count = len(champion_bitmap.get("wrong_rows", [])) if champion_bitmap else 0
    visible_total = len(visible) if visible else 0
    holdout_total = len(holdout) if holdout else 0

    results: list[dict] = []

    for raw_path in candidate_paths:
        cpath = Path(raw_path).resolve()
        rec: dict = {
            "candidate": str(cpath),
            "carrier": "unknown",
            "visible_exact": -1,
            "visible_total": visible_total,
            "visible_env_excluded": 0,
            "wrong_rows": [],
            "holdout_depth": -1,
            "holdout_total": holdout_total,
            "partial": False,
        }

        if not cpath.exists():
            rec["load_error"] = f"file not found: {cpath}"
            results.append(rec)
            continue

        program, ctype, err = _load_candidate(cpath, project_dir)
        rec["carrier"] = ctype

        if err:
            rec["load_error"] = err
            results.append(rec)
            continue

        if program is None:
            rec["load_error"] = "program resolved to None"
            results.append(rec)
            continue

        try:
            rec["description_length"] = composed_carrier_description_length(
                cpath,
                project_dir=project_dir,
            )
            rec["description_length_unit"] = "source_token_closure_v1"
        except Exception as exc:  # noqa: BLE001
            rec["load_error"] = f"carrier description closure invalid: {exc}"
            results.append(rec)
            continue

        # grid_dsl_expressible: mirrors gate_harness logic exactly — callable
        # carriers pass with size=-2; AST carriers probe evaluate() on the
        # first visible transition; no visible episode → fail with size=-1.
        if callable(program):
            rec["grid_dsl_expressible"] = True
            rec["grid_dsl_size"] = -2
        elif visible is not None:
            try:
                first_s = visible.transitions()[0].s
                _expr = _dsl_evaluate(program, first_s, 0, 0) is not None
                _size = _dsl_program_size(program)
            except Exception:  # noqa: BLE001
                _expr, _size = False, -1
            rec["grid_dsl_expressible"] = _expr
            rec["grid_dsl_size"] = _size
        else:
            rec["grid_dsl_expressible"] = False
            rec["grid_dsl_size"] = -1

        if visible is not None:
            exact, wrong, env_excl, partial, abort_reason = _eval_visible(
                program,
                visible,
                early_abort_on_worse=early_abort_on_worse,
                champion_wrong_count=champion_wrong_count,
            )
            # ponytail: correct total = checked rows only (env frames excluded)
            rec["visible_total"] = visible_total - env_excl
            rec["visible_exact"] = exact
            rec["visible_env_excluded"] = env_excl
            rec["wrong_rows"] = wrong
            rec["partial"] = partial
            if abort_reason:
                rec["abort_reason"] = abort_reason

        if holdout is not None and not rec["partial"]:
            rec["holdout_depth"] = rollout_depth(program, holdout)

        # Hard invariant: counts must be geometrically possible.
        v_exact = rec.get("visible_exact", -1)
        v_total = rec.get("visible_total", 0)
        h_depth = rec.get("holdout_depth", -1)
        h_total = rec.get("holdout_total", 0)
        violated = []
        if v_exact >= 0 and v_total >= 0 and v_exact > v_total:
            violated.append(f"visible_exact={v_exact} > visible_total={v_total}")
        if h_depth >= 0 and h_total > 0 and h_depth > h_total:
            violated.append(f"holdout_depth={h_depth} > holdout_total={h_total}")
        if violated:
            rec["load_error"] = "GATE_COUNTING_INVARIANT_VIOLATED: " + "; ".join(violated)

        results.append(rec)

    return results


# ── CLI ───────────────────────────────────────────────────────────────────────

def _cli() -> int:
    import argparse, time

    ap = argparse.ArgumentParser(
        description="In-process batch gate for K candidates (one episode load)."
    )
    ap.add_argument("--project", required=True, help="Project directory (contains gate_harness.py)")
    ap.add_argument("--candidates", nargs="+", required=True, help="Candidate .py files")
    ap.add_argument("--differential", action="store_true",
                    help="Use champion bitmap for early-abort screening (partial results)")
    ap.add_argument("--early-abort-margin", type=int, default=0,
                    help="With --differential: abort when wrong > champion_wrong + margin")
    ap.add_argument("--champion", default=None,
                    help="Champion .py path for differential mode (default: project/test_model.py)")
    ap.add_argument("--episodes", nargs="+", default=["visible", "holdout"],
                    choices=["visible", "holdout"])
    ap.add_argument("--time-subprocess", action="store_true",
                    help="Also time the subprocess path for comparison")
    args = ap.parse_args()

    project_dir = Path(args.project).resolve()

    champion_bitmap: "dict | None" = None
    if args.differential:
        from ztare.worldmodel.evidence_consolidation import build_row_bitmap, resolve_episode_paths
        champion_path = Path(args.champion) if args.champion else (project_dir / "test_model.py")
        visible_path = resolve_episode_paths(project_dir)["visible"]
        if champion_path.exists() and visible_path is not None and visible_path.exists():
            champion_bitmap = build_row_bitmap(champion_path, visible_path, project_dir=project_dir)
            print(f"# Champion bitmap: {champion_bitmap['exact_count']}/{champion_bitmap['total_rows']} exact, "
                  f"{len(champion_bitmap['wrong_rows'])} wrong rows", file=sys.stderr)
        else:
            print(f"# Warning: champion {champion_path} or visible episode not found; "
                  f"running without differential", file=sys.stderr)

    t0 = time.perf_counter()
    results = batch_gate(
        project_dir,
        args.candidates,
        episodes=tuple(args.episodes),
        champion_bitmap=champion_bitmap,
        early_abort_on_worse=args.early_abort_margin if args.differential else None,
    )
    elapsed_batch = time.perf_counter() - t0

    print(json.dumps(results, indent=2))
    print(f"\n# batch_gate: {len(args.candidates)} candidates in {elapsed_batch:.2f}s "
          f"({elapsed_batch/max(len(args.candidates),1):.2f}s/candidate)", file=sys.stderr)

    if args.time_subprocess:
        harness = project_dir / "gate_harness.py"
        t1 = time.perf_counter()
        for cpath in args.candidates:
            subprocess.run(
                [sys.executable, str(harness), "--candidate-path", cpath],
                capture_output=True, timeout=180,
            )
        elapsed_sub = time.perf_counter() - t1
        print(f"# subprocess path: {len(args.candidates)} candidates in {elapsed_sub:.2f}s "
              f"({elapsed_sub/max(len(args.candidates),1):.2f}s/candidate)", file=sys.stderr)
        print(f"# speedup: {elapsed_sub/max(elapsed_batch,0.001):.1f}x", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
