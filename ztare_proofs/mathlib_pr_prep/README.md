# Mathlib PR Prep

This folder holds neutral, Mathlib-shaped drafts extracted from the NS proof
substrate. These are preparation artifacts, not claims that the files have been
accepted by Mathlib.

## Current Status

Current strategy: prefer small, generic, one-file or two-file PRs until the
first Mathlib contribution has CI and reviewer feedback. Recent accepted PRs
with a similar contributor profile are usually compact API additions or cleanup
patches, not large theory imports.

### PR 1: diagonal subsequence extraction

- Draft file: `PR1_CantorDiagonal.lean`
- Source file: `ZtareProofs/ns_trackb_krf_cantor_diagonal.lean`
- Proposed target: `Mathlib/Order/Monotone/Basic.lean`, near
  `Nat.exists_strictMono_subsequence`
- Upstream PR: https://github.com/leanprover-community/mathlib4/pull/40416
- Status: compiles locally with
  `lake env lean mathlib_pr_prep/PR1_CantorDiagonal.lean`; opened against
  Mathlib on 2026-06-09.
- Current-Mathlib check: inserted cleanly into a fresh
  `/private/tmp/mathlib4-pr-check` clone of `leanprover-community/mathlib4`
  on Lean `v4.31.0-rc2`. The proof deliberately keeps a small local induction
  for `StrictMono f → n ≤ f n`: the existing Mathlib API `StrictMono.id_le`
  lives in `Mathlib.Order.WellFounded`, and importing that file into
  `Mathlib.Order.Monotone.Basic` creates an import loop.
- Why first: short, generic, no local dependencies, no NS/PDE framing, no
  sorries, and useful as a sequence/order lemma.
- CI status at last poll: all build/lint checks green; only bot comments so
  far. Awaiting reviewer/maintainer feedback.

### PR 2 prep: oscillatory integral bounds

- Draft file: `PR2_OscillatoryIntegralBounds.lean`
- Dedup note: `PR2_BOHR_DEDUP.md`
- Status: branch prepared, committed, and pushed to the fork:
  https://github.com/sparckix/mathlib4/tree/oscillatory-integral-bounds
  (`08222cd`, `oscillatory-integral-bounds`). Local checkout:
  `/private/tmp/mathlib4-upstream-master`.
- Current-Mathlib check: inserted into
  `Mathlib/Analysis/SpecialFunctions/Integrals/Basic.lean` after
  `integral_exp_mul_complex`. The exposed API is now two interval-integral
  estimates:
  `norm_integral_exp_mul_I_le_length` and
  `norm_integral_exp_mul_I_le_two_div`; the quotient estimate is private.
- Verification on 2026-06-09:

  ```bash
  lake env lean Mathlib/Analysis/SpecialFunctions/Integrals/Basic.lean
  lake exe lint-style Mathlib.Analysis.SpecialFunctions.Integrals.Basic
  lake build Mathlib.Analysis.SpecialFunctions.Integrals.Basic
  ```

- Submission posture: technically PR-ready, but do not open immediately unless
  you want multiple simultaneous Mathlib PRs. Better odds: wait for first
  reviewer feedback on PR #40416, then submit this as the next small PR.

### PR 3 prep: `eLpNorm` translation continuity

- Draft file: `PR3_translate_eLpNorm_continuity_domact.lean`
- Source files:
  `ZtareProofs/mathlib_pr_drafts/PR_1a_translate_eLpNorm_continuity.lean`
  and `ZtareProofs/SQ3/SQ3_PR1_lp_translation_continuity.lean`
- Status: internal only; no upstream branch or PR opened.
- Current-Mathlib check on 2026-06-09:

  ```bash
  lake env lean ztare_proofs/mathlib_pr_prep/PR3_translate_eLpNorm_continuity_domact.lean
  ```

- Result: the short proof compiles. The better upstream shape is not the long
  density proof; it is a corollary of the existing continuity of the
  `DomAddAct` action on `Lp`, converted back to a concrete `eLpNorm` statement
  using `Lp.tendsto_Lp_iff_tendsto_eLpNorm'` and
  `DomAddAct.mk_vadd_toLp`.
