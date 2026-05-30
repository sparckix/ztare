# GP-102 — Reflexive Primitive Discovery: Mechanizing the Inception Move

> **Seam metadata** · `seam_id:` GP-102 · `track:` apparatus · `status:` open - opened 2026-04-19 · `last_updated:` 2026-05-08


**Status:** open *(inferred 2026-05-08 — needs operator review)*

## Status

open — opened 2026-04-19

## ID

GP-102

## Eigenquestion

Can a periodic cron goal reliably identify when a new reflexive engineering primitive is needed, and at which layer of the stack?

## Problem Statement

Every reflexive primitive in the catalog (`reflexive_engineering_primitives.md`) was discovered the same way: the principal observed a failure class, recognized it as an infrastructure problem (not a science problem), identified which ZTARE leg applies, and proposed the fix. The engine discovered none of them.

The primitives:
- **Token-Optimized Self-Modeling** — principal watched agent make partial-view mistake
- **Inception Pattern** — same incident, same principal inception
- **Hybrid Persona Router** — principal noticed static personas were stale
- **Residual Isomorphism** — principal watched Langevin stagnate at exp/exp ratio
- **Reflexive Orchestration** — principal noticed process friction in goal lifecycle

The pattern: principal frustration → inversion → new primitive. The frustration signal doesn't exist in any log file.

### The Proxy Signal

While the creative act of inventing a primitive can't be mechanized (yet), the *detection* that one might be needed CAN be. The proxy: when the engine exhausts all known recovery mechanisms and still doesn't improve, *something structural is wrong*. A periodic review — not a crisis detector — is the honest implementation.

## Proposed Architecture

### A Cron Goal, Not a Signal Detector

The simplest mechanism that could work: a scheduled goal in the orchestrator that runs every N completed goals (or every N hours of wall clock time). Not triggered by crisis — triggered by calendar.

```yaml
# config/goals/reflexive_audit.yaml
name: reflexive_primitive_audit
trigger: cron
frequency: every_5_goals  # or every_48h, tunable
type: diagnostic

stages:
  - name: gather_telemetry
    description: >
      Read recent iteration_telemetry.jsonl, transitions.jsonl,
      latent_distance.jsonl, and structural_memory.json across
      all active projects. Extract: stagnation patterns, gate
      failure persistence, recovery primitive fire rates,
      persona router dynamic generation frequency.

  - name: convene_process_committee
    description: >
      Use the Hybrid Persona Router (GP-079) to select reviewers
      based on the telemetry summary. The "failure families" are
      process-level: "persistent_stagnation", "gate_ceiling",
      "primitive_exhaustion", "persona_churn".

  - name: diagnose_layer
    description: >
      The committee answers: Is any layer of the stack stuck in
      a way that no existing reflexive primitive addresses?
      If yes: which layer, what is the failure class, and which
      ZTARE leg applies reflexively?
      If no: output "all clear" and close the goal.

  - name: propose_seam
    description: >
      If a gap is identified, draft a seam at n=0 in
      research_areas/private/seams/ with eigenquestion,
      proposed primitive, and the telemetry evidence that
      motivated it. Principal reviews before promotion.
```

### What This Does NOT Do

- **Invent the primitive.** The creative move (Compress applied to X, Invert applied to Y) still requires principal or high-capability agent judgment. The cron goal narrows the search space: "this layer is stuck, here's the failure trace."
- **Implement anything.** Output is a seam, not code. The principal decides whether the proposed primitive is real.
- **Replace the principal.** The principal can still inception primitives directly. The cron goal catches cases the principal isn't watching.

### Why Cron, Not Event-Driven

Event-driven detection ("fire when compound failure signal exceeds threshold") requires knowing what the compound signal looks like in advance. But by definition, a *new* primitive addresses a failure class you haven't seen before — so you can't pre-specify its trigger.

