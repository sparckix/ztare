# GP-249 — Cognitive-worker dispatch: capability ⟂ state ⟂ identity ⟂ transport

> **Seam metadata** · `seam_id:` GP-249 · `track:` engine · `status:` IMPLEMENTED v8 — mutator/judge/committee dispatch wired + RD workbench correction; empirical lift open · `last_updated:` 2026-06-11

**Status:** IMPLEMENTED v8. v1–v3 (Claude↔codex debate, §7) drifted (argued warm-vs-atomic per call-site without reading the autoresearch map). v4 re-anchored on the real map + the state×identity×transport taxonomy but framed the workbench as "fungible LLM that stays fungible — NO migration." v5 corrected the missing **capability** axis. v6 folded in the implementation order: metadata first, negative-space briefing second, then flag-gated fungible agent dispatch; **no RD session registry as the main move**. v7 recorded mutator call-site dispatch. v8 records that mutator, judge, and dynamic committee call sites are wired behind `ZTARE_AGENT_DISPATCH_<CALL_SITE>=agent`, route-json action-intelligence logging is available, and empirical lift remains open as a separate parity/A-B experiment.
**Cabinet:** `engine/` (the SHARED execution-substrate distinction across leanmill + autoresearch; reuses leanmill's `subscription_agent_runtime`, no fork).
**Authored:** 2026-06-09.

> **What this seam IS:** the canonical statement that "LLM vs agent" is a **capability** axis ORTHOGONAL to fungibility, state, and transport — and the design that lets the autoresearch workbench gain agentic capability (verify-before-propose, in-loop error recovery) WITHOUT losing the fungibility/airgap/externalized-state the discovery loop runs on.
>
> **What this seam is NOT:** a blanket migration to an agentic orchestrator (that breaks reproducibility — kept deterministic); a warm-shard mutator (v2/v3 over-scoped — dropped); a session manager for the RD (the RD is the EXTERNAL agent — §5); a claim that API calls are inherently inferior. Transport is a cost/capability surface; the worker category is the four-axis point.

---

## 0. The taxonomy — FOUR orthogonal axes (the operator's distinction, made precise; spans BOTH repos)

"API vs agent" is **transport**, not a worker category — anything can be promoted across it, so on its own the label dissolves. A cognitive worker is a point in a 4-axis space, all independent:

- **Capability** — *LLM* (one forward pass: prompt→completion) vs *agent* (a bounded act→observe→reason→repeat loop with tool-use). This is a capability threshold, not "more turns": agentic GPT-3.5 has been shown to beat single-shot GPT-4 (§6). **This is the axis v4 missed.**
- **State** — *stateless* (context supplied EXTERNALLY each call) vs *stateful* (carries continuity internally).
- **Identity / fungibility** — *fungible* (swappable commodity; any capable worker does this call; parallelizable; airgappable) vs *persistent* (a named entity whose ACCUMULATED context is its value).
- **Transport** (a cost/capability choice, not a category) — metered API vs subscription CLI vs local process.

The historically-conflated cell is **fungible AGENT** = agent capability + fungible identity + stateless-from-outside. It is not exotic: **leanmill's agentic leaf is the existence proof** — best-of-N codex/claude workers, each given the goal + a briefing, swappable, parallel, airgapped, returning a typed proof. Capability-rich AND fungible.

Then the old labels resolve as *regions*, not points:
- **"LLM" call** = stateless + fungible, **LLM-capability** — today's in-loop workbench.
- **"agent"** (as the operator used it loosely) = persistent + stateful — the **research director** (the strange loop). But that's the RD's *identity/state*, not its capability — and the RD is EXTERNAL (§5).
- **"fungible agent"** = stateless + fungible + **agent-capability** — the upgrade this seam enables for the workbench.

**The cognitive firm needs the whole space, and the architecture already FORCES the non-collapsible parts:**
- The **cross-family epistemic airgap** (`autoresearch_loop.py:254` — mutator and judge MUST be different provider families) *requires fungibility* of the workbench. You cannot make the mutator one persistent single-identity worker without breaking the airgap. The literature independently says you *want* this: homogeneous worker scaling has strong diminishing returns; diversity sustains the gains (§6).
- The **strange loop** (a director reasoning about / improving the loop that contains it) *requires persistence* — but it lives OUTSIDE the loop (§5).
- **Capability is free to vary independently of both.** A fungible, stateless, airgapped worker can be LLM-capability OR agent-capability. That is the whole insight of v5.

## 1. The REAL architecture (grounded in the map) — the briefing is the enabling invariant

`autoresearch_loop.py`: a per-iter loop of **mutate → fit → judge → loop-control**, instrumented heavily (DAG steering, pivot heuristics, op-class enrichment, fit-primitive/Lagrangian/Buckingham, compiler-bounce retry). Two facts decide the migration:

- The **in-loop workbench is already stateless + fungible by design.** Its cross-iteration state is EXTERNALIZED into the **MutatorBriefing** provider registry (`src/ztare/orchestrator/briefing_providers/`), persisted per-iter (`mutator_briefing_iter_NNN.md`). This is the structured/procedural memory pattern the cost literature prescribes (§6). The briefing is what makes the worker stateless-from-outside REGARDLESS of capability: feed an *agent* the same briefing and it is just as fungible, airgapped, and cheap (≈ API cost + one bounded tool-loop, NOT O(N²) transcript replay).
- The **out-of-loop research director / strange loop is the only persistent role** — and it is EXTERNAL (the operator, or the Claude-Code agent invoking autoresearch as a tool; §5). It is not a call site inside the loop.

**Consequence (v6):** the briefing does NOT become unnecessary under an agentic workbench; it is the mechanism that lets a capability-upgraded worker stay fungible + airgapped + cheap. Hand the agent a warm transcript instead and you reintroduce O(N²) cost, leak across the airgap, and kill swappability. So: **capability is the variable, the briefing is the invariant.**

## 2. The migration — a per-call-site CAPABILITY promotion (v5 supersedes v4's "no migration")

| in-loop worker | state | identity | capability today | capability target | verdict |
|---|---|---|---|---|---|
| **mutator** | stateless (BriefingProviders) | **fungible** (airgap) | LLM (propose blind) | **agent** (verify-before-propose: compile/fit/search the candidate, recover before emission) | **WIRED behind flag** — `safe_mutate` uses `dispatch_model` when `ZTARE_AGENT_DISPATCH_MUTATOR=agent`; this covers the whole mutator generation boundary (initial proposal, alignment rewrite, compiler-bounce retries, parse-retry calls), not only R1. Same downstream extraction, mutation contract, fit path, and gates. Lift unproven until A/B. |
| **judge** | stateless | **fungible** (airgap, ≠ mutator family) | LLM (verdict JSON) | optionally **agent** (run/check then emit verdict JSON) | **WIRED behind flag** — `test_thesis.safe_generate` uses `dispatch_model` when `ZTARE_AGENT_DISPATCH_JUDGE=agent`; response-schema hints are folded into the prompt and the existing JSON parser, schema retry, score caps, and gates still ratify. Use where the judge has a runnable verification surface; otherwise atomic remains cheaper and more reproducible. |
| **dynamic committee** | stateless | fungible | LLM (panel JSON) | optionally **agent** (inspect context then emit panel JSON) | **WIRED behind flag** — `generate_committee.safe_generate_committee` uses `dispatch_model` when `ZTARE_AGENT_DISPATCH_COMMITTEE=agent`; existing JSON parser owns the boundary. |
| **fit / gates** | stateless | fungible | LLM/deterministic | mostly atomic | usually NO — structured single-shot is cheaper + more reproducible. |
| **research director / strange loop** | stateful | persistent | — | — | NOT a call site — EXTERNAL agent (§5). No internal mechanism. |

Both modes coexist **per call-site**, routed by policy (§4), default-off (parity). The loop control (mutate→fit→judge→loop-control sequencing) stays **deterministic** — the agent upgrade is on the *worker*, never the *orchestrator* (reproducibility, §6).

**What the intra-step loop SUPERSEDES (grounded — the existing R1 bounce).** There is ALREADY a primitive, externally-orchestrated verify-before-propose: the **Runner R1 path** (`src/ztare/validator/autoresearch_loop.py`). The mutator emits BLIND; R1 then validates the submission — import-safety dry-run (GP-156, `:1152`), the required `MutationDeclaration` JSON header / typed contract (`:1119`, `core/mutation_contract.py`), bounded-discriminator syntax (`:1049`), forced-reframe AST-bucket compliance (`orchestrator/forced_reframe.py:536`) — and on failure **raises `ValueError` so the mutator gets the error STRING and ONE free retry**, capped by `R1ExhaustionTracker` at **3 strikes** before flagging the mutator off-rails. This is suboptimal: each bounce is a FULL fresh LLM call re-sending the whole prompt (the O(N²) tax), the worker sees only the error string (not the live check), and it's strike-capped — so the prompt even ships a hardcoded *"COMMON R1 REJECTION PATTERNS — DO NOT EMIT THESE"* list (`:2394`) to dodge the bounce by prompt-engineering. The intra-step agentic loop **internalizes the retry but NOT the gate**: R1's *checks* become *tools the worker calls itself* before emitting, so it revises in-place (cheaper, sees the tool not the string, not strike-capped); R1's *gate* stays loop-side as the deterministic ratifier — the verification authority is never delegated to the worker. So the change is precise: **keep the R1 gate, retire the R1 bounce.**

## 2b. BriefingProvider — the tried-and-failed / negative-space ledger (operator add)

The one thing warm memory could give that the briefing only partially had is procedural/**negative** knowledge — "I already tried AST-bucket X / primitive Y / this mutation shape and it failed." The principled fix (keep it externalized ⇒ fungible, airgapped, cheap) is a `TriedFailedDigestProvider` that aggregates rejection signal the loop already produces: R1 rejection error strings, contract-adherence violations, mutation mismatch records where available, and fit/eval failures. It joins the provider registry as a digest fed to the next mutator. Effect: (a) closes the only honest gap warm memory had — *without* warm state; and (b) directly reduces R1 bounces (the next mutator sees the prior failures up front instead of re-discovering them). It enriches the briefing, never gates. Cross-repo analogue: a no-good/refutation store, externalized rather than private warm memory.

**Granularity (operator probe — the lever is INTRA-step capability, NOT cross-iteration memory).** The stateless LLM mutator is "fresh every iteration" *at the worker* but the loop is NOT memoryless: the `MutatorBriefing` re-injects accumulated judge feedback + fit telemetry + trajectory each iteration, so "read thesis, improve off judge feedback" ALREADY happens — the memory just lives in the briefing, not the worker. A *warm* agentic mutator would only RELOCATE that memory (briefing → worker's internal context across the N iterations) — a strictly worse location (breaks airgap, fungibility, O(N²) cost) and ~redundant with the briefing. That is the warm-shard design v4 killed; equating "agentic" with "memory" is the trap. The non-redundant lever is a DIFFERENT granularity: a tool-loop INSIDE one mutation step — propose candidate → compile/fit-check it itself → revise → emit — so error recovery happens *within the iteration, before the candidate leaves the worker*, instead of being discovered one iteration later by fit/judge. This is orthogonal to memory: it works the same whether the worker is fresh-every-iteration or warm. **Claim the lift on intra-step verify-before-propose; never on warm memory.** The one thing warm memory could add that the briefing can't = procedural/negative "already-tried-X" knowledge (the briefing is a lossy 5-provider projection) — but the principled fix is a NEW provider (externalized, airgapped, fungible), not warm state. Even that argument routes back to the briefing.

## 3. Auditability rule (codex R1/R2, retained — the governance analogue)

Warm/agentic workers may PROPOSE + PRIORITIZE; explicit artifacts must JUSTIFY + COMMIT. CANONICAL = candidate set, novelty archive, decision rationale, scores, judge outputs, the BriefingProvider artifacts. CACHE = the agent's local tool-loop reasoning. A cold replay must reach an equivalent DECISION CLASS (not byte-identical). The opaque transcript is never the authoritative memory. This is the leanmill governance analogue: solver PROPOSES, artifacts RATIFY.

## 4. The one thing to BUILD — `dispatch_model`, capability-aware (reuse, no fork)

A thin resolver over the existing runtime, NOT a new manager. `dispatch_model(prompt, briefing, *, capability, fungible, stateful, continuity_key, backend)` resolves the taxonomy → routes:
- `capability=llm` → one `_call_once` (today's path; API or atomic CLI).
- `capability=agent`, `fungible=True`, `stateful=False` → a **bounded tool-loop** seeded with the SAME briefing, returning the SAME typed contract (`Mutation` / judge verdict). Reuses `run_subscription_agent_with_recovery` (`subscription_agent_runtime.py`); tools are the verify-before-propose primitives (compile/fit/search) — reuse leanmill's `agent_tools` surface where the tool already exists, do NOT fork.
- `stateful=True, persistent` → resumed warm session via `--resume` (`subscription_agent_runtime.py:41`) — reserved for the RD ONLY, and the RD is external, so this branch is latent (built for symmetry, unused in-loop).

Flag-gated `ZTARE_AGENT_DISPATCH=off` (default) keeps today's path. Per-call-site override is explicit: `ZTARE_AGENT_DISPATCH_MUTATOR=agent`, `ZTARE_AGENT_DISPATCH_JUDGE=agent`, or `ZTARE_AGENT_DISPATCH_COMMITTEE=agent` promotes only that call site. `ZTARE_AGENT_DISPATCH=agent` promotes every wired call site, so use scoped flags for controlled experiments. No autoresearch-local session manager; the resolver composes the shared subscription runtime.

## 5. The research director is the EXTERNAL agent (operator correction)

The RD is not a call site to migrate — it is the agent OPERATING autoresearch as a tool. The strange loop = that external agent reasoning about / refining the loop it runs. So: **no internal session-registry-for-the-RD** (v4 over-built this). The persistent+stateful branch in §4 exists only for completeness; the in-loop work is all fungible workers. The RD's statefulness lives in the external agent's own context + the canonical artifacts it reads/writes.

**Underuse correction (2026-06-11).** Reflexive mining showed the live substrate had shifted toward out-of-loop agent work, while paper/prose still positioned autoresearch as the in-loop workbench. That drift is partly economic: subscription Codex/Claude work is cheap at the margin while API loops feel expensive, so the RD bypasses the workbench. The fix is not to collapse RD and workbench into one persistent agent. The fix is:

1. record worker shape in run/projection carriers (`worker_archetype`, `worker_capability`, `worker_state`, `worker_identity`, `transport`);
2. feed negative-space failure memory into the existing briefing;
3. give the RD a small routing primitive that says when a task has enough evaluator/rubric/artifact surface to invoke autoresearch;
4. only then A/B a flag-gated fungible agent mutator.

That preserves the strange-loop architecture: external persistent RD chooses and interprets workbench runs; the in-loop workers remain fungible, airgapped, and ratified by deterministic gates.

## 5b. Projected-state overlap — adopt the projection lesson, not the controller shape

The useful lesson for this seam is not to make the worker warmer. It is that
long-horizon autonomous research benefits from explicit external research state:
hypotheses, artifacts, evidence, failed directions, and admission decisions in
one inspectable projection. ZTARE already has most of those ingredients, but
they are spread across `eval_history`, DAG steering logs, gate artifacts, GP
ledgers, action-intelligence rows, and RD notes.

The correct GP-249 response is therefore a **read-only projection over existing
state**, not a new hypothesis-tree controller:

- `src/ztare/validator/hypothesis_projection.py` emits a hypothesis/evidence
  projection from existing autoresearch run history.
- The projection records worker metadata (`worker_archetype`,
  `worker_capability`, `worker_state`, `worker_identity`, `transport`) so
  in-loop API work, fungible agent work, and out-of-loop RD work can be compared
  rather than hand-waved.
- It counts held-out/admission evidence only when present; it does not infer it
  from development score.
- It exposes pruned failure signatures as reusable negative constraints, giving
  the workbench a "do not re-open this failed direction" inspection surface
  without granting the projection admission authority.

Boundary: ZTARE keeps its gates, claim membrane, briefing providers, and
action-intelligence rows. A pure tree controller would duplicate those
authorities and weaken the membrane. The open empirical question is a benchmark:
flat loop vs projected-tree inspection vs the existing pivot/briefing loop on a
fixed substrate. Until that benchmark exists, the projection is advisory.

## 6. Literature — is API-LLM suboptimal vs agent, BEYOND cost? (operator asked to check)

Cost favors agents under subscription, but it is not the decisive axis — and the cost objection that killed the first attempt was likely an implementation artifact:

- **Capability ceiling (the real upside).** act→observe→reason→repeat solves tasks intractable for single-shot; agentic GPT-3.5 has beaten single-shot GPT-4. ([CodeToDeploy](https://medium.com/codetodeploy/agentic-systems-without-the-hype-when-multi-step-llm-workflows-actually-improve-software-e1492ebdfacf), [MindStudio](https://www.mindstudio.ai/blog/what-is-loop-engineering-ai-coding-agents)) → for us: mutator verify-before-propose; in-loop error recovery single-shot can't do.
- **The "token too high" was a misimplementation.** Naive agent loops are O(N²) because the stateless API re-bills the whole transcript each call ([Augment Code](https://www.augmentcode.com/guides/ai-agent-loop-token-cost-context-constraints)). Prefix/KV caching → ~90% input-cost cut on stable prefixes ([digitalapplied](https://www.digitalapplied.com/blog/kv-cache-optimization-techniques-2026-engineering-guide)); structured/procedural memory → equivalent accuracy at ~5% of full-context tokens, 20× savings ([Memori](https://arxiv.org/pdf/2603.19935)). **The BriefingProviders ARE that fix.** Feed the agent the briefing (not the transcript) and the cost objection dissolves.
- **Diversity/airgap is epistemically decisive.** Homogeneous worker scaling → strong diminishing returns (redundant trajectories); diversity sustains gains ([agent-scaling-via-diversity](https://arxiv.org/pdf/2602.03794)). A *positive* argument to keep the workbench fungible even when agentic; one persistent mutator would be worse for discovery.
- **Reproducibility → keep the ORCHESTRATOR deterministic.** Autonomous agents strain reproducibility (same query → different trajectory, drift, hard to audit; [Autonomous Science survey](https://arxiv.org/html/2509.09915v1)); controlled pipelines are reproducible ([ZenML](https://www.zenml.io/blog/steerable-deep-research-building-production-ready-agentic-workflows-with-controlled-autonomy)). Verdict: agentic *worker*, deterministic *loop* — exactly §2/§3.

Net: API-LLM is not "suboptimal" wholesale. It is optimal for atomic, structured, reproducibility-critical calls; agentic is optimal where verify-before-propose/error-recovery pays. → support BOTH, route per call-site.

## 7. Debate log (v1→v3, then the grounding corrections)

**R1** (codex): mutator hybrid not atomic; semantic dispatch not backend modes; reuse leanmill infra; transcript never canonical. **R2** (codex): start archive-fed-atomic not warm shards; auditability = equivalent decision-class; concrete piece = a session registry. **GROUNDING CORRECTION v4 (operator):** the debate drifted — neither agent read the autoresearch map; the BriefingProviders already ARE the archive, the airgap forces fungibility, the real distinction is state×identity×transport. v4 dropped the warm-shard machinery. **CORRECTION v5 (operator):** v4 still missed the **capability** axis and over-built an RD session-registry. Fungibility ⟂ capability — you can have fungible AGENTS (leanmill's leaf proves it). The migration is a per-call-site capability promotion (briefing-fed, flag-gated), the RD is the EXTERNAL agent (no internal registry), and the literature (§6) confirms the token blowup was an implementation artifact + that diversity/airgap and deterministic orchestration are the binding constraints. LESSON: name all FOUR axes before designing; "API vs agent" hides a capability promotion that is independent of fungibility, state, and transport.

## 8. Downstream

Spec: `research_areas/specs/active/engine/GP-249_warm_agent_dispatch_spec.md` (the implementation blueprint — capability-aware `dispatch_model`, parity-default, per-call-site routing).

Action-impact carrier: GP-243 `domain=agentic_workbench` rows record RD/out-of-loop agent use at this boundary. This is the durable comparison table for in-loop autoresearch vs prepared surfaces vs manual agent labor; it is not an internal RD session registry.