- Submission posture: mathematically strong and cleaner than the older long
  drafts, but not a next-PR default. It needs a placement/import decision,
  because the proof uses both `LpSpace/DomAct/Continuous` and
  `LpSpace/Complete`. Ask on Zulip or wait for maintainer signal before
  opening.

The local compile currently prints warnings that the vendored Mathlib and
Batteries package directories have local changes. That does not invalidate the
drafts, but any submitted PR must be checked in a clean Mathlib fork.

## PR 1 Content

The theorem is:

```lean
Nat.exists_strictMono_diagonal_subsequence
```

It says that if `φ (k + 1)` factors through `φ k` by a strictly monotone map,
then the diagonal `fun n => φ n n` is strictly monotone and every tail of that
diagonal factors through the corresponding `φ k` by a strictly monotone map.

For the actual Mathlib PR, do not copy the NS source file. Copy the neutral
theorem and docstring from `PR1_CantorDiagonal.lean` into the target Mathlib
file.

## Not Ready As First PR

The following files compile locally but are not first-PR ready without more
extraction:

- `PR_A1_BohrCoeffExpNe_Discharge.lean`: contains useful analytic lemmas, but
  the file has internal audit language, `_used_*` proof bookkeeping, and
  discharge/smoke-test framing. The current dedup pass extracted only the
  oscillatory-bound residue into `PR2_OscillatoryIntegralBounds.lean`.
- `PR_A1_CubeAvgModSqLeLinftySq.lean`: compiles, but has unused-variable
  warnings and T9/axiom-decomposition framing.
- `PR_A1_T9_Lemma_4_2.lean` and `PR_A1_T9_Lemma_4_3.lean`: compile, but must be
  renamed and detached from T9/Bohr/NS language.
- `mathlib_pr_drafts/PR_1a_translate_eLpNorm_continuity.lean` and
  `SQ3/SQ3_PR1_lp_translation_continuity.lean`: compile, but overlap. They
  should not be submitted in their long form. The current prep artifact is the
  shorter `PR3_translate_eLpNorm_continuity_domact.lean`, which derives the
  result from the existing `DomAddAct` continuity API.

## Submission Process

1. Fork `leanprover-community/mathlib4`.
2. Clone your fork and create a small branch, for example
   `nat-diagonal-subsequence`.
3. Install/fetch the Mathlib cache in that clean checkout.
4. Insert the PR 1 theorem into `Mathlib/Order/Monotone/Basic.lean`, likely in
   the `namespace Nat` section near `exists_strictMono_subsequence`. The proof
   keeps a tiny local induction lemma rather than importing
   `Mathlib.Order.WellFounded`, because that import creates a dependency loop.
5. Run the narrow file check first:

   ```bash
   lake env lean Mathlib/Order/Monotone/Basic.lean
   ```

6. Run the relevant build target:

   ```bash
   lake build Mathlib.Order.Monotone.Basic
   ```

7. Open a small PR from your fork. Proposed title:

   ```text
   feat(Order/Monotone): add diagonal subsequence extraction on Nat
   ```

8. In the PR description, keep the mathematical motivation generic. Do not
   mention Navier-Stokes, Clay, KRF, or the private proof substrate.
9. Disclose AI assistance because Mathlib asks for it when AI tools were used:
   say that AI tools helped with extraction/review and that you understand and
   take responsibility for the statement and proof.
10. For anything larger than PR 1, ask on the Lean Zulip `#mathlib` channel
    first, in your own words. For the highest acceptance odds, keep the next PR
    in the same size class as recent merged Mathlib API patches.

## Draft PR Description

```text
This PR adds a small diagonal extraction lemma for nested strictly monotone
subsequences of Nat.

Given strict-mono maps φ k : Nat -> Nat such that each φ (k + 1) factors
through φ k by a strict-mono map τ k, the diagonal sequence fun n => φ n n is
strictly monotone and each tail of the diagonal factors through the
corresponding φ k by a strict-mono map.

The lemma is intended as a reusable sequence/order fact and is placed near
Nat.exists_strictMono_subsequence.

AI assistance disclosure: I used AI tools to help extract and review this
small lemma from a local formalization project. I have checked the statement
and proof myself and am responsible for the submitted code.
```
