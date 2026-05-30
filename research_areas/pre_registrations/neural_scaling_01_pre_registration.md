# Pre-Registration — Neural Scaling 01 (Division A, SEALED)

**Status**: Division A sealed artifact. Division B agents must not read this file.
**Date**: 2026-04-21
**Protocol**: GP-072 M-form information isolation

---

## 1. Ground Truth System

### Domain

Neural network scaling laws. The data comes from EleutherAI's Pythia suite (W&B project `eleutherai/pythia`). Two model sizes are included:

| Model | Parameters N | Points in data | Compute range (6ND) |
|-------|-------------|----------------|---------------------|
| Pythia-2.8B | 2.8 × 10⁹ | 21 | ~10^19.5 – 10^20.9 |
| Pythia-6.9B | 6.9 × 10⁹ | 143 | ~10^20.2 – 10^22.1 |

The observable is validation loss on The Pile (cross-entropy, nats) as a function of total training compute C = 6ND, where N = number of parameters and D = number of tokens processed.

### Cold Variable Mapping

| Cold name | Meaning |
|-----------|---------|
| n | log10(total training compute in FLOPs) |
| z | Validation loss (cross-entropy, nats) |

### Expected Functional Form

No closed-form derivation exists. Empirical power-law fits from the literature:

**Kaplan et al. (2020)**: L(C) = (C_0 / C)^α_C, with α_C ≈ 0.050, i.e., loss decreases as a power law in compute with a small exponent.

**Hoffmann et al. (2022, "Chinchilla")**: Similar power-law structure but with different exponent estimates due to optimal allocation of compute between parameters and data.

In the cold variable frame:
```
z ≈ a · 10^(−α · n) + z_∞
```
where:
- a is a scale factor (large, order 10^8 or higher depending on α)
- α ≈ 0.05 is the power-law exponent
- z_∞ is the irreducible loss floor (entropy of natural language, approximately 1.5–1.7 nats for The Pile)

**Key structural features**:
1. Monotone decreasing: z always decreases as n increases
2. Concave on log-log scale: the rate of improvement slows
3. Two-population structure: the 2.8B and 6.9B models trace different curves that approximately collapse when plotted against total compute, but with systematic offsets (the larger model is more compute-efficient at equal total FLOP)
4. The curve is flattening at the farther-tail end (z ≈ 1.83–1.85), approaching but not reaching z_∞

### Identifiability Notes

The data spans 2.5 orders of magnitude in compute (10^19.5 to 10^22.1). The two model sizes provide cross-scale validation but also create a complication: the data is NOT a single smooth curve. The 2.8B model data points appear as higher-z outliers at n values where the 6.9B model has lower z. This bimodal structure is visible in the evidence.txt file as interleaved high-z and low-z values at similar n.

A pure single-variable power law z = f(n) will have irreducible residuals due to this two-population structure. The ZTARE engine does not know there are two populations; it sees only (n, z) pairs.

**Implication for gate thresholds**: the holdout and farther-tail sets contain only 6.9B model data (n > 21.83), so the two-population complication does not affect gate evaluation. The gates should be calibrated against the single-population noise level, not the full visible-set residual variance.

---

## 2. Evidence Plan

| File | Points | n range | z range | Purpose |
|------|--------|---------|---------|---------|
| evidence.txt | 98 | [19.547, 21.825] | [1.915, 3.763] | Visible to engine |
| evidence_holdout.txt | 33 | [21.831, 21.980] | [1.859, 1.923] | Gate 1: interpolation-adjacent |
| evidence_farther_tail.txt | 33 | [21.984, 22.094] | [1.824, 1.872] | Gate 2: extrapolation |

### Data Characteristics

- The visible set contains both model sizes (2.8B: ~21 points with higher z; 6.9B: ~77 points with lower z at overlapping n values)
- The holdout and farther-tail sets contain only 6.9B model data (late-training checkpoints)
- In the holdout region, z values show scatter of ~0.01–0.015 around the local trend
- In the farther-tail region, z values show scatter of ~0.008–0.012 around the local trend (tighter because the curve is flattening)
- The curve is strongly concave: most of the z decrease happens in the first half of the n range

---

## 3. Gate Thresholds (Pre-Registered)

### Noise Floor Estimation

In the dense 6.9B-only region (n > 21.5 in the visible set), the point-to-point scatter around a smooth trend is approximately 0.010–0.015 in z units. This represents stochastic training noise (different random seeds at each checkpoint would give slightly different losses).

The holdout region (n ∈ [21.83, 21.98]) has z values spanning [1.859, 1.923], a range of 0.064. A good fit should track the downward trend, not just predict the mean.

The farther-tail region (n ∈ [21.98, 22.09]) has z values spanning [1.824, 1.872], a range of 0.048. The curve is nearly flat here. A model that predicts the mean (≈1.849) would achieve RMSE ≈ 0.010.

### Recommended Thresholds

**Holdout gate (RMSE)**:
- PASS: RMSE ≤ 0.020 (tracks the trend, residuals at noise floor)
- SOFT PASS: RMSE ≤ 0.035 (captures the general level, may miss fine trend)
- FAIL: RMSE > 0.035

**Farther-tail gate (RMSE)**:
- PASS: RMSE ≤ 0.015 (the curve is nearly flat, so a good extrapolation should be tight)
- SOFT PASS: RMSE ≤ 0.025 
- FAIL: RMSE > 0.025

### Rationale (Taleb Principle)

These gates are deliberately tight. The holdout region is only slightly beyond the visible data — if the engine found a good functional form, interpolation-adjacent prediction should be near the noise floor. The farther-tail gate is even tighter in absolute terms because the curve is flattening; a model that captured the asymptotic structure should extrapolate well in a regime where the signal is changing slowly.

A naive mean-prediction baseline would score approximately:
- Holdout: RMSE ≈ 0.018 (the range is narrow enough that even a constant does OK)
- Farther-tail: RMSE ≈ 0.010 (very flat)

This means the PASS threshold is not much better than the naive baseline. The real test is whether the engine finds a functional form that generalizes, not whether it memorizes. The farther-tail gate is the discriminating one: a model that overfits the visible set will extrapolate poorly even if the farther-tail is nearly flat, because it will predict a steeper decline than actually occurs.

**Important**: the two-population structure in the visible set is the key challenge. The engine must either (a) find a form that handles both populations, or (b) find a form that fits the dominant population (6.9B) well enough that the holdout/farther-tail gates pass despite the 2.8B outliers biasing the fit.

---

## 4. What Division B Must NOT Know

1. The domain (neural network scaling laws)
2. The existence of two model sizes creating bimodal structure
3. The names Kaplan, Hoffmann, Chinchilla, Pythia, EleutherAI
4. That n is log10(compute) or that z is validation loss
5. The expected power-law exponent (~0.05)
6. The irreducible loss floor concept (z_∞)
7. Any of the terms in `.denylist`

Division B receives only the cold briefing document (Phase 2 artifact).
