# GP-116 — Compression as Architecture Discovery (Karpathy Connection)

> **Seam metadata** · `seam_id:` GP-116 · `track:` engine · `status:` unrecorded · `last_updated:` 2026-05-08


Status: opening
Opened: 2026-04-22

*Note: All panelist names in this seam are fictitious personas used as
adversarial reasoning lenses. They evoke intellectual traditions, not
real individuals or endorsements.*

## Eigenquestion

> ZTARE compresses mathematical forms by stripping overparameterized
> surrogates to their minimal gate-passing core. Can the same principle
> be applied to neural network architectures — compressing a large model's
> internal representations to discover its minimal "cognitive core"?

## Motivation (Karpathy, April 2026)

Karpathy claimed a 1B parameter model on clean data could match a 1.8T
frontier model. The compression ratio (1800x) rests on the observation
that most parameters are memorization overhead for noisy training data.

ZTARE already implements this principle for function discovery:
- LLM mutator proposes at k=6-17 parameters (overparameterized)
- Compression strips to k=3 (minimal gate-passing form)
- The 5.7x compression on GP-088 is the mathematical analogue

The isomorphism:

| Karpathy | ZTARE |
|----------|-------|
| 1.8T model | LLM mutator proposals (k=17) |
| Cognitive core (1B) | Compressed form (k=3) |
| External memory | Evidence files |
| Data quality | Holdout gate severity |
| Memorization noise | Overparameterized terms that fail farther-tail |

## What would it take

1. **Substrate:** Internal representations of a transformer across training.
   Pythia checkpoints have model weights at every 1K steps.
   Observable: some scalar aggregate of the weight structure.

2. **Compression:** Run ZTARE on the weight evolution trajectory.
   Does the trajectory compress to a simple dynamical law?

3. **Architecture extraction:** If ZTARE finds that k out of N weight
   groups carry all the gate-passing structure, those k groups are the
   "cognitive core." The rest are memorization.

## Barriers

- Multivariate: weight matrices are high-dimensional. Current pipeline
  is univariate. GP-080 (bivariate) is the bridge but hasn't shipped.
- Observable design: what scalar aggregate of weights captures the
  relevant structure? Frobenius norm? Effective rank? Singular value
  distribution? This is the research question.
- Compute: loading Pythia checkpoints (14GB for 12B) requires GPU RAM
  for weight extraction, not for inference.

## Relationship to the session's findings

The observable rotation finding (Ulam compresses in reciprocal space)
suggests that the RIGHT observable is the key, not the RIGHT template.
For neural architecture: the right aggregate of weights might reveal
structure that raw weight values hide.

The capability freezing finding (12/65 tasks freeze early) suggests
that the cognitive core for specific tasks LOCKS early in training.
If ZTARE could identify WHICH weight groups freeze and WHICH keep
learning, that would validate the Karpathy split empirically.

## Panel 1: Knuth / Dijkstra / Karpathy / Shannon (2026-04-22)

*All panelist names are fictitious personas used as adversarial reasoning
lenses, not real individuals or endorsements.*

**Q1 (category error?):** Knuth/Dijkstra: partly yes. ZTARE discovers
scaling laws, not computation graphs. But Karpathy: it CAN discover that
attention is overkill for certain inputs. Shannon: ZTARE measures the
rate-distortion function; if it has a simpler achiever than attention,
ZTARE proves the architecture is wasteful.

**Q2 (what to measure?):** Four proposals, all reducible to univariate:
- Knuth: minimum description length of f(prompt, position) → logits, as function of depth
- Dijkstra: rank of Jacobian of each layer output w.r.t. input (rank vs layer index)
- Karpathy: attention entropy per head, clustered by behavioral type
- Shannon: mutual information I(X_l; X_{l+k}) between layer activations

**Q3 (univariate sufficient?):** Surprisingly yes for first experiments.
All four proposals reduce to univariate curves. Multivariate needed
only for interaction effects (CoT exchange rate).

**Q4 (simplest MacBook experiment):** Consensus: compress effective-rank-vs-layer
curve of a small model (Llama-3.2 1B or Pythia-410M). 16 points. If the curve
compresses to exponential decay, most layers are doing degenerate attention.
One hour on a MacBook.

## Execution Plan (reconciled)

All candidates are consistent: different observables of "where is the
transformer wasteful?" Run in parallel order of data accessibility:

1. **Effective rank vs layer** (Dijkstra/Knuth, Q4) — 16 points, univariate,
   one forward pass. Simplest. Scripts: need to build.
2. **Bracket challenge** (Candidate 0, Gemini Pro) — accuracy vs sequence
   length, synthetic data. Scripts: built (generate + eval).
3. **CoT exchange rate** (Candidate 1, Karpathy) — accuracy vs (P, T).
   Scripts: built but needs model that can do the task (70M too small).
4. **Attention entropy** (Karpathy, Q2) — per head per layer. Needs
   inference hooks. Future.

## Next actions

- [ ] Build effective-rank-vs-layer extraction script
- [ ] Run on Pythia-70M or Pythia-410M
- [ ] Run bracket challenge on Pythia-70M
- [ ] Feed both curves into ZTARE compression
- [ ] Compare: which observable reveals more structure?
