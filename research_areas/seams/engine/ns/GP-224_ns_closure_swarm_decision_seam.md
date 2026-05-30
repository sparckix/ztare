# GP-224 — NS Closure Swarm vs Typed Endpoint Compression

> **Seam metadata** · `seam_id:` GP-224 · `track:` engine · `status:` unrecorded · `last_updated:` 2026-05-09


Status: open
Opened: 2026-05-06 11:41:06 EDT
Updated: 2026-05-06 21:34:00 EDT
Owner: Research Director / Codex
Visibility: private while active

## Problem Statement

NS Track B now has enough graph, typed-endpoint, dimensional, and Lean-verifier tooling that parallel candidate generation is tempting. The risk is that a swarm/queue system could multiply tautological or self-referential proof attempts faster than the verifier stack can reject them. The controlling question is whether queue infrastructure would increase verified proof progress, or merely increase apparatus motion.

## Jobs To Be Done

1. Keep proof work aimed at the six remaining source constructors, not generic theorem search.
2. Shift cheap failures to the front: endpoint resolution, dimensional checks, source-provenance checks, and no-new-axiom audits before expensive Lean loops.
3. Preserve adversarial lanes: one lane searches for bypass/falsifier routes, another tries to close them through audited source receipts.
4. Prevent mode collapse: no worker may “solve” a target by changing the target, adding axioms, weakening hypotheses, or routing through the desired conclusion.
5. Produce durable learning: every failed patch must land in a typed failure category that changes the next attempt.

## Options

### Option A — No Swarm; Continue Manual Codex + Targeted Agents

Pros:
- Lowest overhead; keeps attention on Lean constructors.
- Best protection against proof theater while the hard source objects are still being understood.
- Existing `spawn_agent` read-only audits already cover parallel review without queue infrastructure.

Cons:
- Lower throughput once patch classes are stable.
- Human/Codex remains the scheduler.

### Option B — Lightweight Local Work Queue

Use a JSONL/SQLite worklist over existing scripts: `typed_endpoint_pack.py`, `patch_class_selector.py`, dimensional gate, mathlib scout, Lean fast compile, failure clustering.

Pros:
- 80% of swarm value without beanstalkd/Redis/system services.
- Easy to audit, checkpoint, and kill.
- Can enforce per-job immutable target, allowed file scope, no-new-axiom scan, and failure-category logging.

Cons:
- Still adds process surface.
- Worthless if targets are not typed tightly enough.

### Option C — Beanstalkd/Worker Swarm

Pros:
- Better if hundreds of independent typed candidates need scheduling.
- Useful once failure logs are large enough for policy learning.

Cons:
- Infrastructure before bottleneck proof is known.
- Raises mode-collapse risk by making bad attempts cheap.
- Adds operational state that can rot.

## Recommendation

Do **not** build beanstalkd/swarm code yet. Use Option A now, with Option B as the next mechanization only after the following tripwire fires:

- at least 50 typed endpoint attempts are logged;
- at least 10 are blocked by scheduler/throughput rather than missing PDE content;
- patch classes are restricted to known safe shapes;
- every job has immutable endpoint type, allowed write scope, dimensional/source gates, Lean build, and axiom audit;
- failures are categorized by `failure_cluster_analyzer.py`.

Current best forward path: keep doing endpoint-type compression and source-route hardening manually, using targeted read-only agents for distinct proof-surface audits. Parallelization becomes decisive only when typed candidate throughput, not PDE object identification, becomes the bottleneck.

Correction: the evidence above refutes blind replay on `TrackBProfileLipschitz*`; it does **not** refute a small breadth test across the other source constructors. Under the paper-7 operator model, the principal supplies taste/scope/kill criteria while substrate proof work is delegated. The missing empirical question is whether Codex's conversation-paced one-target-at-a-time behavior is hiding useful attempts on the non-TrackB source constructors.

## Current Decision

Swarm is a later accelerator, not today's proof step. Today's proof step remains: instantiate or compress the source constructors around phase latency, quartic amplitude observable, self-tax output source, profile/Lipschitz control, flat-torus reserve, then rebuild GP216 and refresh the graphs.