A cron review avoids this chicken-and-egg: it periodically asks "what's stuck?" without needing to know the shape of the stuckness. This is how Kaizen works in manufacturing — periodic, scheduled, not triggered by crisis.

The frequency tunable (`every_5_goals` or `every_48h`) controls the cost/benefit: too frequent wastes tokens on "all clear" reports, too infrequent misses opportunities. Start with every 5 goals and tune.

## Scope

**Covers:**
- What telemetry to ingest for the periodic review
- How to route personas for process-level failure families
- What format the diagnostic output takes (seam at n=0)
- How to distinguish "the science is hard" from "the machinery is broken"
- Frequency tuning

**Does not cover:**
- Automating primitive invention (creative act, out of scope)
- Automating primitive implementation (requires code changes)
- Replacing principal judgment on whether a proposed primitive is real

## Visibility Architecture: What Can the Audit Actually See?

The cron goal needs to inspect multiple layers of the stack. The honest inventory of what exists today vs what's aspirational:

### Layer Catalog

| Layer | Code | Structural Map | Telemetry Emitted Today | Gap |
|-------|------|---------------|------------------------|-----|
| Discovery engine | `autoresearch_loop.py` (4100 LOC) | `autoresearch_loop_architectural_map.md` | `iteration_telemetry.jsonl`, `structural_memory.json`, `fit_result.json` | `latest_eval_results.json` is ephemeral (overwritten per iteration) |
| Supervisor / orchestrator | `supervisor_*.py` (~20 files) | **None** | **None** (`transitions.jsonl` not wired) | No map, no persistent telemetry |
| V4 kernel meta-runner | `v4_meta_runner.py` | **None** | Inherits from discovery engine | No map |
| Bridge meta-runner | `bridge_meta_runner.py` | **None** | Inherits from discovery engine | No map |
| Persona / review layer | `personas/routing.py`, `registry.py` | **None** (small enough) | None (promotion events not logged) | Router selection history not persisted |
| Composition / Component D | `topology_synthesizer.py` | **None** | `structural_memory.json` (family exhaustion) | No standalone telemetry |
| Gate architecture | `deterministic_charter_gates.py`, `test_thesis.py` | **None** | Gate results in eval (ephemeral) | Gate history not persisted across iterations |
| Cognitive Gym / A-B form | Goal configs in `config/goals/` | Self-documenting (YAML) | Via discovery engine | No process-level telemetry |

### What This Means for the Cron Goal

**Today, the cron goal can reliably inspect:**
1. Per-project `iteration_telemetry.jsonl` — stagnation patterns, score trajectories, failure rates across 36 projects
2. Per-project `structural_memory.json` — expression family exhaustion, fit history
3. Per-project `fit_result.json` — champion expressions, parameter counts
4. The one architectural map (discovery engine pipeline)
5. Git history — artisan edits, commit patterns, which files change together
6. Goal configs — declarative intent for each project type

**Today, the cron goal CANNOT inspect:**
1. Supervisor-level process health (no `transitions.jsonl`)
2. Gate failure persistence across iterations (eval results are ephemeral)
3. Router selection history (which personas were tried, which converged)
4. Cross-project patterns (no aggregation layer)

### Artisan Mode: When GP-070 Is Not Running

The principal operates in artisan mode most of the time. This means:
- **No orchestrator telemetry.** `transitions.jsonl` doesn't exist because goals aren't flowing through GP-070's stage-gate pipeline.
- **Discovery engine telemetry still accumulates.** `iteration_telemetry.jsonl` and `structural_memory.json` are written by `autoresearch_loop.py` regardless of who triggers the run.
- **Git is the artisan audit trail.** Manual edits to code, configs, seams, and specs are captured in commit history. The cron goal can read `git log` to detect which layers are being touched and what the commit messages say about friction.
- **The Executive Inbox pattern still works.** Output is a seam at n=0, landing for principal review. Artisan mode just means the principal triggered the run manually instead of the orchestrator scheduling it.

