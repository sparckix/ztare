#!/usr/bin/env python3
"""
predispatch_check.py — MECHANICAL pre-dispatch discipline gate.

Operator catch 2026-05-09 ~20:10 UTC (paraphrased): the apparatus was
over-indexing on a single external model and not consulting the
orchestration menu — tunnel vision, with a concern that autonomous
remote agents would inherit the same undisciplined dispatch behaviour.

Diagnosis: the apparatus has the orchestration menu + PATTERN-013
deployment ledger + diversity scorer + kernel-grep pre-mint protocol,
but the RD (and by extension VPS agents) don't ENFORCE the discipline.
Free-recall dispatch is the default; menu consultation is voluntary.

Fix: this script is a MECHANICAL GATE. Any dispatch (cold-shot or
internal agent) should pass through this check FIRST. If the
gate is bypassed, the apparatus has knowingly violated the discipline.

Usage:
  python scripts/public/control/predispatch_check.py \\
      --pattern-id PATTERN-009 \\
      --mode audit \\
      --internal-or-external internal \\
      --substrate NS-Track-B/some-question

Exit codes:
  0 — gate passed; safe to dispatch.
  1 — monoculture flag firing on the proposed pattern. Print warning.
      Exit 1 unless --override is set.
  2 — proposed pattern is in a blind-spot zone (could be useful) but
      not strictly required. Print recommendation; exit 0.
  3 — invalid args / config not found.

Behavior:
  1. Reads org/menu/orchestration_menu.yaml (if present) to surface
     recommended pattern-chain for the substrate.
  2. Runs diversity scorer (scripts/public/analytics_shared/score_pattern_deployment_diversity.py)
     internally and parses JSON output.
  3. Checks monoculture_flag + structural_blind_spots vs proposed pattern.
  4. Recommends overrides or alternatives.

Going forward: VPS agents inheriting this repo MUST run this script
before any dispatch. The repo's Makefile / CI / agent-launch wrapper
should make this gate UNBYPASSABLE without explicit operator signoff.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


# Tenant-root resolution. Promoted from figs to cognitive-firm 2026-05-10
# per operator architectural-debt directive. Reads $TENANT_ROOT env var
# (set by daemon / VPS launcher) or falls back to repo root for in-repo dev.
def _resolve_repo() -> Path:
    cwd = Path.cwd()
    if (cwd / "scripts/public/analytics_shared/score_pattern_deployment_diversity.py").exists():
        return cwd
    env = os.environ.get("TENANT_ROOT")
    if env:
        candidate = Path(env).expanduser()
        if (candidate / "scripts/public/analytics_shared/score_pattern_deployment_diversity.py").exists():
            return candidate
        print(
            f"WARNING: TENANT_ROOT={candidate} does not contain the deployment diversity scorer; "
            "falling back to this checkout.",
            file=sys.stderr,
        )
    resolved = Path(__file__).resolve()
    for parent in resolved.parents:
        if (parent / "scripts/public/analytics_shared/score_pattern_deployment_diversity.py").exists():
            return parent
    return resolved.parents[1]

REPO = _resolve_repo()
SCORER = REPO / "scripts/public/analytics_shared/score_pattern_deployment_diversity.py"
SUMMARY = REPO / "analytics/public/ledgers/pattern_deployment/pattern_deployment_diversity.json"
MENU = REPO / "org/menu/orchestration_menu.yaml"


# Menu-enforcement helpers (added 2026-05-09 ~23:50 UTC per operator catch
# "we built a catalog of patterns per use case, is that shitty or not used")
# Empirical baseline before this fix: 29/30 last deployment-ledger entries
# had pattern_id=NA, 0/30 had a menu_consulted field. Menu was 0% used.

def load_menu() -> dict:
    """Load the orchestration menu YAML; return {} if missing."""
    if not MENU.exists():
        return {}
    try:
        import yaml  # type: ignore
    except ImportError:
        print(f"WARNING: pyyaml not available; menu enforcement disabled",
              file=sys.stderr)
        return {}
    try:
        return yaml.safe_load(MENU.read_text(encoding="utf-8")) or {}
    except Exception as e:
        print(f"WARNING: menu parse failed: {e}", file=sys.stderr)
        return {}


def _clean_pattern_tokens(items) -> list[str]:
    """Strip YAML comments; keep only PATTERN-XXX / META-PATTERN-XXX tokens."""
    cleaned = []
    for item in items or []:
        if isinstance(item, str):
            tok = item.split()[0].strip()
            if tok.startswith("PATTERN-") or tok.startswith("META-PATTERN-"):
                cleaned.append(tok)
    return list(dict.fromkeys(cleaned))  # de-dupe preserving order


def recommended_patterns_for_problem_class(
    menu: dict, problem_class: str
) -> tuple[list[str], list[str]]:
    """Return (default_chain, applicable) pattern_id lists for a problem-class.

    v0.2.0 menu structure: problem_classes[<pc>].default_chain (the spine) plus
    .applicable (other patterns that declare the class — available, not default).
    Backward compat: a legacy v0.1.1 menu's sub_classes[*].chain_addition is
    folded into the `applicable` list so older menus still surface their full
    pattern set. Returns the two lists distinctly so callers can label them.
    """
    pc = (menu.get("problem_classes") or {}).get(problem_class)
    if not pc:
        return [], []
    default_chain = _clean_pattern_tokens(pc.get("default_chain"))
    applicable = list(pc.get("applicable") or [])
    for sc in (pc.get("sub_classes") or {}).values():  # legacy v0.1.1 fallback
        if isinstance(sc, dict):
            applicable.extend(sc.get("chain_addition") or [])
    applicable = _clean_pattern_tokens(applicable)
    # An applicable pattern already on the default chain is not also "extra".
    applicable = [p for p in applicable if p not in default_chain]
    return default_chain, applicable


def recommended_chain_for_problem_class(menu: dict, problem_class: str) -> list[str]:
    """Return the full surfaced pattern set for a problem-class label.

    Union of the v0.2.0 default_chain and applicable lists (and, for legacy
    menus, sub_classes' chain_addition). Order: default_chain first, then
    applicable. Use recommended_patterns_for_problem_class() when the caller
    needs the default/applicable split distinctly.
    """
    default_chain, applicable = recommended_patterns_for_problem_class(
        menu, problem_class
    )
    return list(dict.fromkeys(default_chain + applicable))


def menu_problem_classes(menu: dict) -> list[str]:
    return list((menu.get("problem_classes") or {}).keys())


def always_on_patterns(menu: dict) -> list[str]:
    """Return the menu's top-level `always_on` pattern ids.

    These are standing-discipline patterns that apply on EVERY tick
    regardless of the routed problem_class. A dispatch of one is always
    legitimate — no menu-deviation reason required.
    """
    return _clean_pattern_tokens(menu.get("always_on") or [])


def run_scorer(window: int = 15) -> dict:
    """Run diversity scorer; return parsed summary."""
    if not SCORER.exists():
        print(f"ERROR: {SCORER} not found", file=sys.stderr)
        sys.exit(3)
    result = subprocess.run(
        [sys.executable, str(SCORER), "--window", str(window)],
        capture_output=True, text=True,
    )
    if SUMMARY.exists():
        return json.loads(SUMMARY.read_text())
    print(f"ERROR: scorer didn't produce {SUMMARY}", file=sys.stderr)
    sys.exit(3)


def check_gate(args, summary: dict) -> int:
    metrics = summary.get("metrics", {})
    blind_spots = [p for p, _ in summary.get("blind_spots", [])]

    monoculture_max_pattern = metrics.get("monoculture_max_pattern")
    monoculture_max_share = metrics.get("monoculture_max_share", 0)
    monoculture_flag = metrics.get("monoculture_flag", False)

    # ── Menu-enforcement gate (added 2026-05-09 ~23:50 UTC) ─────────
    # Required: --problem-class. Loads org/menu/orchestration_menu.yaml,
    # looks up the recommended pattern chain, checks if --pattern-id is
    # on the chain. If not, refuses unless --menu-deviation-reason is
    # provided. Logs deviation reason to ledger via the dispatcher.
    menu = load_menu()
    problem_class = getattr(args, "problem_class", None)
    if menu and problem_class:
        all_classes = menu_problem_classes(menu)
        if problem_class not in all_classes:
            print(f"\n!!! UNKNOWN PROBLEM CLASS: {problem_class!r} !!!")
            print(f"    Known classes: {', '.join(all_classes)}")
            print(f"    Edit org/menu/orchestration_menu.yaml or pick "
                  f"an existing class.")
            return 4
        default_chain, applicable = recommended_patterns_for_problem_class(
            menu, problem_class
        )
        recommended = recommended_chain_for_problem_class(menu, problem_class)
        standing = always_on_patterns(menu)
        print()
        print(f"=== orchestration menu lookup ===")
        print(f"  problem_class: {problem_class}")
        print(f"  default chain: {' → '.join(default_chain) if default_chain else '(none)'}")
        print(f"  applicable (available, not default): "
              f"{', '.join(applicable) if applicable else '(none)'}")
        print(f"  always_on (standing discipline, any class): "
              f"{', '.join(standing) if standing else '(none)'}")
        # An always_on pattern is always legitimate regardless of the routed
        # class — accept it without requiring a menu-deviation reason.
        if recommended and args.pattern_id not in recommended \
                and args.pattern_id not in standing:
            print()
            print(f"!!! PATTERN-MENU MISMATCH !!!")
            print(f"    Proposed: {args.pattern_id}")
            print(f"    Recommended for {problem_class}: {recommended}")
            if args.menu_deviation_reason:
                print(f"    --menu-deviation-reason supplied: "
                      f"{args.menu_deviation_reason!r}")
                print(f"    PROCEEDING (deviation logged for audit).")
            else:
                print(f"    REFUSING dispatch unless --menu-deviation-reason "
                      f"is supplied.")
                print(f"    Either:")
                print(f"      (a) pick a pattern from the recommended chain, or")
                print(f"      (b) re-run with --menu-deviation-reason '<why "
                      f"this dispatch deviates>'.")
                return 5

    print(f"\n=== predispatch_check ===")
    print(f"  Proposed pattern: {args.pattern_id}")
    print(f"  Mode: {args.mode}")
    print(f"  Internal/external: {args.internal_or_external}")
    print(f"  Substrate: {args.substrate}")
    print()
    print(f"=== diversity state (last-{summary.get('metrics', {}).get('window', 15)} window) ===")
    for p, s in sorted(metrics.get("primary_shares", {}).items(), key=lambda kv: -kv[1]):
        print(f"  {p}: {s:.3f}")
    print(f"  monoculture_flag = {monoculture_flag} (max {monoculture_max_share} on {monoculture_max_pattern})")
    print(f"  audit_share = {metrics.get('audit_share', 0)} (in-band {metrics.get('audit_in_band', False)})")
    print(f"  external_share = {metrics.get('external_share', 0)} (in-band {metrics.get('external_in_band', False)})")
    print(f"  eigenquestion_share = {metrics.get('eigenquestion_share', 0)} (in-band {metrics.get('eigenquestion_in_band', False)})")
    print()
    print(f"=== blind spots (under-deployed patterns, last-20 share < 0.05) ===")
    for p in blind_spots:
        print(f"  {p}")

    # Gate decisions
    if monoculture_flag and args.pattern_id == monoculture_max_pattern:
        print()
        print(f"!!! MONOCULTURE FLAG FIRING on {monoculture_max_pattern} ({monoculture_max_share:.3f}) !!!")
        print(f"    Proposed dispatch deploys the same pattern.")
        print(f"    REFUSING dispatch unless --override is set.")
        print()
        print(f"    Recommended alternatives (blind spots):")
        for p in blind_spots[:5]:
            print(f"      {p}")
        print()
        if args.override:
            print(f"    --override set; proceeding despite monoculture flag.")
            print(f"    Logging override decision for audit.")
            return 0
        return 1

    if args.pattern_id in blind_spots:
        print()
        print(f"  NOTE: {args.pattern_id} is currently in blind-spot zone (under-deployed).")
        print(f"  Deploying it now is HEALTHY for diversity.")
        print()

    print()
    print(f"=== gate PASSED ===")
    print(f"  Now: pre-register PL row in analytics/public/ledgers/prediction/prediction_ledger.jsonl with conditional odds.")
    print(f"  Then: dispatch.")
    print(f"  After: log to analytics/public/ledgers/pattern_deployment/pattern_deployment_ledger.jsonl with task_id when known.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pattern-id", required=True,
                        help="Primary pattern (e.g., PATTERN-009).")
    parser.add_argument("--mode", required=True,
                        choices=["audit", "construct", "scope", "calibrate"],
                        help="Dispatch mode.")
    parser.add_argument("--internal-or-external", required=True,
                        choices=["internal", "external_via_api",
                                 "external_via_operator"],
                        help="Where the dispatch lands.")
    parser.add_argument("--substrate", required=True,
                        help="Substrate / question identifier.")
    parser.add_argument("--problem-class", required=False, default=None,
                        help="Menu problem-class label. Required for the "
                             "menu-enforcement gate to fire. Use "
                             "--list-problem-classes to enumerate. Omitting "
                             "this skips menu enforcement (exit 0 on menu "
                             "checks, but logs that the dispatcher bypassed).")
    parser.add_argument("--menu-deviation-reason", required=False, default=None,
                        help="If --pattern-id is not on the menu's recommended "
                             "chain for --problem-class, supply a reason here "
                             "to proceed with deviation logged for audit. "
                             "Refuses dispatch otherwise.")
    parser.add_argument("--list-problem-classes", action="store_true",
                        help="Print menu problem-classes and exit.")
    parser.add_argument("--window", type=int, default=15,
                        help="Diversity-scorer window (default 15).")
    parser.add_argument("--override", action="store_true",
                        help="Override monoculture-flag refusal.")
    args = parser.parse_args()

    if args.list_problem_classes:
        m = load_menu()
        for pc in menu_problem_classes(m):
            dchain, appl = recommended_patterns_for_problem_class(m, pc)
            print(f"  {pc}:")
            print(f"    default: {' → '.join(dchain) if dchain else '(none)'}")
            print(f"    applicable: {', '.join(appl) if appl else '(none)'}")
        return 0

    summary = run_scorer(window=args.window)
    return check_gate(args, summary)


if __name__ == "__main__":
    raise SystemExit(main())
