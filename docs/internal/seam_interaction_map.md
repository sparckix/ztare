# ZTARE Seam Interaction Map

```yaml
topology: network          # seams are nodes; dependency edges are typed
format_version: gp101-v2   # structured blocks + typed DEPENDS_ON edges + lookup table
last_updated: 2026-04-20
purpose: >
  Token-optimized AI self-reference. Prevents the class of errors where the
  operator or agent acts on one seam without consulting the others it depends on.
  Lead with lookup table — that section catches 80% of errors alone.
```

---

## EDIT-INTENT LOOKUP TABLE

> "I want to do X → I MUST consult Y before acting"

| Intent | Must consult | Why |
|---|---|---|
| Create a new sandbox / Phase B experiment | GP-072 (protocol) + GP-075 (rubric) + GP-085 (grammar reachability) | Division A/B isolation is load-bearing; rubric Layer 4 constraints fire immediately |
| Write or edit a rubric JSON | GP-075 spec + GP-086 cage/kernel table | GP-075 Layer 4 hard-constrains `enable_component_c`; GP-086 governs which flags are CAGE vs KERNEL vs RUBRIC |
| Set `enable_component_c` | GP-075 Layer 4 — STOP | Hard constraint: `false` in discovery mode regardless of LLM suggestion. Self-referential operation = oracle contamination |
| Declare grammar ceiling (GCH) | GP-095 first, GP-085 second | Must rule out convergence failure and ill-conditioning before invoking GCH. Wrong order burns iterations |
| Inject a new grammar primitive | GP-095 (confirm ceiling) → GP-087 (residual shape) → GP-085 (GCH confirmed) | Primitive injection is the intervention for true GCH only; GP-087 gives the residual diagnostic signal |
| Add a gate to autoresearch_loop | GP-086 channel table | Three distinct channels: CAGE (gate_harness.py), KERNEL (autoresearch_loop.py), RUBRIC (json). Wrong channel = low durability or fragility |
| Promote a gaming pattern | GP-086 promotion table | Must go miner → promotion table → implementation, not operator intuition directly to code |
| Build a goal / stepping-out task | GP-070 (orchestrator) + GP-071 (inbox) | Runners (findings_runner, autoresearch_loop, supervisor_autoloop) are inputs to the orchestrator, not peers of it |
| Create a new reflexive primitive | GP-102 (cron audit trigger) | Primitives are discovered via periodic audit of stagnation signals, not crisis response |
| Add multi-regime topology exploration | GP-103 (H-GP103-5 + H-GP103-4) | Read PHASE_G1.5 in arch map + structural_memory.py; gp103_stagnation_threshold rubric flag controls firing |
| Decide Phase B is complete / open Phase C | GP-096 claim ladder | Phase B clean requires Outcome A on ≥1 substrate; Phase C gate opens only then |
| Advance a finding to public writeup | GP-083 (inference type) + GP-082 (substrate scope) | Output type must be "simplest surviving structural form" not "true law" — GP-083 enforces epistemic honesty |
| Place a pre-registration document | GP-072 protocol + AGENTS.md | Goes in `research_areas/private/seams/` not in project root or raw/ |
| Edit test_model.py or gate_harness.py function names | autoresearch_loop `_ensure_canonical_model_aliases` | GP-035 always writes `def f()` + `model = f`; harnesses should look for either. Fix at generator, not consumer |
| Wipe a sandbox workspace | raw/wipe_sandbox.py (task #137) | Removes run artifacts only; never touches evidence*, harness, charter, thesis, raw/ |
| Generate a qualitative project / rubric | GP-104 + GP-054 review_rubric.py | TYPE_B_GATE_CONFIG required; RUBRIC_SYSTEM_PROMPT Rule 7 persona modeling failure mode; charter_spirit_coverage check fires pre-run |
| Detect high-score qualitative Goodharting | GP-105 (M-Form Alignment Audit) | High early scores on qualitative projects are the primary signature of rubric Goodharting; GP-105 is the runtime immune system |
| Run supervisor findings promotion | GP-036 + GP-031 | Findings Runner → Supervisor convergence; birth bridge controls how findings graduate from run artifacts to seam entries |
| Expand grammar vocabulary / primitives | GP-099 (vocabulary floor) + GP-085 (ceiling check) | Must confirm floor (what's reachable now) before declaring ceiling; prevents redundant primitive injection |
| Build multi-project synthesis / ledger | GP-033 + synthesis/ledger.py | GP-033 governs cross-substrate generalization; ledger.py is the RAM layer accumulation |
| Modify evidence compressor / compile_evidence.py | GP-098 (evidence compressor) | Raw → structured evidence pipeline; preserves contradictions; ZTARE-external accumulation layer |
| Change autoresearch_loop.py | Arch map FIRST | 4100-line file with strict pipeline ordering; read `docs/internal/autoresearch_loop_architectural_map.md` before any edit |

---

## FILE → SEAM OWNERSHIP TABLE

> "I want to touch file X → I MUST check its governing seam first"

**Before modifying any file below, check its governing seam.** Load-bearing seams encode why the current design exists, what failure class it addresses, and which invariants cannot be violated.

| File / Component | Governing Seam | Seam Location | Why it matters |
|---|---|---|---|
| `src/ztare/validator/autoresearch_loop.py` | Arch map | `docs/internal/autoresearch_loop_architectural_map.md` | 4100-line pipeline with strict ordering contract; 8 named invariants; 4 exit taxonomies |
| `src/ztare/rubrics/review_rubric.py` | GP-054 | `research_areas/seams/protocol/GP-054_rubric_quality_and_generation_seam.md` | 6 pre-run checks (incl. charter_spirit_coverage); changing CHECK_NAMES changes output parsing |
| `src/ztare/scaffold/generate_gp_project.py` | GP-104 + GP-104B | `research_areas/seams/protocol/GP-104_qualitative_rubric_gate_configuration_seam.md` | TYPE_B_GATE_CONFIG omissions cause hard fails; RUBRIC_SYSTEM_PROMPT persona Rule 7 is the charter-spirit fix |
| `src/ztare/composition/structural_memory.py` | GP-103 | `research_areas/private/seams/GP-103_topology_induction_gap.md` | H-GP103-5 trigger guard, warm-start invariant, additive composite seeds |
| `src/ztare/validator/test_thesis.py` | GP-055 | `research_areas/private/seams/engine/GP-055_meta_judge_parse_robustness_seam.md` | Judge prompt structure, charter injection (line ~866), drift check advisory-only |
| `src/ztare/gates/` (any gate file) | GP-046 | `research_areas/seams/protocol/GP-046_asymptotic_regime_claim_discipline_seam.md` | Farther-tail gate, extrapolation gap — disable keys required for qualitative projects |
| `src/ztare/fit/fit_primitive.py` | GP-035 fit contract | arch map §PHASE_C + §PHASE_D | INV-3 (layer3_exclusive): when enable_fit_primitive, LLM python NEVER used for def f() |
| `src/ztare/primitives/` or grammar | GP-085 + GP-097 | `research_areas/private/seams/mission/GP-085_grammar_ceiling_hypothesis_seam.md` | Grammar wall exits, Feynman wall detection, composition stagnation |
| `src/ztare/primitives/` vocabulary | GP-099 | `research_areas/private/seams/engine/grammar/GP-099_vocabulary_floor_seam.md` | Floor declaration prevents redundant injection; governs what's reachable vs what isn't |
| `projects/*/gate_harness.py` | GP-072 | `research_areas/private/specs/active/GP-072_role_separation_sandbox_construction_spec.md` | Division A/B boundary; denylist; smoke gate must be canonical path |
| `src/ztare/validator/core/information_yield.py` | GP-073 | `research_areas/private/seams/gaming/GP-073_subliminal_learning_reproduction_seam.md` | Yield decision drives stagnation pivot; shared init vulnerability |
| `src/ztare/rubrics/` (any rubric JSON) | GP-079 | `research_areas/private/seams/protocol/GP-079_persona_library_unification_seam.md` | Persona routing, static vs. dynamic generation |
| `src/ztare/orchestration/` | GP-070 | arch map §6h | Goal stage gates; `make experiment-loop` auto-configs; advance CLI |
| `src/ztare/validator/runner_r4_fixture_regression.py` | GP-080 | private postmortem `gp080_continuous_model_contract_missing_2026_04_17.md` | Branch audit: every rubric flag value must have explicit contract coverage |
| `src/ztare/synthesis/synthesize.py` | GP-033 | `research_areas/private/seams/apparatus/instrumentation/GP-033_multi_project_synthesis_generalization_seam.md` | heuristic_project_type() entry point; multi-project ledger integration |
| `src/ztare/supervisor/supervisor_findings_runner.py` | GP-036 | `research_areas/private/seams/apparatus/supervisor/GP-036_findings_runner_supervisor_convergence_seam.md` | Findings Runner → Supervisor pipeline; context-awareness requirements; actor dispatch |
| `src/ztare/supervisor/supervisor_attended_autoloop.py` | GP-031 | `research_areas/private/seams/apparatus/supervisor/GP-031_findings_birth_bridge_seam.md` | Controls how findings graduate from run artifacts to seam entries; birth bridge invariants |
| `src/ztare/supervisor/supervisor_backlog.py` | GP-070 + GP-071 | seams at `apparatus/supervisor/` | Backlog is input to goal orchestrator; executive inbox governs human-signature gates |
| `src/ztare/validator/core/latent_distance.py` | GP-061 corrector | `research_areas/private/seams/apparatus/supervisor/GP-061_constraint_accumulation_as_output_seam.md` | Constraint accumulation primitive; void-driven steering signal |
| `src/ztare/validator/fit_multistart_replay.py` | GP-095 | `research_areas/private/seams/mission/GP-095_...` | Multi-start convergence classification; n≥3 required for GCH ruling |
| `src/ztare/validator/autoresearch_loop.py` (PHASE_G1.5) | GP-103 | `research_areas/seams/protocol/GP-103_topology_induction_gap.md` | Compositional hypothesis generator; gp103_stagnation_threshold rubric flag |
| `src/ztare/validator/information_yield.py` | GP-040 | `research_areas/private/seams/apparatus/instrumentation/GP-040_throughput_instrumentation_seam.md` | Cost+throughput accounting; cycle-time instrumentation |
| Any rubric `"persona"` field | GP-054 + GP-104B | see GP-054 and GP-104 above | Persona must name at least one specific modeling failure mode (Rule 7) |
| `config/goals/` (cron yaml files) | GP-102 | `research_areas/private/seams/apparatus/instrumentation/GP-102_reflexive_primitive_discovery_seam.md` | Kaizen cron; periodic primitive audit trigger; not crisis-response |
| `docs/internal/*.md` (self-model files) | GP-101 | `research_areas/private/seams/apparatus/instrumentation/GP-101_agent_native_self_model_format_seam.md` | Format spec: lookup table + invariants as minimum viable AI self-model |

**Coverage gaps (load-bearing but seam does not yet exist):**
- GP-105 (M-Form Alignment Audit) — seam being opened 2026-04-20; runtime rubric Goodhart detection for qualitative projects
- `src/ztare/validator/structural_memory_fixture_regression.py` — fixture regression test for GP-103 structural memory; no dedicated seam
- `src/ztare/composition/` catch_grammar modules — no seam; governed implicitly by GP-085 + GP-099

---

## INVARIANT CONTRACTS

```
INV-1: Division A/B information isolation
  ASSERT: No Division B-visible file contains GT vocabulary
  CHECK: sentinel (leak_sentinel.py) against raw/.denylist before seal
  TRAP: sandbox_construction_record.md at project root — Division A doc visible to B
  DEPENDS_ON: GP-072

INV-2: enable_component_c = false in discovery mode
  ASSERT: rubric["enable_component_c"] is False when operating in Phase B/C
  CHECK: grep rubric JSON before run starts
  WHY: Component C reads residual surface to guide next topology — self-referential
       when the engine is the thing being tested. Oracle contamination, not a feature.
  TRAP: LLM (Gemini) suggested enable_component_c=true + hallucinated flags
        (discovery_mode, holdout_budget) not consumed by autoresearch_loop.py
  DEPENDS_ON: GP-075 Layer 4

INV-3: Grammar ceiling requires convergence ruling first
  ASSERT: GCH is only declared after multi-start fitting (n≥3) with explicit
          OptimizeResult metadata reviewed
  CHECK: GP-095 convergence classifier output before invoking Component D
  TRAP: Langevin sandbox_16 — engine never proposed coth topology (additive bias),
        which looked like GCH but was search failure. Gate calibration 22,000× gap
        confirmed grammar was sufficient.
  DEPENDS_ON: GP-095 → GP-085

INV-4: Canonical model aliases in test_model.py
  ASSERT: Every test_model.py written by any path exposes both f() and model()
  CHECK: _ensure_canonical_model_aliases() called at all three write points in autoresearch_loop
  TRAP: sandbox_18 gate_harness expected model(); GP-035 wrote f() → harness defect,
        score 0 every iteration. Fix: generator emits alias, not consumer defends.
  DEPENDS_ON: autoresearch_loop.py lines 3480-3579

INV-5: fit_declaration fence format
  ASSERT: thesis.md fit_declaration uses ```fit_declaration fence, not ```yaml
  CHECK: grep "```fit_declaration" thesis.md before run
  TRAP: seed thesis used ```yaml → parse error in iters 1-2, score 0
  DEPENDS_ON: autoresearch_loop.py parse_fit_declaration

INV-6: Pre-registration location
  ASSERT: pre_registration docs live in research_areas/private/seams/ not in raw/ or project root
  CHECK: AGENTS.md convention
  TRAP: sandbox_18 pre_registration was in raw/pre_registration.md — wrong location

INV-7: Phase claim ladder is sequential
  ASSERT: Phase C gate opens only after Phase B clean on ≥1 substrate (Outcome A)
  CHECK: GP-096 seam closure criteria
  TRAP: stale GP-096 seam said "KWW discriminator not yet run" when Outcome A was already confirmed

INV-8: CAGE / KERNEL / RUBRIC channels are distinct
  ASSERT: gaming pattern promotions go to exactly one channel based on GP-086 table
  CHECK: GP-086 promotion table before implementing any gate
  TRAP: conflating KERNEL (autoresearch_loop.py) with CAGE (gate_harness.py) — different
        durability and different blast radius

INV-9: Qualitative rubric must pass charter_spirit_coverage check
  ASSERT: review_rubric.py CHECK_NAMES[5] fires before any qualitative project run
  CHECK: review_rubric.py output shows 6/6 checks before loop starts
  TRAP: GP-104B — Seattle run scored 94 on housing-only thesis; charter asked for full
        externality balance; rubric dropped implicit dynamic modeling requirement
  DEPENDS_ON: GP-054 charter_spirit_coverage + GP-104B persona Rule 7

INV-10: Seam must precede spec; spec must precede implementation
  ASSERT: Three-artifact sequence: seam (investigation) → spec (blueprint) → impl
  CHECK: seam has ## Recommendation section before spec is opened
  TRAP: mixed investigation-plus-blueprint files caused "what's in flight?" ambiguity
  DEPENDS_ON: GP-053
```

---

## DEPENDENCY GRAPH

```
GP-072 (Division A/B Protocol)
  ← consumed by: ALL sandbox construction
  → produces: evidence isolation, sentinel, Division B artifact set
  DEPENDS_ON: AGENTS.md (procedure checklist)

GP-075 (Rubric for Unknowns)
  ← consumed by: rubric JSON construction for Phase B/C
  → hard-constrains: enable_component_c, holdout_hard_gate, farther_tail_contract
  DEPENDS_ON: GP-072 (must be built by Division B agent that doesn't know GT)
  BLOCKS: any discovery-mode run without its Layer 4 constraints

GP-085 (Grammar Ceiling Hypothesis)
  ← consumed by: post-run diagnosis when all forms fail farther-tail gate
  → declares: true GCH vs convergence failure vs ill-conditioning
  DEPENDS_ON: GP-095 (convergence ruling must precede GCH declaration)
  BLOCKS: GP-087 (primitive injection is GCH intervention only)

GP-086 (Cage/Kernel Hardening)
  ← consumed by: any gaming pattern promotion
  → targets: CAGE (gate_harness.py) | KERNEL (autoresearch_loop.py) | RUBRIC (json)
  DEPENDS_ON: sandbox_gaming_extractor.py (miner)
  BLOCKS: implementation of any new deterministic gate

GP-087 (Residual-Driven Primitive Generation)
  ← consumed by: grammar ceiling confirmed by GP-095 + GP-085
  → proposes: next grammar primitive from alien-model tail residual shape
  DEPENDS_ON: GP-095 (convergence confirmed) + GP-085 (GCH confirmed)

GP-095 (Post-Fit Residual Ambiguity)
  ← consumed by: every run where best fit fails farther-tail gate
  → classifies: reachable_low_residual | pathological_surface | ceiling_candidate
  DEPENDS_ON: GP-035 (fit primitive — removes param-guess noise first)
  BLOCKS: GP-085 (ceiling declaration), GP-087 (primitive injection)

GP-096 (Science Programme: Phase A→B→C→D)
  ← consumed by: substrate selection, Phase transition decisions
  → gates: Phase C open only after Phase B Outcome A on ≥1 substrate
  DEPENDS_ON: GP-072 (blind experiment protocol) + GP-085 (grammar reachability pre-check)
  Phase B result: KWW Outcome A CONFIRMED 2026-04-18 (sandbox_17, score 98/100)
  Phase B result: Langevin Outcome D — search failure baseline (INS-029, sandbox_16)
  Phase B result: DFDO Outcome A CONFIRMED 2026-04-19 (sandbox_18, score 95/100) — functional surrogate
  Phase C: OPEN — gate confirmed by double Outcome A (KWW + DFDO)

GP-103 (Topology Induction Gap — DFDO sandbox_18 finding)
  ← consumed by: PHASE_G1.5 in autoresearch_loop; structural_memory.py primitives
  → ships: H-GP103-5 (compositional hypothesis generator) + H-GP103-4 (log-offset granularity)
  DEPENDS_ON: GP-096 Phase B closure (finding is from sandbox_18)
  KEY FINDING: multi-regime observables require additive two-regime composite topology;
               LLM systematically explores individual regimes but never composes them
  SEAM DOC: research_areas/private/seams/GP-103_topology_induction_gap.md

GP-070 (Meta-Supervisor / Goal Orchestrator)
  ← consumed by: operator stepping-out, multi-runner sequences
  → routes: goals to findings_runner | autoresearch_loop | supervisor_autoloop
  DEPENDS_ON: GP-071 (executive inbox for human-signature gates)
  NOTE: runners are inputs to GP-070, not peers of each other

GP-102 (Reflexive Primitive Discovery — Kaizen)
  ← consumed by: periodic audit (cron, not crisis trigger)
  → proposes: new reflexive engineering primitives when stagnation patterns exceed threshold
  DEPENDS_ON: GP-070 (cron goal scheduling) + GP-079 (hybrid persona router for committee)
  LIMITATION: detects Score=0 stagnation; blind to high-score Goodharting (→ GP-105)

GP-105 (M-Form Alignment Audit — OPENING 2026-04-20)
  ← consumed by: qualitative project runs where score ≥ 90 within first 5 iters
  → audits: champion thesis against project_charter.md while blinded to rubric
  → acts: demotes false success, appends adversarial dimension to rubric, resumes run
  DEPENDS_ON: GP-102 (kaizen seam) + GP-054 (review_rubric charter_spirit_coverage)
  COMPLEMENTS: GP-104B (pre-run rubric hardening); GP-105 is the runtime immune system

GP-054 (Rubric Quality and Generation)
  ← consumed by: every pre-run rubric review; generate_gp_project.py
  → blocks: run if review_rubric.py fails any of 6 checks
  DEPENDS_ON: GP-053 (format); charter_spirit_coverage is check 6 (added GP-104B)

GP-101 (Agent-Native Self-Model Format)
  ← consumed by: any token-optimized self-model document (including this one)
  → specifies: lookup table + invariant contracts as minimum viable format
  Convergence: keep causal context as typed DEPENDS_ON edges; lookup table is highest-value section
```

---

## SEAM REGISTRY

| ID | Name | Status | Key behavior | Spec? | Location |
|---|---|---|---|---|---|
| GP-024 | Persistent Research Workspace / Librarian | active | Workspace scoping, librarian accumulation pattern; research_areas/ structure | — | `apparatus/instrumentation/` |
| GP-031 | Findings Birth Bridge | active | Controls how findings graduate from run artifacts to seam entries; birth bridge invariants | — | `apparatus/supervisor/` |
| GP-032 | Epistemic Throughput Unit Economics | active | Per-iteration cost accounting; epistemic unit economics across substrates | — | `apparatus/instrumentation/` |
| GP-033 | Multi-Project Synthesis Generalization | active | Cross-substrate generalization; synthesis/ledger.py integration | — | `apparatus/instrumentation/` |
| GP-036 | Findings Runner / Supervisor Convergence | active | Findings Runner → Supervisor pipeline; actor dispatch; context-awareness | — | `apparatus/supervisor/` |
| GP-037 | Substrate Swap | closed | Substrate rotation pre-registration protocol | — | `seams/protocol/` |
| GP-038 | Tail Cycle-Time Instrumentation | active | Tail-run timing; cycle-time signal for throughput optimization | — | `apparatus/instrumentation/` |
| GP-039 | Gate Library Formalization | active | Gate taxonomy; formal gate interface in gate_harness.py | — | `apparatus/cage/` |
| GP-040 | Throughput & Cost Instrumentation | active | Token cost + iteration throughput; information_yield.py accounting | — | `apparatus/instrumentation/` |
| GP-046 | Asymptotic Regime Claim Discipline | active | Farther-tail gate; extrapolation gap; disable keys for qualitative projects | — | `seams/protocol/` |
| GP-049 | Epistemic Verification Decomposition Validation | active | Abductive→deductive split; validation architecture | — | `mission/` |
| GP-050 | Post-Treatise Philosophy Anchors | active | Philosophy anchors for post-Paper-5 work | — | `mission/` |
| GP-053 | Seam-Spec Format | active | Three-artifact system: seam → spec → impl ordering invariant | — | `seams/protocol/` |
| GP-054 | Rubric Quality and Generation | active | 6 pre-run checks; charter_spirit_coverage (check 6 added GP-104B); blocks run on fail | — | `seams/protocol/` |
| GP-055 | Meta-Judge Parse Robustness | active | Judge prompt structure; charter injection at test_thesis.py:866; drift check advisory-only | Yes | `engine/` |
| GP-058 | Bug Bounty + Factory Integration | open | Automated gaming pattern detection pipeline | — | `gaming/` |
| GP-061 | Constraint Accumulation as Output | active | Constraint accumulation primitive; void-driven steering; R4 retrospective audit | Yes | `apparatus/supervisor/` |
| GP-070 | Meta-Supervisor Goal Orchestrator | draft | Routes goals to runners; stepping-out operator interface | Yes | `apparatus/supervisor/` |
| GP-071 | Executive Inbox | active | Human-signature gate for seam escalations | Yes | `apparatus/supervisor/` |
| GP-072 | Division A/B Sandbox Protocol | active | 7-phase run protocol; M-form information isolation | Yes | `seams/protocol/` |
| GP-073 | Subliminal Learning Reproduction | active | Shared-init subliminal channel; cross-family + deterministic gate = channel severed | — | `gaming/` |
| GP-074 | Component C Residual Fingerprinting | active | Positive-space geometric hints; disabled in discovery mode | Yes | — |
| GP-075 | Rubric for Unknown Domains | active | Layer 4 hard-constraints; GT-independent criteria taxonomy | Yes | `apparatus/cage/` (protocol) |
| GP-076 | Predictive Divergence Sweep | active | Pre-run sweep to find rival-separating observables | Yes | `apparatus/cage/` (protocol) |
| GP-077 | OEIS Sequence Law Recovery | active | ZTARE as machine scientist for dark sequences; COMPRESS replaces number-theoretic library | — | `substrates/erdos/` |
| GP-078 | Component D Topology Synthesizer | active | Grammar primitive injection for GCH cases | Yes | — |
| GP-079 | Persona Library Unification | active | Hybrid persona router; dynamic generation; opinionated personas resist Goodharting | — | `apparatus/cage/` (protocol) |
| GP-080 | Substrate Pharmacokinetics (Tacrolimus) | active | Component D test on continuous clinical domain | — | `substrates/tacrolimus/` |
| GP-082 | Substrate Scope Boundary | active | Phase A/B/C definitions; what counts as a valid Phase B substrate | — | `gaming/` |
| GP-083 | Inference Type Boundary | active | Output type = "simplest surviving structural form"; epistemic honesty | Yes | `gaming/` |
| GP-085 | Grammar Ceiling Hypothesis | active | GCH declaration criteria; null result for unreachable GT | Yes | `mission/` |
| GP-086 | Cage/Kernel Hardening | active | Gaming pattern promotion table; three channels (CAGE/KERNEL/RUBRIC) | — | `apparatus/cage/` |
| GP-087 | Residual-Driven Primitive Generation | note | Alien math as diagnostic, not translator | — | — |
| GP-088 | Ansatz to Prover | active | Phase D — post-discovery deductive lift; downstream of Phase C | — | `apparatus/instrumentation/` |
| GP-095 | Post-Fit Residual Ambiguity | active | Convergence vs ill-conditioning vs GCH classifier; n≥3 multi-start | — | — |
| GP-096 | Science Programme Decomposition | active | Phase A→B→C→D claim ladder; Phase B clean 2026-04-18 | — | `mission/` |
| GP-097 | N-D Manifold Compressor | active | Topological coordinate descent; compress N-D before synthesis | Yes | — |
| GP-098 | Evidence Compressor | active | compile_evidence.py; raw→structured; preserves contradictions | Yes | `apparatus/instrumentation/` |
| GP-099 | Vocabulary Floor | active | Floor declaration: what's reachable now; prevents redundant primitive injection | — | `engine/grammar/` |
| GP-100 | Epistemic Decoupling | active | Token-optimized self-modeling; autoresearch_loop_architectural_map.md | — | `engine/mutator/` |
| GP-101 | Agent-Native Self-Model Format | open | Format debate: lookup+invariants minimum viable; convergence reached | — | `apparatus/instrumentation/` |
| GP-102 | Reflexive Primitive Discovery (Kaizen) | open | Cron-triggered audit; periodic not crisis; committee via GP-079; blind to high-score Goodharting | Yes | `apparatus/instrumentation/` |
| GP-103 | Topology Induction Gap | active | H-GP103-5 compositional hypothesis generator; H-GP103-4 log-offset granularity; shipped 2026-04-19 | — | `seams/protocol/` + `private/seams/` |
| GP-104 | Qualitative Rubric Gate Configuration | active | TYPE_B_GATE_CONFIG; charter_spirit_coverage; persona Rule 7; GP-104B amendment | — | `seams/protocol/` |
| GP-105 | M-Form Alignment Audit | opening | Runtime Goodhart detection; General Office audit; qualitative score ≥ 90 trigger | — | TBD |
| GP-143 | Continuous-Chaotic Kernel Integration | active | Dynamical-lattice dispatch + Wasserstein-persistence gate; seam + spec + runnable gate module shipped 2026-04-24 (pre-promotion) | Yes | `private/seams/engine/` + `private/specs/active/` |
| GP-144 | New-Science Claim Discipline | active | Four-gate claim-pipeline stack G1–G4 + G5–G8 gp147 extensions; 3-phase layering (C admission / D claim / E bridge) per Gemini synthesis; G4 reuses gp139 backbone | — | `private/seams/engine/` |
| GP-145 | SAW Connective Constant μ_sq | active | First real conjecture-refinement substrate; run-1 archived partial_null at score 56; run-2 narrow-scope gp145b scaffolded | — | `private/seams/engine/` + `projects/gp145*/` |
| GP-146 | Gate-Stack Self-Validation | pending | Arnold cat map false-positive injection against GP-144 stack; blocks any external-submission-grade claim | — | TBD |
| GP-148 | Mining the Void — Infrastructure | active | Stage 1 extractor + Stage 1.5 enrichment shipped; Stage 2 queries A-E done; Stage 3 LLM meta deferred | — | `private/seams/engine/` |
| GP-149 | Mining Findings + Interventions | draft | First-pass findings: tail_generalization convergent blindspot; Lollapalooza refuted; structural-blocker vs ceiling-breaker dichotomy (B3); persistence+cycling profile for champions (B4). Seven-item intervention catalog with pros/cons, gated by rubric flags, default-safe. | — | `private/seams/engine/` |

---

## INVARIANT — HOSTILE JUDGE VERIFICATION AT PROMOTION BOUNDARY (added 2026-04-24 per GP-149 §8a Oracle Illusion measurement)

**Scope:** external-submission and kernel-default-promotion boundaries ONLY. NOT per-gate-invocation.

**Rule:** no claim may be promoted from GP-144 Phase D (claim-grounded, all gates passed) to GP-144 Phase E (submission-ready) without a Hostile Judge re-score returning ≥ the primary judge's promotion threshold.

**Hostile Judge definition** (must satisfy ALL):
- Different vendor family than the primary judge (e.g., if primary is OpenAI, hostile must be Anthropic/Google/Meta).
- Different model size tier (if primary is frontier-class, hostile may be frontier-class OR a tier-down reasoning model; never a smaller non-reasoning model).
- Not the same model instance (no self-reflection; must be a genuine separate call).

**Rationale:** cross-judge stratified analysis (GP-149 §8a, 2026-04-24) measured a 3× score differential for the same (mutator, thesis) pair under different judges (o3→claude-sonnet dropped mean 49.2 to 15.4). Promoting a claim that only passed under one judge family risks exporting judge-aesthetic-validated, not structurally-valid, results.

**Scope clarifications (what this invariant does NOT require):**
- NOT per-iteration re-scoring. Primary judge remains authoritative within a run.
- NOT per-gate re-invocation. G1-G8 gates are deterministic; they don't need judge mediation.
- NOT kernel-solver verification. CW-PT and similar solver outputs don't need hostile-judge check to enter the gate stack.
- NOT for internal mining / research. Mining-derived insights stay single-judge unless a pattern is being promoted to kernel-default-intervention, in which case cross-judge replication is required per GP-149 §8a.

**The boundary where this fires:**
- Claim passes all GP-144 Phase D gates (G1 continuum, G2 PSLQ, G3 ansatz-survivor, G4 proof-surveyability) under the primary judge.
- Before the claim is declared "submission-ready" or used to promote an intervention to kernel-default behavior: hostile-judge re-score required.
- Re-score failure → claim stays internal, can be revised and re-submitted; loop does NOT abort.

**Cost:** ~1-5 additional judge calls per external-submission or kernel-promotion event. Not per-iter. Acceptable.

**Credit:** Gemini-Pro 2026-04-24 proposed at G1/G2-per-invocation scope; operator flagged "too harsh"; refactored to promotion-boundary scope per operator instinct.

---

## COMMON TRAPS (INCIDENTS)

```
TRAP-1: Rubric constructed without checking GP-075 Layer 4
  What happened: enable_component_c omitted/set wrong; discovered only during run
  Fix: always grep rubric for enable_component_c before seal; INV-2

TRAP-2: GCH declared without convergence ruling
  What happened: Langevin sandbox_16 looked like grammar ceiling; was search failure
  Fix: GP-095 multi-start first, always; INV-3

TRAP-3: Generator/consumer function-name mismatch in test_model.py
  What happened: sandbox_18 gate_harness expected model(); GP-035 wrote f()
  Fix: _ensure_canonical_model_aliases() at all three write points in autoresearch_loop; INV-4

TRAP-4: fit_declaration fence format mismatch
  What happened: seed thesis used ```yaml; loop parser expected ```fit_declaration
  Fix: grep before run; INV-5

TRAP-5: Stale seam read as current state
  What happened: GP-096 seam said KWW discriminator not done; it was done
  Fix: read artifact (pre_registration.md) not seam prose; seams lag

TRAP-6: Division A document placed at project root
  What happened: sandbox_construction_record.md at project root; contained GT physics vocabulary
  Fix: Division A artifacts → raw/ only; sentinel enforces; INV-1

TRAP-7: LLM-suggested rubric flags accepted without code verification
  What happened: Gemini suggested discovery_mode: true, holdout_budget: N — not consumed by loop
  Fix: grep autoresearch_loop.py for any new rubric flag before adding to JSON

TRAP-8: High-score qualitative output accepted as success (GP-104B / Seattle)
  What happened: Seattle run scored 94 on housing-NPV thesis; charter asked for full externality
                 balance with dynamic modeling + counterfactual + distributional decomposition;
                 rubric had dropped all three implicit requirements during LLM rubric drafting
  Fix: GP-104B pre-run hardening (review_rubric check 6 + persona Rule 7); GP-105 runtime audit;
       score > 90 on qualitative project within 5 iters is the Goodharting signature, not success

TRAP-9: Seam consulted after file edit (not before)
  What happened: autoresearch_loop.py edited without reading arch map; partial-view mistake
                 corrupted pipeline ordering contract
  Fix: seam-first sequencing (GP-053); read arch map BEFORE any autoresearch_loop.py edit;
       INV-10 — seam precedes spec precedes impl, same principle applies to edits
```
