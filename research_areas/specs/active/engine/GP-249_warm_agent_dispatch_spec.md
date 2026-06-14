# GP-249 — Capability-aware cognitive-worker dispatch (`dispatch_model`)

## Status

Implementation-complete for GP-249 v8 surfaces — 2026-06-11.
Measurement remains open: flag-gated agent call sites must still be evaluated
against scoped parity/A-B runs before any capability-lift claim is admitted.

## Seam

`research_areas/seams/engine/GP-249_warm_agent_dispatch_seam.md` (v8)

## Scope

- defines the resolver that routes an autoresearch worker call across four orthogonal axes — **capability** (LLM vs agent), **state**, **fungibility/identity**, **transport** — to either a single LLM forward pass or a bounded, briefing-fed agentic tool-loop
- defines the parity-default flag and the per-call-site routing policy (atomic-LLM vs fungible-agent)
- defines the run/projection metadata fields that record those axes (`worker_archetype`, `worker_capability`, `worker_state`, `worker_identity`, `transport`)
- defines the invariant that the **briefing** (not a transcript) is what the agent consumes, preserving fungibility / airgap / cost
- defines a 6th **negative-space `BriefingProvider`** (the tried-and-failed ledger) that externalizes procedural/negative memory — shippable independently, before the resolver
- defines an RD-side router for deciding when out-of-loop research should invoke autoresearch as a workbench
- defines the GP-243 action-impact carrier for RD/out-of-loop agent work at this boundary (`domain=agentic_workbench`)
- defines the user surfaces for inspection/logging: `make autoresearch-projection`, `ztare autoresearch projection`, `ztare autoresearch route --record-decision-id`, and `ztare action-intel record-agentic-route` for pre-saved route JSON
- defines the projected-state boundary: hypothesis/evidence projection and negative constraints are read-only inspection surfaces, not a replacement controller
- defines that the intra-step loop can reduce blind mutator emissions before the candidate leaves the worker; the existing R1 **gate** stays loop-side as the deterministic ratifier
- defines the auditability contract (canonical artifacts authoritative; agent transcript is cache)

Does not cover:

- migrating the loop *control* to an agent (explicitly out of scope — the orchestrator stays deterministic)
- the research director (it is the EXTERNAL agent operating the loop as a tool — no internal call site)
- a new session manager (reuses `subscription_agent_runtime`)
- a pure projected-tree controller that supersedes ZTARE gates, briefing providers, GP ledgers, or the claim membrane
- guaranteed live mutator-agent lift before parity/A-B validation

## Decision

Add a thin `dispatch_model(prompt, briefing, *, capability, fungible, stateful, continuity_key, backend)` resolver over the existing `_call_once` / `run_subscription_agent_with_recovery` runtimes. It routes a worker call by the four-axis taxonomy: `capability=llm` → today's single forward pass (unchanged); `capability=agent` + `fungible` + stateless → a bounded act→observe→reason→repeat tool-loop **seeded with the same externalized state surface** and returning text for the same typed-contract validator. The agent path is behind `ZTARE_AGENT_DISPATCH=off` (default) and per-call-site overrides such as `ZTARE_AGENT_DISPATCH_MUTATOR=agent`, `ZTARE_AGENT_DISPATCH_JUDGE=agent`, and `ZTARE_AGENT_DISPATCH_COMMITTEE=agent`. Current implementation has shipped the safe infrastructure: worker metadata, read-only projection support with held-out evidence counting and negative constraints, negative-space briefing, env-gated resolver, RD workbench router, action-intelligence route logging, Make/CLI surfaces, and call-site wiring for the mutator, judge, and dynamic committee. The live paths are available behind flags; lift remains unproven until parity/A-B measurement.

## Problem

The autoresearch loop's in-loop workers (mutator, judge, fit, gates) are LLM-capability single-shot calls: the mutator proposes a thesis mutation **blind**, and only the downstream fit/judge stages discover *one iteration later* that it doesn't compile or doesn't fit — a wasted iteration. Single-shot calls structurally cannot verify-before-propose or recover from a tool failure **within a single mutation step**, which the literature identifies as the capability gap that lets an agentic wrapper beat a stronger single-shot model.

**The lever is intra-step capability, NOT cross-iteration memory.** Getting this wrong reconstructs the rejected warm-shard design. The stateless mutator is fresh every iteration *at the worker*, but the loop already carries memory: the `MutatorBriefing` re-injects accumulated judge feedback + fit telemetry + trajectory each iteration, so the mutator already "improves off judge feedback." A warm agent would only relocate that memory from the briefing into the worker's internal context — strictly worse (breaks airgap/fungibility, O(N²) cost) and redundant. The agentic value is orthogonal to memory: a tool-loop *inside one mutation step* (propose → self-check compile/fit → revise → emit), so the error recovery happens before the candidate leaves the worker. It works identically whether the worker is fresh-every-iteration or warm. Any residual gap the briefing can't capture (procedural "already-tried-X" knowledge) is closed by adding a `BriefingProvider`, not by making the worker stateful.