Allowed bounded test: run a five-job typed-endpoint panel across non-TrackB source constructors. Prefer zero-API subagent fan-out first: each agent receives one immutable constructor/field target and returns a compile-safe patch sketch, a concrete missing primitive, or "no useful move." Only drain `typed_endpoint_queue.py --worker` through an external LLM if the agent panel cannot classify the target. This is not a default scheduler flip and not a proof claim. It is an empirical utility test with this interpretation rule:

- `>= 3/5` verified or producing concrete non-stale missing primitives: promote Option B to routine opt-in during closure attempts.
- `0-1/5` useful: keep queue off the proof path and focus on type reformulation/manual PDE construction.
- `2/5` useful: ambiguous; repeat on a different patch class before changing mandate defaults.

The panel must not target the stale `generated_quartic_survival_projection` TrackB field and must not write source patches without a Lean build plus axiom/sorry audit.

## Evidence Update — 2026-05-06 11:53:00 EDT

`analytics/public/queries/audits/failure_clusters.md` concentrates all 9 typed-endpoint failures on obligation endpoints, with 7/9 under `instance_with_evidence`; the repeated TrackB target is the stale projection field `generated_quartic_survival_projection`. The refreshed workmap now shows the live TrackB field as `generated_quartic_survival_amplitude_observable_source`, so the useful action is target-type reformulation/source routing, not swarm throughput. `analytics/public/queries/lean/endpoint_compression_audit.json` has only one GP-223 compression candidate in this 28-day window, below the seam's threshold for shipping Layer 1+2 as a general gate.

Decision updated: no beanstalkd/worker swarm now, but run the bounded five-constructor typed-endpoint panel as a discriminating test. The default implementation is read-only subagent fan-out, not paid LLM queue drain. Keep using bounded Codex + targeted read-only agents; promote only compiler-checked source-routing edits or concrete falsifiers.

## Evidence Update — 2026-05-06 12:00:43 EDT

The paper-7 operator-as-metacognition correction weakens the prior "not throughput-bound" conclusion. The current failure log only says that one family/patch-class combination is loss-leading. It does not show whether phase latency, self-tax output source, flat-torus reserve, event recurrence, or GP216 macro-clock endpoints would produce useful missing-primitives evidence if fanned out. Because subagent fan-out is available without external LLM API calls, the discriminating test should be zero-spend agent breadth first, with the JSONL queue retained only as a scheduler/logging scaffold.

## Evidence Update — 2026-05-06 12:20:53 EDT

The bounded five-constructor Codex-agent panel was useful. Results harvested at `analytics/public/queries/agent_panels/20260506T161557Z_ns_trackb_live_agent_panel_20260506/metrics.json`: 5/5 completed, 5/5 useful, 4 compile-safe projection/routing aliases, and 1 concrete non-stale missing primitive (`FlatTorusSmoothKillingFourierSource`). Decision: promote the zero-spend typed-endpoint agent-panel pattern as an opt-in RD tool for closure attempts.

This does **not** promote beanstalkd/Redis swarms or paid LLM queue drains. It also does not move theorem construction inside `autoresearch_loop`. The clean split is: ZTARE core/autoresearch keeps general theory-building primitives, falsifiers, deterministic gates, framer/Lagrangian derivation, and bounded briefing artifacts; RD/Codex uses panels and workbench callers to choose proof targets, then feeds only compiler-checked theorems, concrete falsifiers, or summarized failure categories back into ZTARE memory.

## Evidence Update — 2026-05-06 16:13:20 EDT

Budget-gated paid dispatch is now mechanized generally enough for reuse:

