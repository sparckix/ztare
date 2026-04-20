"""Sandbox gaming behavior extractor.

Mines all debate_log_iter_*.md files across sandbox/science/general-purpose
projects to surface gaming patterns the mutator used against the cage
(rubric + gates). Output is a structured catalog suitable for:
  - promoting new deterministic gate contracts
  - feeding the V4 kernel's self-improvement loop
  - annotating paper findings on gaming taxonomy

Usage:
    python -m src.ztare.validator.sandbox_gaming_extractor [--output-dir DIR]
    python -m src.ztare.validator.sandbox_gaming_extractor --projects gp023_crucial_01 gp080_01

Output:
    workspace/sandbox_gaming_catalog.json   -- per-debate structured records
    workspace/sandbox_gaming_summary.md     -- ranked pattern report
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

PROJECTS_DIR = Path(__file__).resolve().parents[3] / "projects"
WORKSPACE_DIR = Path(__file__).resolve().parents[3] / "workspace"

# ---------------------------------------------------------------------------
# Gaming signal taxonomy
# ---------------------------------------------------------------------------

SIGNAL_PATTERNS: dict[str, list[str]] = {
    # Science / symbolic regression domain
    "uniqueness_gap": [
        "uniqueness", "unique", "exhaustive", "equally parsimonious",
        "identifiability", "no formal proof", "not proven", "cannot prove",
        "combinatorially", "rival.*equally", "other.*form.*also fit",
        "proof.*uniqueness", "uniqueness.*proof",
    ],
    "derivation_laundering": [
        "circular", "post-hoc", "reverse.engineer", "assumes what it proves",
        "tautolog", "not independently derived", "derived from the fit",
        "no independent derivation", "asserted rather than derived",
        "parameter.*not.*derived", "no.*mechanistic.*justification",
    ],
    "parameter_flexibility_abuse": [
        "extra parameter", "additional.*degree of freedom", "free parameter",
        "floating exponent", "over-parameteriz", "unnecessary.*parameter",
        "arbitrary.*constant", "tuned.*parameter", "added.*flexibility",
        "more parameters than", "too many.*parameter",
    ],
    "extrapolation_gap": [
        "extrapolat", "out of distribution", "outside.*observed", "tail.*behavior",
        "generalization.*claim", "beyond.*evidence", "outside.*training",
        "holdout", "farther.tail", "regime.*not.*tested",
    ],
    "parsimony_violation": [
        "parsimony", "parsimonious", "simpler.*explanation", "occam",
        "unnecessarily complex", "complexity.*not.*justified", "overfit",
        "over-fit", "too complex",
    ],
    "suite_pass_structure_gap": [
        "unit test.*pass.*but", "pass.*falsification.*however",
        "survived.*suite.*but", "technically.*pass", "gate.*pass.*weakness",
    ],
    "rival_construction_weakness": [
        "limited.*rival", "no.*alternative.*consider", "strongest.*rival.*weak",
        "strawman", "straw man", "rival.*not.*represent", "only.*one.*rival",
        "narrow.*rival", "rival.*hand.pick",
    ],
    "no_structural_progress": [
        "no.*hypothesis", "no.*proposed.*law", "no.*formula", "no.*attempt",
        "fails to engage", "no.*candidate", "no.*structural", "no.*mechanistic",
        "avoids.*commitment",
    ],
    # General purpose domain
    "evidence_cherry_picking": [
        "cherry.pick", "selectively cited", "ignor.*contrary", "contrary.*evidence.*ignored",
        "one.sided", "confirmation bias", "favorable.*evidence",
    ],
    "definitional_drift": [
        "redefine", "shifts.*definition", "goalpost", "definition.*shift",
        "equivocate", "ambiguous.*term", "term.*inconsistently",
    ],
    "specificity_inflation": [
        "vague.*claim", "no.*falsifiable", "untestable", "not.*specific",
        "cannot.*be.*falsified", "hedged.*to.*point", "empty.*claim",
    ],
    "base_rate_neglect": [
        "base rate", "prior probability", "prior.*neglect", "baseline",
        "unconditional probability",
    ],
    "counterfactual_weakness": [
        "counterfactual", "what would falsify", "alternative.*explanation",
        "could.*also.*explain", "underdetermin",
    ],
    "score_inflation_signal": [
        "score.*despite", "high.*score.*but", "awarded.*despite",
        "generous.*score", "score.*not.*reflect", "inflated",
    ],
}


def classify_signals(text: str) -> list[str]:
    """Apply taxonomy to free text, return matching signal names."""
    text_lower = text.lower()
    hits = []
    for signal, patterns in SIGNAL_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, text_lower):
                hits.append(signal)
                break
    return hits


# ---------------------------------------------------------------------------
# Debate log parser
# ---------------------------------------------------------------------------

@dataclass
class DebateRecord:
    project: str
    rubric: str
    mutator: str
    judge: str
    log_file: str
    iter_id: str               # numeric suffix from filename
    unit_test_pass: bool | None
    unit_test_error: str
    score: int | None
    weakest_point: str
    rationale: str
    gaming_signals: list[str]
    # from telemetry (filled in if available)
    iteration_index: int | None = None
    score_improved: bool | None = None
    champion_promoted: bool | None = None
    loop_control_action: str | None = None
    stagnation_count: int | None = None


def parse_debate_log(path: Path) -> DebateRecord | None:
    try:
        text = path.read_text(errors="replace")
    except Exception:
        return None

    project = path.parent.name

    # Header metadata
    rubric = mutator = judge = ""
    meta_match = re.search(
        r"<!--\s*rubric:\s*([^\|]+)\|?\s*mutator:\s*([^\|]+)\|?\s*judge:\s*([^-]+?)\s*-->",
        text,
    )
    if meta_match:
        rubric = meta_match.group(1).strip()
        mutator = meta_match.group(2).strip()
        judge = meta_match.group(3).strip()

    # Unit test result
    unit_test_pass: bool | None = None
    unit_test_error = ""
    if "✅ PASS" in text:
        unit_test_pass = True
    elif "❌ FAIL" in text:
        unit_test_pass = False
        err_match = re.search(r"❌ FAIL.*?\n(.*?)(?=\n# Final Score|\Z)", text, re.DOTALL)
        if err_match:
            unit_test_error = err_match.group(1).strip()[:500]

    # Score
    score: int | None = None
    score_match = re.search(r"#\s*Final Score:\s*(\d+)", text)
    if score_match:
        score = int(score_match.group(1))

    # Weakest point
    weakest_point = ""
    wp_match = re.search(r"\*\*Weakest Point:\*\*\s*(.+?)(?=\*\*Rationale|\Z)", text, re.DOTALL)
    if wp_match:
        weakest_point = wp_match.group(1).strip()

    # Rationale
    rationale = ""
    rat_match = re.search(r"\*\*Rationale:\*\*\s*(.+?)(?=\n#|\Z)", text, re.DOTALL)
    if rat_match:
        rationale = rat_match.group(1).strip()

    if score is None and not weakest_point:
        return None  # unparseable / incomplete log

    combined = f"{weakest_point} {rationale}"
    signals = classify_signals(combined)

    iter_id = re.sub(r"^debate_log_iter_|\.md$", "", path.name)

    return DebateRecord(
        project=project,
        rubric=rubric,
        mutator=mutator,
        judge=judge,
        log_file=str(path.relative_to(PROJECTS_DIR.parent)),
        iter_id=iter_id,
        unit_test_pass=unit_test_pass,
        unit_test_error=unit_test_error,
        score=score,
        weakest_point=weakest_point[:800],
        rationale=rationale[:800],
        gaming_signals=signals,
    )


# ---------------------------------------------------------------------------
# Telemetry correlator
# ---------------------------------------------------------------------------

def load_telemetry(project_dir: Path) -> dict[str, dict]:
    """Map iter_id → telemetry record from iteration_telemetry.jsonl."""
    telem_path = project_dir / "workspace" / "iteration_telemetry.jsonl"
    if not telem_path.exists():
        return {}
    result: dict[str, dict] = {}
    try:
        with telem_path.open() as f:
            for line in f:
                rec = json.loads(line)
                if rec.get("record_type") == "iteration":
                    # iter_id in debate log is the timestamp suffix — use run_id+iter_index
                    # but we match by iteration_index position order
                    result[str(rec.get("iteration_index", ""))] = rec
    except Exception:
        pass
    return result


def correlate_with_telemetry(record: DebateRecord, telemetry: dict[str, dict]) -> None:
    """Best-effort: match debate log to telemetry by iteration_index."""
    if not telemetry:
        return
    # Debate log iter_id is a Unix timestamp; telemetry has iteration_index.
    # We can't directly join them, but we can join by position if logs are ordered.
    # Use iteration_index if available in single-run projects.
    for idx_str, trow in sorted(telemetry.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0):
        pass  # just keep the last one as reference
    # If exactly one run, try matching by debate log mtime order vs telemetry index order
    # This is approximate — we only annotate champion iterations reliably
    for idx_str, trow in telemetry.items():
        if trow.get("champion_promoted"):
            if record.iter_id in str(trow.get("iteration_start_utc", "")):
                record.iteration_index = trow.get("iteration_index")
                record.score_improved = trow.get("score_improved")
                record.champion_promoted = trow.get("champion_promoted")
                record.loop_control_action = trow.get("loop_control_action")
                record.stagnation_count = trow.get("stagnation_count")
                break


# ---------------------------------------------------------------------------
# Project scanner
# ---------------------------------------------------------------------------

EXCLUDE_PATTERNS = [
    "_bench_", "bridge_hardening", "epistemic_engine_v4",
    "recursive_bayesian", "unidirectional_decay", "self_referential",
    "deterministic_score_contract", "t1_recursive",
]


def is_excluded(project_name: str) -> bool:
    return any(pat in project_name for pat in EXCLUDE_PATTERNS)


def scan_projects(projects_dir: Path, filter_projects: list[str] | None = None) -> list[DebateRecord]:
    records: list[DebateRecord] = []
    project_dirs = sorted(projects_dir.iterdir())

    for pdir in project_dirs:
        if not pdir.is_dir():
            continue
        if is_excluded(pdir.name):
            continue
        if filter_projects and pdir.name not in filter_projects:
            continue

        logs = sorted(pdir.glob("debate_log_iter_*.md"))
        if not logs:
            continue

        telemetry = load_telemetry(pdir)

        for log in logs:
            rec = parse_debate_log(log)
            if rec is None:
                continue
            correlate_with_telemetry(rec, telemetry)
            records.append(rec)

    return records


# ---------------------------------------------------------------------------
# Analysis and reporting
# ---------------------------------------------------------------------------

def build_summary(records: list[DebateRecord]) -> str:
    lines: list[str] = []
    lines.append("# Sandbox Gaming Behavior Extractor — Summary Report")
    lines.append(f"\nTotal debate logs parsed: {len(records)}")

    projects = sorted({r.project for r in records})
    lines.append(f"Projects covered: {len(projects)}")
    lines.append(f"Score=0 (unit test fail / no structural content): "
                 f"{sum(1 for r in records if r.score == 0)}")
    lines.append(f"Score>0 (substantive debate): "
                 f"{sum(1 for r in records if r.score and r.score > 0)}")

    # Signal frequency across all records with score > 0
    substantive = [r for r in records if r.score and r.score > 0]
    signal_counts: Counter = Counter()
    for r in substantive:
        for s in r.gaming_signals:
            signal_counts[s] += 1

    lines.append("\n---\n## Gaming Signal Frequency (score>0 debates only)")
    lines.append(f"Total substantive debates: {len(substantive)}\n")
    lines.append(f"{'Signal':<35} {'Count':>6}  {'% of debates':>14}  {'Promote to contract?':>20}")
    lines.append("-" * 80)
    for signal, count in signal_counts.most_common():
        pct = count / len(substantive) * 100 if substantive else 0
        promote = "YES" if pct >= 10 else "candidate" if pct >= 5 else "rare"
        lines.append(f"{signal:<35} {count:>6}  {pct:>13.1f}%  {promote:>20}")

    # Per-signal: show top examples
    lines.append("\n---\n## Top Examples per Signal\n")
    signal_to_records: dict[str, list[DebateRecord]] = defaultdict(list)
    for r in substantive:
        for s in r.gaming_signals:
            signal_to_records[s].append(r)

    for signal, count in signal_counts.most_common(12):
        recs = signal_to_records[signal]
        lines.append(f"### {signal}  (n={count})")
        # Show up to 3 diverse examples across different projects
        seen_projects: set[str] = set()
        shown = 0
        for r in sorted(recs, key=lambda x: -(x.score or 0)):
            if r.project in seen_projects:
                continue
            seen_projects.add(r.project)
            lines.append(f"\n**{r.project}** (score={r.score}, judge={r.judge})")
            lines.append(f"  Weakest: {r.weakest_point[:200]}")
            shown += 1
            if shown >= 3:
                break
        lines.append("")

    # Score distribution per signal
    lines.append("---\n## Score Distribution by Signal\n")
    lines.append(f"{'Signal':<35} {'n':>5}  {'mean_score':>10}  {'min':>5}  {'max':>5}")
    lines.append("-" * 65)
    for signal, _ in signal_counts.most_common():
        recs = signal_to_records[signal]
        scores = [r.score for r in recs if r.score is not None]
        if scores:
            mean_s = sum(scores) / len(scores)
            lines.append(
                f"{signal:<35} {len(scores):>5}  {mean_s:>10.1f}  {min(scores):>5}  {max(scores):>5}"
            )

    # Per-project breakdown
    lines.append("\n---\n## Per-Project Signal Profile\n")
    for proj in sorted(projects):
        proj_recs = [r for r in substantive if r.project == proj]
        if not proj_recs:
            continue
        proj_signals: Counter = Counter()
        for r in proj_recs:
            for s in r.gaming_signals:
                proj_signals[s] += 1
        top = ", ".join(f"{s}({c})" for s, c in proj_signals.most_common(4))
        mean_score = sum(r.score for r in proj_recs if r.score) / max(len(proj_recs), 1)
        lines.append(f"**{proj}** ({len(proj_recs)} debates, mean_score={mean_score:.0f}): {top or 'no signals'}")

    # Promotion decision table
    lines.append("\n---\n## Promotion Decision Table\n")
    lines.append("Two fix channels. Rule: if the judge caught it but a deterministic gate could have")
    lines.append("prevented it → CAGE fix. If the mutator never produced the right kind of content")
    lines.append("regardless of how the gate is tuned → KERNEL fix.\n")
    lines.append(f"{'Signal':<35} {'Prevalence':>10}  {'Channel':<8}  Concrete fix")
    lines.append("-" * 95)
    promotion_table = [
        ("no_structural_progress",   "KERNEL",  "Contract: mutator must propose ≥1 functional form with fitted params before score is read"),
        ("specificity_inflation",    "CAGE",    "Gate: any claim lacking a falsifiable prediction → automatic -10 penalty in gate_harness"),
        ("extrapolation_gap",        "CAGE",    "Gate: farther-tail discriminator required on all projects, not just science (adapt for general-purpose domain)"),
        ("uniqueness_gap",           "CAGE",    "Gate: thesis must enumerate ≥2 structural rivals + show divergence at holdout → cap 60 if absent"),
        ("parsimony_violation",      "CAGE",    "Gate: parameter count > evidence points → automatic FAIL or -15 penalty"),
        ("derivation_laundering",    "KERNEL",  "Contract: each parameter must have an independent derivation path cited in the thesis body"),
        ("rival_construction_weakness", "CAGE", "Gate: rivals must be drawn from pre-committed rival list (sealed before run), not hand-picked post-hoc"),
        ("suite_pass_structure_gap", "CAGE",    "Gate: unit test PASS is necessary but not sufficient — structural checklist runs after"),
        ("score_inflation_signal",   "KERNEL",  "Contract: judge must cite specific evidence lines for each +10 score increment"),
        ("counterfactual_weakness",  "RUBRIC",  "Rubric: every thesis must state what evidence would falsify it — scored 0 if absent"),
        ("base_rate_neglect",        "RUBRIC",  "Rubric: prior-probability section required for all probabilistic claims"),
    ]
    for signal, channel, fix in promotion_table:
        pct = signal_counts.get(signal, 0) / len(substantive) * 100 if substantive else 0
        lines.append(f"{signal:<35} {pct:>9.1f}%  {channel:<8}  {fix}")

    lines.append("\nChannels:\n"
                 "  CAGE   = add deterministic check to gate_harness.py or rubric scoring formula\n"
                 "  KERNEL = add contract to v4_meta_runner.py contract library\n"
                 "  RUBRIC = fix rubric template; no code change needed\n")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Incremental state — the painter's problem
# ---------------------------------------------------------------------------

def load_state(state_path: Path) -> dict[str, Any]:
    """Load previously-seen file registry to avoid re-scanning unchanged logs."""
    if state_path.exists():
        try:
            return json.loads(state_path.read_text())
        except Exception:
            pass
    return {"seen_files": {}, "last_run_utc": None, "total_processed": 0}


def save_state(state_path: Path, state: dict[str, Any], records: list[DebateRecord]) -> None:
    from datetime import datetime, timezone
    for r in records:
        fpath = Path(r.log_file)
        abs_path = PROJECTS_DIR.parent / fpath
        try:
            mtime = abs_path.stat().st_mtime
        except Exception:
            mtime = 0.0
        state["seen_files"][str(fpath)] = mtime
    state["last_run_utc"] = datetime.now(timezone.utc).isoformat()
    state["total_processed"] = len(state["seen_files"])
    state_path.write_text(json.dumps(state, indent=2))


def filter_new_files(
    project_dir: Path,
    state: dict[str, Any],
    incremental: bool,
) -> list[Path]:
    """Return debate logs not yet in state (or all if not incremental)."""
    logs = sorted(project_dir.glob("debate_log_iter_*.md"))
    if not incremental:
        return logs
    seen = state.get("seen_files", {})
    result = []
    for log in logs:
        rel = str(log.relative_to(PROJECTS_DIR.parent))
        try:
            mtime = log.stat().st_mtime
        except Exception:
            continue
        if rel not in seen or seen[rel] != mtime:
            result.append(log)
    return result


def scan_projects_incremental(
    projects_dir: Path,
    state: dict[str, Any],
    incremental: bool,
    filter_projects: list[str] | None = None,
) -> list[DebateRecord]:
    records: list[DebateRecord] = []
    for pdir in sorted(projects_dir.iterdir()):
        if not pdir.is_dir():
            continue
        if is_excluded(pdir.name):
            continue
        if filter_projects and pdir.name not in filter_projects:
            continue
        logs = filter_new_files(pdir, state, incremental)
        if not logs:
            continue
        telemetry = load_telemetry(pdir)
        for log in logs:
            rec = parse_debate_log(log)
            if rec is None:
                continue
            correlate_with_telemetry(rec, telemetry)
            records.append(rec)
    return records


def merge_catalog(existing_path: Path, new_records: list[DebateRecord]) -> list[DebateRecord]:
    """Merge new records into existing catalog, deduplicating by log_file."""
    existing: list[dict] = []
    if existing_path.exists():
        try:
            existing = json.loads(existing_path.read_text())
        except Exception:
            pass
    seen_files = {r["log_file"] for r in existing}
    merged = existing + [asdict(r) for r in new_records if r.log_file not in seen_files]
    # Reconstruct as DebateRecord objects for analysis
    result = []
    for d in merged:
        try:
            result.append(DebateRecord(**{k: v for k, v in d.items() if k in DebateRecord.__dataclass_fields__}))
        except Exception:
            pass
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Mine sandbox debate logs for gaming patterns (incremental)."
    )
    parser.add_argument("--projects", nargs="+", help="Limit to specific project names")
    parser.add_argument("--output-dir", default=None, help="Output directory (default: workspace/)")
    parser.add_argument("--min-score", type=int, default=0, help="Only include debates with score >= N")
    parser.add_argument(
        "--full", action="store_true",
        help="Re-scan all files regardless of state (ignore painter's cache)"
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir) if args.output_dir else WORKSPACE_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    state_path = output_dir / "sandbox_gaming_state.json"
    catalog_path = output_dir / "sandbox_gaming_catalog.json"
    summary_path = output_dir / "sandbox_gaming_summary.md"

    incremental = not args.full
    state = load_state(state_path)

    previously_seen = len(state.get("seen_files", {}))
    print(
        f"[sandbox_gaming_extractor] State: {previously_seen} files seen previously. "
        f"Mode: {'full rescan' if args.full else 'incremental'}",
        flush=True,
    )

    print("[sandbox_gaming_extractor] Scanning for new debate logs...", flush=True)
    new_records = scan_projects_incremental(
        PROJECTS_DIR, state, incremental, filter_projects=args.projects
    )
    print(f"[sandbox_gaming_extractor] New logs this run: {len(new_records)}", flush=True)

    if not new_records and incremental:
        print("[sandbox_gaming_extractor] No new logs. Regenerating summary from existing catalog.")

    # Merge with existing catalog
    all_records = merge_catalog(catalog_path, new_records)

    if args.min_score > 0:
        all_records = [r for r in all_records if r.score is not None and r.score >= args.min_score]

    print(f"[sandbox_gaming_extractor] Total records in catalog: {len(all_records)}", flush=True)

    # Write merged catalog
    with catalog_path.open("w") as f:
        json.dump([asdict(r) for r in all_records], f, indent=2)
    print(f"[sandbox_gaming_extractor] Catalog written: {catalog_path}", flush=True)

    # Save updated state
    save_state(state_path, state, new_records)
    print(f"[sandbox_gaming_extractor] State saved: {state_path}", flush=True)

    # Write summary
    summary = build_summary(all_records)
    summary_path.write_text(summary)
    print(f"[sandbox_gaming_extractor] Summary written: {summary_path}", flush=True)

    print("\n" + summary)


if __name__ == "__main__":
    main()
