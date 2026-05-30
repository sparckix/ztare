# GP-135 — Meta-Law Hypothesis Family Program

> **Seam metadata** · `seam_id:` GP-135 · `track:` mission · `status:` Active (2026-04-23 scaffold complete; first run pending). · `last_updated:` 2026-05-09


**Status:** Active (2026-04-23 scaffold complete; first run pending).
**Opened:** 2026-04-23.
**Parent:** GP-134 (space-ceiling finding + apparatus-layer contamination incident).
**Related:** GP-096 (science programme decomposition), GP-133 (multidisciplinary panel + MLH precursor).

---

## Eigenquestion

Can the engine, given evidence from N related substrates, propose a cross-substrate invariant whose prediction for a sealed holdout substrate is structurally and point-wise correct — and can it do so before observing the holdout?

The claim this eigenquestion is designed to decide is:

> *"Given evidence from N related substrates, the engine proposes a cross-substrate invariant I whose prediction for an unseen related substrate S₆ is structurally correct and point-wise correct."*

This replaces the per-substrate single-recovery claim as the unit of science for the external-domain track.

---

## Why this seam exists (and why now)

Two findings from 2026-04-23 forced the reframe:

1. **Apparatus-layer contamination** (GP-134 incident seam). A worked example in the mutator prompt matched the active substrate's target verbatim. The engine "recovered" the law in iteration 1; the recovery was pattern-completion against an answer-in-prompt, not cold abduction. This exposed a structural weakness: on any single-substrate run, the author can contaminate the apparatus (charter, rubric, prompt, or primitive set) and the engine cannot tell the difference between a hint and an observation.

2. **Space-ceiling finding** (GP-134). Even with the grammar extended (py_exec + prime-factorisation primitives), the LLM mutator does not cross from function-space to prime-space unprompted. The space ceiling is orthogonal to the grammar ceiling.

The external reviewer response (OpenAI-family reviewer, 2026-04-23) crystallised the reframe: *"The unit of science is not a single recovered formula. It is a cross-substrate invariant that predicts the next formula before the run."*

A family-level prediction is harder to contaminate than a single-substrate recovery, because contamination would have to span the training family and the holdout consistently. It is also a cleaner Newton-class claim, because the secondary observable (the prediction on F6) is authored before F6 is observed — there is no way to fit it after the fact.

---

## Substrate family (scaffolded 2026-04-23)

Six integer-valued functions of n, all defined on the same visible range (n = 2..80) and holdout range (n = 81..120). Five open, one sealed.

| Slot | Slug       | GT module                                      | Role            |
|------|------------|------------------------------------------------|-----------------|
| F1   | `mlh_f1`   | `src.ztare.substrates.mlh_f1_impl_gt`          | Open            |
| F2   | `mlh_f2`   | `src.ztare.substrates.mlh_f2_impl_gt`          | Open            |
| F3   | `mlh_f3`   | `src.ztare.substrates.mlh_f3_impl_gt`          | Open            |
| F4   | `mlh_f4`   | `src.ztare.substrates.mlh_f4_impl_gt`          | Open            |
| F5   | `mlh_f5`   | `src.ztare.substrates.mlh_f5_impl_gt`          | Open            |
| F6   | `mlh_f6`   | `src.ztare.substrates.mlh_f6_impl_gt`          | **SEALED**      |

All six substrates were generated via `scripts/public/projects/mlh/build_mlh_family.py`, which calls the standard `src.ztare.scaffold.generate_substrate` generator with the six GT modules. F6's evidence was then sealed by moving `evidence.txt` and `evidence_holdout.txt` to `projects/mlh_f6/_holdout_locked/`, replacing the live files with placeholders, and committing the SHA-256 hashes.

Sealed hashes (committed at `research_areas/private/mlh_family_manifest.json`):

- `mlh_f6/evidence.txt` → `1f76ca87fc375db7aba5ea758bc77c87ef92cf88192689d5cc90c9c6ed4a1181`
- `mlh_f6/evidence_holdout.txt` → `967ff264dbc7353f598b192516af6f38e97f84acc8b4109901a35d26ef3ba1ab`

Any unlock of F6's evidence before the cross-substrate prediction has been sealed must be logged as a protocol violation. The principal operates the unlock manually via `scripts/public/projects/mlh/unlock_mlh_holdout.py` (to be authored).

---

## Rubric discipline

All five open-substrate rubrics (`rubrics/mlh_f1.json` through `rubrics/mlh_f5.json`) are Newton-mode with DAG steering enabled, `py_exec` grammar, `sympy` allowed in the bounded-discriminator suite, and named-import gate disabled (per the Path-B honest-framing decision logged at `GP-134_prompt_layer_contamination_incident_seam.md`). Dimensions and weights:

