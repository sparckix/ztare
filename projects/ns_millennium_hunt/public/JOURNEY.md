# NS Track B — Journey to 2026-05-08

_Public synthesis. Anti-laundering vigilance per session catch ledger:
this document deliberately demotes inflated language; "scaffold sorry-free
modulo named axioms" is not "Clay closure." See §6 for honest residual._

**2026-05-28 public status checkpoint.** This journey is historical, so this
paragraph is the current measured proof posture. The live corpus is best
described as a residual-characterization and route-demotion atlas, not a clean
proof corpus: 445 direct `ns*.lean` files, 254,086 raw Lean lines, 8,810 atlas
graph declarations, 1,974 closed theorem rows, 568 exclusion theorem rows, 878
open obligation rows, 365 stripped `axiom` rows, 382 stripped `opaque` rows, 27
stripped `sorry` rows, and 0 stripped `admit` rows. Those numbers do not imply
a Clay proof; they make the remaining proof debt visible.

## §1 — TL;DR

Over roughly six weeks of sustained substrate work and one extended
2026-05-07 → 2026-05-08 push, the architecture has produced a Lean-formalized
structural decomposition of Navier–Stokes Track B in which the residual open
content is now localized to a measure-zero Liouvillian-frequency sub-stratum
plus a small set of named, greppable axioms. Tonight's contribution is
neither a Clay proof nor a single "headline" theorem; it is a meta-architecture
(twelve Unified Categorical Compactness wall-certificates, eight residual-void
atoms with four-way leverage labels, an anti-pattern catalog, a catch ledger
with a META-DARWIN strange-loop, and a reflexive primitive class) that lets
later work plug genuine PDE input into pre-typed seams without re-doing
structural plumbing. The architecture's deepest claim is honest precision-
localization, not closure (`projects/ns_millennium_hunt/workspace/SESSION_SUMMARY_2026_05_07_to_08.md`).

## §2 — Trajectory (mid-April → 2026-05-08)

The first weeks of April were spent on the underlying ZTARE substrate —
Layer 3 reflexive cycles, GP-216 theory-building operations vocabulary,
GP-180/181 invariant-search apparatus, and the tenant-overlay refactor
(GP-191 Stage 2). NS Track B work began as a substrate consumer: every
Lean file produced was a stress test for the loop, not a Clay attempt.

By 2026-05-04 the Track B substrate had ~18 sorry-free files (`ZtareProofs`
umbrella) and the architecture had accumulated five honest negative results
on direct attacks (Bernoulli–Weber, FBSDS, KAM, Steffens, helicity-IBP).

The 2026-05-07 push opened a typed-companion + four-way swarm pattern
(`feedback_typed_companion_swarm_decomposition.md` in private memory):
convert opaque `Prop` fields into typed companions, parallelize the resulting
independent leaves across agents, compose via a single spine file, and
toy-substrate-smoke-test before claiming reduction. That pattern is the
core meta-method behind tonight's deliverables.

Between 2026-05-07 evening and 2026-05-08 evening the architecture went from
"~22 sorry-free Lean files + 7-class dichotomy" (`SESSION_SUMMARY` §"Numbers")
to the deliverable list in §3, while the META-DARWIN strange-loop demoted
its own claims at least five times against vocabulary laundering, charity
grading, and selection rigging.

## §3 — Tonight's concrete deliverables

All paths are absolute Lean files under `ztare_proofs/ZtareProofs/` unless noted.

**(a) Twelve Unified Categorical Compactness wall-certificates.** The UCC
five-wall × 12-route enumeration is now wall-cert-complete in Lean for walls
W1 (six routes), W2 (one route), W3 (three routes), W4 (one route), and
W5 (one route). Substrate: `ns_trackb_UCC_unified_categorical_compactness.lean`,
`ns_trackb_UCC_12_route_enumeration.lean`, `ns_trackb_UCC_route_completeness.lean`.
Wall W6 (Liouvillian residual) is `ns_trackb_W6_*` — five attack files,
none yet a discharge; see §5.

