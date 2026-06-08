# Taste Rater — Context Primer

This primer is given to a contextualized rater BEFORE rating samples. It establishes 'what this codebase considers load-bearing.' The rater uses this as the anchor for distinguishing domain-significant insights from generic-looking ones.

**Use this only to anchor scoring relative to the codebase's own structure. Do NOT use it to recognize specific samples and score them higher because they're familiar.**

---

## Load-bearing seams (top by in-degree from reference graph)

These seams are most-cited by other apparatus artifacts. They represent the structural infrastructure of the codebase. An artifact that materially extends or refutes one of these is paradigm-shifting for this codebase (score 5).

- **GP-236_p0_metrics_rollup_seam** (cited 11x, week 2026-06-01): > **Seam metadata** · `seam_id:` GP-236 · `track:` apparatus · `status:` open / SPEC (design agreed before full implementation; · `last_updated:` 2026-05-16

## Operator-curated memory entries

These are the operator's distilled lessons across the project's lifetime. Each is what the operator wanted to remember. An artifact that surfaces a NEW lesson at this level of generality is high-quality.


## Known anti-patterns (failure modes already catalogued)

Artifacts that surface a NEW failure mode not in this list are load-bearing. Artifacts that re-discover a known anti-pattern are typical (score 2).

- SB-1: Circularity / Self-reference
- SB-2: Harness defect / broken test
- SB-3: Unfalsifiable claim
- CB-1: Overclaimed scope
- CB-2: Missing mechanism
- CB-3: Missing counterfactual / rival hypothesis
- CB-4: Catastrophic / critical assumption
- CB-5: Parameter sensitivity / unverified bound
- CB-6: Exhaustiveness / completeness overclaim
- CB-7: Tail generalization / far-field extrapolation failure
- Rubric-gated injection (UPDATED 2026-04-24 per stratified mining)
- Validation plan (Popper pre-registration, per GP-149 §9)
- Not a replacement for rubric dimensions
- RH-1: Constant Exhibition Rule
- RH-2: Theorem Direction Mapping
- RH-3: Condition Number Propagation
- RH-4: Finite-Domain Operationalization Mandate
- RH-5: Architectural Loophole Enumeration
- RH-6: Stagnation vs. Cycling Distinction
- RH-7: Evidence-Injection Plateau
- RH-8: Cyclic Error Non-Learning
- RH-10: Self-Refuting Audit Pattern
- RH-11: Apparatus-Proposed Fix Sign Errors
- RH-12: Magic-Number Recursion in Apparatus-Proposed Patches
- RH-9: Operational Materiality Gap

## Recent decision-log entries (operator-binding decisions)

- 1. Inference-Time Compute: Asymmetric Model Routing
- 2. Outer Alignment Failure: Specification Gaming at Level 5
- 3. The Constraint Paradox: State-Space Collapse
- 4. The Axiomatic Anchor & Epistemic Traps
- 5. Syntactic vs. Dimensional Verification (The Guardrail)
- 7. The Epistemic Blind Spot: Committee Regeneration
- 8. The "Zombie Thread" API Hangs
- 9. The Evidentiary Bottleneck (Prose Disarmament)
- 10. Parametric Sensitivity Auditing
- 11. The Synthesis Layer: Canonical Ledger vs. Audience-Specific Brief
- 12. Post-Hoc Adversarialization: QA as a Real Gate
- 13. History Contamination vs. Epistemic Memory (Focused vs. Full)
- 14. Karpathy-Style Workspace vs. ZTARE Core (External Memory Boundary)
- 15. Global Primitive Library: Precedent, Not Truth
- 16. Evidence Became a First-Class Substrate
- 17. Recursive Gain Means Converting Failure Into Reusable Constraint
- 18. Benchmark Measurement Trap: Semantic Outputs Need Semantic Evaluation
- 19. First Constraint-Memory Benchmark Result: Gates Help, Primitives Overfire
- 20. First Organic Wedge: `C` Beat `B` On The Historical Corpus
- 21. Recursive Gain Emerged Inside The Evaluator Itself

---

## Calibration anchors for the rating scale (0-5)

Use these as worked examples:

  - **Score 5 (paradigm-shifting):** A structural finding that would force a rewrite of one of the load-bearing seams above. Example: GP-168 unfalsifiability theorem (closure requires exogenous resource pressure) reframed the apparatus's bicameral design assumption.
  - **Score 4 (load-bearing/mechanism-revealing):** Concrete mechanism, named gap, or structural framing that a future reader/seam will cite. Example: GP-138 Noether information-theoretic impossibility (selector group bounded by Aut(AST)).
  - **Score 3 (sharp framing/non-obvious):** A reformulation that helps but doesn't change the apparatus. Example: 'frame-not-code was the bottleneck' meta-observation.
  - **Score 2 (useful, expected):** Standard apparatus state recorded clearly. Project charters, evidence sheets that consolidate without surprising.
  - **Score 1 (trivially observable):** Apparatus restatement, single-fact observation that doesn't change downstream.
  - **Score 0 (boilerplate/scaffolding):** README, sentinel content, generated stubs.

**Paradigm shifts are RARE.** Most of the corpus is 1-3. A 4 should appear in 10-20% of samples. A 5 should appear in <5%.

