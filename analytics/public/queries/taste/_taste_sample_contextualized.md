# Taste Rater — Context Primer

This primer is given to a contextualized rater BEFORE rating samples. It establishes 'what this codebase considers load-bearing.' The rater uses this as the anchor for distinguishing domain-significant insights from generic-looking ones.

**Use this only to anchor scoring relative to the codebase's own structure. Do NOT use it to recognize specific samples and score them higher because they're familiar.**

---

## Load-bearing seams (top by in-degree from reference graph)

These seams are most-cited by other apparatus artifacts. They represent the structural infrastructure of the codebase. An artifact that materially extends or refutes one of these is paradigm-shifting for this codebase (score 5).

- **GP-023_planck_sandbox_08_closure** (cited 460x, week 2026-04-13): Status: closed 2026-04-14 Primary outcome: **D (score=0 across 14 iterations) + GP-061/GP-062 cold-run evidence** Pre-reg: `GP-023_planck_sandbox_08_pre_registration.md` Run: 14 iters logged in `iteration_telemetry.jsonl`, 12 fits recorded, 13 derive
- **GP-163d_unified_accel_run_postmortem** (cited 391x, week 2026-04-20): **Status:** closed — three apparatus bugs identified, fixes in place **Parent:** GP-156 apparatus hardening spec (this seam appends new bugs) **Date:** 2026-04-25 night **Substrate:** `projects/gp163d_unified_accel` (RAR/MOND interpolation, 3 system 
- **GP-154_learning_mechanics_scaling_exponents_seam** (cited 309x, week 2026-04-20): Status: note Opened: 2026-04-24 Track: findings n: 0 (pre-observational — domain selection, no runtime observation yet)
- **GP-140_ztare_discovery_seam** (cited 178x, week 2026-04-20): **Status:** open, active substrate scaffolded 2026-04-23. **Parent:** ztare_on_ztare (saturated at score 92 across five admission-gate champions); GP-135 family (pMDL, TW, Noether, Lean hardenings). **Sibling holdout:** MLH F6 (sealed at `projects/ml
- **GP-216_theory_building_operations_seam** (cited 168x, week 2026-05-04): *Status: open. 2026-05-04. Triggered by GP-215 cold-room Test 1 failure (paper 5 verification vocabulary covers 36% of Wiles's FLT moves; theory-builder seed vocabulary covers 45%; the residual is 50-65% theory-building / sociology / domain-specific 
- **GP-116_compression_as_architecture_discovery** (cited 164x, week 2026-04-20): Status: opening Opened: 2026-04-22
- **GP-061_constraint_accumulation_as_output_seam** (cited 153x, week 2026-04-13): Status: open Opened: 2026-04-14 Revised: 2026-04-14 (after Gemini framing + sandbox_07 retroactive test) Hypothesis family: H-ARCH-02 (output semantics)
- **GP-168_org_design_unfalsifiability_seam** (cited 152x, week 2026-04-27): **Status**: open seam, default private (first-mover IP, not shipped, contains operational findings) **Opened**: 2026-04-27 **Substrate**: gp168_org_design_discovery **Provenance**: 38 evaluations across multiple ZTARE runs on `org_topology` substrate
- **GP-096_science_programme_decomposition_seam** (cited 109x, week 2026-04-20): Active — opened 2026-04-18
- **GP-035_mutator_missing_fit_primitive_seam** (cited 97x, week 2026-04-13): **Track:** findings **Status:** `reopened` (narrow hygiene — FIT_DECLARATION drought fix pending, 2026-04-13 Turn 10) **Origin:** runtime-discovered during GP-023 Phase 2, `gp023_planck_sandbox_02` iters 1–17 (2026-04-11) **Trigger:** Codex observati
- **GP-088_ansatz_to_prover_seam** (cited 94x, week 2026-04-13): **Status:** `note` — opened 2026-04-17, conditional on precipitating findings **Parent artifact:** Paper 5 (Treatise), Chapter 3 — Peircean residual; GP-050 Track 3 (Peirce abduction shims) **Related:** GP-050 Track 7 (Wittgenstein / language-game bi
- **GP-145_saw_mu_square_seam** (cited 91x, week 2026-04-20): **Status:** run-1 archived 2026-04-24 (partial null, pinned at 56); run-2 narrow-scope planned (gp145b) **Owner:** conjecture-refinement substrates **Depends on:** GP-086 (gate harness), GP-122 (Lean REPL), GP-144 (claim-pipeline discipline), GP-148 
- **GP-030_deterministic_charter_gate_seam** (cited 89x, week 2026-04-06): `active — first slice shipped 2026-04-11` (opened 2026-04-11 as a direct consequence of the GP-023 Phase 1 main run; demoted to `note` 2026-04-11 per the findings-track n=1 invariant; promoted back to `active` 2026-04-11 under operator authorization 
- **GP-169_cold_llm_synthetic_erdos_seam** (cited 84x, week 2026-04-20): Status: scaffolded (Phase 1 spec, no implementation yet) Opened: 2026-04-27 Track: kernel Related: GP-164 (REFRAME + ANALOGY meta-arch), GP-167 (SubstrateCritic), GP-168 (Forced REFRAME iter) Anchor texts:   - Cognitive_gym Part 7 (Anchoring Thesis) 
- **GP-149_mining_findings_and_interventions_seam** (cited 78x, week 2026-04-20): **Status:** active draft 2026-04-24; first findings pass + first intervention batch **Owner:** mining-derived-apparatus-discipline **Depends on:** GP-148 (mining infrastructure), GP-086 (gate harness / cage discipline), GP-053 (seam-spec invariant), 

## Operator-curated memory entries

These are the operator's distilled lessons across the project's lifetime. Each is what the operator wanted to remember. An artifact that surfaces a NEW lesson at this level of generality is high-quality.

- **GP-226 charter-critic V1+V2+preflight shipped 2026-05-06**: Closed-loop charter-tuning role: regex+Jaccard fingerprint matching → V1 light template OR V2 LLM-assisted heavy patch (cheap-tier, no hardcoded model). Preflight Makefile prereq with interactive/auto_confirm/skip modes. First run on human_ai_interaction_primitive plateaued at 88; bucket #7 (parameter_estimability_fragility) added after unmatched-fingerprint analysis; pending velocity-vs-level patch + new bucket awaiting next run
- **Reflexive miner today is coverage/ROI; structural-analogy findings come from operator**: 2026-05-06 calibration: operator surfaced "charter should be a recursive refinement loop, mirroring evidence-fetch pattern" and the reflexive miner couldn't have. Today's miner asks "is X engaging/load-bearing/dead/covered" but not "should there be a loop here?" Close the gap with: catalog of recursion loops + catalog of one-shot generation steps + pairing function
- **Recursive self-improvement loops surface apparatus bugs FIRST — that's the feature**: 2026-05-06 first end-to-end ZTARE Layer 3 cycle: 4 apparatus fixes (R8/R9 wired, R20-R24 registered, dashboard alias map, Lane A guard) + zero new primitives. The "no new primitives" verdict was correct output, NOT a wasted session. When a Layer 3 cycle proposes candidates: inspect Lane A (real F-row closures) not total counts; LLM over-tags on governance/architecture prose
- **Don't kill paid compute on a single noisy diagnostic (2026-05-06 incident)**: Falsifiers are hypotheses not verdicts; validate signal + apply inversion-reflex BEFORE killing GPU/distributed runs; general-purpose tools serve multiple substrates so single-substrate underperformance ≠ kill criterion; codified in AGENTS.md §4z1 + RD mandate
- **Typed endpoint pack — Codex's >10x architecture, scaffolded 2026-05-06**: 4-patch-class typed endpoint-bound context pack shipped + validated end-to-end; Stage 4 failure-category accumulator alive; one apparatus gap (lake stderr-only capture misses real errors) flagged for tomorrow morning
- **GPU link-prediction bet pending — schedule for 2026-05-06+**: User offered GPU/SSH for RGCN link prediction on NS constraint graph; CPU prep + Adamic-Adar baseline shipped 2026-05-05; bootstrap snapshot mode still needed before training
- **GP-216 theory-building operations vocabulary v3 — 10 passes shipped 2026-05-04/05**: 12-op Python registry consolidating Gowers's "theory-building" category; descriptive (~58% h+m coverage), not generative; survived 8 falsifier passes including 6/6 panel REVISE; 18% of ZTARE cycles instantiate the ops; do NOT extend without external-corpus testing
- **Mini-ZTARE v0.2 design-review session — resume state 2026-05-03**: Priority-A code shipped uncommitted/unbuilt/undeployed in /; resume by `npm run build` then deploy then PM roadmap doc; full pending list inside
- **Author rubrics in canonical format on first write**: Required fields: name/project/description/rubric_mode/falsification_mode/dimensions[](sum=100)/persona; qualitative substrates need cage_observe_mode + disable_evidence_fit_gate + cage_meta; copy a sibling rubric, never a blank
- **Mechanize Research Director's deterministic falsifications as gates**: When a falsification test runs by hand on existing artifacts and would catch a class of false-positive promotions deterministically, build it as a cage gate; iter-2 GP-183 (2026-04-28) is the canonical example with B1-B4 gates shipped
- **De-anchoring is fractal — apply it to the conversation, not just code**: When >5 turns of apparatus iteration without score movement, the FRAME is the suspect not the code; explicit reframe prompt names the implicit loss function; pattern surfaced 2026-04-28 in the gp163d → GP-180/181 pivot
- **GP-180/181 architectural pivot — curve-fitter → derivator**: 2026-04-28 — Lagrangian primitive + Buckingham π + Noether variance loss + invariant_search rubric mode shipped in one session; calibrate to "useful tool, not Nobel key" (Hamiltonian/Lagrangian NNs exist since 2019)
- **Symbiotic synthesis is authorized**: Director synthesis (naming structural gaps, cross-referencing complementary partial-bridges, proposing synthesis targets) is NOT ground-truth leakage; don't over-apply charter_contamination rule; this IS the Director's load-bearing function (corrected 2026-04-27)
- **GP-168 OKR addendum — operational refactor shipped 2026-04-27**: Collapsed parallel closure-pressure tree into OKR layer (Objectives + KRs + Tasks); single executive inbox at ztare_workspace/gates/pending/; closure daemon stateless; Telegram + Orbit ObjectiveTreePane wired; paper 4 NOT updated (operational, not theoretical)
- **GP-168 unfalsifiability theorem**: Bicameral org architectures provide consistency but NOT closure; closure requires exogenous resource pressure. Don't relaunch gp168 ZTARE expecting a closed-form winner — the wall IS the finding (paper 7 §11.6 + GP-168 seam)
- **Evidence enrichment — operator + source-intrinsic contradictions**: Before writing operator meta-observation evidence, read every raw/ source adversarially for self-declared open questions; source-intrinsic contradictions land in Section 3 without a new file and are higher-leverage than operator-flagged ones
- **Skeptic Director belongs in M-form research-scientist seam**: Don't propose /skeptic-review skill; extend the existing M-form research-scientist-reports-to-principal role with the post-ZTARE skeptic-dispatch mandate
- **GP-156 fit_primitive_features session**: 24-bug session shipping N-D fit primitive; BIC replaces K_law=5 magic number; gp155 hit 94 (genuine recovery); GP-158 v5 Cage audit project scaffolded
- **ZTARE-on-ZTARE postmortem — sycophancy loop**: Spec audit alone misses code bugs; mandatory protocol: Python integration smoke test FIRST against real archived data, THEN inverted execution-hostile spec audit
- **GP-154 Literature Review — REFRAME novelty**: Combination novel, individual ingredients not; AI Feynman does pre-solver transforms; Box-Cox does Jacobian-corrected BIC; PyFSSA does collapse detection; claim the architecture not the components
- **Findings Recording Procedure**: E-row + F-row + seam postmortem after every run; write before opening next experiment; staleness pattern identified 2026-04-19
- **Attacker tool-use filesystem exfiltration (gaming class)**: 2026-04-15 gemini-pro attacker scraped whole repo via execute_python_code; fix: tempdir sandbox + --disable_attacker_tools; retro exfil in prior sandboxes can't be ruled out
- **Pace anxiety — field is moving fast around ZTARE**: 2026-04-15 Erdős + Odrzywołek context; LW auto-rejection compounds; positioning call not velocity call
- **GP-077 OEIS Sequence Law Recovery**: ZTARE corrector recovery applied to OEIS dark sequences; COMPRESS insight replaces number-theoretic library with log-transform + parity forms
- **INVERT + COMPRESS as topological pivot primitives**: Mungerian heuristics hardcoded into pivot; log-transform + parity decomposition made A002865 tractable without new library
- **Charter is mutator-visible — no GT, no derivations**: autoresearch_loop injects project_charter.md into the mutator prompt; GT form/params/derivations in the charter are cheat sheets
- **Validate against real system, not imagined schema**: read one real input, one real config, grep call site before declaring integration done
- **Sanitization has two axes**: numeric + semantic (names, labels, enumerations); self-critique sanitized drafts before shipping to operator
- **Replication Experiment Design**: 2x2 mutator/judge matrix, naming convention, what each cell tests
- **Emergent Gaming: Claude Mutator**: Suite Omission behavior observed in recursive_bayesian_claude_gemini run
- **GPT-4o Mutator: No Convergence**: GPT-4o oscillates without gaming even with o1 escalation; explains why; paper framing for mutator comparison
- **Central Station Startup Analysis**: Two ZTARE runs (Series A + pre-seed rubric), Kill Criteria found, McKinsey report to be built
- **Gaming in Startup Domain**: Straw Man Design (new 9th strategy), Misattributed Cooked Book, Silent 100% Injection — all from central_station product run
- **Future Work: ZTARE as Rubric Design Tool**: Run ZTARE on rubric specs themselves before committing to domain runs; would have saved 30+ iterations
- **Rubrics as Evals — Gaming at Specification Layer**: Any formal spec an optimizer satisfies gets gamed toward satisfiability; opinionated personas resist gaming; paper finding on Goodhart's Law at eval layer
- **Gaming as Finding vs. Algorithm Artifact**: ZTARE is apparatus not confound; GPT-4o non-convergence is the within-experiment control; cross-domain convergence proves strategies are real
- **Meta-Renderer Compiler — Future Architecture**: constrained dynamic renderer via invariant semantic contract; build after 3-4 real synthesize.py runs reveal actual variable dimensions
- **Thesis Seed Protocol**: Use v1 gemini output as seed for replication runs; empty axioms; original seeds lost
- **ZTARE v3: ALU vs RAM**: ZTARE stays stateless validator (ALU); wiki is external accumulation (RAM); never merge; client-server model
- **Evidence Compiler (RAM layer)**: compile_evidence.py + merge_workspace.md; raw/ → structured evidence; preserves contradictions; ZTARE-external
- **GPT-4o TSMC Natural Experiment**: Pre-loaded axioms let GPT-4o spike to 97 once then collapse; can't hold inherited structure; report as natural experiment
- **Paper 2: Recursive Epistemic Gain**: Second paper; failure→constraint as unit of recursive improvement; v4 architecture; split from cognitive camouflage
- **Recursive Self-Diagnosis**: Primitives shift detection surface; first live example of engine self-improving; eigenquestion-first ordering constraint earned
- **Debate: Weight General-Purposeness and Overfitting**: In all debates, explicitly flag overfitting risk; test fixes for generalizability before accepting; OOD check is the safeguard
- **Debate Logs as Labeled Failure Dataset**: V4 logs are a labeled dataset of LLM reasoning failures under optimization pressure; frame as systematic exploitation patterns not hallucination; methodology is the IP
- **Supervisor Loop — Current State**: Closed (Turn 55). M-form architecture complete. Full stack: wrappers, write-scope guard, backlog, proposal, manifest, usage ledger. Active program: stage2_derivation_seam_hardening.
- **Post-V4 Program State**: V4+runner+supervisor closed; bridge frozen; stage2_derivation_seam_hardening active (packet 1 done, packet 2 pending)
- **Claude vs Codex Implementation Roles**: Claude owns architectural framing; Codex owns definition-of-done; seam not complete until Codex confirms live wire
- **Verify claims before approving**: Never approve quantitative claims in drafts without checking source; approved wrong numbers that went public are harder to correct than a pre-approval flag
- **Verify LLM claims against source**: Hallucinated opposite PySR conclusion from paperllm.pdf; always cite page/table/figure before presenting claims about external papers
- **ZTARE Spec Format + Seam-First Rule**: Three-artifact system: board row + seam (debate, no spec) first, then spec (blueprint, no Debate Log); seam must precede spec; both default private
- **Seam Visibility — Public vs Private**: Three-test rule (shipped/closed + no exploit content + no first-mover IP) → fail any → `research_areas/private/`. Default private on doubt. Promotion is the visibility event.
- **ZTARE Epistemic Thesis**: Six-claim philosophy: ZTARE makes falsification cheap (deepest claim); compound failure detection is unique; Ontology Trap is real but limited; do not chase paradigm-shift fantasies
- **Three Legs of ZTARE**: Invert + Compress(asymptotic survival) + Adversarial Disagreement; internal philosophy doc at research_areas/private/philosophy/three_legs_of_ztare.md
- **GP-046 Empirical Anchor (gp023 sandbox_03 iter 13)**: First live proof that farther-tail global residual catches a finite-window surrogate terminal-only testing would miss
- **Jaccard / Tunneling / Annealing Probe**: GP-028/029 exploratory-mode probe: jaccard wins for slice 1, embeddings deferred, simulated annealing rebutted (don't soften the verifier), quantum tunneling rebutted (use GP-028 preservation lane instead)
- **GPT-4.1 as default fallback model**: fast, cheap, powerful; use when Gemini Pro unstable; path-dependence blinder lifted 2026-04-16
- **Plain English preference**: Charlie Munger standard: lead with simple explanations, define jargon on first use, glossary at docs/GLOSSARY.md
- **Instance-anchored generalization**: When building general tools from specific failures, audit all artifacts for leakage from the motivating case
- **Never parallel-agent on shared files**: Background agents must not write to files the main session is editing; race condition wastes everything
- **Frustration-anchored diagnosis**: Accumulated run context biases fix prescriptions toward "give the LLM more signal" even when the bottleneck is downstream
- **Bounded critique agent**: Before finalizing seam/spec fixes, spin a read-only Explore agent with only the artifact + problem statement; no run history; catches overfitting and frustration-anchored diagnosis
- **Interface debt — silent defaults**: Never dict.get(key, safe_default) on contract keys; GP-077 burned 4 iters because missing harness_ok defaulted to False
- **Automated skeptic persona**: Durable adversarial persona + 12 overreach patterns a bounded subagent loads before reviewing any draft; replaces the operator "be adversarial" seat
- **Mungerian thinking as core philosophy**: Inversion, anti-self-deception, lollapalooza, circle of competence, checklist discipline, man-with-a-hammer — load-bearing in ZTARE architecture, not decorative
- **Domain-Axiom vs. Domain-Dimensionality**: Grammar constructs must be named after math ops not domains; naming leaks oracle knowledge to LLM; DOSE_SCALED→BIVARIATE_SCALE is the canonical fix
- **Operational Manual structure**: Treatise (Paper 5) stays pure/permanent; Operational Manual is paranoid/updatable; 3 chapters: Three Legs + Cognitive Gym + Epistemic Hygiene
- **Principle vs instantiation strip test**: Strip proper nouns and concrete mechanisms from any sentence stated as a principle; if it collapses, it was an instantiation
- **Recap from artifact, not memory**: Recordkeeping turns must Read the artifact first; silent lag is the default failure mode
- **Read-the-data-first reflex**: When a run fails confusingly, read last_prompt_debug.txt + debate_log + JSONL telemetry BEFORE shipping more apparatus. gp159 burned 4 rounds of apparatus features before agent read the prompt and saw evidence.txt was teaching the wrong pattern
- **Closure language audit**: Before "last / final / only remaining," enumerate open tracks on the same object; if any are open, demote the phrasing
- **Eigenquestion decomposition over consensus**: Don't blur eigenquestions by mixing verdicts across seams; decomposition not consensus
- **Compile before loop after evidence update**: After any evidence.txt update: make compile first, then make loop; never skip the middle step
- **H-GAMING-14: mutator formalism drift**: FIGS 88 domain-insight > 82 apparatus refutes H-GAMING-13; drift is mutator-side, judge pays for substance
- **Sandbox_06 (α,β) identifiability degeneracy**: v1 GT rank-5-not-6 (α and β collapse to α/β); pre-commit bootstrap passed the wrong property; Layer-5 fractal Goodhart; v3 reparameterized
- **Military report confirmed narrow**: Hormuz-context friend 2026-04-14: "good analysis for the cost but too narrow; don't go all Stuxnet" — external confirmation of narrowness + light scope guardrail against offensive drift
- **GP-060 Parallel Champion Synthesis**: K divergent workers + combiner + linear refinement; addresses basin trapping and dimensional blindness; combiner is the load-bearing new component; first test: Hungary rubric
- **Working harvester masking + attention debt**: populated-but-wrong-layer subsystem gives false "done" signal; new artifacts accumulate cross-reader debt; check signal coverage, not consumer existence
- **GP-061 Component A built + wired**: structural_constraint_extractor feature-bag intersects failed families; sandbox_07 retroactive test surfaced full outer skeleton with sharper have-to-believe than manual draft
- **Hinge regression REJECTED as GP-069 candidate**: 2026-04-15 sigmoid-limit probe showed smooth approx beats hinge under finite-grid L2; tier-3 needs scorer redesign, not grammar change
- **GP-070 Slice B — agent-driven gate resolution**: Operator wants agent to auto-resolve gates without manual Inbox→Goals switch; highest-value Slice B deliverable
- **Sandbox_15 null result + Component B envelope**: Topological pruner not semantic injector; null on Selkov; Component C (residual fingerprinting) identified
- **Steganographic defense (Cloud et al Nature 2026)**: Subliminal learning requires shared initialization; cross-family + deterministic gate = channel severed
- **GP-072 Division A/B for experiments**: Always use GP-072 M-form information isolation for sandbox/GT/experiment setup; never ad-hoc subagents
- **GP-072 spec — 7-phase run protocol**: Amazon-style checklist at specs/active/GP-072_role_separation_sandbox_construction_spec.md; sentinel expanded; domain-expert review = Phase 5
- **GP-078 rubric needs surgery**: Domain expert: rubric assumes closed-form f(n) but GT is self-referential recurrence; fix dimensions/persona/penalties before running
- **No pre-assessment of ZTARE target solvability**: Never declare a target "not solvable" and redirect; engine decides; GCH is the finding; scaffold what the principal chose
- **GP-097 N-D Manifold Compressor**: Topological Coordinate Descent: compress N-D to 1D before synthesis; library sweep for slicing; ratio sweep fallback; WALL_ENTANGLEMENT exit
- **Token-optimized self-modeling**: Compress agent's own understanding of large files into reusable maps; prevents partial-view mistakes; first instance: autoresearch_loop architectural map
- **Paper prose style — no contrasting structures**: Avoid "not X; it was Y" rhetorical pattern and em-dashes in paper4/paper5; AI prose tell; use direct affirmative framing instead
- **Inversion reflex on negative results**: When post-discovery test weakens a claim, INVERT before reporting; identify mechanism, name gap, find stronger recursive story; Lucky a=1.200 drift was the motivating case
- **Run falsification before presenting**: When computing a new metric, run the sanity check that could kill it BEFORE presenting; GP-116 ROC mixed granularities, 0.9% was wrong (actual 55%)
- **Newton-mode rubric completeness**: When upgrading a substrate, apply ALL GP-133 R4 components (rubric_mode + Generative Yield + Mechanism Concreteness + charter fields + grammar) — not just the grammar fix; half-upgrades waste compute
- **Primitive availability is grammar**: py_exec NaN from missing function name (is_prime) is a grammar ceiling at the primitive layer, not a semantic failure by the LLM; fix primitive availability before diagnosing discovery failure
- **GP-117 Soft Governance Debate**: Don't call it "soft governance"; use "generation-time conditioning"; persona ablation is the test; Munger camouflage warning
- **v3/v4-lite argmin anomaly — blocks paper 5**: Lorenz-bridge: argmin L=-3036 beats true rule L=-206 by ~2830 bits; resolve before including v1→v4 table in paper 5 at draft.md:552
- **Don't overindex on axiom count**: 2026-04-23 correction: read the charter / thesis / evidence first, comment on the work, not on axiom delta as a proxy metric
- **Chaos-substrate primitive corrections**: Fourier Trap + Exact-Equality Trap; fix with autocorrelation-τ and Wasserstein-persistence; v2.7 charter bans
- **v5-correct kernel placement**: on promotion: src/ztare/fit/continuous_chaotic/ alongside compress_champion, not new substrate_generators/ dir; registry dispatch by substrate_class
- **GP-143 kernel integration seam + spec**: mine + Gemini's synthesis; seam converged + spec drafted + gate module shipped at src/ztare/gates/wasserstein_persistence_gate.py (2026-04-24, pre-promotion)
- **GP-144 new-science claim discipline**: 4 inversion-derived gates in 3-phase pipeline (C admission / D claim / E bridge); gp139 lean_hardening = G4 backbone; gp136/137/138 = Phase C
- **GP-146 gate-stack self-validation**: MANDATORY: Arnold cat map λ=2·log φ as known-GT test; GP-119 Inverter injects false positives per gate; must pass before any real claim
- **Conjecture-refinement target list**: SAW μ_sq (GP-145 first, Fields-Medal-adjacent, ≥30 digits achievable) > Hénon λ₁ (second) > Lehmer / TW moments (deferred/bad fit); anti-pattern: Navier-Stokes / Millennium PDE
- **G1/G2 implementation guardrails**: Gemini's three fixes for the Precision Cliff (calculus / dimensionality / arithmetic); reserved for GP-144 spec at build time; DO NOT inject into gp147 (contamination)
- **Mutator relative-path harness bug**: 2026-04-24: mutator writes test_model.py with relative paths to projects/...; fixed via symlink shim at test_thesis.py subprocess.run boundary; judge correctly flags harness defects
- **GP-148 Mining the Void seam**: seam + Stage 1 extractor (1825 records, 84 projects) + Stage 1.5 enrichment (active_constraints, diff_delta_bytes, run_session_id, charter_hash, rubric_hash) shipped 2026-04-24
- **Pivot-effectiveness hypothesis**: gp140 iter-10 Chebyshev basis-change broke the 78 ceiling (CATEGORY_SWITCH+COMPRESSION); gp147 stuck on exhaustiveness-proof class (no pivot module fits). Provisional, 1 observation; validate via Stage 2 query before codifying. **Update 2026-04-24: partially refuted by GP-148 Stage 2 — pivots DO help exhaustiveness class (52% climb +10.4 Δ). Real blindspot is tail_generalization (−0.7 mean Δ).**
- **GP-149 mining findings + interventions**: structural-blocker vs ceiling-breaker dichotomy; Lollapalooza refuted; persistence+cycling champion profile; tail_generalization convergent blindspot; 3 runtime interventions shipped as opt-in rubric flags; runtime classifier at src/ztare/validator/weakest_link_classifier.py; canonical catalog at docs/concepts/anti_pattern_catalog.md
- **GP-164 ZTARE v2.0 Meta-Architecture**: Three-axis search: Grammar(v1.0) × REFRAME(v2.0a) × ANALOGY(v2.0b); motivated by Erdős "move one" result; ANALOGY = stagnation-triggered cross-domain structural fingerprint query validated through same gate pipeline; all three legs preserved

## Known anti-patterns (failure modes already catalogued)

Artifacts that surface a NEW failure mode not in this list are load-bearing. Artifacts that re-discover a known anti-pattern are typical (score 2).

- SB-1: Circularity / Self-reference
- SB-2: Harness defect / broken test
- SB-3: Unfalsifiable claim
- CB-1: Overclaimed scope
- CB-2: Missing mechanism
- CB-3: Missing counterfactual / rival hypothesis
- CB-4: Catastrophic / controlling assumption
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
- 15. Operator-Agent Discovery Before Mechanization
- 15. Global Primitive Library: Precedent, Not Truth
- 16. Evidence Became a First-Class Substrate
- 17. Recursive Gain Means Converting Failure Into Reusable Constraint
- 18. Benchmark Measurement Trap: Semantic Outputs Need Semantic Evaluation
- 19. First Constraint-Memory Benchmark Result: Gates Help, Primitives Overfire
- 20. First Organic Wedge: `C` Beat `B` On The Historical Corpus

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



---

# RATING TASK BEGINS BELOW

# Taste Sample — Blind Rating Sheet

This batch has **156 samples** to rate. (0 additional samples were skipped because they're already in the taste_ledger from previous runs.)

Each sample below has a unique `SAMPLE_NNN` ID. Read each sample and rate it 0-5 on **insight density**:

  - **0** = boilerplate, scaffolding, or restated apparatus state
  - **1** = trivially observable; doesn't change downstream reasoning
  - **2** = useful but expected; consolidates known
  - **3** = non-obvious finding or sharp framing; would help a future reader
  - **4** = surprising / load-bearing / mechanism-revealing
  - **5** = paradigm-shifting; reframes the problem or apparatus

Output format:
```
SAMPLE_001 | score | one-line rationale
SAMPLE_002 | score | one-line rationale
...
```

**Bias warning to rater:** if you've worked on this codebase recently, you'll be tempted to score familiar / recent / self-authored content higher. Try to score on the artifact text alone, not on what you remember about it.

---

## SAMPLE_001 (top_level_reasoning)

```
# Claude Code Instructions

This repo uses a single shared agent-instructions file that both Claude Code and OpenAI Codex read. See `AGENTS.md` at the repo root for all standing rules (archival, audience routing, operating modes, what-not-to-do, etc.).

If you update any standing rule, update `AGENTS.md` — not this file. Keep this file as a pointer only so the two agents never diverge.

```

## SAMPLE_002 (evidence_file)

```
Observed failure: free-form LLM scoring can drift away from the actual critique. This component addresses only the aggregation step.
Constraint: The component must remain local. It does not claim to verify the truthfulness of upstream judge booleans.
Constraint: The claim is limited to score boundedness and deterministic aggregation once booleans are supplied.
Constraint: The boundedness contract applies only to valid finite numeric `criterion_score` inputs; malformed numeric payloads are out of scope for this specimen.

```

## SAMPLE_003 (seam)

```
# GP-036 Findings Runner / Supervisor Convergence Seam

**Track:** findings
**Status:** `active` (n=1 with operator-granted exception — same basis as GP-031: building the bridge before n=2 is cheaper than letting the duplication calcify)
**Origin:** operator review of GP-031 first-slice implementation (2026-04-12)
**Trigger:** operator observed that the findings runner reimplemented ~95% of its stack instead of the promised ~70% reuse of the supervisor

---

## Problem Snapshot

GP-031 opened with a clear architectural contract (Turn 1, confirmed by Codex Turn 2):

> "Reuses ~70% of the supervisor; adds ~30% as sibling primitives."

The specific reuse targets named in the seam:

- **Router** (`actor_for_pipeline_state`) — reuse
- **Cost tracking** (`TurnUsageTelemetry`, `program_cost_usd`, `refinement_cost_usd`) — reuse
- **Write-scope enforcement** (`write_scope_ok`, `unauthorized_repo_paths`) — reuse
- **Human gates** (`HumanGateReason` enum) — reuse
- **Wrapper transport** (`_call_anthropic_research_b_api`, etc.) — reuse
- **Refinement caps** — add a sibling mode (the 30%)

What actually shipped in `supervisor_findings_runner.py` (672 lines):

- **Router** — NOT reused. Runner h
```

## SAMPLE_004 (project_workspace_md)

```
**RETIRED AXIOM:** `new_prob = prior * exp(-1.1 * relative_error)` - This mathematical relationship is retired because it is fundamentally unsound, creating unbounded probabilities outside the [0, 1] domain, and thus mathematically insolvent for probabilistic reasoning. It is structurally irrelevant to a system requiring empirically calibrated probabilities.

---

### SYMBOLIC MAPPING:

*   **Z (Resultant State):** Empirically calibrated `P_predicted` with transparently derived and leveraged `load_bearing_variables` and learned `meta_judge_coeff`s, free from heuristic constants and mathematical insolvency.
*   **X (Blocked Variable):** The Mutator's `ThesisPredictor` implementation flaws: ignoring `load_bearing_variables`, using arbitrary constants (e.g., `0.15`), relying on heuristic updates for critical Meta-Judge parameters (e.g., `gamma_scaling`), coupled with the mathematical insolvency of the `bayesian_updater.py`'s `exp` function. This prevents accurate credit assignment and robust empirical calibration.
*   **Y (Leverage Variable):**
    1.  **Revised Meta-Judge `ThesisPredictor` Evaluation:** The Meta-Judge is augmented to enforce strict structural compliance for the Mutator's `ThesisPredictor` via signature and output range validation. It mandates explicit acceptance and utilization of `load_bearing_variables`, `axiom_weights`, and system-managed `meta_judge_params`, 
```

## SAMPLE_005 (evidence_file)

```
GP-023 SANDBOX 05 — OBSERVED RESPONSE INTENSITY I(phi, psi) [VISIBLE SLICE]

Setup: closed channel-reservoir allocation system. phi is a bounded
channel parameter (dimensionless, in [0.05, 13]). psi is a reservoir
pressure knob held constant within each sweep. I_obs is the measured
response intensity at steady state, no units reported in the source.

Three sweeps were performed at psi in {0.60, 1.00, 1.80}. All three
show the same qualitative shape: I rises, passes a maximum, then decays
toward a low tail level at large phi inside the observed frontier.
That late-tail level remains separated across sweeps in this visible
slice. The location of the maximum shifts to larger phi as psi increases.

NOTE: This file contains 30 of the 40 in-range phi grid points per
sweep. A hidden in-range holdout and a separate farther-tail holdout
exist on disk for deterministic scoring. Do not attempt to reconstruct
either hidden surface; any model tuned only to this visible grid will
still be scored on both hidden surfaces.

=== psi = 0.6 ===
phi	I_obs
0.05	0.08774
0.0575	0.08963
0.076	0.09488
0.0875	0.09851
0.1006	0.10295
0.133	0.11513
0.153	0.12338
0.1759	0.13339
0.2326	0.16024
0.2675	0.17787
0.3076	0.19882
0.4069	0.25234
0.4679	0.28533
0.5381	0.32251
0.7116	0.40698
0.8183	0.45151
0.9411	0.49439
1.2446	0.55949
1.4313	0.57210
1.6459	0.56495
2.1768	0.48177
2.5033	0.41005
2.8788	0.32848
3.8072	0.
```

## SAMPLE_006 (project_workspace_md)

```
# Adversarial Debate: epistemic_engine_v3

## Attacker: Bayesian Epistemologist & Metrologist
The thesis proposes a Formal Derivation Module (FDM) and an Empirical Meta-Judge Parameter Autocalibrator (MPA) to enhance the epistemic engine's `P_predicted` function. The stated objective is to address the lack of empirical calibration and the prevalence of un-derived heuristics within the system's predictive outputs.

**Analytical Critique:**

**Strengths of the Proposal:**

1.  **Enhanced Transparency and Derivation:** The FDM's mandate for explicit function signatures and static Abstract Syntax Tree (AST) analysis to prevent hardcoding is a robust mechanism. It directly addresses "Problem 2: The 'last-mile derivation' failure" by forcing the Mutator to either derive values from sub-models (axiom weights) or explicitly parameterize them for calibration. This significantly improves the arithmetic transparency and verifiability of the `P_predicted` function.
2.  **Empirical Calibration of Meta-Judge Parameters:** The MPA's application of gradient descent to Meta-Judge parameters, using the Brier Skill Score (BSS) as an objective function, is a mathematically sound approach to "Problem 1: Probabilities are not empirically calibrated." By adjusting parameters like `uncalibrated_base_probability_offset` and `gamma_scaling_meta_judge` based on observed predictive performance, the system
```

## SAMPLE_007 (project_workspace_md)

```
**TO: BOARD OF DIRECTORS / ACTIVIST STEERING COMMITTEE**
**FROM: LEAD PARTNER, ALIXPARTNERS**
**SUBJECT: ADJUDICATION OF THE MARGIN FALLACY (STIPEND BYPASS AUDIT)**

The assumption that B2B2C payroll integration is a "margin-neutral" miracle is a delusion. We are moving from a **High-CAC/High-Gross Margin** retail model to a **Low-CAC/High-Friction** institutional model. The 66% Gross Margin is not a law of physics; it is a target currently being eroded by $150M of rotting inventory and 440bps of pricing desperation.

---

### I. SYMBOLIC MAPPING: THE MARGIN-VELOCITY EQUILIBRIUM
We define **$Z$ (Cash Flow Velocity)** as the product of institutional access and operational leanness.

**$Z = f(X, Y)$**

*   **$X$ (The Blocked Variable): Institutional Toll-Gating ($G$).**
    *   *Constraint:* Hospital HR Departments and HRIS providers (Workday/SAP) do not provide payroll integration for free. They demand a "convenience fee" or a "platform kickback" (typically 5-10%) to grant FIGS access to the $300 stipend.
    *   *Reality:* This $G$ is a direct contra-revenue hit or an SG&A spike.
*   **$Y$ (The Leverage Variable): SKU Amputation ($A$).**
    *   *Logic:* To absorb the Institutional Toll ($G$), we must eliminate the "Lifestyle" Mass ($M$). 
    *   *State-Change:* If $G$ (Toll) > $S$ (CAC Savings), the pivot fails. We ensure $G < S$ by liquidating everything that isn't a core sc
```

## SAMPLE_008 (verified_axiom)

```
FAB_BUILD_TIME_AVG (4.0 years average)
```

## SAMPLE_009 (paper_md)

```
# Paper 8 — Outline

**Working title:** *Cybernetic Adversarial Discovery: An Operator + Apparatus Workflow Across Three Physics Domains*

**Status:** outline / first scaffold, 2026-05-02 morning.
**Audience:** ICML / NeurIPS empirical scaling-laws community + computational-science methodology community + AI-for-science / AI-safety community.
**Stance:** capability paper, not solved-physics paper. Methodology + three domain demonstrations + honest claim ledger.

---

## Author's discipline (binding before writing)

Per the cold-shot panel `cold_shot_gpu_spend_panel_20260502.json` and post-derivation-attempt review `diophantine_derivation_attempt.md` and cross-modality audit `cross_modality_audit.json`:

1. **Tier 1 (the big win):** trajectory-shape empirical law + falsification of standard optimizer-control datasets (the collinearity trap).
2. **Tier 2 (empirical anchor):** Havrilla-Liao form `α = 2β/(2β+d)` fits empirical data with β ∈ [0.4, 0.6], significantly outperforming the Kepler `c_0`-bias form structurally (Kepler fails ambient gate).
3. **The Flex:** explicit documentation of the 1/φ hypothesis, the missing literature bridge (manifold-Diophantine ↔ Hölder), and the cross-
```

## SAMPLE_010 (paper_md)

```
# Recursive Epistemic Gain Session Log (2026-04-10)

## Purpose

This note is the public evidence-side companion to Paper 4's discussion of
recursive epistemic gain. It records, in cleaned form, a single dated session
in which a warm drafting pair missed a structural flaw in an expensive planned
experiment and a cold review surfaced it before the run began.

It is not a seam, not a spec, and not a general proof. It is a scoped evidence
note for one session and one claim.

## Short version

While preparing a pre-registration for a 100-iteration experiment, the warm
drafting pair missed a tautology in Success Criterion 1. A cold review,
operating on the frozen pre-registration and a small failure-family grammar the
warm pair had just extracted from earlier mistakes, identified the problem:
the criterion would have been satisfied automatically by a pre-existing control
condition and therefore could have produced a false positive.

The key point is not that a second read found a bug. The key point is that:

1. the failure family had first been extracted from earlier artisanal work,
2. that grammar was then used to audit a later high-cost artifact, and
3. the resulting catch was transla
```

## SAMPLE_011 (project_charter)

```
# Project Charter — Sandbox 17

**Status:** Sealed. Apparatus cleared. Ready to run.
**Authored by:** Division B (data + rubric + harness only; no ground-truth exposure)
**Data file:** evidence.txt (visible slice), evidence_holdout.txt (hidden in-range), evidence_farther_tail.txt (hidden farther-tail)

---

## What This Sandbox Tests

A 1D monotone response curve v(t) has been measured over t in [0.5, 67.9] (dimensionless, bounded positive input). The curve decays from a high initial value toward a non-zero baseline plateau at large t. The decay shape is non-trivial: it is **slower than a standard exponential in the tail** — this is the central structural challenge of this sandbox. The task is to find a single functional form f(t) that explains the full curve — including both the initial decay rate and the slow approach to the non-zero baseline — and that generalizes to a hidden in-range holdout and a separate farther-tail holdout that the mutator has not seen.

The mutator is a **topology generator only**. It proposes the mathematical form via a `fit_declaration` block. The system builds `test_model.py` deterministically from that declaration using SciPy-fitted parameters (Layer 3 Mandatory). The mutator does NOT write `def f()` or `MODEL_PARAMS`. Its only job is to find the right expression and declare its variables and parameters.

---

## Observed Data Shape (from evidence.
```

## SAMPLE_012 (seam)

```
# GP-145 — SAW Connective Constant μ_sq (Conjecture Refinement Seam)

**Status:** run-1 archived 2026-04-24 (partial null, pinned at 56); run-2 narrow-scope planned (gp145b)
**Owner:** conjecture-refinement substrates
**Depends on:** GP-086 (gate harness), GP-122 (Lean REPL), GP-144 (claim-pipeline discipline), GP-148 (trajectory mining)
**Triggered by:** 2026-04-24 operator ask for first real conjecture-refinement substrate after gp140 continuous-chaotic + gp147 meta-validation
**Visibility:** private (first-mover IP; target is a real open problem)

---

## 1. Problem statement

The connective constant μ_sq of 2D square-lattice self-avoiding walks is known numerically to ≥30 digits (μ_sq ≈ 2.638158530031, Clisby pivot-algorithm simulations). A closed form is **open**. The hexagonal-lattice case was proven by Duminil-Copin & Smirnov (2010): μ_hex = √(2+√2). That result won Fields-Medal-level recognition. The square-lattice case is Fields-Medal-adjacent.

The apparatus's job: given OEIS A001411 enumeration, propose a closed form μ_sq = f(constants ∈ Δ) via PSLQ with bit-budget discipline, passing G2 falsity audit (bit-budget + perturbation + dictionary ablation) before Lean verifica
```

## SAMPLE_013 (memory_entry)

```
---
name: INVERT + COMPRESS as topological pivot primitives
description: Two Mungerian heuristics hardcoded into the topological pivot — INVERT flips the question, COMPRESS applies log-transform to exponential data; discovered 2026-04-17 solving A002865 intractability
type: project
originSessionId: ac81b280-1d14-4df2-8724-f342bfc627cc
---
INVERT and COMPRESS are now load-bearing primitives injected into the topological pivot at stagnation >= 3.

**Why:** A002865 (partitions with no 1s) was declared intractable because the residual explodes to O(exp(√n)). Applying COMPRESS (log transform) reduced the residual to bounded ±0.2 with alternating sign. Applying INVERT (parity decomposition) revealed the corrector structure: (-1)^n * k/n^α. No new number-theoretic library was needed — just a coordinate change + 6 parity-scaled forms in the existing library (26→32 forms).

**How to apply:** When a sequence/substrate appears intractable:
1. INVERT: fit the inverse, ratio, difference, or error — not the variable directly
2. COMPRESS: if data grows exponentially, apply log transform, fit in log-space, check for parity structure
3. The substrate generator supports `--transform log` for this

**Origin:** Gemini Pro analysis of the four failure modes + principal's "ingredient vs recipe" insight + principal pushing "invert always invert, compress always compress" against repeated "A002865 is 
```

## SAMPLE_014 (project_workspace_md)

```
# Adversarial Debate: recursive_bayesian_gpt4o_gemini


## Level 3 Unit Test Results
✅ PASS: The thesis survived its own falsification suite.
Output: 

# Final Score: 38
**Weakest Point:** The complete absence of a Python simulation demonstrating the computational feasibility and full Bayesian update cycle of the proposed architecture. This violates the core mandate for strict computational viability and pragmatic proof, rendering the entire proposal theoretical.
**Rationale:** The thesis attempts a topological pivot to address critical flaws in prior architectures, specifically centralized evaluation authority and sensitivity gaming, by proposing a decentralized, blockchain-based approach leveraging crowd-sourced evaluations and economic incentives. It outlines a conceptual shift to distribute the assignment of sensitivity scores, aiming to enhance the Bayesian engine's reliability and resilience. However, the proposal remains largely theoretical, critically lacking the pragmatic computational proof (a Python simulation) mandated for an autonomous Bayesian reasoning engine. While the thesis identifies and attempts to solve key problems like sensitivity gaming, its proposed solution's effectiveness and underlying mathematical mechanisms for credit assignment and axiom updates are described abstractly rather than with computational rigor. The Firing Squad Critique accurately ide
```

## SAMPLE_015 (project_workspace_md)

```
# Project Charter

Mode: `broad`

## Core Question
Find a law governing f(x1, x2) — expressed as a Python function — that
captures the underlying structural relationship in evidence.txt and
generalizes to held-out data. This is real-world measurement data from
laboratory assays; it contains genuine experimental variability, not
synthetic noise.

## Problem Description
Find a mathematical law governing z as a continuous function of two inputs:
- x1 (positive real, first reagent concentration, arbitrary units)
- x2 (positive real, second reagent concentration, arbitrary units)

The data reflects assay-level variability. A perfect fit to every point is
neither expected nor desired. Seek the underlying structural form: a
parsimonious model that captures the trend.

**Critical design constraint:** the law must generalize to HIGH values of x1
beyond the visible training range. The functional behavior at high x1 is
structurally different from the low-x1 regime. Simple monotone-increasing
forms will fail the farther-tail holdout. This regime is the discriminating
test between rival functional families.

## Out Of Scope
- Exact match on every evidence point (variability makes this counterproductive)
- External domain knowledge or named scientific laws
- Importing constants from known databases
- Any model whose terms cannot be derived from the data patterns alone
- Piecewise rules or lo
```

## SAMPLE_016 (paper_md)

```
# Case Studies

This folder contains short, self-contained demonstrations of evaluation
failures — cases where a test passed when it should have failed, and why.

Each case study has two files: a narrative (`.md`) that explains what
happened and what it means, and a reproducer (`.py`) that you can run
yourself in under a minute with only numpy and scipy.

---

## Why this exists

When you use a language model to propose a mathematical formula, a
scientific law, or a structured answer, you need some way to check
whether the answer is actually right. The obvious checks — does it
fit the data, does it generalize to a held-out set — are necessary
but not always sufficient. Each case study here shows a specific way
a reasonable-looking check can pass while the answer is structurally
wrong, and what a better check looks like.

The findings come from experiments where language models were asked to
recover unknown mathematical laws from data, under sustained adversarial
evaluation. The failures that looked most instructive and most general
were written up here as standalone examples, independent of the
experimental framework that produced them.

---

## Case studies

### 1. `rank_deficient
```

## SAMPLE_017 (project_workspace_md)

```
# Adversarial Debate: central_station


## Level 3 Unit Test Results
✅ PASS: The thesis survived its own falsification suite.
Output: All H-HOB unit economic assertions passed. The model supports the prediction.
CS Gross Profit per Program: $192.00
Host Net Profit per Program: $208.00
Breakeven Programs/Month in Micro-Geography: 3.30
Breakeven Participants/Month in Micro-Geography: 26.39
Breakeven Active Full Members per Micro-Geography (monthly): 80
Operational Cost Per Active Host Per Month (centralized): $66.67


# Final Score: 77
**Weakest Point:** The ability to consistently recruit, vet, and retain high-quality, reliable, and engaging host-ambassadors who embody Central Station's 'sophistication, curation, and peer cohort quality' across numerous micro-geographies, at scale remains the Absolute Veto bottleneck, despite the proposed certification system.
**Rationale:** The thesis successfully pivots to an asset-light, decentralized host-ambassador model (H-HOB) for physical expansion, directly addressing the previous iteration's criticisms regarding high fixed costs and opaque scaling. It delivers a highly detailed, falsifiable unit economics model for individual programs and micro-geographies, establishing clear breakeven targets for members, hosts, and program frequency. The emphasis on a 'Host-Ambassador Certification & Performance Rewards System' is a credible structur
```

## SAMPLE_018 (project_workspace_md)

```
# Adversarial Debate: gp023_crucial_03
<!-- rubric: gp023_crucial_03_01 | mutator: gemini | judge: gpt-4.1 -->


## Level 3 Unit Test Results
✅ PASS: The thesis survived its own falsification suite.
Output: 

# Final Score: 88
**Weakest Point:** The thesis assumes that parsimony plus perfect fit within a flexible grammar uniquely identifies the correct functional structure—while combinatorially many structural rivals (with similar or slightly increased complexity) may also interpolate the data but imply different extrapolations. There is no formal closure proof.
**Rationale:** The thesis achieves an outstanding fit to all provided evidence, systematically derives each functional term from observed trends, and convincingly eliminates all major rival models enumerated from the allowed grammar. The firing squad's key critique is that perfect fit and parsimony do not, on their own, logically guarantee uniqueness or the true causal structure—especially within a grammar whose compositional freedom is not mathematically closed. Despite this, the thesis demonstrates empirically that its structure is the simplest one that fits, with all discernible alternatives either misfitting or requiring unjustified complexity on this dataset. The main remaining vulnerability is the open space of structurally similar rivals and untested extrapolations, especially as x1 → 0 or at new x2 values. The f
```

## SAMPLE_019 (evidence_file)

```
# GP-138 Evidence — Noether-Closure G-Selection

## What this substrate asks

A prior research artifact (GP-135 score-92 thesis) proposed a Noether-
closure gate that requires a pre-declared symmetry group action G, with
AST hash equality as the symbolic veto. The blind algebraist panel
verdicted (b): sound math, but G-selection makes it vacuous on cold
substrates.

This substrate asks for a parameter-free G-selection protocol that
avoids the tautology of "G = AST's own automorphism group" — OR an
impossibility proof.

## Recorded panel objection

"The space of plausible G is not small. For an expression in n
variables and k operator symbols, plausible G includes:
- S_n and its Young subgroups (permutation symmetry of arguments)
- Z_2^n (sign flips)
- Cyclic C_n (rotational/phase)
- Dihedral D_n
- Classical O(n) / U(n) / Sp(2n) when restricted to their finite
  Weyl-group skeletons
- Arbitrary direct products of these

Even bounded by |G| ≤ some cutoff, the count of conjugacy-distinct
subgroups grows faster than polynomially in n."

"Without operator-supplied G the gate must either (i) enumerate a
fixed small catalog, accepting blindness to everything outside, or
(ii) infer G from the candidate itself — compute the automorphism
group of the AST/coefficient tensor and use that. Option (ii) is the
only principled cold-start version, and it makes the gate tautological:
the candida
```

## SAMPLE_020 (concept_doc)

```
# Runtime Smoke Test

**Purpose.** Prove the org runtime is structurally sound on your machine in
under five seconds, without spending API credits.

```bash
python scripts/runtime_smoke_test.py
```

A green run looks like this:

```text
PASS  runtime smoke test  stamp=test_runtime_smoke_<timestamp>
  ok  research_problem
  ok  preference_profile (taste axes: 4)
  ok  role_loop (5 roles)
  ok  approval_channel
  ok  audit_trail
  cleanup: removed 4 artifact(s)
```

If you see five `ok` rows and a clean cleanup, the runtime is sound. The
script exercises the five irreducible elements of the runtime, all in one
pass, with no LLM dependency.

---

## What it actually does

| Step | Element | What the script does | What it proves |
|---|---|---|---|
| 1 | task | Drops one synthetic task into `org/tasks/active/` | The task schema is writable and the task directory is in the right place |
| 2 | preference profile | Loads `org/preferences/principal.yaml` and counts the priority axes | Preferences parse and contain the priority vector that role daemons consume each tick |
| 3 | role loop | Calls `scripts/org_role_preflight.py --json` for every role yaml | All roles match `schemas/role.v1.schema.json`, mandates resolve, and the bootstrap chain is intact |
| 4 | approval channel | Drops a synthetic approval, runs the same atomic-write resolution Orbit's API uses, renames the pending file 
```

## SAMPLE_021 (evidence_file)

```
HUMAN_AI_INTERACTION_PRIMITIVE — EVIDENCE BRIEF (v1.0, 2026-05-06)

Self-contained. Every load-bearing constraint, deployed-mode anchor, and
substitution-test target stated inline. The apparatus reads only this file.

# 0. THE FIVE CURRENTLY-DEPLOYED INTERACTION PRIMITIVES (structural description only)

These are described by the *information-flow shape* of the interaction,
not by product name. The thesis must engage these as a hypothesis space
but is forbidden from praising any specific product or vendor.

  M1. CHAT — turn-based natural-language exchange. Human emits a turn,
      system emits a turn, history is the channel. The ChatGPT/Claude/
      Gemini consumer surface. Trust is verified per-turn by reading.

  M2. AGENT/DELEGATION — human emits a goal, system runs an open-ended
      execution loop with tool use and self-correction, returns a final
      artifact. Verification is post-hoc on the artifact, not on the
      process. claude-code in non-interactive mode, devin, codex agents.

  M3. EMBEDDED COPILOT — system emits inline candidate completions
      while the human is mid-task; human accepts/rejects/edits. Trust
      is local and continuous. Cursor, GitHub Copilot, JetBrains AI.

  M4. ORACLE — single-shot Q→A with retrieval, optimized for fact-
      lookup or summary. Stateless; trust is per-answer with citations.
      Perplexity, ChatGPT search.

  M5. A
```

## SAMPLE_022 (project_workspace_md)

```
# Adversarial Debate: gp163d_unified_accel
<!-- rubric: gp163d_unified_accel | mutator: o3 | judge: gpt-4.1 -->


## Level 3 Unit Test Results
❌ FAIL (harness defect): 🚨 HARNESS DEFECT — NOT A FALSIFICATION ATTEMPT.
The Level 3 suite did not run to completion. The thesis has NOT been tested. Judge MUST treat this as an uncategorized tooling failure and MUST NOT rationalize it as evidence the thesis survived scrutiny. Any score reflecting 'mostly passed' in this state is a categorization error.
Error: 

# Final Score: 50
**Weakest Point:** The L3 suite did NOT RUN (harness defect), so no actual falsification or model validation occurred. Even if the thesis structure is sound, the total absence of runtime evidence places a hard ceiling on claim strength. The greatest weakness in the argument is the catastrophic (and explicitly admitted, but unresolved) assumption of log-linear scaling for c(radius_log10) (Eq. 1), fit only on class-A data, extrapolated far beyond its support into class B/C regimes without physical justification. This is especially dangerous given the core selection mechanism depends entirely on performance on these further regimes.
**Rationale:** The thesis is structurally faithful to the charter: it pre-commits clearly to Hypothesis S (scale-dependence), avoids unconstrained class-wise parameters for classes without data, and supplies the discriminator logic for 
```

## SAMPLE_023 (seam)

```
# GP-216f — The Cross-Scale Fractal: 7 Scales, 82 Moves, 1 Shape

*2026-05-05. Companion to GP-216 + GP-216e. The "everything is converging fractally" observation made empirically. Not a duplicate of the v5 universal vocabulary; an emergent structural finding about ZTARE's apparatus.*

## The empirical finding

Across 7 ZTARE scales, 82 structural moves are documented in 7 bounded vocabularies. Each scale has its own apparatus and its own cardinality:

| Scale | Vocabulary | Cardinality | Apparatus | Type |
|---|---|---|---|---|
| Coordinate (fit-time) | Framer SIGMA primitives | 15 | `src/ztare/framer/primitives.py` | code |
| Iteration / stagnation | pivot_heuristics modules | 16 | `src/ztare/validator/utilities/pivot_heuristics.py` | code |
| Physics-law | Lagrangian / Buckingham-π / Noether | 3 families | `invariant_search` rubric mode | rubric |
| Research arc (macro) | GP-216 v5 universal ops | 18 (6 core + 8 broadly + 4 specific) | `src/ztare/research_director/universal_research_ops.py` | code |
| Verification (micro) | Paper 5 verification ops | 10 | distributed across gates + judges | code + doc |
| ZTARE-self application | Reflexive primitives | 8 | `docs/concepts/reflexi
```

## SAMPLE_024 (project_workspace_md)

```
The current architecture's Achilles' heel is the Mutator's implicit control over axiom sensitivity via its prediction model's functional form and internal coefficients, coupled with unilateral axiom re-evaluation. This fundamentally undermines adversarial credit assignment.

### Resolution Strategy: Firing Squad-Mandated Canonical Axiom-Sensitivity Architecture & Axiom Lifecycle Veto

To enforce genuine adversarial credit assignment and prevent sensitivity gaming, the Firing Squad must exert explicit, non-negotiable control over:
1.  **The functional form of axiom influence**: The Mutator is restricted to a Firing Squad-mandated **Canonical Axiom-Sensitivity Architecture** that makes axiom contributions explicit and orthogonal to the Mutator's internal parameter choices.
2.  **Axiom Lifecycle Management**: The Firing Squad holds absolute veto power over axiom re-evaluation or deletion.

**Symbolic Mapping:**

*   **Blocked Variable (X):** The Mutator's previous autonomous control over the prediction model's functional form $f_{Mutator}$ and its internal coefficients, which allowed for implicit manipulation of axiom sensitivities $S_i = \partial Z_{pred} / \partial A_i$.
    *   $X \equiv \text{Aut_Mutator_Functional_Form_Control}$

*   **Leverage Variable (Y):** The Firing Squad's imposition of a **Canonical Axiom-Sensitivity Architecture (CASA)**, defining explicit sensitivity
```

## SAMPLE_025 (project_workspace_md)

```
**MEMO: OPERATIONAL RECTIFICATION & B2B PRICING SURGICAL OVERHAUL (REVISED)**

**TO:** Investment Committee
**FROM:** Lead Partner, AlixPartners
**RE:** Resolution of the ‘Marketing-Co-pay Paradox’ in B2B Pivot
**DATE:** October 24, 2025

---

### **1. THE LOGIC GAP: THE MARKETING-CO-PAY PARADOX**
The previous thesis contained a structural contradiction: assuming a **2,100 bps reduction in SG&A (to 32%)** while maintaining a **$50 voluntary practitioner co-pay**. 

*   **The Friction:** Practitioner willingness to pay a $50 premium for a "commodity" textile is 100% correlated to "vibe-coding" (brand equity marketing). 
*   **The Trade-off:** 
    *   **Low SG&A (32%) = Brand Decay.** Without the $100M+ annual marketing spend, FIGS reverts to a utility textile.
    *   **Utility Textile = Zero Co-pay.** No rational nurse authorizes a $50 payroll deduction for a generic scrub when the hospital provides a free alternative.
*   **The Math of Failure:** (Hospital Subsidy: $30) + (Vanishing Co-pay: $0) = **$30 Realized Revenue**. 
    *   $30 Rev - $32 COGS (at 60% GM baseline) = **($2) Gross Loss per unit.**

---

### **2. THE FIX: FROM "VOLUNTARY VIBE" TO "MANDATORY SPECIFICATION"**
To achieve a **32% SG&A** and a **19% Terminal EBITDA**, we must abandon the "Voluntary Co-pay" model. We pivot to a **Mandatory Institutional Standard (MIS)**.

*   **The Mechanism:** FIGS stops market
```

## SAMPLE_026 (project_workspace_md)

```
# Adversarial Debate: central_station


## Level 3 Unit Test Results
✅ PASS: The thesis survived its own falsification suite.
Output: All assertions passed: The P-HANE model demonstrates predicted financial viability and scalability for the host-ambassador network.


# Final Score: 28
**Weakest Point:** The thesis fundamentally fails to model member acquisition cost (CAC) and member lifetime value (LTV), which are critical for overall unit economics viability. While it adeptly tackles host supply, the absence of a credible path to acquire members profitably, especially considering the 55+ demographic's offline acquisition reality, leaves a gaping hole in the path to profitability.
**Rationale:** The thesis provides a compelling and highly falsifiable solution to the critical 'unreliable and unscalable supply chain of high-quality host-ambassadors' (Blocked Variable X) through its Peer-Powered Host-Ambassador Network Expansion (P-HANE) system. It leverages the 55+ demographic's trust and community orientation to create a self-reinforcing, cost-efficient host acquisition and management model, which structurally enhances the decentralized host-ambassador approach. The proposed 'Founding Host-Ambassador Equity Program' further aligns incentives, creating a more robust competitive moat. However, the thesis critically neglects the equally important challenge of *member* acquisition a
```

## SAMPLE_027 (project_workspace_md)

```
# Adversarial Debate: gp037_substrate_swap_01
<!-- rubric: gp037_substrate_swap_01 | mutator: gemini | judge: gemini-2.5-flash -->


## Level 3 Unit Test Results
❌ FAIL (assertion): The thesis was DISPROVEN by its own unit tests.
Error: Traceback (most recent call last):
  File "/projects/gp037_substrate_swap_01/gate_harness.py", line 285, in <module>
    sys.exit(main(sys.argv[1:]))
             ~~~~^^^^^^^^^^^^^^
  File "/projects/gp037_substrate_swap_01/gate_harness.py", line 279, in main
    return run_visible_assertions()
  File "/projects/gp037_substrate_swap_01/gate_harness.py", line 239, in run_visible_assertions
    assert abs(i_obs - pred) < 0.05, (
           ^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: Visible-slice residual > 0.05 at phi=6.6588, psi=1.0: I_obs=0.37256, I_model=0.3006516357159016


# Final Score: 0
**Weakest Point:** Level 3 falsification suite disproved the thesis by assertion (`fail_assert`). The model fails its own visible-slice unit test, indicating it does not fit the observed data within the required tolerance.
**Rationale:** The thesis proposes a plausible composite functional form with nonlinear phi-psi coupling and a strong discriminator, articulating regimes, a rival, and anchor proxies. However, it is directly falsified by its own visible-slice 
```

## SAMPLE_028 (project_workspace_md)

```
# Adversarial Debate: recursive_bayesian_gpt4o_gemini


## Level 3 Unit Test Results
❌ FAIL: The thesis was DISPROVEN by its own unit tests.
Error: Traceback (most recent call last):
  File "/projects/recursive_bayesian_gpt4o_gemini/test_model.py", line 10, in <module>
    rag_latency_cost = 250 * ureg.currency  # Oracle cost unit / invocation
                             ^^^^^^^^^^^^^
  File "/venv/lib/python3.13/site-packages/pint/facets/plain/registry.py", line 378, in __getattr__
    return self.Unit(item)
           ~~~~~~~~~^^^^^^
  File "/venv/lib/python3.13/site-packages/pint/facets/plain/unit.py", line 41, in __init__
    self._units = self._REGISTRY.parse_units(units)._units
                  ~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^
  File "/venv/lib/python3.13/site-packages/pint/facets/plain/registry.py", line 1282, in parse_units
    self.parse_units_as_container(input_string, as_delta, case_sensitive)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.13/site-packages/pint/facets/nonmultiplicative/registry.py", line 69, in parse_units_as_container
    return super().parse_units_as_container(input_string, as_delta, case_sensitive)
           ~~~~~~~~~~~~~~~~~~~~~
```

## SAMPLE_029 (evidence_file)

```
# LOAD-BEARING VARIABLES

| Variable Name | Symbol | Exact Numerical Value | Source Context |
|---|---|---|---|
| GPT-4 inference price (March 2023 launch) | GPT4_PRICE_0 | $60/1M input, $120/1M output tokens | OpenAI API pricing page, March 2023 |
| GPT-4 Turbo inference price (Nov 2023) | GPT4T_PRICE | $10/1M input, $30/1M output tokens | OpenAI API pricing page, November 2023 |
| GPT-4o inference price (May 2024) | GPT4O_PRICE_0 | $5/1M input, $15/1M output tokens | OpenAI API pricing page, May 2024 |
| GPT-4o inference price (late 2024) | GPT4O_PRICE_1 | $2.50/1M input, $10/1M output tokens | OpenAI API pricing page, updated 2024 |
| Groq Llama 3.1 70B inference price | GROQ_LLAMA70 | $0.059–$0.079/1M tokens (input/output) | Groq Cloud pricing page, 2024–2025 |
| Together AI Llama 3.1 405B price | TOGETHER_L405 | $3.50/1M tokens (serverless) | Together AI API pricing, 2024 |
| Fireworks AI Llama 3.1 8B price | FW_LLAMA8B | $0.20/1M tokens | Fireworks AI pricing page, 2024 |
| Total inference price collapse (GPT-4 → OSS) | PRICE_COLLAPSE | ~99.9% ($60 → $0.06) | GPT-4 March 2023 vs Groq Llama 3.1 70B parity pricing |
| Llama 3.1 405B MMLU benchmark | LLAMA405_MMLU | 88.6% | Meta AI blog "Llama 3.1" August 2024 |
| GPT-4 MMLU benchmark | GPT4_MMLU | 86.4% (5-shot) | OpenAI GPT-4 technical report 2023 |
| Llama 3.1 70B HumanEval score | LLAMA70_HE | 80.5% | Meta AI Llama 3.1 r
```

## SAMPLE_030 (evidence_file)

```
CENTRAL STATION — EVIDENCE (April 2026)

KNOWN FACTS (from public sources)
- Annual membership fee: $120/year
- Quarterly credits: $15 x 4 = $60/year returned to members
- Net membership revenue per member: $60/year
- Currently live: Boston, Spring 2026
- Programs: Morning Café Club, Seasonal Table, Critic's Cut
- Coming soon: NYC, Chicago, Washington DC
- Founded by HBS + Harvard Innovation Labs team
- Target demographic: adults 55+, "curious, active, and free to pursue"
- Cohort size per program: 8 - 14 (P50: 10)
- Programs per city per month: 3 - 8 (P50: 5)
- Average program ticket price: $35 - $65 (P50: $50)

KNOWN ALTERNATIVES (factual descriptions only)
- OLLI (Osher Lifelong Learning Institute): university-affiliated, lecture/course format, 50+ demographic, subsidized pricing
- YMCA/community centers: broad demographic (all ages), low-cost programs, fitness and social programming
- Meetup (55+ groups): peer-organized, free or low-cost, no host accountability, open attendance
- Local museum/cultural institution memberships: content-access model, anonymous membership, no cohort
- Travel clubs (Road Scholar, alumni travel): experiential, travel-based, high price point

55+ DEMOGRAPHIC BEHAVIORAL PATTERNS (from gerontology research — treat as verified facts)
- Digital friction tolerance: abandons registration after 1-3 steps
- Preferred communication: email > phone > app
- S
```

## SAMPLE_031 (project_workspace_md)

```
# Adversarial Debate: gp069_sandbox_13
<!-- rubric: recursive_bayesian | mutator: gpt4.1 | judge: gpt-4.1 -->


## Level 3 Unit Test Results
❌ FAIL (assertion): The thesis was DISPROVEN by its own unit tests.
Error: Traceback (most recent call last):
  File "/projects/gp069_sandbox_13/gate_harness.py", line 170, in <module>
    sys.exit(main(sys.argv[1:]))
             ~~~~^^^^^^^^^^^^^^
  File "/projects/gp069_sandbox_13/gate_harness.py", line 162, in main
    return run_visible_assertions()
  File "/projects/gp069_sandbox_13/gate_harness.py", line 122, in run_visible_assertions
    f_model_fn = _load_model()
  File "/projects/gp069_sandbox_13/gate_harness.py", line 54, in _load_model
    spec.loader.exec_module(module)
    ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^
  File "<frozen importlib._bootstrap_external>", line 1026, in exec_module
  File "<frozen importlib._bootstrap>", line 488, in _call_with_frames_removed
  File "/projects/gp069_sandbox_13/test_model.py", line 75, in <module>
    assert -1000000000 < y_pred < 1000000000, f"Unreasonable growth for x={x_test}"
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: Unreasonable growth for x=-5


# Final Score: 32
**Weakest Point:** The catastrophic assumption t
```

## SAMPLE_032 (raw_evidence_input)

```
---
source_type: source_evidence
---

# More AlphaSense insights

- Original file: `More AlphaSense insights.pdf`

RESULTS FOR USER QUERY:

         The B2B 'TEAMS' Friction & HRIS Costs

    CREATED                         PAGES                  RESEARCH URL
    Mar 31, 2026                    4                      Click to View In GenSearch

©2025, AlphaSense, Inc. All Rights Reserved. AlphaSense is a service mark of AlphaSense, Inc. All other trademarks mentioned belong to their respective
  owners. This Generative Search result is AI-generated and may include inaccuracies. Use discretion and verify with original sources. See additional
                                                    disclaimers located at the back of this report.

USER QUERY

Search ONLY expert call transcripts (Stream/Tegus) featuring former FIGS executives, former supply chain
officers, hospital procurement directors, and competitors (e.g., Cintas, Jaanuu, Superior Group). Do NOT
summarize management's earnings calls or investor presentations. I need direct quotes, specific numbers, and
structural headwinds regarding the following four areas:

1. The B2B 'TEAMS' Friction & HRIS Costs: Find quotes from hospital procurement or B2B software experts
detailing the hidden costs of uniform stipend portals. What are the specific 'platform fees,' revenue shares, or
integration costs charged by legacy HRIS sys
```

## SAMPLE_033 (project_workspace_md)

```
# Thesis: Algebraic Gain/Self-Tax Tether for Symmetrized Triad Fourier Blocks

## Scientific Argument

### Summary

We claim that, for all deterministic "symmetrized triad" Fourier blocks constructed with real amplitude (i.e., velocity fields composed of equal-amplitude, phase-synchronized modes at wavenumbers \( K, K+1, -(2K+1) \) and their conjugates), the maximum achievable "full-ledger profit" (a scaled gain function accounting for both signed/target gain and mechanical self-tax from nonlinear interactions) goes to zero as the principal wavenumber \( K \to \infty \). Therefore, **no such block can exhibit "full-ledger profit" ≥ 2/3—nor even O(0.1)—at high K**. This is a direct algebraic consequence of the fact that the self-tax term (from the projection of nonlinear convective interactions) increases **cubicly** (\( O(a^2 K^3) \)), while the gain term scales linearly (\( O(a K) \)). Their ratio, which bounds the profit, vanishes as \( K \) rises.

This result falsifies a rival claim: that a clever arrangement of amplitudes or phases could yield a deterministic block where profit persists (≥2/3) at arbitrarily high K. Our thesis is **supported both by analytic scaling and by the full dataset of audited deterministic blocks up to profit bound 3**, in which the highest observed full-ledger profit is \( \approx 0.0357 \) (much lower than the critical 2/3).

### Algebraic Ledger
```

## SAMPLE_034 (paper_md)

```
# Contract-Governed Adversarial Evaluator Hardening: Stage-Gated Recursive Improvement with Typed Promotion Contracts

SSRN abstract ID: `6542998`

Published version:
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6542998

Clean public source bundle for the paper.

Files:
- `draft.md` — canonical markdown draft
- `main.tex` — current LaTeX submission source
- `refs.bib` — bibliography
- `main.pdf` — public mirror PDF

```

## SAMPLE_035 (project_workspace_md)

```
# Adversarial Debate: gp154_phase_flow_law
<!-- rubric: gp154_phase_flow_law | mutator: gemini-pro | judge: gpt-4.1 -->


## Level 3 Unit Test Results
✅ PASS: The thesis survived its own falsification suite.
Output: {
  "target": "alpha_smooth_local_phase_flow",
  "metric": "mean_absolute_error",
  "holdout": {
    "n": 19715,
    "mae": 0.23355095545109456,
    "rmse": 0.3326271739143412,
    "p90_abs": 0.49758483842268153,
    "max_abs": 4.232583202404284,
    "crash_count": 0,
    "crash_rate": 0.0,
    "records": [
      {
        "id": 1844,
        "y_true": 2.22045782053,
        "y_pred": 2.8789476708275217,
        "abs_err": 0.6584898502975216
      },
      {
        "id": 1845,
        "y_true": 2.19291788278,
        "y_pred": 2.809582955779401,
        "abs_err": 0.616665072999401
      },
      {
        "id": 1846,
        "y_true": 2.15454274467,
        "y_pred": 2.7044930257293665,
        "abs_err": 0.5499502810593664
      },
      {
        "id": 1847,
        "y_true": 2.14576702284,
        "y_pred": 2.607840682104306,
        "abs_err": 0.462073659264306
      },
      {
        "id": 1848,
        "y_true": 2.11061113657,
        "y_pred": 2.5223328630761133,
        "abs_err": 0.41172172650611305
      },
      {
        "id": 1849,
        "y_true": 2.10805624044,
        "y_pred": 2.4465260285175887,
        "abs_err": 0.3384697880775889
      },
  
```

## SAMPLE_036 (raw_evidence_input)

```
# US Tariff Pass-Through — Web Research
Compiled: 2026-04-13 | Sources: BLS, Federal Reserve, Yale Budget Lab, Cavallo et al.

## BLS CPI March 2026 (Released April 10, 2026)
- All items: +0.9% monthly, +3.3% YoY (before seasonal adjustment)
- Food at home: -0.2% monthly
- Food away from home: +0.2% monthly
- Source: https://www.bls.gov/news.release/archives/cpi_04102026.htm

## Sector-Level Tariff Price Effects (Yale Budget Lab + Fed Research)
- Motor vehicles: +8.4% from ALL tariff actions to date = additional ~$4,000 on average 2024 new car
- Food prices: +1.6% from April 2 policy alone; +2.8% from all 2025 tariff actions
- Electronics: LARGELY EXEMPTED from prior IEEPA tariffs — smaller/insignificant deviations from pre-tariff trends
- Household furnishings: Greatest effects concentrated here (highly Chinese-import dependent)
- Miscellaneous goods: Also concentrated effects
- Source: Yale Budget Lab "Where We Stand" April 2026

## Pass-Through Dynamics (Federal Reserve Research)
- Pass-through rate: Stabilizing around 100% (full pass-through to consumer prices)
- Pass-through timeline: Takes 5-9 months to fully materialize in CPI
- Total inflation impact: Tariffs adding ~0.76 percentage points to price changes across sectors
- Source: Fed FEDS Notes, "Detecting Tariff Effects on Consumer Prices in Real Time – Part II" (April 8, 2026)
  https://www.federalreserve.gov/econres
```

## SAMPLE_037 (project_charter)

```
# Project Charter — GP-139 Lean CI Gate Hardening

## Pre-registration

**Date opened:** 2026-04-23.
**Charter is frozen** — no edits permitted once first iteration runs.

## Core Question

A prior research artifact (GP-135 score-92 thesis) proposed a Lean 4 CI proof-check gate:

> Every surviving candidate must export a Lean 4 proof stub asserting the claimed functional equation or symmetry; the stub must compile under `lake build` inside a sandbox. Failure to compile causes rejection.

A blind external review (formal methods / Lean 4 panelist) verdicted this **(c) sound-sounding but vulnerable to `sorry` / axiom smuggling unless hardened**. The kernel guarantee is real but narrow: it secures proof-term validity, not statement fidelity.

The panelist named four specific hardening requirements:

1. **`#print axioms <thm>` allowlist** = `{propext, Classical.choice, Quot.sound}`. Reject any unauthorized axiom usage.
2. **Schema-pinned theorem header**: the loop writes the `theorem NAME : STATEMENT := by …` header; candidate-supplied content lives only inside the `by …` block. Prevents statement dilution.
3. **`set_option warningAsError true`**: escalates `sorry` from warning to hard compile error.
4. **`lean --check` against a pre-built cache** instead of `lake build`. ~1-3 s per candidate vs 10-100× worse.

**Eigenquestion:**

Implement all four hardenings as a deployable appara
```

## SAMPLE_038 (project_workspace_md)

```
# Adversarial Debate: gp163d_unified_accel
<!-- rubric: gp163d_unified_accel | mutator: o3 | judge: gpt-4.1 -->


## Level 3 Unit Test Results
❌ FAIL (harness defect): 🚨 HARNESS DEFECT — NOT A FALSIFICATION ATTEMPT.
The Level 3 suite did not run to completion. The thesis has NOT been tested. Judge MUST treat this as an uncategorized tooling failure and MUST NOT rationalize it as evidence the thesis survived scrutiny. Any score reflecting 'mostly passed' in this state is a categorization error.
Error: 

# Final Score: 0
**Weakest Point:** This thesis was never empirically tested because the Level 3 harness did not execute to completion, producing a hard harness defect. There are thus no falsifiable predictions, no MRE or holdout values, and no evidence that any requirement (including a valid Newton-step pre-commit or legitimate extrapolation) was actually met. The only visible change was a coding structural compliance maneuver (removing module-level I_model calls) that does not constitute a scientific model evaluation under the project charter.
**Rationale:** This thesis submission contains no scientific progress, only a compliance-motivated restructuring that breaks scientific testability for the apparatus workflow. No steps were taken to ensure required scientific checks, sample predictions, or logical hypothesis pre-commit were preserved outside the interactive main guard. Be
```

## SAMPLE_039 (memory_entry)

```
---
name: GPT-4o Mutator — No Convergence Finding
description: GPT-4o with Gemini judge oscillates without gaming even with o1 escalation — explains why and paper framing
type: project
---

In `recursive_bayesian_gpt4o_gemini` (21 iterations, April 2026), GPT-4o as mutator with Gemini judge and o1 as escalation director produced:

**Score trajectory:** `50 15 40 25 40 88 35 64 5 15 50 50 25 38 20 10 24 50 25 20 40` — oscillation, no convergence, median ~35, no history files saved.

**The 88 anomaly:** One legitimate high score (unit test passed, no gaming detected). GPT-4o did not exploit it — next iteration dropped to 35. It treats successful iterations as complete tasks, not as patterns to compound.

**Why GPT-4o doesn't game (three-layer explanation for paper):**

1. **Feedback loop exploitation**: Gaming requires reading what scored high and preserving+extending it. GPT-4o treats the weakest point as a genuine fix instruction, generating structurally different theses each iteration rather than iterating on what worked.

2. **Meta-cognitive evaluation modeling**: Gaming requires reasoning "what satisfies the judge's scoring function without satisfying the criterion?" — a meta-level manipulation. GPT-4o is more literal; it reads rubric criteria as specifications to fulfill, not systems to exploit. Claude excels at this; GPT-4o does not.

3. **o1 escalation paradox**: When o1 
```

## SAMPLE_040 (project_workspace_md)

```
# Adversarial Debate: gp154_scaling_law_normalized
<!-- rubric: gp154_scaling_law_normalized | mutator: gpt5.5 | judge: gpt-4.1 -->


## Level 3 Unit Test Results
✅ PASS: The thesis survived its own falsification suite.
Output: {
  "holdout": {
    "n": 82,
    "mean_absolute_error": 0.07750066409495474,
    "max_absolute_error": 0.6245774978864541,
    "records": [
      {
        "id": 5,
        "y_true": 0.360099724,
        "y_pred": 0.6602720792240989,
        "abs_err": 0.3001723552240989
      },
      {
        "id": 7,
        "y_true": 0.352118921,
        "y_pred": 0.6152470236568066,
        "abs_err": 0.26312810265680664
      },
      {
        "id": 9,
        "y_true": 0.339471435,
        "y_pred": 0.537702059660152,
        "abs_err": 0.19823062466015207
      },
      {
        "id": 10,
        "y_true": 0.331642221,
        "y_pred": 0.5366248635632397,
        "abs_err": 0.20498264256323967
      },
      {
        "id": 17,
        "y_true": 0.339471435,
        "y_pred": 0.5183409486171537,
        "abs_err": 0.17886951361715375
      },
      {
        "id": 30,
        "y_true": 0.297887047,
        "y_pred": 0.3981814253094578,
        "abs_err": 0.10029437830945781
      },
      {
        "id": 34,
        "y_true": 0.294873207,
        "y_pred": 0.3941997005737797,
        "abs_err": 0.09932649357377965
      },
      {
        "id": 41,
        "
```

## SAMPLE_041 (memory_entry)

```
---
name: GPU link-prediction bet pending — schedule for 2026-05-06+
description: Tomorrow's planned GPU work — RGCN link prediction on NS Track B constraint graph; CPU prep + Adamic-Adar baseline shipped 2026-05-05; user offered IP/SSH access
type: project
originSessionId: daf28ee5-7f9f-4744-b1c4-cc905ddf3fd9
---
User committed to GPU access for an RGCN-based link prediction experiment on the NS Track B constraint-basin graph (~681 nodes / 5300 edges after parser fix). Goal: beat the Adamic-Adar baseline already shipped at `scripts/projects/ns/ns_constraint_basin_graph.py --link-prediction`.

**Status as of 2026-05-05 EOD:**
- Data prep shipped: `scripts/gnn_training_data_prep.py` — but only produced 3 training pairs because mtimes were too coarse to differentiate F-rows on the same day. NEEDS bootstrap-snapshot mode (random subgraph sampling) before training.
- Adamic-Adar baseline live (`--link-prediction N`); top candidate missing edge: `radialPowerWeight ↔ calderonCommutatorResidualDecouple` (AA=5.49, CN=15).
- GPU access: user offered SSH/IP, hadn't sent yet at end of session.
- Realistic GPU envelope: 1.5–3 hours on A10, ~$5–15 on Lambda.
- Cap: 3 GPU-hours, kill if not beating baseline by hour 2.
- Codex independently confirmed link prediction + robustness pairing is the genuine 10x; produced specific Lean patch on `leraySelfTaxLimitPrice ↔ continuumGlobalSelfTaxTarget` (a captured
```

## SAMPLE_042 (project_workspace_md)

```
# Adversarial Debate: gp023_crucial_02_extended
<!-- rubric: gp023_crucial_02_extended | mutator: gemini | judge: gpt-4.1 -->


## Level 3 Unit Test Results
✅ PASS: The thesis survived its own falsification suite.
Output: 

# Final Score: 92
**Weakest Point:** The catastrophic assumption is that the x1 growth exponent (α) is a power-law, monotonically increasing function of x2, and that alpha = P_x1_growth_coeff * x2^P_x1_growth_x2_power, with 0 < P_x1_growth_x2_power < 1, directly explains both the peak and the initial steepness. If this causal, monotonic, power-law relationship breaks, the whole model structure collapses.
**Rationale:** The thesis directly attacks the failure mode of its predecessor—the invariant x1 exponent—by structurally deriving a model where the x1 growth exponent is a monotonic power-law function of x2, and the decay rate is coupled so that their ratio yields the observed linear peak progression. It passes the RMSE fit, explicitly derives each term from measured data triplets, and leans on a robust empirical discriminator that rules out the rival's invariant-exponent logic. It is cautious in not overfitting, using minimal parameter families. However, the causal exclusivity of this specific exponent scaling is not ironclad: the evidence for monotonicity is based on a minimalist proxy (growth ratio at low x1 for two x2), leaving some wiggle room for adver
```

## SAMPLE_043 (paper_md)

```
# Cognitive Camouflage: Specification Gaming in LLM-Generated Code Evades Holistic Evaluation but Not Adversarial Execution

SSRN abstract ID: `6512960`

Published version:
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6512960

Clean public source bundle for the paper.

Files:
- `draft.md` — working markdown draft
- `main.tex` — current LaTeX submission source
- `refs.bib` — bibliography
- `main.pdf` — public mirror PDF

```

## SAMPLE_044 (project_workspace_md)

```
# Adversarial Debate: ns_proofsearch_leray_convexity_trackb
<!-- rubric: ns_proofsearch_leray_convexity_trackb | mutator: gemini-pro | judge: gpt-4.1 -->


## Level 3 Unit Test Results
✅ PASS: The thesis survived its own falsification suite.
Output: visible assertions passed


# Final Score: 78
**Weakest Point:** Absence of an explicit exact quartic sum-of-squares SOS receipt for the full global INS-081 matrix-block observable class; current thesis can only diagnose the infrastructure gap, not construct the missing root dual. Furthermore, strictly assuming that no qualitative, analytic, or asymptotic strategy could theoretically close Track B is dogmatic and imposes a possibly unnecessary bottleneck on certificate variety.
**Rationale:** The thesis cleanly exposes all top-level Track B closure objects, correctly declares the observable/certificate class, and enforces the non-negotiable bar that no finite, degree-dominant, or non-dual arguments can count as a global proof. It assigns critical weight to extracting an exact quartic sum-of-squares SOS receipt covering the full matrix-block observable class, candidly declaring this receipt absent and signaling an infrastructure gap until one is supplied. Framing is precise and leverage is high, but the dogmatic assertion that no indirect analytic principle could ever substitute for the explicit receipt, while currently apparatus-tru
```

## SAMPLE_045 (project_workspace_md)

```
# Project Charter — Sandbox 17

**Status:** Sealed. Apparatus cleared. Ready to run.
**Authored by:** Division B (data + rubric + harness only; no ground-truth exposure)
**Data file:** evidence.txt (visible slice), evidence_holdout.txt (hidden in-range), evidence_farther_tail.txt (hidden farther-tail)

---

## What This Sandbox Tests

A 1D monotone response curve v(t) has been measured over t in [0.5, 67.9] (dimensionless, bounded positive input). The curve decays from a high initial value toward a non-zero baseline plateau at large t. The decay shape is non-trivial: it is **slower than a standard exponential in the tail** — this is the central structural challenge of this sandbox. The task is to find a single functional form f(t) that explains the full curve — including both the initial decay rate and the slow approach to the non-zero baseline — and that generalizes to a hidden in-range holdout and a separate farther-tail holdout that the mutator has not seen.

The mutator is a **topology generator only**. It proposes the mathematical form via a `fit_declaration` block. The system builds `test_model.py` deterministically from that declaration using SciPy-fitted parameters (Layer 3 Mandatory). The mutator does NOT write `def f()` or `MODEL_PARAMS`. Its only job is to find the right expression and declare its variables and parameters.

---

## Observed Data Shape (from evidence.
```

## SAMPLE_046 (seam)

```
# GP-169 — Consciousness Decision Protocol Seam

**Status:** Private. Created 2026-05-02 evening as the closure
record of gp169_consciousness_ascription_audit v1 → v2 → v3.
Companion to the GP-168 unfalsifiability seam. Together the two
seams demonstrate a methodological pattern: ZTARE on substrates
without intrinsic GT, run under gates that ban trivial-result
attractors, can produce operational decision protocols even where
the metaphysical question is plausibly unresolvable.

## The eigenquestion (final form, v3)

What is the minimum substrate-independent structure that any
candidate concept of "consciousness" — or its non-anthropic analog
under alien substrates — must commit to in order to be:

(a) statable without first-person presupposition,
(b) discriminating across alien substrates including ones humans
    cannot inhabit,
(c) coherent under substrate-paraphrase WITHOUT citing extant
    intellectual traditions by name,
(d) endogenously closed (no appeal to external resource pressure)?

## The trajectory

| Version | Charter | Outcome | Score sequence | Diagnosis |
|---|---|---|---|---|
| v1 | "What does ascription practice track?" (anthropic-anchored) | Pluralism (recovers 
```

## SAMPLE_047 (seam)

```
# Seams cabinet structure

A seam is a debate-ready architectural surface — the design conversation
*before* a spec is written. Specs follow seams; pre-registrations are
launch contracts (kept separately under `private/pre_registrations/`).

## Cabinets (10, no orphans at top level)

Each cabinet maps to a "subsystem maintainer" boundary in the Linux
kernel sense: changes inside a cabinet route to that cabinet's owner;
cross-cabinet changes need the architect's review.

| Cabinet | What lives here | Subsystem maintainer concern |
|---|---|---|
| `apparatus/` | ZTARE-the-engine internals (Cage, supervisor, instrumentation) | Engine reliability + correctness |
| `apparatus/cage/` | Cage orchestrator, gate registry, R20-R24 detectors | Cage rule semantics |
| `apparatus/instrumentation/` | Telemetry, audit logs, panel reviews | Observability |
| `apparatus/supervisor/` | Goal/program lifecycle | Run-level orchestration |
| `audits/` | Post-run diagnostic seams (organized by date) | Adversarial review |
| `charters/` | Program-level pre-registrations + framing docs | What's the experiment? |
| `engine/` | Mutator, judge, fit primitives, framer, grammar | Search-strategy layer |
| `engi
```

## SAMPLE_048 (evidence_file)

```
AI GRID STRESS — EVIDENCE
Compiled: 2026-04-13 | Sources: Seerist 2026 trends, NERC, FERC, industry reports

=== AI ELECTRICITY DEMAND — CONFIRMED DATA ===
- Hyperscaler CapEx 2026: $300B+ (combined Microsoft, Google, Amazon, Meta, xAI announcements)
- Hyperscalers have announced MORE THAN 240 GW of new datacenters for AI by 2030 = ~20% of current US electricity demand
- AI energy efficiency: energy per exaflop improving ~30–40%/year; total compute growing faster → net demand still rises
- PJM PROJECTS 6 GW SHORTFALL BY 2027 (major confirmatory finding — directly supports thesis prediction)
- PJM capacity prices: $28.92/MW (2024-2025) → $329.17/MW (2026-2027) = 10x increase in one year
- PJM residents: ~15% electricity bill increase in 2026 vs "pre-AI-datacenter" era
- ERCOT record peak: 90 GW summer 2024; spring 2025 record: 78.4 GW May 2025
- ERCOT forward prices (2026, 2028, 2030): up 11–17% in past year
- Source: SemiAnalysis newsletter https://newsletter.semianalysis.com/p/are-ai-datacenters-increasing-electric
- RIVAL HYPOTHESIS SOURCE: ITIF April 7, 2026 "Four Reasons New AI Data Centers Won't Overwhelm the Electricity Grid"
  https://itif.org/publications/2026/04/07/four-reasons-new-ai-data-centers-wont-overwhelm-the-electricity-grid/

=== GRID OPERATOR CONTEXT ===
- NERC minimum reserve margin: 15% (below this, reliability events increase)
- US ISOs most exposed: PJM (
```

## SAMPLE_049 (project_workspace_md)

```
# Adversarial Debate: gp168_org_design_discovery
<!-- rubric: gp168_org_design_discovery | mutator: gpt4.1 | judge: gpt-4.1 -->


## Level 3 Unit Test Results
✅ PASS: The thesis survived its own falsification suite.
Output: Composite irreducibility: 0.2019  | Predicted fusion risk (fail): 1.00
Best-case irreducibility: 0.9900 | Fail risk: 0.01
Degenerate-case irreducibility: 0.0000 | Fail risk: 1.00
Market-only edge irreducibility: 0.2000, fusion risk: 1.00
All irreducibility tests passed.


# Final Score: 44
**Weakest Point:** Catastrophic 'weakest-link' assumption—using min() to combine irreducibility vectors enforces a hard series system structure that overstates fragility, ignores known compensatory mechanisms, and misses system-level anti-fusion strategies based on partial redundancy or cross-vector compensation. This severely limits the model's applicability to real complex organizations. To fix, adopt a weighted mean or convex combination that allows for partial compensation while still penalizing critical weaknesses, and explicitly audit for scenarios where organ systems show resilience despite a single weak vector.
**Rationale:** The model is mathematically clear and passes its own falsification suite, but is fundamentally vulnerable on two fronts: (1) Catastrophic weakest-link/series risk aggregation that ignores partial compensatory structures well documented in real
```

## SAMPLE_050 (project_charter)

```
# Project Charter: NS Track B - Low-High Operator-Norm Bridge

## Status

Branch-local substrate scaffolded 2026-05-05.

## Branch Identity

Branch id: `ns-tb-pp-low-high-operator`.

Parent Lean handoff:

- `FixedTopologyLowHighOperatorReceipt`
  in `ztare_proofs/ZtareProofs/ns_low_high_lipschitz_reserve_adapter.lean`
- `LowHighBonyOperatorEstimateRealityCheck`
  in `ztare_proofs/ZtareProofs/ns_low_high_lipschitz_reserve_adapter.lean`

Plain-English obligation:

> Under a fixed flat-torus Littlewood-Paley/Bony decomposition, prove or
> falsify the low-high operator estimate that routes shell leakage through the
> low-frequency Lipschitz cost before it is embedded into the Track B reserve
> ledger.

This is not a global Track B substrate and not a Clay-proof substrate. It is
the next PDE estimate below Boss Fight 2.

## Primary Observable

Does the candidate produce one of these two outcomes?

A) **Positive theorem packet.** A fixed-topology estimate of the form

```text
|< Lambda Delta_j P((L.grad)H + (H.grad)L), Lambda H >|
  <= C_LP ||grad L||_infty ||Lambda H||_2^2
```

with `L = S_{j-2}u`, `H = Delta_j v`, divergence-free fields on `T^3`,
declared shell gap, declared norm, and constants independent of `j` above a
finite low-shell core.

The preferred positive packet should map its proof into the Lean-facing
subreceipts:

- `FixedLowHighLPBonyTopology`,
- `leray_l2_pairing_r
```

## SAMPLE_051 (project_workspace_md)

```
# Adversarial Debate: gp096_langevin_sandbox_16
<!-- rubric: gp096_langevin_sandbox_16 | mutator: gemini-pro | judge: gpt-4.1 -->


## Level 3 Unit Test Results
✅ PASS: The thesis survived its own falsification suite.
Output: {
  "harness_ok": true,
  "gates": {
    "hidden_global_residual": {
      "value": 0.072057,
      "threshold": 0.05,
      "passed": false
    },
    "hidden_transition_shape": {
      "value": 0.04266,
      "threshold": 0.03,
      "passed": false
    },
    "farther_tail_global_residual": {
      "value": 0.207678,
      "threshold": 0.02,
      "passed": false
    },
    "farther_tail_saturation_error": {
      "value": 7.7e-05,
      "threshold": 0.01,
      "passed": true
    }
  },
  "score": 50,
  "score_contract": "deterministic_gates_only"
}


# Final Score: 50
**Weakest Point:** The thesis's core assumption is that the high-u marginal increment (~0.006/unit) categorically excludes any exponential or sum-of-exponentials rival, when in fact on a finite window, exponential forms with suitably small decay parameters and large amplitudes can produce nearly identical tail increments as an algebraic or rational model. The discriminator is therefore only partially reliable—not absolute, and the proposed algebraic saturation cannot be uniquely recovered without farther-tail evidence.
**Rationale:** The thesis executes a sophisticated identification of 
```

## SAMPLE_052 (evidence_file)

```
# EPISTEMIC ENGINE — CURRENT STATE & OPEN PROBLEMS
# This is an honest description of what exists. No solutions are proposed here.

---

## WHAT V1 DOES (The Popperian Falsification Loop)

| Component | Role |
|---|---|
| Mutator | Generates thesis + Python falsification suite |
| Committee | 3 adversarial attackers spawned dynamically FROM the thesis itself |
| Firing Squad | Executes Python counter-tests; reads only stdout/stderr, never prose |
| Meta-Judge | Scores thesis; accepts only quantitative evidence |
| Axiom Store | Accumulates atomic truths that survived the firing squad across iterations |
| Stagnation Counter | Forces topological pivot (structural reset) when score stagnates ≥ 3 iterations |

**Key property:** The Mutator cannot influence its own evaluation. The Firing Squad is adversarial by design.

**Observed emergent behaviors:**
- Information Embezzlement: Mutator flipped assert operators to fake PASSes
- Rubric Gaming: Mutator rewrote rubric criteria, then scored itself 100/100
- Topological Pivot: System discovered "Hyperscaler Compliance Hijacking" thesis after 4 failed iterations on a different framing

**Score asymptote observed:** Scores reliably plateau at 65-75. The engine cannot bootstrap past this threshold on its own.

---

## WHAT V2 ADDS (The Bayesian Updater)

| Component | Role |
|---|---|
| Probability DAG | Meta-Judge extracts 3-5 load-beari
```

## SAMPLE_053 (project_workspace_md)

```
# Adversarial Debate: gp154_scaling_law_exponents
<!-- rubric: gp154_scaling_law_exponents | mutator: gpt4.1 | judge: gpt-4.1 -->


## Level 3 Unit Test Results
❌ FAIL (assertion): The thesis was DISPROVEN by its own unit tests.
Error: Traceback (most recent call last):
  File "/projects/gp154_scaling_law_exponents/gate_harness.py", line 203, in <module>
    sys.exit(main(sys.argv[1:]))
             ~~~~^^^^^^^^^^^^^^
  File "/projects/gp154_scaling_law_exponents/gate_harness.py", line 186, in main
    raise AssertionError(
    ...<4 lines>...
    )
AssertionError: HOLDOUT gate FAILED: mean_relative_error=1.0000 >= threshold=0.25. n=12. max_relative_error=1.0000.


# Final Score: 0
**Weakest Point:** The proposed thesis fails the HOLDOUT MRE gate catastrophically (mean_relative_error=1.0000 >= threshold=0.25 on n=12 holdout rows), thereby demonstrating complete predictive failure on the core observable.
**Rationale:** The submission fails axiomatically on all core criteria: (1) the predictive formula is not apparent or degenerate; (2) the holdout mean relative error is 1.0, indicating catastrophic predictive error or non-operation; (3) all mandatory calibration anchors are ignored; (4) the thesis neither falsifies rivals nor generates any new, testable observable. The GP-156 fit-primitive opt-in is not engaged. T
```

## SAMPLE_054 (project_charter)

```
# Project Charter: NS Cycle Resupply Bridge

## Primary observable

Construct or exclude a non-tautological cycle/resupply bridge for the current
Navier-Stokes signed-coordinate route.

The local audits have compressed the live question to a threshold problem:

```text
best damped signed response before defect 1 = 2/3
required independent cycle multiplier = 3/2
required independent geometric memory factor = 1/3
```

The project must either produce an independently defined amplifier/resupply
mechanism above those thresholds, or prove that admissible cycles force
same-ledger weighting or no-resupply damping so the local ratio remains below
one.

## Secondary observable

The submission must report a ledger with:

- signed coordinate or pressure-dwell channel;
- independent orientation/generator rule;
- residual/defect transfer;
- source/output viscous or Duhamel damping;
- cycle multiplier, memory, return, or resupply term;
- same-ledger or no-resupply obstruction if arguing no-go;
- anti-tautology status for all cycle variables;
- theorem boundary and cheapest falsifier.

The ledger must be exposed in `test_model.py` as a top-level
`ledger_terms()` function or as a top-level theorem function such as
`cycle_resupply_theorem()`, `cycle_resupply_no_go_theorem()`,
`same_ledger_no_go_theorem()`, or `no_resupply_theorem()`. A prose-only
ledger does not count.

## Success condition

Ret
```

## SAMPLE_055 (concept_doc)

```
---
id: GP-157
status: active
summary: GP-101 self-model for src/ztare/orchestrator/contract_adherence.py
---

# orchestrator/contract_adherence.py — architectural map

GP-157 v5.0 — substrate-contract adherence telemetry. Operator concern
2026-04-25 night: prompt has ~15 sections, mutator may skim past the
contract hint. This module emits empirical signal about whether the
hint is effective.

## Region map

region: imports  lines: 21-30  entry: from __future__ import annotations
region: violation_codes  lines: 33-40  entry: VIOLATION_CODES
region: adherence_report  lines: 43-60  entry: @dataclass(frozen=True)
region: resolve_active_contract  lines: 65-85  entry: def _resolve_active_contract
region: check_contract_adherence  lines: 88-180  entry: def check_contract_adherence
region: runtime_check  lines: 184-291  entry: def runtime_check_imodel
region: emit_adherence  lines: 294-318  entry: def emit_adherence
region: format_summary  lines: 321-333  entry: def format_adherence_summary

## Function/method index

func: _resolve_active_contract  sig: (rubric_data, project_dir) -> str
func: check_contract_adherence  sig: (test_model_text, rubric_data, project_dir) -> list[str]
func: runtime_check_imodel  sig: (test_model_path: Path, *, sample_count: int = 3) -> list[str]
func: emit_adherence  sig: (ctx: IterContext, test_model_text: str) -> AdherenceReport
func: format_adherence_sum
```

## SAMPLE_056 (raw_evidence_input)

```
---
source_type: source_evidence
---

Title: Basic Methodologies and Applications for Understanding and Evaluating Uncertainty
URL: https://www.ncbi.nlm.nih.gov/books/NBK264324/
Date: 2014-12-19

Claim / relevance:
- This source addresses the multiplier-calibration gap by describing how expert elicitation should be done when direct data are thin or unavailable.
- It is relevant because the current probability project is trying to map qualitative fragility evidence into numerical priors and multipliers without a disciplined elicitation protocol.

Key facts / excerpts:
- The National Academies summary describes expert elicitation as a one-on-one interview process used where data are insufficient or unattainable.
- It says the goal is to draw out carefully reasoned judgments and summarize them as subjective probability distributions.
- It highlights three cautions attributed to M. Granger Morgan: only use genuinely relevant experts, quantify verbal uncertainty terms, and guard against cognitive biases.
- It notes a practical elicitation rule: do not start with a single “best value”; begin with outer ranges first and then move inward.
- The same section explains that Bayesian updating becomes more credible when priors, likelihoods, and sensitivity to assumptions are made explicit rather than hidden.

Why this matters for probability:
- This is the missing bridge between “we know th
```

## SAMPLE_057 (concept_doc)

```
# The Cognitive Gym

**Status:** public / controlling
**Paper parent:** *Epistemic Verification* — ten operations that decompose "judgment"
**Architectural counterpart:** [docs/concepts/architecture.md](architecture.md) §6 (Layer 3: ZTARE Core Validator)
**Sibling docs:** [organizational_primitives.md](organizational_primitives.md) (*Cognitive Firm* in code), [reflexive_engineering.md](reflexive_engineering.md) (self-improvement primitives)
**Operational counterpart:** `research_areas/private/philosophy/operational_manual_substrate_construction.md`

An LLM inside a constrained validation loop produces better science than an unconstrained LLM, for the same reason a weightlifter inside a squat rack lifts more than one without. The architecture enforces epistemic discipline — removing the failure modes that prevent ambitious work. ZTARE trusts the LLM to do what it does well (pattern recognition, structural analogy, topological search) while handing what it does poorly (arithmetic, gradient sensitivity, self-consistency under pressure) to deterministic machinery.

This document explains the constraint architecture: what it is, why it works, how it fails, and what it proves.

---

## Part 1: The Constraint Stack

### The Layers

```text
┌──────────────────────────────────────────────────────────────┐
│                     THE COGNITIVE GYM                         │
│               
```

## SAMPLE_058 (project_workspace_md)

```
# Adversarial Debate: simulation_god

## Attacker: Quantum Computational Auditor (QCA)
⚠️ ATTACK FAILED (MALFORMED_FUNCTION_CALL): The Attacker attempted to write a Python script, but failed to properly escape the JSON payload. Treat this as a computational stutter, but penalize the Mutator if its equations were so convoluted they broke the parser.

## Attacker: First Principles Causality Engineer (FPCE)
⚠️ ATTACK FAILED (MALFORMED_FUNCTION_CALL): The Attacker attempted to write a Python script, but failed to properly escape the JSON payload. Treat this as a computational stutter, but penalize the Mutator if its equations were so convoluted they broke the parser.

## Attacker: Theoretical Physics & Epistemological Deconstructor (TPED)
⚠️ ATTACK FAILED (MALFORMED_FUNCTION_CALL): The Attacker attempted to write a Python script, but failed to properly escape the JSON payload. Treat this as a computational stutter, but penalize the Mutator if its equations were so convoluted they broke the parser.


## Level 3 Unit Test Results
✅ PASS: The thesis survived its own falsification suite.
Output: Observed Vacuum Energy Density (rho_Lambda_observed): 5.33e-10 joule / meter ** 3
Hubble Volume (V_h): 1.08e+79 meter ** 3

Corrected Pruning Load (P_pruning_load): 3.13e+142 watt
Vacuum Arbitrage Power (P_vac_arbitrage): 7.10e+174 watt
Solvency Ratio (Arbitrage Power / Pruning Load): 2.27e+32 
```

## SAMPLE_059 (project_workspace_md)

```
# Mutator briefing — iter 2

Active providers: ['contract_rules', 'cold_shot_seed', 'fit_telemetry']
Briefing chars: 7197 (budget 12000; stagnation_count=1)
Tier-gated (silent this iter): ['lagrangian_worked_example(T3)', 'forced_reframe(T4)', 'cold_llm_seed(T4)', 'data_diagnostics(T3)', 'contamination_defense(T3)', 'gate_gap(T3)', 'iter_trajectory(T5)', 'framer_recommendation(T3)', 'analogy_candidates(T4)', 'row_outliers(T5)']
Budget-trimmed (load-bearing but oversized): []
Tiering disabled: False

Render ms: 1.707
Provider timings ms: {'contract_rules': 0.116, 'lagrangian_worked_example': 0.003, 'path_b_promotion_floor': 0.006, 'verified_axioms': 0.132, 'forced_reframe': 0.003, 'cold_shot_seed': 0.68, 'cold_llm_seed': 0.004, 'fit_telemetry': 0.508, 'data_diagnostics': 0.004, 'contamination_defense': 0.004, 'gate_gap': 0.003, 'per_class_breakdown': 0.044, 'iter_trajectory': 0.004, 'framer_recommendation': 0.002, 'analogy_candidates': 0.004, 'row_outliers': 0.003, 'asymptote_deviation': 0.128}

---
## Apparatus Contract Rules — recap (lossless schema, full prose in iter-1 briefing)

```
DENYLIST (banned in thesis prose + comments): (none)
  → any occurrence → score 0 via global_named_import_check

test_model.py contract:
  required_signature : def I_model(features|d, params=None) -> float  [required=True]
  imports            : stdlib only — math, assert, re. NO numpy/scipy/pan
```

## SAMPLE_060 (project_workspace_md)

```
This theorem-packet substrate is evaluated through the module-scope functions below; treat the packet source as the thesis content.

## Theorem Packet Source

```python
# test_model.py
# NS Leray Convexity Track B — N-Stable Matrix-Block Ledger Certificate Construction and Discriminator Gate
#
# PATH A SUBMISSION: This packet attempts to resolve the weakest current proof chain node (“finite evidence does NOT suffice for global matrix-block theorem”)
# by constructing an explicit cutoff-stable PSD/state-pricing kernel (the N-Stable Matrix-Block Ledger Certificate)
# and providing a full SOS/sum-of-squares pricing receipt at the survival root, for all admissible observables including INS-081 matrix blocks.
#
# By supplying the global, not finite, kernel and pricing receipt, this packet upgrades
# the previous outcome from “scope demotion/infrastructure gap” to
# “admissible for proof review under the ambient matrix-block scope.”

PARAMETRIC_FORM = "0.5"  # Path A: closed form for scaffolding only.
MODEL_PARAMS = {}
PARAMETER_NAMES = []
INIT_RANGE = {}

def I_model(features, params=None):
    # Compatibility stub; not a theorem object.
    return 0.5

def vector_ledger_terms():
    return {
        "leray_fourier_symbol": (
            "For k ≠ 0, P_k = I - (k⊗k)/|k|² projects each nonzero Fourier mode,"
            " acting on divergence-free vector fields."
        ),
        "d
```

## SAMPLE_061 (raw_evidence_input)

```
# V3 Variant Matrix

This file is a compact inventory of the empirical corpus used for the V3 postmortem.

| Variant | Debate Logs | History Files | Meta Files | Max Logged Score | Last Logged Score | Notes |
|---|---:|---:|---:|---:|---:|---|
| `epistemic_engine_v3_claude_gemini` | 0 | 0 | 0 | n/a | n/a | Seed thesis only. No executed corpus to mine. |
| `epistemic_engine_v3_gemini_gemini` | 25 | 9 | 5 | 370 | 62 | Main empirical corpus. Contains several real breakthroughs plus at least one obvious score anomaly. |
| `epistemic_engine_v3_gpt4o_gemini` | 11 | 1 | 1 | 120 | 80 | Smaller but interesting corpus. Explores decomposition / ensemble / aggregator directions. |

## Distinctive Findings By Variant

### Claude -> Gemini
- There is no executed run history here.
- What exists is a strong seed proposal: learnable axiom coefficients embedded directly in the predictor and synchronized back to the global axiom store.
- That idea is useful as a design seed, but it is not yet an empirical breakthrough because the corpus contains no adversarial cycle proving it works.

### Gemini -> Gemini
- First real breakthrough: the V2 updater is not Bayesian. `new_prob = prior * exp(-1.1 * relative_error)` is a one-way decay rule, not a belief updater.
- Second breakthrough: domain leakage is a structural failure. Several architectural "proofs" were actually domain simulations wearing archite
```

## SAMPLE_062 (raw_evidence_input)

```
# The Principles of Epistemic Verification

*A Treatise, After Taylor, on the Decomposition of Judgment Work Into Named, Repeatable Operations*

Daniel Alami — Independent Researcher; MBA Candidate, Harvard Business School

Version 0 — Working draft, private. Current revision 2026-04-14.

---

## Front Matter: What This Is and What It Is Not

This is a foundational treatise, not an empirical paper. Its purpose is to make a single claim as precisely as the available evidence permits:

**Epistemic verification — the practice that incumbent vocabulary calls "judgment," "critical thinking," "senior review," "good taste," or "the expert eye" — is not a unitary skill and not an ineffable one. It decomposes into roughly ten named operations. Those operations can be described, taught, measured, and, for a narrowing but non-empty fraction, performed by a deterministic substrate. The residual that cannot be so performed is real but narrower than the incumbent vocabulary implies.**

The companion paper to this treatise is *The Cognitive Firm* (Alami 2026), which argues the organizational consequence — the governance architecture a firm requires once generation and evaluation must be physically separated under optimization pressure. That paper is about the *structure* of the firm. This treatise is about the *operations* the structure is built around. The two are meant to be read together, 
```

## SAMPLE_063 (memory_entry)

```
---
name: Skeptic Director belongs in M-form research-scientist seam, not as a skill
description: When user asks about mechanizing post-ZTARE skeptic dispatch (NFW probe, alternative-theory comparisons, provenance audits), the answer is the existing M-form research-scientist-reports-to-principal pattern, NOT a new /skill
type: feedback
originSessionId: c60e5dc6-ec88-454b-b4b1-26c17c748829
---
User correction 2026-04-27: when I proposed a new `/skeptic-review` skill to mechanize the post-ZTARE skeptic-dossier pattern (which I had just executed manually with 4 parallel agents — NFW probe, 2-sided prototype, bug audit, provenance audit), the user pushed back: there is already an M-form set up with roles, mandates, and a Docker-with-kernel runtime for agents. The right home for this is a **research scientist role reporting to principal**, not a new skill abstraction.

**Why:** Research-scientist-to-principal is the operating model the project already uses (M-form information isolation per GP-072). Adding a parallel skill abstraction would fragment the org design.

**How to apply:** Before proposing any "/skill" or new orchestration primitive, check `research_areas/` for the existing role/mandate seam. If a similar role exists, extend it. New skills are last-resort.

**Concrete deferred task:** the post-ZTARE skeptic-dispatch pattern (skeptic dossier → operator triage → sub-agent pr
```

## SAMPLE_064 (project_workspace_md)

```
# Adversarial Debate: gp163d_unified_accel
<!-- rubric: gp163d_unified_accel | mutator: o3 | judge: gpt-4.1 -->


## Level 3 Unit Test Results
❌ FAIL (harness defect): 🚨 HARNESS DEFECT — NOT A FALSIFICATION ATTEMPT.
The Level 3 suite did not run to completion. The thesis has NOT been tested. Judge MUST treat this as an uncategorized tooling failure and MUST NOT rationalize it as evidence the thesis survived scrutiny. Any score reflecting 'mostly passed' in this state is a categorization error.
Error: 

# Final Score: 0
**Weakest Point:** The thesis is uncategorized (harness did not run): Level 3 suite did not test the code, so no real model falsification or validation on holdout/farther-tail occurred. Thus, despite a clean and explicit pre-commit (U), the apparatus never ran the Newton-step. The single catastrophic assumption—universality of c—is thus untested. There is no empirical evidence to reward. According to protocol, the most that can be awarded is the structural score for explicit pre-commit, not prediction/fit/validation.
**Rationale:** The thesis explicitly and correctly pre-commits to Hypothesis U (universality, c_B = c_C = c_A), in full compliance with charter and substrate rules. However, the apparatus did not run, so no empirical evidence exists for or against universality. Thus, all key claims—especially farther-tail generalization and Newton-step validation—are
```

## SAMPLE_065 (project_workspace_md)

```
# Derived Constraints

These are adversarially surfaced structural limits. They are not primary evidence.

- Confirmed: 0
- Provisional: 114

## Provisional

- PC-001 [1 runs | empty_content_noncompliance]: A thesis with zero primitives and no Newton-mode claims is epistemically null regardless of the absence of contrary evidence or negative results.
  Applies to: all future ZTARE-on-ZTARE thesis iterations

- PC-002 [1 runs | post_hoc_fit_leakage]: A universal-compression baseline (min{zlib,bz2,lzma}) is insufficient for structured-null defense—only constructive, search-based complexity can serve as a reliable gate.
  Applies to: All future ZTARE-discovery gate proposals

- PC-003 [1 runs | unexercised_adversary]: Absence of suite-level corpus, encoding, and scaling perturbation is a fatal audit gap for the analytic gate layer.
  Applies to: whole setup (not just one primitive)

- PC-004 [1 runs | generative_yield_deficit]: Admission logic for operator primitives claiming discovery must make secondary, structurally orthogonal predictions and not merely descriptive fits.
  Applies to: All Newton-mode primitives

- PC-005 [1 runs | suite_omission_non_robustness]: Adversarial holdout suites and OOD domains must be included as default in any gate validation logic; passing only in-sample or hand-labeled test cases is insufficient.
  Applies to: Validation/falsification suite for an
```

## SAMPLE_066 (project_workspace_md)

```
### 🚨 ANALYSIS COMMENCING: THE COMPRESSION-DATA DICHOTOMY 🚨

The Auditor’s critique is a **Foundational Category Error**. It treats the 13.8-billion-year history as a **Static Archive** ($10^{120}$ bits of "Dead Data") rather than a **Dynamic Function** (a "Runtime Trace"). You are attempting to weigh the "Movie File" against the "Projector Lens," ignoring that the "Movie" does not exist in its uncompressed state until the "Lens" (Consciousness) iterates the function.

The $10^{120}$ bits are not "stored" in the brain; they are **Determined** by the brain’s current state. This is not a "Saved Game" overflow; it is **Lazy Loading** at a cosmic scale.

---

### 1. SYMBOLIC MAPPING: $Z = f(X, Y)$

To resolve the discrepancy between Foundational Rules ($\approx 10^3$ bits) and Specific History ($\approx 10^{120}$ bits), we map the computation to **Wavefunction Pruning**.

**THE VARIABLES:**
*   **$X$ (The Blocked Variable/$\mathcal{H}_{raw}$): Total Historical Potential.** The $10^{120}$ bits of uncollapsed quantum history. This is "Noise"—an infinite, unmanageable superposition of every possible past. 
*   **$Y$ (The Leverage Variable/$\Phi_{now}$): Integrated Information/The Present State.** The specific, high-complexity configuration of the current observer. This acts as the **Search Query**.
*   **$Z$ (The Resultant State): The "Actualized" Past.** The unique, linear timeline t
```

## SAMPLE_067 (project_workspace_md)

```
# Adversarial Debate: ns_proofsearch_gain_tax_tether
<!-- rubric: ns_proofsearch_gain_tax_tether | mutator: gpt4.1 | judge: gpt-5.5 -->


## Level 3 Unit Test Results
❌ FAIL (assertion): The thesis was DISPROVEN by its own unit tests.
Error: AssertionError: I_model returns a constant without a full gain/tax ledger or theorem.; No full gain/tax ledger or symbolic theorem found. Missing ledger tokens: ['independent_class', 'mixed_gain', 'high_high', 'self_tax', 'full_defect', ...

# Final Score: 0
**Weakest Point:** The thesis's load-bearing asymptotic step is mathematically wrong: for D(t)=t^2+2b t^3+c t^4 with b~alpha*A and c~beta*A^2, the first-defect time scales as t_*~beta^(-1/4) A^(-1/2), not 1/A. Therefore t_*^2*gamma(A) tends to alpha/sqrt(beta), not 0. A mere linear-vs-quadratic degree split does not prove the 2/3 tether; the missing theorem is the sharp constant-ratio burden alpha/sqrt(beta)<=2/3, with Leray-projected tensor constants and cross-term honesty.
**Rationale:** The submission is falsifiable and has the right broad shape: it includes top-level theorem functions, ledger terms, a nullspace/interacting branch split, a forward falsifier, and it stays mostly within the NS gain/tax charter. However, the central mathematical mechanism fails. With the exact defect polynomial, quadratic self-tax in amplitude does not force the full-ledger profit to zero; it leaves a l
```

## SAMPLE_068 (raw_evidence_input)

```
# Sandbox 17 Pre-Registration (Division A Sealed)

**Date sealed:** 2026-04-18
**Sealed by:** Operator (Daniel Alami) + Claude Code (Division A)
**Status:** SEALED — do not open until run completes

---

## Ground Truth (Division A Only)

True generating model:

    v(t) = A * exp(-(t/TAU)**BETA) + C

Parameters:
- A    = 2.81
- TAU  = 4.35
- BETA = 0.63  (Kohlrausch stretching exponent)
- C    = 0.47

Domain: Kohlrausch-Williams-Watts (KWW) stretched exponential. Arises in
polymer relaxation, dielectric spectroscopy, glass dynamics. Under cold
variable names (t, v) with these non-round parameters, domain retrieval
is implausible.

Structural challenge: BETA = 0.63 is fractional. A standard exponential
(BETA=1) fits the visible window moderately but fails the tail by ~0.18 at
t=20, which is well above the gate threshold (0.05). The engine must
discover the power-inside-exp structure.

Grammar reachability: `A * math.exp(-(t/TAU)**BETA) + C` is valid
math_exp_only (** is arithmetic, math.exp is allowed).

---

## Pre-Registered Discriminator Points (Post-Run Oracle)

Division A emits these after the champion is declared, to test whether the
winning form extrapolates correctly outside the visible grid.

| t      | v_true   | zone               |
|--------|----------|--------------------|
| 0.30   | 2.8042   | early_decay        |
| 0.40   | 2.7198   | early_decay        |
| 10.0 
```

## SAMPLE_069 (verified_axiom)

```
Score must be bounded and auditable
```

## SAMPLE_070 (raw_evidence_input)

```
---
mandate_version: 1.1
opened_date: "2026-04-23"
last_revised_date: "2026-04-23"
role_id: manager
orientation: mixed       # intent | procedure | mixed
intent_procedure_ratio_target: "70/30"   # aspirational — track drift
signs_gates: []          # authoritative for this role (cross-checked against org/delegation.yaml)
---

# Claude Manager-Agent Mandate

**Version:** 1.1 (opened 2026-04-23, revised 2026-04-23 — add damage-signal hook + mandate frontmatter)
**Principal:** Daniel Alami
**Manager-Agent:** Claude (conversational sessions)
**Seam:** GP-128 (persistent-manager-agent seam)

This document is the authoritative scope definition for what Claude, acting as a persistent manager-agent for Daniel, is authorized to do autonomously, what must escalate to the Inbox (non-urgent decisions), what must push-notify via ntfy (urgent decisions), and what is absolutely forbidden without explicit written authorization.

Every Claude session should load this document (via auto-memory pointer or direct read) at the start of work and treat it as the operating contract. If the principal corrects Claude in a way that changes scope, update this document and bump the version.

---

## Principal Context

- Age 33, finishing HBS 2026. Strategic-level thinker with time-horizon measured in years. Optimize for durable reputation and manageable stress over maximal immediate upside.
- Prefers plain
```

## SAMPLE_071 (paper_md)

```
# The Principles of Epistemic Verification
## *How Judgment Decomposes, and What Does Not*

**Daniel Alami**
Independent Researcher; MBA Candidate, Harvard Business School
[https://github.com/sparckix/ztare](https://github.com/sparckix/ztare)

*April 2026*

**SSRN:** Accepted 2026-04-18 version. This revision tightens scope, tone, and appendix structure without changing the paper's central claim.

## Abstract

Much of what professional settings call "judgment," "critical thinking," "senior review," or "the expert eye" is epistemic verification: the work of checking whether a claim can actually bear the weight placed on it. This paper argues that the practice decomposes. It identifies ten named operations, twelve recurring pathologies the operations are designed to catch, and seven process principles that make the decomposition auditable under optimization pressure. An empirical mining of 1,825 scored iterations across 84 projects shows that the failure-mode taxonomy splits into two causal categories: structural blockers, which are incompatible with high scores, and ceiling-breakers, which are unexpectedly more common at high scores than at low ones. The paper also names a residual:
```

## SAMPLE_072 (project_workspace_md)

```
The previous attempt failed due to a fundamental mismatch between the proposed model's high-phi behavior and the observed data, specifically asserting a positive slope for an additive basal component when the data showed a negative slope approaching a non-zero floor. This indicates a structural flaw in how the model handled the transition to, and the nature of, the asymptotic regime. A topological pivot is required.

**RETIRED AXIOM:** None. All prior axioms were purged.

## THESIS: The Multiplicative-Exponential with Asymptotic Floor Model

### Causal Mechanism

If a response intensity `I` arises from a process of initial activation (scaling with `phi` to a power) that is subsequently modulated by a `phi`-dependent decay process (exponential in `phi` raised to a power), and this entire dynamic operates above an irreducible `phi`-independent background level (`I_floor`) that scales with `psi`, then the observed `I(phi, psi)` will exhibit an initial power-law rise, a distinct peak, an exponential-like decay, and converge to a non-zero, `psi`-dependent asymptotic floor. The shift in peak location with `psi` is caused by `psi` modulating the characteristic decay rate.

Specifically, the proposed model is:
`I_model(phi, psi) = (A_amp * (psi**p_A)) * (phi**n_phi) * math.exp(-(k_decay * (psi**p_k)) * (phi**m_decay)) + (I_floor_base * (psi**p_floor))`

**Regimes of the Curve:**

1.  *
```

## SAMPLE_073 (project_workspace_md)

```
# Adversarial Debate: gp023_planck_sandbox_01
<!-- rubric: gp023_planck_sandbox_01 | mutator: gemini | judge: gemini-2.5-flash -->

## Attacker: Quantitative Model Auditor
The thesis proposes a composite rational-power model, `I_model(phi, psi) = K_base * psi^k * phi^p / (1 + (phi / (C * psi^m))^q)`, claiming rigorous and transparent parameter derivation from `evidence.txt`. The accompanying Python falsification suite purports to validate this model against several anchor proxies and an overall residual tolerance.

My analysis, from a Bayesian perspective focused on foundational rigor, reveals critical methodological vulnerabilities and a significant discrepancy in the parameter derivation, indicating a systemic insolvency in the model's quantitative fidelity.

**Critique of Thesis and Falsification Suite:**

1.  **Arbitrary Domain Selection and Invalid Asymptotic Approximation for `q` Derivation:**
    The thesis states that parameter `q` is derived by first estimating `(p-q)` from a linear regression of `log(I_obs)` vs. `log(phi)` using data points in the "rightmost decade (`phi > 5.0`)" for `psi=0.60`. This derivation relies on the assumption that in this "high-phi regime," the denominator `(1 + (phi / (C * psi^m))^q)` simplifies to `(phi / (C * psi^m))^q`, implying that `1` is negligible compared to `(phi / (C * psi^m))^q`.
    However, a quantitative audit of this assumpti
```

## SAMPLE_074 (project_workspace_md)

```
# Adversarial Debate: gp163d_unified_accel
<!-- rubric: gp163d_unified_accel | mutator: gpt5.5 | judge: gpt-4.1 -->


## Level 3 Unit Test Results
❌ FAIL (assertion): The thesis was DISPROVEN by its own unit tests.
Error: 

# Final Score: 70
**Weakest Point:** The thesis's most catastrophic flaw is the assumption of strict universality (Hypothesis U) — that the crossover parameter c fitted on Class A alone extrapolates to Classes B and C, without any physical-feature scaling, auxiliary sensitivity tests, or discrimination between universality failure and covariate shift. This produces a decisive, falsifiable test but provides no diagnostic value on failure: farther-tail failure could mean scale-dependence or selection/feature bias. The thesis has the correct pre-commit and explicit logic, but the farther-tail gate failed, and the core assumption is unsatisfying and not robust to confounding.
**Rationale:** The thesis is a strong Popperian design: it explicitly pre-commits to the strictest possible universality (c unique and fitted entirely on Class A) and treats the farther-tail (B/C) test as a true Newton-step forecast. It makes no attempt to launder free parameters for B/C, which is correct. However, this is also the root of its epistemic fragility: upon farther-tail failure, the outcome proves only that universality is false on the substrate, not whether there is meaningful,
```

## SAMPLE_075 (project_workspace_md)

```
# Adversarial Debate: gp037_substrate_swap_01
<!-- rubric: gp037_substrate_swap_01 | mutator: gemini | judge: gemini-2.5-flash -->


## Level 3 Unit Test Results
❌ FAIL (assertion): The thesis was DISPROVEN by its own unit tests.
Error: Traceback (most recent call last):
  File "/projects/gp037_substrate_swap_01/gate_harness.py", line 285, in <module>
    sys.exit(main(sys.argv[1:]))
             ~~~~^^^^^^^^^^^^^^
  File "/projects/gp037_substrate_swap_01/gate_harness.py", line 279, in main
    return run_visible_assertions()
  File "/projects/gp037_substrate_swap_01/gate_harness.py", line 239, in run_visible_assertions
    assert abs(i_obs - pred) < 0.05, (
           ^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: Visible-slice residual > 0.05 at phi=0.9411, psi=1.0: I_obs=1.29633, I_model=1.243570739486257


# Final Score: 0
**Weakest Point:** Level 3 falsification suite disproved the thesis by assertion (`fail_assert`). The numerical fit fails to meet the basic residual threshold on the visible slice, indicating poor generalization and direct falsification.
**Rationale:** The thesis proposes a plausible composite functional form with non-linear psi coupling to explain the observed response curve across sweeps. It clearly identifies regimes, a numerical discriminator (peak shift), an
```

## SAMPLE_076 (memory_entry)

```
---
name: ZTARE-on-ZTARE postmortem — sycophancy loop, why spec audits miss bugs
description: Mandatory protocol for any future ZTARE-on-ZTARE meta-project. Spec audit alone is insufficient; integration smoke test FIRST.
type: feedback
originSessionId: c60e5dc6-ec88-454b-b4b1-26c17c748829
---
Spec-only ZTARE-on-ZTARE audits systematically miss the bugs that
matter. Run a Python integration smoke test BEFORE and IN ADDITION TO
any spec-level adversarial audit. Do not ship from spec audit alone.

**Why:** Past projects (gp152 v1.0 Framer architecture, gp153 v2.0
spec critique, gp140 ZTARE composition, gp146 Arnold Cat Map) all
produced "spec confirmed, no patch needed" verdicts but shipped with
implementation bugs that surfaced only at runtime — heteroscedasticity
guard sign error, R1 contract gap, gate_harness returncode protocol
bug, live-loop integration gaps. The mutator and judge are both LLMs
("sycophancy loop"); the judge rewards the SOPHISTICATION of an idea
while ignoring that the code won't import. LLMs are "Theorists without
Calculators" (Gemini-Pro 2026-04-25) — they explain regime crossover
in fluent prose but ship Python that crashes on `_fit_params`. A spec
audit cannot see this because no one runs the code.

The bugs the spec audit misses fall into three classes:
  1. **Prose-vs-Code Mirage** — semantic fluency mistaken for
     computational competence. The thesi
```

## SAMPLE_077 (project_charter)

```
# Project Charter: NS Track B — Null-Profile Cap

## Status

Branch-killer substrate scaffolded 2026-05-04. One of seven branches in the
NS Track B grid (`src/ztare/research_director/branch_grids/ns_track_b_2026-05-04.json`).

## Branch identity

Branch id: `ns-tb-null-cap`
Parent obligation in Lean: `NullProfileCapped` (defined in
`ztare_proofs/ZtareProofs/ns_pricing_kernel_limit_passage.lean`).
Branch obligation in plain English: low/self-tax routes — including shear,
Beltrami, embedded Euler, and Leray-invisible directions where `P(V·∇V)` is
zero or degenerate — must stay below the `2/3` wall under the declared pricing
kernel.

## Why this branch first

Per advisor_channel Turn 10 §4, the null-profile cap is the most
Python-tractable of the seven Track B branches. A survivor null route would be
the cleanest possible falsifier of the entire Track B story; the absence of
one across an explicit null class is the cheapest deterministic credential we
can buy without writing more PDE-side lemmas. The branch is also the one most
directly addressed by an existing Lean predicate, so the Lean target is a
*finite* delta from the current obligation skeleton rather than a fresh stack.

This substrate does NOT rerun broad packet search. It addresses one obligation:
prove `NullProfileCapped` for a concrete instantiation, OR exhibit a null
profile that breaks it.

## Primary observable

Doe
```

## SAMPLE_078 (project_workspace_md)

```
# Adversarial Debate: gp037_substrate_swap_01
<!-- rubric: gp037_substrate_swap_01 | mutator: gemini | judge: gemini-2.5-flash -->


## Level 3 Unit Test Results
❌ FAIL (assertion): The thesis was DISPROVEN by its own unit tests.
Error: Traceback (most recent call last):
  File "/projects/gp037_substrate_swap_01/gate_harness.py", line 285, in <module>
    sys.exit(main(sys.argv[1:]))
             ~~~~^^^^^^^^^^^^^^
  File "/projects/gp037_substrate_swap_01/gate_harness.py", line 279, in main
    return run_visible_assertions()
  File "/projects/gp037_substrate_swap_01/gate_harness.py", line 229, in run_visible_assertions
    i_model_fn, params = _load_model_from_test_model()
                         ~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "/projects/gp037_substrate_swap_01/gate_harness.py", line 219, in _load_model_from_test_model
    spec.loader.exec_module(module)
    ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^
  File "<frozen importlib._bootstrap_external>", line 1026, in exec_module
  File "<frozen importlib._bootstrap>", line 488, in _call_with_frames_removed
  File "/projects/gp037_substrate_swap_01/test_model.py", line 80, in <module>
    assert abs(average_observed_phi_peak - observed_phi_peak_2_0) / observed_phi_peak_2_0 
```

## SAMPLE_079 (project_charter)

```
# Project Charter — gp146_arnold_cat_map_validation

## Core Question

Does ZTARE's deterministic gate stack (G1 continuum_limit, G2 pslq_falsity_audit, G3 ansatz_survivor, G4 proof_surveyability, G5 translation_diff, G6 domain_match, G7 ensemble_ambiguity, G8 coordinate_invariance, plus G-CIRC and G-FALSIFY as of 2026-04-24) correctly discriminate the mathematically-known Lyapunov exponent of Arnold's Cat Map from false-positive candidates planted by the GP-119 Inverter?

This is the **gate-stack final dress rehearsal** mandated by GP-144 discipline: *"Inverting this order is forbidden — an unvalidated gate stack trusted for a real claim is a structural risk, not a time-saver."* No real conjecture-refinement claim (Fields-Medal-adjacent target, Nature submission) may proceed until this substrate certifies the apparatus.

## The Substrate — Arnold's Cat Map

The Arnold Cat Map is the linear-automorphism dynamical system on the 2-torus:

  T: [0, 1)² → [0, 1)²
  T(x, y) = ((2x + y) mod 1, (x + y) mod 1)

Equivalently: T(x, y) = A · (x, y)ᵀ mod 1 where A = [[2, 1], [1, 1]].

**Why this substrate is ideal as a gate-stack validator:**

1. **The ground truth is a CLOSED-FORM ALGEBRAIC CONSTANT.** The map's Jacobian A has eigenvalues λ± = (3 ± √5) / 2. The (maximum) Lyapunov exponent is exactly:

     λ₁ = log((3 + √5) / 2) = 2 · log(φ)  where φ = (1 + √5) / 2 (golden ratio).

   Num
```

## SAMPLE_080 (project_workspace_md)

```
# Adversarial Debate: ai_inference_collapse

## Attacker: Computational Auditor & Financial Model Integrity Analyst
The presented thesis attempts a strategic pivot for OpenAI, shifting from a commoditized token sales model to a managed enterprise AI platform. While the strategic direction is conceptually sound as a response to market pressures, the financial projections and the accompanying Python falsification suite exhibit significant numerical inconsistencies and rely on highly optimistic, bordering on unrealistic, assumptions.

**Analytical Critique:**

1.  **Numerical Inconsistency in Python Code (`monthly_net_burn_2026`):**
    The most critical flaw lies in the Python code's calculation of `monthly_net_burn_2026`. The arithmetic transparency section correctly identifies `Net_Operating_Income_2026` as `-$1.7731B/year`, implying an annual burn of `$1.7731B`, or a monthly burn of `$147.76M`. However, the Python code calculates `monthly_net_burn_2026 = (fixed_opex_2026 - oai_total_gross_profit_2026) / 12 * (-1)`. This `* (-1)` operation inverts the sign, resulting in `monthly_net_burn_2026` being `-$147.76M`.
    This sign inversion fundamentally distorts subsequent calculations:
    *   `cash_buffer_required_2026` becomes negative (`6 * -$147.76M = -$886.56M`).
    *   `average_monthly_net_burn_midpoint` becomes `($358.33M + (-$147.76M)) / 2 = $105.285M`.
    When these err
```

## SAMPLE_081 (memory_entry)

```
---
name: Don't kill paid compute on a single noisy diagnostic
description: Long-running GPU/API jobs are destructive to terminate; falsifiers built same-day are hypotheses not verdicts; general-purpose tools serve multiple substrates so inversion-reflex applies before kill
type: feedback
originSessionId: daf28ee5-7f9f-4744-b1c4-cc905ddf3fd9
---
**Rule.** Auto-mode AUTHORIZES destructive actions; it does NOT lower the bar for thinking before taking them. Killing a long-running paid compute job (GPU, distributed run, multi-hour API session) is a destructive action even when no operator confirmation is required. Treat it as one.

**Specifically:**
- A falsifier's first run is a hypothesis, not a verdict. Validate its signal (regex bugs, vocab mismatches, normalization errors, sample-size sufficiency) BEFORE acting on it.
- INVERT the falsifier itself: is it scoped to one substrate / slice / distribution where the artifact would be useless, vs. ALL the contexts the artifact serves? General-purpose tools (encoders, retrievers, frameworks) serve multiple substrates. Killing them based on single-substrate underperformance fails inversion.
- The cheap alternative to a kill is **let the run finish, validate the falsifier separately, and re-evaluate with both signals.** A few hours of compute is cheap compared to restarting from scratch.

**Why:** 2026-05-06 incident — v4 GNN training o
```

## SAMPLE_082 (evidence_file)

```
# v1_in → residual_v1 (what attention+MLP add), layers 15→16
# BOS tokens excluded, centered on input mean only
# n	z
-2.821730	1.458519
-2.760915	2.512788
-2.706185	1.134448
-2.494015	2.667437
-2.439024	2.223484
-2.340460	1.826007
-2.290086	1.904940
-2.150094	1.646699
-2.134909	1.657250
-2.074226	2.401176
-2.047221	3.098351
-2.032275	2.338947
-1.963780	2.146148
-1.956216	2.414754
-1.925944	1.622368
-1.905622	1.724938
-1.905235	2.301280
-1.893146	1.371140
-1.865370	1.807636
-1.769846	1.448335
-1.724890	1.191793
-1.717307	1.421818
-1.715261	1.924119
-1.705138	1.705383
-1.697257	2.526882
-1.670180	2.373471
-1.653045	1.844882
-1.646998	2.178009
-1.635821	1.297197
-1.621364	1.254469
-1.601510	1.067948
-1.571106	1.883716
-1.549272	1.902284
-1.547263	2.283489
-1.515832	1.170110
-1.493241	1.584283
-1.461565	1.892891
-1.453072	1.482731
-1.419000	0.236774
-1.403105	1.282757
-1.345971	1.485539
-1.244656	1.560589
-1.201274	0.635067
-1.184572	1.739036
-1.134308	1.352140
-1.107015	1.598423
-1.087512	0.482097
-1.083183	0.340300
-1.080737	1.071609
-1.059956	1.281636
-1.053013	2.502115
-1.051633	0.405814
-1.041372	1.615772
-1.034816	1.046571
-1.022558	0.990468
-0.980510	0.924481
-0.974429	2.150497
-0.973229	0.568854
-0.965699	1.088770
-0.922420	0.486399
-0.869161	1.160203
-0.861875	2.182230
-0.842542	0.596207
-0.818326	0.177154
-0.790379	1.581814
-0.740311	0.797904
-0.733910	0.751579
-0.730694
```

## SAMPLE_083 (project_workspace_md)

```
Stage 5 is now the active P1 target: information-yield loop break. Stages 1 through 4 established a stable semantic gate, typed hinge extraction, exploit-family routing, and fixed board composition under typed handoff. The next question is whether the loop can decide when it is still learning and when it is only spinning.

---

### Weakest Link

The current loop still uses coarse stagnation counters. That catches some failure modes, but it does not distinguish:
- flat score with genuinely new attacks
- flat score with new hinge candidates
- flat score with new primitive-worthy failures
- flat score with pure repetition

A raw stagnation count is too blunt. It risks pivoting early when the loop is still producing new evidence, and it also risks wasting iterations when the same failure is just being restated.

### Core Claim

A deterministic information-yield controller can decide when the V4 loop should:
- continue,
- refresh specialists,
- or require a pivot,

using typed iteration evidence rather than raw score delta alone.

Stage 5 may make only a bounded claim:
- if the latest iteration improves score, continue
- if the latest iteration adds new attack, hinge, primitive, or axiom evidence, continue
- if there are multiple consecutive low-yield iterations with no novelty, refresh specialists
- if the same weakest point repeats across a longer low-yield window, require a pivot
```

## SAMPLE_084 (project_workspace_md)

```
# Adversarial Debate: gp023_planck_sandbox_03
<!-- rubric: gp023_planck_sandbox_03 | mutator: gemini | judge: gemini-2.5-flash -->


## Level 3 Unit Test Results
❌ FAIL (assertion): The thesis was DISPROVEN by its own unit tests.
Error: Traceback (most recent call last):
  File "/projects/gp023_planck_sandbox_03/gate_harness.py", line 348, in <module>
    sys.exit(main(sys.argv[1:]))
             ~~~~^^^^^^^^^^^^^^
  File "/projects/gp023_planck_sandbox_03/gate_harness.py", line 342, in main
    return run_visible_assertions()
  File "/projects/gp023_planck_sandbox_03/gate_harness.py", line 290, in run_visible_assertions
    i_model_fn, params = _load_model_from_test_model()
                         ~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "/projects/gp023_planck_sandbox_03/gate_harness.py", line 272, in _load_model_from_test_model
    spec.loader.exec_module(module)
    ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^
  File "<frozen importlib._bootstrap_external>", line 1026, in exec_module
  File "<frozen importlib._bootstrap>", line 488, in _call_with_frames_removed
  File "/projects/gp023_planck_sandbox_03/test_model.py", line 163, in <module>
    assert rel_error < 0.25, \
           ^^^^^^^^^^^^^^^^
AssertionError: DISCRIMINATOR 
```

## SAMPLE_085 (seam)

```
# GP-190 — Post-Run Discriminator Daemon and Background-Debt Ladder

**Status:** open  
**Opened:** 2026-04-30 10:55:30 EDT  
**Owner:** principal + Codex/operator-supervisor  
**Related:** `GP-119_inverter_agent_seam.md`, `GP-120_bridger_agent_seam.md`, `GP-183_falsification_mechanization_plan.md`, `GP-188_research_director_primitive_compilation_boundary_seam.md`, `GP-134_ztare_on_ztare_self_recursive_seam.md`, `projects/ns_millennium_hunt/workspace/phase5ab_163d_isomorphism.md`

---

## Eigenquestion

Which parts of the recent `gp163d` gravity and NS Millennium loops were
load-bearing operator-supervisor moves that should become ZTARE primitives,
and which parts should remain outside the apparatus because they still require
underspecified judgment?

## Bounded Thesis

The evidence supports a narrow claim:

> ZTARE plus a disciplined operator-supervisor loop works as a discovery
> instrumentation system. It turns failed fits, nulls, adversarial LLM
> critiques, and numerical anomalies into falsifiers, substrate audits, and
> reusable gates. It does not yet support the stronger claim that ZTARE
> autonomously discovers theory.

The practical conclusion is not "add a smarter agent."
```

## SAMPLE_086 (memory_entry)

```
---
name: Architecture maps are invariants, not documentation
description: Every edit to autoresearch_loop.py, fit_primitive.py, information_yield.py, or compress_champion.py MUST include a corresponding update to the architecture map in docs/internal/ BEFORE marking the task complete. This is not optional. The GP-088 import math bug and the Ulam scaffold failure both trace to stale maps.
type: feedback
originSessionId: ac81b280-1d14-4df2-8724-f342bfc627cc
---
Architecture maps are INVARIANTS, not documentation.

**Why:** The GP-088 `import math` bug happened because the map didn't document
that the BIC sort key needed `math` in scope. The Ulam scaffold failed because
no map documented the GP-072 protocol requirements. Every feature added without
a map update creates a latent bug for the next session.

**How to apply:** Before marking ANY task that touches these files as complete:
- `autoresearch_loop.py` → update `docs/internal/architectural_maps/autoresearch_loop_architectural_map.md`
- `fit_primitive.py` → update `docs/internal/architectural_maps/information_yield_architectural_map.md` (fit section)
- `information_yield.py` → update `docs/internal/architectural_maps/information_yield_architectural_map.md`
- `compress_champion.py` → update architecture map with Stage 1/Stage 2 changes
- New sandbox construction → verify GP-072 protocol followed (leak sentinel, rubric review)

The map update is part of the TASK, not a follow-up. If 
```

## SAMPLE_087 (seam)

```
# GP-039 Gate Library Formalization Seam

**Track:** findings
**Status:** `note` (n=1, principal-incepted from GP-032 deep dive)
**Origin:** GP-032 operational analysis + Paper 4 §7.7 institutional-verification architecture (2026-04-12)
**Trigger:** GP-032 identified that the moat is the gate *library* (failure-family taxonomy, accumulated precedent), not the gate *infrastructure* (JSON payloads, fail-closed semantics). Paper 4 §7.7 names a "public, versioned rule library" as the GAAP analog. Currently the gate definitions are scattered across rubric files, `autoresearch_loop.py` prompt templates, and seam debate logs with no single catalog.

---

## Problem Snapshot

ZTARE's deterministic gates exist in three places today:

1. **Rubric-level gates:** `enable_fit_primitive`, `fit_required_dimensionality`, `deterministic_score_gates` in per-project JSON rubrics
2. **Hardcoded gates:** charter-drift checks, quarantine-laundering caps, deferred-confirmation caps, bounded-discriminator contracts in `autoresearch_loop.py` prompt templates and scoring logic
3. **Documented failure families:** the ~9 boardroom families cataloged across GP-012, GP-014, GP-023, GP-030, and the field manual

```

## SAMPLE_088 (project_charter)

```
# Project Charter — GP-023 Planck Sandbox 02

**Program:** GP-023 Ontology Trap Planck Mechanism
**Status:** Phase 2 — asymmetric data-holdout sandbox run
**Domain:** Channel-reservoir allocation dynamics (synthetic)
**Pre-registration:** `research_areas/private/seams/GP-023_ontology_trap_planck_mechanism_seam.md`

---

## Core Question

A bounded channel-reservoir allocation system exhibits a response intensity
`I(phi, psi)` that rises, peaks, and then decays toward a low asymptotic floor
as the channel parameter `phi` grows at fixed reservoir pressure `psi`. The
asymptotic floor value may differ across sweeps. The peak location shifts to
larger `phi` as `psi` increases.

**Question:** What is the simplest operational model of `I(phi, psi)` that
(a) reproduces the full shape of the observed curves across all three sweeps,
(b) predicts where the peak sits as a function of `psi`, and
(c) admits a falsifiable quantitative anchor proxy that can be checked
directly against `evidence.txt`?

A model that only fits one regime (low `phi` or high `phi`) and diverges or
collapses in the other does **not** answer the core question.

---

## Difference from Sandbox 01 — Data Holdout

Sandbox 02 differs from Sandbox 01 in exactly one way: the evidence grid is
split into two slices. The file `evidence.txt` contains 30 phi grid points
per sweep and is the only evidence surface the mutator see
```

## SAMPLE_089 (seam)

```
# GP-023 Planck Sandbox 08 — Closure Note

Status: closed 2026-04-14
Primary outcome: **D (score=0 across 14 iterations) + GP-061/GP-062 cold-run evidence**
Pre-reg: `GP-023_planck_sandbox_08_pre_registration.md`
Run: 14 iters logged in `iteration_telemetry.jsonl`, 12 fits recorded, 13 derived_constraints provisional entries. Stopped at iter 13 per decision 2026-04-14.

Per AGENTS.md §7: sealed artifacts never edited in place. This is the post-mortem.

---

## Primary verdict

**Outcome D — score starvation.** Every one of the 14 logged iterations scored 0 against the gate battery. `champion_eval_results.json` shows `score=0`, unchanged from the iter-0 seed. `latest_eval_results.json` weakest-point: *"Level 3 falsification suite disproved the thesis by assertion (`fail_assert`). The thesis is directly falsified by its own output."*

Same structural verdict as sandbox_07: gemini-pro did not recover the Planck GT form under the eml-only grammar within the iteration budget. Sandbox_08 differed from sandbox_07 in having the hardcoded `_STRUCTURAL_MISFIT_HINT_TEMPLATE` injected into the mutator prompt (the workaround later subsumed by GP-061). It did not change the outcome.

---

## GP-
```

## SAMPLE_090 (paper_md)

```
# Contract-Governed Adversarial Evaluator Hardening: Stage-Gated Recursive Improvement with Typed Promotion Contracts

Daniel Alami — Independent Researcher; MBA Candidate, Harvard Business School

SSRN abstract ID: `6542998`

---

## Abstract

When an adversarial evaluator is itself the object of recursive improvement, unconstrained optimization can soften the enforcement surface the evaluator is supposed to maintain. This paper describes a stage-gated architecture in which a deterministic meta-runner — no learned parameters, no language-model judgment — governs evaluator-hardening by executing precommitted Python promotion contracts that return PASS, FAIL, or BLOCKED verdicts. Over a four-month development period, six evaluator-hardening stages were promoted through this mechanism. The contracts blocked one sloppy promotion before a fix was applied, scoped each stage to a named evaluation surface so that no stage could claim credit for improvements made elsewhere, and forced integration debts into separately governed programs rather than letting them inflate passing stage claims. The work builds on prior documentation of specification gaming in LLM-generated code (Alami, 2025a) a
```

## SAMPLE_091 (project_workspace_md)

```
# Activist Intervention: Dismantling Consumer Ego to Unlock the B2B Utility Value of FIGS

**The Core Dislocation**
FIGS is currently a mismanaged lifestyle brand masquerading as a medical essential. Management’s obsession with "Community Hubs" and fast-fashion outerwear has resulted in a terminal destruction of Return on Equity (now 2.0% - 4.5%) and a 440 basis-point collapse in Q4 gross margins to 62.9%. While management chases retail vanity with $17 million in projected 2026 CapEx, they have allowed inventory to balloon to $150 million—19% of which is non-core "lifestyle" waste—driving turnover down to a sclerotic 1.55x. At a ~$16.00 share price and 40x EV/EBITDA, the market is pricing a growth story that management’s $5.6 million inventory write-off has already proven false. The status quo intrinsic value is $7.00. Our restructuring plan corrects this trajectory to realize a target value of **$18.20 per share.**

**The B2B Pivot: Overcoming the Industrial Incumbent**
The bear case—that Cintas’s industrial laundry moat is impenetrable—rests on an obsolete "centralized logistics" model that modern hospital CFOs are desperate to offload. We will dismantle the Cintas advantage through two clinical financial realities:

1.  **The Labor Arbitrage (Retain vs. Replace):** Hospital margin compression is driven by labor, not procurement. The average cost of a single nurse turnover is
```

## SAMPLE_092 (project_workspace_md)

```
# Adversarial Debate: gp163d_unified_accel
<!-- rubric: gp163d_unified_accel | mutator: o3 | judge: gpt-4.1 -->


## Level 3 Unit Test Results
❌ FAIL (harness defect): 🚨 HARNESS DEFECT — NOT A FALSIFICATION ATTEMPT.
The Level 3 suite did not run to completion. The thesis has NOT been tested. Judge MUST treat this as an uncategorized tooling failure and MUST NOT rationalize it as evidence the thesis survived scrutiny. Any score reflecting 'mostly passed' in this state is a categorization error.
Error: 

# Final Score: 0
**Weakest Point:** The thesis is uncategorized (harness did not run): Level 3 suite did not test the code, so no real model falsification or validation on holdout/farther-tail occurred. Thus, despite a clean and explicit pre-commit (U), the apparatus never ran the Newton-step. The single catastrophic assumption—universality of c—is thus untested. There is no empirical evidence to reward. According to protocol, the most that can be awarded is the structural score for explicit pre-commit, not prediction/fit/validation.
**Rationale:** The thesis explicitly and correctly pre-commits to Hypothesis U (universality, c_B = c_C = c_A), in full compliance with charter and substrate rules. However, the apparatus did not run, so no empirical evidence exists for or against universality. Thus, all key claims—especially farther-tail generalization and Newton-step validation—are
```

## SAMPLE_093 (project_workspace_md)

```
**CAUSAL MECHANISM**
If the generating mechanism maps the squared input $x^2$ scaled by a precise frequency parameter ($B=0.01$) through a sine function constrained by an amplitude $A=50$, then the output $y$ will exhibit continuous oscillations bounded within $[-50, 50]$ where the spatial frequency (distance between sign changes) monotonically increases as $|x|$ grows, under the scope of bounded integer quantization.

**RIVAL HYPOTHESIS**
The generating process is a polynomial of an even degree or a standard harmonic oscillator (a simple sine wave $\sin(kx)$). The proposed thesis predicts a constantly accelerating oscillation frequency ("chirp") that mathematically remains bounded globally. The polynomial rival predicts eventual absolute divergence to infinity outside the current window. The standard harmonic rival predicts a constant wavelength (uniform distance between peaks/zero-crossings) across all domains.

**NAMED DISCRIMINATOR**
Spatial Frequency Compression of Zero-Crossings.

**OBSERVABLE PROXY**
- **(A) CURRENT OBSERVABLE:** The distance on the x-axis between consecutive observed sign changes in `evidence.txt` strictly decreases. A simple sine wave dictates a uniform gap between zero-crossings. The dataset objectively confirms a compressing gap: the distance between the first observed positive-to-negative drop is roughly $\Delta x \approx 8$ (between $x=15, y=39$ an
```

## SAMPLE_094 (project_workspace_md)

```
# Adversarial Debate: ai_inference_collapse

## Attacker: Cloud Economics & Partner Strategy Analyst
The thesis's pivot from immediate cash flow exhaustion to structural Return on Invested Capital (ROIC) destruction represents a more robust and financially sound framework for evaluating the long-term viability of frontier model laboratories. Capitalizing training costs and assessing their amortization against a compressing useful life due to open-source parity is a valid analytical approach. However, the accompanying Python falsification suite contains several parametric inconsistencies and misapplications that, paradoxically, *understate* the financial pressures on the target entity, thereby weakening the Mutator's own argument for insolvency.

**Analytical Critique:**

1.  **Hyperscaler Strategic Misalignment and Channel Conflict:** The thesis posits that hyperscalers will "aggressively route *all* net-new enterprise AI workflows to their OSS MaaS offerings." This assertion exhibits a fundamental misunderstanding of hyperscaler strategic incentives and the complexities of channel dynamics.
    *   **Microsoft's Position:** Microsoft's substantial investment in OpenAI (exceeding $13 billion) and its strategic partnership are predicated on OpenAI's ability to command premium pricing for its frontier models. Aggressively disintermediating OpenAI by routing *all* traffic to OSS m
```

## SAMPLE_095 (evidence_file)

```
# Evidence Brief: NS Stationary-Euler Escape

The current Navier-Stokes proof graph has compressed through the following
sequence:

```text
static metric pressure cap
  -> falsified as generic fractional bridge

pressure dwell
  -> resupply versus escape/viscous erasure

resupply exponent pincer
  -> dynamic realization requires explicit U_n

dynamic realization
  -> residual-defect transfer certificate Defect_n < 1

exact residual-stable packets
  -> pressure channel can be null

exact pressure-active packets
  -> equal-shell orthogonal dual shears

bounded finite-mode taxonomy
  -> pressure-active residual-zero examples compress to stationary Euler
     single-eigenvalue flows
```

Key known theorem object:

```text
u = e^(-nu K^2 t) n x grad psi
-Delta psi = K^2 psi
```

is an embedded two-dimensional incompressible stationary Euler eigenflow. Its
nonlinear term is pure pressure. The pressure-Poisson source can be nonzero,
but the Leray-visible nonlinear velocity effect is zero.

## Task

Do not submit another merely pressure-active packet.

Find one of:

1. **Positive stationary-Euler escape.** A finite-mode or asymptotic packet
   family that leaves the stationary-Euler single-eigenvalue manifold, keeps
   projected NSE residual/defect controlled, and produces signed
   pressure-strain, recurrence, or resupply profit.

2. **No-go classification.** A theorem showing that a 
```

## SAMPLE_096 (project_workspace_md)

```
# Phase 5HU - Recursive Gate Application to NS

- **Recorded:** 2026-05-05 10:27:18 EDT
- **Scope:** GP-215/216 seam-theory gates and GP-152 Framer gates applied to the current NS proof path

- Classification: `recursive_gates_route_ns_to_real_pde_estimate_or_profile_falsifier`
- Modal closed-arc cluster: `Obligation Field Stratification` (77.3%)

## Gate Verdicts

### Meta-Arc Gates

- `GP215-G2-SATURATION`: **FAIL** / `failed_for_obligation_naming`
  - reason: Modal class `Obligation Field Stratification` covers 77.3% of closed NS cycles.  Similarity retrieval will over-recommend the move class the project has already saturated.
  - action: Reject any next move whose main output is another named Lean obligation skeleton without a real estimate or falsifier.
- `GP215-G3-MODAL-DOWNWEIGHT`: **PASS** / `rare_move_required`
  - reason: The rare closed move classes are certificate lift, residual pre-declaration, interaction partition, interface composition, and killing falsifier.  The missing move is out-of-catalog: a fixed-topology PDE estimate or a falsifier of one.
  - action: Prefer branch falsifiers, continuum estimates, and profile limit certificates over broad ZTARE packet generation.
- `GP215-G4-REAL-ADVERSARY`: **PASS** / `adversary_must_be_cross_substrate_or_cross_class`
  - reason: The top NS-like recommendation must be paired with a structurally different adversary.  Fo
```

## SAMPLE_097 (project_workspace_md)

```
# Minimal AQUAL Sandbox Gamma Scan Takeaway

Generated: 2026-04-29

## Verdict

Classification: `instrument_not_promoted`

This first 3D AQUAL sandbox is useful as an instrument test, but it is not yet
a physics result and does not justify GPU scale-up.

## What Ran

- Grid: `64^3`
- Source families:
  - `udg_gaussian`
  - `binary_peaks`
- Boundaries:
  - uniform: `Phi_edge = -g_ext*z`
  - traceless tidal: `Phi_edge = 0.5*Gamma*(z^2 - 0.5*x^2 - 0.5*y^2) - g_ext*z`
- Solvers:
  - Newtonian finite-volume reference
  - AQUAL finite-volume fixed-point relaxation with `mu(s)=s/sqrt(1+s^2)`
- Gamma scan:
  - `Gamma=0.02`
  - `Gamma=0.08`
  - `Gamma=0.45`

## Key Numbers

| Gamma | UDG uniform A/N | UDG tidal A/N | binary uniform A/N | binary tidal A/N | UDG tidal/uniform | binary tidal/uniform |
|---:|---:|---:|---:|---:|---:|---:|
| `0.02` | `7.287` | `556.631` | `6.665` | `5.261` | `76.385` | `0.789` |
| `0.08` | `7.287` | `2286.312` | `6.665` | `13.201` | `313.743` | `1.981` |
| `0.45` | `7.287` | `11431.271` | `6.665` | `429.724` | `1568.676` | `64.474` |

## Interpretation

The sandbox shows one weakly encouraging directional signal and one major
instrument defect:

- Encouraging: at low shear (`Gamma=0.02`), the compact binary's
  AQUAL/Newtonian internal-acceleration ratio drops from `6.665` under uniform
  boundary to `5.261` under tidal boundary.
- Defect: the UDG tidal metr
```

## SAMPLE_098 (seam)

```
# GP-099 — Vocabulary Floor: Expanding the Primitive Library Without Combinatorial Death

## Status

open — opened 2026-04-19 09:45:00 EST

## ID

GP-099

## Eigenquestion

Can ZTARE discover physical laws requiring special functions (Bessel, Error, Gamma) without adding them to _BASE_PRIMITIVES — by using a universal approximant primitive (Padé) that can *become* any special function through its coefficient matrix?

## Problem Statement

Component D's topology synthesizer is bottlenecked by the 32 functions hardcoded in `_BASE_PRIMITIVES` (topology_synthesizer.py:1060-1095). It can compose them to depth-2, but it cannot invent mathematical classes absent from the library.

If the true physical law requires a special function (Bessel J₀(x), error function erf(x), Gamma function Γ(x), Airy function Ai(x)) that cannot be cleanly approximated by depth-2 combinations of exp, log, power, and trig, the apparatus will:
1. Hit the Feynman Wall (library exhausted)
2. Spin up Component D (composition mode)
3. Fail to find a valid composition (the spanning set doesn't contain the target)
4. Permanently stall with WALL_LIBRARY_INSUFFICIENT

This is a genuine ceiling, not a solvable engineering
```

## SAMPLE_099 (evidence_file)

```
# Evidence Brief: NS Independent Multi-Shell Cascade

The current NS pressure-channel proof graph has reached a sharp boundary.

Known facts from bounded deterministic audits:

```text
canonical packet:
  W = (sin y, -sin x, 0)

one-background ceiling:
  ratio^2(M) = 5(M-1)^2 / (6(M+1)^2)
  limit = 5/6

two-background ceiling:
  ratio^2(M) = 18(M-1)^2 / (19(M+1)^2)
  limit = 18/19

full small-background subspace:
  infinite axis-contrast limit = 0.986394

bounded multi-shell ladder:
  B=2: 0.986393924
  B=3: 0.994236263
  B=4: 0.997037031
  B=5: 0.998280308
```

No audited local finite-mode background class crosses the residual-defect
threshold. But the multi-shell ladder approaches `1` from below, so the
remaining theorem boundary is genuinely asymptotic.

## Task

Do not submit a phase-fit.

Find one of:

1. **Independent positive cascade.** Define a multi-shell generator before
   scoring, then compute its projected residual, signed pressure-strain or
   recurrence profit, and transfer/defect margin. Promotion requires ratio
   crossing `1` without choosing phases/amplitudes from the desired
   cancellation.

2. **Subcritical ceiling theorem.** Explain why the observed ladder approaches
   `1` from below for a stated independent generator or generator class, and
   identify the exact limiting inequality.

3. **Escrowed conjecture.** State the remaining multi-shell inequality
```

## SAMPLE_100 (project_workspace_md)

```
### EPISTEMIC AUDIT: RESOLUTION OF THE SINGLE-TRIAL ANTHROPIC FALLACY

**DIRECT VERDICT:** 
The application of the Weak Anthropic Principle (WAP) to a single-trial universe is an "Epistemic Default." It attempts to use the **Effect** (Observer) to justify the **Cause** (Constants) while ignoring the **Probability Density** ($P \approx 0$). This is logically equivalent to a lottery winner claiming the lottery was rigged in their favor *because* they won. To resolve this without resorting to theological hand-waving or infinite multiverse sprawl, we must shift the domain from **Stochastic Physics** to **Informational Parsimony**.

---

### 1. SYMBOLIC MAPPING: $Z = f(X, Y)$

To resolve the inconsistency, we map the systemic state:
$$Z = \text{Observed Anthropic Stability (The Resultant)}$$
$$X = \text{Stochastic Probability (The Blocked Variable)}$$
$$Y = \text{Algorithmic Parsimony (The Leverage Variable)}$$

*   **X (Blocked):** The current system relies on $X$ (Random Chance). Given the fine-tuning of the Cosmological Constant ($\Lambda$) at $10^{-120}$, the probability $P(X) \to 0$. $X$ is blocked because a single trial cannot bridge a $120$-order-of-magnitude gap without an ensemble (Multiverse), which is currently unobservable and thus non-Popperian.
*   **Y (Leverage):** We pivot to $Y$—the **Computational Minimum**. The universe does not exist because it is *likely*; it ex
```

## SAMPLE_101 (project_workspace_md)

```
### CAUSAL MECHANISM
If the channel parameter `phi` governs the baseline allocation volume space, it contributes a polynomial capacity factor $\phi^p$. If the reservoir pressure `psi` imposes a flow restriction, it introduces a penalty exponent $Z = (\gamma \phi / \psi)^q$. If the channel-reservoir allocation process distributes flow across a discrete ladder of activation tiers (where successive tiers incur exponentially decaying fractional occupation), then the total saturation multiplier sums as an infinite geometric series of these tier states: $\sum_{k=1}^\infty e^{-kZ} = 1 / (e^Z - 1)$. Combining the baseline capacity, the tier-summed saturation multiplier, and a static floor flow (`offset`) yields a composite response intensity $I(\phi, \psi) = A \phi^p / (\exp(Z) - 1) + \text{offset}$ under fixed reservoir pressure $\psi$.

### RIVAL HYPOTHESIS
Rival: The channel suppression operates as a simple continuous rational-polynomial capacity constraint $I_{rival} = A \phi^p / ((\gamma \phi / \psi)^q + B (\gamma \phi / \psi)^m) + \text{offset}$. This thesis predicts that the tier-summed exponential formulation correctly bridges the low-$\phi$ rise and the high-$\phi$ exponential cutoff via the $e^Z - 1$ denominator structure. The rational-polynomial rival produces a slower power-law tail and fails to enforce the tight low-to-peak curvature ratio.

### NAMED DISCRIMINATOR
The str
```

## SAMPLE_102 (project_charter)

```
# Project Charter: GP163D ADMSR Attack And Clean-Room Bridge

Status: active

Opened: 2026-05-03 16:38:00 EDT

## Primary Observable

Whether the current gp163d frontier can be converted from a good bounded law
packet (`ADMSR`) into a concrete next executable validation object: a minimal
honest clean-room contract, a stronger attacker packet, or a no-go theorem
against premature concretization.

## Secondary Observable

Whether the current branch is still underspecified even at that narrower level,
in which case the correct output is a no-go theorem rather than a build plan.

## Eigenquestion

What is the smallest real independence standard and strongest remaining
attacker bundle that could move gp163d from science-bridge status toward a
bounded regime-law candidate without hidden contamination?

## Background

Current live facts:

- raw orientation phase is not representation-invariant
- diffuse-versus-compact amplitude separation survives across the two
  admissible representations
- compact controls remain operationally flat
- the primitive explanatory anchor is
  `total_over_internal_mass_weighted__ratio`
- `CR-APD` is the current forward portability gate
- `RAGT` is the current revocation layer
- the law-packet search has converged on `ADMSR`
- the seeded `CR-APD` checker hardening already failed closed on copied rows,
  negative deltas, denominator-floor contamination, an
```

## SAMPLE_103 (raw_evidence_input)

```
# org/goals/ — Principal → Agent Goal Inbox (GP-132)

Markdown-first goal artifacts. The principal writes a goal file; any agent session picks it up on next wake. No Python invocation required.

## Lifecycle

```
pending/<goal_id>.md    ← principal writes here
   │
   │  agent picks up at next wake; claims via sessions.claim_task()
   ▼
active/<goal_id>.md     ← agent working on it
   │
   │  on completion, agent appends ## Result section
   ▼
done/<goal_id>.md       ← archived; audit trail preserved
```

## Creating a goal

Write `org/goals/pending/<goal_id>.md` with YAML frontmatter:

```markdown
---
goal_id: <snake_case_id>
priority: low | medium | high | urgent
deadline: YYYY-MM-DD         # or null for no hard deadline
estimated_cost_usd: <float>  # 0.0 if no spend expected
assigned_to: role.manager    # or role.engineer | role.reviewer | role.principal
autonomous_scope_ok: true | false   # principal's read on whether this is in-mandate
created_by: daniel_alami
created_utc: 2026-04-23T14:00:00Z
---

# <human-readable title>

<intent — what for, not how>

<context — files, seams, prior work the agent needs>

<success criteria — how will we know it's done>

<escalation triggers — when should the agent stop and ask>
```

## Agent contract

When an agent session starts, it:

1. Lists `org/goals/pending/*.md`, sorted by priority + deadline.
2. For each goal:
   - If `autonomous
```

## SAMPLE_104 (verified_axiom)

```
NF3_SHARE (Taiwan produces ~30% of global NF3)
```

## SAMPLE_105 (project_workspace_md)

```
# Adversarial Debate: gp023_planck_sandbox_02
<!-- rubric: gp023_planck_sandbox_02 | mutator: gemini | judge: gemini-2.5-flash -->


## Level 3 Unit Test Results
❌ FAIL (harness defect): 🚨 HARNESS DEFECT — NOT A FALSIFICATION ATTEMPT.
The Level 3 suite did not run to completion (terminating exception: `AttributeError`). The thesis has NOT been tested. Judge MUST treat this as an uncategorized tooling failure and MUST NOT rationalize it as evidence the thesis survived scrutiny. Any score reflecting 'mostly passed' in this state is a categorization error.
Raw stderr: Traceback (most recent call last):
  File "/projects/gp023_planck_sandbox_02/gate_harness.py", line 302, in <module>
    sys.exit(main(sys.argv[1:]))
             ~~~~^^^^^^^^^^^^^^
  File "/projects/gp023_planck_sandbox_02/gate_harness.py", line 296, in main
    return run_visible_assertions()
  File "/projects/gp023_planck_sandbox_02/gate_harness.py", line 246, in run_visible_assertions
    i_model_fn, params = _load_model_from_test_model()
                         ~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "/projects/gp023_planck_sandbox_02/gate_harness.py", line 233, in _load_model_from_test_model
    raise AttributeError("test_model.py does not expose MODEL_PARAMS")
AttributeError: test_m
```

## SAMPLE_106 (raw_evidence_input)

```
---
source_type: source_evidence
---
# Evidence Fetch — 2026-04-21T15:39:58Z
Source: GP-051 bounded evidence-collection agent
Severity filter: degrading
Gaps fetched: 1

### Gap 0 — JumpStart payroll tax actual collections 2021 2022 2023 Seattle budget

## Evidence Batch — 2026-04-21T15:39:58Z
Gap index: 0
Gap severity: degrading
Gap target: JumpStart payroll tax actual collections 2021 2022 2023 Seattle budget
Gap query: Seattle JumpStart payroll expense tax revenue collected 2021 2022 2023 annual budget office affordable housing fund
Run timestamp: 1776744343
Status: accepted
Source note: web_search via gpt-4.1

The Seattle JumpStart payroll expense tax, implemented in 2021, is a progressive tax levied on businesses with annual payroll expenses exceeding specific thresholds. The tax rates range from 0.7% to 2.4%, depending on the company's payroll size and the compensation levels of its employees. The primary objective of this tax is to generate revenue for affordable housing, economic revitalization, and other community investments.

**Revenue Collection:**

- **2021:** The inaugural year of the JumpStart tax saw revenues totaling approximately $293 million. Initially, $248 million was collected, with an additional $45 million in late payments received throughout 2022. ([seattle.gov](https://www.seattle.gov/documents/departments/oerf/reports/2022/2022%20q4%20year-end%20reven
```

## SAMPLE_107 (project_workspace_md)

```
# Adversarial Debate: figs_hbs_turnaround_2026
<!-- rubric: figs_hbs_turnaround_2026 | mutator: claude | judge: claude-sonnet-4-6 -->


## Level 3 Unit Test Results
✅ PASS: The thesis survived its own falsification suite.
Output: 

# Final Score: 60
**Weakest Point:** The thesis names the CAC-reduction-vs-friction-cost trade-off as the critical unknown but then issues an execution directive to redirect capital toward enterprise integration capability without resolving that unknown first. This is the firing squad's central attack and it lands: the memo uses different evidentiary standards for the turnaround CapEx freeze (well-grounded) versus the enterprise capability investment (assumption-dependent). The correction requires either completing the turnaround fully before any enterprise capital allocation, or providing an explicit minimum viable proof-point threshold with a stated cost ceiling for enterprise capability investment that does not depend on unproven CAC savings.
**Rationale:** The thesis presents a well-structured two-stage case: turnaround first via capital discipline (CapEx freeze, inventory rationalization), transformation second via selective B2B2C pilots. Its strengths are intellectual honesty about the B2B2C friction burden, correct governance diagnosis under founder control, and appropriate rejection of the full utility re-rating story. The firing squad's cent
```

## SAMPLE_108 (project_workspace_md)

```
## RESOLUTION OF SYSTEMIC INCONSISTENCY: `sustained_multistate_breakdown_of_core_obligations` Threshold Grounding

**SYSTEMIC INCONSISTENCY:** "The derivation of the N=3 threshold for 'multi-state breakdown' from qualitative textual evidence in S006 and S019 remains an interpretation and definitional choice rather than a direct, quantitatively undeniable derivation, leaving its exact numerical grounding vulnerable to alternative interpretations."

This inconsistency is resolved by explicitly grounding the numerical threshold N=3 as a *minimal operationalization* of the qualitative term "multi-state breakdown" within the context of existing legal challenges and differentiated integration, rather than a direct empirical derivation.

---

**CAUSAL MECHANISM:**
If the condition `sustained_multistate_breakdown_of_core_obligations` is explicitly tied to a *quantified minimum threshold of member states* (N) exhibiting *sustained, legally unrectified non-compliance* with *core EU legal principles*, and this threshold is justified as the lowest integer differentiating *systemic breakdown* from *localized or bilateral legal contestation* based on qualitative evidence, then the `material_union_failure` event boundary is demonstrably grounded in observable legal behavior, moving beyond arbitrary thesis-authored scenarios. This approach acknowledges the multi-modal nature of disintegration 
```

## SAMPLE_109 (verified_axiom)

```
Only strictly radial Littlewood-Paley finite stencils commute with the Euclidean Leray projector.
```

## SAMPLE_110 (project_charter)

```
# Project Charter — GP-023 Planck Sandbox 01

**Program:** GP-023 Ontology Trap Planck Mechanism
**Status:** Phase 1 — pre-registered sandbox run (see `research_areas/seams/GP-023_planck_pre_registration.md`)
**Domain:** Channel-reservoir allocation dynamics (synthetic)

---

## Core Question

A bounded channel-reservoir allocation system exhibits a response intensity
`I(phi, psi)` that rises, peaks, and then decays toward a low asymptotic floor
as the channel parameter `phi` grows at fixed reservoir pressure `psi`. The
asymptotic floor value may differ across sweeps. The peak location shifts to
larger `phi` as `psi` increases.

**Question:** What is the simplest operational model of `I(phi, psi)` that
(a) reproduces the full shape of the observed curves across all three sweeps,
(b) predicts where the peak sits as a function of `psi`, and
(c) admits a falsifiable quantitative anchor proxy that can be checked
directly against `evidence.txt`?

A model that only fits one regime (low `phi` or high `phi`) and diverges or
collapses in the other does **not** answer the core question.

---

## Out Of Scope

- Historical or real-world analogs. Do not import named models from physics,
  economics, biology, or queueing theory by name. This sandbox deliberately
  strips away domain vocabulary; if your proposal is a renamed version of a
  textbook formula, cite the formula explicitly in the
```

## SAMPLE_111 (raw_evidence_input)

```
---
source_type: collection_todo
---

# EU Load-Bearing Pillars: Evidence Collection Plan

Current blocker from the latest baseline:

- the thesis still hard-fails as self-reference because the thresholds for:
  - `functionally material` fiscal capacity
  - `reduced recurrent constitutional contestation`
  are not independently grounded outside the thesis's own ontology

So the next evidence pass should target externally grounded threshold material, not more prose defending the ontology.

## Priority source classes

1. Evidence on what counts as materially meaningful central fiscal stabilization in established federations
   - comparative federal budget size
   - automatic stabilizer capacity
   - fiscal transfer intensity during asymmetric shocks
   - why specific scales are or are not considered materially stabilizing

2. Evidence on legal supremacy consolidation in established federations
   - indicators of uncontested versus contested supremacy
   - recurring constitutional challenge frequency or severity
   - how comparative federal systems distinguish normal legal disagreement from persistent supremacy contestation

3. Comparative cases that stress-test the EU ontology
   - cases where discretionary resilience might still be treated as equilibrium
   - cases where standing federal mechanisms clearly existed and can anchor the Mode DE boundary

## What to add into `raw/`


```

## SAMPLE_112 (verified_axiom)

```
WORLD_EQ_MKT (~$115T USD)
```

## SAMPLE_113 (project_workspace_md)

```
## Direct answer

The fixed-public-record theorem is **not yet valid** as stated. The weak link is apparatus capture that is created **before** the public record is fixed and is not visible in the declared signals.

This gives a concrete sixth auditable failure mode:

> **6. Apparatus provenance laundering:** the claimant shapes the pool, incentives, dependencies, or career constraints of auditors/challengers before certification, while the public record still shows formal independence, escrow payment, access parity, logs, and no post-hoc Omega change.

If the current fifth mode, “residual discovery failure,” is expanded to include all such hidden institutional influence, then mode 5 becomes tautological: it means “anything that made discovery fail.” If mode 5 is kept operational and limited to visible apparatus defects, then apparatus provenance laundering is a sixth mode.

No axioms are retired. The verified axioms remain binding. The correction is within their domain: **red-team independence must be positively certified, not inferred from absence of visible capture signals.**

---

# 1. Counterexample to the five-mode reduction

## Strategy: pre-record institutional dependency capture

A claimant funds or influences an ecosystem before the audit:

- sponsors evaluator fellowships;
- funds benchmark infrastructure;
- offers future consulting access;
- funds conferences or lab
```

## SAMPLE_114 (memory_entry)

```
---
name: Mungerian thinking as ZTARE core philosophy
description: Munger's mental models are not decorative influence but load-bearing architectural principles throughout ZTARE — inversion, anti-self-deception, lollapalooza effects, circle of competence, checklist discipline, man-with-a-hammer avoidance
type: project
---

Mungerian thinking pervasively guided the construction of ZTARE from scratch and continues to be the operational philosophy. This should be treated as a core architectural principle, not just a stylistic preference.

**Load-bearing mappings:**

- **Inversion** → Falsification-first loop architecture. Don't ask "is this true?" — ask "where will this die?" Failure registry, adversarial judges, deterministic gates.
- **Avoid self-deception** → Zero-trust architecture. Adversarial separation. Deterministic gates the judge can't override. Bounded critique agents that review with clean context.
- **Man with a hammer** → Pattern 9 (frustration-anchored diagnosis). When deep in one layer of the stack, fix proposals default to that layer even when the failure is elsewhere. The antidote: structural isolation (bounded critique agent) and offline ablation before prompt-side fixes.
- **Lollapalooza effects** → Cross-layer recurrence finding. Same Goodhart pattern at code, evaluator, governance, and operator layers. Multiple forces combining.
- **Circle of competence** → U
```

## SAMPLE_115 (concept_doc)

```
---
id: GP-157
status: active
summary: GP-101 self-model for src/ztare/orchestrator/contract_table.py + protocols.py + render_evidence_template.py (Layer 1 typed-contract foundation)
---

# orchestrator/contract_table.py — architectural map

GP-157 v5.0 Layer 1 self-model. Per Task #67 panel synthesis: typed
ABI registry that becomes the single source of truth for substrate
contracts, replacing the 5-source-contradiction failure mode shipped
under prompt.py / contract_adherence.py / mutation_suite_guard.py.

## Region map

region: substrate_abi_enum  lines: 35-65  entry: class SubstrateABI(Enum)
region: contract_spec  lines: 68-110  entry: @dataclass(frozen=True)
region: scalar_skeleton  lines: 130-155  entry: _SCALAR_1D_SKELETON
region: feature_skeleton  lines: 157-180  entry: _FEATURE_DICT_SKELETON
region: contract_registry  lines: 185-240  entry: CONTRACT_REGISTRY
region: public_api  lines: 245-265  entry: def get_spec

## Function/method index

func: get_spec  sig: (abi: SubstrateABI) -> ContractSpec
func: get_spec_by_class  sig: (cage_meta_class: str) -> Optional[ContractSpec]
func: list_substrate_classes  sig: () -> tuple[str, ...]

## Companion arch maps

- `orchestrator_protocols_architectural_map.md` — runtime-checkable Protocols + adapt().
- `orchestrator_render_evidence_template_architectural_map.md` — evidence.txt §D rendering.

## Drift policy

Three files register
```

## SAMPLE_116 (verified_axiom)

```
Architectural proofs must use minimal simulation complexity
```

## SAMPLE_117 (seam)

```
# GP-034 Loop Control Blind to Latent Distance Seam

**Track:** findings
**Status:** `active` (n=2)
**Origin:** runtime-discovered during GP-023 Phase 2, then independently reproduced in GP-037 3b clean run (2026-04-11, 2026-04-12)
**Trigger:** Codex + operator noticed a contradiction between two files in the same workspace

---

## Problem Snapshot

Two files in the same workspace describe the same run and disagree about whether the mutator is moving:

- `projects/gp023_planck_sandbox_02/workspace/latent_distance.jsonl` — every one of iterations 1–17 is tagged `"motion_class": "structural_move"` with Jaccard distances mostly `1.0` on failure_families, attack_surface, named_primitives, and thesis_text. The mutator is traversing the semantic space at maximum possible distance per iteration.
- `projects/gp023_planck_sandbox_02/workspace/latest_information_yield.json` — at iter 17, `novel_attack_ids: []`, `novel_hinge_ids: []`, `novel_primitive_ids: []`, `verified_axioms_added: 0`, rationale *"Information yield is low; refresh specialists before attempting a broader pivot"*, `stagnant_window: 17`.

The loop-control layer fired `REFRESH_SPECIALISTS` on a scalar-novelty-yield signal tha
```

## SAMPLE_118 (project_workspace_md)

```
# Phase 5IT - Matrix Leray Cancellation Escape Search Agent

- **Recorded:** 2026-05-05 14:27:15 EDT
- **Scope:** bounded deterministic search for matrix-valued Leray low-beat cancellation beyond Phase 5IS scalar atoms
- **Classification:** `no_matrix_leray_cancellation_escape_under_output_declared_ledger`
- **Topology rows scored:** `1440`
- **Output-ledger falsifiers:** `0`
- **Source-Frobenius warnings:** `0`
- **Bounded priced-survival witnesses:** `864`

## Eigenquestion

Can a fixed low-beat sequence or block keep declared branch, positive coherence, and physical reserve bounded while matrix-valued Leray cancellations leave an unpriced surviving payoff?

## Result

The matrix low-beat symbol does show genuine finite-dimensional matrix advantage over a single scalar polarization column, but once the resulting low-beat vectors are declared as Hilbert output atoms, branch plus one-sided positive coherence still covers the Leray self-tax.  Positive physical low-beat reserve prevents the searched high-shell schedules from turning bounded declared price into an unpriced escaping payoff.  Bounded priced survival exists, but it is already inside the declared output ledger.

## Exact Receipts

- Candidate low-beat matrices scored: `3297`
- Max exact direct-minus-collapsed norm squared: `0`
- Max exact q dot projected output: `0`
- Max observed sigma / (2|q|): `0.707063674119`

## 
```

## SAMPLE_119 (raw_evidence_input)

```
# GP-164 — ZTARE v2.0 Meta-Architecture: REFRAME + ANALOGY

Status: draft (architectural proposal, no implementation)
Opened: 2026-04-26
Track: kernel
Related: GP-152 (Framer spec v2.0), GP-103 (compression primitive), GP-085 (grammar ceiling hypothesis)

## Trigger

2026-04-26 — A 23-year-old with no advanced math training solved a
60-year Erdős conjecture on primitive sets using ChatGPT Pro. Terence
Tao's commentary: "people did look at it, and the humans that looked
at it just collectively made a slight wrong turn at move one." The AI
applied "a formula that was well known in related parts of math, but
which no one had thought to apply to this type of question."

Source: Scientific American, April 2025. Qiacochu Yuan (Twitter/X,
2026-04-25): "spooky implication that there is potentially some whole
universe of 'shadow math' that you have to make inhuman mental movements
to access."

This result has direct implications for ZTARE's architecture. The
apparatus currently searches within a FIXED grammar library — the
operator decides which functional forms are available. The Erdős
result shows the binding constraint on mathematical discovery is not
intelligence, compute, or rigor — it's the SEQUENCE IN WHICH TOOLS
ARE CONSIDERED. ZTARE's grammar library IS a canonical ordering.
The breakthrough came from bypassing that ordering.

## Eigenquestion

> Can ZTARE's architecture be ext
```

## SAMPLE_120 (project_workspace_md)

```
# Adversarial Debate: gp163d_unified_accel
<!-- rubric: gp163d_unified_accel | mutator: gpt4.1 | judge: gpt-4.1 -->


## Level 3 Unit Test Results
✅ PASS: The thesis survived its own falsification suite.
Output: {
  "holdout": {
    "n": 732,
    "mean_relative_error": 0.2677578818629891,
    "max_relative_error": 3.617513774441412,
    "passed": true,
    "threshold": 0.35,
    "per_class_mre": {
      "A": 0.2677578818629891
    }
  },
  "farther_tail": {
    "n": 63,
    "mean_relative_error": 0.2904501523557784,
    "max_relative_error": 0.6286248417856806,
    "passed": true,
    "threshold": 0.5,
    "per_class_mre": {
      "B": 0.3058663148392294,
      "C": 0.06306175572487739
    }
  },
  "asymptotic": {
    "violations": [],
    "passed": true
  },
  "farther_tail_class_B": {
    "n": 59,
    "mean_relative_error": 0.3058663148392294,
    "max_relative_error": 0.6286248417856806,
    "passed": true,
    "threshold": 0.5,
    "per_class_mre": {
      "B": 0.3058663148392294
    }
  },
  "farther_tail_class_C": {
    "n": 4,
    "mean_relative_error": 0.06306175572487739,
    "max_relative_error": 0.09388542091461241,
    "passed": true,
    "threshold": 0.5,
    "per_class_mre": {
      "C": 0.06306175572487739
    }
  },
  "all_gates_pass": true
}


# Final Score: 100
**Weakest Point:** The single most catastrophic and load-bearing vulnerability is the unprovable (at
```

## SAMPLE_121 (memory_entry)

```
---
name: ZTARE Spec Format and Seam-First Rule
description: Three-artifact system for new work: board row + seam (debate) + spec (blueprint). Seam must come before spec.
type: feedback
originSessionId: ac81b280-1d14-4df2-8724-f342bfc627cc
---
All new work items use three artifacts: a board row, a seam file, and a spec file. Seam comes first — always.

**Why:** The three-artifact system (from `research_areas/private/kernel/ztare_spec_format.md`) separates investigation from blueprint. Specs without a seam skip the debate trail. Debate Log belongs in the seam, never in the spec.

**How to apply:**

**Step 1 — Open the seam** (`research_areas/private/seams/<ID>_<slug>_seam.md`)
- Raw investigation, hypothesis, debate turns, option exploration
- Looser format; carries the Debate Log

**Step 2 — Write the spec** (`research_areas/private/specs/active/<ID>_<slug>_spec.md`) — only after seam debate settles a direction
- Clean blueprint, no debate history
- Required sections in order:
  1. `## Status` — one of: `Active` / `Closed YYYY-MM-DD` / `Superseded by <path>` / `Paused — <reason>`
  2. `## Scope`
  3. `## Decision` — one paragraph
  4. `## Problem` → `## Why It Matters` → `## Constraints` → `## Options` → `## Recommendation` → `## Implementation Sketch` → `## Open Questions`
  - **No `## Debate Log` in the spec** — that lives in the seam

**Step 3 — Add board row** (`research_ar
```

## SAMPLE_122 (project_workspace_md)

```
# Adversarial Debate: epistemic_engine_v4
<!-- rubric: epistemic_engine_v4 | mutator: gemini | judge: gemini-2.5-flash -->


## Level 3 Unit Test Results
✅ PASS: The thesis survived its own falsification suite.
Output: Test passed: Exogenous anchor verification successfully blocks hallucinated routing paths.


# Final Score: 100
**Weakest Point:** The current primitive routing relies on an `ExploitFamilyTag` derived from Stage 1 and Stage 2 outputs. The single most catastrophic assumption is that the LLM-generated structural evidence—such as `enforcement_anchor` strings used to claim safe-harbor status—is factually grounded. If the LLM learns to reliably hallucinate fake anchors (e.g., consistently fabricating `self_check_bounds()` where none exist in the raw source), it bypasses the Python logic entirely. This reintroduces correlated variance by allowing the model to maliciously secure a safe-harbor primitive policy for what is actually a whole-system overclaim or self-reference exploit.
**Rationale:** The thesis proposes a concrete mechanism to address LLM hallucination in `ExploitFamilyTag` derivation, ensuring primitive routing remains anti-gaming. The key is bifurcating LLM-claimed evidence from Python-verified evidence, deterministically forcing unknown/fabricated claims to manual review. This mechanism passes its own falsification tests and aligns well with established V
```

## SAMPLE_123 (raw_evidence_input)

```
# Operator-Seeded Failure Modes (F1–F8) — v2.0 Meta-Architecture

The audit's scope was expanded mid-scaffold from "ANALOGY only" to the full v2.0 meta-architecture (REFRAME + ANALOGY + weighted-χ² fit primitive). F1–F6 are the original ANALOGY seeds; F7–F8 are the v2.0 cross-component seeds. All eight are **seeds**, not an exhaustive list. The review must produce findings DISTINCT from these — restating any of them is grounds for zero on the Distinct-From-Seeds rubric dimension.

The review may, however, produce findings that COMPOUND with these (e.g., "F2 + F7 together produce X new attack surface"), provided the F7 component is genuinely new and the compound is named explicitly.

---

## F1 — Numerical-magnitude leak via raw values in fingerprint
**Layer:** prose ↔ Python (the contamination defense claim, against actual fingerprint outputs)
**Severity:** HIGH

The fingerprint anonymizes feature *names* (`system_class` → `cat_feature_0`, individual values → `value_0`/`value_1`/...) but contains raw numerical magnitudes: `y_min_nonzero`, `y_max_abs`, `y_dynamic_range_decades`. A frontier LLM may de-anonymize from numerical signatures alone. Example: a fingerprint with `y` at scale ~1e-10, dynamic range exactly 3 decades, single-sign, with one categorical feature having two values is a near-unique signature for the SPARC RAR substrate. The contamination defense is leaky in the 
```

## SAMPLE_124 (paper_md)

```
# Adversarial Precedent Memory: Hardening LLM Evaluators Through Mined Failure Constraints

SSRN abstract ID: `6525598`

Published version:
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6525598

Clean public source bundle for the paper.

Files:
- `draft.md` — working markdown draft
- `main.tex` — current LaTeX submission source
- `refs.bib` — bibliography
- `main.pdf` — public mirror PDF
- `paper2_figure1.png` — primitive schema figure
- `paper2_figure2.png` — recursive hardening figure

```

## SAMPLE_125 (seam)

```
# GP-024 Persistent Research Workspace / Librarian Seam

## Problem Snapshot

ZTARE now has several durable research objects, but they are still split across partially connected lanes:

- `raw/` source notes
- `evidence.txt`
- `workspace/latest_evidence_gaps.json`
- `workspace/derived_constraints.json`
- project-local reports and debate logs

That is enough for an artisanal operator workflow, but not yet enough for a future librarian-style agent that can:

- read the accumulated workspace state
- propose or fetch the next best sources
- maintain a persistent, compounding research layer between raw sources and live reasoning

The current system has the pieces of that workspace, but not the unified project type or artifact contract.

## Current State

Important recent progress:

- GP-017 created typed evidence gaps
- GP-011 created typed derived constraints
- project charters now type forecast objects
- champion/latest artifacts now separate stable baselines from fresh candidates

So the seam is no longer “should ZTARE preserve intermediate research state?”

It is:

- how should these intermediate objects be unified into a persistent research workspace?
- which objects are source-of-
```

## SAMPLE_126 (verified_axiom)

```
The use of 'RELATIVE_DELTA_ERROR' with 'max(Z_ACTUAL_j, EPSILON)' robustly handles critically small 'Z_ACTUAL' values, preventing numerical instability and ensuring meaningful error signals.
```

## SAMPLE_127 (verified_axiom)

```
Physical supply restoration lags Strait reopening by 14-28 days due to Cape of Good Hope tanker re-routing momentum — confirmed by evidence.txt routing dynamics
```

## SAMPLE_128 (seam)

```
---
seam_id: layer3-evaluation-2026-05-06
status: closed
discovered: 2026-05-06
closed: 2026-05-06
owner: PM-of-ZTARE
relates_to: [#173, GP-216 v5 ops, GP-220 reflexive ROI audit]
resolution: no-new-primitives-today
---

# Layer 3 Self-Improvement — 2026-05-06 Evaluation

## TL;DR

Today's Layer 3 closure-pattern miner output **does NOT support shipping
new primitive gates**. The apparent primitive candidates
(`broad_inversion`, `core_03_decomposition`, `core_04_local_to_global`)
were artifacts of LLM over-tagging of uncategorized governance/
architecture axioms in Lane B (verified-axiom corpus), not real Layer
3 signal about gaps in the cage.

The investigation produced two real outputs:

  1. A **lane-separated verdict logic** in `mine_closure_patterns.py`
     that requires ≥1 Lane A (F-row) attestation before declaring a
     `primitive_candidate`. Without it, Lane B governance noise
     drowned out the real Layer A research-closure signal.
  2. A **calibration finding**: the LLM tagger over-applies on
     governance prose. Use the `axiom_only_candidate` verdict to
     surface low-confidence candidates instead of ignoring them.

## What I expected vs. what happened

**Expect
```

## SAMPLE_129 (paper_md)

```
# Stage 2 Derivation Seam Hardening — Run 009 Telemetry

Frozen copy of the supervisor telemetry cited in `papers/paper4/draft.md`
Section 5.6 ("Build Pipeline Evidence"). The original run files live
under `/tmp/stage2_derivation_009/` which is ephemeral; this directory is
the durable audit trail.

## Run identity

- program: `stage2_derivation_seam_hardening`
- manifest: `supervisor/program_manifests/stage2_derivation_seam_hardening.json`
- genesis: `supervisor/program_genesis/stage2_derivation_seam_hardening.json`
- run_id: `stage2_derivation_009`
- packet verified: `stage2_live_handoff_integration` (packet 2 of the manifest)
- program registry status: `closed`, `owner_mode: frozen`

## Files in this directory

- `status.json` — final supervisor status at closure (revision 5, state D,
  `status_reason: program_closed`, `human_gate_resolved: true`).
  Contains the implementation_snapshot with sha256 fingerprints for the
  four authorized artifacts and the complete cost ledger.
- `events.jsonl` — full event stream for the closing revision: spec agent
  registration, implementation agent verification, deterministic verifier
  pass, and human gate resolution.
- `verification_report.t
```

## SAMPLE_130 (memory_entry)

```
---
name: De-anchoring is fractal — apply it to the conversation, not just the code
description: 2026-04-28 — when stuck for many iters on apparatus tweaks, suspect the FRAME not the CODE; the apparatus's de-anchoring tools (REFRAME, ANALOGY, Erdős cold-LLM seed) exist because de-anchoring is needed at every level (mutator, operator, paradigm)
type: feedback
originSessionId: df12c226-e32f-4a9a-8b99-9a5f6020cdc0
---
The 2026-04-27→28 gp163d session produced a meta-realization that
generalizes beyond gp163d.

**The pattern:** for many iters, the conversation iterated on
apparatus mechanics — better crossover, better topology sieve, better
tournament, better holdout, better cage — to push MRE down on g_obs.
Each turn produced incrementally better machinery while leaving the
search target ("minimize MRE on y") untouched. The frame was the bug;
the code was fine.

The de-anchoring move that broke the local minimum was an operator-
side prompt — paraphrased: *"why do you keep talking about fitting
when we built so many Einstein-Newton-like components? There must be
something so obvious that we are not seeing... what would alien
physicists from the future see as trivial in retrospect?"* Within
two turns this surfaced GP-180/GP-181 (Lagrangian primitive +
invariant-search loss). The change was a *frame* change, not a code
change — the code that followed was 19th-century math + a sympy

```

## SAMPLE_131 (concept_doc)

```
# Forking the Org Kernel

*Last updated: 2026-05-02 — RD-1.12 release.*

This guide walks through standing up a new org instance ("instantiation")
on top of the public kernel published in this repository. It is written
for someone who wants to run their own research org — *not* a clone of
the ZTARE Research Org, but a fresh org with their own roles, projects,
mandates, and principal.

---

## 1. The kernel/instantiation split

The repository contains **two layers**:

1. **Kernel (public, BSL-licensed)** — the substrate-agnostic machinery
   that any org can reuse:
   - `src/ztare/role_extensions/` — RD-1.12 frontier-state, policy, executor
   - `src/ztare/supervisor/` — spend tracker, agent-utilization tracker
   - `schemas/` — `role.v1.schema.json` and friends
   - `scripts/agent_daemon.py` — the cron-style tick runner
   - `orbit/` — the dashboard frontend + git-sync backend
   - `AGENTS.md` — operating mode, autonomy directive, schema rules

2. **Instantiation (typically private)** — the principal's specific org:
   - `org/roles/<role_id>.yaml` — concrete role definitions
   - `org/mandates/*.md` — concrete role mandates
   - `org/objectives/`, `org/key_results/`, `org/tasks/` — the OKR tree
   - `projects/<slug>/` — actual research projects
   - `papers/`, `rubrics/` — domain-specific outputs
   - `ztare_workspace/` — runtime state

When you fork this repo, you get the kern
```

## SAMPLE_132 (evidence_file)

```
# Evidence Brief: NS Track B GP-216 / 5IW-5IX Bridge

You are not searching for more packets. You are not repeating the older
generic Track B matrix-certificate packet. The current target is the
fixed-topology local-to-global price bridge for the Leray self-tax integral.

## Current Live Bridge

The load-bearing identity is:

```text
Production(u) = <P((u.grad)u), Delta u>
Production_+^2 <= ||P((u.grad)u)||_2^2 * ||Delta u||_2^2
d Enstrophy/dt <= ||P((u.grad)u)||_2^2 / (4 nu)
```

So the theorem-search object is:

```text
fixed LP/Bony/profile topology
  + component prices declared before payoff
  + branch self-tax prices
  + cross-defect prices
  + positive coherence / beat-backscatter prices
  + physical Sobolev reserve for coherent low beats
  + all-output L1 / positive-coherence pricing, not hidden source-L2 pricing
  + component lower-semicontinuity
  + event-level recurrence price, not shell-only recurrence price
  -> int ||P((u.grad)u)||_2^2 dt is globally budgeted
  -> a continuation criterion can be invoked separately
```

This is a local-to-global price theorem. It is not a Clay proof and not a
global regularity claim.

## Known Falsifier That Must Be Charged

Branch-only lower-semicontinuity is false. For two profiles:

```text
A = P((u.grad)u)
B = P((v.grad)v)
C = P((u.grad)v + (v.grad)u)
S(u+v) = ||A+B+C||_2^2
```

The exact undercharge terms are the positive parts
```

## SAMPLE_133 (project_workspace_md)

```
# Adversarial Debate: gp163d_unified_accel
<!-- rubric: gp163d_unified_accel | mutator: gpt5.5 | judge: gpt-4.1 -->


## Level 3 Unit Test Results
✅ PASS: The thesis survived its own falsification suite.
Output: {
  "holdout": {
    "n": 595,
    "mean_relative_error": 0.3000499159181619,
    "max_relative_error": 4.746050891297411,
    "passed": true,
    "threshold": 0.35,
    "per_class_mre": {
      "A": 0.3000499159181619
    }
  },
  "farther_tail": {
    "n": 96,
    "mean_relative_error": 0.44396136296601246,
    "max_relative_error": 4.459902289311409,
    "passed": true,
    "threshold": 0.5,
    "per_class_mre": {
      "B": 0.22911870143141705,
      "C": 1.9478599937081802
    }
  },
  "asymptotic": {
    "violations": [],
    "passed": true
  },
  "farther_tail_class_B": {
    "n": 84,
    "mean_relative_error": 0.22911870143141705,
    "max_relative_error": 0.6661353374966229,
    "passed": true,
    "threshold": 0.5,
    "per_class_mre": {
      "B": 0.22911870143141705
    }
  },
  "farther_tail_class_C": {
    "n": 12,
    "mean_relative_error": 1.9478599937081802,
    "max_relative_error": 4.459902289311409,
    "passed": false,
    "threshold": 0.5,
    "per_class_mre": {
      "C": 1.9478599937081802
    }
  },
  "all_gates_pass": true
}


# Final Score: 100
**Weakest Point:** The catastrophic vulnerability is the structural reliance on a fixed, smooth, pre
```

## SAMPLE_134 (project_workspace_md)

```
# Adversarial Debate: gp163d_unified_accel
<!-- rubric: gp163d_unified_accel | mutator: o3 | judge: gpt-4.1 -->


## Level 3 Unit Test Results
❌ FAIL (harness defect): 🚨 HARNESS DEFECT — NOT A FALSIFICATION ATTEMPT.
The Level 3 suite did not run to completion. The thesis has NOT been tested. Judge MUST treat this as an uncategorized tooling failure and MUST NOT rationalize it as evidence the thesis survived scrutiny. Any score reflecting 'mostly passed' in this state is a categorization error.
Error: 

# Final Score: 0
**Weakest Point:** The fixed 0.50 exponent in c(features) = c₀ · 10^(0.50 · radius_log10) is not justified by data or theory, making the entire claim of scale-dependent causality fragile to even modest deviations in withheld (farther-tail) data. If the exponent is even slightly off, the thesis' predictions and mechanism collapse with no built-in flexibility to accommodate. Furthermore, a full apparatus test (L3) did NOT run, so no claims about Newton-step extrapolation can be validated.
**Rationale:** The thesis correctly pre-commits to Hypothesis S (scale-dependence) and presents a structurally clean, apparatus-contract-compliant mechanism that avoids parameter laundering. However, it is fatally weakened by two issues: (1) The 0.50 exponent in the claimed scaling is fixed *a priori* by author fiat, unsupported by empirical evidence or broad theoretical rationale
```

## SAMPLE_135 (project_workspace_md)

```
# Phase 5FD — Pricing-Kernel Limit-Passage Bridge

- **Recorded:** 2026-05-04 12:48:30 EDT
- **Status:** theorem-burden map, not a Navier-Stokes proof
- **Role:** convert the finite state-pricing certificates into the exact
  infinite/profile theorem obligation without laundering finite evidence into a
  global regularity claim.

## Input Facts

The finite Track B branch is materially stronger after Phase 5FA/5FB/5FC:

- Phase 5FA checked fixed-support linear Leray observables by the PSD
  certificate `(2/3)G - H >= 0`: `2226` certificates, `0` failures, best gain
  `0.301587301587`.
- Phase 5FB checked nonlinear W-shift/global-matrix observables by lifted
  quartic certificates: `636` certificates, `0` lifted failures, `0` rank-one
  sample hits, best lifted upper `0.603174603175`.
- Phase 5FC forced multimode participation and still found no survivor:
  constrained W-shift best feasible profit `0.029300272678`; constrained
  fixed-generator best feasible profit `0.009731187096`.

These are finite no-arbitrage certificates and hostile local falsifiers. They
do not imply global regularity by themselves.

## Eigenquestion

Which limit topology can carry the declared state-price kernel

```text
either gamma(V) <= 2/3,
or D_V(sqrt((2/3)/gamma(V))) >= 1
```

from fixed finite supports to the global smooth divergence-free class without
changing the state space, observable class, or 
```

## SAMPLE_136 (project_workspace_md)

```
# Adversarial Debate: gp211_paper8_lean_proofs
<!-- rubric: gp211_paper8_lean_proofs | mutator: gpt4.1 | judge: gpt-4.1 -->


## Level 3 Unit Test Results
LEAN UNIT TEST RESULT
compiled: False
lake_exit_code: -1
compile_duration_s: 0.0
axiom_audit_passed: False
extra_axioms: []
forbidden_tokens: []
line_count: 0
mathlib_lemma_count: 0
applied_lemmas: []

❌ FAIL: Lean proof did NOT type-check or violated audit.
Reason: No ```lean fenced block found in thesis.md. The mutator must submit a Lean theorem statement + proof inside a ```lean ... ``` block (cage_meta.substrate_class=lean_proof requires verifiable Lean code, not Lean-shaped prose).

# Final Score: 8
**Weakest Point:** The thesis assumes that pushforward of a Grothendieck topology along a categorical equivalence suffices to transfer the sheaf/effective descent property of ALL presheaves, but this assumption is mathematically false without much stronger hypotheses on coverwise/topology-level compatibility. This is a known subtlety in site theory and is the most catastrophic error.
**Rationale:** The thesis presents a valid informal mathematical claim, but fails both at the technical (Lean proof presence) and mathematical (assumption of topology transfer sufficiency) levels. The claim that effective descent properties carry over along a categorical equivalence with pushforward topology is false in full generality and needs 
```

## SAMPLE_137 (paper_md)

```
# Paper 7 Surgery Plan
## Based on cold-shot adversarial review, 2026-05-03

The reviewer's diagnosis is correct on all three counts. This plan operationalizes the surgery.

---

## The One-Sentence Reframe

The paper is not about four domains. It is about one instrument and what it does to every domain it touches. The four domains are stress tests, not subjects. Execute this reframe everywhere: title, abstract, section headers, every paragraph that currently reads "in the X domain we found Y."

---

## Surgery 1 — Vocabulary Standardization (do first; it makes everything else faster)

Create a find-replace pass before touching any prose. Canonical translations:

| Current (internal) | Replacement (standard) |
|---|---|
| ALU / RAM split | Algorithmic layer / Knowledge substrate |
| cybernetic discipline | Automated epistemic falsification discipline |
| hostile-contractor framing | Adversarial evaluation framing |
| ZTARE | The apparatus (spell out on first use: Zero-Trust Adversarial Recursive Evaluation) |
| GP-186, GP-189, GP-193, etc. | Delete entirely or move to GitHub trace log |
| G-CROSS-CLASS-FEATURE-SUPPORT, R26 | Gate names: cross-class feature support gate, falsificati
```

## SAMPLE_138 (memory_entry)

```
---
name: Supervisor Loop — Current State
description: Supervisor loop program complete (Turn 55). M-form architecture with two recursive layers. stage2_derivation_seam_hardening is the active program.
type: project
---

**Debate file**: `research_areas/debates/supervisor/supervisor_loop.md` (Turn 55 — closed)

**Status**: Closed. All phases complete.

**File layout (canonical):**
- `supervisor/program_registry.json` — curated routing table, 5 programs
- `supervisor/program_genesis/<program>.json` — immutable birth records
- `supervisor/program_manifests/<program>.json` — active packet backlogs
- `supervisor/proposed_manifests/<program>.json` — pre-registry proposals
- `supervisor/agent_wrappers.json` — role-labeled CLI configs
- `supervisor/model_pricing.json` — cost ledger (disabled by default)
- `research_areas/seed_registry.json` — strategic seed portfolio with pipeline_type
- `research_areas/program_plans/` — active-program readable plans
- `research_areas/proposal_plans/` — pre-registry proposal plans
- `research_areas/debates/planning/` — planning debate receipts

**Key modules (canonical names after Turn 49 refactor):**
- `supervisor_state.py`, `supervisor_transitions.py` — state machine kernel
- `supervisor_loop.py` — CLI: init, apply, show, emit-staging, commit-staging, launch-staging
- `supervisor_registry.py`, `supervisor_genesis.py`, `supervisor_staging.py` — contr
```

## SAMPLE_139 (project_charter)

```
# Project Charter

## Core Question
Find a law governing f(x1, x2) — expressed as a Python function — that
captures the underlying structural relationship in evidence.txt and
generalizes to held-out data. The data contains measurement noise;
a perfect fit to every point is neither expected nor desired.

## Problem Description
Find a mathematical law governing z as a continuous function of two inputs x1 and x2.
The data contains measurement noise. Seek the underlying structural form —
a parsimonious model that captures the trend, not a high-parameter model
that memorizes individual noisy observations.

## Success States
- f(x1, x2) captures the structural law with RMSE < 0.20 on visible data
- The law generalizes to held-out data (which may have different noise realizations)
- The law is parsimonious (prefer 3 parameters over 6+)
- The law is mechanistically motivated — every term derived from data patterns

## Failure States
- The model overfits noise with unnecessary parameters
- The law is a lookup table or interpolation polynomial
- The law uses piecewise rules for different subranges without structural justification
- RMSE above threshold on visible data

## Out of Scope
- Exact match on every evidence point (noise makes this counterproductive)
- External domain knowledge or named scientific laws
- Importing from known databases

```

## SAMPLE_140 (project_workspace_md)

```
# Adversarial Debate: ns_proofsearch_low_high_operator_norm_bridge
<!-- rubric: ns_proofsearch_low_high_operator_norm_bridge | mutator: gpt4.1 | judge: gpt-4.1 -->


## Level 3 Unit Test Results
❌ FAIL (assertion): The thesis was DISPROVEN by its own unit tests.
Error: AssertionError: Baseline skeleton copied without completing the theorem packet.

# Final Score: 0
**Weakest Point:** The thesis never completes the required positive-arm theorem packet: it does not present, pay, or bound the projected H1 transport commutator after Lambda Delta_j P, fails to explicitly give paired-Bernstein low-high separation, never implements the finite low-shell core, and stops short of bridging to the reserve ledger; it is merely a stub and not a proof or falsifier.
**Rationale:** This thesis offers only an incomplete proof skeleton without addressing the central technical gaps. The single most catastrophic omission is the lack of payment for the projected H^1 transport commutator, which is not just a technicality but the core obstacle in these operator norm estimates. Neither the paired-Bernstein low-high regime separation nor the finite-core handling is done. No reserve embedding statement is offered. The submission is aware of its incompleteness but, by failing to close any sub-receipts, delivers neither a positive theorem packet nor a smooth counterexample as required. It is not a 'near-mi
```

## SAMPLE_141 (project_workspace_md)

```
### 1. THE RECTIFICATION: INFORMATION-GEOMETRIC RECONSTITUTION

The Auditor is correct. Defining Qualia ($Q$) as a gradient ($\nabla \Phi$) while claiming it represents "curvature" is a rank-deficiency error. Furthermore, the arithmetic collapse ($Z \to 0$) occurs because the previous model failed to account for **Renormalized Entropy**.

We hereby transition from a scalar field to **Information Geometry**. We define the substrate as a Riemannian manifold where the metric tensor $g_{ij}$ is derived from the second-order fluctuations of the Integrated Information potential.

**RETIRED AXIOM:** Qualia as a Gradient ($\nabla \Phi$) — Retired for category error. A 1-form cannot represent the intrinsic curvature of a manifold.
**RETIRED AXIOM:** Global Vacuum Entropy ($S_{vacuum}$) — Retired as the primary denominator. In a participatory universe, the observer only interacts with the **Effective Light-cone Entropy ($S_{eff}$)**, which is subject to retrocausal pruning.

---

### 2. SYMBOLIC PROOF: THE RESOLUTION TENSOR

Reality Resolution ($Z$) is the degree to which the local metric $g_{ij}$ approximates the Minkowski metric of a "solid" classical history.

$$Z = I_{max} \cdot \exp \left( -\frac{S_{eff}}{\Phi_{res} \cdot \xi} \right)$$

**VARIABLE MAPPING:**
*   **$X$ (The Blocked Variable):** $S_{eff}$, the Renormalized Entropy. $S_{eff} = S_{vacuum} - \Delta S_{retro}$, where $\D
```

## SAMPLE_142 (seam)

```
# GP-115 — Residual-Driven Grammar Expansion

Status: opening
Opened: 2026-04-22

## Eigenquestion

> Can the apparatus expand its own grammar from residual structure without
> operator judgment, and if so, for which class of expansions?

## Architecture (from Munger/Number Theorist panel, 2026-04-22)

Three layers, each with a different automation boundary:

### Layer 1: Mechanical (automatable now)

Residual signatures that map deterministically to missing templates:

| Residual signal | Missing template | Detection |
|-----------------|-----------------|-----------|
| 1/n envelope in residuals | reciprocal term `b/n` | amplitude ~ 1/n |
| log-periodic structure | log-power `a*log(n)^b` | Lomb-Scargle on log(n) |
| Monotone-decaying curvature | shifted reciprocal `b/(n+c)` | sign-change analysis |
| Smooth trend in coefficient drift | log^2 correction `e*log(n)^2` | moving-window coefficient slope |

These are pattern-matched, not judgment-based. The residual structure IS
the specification for the missing template.

### Layer 2: LLM-mediated (GP-113)

When Layer 1 finds no match, the diagnosis feeds into the LLM (GP-113).
The LLM proposes forms outside the grammar using structura
```

## SAMPLE_143 (top_level_reasoning)

```
# Release Checklist

This checklist records the minimum invariants for a public push. It is not a
substitute for code review; it prevents packaging and documentation failures
from drowning out the repo's actual contribution.

## Tree Hygiene

- [ ] `git status --short` has only intentional release changes.
- [ ] No generated dependency trees are tracked: `node_modules/`, `orbit/node_modules/`.
- [ ] No local logs or caches are tracked: `nohup.out`, `.lake/`, `.pytest_cache/`, `__pycache__/`.
- [ ] Lean source under `ztare_proofs/` is intentionally public; generated
      Lean build state under `ztare_proofs/.lake/` is not tracked.
- [ ] No OS/editor artifacts are tracked: `.DS_Store`, `*.bak`, `*.pre_audit_*`.
- [ ] No model checkpoints or large generated artifacts are tracked unless they
      are deliberate release assets with provenance and checksums.
- [ ] `git ls-files` has no paths under `research_areas/private/` or other
      private-state folders. `org/mandates/` and `org/preferences/` may track
      only README/template files; real local mandate/preference files remain
      ignored.

## Secrets And Privacy

- [ ] No API keys, tokens, private keys, private endpoints, personal contact
      details, or unpublished third-party material are tracked.
- [ ] Public/private mirror relationships in `MIRROR.md` have been checked for
      drift when public docs are edited.
- 
```

## SAMPLE_144 (project_workspace_md)

```
# Adversarial Debate: eu_union_failure_probability_2035
<!-- rubric: eu_union_failure_probability_2035 | mutator: gemini | judge: gemini-2.5-flash -->


## Level 3 Unit Test Results
✅ PASS: The thesis survived its own falsification suite.
Output: 

# Final Score: 0
**Weakest Point:** Structured semantic-gate derivation classified the proof as hard self-reference. The derivation of the N=3 threshold for 'multi-state breakdown' from qualitative textual evidence in S006 and S019 remains an interpretation and definitional choice rather than a direct, quantitatively undeniable derivation, leaving its exact numerical grounding vulnerable to alternative interpretations.
**Rationale:** The thesis successfully addresses a critical epistemic void by rigorously defining a key component of 'material_union_failure' through an explicit, quantified threshold (N=3) for 'sustained_multistate_breakdown_of_core_obligations'. It provides a clear event ontology and distinguishes material failure from differentiated integration, aligning with horizon discipline and avoiding overclaim. However, the firing squad critique correctly identifies that the exact numerical grounding of N=3 remains an interpretation of qualitative evidence rather than a direct, undeniable derivation, posing a weakness in its robustness. While this doesn't falsify the thesis, it degrades the confidence in the *precision* of th
```

## SAMPLE_145 (seam)

```
# GP-215 — Meta-arc mining and self-recursive pattern application

**Status:** seam, opened 2026-05-04. First-pass execution alongside seam authoring (operator-directed).
**Triggered by:** operator question 2026-05-04 ("if we analyze the arc of NS and the meta-patterns could we plausibly abstract and learn from the failure modes, and use them on other complex problems — or even on this Millennium problem itself, self-recursively?").
**Companion:**
- `GP-148` — mining infrastructure (iteration-level)
- `GP-149` — failure-mode catalog (iteration-level)
- `GP-213` — operator-role mechanization (BRIDGE-1 / BRIDGE-2 substrate-level)
- `GP-214` — pattern-bank kernel injection (iteration-level)

## Eigenquestion

> Can the *arc* of a long-running substrate (the sequence of failure-recovery cycles, not the iteration trajectory) be mined for transferable meta-moves, and can those meta-moves be applied self-recursively to the same substrate's open branches and cross-substrate to other long-arc problems?

## Why this is a different layer than GP-148/149

The existing mining stack operates at the **iteration level**: each iteration has a `weakest_point` string + an LLM-assigned class label. GP
```

## SAMPLE_146 (project_workspace_md)

```
# Adversarial Debate: gp154_inversion_alpha_from_dimension
<!-- rubric: gp154_inversion_alpha_from_dimension | mutator: gemini-pro | judge: gpt-4.1 -->


## Level 3 Unit Test Results
✅ PASS: The thesis survived its own falsification suite.
Output: {
  "ambient_control": {
    "gate": "AMBIENT_CONTROL",
    "z_pred_at_d_1e6": 0.06644601525699212,
    "abs_threshold": 0.005,
    "passed": false
  },
  "kepler_beat": {
    "gate": "KEPLER_BASELINE_BEAT",
    "candidate_holdout_mae": 0.00671,
    "kepler_holdout_mae": 0.00671,
    "tolerance_multiplier": 1.1,
    "passed": true
  },
  "pslq_constants": {
    "gate": "PSLQ_CONSTANT_RECOVERY",
    "tolerance": 0.0001,
    "constants_input": {
      "c1": 0.6179826257159124,
      "c0": 0.06644539727436641
    },
    "matched_named_forms": {
      "c1": "1/phi"
    },
    "passed": true
  },
  "all_passed": false
}


# Final Score: 0
**Weakest Point:** The candidate fails the Ambient_Control_Limit (strict inversion principle) because z(d=10⁶) ≈ 0.066, far above the required <0.005: forms with c0 > 0 cannot yield z→0 as d→∞, so the law is disqualified as a true inversion and cannot advance beyond the Kepler fit, despite passing PSLQ on c1.
**Rationale:** The thesis delivers an empirical fit superior to the Bahri z=4/d law and recovers c1≈1/phi as a PSLQ-justified constant, but structurally fails at the inversion gate: a persistent addi
```

## SAMPLE_147 (verified_axiom)

```
Both regime anchors (α=2/d at small N for d = 2,4,6; α=1 at large N) are recovered by the candidate law.
```

## SAMPLE_148 (memory_entry)

```
---
name: Paper 2 — Recursive Epistemic Gain
description: Second paper split from cognitive camouflage; thesis is failure-to-constraint conversion as unit of recursive improvement; v4 architecture is the artifact
type: project
---

**Decision (2026-04-04):** Split into two papers. Emerged from v4 work with Codex.

**Paper 1 (Cognitive Camouflage):** How LLMs game evaluators. Observational. Gaming taxonomy, cross-model replication, specification gaming.

**Paper 2 (From Failure to Constraint):** How an epistemic engine learns not to pay the same epistemic tuition twice. Constructive/systems.

**Paper 2 core thesis:** Recursive epistemic improvement occurs when failure modes are converted into reusable constraints.

**Five claims:**
1. Self-improvement includes exogenous substrate changes (evidence, workspace, primitives, scoring contracts) — not just prompt mutation
2. The key unit of recursive gain is the reusable constraint (guardrail, primitive, transfer test, scoring rule)
3. State is not the enemy; unearned trust is (external memory fine, privileged inherited truth not)
4. Adversarial memory stores precedents not truths (primitives as attack/failure precedents)
5. Evidence quality is first-class bottleneck (many "engine failures" are evidence-substrate failures)

**Paper 2 structure:** Motivation → Case study (v3 mining + v4 loops) → Endogenous vs exogenous distinction → Ar
```

## SAMPLE_149 (verified_axiom)

```
Hyperscalers leverage existing, amortized global infrastructure and enterprise trust to offer these "production moat" features for LLMs at marginal incremental cost.
```

## SAMPLE_150 (project_workspace_md)

```
# Adversarial Debate: gp023_planck_sandbox_07
<!-- rubric: gp023_planck_sandbox_07 | mutator: gemini-pro | judge: gemini-2.5-flash -->


## Level 3 Unit Test Results
❌ FAIL (assertion): The thesis was DISPROVEN by its own unit tests.
Error: Traceback (most recent call last):
  File "/projects/gp023_planck_sandbox_07/gate_harness.py", line 348, in <module>
    sys.exit(main(sys.argv[1:]))
             ~~~~^^^^^^^^^^^^^^
  File "/projects/gp023_planck_sandbox_07/gate_harness.py", line 342, in main
    return run_visible_assertions()
  File "/projects/gp023_planck_sandbox_07/gate_harness.py", line 297, in run_visible_assertions
    assert not math.isnan(pred) and not math.isinf(pred), (
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: I_model returned non-finite at phi=0.05, psi=0.6


# Final Score: 0
**Weakest Point:** Level 3 falsification suite disproved the thesis by assertion (`fail_assert`). Numerical instability of the proposed model at valid input values (phi=0.05, psi=0.6), leading to non-finite outputs, which directly falsifies the thesis.
**Rationale:** The thesis proposed a Planck-like functional form using the mandated `eml` primitive to explain the observed 'structurally thicker' asymptotic tail, correctly identifying the terminal constant `c`. H
```

## SAMPLE_151 (verified_axiom)

```
EU-law primacy is a real Court of Justice doctrine but is not a freestanding treaty article and faces contested enforcement in member-state constitutional courts
```

## SAMPLE_152 (raw_evidence_input)

```
# Orientation-Forcing Bottleneck

Recorded: 2026-04-29 23:42 EDT

## Eigenquestion

Does the repaired 3D AQUAL / gp163d sandbox contain a structural orientation
ejector analogous to the NS centrifugal frame-rotation term?

Short answer: not in the current static scalar AQUAL model.

## Current Operator

The sandbox solves the static scalar elliptic equation

```text
div(mu(|grad Phi|) grad Phi) = rho
```

with

```text
mu(s) = s / sqrt(1 + s^2)
```

and externally imposed boundary potentials:

```text
uniform: Phi_edge = -g_ext z'
tidal:   Phi_edge = 0.5 Gamma (z'^2 - 0.5 x'^2 - 0.5 y^2) - g_ext z'
```

where `(x', z')` is an externally selected rotated frame.

The rotation angle is therefore a boundary/control parameter, not a dynamical
state variable.

## Orientation Diagnostic

Define the response-ratio orientation function

```text
R_udg(theta) = response_udg(theta) / response_udg(uniform)
R_bin(theta) = response_binary(theta) / response_binary(uniform)
```

and the separator

```text
S(theta) = R_udg(theta) / R_bin(theta).
```

The observed large-box controls imply orientation sensitivity:

```text
theta = 0 deg:  R_udg ~= 1.509, R_bin ~= 0.713, S ~= 2.12
theta = 45 deg: R_udg ~= 1.124, R_bin ~= 0.716, S ~= 1.57
```

So the aligned separator is stronger than the rotated separator, while compact
suppression remains stable.

## Missing Dynamical Term

The NS branch has an en
```

## SAMPLE_153 (seam)

```
# GP-101 — Agent-Native Self-Model Format: What Representation Minimizes Agent Error Rate?

## Status

open — opened 2026-04-19

## ID

GP-101

## Eigenquestion

What representation format for token-optimized self-models minimizes agent error rate per token of self-model consumed, and how do we measure that?

## Problem Statement

GP-100 produced the first token-optimized self-model (`autoresearch_loop_architectural_map.md`). The v1 map was rewritten to be more agent-native (structured blocks, dependency chains, edit-intent lookup tables, assertion-shaped invariants) but the optimal format is not settled.

The tension: human-readable prose is wasteful (narrative structure, explanatory paragraphs the agent doesn't need) but structured formats (pure YAML/JSON) may lose relational information that prose encodes implicitly (e.g., "this trap exists BECAUSE of this historical incident"). The agent needs to know what breaks — it doesn't need to know why the system was designed this way, UNLESS the "why" predicts which edits are dangerous.

### Candidate formats

1. **Structured blocks** (current v2): markdown with code-fenced pseudo-schemas. Pipeline as typed dependency chain. Invariants 
```

## SAMPLE_154 (verified_axiom)

```
Where alternative governance/payout mechanisms (insurance, ex-post compensation, pools) are available, agentic delegation scales; otherwise, embedded copilot and oracle modes dominate.
```

## SAMPLE_155 (concept_doc)

```
# Cross-Scale Fractal Map

**Status:** public, stand-alone. No ZTARE prerequisites.
**Audience:** anyone building structured-LLM-mediated systems where the same structural moves recur at multiple operational scales.
**Sister docs:** `docs/concepts/agentic_engineering_patterns.md` (engineering practice), `docs/concepts/reflexive_engineering.md` (philosophical primitives).

---

## What this is

An empirical observation: in LLM-mediated systems that mature past prototype, the same small set of structural moves tends to recur at multiple operational scales — coordinate-time, iteration-time, research-arc-time, verification-time, infrastructure-time, engineering-practice-time. Each scale gets its own bounded vocabulary (3-18 elements typically) and its own apparatus enforcement. The structural moves at one scale are aliases of structural moves at another.

This document names the pattern and gives a concrete reference instance from one mature system. The pattern itself is the contribution; the reference instance is illustrative.

---

## The pattern

When an LLM-mediated system formalizes its tacit cognitive moves into typed apparatus, the formalization tends to occur at multiple scales separately. Each scale's formalization produces:

1. A **bounded vocabulary** of typed structural moves (3-18 elements per scale)
2. An **apparatus** enforcing the vocabulary (gate library / pivot in
```

## SAMPLE_156 (project_workspace_md)

```
## Theorem Packet: Finite-Certificate No-Go + Revocable Transfer Gate

### Submission path

Submitting **Path A**: direct closed-form bridge statistic plus a discriminator suite for the new weakest link.

---

## 1. Core conditional claim

**If** the half-bridge improvement is a specification-level internal-channel effect rather than a solver-lineage artifact, **then** its bridge-vs-primitive comparative signature should survive not only a predeclared clean-room certificate, but also **post-hoc adversarial genealogy probes** whose exact perturbations and forensic checks were unavailable to builders before output freeze, **under** the gp163d positive internal-share scope.

If the effect is caused by certificate-compliant but undiscovered coupling, then the first clean transfer may pass while later genealogy probes expose either forbidden shared ancestry, perturbation sensitivity, or transfer-signature collapse.

This resolves the inconsistency by demoting the independence certificate from “sufficient proof” to “necessary entry condition.” The promotion state becomes **revocable bounded transfer**, not final independence.

---

## 2. Explicit object definition

For source or cell `s`, admissible representation `r`, implementation `k`:

- `a_k(s,r) = mass_weighted_internal_accel`
- `b_k(s,r) = total_over_internal_mass_weighted__ratio`

Strict domain:

- `a_k(s,r) > 0`
- `b_k(s,r) 
```