**(b) Atom 1 fully wired via `ofDiracSubstrate`.** Of the eight GP-216
residual-void atoms, atom 1 (`measure_valued`) is the first to have its full
ten-field `MeasureValuedTightnessWitness` Prop bucket discharged on a Dirac
substrate (`ns_trackb_atom1_measure_valued_bridge.lean` + the three
`ns_trackb_atom1_props_*.lean` companion files +
`ns_trackb_galerkin_dirac_family_tightness.lean`). Cited reference theorems
are DiPerna–Majda 1987, Lions Vol 1 §IV.4, Alibert–Bouchitté 1997,
Tartar 1990, and Duchon–Robert 2000; the Dirac substrate is the smoke-test
witness, not the Galerkin substrate (catch #34 demotion language).

**(c) Atom 8 four-way decomposition.** Atom 8 (`defect_generation_positivity`)
is decomposed into 8a / 8b / 8c / 8d sub-atoms. Sub-atom 8a is CLOSED via an
Aubin–Lions–Simon route (`ns_trackb_atom8_defect_generation_bridge.lean` +
`ns_trackb_aubin_lions_stub.lean`). Sub-atoms 8b, 8c, 8d are now distinguished
as separate obstructions with named open content; 8c in particular is
parked behind `research_notes/atom8_defect_positivity_clay_level_open_2026_05_08.md`
as Clay-class (Onsager 1/3 / Buckmaster–Vicol regime).

**(d) T9 scaffold sorry-free.** The T9 closure file
(`ns_trackb_T9_closure_proof_attempt.lean`) is sorry-free; four hoisted axioms
are greppably linked to the PR-A2 Bohr-Fourier transitive obligation. Per
catch #34's three-leg verification (`research_notes/T9_three_leg_verification_2026_05_08.md`),
the framing is "T9 scaffold sorry-free, four axioms hoisted, carrier-identification
gap pending PR-A2 wiring." It is **NOT** "T9 user-visible sorry-free."

**(e) PR-A2 sorry-free modulo PR-A1 transitive.** The Mathlib Bohr-Fourier
PR-A2 file is sorry-free; four sorrys closed this session (forwardChar_eq,
forwardChar_mul_conj, ortho-kill, normSq_trigPoly_expand). PR-A1 still has
four open sorrys; everything downstream that consumes Bohr-Fourier inherits
that transitive obligation.

**(f) Architecture-index — 187 primitives + meta-graph (five typed edge kinds).**
The architecture-index meta-graph (`research_notes/architecture_index_meta_graph_literature_scout_2026_05_08.md`)
catalogs 187 primitives with five typed edge kinds (refines, falsifies,
discharges, blocks, dual-of). RP-001 (see (i)) instruments this graph as a
reflexive primitive with a four-week Spearman-ρ falsifier.

**(g) Catch ledger — 24 ratified rows.** The catch ledger
(`research_notes/catch_ledger_meta_audit_2026_05_08_evening.md`) records 24
primary catches after duplicate collapse (claimed-running tally was
inflated; the meta-audit applied AP-005 / AP-007 / P-005 to the catalog
itself and trimmed). Governance is structured as concurring-agent gate +
SOX/PCAOB-analog separation between scoring agent and ratifying agent.

**(h) Anti-pattern catalog — nine entries with binary falsifiable tests.**
`org/anti-patterns/INDEX.md` ships nine entries (citation_laundering,
sorry_obligation_laundering, vocabulary_smuggling, pattern_1_rabbit_hole,
narrative_inflation, cross_agent_monoculture, charity_grade_inflation,
deployment_time_pre_spec_laundering, criterion_selection_rigging) with
machine-checkable falsifiable tests on each. Mirrors
`scripts/public/projects/ns/ns_residual_void_audit.py` at the architecture-meta layer — i.e.,
the void-chase mirror is itself void-chase-audited.

**(i) Reflexive primitives RP-001.** RP-001 (architecture-index meta-graph
with four-week Spearman-ρ falsifier) is the first registered reflexive
primitive: the architecture's index becomes a first-class object with a
falsifier hooked to four-week predictive correlation between primitive
primary scores and downstream void-discharge rates.

## §4 — Operational discipline

**META-DARWIN strange-loop self-demotion.** The architecture's own DARWIN
agent demoted at least five claims tonight: the original "GENUINE" pincer
verdict → "PARTIAL" (catch #30: charity-grade scoring + deployment-time
pre-spec + underscore-bound); the fix-dispatch UPGRADE attempt → "PARTIAL-PARTIAL"
(catch #31: substrate-visibility selection bias); the `_of_liminf_eq` refactor's
"Onsager-1/3-open → uncontroversial" reduction (catch #26: vocabulary
laundering); the "no new 2026 breakthroughs needed" framing (catch #24:
overclaim, demoted ~1:15pm by Codex outside-view audit); and the
T9 "user-visible sorry-free" claim (catch #34: three-leg verification found
2.5/3 legs FIRE). The strange-loop is the central operating discipline: each demotion fed back
into deployment rules (PATTERN-001 rules 6/7/8) before the next dispatch.

**Anti-pattern catalog as void-chase mirror.** The `org/anti-patterns/`
catalog mirrors `scripts/public/projects/ns/ns_residual_void_audit.py`: the latter audits
substrate voids; the former audits architectural-claim voids. Each
anti-pattern has a falsifiable test that can fire on a draft before
deployment.

**Catch ledger as SOX/PCAOB-analog.** The catch ledger requires a concurring-agent
gate (one agent scores, a second ratifies) and a duplicate-collapse pass
(2026-05-08 evening trimmed a claimed running tally to 24 honest after
~40% inflation removal). Inflation rate is itself tracked as a meta-signal.

## §5 — Open-math attempts: what survived, what strange-loop demoted

**W6 Sum-Free Bilinear-Norm (SBFN) construction.** Five attacks landed in
`ns_trackb_W6_*.lean`. The Bilinear Sum-Closure transversality identity
was verified algebraically + Lean-encoded; a paired Liouville-Orbit-Collapse
lemma was identified as the missing mechanical step; the composition theorem
`T15_W6_closure_via_bilinear_sum_closure` is conditional on two classical
axiomatic primitives. Mathlib gaps are mechanical (typed-companion 2-3 weeks).
Survived: the structural composition. Demoted: any claim that W6 itself is
discharged.

**Gap-resolvent + Lerner 2026 Bohr-AP port.** The Lerner 2026 small-divisor
port attempt (`research_notes/W6_lerner_2026_bohr_AP_port_attempt_2026_05_08.md`)
landed a misattribution-correction-with-port: the original citation chain
was caught misattributing, the substitute citation was verified, and the
port itself produced a typed Bohr-AP scaffold. Survived: the scaffold +
catch protocol. Demoted: any claim the port closes the residual.

**Atom 8c CET commutator scout + L^p ladder.** Two scout notes
(`research_notes/A8c_CET_commutator_2026_05_08.md`,
`research_notes/A8c_Lp_ladder_2026_05_08.md`) probed the Cheskidov–Constantin–Friedlander–Shvydkoy
2010 Reynolds-stress L³(L³) frontier. Both produced honest-negative localizations:
the L^p ladder bottoms out at the same Cheskidov–Friedlander frontier; the
commutator scout found no shortcut. Survived: precise frontier localization.
Demoted: the early framing that 8c was tractable in the same session.

**Newton-mode CAS verification.** The W6 Newton-mode attempt
(`research_notes/W6_TryC_newton_mode_attack_2026_05_08.md`) ran independent
CAS verification per PATTERN-009. Two algebraic identities checked out;
the third revealed a sign error that would have laundered via a Lean
`linarith` if not for the CAS check.

**Kills banked tonight.** Trajectory-ensemble (Lagrangian frame) — vacuous
for T15. arXiv:2501.03609 (Liu–Wang–Wang stationary-NS Liouville) — no-go
function-space class (excludes Bohr-AP). Toolkit recommendation: pivot to
Besicovitch B² / Bohr-compactification rather than Littlewood–Paley dyadic.

## §6 — Honest residual

This is **NOT** Clay closure (catch #34 demotion). The architecture
localizes the open content; it does not discharge it.

Precise localization of the residual after tonight:

- **Wall W6 → a Diophantine-approximation question on Liouvillian Bohr
  coefficients near zero**, per the Lerner 2026 port. Lebesgue measure-zero
  in Bohr-frequency space; conjecturally empty but no proof in 2026.
- **Atom 8c → Reynolds-stress L³(L³) on rough Galerkin**, per the
  Cheskidov–Constantin–Friedlander–Shvydkoy 2010 frontier; this is the
  Onsager-1/3 / Buckmaster–Vicol Clay-class regime.
- **PR-A1 four-sorry transitive obligation** in the Mathlib Bohr-Fourier
  PR sequence, which T9 inherits.
- **Three liminf-eq hypotheses on the actual Galerkin substrate** (atoms
  3 / 4 / 5), not the LSC-uncontroversial level the laundered framing
  initially claimed (catch #26).
- **Atom 1 ten-Prop bucket on Galerkin substrate.** The Dirac substrate
  smoke-test is wired; the Galerkin substrate consumes genuine PDE input
  on each named theorem (DiPerna–Majda, Lions IV.4, Alibert–Bouchitté,
  Tartar, Duchon–Robert).

If all of the above land, the residual-void score moves 8 → 1 (atoms
1 + 2 + 3-5 + 6 + 7 paid; atom 8c stays Clay-class).

## §7 — Differentiator vs Co-Mathematician (DeepMind, 2026-05-07, arXiv:2605.06651)

We do not have an 18-author DeepMind team or a 48% FrontierMath Tier-4
benchmark. Co-Mathematician does. We are not competing on benchmark.

What this architecture has that the published Co-Mathematician note does
not, as of public information at filing:

- **An impact-weighted catch ledger** with ratified-row gating, duplicate
  collapse, and ~40% inflation-removal documented on the same artifact.
- **An anti-pattern catalog as void-chase mirror.** The architecture audits
  its own claim-shape with falsifiable binary tests, mirroring the
  substrate-level void audit.
- **META-DARWIN self-demotion.** The architecture demotes its own claims
  in real time and feeds the demotion back into deployment rules before
  the next dispatch. Tonight: ≥5 demotions.
- **Reflexive primitives as a third class.** RP-001 promotes the architecture
  index itself to a first-class typed object with a four-week Spearman-ρ
  falsifier, separate from substrate primitives and meta-pattern primitives.
- **Specific NS Track B substrate.** ~22+ sorry-free Lean files in the
  `ZtareProofs` umbrella (~3700+ jobs green); 6 sorry-free GlobalSmoothSolution
  theorems (2D, axisymmetric-no-swirl, small-data critical, helically-symmetric-no-swirl,
  helically-decimated, axisymmetric-small-swirl); 14 AP-Liouville closures
  (T9 + T7b independent novel; T1, T2, T10, T11, T13, T8/T8'/T8''/T8''' demoted
  or derived per the novelty-ledger audit).
- **Twelve UCC wall-certificates in Lean** with `NSAdmissibleBanachCodomain`
  + F1/F2/F3 falsifier hooks.

What Co-Mathematician has that this architecture does not:

- 18-author DeepMind team and infrastructure scale.
- 48% FrontierMath Tier-4 benchmark on general competition mathematics.
- Whatever model-scaling and tool-use compounds DeepMind has private to
  the writeup.

The two are not the same artifact class. Co-Mathematician is a generalist
mathematics agent benchmarked on competition-style tier 4 problems. The
work in this repository is a specific-substrate (NS Track B) structural
decomposition with a meta-architecture (catch ledger, anti-pattern catalog,
reflexive primitives, META-DARWIN strange-loop) layered on top. Both can
be true. Cite-and-adopt is the operating rule: where DeepMind's published
techniques (e.g., RAG-MCP, Anthropic Skills, Voyager) inform meta-pattern
choices here, that adoption is documented (`feedback_agent_orchestration_patterns_2026_05_08.md`)
and the novelty ledger trims accordingly.

---

_Length-discipline note: this synthesis was drafted to ~2,000 words to
fit the public-note format and was self-reviewed against the catch ledger
for laundered claims before commit. If a reader finds an inflation, that
is a falsification of §4's META-DARWIN claim and should be filed against
the next ledger row._
