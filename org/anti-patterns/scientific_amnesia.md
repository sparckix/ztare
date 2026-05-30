---
id: ANTI-PATTERN-011
name: scientific_amnesia
version: 1
status: active
discovered: 2026-05-14
triggers:
  lexical: ["have we been here before", "why did we not see this", "prior arc", "repeat"]
  structural:
    - branch_selected_without_prior_artifact_overlap_check
    - operator_supplies_history_that_local_artifacts_already_contain
    - repeated_wrapper_work_around_same_unpaid_frontier
    - gp233_or_experiment_rows_exist_but_are_not_consulted
  problem_classes: [hard_mathematical_residual, apparatus_self_audit, too_complex_direct_attack]
detection_protocol:
  primary: PATTERN-024
  secondary: PATTERN-017
  rule:
    - "Run scientific-amnesia precheck on the branch text before dispatch or proof edit."
    - "If top hits include prior E/F rows or code declarations with the same active bottleneck, classify the branch as repeat, reuse, adjacent_but_distinct, or no_close_prior before acting."
mitigation:
  - "Convert repeat into reuse or stop."
  - "When reuse is valid, add the explicit import/source bridge instead of redoing the old arc."
  - "Log the classification in the E/F row or GP-233 row if it changes the next lever."
examples:
  - id: ns_pressure_riesz_2026_05_14
    summary: "Operator asked whether the route-1 pressure/Riesz angular branch had been visited before. Prior ticks 302-313 had pressure/Riesz source stations; ticks 314-319 shifted to lower-bound angular carrier visibility. The missing primitive was a pre-tick overlap query across E/F rows, GP-233 rows, and NS Lean declarations."
    file: analytics/public/queries/scientific_amnesia/ns_latest.json
falsifiable_test:
  description: "Given a branch query that contains terms from a known prior basin, the checker must return exact artifact pointers above threshold before branch choice."
  binary_check: "exists(top_hit.score >= threshold and top_hit.path points to prior E/F, GP-233, or code declaration)"
  not_trivial: "Returns not-firing for low-overlap branch terms; returns firing on the 2026-05-14 NS pressure/Riesz query."
chain_position: pre
references:
  - "PATTERN-024 scientific_amnesia_precheck"
  - "src/ztare/research_director/scientific_amnesia.py"
  - "analytics/public/queries/scientific_amnesia/ns_latest.json"
---

# ANTI-PATTERN-011 — Scientific Amnesia

## What it is

Selecting or defending a branch without first checking whether local
artifacts already contain the same basin. The symptom is an operator or
later agent asking, "have we been here before?" and the answer being
recoverable from existing E/F rows, GP-233 evidence, or code declarations.

## Why it appears

The frontier moves quickly and the vocabulary shifts. A prior branch may
be recorded as a pressure-source station, while the current branch is
phrased as angular carrier visibility. Without a deterministic overlap
check, the RD can treat familiar terrain as fresh.

## Why it matters

Scientific amnesia wastes proof ticks and corrupts confidence updates.
It can also hide useful reuse: prior work may not solve the current
frontier, but it can feed a narrower source station if the boundary is
made explicit.

## Detection Protocol

Run PATTERN-024 before branch commitment:

```bash
./venv/bin/python scripts/public/control/scientific_amnesia_precheck.py \
  --substrate NS \
  --query "pressure hessian tail window recovered Riesz angular carrier identification" \
  --code-glob "ztare_proofs/ZtareProofs/ns*.lean"
```

The anti-pattern fires if:

- the top hits show a close prior basin;
- the RD had not cited those hits before choosing the branch;
- the current branch note does not classify the relation to prior work.

## Mitigation

If the relation is `repeat`, stop or reformulate the branch.
If it is `reuse`, add the source/import bridge and record why the prior
object is insufficient for the current proof obligation.
If it is `adjacent_but_distinct`, proceed but name the exact difference.

## Falsifiable Test

The 2026-05-14 NS pressure/Riesz query returns exact prior pointers:
E/F rows, GP-233 evidence, and Lean declarations. A session that would
not have surfaced those pointers before operator prompting is firing this
anti-pattern.

## AKA (MECE audit 2026-05-16)

The proposed "ANTI-PATTERN-018 Semantic Laundering / Vocabulary
Loop" (a defeated constraint regenerated under new vocabulary —
e.g. strict-margin atom → "viscous alignment surplus" → "subcaloric
threshold") is THIS pattern. NOT logged separately (duplicate); it
is ANTI-PATTERN-011 + the O(1) residual-manifest alias table
(7 drifts logged) + vocabulary_chain_laundering / vocabulary_smuggling.
