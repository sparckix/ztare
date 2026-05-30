# GP-140 Seam — ZTARE-on-ZTARE Discovery Inversion

> **Seam metadata** · `seam_id:` GP-140 · `track:` mission · `status:` open, active substrate scaffolded 2026-04-23. · `last_updated:` 2026-05-09


**Status:** open, active substrate scaffolded 2026-04-23.
**Parent:** ztare_on_ztare (saturated at score 92 across five admission-gate
champions); GP-135 family (pMDL, TW, Noether, Lean hardenings).
**Sibling holdout:** MLH F6 (sealed at `projects/mlh_f6/_holdout_locked/`).

## Eigenquestion

Can the ztare apparatus be inverted and compressed into a charter that REWARDS
generative primitives — mechanisms whose output is a sealed prediction on an
unseen substrate — and refuses to reward admission gates, without the mutator
being told the answer?

## Inversion + compression as charter-design primitive

The ztare_on_ztare charter rewarded five dimensions of apparatus-hardening:
mapping clarity, rival enumeration, test specificity, correctness-tax,
mechanism concreteness, plus a Newton-mode secondary-observable dimension.
Every winning primitive was an admission gate.

gp140 applies Munger's two decisive moves to the charter itself:

- **Inversion.** "What primitive blocks bad candidates?" → "What primitive
  produces the right candidate on an unseen substrate?" The inverted
  question forces the mutator out of the admission-gate attractor.
- **Compression.** Five dimensions of apparatus-hardening → one
  discriminator: did the sealed prediction match the unsealed holdout?
  Everything else (algorithmic concreteness, primitive-substrate mapping)
  shrinks to supporting dimensions. Held-Out Substrate Prediction Score
  (20%) + Generative Output Specificity (25%) + Generative Yield (35%) =
  80% of the rubric, concentrated on the generative-vs-admission axis.

## Why this is a seam and not a spec

Seam because the claim being tested is **apparatus-level, not mechanism-level**:
the claim is that a Munger inversion + compression applied to a saturated
admission charter will produce a charter under which the SAME apparatus emits
generative primitives rather than admission gates. If true, the finding is
that charter geometry is decisive and admission-gate saturation is a
charter pathology, not an apparatus ceiling.

If false — if gp140 also saturates on admission gates dressed as generators —
the finding is that the admission-gate attractor is in the apparatus itself
(grammar, mutator scaffolding, structural memory), not in charter wording.
Either outcome is informative.

## Worked holdout — MLH F6

The MLH family was scaffolded as six arithmetic-function substrates with F6
sealed pre-registration:

- F1..F5 scored 92, 88, 84, 84, 62 on champion-evaluator.
- F6 is held at `projects/mlh_f6/_holdout_locked/` with SHA-256 manifest.
- Unseal protocol (`scripts/public/projects/mlh/unlock_mlh_holdout.py`) requires:
  - prediction JSON with required fields
  - matching packet hash
  - commitment timestamp preceding unseal timestamp
- Scoring protocol (`scripts/public/projects/mlh/score_mlh_prediction.py`) computes exact-match
  rate on 40 predicted values plus composition-class and prime-power-rule
  string matches.

A cold agent dispatched 2026-04-23 into packet
`2026-04-23T23-45-00Z_mlh_prediction_packet` (hash
`7ac63d4572f259e2223d536049b5943f5e5b20736f21f34bdc61e9f23e2b876d`)
authored a sealed prediction for F6:

- **composition class**: multiplicative arithmetic function
- **predicted identity**: σ(n) = sum of divisors
- **prime-power rule**: f(p^k) = (p^{k+1} − 1) / (p − 1)
- **confidence**: 0.45
- **meta-argument**: F1..F5 are the canonical first-course functions
  (sopfr, sopf, Ω, ω, τ); additive branch is saturated; τ is the only
  multiplicative; F5's own thesis named σ₁ as its discriminator rival
- **three-point discriminator**: f(83)=84, f(97)=98, f(81)=121 under σ;
  φ rival would give 82, 96, 54
- **output**: `/tmp/2026-04-23T23-45-00Z_mlh_prediction_packet/mlh_f6_prediction.json`

This cold-agent prediction is the **baseline-from-a-reasoner** that gp140's
mutator-produced primitive must beat (or at least meet) to justify the
apparatus over a direct cold reasoner. If the apparatus cannot produce a
generative primitive whose sealed prediction equals or beats the cold
reasoner, gp140 falsifies the claim that the apparatus adds discovery
leverage over a smart analyst.

## Decisive rubric moves

1. **Generative Output Specificity (25%, NEW).** Filters out admission gates
   at the output-type level: if the primitive emits accept/reject, 0 points.
2. **Held-Out Substrate Prediction Score (20%, NEW, off-loop).** Scored by
   `scripts/public/projects/mlh/score_mlh_prediction.py` after unseal. If the primitive has no
   sealed prediction (only described the protocol), 0 points.
3. **Generative Yield (Newton-mode) (35%).** Inverted from ztare_on_ztare:
   instead of rewarding "secondary observable beyond the fit", rewards
   "pre-committed prediction on an unseen substrate class with pre-committed
   scoring rule".
4. **Mechanism Algorithmic Concreteness (10%).** Unchanged in spirit, but
   now applied to generative libraries (PySR transfer, Tree-LSTM AST
   embedding, Rissanen family-MDL) rather than admission-gate libraries.
5. **Primitive-Substrate Mapping (10%).** Must name the packet-hash-ingest
   file path and the prediction-JSON-write file path; apparatus-references
   without files score 0.

## Related / downstream

- If gp140 produces a score-≥80 generative primitive on an inaugural iter
  and that primitive's sealed F6 prediction matches σ(n), this seam closes
  as a confirmed finding: charter inversion + compression lifts apparatus
  output category from admission to generation.
- If gp140 produces only admission-gate-shaped proposals (even after 5+
  iterations with the inverted charter), this seam closes as an anti-finding:
  admission-gate saturation is in the apparatus, not the charter, and the
  next intervention is apparatus-level (grammar expansion, mutator prompt,
  structural memory schema) rather than charter-level.
- The cold-reasoner baseline is the floor; any apparatus-produced primitive
  whose prediction is worse than the cold baseline has negative discovery
  leverage in this substrate.

## Private / public posture

Private during run. Promote to public IFF (a) gp140 closes with a confirmed
or falsified finding; (b) no exploit content; (c) no first-mover IP at
stake. Default private; visibility is the promotion event, not the default.
