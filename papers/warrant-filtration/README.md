# Warrant Filtration

**Claim.** A checkability-stratified gradual argumentation semantics: instead of weighting the edges of a bipolar
argument graph with chosen numbers, order them by an epistemic-checkability ladder (kernel-certified ≻
re-executable ≻ verbatim-quote ≻ unchecked) and run a continuous gradual semantics (the Quadratic Energy Model)
once per nested stratum, emitting an uncollapsed lexicographic strength *profile*. Zero free numeric parameters,
so it stays prior-free — the point of a governed setting. Paired with a refutation-preserving override lattice,
exact Shapley source-attribution, and per-source / derivation-lineage collapse.

**Status.** Draft v1. Positioned as a **short technical / workshop paper or preprint**, not a top-venue full
paper — see the paper's §7. The specific synthesis was found without direct precedent by a reviewer-grade
prior-art pass, but the empirics are demonstration-grade (four synthetic topologies, one model) and one
theoretical question (cyclic convergence) is left open and surfaced as an explicit non-terminal state rather than resolved.

**Honest framing.** Every ingredient is classical and cited, not claimed: gradual QEM [Potyka 2018];
Shapley-over-gradual-argumentation [Yin/Potyka/Toni, IJCAI 2024]; LLM→QBAF→gradual [ArgLLMs, 2024];
lexicographic strata [System-Z/Brewka 1989; Thimm & Kern-Isberner 2013]; ordinal certainty levels [possibilistic
argumentation]. The contribution is the assembly — present it as an assembly with its lineage named, not as
inventing stratified argument strength.

**Companion artifacts (this repo).**
- Method: `src/ztare/scenarios/strength.py` (filtration + QEM + override + collapse + Shapley),
  `research_signals.py`, `wager.py`, `warrant_promotion.py`.
- Experiment (reproduces §5, incl. the three-arm LLM-judge): `src/ztare/experiments/epistemic_lift_experiment.py`
  (`ZTARE_LIFT_LLM_JUDGE=1 ZTARE_LIFT_JUDGE_MODE=cold|structured|labeled`).
- Concept write-up: `docs/concepts/graded_reasoning.md`.

- [draft.md](draft.md)
