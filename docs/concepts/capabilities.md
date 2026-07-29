---
description: "What ZTARE currently has: the architectural stack, operating discipline, and named primitives, each grounded in a module or deeper doc."
---

# Capabilities

> Up: [`docs/README.md`](../README.md)

What ZTARE currently has. Each capability points to the deeper
doc or the actual module that implements it, and is grounded elsewhere in the
repository.

The page sits between three neighbours:
[`system_position_and_module_map.md`](system_position_and_module_map.md) is the
architectural framing. [`architecture.md`](architecture.md) is the
implementation map. [`public_claim_register.md`](../public_claim_register.md)
is the per-claim result surface.
[`evidence_atlas/README.md`](../evidence_atlas/README.md) is the
reviewer-facing evidence crosswalk. [`priority_roadmap.md`](../../priority_roadmap.md)
is what is next.

The capabilities are organised in three layers: the architectural stack
(what the system is), the operating discipline (what it does, across
projects and evaluator surfaces), and a short list of named primitives
(specific reusable tools).

Capability here means "there is an implementation surface a reviewer can
inspect or run." It does not mean the capability has external validation,
benchmark lift, or broad domain reliability. When a capability supports a
public claim, the claim register and evidence atlas carry that scope.
For the v1.1 reasoning-compiler language, the inspectable capability map is
[`reasoning_compiler_capabilities.json`](../evidence_atlas/reasoning_compiler_capabilities.json).
`make reasoning-compiler-capability-audit` checks that each row names an input
object, check or transform, output object, falsifier, evidence refs, and a
runnable anchor, plus at least two research anchors from
[`research_anchors.json`](../evidence_atlas/research_anchors.json).
This page uses `substrate` only for internal kernel routing or reusable gate
families. Public workflows should usually say project, project brief, review
artifact, or saved review file. The glossary owns the exact distinction.

## Table of Contents

