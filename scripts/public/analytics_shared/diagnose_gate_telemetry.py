#!/usr/bin/env python3
"""Cage-engagement telemetry diagnostic.

The 2026-05-06 GP-220 ROI audit surfaced 0% engagement for R8/R9/R10
(feature_coverage_adequacy, target_convention_homogeneity,
cross_class_extrapolation) across 1857 eligible iters. Two
hypotheses:

  H1 (logging-name mismatch): the gates run but emit telemetry under
      different keys than what GP-220 reads. Real fix: rename / map.
  H2 (engagement actually rare): the gates run-or-refuse correctly
      but don't fire often. Real fix: investigate `can_handle`
      predicates.

This diagnostic walks every ``cage_engagement.jsonl`` across all
project workspaces, aggregates the actual gate names that appear,
and cross-references against the registry GP-220 expects. The
gap (or lack of gap) discriminates H1 vs H2.

Output:
  ``analytics/public/queries/audits/gate_telemetry_diagnosis.json``
  ``analytics/public/queries/audits/gate_telemetry_diagnosis.md``

Pure CPU. No LLM.

Usage:
    python scripts/public/analytics_shared/diagnose_gate_telemetry.py
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PROJECTS_DIR = REPO / "projects"
OUT_JSON = REPO / "analytics" / "public" / "queries" / "audits" / "gate_telemetry_diagnosis.json"
OUT_MD = REPO / "analytics" / "public" / "queries" / "audits" / "gate_telemetry_diagnosis.md"


# What GP-220 expects to find in cage_engagement.jsonl
EXPECTED_GATE_NAMES = {
    "feature_coverage_adequacy",  # R8
    "target_convention_homogeneity",  # R9
    "cross_class_extrapolation",  # R10
    "per_class_farther_tail",  # R11
    "symbolic_logic_cage",  # R12
    "substrate_critic",  # R13 (direct-wired today)
    "noise_profile",  # R14 (direct-wired today)
    "analogy",  # R15 (direct-wired today)
    "framer_1d",  # R16 (direct-wired today)
    # Structural anti-pattern gates surfaced by 2026-05-06 cross-audit
    # — registered late but emit 424 events each in cage_engagement.jsonl
    "withheld_value_leakage",  # R20
    "effective_parameter_count",  # R21
    "apparatus_meta_runner",  # R22
    "sparse_cell_exclusion",  # R23
    "feature_bump_pattern",  # R24
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-json", type=Path, default=OUT_JSON)
    ap.add_argument("--out-md", type=Path, default=OUT_MD)
    args = ap.parse_args()

    print("=== gate-telemetry diagnostic ===")

    if not PROJECTS_DIR.exists():
        print(f"  ERROR: {PROJECTS_DIR} not found")
        return 1

    # Aggregate actual gate names that appear
    actual_gate_counts: Counter[str] = Counter()
    actual_engaged_counts: Counter[str] = Counter()
    actual_refused_counts: Counter[str] = Counter()
    # Per-project gate-name appearance
    per_project_gates: dict[str, set[str]] = defaultdict(set)
    # Total cage_engagement events
    n_events = 0
    n_files = 0

    for project_path in sorted(PROJECTS_DIR.iterdir()):
        if not project_path.is_dir():
            continue
        cage_log = project_path / "workspace" / "cage_engagement.jsonl"
        if not cage_log.exists():
            continue
        n_files += 1
        try:
            for line in cage_log.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:  # noqa: BLE001
                    continue
                n_events += 1
                engagements = rec.get("engagements") or {}
                if not isinstance(engagements, dict):
                    continue
                for gate_name, info in engagements.items():
                    actual_gate_counts[gate_name] += 1
                    per_project_gates[project_path.name].add(gate_name)
                    if isinstance(info, dict):
                        if bool(info.get("ok", False)):
                            actual_engaged_counts[gate_name] += 1
                        else:
                            actual_refused_counts[gate_name] += 1
        except Exception:  # noqa: BLE001
            continue

    print(f"  cage_engagement.jsonl files: {n_files}")
    print(f"  cage events: {n_events}")
    print(f"  distinct gate names seen: {len(actual_gate_counts)}")
    print(f"  expected gate names: {len(EXPECTED_GATE_NAMES)}")

    # Discriminate H1 (logging-name mismatch) vs H2 (rare engagement)
    expected_set = EXPECTED_GATE_NAMES
    actual_names_set = set(actual_gate_counts.keys())

    expected_present = expected_set & actual_names_set
    expected_missing = expected_set - actual_names_set
    unexpected_present = actual_names_set - expected_set

    # Diagnosis: for each expected-but-missing gate, the H1 hypothesis
    # would be confirmed by an unexpected-present gate that's
    # similar in name (rename candidate).
    rename_candidates = []
    for missing in expected_missing:
        # Find unexpected gates that share a token
        missing_tokens = set(missing.split("_"))
        for unexpected in unexpected_present:
            shared = missing_tokens & set(unexpected.split("_"))
            if len(shared) >= 1:
                rename_candidates.append({
                    "expected": missing,
                    "actual": unexpected,
                    "shared_tokens": sorted(shared),
                    "actual_count": actual_gate_counts[unexpected],
                })
    rename_candidates.sort(key=lambda c: (-c["actual_count"], c["expected"]))

    # Per-expected-gate appearance summary
    expected_summary = []
    for name in sorted(expected_set):
        total = actual_gate_counts.get(name, 0)
        engaged = actual_engaged_counts.get(name, 0)
        refused = actual_refused_counts.get(name, 0)
        n_projects = sum(1 for gates in per_project_gates.values() if name in gates)
        expected_summary.append({
            "expected_name": name,
            "total_appearances": total,
            "engaged": engaged,
            "refused": refused,
            "n_projects_seen": n_projects,
            "engagement_rate": (
                engaged / total if total > 0 else 0.0
            ),
            "verdict": (
                "missing_from_logs"
                if total == 0
                else (
                    "low_engagement"
                    if (engaged / total) < 0.05
                    else "engaging"
                )
            ),
        })

    payload = {
        "audit_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "n_cage_engagement_files": n_files,
        "n_cage_events": n_events,
        "n_distinct_gate_names_seen": len(actual_gate_counts),
        "all_actual_gate_names_with_counts": dict(actual_gate_counts.most_common()),
        "expected_gate_names": sorted(expected_set),
        "expected_present_in_logs": sorted(expected_present),
        "expected_missing_from_logs": sorted(expected_missing),
        "unexpected_present_in_logs": sorted(unexpected_present),
        "rename_candidates": rename_candidates,
        "expected_gate_summary": expected_summary,
        "diagnosis": (
            "H1 confirmed: logging-name mismatch — see rename_candidates"
            if rename_candidates and expected_missing
            else (
                "H2 confirmed: gates appear in logs at low engagement rate"
                if not expected_missing
                else "Unclear — gates missing from logs but no rename candidates found"
            )
        ),
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, indent=2))
    print(f"  wrote {args.out_json}")

    md = ["# Cage-Engagement Telemetry Diagnostic\n"]
    md.append(f"_Generated {payload['audit_timestamp_utc']}_  ")
    md.append(f"_Files:_ {n_files}  _Events:_ {n_events}  _Distinct names:_ {len(actual_gate_counts)}\n")
    md.append(f"## Diagnosis\n\n**{payload['diagnosis']}**\n")
    md.append("## Per-expected-gate verdict\n")
    md.append(
        "| Expected name | Total | Engaged | Refused | Projects | Engagement rate | Verdict |\n"
        "|---|---:|---:|---:|---:|---:|---|"
    )
    for s in expected_summary:
        md.append(
            f"| `{s['expected_name']}` | {s['total_appearances']} | "
            f"{s['engaged']} | {s['refused']} | {s['n_projects_seen']} | "
            f"{s['engagement_rate']:.2%} | `{s['verdict']}` |"
        )
    md.append("")
    if rename_candidates:
        md.append("## Rename candidates (likely H1 — logging-name mismatch)\n")
        md.append(
            "| Expected | Actual | Shared tokens | Actual count |\n"
            "|---|---|---|---:|"
        )
        for r in rename_candidates[:25]:
            md.append(
                f"| `{r['expected']}` | `{r['actual']}` | "
                f"{', '.join(r['shared_tokens'])} | {r['actual_count']} |"
            )
        md.append("")
    if unexpected_present:
        md.append("## All gate names actually seen in logs (top 30 by count)\n")
        md.append("| Actual name | Count |\n|---|---:|")
        for name, c in actual_gate_counts.most_common(30):
            tag = "  ← expected" if name in expected_set else ""
            md.append(f"| `{name}`{tag} | {c} |")
        md.append("")
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text("\n".join(md) + "\n")
    print(f"  wrote {args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
