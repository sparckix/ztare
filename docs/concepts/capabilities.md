---
description: "What the apparatus actually has: the architectural stack, operating discipline, and named primitives, each grounded in a module or deeper doc."
---

# Capabilities

> **Up:** [`docs/README.md`](../README.md)

What the apparatus actually has. This page is the "what does this run" surface,
sized to be read in five to ten minutes. Each capability points to the deeper
doc or the actual module that implements it; nothing here is a claim that is
not grounded somewhere else in the repository.

The page sits between three neighbours:
[`system_position_and_module_map.md`](system_position_and_module_map.md) is the
architectural framing; [`architecture.md`](architecture.md) is the
implementation map; [`public_claim_register.md`](../public_claim_register.md)
is the per-substrate result surface;
[`evidence_atlas/README.md`](../evidence_atlas/README.md) is the
reviewer-facing evidence crosswalk; [`priority_roadmap.md`](../../priority_roadmap.md)
is what is next.

The capabilities are organised in three layers: the **architectural stack**
(what the system is), the **operating discipline** (what it does, across
substrates), and a short list of **named primitives** (specific reusable
tools).

---

## 1. The architectural stack

### Cage Orchestrator (GP-157) — top-level substrate dispatcher

Sits above every constraint layer below. Reads `substrate.meta['class']`,
queries each gate's `can_handle()` predicate, and runs gates in a
dependency-ordered DAG so a Lean-proof substrate, a PDE substrate, and
an integer-sequence substrate each route through a different
gate-and-judge ordering without operator intervention. Mode is per
substrate class: `off` / `observe` / `authoritative`. Lives in
[`src/ztare/gates/registry.py`](../../src/ztare/gates/registry.py),
[`src/ztare/gates/substrate_evaluation.py`](../../src/ztare/gates/substrate_evaluation.py),
and the symbolic-logic dispatcher
[`src/ztare/gates/symbolic_logic_cage.py`](../../src/ztare/gates/symbolic_logic_cage.py).

### Statistical meta-diagnostics (GP-166) — pre-loop substrate classification

Runs *before* the first iteration. A noise-profile classifier probes
the substrate for heteroscedasticity, non-Gaussian residuals,
autocorrelation, and errors-in-X, and *auto-routes* the solver
configuration (fit-score mode, grammar tier, gate-DAG order) before any
mutator call. The point is that the apparatus does not assume the
operator got the data epistemology right — it measures it.
Implementation at
[`src/ztare/diagnostics/noise_profile.py`](../../src/ztare/diagnostics/noise_profile.py)
with companion substrate critic at
[`src/ztare/diagnostics/substrate_critic.py`](../../src/ztare/diagnostics/substrate_critic.py).

### In-loop validator: the iteration pipeline

A loop that proposes, fits, and adversarially tests claims under deterministic
gates. One iteration runs through a fixed pipeline; the relevant entry points
are catalogued in a maintainer-only architectural map for audit.
Per-iteration: **rubric pre-flight → prepare
candidate → mutator call → prompt assembly → fit → compression → gate
battery → judge → information-yield → pivot/close.** A rejection at the
candidate-preparation stage (lint, AST, NameError, KeyError, missing
`I_model`/`PARAMETRIC_FORM`) is recoverable: the **Compiler Bounce** retry
gives the mutator up to three in-place re-prompts with the specific error
injected, costing ~$0.05/retry vs. ~$0.40 for a full iteration; the iteration
counter does not advance during retries. Lives under
[`src/ztare/validator/`](../../src/ztare/validator/),
[`src/ztare/fit/`](../../src/ztare/fit/),
[`src/ztare/composition/`](../../src/ztare/composition/), and
[`src/ztare/orchestrator/`](../../src/ztare/orchestrator/).

### Grammar tiers and the EML primitive

The expression language is tiered, not unbounded. `fit_expression_grammar`
takes one of: `eml_only` (only the EML primitive `eml(x, y) = exp(x) − ln(y)`
plus arithmetic), `math_exp_only` (arithmetic + `math.exp`), `math_exp_trig`
(adds `math.sin`/`math.cos`/`math.tan`), `py_exec` (sandboxed Python with
authorised primitives like `isprime`, `factorint`, `primefactors`, `divisors`,
`gcd`), or `omit`. EML is the canonical "single composite primitive" used in
the Planck-sandbox vocabulary-escape calibration: by giving the mutator one
fused exp/ln operator, the apparatus forces *categorical* invention (the
mutator must build composites *out of* the primitive) rather than vocabulary
drift. `py_exec` is gated by an explicit `py_exec_authorized_by` rubric flag
plus an `expression_byte_budget` ceiling, enforced fail-closed at
rubric-preflight.

### Fit primitives and Stage 1/2/2.5 compression

