#!/usr/bin/env python3
"""gp225_audit.py — the productized Path-B harness interface.

"Package the minimum useful harness" (GPT-5.5 bundle roadmap). This is a
THIN COMPOSITION of already-validated primitives — it adds NO new
detectors:
  - v33_preflight_risk_detector.detect_risks   (vacuity/single-exact/...)
  - ns_governance_gate.adjudicate              (target_kind + mush block)
  - residual_to_lever.classify                 (kernel residual->lever map)

Given a claimed proof/closure/route/gap it emits ONE report:
  target_kind, governance_verdict, anti_pattern_flags, residual_class,
  next_lever, next_target, scoreboard.

Strict two-scoreboard: a closure counts ZERO until it is v33-clean AND
residual_to_lever returns none_closed AND xpanel+operator-inversion
ratifies (forward_evidence). This tool only AUDITS; it never ratifies.

Usage:
  gp225_audit.py --statement "<lean stmt>"            # quick anti-pattern + residual read
  gp225_audit.py --dispatch-json /tmp/er_*.json       # audit a route_c outcome
  gp225_audit.py --claim "<text>" --ns-kind expose_consequence --evidence <path>
"""
from __future__ import annotations
import argparse, importlib.util, json, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CTL = REPO / "scripts/public/control"


def _load(mod: str):
    spec = importlib.util.spec_from_file_location(mod, CTL / f"{mod}.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules[mod] = m
    spec.loader.exec_module(m)  # type: ignore[attr-defined]
    return m


def audit(args) -> dict:
    flags: list[str] = []
    target_kind = None
    gov_verdict = "pending"
    record: dict = {}

    # 1. anti-pattern flags (deterministic v33 preflight)
    if args.statement:
        try:
            v33 = _load("v33_preflight_risk_detector")
            r = v33.detect_risks(args.statement)
            flags += list(r.get("risk_flags", []))
            record["risk_flags"] = flags
            if r.get("vacuity_suspected"):
                gov_verdict = "killed"
        except Exception as e:
            flags.append(f"v33_degraded:{e}")

    # 2. target_kind + mush governance (ns_governance_gate) when ns-kind given
    if args.ns_kind and args.evidence:
        try:
            ng = _load("ns_governance_gate")
            a = ng.adjudicate(args.claim or args.statement or "", args.ns_kind,
                              args.evidence, args.lean)
            target_kind = a.get("target_kind")
            if a.get("verdict") == "BLOCK":
                gov_verdict = "killed"
                flags += [f"mush_block:{b[:60]}" for b in a.get("blocks", [])]
            record["target_kind"] = target_kind
        except Exception as e:
            flags.append(f"ns_gate_degraded:{e}")

    # 3. residual -> lever (kernel-owned map) on a dispatch outcome
    if args.dispatch_json:
        rec = json.loads(Path(args.dispatch_json).read_text())
        rec.setdefault("_src", args.dispatch_json)
        try:
            rl = _load("residual_to_lever")
            lever = rl.classify(rec)
        except Exception as e:
            lever = {"residual_class": "apparatus_or_source_mismatch",
                     "next_lever": "fix_replay_import_context",
                     "next_target_statement": f"residual_to_lever degraded: {e}"}
        target_kind = target_kind or rec.get("target_kind")
        flags += list(rec.get("v33_organ_flags", []))
    else:
        rl = _load("residual_to_lever")
        lever = rl.classify(record)

    # governance verdict roll-up (audit-only; never ratifies)
    if gov_verdict != "killed":
        rc = lever["residual_class"]
        gov_verdict = {"none_closed": "pending_ratification",
                       "theorem_or_pde_gap": "gap_isolated",
                       "gate_contract_not_crisp": "weakened",
                       "vocabulary_gap": "pending_operator_review",
                       "new_channel_or_residual_measure_needed": "pending_operator_review",
                       "apparatus_or_source_mismatch": "apparatus_fix_needed"
                       }.get(rc, "pending")

    return {
        "tool": "gp225_audit",
        "target_kind": target_kind,
        "governance_verdict": gov_verdict,
        "anti_pattern_flags": sorted(set(flags)),
        "residual_class": lever["residual_class"],
        "next_lever": lever["next_lever"],
        "next_target_statement": lever["next_target_statement"],
        "scoreboard": ("GOVERNANCE audit only — NOT a closure. A closure "
                       "counts zero until v33-clean AND residual=none_closed "
                       "AND xpanel+operator_inversion ratified. Two scoreboards "
                       "never merge."),
        "evidence_pointer": args.evidence or args.dispatch_json or args.statement,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--statement")
    ap.add_argument("--dispatch-json")
    ap.add_argument("--claim")
    ap.add_argument("--ns-kind")
    ap.add_argument("--evidence")
    ap.add_argument("--lean")
    a = ap.parse_args()
    if not (a.statement or a.dispatch_json or a.claim):
        print("need --statement | --dispatch-json | --claim", file=sys.stderr)
        return 2
    print(json.dumps(audit(a), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