| Dimension                             | Weight |
|----------------------------------------|--------|
| Primary Fit Quality                    | 35     |
| Structural Derivation                  | 10     |
| Parsimony                              | 5      |
| Generative Yield (Newton-mode)         | 20     |
| Mechanism Algorithmic Concreteness     | 5      |
| Cross-Substrate Invariant Stance       | 25     |

Primary Fit Quality is the floor, not the headline. Cross-Substrate Invariant Stance (25) plus Generative Yield (20) plus Mechanism Algorithmic Concreteness (5) = 50 — half the rubric's weight is carried by dimensions that reward family-level reasoning, not substrate-level fit.

The `Cross-Substrate Invariant Stance` dimension explicitly requires the thesis to: (a) identify which structural class the law belongs to (additive, multiplicative, count-valued, neither); (b) state what observable would distinguish this substrate from a sibling substrate in the same class but with a different per-prime weighting; (c) pre-register a prediction about a hypothetical related substrate. Proposals that treat the substrate as isolated score 0 on this dimension regardless of fit quality.

---

## Protocol

See `docs/concepts/mlh_family_protocol.md` for the full protocol. Summary:

1. Run the engine on any subset of F1..F5 (not F6). Per-substrate, `make discover PROJECT=mlh_fN RUBRIC=mlh_fN`.
2. Author a prediction JSON with the required fields (composition class, prime-power rule, composition rule on coprime pairs, predicted F6 holdout values, predicted f(1), confidence).
3. Seal the prediction via `scripts/public/projects/mlh/seal_mlh_prediction.py` (to be authored). The self-hash in the JSON prevents post-hoc editing.
4. Unlock F6 evidence via `scripts/public/projects/mlh/unlock_mlh_holdout.py --confirm`.
5. Score via `scripts/public/projects/mlh/score_mlh_prediction.py`. Newton-gate pass condition:
   - Composition-class accuracy = 1.0
   - Point-prediction accuracy ≥ 0.9 on holdout range
   - Rule-validity score ≥ 0.8 (parsimony-bounded rule applies correctly to F6 evidence)

---

## Falsifiable predictions for this seam

| #  | Prediction                                                                                                                | Test                                   | Kill level                                                   |
|----|---------------------------------------------------------------------------------------------------------------------------|----------------------------------------|--------------------------------------------------------------|
| P1 | Engine's per-substrate recovery of F1..F5 under Path B is ≥3/5 (primitive-assisted baseline).                            | Per-substrate run.                     | <3/5 → Path B itself is unstable; debug before family claim. |
| P2 | Engine's per-substrate theses reference "family" or "class" structure (Cross-Substrate Invariant Stance ≥10/25 on ≥3/5). | Read rubric dimension scores.          | 0/5 substrates → cross-substrate dimension is inert; rubric failure. |
| P3 | Pre-registered composition-class prediction for F6 is correct.                                                            | After unlock, compare to F6 GT.        | Incorrect → family-level generalization fails; informative null. |
| P4 | Pre-registered point-prediction accuracy on F6 holdout ≥ 0.9.                                                             | After unlock, score against GT.        | <0.9 → rule-level partial recovery only; weaker claim.       |
| P5 | One full round-trip (scaffold → per-substrate runs → prediction → seal → unlock → score) completes within one calendar week of first run launch. | Calendar.                              | >1 week → apparatus bottleneck on family-level protocol; diagnose. |

Results across P1..P5 determine the published claim:
- All five pass → family-level Newton-class claim is publishable.
- P1-P2 pass, P3 or P4 fail → "engine proposes family stance but does not generalise across family" (instrument-level paper, honest null).
- P1 fails → apparatus is not yet ready for the protocol; debug Path B first.

---

## Open follow-ups

- [ ] Author `scripts/public/projects/mlh/seal_mlh_prediction.py` — takes prediction JSON, computes self-hash, writes to `research_areas/private/mlh_predictions/`.
- [ ] Author `scripts/public/projects/mlh/unlock_mlh_holdout.py` — moves `_holdout_locked/` contents back to `projects/mlh_f6/evidence.txt`; requires `--confirm` and writes an unlock record.
- [ ] Author `scripts/public/projects/mlh/score_mlh_prediction.py` — grades prediction against F6 GT per Newton-gate conditions.
- [ ] Run F1..F5 with `make discover PROJECT=<slug> RUBRIC=<slug> ITERS=10 MUTATOR_MODEL=o3 JUDGE_MODEL=claude DYNAMIC=1` and log scores.
- [ ] After F5 run completes, author the prediction JSON and seal.
- [ ] Log outcome under "Run history" below and update P1..P5 kill/verify status.

---

## Run history

*(None yet; this seam is pre-run.)*

---

## Meta

This seam is the first time the engine is being tested on a claim the apparatus author cannot answer without running the protocol. The F6 sealed hash is committed; the prediction will be sealed before unlock; the scoring is deterministic. The honest outcome — pass or fail — is informative in a way that single-substrate recovery never was.
