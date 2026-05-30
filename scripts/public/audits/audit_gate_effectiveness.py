#!/usr/bin/env python3
"""META-GATE 2B: dynamic gate-effectiveness audit.

Mines run logs to detect gates that engage but never raise verdicts -
the historical R20-R24 form_str key bug pattern, where the dispatcher
read fit['parametric_form_substituted'] (non-existent) instead of
fit['form'], so the gates ran into a vacuum across many iters.

Detector classes:
    HIGH-RISK     -- gate engages > 70% of iters AND flags 0%, run
                     cap-rate > 50%, AND the gate has a known verdict
                     file source (so 0% really means the file says "no
                     fire", not "we have no way to read it"). Vacuum
                     verdicts (n_constants_scanned=0 etc.) are the
                     load-bearing form_str-key-bug fingerprint.
    SUSPICIOUS    -- engages > 70%, flags < 5%, and the rare flags do not
                     correlate with score caps. Either the gate misses
                     the failure mode or the score ignores it.
    HEALTHY       -- engages, occasionally flags, flags correlate with
                     score caps.
    HARNESS-GAP   -- gate refuses because gate_harness_result.json is
                     absent (or its prerequisite is). Not a gate bug,
                     a missing harness-output bug.
    NO-VERDICT-SOURCE -- gate engages but the audit has no verdict file
                     to read for it (e.g. circularity/falsifiability
                     emit verdicts inline in eval_history.gate_verdicts).
                     Cannot judge effectiveness from telemetry alone.
    INACTIVE      -- gate never engaged on any iter (off by class scope).

Usage:
    python scripts/public/audits/audit_gate_effectiveness.py [--strict] [--json]
        [--root <repo_root>] [--cap-threshold 70] [--engage-threshold 0.7]
        [--project <name>]      # restrict to one project (repeatable)

Exit codes:
    0  no HIGH-RISK findings (or --strict not passed)
    1  HIGH-RISK findings present and --strict was passed
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


# ---- structural-anti-pattern (R20-R24) verdict reader -------------------
# Each gate sub-block looks like:
#   { "flagged": bool, "matches": [...], "n_constants_scanned": int, ... }
# A "vacuum" verdict (the form_str-key-bug fingerprint) is:
#   flagged=False AND every numeric "n_*" counter is 0 AND matches==[]
R_GATES_STRUCTURAL = (
    "r20_withheld_value_leakage",
    "r21_effective_parameter_count",
    "r22_apparatus_meta_runner",
    "r23_sparse_cell_exclusion",
    "r24_feature_bump_pattern",
)

# Gates whose verdict can be read from a file in the workspace. Only
# these are eligible for HIGH-RISK / SUSPICIOUS classification, because
# only here can we confidently say flag_count == 0.
GATES_WITH_VERDICT_SOURCE: set[str] = {
    "R20_withheld_value_leakage",
    "R21_effective_parameter_count",
    "R22_apparatus_meta_runner",
    "R23_sparse_cell_exclusion",
    "R24_feature_bump_pattern",
    "R14_noise_profile_post_fit",
    "Forced_REFRAME",
}


# Map cage_engagement gate_id (R20_..., R21_...) -> structural file key (r20_..., r21_...).
def _engage_id_to_struct_key(engage_id: str) -> str | None:
    m = re.match(r"^(R2\d)_", engage_id)
    if not m:
        return None
    n = m.group(1).lower()
    for k in R_GATES_STRUCTURAL:
        if k.startswith(n + "_"):
            return k
    return None


def _is_vacuum_struct_verdict(block: Any) -> bool:
    """Return True if a R20-R24 sub-block looks like a vacuum verdict.

    Vacuum = flagged False AND no positive counters AND empty matches.
    A genuine non-fire (gate ran, found nothing real) will have non-zero
    scan counters or a non-empty load-bearing list.
    """
    if not isinstance(block, dict):
        return False
    if block.get("flagged") is True:
        return False
    matches = block.get("matches") or []
    if matches:
        return False
    # Look at all numeric counters; if any > 0, gate had material to chew.
    for k, v in block.items():
        if k == "flagged":
            continue
        if isinstance(v, (int, float)) and v != 0:
            return False
        if isinstance(v, list) and v:
            return False
    return True


# ---- workspace discovery ------------------------------------------------
SKIP_PROJECT_PREFIXES = ("_bench",)
SKIP_PARENT_DIR_PATTERNS = ("archive_", "frozen_")


def discover_workspaces(projects_root: Path) -> list[tuple[str, Path]]:
    """Return [(project_label, workspace_dir)].

    We include archived workspaces explicitly because the historical
    form_str key bug only lives in pre-fix archives. Each is labelled
    `<project>::<archive_subdir>` so the operator can tell them apart.
    """
    out: list[tuple[str, Path]] = []
    for project_dir in sorted(projects_root.iterdir()):
        if not project_dir.is_dir():
            continue
        name = project_dir.name
        if any(name.startswith(p) for p in SKIP_PROJECT_PREFIXES):
            continue
        ws = project_dir / "workspace"
        if ws.is_dir() and (ws / "cage_engagement.jsonl").exists():
            out.append((name, ws))
        # Archived / frozen runs (these are where the historical bug lives).
        for sub in sorted(project_dir.iterdir()):
            if not sub.is_dir():
                continue
            if not any(sub.name.startswith(p) for p in SKIP_PARENT_DIR_PATTERNS):
                continue
            ws_arch = sub / "workspace"
            if ws_arch.is_dir() and (ws_arch / "cage_engagement.jsonl").exists():
                out.append((f"{name}::{sub.name}", ws_arch))
    return out


# ---- per-workspace parsing ----------------------------------------------
def _read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    if not path.exists():
        return rows
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def _read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        with path.open() as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _iter_struct_files(ws: Path) -> dict[int, Path]:
    out: dict[int, Path] = {}
    for p in ws.glob("structural_anti_pattern_iter_*.json"):
        m = re.search(r"iter_(\d+)", p.name)
        if m:
            out[int(m.group(1))] = p
    return out


def _iter_forced_reframe_files(ws: Path) -> dict[int, Path]:
    out: dict[int, Path] = {}
    for p in ws.glob("forced_reframe_iter_*.json"):
        m = re.search(r"iter_(\d+)", p.name)
        if m:
            out[int(m.group(1))] = p
    return out


def _iter_noise_post_fit_files(ws: Path) -> dict[int, Path]:
    out: dict[int, Path] = {}
    for p in ws.glob("noise_profile_post_fit_iter_*.json"):
        m = re.search(r"iter_(\d+)", p.name)
        if m:
            out[int(m.group(1))] = p
    return out


def analyse_workspace(label: str, ws: Path, *, cap_threshold: float, engage_threshold: float) -> dict:
    """Compute per-gate effectiveness statistics for one workspace."""
    eval_rows = _read_jsonl(ws / "eval_history.jsonl")
    cage_rows = _read_jsonl(ws / "cage_engagement.jsonl")
    iters = max(len(eval_rows), len(cage_rows))

    # Score / cap analysis.
    iter_scores: dict[int, float] = {}
    for r in eval_rows:
        it = r.get("iteration") or r.get("iter")
        if isinstance(it, int):
            iter_scores[it] = float(r.get("score") or 0)
    capped_iters = {it for it, s in iter_scores.items() if s < cap_threshold}
    n_eval = len(iter_scores)
    cap_rate = (len(capped_iters) / n_eval) if n_eval else 0.0
    champion = max(iter_scores.values()) if iter_scores else None

    # Engagement matrix (gate_id -> set of iters where ok=True).
    gate_engage: dict[str, set[int]] = defaultdict(set)
    gate_refused_with_reason: dict[str, list[tuple[int, str]]] = defaultdict(list)
    seen_gates: set[str] = set()
    cage_iters: list[int] = []
    for row in cage_rows:
        it = row.get("iter")
        if not isinstance(it, int):
            continue
        cage_iters.append(it)
        engagements = row.get("engagements") or {}
        for gid, payload in engagements.items():
            seen_gates.add(gid)
            if isinstance(payload, dict) and payload.get("ok"):
                gate_engage[gid].add(it)
            elif isinstance(payload, dict):
                reason = str(payload.get("reason") or "")
                gate_refused_with_reason[gid].append((it, reason))
    n_cage = len(cage_iters)

    # Verdict matrices: which iters did each gate FLAG.
    gate_flag: dict[str, set[int]] = defaultdict(set)
    gate_vacuum: dict[str, set[int]] = defaultdict(set)
    gate_verdict_iters: dict[str, set[int]] = defaultdict(set)  # iters where a verdict file exists
    # R20-R24 from structural_anti_pattern_iter_*.json
    for it, path in _iter_struct_files(ws).items():
        data = _read_json(path) or {}
        for k in R_GATES_STRUCTURAL:
            block = data.get(k)
            num = k[1:3]  # '20'..'24'
            rest = k[4:]
            engage_id = f"R{num}_{rest}"
            if block is None:
                continue
            gate_verdict_iters[engage_id].add(it)
            if isinstance(block, dict) and block.get("flagged") is True:
                gate_flag[engage_id].add(it)
            elif _is_vacuum_struct_verdict(block):
                gate_vacuum[engage_id].add(it)

    # forced_reframe_iter_*.json -> "Forced_REFRAME" pseudo-gate
    for it, path in _iter_forced_reframe_files(ws).items():
        data = _read_json(path) or {}
        gate_verdict_iters["Forced_REFRAME"].add(it)
        if data.get("should_force"):
            gate_flag["Forced_REFRAME"].add(it)

    # noise_profile_post_fit_iter_*.json -> R14_noise_profile_post_fit-ish
    for it, path in _iter_noise_post_fit_files(ws).items():
        data = _read_json(path) or {}
        gate_verdict_iters["R14_noise_profile_post_fit"].add(it)
        if data.get("needs_robust") or data.get("needs_weighted") or data.get("needs_correlated"):
            gate_flag["R14_noise_profile_post_fit"].add(it)

    # gate_harness_result.json present?
    harness_present = (ws / "gate_harness_result.json").exists()

    # Build per-gate findings.
    findings: list[dict] = []
    all_gate_ids = sorted(seen_gates | gate_flag.keys() | gate_vacuum.keys() | gate_verdict_iters.keys())
    for gid in all_gate_ids:
        engage_iters = gate_engage.get(gid, set())
        verdict_iters = gate_verdict_iters.get(gid, set())
        flag_iters = gate_flag.get(gid, set())
        vacuum_iters = gate_vacuum.get(gid, set())

        # "Effective engagement" = the gate either ran (cage_engagement.ok=true)
        # OR produced a verdict file (which means the dispatcher was invoked,
        # even if cage_engagement marked it refused). This is the load-bearing
        # signal for the form_str-key-bug class: the dispatcher writes a
        # vacuum file the gate would never have written if it had been
        # genuinely refused upstream.
        effective_engage = engage_iters | verdict_iters
        n_eng = len(effective_engage)
        n_flag = len(flag_iters)
        n_vac = len(vacuum_iters)
        engage_rate = (n_eng / n_cage) if n_cage else 0.0
        flag_rate = (n_flag / n_eng) if n_eng else 0.0
        vacuum_rate = (n_vac / n_eng) if n_eng else 0.0
        has_verdict_source = gid in GATES_WITH_VERDICT_SOURCE

        # flag-correlates-with-cap: of the iters where gate flagged, how many were capped?
        if flag_iters and capped_iters:
            corr_n = len(flag_iters & capped_iters)
            corr_pct = corr_n / max(len(flag_iters), 1)
        else:
            corr_pct = None

        # Categorise.
        category = "OK"
        note = ""

        if n_cage and n_eng == 0:
            # Never engaged AND no verdict file ever written.
            reasons = [r for _, r in gate_refused_with_reason.get(gid, [])]
            if any("harness" in r.lower() or "gate_harness" in r.lower() for r in reasons):
                category = "HARNESS-GAP"
                note = "gate refused due to missing harness output"
            elif gid.startswith(("R10", "R11")) and not harness_present:
                category = "HARNESS-GAP"
                note = "gate_harness_result.json absent; not a gate bug"
            else:
                category = "INACTIVE"
                note = reasons[0][:120] if reasons else "gate scope did not include this run"

        elif has_verdict_source and engage_rate >= engage_threshold and n_flag == 0 and cap_rate >= 0.5:
            category = "HIGH-RISK"
            if n_vac > 0:
                note = (
                    f"verdict file exists on {n_vac}/{n_eng} iters with vacuum content "
                    f"(no constants/forms scanned) -- form_str-key-bug fingerprint"
                )
            else:
                note = (
                    "engages but never flags and run is mostly capped -- "
                    "scope mismatch / dispatcher reads wrong key"
                )

        elif has_verdict_source and engage_rate >= engage_threshold and flag_rate < 0.05 and corr_pct is not None and corr_pct < 0.5:
            category = "SUSPICIOUS"
            note = (
                f"engages {engage_rate:.0%} but flags only {flag_rate:.0%}, "
                f"and flags do not correlate with score caps ({corr_pct:.0%})"
            )

        elif has_verdict_source and engage_rate >= engage_threshold and n_flag > 0:
            if corr_pct is not None and corr_pct >= 0.5:
                category = "HEALTHY"
                note = "flags correlate with capped iters"
            else:
                category = "OK"
                note = f"engages and flags ({n_flag}/{n_eng}); cap-correlation n/a or weak"

        elif not has_verdict_source and engage_rate >= engage_threshold:
            # Gate engages but its verdict is emitted inline (eval_history.gate_verdicts)
            # or nowhere we can read. Cannot judge effectiveness from filesystem alone.
            category = "NO-VERDICT-SOURCE"
            note = "gate engages; verdict not in workspace files (likely inline in eval_history)"

        # Special: vacuum verdicts even when not high-risk overall (e.g. low cap-rate)
        # are still a smell. Demote to SUSPICIOUS-ish-but-flag-it:
        if category not in ("HIGH-RISK",) and n_vac > 0 and n_flag == 0 and has_verdict_source:
            category = "SUSPICIOUS"
            note = (
                f"{n_vac} vacuum verdict(s) written (n_constants_scanned=0); "
                f"dispatcher invoked but found nothing to scan"
            )

        findings.append(
            {
                "gate": gid,
                "engage_pct": engage_rate,
                "flag_pct": flag_rate,
                "vacuum_pct": vacuum_rate,
                "engage_iters": sorted(engage_iters),
                "verdict_iters": sorted(verdict_iters),
                "flag_iters": sorted(flag_iters),
                "vacuum_iters": sorted(vacuum_iters),
                "flag_correlates_with_cap": corr_pct,
                "has_verdict_source": has_verdict_source,
                "category": category,
                "note": note,
            }
        )

    return {
        "label": label,
        "iters": iters,
        "n_eval": n_eval,
        "capped": len(capped_iters),
        "cap_rate": cap_rate,
        "champion": champion,
        "harness_present": harness_present,
        "findings": findings,
    }


# ---- reporting ----------------------------------------------------------
CATEGORY_ORDER = ("HIGH-RISK", "SUSPICIOUS", "HARNESS-GAP", "HEALTHY", "OK", "NO-VERDICT-SOURCE", "INACTIVE")


def _fmt_pct(x: float | None) -> str:
    if x is None:
        return " n/a"
    return f"{x*100:4.0f}%"


def print_human(reports: list[dict], *, verbose: bool = False) -> None:
    totals: dict[str, int] = defaultdict(int)
    quiet_cats = {"OK", "INACTIVE", "NO-VERDICT-SOURCE"} if not verbose else set()
    interesting_per_project: dict[str, int] = {}
    for rep in reports:
        if not rep["findings"]:
            continue
        # Sort findings into categories.
        by_cat: dict[str, list[dict]] = defaultdict(list)
        for f in rep["findings"]:
            by_cat[f["category"]].append(f)
            totals[f["category"]] += 1
        # Decide whether to print this project at all (verbose: yes; non-verbose: only if there's an interesting finding).
        interesting = sum(len(by_cat.get(c, [])) for c in CATEGORY_ORDER if c not in quiet_cats)
        interesting_per_project[rep["label"]] = interesting
        if not verbose and interesting == 0:
            continue
        print(f"== {rep['label']} ==")
        ev = rep["n_eval"]
        capped = rep["capped"]
        ch = rep["champion"]
        cap_pct = (capped / ev * 100) if ev else 0.0
        ch_str = f"{ch:.0f}" if isinstance(ch, (int, float)) else "n/a"
        print(
            f"  iters: {rep['iters']}, capped (score<70): {capped}/{ev} "
            f"({cap_pct:.0f}%), champion: {ch_str}, harness_present={rep['harness_present']}"
        )
        for cat in CATEGORY_ORDER:
            if cat in quiet_cats:
                continue
            for f in sorted(by_cat.get(cat, []), key=lambda x: x["gate"]):
                gate = f["gate"]
                print(
                    f"    {gate:<36s} | engage={_fmt_pct(f['engage_pct'])} | "
                    f"flag={_fmt_pct(f['flag_pct'])} | "
                    f"corr={_fmt_pct(f['flag_correlates_with_cap'])} | "
                    f"{cat}"
                )
                if f["note"]:
                    print(f"        -> {f['note']}")
                if f["vacuum_iters"]:
                    print(f"        -> vacuum verdicts on iters: {f['vacuum_iters']}")
        # Show one-line summary of suppressed categories so the operator
        # knows we looked.
        suppressed = sum(len(by_cat.get(c, [])) for c in quiet_cats)
        if suppressed:
            cnt = ", ".join(f"{c}={len(by_cat.get(c, []))}" for c in CATEGORY_ORDER if c in quiet_cats and by_cat.get(c))
            print(f"    [suppressed: {cnt}]")
        print()
    print("== aggregate (per-gate row counts, all projects) ==")
    for cat in CATEGORY_ORDER:
        if totals[cat]:
            print(f"  {cat:<18s} {totals[cat]}")


def print_json(reports: list[dict]) -> None:
    print(json.dumps(reports, indent=2, sort_keys=True, default=str))


def collect_high_risk(reports: list[dict]) -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []
    for rep in reports:
        for f in rep["findings"]:
            if f["category"] == "HIGH-RISK":
                out.append((rep["label"], f["gate"], f["note"]))
    return out


# ---- entry point --------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[3]))
    ap.add_argument("--strict", action="store_true", help="exit 1 if any HIGH-RISK pattern found")
    ap.add_argument("--json", dest="emit_json", action="store_true", help="emit JSON instead of human-readable text")
    ap.add_argument("--cap-score-threshold", type=float, default=70.0, help="score < this is 'capped' (default 70)")
    ap.add_argument("--engage-threshold", type=float, default=0.7, help="engage rate threshold for risk classes (default 0.7)")
    ap.add_argument("--project", action="append", default=[], help="restrict to one project (repeatable, matches by prefix)")
    ap.add_argument("--include-archives", action="store_true", default=True, help="include archived/frozen workspaces (default: on; this is where historical bugs live)")
    ap.add_argument("--no-archives", dest="include_archives", action="store_false")
    ap.add_argument("--verbose", "-v", action="store_true", help="show INACTIVE / NO-VERDICT-SOURCE / OK rows too")
    args = ap.parse_args()

    root = Path(args.root)
    projects_root = root / "projects"
    if not projects_root.is_dir():
        print(f"ERROR: {projects_root} not found", file=sys.stderr)
        return 2

    workspaces = discover_workspaces(projects_root)
    if not args.include_archives:
        workspaces = [(lab, ws) for lab, ws in workspaces if "::" not in lab]
    if args.project:
        workspaces = [(lab, ws) for lab, ws in workspaces if any(lab.split("::", 1)[0].startswith(p) for p in args.project)]

    reports: list[dict] = []
    for label, ws in workspaces:
        try:
            rep = analyse_workspace(label, ws, cap_threshold=args.cap_score_threshold, engage_threshold=args.engage_threshold)
            reports.append(rep)
        except Exception as exc:  # noqa: BLE001 - audit must be robust
            reports.append({"label": label, "iters": 0, "n_eval": 0, "capped": 0, "cap_rate": 0.0, "champion": None, "harness_present": False, "findings": [{"gate": "<audit_error>", "engage_pct": 0, "flag_pct": 0, "engage_iters": [], "flag_iters": [], "vacuum_iters": [], "flag_correlates_with_cap": None, "category": "OK", "note": f"audit error: {exc}"}]})

    if args.emit_json:
        print_json(reports)
    else:
        print_human(reports, verbose=args.verbose)

    high_risk = collect_high_risk(reports)
    if not args.emit_json:
        if high_risk:
            print()
            print("== HIGH-RISK summary ==")
            for label, gate, note in high_risk:
                print(f"  {label}::{gate}  -> {note}")
        else:
            print()
            print("No HIGH-RISK gate-effectiveness findings.")

    return 1 if (high_risk and args.strict) else 0


if __name__ == "__main__":
    sys.exit(main())
