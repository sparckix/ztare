# Taste Rater — Context Primer

This primer is given to a contextualized rater BEFORE rating samples. It establishes 'what this codebase considers load-bearing.' The rater uses this as the anchor for distinguishing domain-significant insights from generic-looking ones.

**Use this only to anchor scoring relative to the codebase's own structure. Do NOT use it to recognize specific samples and score them higher because they're familiar.**

---

## Load-bearing seams (top by in-degree from reference graph)

These seams are most-cited by other apparatus artifacts. They represent the structural infrastructure of the codebase. An artifact that materially extends or refutes one of these is paradigm-shifting for this codebase (score 5).


## Operator-curated memory entries

These are the operator's distilled lessons across the project's lifetime. Each is what the operator wanted to remember. An artifact that surfaces a NEW lesson at this level of generality is high-quality.

- **Do recursive work yourself; agents for adversarial only 2026-05-16**: do depth-n reasoning/math/construction DIRECTLY in-thread; reserve Agent dispatch for (1) adversarial kill of my own work (the only real independence benefit) or (2) genuine divide-and-conquer; don't outsource forward work I can do — gate [5] = me + one adversarial agent, not outsourced generation
- **Taste-rating canonical = contextualized rater 2026-05-16**: reflexive-mining/taste primary rater is CONTEXTUALIZED/warm (rater_id cold_subagent_contextualized, 154-entry series); cold + cross-family are CONTROLS only; aggregate_taste --rater-id defaults to cold_subagent & pools all raters → ALWAYS pass --rater-id; read docs/concepts/reflexive_mining_methodology.md before any reflexive run
- **Don't patch the checker to pass the current task 2026-05-16**: linter/gate mis-scopes current artifact → record verdict transparently (artifact-scoped), do NOT patch checker so current outputs pass (overfit/gaming); real fix = structural not lexical, separate reviewed change, regression-checked vs real laundering. Operator caught a lexical disclaimer-marker hack ("Clay overfits no?")
- **Buried-prescription point-fix treadmill 2026-05-16**: recurring class: prescribed moves land non-forcing (candidate sub_class/pointer/memory), repaired only by reactive bespoke blocks (point-fix IS the anti-pattern); + menu catch-22 (candidate hidden→never used→never promoted, 40/51 dead, 8 PROMOTE-READY at N=4-38 the moment a reader wired). Fix generatively: validate_prescription_surfacing.py (coverage+promotion loop) as post_tick GAP-E; confidence=trust-weight not visibility gate; evidence-driven promotion; 3-source audit before any fix
- **Banned AI-prose phrases 2026-05-16**: operator (AGENTS.md top): never use "load bearing", "it's not X; it's Y", "real work", "lands hard" or that AI-prose family, internal OR external; scan+rewrite plainly before sending
- **Discipline verdict is artifact-scoped not idea-scoped 2026-05-16**: Tier-3 laundering verdict = artifact framing ONLY, never idea validity; never settle a scientific negative from it or from one attack-only adversary; linter RC-A guard + ANTI-PATTERN-014 sub_modes added; pattern_catalog.yaml unaffected (generated from org/patterns/ only)
- **experiment-loop apparatus debt 2026-05-15**: scripts-reorg broke experiment-loop REPO-WIDE (lean_proof_gate stale verify_lean_stub path, crashes iter-1; FIXED); stale Makefile validator/seal/eigenq paths → run canonical validators directly + VALIDATE_RUBRIC=0; make seal Phase-3.5 is numeric-only, incompatible w/ qualitative audits (gp169 proof) — set cage_meta.class:audit, don't fabricate numbers
- **Solver pessimism OVERCLAIMED (Meta-Darwin) 2026-05-16**: operator-forced Meta-Darwin: my "GP-225 settled, not a (meta-)solver" = category error conflating retrospective-mined-prior-impossibility with the WIRED forward generate-and-govern loop (route_c_layer_2c_dispatch); generator ran 0/10 only on natural-Mathlib (where emptiness theorem predicts 0); discriminating experiment = escape-route ablation, cheap+bounded+NOT run; constraints survive (forbidden atom, ratifier bottleneck); stop asserting settled-negative
- **Isolate-and-defer is itself laundering 2026-05-16**: Tier-3 3/3 methodology catch: naming an OPEN input + conditional implication + "forwarding" = PATTERN-026 face-saving regardless of honest framing; once isolated only measure/discharge, ONE flat prose no-progress, or external dispatch — never another reduction tick; refined into META-PATTERN-024 HARD GUARD
- **Catch validator dead path-bug 2026-05-15**: SOX-analog catch_ledger validator silently FATAL-dead (wrong LEDGER_PATH) since ≥2026-05-09; resurrected → 297 integrity errors/131 rows; pre-2026-05-15 "ratified catch tally" was never integrity-checked; ledger remediation = pending operator policy (do NOT auto-rewrite append-only audit ledger / null concurring_agent)
- **Two RD discovery channels + mechanization principle 2026-05-15**: orchestration_menu.yaml is HAND-AUTHORED (verify by grepping writers before claiming generated) + a SEPARATE RD precheck channel from architecture_index; register in BOTH; menu sub_class routing was dead-at-precheck (deepened 2026-05-15); hand-author only irreducible judgment, mine ledger-derivable facts (graph.yaml surfaced_catch / impact_factor)
- **arXiv poll + cross-field isomorphism 2026-05-15**: periodic arXiv polling is standing process (was missing); closing insight may come from another field via language-isomorphism: abstract frontier to operator-seam, find field where seam is solved (e.g. heat-kernel off-diagonal for div-free fields ↔ NS Leray-CZ), transport structure, predict+falsify, never cite+launder
- **Strict-margin perennial atom**: route-1 NS closure has ONE genuine open atom since 2026-05-12 (produce defectBudgetStrictMarginCertificate ratio<1 from PDE, not adapter); rediscovered ≥4× under drifting vocabulary; scaling is exactly critical so needs sub-scaling gain; do NOT re-derive (forbidden 2026-05-12)
- **Amnesia basin exists — run precheck first 2026-05-15**: the NS graph-basin is built & fresh (6991-node artifact graph + precheck scripts + PATTERN-024); amnesia is a PROCESS failure (precheck not run before ticks), not infra; read AMNESIA_BASIN_ENTRYPOINT.md at session start, run ns_scientific_amnesia_precheck before any new NS tick
- **Don't pre-concede MISSING_HYPOTHESIS 2026-05-15**: push the reduction 1-3 concrete steps harder (Hölder/Chebyshev/CZ/scaling) before declaring any residual open; self-audit own Lean encodings for vacuous quantifiers/trivially-true Props first; recurring pessimism pattern operator flagged ≥3×
- **Scientific amnesia in Route C work 2026-05-15**: operator-surfaced: I built proof_route_fingerprint v1/v2/v3 + §4 validation from scratch without checking existing infra; 14 directly-pluggable v22-v30 components already existed (structural/statistical_fingerprint.py, mathlib_graph.json, v28B node2vec embeddings, lean_tactic_hammer/fast_compile, gnn_v31/v41, two_cultures, universal_classifier); PATTERN-024 scientific_amnesia_precheck was available but not dispatched under corrective-bias pressure; v35 §4 reached 3/5 joint-pass folds with kernel reuse from v28B
- **Parallel-agent linter convergence 2026-05-15**: two Claude agents independently shipped complementary linter checks into same file: this session added Tier-1.7b architecture-component check (markdown seams); parallel NS agent added Tier-1.7 alpha-rename-invariance (Lean theorem files w/ Mathlib-shell composition decoration). Both coexist without overlap. Tier-2 + Tier-3 PATTERN-026 validated with 3/3 cross-provider consensus on GP-235 v1; counts discriminate dead-vs-revised even though headline verdict doesn't.
- **Linter ⇄ PATTERN-026 convergence 2026-05-15**: 3-tier discipline linter (deterministic / gpt-4.1-mini semantic / multi-provider cross-val) now supports architecture-laundering audit via --check-type pattern_026; calibration on 5 seams PASS (3/5 AUTOMATIC, positive control fires 6/7 layers); menu architecture_drafting sub-class points at mechanical dispatch commands
- **Recursive over-architecting failure mode 2026-05-15**: session 2026-05-15: I wrote 3 sequential architectures, all caught by external audit not in-artifact self-audit; corrective: pre-flight Meta-Darwin BEFORE architecture is load-bearing + structural-not-lexical triggers + primitive-first sequencing + commit-to-retract not name-the-limitation + external-reviewer pass on top of Meta-Darwin; in-artifact self-audit is necessary but insufficient
- **Epistemic-hygiene cross-domain bundle 2026-05-15**: epistemic_hygiene_bundle (28 entries: L1+L3 substrate-agnostic, MD+JSON+JSONL, schema v1.0) shipped externally for CONOP/Palantir-style tools; validates L1+L3 transfer cross-domain while L2+L4 stay substrate-specific. One-shot ship: packaged `epistemic_hygiene_bundle.zip`, removed from the tree; regenerate from native `org/` catalogs if needed for another recipient.
- **GP-225 Munger-inversion premortem + Munger compression test 2026-05-15**: operator+GPT-5.5 premortem: 10 failure modes + 10 kill criteria + harness vs solver-0 success criteria; load-bearing Munger compression: "what would survive if adversary reran with current LeanHammer + no oracle + fixed budgets + DAG dedup + replay from scratch?" every claim must pass this BEFORE persisting
- **GP-225 Route C proof-composition harness reframe 2026-05-15**: operator reframe after Meta-Darwin killed 4/6 v28-v29 claims; retire GNN lemma-ranker; promote Route C as Lean proof-composition harness; build v30 30-row hammer-open composition benchmark; rigorous moat-grade definition (proof DAG fingerprint not text); solver-0 gate ≥15/30 hammer-open closures; row-class taxonomy mandatory
- **GP-225 v28-v29 PARTIALLY RETRACTED 2026-05-15**: first moat-grade chain after 5 negatives; 15 LLM-mediated proofs across 3 of 4 rich-arithmetic OPEN rows; LeanHammer Carleson R@1=60% (paper claim 0% obsolete); moat moved from retrieval to composition; row-class boundary identified (rich-arithmetic vs definition-bound); audit relaxed to paper-metric per arXiv:2506.07477
- **GP-225 v27 premise-enum-then-exact zero moat-grade 2026-05-15**: 0 moat-grade closures across 240 exact-tests on 3 single-lemma-exact moat-surface rows (0162/0163/0329); unique closer IS gold lemma or @[simp]/@[fun_prop]/@[grind] sibling that blind-exclude+filter removes; cloud premise selector quality VALIDATED (top-1 for 0163 is gold lemma); 5th sharp-calibration chain; route question for v28 (multi-step rw / refine / boundary accept / class pivot)
- **GP-225 v26 LeanHammer baseline moat surface 2026-05-15**: operationalized moat surface = 9 of 12 canonical-train OPEN rows hammer-resistant (0021/0025/0121/0126/0162/0163/0180/0279/0329); 3 closures all fail 4-way audit (2 tautological apply-original, 1 indirect-leakage simp_all-only); FIRST actionable moat target list for v27+ harness; v4.29.0 sandbox preserved
- **GP-225 v24 deterministic-cascade calibration 2026-05-15**: pure-tactic cascade closes 3/15 canonical train rows at calibration-grade, 0/15 at moat-grade after indirect-simp-set-leakage + definitional-triviality audit; 12 rows OPEN; GP-230 Franklin/Noether/Claude RD aggregate 0.598 → literal-true; validates `feedback_be_meta_darwin_to_self`; harness works mechanically but does NOT beat LeanHammer typeclass baseline
- **Numerical pre-check every tick (ns_graph_tick) 2026-05-14**: call mechanized RD primitive surface (`ns_graph_tick`, `primitive_tick_surface`, `rd_tick_brief`) BEFORE picking tick surface; do not select from chat-context anchoring. Session 2026-05-14 shipped 3 route-1 pressure-share ticks; post-hoc pre-check showed all top closure-miner / typed-endpoint targets were Track-B (`LeraySelfTaxProfilePriceStream:1095`, etc.) — route-1 work wasn't on the radar.
- **Be Meta-Darwin to self — load-bearing 2026-05-14**: every claim-bearing artifact MUST run its own null distribution, distinct-outcome count, class-balance ablation, LOO, floor-satisfiable-by-failing check, and source-leakage verification IN THE SAME ARTIFACT, before the claim is stated. Do NOT rely on a dispatched Meta-Darwin to catch laundering after the fact. Operator teaching after v22.05-v22.07 chain shipped 4 killed overclaims.
- **Lean premise-selection SOTA survey 2026-05-14**: Hard target is LeanPremise/LeanHammer (arXiv:2506.07477, R@16=63.5%, 5.82M pairs, 82M params, Carleson OOD=0%). Shared weakness: text-only input; unexploited levers are typed-Expr AST GNN, dep-DAG online embedding (Graph2Tac arXiv:2401.02949), verifier-grounded rerank, CoRNStack HN curriculum (arXiv:2412.01007). CPU-only validation path: SSL pretrain dep graph → frozen-encoder logistic probe → verifier-rerank smoke. Falsifier: Mathlib-test R@16>0.635 AND Carleson R@1>5%.
- **Operator's pattern — language isomorphism via parallel channels 2026-05-08**: leverage language ISOMORPHISM by translating into ONE other domain (e.g. business) + reason IN PARALLEL via universal/math language seams. Two channels feed each other bidirectionally. NOT convergence diagnostic, NOT MCDA, NOT 4-vocabulary quartet. Distinct from PATTERN-010 (stuck-diagnosis single-deployment). Architecture should run dual-channel when problem warrants. Op-catalog rigging defense per catch #23.
- **Codex outside view 2026-05-08 — architecture inflation flag**: Codex audit: 2-5% odds current architecture → Clay without new hard analytic idea; residual_void_score still 8; "no new 2026 breakthroughs needed" is OVERCLAIM (revised out). Concrete pivot: GP216 residual atom + reconcile liminf constructor; 4-way label every "closure" theorem; freeze broad architecture generation.
- **Restrict-Σ vs Redefine-space dichotomy 2026-05-08**: recurring PDE substrate-attack meta-move surfaced via PATTERN-012 4-vocab translation on W6: V2+V4 → restrict admissible class via Diophantine cut; V1+V3 → conjugate to weighted Sobolev. Stand up TWO parallel seams; falsification decides. Generalizes (Bourgain-Kuksin / Carleman / Yamazaki). PATTERN-012 N=2 promotion evidence.
- **Honest novel-closure axes shrink to 2 — T10 demoted 2026-05-08**: second-opinion GIMS-2007/BMN-1999 audit (agent a0703b5f) downgraded T10 from "partially novel" to "corollary of BMN-1999 resonant-projection + finite-dim limit equations". Honest independent axes: T9 (closed-aliasing) + T7b (sparse tightness). Two, not five. T11/T13/T10 all derived.
- **VBNS-PT + finite-Σ NS closure 2026-05-08 EXTENDED**: 5 new Lean files (OCCT, FDOS, Bilinear-Sum-Closure, Sum-Free-Heat-Collapse, Bohr-Mean-Enstrophy); finite-Σ stationary 3D NS COMPLETELY CLOSED for ν>0; W6 reduced to pure small-divisor harmonic-analysis problem (Liouvillian-Σ pressure-AP non-existence); 4 anti-laundering catches; META-META-META Postnikov-tower principle; VBNS-PT named candidate
- **Fractal mining at session scale 2026-05-08**: applied scripts/mining/{sample,rate,aggregate}_artifacts_for_taste.py methodology at SESSION granularity (not weekly). 10 samples / cold rater / 0-5 rubric. Mean 3.2, max 4, 4/10 ≥ 4. Empirically corrected "breakthrough night" narrative — Lean/Mathlib work scored 2-3 (competent infrastructure); META-architecture work scored 4 (class-catching). Catch-rate proxies META progress, not math progress. Reusable cross-session calibration tool.
- **Mitigations 11/12/13 — Vocabulary Quarantine + Falsifiable Asymmetry + Reducer Friction 2026-05-08**: 3 operator-directed guardrails on 2150-vocab projections: P11 strip elite nouns to 2026 foundational vocab; P12 demand falsifiable prediction about classical solved system; P13 adversarial Reducer outputs LAUNDERED for tautological renames. Combined chain protects against time-jump hallucination. Applies to OCCT/FDOS/VBNS-PT (predicted LAUNDERED) and any ZTARE meta-vocabulary output.
- **Orchestration chains from repo history 2026-05-08**: 5 forward chains extracted from this repo's 10 inflection points + 8 negative patterns: A=Pattern1→DARWIN→3-Leg, B=Registry→DARWIN→Cross-Family, C=Run-vs-Analyze→Pattern1→DARWIN, D=Mini-ZTARE→Real-Substrate, E=3-Source-Audit→Construction→DARWIN. Most under-used: Run-vs-Analyze (Tier 3). Catches generate rules; rules compose into chains.
- **Reusable agent-orchestration meta-patterns 2026-05-08**: 5 patterns validated tonight: ★ adversarial 2-role w/ friction (PRODUCED 2 clean theorems); ★ business-framing for pre-category-emergence stuck; tautology-trap detector (caught Massey-Toda circular); ★ independent CAS verification; ★ background-parallel agent batches. Apply to ZTARE.
- **NS Track B EXTENDED session 2026-05-07 to 2026-05-08**: 22+ Lean files; 6 sorry-free GSS; 14 AP-Liouville closures; UCC + 7-class dichotomy + 5+1-wall T15 characterization; 4-shadow 2150-vocabulary finding; 23+ defects auto-caught; T15 localized to single Liouvillian-frequency-AP measure-zero residual; mechanical Clay-closure roadmap requires NO new 2026 breakthroughs; full session summary at projects/ns_millennium_hunt/workspace/SESSION_SUMMARY_2026_05_07_to_08.md
- **NS Track B typed-companion + lean-dojo bridge session 2026-05-07**: 7 Lean files compose end-to-end Leray-Hopf energy_inequality reduction; scalar L² LSC primitive sorry-free; 4-way swarm decomposition; Mathlib lemma treasure map captured
- **Typed-companion + 4-way swarm is the Lean-formalization superpattern**: Validated 2026-05-07 NS Track B: convert opaque Props to typed companions, parallelize independent workstreams via swarm, compose via spine file, toy substrate as smoke-test, search Mathlib lemma names before custom proofs
- **VPS autonomous SRO daemon — full bring-up + bug-fix journey 2026-05-07**: Hetzner CCX23 deployed; SRO role autonomous + Telegram-gated; GP-228 v3 strange-loop test ran (3 iters; cross-family Claude×GPT-4.1; scores 51→49→67); 11 bugs surfaced + fixed in-session; RUN-VS-ANALYZE mandate discipline added per principal direction
- **GP-191 Stage 2 tenant overlay shipped 2026-05-07**: two-repo split: public kernel (sparckix/ztare) + private tenant overlay (ztare-research-co). 6 ZTARE-specific files moved; symlinks bridge into public tree. Kernel-only mode verified
- **Always check before duplicating; mechanize over scripts**: 2026-05-07: shipped scripts/ duplicates of director-side capabilities without checking src/ztare/research_director/ + GP-128 daemon + org/ runtime. Before any new file: 3-source audit (kernel + org/ + scripts/); kernel integration over standalone scripts; scripts/ is for one-shot operator tools only
- **ZTARE-on-ZTARE v0.5+v3+portfolio (2026-05-07)**: 4 orthogonal anti-anchoring layers (rotation+ceiling+adversarial+cross-substrate) + portfolio launcher + v3 meta-recursive variant + META_APPARATUS_AUDIT_TAXONOMY; documented in rubric_specification.md §§22-27
- **Recursive gain is agent-agnostic — mining-mediated, not iter-loop-mediated**: 2026-05-06 realization that broke a load-bearing assumption: recursive self-improvement doesn't require working inside a ZTARE iter loop. As long as work hits the data ecosystem (F-rows, project workspaces, seams, papers), mining harvests it and feeds signals back via GP-227 dashboard. RD agents, Claude, Codex are interchangeable from the gain cycle's perspective. Week-scale gain cycle is structurally identical to ZTARE iter loop. Dissolves the dormancy concern about ZTARE-on-ZTARE.
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
- SB-4: Vocabulary-chain laundering (rapid-synthesis-without-explicit-verification)
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