A fit primitive (`scipy.optimize.curve_fit` and multi-start variants)
estimates parameters on visible evidence only; deterministic holdout +
farther-tail gates enforce generalisation. The compression primitive then
strips overparameterised surrogates:

- **Stage 1** enumerates 22 additive templates over `√n`, `ln n`, `n^b`,
  `e^{an}`, `1/n` with selection by BIC inside topology classes and an
  exponent grid `{0.25, 1/3, 0.5, 2/3, 1, 1.5, 2}` constraining free
  power-law exponents.
- **Stage 2** activates only when Stage 1 returns no gate-passing form: 13
  depth-1 compositional templates such as `√(n / ln n)` (which is how the
  Vaughan prime-partition form was first reached). Component D seed
  selection uses BIC sort + topology diversification so the next iteration
  is not trapped in one family.
- **Stage 2.5 (observable rotation)** applies monotonic transforms
  (`1/z`, `ln z`, `Δz`) when Stage 1 and Stage 2 both return no
  gate-passing form, and re-runs compression on the transformed
  representation. This is how the Ulam reciprocal compression
  (`n / U(n)`) was discovered without operator guidance.

The fit-primitive-features path (GP-156 Proposal 3) writes
`workspace/fit_features_result.json` with per-parameter init-range
auto-escalation (5×, 25× widening on flat-desert) and substitutes the
fitted `MODEL_PARAMS` into the in-memory `python_code` via AST rewrite —
no disk round-trip during the substitution.

### The Mutator Briefing (five providers)

Before the mutator is called, a structured pre-prompt is assembled by five
deterministic providers under
[`src/ztare/orchestrator/briefing_providers/`](../../src/ztare/orchestrator/briefing_providers/):
**fit_telemetry**, **gate_gap**, **iter_trajectory**, **row_outliers**, and
**asymptote_deviation**. Each provider writes its own section; the resulting
`workspace/mutator_briefing_iter_NNN.md` is persisted per-iteration for
operator audit, and adding a future provider is one file plus one line —
not a redesign.

### Component A (positive-space) and Component B (negative-space) extractors

Two structural extractors named for the side of the search space they read.
**Component A** is the positive-space extractor (GP-061.A,
[`src/ztare/gates/structural_constraint_extractor.py`](../../src/ztare/gates/structural_constraint_extractor.py)):
it surfaces features that *are present* in the current evidence as candidates for the
next form. **Component B** is the negative-space / void extractor
(GP-061.B,
[`src/ztare/gates/negative_space_extractor.py`](../../src/ztare/gates/negative_space_extractor.py)):
it surfaces *what is structurally missing* — feature-bag gaps
the mutator systematically avoids. Component B's canonical instance is the
Planck-sandbox-08 post-mortem, where it mechanically surfaced
`EMLCALL(arg0|has_op:Pow)` as a dense void on a corpus of 8 failed
families. Both write to the derived-constraints ledger
([`src/ztare/gates/derived_constraints.py`](../../src/ztare/gates/derived_constraints.py));
only confirmed constraints render into the mutator prompt.

### Component C (topological sieve) and Component D (topology synthesizer)

Two layers further down the constraint stack. **Component C**
([`src/ztare/motion/residual_analyzer.py`](../../src/ztare/motion/residual_analyzer.py))
is the topological sieve: a deterministic 2-bit residual-shape
descriptor that classifies a fitted form's residual as smooth,
periodic, or pathological, narrowing the corrector-library
recommendation *without oracle leakage*. **Component D**
([`src/ztare/composition/topology_synthesizer.py`](../../src/ztare/composition/topology_synthesizer.py))
is the topology synthesizer: when the additive and depth-1
compositional templates exhaust, Component D composes new candidate
forms via LLM-guided depth-2 templates, deterministic ratio probes,
tail-correction primitives (GP-087 residual-driven seeds), and
additive regime composition (GP-103 additive composite). Component D
runs in lifecycle phases (G1, G1.5, G2) with explicit seed-queue
source tags so an operator can audit which iterations were
mutator-driven vs. composition-driven.

### Information-yield evaluator and stagnation pivots

A per-iteration evaluator tracks whether the mutator's current functional
class is still producing new structural information. **Class-novelty
stagnation decoupling** (Task 12, 2026-04-24) lets the loop register
stagnation on the *class* of forms even when the iteration counter
increases. A **committee-rotation throttle** prevents the same judge
panel from re-affirming a stuck class. Stagnation thresholds are
resolved through `pivot_heuristics.resolve_stagnation_pivot_state()` —
one source of truth for prompt assembly *and* event logging. **GP-216
op-class pivot enrichment** maps current failure-log signals (e.g.
`profile decomposition`, `lower-semicontinuity`, `limit-passage`,
`finite certificates`, `global Sobolev`) into named operation classes
(e.g. `patches_dont_glue_globally` → `core_04 Local-to-Global
Assembly`) and rewrites the mutator instruction text — advisory only;
the pivot itself is data-driven.

