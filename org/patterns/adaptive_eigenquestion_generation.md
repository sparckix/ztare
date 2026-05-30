---
id: PATTERN-019
name: adaptive_eigenquestion_generation
version: 1
status: candidate
discovered: 2026-05-09
demoted_at: 2026-05-09T07:55:00Z
demoted_reason: |
  PL-076 audit (agent a13724f1bb8aa04db, reducer + tautology-trap on
  tonight's mintings) found this pattern's `falsifiable_test` field
  lacks a quantified baseline. Original test: "substrates where
  PATTERN-019 has been deployed at the 5-runs-1-family threshold show
  a higher rate of primitive-family rotation in subsequent runs than
  substrates where it was not deployed." The "higher" is unquantified
  — 1.01x counts as "higher" but is not central. Demoted to
  candidate confidence per PATTERN-005 falsifiable_asymmetry +
  PATTERN-006 tautology_trap_detector. Promote back to active when
  the falsifiable_test has a quantified threshold (proposal: rotation
  rate in post-deployment runs ≥ 2x rotation rate in matched-history
  control-window, with N≥5 deployment instances).
discovered_reason: |
  META-DARWIN audit on pattern architecture (2026-05-09 evening) found
  this primitive at src/ztare/research_director/eigenquestion_generator.py
  (GP-228) was missing from the catalog. Audit catch C-2026-05-09-60
  (cold-shot extraction failure) produced a sibling extraction failure
  on the same audit pass.
triggers:
  lexical: [eigenquestion, family-attractor, fixed eigenquestion, run-history]
  structural:
    - 3+ runs on same substrate converging to same primitive family
    - charter-eigenquestion is fixed but substrate has shifted
    - per-run mining outputs suggest a different residual than the charter eigenquestion
  problem_classes: [orchestration_meta_architecture, anti_anchoring]
spawn:
  mode: kernel_call
  module: src.ztare.research_director.eigenquestion_generator
  cost_per_call_usd: 0.005-0.01
  output: advisory_eigenquestion_text  # NEVER auto-modifies charter
related_patterns:
  - id: PATTERN-015
    relation: complement  # PATTERN-015 is the static 7-point checklist; this generates the dynamic eigenquestion content
  - id: PATTERN-014
    relation: feeds  # cold-shot dispatches benefit when seeded from an adaptive eigenquestion
  - id: PATTERN-013
    relation: feeds  # pattern-deployment-ledger flags monoculture; this is one structural correction
references:
  - existing kernel: src/ztare/research_director/eigenquestion_generator.py
  - GP-228 charter-critic V1+V2+preflight (project memory file project_gp226_charter_critic_status.md)
falsifiable_test: |
  Across N>=5 deployment instances at the 5-runs-1-family threshold, the
  primitive-family-rotation rate in the K=3 runs following deployment must be >=2x
  the rotation rate in a matched-history K=3-run pre-deployment control-window; the
  pattern counts as working only if >=60% of the N instances clear the 2x bar.
  Below that, demote.
  metric_source: architecture_index.jsonl + miner residual-fingerprint history
  (primitive-family-per-run), computed identically over pre- and post-deployment
  K=3 windows.
last_reviewed: 2026-05-22
review_due: 2026-06-21
review_cadence: per_campaign_summary
---

# PATTERN-019 — Adaptive Eigenquestion Generation

## What this pattern is

A **run-time eigenquestion regeneration apparatus** that breaks the
family-attractor failure mode of fixed eigenquestions. Per-run, one
LLM call (~$0.005-0.01) drafts an ADVISORY eigenquestion tailored to:

1. The substrate's most-recent mining outputs (residual-fingerprint,
   primitive-coverage, dead-route catalog).
2. The substrate's prior-run history of explored primitive classes
   (avoid re-deriving same family).

Output is **advisory only**: operator review gates promotion to
charter; never auto-modifies the eigenquestion field.

## Why static eigenquestions fail

When the charter eigenquestion is fixed but the substrate's
exploration has converged on one primitive family for ≥ 3 runs, the
fixed eigenquestion is itself the anchor causing the convergence.
PATTERN-015 (eigenquestion_phrasing_discipline) sharpens the
phrasing of any given eigenquestion; PATTERN-019 generates the
EIGENQUESTION CONTENT itself based on substrate history.

## When to deploy

* **5-runs-1-family rule**: when the primitive miner reports the same
  primitive family ≥ 5 of the last 5 runs on a substrate, fire
  PATTERN-019 to draft an alternative eigenquestion biased toward the
  underexplored primitive classes.
* **Substrate-shift signal**: when mining outputs (residual fingerprint
  at iter K) diverge structurally from the charter eigenquestion's
  framing, fire PATTERN-019 to surface the divergence as an advisory
  eigenquestion candidate.
* **Pre-cold-shot**: before a paid PATTERN-014 (cold_shot_dispatch),
  optionally run PATTERN-019 to refresh the eigenquestion content
  before the cold-shot consumes paid cross-family capacity on a stale
  question.

## Falsifiable-asymmetry test (per PATTERN-005) — REVISED 2026-05-09 per PL-076

The pattern is "working" iff:

* **Quantified threshold**: substrates where PATTERN-019 has been
  deployed at the 5-runs-1-family threshold show a primitive-family-
  rotation rate in the K=3 subsequent runs that is **≥ 2× the
  rotation rate in a matched-history K=3-run control-window taken
  pre-deployment** (or ≥ 2× a matched non-deployed substrate's
  baseline).
* **Sample size**: at least N=5 deployment instances across distinct
  substrates required before the test verdict is meaningful.
* **Empirical baseline**: pre-deployment rotation rate computed from
  `analytics/public/index/architecture_index.jsonl` + miner residual-fingerprint
  history; post-deployment rotation rate computed identically over
  the K=3 runs that follow each deployment.
* **Discriminator**: ratio < 2× ⟹ pattern fails discrimination test
  on that deployment instance; ratio ≥ 2× counts toward "working."
  Pattern as a whole counts as "working" iff ≥ 60% of N deployment
  instances pass the 2× threshold.

This replaces the original unquantified "higher rate" formulation
that PL-076 audit flagged as partially tautological.

## Anti-laundering catches

* **Auto-promote laundering**: if the advisory eigenquestion is auto-
  promoted to charter without operator review, the apparatus has
  become a substrate-mutator and the advisory discipline is broken.
  Enforce: writes to charter only via operator-gated review.
* **LLM hallucination laundering**: the LLM may generate a plausible-
  sounding eigenquestion that doesn't address the actual residual.
  Mitigation: PATTERN-015 (eigenquestion_phrasing_discipline) 7-point
  checklist applied to the advisory output BEFORE operator review.
