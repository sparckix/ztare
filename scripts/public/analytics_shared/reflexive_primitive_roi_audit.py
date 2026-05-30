#!/usr/bin/env python3
"""GP-220 reflexive primitive ROI scorecard.

Per-primitive scorecard over the R8/R9/R10/R11/R12/R13/R14/R15/R16
catalog (and adjacent primitives like GP-076 predictive divergence
sweep, GP-156 visible-MRE attestation, GP-180 DAG steering, etc.).

Per primitive, we compute over a 28-day window:

  - ``engagement_rate`` = (iters where ``can_handle`` returned True) /
                         (total iters where rubric flag was on)
  - ``hit_rate``        = (iters where engagement produced a
                          non-empty finding) / (engaged iters)
  - ``action_rate``     = (iters where finding influenced next-iter
                          mutator briefing) / (hit iters)
  - ``score_lift``      = mean Δ-score on iters where action took
                          effect vs control

Verdict bands per GP-220 seam:

  load_bearing: action_rate ≥ 0.30 AND score_lift ≥ +1.0 over window
  useful:       action_rate ≥ 0.10 AND score_lift ≥ 0
  noisy_detector: hit_rate ≥ 0.20 BUT score_lift ≤ 0
  decorative:   engagement_rate ≥ 0.30 AND action_rate < 0.05
  dead:         engagement_rate < 0.05 AND data_points ≥ 50

Today's pragmatic limit: ``score_lift`` is hard to compute without
controlled-experiment design. We surface engagement + hit rates
per primitive (the deterministic part) and mark score_lift as
deferred — placeholder field 0.0 with a "not_computed" tag so
operator knows to interpret it cautiously.

Output:
  ``analytics/public/queries/reflexive/reflexive_primitive_roi.json``
  ``analytics/public/queries/reflexive/reflexive_primitive_roi.md``

Pure CPU (jsonl reads + grep). No LLM.

Usage:
    python scripts/public/analytics_shared/reflexive_primitive_roi_audit.py
    python scripts/public/analytics_shared/reflexive_primitive_roi_audit.py --since 2026-04-08
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PROJECTS_DIR = REPO / "projects"
RUBRICS_DIR = REPO / "rubrics"
OUT_JSON = REPO / "analytics" / "public" / "queries" / "reflexive_primitive_roi.json"
OUT_MD = REPO / "analytics" / "public" / "queries" / "reflexive_primitive_roi.md"


# Primitive registry: each entry tells the audit how to detect
# engagement + finding for one reflexive primitive.
#
# `cage_engagement_keys`: list of gate names in cage_engagement.jsonl
#   that map to this primitive (multiple if the primitive emits at
#   multiple phases like preflight + post_fit). Empty list means
#   primitive is detected via per_primitive_log instead.
# `per_primitive_log`: workspace-relative path of per-primitive log
# `rubric_flag`: rubric flag that opt-ins / enables this primitive
#
# 2026-05-06 PM correction: actual gate names in
# cage_engagement.jsonl are `R<N>_<descriptor>` per the GP-157 spec
# (the diagnose_gate_telemetry.py audit revealed the logging-name
# mismatch). Earlier registry assumed bare names. Fixed.
PRIMITIVE_REGISTRY: list[dict] = [
    # Cage-routed (R8-R12). R8 + R9 wired 2026-05-06 PM via
    # src/ztare/gates/r8_r9_substrate_validators.py — both opt-in by
    # default (engagement requires the rubric flag below).
    {
        "primitive_id": "R8",
        "name": "feature_coverage_adequacy",
        "cage_engagement_keys": ["R8_feature_coverage_adequacy"],
        "per_primitive_log": None,
        "rubric_flag": "enable_r8_feature_coverage",
    },
    {
        "primitive_id": "R9",
        "name": "target_convention_homogeneity",
        "cage_engagement_keys": ["R9_target_convention_homogeneity"],
        "per_primitive_log": None,
        "rubric_flag": "enable_r9_target_convention_homogeneity",
    },
    {
        "primitive_id": "R10",
        "name": "cross_class_extrapolation",
        "cage_engagement_keys": ["R10_cross_class_extrapolation"],
        "per_primitive_log": None,
        "rubric_flag": None,
    },
    {
        "primitive_id": "R11",
        "name": "per_class_mre_ceiling",
        "cage_engagement_keys": ["R11_per_class_mre_ceiling"],
        "per_primitive_log": None,
        "rubric_flag": "enforce_per_class_farther_tail",
    },
    {
        "primitive_id": "R12",
        "name": "symbolic_logic_cage",
        "cage_engagement_keys": ["R170_symbolic_logic_cage"],
        # Note: spec calls this R12 but the cage emits it as R170 —
        # numbering scheme is internal and doesn't always match the
        # primitive registry's R-number.
        "per_primitive_log": None,
        "rubric_flag": "enable_symbolic_logic_cage",
    },
    # Direct-wired (R13-R16) — appear at preflight AND post_fit phases
    {
        "primitive_id": "R13",
        "name": "substrate_critic",
        "cage_engagement_keys": [
            "R13_substrate_critic_preflight",
            "R13_substrate_critic_post_fit",
        ],
        "per_primitive_log": "substrate_critique.json",
        "rubric_flag": "disable_substrate_critic",  # opt-OUT
        "opt_out_flag": True,
    },
    {
        "primitive_id": "R14",
        "name": "noise_profile",
        "cage_engagement_keys": [
            "R14_noise_profile_preflight",
            "R14_noise_profile_post_fit",
        ],
        "per_primitive_log": "noise_profile.json",
        "rubric_flag": "disable_noise_profile",
        "opt_out_flag": True,
    },
    {
        "primitive_id": "R15",
        "name": "analogy",
        "cage_engagement_keys": ["R15_analogy"],
        "per_primitive_log": "analogy_log.jsonl",
        "rubric_flag": "enable_analogy",
    },
    {
        "primitive_id": "R16",
        "name": "framer_1d",
        "cage_engagement_keys": ["R16_framer_pre_fit"],
        "per_primitive_log": "framing_report.json",
        "rubric_flag": "enable_framer",
    },
    # New gates surfaced by the diagnostic that weren't in the
    # original spec doc — register them here so they show up in
    # the ROI scorecard. R20-R24 all live in
    # src/ztare/gates/structural_anti_pattern_gates.py and emit 424
    # events each across the corpus per cage_engagement.jsonl
    # diagnostic 2026-05-06 PM.
    {
        "primitive_id": "R20",
        "name": "withheld_value_leakage",
        "cage_engagement_keys": ["R20_withheld_value_leakage"],
        "per_primitive_log": None,
        "rubric_flag": "enable_withheld_value_leakage_gate",
    },
    {
        "primitive_id": "R21",
        "name": "effective_parameter_count",
        "cage_engagement_keys": ["R21_effective_parameter_count"],
        "per_primitive_log": None,
        "rubric_flag": "enable_effective_parameter_count_gate",
    },
    {
        "primitive_id": "R22",
        "name": "apparatus_meta_runner",
        "cage_engagement_keys": ["R22_apparatus_meta_runner"],
        "per_primitive_log": None,
        "rubric_flag": None,
    },
    {
        "primitive_id": "R23",
        "name": "sparse_cell_exclusion",
        "cage_engagement_keys": ["R23_sparse_cell_exclusion"],
        "per_primitive_log": None,
        "rubric_flag": None,
    },
    {
        "primitive_id": "R24",
        "name": "feature_bump_pattern",
        "cage_engagement_keys": ["R24_feature_bump_pattern"],
        "per_primitive_log": None,
        "rubric_flag": "enable_feature_bump_pattern_gate",
    },
    {
        "primitive_id": "ansatz_survivor",
        "name": "ansatz_survivor",
        "cage_engagement_keys": ["ansatz_survivor"],
        "per_primitive_log": None,
        "rubric_flag": None,
    },
    # Adjacent primitives
    {
        "primitive_id": "GP-076",
        "name": "predictive_divergence_sweep",
        "cage_engagement_key": None,
        "per_primitive_log": None,
        "log_glob": "divergence_sweep_*.json",
        "rubric_flag": "enable_predictive_divergence_sweep",
    },
    {
        "primitive_id": "GP-180",
        "name": "dag_steering",
        "cage_engagement_key": None,
        "per_primitive_log": "dag_steering_log.jsonl",
        "rubric_flag": "enable_dag_steering",
    },
    {
        "primitive_id": "contract_adherence",
        "name": "contract_adherence",
        "cage_engagement_key": None,
        "per_primitive_log": "contract_violations.jsonl",
        "rubric_flag": None,
    },
]


def parse_ts(s: str) -> datetime | None:
    if not s:
        return None
    try:
        s = s.strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except Exception:  # noqa: BLE001
        return None


def file_mtime_within(path: Path, cutoff: datetime | None) -> bool:
    if not path.exists():
        return False
    if cutoff is None:
        return True
    try:
        m = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        return m >= cutoff
    except Exception:  # noqa: BLE001
        return False


def read_rubric_for_project(project_name: str) -> dict | None:
    for cand in (
        RUBRICS_DIR / f"{project_name}.json",
        RUBRICS_DIR / f"dynamic_{project_name}.json",
    ):
        if cand.exists():
            try:
                return json.loads(cand.read_text())
            except Exception:  # noqa: BLE001
                continue
    return None


def primitive_is_enabled_for_project(prim: dict, rubric: dict | None) -> bool:
    """True if rubric flags allow this primitive to engage."""
    flag = prim.get("rubric_flag")
    if flag is None:
        return True
    if rubric is None:
        return False
    val = rubric.get(flag, False)
    if prim.get("opt_out_flag"):
        # opt-OUT semantics: the flag DISABLES; primitive is on unless
        # flag is True
        return not bool(val)
    return bool(val)


def count_iter_telemetry(workspace: Path, cutoff: datetime | None) -> int:
    """Number of iter rows in iteration_telemetry.jsonl within window."""
    p = workspace / "iteration_telemetry.jsonl"
    if not p.exists():
        return 0
    n = 0
    try:
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:  # noqa: BLE001
                continue
            if rec.get("record_type") != "iteration":
                continue
            if cutoff is not None:
                ts = parse_ts(str(rec.get("iteration_end_utc") or ""))
                if ts is not None and ts < cutoff:
                    continue
            n += 1
    except Exception:  # noqa: BLE001
        return 0
    return n


def count_cage_engagements(workspace: Path, cutoff: datetime | None) -> dict:
    """Aggregate per-gate engaged/refused counts from cage_engagement.jsonl."""
    p = workspace / "cage_engagement.jsonl"
    if not p.exists():
        return {}
    per_gate: dict[str, dict[str, int]] = {}
    try:
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:  # noqa: BLE001
                continue
            if cutoff is not None:
                ts = parse_ts(str(rec.get("utc") or ""))
                if ts is not None and ts < cutoff:
                    continue
            engagements = rec.get("engagements") or {}
            for name, info in engagements.items():
                bucket = per_gate.setdefault(
                    name, {"engaged": 0, "refused": 0}
                )
                if isinstance(info, dict) and bool(info.get("ok", False)):
                    bucket["engaged"] += 1
                else:
                    bucket["refused"] += 1
    except Exception:  # noqa: BLE001
        return {}
    return per_gate


def count_per_primitive_log(workspace: Path, prim: dict, cutoff: datetime | None) -> int:
    """Count engagement events for a direct-wired primitive."""
    log_name = prim.get("per_primitive_log")
    glob_pattern = prim.get("log_glob")
    if log_name:
        p = workspace / log_name
        if not p.exists():
            return 0
        if str(p).endswith(".jsonl"):
            n = 0
            try:
                for line in p.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    try:
                        rec = json.loads(line)
                    except Exception:  # noqa: BLE001
                        continue
                    if cutoff is not None:
                        ts = parse_ts(str(rec.get("utc") or rec.get("ts") or ""))
                        if ts is not None and ts < cutoff:
                            continue
                    n += 1
            except Exception:  # noqa: BLE001
                return 0
            return n
        # JSON file — count as one event if mtime within window
        return 1 if file_mtime_within(p, cutoff) else 0
    if glob_pattern:
        try:
            matches = list(workspace.glob(glob_pattern))
        except Exception:  # noqa: BLE001
            return 0
        if cutoff is None:
            return len(matches)
        return sum(1 for p in matches if file_mtime_within(p, cutoff))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", type=str, default=None,
                    help="ISO date — count only events on/after this (default 28d ago)")
    ap.add_argument("--out-json", type=Path, default=OUT_JSON)
    ap.add_argument("--out-md", type=Path, default=OUT_MD)
    args = ap.parse_args()

    if args.since:
        cutoff = parse_ts(args.since)
    else:
        cutoff = datetime.now(timezone.utc) - timedelta(days=28)
    print(f"=== GP-220 reflexive primitive ROI audit ===")
    print(f"  cutoff: {cutoff.isoformat() if cutoff else '(all time)'}")
    print(f"  registry: {len(PRIMITIVE_REGISTRY)} primitives")

    # Per-primitive aggregation
    per_primitive: dict[str, dict] = {}
    for prim in PRIMITIVE_REGISTRY:
        per_primitive[prim["primitive_id"]] = {
            "primitive_id": prim["primitive_id"],
            "name": prim["name"],
            "rubric_flag": prim.get("rubric_flag"),
            "opt_out": bool(prim.get("opt_out_flag", False)),
            "n_projects_eligible": 0,
            "n_iters_eligible": 0,
            "n_engaged": 0,
            "n_refused": 0,
            "n_findings": 0,  # for direct-wired primitives, "findings" ≈ log events
        }

    if not PROJECTS_DIR.exists():
        print(f"  ERROR: {PROJECTS_DIR} not found")
        return 1

    n_projects_scanned = 0
    for project_path in sorted(PROJECTS_DIR.iterdir()):
        if not project_path.is_dir():
            continue
        workspace = project_path / "workspace"
        if not workspace.is_dir():
            continue
        n_projects_scanned += 1
        rubric = read_rubric_for_project(project_path.name)
        n_iters = count_iter_telemetry(workspace, cutoff)
        cage_per_gate = count_cage_engagements(workspace, cutoff)

        for prim in PRIMITIVE_REGISTRY:
            pid = prim["primitive_id"]
            agg = per_primitive[pid]
            if not primitive_is_enabled_for_project(prim, rubric):
                continue
            agg["n_projects_eligible"] += 1
            agg["n_iters_eligible"] += n_iters

            # Cage-routed: sum across all cage_engagement keys this
            # primitive emits under (e.g., R13 has both _preflight
            # and _post_fit names).
            cage_keys = prim.get("cage_engagement_keys") or []
            cage_engagement_seen = False
            for cage_key in cage_keys:
                if cage_key in cage_per_gate:
                    agg["n_engaged"] += cage_per_gate[cage_key]["engaged"]
                    agg["n_refused"] += cage_per_gate[cage_key]["refused"]
                    cage_engagement_seen = True
            if not cage_keys:
                # Pure direct-wired (no cage logging): count log events
                events = count_per_primitive_log(workspace, prim, cutoff)
                agg["n_engaged"] += events
                agg["n_findings"] += events
            elif not cage_engagement_seen and prim.get("per_primitive_log"):
                # Cage-key registered but absent from logs AND has a
                # per-primitive log fallback — try the log
                events = count_per_primitive_log(workspace, prim, cutoff)
                agg["n_engaged"] += events
                agg["n_findings"] += events

    # Compute rates + verdict
    output_records = []
    for pid, agg in per_primitive.items():
        n_eligible = agg["n_iters_eligible"]
        n_engaged = agg["n_engaged"]
        engagement_rate = (
            n_engaged / max(1, n_eligible) if n_eligible > 0 else 0.0
        )
        # hit_rate == n_findings / n_engaged for direct-wired primitives;
        # for cage-routed primitives without per-primitive findings logs,
        # we treat hit_rate == engagement_rate (engagement IS the finding
        # signal for those gates).
        if agg.get("n_findings"):
            hit_rate = agg["n_findings"] / max(1, n_engaged)
        else:
            hit_rate = 1.0 if n_engaged > 0 else 0.0
        # action_rate + score_lift: deferred (need to join with mutator
        # briefing logs and per-iter score deltas — out of scope for this
        # round). Mark as not_computed.
        action_rate = None
        score_lift = None

        # Verdict bands per GP-220 seam
        if n_eligible < 50:
            verdict = "insufficient_data"
        elif engagement_rate < 0.05:
            verdict = "dead"
        elif engagement_rate >= 0.30 and (action_rate is None or action_rate < 0.05):
            # Without action_rate, fall back to "low engagement-to-finding"
            verdict = (
                "decorative_candidate"
                if hit_rate < 0.10
                else "engagement_high"
            )
        elif hit_rate >= 0.20 and (score_lift is None or score_lift <= 0):
            verdict = "noisy_detector_candidate"
        else:
            verdict = "alive_action_unmeasured"

        output_records.append({
            "primitive_id": pid,
            "name": agg["name"],
            "rubric_flag": agg["rubric_flag"],
            "opt_out": agg["opt_out"],
            "n_projects_eligible": agg["n_projects_eligible"],
            "n_iters_eligible": n_eligible,
            "n_engaged": n_engaged,
            "n_refused": agg["n_refused"],
            "n_findings": agg["n_findings"],
            "engagement_rate": round(engagement_rate, 4),
            "hit_rate": round(hit_rate, 4),
            "action_rate": action_rate,
            "score_lift": score_lift,
            "verdict": verdict,
            "score_lift_status": "not_computed_v0",
        })
    output_records.sort(key=lambda r: -r["n_engaged"])

    # Aggregate verdict counts
    by_verdict: dict[str, int] = Counter(r["verdict"] for r in output_records)

    payload = {
        "audit_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "since": cutoff.isoformat() if cutoff else None,
        "n_projects_scanned": n_projects_scanned,
        "by_verdict": dict(by_verdict),
        "primitives": output_records,
        "honest_caveats": [
            "score_lift not yet computed — needs join with per-iter "
            "score deltas + mutator briefing context. v1.0 surfaces "
            "engagement + hit rate (deterministic).",
            "Cage-routed primitives without per-primitive findings logs "
            "treat engagement as the finding signal (hit_rate==1.0 when "
            "engaged>0).",
            "verdict bands are placeholders without action_rate / "
            "score_lift; promote primitives to load_bearing only when "
            "those metrics ship.",
        ],
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, indent=2))
    print(f"  wrote {args.out_json}")

    md = ["# Reflexive Primitive ROI Scorecard\n"]
    md.append(f"_Generated {payload['audit_timestamp_utc']}_  ")
    md.append(f"_Since:_ {payload['since'] or '(all time)'}  ")
    md.append(f"_Projects scanned:_ {n_projects_scanned}\n")
    md.append("## By verdict\n")
    md.append("| Verdict | Count |\n|---|---:|")
    for v, c in by_verdict.most_common():
        md.append(f"| `{v}` | {c} |")
    md.append("")
    md.append("## Per primitive\n")
    md.append(
        "| Primitive | Eligible projects | Eligible iters | Engaged | Refused | "
        "Findings | Engagement rate | Verdict |\n"
        "|---|---:|---:|---:|---:|---:|---:|---|"
    )
    for r in output_records:
        md.append(
            f"| `{r['primitive_id']}` ({r['name']}) | "
            f"{r['n_projects_eligible']} | {r['n_iters_eligible']} | "
            f"{r['n_engaged']} | {r['n_refused']} | {r['n_findings']} | "
            f"{r['engagement_rate']:.2%} | `{r['verdict']}` |"
        )
    md.append("")
    md.append("## Honest caveats\n")
    for c in payload["honest_caveats"]:
        md.append(f"- {c}")
    md.append("")
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text("\n".join(md) + "\n")
    print(f"  wrote {args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