### DAG steering (GP-134)

Before each mutator call, the apparatus computes a steering context from
the probability DAG of prior iterations — which nodes have survived,
which have been demoted, which open questions remain. The mutator
receives the DAG context as part of the briefing, so structurally
similar lines that have already failed are not re-proposed under a
different rename.

### Invariant-search mode: Lagrangian derivation + Buckingham π + Noether variance

A specialised `rubric_mode: invariant_search` enables a chain of
physics-motivated gates. **GP-180 Lagrangian Derivation Primitive**:
when the mutator declares `LAGRANGIAN`, `Q_VARIABLES`, `BACKGROUND`,
`PREDICTION`, and `SYMMETRIES`, the apparatus derives a closed-form
prediction and captures Noether invariants. **GP-179 Buckingham π gate**:
AST-walks the fit form for transcendentals applied to raw dimensional
arguments and refuses fits where the dimensional content is incoherent
(strict mode skips the fit; soft mode surfaces a briefing note).
**GP-180 Noether-variance loss**: adds `λ · CV²(Π)` per declared
invariant to the loss so the optimiser pays for variance in any quantity
the mutator asserted is conserved.

### REFRAME and ANALOGY — the two non-grammar primitives

REFRAME enumerates coordinate transforms `(h_in, h_out)` the operator's
prior would not try, ranks them by MDL on the actual data, and tells the
apparatus which frame the data prefers. ANALOGY queries an LLM for
cross-domain forms whose structural shape matches the failure surface,
breaking out of the home discipline's repertoire of templates. Both are
explicitly anti-anchor: they succeed only when they propose something the
operator's prior would have suppressed. Implementations live in the
analogy / framer trees referenced in
[`cognitive_gym.md`](cognitive_gym.md).

### Constraint-to-Isomorphism engine (the strange loop) — substrate-agnostic

`src/ztare/common/constraint_isomorphism.py` generalises ANALOGY beyond
curve-fit residuals into a canonical INTERFACE any consumer plugs into
(Strategy pattern, like `fit.mdl.MDLLibrary`). When a system hits a
structural ceiling it (1) abstracts the failure to a domain-stripped
`ConstraintFingerprint` (pure topology/complexity/algebra), (2) queries an
LLM with ONLY that abstract constraint — and a `forbidden_domain` to push
away from — to surface established theorems from any field that solve it
(the "orthogonal jump"; stripping semantic gravity is *why* it can reach a
match that direct prompting can't), and (3) compiles each match to a gate
and holdout-verifies it via the consumer's `oracle` (MDL / closure rate /
MRE) — only matches that improve the metric survive. The general engine is
shared; each consumer implements `StrangeLoopDomain` (`abstract_failure`,
`compile_to_test`, `oracle`). `fit/analogy.py` (GP-164) is the validated
curve-fit specialisation and remains in-loop; leanmill and the research
directors are the intended new consumers. **Efficacy is unproven** — the
apparatus exists; whether the autonomous query surfaces useful matches vs.
plausible nonsense is the open test. Surfaced by the `primitive_amnesia`
precheck (run it before building lateral-search machinery). The SOP for
wiring any new primitive into the precheck is
[`primitive_surfacing.md`](primitive_surfacing.md).

### Kepler vs Newton — two observable layers, judged separately

A gate-and-judge layer distinguishes two layers of explanation. The
**Kepler step** is the empirical fit on visible evidence — a curve that
reproduces the observed numbers. The **Newton step** is the predictive,
mechanistic step — a derivation that predicts a *secondary* observable
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

### Post-run discriminator wiring (GP-190)

When `enable_post_run_meta_audit` is set, the postloop translates the
meta-audit verdict into `workspace/next_discriminator_queue.jsonl` via
`proposals_from_meta_audit()`; if `enable_post_run_discriminator_queue`
is also set, durable artifacts are replay-scanned into
`workspace/next_discriminator_queue.replay.jsonl`. Both hooks are
fail-graceful and never alter champion selection or loop control. The
discriminator queue is what populates the *next* eigenquestion if the
Research Director picks the run back up.

### The gate library (catalogue)

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
and active-scale Reynolds channel-estimate receipts; callers still own the
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
finite channel budget, it is treated as the all-prefix budget itself; signed or
current-theoretic cancellation and forced endpoint coalescence must be declared
as separate channels. Each gate is code, not a prompt; each gate has a
charter-line that says *which* failure mode it exists to prevent.

### The Framer language

