"""BRIDGE-2 — Substrate-retirement detector.

Spec: research_areas/private/specs/active/engine/GP-213_BRIDGE2_retirement_detector_spec.md

Pure-deterministic decision rule. No LLM calls. Reads the trajectory archive
and the experiment track record; writes recommendations into
ztare_workspace/inbox/retirement_candidates/.

Operator-confirmed only in v0. Never auto-retires.
"""

from __future__ import annotations

import argparse
import json
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ARCHIVE = REPO_ROOT / "analytics" / "trajectory_archive_enriched.jsonl"
DEFAULT_TRACK_RECORD = REPO_ROOT / "research_areas" / "EXPERIMENT_TRACK_RECORD.md"
DEFAULT_INBOX = REPO_ROOT / "ztare_workspace" / "inbox" / "retirement_candidates"

DEFAULT_STAGNATION_THRESHOLD = 5
DEFAULT_VARIANCE_THRESHOLD = 5.0
DEFAULT_COST_MULTIPLIER = 2.0
ACTIVE_WINDOW_DAYS = 30
COLD_START_MIN_ITERS = 10
PIVOT_LOOKBACK_DAYS = 30

PLATEAU_FRIENDLY_CLASSES = frozenset(
    {"tail_generalization", "exhaustiveness_proof", "exhaustiveness_claim"}
)


@dataclass
class ProjectMetrics:
    project: str
    iter_count: int
    last_iter_ts: int
    stagnation_count: int
    last_5_score_variance: float
    cost_per_finding_30d: float
    iters_in_30d: int
    promotions_in_30d: int
    pivots_in_30d: int
    paper_critical: bool
    substrate_class: str | None
    last_5_scores: list[float] = field(default_factory=list)


@dataclass
class Decision:
    project: str
    recommend_retirement: bool
    rule_firings: dict[str, bool]
    plateau_guards: list[str]
    rationale: str
    metrics: ProjectMetrics


