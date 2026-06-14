# Mathlib PR Candidate Audit

Date: 2026-06-09

This is the current submission queue after reconciling the prior NS PR-readiness
notes with the fresh static scan and a quick check of recent Mathlib PR shape.

High-odds here means: small generic theorem surface, one or two files, obvious
placement in an existing API, no project vocabulary, no new local theory unless
a maintainer has asked for it. Recent examples:

- #40279 added natural-number factorial/choose bounds in two files, about two
  dozen lines.
- #40418 is a new-contributor PR adding two unitary-ring lemmas in one file,
  13 lines.
- #39354 touched the active `eLpNorm` approximation area, but as a very small
  cleanup/generalization in one file.

## Submitted

### PR 1: diagonal subsequence extraction

- Draft: `PR1_CantorDiagonal.lean`
- Source: `ZtareProofs/ns_trackb_krf_cantor_diagonal.lean`
- Proposed theorem: `Nat.exists_strictMono_diagonal_subsequence`
- Upstream PR: https://github.com/leanprover-community/mathlib4/pull/40416
- Status: opened against Mathlib on 2026-06-09. Local current-Mathlib checks passed:
  `lake env lean Mathlib/Order/Monotone/Basic.lean`, `lake build
  Mathlib.Order.Monotone.Basic`, `lake exe lint-style
  Mathlib/Order/Monotone/Basic.lean`, and `git diff --check`.
- CI status at last poll: all build/lint checks green; only bot comments so
  far. Awaiting reviewer/maintainer feedback.
- Review risk: moderate. The statement is small and generic. The proof uses a
  small local induction lemma for `StrictMono f → n ≤ f n`; the existing
  `StrictMono.id_le` theorem is unavailable in `Mathlib.Order.Monotone.Basic`
  without creating an import loop through `Mathlib.Order.WellFounded`.

Verdict: submitted. Do not open another PR until this one either passes CI or
receives maintainer feedback.

## High-Odds Follow-Ups

### PR 2 candidate: oscillatory-integral bounds

- Sources:
  - `ZtareProofs/PR_A1_BohrCoeffExpNe_Discharge.lean`
  - `ZtareProofs/PR_A1_BohrCoeffExpNe_Cascade.lean`
  - `ZtareProofs/PR_A1_CubeAvgModSqLeLinftySq.lean`
  - `ZtareProofs/PR_A1_T9_Lemma_4_2.lean`
  - `ZtareProofs/PR_A1_T9_Lemma_4_3.lean`
- Draft: `PR2_OscillatoryIntegralBounds.lean`
- Status: branch prepared, committed, and pushed to the fork:
  https://github.com/sparckix/mathlib4/tree/oscillatory-integral-bounds
  (`08222cd`, `oscillatory-integral-bounds`). Local checkout:
  `/private/tmp/mathlib4-upstream-master`.
- Dedup result: `cube_integral_prod_factor` is not an upstream gap; current
  Mathlib already has `volume_pi`, `Measure.restrict_pi_pi`, and
  `integral_fin_nat_prod_eq_prod`. `integral_Icc_exp_mul` is mostly a wrapper
  around current `integral_exp_mul_complex`. The plausible reusable residue is
  the oscillatory-bound API.
- Current branch content:
  - exposed:
    `norm_integral_exp_mul_I_le_length`
  - exposed:
    `norm_integral_exp_mul_I_le_two_div`
  - private proof helper:
    `norm_exp_mul_I_sub_exp_mul_I_div_le`
- Current-Mathlib validation passed on 2026-06-09:
  `lake env lean Mathlib/Analysis/SpecialFunctions/Integrals/Basic.lean`,
  `lake exe lint-style Mathlib.Analysis.SpecialFunctions.Integrals.Basic`, and
  `lake build Mathlib.Analysis.SpecialFunctions.Integrals.Basic`.
- Required work: if opening, push this branch from the Mathlib fork and use a
  compact PR description with AI-assistance disclosure.

Verdict: technically PR-ready and the best small follow-up candidate. Better
sequencing is to wait for first feedback on PR #40416 before opening it.

### Tiny cleanup/API candidates

No concrete candidate is selected yet. The acceptance data suggests these are
worth mining before opening a larger analysis PR:

- remove unused assumptions from existing Mathlib statements, if our proofs
  reveal any;
- add one-lemma API facts near existing definitions, with no new imports;
- replace fragile proof steps or local helper duplication if the change is
  visibly simpler.

Verdict: highest conditional odds in principle, but requires a targeted scan of
current Mathlib rather than extracting from project files.

## Larger Follow-Ups

### `eLpNorm` translation continuity

- Sources:
  - `ZtareProofs/mathlib_pr_drafts/PR_1a_translate_eLpNorm_continuity.lean`
  - `ZtareProofs/SQ3/SQ3_PR1_lp_translation_continuity.lean`
- Prep draft: `PR3_translate_eLpNorm_continuity_domact.lean`
- Status: mathematically stronger than PR 2, and the proof now has a compact
  Mathlib-native shape. The theorem is derived from existing continuity of the
  `DomAddAct` action on `Lp`, then converted to the concrete `eLpNorm`
  statement with `Lp.tendsto_Lp_iff_tendsto_eLpNorm'` and
  `DomAddAct.mk_vadd_toLp`.
- Current-Mathlib validation passed on 2026-06-09:
  `lake env lean /Users/daalami/figs_activist_loop/ztare_proofs/mathlib_pr_prep/PR3_translate_eLpNorm_continuity_domact.lean`.
- Required work: decide file placement and import direction. This should not
  be submitted as the older long density proof. Ask analysis/measure
  maintainers whether they prefer a small downstream file or adding the
  corollary near `LpSpace/DomAct/Continuous`.

Verdict: high-quality mathematical candidate, but lower short-term acceptance
odds than PR 2 because it needs maintainer alignment on API placement.

### Iterated logarithm utilities

- Source: `ZtareProofs/mathlib_pr_drafts/PR_1c_iterated_log.lean`
- Status: closed proof body in prior scan.
- Required work: decide whether Mathlib wants this exact clipped API or only
  more generic iterated-log lemmas.

Verdict: technically plausible, lower priority.

## Do Not Submit Yet

- `ZtareProofs/ns_trackb_krf_mathlib_pr_ready.lean`: roadmap name only; contains
  unresolved proof obligations in the prior audit.
- Aubin-Lions/Kolmogorov-Riesz-Frechet master theorem stack: mathematically
  meaningful, but a multi-PR analysis project, not a first contribution.
- `PR_A1_DirichletKronecker_SmokeTest.lean`: compiles, but needs a quantifier
  audit before upstreaming.
- Any file with local `ZtareProofs` imports, code `sorry`, `axiom`, `opaque`, or
  `#print axioms` audit scaffolding.

## Practical Order

1. Wait for PR 1 maintainer feedback.
2. Submit the prepared oscillatory-integral bounds PR if PR #40416 feedback
   does not reveal a process issue.
3. Mine current Mathlib for one-file cleanup/API candidates with no new theory
   commitment.
4. Keep the short `eLpNorm` translation-continuity draft internal until an API
   placement sanity check.
5. Only then revisit KRF/Aubin-Lions infrastructure with a Zulip design thread.