### Visibility Gaps to Close (Prerequisites for Full Effectiveness)

These are not blockers for opening GP-102, but they limit what the cron goal can diagnose:

| Gap | What to build | Blocks which process family? |
|-----|--------------|------------------------------|
| No `transitions.jsonl` | GP-070 writes stage transitions to persistent log — SKIP in artisan mode, use `git log` instead | `gate_ceiling` (can't see dwell time) |
| ~~Ephemeral eval results~~ | **CLOSED 2026-04-19**: `eval_history.jsonl` appended in PHASE_E | ~~`gate_ceiling`, `persistent_stagnation`~~ |
| No router selection log | Persona router writes selection + convergence to `persona_telemetry.jsonl` | `persona_churn` (can't count dynamic generations) |
| No supervisor map | Build GP-101-style map for supervisor_loop.py | `context_drift` in supervisor layer |
| No cross-project aggregation | Script that scans `projects/*/workspace/` and produces summary | All families (currently per-project only) |

### Minimum Viable Visibility (What to Ship First)

The cron goal can launch with just what exists today:
1. Scan `projects/*/workspace/iteration_telemetry.jsonl` for stagnation patterns
2. Scan `projects/*/workspace/structural_memory.json` for family exhaustion
3. Read `git log --since="last audit"` for artisan activity
4. Read the reflexive primitives catalog to avoid re-proposals

This is enough to detect `persistent_stagnation` and `primitive_exhaustion` across all projects. The other process families (`gate_ceiling`, `persona_churn`, `context_drift`) require the visibility gaps above to be closed first.

## Open Questions

**Q1: Can the committee reliably distinguish "the science is hard" from "the machinery is broken"?** — **RESOLVED (Turn 4)**

This is the decisive discrimination. A project that stagnates at score 50 because the ground truth is genuinely hard (high-dimensional, noisy, chaotic) should NOT trigger a process fix. A project that stagnates because Component D can't see the farther-tail (Langevin) SHOULD.

**Resolution: Variance of Failure (Deming's SPC applied to gate telemetry)**

The discriminator is not the *magnitude* of the failure — it is the *variance* of the failure across iterations. This maps directly to W. Edwards Deming's Statistical Process Control distinction between common-cause variation (inherent to the system, not assignable) and special-cause variation (assignable to a specific structural factor):

| Signature | Failure variance | Gate behavior | Latent motion | Deming category | Diagnosis |
|-----------|-----------------|---------------|---------------|-----------------|-----------|
| **Machinery broken** | Low (zero-variance stagnation) | Same gate fails K times with similar residual | Low — Component D loops same topologies | Special-cause (assignable to structural defect) | Trigger reflexive audit |
| **Science is hard** | High (thrashing) | Failures rotate across gates | High — mutator tries radically different forms | Common-cause (inherent noise) | Do NOT trigger process fix |

**Historical grounding:**

- **Deming / SPC (1950s):** A manufacturing process "in control" with common-cause variation should not be tampered with — tampering (adjusting a stable process based on individual deviations) makes things worse. Deming's Rule 1: don't intervene on common-cause variation. Applied here: a project thrashing across different gates is "in control" — the engine is searching, just in hostile terrain. Triggering a process fix on a thrashing project is Deming's cardinal sin of "tampering."

- **Ohno / Toyota Production System (1970s):** The "5 Whys" technique distinguishes symptom from root cause. Applied here: when the same gate fails repeatedly, asking "why?" five times traces back to a structural constraint (grammar ceiling, missing primitive, wrong parameter namespace). When different gates fail each iteration, the 5 Whys traces back to "the data surface is rough" — not actionable by process change.

- **Kaizen (continuous improvement):** Kaizen targets *systematic* waste, not random variation. The periodic audit (GP-102's cron goal) IS Kaizen — but Kaizen practitioners know that not all friction is waste. Some friction is the work itself. The variance discriminator separates actionable systematic friction from inherent problem difficulty.

- **Shewhart control charts (1920s):** The original tool. Plot gate failure identity across iterations. If the same gate appears K+ times in a row (a "run" in SPC terms), it's a special-cause signal. If gate failures distribute randomly, the process is in statistical control. Shewhart's insight: the chart doesn't tell you *what's wrong* — it tells you *whether something assignable is wrong*. Same here: the discriminator doesn't identify the missing primitive, it identifies that a primitive is missing.

**Codified discriminator logic for `gather_telemetry`:**

```
flag_for_audit(project) IF AND ONLY IF:
  1. stagnation_count > N (persistent, not transient)
  2. all recovery primitives have fired (GP-087, Component D, persona router)
  3. gate_failure_variance < threshold:
     - read eval_history.jsonl for last K iterations
     - extract gate_verdicts from each
     - compute: do the SAME gates fail across iterations?
     - if >80% of failures are the SAME gate → low variance → machinery
     - if failures rotate across 3+ distinct gates → high variance → science
  4. latent_distance trend is flat (optional, from GP-029 telemetry):
     - high latent motion + stagnation = thrashing (science is hard)
     - low latent motion + stagnation = paralysis (machinery is broken)
```

**Why this is safe to run unattended:** The discriminator prevents false positives. A difficult dataset with inherent noise will produce high-variance failures — the cron goal sees rotating gate failures and reports "all clear, science is hard." Only zero-variance stagnation (same gate, same residual, same topology loop) triggers a process audit. This prevents the system from generating a pile of spurious "process improvement" seams.

**Q2: What are the process-level failure families?**

The persona router uses science-level failure families (`inductive_epistemology`, `model_class_constraint`). The reflexive audit needs process-level families. Candidates:

| Process family | Signal | Layer |
|---------------|--------|-------|
| `persistent_stagnation` | Stagnation > N after all primitives fired | Grammar / primitives |
| `gate_ceiling` | Same gate fails on every candidate for K iterations | Gate architecture |
| `primitive_exhaustion` | Structural memory shows all families exhausted | Component D |
| `persona_churn` | Router generates >3 dynamic personas without promotion | Review layer |
| `parameter_collision` | Fit fails with duplicate parameter names | Composition layer |
| `context_drift` | Agent edits break invariants the map covers | Self-model / map |

**Q3: How does this interact with GP-070 (orchestrator)?**

The reflexive audit goal is a first-class goal in the orchestrator. It runs through the same stage-gate process as any other goal. The only difference: its input is cross-project telemetry (not a single project's evidence) and its output is a seam (not a thesis). The orchestrator doesn't need new machinery — just a new goal config.

**Q4: Should the audit goal have access to the reflexive primitives catalog?**

Yes — the catalog (`reflexive_engineering_primitives.md`) is the "what we already know" baseline. The audit committee should read it before diagnosing, so it doesn't re-propose existing primitives. This is analogous to how the persona router reads the static catalog before generating dynamically.

## Recommendation

Adopt the cron goal architecture with variance-of-failure discriminator. Specifically:

1. **Mechanism:** A periodic goal in the orchestrator (or manually triggered in artisan mode) that scans cross-project telemetry for zero-variance stagnation — the "Groundhog Day" signature where the same gate fails with similar residual across K+ iterations after all recovery primitives have fired.

2. **Visibility MVP:** Scan `iteration_telemetry.jsonl` (stagnation), `structural_memory.json` (family exhaustion), `eval_history.jsonl` (gate failure variance, now shipping), and `git log` (artisan activity). No new infrastructure required.

3. **Discriminator:** Deming's SPC logic. Low failure variance + low latent motion = machinery broken → trigger audit. High failure variance + high latent motion = science is hard → "all clear." This prevents false-positive process audits on difficult substrates.

4. **Output:** A seam at n=0 in `research_areas/private/seams/` with eigenquestion, proposed primitive, and telemetry evidence. Principal reviews before any promotion or implementation.

5. **Frequency:** Every 5 completed goals or manually triggered. Tunable. In artisan mode, the principal triggers it when they sense friction — the cron is a reminder, not an automation.

6. **Committee:** Process Committee selected via GP-079 Hybrid Persona Router using process-level failure families (`persistent_stagnation`, `gate_ceiling`, `primitive_exhaustion`, `persona_churn`, `parameter_collision`, `context_drift`). Additional reviewers: Deming (SPC/control charts), Ohno (Toyota/root cause analysis) as process-specific lenses alongside the existing Munger/Dijkstra seats.

**Next step:** Open spec per GP-053 sequencing. The spec should cover the `gather_telemetry` implementation (scanner function), the discriminator logic (variance computation), and the `propose_seam` output format.

## Cross-references

- `research_areas/private/philosophy/reflexive_engineering_primitives.md` — the catalog this mechanism extends
- `research_areas/private/seams/GP-079_persona_library_unification_seam.md` — the router that selects the process committee
- `research_areas/private/seams/GP-087_residual_driven_primitive_generation_seam.md` — the most recent primitive, discovered by principal inception
- `research_areas/private/seams/GP-070_*` — the goal orchestrator this runs inside

## Debate Log

### Turn 1 — Operator (2026-04-19)

Principal observed that all reflexive primitives were discovered via manual inception (principal frustration → inversion → fix). Proposed mechanizing the detection via the goal orchestrator: "maybe this is just a cron every X time that is manifested as a new goal." Key insight: the creative invention can't be automated, but the periodic "is anything stuck?" review can. Cron over event-driven because you can't pre-specify the trigger for a failure class you haven't seen yet.

### Turn 2 — Operator + Engine (2026-04-19)

Principal raised the visibility question: "how will it have visibility of all the potential layers and code?" Stack includes general-purpose projects, v4 kernel, cognitive gym, A/B form, supervisor loop — many improvement points. Also flagged artisan mode as the common operating mode (GP-070 not always running).

Ground truth audit: `iteration_telemetry.jsonl` exists across 36 projects, `structural_memory.json` across 30. But `transitions.jsonl` (orchestrator) doesn't exist at all, `latest_eval_results.json` is ephemeral (overwritten per iteration), and only the discovery engine has a structural map (supervisor, v4, bridge have none).

Resolution: ship the cron goal with minimum viable visibility (iteration telemetry + structural memory + git log + primitives catalog). This is enough for `persistent_stagnation` and `primitive_exhaustion`. The other process families (`gate_ceiling`, `persona_churn`, `context_drift`) are gated on closing specific visibility gaps: persistent eval history, router selection log, and supervisor structural map.

Key insight: in artisan mode, git IS the audit trail. The cron goal reads commit history to detect which layers are under friction. The orchestrator telemetry is a nice-to-have, not a prerequisite.

### Turn 3 — Engine (2026-04-19 11:11:24 EST) — Expert panel closes visibility gaps

Expert panel convened (Munger, Dijkstra, Norvig, Karpathy) to close the 5 visibility gaps and determine shipping order. Panel constraint: principal operates in artisan mode — solutions that add friction will be abandoned.

**Panel verdicts:**

| Gap | Verdict | Rationale |
|-----|---------|-----------|
| Ephemeral eval results | **Ship now** — append slim record to `eval_history.jsonl` in PHASE_E | Highest value, lowest cost (2 lines). Unblocks `gate_ceiling` + `persistent_stagnation` at gate-level granularity. |
| Cross-project aggregation | **Free** — the cron goal IS the aggregator | No separate layer needed. `gather_telemetry` stage scans `projects/*/workspace/` directly. Compare stagnation duration and primitive exhaustion depth, not raw scores (Dijkstra: different rubrics make raw scores incomparable). |
| Artisan-mode git scan | **Ship with cron goal** | `git log --since="last audit" --name-only` shows which layers are changing and how often. Git is the artisan audit trail. |
| Router selection log | **Defer** | Persona router not yet in regular use. Instrument when it is. When ready: `RouteResult.log_to()` method + one call site. |
| Orchestrator transitions | **Skip** | GP-070 is not the daily driver. Building telemetry for a system you're not using is a bridge to nowhere. Git log is the artisan substitute. |
| Structural maps (supervisor, v4, bridge) | **Reactive** | Build per-file when a partial-view error occurs or cron goal flags a candidate. Don't speculatively map files that haven't caused problems. |

**Munger closing argument:** "The artisan mode concern dissolves when you stop thinking of GP-070 as the visibility source. The gap was never 'GP-070 isn't running.' The gap was 'eval results are ephemeral.' Fix that one thing and the MVP is real."

**Implementation note:** `eval_history.jsonl` persistence was shipped in this session (PHASE_E, `autoresearch_loop.py`). This was a prerequisite telemetry fix, not GP-102 implementation proper. The cron goal mechanism itself still needs a spec before implementation.

**Seam status after this turn:** Visibility architecture is now bounded. Remaining open question before `## Recommendation` can be written: Q1 (science vs machinery discriminator) — the decisive question that determines whether the cron goal produces useful output or noise.

### Turn 4 — Engine + Operator (2026-04-19 11:14:16 EST) — Q1 resolved via Deming's SPC + Kaizen historical grounding

Panel expanded with process-specific reviewers: Deming (SPC/control charts) and Ohno (Toyota/root cause analysis) alongside existing Munger/Dijkstra/Norvig/Karpathy seats.

**Q1 resolution:** The discriminator is not the magnitude of failure but the **variance of failure** across iterations. This maps to Deming's SPC framework:

- **Low failure variance** (same gate fails K+ times, similar residual, low latent motion) = special-cause variation = machinery is broken → trigger audit. This is Shewhart's "run" signal on a control chart.
- **High failure variance** (failures rotate across 3+ gates, high latent motion) = common-cause variation = science is hard → "all clear." Intervening here is Deming's cardinal sin of "tampering" — adjusting a stable process based on random variation makes it worse.

**Historical anchors:**
- Shewhart (1920s): control charts detect assignable causes, not random noise
- Deming (1950s): don't tamper with common-cause variation
- Ohno (1970s): 5 Whys traces zero-variance failures to structural roots
- Kaizen: targets systematic waste, not inherent difficulty

**Panel endorsement:** Unanimous. The variance discriminator is computable from `eval_history.jsonl` (now shipping), makes GP-102 safe to run unattended, and prevents false-positive audits on difficult substrates.

**Seam status:** Q1 resolved. `## Recommendation` written. Seam has converged — ready for spec per GP-053 sequencing.

### Turn 5 — Bounded Skeptic Review (2026-04-19 11:22:00 EST) — Spec review, REVISE → fixes applied

Spec drafted at `research_areas/private/specs/active/GP-102_reflexive_primitive_discovery_spec.md`. Bounded skeptic agent (isolated: spec + seam + primitives catalog only, no session history) reviewed against 12 overreach patterns.

**Two decisive defects found and fixed:**

1. **`recovery_primitives_fired` doesn't exist in telemetry.** The discriminator's gate 2 ("if not all recovery primitives have fired") was uncomputable — no telemetry artifact records which recovery mechanisms have activated. GP-087 writes seeds silently, not telemetry events. **Fix:** replaced with `recovery_exhausted` proxy: `families_exhausted == families_total AND stagnation_count > composition_stagnation_threshold`. Computable from existing `structural_memory.json` and `iteration_telemetry.jsonl`. Not perfect (it's a proxy, not a direct check), but honest about what's computable today.

2. **Committee silently imported all 6 process families including deferred ones.** The seam's MVP section explicitly limited launch to `persistent_stagnation` and `primitive_exhaustion`. The spec copied the full future-state family list without the MVP caveat. **Fix:** split families into MVP (2) and deferred (4) with explicit pointers to which visibility gap blocks each.

**Four bounded concerns acknowledged:**
- `eval_history.jsonl` wired but zero records accumulated yet (premature "CLOSED" label — acknowledged, data will accumulate as runs execute)
- Historical grounding (Deming/Shewhart) restates the same logic in period costume — doesn't add discriminating power beyond the math. Acknowledged.
- Git commit message friction signals are heuristic, not reliable. Fixed: file-change frequency is primary signal, commit messages are corroborating only.
- Line estimate revised from 200-300 to 400-500 (LLM call scaffolding in Component 3).

**Verdict: REVISE → MERGE after fixes.** Both decisive defects are resolved. Spec is ready for implementation.

### Turn 6 — Operator + Gemini Pro (2026-04-19 11:24:29 EST) — Invert + Compress on typified failure modes

Principal applied ZTARE Legs 1+2 to the spec itself: "invert the design and compress around typified failure modes."

**Compression gap identified:** Original Component 3 asked an LLM to "diagnose which layer is stuck" — but the diagnosis is already deterministic. If `recovery_exhausted == True`, it's `primitive_exhaustion` at the Component D / Grammar layer. Asking an LLM to "diagnose" a computable state wastes tokens and risks hallucinated diagnoses (e.g., blaming the prompt when the bottleneck is the grammar ceiling). This violates the Compress principle.

**Inverted design:** Split the LLM's role. Diagnosis is deterministic (Python). LLM is reserved for Inception only — the creative act of proposing which ZTARE leg to apply reflexively.

| Before (spec v1) | After (spec v2) |
|-------------------|------------------|
| Component 3: LLM diagnoses AND proposes | Component 3: Python classifies failure mode deterministically |
| — | Component 4: LLM invents the cure (inception only) |
| LLM risks hallucinating wrong layer | Diagnosis is math, not judgment |
| LLM does two tasks (diagnosis + invention) | LLM does one task (invention) with higher context budget |

**Spec revised.** Component 3 is now `classify_failure_mode` (pure Python, no LLM). Component 4 is now `inception_committee` (LLM invents, does not diagnose). Total components: 7 (gather, discriminate, classify, inception, propose_seam, artisan_git_scan, entry point).

**Extensibility benefit:** When deferred failure modes (gate_ceiling, persona_churn) become computable, adding them is a 3-line Python heuristic in Component 3 — no LLM prompt changes needed.

<!-- FINDINGS_DEBATE: Turn 6: Invert+Compress applied to spec. Diagnosis split from inception. Component 3 is now deterministic Python. LLM reserved for creative inception only. Spec v2 merged. -->

### Turn 7 — Operator + Expert Review (2026-04-19) — Self-Licking Ice Cream Cone Risk + Structural Preventatives

Operator applied Munger's inversion to the reflexive audit design: "What must be structurally true for GP-102 to successfully abandon science and become a permanent meta-auditor?"

**Four failure conditions identified (Chandlerian M-Form: HQ suffocating the Divisions):**

1. **Process Goodharting:** LLM committee finds it cheaper to hallucinate a plausible primitive than for Component D to find a mathematical tail correction. If both yield "Goal Completed," audit wins.
2. **Uncapped architectural complexity:** No parsimony gate on the orchestration layer itself.
3. **Decoupling from science metric:** Process fixes promoted on internal logic alone, not validated against scientific stagnation. Seam gets raised without proof the primitive reduces the stagnation signal.
4. **Principal fatigue:** Operator rubber-stamps n=0 seams because they are exhausting to read. The "Executive Signature" becomes an automated pass-through.

**Protection status (from bounded skeptic review of implementation):**

| Failure Mode | Status | Mechanism |
|---|---|---|
| 1. Process Goodharting | PARTIALLY PROTECTED | Inception prompt anchors LLM to deterministic diagnosis; meta-parsimony (one-in-one-out) constraint added to prompt — committee must identify what is superseded or justify complexity increase |
| 2. Uncapped complexity | PROTECTED | Discriminator has bounded threshold parameters; K and stagnation_threshold are CLI-tunable constants |
| 3. Science decoupling | PROTECTED (added) | Retroactive falsification gate added to every seam: target_sandbox field mandatory, principal must re-run that sandbox before raising |
| 4. Principal fatigue | PROTECTED | Hardware air-gap structural: seam is SENTINEL_DECISION: hold only; no auto-merge path exists in the code |

**Four structural preventatives implemented:**

**Preventative 1: Meta-Parsimony Constraint (One-In, One-Out)**
Added to inception committee prompt: LLM must identify an existing primitive that is superseded by its proposal, OR provide a mathematical justification for complexity increase. If neither is satisfied, it must return "NO_NEW_PRIMITIVE." This is enforced in the prompt template; the discriminator is not the LLM's to relax.

**Preventative 2: Hard Meta-Budget (20:1 science:audit token ratio)**
`run_reflexive_audit()` now accepts `science_token_budget` parameter. When provided, the inception committee (LLM call) only fires if `science_token_budget >= 20 × estimated_audit_tokens`. The General Office is literally starved of LLM resources unless the Divisions are producing science tokens. Default: ratio check skipped in artisan mode (science_token_budget=0).

**Preventative 3: Retroactive Falsification Gate**
Every generated seam now includes a mandatory "Retroactive Falsification Gate" section with `target_sandbox` (the project_id of the stagnated sandbox that motivated the proposal). Before the seam can be raised from "hold" to "active," the principal MUST re-run that exact sandbox with the proposed primitive in effect and record the result in Turn 2 of the Debate Log. If the sandbox does not break stagnation, the primitive is reverted as false-positive bureaucracy. No exceptions.

**Preventative 4: Hardware Air-Gap (already implemented)**
The GP-102 cron goal can only WRITE to `research_areas/private/seams/reflexive/`. It cannot merge into the primitives catalog, modify the OS layer, or update any config. The agent runtime has no write path to `reflexive_engineering_primitives.md`. Manual copy → commit by the principal is the only promotion path. This forces System 2 engagement and prevents rubber-stamp fatigue.

**Expert review findings (bounded skeptic, read-only agent, 2026-04-19):**

Integration risks addressed:
- **B2 (latent distance disambiguation):** `discriminate()` now checks `latent_distance_trend` when `n_iters_with_any_failure == 0`. If latent motion is active (|trend| > 0.05), returns SCIENCE_IS_HARD instead of MACHINERY_BROKEN.
- **B4 (_extract parser):** Verified case-insensitive (`.upper()` on both sides); not a real gap.
- **C1 (eval_history.jsonl):** Implementation uses `iteration_telemetry.jsonl` for gate failure history, not `eval_history.jsonl`. The agent reviewer confused spec language with code. Not a gap.

Remaining gap (not fixed — tracked):
- **B1 (recovery_exhausted proxy at 50% threshold):** The fallback path uses `families_exhausted >= families_total // 2` when `composition_primitive_count == 0`. This can fire false positives on projects where Component D simply hasn't run yet. Accepted for now — the stagnation_count >= threshold guard provides a second layer of protection.

**Seam status after Turn 7:** Implementation complete and hardened. The four structural preventatives are either implemented in code (P1, P2, P3) or structural by design (P4). Safe to run in skip-llm mode. First LLM-enabled run requires science_token_budget to be passed from the orchestrator for P2 to fire.

<!-- FINDINGS_DEBATE: Turn 7: Self-licking ice cream cone risk analyzed and mitigated. Four structural preventatives implemented. Retroactive falsification gate added to seam proposals. Meta-budget guard added to entry point. Hardware air-gap confirmed. -->

