# Mathlib Follow-Up PR Audit

Date: 2026-06-09

This pass checks the repo for additional Mathlib PR candidates after PR #40416
was opened.

## Acceptance-Odds Filter

Recent Mathlib PRs suggest a conservative follow-up profile:

- compact API additions often change one or two files and add roughly 10-25
  lines;
- cleanup/generalization PRs in active files can move quickly when they remove
  assumptions or simplify existing code;
- larger theory PRs can merge, but they generally need clearer maintainer
  alignment and more review time.

Examples checked:

- #40279: natural-number choose/factorial bounds; two files, about two dozen
  added lines, merged.
- #40418: new-contributor unitary-ring API; one file, 13 added lines, currently
  open.
- #39354: `eLpNorm` approximation cleanup/generalization; one file, 12 changed
  lines, merged.

This changes the ordering below: the `eLpNorm` translation theorem is a strong
mathematical candidate, but it is not the best immediate high-odds submission.

## Local Compile Checks

These files compiled in the local `ztare_proofs` environment:

- `ZtareProofs/PR_B_CharMulConj_SmokeTest.lean`
- `ZtareProofs/PR_B_NormSqExpand_SmokeTest.lean`
- `ZtareProofs/PR_A2_FwdBridge_SmokeTest.lean`
- `ZtareProofs/mathlib_pr_drafts/PR_1c_iterated_log.lean`
- `ZtareProofs/ns_tick496_minkowski_content_reduction.lean`
- `ZtareProofs/mathlib_pr_drafts/PR_1a_translate_eLpNorm_continuity.lean`
- `ZtareProofs/SQ3/SQ3_PR1_lp_translation_continuity.lean`

The compile checks are necessary but not sufficient. Several files still have
project-specific names, local framing, or an API story that Mathlib maintainers
may not want.

## Best Substantive Candidate

### Lp translation continuity

Sources:

- `ZtareProofs/mathlib_pr_drafts/PR_1a_translate_eLpNorm_continuity.lean`
- `ZtareProofs/SQ3/SQ3_PR1_lp_translation_continuity.lean`
- `mathlib_pr_prep/PR3_translate_eLpNorm_continuity_domact.lean`

Current verdict:

- Good mathematical candidate.
- The old long proof is no longer the right upstream shape. Current Mathlib
  already proves continuity of the `DomAddAct` action on `Lp`; the cleaner PR
  candidate is the short function-level `eLpNorm` corollary in
  `PR3_translate_eLpNorm_continuity_domact.lean`.
- More substantial than the oscillatory-bound helper because it raises an API
  placement/import question: the proof uses both
  `MeasureTheory.Function.LpSpace.DomAct.Continuous` and
  `MeasureTheory.Function.LpSpace.Complete`.

Why it is worth building:

- Current Mathlib has the abstract continuity theorem; this draft packages the
  concrete `eLpNorm (fun x => f (x + h) - f x)` consequence.
- Direct searches did not find this concrete theorem.
- The statement is standard and useful beyond this repo.

Required prep before opening:

- Decide placement. Options: add a small theorem near `DomAct/Continuous` with
  an added import from `LpSpace.Complete`, or create a small downstream file
  for `eLpNorm` corollaries of domain-action continuity.
- Consider whether the final theorem should use left translation
  `fun x => f (h + x)` or right translation `fun x => f (x + h)`. The draft
  proves the right-translation statement over an additive commutative group by
  rewriting with `add_comm`.
- Ask on Zulip or wait for PR #40416 feedback before submitting because this is
  an API/placement question, not just a proof check.

## Best Small Candidate

### Oscillatory integral bounds

Sources:

- `ZtareProofs/PR_A1_BohrCoeffExpNe_Discharge.lean`
- `mathlib_pr_prep/PR2_OscillatoryIntegralBounds.lean`

Current verdict:

- Current-Mathlib branch prepared, committed, and pushed to the fork:
  https://github.com/sparckix/mathlib4/tree/oscillatory-integral-bounds
  (`08222cd`, `oscillatory-integral-bounds`). Local checkout:
  `/private/tmp/mathlib4-upstream-master`.
- The candidate was reshaped from a standalone quotient/set-integral helper
  into two exposed interval-integral estimates placed after
  `integral_exp_mul_complex` in
  `Mathlib/Analysis/SpecialFunctions/Integrals/Basic.lean`.
