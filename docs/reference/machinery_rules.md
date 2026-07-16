---
description: "Rules governing evidence-bound changes to classifiers, gates, acceptance checks, and harness machinery."
---

# Machinery Rules

Version: v1
Date: 2026-07-03
File SHA: `git rev-parse HEAD:docs/reference/machinery_rules.md` after first commit — the file's SHA is the version.

These rules govern how the system's own machinery (classifiers, gates, acceptance
tests, harness) may be self-modified. Each rule names the primitive it instantiates
from the Audited Multidivisional Architecture (cognitive-firm/draft.md §3, Table 1).

---

## Rule 1 — Proposals Are Cards  (I1: Rule-Boundedness)

Every proposed machinery change must enter the operator-proposals ledger
(`workspace/operator_proposals.jsonl`) as a card with schema
`machinery-contradiction-v1`. A change proposed outside the ledger is not
eligible for adoption.

## Rule 2 — Acceptance Kernel  (S2: Deterministic Enforcement Floor; I1: Rule-Boundedness)

A card may be adopted only when all three conditions hold simultaneously:

  (a) the full frozen test suite passes without modification;
  (b) the card's planted synthetic acceptance test passes; and
  (c) the change shows strict improvement on the named evidence indices relative
      to the current machinery.

## Rule 3 — Certifier Separation  (S1: Separation of Generation from Evaluation; I2: Independence)

Cards with `certifier_touched = True` — those targeting gates, classifiers,
acceptance tests, or the test harness — are NEVER eligible for auto-adoption.
Disposition is conductor-only. A proposal must not amend its own certifier in
one transaction.

## Rule 4 — Tightening Only for Auto-Adopt  (S2: Deterministic Enforcement Floor; I1: Rule-Boundedness)

Auto-adoption is permitted only for changes that TIGHTEN: narrowing an excusal,
strengthening a gate, or reducing a grammar ceiling. Any change that loosens a
constraint requires a countersigned adversarial receipt before adoption.

## Rule 5 — Exogenous Clock  (S3: Exogenous Resource Clock)

At most 3 machinery cards may be written per run. If more than 3 contradictions
are detected in a single call, the first 3 are written plus one meta-card
"machinery churn exceeds clock — escalate", and detection stops. The cap is set
by the conductor, not the detector.

## Rule 6 — Attestation on Every Adoption  (I3: Attestation; liability open)

Every adoption writes one attestation record to the ledger row: card SHA,
outcome, principal identity, first 16 hex digits of the rules-file SHA, test-suite
summary, and timestamp. Liability for a wrong adoption verdict remains an open
institutional problem (cognitive-firm/draft.md §3.4, "Attestation and Liability").

## Rule 7 — Optimization Certificate  (S2: Deterministic Enforcement Floor; S3: Exogenous Resource Clock)

Performance patches touching a hot loop, scorer, cache, harness, provider, or
gate must carry an `optimization_certificate` before adoption. The certificate
declares its class:

- `exact`: the optimized path is equivalent to the reference path over the
  stated domain, with an equivalence or byte-identical-winner test.
- `bounded`: the optimized path is valid only under a named sufficiency
  condition, with a detector for that condition, a fallback/defer behavior when
  it fails, and a regression proving the detector blocks the uncertified path.

Required fields: `abstraction`, `sufficient_statistic`, `soundness_condition`,
`fallback`, `complexity_delta`, and `equivalence_tests`. The adoption harness
rejects performance patches without this certificate. This rule exists for the
failure family where a guard or reader becomes the computation: Galois footprint
recomputation, harness re-identification, prompt-provider abduction, and
uncertified region-write replay.

## Rule 8 — Artifact Authority  (S1: Separation of Generation from Evaluation; S2: Deterministic Enforcement Floor)

Replay, holdout, reachability, task adjudication, planted synthetic tests, and
project-local deterministic gate payloads dominate prose, judge rationale,
strategy-office notes, conjectures, and prompt summaries. A failed deterministic
gate is candidate failure unless a separate gate-integrity receipt proves the
checker itself failed: malformed log slice, environment reset mismatch, parser
crash, hash mismatch, unavailable toolchain, or corrupted harness output.

No mutator, judge, strategy worker, briefing provider, or conjecture write-back
may promote a candidate over a failed deterministic artifact. If a prose artifact
conflicts with a newer SHA-bound gate payload, prompt renderers must surface the
prose as stale commentary or omit it. This rule is substrate-agnostic: it applies
equally to ARC worldmodels, theorem packets, PDE gates, and any future governed
kernel.

## Rule 9 — Meta-Change Contracts  (S1: Separation of Generation from Evaluation; I1: Rule-Boundedness)

Telemetry anomalies may request self-improvement, but they do not directly
authorize code edits. A meta-change starts as a typed anomaly receipt with:
`anomaly_class`, `source_artifact_hash`, `lost_information_yield`, `expected_next
kernel action`, `observed_next action`, `candidate_invariant`, `affected
surfaces`, and `kill_condition`.

A meta-leaf may only write a structured invariant proposal against that receipt.
It must not edit Python, gates, harnesses, tests, prompt renderers, or provider
code. Translation into code is a separate compiler/coder step that must preserve
the original receipt hash and produce a normal machinery card. Adoption then
uses Rules 2, 3, 7, and 8.

The default repair path for compact failures is:

1. telemetry detects a low-entropy counterexample or repeated small residue
   after substantial progress;
2. Strategy Office emits `compressed_counterexample_repair`;
3. the repair card must quotient redundant witnesses, name the substrate-neutral
   kernel role, and propose one discriminating test before broad exploration
   resumes.

This rule is intentionally substrate-neutral. A compact residue may be a grid
transition mismatch, a theorem counterexample, a PDE witness, a stale prompt
surface, or a provider/harness routing anomaly.

## Rule 10 — Kernel Admissibility Receipt  (S1: Separation of Generation from Evaluation; S2: Deterministic Enforcement Floor)

Any change claimed as a kernel-level generalization rather than a substrate
patch must carry a `ztare-kernel-change-admissibility-v1` receipt. The receipt
must declare: `change_class`, `math_anchors`, `raw_evidence_refs`,
`verification_refs`, `preserves_raw_fiber=true`,
`candidate_promotion_authority=false`, and
`introduces_substrate_specific_rule=false`.

For quotient or abstraction changes, the receipt must also name the
`quotient_or_abstraction` and the `raw_witness_projection` back to the original
evidence. For provenance changes, it must name content-addressed refs. Gate
changes are admissible here only when declared as tightening; loosening remains
under Rules 3, 4, and 8.

Mathematical reference point: this is the alpha/gamma contract from
`ztare.common.abstraction_functor`. Kernel code may work on a quotient,
abstraction, MDL compression, CEGAR split, bisimulation class, or
content-addressed carrier, but raw replay/holdout/sealed verifier artifacts
remain the judging fiber. A change that adds domain constants, special-cases a
level, or grants candidate-promotion authority is a substrate patch, not a
kernel generalization.
