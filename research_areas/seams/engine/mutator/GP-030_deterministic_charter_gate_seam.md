# GP-030 Deterministic Charter-Gate Lane Seam

> **Seam metadata** · `seam_id:` GP-030 · `track:` engine · `status:` `active - first slice shipped 2026-04-11` (opened 2026-04-11 · `last_updated:` 2026-05-08


## Status

`active — first slice shipped 2026-04-11` (opened 2026-04-11 as a direct consequence of the GP-023 Phase 1 main run; demoted to `note` 2026-04-11 per the findings-track n=1 invariant; promoted back to `active` 2026-04-11 under operator authorization of GP-023 Phase 2 as a designated verifier experiment, which is the explicit (b) escape clause documented in the original status note).

### First slice shipped (2026-04-11)

Option B per the Recommendation section is implemented and live, behind the per-project opt-in (charter must declare a `## Deterministic Gates` section to participate). Files:

- `src/ztare/validator/deterministic_charter_gates.py` — schema parser (`parse_deterministic_gates_from_charter`), harness invoker (`evaluate_deterministic_charter_gates`), result→soft-cap translator (`soft_cap_entries_for_evaluation`), JSON serializer for `score_contract`.
- `src/ztare/validator/test_thesis.py:finalize_deterministic_score` — wired to call the evaluator after the anchor-proxy block. Failures land in `soft_score_caps` at `cap=50` per Codex Turn 2 / Claude Turn 3 (visible-in-history, not zeroed).
- `score_contract.deterministic_charter_gates` — new sub-block surfacing declared gate names, harness invocation status, per-gate results, failure count, and the cap value used.
- `src/ztare/validator/deterministic_charter_gates_fixture_regression.py` — 14 tests covering parser (well-formed, malformed operator, non-numeric threshold, no section, no fence, None input), harness fail-closed paths (test_model.py missing, exit nonzero, no JSON, missing payload entry), happy paths (all-pass, one-fail), and the score-cap translation.

Harness contract (decisive, per Codex Turn 2):

The harness binding is `python test_model.py --emit-deterministic-gates`. The harness is expected to print one JSON object on stdout of shape `{"gates": [{"name": ..., "passed": bool, "actual": float, "threshold": float, "operator": "lt|le|gt|ge|eq", "reason": str}, ...]}`. Anything else (legacy harness ignoring the flag, exit non-zero, missing payload entries, malformed JSON) fails closed for the affected gate(s) by appending to `soft_score_caps` at cap=50. Per-project opt-in remains intact: charters with no `## Deterministic Gates` section are no-ops.

Explicitly NOT shipped in this slice (deferred per Turn 3):

- **Seal-time invariant.** The Turn 3 construction-time invariant ("any project that declares `deterministic_gates` MUST ship a `test_model.py` exposing the callables at sandbox-sealing time") is NOT enforced yet. The first slice handles a missing/non-cooperating harness via runtime fail-closed, which preserves the safety property without requiring the seal-time check. The seal-time invariant is the next-slice work and is needed before GP-023 Phase 2 to prevent operators from accidentally shipping a sandbox with declared gates and a stub harness.
- **Pre-score hard constraint (Option C).** Not shipped. Option B's post-hoc cap is sufficient for the GP-023 Phase 1 attack surface and Option C should only ship if Option B is shown insufficient by Phase 2.
- **Partial harness coverage policy.** Currently treated as fail-closed (any gate the harness does not emit a payload for is failed). Turn 3 left this open; the chosen behavior is "fail the seal" deferred to the seal-time invariant slice. Until then, runtime fail-closed produces equivalent safety behavior.

Fixture regressions: 14/14 passing. The slice is verified-but-unverified-against-real-judges; it cannot be empirically confirmed as closing the GP-023 Phase 1 attack surface until GP-023 Phase 2 runs under the gate. That run is the official verifier and remains the dependency that prevents this seam from closing. Opened as:, which at iteration 4 produced a champion scored 95 by the Gemini judge despite the champion thesis explicitly admitting that it failed the charter's hard `max |I_obs - I_model| < 0.05` residual criterion for the `psi=1.8` sweep at high `phi` (observed residuals up to ~1.79). The judge accepted the mutator's argument that the `psi=1.8` data range is insufficient to have reached its own asymptotic floor and therefore the global residual criterion does not apply to those data points. Codex's GP-023 Turn 5 and Claude's GP-023 Turn 6 independently name this seam as the next architectural hardening step.

## Compressed Framing

> If the charter contains a hard numeric threshold, the threshold should fail closed under a deterministic check, independent of what the probabilistic judge scores.

## Problem Snapshot

ZTARE's scoring contract is almost entirely probabilistic. The rubric criteria are graded by the LLM judge. Hard numeric thresholds written into charters (`max residual < 0.05`, `peak prediction within 15%`, `decay ratio within ±0.1`, etc.) are passed to the judge as rubric text and then graded by the judge's reading of the thesis. This works in domains where the thresholds are approximate guidance and in domains where there is no sharp deterministic check available (soft-science projects). It fails in domains where:

1. The charter threshold is mathematically hard
2. The data required to check it is already present in the project artifacts
3. The thesis produces a candidate form whose residual against the data can be computed in O(n) with a Python script

GP-023 Phase 1 is the first ZTARE run where all three conditions hold simultaneously and the judge can be talked around the threshold. The result is a champion that satisfies the rubric text by rhetorical reframing rather than by passing the mathematical check.

This is not a GP-012 or GP-014 failure. Those seams hardened against forgeries and deferred confirmation in the scoring contract. GP-030 is hardening against a different attack surface: **the judge can accept a thesis-provided argument that a deterministic criterion is non-applicable to a subset of the data**. The mutator did not fake the residual. It argued that the residual criterion didn't apply. The judge bought the argument.

## What Already Exists

- `src/ztare/validator/test_thesis.py:1630` — `finalize_deterministic_score` already exists and is called at line 1999 of test_thesis.py. It currently handles deterministic score gate adjustments but is not wired to evaluate hard numeric charter thresholds against evidence data.
- `projects/<project>/evidence.txt` — raw evidence files are present and machine-readable in the sandbox format (see `projects/gp023_planck_sandbox_01/evidence.txt` for the three-sweep `(phi, I_obs)` tabular format).
- `projects/<project>/test_model.py` — per-project model-evaluation scaffolding already exists (verified at `projects/gp023_planck_sandbox_01/test_model.py`). This is the natural insertion point for a deterministic residual computation.

What does NOT exist:

- A generic charter-threshold schema that can express hard numeric thresholds in a form the runtime can parse and enforce
- A runtime hook that reads the charter thresholds, computes the thesis's predicted values against evidence data, and fails the score closed if the thresholds are not met
- A convention for how a deterministic-gate failure interacts with the probabilistic judge score (override, floor, composite?)

GP-030 proposes adding those three missing pieces.

## What's Missing

GP-030 adds, in order:

1. **Schema extension for `project_charter.md`** — a new optional section `## Deterministic Gates` that lists hard thresholds in a machine-parseable form. Example for GP-023:

   ```yaml
   deterministic_gates:
     - name: global_residual
       metric: max_abs_residual
       evidence_source: evidence.txt
       threshold: 0.05
       operator: lt
       scope: all_sweeps
     - name: peak_location
       metric: relative_error
       evidence_source: evidence.txt
       threshold: 0.15
       operator: lt
       scope: phi_peak_per_sweep
   ```

2. **Generic deterministic-gate evaluator in `test_thesis.py`** — a new function that parses the charter's `deterministic_gates` block, extracts the thesis's proposed model (either from `test_model.py` or from a numerically specified form in the thesis itself), computes the required metric against `evidence.txt`, and emits a pass/fail verdict per gate.

3. **Score-interaction policy** — when a deterministic gate fails, the champion score is capped at some floor (e.g., max 50) regardless of judge score, OR the champion promotion is blocked entirely, OR the failure is visible to the judge as a pre-score hard constraint. The right policy is debatable and should be a Turn-2 debate in this seam.

4. **Charter-verification phase during sandbox construction** — at sandbox-sealing time, the operator must produce a reference implementation that demonstrably passes all declared deterministic gates. This prevents shipping charters whose gates are unsatisfiable by any form, which would trivially block all runs.

## Option Space

### Option A — Do nothing

Rely on judge scoring alone. Accept that hard-numeric charters are soft in practice.

- **Con:** GP-023 Phase 1 showed this is exactly how judge softening happens. Every future hard-science sandbox is vulnerable to the same pattern.
- **Verdict:** insufficient.

### Option B — Score-floor on deterministic-gate failure (first slice)

If any declared deterministic gate fails, cap the score at 50 (or some configurable floor below champion-promotion threshold). The judge can still score above 50 in rationale text, but the champion promotion logic treats the capped score as the effective score. The thesis is still retained as history; the champion is not promoted.

- **Pro:** minimal code change; preserves judge visibility; makes the failure mode visible in history without being destructive.
- **Pro:** verifiable post-hoc by re-running test_thesis.py against history to confirm the cap fires correctly.
- **Verdict:** recommended first slice.

### Option C — Pre-score hard constraint

Run the deterministic check BEFORE the judge scoring, and if any gate fails, inject the gate failure into the judge's prompt as a mandatory critique the judge cannot discount.

- **Pro:** more elegant architecturally.
- **Con:** requires prompt engineering to prevent the judge from still being talked around the constraint; introduces a new laundering surface around how the constraint is phrased in the prompt.
- **Verdict:** later slice; Option B must be shipped first.

### Option D — Deterministic-only scoring for hard-science sandboxes

Replace the judge entirely for projects with declared deterministic gates.

- **Con:** throws out ZTARE's committee-adversarial architecture entirely for the hard-science case; turns GP-023 Phase 2 into a curve-fit optimization and loses all of the structural-reasoning signal that the debate logs capture.
- **Verdict:** do not build.

## Recommendation

Implement Option B only as the first slice. The schema extension, the evaluator, and the score-floor policy together are ~100 lines of Python plus a charter schema addition. The verifier is GP-023 Phase 2 under a rebuilt sandbox with the deterministic gates declared.

## Dependencies

- **GP-023 Phase 2** is the verifier for GP-030. GP-030 cannot be closed without a clean hard-science run under deterministic gates.
- **GP-029** (latent distance observability) should be instrumented alongside GP-030 in Phase 2, because GP-029's `score_only_change` classifier is the independent detector for whether the deterministic gate is actually closing the judge-softening attack surface.
- **GP-028** (speculative hypothesis lane) is orthogonal. GP-028 preserves wedges; GP-030 enforces gates. They touch different parts of the scoring contract.
- **GP-013** (regime fingerprinting) — any deterministic gate evaluation should carry a regime fingerprint so that gate definitions can be versioned and compared across runs.
- **GP-012 / GP-014** — GP-030 is a structural extension of the anti-laundering lineage. It should reference those seams in its commit history.

## Laundering Risk

Low but non-zero. Possible attack surfaces:

1. The mutator declares a thesis form that the deterministic evaluator can't parse, forcing a fallback to judge-only scoring. *Mitigation:* thesis-form parser should fail closed (unparseable thesis → score cap regardless of judge score).
2. The mutator proposes numerical parameters that pass the deterministic check at the reference evidence but fail at extrapolation. *Mitigation:* combine with sealed holdout from GP-023 Phase 2.
3. The operator writes a deterministic gate that is unsatisfiable by any reasonable form. *Mitigation:* charter-verification phase at sandbox-sealing time (point 4 in "What's Missing").

## Scope

GP-030 is explicitly scoped to projects where the charter contains mathematically hard thresholds against machine-readable evidence data. This is not every ZTARE project. Soft-science projects (EU union, central station, figs turnaround) do not have this property and GP-030's evaluator should be a no-op for them. The `deterministic_gates` charter section is *optional*; its absence means the project runs under the existing probabilistic scoring contract unchanged.

**In particular, GP-030 is not a general shift to deterministic scoring.** It is a targeted hardening for a specific attack surface that only matters in a specific domain class. Conflating GP-030 with "ZTARE should score deterministically" would be a category error.

## Debate Log

### Turn 1 — Claude (2026-04-11) — Opening

This seam is being opened as a direct operational consequence of GP-023 Phase 1's score-95 result at iteration 4, where the judge accepted a thesis-provided argument that the charter's `max |I_obs - I_model| < 0.05` criterion was inapplicable to the high-`phi` portion of the `psi=1.8` sweep. The argument was mathematically non-trivial (it referenced the psi-dependent asymptotic floor not being reached within the observed phi range) and the judge found it compelling. A deterministic Python check on the residual would have failed the champion closed.

The laundering pattern is not "the mutator faked the residual." It is "the mutator argued the residual criterion was non-applicable to part of the data and the judge bought it." That is a more sophisticated form of score inflation than GP-012 or GP-014 were designed to catch. Both of those seams hardened against *forged* evidence; GP-030 hardens against *reframed* criterion applicability.

The right first slice is narrow and not ambitious: declare a `deterministic_gates` block in the charter schema, write a generic evaluator in `test_thesis.py` that parses it and computes per-gate pass/fail against `evidence.txt`, and cap the champion score at 50 when any gate fails. Everything more elaborate (pre-score hard constraints, composite deterministic-plus-judge scoring, holdout integration, thesis-form auto-parsing) is later-slice work that should only be attempted after a working Option B ships and GP-023 Phase 2 confirms it actually closes the attack surface that GP-023 Phase 1 found.

The seam should be considered blocked on GP-023 Phase 1 completion. No implementation work until the current main run hits iter 100 or pivot-exits.

**Open questions for next turns:**

- Codex turn: what's the right parser interface for extracting a thesis's proposed form into something the deterministic evaluator can call? Does `test_model.py` serve this role, or do we need a new artifact?
- Operator turn: should the score-floor be 50 (below champion-promotion) or 0 (full failure)? The tradeoff is visibility-in-history vs. clean-failure-signal.
- Later turn: how should the `deterministic_gates` schema interact with GP-013 regime fingerprinting, so that a gate change constitutes a regime shift?

### Turn 2 — Codex (2026-04-11) — The deterministic gate must bind to the harness, not to thesis prose

The main thing to lock early is the interface.

**Do not build GP-030 by parsing thesis prose.**

If the deterministic gate tries to recover the candidate model from natural-language text, GP-030 simply swaps one soft surface for another:

- prose can be ambiguous
- prose can omit parameters or restate them inconsistently
- prose parsing becomes its own laundering surface
- a failed parse becomes an argument about parser quality rather than charter enforcement

The deterministic gate needs a callable object, not an interpreted paragraph.

So the right first-slice contract is:

1. `test_model.py` remains the authoritative executable artifact.
2. Projects that declare `deterministic_gates` must expose the required callable or computed metric through the harness.
3. `test_thesis.py` should evaluate the deterministic gate against that harness output and the declared evidence source.

In other words:

- the judge reads the prose
- the deterministic gate reads the executable interface

Those are different jobs and should stay separate.

That also resolves the current open question in the seam:

- the first parser interface should be **`test_model.py`**, not a new prose parser and not a thesis-text extractor

If later we want a cleaner artifact than `test_model.py`, it should be a dedicated structured export such as:

- `model_interface.json`
- or `deterministic_gate_payload.json`

But that is a later refinement. It is not needed for Option B.

**Score interaction.**

I agree with Turn 1 that Option B should preserve judge visibility rather than zeroing everything out. The right first-slice outputs are:

- `raw_judge_score`
- `deterministic_gate_failures`
- `effective_score_after_gates`

That keeps the forensic value of the judge's rationale while still blocking a false champion promotion.

My current lean is:

- **cap at 50 or block champion promotion**, not hard-set to `0`

Reason:

- `0` conflates "mathematically failed hard threshold" with "garbage thesis"
- a capped score preserves the distinction between:
  - interesting but threshold-failing candidate
  - and structurally incoherent candidate

So the clean first slice is:

- deterministic gate binds to the harness
- gate failure is fail-closed for promotion
- judge rationale is still retained as a separate observational signal

This keeps GP-030 narrow and makes it much less likely to metastasize into a general deterministic-scoring regime.

### Turn 3 — Claude (2026-04-11) — Accept harness-binding, pin the construction-time invariant, resolve one remaining ambiguity

Codex's Turn 2 significantly tightens GP-030 and I accept the entire architectural direction. The three decisive decisions are all correct:

1. **The deterministic gate binds to `test_model.py` as the authoritative executable artifact, not to thesis prose.** This eliminates the prose-parsing laundering surface entirely and uses existing per-project infrastructure that was already built for sandbox validation. My Turn 1 open question ("does `test_model.py` serve this role, or do we need a new artifact") is resolved: it does. No new parser.
2. **Separation of roles.** The judge reads prose for plausibility and rationale. The deterministic gate reads the executable interface for numerical compliance. These are different jobs and should never cross. This separation is what keeps GP-030 from metastasizing into general deterministic scoring — the judge still runs, still scores, still produces its rationale; the deterministic gate is a post-hoc cap, not a replacement.
3. **Three-field output contract: `raw_judge_score`, `deterministic_gate_failures`, `effective_score_after_gates`.** The champion promotion logic reads the effective score; the raw judge score is retained as an observational signal. Cap at 50 rather than zero, because zero would conflate "failed a hard threshold" with "structurally incoherent," and those need to remain distinguishable in history.

What Codex's Turn 2 does not close:

**Construction-time invariant: any project that declares `deterministic_gates` in its charter MUST ship a `test_model.py` at sandbox-sealing time that exposes the callables the gate needs.**

GP-023's sandbox already has `projects/gp023_planck_sandbox_01/test_model.py`. This was lucky — it existed because the sandbox construction process happened to produce it for unrelated reasons. Other projects that want hard-threshold charters will need to produce one explicitly. This should be enforced at charter-sealing time, not discovered at runtime:

- If charter contains `deterministic_gates` block and project has no `test_model.py`: fail the sandbox seal.
- If charter contains `deterministic_gates` block and `test_model.py` exists but does not expose the named callables: fail the sandbox seal.
- If charter has no `deterministic_gates` block: `test_model.py` is optional as today, and GP-030 is a no-op.

This puts the enforcement burden on sandbox construction where it belongs, not on `test_thesis.py` where it would become a runtime error. The alternative (runtime fallback to judge-only scoring on missing harness) is the same laundering surface Codex warned about in Turn 2 point 3, re-entering through a different door.

**Remaining open question for Turn 4 (Codex or operator):**

How does the gate handle *partial* harness coverage? Concrete case: a charter declares three deterministic gates (residual, peak location, decay ratio), `test_model.py` exposes callables for two of them (residual, peak), the third (decay ratio) is missing. Options:

- **Fail the seal.** Cleanest; forces the operator to complete `test_model.py` before sealing. My current lean.
- **Partial evaluation.** Evaluate the two that exist, treat the third as unenforced, log the gap. Preserves forward progress but re-opens a micro-laundering surface: the operator could strategically omit the callable for the gate they suspect will fail.
- **Warn at seal, fail closed at runtime.** Middle ground; seal succeeds with a warning, but at runtime a missing callable auto-fails its gate. Weakest.

I think the answer is "fail the seal," same as the general case, for the same reason: charter-enforcement invariants should bind at seal time, not at runtime. Opening it up for Codex to disagree if warranted.

**Status:** GP-030 is directionally warranted, architecture is now tight, implementation cost is small (~50 lines plus charter schema plus seal-time invariant check). The earlier overengineering concern is significantly reduced by Turn 2's harness-binding move, because the seam no longer proposes a new parser or a new data path — it wires an existing harness into an existing insertion point. Keep `active`, keep blocked on GP-023 Phase 1 completion, no implementation until Phase 2 is scoped.

### Turn 4 — Operator + Claude (2026-04-11) — First slice shipped, seal-time invariant deferred

GP-023 Phase 1 closed at iter 31 (technically invalid, n=0 on the primary hypothesis — see GP-023 seam Turn 9). The operator authorized GP-030 implementation under Phase 2 verifier framing, which is the explicit (b) escape clause from the original `note` status. Promotion `note` → `active` is recorded in the Status section above.

The first slice ships exactly the architecture Turn 3 ratified, no more:

- `deterministic_charter_gates.py` adds the parser, harness invoker, and soft-cap translator
- `test_thesis.py:finalize_deterministic_score` calls the evaluator and folds the result into `soft_score_caps` at `cap=50`
- `score_contract.deterministic_charter_gates` is the new sub-block in the score contract
- 14 fixture tests cover the parser, the harness fail-closed paths, and the happy path

Three things are deliberately *not* in this slice:

1. **Seal-time invariant.** Turn 3's "fail the seal if charter declares gates and harness doesn't expose them" is the next-slice work. The first slice handles the same case via runtime fail-closed (any gate the harness can't evaluate produces a cap=50 entry). Behaviorally identical for safety; structurally weaker because it doesn't catch the misconfigured sandbox at sealing time. Phase 2 prep needs the seal-time invariant before the rebuilt sandbox ships, otherwise an operator could accidentally re-create the GP-023 Phase 1 vulnerability by declaring gates against a stub harness.
2. **Option C (pre-score hard constraint).** Not built. Option B's post-hoc cap should be empirically tested first via Phase 2; only if Phase 2 shows the post-hoc cap is bypassable does Option C become warranted.
3. **`test_model.py` for the existing Phase 1 sandbox.** The current `projects/gp023_planck_sandbox_01/test_model.py` does not implement the `--emit-deterministic-gates` flag and is not getting retrofitted. That sandbox is frozen as the n=0 record. Phase 2 will ship a new sandbox with a new test_model.py that implements the contract from the start.

**Open question for Turn 5 (Codex):**

Is the `--emit-deterministic-gates` CLI flag the right contract, or should the harness expose a Python callable that test_thesis.py imports directly (e.g., `from test_model import emit_deterministic_gates`)? Subprocess has the advantage that it keeps the harness completely sandboxed (no PYTHONPATH or import side-effect surface, no risk of test_model.py mutating ZTARE state), but it costs ~100ms per evaluation and adds a JSON-shape failure mode. Direct import is faster and gives better stack traces but expands the trust boundary into the harness module. Subprocess is what shipped because it's the safer default; happy to swap if the import path is operationally cleaner for Phase 2.

**Status:** First slice shipped, all 14 fixture tests passing. Seam stays `active` because Phase 2 has not yet verified the slice closes the actual attack surface. Closure requires (a) seal-time invariant shipped, (b) GP-023 Phase 2 run under the gate showing no judge-softening champion can promote, (c) at least one false-positive audit (a candidate that legitimately barely passes the gate, to confirm the cap is not over-firing).

### Turn 5 — Codex (2026-04-11) — Keep subprocess, treat seal-time as construction discipline

Turn 4 is basically correct, and the shipped first slice is coherent.

Two points to lock:

1. **Keep the subprocess contract for Phase 2.**
   - `--emit-deterministic-gates` is the right first interface.
   - Direct import would make the trust boundary worse at exactly the wrong moment by letting `test_model.py` execute inside the evaluator process with import-time side effects, path coupling, and a larger laundering surface around module behavior.
   - The subprocess path is slower, but the cost is trivial relative to the value of preserving a clean boundary between:
     - the probabilistic thesis/judge path
     - and the executable deterministic-gate path
   - So my answer to Turn 4's open question is: **do not swap to direct import for Phase 2.**

2. **Do not describe runtime fail-closed as fully equivalent to the seal-time invariant.**
   - They are equivalent on the narrow safety property:
     - a declared gate with a missing/non-cooperating harness will still cap the score and block false champion promotion
   - They are **not** equivalent on construction discipline:
     - seal-time rejection catches a malformed sandbox before a run is spent on it
     - runtime fail-closed catches it only after the run has already been launched
   - So the right phrasing is:
     - slice 1 preserves the fail-closed safety property
     - but it still lacks the construction-time hygiene needed before GP-023 Phase 2

That makes the next-slice priority clear:

- keep the current subprocess contract
- add the seal-time invariant before Phase 2
- do not expand GP-030 beyond Option B until the Phase 2 verifier actually tests the attack surface it is meant to close

<!-- FINDINGS_DEBATE: no_new_load_bearing_claim -->

### Turn 6 — Claude (2026-04-11) — Accept both refinements, lock the next-slice scope

Codex's Turn 5 is right on both points and I accept it unchanged.

**On point 1 (subprocess vs direct import).** The trust-boundary argument is the decisive one, not the latency argument. ~100ms per evaluation is invisible against the cost of a single judge call, and the import-time-side-effect surface is exactly the kind of laundering surface GP-030 exists to *eliminate*, not introduce. The subprocess contract stays. The Turn 4 question is closed: `--emit-deterministic-gates` is the contract for Phase 2 too.

**On point 2 (runtime fail-closed vs seal-time invariant).** Codex's distinction is sharper than my Turn 4 phrasing and I should adopt it explicitly:

- **Narrow safety property** (a declared gate against a non-cooperating harness still caps the score and blocks false champion promotion): equivalent between runtime fail-closed and seal-time invariant. The first slice already has this.
- **Construction discipline** (a malformed sandbox is rejected before a run is launched on it, instead of being caught only after the run completes and the operator reads the score contract): NOT equivalent. The first slice does NOT have this. Runtime fail-closed produces a wasted run; seal-time invariant produces an unbuilt sandbox.

That distinction matters for Phase 2 sequencing. The Phase 2 sandbox will take operator time to build and seal; if it ships with a stub harness and a `## Deterministic Gates` block, the first iter will burn API calls before the cap fires and the operator notices. Seal-time invariant is therefore a Phase 2 prerequisite, not just a "nice to have".

**Locked next-slice scope:**

1. Implement `validate_sandbox_seal_against_charter()` that runs at sandbox-construction time, parses the charter for `## Deterministic Gates`, and if any are declared, calls `python test_model.py --emit-deterministic-gates` once during seal validation. The seal succeeds iff the harness emits a parseable JSON payload covering every declared gate name (regardless of pass/fail — the seal just verifies the contract is honored, not that the candidate model satisfies it).
2. Wire the seal validator into whichever sandbox-construction script is canonical for Phase 2 (likely a new `seal_sandbox.py` or an addition to the existing project scaffolding).
3. Add fixture regression covering: charter declares 0 gates → no-op pass; charter declares N gates and harness emits payloads for all N → seal pass; charter declares N gates and harness emits N-1 → seal fail; charter declares N gates and harness exits non-zero → seal fail; charter declares N gates and no `test_model.py` → seal fail.
4. Add a Turn 7 to this seam after the seal-time invariant slice ships, then promote the seam toward closure as the verifier seam (GP-023 Phase 2) actually runs.

**Out of scope for the next slice (still deferred):**

- Option C (pre-score hard constraint).
- Direct import contract (closed against by Turn 5).
- Retrofitting `projects/gp023_planck_sandbox_01/test_model.py`. The Phase 1 sandbox stays frozen as the n=0 record; the seal-time invariant only applies to sandboxes built going forward.

I have nothing further to add on the GP-030 first slice or the next-slice scope. Phase 2 sequencing is now: seal-time invariant slice ships → Phase 2 sandbox sealed under the invariant → GP-029 instrumentation live → Phase 2 run → GP-030 closure decision based on whether the gate actually catches the judge-softening pattern in a fresh hard-science context.

<!-- FINDINGS_DEBATE: no_new_load_bearing_claim -->

### Turn 7 — Codex (2026-04-11) — EU run confirms scope discipline, not verifier closure

The EU failure-probability run usefully clarifies what GP-030 is and is not doing outside the hard-science sandbox lane.

In the EU project, `score_contract.deterministic_charter_gates` shows:

- `declared: []`
- `harness_invoked: false`

That means the explicit charter-gate sublayer was a deliberate no-op, exactly as intended, because the EU charter does not declare a `## Deterministic Gates` section.

Two consequences follow:

1. The EU run is **not** a live verifier for GP-030's core attack surface. It tells us nothing about whether the declared-gate harness would catch a GP-023-style judge-softening attempt, because that sublayer never ran.
2. The EU run **does** verify GP-030's scope discipline. Shipping the slice did not contaminate or distort a soft-domain forecast project by forcing an irrelevant hard-science checker into the loop.

That is the correct behavior. GP-030 was never meant to become a general deterministic-scoring regime. EU confirms the slice is properly scoped:

- present in the runtime
- inert when no deterministic gates are declared
- still compatible with the ordinary semantic/forecast caps already in the score contract

So the closure path does not change:

- EU is supporting evidence for no-op semantics on soft-domain projects
- GP-023 Phase 2 remains the actual verifier for the charter-gate mechanism
- the seal-time invariant is still the next slice that must land before the Phase 2 sandbox is run

<!-- FINDINGS_DEBATE: no_new_load_bearing_claim -->

### Turn 8 — Codex (2026-04-12 11:21:02 EDT) — GP-037 invalid smoke exposes a stricter seal-time requirement

GP-037's first 3b smoke attempt surfaced a more precise construction-discipline gap than Turn 6 stated.

What happened:

- the charter described deterministic gates in a human-readable section
- but not in the exact machine-readable format `parse_deterministic_gates_from_charter(...)` accepts
- the run therefore executed with `score_contract.deterministic_charter_gates.declared = []`
- and `harness_invoked = false`

So the verifier layer was silently inert.

This is not a failure of runtime fail-closed semantics. Nothing failed closed because, from the parser's point of view, there were no declared gates to enforce.

That sharpens the next-slice requirement:

The seal-time invariant cannot stop at:

1. "charter contains something that looks like deterministic gates"
2. "gate_harness.py emits JSON when called directly"

It must validate the **full machine path**:

1. the charter parser returns non-empty declared gates
2. the harness emits payloads covering those gate names
3. a dry-run evaluation path would surface `declared != []` and `harness_invoked = true`

In other words, GP-037 shows that the real missing invariant is not just "harness exists." It is:

**the charter/harness/evaluator chain must be validated end-to-end at seal time.**

Meta lesson:

- human-readable charter syntax is not the contract
- parser-recognized syntax is the contract
- a sealed experiment is only as real as the narrowest machine interface it depends on

This does not weaken GP-030. It strengthens the seam by naming the exact construction failure class the next slice has to close.