- The quotient estimate is private; the public API is:
  `norm_integral_exp_mul_I_le_length` and
  `norm_integral_exp_mul_I_le_two_div`.
- Verification passed on 2026-06-09:
  `lake env lean Mathlib/Analysis/SpecialFunctions/Integrals/Basic.lean`,
  `lake exe lint-style Mathlib.Analysis.SpecialFunctions.Integrals.Basic`, and
  `lake build Mathlib.Analysis.SpecialFunctions.Integrals.Basic`.
- This is now the best small follow-up from the repo. It remains more
  specialized than PR #40416, so the better sequencing is to wait for first
  reviewer feedback before opening it.

Required prep:

- If opening, push the prepared branch from a Mathlib fork and use a small title
  such as `feat(Analysis/SpecialFunctions): add bounds for exponential integrals`.
- Include an AI-assistance disclosure in the PR description.

## Possible But Not Immediate

### Iterated logarithm utility

Source:

- `ZtareProofs/mathlib_pr_drafts/PR_1c_iterated_log.lean`

Current verdict:

- Local compile passes.
- Mathlib has `Real.posLog` and rich log monotonicity/tendsto lemmas, but no
  direct `triLog` / triple-log API by direct search.
- The risk is API taste: Mathlib may not want this exact clipped triple-log
  definition unless there is a broader asymptotics file that benefits from it.

Required prep:

- Replace the project draft with a neutral API proposal.
- Remove broad references and any nonstandard prose.
- Consider whether generic `iterate Real.log n` lemmas are preferable to a
  named `triLog`.
- Ask on Zulip before opening. This is a definition/API-taste question, not
  just a proof-check question.

### Finite forward-character algebra

Sources:

- `ZtareProofs/PR_A2_FwdBridge_SmokeTest.lean`
- `ZtareProofs/PR_B_CharMulConj_SmokeTest.lean`
- `ZtareProofs/PR_B_NormSqExpand_SmokeTest.lean`

Current verdict:

- Local compile passes.
- This is not a good standalone PR unless it is framed as part of a finite
  additive-character/trigonometric-polynomial API.
- Current Mathlib already has additive characters in other contexts
  (`AddChar`, finite Fourier on `ZMod`, padic additive characters), so a custom
  `forwardChar : (Fin n -> Real) -> ...` definition needs careful placement.

Required prep:

- Deduplicate against existing `AddChar` and Fourier APIs.
- Decide whether to build a small additive-character API over `Fin n -> Real`
  or keep this project-local.

After the 2026-06-09 scan, this is not PR-ready: the smoke tests define local
`forwardChar`/`IsTrigPolyVelocity` API and prove algebra around it, while
Mathlib already has adjacent additive-character/Fourier infrastructure. A PR
needs an API design decision first.

## Do Not Build As Mathlib PRs Yet

### Minkowski-content arithmetic

Source:

- `ZtareProofs/ns_tick496_minkowski_content_reduction.lean`

Reason:

- Local compile passes, but the extractable theorem is a very small arithmetic
  inequality with unused hypotheses in its current form.
- It is better as an internal proof receipt than as a Mathlib PR.

### Continuous Minkowski / convolution stack

Source:

- `ZtareProofs/SQ3/MLG_2_eLpNorm_convolution_sub_le.lean`

Reason:

- The file is a large staged development with local imports and many project
  bridge declarations.
- The useful mathematical target is real, but it should follow the smaller Lp
  translation-continuity PR, not precede it.

### Dirichlet/Kronecker continuous witness

Source:

- `ZtareProofs/PR_A1_DirichletKronecker_SmokeTest.lean`

Reason:

- Local compile passes, but the theorem is tied to a very specific permissive
  quantifier shape where the witness can depend on `x` and move continuously.
- Do not submit until the exact intended upstream almost-periodic
  relative-density statement is audited.

## Recommended Order

1. Wait for PR #40416 reviewer feedback.
2. Submit the prepared oscillatory-integral bounds PR if the first PR feedback
   does not reveal a contributor-process issue.
3. Search current Mathlib for tiny cleanup/API improvements discovered by our
   extracted proofs.
4. Keep the short `eLpNorm` translation-continuity prep internal until an API
   placement sanity check; it is useful but larger.
5. Defer iterated logs, finite-character algebra, and KRF infrastructure until
   a maintainer-facing API story is clearer. The KRF/eLpNorm/Minkowski drafts
   are mathematically meaningful but still contain named proof gaps or too much
   theory for a follow-up new-contributor PR.