A bounded, symmetry-filtered, MDL-driven pre-solver phase that reduces the
description length of an invariant that is concise only after a coordinate
change. Prunes the transformation space with symmetry + dimensional filters,
walks the residual search tree with an `O(M log M)` per-axis MDL-greedy
search, and hands the best-MDL coordinate pair to the existing solvers.
Implemented in [`src/ztare/framer/`](../../src/ztare/framer/) (active framer,
search, collapse, enumeration, report) with gate enforcement in
[`src/ztare/framer_gates/`](../../src/ztare/framer_gates/). The GP-152
observe-mode hook fires inside the main loop at the post-mutation
`fit_parameters` site and writes `framing_report.json` without mutating
data, so a Framer claim is an auditable artifact alongside the substrate
fit.

### The Research Director (out-of-loop orchestration)

The out-of-loop research orchestration layer: an
[eigenquestion generator](../../src/ztare/research_director/eigenquestion_generator.py)
to scope a tick's central question, an
[adversarial packet generator](../../src/ztare/research_director/adversarial_packet_generator.py)
to manufacture hostile counter-cases, [typed gap classification](../../src/ztare/research_director/gap_typing.py),
a [hostile packet suite](../../src/ztare/research_director/hostile_packet_suite.py),
[primitive operator cards](../../src/ztare/research_director/primitive_operator_cards.py)
with a deterministic routing surface, a
[pattern action contract](../../src/ztare/research_director/pattern_action_contract.py),
a [pattern bank injector](../../src/ztare/research_director/pattern_bank_injector.py),
PDE-specific [estimate-craft ops](../../src/ztare/research_director/pde_estimate_craft_ops.py),
a [PDE work-unit gate](../../src/ztare/research_director/pde_work_unit_gate.py)
that refuses terminal gap verdicts without estimate derivations and a
falsifier packet, APN semantic bridge surfacing that emits `ns_apn_bridge`
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

### Synthetic personas and debate orchestrator

Multi-mutator cold-shot diversity plus structured adversarial debate.
Personas registry at
[`src/ztare/personas/`](../../src/ztare/personas/) (registry + routing);
debate machinery at
[`src/ztare/orchestration/debate_orchestrator.py`](../../src/ztare/orchestration/debate_orchestrator.py)
and
[`src/ztare/orchestration/friction_debate.py`](../../src/ztare/orchestration/friction_debate.py).
Named persona labels (Dijkstra, Knuth, Munger, etc.) are stylistic
shorthand for reasoning approaches, not claims about the persons; the
README's named-personas note is the canonical disclaimer.

### Commit-membrane daemon (GP-241)

The epistemic verificator daemon — the *sole writer* of the official store
(experiment record + ledgers). The agent cannot hand-edit official state;
it submits a proposal and the daemon stamps or quarantines it. A
hand-written record is non-authoritative by construction. Sits between
the loop and the canonical ledgers.

### Operator daemons

Long-running role processes that claim and run governed work. The
agent daemon is at
[`scripts/public/control/agent_daemon.py`](../../scripts/public/control/agent_daemon.py);
the closure daemon at
[`scripts/public/control/closure_daemon.py`](../../scripts/public/control/closure_daemon.py);
the routine-reviews loop at
[`scripts/public/control/rd_routine_review.py`](../../scripts/public/control/rd_routine_review.py).
Daemons obey mandates and surface their actions in the transition log;
they do not write to canonical state without going through the
commit-membrane.

### Org-runtime tenant overlay

The applied cognitive-firm primitives: persistent role offices,
mandates, tasks, gates, preferences, transition logs, damage signals,
operator surfaces, and optional notification providers. The reusable
kernel lives in the sibling `cognitive-firm` repository; the `org/`
tree in this repo is the ZTARE tenant overlay. See
[`org/README.md`](../../org/README.md) and
[`organizational_primitives.md`](organizational_primitives.md).

---

## 2. Operating discipline (apparatus-wide)

### Deterministic enforcement floor

Charter-committed gates as code, not LLM judges. A claim does not survive
unless a deterministic function over sealed holdout and farther-tail data
returns pass. Pre-registered hypothesis commitment (Hypothesis U vs. S,
etc.) recorded in `thesis.md` before evaluation; mid-run pivots require an
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

### Forecast pool and prediction market (GP-230)

Sealed forecast contracts for macro / meso / micro branch choices, swarm
gates, effort estimates, and externality audits. Belief is recorded
*before* action; calibration scoring runs ex-post. Implementation at
[`scripts/public/control/forecast/pool.py`](../../scripts/public/control/forecast/pool.py)
and
[`scripts/public/control/forecast/resolve_from_json.py`](../../scripts/public/control/forecast/resolve_from_json.py);
spec under
[`research_areas/specs/active/protocol/GP-230_forecast_pool_decision_market_spec.md`](../../research_areas/specs/active/protocol/GP-230_forecast_pool_decision_market_spec.md).

