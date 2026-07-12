# ZTARE Documentation Map

> **Up:** [Repository root](../README.md) · **Tooling:** [scripts/](../scripts/README.md) · [analytics/](../analytics/README.md)

The canonical public map for the docs tree. The root `README.md` is
the entry point. This map sorts each document into its layer and marks
which documents are canonical versus supporting context. Every doc carries an
`> **Up:**` breadcrumb back here, so the tree is walkable in both
directions and in an Obsidian vault as well as on GitHub.

## Layer map

| Layer | Canonical docs | Maturity | Purpose |
|---|---|---:|---|
| First-run path | `README.md`, `docs/guides/first-30-minutes.md` | public / usable | The shortest route to value: run the offline first-run command, see a claim demoted, then inspect the next review artifact or proof point. |
| Gaming behavior catalog | `docs/gaming_behavior_catalog.md`, `docs/concepts/gaming_behavior_catalog_map.md` | public / audit-linked | Skimmable catalog of LLM self-certification and specification-gaming behaviors, with catch patterns, evidence tiers, registry linkage, and hardening protocol. |
| ZTARE architecture | `docs/concepts/architecture.md`, `docs/concepts/leanmill_architecture.md`, `docs/guides/workflow.md`, `docs/guides/quickstart.md` | usable / evolving | Current map of in-loop validation, out-of-loop research operations, LeanMill station workflow, reflexive intelligence, and the project workflow. |
| Capabilities surface | `docs/concepts/capabilities.md` | canonical / public | Reviewer-oriented capability inventory: first-run commands, gaming-catalog audit, evaluator-hardening review artifacts, autoresearch routing, project intake, primitive health, LeanMill governance, and claim/evidence registers, each linked to implementation or evidence. |
| Graded reasoning | `docs/concepts/graded_reasoning.md` | expository / public | The argument-graph reasoning stack: the warrant ladder, the warrant-filtration strength profile, the override lattice, and Shapley/wager attribution over a governed claim graph. |
| System position and module map | `docs/concepts/system_position_and_module_map.md` | canonical / public | How ZTARE positions itself as a socio-technical research system, how related systems such as AI Co-Mathematician and LeanMill fit as orientation points, and how the validator, proof-search, GNN, forecast, workbench, org-runtime, and claim layers compose. |
| ZTARE use cases | `docs/guides/ztare_use_cases.md` | public / practical | Profession-level use cases for ZTARE as a reasoning compiler: diligence, legal review, science, strategy, product, policy, security, investigations, and formal fragments. |
| Proof/governance/residual loop | `docs/concepts/closure_claim_governance.md` | canonical / public | Human-facing map of Proof Execution, Governance Gate, and Residual Compiler, plus the closure-claim governance contract. |
| Claim-review constraint stack / recursive primitives | `docs/concepts/cognitive_gym.md`, `docs/concepts/epistemic_principles.md`, `docs/concepts/reflexive_engineering.md` | conceptual / partially mechanized | The constraint stack and epistemic operations behind bounded validation, anti-laundering checks, and reusable research moves. |
| Reflexive mining methodology | `docs/concepts/reflexive_mining_methodology.md` | authoritative / canonical | Weekly mining + taste-rating procedure, RCA from the 2026-05-16 procedure-inversion incident, gap register, and pre-cycle prevention checklist. Read before running `scripts/public/mining/run_reflexive_mine.py`. |
| Agentic engineering patterns | `docs/concepts/agentic_engineering_patterns.md`, `docs/guides/reflexive_audit_workflow.md` | public / reusable | General LLM-pipeline engineering patterns extracted from building ZTARE. |
| Forecast contracts / decision market | `research_areas/specs/active/protocol/GP-230_forecast_pool_decision_market_spec.md`, `research_areas/seams/protocol/GP-230_forecast_pool_decision_market_seam.md`, `scripts/public/control/forecast/pool.py` | active / mechanized | Sealed forecast contracts for macro/meso/micro branch choices, swarm gates, effort estimates, and externality audits. Historical seam: `GP-230`. |
| Primitive classification criteria | `docs/concepts/primitive_classification_criteria.md` | canonical / public | Deterministic checklist for "should this be in the reflexive-primitives or agentic-patterns catalog?" Replaces argument-by-anecdote with a six-criteria test per class. |
| Universal research language | `docs/concepts/universal_research_language.md`, `docs/concepts/structural_language_catalog.md` | public / generated from registries | Plain-English explainer plus the full generated catalogue for universal research operations, meta-language moves, and PDE estimate-craft handles. |
| Org runtime tenant overlay | `org/README.md`, `docs/concepts/organizational_primitives.md`, `docs/guides/org_runtime_quickstart.md` | working prototype | ZTARE's applied instance of cognitive-firm primitives: persistent roles, mandates, tasks, gates, preferences, transition logs, damage signals, Orbit, optional notification providers, and role-bound execution. |
| Public roadmap and operating record | `priority_roadmap.md`, `research_areas/EXPERIMENT_TRACK_RECORD.md`, `docs/concepts/ztare_research_company_architecture.md` | active / self-applied | Current public priorities, durable experiment/findings records, and the deeper organizational architecture for readers who want the operating model. |
| Human-facing surfaces | `docs/guides/manual_console.md`, `docs/guides/runtime_smoke_test.md`, `docs/guides/org_runtime_docker_deploy.md` | working / local-first | How a human reviewer drives the repo locally or through daemonized roles. |
| `ztare` CLI | `docs/guides/cli.md` | usable | The single command entry point for the workbench's human-facing surface (`ztare autoresearch`, `ztare action-intel`, `ztare forecast`, `ztare bundle`, etc.), wrapping the underlying control scripts. Workbench-only by design. Governance / org-side belongs to `cognitive-firm`. |
| Agent prompt sheets | `docs/guides/agent-prompts.md` | public / usable | Paste-ready prompts for using Codex or Claude to learn the repo, inspect projects, audit forecast-contract and action-intelligence surfaces, and stay inside membrane/observer boundaries. |
| Project case studies and papers | `docs/public_claim_register.md`, `papers/README.md`, `research_areas/EXPERIMENT_TRACK_RECORD.md`, `priority_roadmap.md` | mixed / status-labeled | Conservative public claims, manuscripts, and durable experiment/findings records for science, proof, policy, market, operations, and other bounded campaigns. |
| Evidence atlas | `docs/evidence_atlas/README.md` | public / reviewer-facing | Crosswalk from public claims and project summaries to evidence levels, primitive/pattern status, runnable review commands, non-claims, and known repo-health caveats. |
| Benchmark evidence | `benchmarks/benchmark_evidence.md`, `benchmarks/constraint_memory/README.md`, `papers/experimental_math_letter/evidence/pysr_baseline_full.json` | bounded / public | Conservative comparison evidence for false-positive suppression, null-returning gates, and evaluator hardening. Not a public ranking claim. |
| Formal artifacts | `ztare_proofs/README.md`, `ztare_proofs/ZtareProofs.lean`, `ztare_proofs/ZtareProofs/` | experimental / public source | Lean gate artifacts, proof sources, and formalization experiments. Generated `.lake/` build state is not source. |
| Tooling & data map | `scripts/README.md`, `analytics/README.md` | hand-authored / per-file | The operational toolchain and the analytics/ledger tree. Each sub-folder README names every script and states in one line what it does, so an agent or reader can navigate the code surface without opening source. |
| Failure & governance discipline | `docs/concepts/epistemic_principles.md`, `docs/concepts/anti_pattern_catalog.md`, `docs/concepts/goodhart_at_every_layer.md`, `docs/concepts/closure_claim_governance.md`, `docs/concepts/problem_class_taxonomy.md` | canonical / public | The failure axis, deconflicted: the structural law (`epistemic_principles` Part I), the operational field guide (`anti_pattern_catalog`), the per-layer manifestation map (`goodhart_at_every_layer`), plus closure-claim and problem-class discipline. |
| Specifications & substrate contracts | `docs/concepts/rubric_specification.md`, `docs/concepts/harness_specification.md`, `docs/concepts/mlh_family_protocol.md`, `docs/concepts/chaos_substrate_primitives.md` | canonical / public | The formats and contracts a substrate, rubric, or harness must satisfy. |
| Reusable patterns | `docs/concepts/prediction_ledger_pattern.md`, `docs/concepts/graph_diagnostic_belief_update_pattern.md`, `docs/concepts/cross_scale_fractal_map.md`, `docs/concepts/agent_agnostic_recursive_gain.md` | public / reusable | Self-contained patterns extracted from the work, usable without the rest of ZTARE. |
| Concept-level workflows | `docs/concepts/closed_loop_theorem_writer_workflow.md`, `docs/concepts/closure_utility_test_workflow.md` | public / procedural | Concept-level procedures, distinct from the human-facing guides under `docs/guides/`. |
| Glossary & reference | `docs/concepts/glossary.md`, `docs/reference/` | reference | Plain-language term definitions and supporting reference material. |
| Internal boundary | maintainer-only docs | internal / not public evidence | Maintainer audit support. Listed only to mark the boundary. Not a first-read path or public evidence source. |
| Landings | `docs/landings/` | prototype UI artifacts | Static visual demos for governance and org-runtime concepts. |

