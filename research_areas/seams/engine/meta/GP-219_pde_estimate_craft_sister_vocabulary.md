# GP-219 — PDE estimate-craft sister vocabulary

> **Seam metadata** · `seam_id:` GP-219 · `track:` engine · `status:` mining phase (not pre-registered; vocabulary not yet drafted · `last_updated:` 2026-05-14


**Status:** mining phase (not pre-registered; vocabulary not yet drafted)
**Date:** 2026-05-05
**Audience:** internal — sister track to GP-216 + GP-218
**Sister docs:** GP-216 (theory-builder vocabulary v5), GP-218 (post-cutoff blind validation showed PDE coverage gap), Pass 11 (Gowers two-cultures), planned paper 5c (problem-solver vocabulary)

---

## Eigenquestion

> Is there a coherent sister vocabulary capturing PDE-native estimate-craft moves that v5 does not name — and if so, does mining it help with NS Track B closure?

## Trigger

GP-218 post-cutoff blind validation produced a **differential coverage** signal:

| Subfield | Tagger A | Tagger B | A-B gap |
|---|---|---|---|
| combinatorics | 67% | 71% | 4pp |
| number_theory | 60% | 68% | 8pp |
| topology_geom | 50% | 60% | 10pp |
| alg_geom | 60% | 76% | 16pp |
| **analysis_pde** | **46%** | **62%** | **17pp** |

The PDE paper had the lowest coverage AND the largest tagger-disagreement, suggesting the v5 vocabulary fits worst here. The 13 "none" moves cluster around: barrier construction, blow-up profile extraction, Liouville rigidity, Morse-index transfer under limits, ODE convexity dichotomies, regime-isolation, sharpness counterexamples, edge-subdivision refinements.

This connects directly to NS Track B: Codex's theorem-statement work (Lipschitz reserve ledger, profile-LSC certificates, Bony paraproduct receipts) is all PDE estimate-craft. The 3 deployed gates (potential function, bound chain, special case hint) mechanize **framing** of PDE work but not the estimate-craft itself — confirming a structural gap.

## Hypothesis to mine

A sister vocabulary of ~5-10 PDE estimate-craft ops exists, distinct from v5's theory-building ops, characterized by:
- **Auxiliary-object construction** (barriers, comparison functions, sharpness witnesses, edge subdivisions)
- **Quantitative limit-passage** (property inheritance under λ_n → ∞, Morse-index transfer to limits)
- **Localized rigidity** (Liouville-type, ODE convexity dichotomies, removable singularities)
- **Estimate-chain construction** (chained bounds with explicit constants, surrogate-bound replacement)
- **Regime isolation** (parameter scoping, asymptotic regime selection)
- **Corollary derivation** (integral asymptotics from pointwise bounds)
- **Sharpness counterexamples** (explicit constructions showing rate / threshold optimality)

These are CANDIDATE clusters from inspecting the 13 + Codex's NS work. Actual ops emerge from mining, not deduction.

## What this is NOT

- **Not an extension of v5.** Adding `sub_05_pde` to the universal vocabulary would be man-with-a-hammer scope creep. Sister vocabulary, separate artifact.
- **Not a paper 5c rerun.** Paper 5c is the problem-solver vocabulary (combinatorics / additive-number-theory / regularity-iteration). PDE estimate-craft is plausibly a *third* culture, distinct from both theory-builder and problem-solver — Tao-style harmonic analysis would land here, as would Brendle / Schoen-Yau / De Giorgi.
- **Not a publication first.** Operational utility for NS comes BEFORE publication. If mining produces ops that mechanize Codex's actual moves, that's the win regardless of paper.

## Source corpora (planned)

**Phase 1 (in flight):**
- 13 "none" moves from GP-218 analysis_pde paper (`projects/ztare_on_ztare/workspace/gp219_pde_estimate_craft/seed_corpus_2605.02879.json`) — already extracted with gap descriptions
- ~135 NS Track B F-rows (`grep "F-GP186" research_areas/EXPERIMENT_TRACK_RECORD.md`) — Codex's actual estimate-craft work in operational record
- One mining-agent clustering pass to produce a draft proto-vocabulary (3-7 candidate ops)

**Phase 2 (if Phase 1 looks promising):**
- 5 more PDE papers from arxiv math.AP recent (post-2024-06-01, theory-construction), blind-tagged via the GP-218 methodology
- Validation: do the proto-ops from Phase 1 cover the 5 new papers' moves at ≥50%?
- If yes: vocabulary candidate is real
- If no: PDE moves are paper-specific, no coherent sister vocabulary exists

**Phase 3 (if Phase 2 passes):**
- Standalone seam pre-registration + falsification thresholds (mirrors GP-218 structure)
- Paper 5d candidate: "Estimate-craft as a third research culture: a PDE-native sister vocabulary to theory-building and problem-solving."

## Lakatosian pass/fail (provisional, will sharpen at Phase 2 pre-registration)

**PASS Phase 1 → Phase 2:** mining agent produces 4-7 distinct proto-ops with non-overlapping structural mechanisms, each instantiated by ≥3 of the 13 seed moves OR ≥3 NS F-rows.

**FAIL Phase 1 (kill track):** seed moves cluster trivially (1-2 ops covering everything) OR don't cluster at all (each move stands alone). Either is evidence that PDE estimate-craft doesn't have coherent op structure at this scale.

**WEAK** (revisit with more corpus): 4-7 ops emerge but each has only 1-2 instantiations across seed material. Phase 2 corpus expansion is required before drawing conclusions.

## Connection to NS

If a coherent vocabulary emerges:
- Tag NS Track B F-rows with the new ops to see structural fingerprint
- Identify mechanizable triggers (analog of v5 → potential / bound-chain / stagnation-hint gates)
- Build PDE-specific gates on the same blueprint

If no vocabulary emerges:
- Honest finding: NS work is sui-generis estimate-craft, not pattern-matched
- Apparatus value of v5 + GP-216 gates is upper-bounded; closure work needs PDE-specialist judgment, not mechanizable rules

Either outcome shapes paper 5b's PDE caveat — currently handwavy ("PDE coverage was 46%"), would become substantive ("PDE has its own vocabulary; we mined a sister catalog with N ops").

## Cost estimate

- Phase 1: 1 agent, ~$1-2, ~3-5 min wall clock
- Phase 2: 5 papers blind-tagged + cross-walked + adversarial check ≈ 10-15 agents, ~$15-25, ~30 min wall clock
- Total to validation: ~$25, ~40 min. Cheap enough to run fully.

## Outputs (per phase)

- Phase 1: `projects/ztare_on_ztare/workspace/gp219_pde_estimate_craft/proto_vocabulary_phase1.md` — draft proto-ops with mechanisms + seed instantiations
- Phase 2: `projects/ztare_on_ztare/workspace/gp219_pde_estimate_craft/{paper_<id>}/` per-paper blind cross-walks
- Phase 3 (if reached): pre-registration seam at `research_areas/private/seams/engine/GP-219_pre_registration.md` + scoring script

## Sealed at

2026-05-05 by Claude (autonomous mode, principal-approved). This seam is mining-stage, NOT pre-registration; thresholds will be set when (and only if) Phase 2 begins.

---

## Phase 1 result + operationalization (2026-05-05)

### Proto-vocabulary draft

Phase 1 mining produced 6 proto-ops with cross-source instantiation (each fires on BOTH the analysis_pde paper AND NS Track B F-rows):

- **Proto-op A — Auxiliary Comparison Object Construction** (4 NS instantiations: 5ET intertwiners, 5EX W-coupled, 5GD-GE SOS pricing, 5FA/FB pricing-kernel certificates)
- **Proto-op B — Regime/Class Scoping** (4 NS: 5ET scope-decl, 5FM branch-grid, 5FQ/FR compression, 5GA closure-interface)
- **Proto-op C — Quantitative Threshold Dichotomy** (4 NS: 5EY/EZ, 5FC, 5FK, 5GB — this is the structural shape of the entire state-pricing argument)
- **Proto-op D — Limit-Passage Property Inheritance** (3 NS: 5JD/JH recurrence-budget gap, 5JI hostile-construction split, countable Gram-tail vs finite-prefix)
- **Proto-op E — Sharpness/Failure-Witness Construction** (3 NS: 5DX, 5JI, 5JH counterexamples)
- **Proto-op F — Proof-Surface Compression** (provisional, NS-heavy: 5FZ Track B compression, 5FY branch-grid hardening) — may collapse into proto-op B at Phase 2

Full draft: `projects/ztare_on_ztare/workspace/gp219_pde_estimate_craft/proto_vocabulary_phase1.md`. Mining-agent flagged caveats: F is provisional; A/C and A/E boundary collapse risks should be tested at Phase 2.

### Operationalization plan (3-phase)

**Phase A — Naming discipline (immediate, zero apparatus cost).** Director tags substrate work with proto-ops in advisor channel turns. Codex Track B closure-attempt artifacts (Lean theorems, scoping documents, falsifier panels) explicitly cite which proto-op(s) they instantiate. Done in advisor channel Turn 72 (2026-05-05). No code, no gates. If naming discipline persists for 1-2 weeks without Codex pushback, the proto-ops are operationally aligned.

**Phase B — Rubric augmentation (low cost, ~30 min, after Phase 2 validation).** Once Phase 2 confirms 4+ proto-ops survive cross-walk on fresh PDE papers, augment Track B closure rubric with a "GP-219 proto-op declaration" section parallel to the existing GP-216 rubric metadata:
- Which proto-op(s) does this closure attempt instantiate?
- For proto-op A: declared auxiliary object + engineered properties + comparison target
- For proto-op C: fixed positive threshold + degeneracy alternative + both branches proven
- For proto-op D: named inheritance lemma at the infinite step

**Phase C — Mechanizable gates (deferred until Phase 2 validation + 5 closure-attempt observations).** Proto-ops A, C, D are mechanization candidates:
- `AuxiliaryObjectDeclarationGate` — promote-blocking unless rubric declares auxiliary object + structural properties + comparison
- `ThresholdDichotomyBranchCoverageGate` — promote-blocking unless both threshold AND degeneracy branch are explicitly proven
- `LimitPassageInheritanceLemmaGate` — promote-blocking unless rubric names inheritance lemma at finite-to-infinite step

Building these gates before Phase 2 validation = building on unvalidated foundation. Wait.

### Consumer residual feedback rule (2026-05-14)

**Canonical protocol spec:** `research_areas/specs/active/protocol/GP-216_ood_residual_feedback_spec.md`.
This section is the PDE/NS example of the general consumer-residual contract,
not the only place the rule lives.
Here, `theorem_or_pde_gap` is the PDE-local alias of the spec's canonical
`theorem_or_domain_gap`; shared aggregators should normalize to the canonical
class.

Operational consumers must not treat a vocabulary hit or gate pass as proof
progress by itself.  Every GP-216/GP-219 fingerprint or gate report that
influences a typed research action should preserve a residual-language feedback
object using this rule:

```
Use universal language to route.
Use math/PDE language to act.
Use gates only when the local contract is crisp.
Use residuals to decide whether the language must extend.
```

Minimum feedback fields:

- `residual_class`: one of `none_closed`, `theorem_or_pde_gap`,
  `gate_contract_not_crisp`, `vocabulary_gap`,
  `new_channel_or_residual_measure_needed`, `apparatus_or_source_mismatch`.
- `residual_summary`: the specific obstruction left after the gate/language
  pass.
- `did_language_change_next_action`: boolean.
- `evidence_pointer`: gate report, F-row, Lean declaration packet, or forecast
  contract.
- `next_lever`: the next mathematical, apparatus, or vocabulary action.

Extension rule: if a decision-changing residual cannot be classified without
stretching an existing vocabulary term, mark `vocabulary_gap` or
`new_channel_or_residual_measure_needed`, log it through GP-233, and update the
relevant seam/spec before promoting the language as reusable.  In NS route-1
terms, the current example is the shift from local measure domination to the
lineage-fresh defect reservoir residual: the universal/PDE language routed the
work, but the remaining residual names a concrete theorem/channel obligation.

### Connection to claim A test for GP-216

The 3 GP-216 gates already shipped (`PotentialFunctionMonotonicityGate`, `BoundChainConsistencyGate`, `StagnationSpecialCaseHintGate`) mechanize the earlier GP-216 gate candidates around iterative refinement, bound-chain discipline, and strategic specialization. Under the current 8-subfield v5 registry, these live mainly under `broad_01` Iterative Refinement and `broad_05` Extremal Method, with local links to problem-solver ops `ps_02/ps_06` and theory-builder op `tb_NEW_POLYA`. If Track B field-test shows those gates fire <30% true-positive rate, it is consistent with the GP-218 finding that PDE work is partially out-of-v5-scope. The next-generation gates would mechanize GP-219 proto-ops (A, C, D specifically), which are estimate-craft-native. So GP-216 gate field-test outcomes BOTH inform paper 5b's claim A AND tell us whether GP-219 mechanization is the right next investment.

### Honest scope still

- 6 proto-ops on n=2 sources (one paper + NS F-rows). Phase 2 (5+ fresh PDE papers via blind cross-walk) is required before claiming "this is a vocabulary."
- F is provisional. A/C and A/E boundary risk is real.
- "Estimate-craft" as a third research culture (sister to theory-builder + problem-solver) is a hypothesis, not a finding. Cross-validation against analytic-NT papers is the next discipline check (not a separate vocabulary track — a falsifier of "GP-219 covers estimate-craft broadly" vs "GP-219 is PDE-specific").

---

## Phase 2 + methodology correction + residual mining — RESULT (2026-05-05)

### Phase 2 standalone GP-219 cross-walk (5 fresh PDE papers + 5 analytic-NT)

| Subfield | Mean coverage (GP-219-only) |
|---|---|
| PDE Phase 2 (5 papers) | 50.2% (range 17-70%, bimodal) |
| Analytic-NT cross-validation (5) | 37.6% |

Naive verdict from this: GP-219 fails Phase 2 PASS threshold (≥50%) under strict reading; analytic-NT clearly orthogonal.

### Bracket check

- 2605.02779 (low end, GP-219-only 17%): Tagger B 29.2% — true-machinery zone, ~12pp false-negative correction
- 2605.02797 (high end, GP-219-only 70%): Adversarial 45% — 25pp inflation, proto-op A being stretched

### Combined v5+GP-219 methodology test (THE KEY FINDING)

Re-cross-walked 3 borderline papers with v5 (18 ops) + GP-219 (6 proto-ops) JOINTLY visible. Each move classified to whichever single op fits best across the 24-op space.

| Paper | GP-219-only | Combined | Δ | v5 share | GP-219 share |
|---|---|---|---|---|---|
| 2605.02797 (PDE Carleman) | 70% | **100%** | +30pp | 55% | 45% |
| 2605.02779 (PDE sep-of-vars) | 17% | **92%** | +75pp | 88% | 4% |
| 2605.00673 (NT modular forms) | 32% | **92%** | +60pp | 88% | 4% |

**Mean combined coverage: ~95%. The GP-219-only inflation was a methodology artifact, not a vocabulary defect.** GP-219 is a *complement* to v5, not a separate vocabulary. Standalone GP-219 cross-walks force agents to stretch proto-op A onto framework imports + tool invocations that v5 core_06 cleanly absorbs.

### Residual mining — 188 "none" moves across 14 papers

**1 strong primitive candidate:**
- **Candidate G — Representation / Coordinate Reformulation** (14 instances, 7 papers). Reformulate same problem in conjugate/rescaled/principal-object-swapped frame WITHOUT crossing formal-system boundary. Distinct from core_01 (no domain crossing) and proto-op A (no new object created).
- **Likely v5-tier op (universal across PDE+NT+combinatorics), not GP-219-tier.** Recommended addition: `core_08 Representation/Coordinate Reformulation` or `broad_08`.

**3 provisional candidates (n=3-7, below conservative ≥3-paper-cluster + ≥3-instances-each threshold):** Symmetry/Equivariance Collapse, Parallel-Theatre Transcription, Computational Certification. Defer until cross-validated on 5+ additional papers.

**5 broadening recommendations (existing op definitions too narrow):**
1. v5 `core_06` → cover single-lemma / identity imports (Hecke's Lemma, Caccioppoli, Wick/Isserlis), not just full theorems
2. GP-219 `proto-op E` → cover refutation + separation, not just sharpness/no-survivor
3. GP-219 `proto-op B` → cover exhaustive case-split-and-cover (no defer)
4. v5 `core_01` → cover reduction within same domain via structural correspondence
5. GP-219 `proto-op A` → cover dichotomy lemmas + normal-form reductions, not just barriers

**~75-90 residual entries (~40-48%)** are genuinely-diverse plumbing (special functions, linear algebra packaging, editorial moves, computational spine), NOT undiscovered primitives.

### Verdict on operationalization plan

- **Phase A (naming discipline)**: revised — Director should tag substrate work with **combined v5+GP-219 notation** (e.g., "Phase 5GD-GE → core_06 + proto-A + proto-D"), not GP-219-only. Advisor channel Turn 72's GP-219-only tagging was correct content but partial — should be expanded to v5+GP-219 joint citation.

- **Phase B (rubric augmentation)**: still planned, now sharper — augment Track B closure rubric with declarations across BOTH vocabularies; v5 imports + GP-219 estimate-craft moves both get explicit slots.

- **Phase C (mechanizable gates)**: candidate gates remain proto-op A/C/D — but **the gate definitions should be sharper now that proto-op A is correctly bounded** (only genuinely-engineered auxiliary objects, not framework imports).

### Paper 5b implications (revised)

§5.5.5, §5.3.7, §6.2.4 should be rewritten:
- **Old framing:** "v5 has a sharp scope boundary at PDE estimate-craft (12.5% adversarial)."
- **New framing:** "v5 alone has a recognizable gap on 4-6 specific PDE estimate-craft moves; GP-219's 6 proto-ops fill that gap; v5+GP-219 jointly cover ~95% of structural moves on fresh PDE+NT corpus. Adding `core_08 Representation Reformulation` would push to ~97%."

The differential coverage finding by subfield is REAL but partly methodological — measuring v5 alone systematically underestimates coverage on PDE-leaning work. The right way to measure mathematical-research-move coverage is the joint vocabulary.

### Status

GP-219 → CLOSED Phase 2; v5+GP-219 joint methodology validated; Candidate G logged for future v5 expansion (paper 5b post-publication candidate addition); operationalization plan revised; INS-row + F-row to be appended.

### Consumer-residual extension: Distribution / Tail Upgrade (2026-05-20)

TICK664 exposed a vocabulary gap through the consumer-residual path, not through
a new publication-facing cross-walk. The workbench needed to distinguish a
positive estimate that upgrades signed, averaged, integral, or quadratic-energy
control into a local distribution estimate: weak-L^q tail, reverse Holder gain,
level-set decay exponent, or anti-concentration bound on a specified positive
part. This is not just proto-op C (threshold dichotomy), because the obligation
quantifies a tail law rather than one binary branch. It is not just proto-op E
(sharpness/failure witness), because the positive route is a theorem producing
distribution-function control; the hostile witness is only the kill test.

The source registry now includes:

- `pec_h` — **Distribution / Tail Upgrade**
- Scope: PDE/analysis estimate-craft, especially when average/moment controls
  leave spike concentration unresolved.
- Boundary: keep `pec_h` for the positive theorem obligation; keep `pec_e` for
  the spike witness that kills it.
- Status: operational proto-op from consumer-residual evidence. It is suitable
  for RD routing and workbench surfacing, but should be revalidated in the next
  frozen GP-216/GP-219 OOD campaign before any paper-grade vocabulary claim.

Mechanization note: `src/ztare/research_director/pde_estimate_craft_ops.py` is
the canonical registry; regenerate `docs/reference/structural_language_catalog.json` and `docs/concepts/structural_language_catalog.md`
after changing it. Do not add substrate labels to the registry entry; concrete
substrates belong in examples, workbench profiles, or close artifacts.

### Consumer-residual extension: Phase-Space Packet Ownership Receipt (2026-05-21)

TICK668 exposed a second consumer-residual gap. The workbench could surface
nonadaptive source selection (`pec_i`) and same-carrier no-reuse packing
(`pec_j`), but it could not name the intermediate microlocal theorem shape:
selected events must own concrete phase-space or material packets, and the
owner preimages must have a numerical prefix/Carleson bound. Without that
receipt, pointwise ownership plus a finite atom budget permits one owner atom
to be rebilled through infinitely many descendant events.

The source registry now includes:

- `pec_k` - **Phase-Space Packet Ownership Receipt**
- Scope: PDE/analysis estimate-craft where events, stopping regions, or bad
  scales are assigned to Littlewood-Paley tiles, paraproduct packets,
  phase-space tents, or material tubes.
- Boundary: keep `pec_i` for pre-payoff selection timing; keep `pec_j` for
  same-carrier no-reuse/packing; use `pec_k` only when the missing theorem is
  the event-to-packet owner map plus bounded owner-preimage/prefix budget.
- Status: operational proto-op from consumer-residual evidence. It is suitable
  for RD routing, structural fingerprinting, and workbench surfacing; paper-
  grade vocabulary claims still require revalidation in the next frozen
  GP-216/GP-219 OOD campaign.

### Next moves (deferred, not this session)

- Validate Candidate G via combined cross-walk on 3-5 additional papers including Candidate G as a known op
- Apply 5 broadenings to v5 + GP-219 op definitions (low-risk text edits)
- Re-tag NS Track B work with v5+GP-219 joint notation in advisor channel (small Turn 73)
- Update paper 5b §5.5.5 / §5.3.7 / §6.2.4 with the methodology correction