The primitive's operational rules are empirically derived from its first
child seam, the GP-245 Forecast Calibration Program
([`research_areas/seams/apparatus/instrumentation/GP-245_forecaster_skill_calibration_seam.md`](../../research_areas/seams/apparatus/instrumentation/GP-245_forecaster_skill_calibration_seam.md);
public surface at
[`projects/llm_forecasting_calibration_program/public/CLAIM_SUMMARY.md`](../../projects/llm_forecasting_calibration_program/public/CLAIM_SUMMARY.md)):

- forecast rows collect a separately-elicited tail-worry token
  (`tail_insurance_premium`, int 1–100) alongside `p_success` and the
  decomposed risk channels; the tail token predicts per-row Brier
  independently of the point estimate across four replicated pilots;
- forecasters are kept blind to each other's outputs until resolution
  (architectural sealing, not behavioral instruction — two registered
  light-touch remediations are now on record as failing: rationale
  exchange and direct skeptical-instruction framing);
- a high tail-worry signal on a material contract routes to abstain-
  and-escalate (or to a fresh forecaster from a different model family
  that re-prices the same contract without prior-agent context); the
  naive "raise the act-threshold when worried" wiring degrades utility,
  abstain-or-escalate restores it; closed-loop cross-family re-decision
  improves Brier dramatically on the worried subset under asymmetric-
  favor-yes cost regimes;
- subscription-class forecasters are not used to schedule LeanMill or
  any reasoning queue by yield-prediction — the capability has been
  measured to perform worse than a constant-0.5 baseline on stratified
  proof corpora across all three agents in the trio, so queue policy
  stays FIFO or uses non-LLM heuristics;
- per-contract confidence is weighted by resolution horizon via
  `horizon_confidence_weight()` in
  [`scripts/public/control/forecast/pool.py`](../../scripts/public/control/forecast/pool.py)
  (linear decay from 1.0 at reference date to 0.5 at 180 days,
  floored at 0.1) — universal cross-family effect at $N{=}210$ pooled,
  $\rho(\text{days}, \text{err}^2) = +0.16$ $[+0.03, +0.29]$;
- new emission fields (`p_buy_yes_max`, `p_sell_yes_min` for bid-ask
  spread; `predicted_brier_lo`, `predicted_brier_hi` for self-predicted
  Brier interval) are accepted by both `cmd_add_forecast` and
  `cmd_scratch_forecast` with cross-field validation; downstream
  consumers derive `spread`, `b_mid`, `b_width` from them.

The corresponding agentic implementation pattern is documented in
[`docs/concepts/agentic_engineering_patterns.md`](agentic_engineering_patterns.md)
Pattern 12 (Sealed Forecast Pool for Execution Control); the reflexive
counterpart is Primitive 9 (Reflexive Forecast Market) in
[`docs/concepts/reflexive_engineering.md`](reflexive_engineering.md); the
forecasting-role obligations live in
[`org/mandates/forecasting_agent_mandate.md`](../../org/mandates/forecasting_agent_mandate.md).

### Anti-pattern catalogue and runtime adversarial guard

One layer with two faces. The **durable record** is the catch ledger:
nine named specification-gaming strategies (Blame Shield, Suite
Omission, Cooked Books, Hidden Universality, others) documented as the
published Cognitive Camouflage paper, plus the catch-grammar module at
[`src/ztare/catch_grammar/`](../../src/ztare/catch_grammar/) that
classifies and stores live catches. The **runtime guard** is the
precedent library checked against candidate code each iteration — not
curated post-hoc, not a soft prompt; an in-pipeline gate. New strategies
are added by writing the failure case into the catalogue, which feeds
the guard automatically. See
[`anti_pattern_catalog.md`](anti_pattern_catalog.md) and
[`goodhart_at_every_layer.md`](goodhart_at_every_layer.md) for the
taxonomy.

### Reflexive primitives (the apparatus measures itself)

The apparatus runs on its own infrastructure. A weekly **capability-ROI
audit** re-mines every artifact and scores each primitive as engaged /
dead / never instantiated; several primitives have been demoted by the
audit and recorded as dead. See
[`reflexive_engineering.md`](reflexive_engineering.md) and
[`agent_agnostic_recursive_gain.md`](agent_agnostic_recursive_gain.md).

### Research-yield decomposition (GP-233)

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

### Action intelligence and intelligence surface (GP-243 / GP-244)

A read-side surface that joins forecast use, yield bottlenecks,
experiment state, catch risk, source readiness, and observer-only
learning candidates without mutating official state. The operator can
see what is in flight, what is blocked, what risk is unclosed, and what
proposals are pending. Implementation at
[`scripts/public/control/action_intelligence.py`](../../scripts/public/control/action_intelligence.py);
evidence ledgers under
[`analytics/public/ledgers/action_intelligence/`](../../analytics/public/ledgers/action_intelligence/).

### Audit-integrity chain manifests

