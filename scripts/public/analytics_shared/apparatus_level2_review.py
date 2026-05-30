"""Level 2 — Apparatus-on-apparatus meta-review with mandatory falsifier tests.

The Level 0 / Level 1 / Level 2 hierarchy of cognitive-gym primitives:

  Level 0 (inner):   inverter_agent / compress_champion / margin_of_safety
                     operate on per-iter champions inside autoresearch_loop
  Level 1 (outer):   cognitive_gym_hooks operate on closure attempts,
                     F-rows, paper drafts — meta-artifacts the inner
                     primitives don't reach
  Level 2 (meta):    THIS module — operates on the APPARATUS ITSELF.
                     Tests ZTARE's claims about its own utility by
                     running ablation / hindsight / control experiments

# The danger of Level 2: apparatus narcissism

Most "meta-review" code degenerates into self-congratulatory or self-
negating prose. To avoid this, every Level 2 finding MUST come with:
  - A specific apparatus claim being tested (e.g. "typed-endpoint pack
    increases verified-patch rate")
  - A concrete falsifier experiment (e.g. "compare last 10 closed
    obligations attempted with vs without typed-endpoint")
  - The data the experiment requires (where to look, what to count)

A finding without a falsifier test is suppressed. The output is a
"claim → falsifier test" backlog Codex can run.

# What Level 2 reads (the apparatus's own records)

  - `projects/ns_millennium_hunt/workspace/queries/typed_endpoint_failure_log.jsonl`
  - `analytics/public/queries/novelty/codex_nomination_panel.csv` (Codex-marked verdicts)
  - `analytics/public/queries/reflexive/closure_utility_metric.json`
  - `projects/ns_millennium_hunt/workspace/queries/missing_primitives_backlog.md`
  - `analytics/public/queries/audits/failure_clusters.md`
  - `research_areas/EXPERIMENT_TRACK_RECORD.md` F-rows
  - `org/mandates/research_director_mandate.md` (its own claims)

# What Level 2 writes

  `analytics/public/queries/audits/apparatus_level2_review.md` — structured backlog of
  (apparatus_claim, falsifier_test, required_data, predicted_outcome).

# Honest scope

  - This is a SCAFFOLD that surfaces FALSIFIER DESIGNS. It does NOT
    run the falsifiers itself. Codex / RD chooses which to actually run.
  - The strange loop is real: this script's OWN claim of utility could
    be tested by Level 2 (does the falsifier-test backlog actually get
    consumed and acted on?). That recursion ends here; we don't ship
    Level 3.

Usage:
    python scripts/public/analytics_shared/apparatus_level2_review.py
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]
# ---------------------------------------------------------------------------
# Apparatus claims that warrant Level 2 review
#
# Each is a concrete claim ZTARE makes about its own utility. For each, the
# code below generates a falsifier-test design.
# ---------------------------------------------------------------------------

APPARATUS_CLAIMS = [
    {
        "id": "claim_typed_endpoint_helps",
        "claim": ("The typed-endpoint pack increases the verified-patch "
                   "rate vs. cold LLM nomination."),
        "data_required": ["typed_endpoint_failure_log.jsonl",
                          "Codex-marked panel CSV (pre-typed-endpoint era)"],
        "falsifier_design": (
            "Take the last 20 closure attempts. Split by whether they "
            "used typed-endpoint pack. Compare VERIFIED-rate. If "
            "typed-endpoint-rate ≤ cold-LLM-rate (within 1 SE), claim is "
            "false."
        ),
        "predicted_outcome_if_true": "typed-endpoint VERIFIED-rate ≥ 2x cold-LLM",
        "predicted_outcome_if_false": "rates within noise; typed-endpoint is theater",
    },
    {
        "id": "claim_lemma_scout_helps",
        "claim": ("The mathlib_lemma_scout's PDE-shape index "
                   "(SOBOLEV / HOLDER / etc.) actually surfaces lemmas "
                   "Codex would have missed."),
        "data_required": [
            "list of mathlib lemmas surfaced via scout in last N runs",
            "Codex's pre-scout vocabulary (which lemmas he'd cite spontaneously)",
        ],
        "falsifier_design": (
            "Sample 10 verified patches Codex shipped this week. For each, "
            "ask: did the scout surface the actual lemma used? If hit-rate "
            "≤ 20%, the index is too coarse to be useful."
        ),
        "predicted_outcome_if_true": "scout hit-rate ≥ 50% on real verifications",
        "predicted_outcome_if_false": "hit-rate ≤ 20%; scout is decorative",
    },
    {
        "id": "claim_v3_gnn_predicts_real",
        "claim": ("The v3 GNN lemma-relevance ranker (hit@10 = 0.379 on "
                   "spine-only test set) generalizes to mathlib lemmas Codex "
                   "actually uses in production."),
        "data_required": [
            "v3 ranker checkpoint",
            "list of lemmas used in last N Codex-shipped patches",
        ],
        "falsifier_design": (
            "Take the last 20 verified-patch lemma references. For each, "
            "see if the v3 ranker would have surfaced it in top-10. "
            "If hit-rate < 0.20 (vs claimed 0.38), there's a "
            "spine→production distribution shift that invalidates the "
            "metric."
        ),
        "predicted_outcome_if_true": "production hit@10 ≥ 0.30 (mild degradation)",
        "predicted_outcome_if_false": "production hit@10 ≤ 0.10; spine eval was overfit"
    },
    {
        "id": "claim_idea_feliz_better_than_novelty",
        "claim": ("Idea-feliz produces actionable insights at a higher rate "
                   "than the deprecated novelty-nomination prompt (0/22)."),
        "data_required": [
            "Codex-marked CSV with idea-feliz verdicts",
            "the 0/22 baseline from novelty-nomination Codex panel",
        ],
        "falsifier_design": (
            "Score Codex's idea-feliz panel using the same vocabulary as the "
            "novelty panel (already_have | novel_plausible | wrong | trivial). "
            "If idea-feliz novelty_rate ≤ 5% (matching novelty-prompt floor), "
            "claim is false; the apparatus shifted the slogan, not the substance."
        ),
        "predicted_outcome_if_true": "idea-feliz novelty_rate ≥ 30%",
        "predicted_outcome_if_false": "novelty_rate < 5% — same theater, new costume",
    },
    {
        "id": "claim_failure_log_compounds",
        "claim": ("Stage 4 failure-category accumulator changes apparatus "
                   "behavior over time (later runs avoid earlier failure modes)."),
        "data_required": [
            "typed_endpoint_failure_log.jsonl with timestamps",
        ],
        "falsifier_design": (
            "Bin failures by week. Check if the SAME (target, field, "
            "patch_class) triple's failure category SHIFTS over weeks. If "
            "the same triple keeps failing in the same category, the "
            "accumulator does NOT compound — it's just a write-only log."
        ),
        "predicted_outcome_if_true": "failure-category distribution shifts week-over-week",
        "predicted_outcome_if_false": "static distribution; log is bookkeeping not learning",
    },
    {
        "id": "claim_constraint_basin_is_accountant",
        "claim": ("The constraint-basin graph diagnostics are 5-10x as a "
                   "proof-spine accountant per Codex's 2026-05-05 verdict."),
        "data_required": [
            "Codex's stated belief updates from constraint-basin runs",
            "concrete actions taken on those updates (Lean patches, "
            "rubric edits)",
        ],
        "falsifier_design": (
            "List every belief update Codex attributed to constraint-basin "
            "diagnostics in advisor_channel.md / F-rows. Count: how many "
            "led to a CONCRETE downstream action (Lean patch / rubric edit "
            "/ scoping decision)? If <30%, the diagnostics are scout-only "
            "(1-2x), not accountant (5-10x)."
        ),
        "predicted_outcome_if_true": "≥30% of belief updates produce concrete actions",
        "predicted_outcome_if_false": "scout signal that doesn't compound to action",
    },
    {
        "id": "claim_negative_prompting_expands_method_space",
        "claim": ("negative_prompting_wrapper.py surfaces genuinely different "
                   "methods after typed-endpoint / gap-typed attempts stall."),
        "data_required": [
            "analytics/public/queries/negative_prompting_runs/*.json",
            "Codex verdicts on whether each method was already considered",
            "downstream typed-endpoint / Lean / falsifier attempts spawned by "
            "those methods",
        ],
        "falsifier_design": (
            "Sample the last 10 negative-prompting runs. Mark every method as "
            "already_considered | distinct_but_unusable | distinct_and_used. "
            "If <20% of runs produce at least one distinct_and_used method, "
            "the wrapper is not a closure tool; it is just brainstorming."
        ),
        "predicted_outcome_if_true": "≥20% of runs spawn a concrete typed attempt or falsifier",
        "predicted_outcome_if_false": "methods are paraphrases or too vague to translate",
    },
    {
        "id": "claim_context_deidentifier_reduces_refusal",
        "claim": ("context_deidentifier.py's auto-retry inside typed_endpoint_pack "
                   "reduces open-problem/conjecture refusal failures without "
                   "changing the mathematical content."),
        "data_required": [
            "typed_endpoint_failure_log.jsonl refusal entries",
            "typed_endpoint_runs/*_deidentified_response.md",
            "audit diff from context_deidentifier.py for each retry",
        ],
        "falsifier_design": (
            "For every auto-deidentified retry, check whether the first response "
            "was an open-problem refusal and the retry produced a parseable Lean "
            "block or sharper CANNOT PATCH diagnosis. If success-rate ≤10% or "
            "the diff strips load-bearing assumptions, the tool is not useful "
            "for closure work."
        ),
        "predicted_outcome_if_true": "refusal-to-actionable rate ≥25% with no assumption loss",
        "predicted_outcome_if_false": "retry keeps refusing or deidentification corrupts context",
    },
    {
        "id": "claim_theory_builder_pivot_beats_estimate_chaining",
        "claim": ("When PDE estimate chaining stalls, a theory-builder pivot "
                   "(new object / relaxed carrier / falsifier-first reframing) "
                   "produces more closure progress than adding another local "
                   "inequality adapter."),
        "data_required": [
            "closure attempts tagged ps_06 estimate-chaining vs. tb_01/tb_08 "
            "object-redefinition",
            "Lean patches or explicit falsifiers produced after each tag",
            "graph/workmap delta after the attempt",
        ],
        "falsifier_design": (
            "Compare the next 10 stalled PDE targets after the pivot rule is in "
            "the mandate. If theory-builder turns do not produce either a typed "
            "source object, a new Lean constructor, or a concrete falsifier at a "
            "higher rate than estimate-adapter turns, demote the pivot rule to "
            "advisory rhetoric."
        ),
        "predicted_outcome_if_true": "object/falsifier turns produce ≥2x actionable artifacts",
        "predicted_outcome_if_false": "no artifact-rate lift; pivot language is theater",
    },
    {
        "id": "claim_pde_preflight_cuts_lean_debug_time",
        "claim": ("Deterministic PDE estimate preflight "
                   "(dimensional/endpoint gate + SymPy/asymptotic algebra + "
                   "small Fourier/numeric falsifier when relevant) catches bad "
                   "estimate narratives before Lean and improves time-to-useful "
                   "signal."),
        "data_required": [
            "projects/ns_millennium_hunt/workspace/queries/pde_workbench/*.json",
            "research_areas/EXPERIMENT_TRACK_RECORD.md E/F rows tagged PDE preflight",
            "Lean compile/failure logs for estimates attempted with vs without preflight",
        ],
        "falsifier_design": (
            "For the next 10 PDE-estimate attempts, tag whether preflight ran "
            "before Lean. Count (a) narratives killed by failed units/asymptotics, "
            "(b) Lean failures avoided, and (c) verified/source-constructor "
            "patches reached. If preflight does not kill at least one bad "
            "narrative or reduce repeated Lean-debug failures, demote it to an "
            "optional sanity check."
        ),
        "predicted_outcome_if_true": "≥1 bad narrative killed and fewer repeated Lean-debug failures",
        "predicted_outcome_if_false": "preflight adds delay without changing patch/falsifier outcomes",
    },
]


# ---------------------------------------------------------------------------
# Output rendering
# ---------------------------------------------------------------------------

def render_review(claims: list[dict], aux_data: dict) -> str:
    lines = [
        "# Apparatus Level 2 Review — claim × falsifier-test backlog",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Frame",
        "",
        "This document is the strange-loop / Level 2 layer applying "
        "invert/compress/disagree to ZTARE's claims about ITSELF. Every "
        "row below is a concrete claim the apparatus makes plus a "
        "falsifier-test Codex can run. **A claim without a runnable "
        "falsifier is suppressed.**",
        "",
        "## Auxiliary data summary",
        "",
    ]
    for k, v in aux_data.items():
        lines.append(f"- {k}: {v}")
    lines.extend(["", f"## Backlog ({len(claims)} apparatus claims)", ""])
    for i, c in enumerate(claims, 1):
        lines.append(f"### {i}. {c['id']}")
        lines.append("")
        lines.append(f"**Claim:** {c['claim']}")
        lines.append("")
        lines.append("**Falsifier design:**")
        lines.append("")
        lines.append(f"> {c['falsifier_design']}")
        lines.append("")
        lines.append(f"**Data required:**")
        for d in c["data_required"]:
            lines.append(f"  - {d}")
        lines.append("")
        lines.append(f"**Predicted outcome if claim is TRUE:** {c['predicted_outcome_if_true']}")
        lines.append("")
        lines.append(f"**Predicted outcome if claim is FALSE:** {c['predicted_outcome_if_false']}")
        lines.append("")
        lines.append(f"**Codex action:** mark this claim with one of:")
        lines.append(f"  - `not_yet_tested` — falsifier not yet run")
        lines.append(f"  - `confirmed` — falsifier ran, claim survived")
        lines.append(f"  - `refuted` — falsifier ran, claim failed; remove from mandate")
        lines.append(f"  - `untestable` — claim too vague to run as written; rephrase")
        lines.append("")
        lines.append("---")
        lines.append("")
    lines.append("## Honest scope of THIS document")
    lines.append("")
    lines.append("- These are SCAFFOLDS. None of these falsifiers has been "
                  "run yet by this script.")
    lines.append("- The strange-loop recursion ends here: we don't ship "
                  "Level 3 (apparatus testing the apparatus testing the apparatus).")
    lines.append("- This file should be regenerated whenever the mandate "
                  "adds a new apparatus claim (e.g. via "
                  "`research_director_mandate.md` v1.2x updates).")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Aux data loaders
# ---------------------------------------------------------------------------

def load_aux_data() -> dict[str, Any]:
    out = {}
    log_path = (
        REPO / "projects" / "ns_millennium_hunt" / "workspace" / "queries"
        / "typed_endpoint_failure_log.jsonl"
    )
    if log_path.exists():
        rows = [l for l in log_path.read_text().splitlines() if l.strip()]
        out["failure_log_entries"] = len(rows)
    panel_path = REPO / "analytics" / "public" / "queries" / "novelty" / "codex_nomination_panel.csv"
    if panel_path.exists():
        out["codex_panel_rows"] = sum(1 for _ in panel_path.read_text().splitlines()) - 1
    metric_path = REPO / "analytics" / "public" / "queries" / "closure_utility_metric.json"
    if metric_path.exists():
        try:
            metric = json.loads(metric_path.read_text())
            out["last_known_novelty_rate"] = metric.get("aggregate_novelty_rate")
        except json.JSONDecodeError:
            pass
    backlog_path = (
        REPO / "projects" / "ns_millennium_hunt" / "workspace" / "queries"
        / "missing_primitives_backlog.md"
    )
    if backlog_path.exists():
        out["missing_primitives_backlog_size"] = backlog_path.stat().st_size
    v3_ckpt = REPO / "analytics" / "gnn" / "v3_checkpoint.pt"
    if v3_ckpt.exists():
        out["v3_checkpoint_size_kb"] = round(v3_ckpt.stat().st_size / 1024, 1)
    neg_dir = REPO / "analytics" / "public" / "queries" / "negative_prompting_runs"
    if neg_dir.exists():
        out["negative_prompting_runs"] = len(list(neg_dir.glob("*.json")))
    deid_dir = (
        REPO / "projects" / "ns_millennium_hunt" / "workspace" / "queries"
        / "typed_endpoint_runs"
    )
    if deid_dir.exists():
        out["deidentified_retry_outputs"] = len(
            list(deid_dir.glob("*_deidentified_response.md")))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path,
                    default=REPO / "analytics" / "public" / "queries" / "apparatus_level2_review.md")
    args = ap.parse_args()

    print("=== apparatus level 2 review ===")
    aux = load_aux_data()
    print(f"  aux data: {aux}")
    print(f"  apparatus claims to review: {len(APPARATUS_CLAIMS)}")
    md = render_review(APPARATUS_CLAIMS, aux)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(md)
    print(f"\nwrote {args.out}")
    print(f"\nstrange-loop note: this document tests ZTARE's claims about itself.")
    print(f"Each claim has a runnable falsifier; Codex marks each as ")
    print(f"confirmed / refuted / not_yet_tested / untestable. Recursion ")
    print(f"ends here; no Level 3.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