A primitive, suboptimal version of intra-step verification already exists: the **Runner R1 path**. The mutator emits blind; R1 validates the submission (import-safety dry-run, the required `MutationDeclaration` typed header, syntax, forced-reframe AST-bucket compliance) and on failure raises `ValueError` to hand the mutator the error string for **one free retry**, capped at **3 strikes** (`R1ExhaustionTracker`). It is suboptimal because each bounce is a full fresh prompt re-send, the worker sees only the error *string* (not the live check), it is strike-capped, and the prompt even hardcodes a "COMMON R1 REJECTION PATTERNS — DO NOT EMIT THESE" list to dodge bounces. The intra-step agentic loop replaces the *bounce* (not the *gate*): R1's checks become tools the worker calls before emitting; R1's gate stays loop-side as the deterministic ratifier.

A prior attempt to use agents here was abandoned because "token use was too high." That cost was an O(N²) artifact of replaying raw transcripts per call, not an intrinsic property of agents — and autoresearch already has the structured-memory fix (the `BriefingProviders`) that the cost literature prescribes. The category was also muddled: "API vs agent" conflated four independent axes (capability, state, fungibility, transport), so the design space was never cleanly seen — in particular the **fungible agent** (agent capability + fungible identity).

There is a second practical distortion: RD agents have often used subscription Codex/Claude directly out-of-loop instead of invoking autoresearch, even when prose positioned autoresearch as the workbench. The architecture should make that choice explicit. If the task has a bounded claim, stable evaluator, rubric surface, and artifact surface, the RD should route into autoresearch; if not, the RD should prepare that surface first or stay out-of-loop.

Projected-tree research systems add a useful comparison point: they make failed
branches, evidence, and held-out admission explicit. ZTARE should adopt that
inspection discipline where current autoresearch history is implicit, while
keeping authority in its existing gates, claim membrane, BriefingProviders,
action-intelligence rows, and GP ledgers. The projection should expose state for
the RD and later benchmarks; it should not promote artifacts or replace the
membrane.

## Why It Matters

- **Capability uplift on the highest-leverage call.** The mutator is where blind proposals waste iterations; verify-before-propose converts that into in-loop error recovery. Same for a judge that can run a check instead of rating.
- **Preserves the philosophy if scoped right.** The architecture's invariants — externalized state (briefings), cross-family airgap, deterministic loop control — are all compatible with an agentic *worker*. They are NOT compatible with an agentic *orchestrator*. The boundary must be encoded, not left to discipline.
- **Dissolves the cost objection mechanically.** Feeding the agent the briefing (not the transcript) keeps cost ≈ API mode + one bounded tool-loop. Without this invariant the cost blowup recurs and the feature gets abandoned again.
- **Restores the workbench role.** The RD remains the persistent out-of-loop agent, but gets a routing primitive for when to invoke autoresearch rather than doing everything ad hoc in a subscription CLI.

## Constraints

- `ZTARE_AGENT_DISPATCH=off` default ⇒ today's path. Per-call-site override uses `ZTARE_AGENT_DISPATCH_<CALL_SITE>=agent`, e.g. `ZTARE_AGENT_DISPATCH_MUTATOR=agent`.
- The agent consumes the **MutatorBriefing**, never a raw warm transcript (preserves fungibility, airgap, cost). No new state object.
- The agent returns the **same typed contract** the LLM call returns (`Mutation`, judge verdict) — validated at the boundary, so the loop downstream is unchanged.
- The **cross-family airgap** (`autoresearch_loop.py:254`) is preserved: mutator and judge agents must remain different provider families; fungibility is required, never a single persistent in-loop worker.
- The **loop control stays deterministic** — `dispatch_model` is called by the existing pipeline at the existing seams; it never gains authority over sequencing, stopping, or pivoting.
- Reuse `subscription_agent_runtime` (`run_subscription_agent_with_recovery`, `--resume`); no fork, no autoresearch-local session manager.
- Subscription CLI for agentic calls (codex `exec` / claude `-p`, `env -u ANTHROPIC_API_KEY`); the metered-API agent path stays gated (existing external-prover policy).
- Verification stays deterministic — the agent may propose/prioritize; the fit/judge/gate ratification is unchanged.

## Options

### Option A — Keep LLM-only (status quo)

**Description** Leave all in-loop workers single-shot; never add agentic capability.

**Pros** Zero work; maximal reproducibility; lowest per-call cost.

**Cons** Forfeits the documented agentic>single-shot capability gain on the mutator/judge; blind-propose keeps wasting iterations; leanmill and autoresearch keep diverging worker substrates.