A separate, layered tamper-evidence protocol over JSONL kernel logs.
Tamper-evidence is a *chain manifest* over the log, not a per-row
attestation, and it is a protocol the operator opts into for any log
they want to make tamper-evident. See
[`docs/guides/reflexive_audit_workflow.md`](../guides/reflexive_audit_workflow.md).

### Epistemic Airgap gate (cross-provider enforcement)

`require_cross_family` refuses to run a loop where the mutator and the
judge share a provider family (`openai`, `anthropic`, `google`); the
gate raises `SystemExit` before any LLM call. Default is warn-only;
`CROSS_FAMILY=1` in the Makefile is the standing posture for
`loop` / `experiment-loop` / `discover` / `honeypot-loop` targets.
This is the *loop-internal* discipline; the cold cross-provider pass
below is the on-demand, heavier version.

### Cold cross-provider pass

A self-serve check that dispatches a consequential architecture or
closure question to an independent external model at high reasoning
effort, then splits the verdict and Meta-Darwins its closing. Defends
against single-author monoculture. The pattern is described in
[`glossary.md`](glossary.md) and ships as a runtime move, not a
manual review step.

### Damage signals (GP-129)

An orthogonal signal channel for system failures, constraint
violations, and mandate-compliance alerts — decoupled from
identity-based authorization. Any process can emit a typed damage
signal; manager-agent mandates require listing active signals before
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
`agent_utilization_tracker.py`); operator entry points at
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
training-prior regression-toolbox vocabulary onto an operator-committed
non-elementary transcendental form (the Planck-sandbox calibration
recorded in the public claim register). When a target is incompressible
in one representation, the apparatus automatically tries monotonic
transformations (`1/z`, `ln z`, `Δz`) and re-runs compression on the
transformed representation; the Ulam reciprocal compression was
discovered this way without operator guidance. See
[`cognitive_gym.md`](cognitive_gym.md).

### Cross-mutator / cross-tool triangulation

Multi-mutator family runs (Gemini, Claude, GPT-4o) under the same
gates; specification-gaming behaviour is mutator-family-specific, not
universal, and the apparatus records that. Cross-tool baselines: PySR
independently arrived at the same Lucky-number density coefficient as
the apparatus on the same observable. Cross-tool replication is a
citable triangulation, not a manual review step.

### Grammar-vs-space diagnosis

The apparatus distinguishes a **grammar ceiling** (the expression
language cannot write the answer) from a **space ceiling** (the mutator
does not search in the right mathematical category). The sopfr
(OEIS A001414) result is the canonical case: the grammar admits the
answer syntactically, but the mutator never reaches the prime-
factorisation category that would let it find one. The diagnosis
triggers a grammar or category extension, not a search-budget increase.

### Substrate prober and constraint-to-DoF analysis

Before fitting, the apparatus probes whether a substrate is rich enough
to answer a question — the within-class feature-collapse finding on the
v2 RAR substrate is the canonical case. The probe is a gate
(R26 G-CROSS-CLASS-FEATURE-SUPPORT), not an after-the-fact narrative.

### LeanMill — governed DAG proof-search solver (GP-246, current frontier)

The current leanmill core is a **governed best-first search over a proof-obligation DAG** around a *swappable*
LLM "leaf" (codex/claude on subscription): the leaf PROPOSES moves; **one governance kernel RATIFIES** every
closure (kernel compile + axiom allowlist + matched-negative-control + the v33 anti-laundering organs +
statement-integrity). A goal is *closed* only on a ratified closure — never because the agent says so. The
move space spans the direct attack (native tactic cascade, warm agentic leaf, cold-shot fan-out, external
frontier prover), the structure-changers (conjecture/decompose, specialize, generalize, falsify, tactic-step),
the **exogenous-compute** moves (`witness_transport` — SymPy finds a witness for a non-linear existential /
Kronecker linear-system / Pell-form diophantine, the kernel re-verifies; `corroborate` — the Popper dual of
falsify), **composite ratification** (assemble a parent from proven sub-lemmas), a **target-conditioned
move-router** (promote the move whose precondition matches the goal), boosting, and isomorphism-decomposition.
Shared compute lives in `src/ztare/common/{sandboxed_python,symbolic_witness}.py`; the subsystem is
`src/ztare/leanmill/solver/**`; full spec in [`docs/concepts/leanmill_architecture.md`](leanmill_architecture.md)
and [`research_areas/seams/engine/lean/GP-246_governed_dag_proof_search_seam.md`](../../research_areas/seams/engine/lean/GP-246_governed_dag_proof_search_seam.md).

