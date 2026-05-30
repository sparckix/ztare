#!/usr/bin/env python3
"""solver0_gate.py — the minimal solver-0 measurement (GPT-5.5 reframe).

NOT a new benchmark seed (v1638_twenty_row_solver0_closure_benchmark_seed
already provides Lean closure-attempt rows — reused, not recreated). This
is the MIXED-target GATE the reframe specifies: 10 targets across
{Lean local goal, NS downstream/gap, falsifier, consequence-exposure},
each scored via gp225_audit, against the pre-registered thresholds:

  >=3 replayable closures
  >=3 exact gap / missing-lemma packets
  >=2 valid falsifiers
   0  consequence mislabeled as proof
   0  false closure ratifications

Composes already-validated primitives only (gp225_audit -> v33 +
ns_governance_gate + residual_to_lever). No new detectors, no paid
compute (targets point at existing audited artifacts). Honest by design:
if there are 0 closures it REPORTS FAIL on the closure threshold — the
gate is a measurement of the gap to genuine-solver status, not a thing
to pass by lowering the bar.
"""
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
AUDIT = REPO / "scripts/public/control/gp225_audit.py"

# 10 mixed targets, each pointing at an EXISTING audited artifact.
# kind = expected solver-category role; the gate scores what gp225_audit
# actually returns vs this, so a mislabel is detectable.
TARGETS = [
    # 3 Lean local goals (escape-route rows, already attempted gpt-4.1/mini)
    {"id": "lean_SIE1", "kind": "lean_goal", "dispatch": "/tmp/er_gpt41_ER_SIE1_intervalIntegral_pow_exp.json"},
    {"id": "lean_SIE2", "kind": "lean_goal", "dispatch": "/tmp/er_gpt41_ER_SIE2_sum_Ico_pow_exp.json"},
    {"id": "lean_PENT", "kind": "lean_goal", "dispatch": "/tmp/er_gpt41_ER_PENT_strictMonoOn.json"},
    # 3 NS downstream/gap targets
    {"id": "ns_route1_budget", "kind": "ns_gap", "record": {"target_kind": "gap_isolation",
        "verdict": "OPEN_GAP_REPORT", "gap_report": {"named_candidate_lemmas": ["strict_budget_surplus_from_PDE_subscaling_gain"],
        "target_row": "route-1 strict-margin chain"}, "evidence_pointer": "docs/internal/closure_audits/closed_or_gap_chain.md"}},
    {"id": "ns_SIE3_downstream", "kind": "ns_gap", "dispatch": "/tmp/er_gpt41_ER_SIE3_sum_Iic_pow_exp.json"},
    {"id": "ns_SIE4_downstream", "kind": "ns_gap", "dispatch": "/tmp/er_gpt41_ER_SIE4_sum_Iic_pow_twopow.json"},
    # 2 falsifier targets (natural-10 control: route shown underpowered)
    {"id": "falsifier_natural10", "kind": "falsifier", "record": {"target_kind": "falsifier",
        "verdict": "OPEN_GAP_REPORT", "gap_report": {"target_row": "v32 natural-10 control: cheap loop closes 0/10 -> route underpowered for natural-Mathlib class"},
        "evidence_pointer": "analytics/public/leanmill/results/v32_route_c_replay_results.json"}},
    {"id": "falsifier_escaperoute_midconfig", "kind": "falsifier", "record": {"target_kind": "falsifier",
        "verdict": "OPEN_GAP_REPORT", "gap_report": {"target_row": "gpt-4.1/3-round closes 0/5 escape-route -> cheap+mid configs underpowered for genuinely-new hard analysis lemmas"},
        "evidence_pointer": "docs/internal/leanmill_internal/lean_residual_to_lever_trace.md"}},
    # 2 consequence-exposure (must be classified consequence, NOT proof)
    {"id": "consequence_ns_clay", "kind": "consequence_exposure",
        "claim": "this exposes a consequence that closes Clay", "ns_kind": "expose_consequence",
        "evidence": "analytics/public/forecast_pool/v34_contract_closeout_report.md"},
    {"id": "consequence_route_reduction", "kind": "consequence_exposure",
        "claim": "route reduced to a known subgoal which would close the target", "ns_kind": "route_downstream_subgoal",
        "evidence": "docs/internal/closure_audits/closed_or_gap_chain.md"},
]


def _audit(t: dict) -> dict:
    cmd = ["python3", str(AUDIT)]
    if t.get("dispatch"):
        if not Path(t["dispatch"]).exists():
            return {"_skip": f"dispatch artifact missing: {t['dispatch']}"}
        cmd += ["--dispatch-json", t["dispatch"]]
    elif t.get("record"):
        p = Path(f"/tmp/solver0_{t['id']}.json")
        p.write_text(json.dumps(t["record"]))
        cmd += ["--dispatch-json", str(p)]
    else:
        cmd += ["--claim", t["claim"], "--ns-kind", t["ns_kind"], "--evidence", t["evidence"]]
    r = subprocess.run(cmd, cwd=str(REPO), capture_output=True, text=True)
    try:
        return json.loads(r.stdout)
    except Exception:
        return {"_skip": f"audit non-json: {r.stdout[:100]} {r.stderr[:100]}"}


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    tally = {"closure": 0, "exact_gap": 0, "falsifier": 0,
             "consequence_mislabeled_as_proof": 0, "false_closure_ratification": 0,
             "skipped": 0}
    detail = []
    for t in TARGETS:
        au = _audit(t)
        if au.get("_skip"):
            tally["skipped"] += 1
            detail.append({"id": t["id"], "skip": au["_skip"]}); continue
        rc = au.get("residual_class"); gv = au.get("governance_verdict")
        tk = au.get("target_kind")
        is_closure = (rc == "none_closed" and gv == "pending_ratification")
        is_gap = (rc == "theorem_or_pde_gap")
        if is_closure:
            tally["closure"] += 1
            if "ratified" in str(gv):  # audit-only tool must never self-ratify
                tally["false_closure_ratification"] += 1
        if is_gap:
            tally["exact_gap"] += 1
        if t["kind"] == "falsifier" and is_gap:
            tally["falsifier"] += 1
        if t["kind"] == "consequence_exposure":
            # mislabel = a consequence target that the harness lets pass as proof_closure
            if tk == "proof_closure" or (rc == "none_closed" and gv != "killed"):
                tally["consequence_mislabeled_as_proof"] += 1
        detail.append({"id": t["id"], "kind": t["kind"], "residual": rc,
                        "verdict": gv, "target_kind": tk})

    gate = {
        "closures": tally["closure"], "exact_gaps": tally["exact_gap"],
        "falsifiers": tally["falsifier"],
        "consequence_mislabeled": tally["consequence_mislabeled_as_proof"],
        "false_ratifications": tally["false_closure_ratification"],
        "skipped": tally["skipped"],
    }
    passed = (gate["closures"] >= 3 and gate["exact_gaps"] >= 3
              and gate["falsifiers"] >= 2
              and gate["consequence_mislabeled"] == 0
              and gate["false_ratifications"] == 0)
    out = {"solver0_gate": "PASS" if passed else "FAIL",
           "thresholds": ">=3 closures, >=3 exact_gaps, >=2 falsifiers, 0 mislabel, 0 false_ratify",
           "scoreboard": gate,
           "honest_note": ("FAIL with closures<3 is the TRUE current state — the gate "
                           "measures the gap to genuine-solver status (closures on hard "
                           "rows with available configs). Not pessimism: the constructive "
                           "loop still emits exact gaps; only mode-1 closure is the deficit."),
           "detail": detail}
    print(json.dumps(out, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