**Verdict** Rejected — leaves the highest-leverage uplift on the table.

### Option B — Warm persistent in-loop agents (the v2/v3 warm-shard design)

**Description** Give the mutator a persistent warm session carrying its own transcript across iterations.

**Pros** Maximal local coherence; "remembers" prior mutations without a briefing.

**Cons** Breaks the cross-family airgap (warm state leaks judge-side context); breaks fungibility/diversity (can't swap a different family mid-run; homogeneous → diminishing returns); reintroduces O(N²) transcript-replay cost (the original "token too high" failure); duplicates the BriefingProviders.

**Verdict** Rejected — violates three architecture invariants at once; this is the design the seam grounding-correction killed.

### Option C — Capability-aware `dispatch_model`, briefing-fed, fungible, flag-gated (recommended)

**Description** A thin resolver that routes per-call-site to LLM or **fungible agent**, both seeded with the same briefing and returning the same typed contract, deterministic loop unchanged, parity-default.

**Pros** Capability uplift exactly where it pays; preserves airgap + fungibility + externalized state + deterministic orchestration; cost ≈ API + one bounded loop; shared by both repos; reversible via flag.

**Cons** Two code paths to maintain; needs a per-call-site policy table; tool-loop adds latency on the calls that use it.

**Verdict** Recommended.

## Recommendation

Adopt **Option C**, but stage experiments even when the plumbing supports multiple call sites. Build `dispatch_model` as a capability-aware resolver over the existing runtimes, parity-default, with per-call-site env policy. Ship metadata + negative-space briefing immediately. Validate parity first (flag off ≡ today), then run calibrated A/Bs on discriminating substrates: mutator first (advance-rate / iterations-to-fit), then judge only where a runnable verification surface exists, then committee only if panel quality/coverage is the bottleneck. The lift is inadmissible without the flag-off parity control and the airgap intact. The research director stays external; no internal session registry is built for it.

## Implementation Sketch

1. **Resolver (`src/ztare/common/dispatch_model.py`).**
   `dispatch_model(prompt: str, briefing: str | None, *, capability: Literal["llm","agent"]="llm", fungible: bool=True, stateful: bool=False, continuity_key: str|None=None, backend: str|None=None) -> <typed contract>`.
   - `capability="llm"` → delegate to the existing `LLMRuntime._call_once` (no behavior change).
   - `capability="agent"` + `fungible` + `not stateful` → `run_subscription_agent_with_recovery` with the briefing as the seed context and a bounded tool budget; the tools are the verify-before-propose primitives — the **R1 checks exposed as tools** (import-safety dry-run, `MutationDeclaration` contract-validate, syntax, forced-reframe AST-bucket compliance) plus fit-probe / evidence-search, reusing leanmill's `agent_tools` surface where a tool already exists.
   - `stateful` + persistent → resumed `--resume` session — **latent** (built for symmetry; not invoked in-loop; reserved for an external RD that opts to keep a warm session).
   - Return text is parsed/validated into the SAME typed contract the call site already expects (the mutator's is `MutationDeclaration`, `core/mutation_contract.py`); a parse failure is a hard fail (no silent coercion — the verbatim-contract discipline).

2. **Flag + policy.** `ZTARE_AGENT_DISPATCH=off` default. `resolve_dispatch_capability(call_site)` supports generic opt-in and per-call-site overrides (`ZTARE_AGENT_DISPATCH_MUTATOR=agent`, `ZTARE_AGENT_DISPATCH_JUDGE=agent`, `ZTARE_AGENT_DISPATCH_COMMITTEE=agent`). Prefer scoped flags for experiments; the generic flag promotes every wired call site. Fit/gates stay deterministic/atomic. No agentic loop controller.

3. **Call-site wiring (implemented; parity-gated).**
   - Mutator: `autoresearch_loop.safe_mutate` resolves `resolve_dispatch_capability("mutator")`; default `llm` preserves the existing API call, while `ZTARE_AGENT_DISPATCH_MUTATOR=agent` routes through `dispatch_model(..., capability="agent", fungible=True, stateful=False)`. This covers the whole mutator generation boundary: initial proposals, alignment rewrites, compiler-bounce retries, parse-retry calls, and any other content generated through `safe_mutate`. The downstream extraction, `MutationDeclaration` contract, fit path, judge path, and gates are unchanged.
   - Judge: `test_thesis.safe_generate` resolves `resolve_dispatch_capability("judge")`; default `llm` preserves the existing API call, while `ZTARE_AGENT_DISPATCH_JUDGE=agent` routes through `dispatch_model`. Gemini response-schema config is folded into a textual JSON contract hint before dispatch; the existing JSON parser, schema retry, score caps, score contract, and deterministic gates remain the ratifier.
   - Dynamic committee: `generate_committee.safe_generate_committee` resolves `resolve_dispatch_capability("committee")`; default `llm` preserves Gemini/llm-runtime behavior, while `ZTARE_AGENT_DISPATCH_COMMITTEE=agent` routes through `dispatch_model`. The existing JSON parser owns the boundary.
   Nothing else in `main_loop` changes; the loop still owns mutate→fit→judge→loop-control. This is intentionally not treated as lift until fixed-substrate parity/A-B runs pass.

4. **Auditability.** The agent's tool-loop transcript is written to the run's cache dir (non-canonical); the canonical artifacts (candidate, scores, judge output, briefing) are produced exactly as today. Add a cold-replay-equivalence check to the A/B harness: a flag-off replay of the same iteration must reach an equivalent decision class.

5. **Parity + A/B gate.** Self-test: flag off ≡ current output on a fixed seed (byte-parity). Then a calibrated A/B (mutator agent vs llm) on a discriminating substrate, measuring advance-rate / iterations-to-fit, with the airgap asserted live and the parity arm as the negative control. Report token cost per iteration in BOTH arms (confirm agent ≈ API + bounded-loop, not O(N²)).

6. **Negative-space provider (externalize the procedural/negative memory).** Add `TriedFailedDigestProvider` (`src/ztare/orchestrator/briefing_providers/tried_failed_digest.py`) that aggregates the rejection signal the loop already produces: R1 error strings, contract-adherence violations, fit failures, and non-improving eval weakest-points → a "tried-and-failed" digest fed to the next mutator. This closes the honest gap warm memory had, externalized (stays fungible/airgapped — no warm state), and should reduce R1 bounces because the next mutator sees prior failures up front. It never gates.

7. **RD workbench router.** `src/ztare/research_director/autoresearch_workbench_router.py` returns `invoke_autoresearch`, `prepare_autoresearch_surface`, or `stay_out_of_loop` from the four prerequisites: stable evaluator, bounded claim, rubric readiness, and artifact surface. This is the explicit antidote to RD bypassing autoresearch by habit/economics.

8. **Action-impact carrier for out-of-loop agent work.** When the RD uses a persistent/subscription agent on a task that could plausibly use autoresearch, record the router decision as a GP-243 `domain=agentic_workbench` row with `ztare autoresearch route --record-decision-id <id>`. The command saves the route JSON under `analytics/public/queries/rd/autoresearch_routes/` and appends the validated action-impact row in one step. Required fields include the workbench-router decision, the missing surface if autoresearch was not used, worker metadata, and source refs. `record-agentic-route --route-json <route.json> --decision-id <id>` remains available for pre-saved route JSON, and `record-agentic-work --route-json-ref <route.json>` remains available for custom rows that need extra fields. Operations intelligence consumes these rows as the `agentic_ai_workbench` focus track, alongside reflexive-mining and factory-style read-model outputs.

9. **Read-only projection/user surfaces.** `make autoresearch-projection PROJECT=<slug>` and `ztare autoresearch projection --project <slug>` emit the read-only hypothesis/evidence projection over `eval_history`. The projection records admitted/pruned nodes, held-out/admission evidence when present, worker metadata, and reusable negative constraints derived from pruned failure signatures. `make action-intel-materialize-dry` compiles the action-intelligence read model without writing. These are inspection surfaces, not controllers.

10. **Benchmark the projected-state overlap before expanding it.** Run a fixed-substrate comparison of (a) existing flat/pivot/briefing loop, (b) projection-assisted RD selection, and (c) a projected-tree variant if implemented later. Required metrics: held-out/admission evidence rate, repeated-failure reduction, useful negative-constraint reuse, score gain, token/runtime cost, and false-admission incidents. Do not promote a tree controller without this result.

11. **Reuse audit before building**: run `primitive_amnesia "capability-aware model dispatch"`; grep `subscription_agent_runtime`, `_call_once`, the `BriefingProviders`, `forced_reframe`, `R1ExhaustionTracker`; cite the extension points or stop. The resolver is new only as a router; the provider is new only as a sibling.

## Open Questions

- Is there a discriminating autoresearch substrate today where verify-before-propose actually changes advance-rate, or does the mutator already mostly produce compiling/fitting candidates (making the uplift marginal)? Identify before scaling.
- Which verify-before-propose tools are worth exposing to the mutator first — compile-check, fit-probe, or evidence/Mathlib-equivalent search — and is the tool latency worth it per call?
- Does the judge agent path improve verdict quality only when it has runnable checks, or does the extra tool capability add noise/cost on rubric-only evaluation?
- Where does the four-axis taxonomy itself belong as a durable artifact — here (engine), or in the cognitive-firm repo (where the operator has a codex working on the firm model)? The taxonomy spans both; this spec only consumes it.
