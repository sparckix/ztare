"""Score-evolution trajectory for an autoresearch project — within and across runs, rubric-aware.

This is the single source of truth for the score trajectory so the CLI and the forensic workbench
stay in parity (the workbench shells out to `ztare autoresearch score-trajectory`, it does not
re-implement this logic).

Data sources (read-only):
  * `projects/<p>/workspace/iteration_telemetry.jsonl` — the AUTHORITATIVE per-iteration series; its
    "iteration" rows carry run_id + iteration_index + score (+ raw_judge_score / score_cap_reason /
    cap_kind / champion_promoted / cost). "run_start"/"run_end" rows carry rubric + model labels +
    final score. eval_history.jsonl is a fallback only — it has no run_id, so it cannot segment runs.
  * `projects/<p>/latest_eval_results.json` and `champion_eval_results.json` — the rubric content hash
    (`score_contract.regime.rubric_fingerprint`). Comparing latest vs champion answers the load-bearing
    question: a lower score under a DIFFERENT rubric fingerprint is a tougher bar, not a worse claim.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


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
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _eval_rubric_fingerprint(path: Path) -> str:
    """The rubric content hash recorded in an eval-results file (full-judge path only)."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return ""
    if not isinstance(data, dict):
        return ""
    contract = data.get("score_contract")
    if isinstance(contract, dict):
        regime = contract.get("regime") if isinstance(contract.get("regime"), dict) else {}
        return str(regime.get("rubric_fingerprint") or contract.get("regime_fingerprint") or "")
    return str(data.get("score_regime_fingerprint") or "")


def _num(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def build_score_trajectory(project: str, repo_root: Path) -> dict[str, Any]:
    proot = repo_root / "projects" / project
    telemetry = _read_jsonl(proot / "workspace" / "iteration_telemetry.jsonl")

    runs: dict[str, dict[str, Any]] = {}
    order: list[str] = []

    def _run(run_id: str) -> dict[str, Any]:
        rid = str(run_id)
        if rid not in runs:
            runs[rid] = {
                "run_id": rid,
                "rubric": "",
                "mutator_model": "",
                "judge_model": "",
                "iterations": [],
                "final_score": None,
                "exit_reason": "",
            }
            order.append(rid)
        return runs[rid]

    for row in telemetry:
        kind = row.get("record_type")
        run = _run(row.get("run_id", "0"))
        if kind == "run_start":
            run["rubric"] = row.get("rubric") or run["rubric"]
            run["mutator_model"] = row.get("mutator_model") or run["mutator_model"]
            run["judge_model"] = row.get("judge_model") or run["judge_model"]
        elif kind == "iteration":
            run["iterations"].append(
                {
                    "iteration": row.get("iteration_index"),
                    "score": row.get("score"),
                    "raw_judge_score": row.get("raw_judge_score"),
                    "score_cap_reason": row.get("score_cap_reason"),
                    "cap_kind": row.get("cap_kind"),
                    "score_improved": row.get("score_improved"),
                    "champion_promoted": row.get("champion_promoted"),
                    "estimated_cost_usd": row.get("estimated_cost_usd"),
                }
            )
        elif kind == "run_end":
            if _num(row.get("final_score")):
                run["final_score"] = row.get("final_score")
            run["exit_reason"] = row.get("run_exit_reason") or run["exit_reason"]

    source = "iteration_telemetry"
    # Fallback for older projects with no telemetry: eval_history.jsonl (no run_id → one synthetic run).
    if not any(runs[rid]["iterations"] for rid in runs):
        runs.clear()
        order.clear()
        history = _read_jsonl(proot / "workspace" / "eval_history.jsonl")
        if history:
            source = "eval_history"
            run = _run("0")
            for row in history:
                run["iterations"].append(
                    {
                        "iteration": row.get("iteration"),
                        "score": row.get("score"),
                        "raw_judge_score": row.get("raw_judge_score"),
                        "score_cap_reason": row.get("score_cap_reason"),
                        "cap_kind": None,
                        "score_improved": None,
                        "champion_promoted": None,
                        "estimated_cost_usd": None,
                    }
                )

    run_list: list[dict[str, Any]] = []
    for rid in order:
        run = runs[rid]
        iters = sorted(run["iterations"], key=lambda item: item.get("iteration") if _num(item.get("iteration")) else 0)
        scores = [item["score"] for item in iters if _num(item.get("score"))]
        run_list.append(
            {
                "run_id": run["run_id"],
                "rubric": run["rubric"],
                "mutator_model": run["mutator_model"],
                "judge_model": run["judge_model"],
                "iterations": iters,
                "iteration_count": len(iters),
                "best_score": max(scores) if scores else None,
                "first_score": iters[0]["score"] if iters else None,
                "final_score": run["final_score"] if run["final_score"] is not None else (iters[-1]["score"] if iters else None),
                "exit_reason": run["exit_reason"],
            }
        )

    latest_fp = _eval_rubric_fingerprint(proot / "latest_eval_results.json")
    champion_fp = _eval_rubric_fingerprint(proot / "champion_eval_results.json")
    return {
        "ok": True,
        "schema": "ztare-score-trajectory-v1",
        "project": project,
        "source": source,
        "runs": run_list,
        "run_count": len(run_list),
        "latest_rubric_fingerprint": latest_fp,
        "champion_rubric_fingerprint": champion_fp,
        # The load-bearing signal: different fingerprint ⇒ a score drop may be a tougher rubric.
        "rubric_changed_vs_champion": bool(latest_fp and champion_fp and latest_fp != champion_fp),
    }


def _repo_root() -> Path:
    # src/ztare/reports/score_trajectory.py → repo root is three parents up from this file's parent.
    return Path(__file__).resolve().parents[3]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ztare autoresearch score-trajectory")
    parser.add_argument("--project", required=True, help="Project slug.")
    parser.add_argument("--json", action="store_true", help="Emit JSON (default and only format).")
    args = parser.parse_args(argv)
    if not args.project:
        print("ztare: score-trajectory requires --project <slug>", file=sys.stderr)
        return 2
    payload = build_score_trajectory(args.project, _repo_root())
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