def load_archive(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def project_paper_critical_set(track_record_path: Path) -> set[str]:
    """A project is paper_critical if it has any F-row in the track record.

    F-rows mark confirmed findings; we never auto-recommend retirement on
    substrates that have produced one.
    """
    if not track_record_path.exists():
        return set()
    text = track_record_path.read_text()
    out: set[str] = set()
    for line in text.splitlines():
        if "| F-" in line and "GP" in line:
            for tok in line.split():
                tok = tok.strip("`,|")
                if tok and tok[0].isalpha() and tok.startswith(("gp", "GP", "ns_", "ztare_")):
                    out.add(tok)
                if tok.startswith("F-GP"):
                    parts = tok.split("-")
                    for p in parts:
                        if p.startswith(("gp", "GP", "ns")):
                            out.add(p.lower())
    return out


def compute_metrics(
    rows: Iterable[dict[str, Any]],
    paper_critical: set[str],
    now_ts: int,
) -> dict[str, ProjectMetrics]:
    by_project: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        proj = r.get("project")
        if not proj:
            continue
        by_project.setdefault(proj, []).append(r)

    cutoff_30d = now_ts - ACTIVE_WINDOW_DAYS * 86400

    metrics: dict[str, ProjectMetrics] = {}
    for proj, rs in by_project.items():
        rs_sorted = sorted(
            rs,
            key=lambda r: (
                r.get("iter_timestamp") or 0,
                r.get("iteration_index") if r.get("iteration_index") is not None else -1,
            ),
        )
        last = rs_sorted[-1]
        last_5 = rs_sorted[-5:] if len(rs_sorted) >= 5 else rs_sorted
        scores = [float(r["score"]) for r in last_5 if r.get("score") is not None]
        var = statistics.pvariance(scores) if len(scores) >= 2 else 0.0

        rs_30d = [r for r in rs_sorted if (r.get("iter_timestamp") or 0) >= cutoff_30d]
        iters_30d = len(rs_30d)
        promotions_30d = sum(1 for r in rs_30d if r.get("champion_promoted"))
        cost_per_finding = (
            float(iters_30d) / float(promotions_30d) if promotions_30d > 0 else float("inf")
        )

        # Pivot proxy: a champion_promoted=True following a stagnation_count > 0.
        pivots_30d = 0
        for prev, curr in zip(rs_sorted, rs_sorted[1:]):
            if (curr.get("iter_timestamp") or 0) < cutoff_30d:
                continue
            if curr.get("champion_promoted") and (prev.get("stagnation_count") or 0) > 0:
                pivots_30d += 1

        substrate_class = (last.get("substrate_class") if isinstance(last, dict) else None) or None

        metrics[proj] = ProjectMetrics(
            project=proj,
            iter_count=len(rs_sorted),
            last_iter_ts=int(last.get("iter_timestamp") or 0),
            stagnation_count=int(last.get("stagnation_count") or 0),
            last_5_score_variance=float(var),
            cost_per_finding_30d=cost_per_finding,
            iters_in_30d=iters_30d,
            promotions_in_30d=promotions_30d,
            pivots_in_30d=pivots_30d,
            paper_critical=proj in paper_critical,
            substrate_class=substrate_class,
            last_5_scores=scores,
        )
    return metrics


def median_all_time_cost(metrics: dict[str, ProjectMetrics]) -> float:
    finite = [m.cost_per_finding_30d for m in metrics.values() if m.cost_per_finding_30d != float("inf")]
    if not finite:
        return float("nan")
    return statistics.median(finite)


def evaluate(
    metrics: ProjectMetrics,
    median_cost: float,
    stagnation_threshold: int,
    variance_threshold: float,
    cost_multiplier: float,
    no_plateau_guard: bool = False,
) -> Decision:
    plateau_guards: list[str] = []
    if metrics.iter_count < COLD_START_MIN_ITERS:
        return Decision(
            project=metrics.project,
            recommend_retirement=False,
            rule_firings={"cold_start_exclusion": True},
            plateau_guards=["cold_start_under_10_iters"],
            rationale=f"only {metrics.iter_count} iterations recorded; needs at least {COLD_START_MIN_ITERS}",
            metrics=metrics,
        )
    if metrics.paper_critical:
        return Decision(
            project=metrics.project,
            recommend_retirement=False,
            rule_firings={"paper_critical_block": True},
            plateau_guards=["paper_critical"],
            rationale="project has at least one F-row in EXPERIMENT_TRACK_RECORD.md; never auto-recommend retirement",
            metrics=metrics,
        )

    rule_stagnation = metrics.stagnation_count >= stagnation_threshold
    rule_variance = metrics.last_5_score_variance < variance_threshold
    rule_cost = (
        median_cost == median_cost  # not NaN
        and metrics.cost_per_finding_30d > median_cost * cost_multiplier
    )
    rule_firings = {
        f"stagnation>={stagnation_threshold}": rule_stagnation,
        f"last_5_variance<{variance_threshold}": rule_variance,
        f"cost_per_finding_30d>{cost_multiplier}*median({median_cost:.2f})": rule_cost,
    }

    if not no_plateau_guard:
        if metrics.pivots_in_30d >= 1:
            plateau_guards.append(f"pivots_in_30d={metrics.pivots_in_30d}")
        if metrics.substrate_class and metrics.substrate_class in PLATEAU_FRIENDLY_CLASSES:
            plateau_guards.append(f"substrate_class={metrics.substrate_class}")

    all_rules_fire = rule_stagnation and rule_variance and rule_cost
    recommend = all_rules_fire and not plateau_guards

    if recommend:
        rationale = (
            f"stagnation_count={metrics.stagnation_count}, "
            f"last_5_score_variance={metrics.last_5_score_variance:.2f}, "
            f"cost_per_finding_30d={metrics.cost_per_finding_30d:.2f} (median {median_cost:.2f}); "
            "all three rules fire and no plateau guard triggered"
        )
    elif all_rules_fire and plateau_guards:
        rationale = (
            f"all three rules fire but plateau guards triggered: {', '.join(plateau_guards)}; "
            "do not retire — revisit in 7 days"
        )
    else:
        unfired = [k for k, v in rule_firings.items() if not v]
        rationale = f"rules unfired: {unfired}"

    return Decision(
        project=metrics.project,
        recommend_retirement=recommend,
        rule_firings=rule_firings,
        plateau_guards=plateau_guards,
        rationale=rationale,
        metrics=metrics,
    )


def render_markdown(
    decisions: list[Decision],
    median_cost: float,
    archive_path: Path,
    timestamp: str,
    rule_version: str = "v0",
) -> str:
    retire = [d for d in decisions if d.recommend_retirement]
    plateau = [d for d in decisions if not d.recommend_retirement and d.plateau_guards and "paper_critical" not in d.plateau_guards and "cold_start_under_10_iters" not in d.plateau_guards]

    lines: list[str] = []
    lines.append(f"# Retirement candidates — {timestamp}")
    lines.append("")
    lines.append(f"_Decision rule: {rule_version} (per GP-213 §3.2 + GP-149 §2.2)._")
    lines.append(f"_All-time median cost-per-finding (last 30d windows): `{median_cost:.2f}` iter/promotion._")
    lines.append("")

    lines.append("## Recommended for retirement")
    lines.append("")
    if not retire:
        lines.append("_None._")
        lines.append("")
    for d in retire:
        m = d.metrics
        lines.append(f"### `{d.project}`")
        lines.append("")
        lines.append(f"- iterations recorded: {m.iter_count}")
        lines.append(f"- stagnation_count (latest iter): {m.stagnation_count}")
        lines.append(f"- last-5-iter score variance: {m.last_5_score_variance:.2f}")
        lines.append(f"- cost per finding (last 30d): `{m.cost_per_finding_30d:.2f}` iter/promotion")
        lines.append(f"- iters in last 30d: {m.iters_in_30d}; promotions: {m.promotions_in_30d}; pivots: {m.pivots_in_30d}")
        lines.append("- plateau guards triggered: NONE")
        lines.append(f"- **Recommendation:** retire.")
        lines.append(f"- **Rationale:** {d.rationale}")
        lines.append("")

    lines.append("## Flagged but plateau-guarded — do NOT retire")
    lines.append("")
    if not plateau:
        lines.append("_None._")
        lines.append("")
    for d in plateau:
        m = d.metrics
        lines.append(f"### `{d.project}`")
        lines.append("")
        lines.append(f"- stagnation_count: {m.stagnation_count}; variance: {m.last_5_score_variance:.2f}; cost: `{m.cost_per_finding_30d:.2f}`")
        lines.append(f"- plateau guards: {', '.join(d.plateau_guards)}")
        lines.append(f"- **Recommendation:** keep running; revisit in 7 days.")
        lines.append("")

    not_flagged = sum(1 for d in decisions if not d.recommend_retirement and not d.plateau_guards)
    paper_crit = sum(1 for d in decisions if "paper_critical" in d.plateau_guards)
    cold = sum(1 for d in decisions if "cold_start_under_10_iters" in d.plateau_guards)
    lines.append(f"## Not flagged: {not_flagged} substrates")
    lines.append("")
    lines.append(f"_(Plus {paper_crit} paper-critical and {cold} cold-start substrates excluded by guards.)_")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("**Detector metadata**")
    lines.append("")
    lines.append(f"- Run timestamp: `{timestamp}`")
    lines.append(f"- Trajectory archive snapshot: `{archive_path}`")
    lines.append(f"- Decision rule version: `{rule_version}`")
    return "\n".join(lines)


def run(
    archive_path: Path,
    track_record_path: Path,
    inbox_path: Path,
    *,
    substrate_filter: str | None = None,
    dry_run: bool = False,
    stagnation_threshold: int = DEFAULT_STAGNATION_THRESHOLD,
    variance_threshold: float = DEFAULT_VARIANCE_THRESHOLD,
    cost_multiplier: float = DEFAULT_COST_MULTIPLIER,
    no_plateau_guard: bool = False,
    now_ts: int | None = None,
) -> tuple[str, Path | None]:
    rows = load_archive(archive_path)
    paper_crit = project_paper_critical_set(track_record_path)
    if now_ts is None:
        now_ts = int(datetime.now(timezone.utc).timestamp())
    metrics = compute_metrics(rows, paper_crit, now_ts=now_ts)
    if substrate_filter:
        metrics = {k: v for k, v in metrics.items() if k == substrate_filter}
    median_cost = median_all_time_cost(metrics)
    decisions = [
        evaluate(
            m,
            median_cost,
            stagnation_threshold=stagnation_threshold,
            variance_threshold=variance_threshold,
            cost_multiplier=cost_multiplier,
            no_plateau_guard=no_plateau_guard,
        )
        for m in metrics.values()
    ]
    decisions.sort(key=lambda d: (not d.recommend_retirement, d.project))

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    md = render_markdown(decisions, median_cost, archive_path, timestamp)

    if dry_run:
        return md, None

    inbox_path.mkdir(parents=True, exist_ok=True)
    out_path = inbox_path / f"{timestamp}_retirement_candidates.md"
    out_path.write_text(md)
    return md, out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ztare.research_director.retirement_detector")
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--track-record", type=Path, default=DEFAULT_TRACK_RECORD)
    parser.add_argument("--inbox", type=Path, default=DEFAULT_INBOX)
    parser.add_argument("--substrate", type=str, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--threshold-stagnation", type=int, default=DEFAULT_STAGNATION_THRESHOLD)
    parser.add_argument("--threshold-variance", type=float, default=DEFAULT_VARIANCE_THRESHOLD)
    parser.add_argument("--threshold-cost-multiplier", type=float, default=DEFAULT_COST_MULTIPLIER)
    parser.add_argument("--no-plateau-guard", action="store_true")
    args = parser.parse_args(argv)

    md, path = run(
        args.archive,
        args.track_record,
        args.inbox,
        substrate_filter=args.substrate,
        dry_run=args.dry_run,
        stagnation_threshold=args.threshold_stagnation,
        variance_threshold=args.threshold_variance,
        cost_multiplier=args.threshold_cost_multiplier,
        no_plateau_guard=args.no_plateau_guard,
    )
    if args.dry_run:
        print(md)
    else:
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