- [Fast map for reviewers](#fast-map-for-reviewers)
- [1. The architectural stack](#1-the-architectural-stack)
  - [Kernel gate dispatcher](#kernel-gate-dispatcher)
  - [Statistical meta-diagnostics](#statistical-meta-diagnostics)
  - [In-loop validator: the iteration pipeline](#in-loop-validator-the-iteration-pipeline)
  - [Grammar tiers and the EML primitive](#grammar-tiers-and-the-eml-primitive)
  - [Fit primitives and Stage 1/2/2.5 compression](#fit-primitives-and-stage-1225-compression)
  - [The mutator briefing](#the-mutator-briefing)
  - [Structural-presence and negative-space extractors](#structural-presence-and-negative-space-extractors)
  - [Residual diagnostics and symbolic regression](#residual-diagnostics-and-symbolic-regression)
  - [Information-yield evaluator and stagnation pivots](#information-yield-evaluator-and-stagnation-pivots)
  - [DAG steering](#dag-steering)
  - [Graph action interface and route provenance](#graph-action-interface-and-route-provenance)
  - [Invariant-search mode: Lagrangian derivation + Buckingham π + Noether variance](#invariant-search-mode-lagrangian-derivation--buckingham-π--noether-variance)
  - [REFRAME and ANALOGY: the two non-grammar primitives](#reframe-and-analogy-the-two-non-grammar-primitives)
  - [Full-catalog primitive families](#full-catalog-primitive-families)
  - [LLM-mediated primitive families](#llm-mediated-primitive-families)
  - [Provider runtime, aliases, and telemetry](#provider-runtime-aliases-and-telemetry)
  - [Constraint-to-isomorphism router (cross-domain)](#constraint-to-isomorphism-router-cross-domain)
  - [Kepler vs Newton: two observable layers, judged separately](#kepler-vs-newton-two-observable-layers-judged-separately)
  - [Post-run discriminator wiring](#post-run-discriminator-wiring)
  - [The gate library](#the-gate-library)
  - [The Framer language](#the-framer-language)
  - [The Research Director: out-of-loop orchestration](#the-research-director-out-of-loop-orchestration)
  - [Synthetic personas and debate orchestrator](#synthetic-personas-and-debate-orchestrator)
  - [Commit-membrane daemon](#commit-membrane-daemon)
  - [Work daemons](#work-daemons)
  - [Org-runtime tenant overlay](#org-runtime-tenant-overlay)
- [2. Operating discipline (workbench-wide)](#2-operating-discipline-workbench-wide)
  - [Deterministic enforcement floor](#deterministic-enforcement-floor)
  - [Sealed-result discipline](#sealed-result-discipline)
  - [Forecast pool and prediction market](#forecast-pool-and-prediction-market)
  - [Gaming behavior catalog and runtime guard](#gaming-behavior-catalog-and-runtime-guard)
  - [Reflexive primitives (the workbench measures itself)](#reflexive-primitives-the-workbench-measures-itself)
  - [Machinery governance](#machinery-governance)
  - [Research-yield decomposition](#research-yield-decomposition)
  - [Action intelligence and operations surface](#action-intelligence-and-operations-surface)
  - [Audit-integrity chain manifests](#audit-integrity-chain-manifests)
  - [Epistemic Airgap gate (cross-provider enforcement)](#epistemic-airgap-gate-cross-provider-enforcement)
  - [Cold cross-provider pass](#cold-cross-provider-pass)
  - [Damage signals](#damage-signals)
  - [Supervisor and agent-rotation layer](#supervisor-and-agent-rotation-layer)
  - [Self-demotion and recovery as discipline](#self-demotion-and-recovery-as-discipline)
- [3. Named primitives](#3-named-primitives)
  - [Vocabulary escape and observable rotation](#vocabulary-escape-and-observable-rotation)
  - [Cross-mutator / cross-tool triangulation](#cross-mutator--cross-tool-triangulation)
  - [Grammar-vs-space diagnosis](#grammar-vs-space-diagnosis)
  - [Project readiness and constraint-to-DoF analysis](#project-readiness-and-constraint-to-dof-analysis)
  - [LeanMill governed proof-search solver](#leanmill-governed-proof-search-solver)
  - [Power-aware experimental statistics](#power-aware-experimental-statistics)
  - [Forecasting-program calibration database and Brier/Elo stats](#forecasting-program-calibration-database-and-brierelo-stats)
  - [Lean / formal-verification bridge](#lean--formal-verification-bridge)
  - [Recent additions tracked through July 2026](#recent-additions-tracked-through-july-2026)
- [Current boundaries](#current-boundaries)

## Fast map for reviewers

If you are deciding whether to run the repo, start from the command surface;
the historical seam names are secondary.

| Question | Capability surface | First command or artifact |
|---|---|---|
| Can the repo show value without model keys? | Claim demotion and public smoke checks | `make hello` or `make first-run` |
| Does the repo catch basic release-time code drift? | Exact undefined-name tripwire plus public terminology, scope, evidence-atlas, routing, and docs checks | `make flakes` and `make gates` |
| Does the gaming behavior catalog correspond to live checks? | Gaming behavior registry, hardening map, promotion evidence, and executable fixture anchors | `make gaming-catalog-audit` |
| Is the evaluator-hardening proof point bounded and reproducible? | Frozen constraint-memory suite, three artifact-backed arms, pending ordinary-review arm | `make evaluator-hardening-frozen-check` |
| Should a task enter the in-loop autoresearch kernel? | Workbench router over bounded claim, evaluator, rubric, artifact surface, and move-card route provenance | `ztare autoresearch route --task "<task>" --project <project> --rubric <rubric>` |
| Is a project missing surfaces before run readiness? | Project brief JSON, source index, artifact-source binding contracts, output binding, replay manifest, evidence-gap records, and optional prep ledger | `ztare project intake create --help`, `ztare project source-index --help`, `ztare project evidence-bind --help`, and `ztare project evidence-replay --help` |
| Can launch readiness be checked without model calls? | Intake-bound `plan_preview`, repair-first recommendation, readiness-only run path, expected-command inheritance, and admission record | `ztare autoresearch trace --project <project> --rubric <rubric> --intake <intake.json> --json` then run `plan_preview.recommended_first_command` |
| Did a candidate stay inside the declared mathematical vocabulary? | Expression-grammar compiler over rubric grammar, fit declaration, model body, fitter, and gate verdict | `ztare autoresearch trace --project <project> --rubric <rubric> --intake <intake.json> --json` or `./venv/bin/python research_areas/probes/gp059_eml_expressibility_check.py` |
| What happened in an autoresearch run? | Read-only trace chain over intake readiness (`readiness_canonical`), loop admission, source/evidence records, mutator briefing, graph focus, prediction contracts, projection, and trace-local health | `ztare autoresearch trace --project <project> --rubric <rubric> --intake <intake.json> --json` |
| What should the local UI consume? | Project Workbench contract over all project folders, project brief repair, source/evidence readiness, trace, readiness check, run history, report state, saved history, and file-backed write boundaries | [`forensic_workbench_interface.md`](forensic_workbench_interface.md), `ztare forensic-workbench project-state --project <project> --json` |
| Can I pressure-test a project before or without a full run? | Pre-run rubric critique (gaming surface, evidence anchoring, ceiling reachability), plain-language research-map queries, single-claim falsification, and document→bounded-claim drafting — CLI-first, surfaced in the workbench | `ztare rubric review --project <project> --json`, `ztare research map-query`, `ztare research falsify`, `ztare project draft --doc <path> --json` |
| Is a loop getting simpler to defend or just different? | Advisory compression-progress signal over BIC, MDL, proof length, and telemetry-backed effort; use it beside information yield, not instead of it | [`compression_progress.py`](../../src/ztare/validator/core/compression_progress.py) and `./venv/bin/python scripts/public/control/compression_progress_replay.py --project <project>` |
| Does a project preserve the raw/source/evidence/projection chain before run readiness? | DK0 evidence-trace audit over raw sources, source index, source-binding contracts, compile provenance, evidence output, constraints, projection, route preview, and guarded run command | `make autoresearch-evidence-trace PROJECT=<project> RUBRIC=<rubric> INTAKE=<intake.json> JSON=1` |
| Do run-state traces replay cleanly across projects? | Trace replay over projection fields, latest-eval overlay, current-carrier readiness, artifact refs, worker provenance, transport, constraints, and action links | `ztare autoresearch carrier-replay --project <project> --json` |
| Are graph/DAG signals wired without overstating general graph support? | Graph decision records, graph-derived RD actions, and graph capability audit | [`graph_interfaces.md`](graph_interfaces.md) and `make graph-capability-audit` |
| Do move cards route task phrasings to the intended action surface? | Fixed paraphrase audit over the compact move-card router; semantic atlas must match current content-hash rows before use | `ztare audit move-card-router --json` |
| Are forecast/prediction rows measurement or authority? | Forecast-pool lifecycle, prediction-contract read model, and forecast capability audit | `make forecast-capability-audit` |
| Are subscription/API worker paths comparable? | Dispatch parity and outcome audit | `ztare autoresearch dispatch-parity --json` and `ztare autoresearch subscription-outcomes --json` |
| Is primitive recall healthy before building new tools? | Primitive catalog, digest-checked semantic atlas, and amnesia precheck | `ztare primitive health` |
| Is proof-search evidence externally governed before it counts? | LeanMill proof audit, source review, harness, and axiom policy surfaces | `ztare leanmill proof-audit --help` |
| Which claims are public and which are not? | Evidence atlas and public claim register | [`docs/evidence_atlas/README.md`](../evidence_atlas/README.md) and [`docs/public_claim_register.md`](../public_claim_register.md) |

The detailed sections
below name the implementation surfaces and historical provenance for each
capability.

---

## 1. The architectural stack

### Kernel gate dispatcher

Historical provenance: [GP-157](../../research_areas/seams/apparatus/cage/GP-157_R10_R16_backport_scoping_2026_05_06.md).

The dispatcher is the internal router that chooses which deterministic gates apply to a
kernel surface. It reads `substrate.meta['class']`, queries each gate's
`can_handle()` predicate, and runs gates in a dependency-ordered DAG so a
Lean-proof target, a PDE project, and an integer-sequence project can use
different gate-and-judge ordering without script-specific route tables. Mode is
per internal surface class: `off` / `observe` / `authoritative`. Lives in
[`src/ztare/gates/registry.py`](../../src/ztare/gates/registry.py),
[`src/ztare/gates/substrate_evaluation.py`](../../src/ztare/gates/substrate_evaluation.py),
and the symbolic-logic dispatcher
[`src/ztare/gates/symbolic_logic_cage.py`](../../src/ztare/gates/symbolic_logic_cage.py).

### Statistical meta-diagnostics

Historical provenance: [GP-166](../../research_areas/seams/mission/meta/GP-166_self_enacted_procedural_compliance_seam.md).

Runs *before* the first iteration. A noise-profile classifier probes the
project/evaluator surface for heteroscedasticity, non-Gaussian residuals,
autocorrelation, and errors-in-X, and *auto-routes* the solver configuration
(fit-score mode, grammar tier, gate-DAG order) before any mutator call. The
data epistemology is measured directly from the project surface.
Implementation at
[`src/ztare/diagnostics/noise_profile.py`](../../src/ztare/diagnostics/noise_profile.py)
with companion substrate critic at
[`src/ztare/diagnostics/substrate_critic.py`](../../src/ztare/diagnostics/substrate_critic.py).

### In-loop validator: the iteration pipeline

A loop that proposes, fits, and adversarially tests claims under deterministic
gates. One iteration runs through a fixed pipeline. The relevant entry points
are catalogued in implementation maps and tests for audit.
Per-iteration: **rubric pre-flight → prepare
candidate → mutator call → prompt assembly → fit → compression → gate
battery → judge → information-yield → pivot/close.** A rejection at the
candidate-preparation stage (lint, AST, NameError, KeyError, missing
`I_model`/`PARAMETRIC_FORM`) is recoverable: the Compiler Bounce retry
gives the mutator up to three in-place re-prompts with the specific error
injected, costing ~$0.05/retry vs. ~$0.40 for a full iteration. The iteration
counter does not advance during retries. Lives under
[`src/ztare/validator/`](../../src/ztare/validator/),
[`src/ztare/fit/`](../../src/ztare/fit/),
[`src/ztare/composition/`](../../src/ztare/composition/), and
[`src/ztare/orchestrator/`](../../src/ztare/orchestrator/).

### Grammar tiers and the EML primitive

The expression language is tiered. `fit_expression_grammar`
takes one of: `eml_only` (only the EML primitive `eml(x, y) = exp(x) − ln(y)`
plus arithmetic), `math_exp_only` (arithmetic + `math.exp`), `math_exp_trig`
(adds `math.sin`/`math.cos`/`math.tan`), `py_exec` (sandboxed Python with
authorised primitives like `isprime`, `factorint`, `primefactors`, `divisors`,
`gcd`), or `omit`. EML is the single composite primitive used in
the Planck-sandbox vocabulary-escape calibration: giving the mutator one
fused exp/ln operator forces it to build composites *out of* the primitive,
closing the vocabulary-drift escape. `py_exec` is gated by an explicit `py_exec_authorized_by` rubric flag
plus an `expression_byte_budget` ceiling, enforced fail-closed at
rubric-preflight.

This is also a small example of the broader engine philosophy: declare a small
primitive set, compose inside it, and make vocabulary escapes fail at the parser
or gate layer instead of in prose review.

### Fit primitives and Stage 1/2/2.5 compression

A fit primitive (`scipy.optimize.curve_fit` and multi-start variants)
estimates parameters on visible evidence only. Deterministic holdout and
farther-tail gates enforce generalisation. The compression primitive then
strips overparameterised surrogates:

- Stage 1 enumerates 22 additive templates over `√n`, `ln n`, `n^b`,
  `e^{an}`, `1/n` with selection by BIC inside topology classes and an
  exponent grid `{0.25, 1/3, 0.5, 2/3, 1, 1.5, 2}` constraining free
  power-law exponents.
- Stage 2 activates only when Stage 1 returns no gate-passing form: 13
  depth-1 compositional templates such as `√(n / ln n)` (which is how the
  Vaughan prime-partition form was first reached). Synthesizer seed
  selection uses BIC sort + structural diversity so the next iteration
  is not trapped in one family.
- Stage 2.5 (observable rotation) applies monotonic transforms
  (`1/z`, `ln z`, `Δz`) when Stage 1 and Stage 2 both return no
  gate-passing form, and re-runs compression on the transformed
  representation. This is how the Ulam reciprocal compression
  (`n / U(n)`) was discovered without human guidance.

The fit-primitive-features path, historically specified in
[GP-156 Proposal 3](../../research_areas/specs/active/GP-156_apparatus_hardening_proposal.md), writes
`workspace/fit_features_result.json` with per-parameter init-range
auto-escalation (5×, 25× widening on flat-desert) and substitutes the
fitted `MODEL_PARAMS` into the in-memory `python_code` via AST rewrite,
with no disk round-trip during the substitution.

### The mutator briefing

Before the mutator is called, a structured pre-prompt is assembled by the
deterministic provider registry under
[`src/ztare/orchestrator/briefing_providers/`](../../src/ztare/orchestrator/briefing_providers/):
contract rules, tried-and-failed negative memory, fit telemetry, gate gaps,
per-class breakdowns, structural seeds, verifier context, graph-focus receipts
for local verification gaps, and opt-in stagnation/debug lenses. Each provider
writes its own section. The resulting
`workspace/mutator_briefing_iter_NNN.md` is persisted per-iteration for
reviewer audit. Adding a future provider is one file plus one registry line,
not a prompt rewrite.

The tried-and-failed provider is the negative-memory channel for the in-loop
workbench. It summarizes prior R1 rejection reasons, mutation-contract
mismatches, fit failures, repeated non-improving weakest points, and projection
constraints so the next mutator inherits failed branches as reusable constraints,
sparing it a blank-prompt rediscovery.

### Structural-presence and negative-space extractors

Two structural extractors named for the side of the search space they read.
The structural-presence extractor is the positive-space extractor
([GP-061.A](../../research_areas/seams/apparatus/supervisor/GP-061_R4_retrospective_audit.md),
[`src/ztare/gates/structural_constraint_extractor.py`](../../src/ztare/gates/structural_constraint_extractor.py)):
it surfaces features that *are present* in the current evidence as candidates for the
next form. The negative-space extractor is the void extractor
([GP-061.B](../../research_areas/seams/apparatus/supervisor/GP-061_R4_retrospective_audit.md),
[`src/ztare/gates/negative_space_extractor.py`](../../src/ztare/gates/negative_space_extractor.py)):
it surfaces *what is structurally missing*: feature-bag gaps
the mutator systematically avoids. Its canonical instance is the
Planck-sandbox-08 post-mortem, where it mechanically surfaced
`EMLCALL(arg0|has_op:Pow)` as a dense void on a corpus of 8 failed
families. Both write to the derived-constraints ledger
([`src/ztare/gates/derived_constraints.py`](../../src/ztare/gates/derived_constraints.py));
Only confirmed constraints render into the mutator prompt.

### Residual diagnostics and symbolic regression

Two layers further down the constraint stack. Residual diagnostics
([`src/ztare/motion/residual_diagnostics.py`](../../src/ztare/motion/residual_diagnostics.py))
uses a deterministic 2-bit residual
descriptor that classifies a fitted form's residual as smooth,
periodic, or pathological, narrowing the corrector-library
recommendation *without oracle leakage*. Grammar-guided symbolic regression
([`src/ztare/composition/symbolic_regression_synthesizer.py`](../../src/ztare/composition/symbolic_regression_synthesizer.py))
builds new forms when the additive and depth-1
compositional templates exhaust. It composes candidate
forms via LLM-guided depth-2 templates, deterministic ratio probes,
tail-correction primitives
([residual-driven seeds, GP-087](../../research_areas/seams/engine/grammar/GP-087_residual_driven_primitive_generation_seam.md)), and
additive regime composition
([additive composite, GP-103](../../research_areas/seams/engine/GP-103_topology_induction_gap.md)). The synthesizer
runs in lifecycle phases (G1, G1.5, G2) with explicit seed-queue
source tags so a reviewer can audit which iterations were
mutator-driven vs. composition-driven.

### Information-yield evaluator and stagnation pivots

A per-iteration evaluator tracks whether the mutator's current functional
class is still producing new structural information. **Class-novelty
stagnation decoupling** lets the loop register
stagnation on the *class* of forms even when the iteration counter
increases. A committee-rotation throttle prevents the same judge
panel from re-affirming a stuck class. Stagnation thresholds are
resolved through `pivot_heuristics.resolve_stagnation_pivot_state()`,
the single source of truth for prompt assembly *and* event logging. A control
follow-up policy blocks repeated non-emergency pivots or blitzes until the
configured follow-up window has been observed, then records the decision in
`control_followup_policy.jsonl` for audit and health reports. Health reports
separate raw activation rows from non-overlapping control episodes, so a run is
not credited for repeated pivots unless the follow-up window produces evidence,
measured lift, or a named non-success diagnostic. The same audit emits a
bounded recovery queue of control episodes to extend, replay, or mark with an
explicit no-follow-up reason, and distinguishes loop intake files from
compiled evidence artifacts so recovery commands do not pass evidence material as
the run-readiness boundary. **[Theory-building
operation pivot enrichment](../../research_areas/seams/engine/meta/GP-216_theory_building_operations_seam.md)** maps current failure-log signals (e.g.
`profile decomposition`, `lower-semicontinuity`, `limit-passage`,
`finite certificates`, `global Sobolev`) into named operation classes
(e.g. `patches_dont_glue_globally` → `core_04 Local-to-Global
Assembly`) and rewrites the mutator instruction text (advisory only;
the pivot itself is data-driven).

### DAG steering

Historical provenance: [GP-134](../../research_areas/seams/apparatus/instrumentation/GP-134_prompt_layer_contamination_incident_seam.md).

Before each mutator call, the kernel computes a steering context from
the probability DAG of prior iterations: which nodes have survived,
which have been demoted, which open questions remain. The mutator
receives the DAG context as part of the briefing, so structurally
similar lines that have already failed are not re-proposed under a
different rename.

The shared graph action and receipt contract is documented in
[`graph_interfaces.md`](graph_interfaces.md). DAG steering is one registered
graph kind. NS basin graphs and primitive capability graphs use the same
receipt discipline when they are promoted beyond project- or domain-local
diagnostics.

### Graph action interface and route provenance

ZTARE has several graph-shaped surfaces: the in-loop probability DAG, primitive
capability edges, source-claim/evidence graphs, and domain-local basins such as
the NS constraint graph. The reusable capability is not an all-purpose graph
library. It is a small action-and-receipt interface for moving graph
diagnostics into decisions without losing provenance.

The common receipt type lives in
[`graph_carrier.py`](../../src/ztare/common/graph_carrier.py). Source-claim
graphs are consumed by
[`source_claim_graph_carrier.py`](../../src/ztare/validator/source_claim_graph_carrier.py)
and lowered by
[`graph_carrier_actions.py`](../../src/ztare/research_director/graph_carrier_actions.py)
into `graph_rd_actions[]` rows on `ztare autoresearch trace`. Those rows say
whether the graph found out-of-loop source/evidence repair, an in-loop focus
receipt, weak compiled-claim binding that must be repaired or demoted before
report export, a route change, or only an advisory diagnostic. When the graph
diagnostic selects a route, the row carries `operator_card_routes[]`
and `operator_card_ids[]` for `OP-GDC-01`, so later audits can distinguish a
graph-driven action from a prose recommendation.

The audit boundary is executable:
`make graph-capability-audit`. It checks that the docs, implementation
receipts, consumers, tests, and public wording keep graph algorithms, graph
decision records, domain claims, and the move-card atlas/routing state
separate. The companion
`ztare audit move-card-router --json` checks a fixed paraphrase set against the
compact move-card router so routing drift is measured directly by the audit.
The default audit is deterministic and offline. `SEMANTIC=1`
exercises the live embedding atlas and reports `semantic_error_count` when the
provider path is unavailable. Both paths now read the same atlas contract:
embedded ids, metadata rows, and manifest size/source must match the current
move-card catalog. If the contract is stale, the report points to
`make move-card-atlas-build` and the semantic route is not counted as
deployed.

### Invariant-search mode: Lagrangian derivation + Buckingham π + Noether variance

A specialised `rubric_mode: invariant_search` enables a chain of
physics-motivated gates. Lagrangian derivation primitive (historical seam:
`GP-180`):
when the mutator declares `LAGRANGIAN`, `Q_VARIABLES`, `BACKGROUND`,
`PREDICTION`, and `SYMMETRIES`, the kernel derives a closed-form
prediction and captures Noether invariants. Buckingham π gate (historical
seam: `GP-179`):
AST-walks the fit form for transcendentals applied to raw dimensional
arguments and refuses fits where the dimensional content is incoherent
(strict mode skips the fit, soft mode surfaces a briefing note).
Noether-variance loss (historical seam: `GP-180`): adds `λ · CV²(Π)` per declared
invariant to the loss so the optimiser pays for variance in any quantity
the mutator asserted is conserved.

### REFRAME and ANALOGY: the two non-grammar primitives

REFRAME enumerates coordinate transforms `(h_in, h_out)`, ranks them by
MDL on the actual data, and reports which frame the data prefers. ANALOGY
queries an LLM for cross-domain forms whose structural shape matches the
failure surface, drawing candidates from outside the home discipline's
template set. Both exist to propose decompositions a domain expert's priors
would tend to rule out. Implementations live in the
analogy / framer trees referenced in
[`cognitive_gym.md`](cognitive_gym.md).

### Full-catalog primitive families

The live architecture index is a generated 1104-row capability catalog. Each row
now carries two derived taxonomy fields:

- `source_category`: where the implementation lives, such as `research-operator`,
  `proof-search`, `fit/regime`, `gate`, `mining`, or `common-infra`.
- `semantic_family`: what research role it serves, currently one of
  `research_move_operator`, `evidence_governance_gate`,
  `proof_formalization_worker`, `model_fit_structure_probe`,
  `orchestration_briefing_provider`, `mining_operations_intelligence`,
  `pattern_memory`, `substrate_workbench`, or `infrastructure_utility`.

The generator is
[`primitive_catalog_taxonomy.py`](../../src/ztare/research_director/primitive_catalog_taxonomy.py).
It also normalizes moved paths, reports duplicate ids/signatures, and checks
whether the rendered index and semantic atlas are stale. This is the long-term
catalog structure. Embeddings and agents may propose related-capability edges,
but promoted taxonomy should be deterministic or explicitly curated.

### LLM-mediated primitive families

Several primitives use an LLM or subscription-backed agent as a worker, but
they do not all play the same architectural role. The semantic parent graph in
[`primitive_family_registry.py`](../../src/ztare/research_director/primitive_family_registry.py)
groups the concrete child primitives without renaming their implementation
symbols:

- `core_workbench_worker`: the main in-loop mutator, judge, and committee
  workers.
- `external_perspective_generator`: cold seeds, inversion, analogy,
  eigenquestion generation, and alignment-style independent critiques.
- `review_governance_helper`: rubric review, charter critique, primitive
  catalog quality filtering, and post-run meta-audit.
- `composition_helper`: recombination fusion, evidence-gap enrichment, and
  proposal-class labeling.

This parent graph is a legibility layer for dispatchable LLM/agent workers. It
is not a second primitive catalog and does not cover the whole 932-row index.
The RD primitive surface displays both full-catalog parent nodes and these
worker-family nodes before concrete hits, so a director sees the family of move
first and the exact reusable primitive second.
`make primitive-parent-utility JSON=1` checks both held-out route usefulness and
whether the worker-family cards still point at live module entrypoints.

### Provider runtime, aliases, and telemetry

The shared LLM runtime resolves short aliases, selects the provider transport,
enforces cross-family metadata, records usage/cost telemetry, and carries
provider-level timeout budgets into API calls. The current registered provider
families are Google, Anthropic, OpenAI, DeepSeek, Kimi/Moonshot, and Grok/xAI.
The public alias table is
[`docs/reference/model_aliases.md`](../reference/model_aliases.md). The
authoritative implementation is
[`src/ztare/common/llm_runtime.py`](../../src/ztare/common/llm_runtime.py).

Kimi/Moonshot and Grok/xAI use the same Chat Completions-style transport as
other compatible providers, but they retain their own provider families for
airgap checks, pricing, fallback chains, and redacted doctor output. The runtime
also bridges JSON response contracts onto providers that do not receive Gemini
`GenerateContentConfig` objects directly, so schema-sensitive judge calls fail
less often for transport reasons.
In-loop autoresearch runs default to sealed model-family provenance. Cross-model
fallback is an explicit userland opt-in for continuity runs.

### Constraint-to-isomorphism router (cross-domain)

`src/ztare/common/constraint_isomorphism.py` generalizes ANALOGY beyond
curve-fit residuals into a canonical interface any consumer plugs into
(Strategy pattern, like `fit.mdl.MDLLibrary`). When a system hits a
structural ceiling it (1) abstracts the failure to a domain-stripped
`ConstraintFingerprint` (pure topology/complexity/algebra), (2) queries an
LLM with ONLY that abstract constraint (with a `forbidden_domain` to push
away from) to surface established theorems from any field that solve it.
Removing the domain semantics from the prompt is what lets the query reach
matches direct prompting does not. (3) compiles each match to a gate
and holdout-verifies it via the consumer's `oracle` (MDL / closure rate /
MRE). Only matches that improve the metric survive. The general engine is
shared. Each consumer implements `StrangeLoopDomain` (`abstract_failure`,
`compile_to_test`, `oracle`). `fit/analogy.py` ([GP-164](../../research_areas/seams/engine/meta/GP-164_ztare_v2_reframe_analogy_meta_architecture_seam.md)) is the validated
curve-fit specialisation and remains in-loop. Leanmill and the research
directors are the intended new consumers. Efficacy is unproven:
whether the autonomous query surfaces useful matches vs.
plausible nonsense is the open test. Surfaced by the `primitive_amnesia`
precheck (run it before building lateral-search machinery). The SOP for
wiring any new primitive into the precheck is
[`primitive_surfacing.md`](primitive_surfacing.md).

### Kepler vs Newton: two observable layers, judged separately

A gate-and-judge layer distinguishes two layers of explanation. The
Kepler step is the empirical fit on visible evidence: a curve that
reproduces the observed numbers. The Newton step is the predictive,
mechanistic step: a derivation that predicts a *secondary* observable
the Kepler fit had no direct access to. Nothing reaches the Newton step
without first surviving the Kepler step, and `rubric_mode: newton`
enforces a Generative Yield dimension that fails any submission that
clears the Kepler residual but predicts no new observable. Most
specification-gaming strategies collapse at the Newton step (where the
form has nothing to extrapolate), which is the gate the discipline is
designed around. The v2.0 Framer was reframed against this distinction
because some of the early framers were caught optimising for Kepler-step
parsimony at the expense of Newton-step content (the canonical instance
is `gp161_mdl_anti_goodhart`).

### Post-run discriminator wiring

Historical provenance: [GP-190](../../research_areas/seams/engine/GP-190_post_run_discriminator_daemon_seam.md).

When `enable_post_run_meta_audit` is set, the postloop translates the
meta-audit verdict into `workspace/next_discriminator_queue.jsonl` via
`proposals_from_meta_audit()`. If `enable_post_run_discriminator_queue`
is also set, durable artifacts are replay-scanned into
`workspace/next_discriminator_queue.replay.jsonl`. Both hooks are
fail-graceful and never alter champion selection or loop control. The
discriminator queue is what populates the *next* eigenquestion if the
Research Director picks the run back up.

### The gate library

Named gates that catch a specific failure mode at a specific structural
layer. Sample (about 60 gates in
[`src/ztare/gates/`](../../src/ztare/gates/)): `circularity_gate`,
`asymptotic_claim_discipline`, `chokepoint_declaration_gate`,
`bound_chain_consistency_gate`, `buckingham_pi_gate`,
`closure_leverage_gate`, `auxiliary_object_declaration_gate`,
`linear_observable_coercivity_gate`, `ansatz_survivor_gate`,
`continuum_limit_gate`, `threshold_dichotomy_branch_coverage_gate`. PDE/RD
workbench routes also consume exact rational gates such as
`moment_ratio_surplus_gate`, `finite_prefix_selection_gate`, and
`bounded_ratio_support_gate` when an estimate tries to spend average or prefix
surplus as threshold-measure payment. `event_family_binding_gate` checks the
separate carrier-transfer failure mode where a theorem proved on one event
family is consumed by a target event family with only shared vocabulary, labels,
or finite-prefix shape. It has strict `identity` receipts and a weaker
`dominated_injection` mode for transfers that are not equality but do provide a
pre-payoff injection, a domination inequality, and an explicit loss/error
budget. `positive_variation_bridge_gate` checks the signed-to-positive currency
exchange: a positive-variation label is not enough unless a
same-carrier numeric domination receipt is present before payoff.
`positive_variation_quotient_wash_gate` checks the quotient/net-channel
variant: if a net source law identifies many representatives, positive
turnover is not bounded by that net budget until a pre-payoff representative,
no-wash/no-null-cycle law, and no post-payoff grossing receipt are supplied.
`quotient_minimal_carrier_payment_gate` checks the opposite failure mode: an
infimum or minimal norm over representatives may remove wash cycles while also
removing the selected representative-level payment, so it requires a
pre-payoff selector, target-independent representative law, kernel-zero
production receipt, and production-preservation bound before the quotient
carrier can pay selected production.
`quadratic_quotient_descent_gate` checks quadratic selected-production claims
over a quotient: a source-minimal or energy-orthogonal representative is not
enough unless the source-kernel square term and polarized cross term are zero
or nonpositive before payoff, yielding an explicit quotient descent/bound not
defined by the target deficit.
`dimensionless_exponent_source_gate` checks the gap left by
dimensional/Pi analysis: powers of dimensionless variables, such as the square
in a stretch-rate cost, must be backed by a named analytic identity or
inequality fixed before payoff, not inferred from units alone.
`ambiguous_pi_pinning_gate` checks the adjacent free-Pi failure mode: when a
quantity is dimensionally representable but not unique because the sources
contain a dimensionless null direction, a physical/source pinning law must be
fixed before payoff on the same carrier or scope before the monomial can be
spent. Recognized source-pinning kinds include active-scale Reynolds identities
and active-scale Reynolds channel-estimate receipts. Callers still own the
substrate-specific inequality payload.
`nonadaptive_source_selection_gate` checks reinterpretation/extractor moves:
a source object, selection rule, owner binding, index map, and timing receipt
must be fixed before payoff, and the target deficit cannot define the source.
`no_rebilling_freshness_gate` checks budget/freshness arguments that assign
selected units to payment atoms: the assignment must be total on the prefix,
distinct or disjoint, fixed before payoff, same-owner/source, and bounded by a
multiplicity or overlap receipt so one atom cannot be counted as many costs.
`same_carrier_packing_gate` checks the stricter pec_j packing/no-reuse spend:
the source carrier, target payment family, assignment or injection map, same
carrier binding, overlap bound, finite-prefix budget, pre-payoff timing,
anti-nested-reuse receipt, and no-rebilling receipt must all be present before
local payments can be spent as a packed budget.
`metric_covering_selection_gate` checks the upstream covering theorem receipt:
it requires a metric or quasi-metric, source family, scale/radius function,
uniform doubling/Besicovitch constant, engulfing/eccentricity control,
pre-payoff selection rule, total coverage or paid omissions, same-carrier
binding, bounded-overlap conclusion, nested-child policy, and discarded-error
budget before a Vitali/Whitney/Besicovitch label can feed a packing spend. The
PDE workbench also carries a selected-prefix nonnegative-channel collapse
surface: if a nonnegative channel pays every selected target prefix and has a
finite channel budget, it is treated as the all-prefix budget itself. Signed or
current-theoretic cancellation and forced endpoint coalescence must be declared
as separate channels. Each gate is executable code. Each gate has a
charter-line that says *which* failure mode it exists to prevent.

### The Framer language

A bounded, symmetry-filtered, MDL-driven pre-solver phase that reduces the
description length of an invariant that is concise only after a coordinate
change. Prunes the transformation space with symmetry + dimensional filters,
walks the residual search tree with an `O(M log M)` per-axis MDL-greedy
search, and hands the best-MDL coordinate pair to the existing solvers.
Implemented in [`src/ztare/framer/`](../../src/ztare/framer/) (active framer,
search, collapse, enumeration, report) with gate enforcement in
[`src/ztare/framer_gates/`](../../src/ztare/framer_gates/). The [GP-152](../../research_areas/specs/active/GP-152_framer_architecture_spec_v1.md)
observe-mode hook fires inside the main loop at the post-mutation
`fit_parameters` site and writes `framing_report.json` without mutating
data, so a Framer claim is an auditable artifact alongside the substrate
fit.

### The Research Director: out-of-loop orchestration

The Research Director layer is for work that happens before or beside the
bounded validator loop: choosing the next question, splitting a hard problem,
building hostile counter-cases, preparing source surfaces, and deciding whether
an artifact is ready for an in-loop run. It does not replace the validator, and
its outputs do not become claims without the normal evidence and non-claim
discipline.

Implementation details include a
[next-question generator](../../src/ztare/research_director/eigenquestion_generator.py)
to scope a tick's central question, an
[hostile review-artifact generator](../../src/ztare/research_director/adversarial_packet_generator.py)
to manufacture counter-cases, [typed gap classification](../../src/ztare/research_director/gap_typing.py),
a [hostile review-artifact suite](../../src/ztare/research_director/hostile_packet_suite.py),
[primitive move cards](../../src/ztare/research_director/primitive_operator_cards.py)
with deterministic routing, optional semantic-atlas routing, and explicit route
provenance in the
[pattern action contract](../../src/ztare/research_director/pattern_action_contract.py).
Hard-residual and PDE estimate/carrier work route through `OP-HRD-01` and
`OP-PDE-01`, replacing the older local contract phrase lists,
a [pattern bank injector](../../src/ztare/research_director/pattern_bank_injector.py),
PDE-specific [estimate-craft ops](../../src/ztare/research_director/pde_estimate_craft_ops.py),
a [PDE work-unit gate](../../src/ztare/research_director/pde_work_unit_gate.py)
that refuses terminal gap verdicts without estimate derivations and a
falsifier review artifact, APN semantic bridge surfacing that emits `ns_apn_bridge`
edges from AlphaProof Nexus declarations into the workbench pack, exact
rational support/selection checks under
[`src/ztare/gates/`](../../src/ztare/gates/) for moment-ratio, finite-prefix,
bounded-ratio surplus payments, and event-family source/target binding, a
[single-spend audit](../../src/ztare/research_director/single_spend_carrier_audit.py)
for separated spend-channel surfaces, a [receipt-strength audit](../../src/ztare/research_director/receipt_strength_audit.py)
that flags Prop-only no-overlap/same-owner/no-reuse/payoff-independence receipts,
and a
[currency ledger](../../src/ztare/research_director/pde_currency_ledger.py)
for PDE estimate-craft moves, including explicit exchange-rate obligations for
nonnegative selected-channel payments versus signed/coalescent escape channels,
and boundary/local-energy invoices that must become same-stream no-reuse
finite-prefix budgets before they can pay selected recursive levels.

The project-intake surface sits before that boundary. `ztare project
source-init` creates the source-ingest directories plus
`raw/source_type_map.json` for typing raw documents before evidence compilation.
It does not create evidence claims or launch a loop. `ztare project
source-check` is the offline source-readiness preflight that
`make evidence-prepare` runs before workspace update and evidence compilation.
`ztare project source-index` writes a source-index receipt when source surfaces
are already fresh enough for review. Trace verifies that the indexed artifacts
still exist and match that receipt before admission. `ztare project
evidence-bind` binds legacy compiled outputs to the current compile-provenance
hash without refreshing evidence. `ztare project evidence-gap justify` records
a hash-bound resolution for a specific gap row without editing the gap
detector's output. It can target the latest, champion, or currently active gap
source, and writes through a project-local lock plus atomic replace so parallel
prep agents preserve each other's receipt rows.
Active gap rows now carry a recovery contract: `public_evidence` rows are
recoverable by out-of-loop public source or dataset work, while
`local_verification` rows are carried as local verifier, fixture, code/log,
preflight, receipt, or in-loop discriminator work. Trace and evidence briefs
expose the canonical route fields plus the
`ztare-evidence-gap-recovery-contract-v1` object, so `make evidence-fetch` and
graph-focus briefings consume the same structured contract directly.
Legacy prose inference is still supported for old rows, but the contract marks
it as `fallback_inference` with `schema_promotion_required`. Explicit route
fields are the preferred producer interface. Automated `make evidence-fetch`
now skips schema-promotion rows by default. `ALLOW_INFERRED_PUBLIC=1` is the
compatibility path for replaying old inferred-public gaps.
The evidence brief now leads with `## Next Action`: selected gap, target,
recovery kind, exact command when public-source fetch is valid, and a boundary
note when the gap must stay local. The compiler writes the same selected action
to `workspace/evidence_gap_action.json` so scripts and future UI surfaces do not
parse markdown.
Evidence compiles also write
`compiled_evidence_replay_manifest.json`, a stable identity contract over the
source binding, workspace snapshot or raw-cache replay mode, structured packet
hash, support-binding hash, rendered evidence hash, and evidence-gap action
hash. Use that manifest when a script or UI needs replay identity. Do not use
the rendered markdown alone as the stable key.
`ztare project evidence-replay --project <project> --json` verifies the
manifest against current files without calling a model. `ztare autoresearch
trace` includes the same replay report in `surfaces.evidence_replay` and blocks
run readiness when a required replay manifest is stale. Higher-level health and
synthesis reports present the combined user-facing state as evidence readiness
so readers do not need to reason across separate provenance, output, and replay
receipts.
`ztare project claim-support --project <project> --json` is the companion
demotion surface for claims inside compiled evidence. It reads the compiled
packet and current source index, then classifies each claim row as direct
source support, synthesized across sources, local/seed-only, mixed, missing
source refs, or unsourced. It does not claim semantic entailment. Its job is to
make weak source binding visible before reports or UI surfaces present a claim
as source-backed. The audit also reads the raw source files referenced by the
source index, verifies their stripped-source hashes, and emits bounded preview
context. If the source index points at missing or edited raw files, the audit
blocks even when the claim row still names a known `source_id`.
`ztare project intake` records project-brief files, source/evidence
references, non-claims, and next falsifiers so a task can be reviewed for later
in-loop autoresearch entry. A project brief can also seed `evidence_gap_contracts`
for the first local-verification targets. Validation canonicalizes them into
the same recovery-contract object used by graph routing, evidence fetch, and
the graph-focus briefing. `ztare project intake draft-from-compiled` can draft
the same project-brief shape from a compiled evidence artifact and its provenance, but
the ordinary validator still rejects stale source refs or missing falsifiers.
`ztare project prep-ledger` is only the optional
append-only prep ledger for project-brief blockers or missing artifacts. These commands do not
execute RD out-of-loop agent work or run the autoresearch loop. The `task`
field is the bounded work item that the router or loop may later evaluate once
the intake file has the required surfaces.

`ztare autoresearch trace` is the read-only review surface for that chain. Its
`carrier_chain` reports source-index freshness, output-binding status,
unresolved evidence gaps, intake/admission receipts, mutator briefing records,
graph-focus targets, and prediction-contract summaries. `readiness_canonical`
is the current intake-facing go/no-go status. `readiness` preserves older
status ids for compatibility. An intake file can carry `expected_command`
defaults. `ztare autoresearch run --intake ...` inherits those defaults unless
the caller supplies an explicit override, and `--preflight-only` verifies the
launch contract without model calls. `plan_preview` is the no-model-call
read-before-run surface over the same route: it lists the first command,
dependency order, worker roles, spend boundary, fallback policy, expected
workspace artifacts, and largest quality risk. Live runs pass the admitted
`--intake` payload into the mutator briefing context, so providers consume the
exact launch intake before falling back to conventional project-local intake or
legacy packet filenames.
Evidence-gap rows written by the loop are normalized at persistence time
through `ztare-evidence-gap-recovery-contract-v1`, so trace, evidence-fetch,
graph focus, and synthesis all read one contract shape that already classifies
public-source versus local-verification work.
A provider timeout or charged no-output event is surfaced as runtime risk,
a transport failure that leaves the research direction untouched.

The synthesis renderer now consumes that same read model when an autoresearch
surface is present. `make synth` writes a compact
`synthesis/autoresearch_review_context.json` from `ztare autoresearch trace`
and includes it with `thesis.md`, `current_iteration.md`, `evidence.txt`, and
review artifacts such as `public/CLAIM_SUMMARY.md`. It also writes
`synthesis/report_support_contract.json` before rendering. That contract
summarizes supported claims, unsupported or unresolved claims, blockers,
runtime caveats, evidence replay/output/provenance status, graph/evidence-gap
actions, and next actions, and is passed to the renderer, refinement step, and
QA step. If trace says the compiled-evidence replay manifest is stale or
required-but-unverified, the support contract carries that as a blocker and
reporting caveat. Optional absence of a replay manifest is normalized as
`not_required` in trace and health summaries while preserving the raw carrier
status for audit. The contract also records `synthesis_input_binding`, a digest
over the artifact files used to extract the ledger. An old unbound ledger or a
digest mismatch blocks the report until synthesis is regenerated. QA blocks
high-severity unsupported additions, unsupported
actions, distortions, overclaims, and similar failures, then allows a bounded
QA-guided repair loop before failing closed. A blocked support contract also
blocks final report promotion regardless of model QA score. The candidate
report and QA JSON remain inspectable. This is a read-only reporting
input, not proof that free-form prose has perfect action discipline. To reduce
that risk, the support contract now includes `report_action_authority` with
typed allowed-now, conditional, deferred, and forbidden-upgrade rows. Generated
multi-project reports resolve domain buckets from explicit project metadata,
rubric fields, or `project_charter.md` before falling back to slug heuristics,
so report grouping does not depend on example project names when metadata is
available. Generated
reports should choose actions from that structure, while the separate post-run
thesis synthesizer remains the state-changing path: it can compose and promote
a candidate thesis only through its own audit trail, judge threshold, and
margin over the full positive-score run baseline.

### Synthetic personas and debate orchestrator

Multi-mutator cold-shot diversity plus structured adversarial debate.
Personas registry at
[`src/ztare/personas/`](../../src/ztare/personas/) (registry + routing).
Debate machinery at
[`src/ztare/orchestration/debate_orchestrator.py`](../../src/ztare/orchestration/debate_orchestrator.py)
and
[`src/ztare/orchestration/friction_debate.py`](../../src/ztare/orchestration/friction_debate.py).
Named persona labels (Dijkstra, Knuth, Munger, etc.) are stylistic
shorthand for reasoning approaches, not claims about the persons. The
README's named-personas note is the canonical disclaimer.

### Commit-membrane daemon

Historical provenance: [GP-241](../../research_areas/seams/apparatus/cage/GP-241_canonical_membrane_first_opener_spec.md).

The epistemic verificator daemon is the *sole writer* of the official store
(experiment record + ledgers). The agent cannot hand-edit official state.
It submits a proposal and the daemon stamps or quarantines it. A
hand-written record is non-authoritative by construction. Sits between
the loop and the canonical ledgers.

### Work daemons

Long-running role processes that claim and run governed work. The
agent daemon is at
[`scripts/public/control/agent_daemon.py`](../../scripts/public/control/agent_daemon.py),
the closure daemon at
[`scripts/public/control/closure_daemon.py`](../../scripts/public/control/closure_daemon.py),
and the routine-reviews loop at
[`scripts/public/control/rd_routine_review.py`](../../scripts/public/control/rd_routine_review.py).
Daemons obey mandates and surface their actions in the transition log.
They do not write to canonical state without going through the
commit-membrane.

### Org-runtime tenant overlay

The applied cognitive-firm primitives: persistent role offices,
mandates, tasks, gates, preferences, transition logs, damage signals,
maintainer surfaces, and optional notification providers. The reusable
kernel lives in the sibling `cognitive-firm` repository. The `org/`
tree in this repo is the ZTARE tenant overlay. See
[`org/README.md`](../../org/README.md) and
[`organizational_primitives.md`](organizational_primitives.md).

### Scenarios: the composable use-case layer

A **Scenario** (`scenarios/<name>.yaml`) binds the governance kernel to a use-case without forking core code:
it declares which rubric drives the judge, run config, an optional Cage gate-package, and the typed capability
plug-ins to use. The filesystem is the registry (a new scenario is a dropped file); binding happens once,
engine-side (`src/ztare/scenarios/resolver.py`), with precedence explicit-flag > scenario > default. Capability
plug-ins satisfy structural `Protocol`s — **EvidenceProvider**, **Renderer**, **Solver**
(`src/ztare/scenarios/protocols.py`) — and self-register via `@capability(kind, name)`
(`src/ztare/scenarios/registry.py`); a mis-shaped plug-in fails loud at registration. A scenario's Renderer
emits artifacts into a per-scenario workspace home (`workspace/<run>/scenarios/<name>/`) — outputs, kept
separate from the charter (the pre-registered input). This is what lets the same claim-hardening kernel produce
domain deliverables (a governed spec / decision-memo / risk-register), not just a score. Afforded via the
`ztare scenario` CLI verb (list / show / validate / new / run / surface / annotate / reingest) and the workbench
`GET /api/scenarios` picker. First scenario: `product-manager`. See [`scenarios.md`](scenarios.md).

The product domain ships a template family (`providers/pm_templates.py`: product_spec, risk_register, prd,
launch_readiness, adr, rice — `adr` uniquely surfaces the governed `rejected` node; `rice` composes the governed
*inputs* to a score, never fabricated numbers) and a rubric library (`launch_readiness`, `prioritization`,
`strategy_review` — dropped JSON, no kernel change). Two kernel additions extend the governed-artifact layer:
**`assemble_verdict`** names the **decision hinge** by *counterfactual sensitivity* (toggle each assumption holds-vs-fails, rank by how far the verdict swings — not graph degree), with ties + a coverage score, so a
verdict reports which claim the decision rests on; and **`annotate`** is the *inverse* firewall — a document in,
the same document back with each sentence tagged by its claim lifecycle (BACKED / CONTRADICTED /
UNTESTED / INERT) against the governed map. Because a document is *input*, annotation never "fails": the
headline is a decision-critical-assumption count, and the same call upgrades UNTESTED → BACKED as evidence
lands. `annotate` and `reingest_gate` share one `align()` door (a document sentence ↔ a governed element).
Workbench surface: the "Annotate a doc" view over `POST /api/scenario-{surface,annotate,reingest}` (all
deterministic; the LLM only proposes spans, the kernel gates them).

**Dynamic plugin install.** Plugins install without editing core: scenarios + rubrics are data (created/edited
from the workbench **Projects → Plugins** manager or `ztare scenario new`, live immediately — the filesystem is
the registry); capability plugins are `@capability` `.py` files dropped into a plugin dir
(`$ZTARE_SCENARIO_PLUGINS` / `plugins/scenarios/`) and discovered on reload (`registry.reload()`). A `decision_brief`
Renderer plugin lays out the PM-facing decision flow from the governed data (presentation is the renderer's job,
not a kernel template). Consumption status: the rubric + renderer drive the whole run; `evidence_sources` are
consumed at the loop's evidence intake (a non-default `EvidenceProvider` like `structured_files` augments the
disk evidence, guarded); `gate_package` wraps the Cage factory (live seam, empty registry in v1); a `Solver` is
resolved for scenario/goal-type dispatch (no auto-solve step in the claim-hardening loop). Afforded via
`ztare scenario plugins` and `GET /api/plugins` / `POST /api/plugin-install`.

### Argument kernel (grounded verdict + minimal cores + warrants + test agenda + recompile)

The verdict over the governed graph is an **assumption-based truth maintenance system**
(`src/ztare/scenarios/argument_kernel.py`), built on classical theory — reused, not reinvented: the verdict is
**grounded (least-fixpoint) acceptance** over an assumption-based argumentation framework (Reiter & de Kleer,
AAAI-1987; Dung 1995; Bondarenko–Dung–Kowalski–Toni 1997); the decision hinges are **minimal cores** (ATMS
minimal environments / prime implicants) — which subsume the old single-toggle sensitivity *and* catch
jointly-pivotal assumption-sets it could not see; the "what to test next" **test agenda** is query-by-committee
active learning over the existing `information_yield_pricing` primitive (deterministic entropy, no priors);
edges carry **Toulmin warrants** typed by *re-executable checkability* — `W0` kernel certificate (a LeanMill
proof / `axiom_authority`), `W1` re-executable computation (recomputes from bound data; the gp-ansatz / fit
gates), `W2` verbatim quote binding, `W3` proposed-unchecked (an LLM edge, admitted but marked) — with the
verdict **monotone in warrant strength** (a conclusion is never more trusted than its weakest decision-critical
warrant). Also: a humane **`verdict_reason`** — a one-line, actionable reading of the status that separates
"BLOCKED because nothing is bound yet" (a workflow step, not a failure) from "BLOCKED because a tension is open,"
so the next action is obvious rather than a cryptic status; **dominators** (which claim sits on every
evidence→verdict path); and **incremental recompile** (`recompile`) — snapshot a decision baseline, recompute
against new evidence, and diff which claims flipped and whether the decision went stale. This is the domain-neutral lift of the discipline the formal substrate already
runs (`leanmill/theory_ir`, `formalization_admission`, `axiom_authority`, `axiom_yield`). Afforded via
`ztare scenario agenda | baseline | recompile` and the workbench "Decision freshness" surface. The strictly
determinism-preserving parts (no LLM, verbatim-not-semantic, all semantics at edge-admission) are ours; the
theory is classical and the LLM-argumentation application is a parallel-discovery frontier (Argumentative
LLMs / QBAF; Graph-of-Verification; Compliance-by-Construction Argument Graphs).

### Wager (a protected, verdict-preserving bet on a BLOCKED claim)

A **wager** (`src/ztare/scenarios/wager.py`) is a protected, thin-evidence *bet* on a claim the decision cannot
yet grade — a **BLOCKED** claim. The grounded verdict is symmetric in payoff: a bold bet with large asymmetric
upside grades identically to a thin-evidence dead end (both BLOCKED). A wager gives the bet dignity **without
laundering it into a fact**: the claim stays BLOCKED (a wager is *not* a fourth verdict — that would be an
idea-parking exemption), and the wager is a separate, ranked, expiring object that names the experiment which
would settle it. The uncompromising part is the **typed outcome→edit contract**: the author declares the test's
outcomes, and each outcome maps to typed edits that touch **evidence and warrants only** (`add_evidence` /
`support` / `attack` / `set_warrant`), each naming the exact node or edge it changes. No edit can set a verdict —
there is no such field — so `recompile` alone derives it. The kernel **simulates every declared outcome** by
`recompile` and records which move the decision: the human names the test, the kernel verifies the payoff-flip.
**flip is an admissibility gate, not the ranking signal** (so nobody games it): a wager is admissible iff its
outcomes are attested exhaustive, every edit is valid (fail-closed), and at least one outcome flips the decision.
Admissible wagers rank by `identification_bits` — a **prior-free** Shannon info-yield over the pre-baseline
minimal cores (junk authored after registration cannot pump it) — then by declared cost. The line that keeps it
clean: *bits and flips are computed* (deterministic functions of the graph); *dollars and odds are declared*
(shown, never aggregated into the score). Anti-laundering teeth: no simulated flip ⇒ not a wager; a passed
deadline **auto-expires** the wager back to the ordinary BLOCKED backlog; extending a deadline **requires a fresh
evidence/feasibility receipt**. Every building block is classical — value-of-information / experiment design,
optimism-under-uncertainty (UCB), Popperian falsifiability-as-information, the argument kernel's ATMS minimal
cores and counterfactual recompilation, Toulmin warrants; none is new theory. The plausibly-novel piece is the
*combination*: **prior-free experiment ranking over deterministically-recompiled warrant graphs, with a
verdict-preserving, anti-laundering wager lifecycle** — a claim we believe but have **not** yet verified against
the literature. A lightweight prior-art sweep found the neighborhood crowded (value-of-information over
argumentation; argumentative-LLM claim verification; counterfactual explanation in argumentation; prior-free
Blackwell informativeness) but no exact precedent for the full combination. Afforded via
`ztare scenario wager <list|add|sim|expire>` (`--json`) and the workbench **Bets** tab — a decision-language form
("if this result → supports / contradicts the claim") that assembles the typed edit contract under the hood.

### Graded argument strength (warrant-filtration QBAF)

The grounded verdict (`SUPPORTED` / `BLOCKED` / `REFUTED`) is crisp, and on a research
substrate almost nothing is ever fully settled — so nearly every live map reads
`BLOCKED`, conflating "grounded but still contested" with "ungrounded." Verified case:
`ai_capex` (a thesis backed by 9 sources, with 11 open challenges) and three theses with
no support at all all read the same crisp `BLOCKED`. `src/ztare/scenarios/strength.py`
adds a deterministic, prior-free **graded strength** per claim over the same bipolar
argument graph, computed by a gradual argumentation semantics: the **Quadratic Energy
Model** (Potyka, KR 2018), a damped forward-Euler iteration. QEM was chosen over
DF-QuAD (acyclic-only; ZTARE's maps have `CONTRADICTS` 2-cycles) and the h-categoriser
(attack-only; the graph is bipolar, support and attack both).

The design choice that preserves claim discipline is **warrant filtration, not cardinal weights**.
Mapping the Toulmin warrant classes `W0..W3` to numbers (0.7, 0.4, …) would smuggle a
prior — why 0.7? Instead the semantics runs four times over nested strata: stratum *k*
keeps only edges at least as checkable as tier *k* (`k=0` keeps `W0` only; `k=3` keeps
all). The output is a **strength profile** `(s0, s1, s2, s3)` — the thesis's strength if
you trust only kernel certificates, then +re-executable computation, then +verbatim
quotes, then +proposed-unchecked edges — built entirely from the warrant partial order,
with zero free parameters. `(0, 0, 0.97, 0.97)` reads as "a castle of quotes: well
supported, but nothing kernel-hard." Base scores are prior-free too: leaf evidence
scores 1, every internal claim/thesis/finding scores 0, so an unsupported open challenge
starts at strength 0 and cannot drag down a well-evidenced thesis — a challenge only
bites once it is itself evidence-backed. Support is also **collapsed per provenance
source** (max within a source, sum across sources) before aggregation, so fifty
redundant quotes from one source cannot saturate a stratum the way independent
corroboration does.

A crisp verdict can still override the number through an **override lattice**: `REFUTED`
(a surviving `W0`/`W1` attack on the thesis) beats `NONCONVERGENT`, which beats
`UNSUPPORTED` (no support at any tier), which beats `CONTESTED` (show the profile — the
status of essentially every live research map). Arithmetic never launders a kernel-grade
refutation into "strength 0.12."

The kernel also names **what the decision rests on**: `shapley_support` runs exact
removal-Shapley over the evidence sources — the characteristic function is thesis
strength given only that subset of sources present — so each source's contribution sums
exactly to the thesis strength (Shapley efficiency). On `ai_capex` it names the H100
price, the TDP figure, the AWS p5 price, and the SOFR rate as the decision-critical sources.
Exact up to 13 sources (2^n); past that it reports the source set and the most-connected
sources rather than fabricate a partial Shapley value. `shapley_support` is implemented
and selftested but not yet wired to a CLI or workbench surface — the comment in
`argument_kernel.py` marks it for the brief/"rests-on" surface. The cheaper `strength_profile`
call (a few fixed-point solves on a small graph) already rides the hot path: `argument_analysis`'s
JSON bundle carries a `strength` block (`profile`, `status`, `converged`), so
`ztare scenario agenda --project <slug>` and any consumer of that bundle gets the graded
read for free, additively, alongside the existing verdict/cores/warrants/agenda.

**Is it grounded? Does it work?**

Determinism is unconditional: the QEM update is Lipschitz, so the iteration's trajectory
is unique and bit-reproducible. Convergence to a unique fixed point is *proven* for
acyclic argumentation graphs in the gradual-semantics literature. For cyclic graphs — and
ZTARE's maps have `CONTRADICTS` 2-cycles — no universal convergence theorem exists in
this literature for any bipolar weighted semantics. That is a real limitation, not a
detail to paper over: the kernel surfaces `NONCONVERGENT` as an honest first-class state
when the iteration hits its cap, rather than emit a number reached by an unproven
process. Cycle resistance, separately, *is* a theorem: QEM's squashing function
`h(x) = max(0,x)² / (1+max(0,x)²)` satisfies `h(x) < x` on `(0,1]`, so a pure support
cycle with internal base weight 0 has 0 as its only fixed point — no self-lifting
bootstrap through the cycle. The filtration itself is the standard leximax-as-limit-of-weights
/ System-Z / preferred-subtheories stratification, applied to a bipolar QBAF, which is
why it needs no chosen numbers. Shapley attribution satisfies efficiency (contributions
sum to the total), symmetry, and the dummy property (Yin, Potyka & Toni, *Argument
Attribution Explanations*).

Empirically, the module's selftest covers: a 2-cycle between evidence-backed claims
converging under damping; an unsupported challenge failing to drag down a supported
thesis; a `REFUTED` override surviving on top of a nonzero raw score; and per-source
collapse (two supports from one source count once; two independent sources add up). On
real maps it activates and discriminates where the crisp verdict does not: `ai_capex`
reads `CONTESTED` at `[0, 0, 0.97, 0.97]` against three unsupported theses at
`[0, 0, 0, 0]`, all four of which the crisp verdict alone reports as the same `BLOCKED`.

Every building block here is classical, and several are direct prior art to cite rather
than claim: Shapley over a Quadratic Energy Model (Yin, Potyka & Toni, IJCAI 2024 — over
edges rather than sources; and the impact-measures line, AAMAS 2025); LLM outputs →
bipolar argumentation framework → gradual semantics (the ArgLLMs line, 2024); lexicographic
refinement over ordered strata (preferred subtheories / System-Z, Brewka 1989; stratified
labelings, Thimm & Kern-Isberner 2013); ordinal certainty levels instead of cardinal
weights (possibilistic argumentation). A reviewer-grade prior-art pass found no published
work doing the specific synthesis — a *continuous* gradual semantics (QEM) with cardinal
edge weights replaced by an external epistemic-*checkability* ordering of the edges, re-run
over nested strata and kept as an *uncollapsed* lexicographic profile. That synthesis is the
defensible novel core: a specific assembly no prior work combines, not a new primitive (the
nested-strata-to-profile skeleton is itself old). Present it as an assembly with its lineage
named — pitched that way it holds under review; pitched as inventing stratified argument
strength it does not.

### Gate metrology (measuring discrimination against a formal oracle)

`src/ztare/scenarios/metrology.py` measures whether the deterministic gates actually **discriminate** — catch
laundered/unsound arguments, pass sound ones — against labeled ground truth: a seed corpus (sound cases + one
per laundering family: orphan / paraphrase-drift / unlicensed-relation / bullet / qualifier-drop / unsupported),
a confusion matrix + precision / recall / MCC / Youden's J, and a per-gate positive-control battery (the seed
doubles as the "run the gold control" invariant). The genuinely novel piece is the **`formal_oracle_label`
hook**: for the formal substrate, ground-truth BACKED/CONTRADICTED comes from a **LeanMill kernel** (autoformalize
→ kernel-verify) — measuring soft-gate discrimination against a proof kernel, which nothing else in the
"AI research governance" space can do. Env-gated (`ZTARE_METROLOGY_LIVE_ORACLE=1`) so the selftest never fires a
live proof search.

---

## 2. Operating discipline (workbench-wide)

### Deterministic enforcement floor

Charter-committed gates as code, not LLM judges. A claim does not survive
unless a deterministic function over sealed holdout and farther-tail data
returns pass. Pre-registered hypothesis commitment (Hypothesis U vs. S,
etc.) recorded in `thesis.md` before evaluation. Mid-run pivots require an
explicit retire-and-commit, not a quiet rewrite. See
[`closure_claim_governance.md`](closure_claim_governance.md),
[`harness_specification.md`](harness_specification.md),
[`rubric_specification.md`](rubric_specification.md).

### Sealed-result discipline

When a sandbox closes, its directory becomes a sealed reference (gate
scores + thesis + generator script + SHA-256 fingerprints). A result can
be cited unambiguously without worrying about the live working area
drifting. The
[public claim register](../public_claim_register.md) points at the
per-project `public/CLAIM_SUMMARY.md` slice that summarises each sealed
result.

### Forecast pool and prediction market

Historical provenance: [GP-230](../../research_areas/seams/mission/org/GP-230_cognitive_firm_absorption_seam.md).

Sealed forecast contracts for macro / meso / micro branch choices, swarm
gates, effort estimates, and externality audits. Belief is recorded
*before* action. Calibration scoring runs ex-post. Implementation at
[`scripts/public/control/forecast/pool.py`](../../scripts/public/control/forecast/pool.py)
and
[`scripts/public/control/forecast/resolve_from_json.py`](../../scripts/public/control/forecast/resolve_from_json.py).
Spec under
[the forecast-pool decision-market spec](../../research_areas/specs/active/protocol/GP-230_forecast_pool_decision_market_spec.md).

The primitive's operational rules are empirically derived from its first
child seam, the [Forecast Calibration Program](../../research_areas/seams/apparatus/instrumentation/GP-245_forecaster_skill_calibration_seam.md)
([forecaster-skill calibration seam](../../research_areas/seams/apparatus/instrumentation/GP-245_forecaster_skill_calibration_seam.md),
public surface at
[`projects/llm_forecasting_calibration_program/public/CLAIM_SUMMARY.md`](../../projects/llm_forecasting_calibration_program/public/CLAIM_SUMMARY.md)):

- forecast rows collect a separately-elicited tail-worry token
  (`tail_insurance_premium`, int 1 to 100) alongside `p_success` and the
  decomposed risk channels. The tail token predicts per-row Brier
  independently of the point estimate across four replicated pilots.
- forecasters are kept blind to each other's outputs until resolution
  (architectural sealing, not behavioral instruction; two registered
  light-touch remediations are now on record as failing: rationale
  exchange and direct skeptical-instruction framing).
- a high tail-worry signal on a material contract routes to abstain-
  and-escalate (or to a fresh forecaster from a different model family
  that re-prices the same contract without prior-agent context). The
  naive "raise the act-threshold when worried" wiring degrades utility.
  Abstain-or-escalate restores it. Closed-loop cross-family re-decision
  improves Brier dramatically on the worried subset under asymmetric-
  favor-yes cost regimes.
- subscription-class forecasters are not used to schedule LeanMill or
  any reasoning queue by yield-prediction. The capability has been
  measured to perform worse than a constant-0.5 baseline on stratified
  proof corpora across all three agents in the trio, so queue policy
  stays oldest-ready-first or uses non-LLM heuristics.
- autoresearch iterations are not steered by forecast/Elo/Brier scores.
  The shared read model
  [`src/ztare/forecasting/prediction_contract.py`](../../src/ztare/forecasting/prediction_contract.py)
  normalizes existing forecast-pool contracts, scratch forecasts, prediction-
  ledger mirror rows, and project-local autoresearch receipts into scoreable
  rows with provenance. `ztare autoresearch trace` consumes that model through
  [`src/ztare/validator/autoresearch_prediction_contract.py`](../../src/ztare/validator/autoresearch_prediction_contract.py)
  and reports binary Brier against a constant-0.5 baseline in the
  `prediction_contracts` trace row. Treat this as a measurement lane
  until repeated resolved rows beat simple baselines and carry downstream
  decision receipts. Trace can block invalid prediction-authority claims, but it
  does not use prediction scores to route an autoresearch iteration. Only
  resolved forecast-pool rows in
  `forecast_pool` provenance mode can count as membrane-eligible. Scratch and
  in-loop rows are scoreable measurement receipts, not close evidence. The read
  model rejects post-hoc rows by requiring the forecast/seal timestamps to
  precede `resolved_at`. The executable boundary audit is
  `ztare audit forecast-capability --json` or `make forecast-capability-audit`.
- per-contract confidence is weighted by resolution horizon via
  `horizon_confidence_weight()` in
  [`scripts/public/control/forecast/pool.py`](../../scripts/public/control/forecast/pool.py)
  (linear decay from 1.0 at reference date to 0.5 at 180 days,
  floored at 0.1), with universal cross-family effect at $N{=}210$ pooled,
  $\rho(\text{days}, \text{err}^2) = +0.16$ $[+0.03, +0.29]$.
- new emission fields (`p_buy_yes_max`, `p_sell_yes_min` for bid-ask
  spread; `predicted_brier_lo`, `predicted_brier_hi` for self-predicted
  Brier interval) are accepted by both `cmd_add_forecast` and
  `cmd_scratch_forecast` with cross-field validation. Downstream
  consumers derive `spread`, `b_mid`, `b_width` from them.

The corresponding agentic implementation pattern is documented in
[`docs/concepts/agentic_engineering_patterns.md`](agentic_engineering_patterns.md)
Pattern 12 (Sealed Forecast Pool for Execution Control). The reflexive
counterpart is Primitive 9 (Reflexive Forecast Market) in
[`docs/concepts/reflexive_engineering.md`](reflexive_engineering.md). The
forecasting-role obligations live in
[`org/mandates/forecasting_agent_mandate.md`](../../org/mandates/forecasting_agent_mandate.md).

### Gaming behavior catalog and runtime guard

One layer with two faces. The durable record starts with the
original 9 specification-gaming strategies documented in the Cognitive
Camouflage paper, from Severity Averaging through Weak Baseline. Later
mined vectors and emerging patterns live in the
[`LLM Gaming Behavior Catalog`](../gaming_behavior_catalog.md) and its
[`Gaming Behavior Catalog Map`](gaming_behavior_catalog_map.md), where
the live registry, promotion evidence, and runtime gate status are kept
separate from the paper taxonomy. The runtime guard is the
precedent and gate stack checked as executable code against candidate code during the
loop. New behavior classes should enter through an
incident, reproducer, registry row, promotion receipt, and regression
before public prose treats them as stable. See
[`anti_pattern_catalog.md`](anti_pattern_catalog.md),
[`goodhart_at_every_layer.md`](goodhart_at_every_layer.md), and
`make gaming-catalog-audit` for the current coherence check. The audit now
requires four executable autoresearch anchors to fire through the live gate
code and requires a benign control to pass. That is a maintained anchor set,
not full coverage of every catalog row.

### Reflexive primitives (the workbench measures itself)

ZTARE runs on its own infrastructure. A weekly **capability-ROI
audit** re-mines every artifact and scores each primitive as engaged /
dead / never instantiated. Several primitives have been demoted by the
audit and recorded as dead. See
[`reflexive_engineering.md`](reflexive_engineering.md) and
[`agent_agnostic_recursive_gain.md`](agent_agnostic_recursive_gain.md).
Recent operations-intelligence candidates also pass through a typed
learning-promotion contract before they can become reusable checks:
nearest existing surface, nearest confuser, typed receipt, deterministic
validator, ex-post usage criterion, non-claim, and stop criterion. The contract
builder lives in
[`src/ztare/research_director/learning_promotion_contract.py`](../../src/ztare/research_director/learning_promotion_contract.py).

### Machinery governance

The machinery of the kernel is itself a governed object, extending the recursion one level past models and hypothesis language. The substrate-agnostic pieces live in `src/ztare/common/`.

The proposal-card contract carries a `certifier_touched` flag. Cards where the flag is set require conductor disposition before adoption. [Machinery Rules](../reference/machinery_rules.md) records the governing rules, each instantiating a primitive from the cognitive-firm draft §3 Table 1; the file sha is the version. `attest()` writes a hash receipt at every machinery disposition covering the card sha, rules sha, suite summary, and principal. Institutional independence and liability remain unbuilt by design, not omission.

`adopt_machinery_patch` follows a backup-apply-test-restore cycle against the frozen test suite. A certifier denylist blocks known bad patches. Only tighten-only changes auto-adopt; others require explicit ratification. An exogenous clock caps machinery proposal cards at three per run, then escalation. Certifier-touched proposals never auto-adopt regardless of content.

The three contradiction detectors are the current substrate instance. `excusal_hides_physics` flags classifier excusals that live play diverges on. `absorb_diverge_spiral` catches identification that absorbs evidence while play instantly re-diverges. The visible/holdout split detector surfaces disagreement between the selection arbiter and the holdout. The detector shapes are substrate-agnostic; current implementations read worldmodel artifacts. Any substrate with excusals, rounds, and holdouts can instantiate them.

### Research-yield decomposition

Historical provenance: [GP-233](../../research_areas/seams/apparatus/instrumentation/GP-233_research_yield_decomposition_seam.md).

Throughput is one coefficient in scientific yield. The seam contract
decomposes a research lane into
`candidate_supply × eligibility_rate × verification_compile_rate ×
residual_or_closure_rate × decision_impact / wall_time_or_cost`, names
the current bottleneck and next lever, and refuses to collapse them into
one scalar. The companion governance gate
(`gp233_adversary_yield_decomp.py`) four-way classifies Lean proof rows
under a `#print axioms` kernel guard that trusts only
`{propext, Classical.choice, Quot.sound}`. Controlling invariant: *zero
false ratification*. Evidence ledger at
`analytics/public/ledgers/research_yield_decomposition/`. See
[`closure_claim_governance.md`](closure_claim_governance.md).

### Action intelligence and operations surface

Historical provenance: [GP-243](../../research_areas/seams/protocol/GP-243_action_intelligence_loop_seam.md) and [GP-244](../../research_areas/seams/apparatus/instrumentation/GP-244_research_operations_intelligence_cockpit_seam.md).

A read-side surface that joins forecast use, yield bottlenecks,
experiment state, catch risk, source readiness, and observer-only
learning candidates without mutating official state. The reviewer can
see what is in flight, what is blocked, what risk is unclosed, and what
proposals are pending. Implementation at
[`scripts/public/control/action_intelligence.py`](../../scripts/public/control/action_intelligence.py).
Evidence ledgers under
[`analytics/public/ledgers/action_intelligence/`](../../analytics/public/ledgers/action_intelligence/).
The companion operations-intelligence report attaches source-readiness rows and
learning-promotion contracts, but keeps them diagnostic until a downstream
validator or ex-post usage row pays the claim.

### Audit-integrity chain manifests

A separate, layered tamper-evidence protocol over JSONL kernel logs.
Tamper-evidence is a *chain manifest* over the log, not a per-row
attestation, and it is a protocol the maintainer opts into for any log
they want to make tamper-evident. See
[`docs/guides/reflexive_audit_workflow.md`](../guides/reflexive_audit_workflow.md).

### Epistemic Airgap gate (cross-provider enforcement)

`require_cross_family` refuses to run a loop where the mutator and the
judge share a registered provider family (`openai`, `anthropic`, `google`,
`deepseek`, `kimi`, or `grok`). The gate raises `SystemExit` before any LLM
call. Default is warn-only.
`CROSS_FAMILY=1` in the Makefile is the standing posture for
`loop` / `experiment-loop` / `discover` / `honeypot-loop` targets.
This is the *loop-internal* discipline. The cold cross-provider pass
below is the on-demand, heavier version.

### Cold cross-provider pass

A self-serve check that dispatches a consequential architecture or
closure question to an independent external model at high reasoning
effort, then splits the verdict and Meta-Darwins its closing. Defends
against single-author blind spots. The pattern is described in
[`glossary.md`](glossary.md) and ships as an automated runtime move the
maintainer can fire on demand.

### Damage signals

Historical provenance: [GP-129](../../research_areas/seams/mission/org/GP-129_biological_org_design_panel_seam.md).

An orthogonal signal channel for system failures, constraint
violations, and mandate-compliance alerts, decoupled from
identity-based authorization. Any process can emit a typed damage
signal. Manager-agent mandates require listing active signals before
deciding the next action, so a downstream actor cannot proceed past a
named damage without explicitly addressing it. Implementation at
[`src/ztare/signals/damage.py`](../../src/ztare/signals/damage.py)
with auto-emit hooks at
[`src/ztare/signals/autoemit.py`](../../src/ztare/signals/autoemit.py).

### Supervisor and agent-rotation layer

Long-running daemons for multi-agent orchestration: agent-role
rotation (cycling reasoning styles), escalation management
(automatic promotion to cold-pass on repeated failures), inbox
velocity tracking (bottleneck detection), and LLM-budget guardrails
(spend tracking + pre-authorization gates). Lives under
[`src/ztare/supervisor/`](../../src/ztare/supervisor/)
(`agent_rotation.py`, `escalation_manager.py`,
`llm_budget_guard.py`, `spend_tracker.py`,
`agent_utilization_tracker.py`). Maintainer entry points at
[`scripts/public/control/agent_daemon.py`](../../scripts/public/control/agent_daemon.py)
and
[`scripts/public/control/closure_daemon.py`](../../scripts/public/control/closure_daemon.py).

### Self-demotion and recovery as discipline

The repository preserves the demotions of its own wrong causal stories
next to the original claims. Many entries in
[`public_claim_register.md`](../public_claim_register.md) are demotion
records, not promotion records. The canonical pattern
("judge correctly demotes overclaim, mutator regresses, judge reverts
on corrected derivation") has a sealed reference project the discipline
points at.

---

## 3. Named primitives

### Vocabulary escape and observable rotation

Under sealed gates the cage has forced an LLM mutator out of its
training-prior regression-toolbox vocabulary onto a maintainer-committed
non-elementary transcendental form (the Planck-sandbox calibration
recorded in the public claim register). When a target is incompressible
in one representation, the kernel automatically tries monotonic
transformations (`1/z`, `ln z`, `Δz`) and re-runs compression on the
transformed representation. The Ulam reciprocal compression was
discovered this way without human guidance. See
[`cognitive_gym.md`](cognitive_gym.md).

### Cross-mutator / cross-tool triangulation

Multi-mutator family runs (Gemini, Claude, GPT-4o) under the same
gates. Specification-gaming behaviour is mutator-family-specific, not
universal, and ZTARE records that. Cross-tool baselines: PySR
independently arrived at the same Lucky-number density coefficient as
ZTARE on the same observable. Cross-tool replication stands as a
citable triangulation, an independent tool reaching the same result.

### Grammar-vs-space diagnosis

The kernel distinguishes a grammar ceiling (the expression
language cannot write the answer) from a space ceiling (the mutator
does not search in the right mathematical category). The sopfr
(OEIS A001414) result is the canonical case: the grammar admits the
answer syntactically, but the mutator never reaches the prime-
factorisation category that would let it find one. The diagnosis
triggers a grammar or category extension, not a search-budget increase.

### Project readiness and constraint-to-DoF analysis

Before fitting, the kernel probes whether a project/evaluator surface is rich
enough to answer a question. The within-class feature-collapse finding on the
v2 RAR benchmark surface is the canonical case. The probe is a gate
(R26 G-CROSS-CLASS-FEATURE-SUPPORT), not an after-the-fact narrative.

### LeanMill governed proof-search solver

Historical provenance: [GP-246](../../research_areas/seams/engine/lean/GP-246_governed_dag_proof_search_seam.md). Current frontier.

The current LeanMill core is a governed best-first search over a
proof-obligation DAG around a swappable LLM leaf. The leaf proposes proof
moves. One governance kernel ratifies every closure through kernel compile,
axiom allowlist, matched negative control, anti-laundering checks, and
statement-integrity checks. A goal is closed only on a ratified closure, never
because an agent reports success.

The move space spans direct tactics, warm leaf calls, cold-shot fan-out,
external frontier provers, conjecture/decomposition, specialization,
generalization, falsification, tactic steps, symbolic witness transport,
corroboration, composite ratification, target-conditioned routing, boosting,
and isomorphism-decomposition. Shared compute lives in
`src/ztare/common/{sandboxed_python,symbolic_witness}.py`. The subsystem is
`src/ztare/leanmill/solver/**`. Full spec in
[`docs/concepts/leanmill_architecture.md`](leanmill_architecture.md) and
[the governed DAG proof-search seam](../../research_areas/seams/engine/lean/GP-246_governed_dag_proof_search_seam.md).

*Status:* soundness governance is the validated part. The governance kernel
catches gaming and laundering modes that bare `compile_ok` misses, including
statement alteration, vacuity, axiom smuggling, and in-proof leakage. Measured
lift over a strong bare leaf is still mostly unproven: easy proof targets
saturate and open-conjecture-hard targets still fail. LeanMill is a governed
environment around a frontier leaf, not a trained prover. Whether the
environment multiplies that leaf remains under active matched-baseline
measurement. The older
[GNN lemma-relevance ranker](../../research_areas/seams/engine/lean/GP-225_gnn_lemma_relevance_ranker_seam.md)
and Lean station workers (`scripts/public/control/leanmill_*`) remain the
lower-level station layer beneath this solver.

### Power-aware experimental statistics

Historical provenance: [GP-245](../../research_areas/seams/apparatus/instrumentation/GP-245_forecaster_skill_calibration_seam.md).

A single-file general-purpose statistics module that codifies the experiment-discipline used across pilot rounds: Fisher-$z$ power computation, proper equivalence testing, multi-comparison correction, OLS with leave-one-out cross-validation, three legal verdicts, and a Bayes factor wrapper. Lives at
[`src/ztare/experiment_stats.py`](../../src/ztare/experiment_stats.py).
Thirteen public functions:

- Power before fire: `n_required_for_rho(target_rho)`, `detectable_rho_at_n(n)`, `n_required_for_brier_delta(delta)`: Fisher-$z$ sample-size computation. Pre-registration discipline: no pilot is fired without `n_required` written down first.
- Correlation with CI: `spearman_rho(xs, ys)`, `spearman_rho_with_ci(xs, ys, ci=0.95)`: Fisher-$z$ transform 95% CI.
- Difference tests: `paired_permutation_test(a, b)`, `bootstrap_ci(values)`, `bf_bic_paired_t(a, b)`: paired Δ-testing with BIC-approximation Bayes factor (Wagenmakers 2007).
- Equivalence testing: `tost_equivalence(a, b, equiv_bound)`: proper `h0_kept` claims via two one-sided tests at a pre-stated bound, not "p > 0.05".
- Multiple comparison: `bh_fdr(p_values)`: Benjamini-Hochberg false-discovery-rate correction across panel tests.
- Multi-channel R² without overfitting: `ols_multichannel_r2(xs_cols, ys)` returns R², adjusted R², and leave-one-out R²_LOO, the audit-clearing test against in-sample-fit noise at small N. The meta-Darwin audit flagged "R² without LOO at small N" as a recurring program error. This function makes the correct report unavoidable.
- Three legal verdicts: `power_aware_verdict(observed_rho, n, target_rho)` returns one of `h1_supported` / `h0_kept` / `inconclusive_underpowered`. `h0_kept` requires the CI to wholly exclude $\pm$target_rho, otherwise the verdict is `inconclusive_underpowered`. The "underpowered null misread as h0_kept" error is what the [Forecast Calibration Program](../../research_areas/seams/apparatus/instrumentation/GP-245_forecaster_skill_calibration_seam.md) found in 8 of 12 of its own earlier nulls. This resolver makes the correct verdict unavoidable.
- Reproducibility manifest: `reproducibility_hash(prompt_template, dispatcher_version, corpus_row, agent_id)`: per-call SHA-256 of inputs so any score row can be audited back to the exact prompt + corpus row that produced it.

Codified disciplines that the toolkit supports (referenced by [`AGENTS.md`](../../AGENTS.md) §6n.6 to §6n.9):

- Power before fire. Every pilot ships with `n_required` from `n_required_for_rho` written into the pre-registration row before the first call.
- Three legal verdicts, no fourth. Findings resolve to `h1_supported` / `h0_kept` / `inconclusive_underpowered`. The "I tried, got p>0.05, calling it null" verdict is now `inconclusive_underpowered` unless the equivalence-bound condition is met.
- LOO-CV at small N. Multi-channel R² claims at $N < 30$ with $k \geq 3$ regressors carry LOO alongside in-sample. The meta-Darwin audit retracts findings reported without it.
- BH-FDR across panel tests. Per-family panel tests (5-family $\times$ multi-intervention) carry BH-FDR adjustment when reported.

The meta-Darwin retract-and-retest pattern (audit every claim post-hoc against the discipline, retract anything that fails, re-fire if a retest disambiguates) is documented in the pattern catalogue and applied to all [Forecast Calibration Program](../../research_areas/seams/apparatus/instrumentation/GP-245_forecaster_skill_calibration_seam.md) findings (`projects/llm_forecasting_calibration_program/forecaster_skill_calibration_v1/workspace/meta_darwin_audit_2026_05_27.md`).

### Forecasting-program calibration database and Brier/Elo stats

The general-purpose tooling for any binary-forecast calibration program. Both modules were hoisted 2026-05-27 from the [Forecast Calibration Program](../../research_areas/seams/apparatus/instrumentation/GP-245_forecaster_skill_calibration_seam.md) workspace into `src/` so future calibration programs can reuse them as a library. The historical CLI paths in `projects/llm_forecasting_calibration_program/forecaster_skill_calibration_v1/workspace/` survive as thin shims that import from canonical copies.

- [`src/ztare/forecasting/calibration_db.py`](../../src/ztare/forecasting/calibration_db.py): SQLite schema (three tables: `contracts`, `pilot_calls`, `pre_registrations`), idempotent DELETE-then-INSERT ingest (so re-ingesting a fired JSONL is safe), per-call Brier auto-computed from `y_known`, normalised primitive/family/pilot_id fields. CLI: `init`, `ingest-corpus`, `ingest-pilot`, `ingest-all`, `query`, `stats`, `prereg-add` (auto-computes `n_required` from `--target-rho` via Fisher-$z$ power), `prereg-resolve`, `prereg-list`. The pre-registration table makes "you said you'd need N=42 to call a `h1` here" auditable.
- [`src/ztare/forecasting/calibration_stats.py`](../../src/ztare/forecasting/calibration_stats.py): forecasting-specific stat wrappers on top of `ztare.experiment_stats`. CLI: `brier-ci`, `delta-test` (paired Δ-Brier with bootstrap CI + Bayes factor), `spearman` (per-family ρ + 95% CI + verdict), `elo` (cross-pilot Elo ranking across families), `finding` (replication-harness checking a named finding against current DB state), `power-n`, `power-detectable`, `tost`, `brier-decomp` (Murphy reliability/resolution/uncertainty), `verdict` (resolves a finding to one of three legal verdicts).

The forecasting-program-specific pieces remain in `projects/llm_forecasting_calibration_program/forecaster_skill_calibration_v1/workspace/`: the per-pilot dispatchers (`run_pilot_v28_dispatch.py` and siblings), the corpus sourcers (`extend_corpus_v25_*`), the keyword tagger (`topic_tag.py`), and the program's research log + pilot queue. Those are not generic and should not be hoisted. The split is "general toolkit in src/, pilot-specific orchestration in workspace/".

### Lean / formal-verification bridge

A Lean 4 compiler generates proof stubs for surviving claims: `#eval`
blocks that verify gate bounds at every holdout point, plus PSLQ
conjectures mapping fitted floats to candidate mathematical constants.
The Navier-Stokes campaign carries sorry-free Lean scaffolding modulo
named axioms (typed infrastructure, not analytic-PDE closure). See
[`ztare_proofs/`](../../ztare_proofs/).

---

### Recent additions tracked through July 2026

- Consumer-indexed factored search (`src/ztare/common/factored_search.py` plus
  `src/ztare/worldmodel/compiled_fiber_planning.py`): accepted carrier effects
  lower into opaque transition equality, ordered feasibility, terminal-edge,
  and allocation callbacks. The LS20 normal self-play caller emitted paired
  compile/first-fire receipts and advanced the adapter task edge; transfer to a
  different ontology remains untested.
- Canonical MDL/BIC engine (`src/ztare/fit/mdl.py`): `bic` / `bic_from_loglik` (de-duped from compress_champion's inline copies) + the two-part-code `MDLLibrary` (a Strategy interface). Consumed by autoresearch (compress_champion) and leanmill (lemma-library pruning).
- LeanMill calibration (`src/ztare/leanmill/solver/move_calibration.py`): recursive self-tuning `selection_priors` shifts each move's estimated close probability from compile-only evidence toward ratified outcomes as governed data accrues. `select_calibration_model` uses BIC to decide split-by-error-class vs pooled calibration. Recorded forecasts carry Brier/Elo statistics.
- Constraint-to-isomorphism engine (`src/ztare/common/constraint_isomorphism.py`, see §1): provider-flexible isomorphism surfacing for constraint families and proof/search surfaces.
- Autoformalization + faithfulness firewall (`src/ztare/leanmill/solver/autoformalize.py`, opt-in): NL→Lean via a frozen leaf, gated by governance-as-faithfulness: compile, non-triviality, non-vacuity, structural preservation, and a directional cold cross-family judge. It fails closed because a false accept would fabricate success. It routes through the existing governance kernel, reusing that path. Efficacy remains unproven.
- Isomorphism-surfaced default-off levers (`governance_organs.py` MDL-generativity + Schwartz-Zippel [advisory]; equiv-keyed proof cache; reachability invent-criterion). Built, self-tested, and parity-safe. Lift remains mostly unproven because easy-target A/Bs came out null. The discriminating measurement needs a critical-difficulty proof target. Full status: `leanmill_architecture.md`.
- Three-tier proof reuse (`src/ztare/leanmill/solver/proof_cache.py`): the α-keyed within-run cache (binder axis) + semantic-defeq reuse (`defeq_reuse_candidate`, default-on), `semantic_premise_shelf` embeddings RETRIEVE cross-vocab candidates, the kernel `@goal=@cand:=rfl` oracle VERIFIES before any cite (similarity never closes; the cite is re-verified by governance), and theory-identity (`autoformalize_notes.theory_consolidation` refuses to re-formalize a RESET substrate that has prior banked facts, the AMM vocab-orphan prevention). Sound by construction; metamorphic guards in `tests/test_leanmill_agentic_invariants.py` fail on the pre-fix code.
- Warm-compile door (`agentic_leaf.verify_lean_proof` + `v33_preflight._compile_probe`, default-on): the leaf ratify gate and the audit/composite compile route through the pre-elaborated warm campaign env (the SAME compile + `#print-axioms` gate, fail-closed) when a substrate is registered, eliminating the recurring cold-`lake env lean` Mathlib-re-import tax (592 to 1016s heavy-substrate); cold fallback when no substrate.
- Single-door closure invariant + deterministic conjunctive split (`governed_dag_search`, `isomorphism_decompose.derive_conjunctive_dag`): `status=="closed"` ⟺ a kernel-verified `proof_text` exists (no status-flip false-clean); a top-level `∧` target is split mechanically into its conjuncts and assembled via `composite_ratify`. Kernel-validated end-to-end.
- Campaign-start P0 forecast (`forecast_router.forecast_campaign_p0`): predicts expected yield + time-to-closure + cost from per-lemma `P(close)` × the domain's historical mean time (`phase_timing`), logged at campaign start and scored ex-post against the actual (the self-learning loop via `reweight`). Enables admissibility filtering + budget focus; validated by backfilling the filed campaigns (APR/AMM/Topkis).

## Current boundaries

Concrete non-claims, listed so a reader is not left guessing:

- No fully autonomous research replacement. ZTARE has autonomous loops and
  agent workers, but the human maintainer remains an uncontrolled variable and public
  claims still require bounded evidence, checks, non-claims, and saved review
  files.
- No domain-knowledge replacement. ZTARE does not substitute for
  an expert physicist, mathematician, or biologist.
- No autonomous optimizer or RL routing of governance state. Outcome
  signals are recorded. Tenant policy decides whether and how to route on
  them.
- No claim that any single high-variance substrate (NS, gravity, neural,
  consciousness) is solved. The claim register records bounded results.
- No claim that primitive prose improves agent outputs in general. The
  surviving agent-facing positive is narrower: source-bound,
  action-constraint-carrying contracts can make audit intent recoverable
  to a downstream consumer. Passive primitive prose is inert under the
  tested designs.
