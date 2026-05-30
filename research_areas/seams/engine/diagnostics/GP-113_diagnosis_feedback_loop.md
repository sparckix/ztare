# GP-113 — Diagnosis-Informed LLM Feedback Loop

> **Seam metadata** · `seam_id:` GP-113 · `track:` engine · `status:` unrecorded · `last_updated:` 2026-05-08


Status: opening
Opened: 2026-04-21

## Eigenquestion

> When the deterministic compression exhausts its grammar and GP-112 produces
> a structural diagnosis (spectral slope, autocorrelation, gap dependence),
> can the LLM mutator use that diagnosis to propose forms OUTSIDE the grammar
> that the deterministic search cannot reach?

## Motivation

Cross-substrate audit (2026-04-21) found: Phase 2 (deterministic compression)
found the answer on 6/10 substrates. Phase 1 (LLM) contributed on 2/10. The
natural conclusion: the LLM is dead weight.

The operator inverted: the LLM is not dead weight — we are starving it of the
right signal. The mutator currently sees: thesis, evidence, judge feedback. It
does NOT see: compression results, margin-of-safety diagnosis, residual spectral
characterization, or gap-structure analysis.

If we feed the PERSIST signal into the mutator prompt, the LLM becomes a creative
hypothesis generator for what the deterministic system diagnosed but cannot fix.
This is the LLM doing what it does well (structural analogy, cross-domain transfer)
informed by what the deterministic system measured.

## Architecture

```
Phase 1 (LLM loop, cold start) → Phase 2 (compression) → Phase 2.5 (GP-112)
    ↓ PERSIST + diagnosis
Phase 1b (LLM loop, diagnosis-informed) → Phase 2b (re-compression) → Phase 2.5b
```

Phase 1b prompt includes:
- The champion form from Phase 2 (the best the grammar produced)
- The GP-112 diagnosis: spectral slope, noise class, autocorrelation, gap structure
- Explicit instruction: "the deterministic search exhausted all additive and
  compositional templates. The residuals have [spectral slope] noise. Propose
  a functional form that addresses this residual structure. You may use forms
  NOT in the standard grammar."

## Evidence from this session

| Substrate | Phase 1 | Phase 2 | GP-112 diagnosis | Phase 1b potential |
|-----------|---------|---------|------------------|-------------------|
| Lucky 500K | score 98 (wrong form) | compositional | Brown noise, slope -1.63 | "Propose multiplicative or gap-dependent correction" |
| Ulam | score 0 | UNDERIDENTIFIED | Near-white, H=0.05 | "Propose periodic + anti-persistent model" |
| Neural scaling | score 0 | degenerate fit | 1/f, slope -0.77 | "Propose power-law with 1/f correction" |

## Constraints

1. Phase 1b uses the GP-112 diagnosis as a PROMPT, not as a grammar expansion.
   The LLM proposes structure; SciPy fits parameters; gates verify.
2. Phase 1b runs a LIMITED budget (5 iterations, not 15). The diagnosis
   constrains the search space.
3. The diagnosis prompt must NOT contain domain-specific vocabulary. Only
   mathematical descriptions: "spectral slope -0.77", "lag-1 autocorrelation
   0.93", "U-shaped dependence on gap size."
4. Phase 2b re-compression includes any new forms proposed by Phase 1b.

## Relationship to other seams

- GP-111 (rival exclusion): Phase 2.5a, fires after compression
- GP-112 (margin of safety): Phase 2.5b, fires after GP-111, produces the diagnosis
- GP-113 (this): Phase 1b, fires after GP-112 PERSIST, uses the diagnosis

## Next actions

- [ ] Panel review: is this architecture sound? Does feeding residual diagnostics
      to the LLM create a new contamination vector?
- [ ] Implement Phase 1b prompt construction from GP-112 output
- [ ] Test on Lucky 500K, Ulam 550K, neural scaling
- [ ] Measure: does Phase 1b propose forms the deterministic search missed?