**Honest status (the discipline, not marketing):** the **soundness moat is the validated strength** — the
governance kernel demonstrably catches gaming/laundering (statement alteration, vacuity, axiom smuggling,
in-proof leakage) that a bare `compile_ok` misses. The **capability LIFT over the bare leaf is mostly
UNPROVEN**: a strong Lean+Mathlib leaf saturates easy substrates (witness-transport measured lift = 0) and
fails open-conjecture-hard ones (P1), so most moves are "lift-test pending" per the capability-discipline
ledger in the architecture doc. leanmill is a governed *environment* around a frontier leaf, **not** a trained
prover — it competes on governance, and whether the environment multiplies the leaf is under active
measurement (PutnamBench baseline-vs-apparatus). The older GP-225 GNN lemma-relevance ranker + 24/7 Lean
station-factory workers (`scripts/public/control/leanmill_*`) remain the SCALE layer beneath this solver.

### Power-aware experimental statistics (GP-245 toolkit)

A single-file general-purpose statistics module that codifies the experiment-discipline used across pilot rounds — Fisher-$z$ power computation, proper equivalence testing, multi-comparison correction, OLS with leave-one-out cross-validation, three legal verdicts, and a Bayes factor wrapper. Lives at
[`src/ztare/experiment_stats.py`](../../src/ztare/experiment_stats.py).
Thirteen public functions:

- **Power before fire:** `n_required_for_rho(target_rho)`, `detectable_rho_at_n(n)`, `n_required_for_brier_delta(delta)` — Fisher-$z$ sample-size computation. Pre-registration discipline: no pilot is fired without `n_required` written down first.
- **Correlation with CI:** `spearman_rho(xs, ys)`, `spearman_rho_with_ci(xs, ys, ci=0.95)` — Fisher-$z$ transform 95% CI.
- **Difference tests:** `paired_permutation_test(a, b)`, `bootstrap_ci(values)`, `bf_bic_paired_t(a, b)` — paired Δ-testing with BIC-approximation Bayes factor (Wagenmakers 2007).
- **Equivalence testing:** `tost_equivalence(a, b, equiv_bound)` — proper `h0_kept` claims via two one-sided tests at a pre-stated bound; not "p > 0.05".
- **Multiple comparison:** `bh_fdr(p_values)` — Benjamini-Hochberg false-discovery-rate correction across panel tests.
- **Multi-channel R² without overfitting:** `ols_multichannel_r2(xs_cols, ys)` returns R², adjusted R², and **leave-one-out R²_LOO** — the audit-clearing test against in-sample-fit noise at small N. The meta-Darwin audit flagged "R² without LOO at small N" as a recurring program error; this function makes the correct report unavoidable.
- **Three legal verdicts:** `power_aware_verdict(observed_rho, n, target_rho)` returns one of `h1_supported` / `h0_kept` / `inconclusive_underpowered`. `h0_kept` requires the CI to wholly exclude $\pm$target_rho; otherwise the verdict is `inconclusive_underpowered`. The "underpowered null misread as h0_kept" error is what the GP-245 program found in 8 of 12 of its own earlier nulls; this resolver makes the correct verdict unavoidable.
- **Reproducibility manifest:** `reproducibility_hash(prompt_template, dispatcher_version, corpus_row, agent_id)` — per-call SHA-256 of inputs so any score row can be audited back to the exact prompt + corpus row that produced it.

Codified disciplines that the toolkit supports (referenced by [`AGENTS.md`](../../AGENTS.md) §6n.6–§6n.9):

- **Power before fire.** Every pilot ships with `n_required` from `n_required_for_rho` written into the pre-registration row before the first call.
- **Three legal verdicts, no fourth.** Findings resolve to `h1_supported` / `h0_kept` / `inconclusive_underpowered`. The "I tried, got p>0.05, calling it null" verdict is now `inconclusive_underpowered` unless the equivalence-bound condition is met.
- **LOO-CV at small N.** Multi-channel R² claims at $N < 30$ with $k \geq 3$ regressors carry LOO alongside in-sample; the meta-Darwin audit retracts findings reported without it.
- **BH-FDR across panel tests.** Per-family panel tests (5-family $\times$ multi-intervention) carry BH-FDR adjustment when reported.

The meta-Darwin retract-and-retest pattern (audit every claim post-hoc against the discipline; retract anything that fails; re-fire if a retest disambiguates) is documented in the pattern catalogue and applied to all GP-245 findings (`projects/llm_forecasting_calibration_program/forecaster_skill_calibration_v1/workspace/meta_darwin_audit_2026_05_27.md`).

### Forecasting-program calibration database and Brier/Elo stats

The general-purpose tooling for any binary-forecast calibration program. Both modules were hoisted 2026-05-27 from the GP-245 workspace into `src/` so future calibration programs can reuse them as a library; the historical CLI paths in `projects/llm_forecasting_calibration_program/forecaster_skill_calibration_v1/workspace/` survive as thin shims that import from canonical copies.