- `src/ztare/supervisor/llm_budget_guard.py` provides prompt-token estimation, per-run cap enforcement, role/day spend checks through `spend_tracker`, actual-spend recording from `LLMRuntime` telemetry, and optional `org/gates/pending` approval-gate emission.
- `scripts/public/lean/typed_endpoint_pack.py`, `scripts/public/lean/typed_endpoint_queue.py`, and `scripts/public/lean/batched_candidate_generator.py` now support `--budget-estimate-only`, `--allow-paid`, `--max-total-cost-usd`, `--role-id`, `--session-id`, and `--write-approval-gate`.
- A dry GP216 source-provenance batch estimated `$0.1927` on `claude-sonnet-4-6` under a `$0.50` cap and wrote `org/gates/pending/20260506T201938Z_batched_candidate_generator.json`.

Decision: paid swarms remain non-default. They are executable only after either a tactical terminal approval (`--allow-paid --max-total-cost-usd X`) or a resolved org gate. Zero-spend Codex-agent lanes remain the default first pass for ansatz, Mathlib translation, and ghost-gram falsifier reconnaissance.

## Evidence Update — 2026-05-06 21:34:00 EDT

Paid Gemini-Pro swarm panels were useful as discriminators but not yet as
Clay-grade theorem generators. The 8-job closure-grade run produced 21
compiled non-self-reference candidates, but hostile review found mostly
projection/API wrappers; refreshed `structure_instantiation_workmap.py`
stayed at 67 open structures. One useful helper was integrated
(`smooth_limit_preserves_cost_and_reserve_of_energy_budget_shell_pde_handoff`),
and the Lean corridor still builds.

Two apparatus corrections did matter:

- prompt truncation was leaking fake Lean identifiers
  (`GP216GeneratedProfileLipschitzBranch` instead of
  `GP216GeneratedProfileLipschitzBranchBlock`), so `typed_endpoint_pack.py`
  now uses safe previews;
- `batched_candidate_generator.py` now has `--require-source-witness`,
  demoting candidates that take the target record itself as input, plus narrow
  normalization of filesystem-style imports (`import ztare_proofs.ZtareProofs...`).

Cheap-model controls were negative for compiler-facing theorem patches:
`gemini-2.5-flash` and `gemini-3.1-flash-lite-preview` both returned 0/3
useful jobs on the same endpoints. Use cheap models only for pre-Lean ansatz
or classification, not source-witness Lean patching.

SymPy falsification shifted the mathematical target:
`scripts/public/projects/ns/ns_phase_latency_sympy_check.py` refutes the naive one-shot capacity
balance (`dt -> 0` and dimension mismatch). The surviving lanes are dyadic
phase-budget and integrated-energy requirements. Future source-witness prompts
must target those lanes explicitly.

Refit decision: do not grow a parallel swarm subsystem. Consolidate scripts
around existing ZTARE primitives: `typed_endpoint_agent_panel.py` for
zero-spend Codex panels, `typed_endpoint_queue.py` for queued serial pack runs,
`typed_endpoint_pack.py` for closed-loop endpoint attempts, `LLMRuntime` +
`llm_budget_guard.py` for paid calls, and existing gates for Lean/SymPy checks.
`surgical_swarm_panel.py` remains a thin RD wrapper only; promote into ZTARE
core only if future runs reduce open workmap structures or discover a
non-stale PDE source witness.

## Evidence Update — 2026-05-06 22:04:00 EDT

Script refit implemented without promoting swarm to core. Repeated generated
Lean hygiene logic moved to `src/ztare/formal/lean_candidate_hygiene.py` and
is now reused by `typed_endpoint_pack.py` and `batched_candidate_generator.py`
for safe previews, import normalization, Lean-block extraction, duplicate
declaration checks, decorative-wrapper detection, and target-field
self-reference filtering. This keeps the paid/queued proof tools aligned with
the existing ZTARE formal layer instead of growing a second validator.

Proof-side update: `ns_profile_lipschitz_clay_bridge.lean` now has
branch-certificate constructors for both noncircular Young/defect and
continuum all-output routes when the caller already has strong
`QuarticSurvivalThresholdRootObservableSource` objects. This removes an
unnecessary matrix-parts detour but does not reduce the workmap count: graph
refresh still reports 67 open structures. Current verdict unchanged: swarm is
2-4x as an RD discriminator/debugger, not >10x as a Clay theorem generator.