## Recommended paths

## Cognitive-firm boundary

The reusable org kernel lives in
[`sparckix/cognitive-firm`](https://github.com/sparckix/cognitive-firm).
The `org/` tree in this repo is the ZTARE overlay and compatibility surface:
role templates, local gates, channels, runtime docs, and tenant-specific
symlinks where a live deployment has them. Public ZTARE should not treat a
tenant notification provider as part of the generic kernel.

### New reader

1. `README.md`
2. Run `make first-run` or read `docs/guides/first-30-minutes.md`
3. `docs/guides/ztare_use_cases.md` (who uses it and for what)
4. `docs/concepts/capabilities.md` (current capability inventory)
5. `docs/gaming_behavior_catalog.md` (the public catalog and catch patterns)
6. `docs/evidence_atlas/README.md` (how to review claim evidence)
7. `docs/public_claim_register.md`
8. `docs/concepts/glossary.md`: evidence levels, historical seam ids
   (for example LeanMill, forecast contracts, and action intelligence), and
   other recurring terms
9. `docs/guides/quickstart.md`
10. `docs/guides/workflow.md`
11. `docs/concepts/architecture.md`
12. `priority_roadmap.md` (what is next)

### Researcher evaluating claims

1. `README.md`
2. `docs/public_claim_register.md`
3. `docs/evidence_atlas/README.md`
4. `docs/evidence_atlas/claim_cards.md`
5. `docs/evidence_atlas/primitive_evidence_matrix.md`
6. `docs/concepts/system_position_and_module_map.md`
7. `docs/concepts/closure_claim_governance.md`
8. `benchmarks/benchmark_evidence.md`
9. `papers/README.md`
10. `research_areas/EXPERIMENT_TRACK_RECORD.md`
11. Relevant project artifacts under `projects/` when intentionally public

### Builder integrating the kernel

1. `docs/concepts/architecture.md`
2. `docs/guides/workflow.md`
3. `docs/concepts/cognitive_gym.md`
4. `docs/concepts/organizational_primitives.md` if you need role/gate/runtime integration

### Builder interested in the org runtime overlay

1. `org/README.md`
2. `docs/concepts/organizational_primitives.md`
3. `docs/concepts/ztare_research_company_architecture.md`
4. `docs/guides/org_runtime_quickstart.md`

### Builder interested in LLM engineering patterns

1. `docs/concepts/agentic_engineering_patterns.md`
2. `docs/concepts/reflexive_engineering.md`
3. `docs/evidence_atlas/primitive_evidence_matrix.md`
4. `docs/guides/reflexive_audit_workflow.md`

### Agent or contributor navigating the code

1. `scripts/README.md` (every tool, grouped, one line each)
2. `analytics/README.md` (ledgers, queries, the data tree)
3. `docs/guides/agent-prompts.md`
4. `docs/concepts/architecture.md`

## Status vocabulary

- `usable`: expected to work for the documented path.
- `working prototype`: exercised locally, but not enterprise-hardened.
- `experimental`: useful research track, not a product promise.
- `conceptual`: explains the architecture or philosophy. Not necessarily a runnable component.
- `internal`: maintainer-facing audit map or implementation note.
- `historical`: preserved for provenance. Not canonical.

## Non-goals for the public entry point

- Do not read every maintainer-only doc first.
- Do not treat every project under `projects/` as a polished public case study.
- Do not infer that a high-scoring experiment is a scientific discovery unless
  the experiment ledger and paper layer say so.
- Do not treat private mirror paths as public source material.

<!-- AUTO-INDEX:START (auto-generated; edit prose OUTSIDE this block) -->

## Index

**Sub-folders**

- [`analysis/`](analysis/) - 1 file(s)
- [`concepts/`](concepts/) - 43 file(s)
- [`evidence_atlas/`](evidence_atlas/) - 17 file(s)
- [`guides/`](guides/) - 15 file(s)
- [`landings/`](landings/) - 2 file(s)
- [`reference/`](reference/) - 5 file(s)

**Documents**

- [LLM Gaming Behavior Catalog](gaming_behavior_catalog.md) - Human-readable catalog of LLM gaming behaviors: benchmarked self-certification patterns, mined cross-domain behavior classes, and audit patterns.
- [Multi-domain evidence inventory](multi_substrate_validation.md) - Evidence inventory for what ZTARE's claim discipline has and has not shown across several research domains.
- [Public Claim Register](public_claim_register.md) - Public claim register for the ZTARE campaigns: what survived, what did not, and where the evidence lives.
- [A 70-Day Sprint, Six Architectural Phases](sprint_70day_journey.md) - Build narrative covering 70 days of work on ZTARE across six architectural phases, including failures and reflexive self-audit.

<sub>6 sub-folder(s), 4 document(s). Auto-generated; re-run `gen_folder_index.py` after adding files.</sub>
<!-- AUTO-INDEX:END -->
