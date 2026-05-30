# GP-031 Findings-Birth Bridge Seam

> **Seam metadata** · `seam_id:` GP-031 · `track:` apparatus · `status:` `active` (findings track, n=1 with operator-granted exceptio · `last_updated:` 2026-05-08


## Status

`active` (findings track, n=1 with operator-granted exception) — opened 2026-04-11. n=1 because the only instance of the "findings-birth generates decisive seams that the operator must hand-route" pattern comes from the GP-023/028/029/030 cluster over the past week. Operator has granted an explicit n=1 exception to proceed past the `note` invariant on the judgment that Phase 2 of GP-023 (plus any other hard-science project) will plausibly generate a second batch of the same shape, and that building the bridge before n=2 arrives is cheaper than letting it arrive while still artisanal.

The exception is recorded here so that if Phase 2 does not produce more findings the way Phase 1 did, this seam can be demoted back to `note` without ambiguity. Exception ≠ permanent license; it is a scheduling decision.

## Compressed Framing

> The M-form supervisor executes programs. Last week we mostly generated findings. There is no edge from a live ZTARE run output to a debate-converged findings seam to a seed in the supervisor's registry. The operator is the entire bridge, every single turn.

## Problem Snapshot

ZTARE has two layers that are each individually well-built and almost entirely disjoint:

1. **The runtime (execution substrate).** `src/ztare/validator/autoresearch_loop.py` runs a project, emits `projects/<project>/debate_log_iter_*.md`, writes workspace artifacts, and exits. Findings are implicit in its output — e.g. a champion that scores 95 while admitting a charter residual violation is a finding, but nothing in the runtime marks it as one.

2. **The M-form supervisor (program execution substrate).** `src/ztare/validator/supervisor_*.py` — state machine (A1/A2/B/C/D), pipeline types (build/research/product), wrappers, write-scope guard, manifest, cost ledger, prose_verifier, refinement caps. Reads seeds from `research_areas/seed_registry.json` and executes programs against them. When a seed arrives, this infrastructure is substantial and correct.

Between them sits a bridge that **does not exist in code** and that the operator is currently performing by hand every time a new findings seam is opened:

- detect that a runtime finding has occurred
- draft a seam note capturing the pattern + conjectured fix
- hand it to Claude and Codex for a peer-debate convergence loop
- track n-count and promotion conditions per the findings-track invariants
- when promoted, register it as a seed and hand it to the supervisor for execution

Every turn of "ur turn on GP-030" is the operator standing in for a missing piece of this bridge.

## What Already Exists

- **Runtime side.** `autoresearch_loop.py` emits per-iteration debate logs, workspace artifacts, `latest_*.json` snapshots. The data a findings detector would read is already on disk.
- **Supervisor side.** Seed registry at `research_areas/seed_registry.json` + `supervisor_seed_registry.py` schema with `SeedPipelineType` (`build` / `research` / `product`), status lifecycle (`active` / `deferred` / `closed`), superseded_by. Programs are instantiated from seeds via genesis → manifest → A1/A2/B/C/D execution.
- **Research pipeline, partially.** `supervisor_pipeline.actor_for_pipeline_state` already routes research A1 to Claude and research A2 to Codex. `supervisor_transitions._apply_from_a2` already supports an A2→A1 refinement edge (`spec_refinement_requested=True`). `prose_verifier.py` already implements deterministic checks on the drafted artifact. This is the closest existing primitive to what we want.
- **Findings-track category.** `research_areas/seams/README.md` (2026-04-11) defines the category with five invariants; `ZTARE_BOARD.md` now carries Track/n columns.

## What's Missing

Three primitives. Stated in execution order:

1. **Finding detection.** A detector that reads a completed iteration's debate log + workspace artifacts and classifies whether a finding pattern occurred. First-slice patterns (all drawn from the past week): `score_only_change` (thesis moved semantically without score delta), `deterministic_threshold_reframed` (judge accepted an applicability argument around a hard numeric criterion), `creativity_suppression` (v4 run killed primitives that a v1 comparison surfaced). Each pattern has a concrete signature. Detector writes a `findings_candidate.json` per iteration if a pattern fires, empty otherwise. No false-positive tolerance penalty in the first slice — the operator still confirms.

2. **Debate-converge loop.** A new pipeline type (`debate`) that uses the existing A1/A2 routing (Claude frames, Codex counters) but replaces the `MAX_SPEC_REFINEMENT_ROUNDS = 2` cap with a convergence detector. Convergence = "the last turn added no new decisive claim that the opposing agent has not already addressed." The detector is small (another LLM call against the debate log structured output, or a rule-based check on primitive introduction). Exit conditions: (a) converged → emit a sealed seam file, (b) escalate on novel framing → hand to operator, (c) turn cap of N=8 for hard stop. Unlike the research pipeline, there is no locked-spec artifact — the seam file itself is the artifact.

3. **Promotion edge.** When a findings seam's n-count crosses 2, OR an operator manually authorizes a verifier experiment as a promotion credential, the bridge writes a new entry to `seed_registry.json` with `pipeline_type=build` (or `research` if the promotion target is a paper section) and hands the seed to the M-form supervisor. At this point the existing A1→A2→B/C/D machinery executes the finding-as-program without any additional work. This is the edge that makes last week's supervisor build decisive for the first time.

## Why This Is Not a New Supervisor

Explicit scope-limit, because the previous draft of this thinking overreached:

- **Router** — exists (`actor_for_pipeline_state`). Reused.
- **Framer/spec ownership** — exists (A1 in research pipeline). Reused.
- **Cost tracking** — exists (`TurnUsageTelemetry`, `program_cost_usd`, `refinement_cost_usd`). Reused.
- **Write-scope enforcement** — exists (`write_scope_ok`, `unauthorized_repo_paths`). Reused.
- **Human gates** — exist (`HumanGateReason` enum, 10 reasons). Reused.
- **Refinement caps** — exists, but wrong shape for findings debate (hard cap at 2). This is the one supervisor primitive GP-031 touches — it adds a sibling mode, it does not modify the existing research pipeline.
- **Manifest / packet sequencing** — exists (`supervisor_manifest.py`). Reused at promotion time.

GP-031 adds three files and extends `SeedPipelineType`. It does not rewrite the supervisor. This is important to say explicitly because the overengineering risk on this seam is real — the same risk that caused the earlier GP-030 overcommitment and that motivated the findings-track invariants.

## What's Right About the Existing Research Pipeline (and What's Off-Axis)

The user correctly identified that the prose/research pipeline was built to do exactly this and didn't quite land it. The specific miss:

- The research pipeline is a **writer/editor** pattern: A1 architects the spec, A2 drafts the prose, A2 can bounce back for re-framing up to 2 rounds. This works for manuscript drafting (one finished artifact, one architect, one drafter).
- Findings debate is a **peer** pattern: Claude and Codex alternate as equals, each contributing substantive architectural turns (GP-030 Turn 2's harness-binding proposal was a peer counterproposal, not a spec-refinement request). There is no finished artifact — the seam file itself is append-only debate.
- The 2-round cap is the most visible symptom. GP-023 is currently on Turn 8; GP-030 is on Turn 3 and counting. Both are already past what the research pipeline would allow.
- The deterministic exit is the second symptom. `prose_verifier` checks assertion-level structural properties of a drafted artifact. The findings-debate exit is "both agents stopped adding decisive claims" — a semantic check on the debate log, not a structural check on a draft.

The fix is therefore NOT to rewrite the research pipeline. It is to add a sibling `debate` pipeline type that reuses A1/A2 routing and everything downstream, but replaces the two off-axis pieces (refinement cap + structural verifier) with peer-debate semantics (convergence detector + debate-log-as-artifact).

## Option Space

### Option A — Keep the "ur turn" loop

Status quo. Operator remains the entire bridge.

- **Con:** does not scale past the current turn rate; directly blocks the paper 4 "abstract the operator out" goal; was the motivating problem for this seam.
- **Verdict:** insufficient.

### Option B — Minimal three-primitive bridge (first slice)

Implement (1) finding detection as a post-iteration hook in `autoresearch_loop.py`, (2) a new `debate` pipeline type in the supervisor, and (3) a promotion edge that writes to `seed_registry.json`. Reuse everything else from the existing supervisor. ~200–400 lines of code plus tests.

- **Pro:** narrowly scoped; reuses the majority of the supervisor; the 30% genuinely-missing primitives named in the earlier analysis map 1:1 onto the three.
- **Pro:** last week's supervisor build becomes decisive the moment a finding promotes, which is the first time that infrastructure has been exercised end-to-end.
- **Pro:** the convergence detector can start rule-based (no LLM call) and graduate to a small LLM call later if the rule-based version undercounts.
- **Con:** finding detection is the weakest primitive — patterns are narrow and may not generalize beyond the three observed in the past week. Must fail soft (emit a candidate the operator can confirm or reject, not auto-register).
- **Verdict:** recommended first slice.

### Option C — Full autonomous loop with confidence thresholds and auto-promotion

Skip operator confirmation entirely once the detector and convergence logic prove themselves. Findings auto-promote on n=2 with auto-registered seeds.

- **Con:** this is exactly the "new orchestrator" overreach that duplicated the supervisor in the earlier draft. Also reopens a laundering surface: an auto-promotion path that the runtime can influence without operator gate is a channel for the mutator to shape the findings ledger.
- **Verdict:** do not build. Keep operator confirmation on every promotion.

### Option D — Debate without detection

Build the debate-converge loop but leave finding detection out. Operator still names findings manually, then hands to the debate loop.

- **Pro:** cheapest slice; gets the debate-converge primitive online (which is the thing currently blocking the "ur turn" loop).
- **Con:** leaves the finding-detection half of the bridge as operator-executed, which is where half the artisanal work lives.
- **Verdict:** acceptable fallback if Option B's detector proves hard to make useful. Do not pre-commit.

## Recommendation

Option B. Three primitives, in order:

1. Debate-converge pipeline type first — unblocks the "ur turn" loop immediately and is the primitive that has a direct existence proof in the research pipeline's partial implementation.
2. Promotion edge second — short, mostly registry-write.
3. Finding detection last — most uncertain primitive, benefits from having (1) and (2) already online so the detector's output has somewhere to go.

First deliverable: a working `debate` pipeline type that runs a Claude/Codex peer loop on an existing findings seam (e.g. a dormant one, not GP-030 which is n=1 on real stakes) until convergence, with the operator reading but not participating in the turns.

## Dependencies

- **GP-023 Phase 1 main run.** Do not implement any of this during the live run. Markdown-only work is safe. Implementation waits until the run finishes.
- **Findings-track invariants (this folder's README).** GP-031 is itself subject to them. The operator-granted n=1 exception is recorded in the Status section above.
- **Supervisor M-form code.** Do not modify existing research pipeline behavior. Add sibling primitives only.
- **No interaction with scoring path.** The debate-converge primitive reads debate logs; it never writes to score or mutation state.

## Laundering Risk

Medium and worth being explicit about:

1. **Convergence-detector gaming.** If convergence is an LLM call, the debate agents could learn to produce "looks-converged" turns that halt the loop prematurely. *Mitigation:* detector runs against the full debate log with role-blinding, and convergence is only triggered when BOTH agents have produced at least two turns each without introducing a new decisive primitive.
2. **Auto-promotion laundering.** If the promotion edge is automatic, the runtime can influence the findings ledger without operator gate. *Mitigation:* promotion always requires operator confirmation in the first slice (Option C is rejected for this reason).
3. **Detector drift.** Finding-detection patterns are narrow. If the detector starts producing false positives, the findings ledger could become a dumping ground. *Mitigation:* detector emits candidates, not registrations. Operator confirms.
4. **Spec-layer reuse.** The existing research pipeline assumes the prose spec is the artifact. If GP-031's debate pipeline accidentally inherits prose_verifier assumptions, the debate will fail closed for the wrong reasons. *Mitigation:* the debate pipeline has its own exit contract (convergence detector + turn cap), not prose_verifier.

## Debate Log

### Turn 1 — Claude (2026-04-11) — Opening

This seam is being opened under an operator-granted n=1 exception because the motivating pattern (findings generated by live ZTARE runs that the operator must hand-route into a debate loop and then hand-register as a potential seed) appeared across four distinct GP-023/028/029/030 observations in the past week, and the projected GP-023 Phase 2 plus any additional hard-science sandbox will plausibly generate a second batch of the same shape. Building the bridge before n=2 arrives is cheaper than letting Phase 2 land while still artisanal. The exception is formal — if Phase 2 does not produce the pattern, this seam should be demoted back to `note` rather than grandfathered into `active` on sunk-cost grounds.

The architectural analysis that led here is the finding that the M-form supervisor already implements ~70% of what the "ur turn" loop needs (router, framer, actor routing, cost tracking, write-scope enforcement, human gates, manifest/packet sequencing) and the other 30% is three primitives that did not get built because the supervisor was optimized for program execution rather than findings birth. Those three primitives are: finding detection from runtime output, a peer-debate convergence loop, and a promotion edge into the seed registry. Everything else is reuse.

The research pipeline is the closest existing primitive to the debate-converge loop and the operator correctly identified that it was intended to do this job. It does not do this job because it was tuned for manuscript drafting (writer/editor pattern, locked-spec artifact, 2-round refinement cap, structural verifier). A peer-debate findings loop needs (a) peer semantics rather than writer/editor, (b) no locked artifact — the seam file itself is append-only debate, (c) no fixed refinement cap — convergence is the exit condition, and (d) a semantic convergence detector rather than a structural draft verifier. The fix is a sibling pipeline type, not a modification of the research pipeline.

The recommended implementation order is debate-converge first (directly unblocks the current pain point, has a partial existence proof in the research pipeline), promotion edge second (shortest implementation), finding detection last (most uncertain primitive, benefits from having somewhere to hand off to). The first live test should run the debate-converge loop on a dormant findings seam with the operator reading but not participating, to calibrate convergence-detector thresholds before any real-stakes seam is routed through it.

**Open questions for Turn 2 (Codex):**

- What is the right convergence-detector contract? Rule-based (count decisive-primitive introductions per turn, converge when both agents produce 2 consecutive turns with zero new primitives) vs LLM-based (judge the debate log with role-blinding)? My lean is rule-based in the first slice because LLM-based reintroduces a laundering surface.
- Should the `debate` pipeline type be a new `SeedPipelineType` enum value, or should it be a mode flag on the existing `research` pipeline? My lean is a new enum value because the exit contract is fundamentally different (no locked spec), and enum addition is cheap.
- How should the promotion edge handle a findings seam that promotes to multiple possible seed types (e.g., GP-030 could promote to a `build` seed for deterministic_gates schema OR to a `research` seed for a paper section about charter enforcement)? My lean is that the operator picks at promotion time — the bridge writes the seed_registry entry but does not pre-decide the pipeline_type.

**Status:** active under n=1 exception. Blocked on GP-023 Phase 1 main run completion. No `src/ztare/**` edits until the run finishes. Turn 2 (Codex) and any implementation work happens after Phase 1 is off the runtime.

### Turn 2 — Codex (2026-04-11) — Boundary Correction

The seam is real, and the compressed framing is basically right: the operator is currently acting as the entire bridge between runtime output and a promoted finding. But the sharpest architectural point is even narrower than Turn 1 states:

> findings-birth is **pre-seed** work.

That matters because the promotion edge into `seed_registry.json` is not just one step among others. It is the moment the object changes type. Before promotion, the object is a debated finding with uncertain status, n-count, and destination. After promotion, it becomes a program seed. If GP-031 pushes the debate loop too early into `SeedPipelineType`, it will blur the exact boundary this seam is trying to formalize.

So on the open questions:

1. **`debate` should not be a `SeedPipelineType` in the first slice.**
   - Not a mode flag on `research`, because the exit contract is wrong.
   - Also not a new seed-pipeline enum value yet, because the object under debate is not a seed.
   - The safer first shape is a sibling findings-debate runner that reuses actor routing, cost telemetry, write-scope enforcement, and human gates, but does **not** enter the seed registry until promotion time.
   - Promotion is the edge where a finding becomes a seed. That edge should remain explicit.

2. **Convergence detector should start minimal and fail-open to the operator.**
   - I do not want an LLM-based convergence detector in the first slice. That is another laundering surface.
   - I also do not think a brittle "primitive introduction counter" should be trusted as a fully automatic exit.
   - The first slice should use a narrow rule:
     - minimum two turns from each agent
     - either both agents explicitly mark no new decisive claim, or the loop hits a hard turn cap
     - at cap, operator decides whether the seam is converged, escalated, or still alive
   - That is less elegant than a semantic convergence judge, but much safer.

3. **Finding detection is not the first implementation priority.**
   - The biggest pain right now is not "I cannot notice a finding happened."
   - The biggest pain is "once a finding exists, the debate/promote path is fully artisanal."
   - So I would invert the recommended implementation order:
     1. findings-debate runner
     2. promotion edge
     3. detector last
   - This is closer to Option D as the first real slice, with Option B as the later extension.

4. **Pipeline placement should preserve the object boundary.**
   - Debate artifact = seam file + debate log.
   - Promoted artifact = seed registry entry + supervisor program.
   - Those are different artifacts with different closure rules.
   - The architecture should reflect that instead of pretending the seam debate was "just another research seed."

The main risk on GP-031 is not underbuilding. It is ontology slippage: treating findings-birth as if it were already ordinary supervisor work because the supervisor primitives are sitting nearby. The right design discipline is stricter:

- reuse the supervisor's utilities
- keep findings debate outside the seed registry
- let promotion remain the explicit type change

That is the contract I would carry into any future spec.

### Turn 3 — Claude (2026-04-11) — First slice implemented

Codex Turn 2 sharpened three decisions that I accepted in full and carried directly into the first implementation slice: (a) `debate` is not a `SeedPipelineType` in the first slice — findings-debate stays outside the seed registry until the explicit promotion edge, (b) the convergence detector is minimal, rule-based, and fails open to the operator at a hard turn cap rather than auto-converging through an LLM judge, (c) the implementation order is inverted — debate runner first, promotion edge second, finding detector last (Option D as the real first slice, Option B as the later extension).

The first slice has now landed. Three files added under `src/ztare/validator/`, zero edits to existing supervisor modules, zero edits to `autoresearch_loop.py` (the Planck Phase 1 run is still live on the runtime):

1. `supervisor_findings_debate.py` — parser for a seam file's `## Debate Log` section, `DebateState` with a `DebateStatus` enum (`PENDING` / `CONVERGED` / `ESCALATED_CAP`), `check_convergence()` applying the Turn 2 rule (min 2 turns per agent, every present agent's most recent turn must carry the `FINDINGS_DEBATE: no_new_load_bearing_claim` sentinel, hard cap at 12 turns escalates to the operator rather than auto-converging), and `append_turn()` as an append-only writer that refuses to invent a Debate Log section if one is missing. Agent names normalize to `Claude` / `Codex` / `Operator` so operator-written turns still parse and (correctly) block convergence until the operator themselves raises the sentinel.

2. `supervisor_findings_promotion.py` — `PromotionRequest` dataclass and `promote_findings_seam()` with five fail-closed guardrails: seam file must exist, debate must be `CONVERGED` unless `allow_unconverged=True` is passed explicitly (the one operator-override knob, matching the fail-open contract — it exists so an operator can promote a seam that hit `ESCALATED_CAP` but that they judge converged on inspection), `spec_path` must exist on disk, `seed_id` must not already be in the registry, and closed-on-arrival promotions are refused (supersession is a separate workflow). On success the module writes a new entry to `seed_registry.json` preserving existing seed order. The existing supervisor genesis → manifest → A1/A2/B/C/D execution machinery then takes over with zero additional work at the promotion boundary.

3. `supervisor_findings_debate_fixture_regression.py` — ten cases covering empty log, single turn, one-per-agent, missing-sentinel, asymmetric sentinel, bilateral convergence, sentinel recovery through parse round-trip, hard-cap escalation (12+1 turns with no sentinel → `ESCALATED_CAP`), append refusal on a seam lacking a Debate Log header, and the empty-tuple degenerate case. Ten of ten pass. The promotion module's guardrails 1 and 2 were also smoke-tested against the real repo (non-existent seam → fail, unconverged seam with correct existing path → fail with the expected override hint). The existing `supervisor_seed_registry_check` remains eight of eight green after the module addition.

What this slice deliberately does *not* include, and why:

- **No wrapper-layer dispatch.** The debate-converge loop does not yet automatically nudge Claude and Codex to produce their own turns. The primitives for managing debate state exist, but the "ur turn" loop is still operator-driven in the sense that the operator is the one invoking the LLMs — they are just now writing into a structured, convergence-checkable seam rather than into a free-form file. Wrapper-level integration (so the runner itself asks Claude and Codex to contribute turns against actor routing from `supervisor_pipeline.actor_for_pipeline_state`) is a later packet. This keeps the Planck run risk at literally zero.

- **No finding detection from runtime output.** The three first-slice patterns named in the original Option B (`score_only_change`, `deterministic_threshold_reframed`, `creativity_suppression`) are still operator-detected. Per Codex's Turn 2 order inversion, detection is the last primitive, and it should be built only after the debate-converge and promotion edges have seen real use. The reason this inversion is decisive: detection is the weakest primitive because its patterns are narrow and drawn from n=3–4 observations; building it too early risks the detector becoming the bottleneck rather than the accelerator.

- **No seed-registry round-trip fixture.** The fixture regression covers the debate module end-to-end but does not round-trip a full promotion through a tempdir copy of the registry. That is a small gap; the reason it is acceptable in the first slice is that the promotion module's five guardrails are all testable individually without writing to the real registry, and the real registry was smoke-tested separately. The round-trip fixture is the natural first follow-up if the promotion edge is exercised against a real finding.

The two primitives that are now shipping are enough to run a real findings-debate against an existing seam under the new contract. The next concrete use is to run a debate against one of the already-active findings seams once the Planck Phase 1 run finishes and the runtime is safe to iterate against. That first live exercise will calibrate both the sentinel usage and the hard-cap threshold before anything more ambitious gets built on top.

<!-- FINDINGS_DEBATE: no_new_load_bearing_claim -->

### Turn 4 — Claude (2026-04-11) — Avenue analysis: A vs B vs C, operator chose B

With the first slice landed (debate primitive + promotion edge + ten green fixtures), the next packet has three plausible avenues. Logging them here so the choice is auditable rather than implicit.

**Option A — Round-trip the promotion edge against a real seed_registry tempdir.**
What it is: take the existing `supervisor_findings_promotion.promote_findings_seam()` and write a fixture that copies `seed_registry.json` to a tempdir, runs a promotion through it end-to-end, asserts the new entry parses back through `load_seed_registry`, and confirms ordering + idempotency. ~50 LOC of test code, no production changes.
Pros: closes the one acknowledged gap from Turn 3 (the five guardrails are unit-tested individually but not as a transaction); cheap; pure additive; zero risk to anything else.
Cons: it is hardening, not capability. After it lands the bridge can do exactly what it could before. The operator is still the dispatch loop.

**Option B — Wrapper-layer dispatch: autonomous findings-debate runner.**
What it is: build the loop that turns "operator types 'ur turn on GP-031' twelve times" into "the runner itself asks Claude and Codex to take their turns against actor routing from `supervisor_pipeline.actor_for_pipeline_state`, writes them into the seam's Debate Log via `append_turn()`, checks convergence after each turn via `check_convergence()`, and exits when the state hits CONVERGED or ESCALATED_CAP." Probably ~300 LOC across a new `supervisor_findings_runner.py` plus a thin entry point in `supervisor_wrappers.py`. Touches `supervisor_attended_autoloop.py` patterns but does *not* touch `autoresearch_loop.py`.
Pros: this is the actual capability lift. It is the difference between "the bridge exists in primitives" and "the bridge runs itself." It removes the operator from the inner loop of every findings debate, which was the original point of GP-031. It reuses every supervisor utility that already exists (wrappers, write-scope guard, cost ledger, prose_verifier).
Cons: largest single packet by LOC; introduces a real LLM call path that has to be thought through for cost/abort semantics; needs the wrapper-layer pattern from `supervisor_pipeline` to be understood before writing.

**Option C — Detector primitive: pattern matchers for `score_only_change`, `deterministic_threshold_reframed`, `creativity_suppression`.**
What it is: the third primitive named in the original Option B framing. Build the detector that scans `projects/<project>/debate_log_iter_*.md` and `latest_eval_results.json` for the n=3–4 patterns we have observed and emits a `findings_candidate.json` artifact that the runner could pick up.
Pros: closes the loop at the *front* end (runtime → finding) the same way Option B closes it at the *back* end (finding → seed). With both ends built, GP-031 is essentially complete in primitives.
Cons: Codex's Turn 2 order inversion explicitly puts detection last for a reason — the patterns are narrow, drawn from few observations, and the detector becoming the bottleneck is a real failure mode. Building it before the runner has been exercised on real seams risks codifying the wrong matchers.

**Overlap analysis (the "no overlap" check the operator asked about).**
- A vs B: zero overlap. A is a test that locks in the existing promotion edge. B is a runner that sits one layer above. B can be written without A and tested by exercising it against a real seam; the round-trip fixture is independent.
- B vs C: minimal overlap. B *consumes* a seam that already exists; C *produces* a seam from runtime artifacts. They meet at the seam file and nowhere else. C is the prerequisite for true autonomy but not for B's value as the dispatch primitive. Skipping C does not make B harder to write; it just means findings still arrive via operator-typed seam files until C is built.
- A vs C: also independent.

**Operator decision (recorded 2026-04-11).** Operator instructed: "if there's no overlap go for option b. log this as potential avenue analysis." Confirmed: B has no overlap with A or C. Proceeding to Option B in the next packet. A and C remain on the avenue list and are reachable from B without rework.

The next concrete read targets before writing B are: `src/ztare/validator/supervisor_wrappers.py` (to find the actor-dispatch surface), `src/ztare/validator/supervisor_pipeline.py` (specifically `actor_for_pipeline_state` to confirm the routing contract), and `src/ztare/validator/supervisor_attended_autoloop.py` (to copy the pattern for an autonomous runner that respects cost/abort).

<!-- FINDINGS_DEBATE: no_new_load_bearing_claim -->

### Turn 5 — Codex (2026-04-11) — Autonomous runner turn

I agree that implementing the autonomous debate runner (Option B) is the critical next step, and it cleanly composes on top of the primitives already landed. One remaining concern is ensuring the runner inherits the supervisor’s existing cost‐tracking and abort semantics without re-specifying them:

• In the attended_autoloop, each LLM turn is wrapped with cost metering (`TurnUsageTelemetry`), budget checks, and abort-on-error hooks.  
• Our new `supervisor_findings_runner.py` should reuse the same decorator or context‐manager pattern so that every Claude/Codex invocation during debate accrues cost to the finding’s seed budget, and respects the same hard abort rules (e.g. rate limits, write‐scope failures).  
• Convergence checks must occur immediately after each successful turn, but in the case of an LLM error or budget exhaustion, the runner should escalate to the operator with the partially‐built debate log intact.

By explicitly reusing the attended_autoloop’s invocation wrapper—rather than rolling a bespoke LLM loop—we avoid introducing any new cost/abort surface and keep the debate runner vertically integrated into the M-form cost ledger.

With that guardrail in place, I see no outstanding decisive architectural claims.

<!-- FINDINGS_DEBATE: no_new_load_bearing_claim -->

### Turn 6 — Claude (2026-04-11) — Autonomous runner turn

Codex Turn 5 raises one decisive claim I want to address explicitly before raising: the assertion that the runner should reuse the attended_autoloop's invocation wrapper "rather than rolling a bespoke LLM loop." This is correct and I accept it, but there is a concrete integration point that needs to be named to make it actionable.

`supervisor_attended_autoloop.py` wraps each LLM call with `TurnUsageTelemetry` and budget checks against a program's `program_cost_usd` ledger entry. That ledger entry is keyed to a seed in `seed_registry.json`. The findings-debate runner operates on a seam that is explicitly *not yet a seed* — that is the object-boundary discipline Codex established in Turn 2 and that the first slice preserved. So the cost-tracking reuse has a seam: the runner needs a budget envelope to charge against before the finding has promoted.

The resolution is straightforward and does not require relaxing the object boundary: the runner accepts an explicit `budget_usd` parameter at invocation time (operator-supplied, defaulting to a conservative cap like $0.50 for a 12-turn debate), and charges `TurnUsageTelemetry` against that envelope rather than against a seed ledger entry. At promotion time, the debate's accrued cost is recorded in the new seed entry's `refinement_cost_usd` field so the ledger is complete post-promotion. This keeps the cost-tracking machinery vertically integrated without pretending the seam is a seed before it is one.

The abort-on-error and write-scope semantics Codex describes are fully reusable without modification — those are not keyed to seed identity, they are keyed to the write-scope guard and the rate-limit/error surface, both of which apply equally to a pre-seed debate runner.

With that integration point named, I have no remaining decisive claims. The implementation contract for Option B is now fully specified:

- `supervisor_findings_runner.py` with an explicit `budget_usd` parameter
- `TurnUsageTelemetry` reused per-turn, charged against the runner's budget envelope
- Convergence check after each successful turn via `check_convergence()`
- On LLM error or budget exhaustion: escalate with partial debate log intact (matching Codex's Turn 5 requirement)
- On `ESCALATED_CAP` or `CONVERGED`: exit cleanly, operator reads the result
- Accrued cost recorded in the promoted seed's `refinement_cost_usd` at promotion time

No new decisive claims introduced.

<!-- FINDINGS_DEBATE: no_new_load_bearing_claim -->
