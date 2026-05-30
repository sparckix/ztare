"""I-5 Mode B experiment scaffold.

Spec: research_areas/private/seams/engine/GP-214_pattern_bank_kernel_injection_seam.md §B

Goal: determine whether auto-injecting catastrophic_fit_failure exemplars on
the next iteration after the runtime classifier detects this class moves the
apparent failure rate of that class.

This script does NOT execute the 600-iteration compute run. It:

  1. Reads the trajectory archive
  2. Selects projects with at least one iteration whose weakest_point
     classifies as catastrophic_fit_failure (per the runtime classifier
     extension shipped today)
  3. Splits the candidates into A/B groups (random seed fixed for repro)
  4. Emits a run-plan markdown into analytics/public/queries/ that lists, for
     each candidate substrate, the exact CLI command an operator would run
     to reproduce the trial — with the rubric.inject_pattern_bank flag
     either off (control) or set to auto_catastrophic_fit (treatment).
  5. The actual launch is operator-triggered.

Run:
    python scripts/public/audits/run_i5_mode_b_experiment.py [--n-per-arm 10] [--seed 0]
"""

from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ARCHIVE = REPO_ROOT / "analytics" / "trajectory_archive_enriched.jsonl"
DEFAULT_OUT = REPO_ROOT / "analytics" / "queries"


