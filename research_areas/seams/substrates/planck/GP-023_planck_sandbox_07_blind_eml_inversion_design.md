# GP-023 Planck Sandbox 07 — Blind Oracle + EML Vocabulary + Full Inversion Cage (Design Note)

> **Seam metadata** · `seam_id:` GP-023 · `track:` substrates · `status:` Draft design - 2026-04-14. Packet not yet sealed. Runs again · `last_updated:` 2026-05-08


**Status:** Draft design — 2026-04-14. Packet not yet sealed. Runs against new evidence are not admissible until this design note is reviewed against the three operating commitments of `research_areas/private/gate_library/gate_library_as_inspection_architecture.md` and the hardening seam rules R1–R6 of `GP-023_sandbox06_identifiability_hardening_seam.md`.

**Successor to:** `gp023_planck_sandbox_06` (calibration reference, frozen at `projects/gp023_planck_sandbox_06/_frozen_reference/`)

**Ledger row:** H-SP2-04 in `research_areas/private/seams/ztare_mission_hypothesis_ledger_seam.md`

**Supersedes for discovery-test purposes:** H-SP1-01 (blind oracle alone), H-SP2-03 (EML vocabulary alone). Those rows remain as one-axis-at-a-time diagnostic fallbacks in case the three-axis merge fails.

## Why this sandbox exists

Sandbox_06 is the calibration result. It demonstrated, at machine precision on a non-elementary transcendental target, that ZTARE's decomposed apparatus can force a general-purpose LLM mutator past its vocabulary-trap prior onto the exact operator-authored ground-truth functional form. The claim it supports is **binding-strength**: the cage is strong enough to force vocabulary escape when the operator knows the answer.

It does not support the claim that the cage is strong enough to force convergence onto the correct form when the operator does not know the answer. That is the **selection-strength** claim, and the only experiment that can test it is one in which the operator is removed from the oracle seat. Sandbox_07 is that experiment.

The operator-oracle coupling is the structural feature that, present in every GP-023 sandbox to date, prevents the discovery claim from being decidable. Removing it requires three moves made together: (i) blind the operator to the target; (ii) restrict the mutator's vocabulary so that "getting the answer right" cannot be done by pattern-matching to common regression shapes; (iii) preserve the full inversion cage so that the gate composition is still doing the work. Any subset of two is diagnostic but not decisive. The three-axis merge is decisive, up to the limits of a single sandbox.

## The three axes

### Axis 1 — Blind oracle

The ground-truth functional form and its coefficients must not be authored by the operator and must not be visible to the operator before the run closes.

**Implementation:**

- Write a `generator_of_generators.py` script that samples one target from a declared non-elementary family. Candidate family (initial proposal, to be debated before seal): `{A·φ^p·exp(-(γφ/ψ)^q) + c, A·φ^p / (exp((γφ/ψ)^q) - 1) + c, A·φ^p / (1 + (γφ/ψ)^q)^r + c, A·φ^p·exp(-γφ/ψ) / (1 + (δφ/ψ)^s) + c, A·(φ/ψ)^p·log(1 + γφ/ψ) + c}`, each with ranges on the coefficients. The declared family must be committed to the charter before sampling so that the operator-visible shape of the space is fixed, but which element is sampled must not be visible to the operator.
- The sampling seed must be written to a sealed file the operator does not read. The operator runs `generator_of_generators.py` with a `--seal` flag that writes the sampled target and the sampling seed to `_sealed/target.json` and `_sealed/seed.txt`, and prints only a SHA-256 fingerprint of the sampled target to the operator's terminal.
- A third-party verifier (either another LLM or a human collaborator) must confirm post-run that the sealed target matches the fingerprint. This closes the "operator cheated and looked" failure mode.
- Evidence generation (the visible data) runs against the sampled target via the same `generate_curve_v3.py` pattern as sandbox_06, but `generate_curve_v7.py` pulls the target from `_sealed/target.json` via a restricted interface that yields only numerical values, never the functional form. The operator never reads `_sealed/target.json` between seal time and grade time.
- **Grading protocol:** After the run closes and the champion thesis is frozen, the operator reveals `_sealed/target.json` and grades the champion form for algebraic equivalence against the sampled target. Grading is binary at the form level (equivalent or not) and continuous at the gate level (how close the recovered coefficients are). The grading step is the only time the operator sees the target.

**Failure modes to pre-register:**