- [`src/ztare/forecasting/calibration_db.py`](../../src/ztare/forecasting/calibration_db.py) — SQLite schema (three tables: `contracts`, `pilot_calls`, `pre_registrations`), idempotent DELETE-then-INSERT ingest (so re-ingesting a fired JSONL is safe), per-call Brier auto-computed from `y_known`, normalised primitive/family/pilot_id fields. CLI: `init`, `ingest-corpus`, `ingest-pilot`, `ingest-all`, `query`, `stats`, `prereg-add` (auto-computes `n_required` from `--target-rho` via Fisher-$z$ power), `prereg-resolve`, `prereg-list`. The pre-registration table makes "you said you'd need N=42 to call a `h1` here" auditable.
- [`src/ztare/forecasting/calibration_stats.py`](../../src/ztare/forecasting/calibration_stats.py) — forecasting-specific stat wrappers on top of `ztare.experiment_stats`. CLI: `brier-ci`, `delta-test` (paired Δ-Brier with bootstrap CI + Bayes factor), `spearman` (per-family ρ + 95% CI + verdict), `elo` (cross-pilot Elo ranking across families), `finding` (replication-harness checking a named finding against current DB state), `power-n`, `power-detectable`, `tost`, `brier-decomp` (Murphy reliability/resolution/uncertainty), `verdict` (resolves a finding to one of three legal verdicts).

The forecasting-program-specific pieces remain in `projects/llm_forecasting_calibration_program/forecaster_skill_calibration_v1/workspace/`: the per-pilot dispatchers (`run_pilot_v28_dispatch.py` and siblings), the corpus sourcers (`extend_corpus_v25_*`), the keyword tagger (`topic_tag.py`), and the program's research log + pilot queue. Those are not generic and should not be hoisted; the split is "general toolkit in src/, pilot-specific orchestration in workspace/".

### Lean / formal-verification bridge

A Lean 4 compiler generates proof stubs for surviving claims: `#eval`
blocks that verify gate bounds at every holdout point, plus PSLQ
conjectures mapping fitted floats to candidate mathematical constants.
The Navier-Stokes campaign carries sorry-free Lean scaffolding modulo
named axioms — typed infrastructure, not analytic-PDE closure. See
[`ztare_proofs/`](../../ztare_proofs/).

---

### Recent additions (2026-06-04, since the last full pass)

- **Canonical MDL/BIC engine** (`src/ztare/fit/mdl.py`): `bic` / `bic_from_loglik` (de-duped from compress_champion's inline copies) + the two-part-code `MDLLibrary` (a Strategy interface). Consumed by autoresearch (compress_champion) and leanmill (lemma-library pruning).
- **LeanMill calibration** (`src/ztare/leanmill/solver/move_calibration.py`): recursive self-tuning `selection_priors` (shifts each move's est_p_close from compile_ok → ratified as governed data accrues — live: claude_warm 0.35 → ~0.82 on ratified outcomes), `select_calibration_model` (BIC decides split-by-error-class vs pool), recorded-forecast Brier/Elo.
- **Constraint-to-Isomorphism engine** (`src/ztare/common/constraint_isomorphism.py`, see §1) — now provider-flexible (gemini API / codex+claude subscription CLI; `gemini-3.1-pro-preview` default).
- **Autoformalization + faithfulness firewall** (`src/ztare/leanmill/solver/autoformalize.py`, OPT-IN): NL→Lean via a frozen leaf, gated by governance-as-faithfulness — compile + non-trivial + non-vacuous + structural iso/lossless preservation + a directional cold cross-family judge; FAIL-CLOSED (a false ACCEPT is a fabricated success). Reuses the kernel; not a parallel governance. EFFICACY UNPROVEN.
- **Isomorphism-surfaced default-off levers** (`governance_organs.py` MDL-generativity + Schwartz-Zippel [advisory]; equiv-keyed proof cache; reachability invent-criterion). Built + self-tested + parity-safe; **lift mostly UNPROVEN** — the easy-substrate A/Bs came out null (the strong leaf solos them), so the real measurement needs critical-difficulty substrate. Full status: `leanmill_architecture.md`.

## What this does not have

Concrete non-claims, listed so a reader is not left guessing:

- No autonomous research engine. The operator remains the uncontrolled
  variable, and the repository is explicit about that.
- No domain-knowledge replacement. The apparatus does not substitute for
  an expert physicist, mathematician, or biologist.
- No autonomous optimizer or RL routing of governance state. Reward
  signals are recorded; tenant policy decides whether and how to route on
  them.
- No claim that any single high-variance substrate (NS, gravity, neural,
  consciousness) is solved. The claim register records bounded results.
- No claim that primitive prose improves agent outputs in general. The
  surviving agent-facing positive is narrower: source-bound,
  action-constraint-carrying contracts can make audit intent recoverable
  to a downstream consumer; passive primitive prose is inert under the
  tested designs.
