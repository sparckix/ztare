# Alien-Math Null Hypothesis — Backtest Design

> **Seam metadata** · `seam_id:` alien_math_null_hypothesis_backtest · `track:` audits · `status:` closed · `last_updated:` 2026-05-09


**Status:** closed *(inferred 2026-05-08 — needs operator review)*

**Created:** 2026-04-26 morning
**Companion:** GP-164 v2.0 meta-architecture seam
**Question:** Has any apparatus output produced a primitive that no human library recognizes, or are all "discoveries" reducible to known-math-badly-indexed?

## The null hypothesis

> H_0 (Recital Null): Every primitive ZTARE has generated reduces to an existing entry in a publicly-indexed mathematical library (Wolfram MathWorld, Wikipedia categories, OEIS, DLMF, NIST handbook of mathematical functions, mathlib4 in Lean, SymPy's function catalogue). The apparent "novelty" is a function-of-indexing, not a function-of-mathematics.

> H_A (Alien-Math): There exists at least one primitive in ZTARE's history (composition output, library extension, or implicit-function definition) that does NOT reduce to any entry in the indexed libraries above and that survives ≥ 2 substrates from different domains without overfitting.

## Why this is the right null

A naive null would ask "did ZTARE produce something not in textbooks?" but textbooks are an ill-defined boundary. The indexed libraries above (especially DLMF + mathlib4 + SymPy's function catalogue) define a **machine-checkable boundary**: a candidate primitive is "in the human library" if it has an entry in any of these or can be expressed as a closed-form composition of entries.

This is the same epistemic discipline as the Erdős case. Tao's framing was "people just collectively made a slight wrong turn at move one" — not "ChatGPT discovered math no human had thought of." The retrieved formula HAD an entry in the analytic-number-theory library; the move-one-error was the failure to retrieve it. Under the H_0 null, every ZTARE output has an analogous retrievable entry.

## Backtest protocol

### Step 1: catalog of candidates

For each project where a non-base-library primitive was produced, record:

  * The primitive's symbolic form (PARAMETRIC_FORM, including any composition operators like CONVOLVE/DERIVE from topology_synthesizer)
  * The substrate it was produced on
  * The score it achieved
  * The path that produced it (operator-curated grammar | composition | margin-of-safety extension | reflexive primitive)

Candidates from the existing run history (initial enumeration; verify before backtest):

| Project | Candidate primitive | Path |
|---|---|---|
| Lucky number A000959 | log + (log n)² correction | margin-of-safety library extension |
| sandbox_18 DFDO | additive composite `exp(-b·u^p) + c·exp(-q·log(1+d·u))` | additive-regime compositor (GP-103) |
| sandbox_07 / Component A | structural skeleton from failed-family intersection | structural_constraint_extractor |
| Various OEIS | CONVOLVE / DERIVE composition forms | topology_synthesizer Component D |

### Step 2: indexed-library reduction check

For each candidate, run a structured reduction attempt:

  1. **DLMF/Wolfram lookup:** does the candidate appear as a named function or composition under known names? (manual inspection or LLM-assisted search)
  2. **SymPy simplify:** can SymPy reduce the candidate to a known special function via `simplify`, `combsimp`, `hyperexpand`?
  3. **mathlib4 search:** is the candidate or its asymptotic equivalent provable in mathlib4 against a known library entry?
  4. **OEIS associate:** for sequence-generating primitives, does the produced sequence (or its generating function) match an OEIS entry not used in the substrate's training?

Outcome per candidate:
  * **REDUCED:** found in indexed library. Counts toward H_0 confirmation.
  * **NOT REDUCED:** survives all four checks. Eligible for H_A consideration.
  * **AMBIGUOUS:** reduction inconclusive (e.g., SymPy timeout). Re-classify with more compute.

### Step 3: cross-substrate generalization test

For every candidate that survives Step 2 (NOT REDUCED), test cross-substrate generalization:

  * Take the candidate's symbolic form; treat it as an additional template available to the COMPRESS primitive.
  * Run COMPRESS on 5 substrates from different domains (OEIS sequences, polymer relaxation, neural-scaling-law, physics conjectures) WITHOUT operator hints.
  * If the candidate passes the holdout gate on ≥ 2 substrates from different domains, it is **provisionally novel**. If it passes on 0-1 substrates, it is substrate-overfitting and counts toward H_0 (the apparatus generated noise that happened to fit one substrate).

### Step 4: external mathematician audit

For provisionally-novel candidates only:

  * Strip the substrate context. Present only the symbolic form to a mathematician unfamiliar with the apparatus.
  * Ask: "Does this form have a name in any field you know of?"
  * If yes → recategorize as REDUCED (downgrades to H_0); the apparatus produced math known to humans but absent from the indexed libraries we checked.
  * If no → remains in H_A. Recursively check 2-3 mathematicians from different fields to confirm.

### Decision rule

  * If 0 candidates reach Step 4 with "no" → **H_0 retained** (no alien math observed; ZTARE is L0+L1.5+L2-lite recital with cross-domain transfer).
  * If 1+ candidates reach Step 4 with "no" from ≥ 3 mathematicians AND survive cross-substrate generalization → **H_A** preliminary support; recommend a separate paper claim about that specific primitive.
  * If candidates reach Step 4 with "no" but fail cross-substrate generalization → **H_0 retained** (substrate-specific noise, not novel mathematics).

## What the test does NOT settle

  * Whether the apparatus *could* generate alien math given a different prompt or grammar. (Open hypothesis; backtest only checks past runs.)
  * Whether human-indexed libraries are themselves complete. (Almost certainly not, but the backtest treats them as the operative null.)
  * Whether the human mathematicians audited are representative. (3-mathematician panel is a sample, not a proof.)

## Expected outcome (operator's prior)

H_0 retained on all current candidates. The composition operators CONVOLVE/DERIVE in topology_synthesizer are well-known in their respective fields (analytic number theory, finite differences). Margin-of-safety library extensions like loglog corrections are textbook for primitive-counting asymptotics.

The Lucky-number `log + (log n)²` finding is the most interesting candidate because (a) the validity-horizon was operator-original, not literature-retrieved, and (b) the correction term emerged from the apparatus's own residual analysis rather than from a curated library. But the form `(log n)²` is a standard Hawkins-sieve correction term in the prime-counting literature; expected reduction in Step 2.

The honest framing for the paper: **"On the available substrates, ZTARE's outputs reduce to indexed-library primitives. We retain H_0. Whether ZTARE could produce alien math under different conditions is a separate empirical question the apparatus is not currently designed to test; we propose primitive-generation extensions to GP-078 Component D as the natural next step."**

## Companion artifact

For operationalizing Step 2-3 of this backtest, build:

  `scripts/public/alien_math_null_backtest.py`

That script:
  * iterates ZTARE's project history
  * extracts candidate primitives via PARAMETRIC_FORM grep
  * runs SymPy + DLMF lookup automation per candidate
  * outputs `workspace/alien_math_audit_<ts>.json` with per-candidate REDUCED / NOT REDUCED / AMBIGUOUS verdicts
  * (Step 3-4 require human-in-loop and are not automated)

This is a v1 design. Build the script after L1 ANALOGY ships and stabilizes; backtest is a measurement, ANALOGY is an architectural addition, and they are independent priorities.
