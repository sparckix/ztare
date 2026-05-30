# GP-124, Process Compression: Measuring Dynamics, Not Products

> **Seam metadata** · `seam_id:` GP-124 · `track:` apparatus · `status:` OPEN · `last_updated:` 2026-05-17


**Status:** OPEN
**Opened:** 2026-04-22
**Category:** Apparatus / Engine / Architectural Gap

## The Void Finding

Across two independent tracks (neural architecture + Riemann Hypothesis),
ZTARE consistently recovered KNOWN structure from product measurements
and found NO NEW structure. The void analysis reveals:

- Neural: every post-hoc measurement of trained models (architecture,
  weight norm, weight decay, init norms, weight scaling) failed to
  identify the causal variable for alignment. The variable exists only
  DURING training.
- Riemann: every compression of zero-derived quantities (spacings,
  Li coefficients, Stieltjes constants) recovered known asymptotics.
  No new arithmetic structure found.

Both voids say the same thing: the answer is in the PROCESS, not
the PRODUCT. ZTARE measures products. The $1M gap is building a
process-measurement engine.

## Two Concrete Instantiations

### A. Neural: Training Dynamics Compression

Instead of measuring trained models, measure the TRAINING TRAJECTORY:
- Cancellation ratio at checkpoints every 100 steps during from-scratch training
- Gradient coherence (cosine similarity of per-layer gradients) per step
- Attention pattern entropy evolution
- Loss landscape curvature (Hessian top eigenvalue) at early checkpoints

The substrate: checkpoint_index → cancellation_ratio. If there's a
phase transition (cancellation drops sharply at step N), the transition
IS the finding. The form of the transition curve constrains what
training-time mechanism creates alignment.

### B. Riemann: Higher-Order Zero Correlations

Montgomery proved the pair correlation (2-point) follows GUE. But
higher-order correlations (3-point, 4-point, n-point) are:
- Conjectured to follow GUE (Bogomolny-Keating, Rudnick-Sarnak)
- Partially verified numerically (Odlyzko)
- NOT proven

If ZTARE compresses the n-point correlation and finds DEVIATION from
GUE prediction, that IS new mathematics. The deviation would encode
arithmetic information that pair correlation doesn't capture.

The substrate: for each n-point cluster of zeros, compute the
correlation function and present as z(separation_vector). ZTARE
compresses the correlation surface.

## The Architectural Gap

ZTARE is a first-order instrument: compress z(n) where z is a
static observable. Process compression requires a second-order
instrument: compress z(n, t) where t is a dynamics parameter
(training step, or correlation order).

The gap is 2D substrate support, ZTARE currently handles 1D
substrates (n → z). Process compression needs 2D (n, t → z) or
the ability to compress a FAMILY of 1D curves indexed by t.

## Connection to Existing Seams

- GP-121 (cross-entity substrates): the training trajectory IS a
  cross-entity substrate (each checkpoint is an "entity")
- GP-116 (neural architecture): the from-scratch A/B test with
  checkpointed cancellation is the first process-compression experiment
- GP-122 (Millennium): higher-order zero correlations are the
  Riemann process-compression experiment
- GP-097 (N-D manifold compressor): the infrastructure for 2D
  substrates may already exist here

## Debate Questions

1. Is process compression a genuinely new capability, or is it just
   time-series compression (which ZTARE already handles)?
2. For neural: is gradient coherence measurable from checkpoints, or
   do we need the actual gradients (which are discarded during training)?
3. For Riemann: are n-point correlations computable from 2000 zeros,
   or do we need millions?
4. Does 2D substrate support require a new compression primitive, or
   can we decompose into a family of 1D problems?
5. What is the minimum viable experiment for each track?
