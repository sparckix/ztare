# STP result cards and the first target-conditioned AxiomPack wave

Read-only audit and executable preflight specification, 2026-07-17. No provider call, remote mutation, campaign launch, or official-store write was performed.

## Verdict

The Carr-Synopsis framing is a good seed architecture, with a strict distinction:

- A hidden-proof **result card** asks a prover to restate or reprove an accepted result and optionally shorten the proof. This is calibration and curriculum generation. By itself it rediscovers known mathematics.
- **Target-conditioned extension** takes an accepted card, its verified proof or an extracted lemma, and a frozen unresolved target, then proposes a nearby theorem whose value is measured by progress on that target. This is the scientific lane.

The current AxiomPack campaign has a suitable target: characterize exactly which elementary type-2 solutions reconstruct from their extracted second tetrahedral 4-groupoids. The existing `Fin 3` counterexample is already a credible frontier-priority candidate; the orbit/differential-mode classification is recurrence/calibration. An STP wave has not yet added a mathematical result.

The nearest literature supports each part but also gives the failure modes:

- Carr's *Synopsis* was explicitly a collection of propositions, formulae, and methods with abridged demonstrations; a contemporary review describes proofs as indications or references. That is the historical analogue for statement cards, not evidence that card replay yields new results: [Nature review, 1880](https://www.nature.com/articles/022582a0).
- STP selects conjectures that are barely provable by the current prover and trains on kernel-accepted proofs: [Dong and Ma, arXiv:2502.00212v4](https://arxiv.org/abs/2502.00212v4).
- Long-running solve-rate-only self-play drifts toward artificially complex statements. SGS repairs this by conditioning on unsolved targets and adding a Guide for relevance and clean formulation: [Bailey et al., arXiv:2604.20209](https://arxiv.org/abs/2604.20209).
- Proof shortening is a useful post-acceptance training operation; it has improved compile time and downstream prover training, but it optimizes a proof, not theorem usefulness: [ProofOptimizer, arXiv:2510.15700](https://arxiv.org/abs/2510.15700).
- False mutations should become counterexample training data instead of being discarded: [Learning to Disprove, arXiv:2603.19514](https://arxiv.org/abs/2603.19514).
- Measured lemma reuse matters: apparent library-learning gains can instead come from self-correction or self-consistency: [Library Learning Doesn't, arXiv:2410.20274](https://arxiv.org/abs/2410.20274).

## Governing object and lifecycle

The object is a **target-conditioned conjecture curriculum attached to one frozen objective lineage**. It is not a global corpus-growth job.

- Owner: the active AxiomPack T2-reconstruction lineage.
- Identity: target proposition hash + formal-context hash + epoch; candidate identity is its canonical logical/statement hash, not its short Lean name.
- Authority: an agent proposes; a separate statement reviewer checks source-to-formal faithfulness; Lean or the finite/SMT boundary checks truth or refutation; a separate Guide assesses target relevance; actual downstream use determines value.
- Lifecycle: frozen target and seed snapshot -> result-card replay -> conjecture proposal -> statement review -> proof/countermodel/language outcome -> target replay -> bank, refute, archive, or stop.
- Equality: canonical Lean declaration identity and statement hash. Target strings are insufficient because generic names recur across unrelated theories.

The implementation should be a campaign-local view over existing closure certificates, learning units, conjecture-book/no-good rows, theory-lineage synthesis, and solver boundaries. It does not justify a new STP registry or prover.

## Three independent gates

| Gate | Question | Authority | What it cannot establish |
|---|---|---|---|
| Statement faithfulness | Does this Lean proposition match the source result, definitions, quantifiers, coordinate convention, and intended mutation? | Independent reviewer with source artifact and statement, but no proof | Truth |
| Proof/refutation | Does a proof elaborate under allowed axioms, or does a finite/kernel certificate refute the statement? | Lean kernel and AxiomPack finite/SMT boundaries | Importance or novelty |
| Target usefulness | Did the result get cited in a target proof, improve matched target solve probability, or eliminate a declared characterization by counterexample? | Independent Guide plus causal target replay | Source faithfulness or truth |

Proof golfing is a fourth, post-acceptance operation. It must preserve the exact statement hash and axiom receipt and be scored by proof size and cold compile time. It supplies no theorem-interest credit.

## Corpus preflight: measured defects

The current certificate ledger produces 208 prover rows in memory, while the saved corpus contains 197 rows.

| Item | Measurement |
|---|---:|
| canonical in-memory rows | 208 |
| saved `prover_corpus.jsonl` rows | 197 |
| unique target strings | 138 |
| unique statement hashes | 208 |
| repeated target-name excess rows | 70 |
| raw statements containing a proof marker | 1 |
| unique AxiomPack targets extractable by current `_split_probe` | 1 / 10 |
| unique AxiomPack targets extractable by canonical namespace-aware resolver | 10 / 10 |

Ledger and saved-snapshot hashes at audit time:

- `adhoc_closure_certificates.jsonl`: `05711c5f22e5562ad879a5754dd6427fa31cb2eff378ce33d4814c2a51776825`
- saved `prover_corpus.jsonl`: `02b326574aa6c91a95cf97313c18b970193ce00d3d65e43d56250d91819f9671`
- saved manifest: `94c1b1607a0552de8a2505530b5e1c97f0aa8203281d2b44bb2fa817145f9163`

The proof leak comes from the first accepted `orbitAction_tetrahedron` certificate having a malformed reconstructed declaration boundary; a later carried artifact is correct, but first-seen alpha-dedup retains both because the malformed signature includes proof text. A result-card producer must select the authoritative carried artifact, parse the signature through the canonical namespace-aware declaration resolver, reject any proof token in the statement view, and keep only a proof hash/reference in the public card.

The namespace failure is general: `self_play_conjecturer._split_probe` converts `decl_blocks` to a dictionary and exact-matches the fully-qualified target against namespace-local declaration names; its regex preamble split has the same mismatch. The existing `resolve_theorem_target`, `extract_signature`, and `preamble_before_target` functions resolve all 10 AxiomPack targets. The repair belongs in this single parsing door; a basename special case would introduce collision risk.

The generic dry-run also shows a scientific routing failure. Eight globally shortest proofs produced six proposals, three passed gates, and none concerned AxiomPack. The prior live pilot closed only transfer-friendly typeclass variants. That is useful corpus top-up, but it does not attack the T2 residual.

## Hidden-proof card contract

A result card is a non-authoritative view over a governed certificate and learning unit. Minimum fields:

```text
card_schema
card_id = hash(statement_hash, context_hash, source_hash, epoch)
source_kind = formal_only | source_bound
source_ref + source_hash
target_identity + context_hash
lean_statement                 # signature only
statement_hash
hidden_proof_ref + proof_hash  # never proof bytes in the prover-facing card
statement_faithfulness_receipt # required for source_bound/science use
kernel_receipt
difficulty_receipt             # sampled proof attempts, not proof length alone
usefulness_receipt             # populated only after target replay
golf_variants[]                # exact statement hash and fresh kernel receipt
```

All 208 rows can in principle seed formal-only reproof/golf tasks after the one malformed row is dispositioned. They do not all carry enough source evidence to assert mathematical statement faithfulness. Science-facing cards must be `source_bound`; the T2 convention audit and primary-question audit supply that source layer for the reconstruction cards.

For STP conjecturing, the seed proof may be revealed to the Conjecturer after the hidden-proof replay. That matches STP's use of seed theorems, proofs, and extracted lemmas. The Prover for the new conjecture still sees no answer because no proof exists yet.

## Frozen AxiomPack seed deck

Five source-bound cards cover the current residual without using the recovered differential-mode theorem as if it were new:

1. `AxiomPackOrbitAction.commutingTranslations_factor_through_orbits`
2. `AxiomPackOrbitAction.commutingTranslations_orbit_action_representation`
3. `AxiomPackT2ReconstructionCounterexample.finalistOne_nonprojection_not_reconstructible`
4. `AxiomPackT2ReconstructionCounterexample.finalistOne_t2_reconstruction_counterexample`
5. `AxiomPackOrbitAction.orbitAction_reconstruction_iff_label_factorization`

The in-memory preflight extracted all five through the canonical resolver, confirmed that the statement views contain no proof/sorry marker, and bound statement, probe, and hidden-proof hashes. The combined card snapshot hash was:

`ca0d2c979b57a2a6f636a710f95a7ab6d4327da6da70a76c065f010432b5c573`

The current generic structural mutators produce only five raw variants across these cards: one typeclass variation and four hypothesis drops. That is insufficient coverage of the reconstruction target. The missing proposal operation is target-conditioned conjecturing through the existing frozen-context theory-lineage route, not more hard-coded AxiomPack mutations.

## Minimum discriminating wave

### Frozen target

> Characterize, with necessary and sufficient conditions, the elementary type-2 solutions whose extracted second tetrahedral 4-groupoid reconstructs the original ternary operation.

Source artifacts:

- `t2_reconstruction_question_prior_art_audit.md`
- `t2_reconstruction_convention_audit.md`
- `t2_reconstruction_obstruction_pencil.md`
- `AxiomPackT2ReconstructionCounterexample.lean`
- `AxiomPackOrbitAction.lean`

### Replay and conjecture sequence

1. Freeze the five-card snapshot and the target/context hashes.
2. Hidden-proof replay: four proof attempts per card. Record difficulty; do not count reproof or golf as science.
3. Reveal each verified seed proof to the Conjecturer with the frozen target. Ask for two target-advancing conjectures per seed, giving at most ten candidates.
4. An independent Guide scores relevance, clean formulation, non-redundancy, and the exact target edge. Admit the top six after recurrence, coordinate-permutation, well-formedness, and triviality gates.
5. For each admitted candidate, run finite/SMT countermodel search first where semantics exist, then LeanMill proving. A counterexample is a learning unit and updates the characterization lattice.
6. Replay the frozen target at matched `K=4` with and without admitted results. Record direct citations, remaining proof state, and counterexample-eliminated branches.
7. Golf only kernel-accepted proofs; preserve statement and axiom hashes.

`K=4` makes the wave small and supports a coarse 1/4 “barely provable” flag. It is not enough for a training-quality difficulty curve. If the wave changes the target residual, the next experiment can use the STP-style larger sampling band.

### Candidate families requested from the Conjecturer

- weaken or remove middle injectivity, faithfulness, source fixing, normalization, or diagonal identity;
- characterize reconstructible basepoint orbits (`some c` versus `every c`);
- replace label equality by equality modulo the action kernel when the action is not faithful;
- generalize the identity inverse-slice to a nontrivial unary extraction and derive its factorization law;
- find a minimal additional T2-groupoid identity that forces basepoint factorization;
- construct or refute converse directions from label/cocycle data to elementary type-2 solutions;
- transport statements through verified coordinate/term equivalences, while treating known differential-mode matches as recurrence controls.

### Outcome algebra

- `proved_useful`: kernel proof plus a direct target citation or matched target lift;
- `proved_unused`: archive/training only, no curriculum credit;
- `refuted_discriminating`: countermodel eliminates a declared characterization branch;
- `recurrence`: known theorem under canonical coordinate/term fingerprint;
- `language_gap`: typed successor-language request, then resume the same lineage;
- `unresolved`: retain with its exact budget and residual, no truth label.

### Continue and kill conditions

Continue only if the six-candidate wave yields at least one of:

- a kernel-accepted lemma actually cited in a stronger target proof or partial derivation;
- a certified counterexample that eliminates a declared necessary/sufficient-condition candidate;
- a typed language gap whose resolution exposes a previously unavailable target experiment.

Kill or redesign the wave if:

- accepted results merely reprove/golf existing cards;
- all candidates are transfer variants, coordinate recurrences, or known differential-mode statements;
- solve rate rises while target citations and target replay stay flat;
- statement complexity grows while semantic-image diversity and Guide relevance fall;
- all sampled pass rates are 0 or 1, so no frontier band exists;
- provider work is dominated by language unavailability or malformed-card failures;
- no target residual changes after the six resolved candidates.

## Launch blockers and smallest general repairs

Before any paid or remote wave:

1. Bind the run directly to a canonical certificate-ledger snapshot or refresh the saved export; record source-ledger and card-deck hashes in the manifest.
2. Replace `_split_probe`'s dictionary/regex target lookup with the existing namespace-aware declaration-resolution door. No AxiomPack name special case.
3. Reject malformed/reconstructed statement views, keep hidden proof bytes outside the card, and select the strongest carried/governed certificate for a logical identity.
4. Route transfer and new closures through the canonical closure/learning-unit path; `self_play_corpus.jsonl` currently has no exporter consumer.
5. Select seeds by the frozen objective lineage instead of global shortest-proof order. Reuse theory-lineage synthesis for target-conditioned proposals and the existing usefulness/interest surfaces for Guide inputs.
6. Keep the existing blind corpus-growth script as a baseline/top-up job. Do not let its closure count stand in for target progress.

After those repairs, the five-card replay plus six-candidate wave is the smallest experiment that can answer the question that matters: whether self-play changes the T2 reconstruction residual rather than merely increasing the proof-pair count.
