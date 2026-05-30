# GP-114 — Spectral Dynamics of Neural Network Training (Paper 6 Candidate)

> **Seam metadata** · `seam_id:` GP-114 · `track:` engine · `status:` unrecorded · `last_updated:` 2026-05-08


Status: opening
Opened: 2026-04-21

## Eigenquestion

> Do LLM training dynamics exhibit universal spectral structure across model
> sizes, and is that structure stationary or detrending-sensitive?

## Motivation

The Pythia 6.9B model (143 evenly-spaced checkpoints) shows correlated
training residuals: spectral slope -0.72 (by compute) to -1.42 (by training
step), lag-1 autocorrelation 0.55-0.69. This was initially reported as
"white noise" when cross-model convergence snapshots were mixed into the
analysis, destroying the temporal structure. Separating within-model dynamics
from cross-model scaling recovered the signal.

The standard AI scaling law (L = a*N^(-alpha) + L_inf) assumes smooth,
independent residuals. If training dynamics have 1/f structure across model
sizes, the smooth-scaling assumption is fundamentally misspecified.

## What we have

- 6.9B: 143 checkpoints, slope -0.72 to -1.42, lag-1 0.55-0.69
- 2.8B: 21 checkpoints, slope -4.64 (likely detrending artifact at low N)
- Other 6 models: 1-4 points each (insufficient for spectral analysis)

## What we need

Dense longitudinal training logs (100+ checkpoints) for at least 3 more
Pythia model sizes. Options:
1. W&B has sparse data for most models (1-4 points). The dense logs may
   require pulling from Pythia GitHub checkpoints directly.
2. Run lm-evaluation-harness on published Pythia checkpoints (all stored
   on HuggingFace). This generates fresh eval data at each checkpoint.
3. Use a different model suite with denser public training logs (OLMo,
   GPT-Neo training logs if available).

## Verification protocol (before any claim)

Per the sieve noise lesson: the detrending sensitivity table MUST be run
on the neural 1/f finding before calling it 1/f. If the slope swings as
violently as it did for Lucky/Ulam (range 1.7), the claim is
"non-stationary training dynamics" not "Self-Organized Criticality."

Required:
- [ ] Dense training logs for 3+ model sizes
- [ ] Spectral analysis per model (step-indexed, not compute-collapsed)
- [ ] Multi-detrending sensitivity table per model
- [ ] Cross-model comparison: does the slope depend on model size?
- [ ] Panel review before any publication claim

## Relationship to Paper 5 / Experimental Math letter

The Exp Math letter includes the neural scaling result as a preliminary
cross-domain finding with appropriate caveats. Paper 6 would be a separate
publication IF the 1/f finding replicates across model sizes with controlled
detrending.

Target venue (if findings hold): Physical Review Letters or Nature Physics
(spectral characterization of optimization dynamics) or NeurIPS/ICML
(empirical scaling laws).

## Next actions

- [ ] Pull dense Pythia training logs (W&B or HuggingFace checkpoints)
- [ ] Run per-model spectral analysis with detrending table
- [ ] Panel review of results before framing