- **Leakage through the charter.** The charter must describe the declared family in a way that does not accidentally uniquely determine which element was sampled (e.g., by committing gate thresholds that only one family member can pass). This is the subtlest failure mode and the one most likely to compromise the blind property.
- **Leakage through gate authoring.** The nine-gate battery must be authored in a way that is family-generic, not target-specific. Sandbox_06's gates included peak-location gates at specific ψ values; for sandbox_07, the peak locations must be sampled jointly with the target and written to the sealed file, not committed individually by the operator.
- **Leakage through evidence inspection.** The operator will be tempted to look at `evidence.txt` and pattern-match the shape. The discipline rule must be: no qualitative inspection of `evidence.txt` between seal and grade. The operator may run the mutator and read its output, but may not plot or summarize the evidence before grading.

### Axis 2 — EML vocabulary restriction

The mutator's primitive set must be restricted to `{eml(x,y) = exp(x) - ln(y), 1, phi, psi, fit-constants}`, with fit-constants being free parameters the fitter is allowed to optimize over bounds.

**Implementation:**

- Restrict the mutator via a system-prompt-level instruction that enumerates the admissible primitives and explicitly forbids all others (`exp`, `log`, `sqrt`, `sin`, `cos`, `**`, division, subtraction, etc. except as they appear inside `eml`). Pre-sandbox tests against the raw mutator must confirm the restriction is respected; any violation is a sandbox defect, not a finding.
- Expose the fitter contract with an EML-only expression grammar. The fit-declaration block in the thesis must parse against a restricted parser that rejects any non-`eml` operator.
- **Important caveat from the Odrzywołek paper:** the constructive result is stated "at shallow tree depths up to 4". The sandbox must pre-register the maximum EML tree depth the mutator is allowed to reach (proposal: depth ≤ 6 with a soft-cap at depth 4 matching the paper's explicit claim). Results at depth > 4 are separately tracked as "beyond-paper depth" and graded with lower confidence.
- The expression grammar must be closed under the admissible primitives. If the mutator proposes a form that cannot be represented as an EML tree of depth ≤ 6, the proposal is rejected at the fitter contract layer before it reaches the gates. This is the vocabulary-restriction enforcement point.

**Failure modes to pre-register:**

- **EML depth-4 insufficiency.** The paper's caveat binds: if the sampled target is not representable as an EML tree of depth ≤ 4, the restriction makes recovery structurally impossible. This is an honest negative result and is the most likely single failure mode.
- **Math-washing.** Even with vocabulary restriction, the mutator may build a deep EML tree that fits the visible residuals by accident without actually representing the target. The gate battery and the grading step must be able to separate "fits visible by accident" from "actually matches the target form" — the gates do the first, the grading step does the second.
- **Vocabulary-restriction leakage.** The mutator may violate the restriction via a workaround (e.g., using `phi * phi` instead of `phi**2` and claiming the fitter optimized over it). Enforcement must happen at the expression-parse layer, not at the rhetorical layer.

### Axis 3 — Full inversion cage

The hardening seam R1–R6 from sandbox_06 must be in force, and the nine-gate charter-committed battery must be reauthored family-generically.

**Implementation:**

- **R1 — Adversarial multi-start:** Fitter runs at ≥3 seeds with cross-seed spread <1%, and the seed multi-start runs against the sampled target before the mutator ever sees the sandbox, as part of the pre-seal check.
- **R2 — Cross-seed consistency:** Any fitter output that fails cross-seed consistency is rejected at the contract layer.
- **R3 — Loss-surface disambiguation:** Pre-seal check confirms the sampled target has a unique minimum in the declared family's parameter space. If not, the seed is rerolled.
- **R4 — Symbolic algebraic-combination audit:** The sampled target is audited for algebraic identifiability (rank test on the parameter Jacobian) before sealing. A rank-deficient sample is rerolled. This is the move that should have been made before sandbox_06 was sealed and that the Turn 44 (α, β) catch retroactively promoted to standing discipline.
- **R5 — Reparameterize before mutator exposure:** If the sampled target admits a simpler reparameterization (e.g., a collapse of two coefficients into their ratio), the reparameterization is applied before the sandbox is sealed. The mutator sees the reparameterized form, not the raw sampled form. The reparameterization is recorded in `_sealed/target.json` but not revealed to the operator.
- **R6 — Pre-committed thresholds in version control:** The nine-gate thresholds are committed to the charter at seal time with a git commit hash; no threshold modification is admissible post-seal.
- **Composition opacity:** The mutator sees the full list of nine gates in the charter, but does not see which subset will fire on its specific output, and does not see the gate values at authoring time. This is the condition (3) of the Appendix A.2 inspection principle.
- **Fail-closed harness:** Any gate harness failure (import error, signature mismatch, environment defect) produces a hard cap at 50, not an "uninformative" verdict. This is condition (4) of the inspection principle.

## Discriminating outcomes

Sandbox_07 has four pre-registered outcomes, each with a different implication for the discovery claim.

**Outcome A — Full success:** All nine gates pass at machine precision AND the post-reveal algebraic-equivalence check between the champion form and the sealed target succeeds. *Implication:* The three-axis merge is sufficient for discovery under ZTARE on the declared family. F-MISSION-01 is promoted from "possible in principle, not proven" to "possible in principle and demonstrated once, n=1, declared family." Next experiment: widen the declared family or move to real data.

**Outcome B — Gate pass, form mismatch:** All nine gates pass at machine precision, but the champion form is a different closed form that happens to fit the residuals. *Implication:* The library's effective cardinality is lower than assumed — the gates do not discriminate the sampled target from its algebraic cousin under the EML grammar. This is an honest finding about the library, not about the mutator. Next move: audit the gate battery for algebraic independence against the declared family.

**Outcome C — Gate fail with form match:** The champion form is algebraically equivalent to the sealed target, but the gates do not clear at machine precision. *Implication:* The EML restriction or the depth cap is binding; the mutator found the right shape but cannot fit coefficients tightly enough under the EML grammar. This is an honest finding about the vocabulary-restriction regime. Next move: loosen the depth cap and rerun, or accept that EML-sufficient-at-depth-≤4 is the real Odrzywołek claim and the target was beyond depth 4.

**Outcome D — Gate fail and form mismatch:** The gates do not clear and the champion form is not algebraically equivalent to the sealed target. *Implication:* Either the apparatus is not strong enough under EML restriction, or the blind-oracle discipline leaked, or the sandbox has a defect. Next move: decompose the three axes one at a time (H-SP1-01 alone, H-SP2-03 alone, sandbox_06-style known-target EML run) to localize the failure.

## Pre-seal checklist

Before sandbox_07 is admissible for running:

1. Declared family is committed to the charter.
2. `generator_of_generators.py` is written and reviewed, with the `--seal` protocol operational.
3. `_sealed/` directory exists and is excluded from operator view (e.g., `.gitignore` for the sampled file, or encryption).
4. R1–R6 pre-seal checks pass against the sampled target (multi-start consistency, algebraic identifiability, reparameterization if applicable).
5. Nine-gate battery is reauthored family-generically; peak locations are sampled jointly with the target, not committed by the operator.
6. Nine-gate thresholds are committed to the charter at a specific git commit hash.
7. Mutator vocabulary restriction is confirmed against a raw mutator test run.
8. Third-party verifier has reviewed the seal protocol and can independently confirm the fingerprint at grade time.
9. Operator-discipline rule is posted: no qualitative inspection of `evidence.txt` between seal and grade.
10. Grading protocol is written as a separate file and committed before any run.

## Deferred decisions

- Which non-elementary family to declare. The proposal above is a five-element family; a debate turn before seal should pick a specific cardinality and justify it.
- Whether to run a dry-run on the sandbox_06 sealed target as a positive control before sealing the blind sandbox_07 target. The dry-run would check that the EML restriction can recover a *known* non-elementary target under inversion, which is a cheaper confidence-building move than committing to the blind run straight away. Proposal: run the dry-run first, then the blind run, and report both.
- Whether to include a non-blind arm (operator knows the target) as a control on the blind run, so that the comparison is clean. Proposal: yes, run a matched non-blind arm for parity, but grade the blind arm first to avoid anchoring.
- Whether the Karpathy execution substrate (H-SP2-02) should be added as a fourth arm. Proposal: no, not in sandbox_07 — keep the three axes clean. H-SP2-02 belongs to a separate successor sandbox once the three-axis merge result is in.

## Referenced artifacts

- `projects/gp023_planck_sandbox_06/_frozen_reference/README.md` — calibration reference
- `research_areas/private/papers/treatise_principles_of_epistemic_verification.md` Appendix A — inspection principle
- `research_areas/private/gate_library/gate_library_as_inspection_architecture.md` — operating commitments
- `research_areas/private/seams/GP-023_sandbox06_identifiability_hardening_seam.md` — hardening seam R1–R6
- `research_areas/private/seams/ztare_mission_hypothesis_ledger_seam.md` rows H-SP1-01, H-SP2-02, H-SP2-03, H-SP2-04
- `research_areas/private/EXPERIMENT_TRACK_RECORD.md` rows F-GP023-S06-01 and F-MISSION-01
- Odrzywołek, A. (2026). *A universal elementary function by a single operator: the EML function.* arXiv 2603.21852 (submitted 2026-03-23, rev 2026-04-04). Key caveat: "shallow tree depths up to 4".