def load_archive(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    return rows


def find_candidate_projects(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Find projects with >=1 iteration whose weakest_point classifies as
    catastrophic_fit_failure under the current runtime classifier."""
    import sys

    sys.path.insert(0, str(REPO_ROOT / "src"))
    from ztare.validator.weakest_link_classifier import classify_weakest_point  # type: ignore

    by_project: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        proj = r.get("project")
        if not proj:
            continue
        by_project.setdefault(proj, []).append(r)

    candidates: list[dict[str, Any]] = []
    for proj, rs in by_project.items():
        cf_hits = []
        for r in rs:
            wp = r.get("weakest_point") or ""
            if not wp:
                continue
            cls = classify_weakest_point(wp)
            if cls == "catastrophic_fit_failure":
                cf_hits.append({
                    "iteration_index": r.get("iteration_index"),
                    "iter_timestamp": r.get("iter_timestamp"),
                    "score": r.get("score"),
                })
        if cf_hits:
            candidates.append({
                "project": proj,
                "n_total_iters": len(rs),
                "n_catastrophic_fit_failure_hits": len(cf_hits),
                "hits": cf_hits[:5],  # cap detail for readability
            })
    candidates.sort(key=lambda c: -c["n_catastrophic_fit_failure_hits"])
    return candidates


def build_plan(candidates: list[dict[str, Any]], n_per_arm: int, seed: int) -> dict[str, Any]:
    rng = random.Random(seed)
    selected = candidates[: 2 * n_per_arm]
    if len(selected) < 2:
        return {
            "warning": (
                f"Found only {len(selected)} candidate projects with catastrophic_fit_failure "
                "hits in the archive. The Mode B experiment is under-powered at this scale; "
                "consider broadening the classifier patterns or running on a per-iteration "
                "(not per-project) basis."
            ),
            "candidates": candidates,
            "control": [],
            "treatment": [],
        }
    rng.shuffle(selected)
    half = len(selected) // 2
    control = selected[:half]
    treatment = selected[half:]
    return {
        "n_selected": len(selected),
        "n_control": len(control),
        "n_treatment": len(treatment),
        "candidates_total": len(candidates),
        "control": control,
        "treatment": treatment,
    }


CONTROL_RUBRIC_OVERRIDE = {
    "inject_pattern_bank": False,
}

TREATMENT_RUBRIC_OVERRIDE = {
    "inject_pattern_bank": {"mode": "auto_catastrophic_fit"},
}


def render_markdown(plan: dict[str, Any], n_iters_per_run: int, timestamp: str) -> str:
    lines: list[str] = []
    lines.append(f"# I-5 Mode B experiment plan — {timestamp}")
    lines.append("")
    lines.append(
        "_Per `GP-214_pattern_bank_kernel_injection_seam.md` §B. Purpose: settle whether "
        "auto-injecting `catastrophic_fit_failure` pattern-bank exemplars moves the apparent "
        "failure rate of that class on the very next iteration._"
    )
    lines.append("")
    if "warning" in plan:
        lines.append("## ⚠ Under-powered experiment")
        lines.append("")
        lines.append(plan["warning"])
        lines.append("")
        lines.append("### Available candidates")
        lines.append("")
        for c in plan["candidates"]:
            lines.append(f"- `{c['project']}` — {c['n_catastrophic_fit_failure_hits']} CF hit(s) in {c['n_total_iters']} iter(s)")
        return "\n".join(lines)

    lines.append(f"**Total candidates with CF hits:** {plan['candidates_total']}")
    lines.append(f"**Selected:** {plan['n_selected']} (control {plan['n_control']} + treatment {plan['n_treatment']})")
    lines.append(f"**Iterations per run:** {n_iters_per_run}")
    lines.append("")

    lines.append("## Control arm — `inject_pattern_bank: false`")
    lines.append("")
    lines.append("```bash")
    for c in plan["control"]:
        lines.append(
            f"# {c['project']}: {c['n_catastrophic_fit_failure_hits']} CF hit(s) in archive"
        )
        lines.append(
            f"python -m ztare.validator.autoresearch_loop --project {c['project']} \\"
        )
        lines.append(f"    --rubric_override '{json.dumps(CONTROL_RUBRIC_OVERRIDE)}' \\")
        lines.append(f"    --max_iters {n_iters_per_run}")
        lines.append("")
    lines.append("```")
    lines.append("")

    lines.append("## Treatment arm — `inject_pattern_bank: { mode: auto_catastrophic_fit }`")
    lines.append("")
    lines.append("```bash")
    for c in plan["treatment"]:
        lines.append(
            f"# {c['project']}: {c['n_catastrophic_fit_failure_hits']} CF hit(s) in archive"
        )
        lines.append(
            f"python -m ztare.validator.autoresearch_loop --project {c['project']} \\"
        )
        lines.append(
            f"    --rubric_override '{json.dumps(TREATMENT_RUBRIC_OVERRIDE)}' \\"
        )
        lines.append(f"    --max_iters {n_iters_per_run}")
        lines.append("")
    lines.append("```")
    lines.append("")

    lines.append("## Analysis after both arms complete")
    lines.append("")
    lines.append("For each project in each arm, count: `n_iters_after_first_CF_hit_with_CF` divided by `n_iters_after_first_CF_hit`. Compare arm means with a paired t-test (matched on prior CF-hit count). Pass criterion: treatment reduces re-fire rate by ≥ 25% relative, p < 0.05.")
    lines.append("")
    lines.append("If treatment fails the criterion, all auto-routing modes of I-5 are buried for v0; only manual mode survives.")
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- The runtime classifier was extended on 2026-05-04 with patterns matching the May 4 LLM-classifier exemplars (`Fit_Quality_Visible: ...`, `matches zero of`, `output is universally incorrect`, etc.). See `src/ztare/validator/weakest_link_classifier.py`.")
    lines.append("- The override log at `analytics/public/operator_overrides.jsonl` records every I-5 injection event; the post-run analysis should match log entries to project iterations to attribute treatment effect cleanly.")
    lines.append("- The `catastrophic_fit_failure` class had cross-LLM stability 0.538 in the GP-149 §10 audit — the highest among all 15 mining classes but still below the 0.60 GP-151 threshold. Mode B is therefore *amber* not green; this experiment is the deciding test.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="run_i5_mode_b_experiment")
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--n-per-arm", type=int, default=10)
    parser.add_argument("--n-iters-per-run", type=int, default=30)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)

    rows = load_archive(args.archive)
    candidates = find_candidate_projects(rows)
    plan = build_plan(candidates, n_per_arm=args.n_per_arm, seed=args.seed)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    args.out.mkdir(parents=True, exist_ok=True)

    json_path = args.out / f"i5_mode_b_experiment_plan_{timestamp}.json"
    json_path.write_text(json.dumps({
        "generated": timestamp,
        "n_per_arm": args.n_per_arm,
        "n_iters_per_run": args.n_iters_per_run,
        "seed": args.seed,
        "plan": plan,
    }, indent=2))

    md_path = args.out / f"i5_mode_b_experiment_plan_{timestamp}.md"
    md_path.write_text(render_markdown(plan, args.n_iters_per_run, timestamp))

    print(f"wrote {json_path}")
    print(f"wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
