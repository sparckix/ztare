# GP-136 — pMDL Threshold Hardening (narrower substrate post-GP-135)

> **Seam metadata** · `seam_id:` GP-136 · `track:` mission · `status:` Active (scaffolded 2026-04-23 evening). Pre-run. · `last_updated:` 2026-05-08


**Status:** Active (scaffolded 2026-04-23 evening). Pre-run.
**Opened:** 2026-04-23.
**Parent:** GP-135 (ztare_on_ztare four-primitive thesis at score 92).
**Related:** GP-134 (apparatus contamination incident).

---

## Eigenquestion

Given a sequential-MDL-based acceptance gate with threshold θ that uses a practical universal-compressor proxy C, characterize the (codec class C × stream length N × distribution class D) domain over which θ is provably universal versus empirically cooked.

Concretely: derive θ(C, N, D) with bounded error against the ideal Kolmogorov criterion, OR prove the impossibility, OR pre-register a precise domain restriction inside which the original ΔMDL < 0 gate IS provably universal.

---

## Why this seam exists

GP-135's ztare_on_ztare run produced a 4-primitive thesis at score 92 under the hardened Newton-mode rubric. Its first primitive (MDL-Exact Compression Gate using `zlib.compress` and ΔMDL < 0 as a "threshold-free, exact" criterion) was partially falsified by:

- The apparatus's own adversarial attacker suite (Δratio swings from 0.12 to 0.55 on short streams; padded Δ = 1326 at length 1024; cross-codec variance with bz2/lzma)
- The blind 4-panel external review (the MDL/info-theorist panelist explicitly verdicted "(c) fundamentally limited by practical-compressor vs theoretical-Kolmogorov gap; effectively the Cilibrasi-Vitányi NCD trick from IEEE TIT 2005 with the same documented caveats")

The user's question — "should we update the GP-135 charter to acknowledge the primitive was found?" — was correctly answered NO (charter drift risk). Instead, this seam opens a new substrate with a narrower, pre-registered question targeting the specific weakness the panel surfaced. GP-135 stands as a record under its frozen charter. GP-136 asks the next-level question.

---

## Substrate type

**Qualitative apparatus-engineering substrate** (like ztare_on_ztare, not like mlh_f*). No (n, z) numeric evidence. The "evidence" is:

1. The score-92 thesis from GP-135 (the originally-proposed ΔMDL < 0 gate)
2. The recorded adversarial counter-test data (codec-swap and short-stream observations)
3. The blind 4-panel review verdicts (in particular the MDL panelist's specific objections)

`fit_score_mode: none`, no holdout hard gate, no farther-tail region. Newton-mode rubric; Generative Yield enforced.

---

## Acceptable thesis structures

Any thesis must include AT LEAST ONE of:

| Structure | Required content |
|---|---|
| **Constructive bound** | Explicit θ(C, N, D) with derivation citing a published information-theoretic redundancy bound (Shtarkov 1987 NML, Rissanen 1996 stochastic complexity, Barron-Rissanen-Yu 1998, Grünwald 2007). Must reduce to ΔMDL = 0 in the asymptotic limit AND reproduce the recorded counter-test data within stated error envelope. |
| **Impossibility result** | Constructive proof that no such θ(C, N, D) can be derived from a practical compressor (e.g., reduction to incomputability of K(·) up to additive constant). Must state what would falsify it. |
| **Domain restriction** | Specific (C, N, D) regime in which the original ΔMDL < 0 gate IS provably universal. Plus an explicit boundary outside which it is not. |

---

## Rubric (frozen at substrate open)

`rubrics/gp136_pmdl_hardening.json`. Newton-mode + DAG steering enabled. Six dimensions, weights total 100:

| Dimension | Weight |
|---|---|
| Threshold Specificity | 30 |
| Theoretical Grounding | 20 |
| Adversarial Reproducibility | 20 |
| Generative Yield (Newton-mode) | 15 |
| Mechanism Algorithmic Concreteness | 15 |

The persona is hostile to verbal hand-waves around "more universal compressors" and to invocation of "Kolmogorov complexity" as a usable computational object.

---

## Falsifiable predictions for this seam

| # | Prediction | Test | Kill level |
|---|---|---|---|
| P1 | First iter under o3 + gpt4.1 judge produces a thesis matching ONE of the three acceptable structures above (not a verbal restatement of the original gate) | Inspect iter 1 thesis | Iter 1 produces verbal restatement → R1/R3 layer is too lax for this charter; reset rubric |
| P2 | Engine names a specific replacement compressor by iter 5 (CTW, NML, sequential-Rissanen, prequential, BIC, ...) — not "a more universal compressor" | Iter 5 thesis content | No named replacement → engine is rubric-gaming; tighten Mechanism Algorithmic Concreteness |
| P3 | Engine reproduces the recorded counter-test data (codec-swap and short-stream) within its proposed error envelope by iter 8 | Adversarial Reproducibility dimension score | All iters score 0 on Adversarial Reproducibility → engine cannot synthesize from prior runs' attacker output |
| P4 | At least one iter scores ≥ 70 by iter 10 | Score trajectory | All iters ≤ 50 → substrate is genuinely intractable under current apparatus, OR pivot to operator-supplied derivations |

---

## Operational commands

```bash
# Run the substrate
make experiment-loop PROJECT=gp136_pmdl_hardening RUBRIC=gp136_pmdl_hardening ITERS=10 \
    MUTATOR_MODEL=o3 JUDGE_MODEL=gpt4.1 DYNAMIC=1
```

No make-discover Phase 3 needed — this substrate is qualitative; no Lean stubs to generate from gate results.

---

## Relationship to GP-135 (separation discipline)

- GP-135 charter: "find architectural primitives that move ZTARE from fitting to constructing." Result: 4-primitive thesis at score 92, partially falsified. **Frozen.**
- GP-136 charter: "given the pMDL primitive identified in GP-135, characterize its threshold's domain of validity." **Independently pre-registered.**

Both charters are independently scored. GP-136's result does not retroactively affect GP-135's record.

---

## Open follow-ups

- [ ] Run iter 1-3 under o3 + gpt4.1; check if engine produces structure-conformant thesis
- [ ] If engine succeeds: implement the proposed θ as a real apparatus gate (not just a thesis)
- [ ] Cross-reference any replacement-compressor proposals against the existing `src/ztare/fit/compress_champion.py` infrastructure
- [ ] Update the GP-135 incident seam to link forward to GP-136 as the resolution arc

---

## Meta

This seam is the cleanest example so far of the apparatus producing a partial result that requires operator-mediated narrowing into a follow-up question. The discipline being practiced: GP-135's flawed primitive is not "fixed" by editing GP-135's charter; it's converted into the input for a NEW pre-registered substrate (GP-136) whose specific question is "where is the flaw, and what's the bounded version?" This separation preserves the historical record of GP-135's overreach AND gives the engine a focused target for the resolution work.
