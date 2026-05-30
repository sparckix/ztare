---
id: GP-157
status: active
summary: v5.0 Cage Orchestrator design + panel debate transcripts
---

# GP-157 — Cage Orchestrator (Substrate-Agnostic Gate Dispatch)

> **Seam metadata** · `seam_id:` GP-157 · `track:` apparatus · `status:` SEAM OPEN - primary v5.0 architectural objective · `last_updated:` 2026-05-09


**Status:** SEAM OPEN — primary v5.0 architectural objective
**Created:** 2026-04-25 (post-audit; gp154/gp155/gp156 today exposed apparatus debt)
**Owner:** Claude (manager) — to be designed jointly before implementation
**Visibility:** private (architectural IP; reveal at v5.0 ship)

## Problem statement

`autoresearch_loop.py` is a monolithic God Object that uses **rubric-as-config**: each gate requires a rubric flag (`enable_X: true`) AND a hardcoded if-block in the loop. Result:

- **13 specialized gates SHIPPED but NOT WIRED** as of 2026-04-25 (audit confirmed):
  wasserstein_persistence (GP-143), ansatz_survivor (GP-144 G3),
  proof_surveyability (GP-144 G4), translation_diff (GP-144 G5),
  continuum_limit, coordinate_invariance, ensemble_ambiguity,
  prompt_leak_audit, pslq_falsity_audit, semantic_gate_stabilization,
  asymptotic_claim_discipline, bridge_scope_contract, domain_match_gate.
- These have smoke tests + fixture regressions, but nothing in production calls them.
- They were built for substrate classes (chaos / time-series / Lean-formalizable / proof-target) we haven't run since gp146.
- Across today's gp154 + gp155 + gp156 runs (~9+ live iters), ZERO of these fired.
- The mutator's silent-failure on Proposal 3 (~$10 of misclassified iters today) is the same disease at smaller scale: rubric flag absence → silent dormancy → no diagnostic.

## Diagnostic from today

Each gate's wiring takes:
1. A rubric flag (per-project, must be remembered)
2. A conditional if-block in autoresearch_loop.py (single point of forgetting)
3. A documentation update (rarely synced)
4. Per-project rubric edits (fan-out scaling-law)

Net: adding a gate costs ~5 places to update. Each new substrate class costs ~13 rubric flags to flip. **The architecture punishes adding apparatus capability.**

## Decision: Cage Orchestrator (substrate-agnostic dispatch)

Replace rubric-routed if-blocks with a Just-In-Time dispatcher that:
1. Inspects the SHAPE of the mutator's submission + substrate state
2. Queries every gate's `can_handle(submission, substrate)` predicate
3. Builds a DAG of qualified gates with declared dependencies
4. Executes the DAG; reports per-gate engagement + outcome
5. Returns control to the loop with merged score contract

The rubric becomes what it should always have been: **scoring instructions for the LLM judge**, not configuration for the Python compiler.

## Universal Gate Contract (v5.0)

Every gate in `src/ztare/gates/` must expose:

```python
class Gate(Protocol):
    name: str
    substrate_class: tuple[str, ...]   # which substrate shapes this targets

    def can_handle(self, ctx: GateContext) -> tuple[bool, str]:
        """Predicate: returns (engage, reason).
        ctx provides: submission_kind, submission_text, python_code,
                      features_module, fit_decl, evidence_text,
                      substrate_class_inferred, project_dir.
        """

    def run(self, ctx: GateContext) -> GateResult:
        """Executes the gate. Returns GateResult with passed, score_delta,
        diagnostic, and per-gate JSON payload."""

    depends_on: tuple[str, ...] = ()   # other gate names that must precede
```

Substrate class taxonomy (initial; extend as we add):
- `"1d_curve"`               — paired (x, y) data, ≥2 points (Framer / fit_primitive)
- `"feature_dict"`           — features.py + I_model(features) (fit_primitive_features)
- `"closed_form_constant"`   — symbolic Lean target (gp146)
- `"time_series_chaotic"`    — Lyapunov / Wasserstein / fractional-operator (gp143-144)
- `"proof_target"`           — Lean-formalizable claim (G3 / G4 / G5)
- `"meta_audit"`             — execution-hostile review of shipped code (gp152/153/156)
- `"feature_dict_categorical"` — categorical-conditional dispatch (gp154 mixed)

Each gate declares the substrate classes it targets; orchestrator filters by intersection with inferred class.

## Substrate inference

The orchestrator detects substrate class FROM ARTIFACTS, not from rubric:
1. `features.py` exists in PROJECT_DIR + has FEATURES dict → `feature_dict` (or `feature_dict_categorical` if any field is str)
2. `evidence.txt` parses as paired numeric → `1d_curve`
3. `test_model.py` declares only a closed-form constant target → `closed_form_constant`
4. `evidence.txt` describes a time series with ≥80 points → `time_series_chaotic`
5. Project name + charter mentions Lean / proof → `proof_target`
6. Charter says "audit / red-team" → `meta_audit`

Inference is fail-closed: if no class matches, emit a warning but run `meta_audit` defaults (philosophy/score-only gates).

## DAG execution

Gates declare dependencies; orchestrator topologically sorts. Examples:
- `falsifiability_gate` depends on `circularity_gate` (cycle in DAG invalidates falsifier)
- `translation_diff` depends on `proof_surveyability` (need surveyable target before diff matters)
- `wasserstein_persistence` depends on `lyapunov` (chaos must be confirmed before persistence test)

Orchestrator emits `workspace/cage_dispatch_iter_NNN.json` per iter:
```json
{
  "iter": 7,
  "substrate_class_inferred": "feature_dict_categorical",
  "gates_total": 27,
  "gates_eligible": 12,
  "gates_engaged": 8,
  "gates_dormant_with_reason": [
    {"name": "wasserstein_persistence", "reason": "substrate_class != time_series_chaotic"},
    {"name": "ansatz_survivor", "reason": "no proof_target declared"},
    ...
  ],
  "execution_order": ["circularity", "falsifiability", "fit_primitive_features", ...],
  "outcomes": {...}
}
```

This file makes the apparatus self-describing: an operator can grep `cage_dispatch` to see exactly what fired and why each dormant gate didn't.

## Migration plan

Don't migrate all 27 gates at once. Sequence:

**Phase 1 (v5.0 alpha — write infra):**
- Define `Gate` protocol + `GateContext` dataclass + `CageOrchestrator` class
- Write substrate-class inference helpers
- Build `make gates` audit command (LANDED 2026-04-25; this seam motivates it)
- Write fixture test: substrate fixture × gate matrix → expected engagement

**Phase 2 (v5.0 beta — migrate one substrate class):**
- Migrate ALL gates targeting `feature_dict` substrate to the protocol
- Replace autoresearch_loop's hardcoded if-blocks for that class with `cage.dispatch(ctx)`
- Validate engagement matches pre-migration via fixture parity test

**Phase 3 (v5.0 RC — migrate remaining):**
- Migrate 1d_curve, time_series_chaotic, proof_target, meta_audit gates
- Retire dead gates that no substrate class targets (formal retirement, not deletion)
- Remove rubric flags that are now redundant; keep only philosophy flags
  (require_cross_family, holdout_hard_gate, etc.)

**Phase 4 (v5.0 release):**
- Document migration in `docs/concepts/architecture.md`
- Update `docs/internal/architectural_maps/autoresearch_loop_architectural_map.md` regions
- Anti-pattern catalog entry: "rubric-as-config" with retired-2026-MM-DD tag

## Anti-patterns to forbid

- **Rubric-as-config (RH-18, NEW)**: any gate gated by `enable_X: true` rubric flag.
  Once Cage ships, rubric flags for gate engagement are anti-pattern.
  Substrate-class targeting via `can_handle` replaces them.
- **Silent dormancy**: a gate that does nothing if no substrate matches — must
  EXPLICITLY log "dormant: <reason>" so audits surface the gap.
- **Hardcoded substrate inference**: substrate class must be derived from
  artifacts, not from project name or rubric metadata. (Inference helpers
  may use rubric metadata as TIE-BREAKER only.)

## What this seam does NOT do (out of scope)

- Does NOT change the rubric's role as scoring instructions for the LLM judge
- Does NOT rewrite the LLM mutator prompt assembly
- Does NOT touch the existing fit_primitive / fit_primitive_features (they become
  gates under the protocol; their internal logic is preserved)
- Does NOT auto-discover new substrate classes — taxonomy is hand-curated
- Does NOT bypass the existing rubric_preflight gates (those are CLI-time, not
  iter-time)

## Risks (for future ZTARE-on-ZTARE review)

R1: **`can_handle` predicates can lie or disagree.** Two gates may both claim to
handle a substrate when only one should. Mitigation: orchestrator runs all
qualified gates and reports overlap; substrate-class taxonomy must be
disjoint by construction.

R2: **DAG cycle risk.** Gates with circular dependencies break dispatch.
Mitigation: cycle detection at registration time; refuse to register a gate
that introduces a cycle.

R3: **Migration leaves apparatus partially-routed.** During Phase 2, some gates
use Cage and some use legacy if-blocks. Mitigation: parity test asserts
identical engagement matrix pre/post per phase.

R4: **`can_handle` becomes a sycophancy loop.** A gate's predicate could be
written by an LLM that wants the gate to fire (no skin in the game). Mitigation:
predicates must be deterministic Python (no LLM calls); audited at registration.

R5: **Substrate-class inference brittleness.** A new substrate that doesn't
match any class causes silent fallback. Mitigation: fallback class is
`meta_audit` which always logs `substrate_unrecognized: true`; ops can monitor.

## Success criteria for v5.0 ship

Before Cage Orchestrator is declared shipped:
1. ALL 27 gates expose the Universal Gate Contract
2. Fixture test: substrate fixture × gate matrix shows ≥95% expected engagement
3. Three real substrates (one per major class) run end-to-end with Cage dispatch
4. `make gates` shows 0 "shipped but not wired" gates (vs today's 13)
5. `cage_dispatch_iter_NNN.json` lands every iter with declared+eligible+engaged
6. autoresearch_loop.py reduces by ≥500 lines (the if-block layer)
7. No rubric flag with `enable_X` for gate engagement (only philosophy flags)

## Related work

- GP-152 / GP-153: Framer architectural audit + spec critique (2026-04-24)
- GP-156: apparatus hardening (2026-04-25) — Proposal 1+2+3 + audit
- This seam (GP-157): the meta-fix that prevents future GP-156s from being needed
- v5.0 kernel placement (project_v5_kernel_placement memory): synthesis kernels
  go under `src/ztare/fit/continuous_chaotic/`; Cage routes them via dispatch

## Decision log

- **2026-04-25** — Seam opened after live audit revealed 13 unwired gates and
  silent Proposal 3 failure. Operator authorized v5.0 primary objective and
  requested `make gates` audit command be built immediately (LANDED same day,
  see `scripts/public/audits/audit_gate_engagement.py`).

- **2026-04-25 (panel debate)** — Operator requested 4-perspective panel
  debate on the proposal. Panel verdicts and required corrections aggregated
  below.

## 4-Perspective Panel Debate (2026-04-25)

### Newton (physics/discipline) — verdict: **ship with corrections**

Five formalization gaps must close before v5.0 ships:

1. **Substrate-class taxonomy is NOT proven disjoint.** A substrate with both
   numeric 1D pairs AND a features.py with 50 fields could match
   `1d_curve` AND `feature_dict`. Inference today runs sequentially —
   first-match wins, no priority order. **Fix:** add formal disjointness
   proof OR explicit priority order; treat overlap as warning + fall-through.

2. **DAG topological verification is undefined.** Spec says "cycle detection
   at registration time" but provides no algorithm. **Fix:** implement
   Tarjan's SCC at orchestrator init; reject any gate whose `depends_on`
   closure contains itself.

3. **`can_handle` predicates: no mutable-state contract.** "Deterministic"
   is under-specified. A predicate reading `Path("features.py").stat().st_mtime`
   is non-deterministic across calls. **Fix:** tighten to "pure" — depends
   only on immutable `ctx` snapshot, no `os.stat`, `time.time`, PRNG.
   Add pre-flight assertion: serialize ctx to JSON, deserialize, re-run
   predicate, assert outcome identical.

4. **Substrate inference brittleness.** Rule "features.py with FEATURES dict
   + str field → feature_dict_categorical" mis-classifies a 50-numeric-field
   schema with one deprecated string field. **Fix:** field-ratio heuristic
   (>90% numeric → feature_dict; <10% → feature_dict_categorical;
   10-90% → diagnostic + meta_audit fallback).

5. **`meta_audit` fallback distorts semantics.** It's both the "adversarial
   review" class AND the "no class matched" fallback. **Fix:** introduce
   explicit `substrate_unrecognized` class; halt iteration or escalate to
   manual review; preserve `meta_audit` for declared red-team intent.

Plus: clarify whether `depends_on` is SEMANTIC (downstream reads upstream's
GateResult) or ORDERING (just runs after). Without this, composability
unclear.

### Munger (inversion) — verdict: **ship with corrections; retire 12 of 15 dormant gates FIRST**

Six inversion attacks:

1. **`can_handle` predicates relocate the rubric-flag rot, don't cure it.**
   "Forgot to set `enable_X: true`" becomes "gate's `substrate_class`
   tuple drifted from inference logic." Same operator-discipline failure,
   harder to grep.

2. **Silent dormancy is hidden debt.** With if-blocks, a missing gate is
   a Python error or test break. With Cage, it's a JSON line nobody
   reads. **Fix:** alert if dormancy ratio drifts >5% week-over-week.

3. **Audit theater for predicates.** Spec says "predicates audited at
   registration." Who audits? When? Drift over months goes silent.
   **Fix:** automated linter + test, NOT human review.

4. **13 dormant gates may be DEAD CODE.** Building Cage gives them
   undeserved life support. **Fix:** retire 12 of 15 BEFORE Phase 1;
   wire only 3 the apparatus actually needs.

5. **Phase-2 / Phase-3 deadlock risk.** Phase 2 may surface bugs
   needing Phase 3 to fix, but Phase 3 needs Phase 2 stable. **Fix:**
   strict parity test asserts identical engagement matrix pre/post
   each phase.

6. **Predicate rot replaces flag rot.** A `can_handle` that USED to be
   correct but substrate reality drifted. New bug class, not smaller
   than the old.

Munger's "laziest implementation passes" test: a gate with `can_handle =
lambda _: (True, "handles everything")` and `depends_on = ()` and `run`
returning trivial result still satisfies the Protocol. Spec is descriptive
not prescriptive; code review doesn't scale.

### Engineer (implementation cost) — verdict: **architecturally sound; 8-11 agent-days, phased**

Concrete numbers:

- **autoresearch_loop.py**: 6,001 lines, 21 rubric conditionals averaging
  15-35 LoC each = 420-735 LoC of if-block scope. Realistic deletion:
  **150-400 LoC net savings** (seam's "≥500" is upper bound).
- **GateContext design**: 11-13 fields including `python_code`,
  `evidence_text`, `features_module`, `fit_decl`,
  `substrate_class_inferred`, `project_dir`, `probability_dag`, `rubric_data`.
  Frozen dataclass. NOT a 20-field explosion.
- **Fixture matrix**: 22 gates × 7 substrate classes = 154 cells. At
  ~15 min/cell = ~40 engineer-hours. **Phased**: Phase 2 covers
  `feature_dict` gates only (42-49 cells) for initial parity.
- **Effort estimate**: Phase 1 (infra) 3-4 days; Phase 2 (`feature_dict`
  migration) 2 days; Phase 3 (rest) 2-3 days; Phase 4 (release) 0.5 day.
  **Total 8-11 agent-days, 1.5-3 weeks engineer-time.**

Concerns:

1. **GateContext field creep**: freeze at 11-13 fields; use
   `extensibility_dict` for future additions.
2. **Substrate inference brittleness**: same point as Newton; needs
   priorities.
3. **DAG cycle on ship**: same point as Newton; needs Tarjan.
4. **Fixture parity test definition**: "≥95% engagement" vague; need
   PER-(gate, substrate) expected matrix.
5. **Phase-2 hybrid loop risk**: keep `if USE_CAGE:` toggles; don't
   delete old if-blocks until v5.0 RC.
6. **Disk-vs-memory bug class**: Cage helps structurally (python_code
   mandatory in ctx) but doesn't FORBID gates from disk-reads. Add
   `requires=("python_code",)` declarations + warn at registration if
   gate's source contains hardcoded `test_model.py` reads.

Rollback: keep both code paths via `USE_CAGE_ORCHESTRATOR` toggle
through v5.0 RC. Hard but possible 48-hour revert.

### Skeptic (production precedent) — verdict: **rationalize existing code FIRST; build Cage only after gate curation + validation protocol commitment**

Five precedent-based skepticism points:

1. **Dispatch pattern already exists.** `global_gates.py` ALREADY
   aggregates 5 gates with rubric-flag dispatch. Cage isn't inventing
   dispatch — it's replacing the **flag-gating layer** with predicates.
   Narrower, more defensible claim. But not architectural novelty.

2. **Cage solves wiring-coordination, not untested-by-default.** 13
   dormant gates are mostly from undeployed substrates (chaos /
   time-series / Lean / proof_target — last run gp146). Retiring is
   the right answer, not wiring. Cage gives them life support.

3. **GP-152 Framer v2.0 promised "no more manual instrumentation."
   Today: zero production fires.** Cage is another clean-sheet redesign
   without committing to the GP-152 fix protocol (Python smoke test +
   execution-hostile audit BEFORE shipping). Reproduces the same
   failure mode unless the protocol commitment is explicit.

4. **Success criterion confuses "wired" with "justified."** "0 'shipped
   but not wired' gates" is noise if gates are dead code with
   `can_handle = (False, "substrate_class != X")` firing forever.
   Honest win: explicit policy (retire OR reclassify OR Cage) for
   each gate.

5. **gp156 success doesn't prove apparatus is broken; proves
   validation protocol is weak.** Bugs found today are
   validation-protocol failures (Prose-vs-Code, Sycophancy Loop), not
   architecture failures. Ship Cage without protocol → gp156 finds
   bugs in `can_handle` predicates next.

Recommended path: **Hybrid — gate curation audit (retire/reclassify/wire decision per gate) + commit to GP-152 validation protocol + THEN build Cage** for whatever survives curation.

## Consolidated panel verdict

**All four panelists agree: do NOT ship Cage as-spec'd today.** Consensus required corrections:

1. **Pre-Phase 1: gate curation audit.** Per-gate explicit decision: retire,
   reclassify, or wire. Stop pretending all 22 gates need life support.
   (Munger + Skeptic.)
2. **Substrate-class formal disjointness or priority order.** No silent
   first-match. (Newton + Engineer.)
3. **Pure-predicate contract** with serialize-and-replay test for
   determinism. (Newton.)
4. **Tarjan SCC cycle detection at registration.** (Newton + Engineer.)
5. **Automated audit (linter + test), not human review.** (Munger.)
6. **Per-(gate, substrate) expected engagement matrix**, not blanket
   ≥95%. (Engineer.)
7. **Validation protocol commitment** (Python smoke test +
   execution-hostile audit) before shipping each phase. (Skeptic.)
8. **Dormancy alerting** if ratio drifts >5% week-over-week. (Munger.)
9. **Phase 2/3 strict parity tests** + `USE_CAGE_ORCHESTRATOR` toggle
   for rollback. (Engineer.)
10. **GateContext frozen at 11-13 fields**, extensibility via dedicated
    dict. (Engineer.)

These corrections are now decisive for v5.0 ship. The seam's success
criteria (line 200+) should be amended to require all 10 before declaring
Cage shipped.

## Programmatic Contract Enforcement (operator insight, 2026-04-25)

After watching gpt-4.1 ignore explicit prose warnings ("DO NOT call
I_model at module level — R1 will reject with KeyError") for multiple
iters in a row, the operator named the deeper pattern:

**"Prompt enforcement is shit if it's ignored. We need a programmatic
way."**

This is the same lesson Cage Orchestrator embodies at the architectural
level, applied at the substrate level. Three tiers of enforcement
strength:

| Tier | Mechanism | Enforceability | Examples |
|------|-----------|----------------|----------|
| Weak | Prose in prompt / persona / docstring | Advisory; LLM may ignore | "DO NOT call I_model at module level" |
| Medium | Runtime exception in R1 / harness | Iter wasted on the API call before reject | KeyError caught by mutation_suite_guard |
| **Strong** | **AST/static check before exec** | **Zero LLM-call cost; mutator MUST resubmit** | `_safe_compile_form` AST whitelist; `_ast_check_no_module_level_i_model_call` (shipped 2026-04-25) |

The Cage Orchestrator's `can_handle()` predicate IS a tier-3
enforcement mechanism for substrate-class engagement: a gate cannot
"opt in" by ignoring the predicate; the orchestrator simply doesn't
call it. Same pattern, broader scope.

### Programmatic enforcement landscape (gp154/gp155/gp156 today)

Three rules already programmatic (tier 3):
1. **AST whitelist for PARAMETRIC_FORM** (`_safe_compile_form`) — a
   mutator cannot call disallowed functions; the AST refuses.
2. **Pre-fit feature-key cross-check** (`extract_referenced_feature_keys`)
   — a misspelled `features['intrnsc_dim_d']` is rejected at form-
   validation time; scipy never spins.
3. **Module-level I_model call detector** (`_ast_check_no_module_level_i_model_call`)
   — shipped 2026-04-25 in response to today's prompt-ignored failures.

Four more should be tier-3 enforced (current rules at tier 1 — prose):
1. **Mandatory thesis prose**: `clean_thesis` length ≥ N chars before
   accepting submission. Currently a persona reject rule that mutators
   sometimes ignore.
2. **Mandatory I_model definition**: rubric flag
   `require_i_model_in_submission` flips this from on/off; tier-3 means
   the AST check fires regardless of rubric flag.
3. **Mandatory `from features import ...`** when PARAMETRIC_FORM
   references `features['key']`: AST detects subscript on `features`,
   asserts there's an import statement.
4. **Mandatory deterministic I_model**: AST + module-load test asserts
   `I_model(features) == I_model(features)` for the same input across
   two calls (catches non-deterministic predictors).

### Cage Orchestrator's role in programmatic enforcement

Cage's contribution is **contract-as-code at the gate level**:
- A gate's `can_handle(ctx)` is a Python predicate, not a rubric flag
- Substrate-class inference is mechanical, not configured
- DAG dependency declared in code, not documented in prose

The 10 required corrections list (above) includes "automated audit
(linter + test), not human review" — that's the same principle:
prose enforcement of contract is theater unless mechanically verified.

### Tier-promotion workflow

When a tier-1 (prose) rule is repeatedly ignored:
1. Document the failure (debate log + iter count).
2. Identify if static analysis can detect the violation.
3. Promote to tier-3 (AST/static check) in the apparatus.
4. Remove the now-redundant prose warning OR keep as documentation
   (NOT as enforcement).

Today's gp155 module-level I_model pattern surfaced this workflow:
prompt → ignored 5+ times → AST check shipped → contract now
mechanically enforced.

## Appendix A — Newton panelist full transcript

**Verdict**: ship with corrections.

I identify 5 discipline-rigor concerns. The proposal is architecturally
sound but carries unresolved physical ambiguities that must be
formalized before v5.0 release.

### 1. Substrate-Class Taxonomy Is NOT DISJOINT. Risk: Silent Misclassification

The taxonomy lists 7 classes: `1d_curve`, `feature_dict`,
`feature_dict_categorical`, `closed_form_constant`,
`time_series_chaotic`, `proof_target`, `meta_audit`. The seam asserts
"each gate declares the substrate classes it targets" BUT provides
no proof the classes partition the space.

**Failure scenario**: A real substrate has BOTH numeric 1D pairs AND
declared features.py with 50 fields. Inference rule (line 80–86) runs
sequentially: if `features.py` + `FEATURES` dict match first, the 1D
structure is NEVER examined. Two gates fire concurrently on disjoint
class definitions. Downstream gates depending on "only time_series
gates ran" get false premise.

**Formalization gap**: The seam needs:
- A formal disjointness proof (or explicit overlap rules if overlap is allowed)
- A canonical PRIORITY ORDER for inference (what if multiple match?)
- Whether "all" is a true equivalence class or a permission wildcard
  (gates targeting "all" don't constrain the substrate)

### 2. DAG Topological Verification Is Undefined. Risk: Registration-Time Cycle Injection

The seam says "cycle detection at registration time; refuse to register
a gate that introduces a cycle" (line 173) BUT provides NO algorithm.
The current code base has ZERO cycle-detection code in the gates
directory. Examples given (line 93–95) are ANECDOTAL, not verified.

**Failure scenario**: Gate A declares `depends_on: ("B",)`. Gate B
(shipped later in v5.1) declares `depends_on: ("A",)`. Both pass
registration individually because each is checked against prior gates
only — no full-graph re-validation. When the Cage loads both,
topological sort fails silently (no error handler specified). The
iteration hangs or falls back to `meta_audit`, swallowing the cycle
entirely.

**Formalization gap**: Implement Tarjan's SCC algorithm at
orchestrator boot. Reject any gate whose `depends_on` closure contains
the gate itself. Document the contract: "all `depends_on` references
must be to gates already registered OR gates whose registration
immediately precedes this one."

### 3. `can_handle` Predicates: No Mutable-State Contract. Risk: Non-Determinism Under Mutation

The seam mandates "deterministic Python (no LLM calls)" (line 180).
But "deterministic" is under-specified. A `can_handle` predicate CAN
read the filesystem (e.g., `Path("features.py").stat().st_mtime`).
The same predicate called twice may return different answers if an
intermediary mutation touched the file.

**Failure scenario**: `can_handle(ctx)` returns True because
`features.py` has modification time < 1 minute old. Iterator mutates
features.py. Re-run the same iteration (debugging, retry).
`can_handle` now returns False due to mtime. Gate's engagement is
non-deterministic; `cage_dispatch_iter_NNN.json` logs disagree with
replay.

**Formalization gap**: Tighten "deterministic" to: "**pure**: depends
ONLY on immutable snapshot in `ctx` (submission_text, features_module
AST, evidence.txt, project_dir BASENAME not filesystem stat)." Forbid
`os.stat()`, `time.time()`, PRNG calls. Add pre-flight assertion:
serialize context to JSON; deserialize and re-run predicate; assert
outcome identical.

### 4. Substrate Inference Brittleness: 1 Deprecated Field = Misclassification. Risk: Silent Categorical Downgrade

Inference rule (line 81): "features.py with FEATURES dict + str field
→ feature_dict_categorical". A features.py from an old project has 50
numeric fields + 1 DEPRECATED string field (never used). The rule
matches; substrate is inferred `feature_dict_categorical`. But the
actual 50 fields are numeric — gates expecting numeric-only data fire
and produce nonsense.

**Failure scenario**: `ensemble_ambiguity_gate` (targets
`feature_dict`) and `fit_primitive_features.py` (targets
`feature_dict_categorical`) both claim eligibility.
`fit_primitive_features` runs and tries to construct feature
dictionaries from the deprecated string field (which is always NULL).
Residuals → NaN. Silent failure: the gate's score_delta is 0 (default),
iteration logs show "gate executed OK", but no actual fit happened.

**Formalization gap**: Enhance inference to be PRAGMATIC: count
numeric-vs-string field ratio, not presence of ANY string. Rule: if
>90% numeric, infer `feature_dict`; <10%, infer
`feature_dict_categorical`; 10-90% → emit a DIAGNOSTIC WARNING and
fall through to `meta_audit`. Never silently misclassify.

### 5. `meta_audit` Fallback Distorts Its Original Semantics. Risk: Conflation of Adversarial vs. Catchall

`meta_audit` was designed for adversarial execution-hostile review
(gp152/gp153/gp156 shape). It contains gates that assume the code is
ATTACK VECTOR CODE, not legitimate predictor. The seam says "if no
class matches, emit warning but run `meta_audit` defaults" (line 88).
This re-purposes `meta_audit` as a catch-all, not an audit class.

**Failure scenario**: A new substrate class (e.g.,
`stochastic_ensemble`, added in 2026-06 but not known to inference
rules) fails to match any class. Cage falls back to `meta_audit`.
`prompt_leak_audit` gate (which hunts for embeddings of the training
prompt in the mutator's code) fires. The gate detects a string literal
in the mutator's code ("I should check if my function works...") and
flags it as a leak. In reality, it's a legitimate comment. The
substrate was never supposed to be audited for prompt leaks — it was
miscategorized.

**Formalization gap**: Introduce an explicit `substrate_unrecognized`
class. Do NOT run `meta_audit` gates on unrecognized substrates.
Instead, log the unrecognized substrate, report to operator, and
HALT the iteration (or escalate to manual review). Preserve
`meta_audit` for its original purpose: deliberate adversarial audit
when the project charter declares "red-team / security audit".

### Conservation Law Concern: Gate Result Chaining

The seam specifies `GateResult` (line 60–62) with `score_delta` but
does NOT define how results flow downstream. If each gate is
independent (reads only `ctx`, ignores prior gate results),
composability is lost: a gate cannot refine or veto the conclusions
of an earlier gate. If gates are chained (later gates read earlier
results), coupling breaks modularity. The seam must clarify: is
`depends_on` a SEMANTIC dependency (gate B uses gate A's result) or
an ORDERING dependency (B runs after A, but they're independent)?

### Specific Fixes for Ship

1. Add `substrate_class_disjoint_proof()` function in a new seam appendix. If overlap allowed, document priority order.
2. Implement Tarjan SCC algorithm in `CageOrchestrator.__init__` (line ~registration). Reject cyclic gates.
3. Add `ctx.is_mutable_filesystem_access()` type-guard in can_handle tests. Use assert in test suite.
4. Enhance `_infer_substrate_class()` with field-ratio heuristic; add fallback → `substrate_unrecognized` not `meta_audit`.
5. Clarify gate result semantics: "downstream gates read `depends_on` gates' GateResult fields if declared."

**CAGE: ship with corrections** — architectural intent is sound, but
physical contract gaps risk silent failures in production under future
substrate additions.

## Appendix B — Munger panelist full transcript

**Verdict**: ship with corrections (and only if the corrections are
mechanically enforced, not human-reviewed).

### 1. Audit Theater for `can_handle` Predicates

The seam demands "deterministic Python — audited at registration."
But who audits? When? The code shows no audit mechanism — only a
hopeful "cycle detection at registration time." In practice: a new
gate lands with a predicate, ops glances at it, ships. 18 months
later, the predicate has drift (substrate reality changed, predicate
didn't). Unlike rubric flags which FAIL LOUDLY when wrong
("enable_X not in schema"), a drifted `can_handle` returns False
silently. You've relocated the operator-discipline problem to a
place with worse observability.

### 2. Same Disease, Relocated Symptom

Rubric-as-config problem: "forgot to enable_X in the rubric." Cage
pattern: "gate's `substrate_class` tuple doesn't match the inference
logic." Both are operator-discipline failures where one file drifts
from another. The seam pretends replacing Python conditionals with
predicates solves this — it doesn't. It just makes it harder to
grep for the breakage. Phase 2 parity tests catch *this iteration's*
drift, but they're a one-time check, not structural prevention.

### 3. Silent Dormancy as Hidden Debt

The seam promises "explicit dormant logging" but doesn't specify who
reads `cage_dispatch_iter_NNN.json`. In practice: that file lands in
`workspace/` alongside 50 other JSON artifacts. A gate fails to
engage? That's now a *log grep* rather than a test failure. The
apparatus is objectively *less visible* when a gate doesn't fire —
you have to know to look. With hardcoded if-blocks, a missing gate
was a Python SyntaxError or test break. Now it's "reason:
substrate_class != time_series_chaotic" in a JSON that never gets
read.

### 4. 13 Dormant Gates May Be Zombie Apparatus

The seam treats these as "should be wired eventually." But maybe
the right answer is: **audit which 12 of 15 are actually dead code
no one needs, retire them formally, and wire only 3**. Building the
Cage gives all 13 a second lease on life without forcing that
discipline. The `substrate_class` taxonomy becomes
self-perpetuating: "we have a `proof_target` class, so the Lean
gates must be useful." Cargo-culting.

### 5. Predicate Rot: A New Bug Class

You've solved rubric-flag rot. You've introduced predicate rot: a
`can_handle` that *used to* be correct but substrate reality
drifted. Example: `proof_target` inference checks "project name
mentions Lean" but a gate's predicate checks for
"closed_form_constant." One drifts, gate silently never fires. The
seam doesn't reduce bug surface — it trades one category for
another. Is the new one smaller? No evidence. It's just *different*.

### 6. Migration Deadlock in 4-Phase Plan

Phase 2 surfaces a bug that requires Phase 3's infrastructure to
fix, but Phase 3 depends on Phase 2 being stable. Result: you're
stuck in a partially-routed apparatus where some gates use Cage
and others use legacy if-blocks — exactly the observability hell
you were trying to escape. The parity tests assume no phase
introduces a behavioral change. If one does, all subsequent
phases are jeopardized.

### 7. Laziest Possible Implementation Still Passes

What stops a gate from `can_handle` always returning
`(True, "handles everything")`? Nothing in the seam. Audit?
Already shown to be theater. A `depends_on` that's always empty?
A gate ordering that ignores declared dependencies? The protocol
is descriptive, not prescriptive. Code review would catch these,
but code review doesn't scale — Cage was supposed to *reduce* the
operator-discipline surface.

**CAGE: ship with corrections** — but only if:
- Audit mechanism is automated (linter + test, not human review).
- `cage_dispatch_*.json` is monitored (alert if dormancy ratio
  drifts >5% week-over-week).
- Phase 2 parity tests explicitly forbid behavioral changes between
  Cage-routed and legacy gates.
- Retire 12 of 13 dormant gates before Phase 1; don't let Cage
  resurrect dead code.

Otherwise, you've moved the rubric-as-config disease sideways, not
cured it.

## Appendix C — Engineer panelist full transcript

**Verdict**: architecturally sound and necessary. **8-11 agent-days
or 2-3 engineer-weeks (serial), 1.5-2 weeks (parallel with external
dependencies on LLM calls).**

### Migration Cost — LoC Delta Reality Check

- **autoresearch_loop.py**: 6,001 lines total; 21 rubric conditionals
  (not 500-line blocks as seam suggests).
- **Actual if-block scope**: Each rubric gate conditional averages
  15-35 LoC (nested logic, error handling, imports), totaling
  ~420-735 LoC.
- **Gate refactoring**: 22 gates total; 15 dormant need Protocol
  exposure (can_handle + run signature). Per gate: ~15-20 LoC to
  expose the contract.
- **Net LoC delta**: elimination of 420-735 LoC from autoresearch_loop
  minus ~225-300 LoC added to gate modules = **net 120-510 LoC reduction**.

Seam's "≥500 lines" is **realistic but at upper bound**.

### GateContext Design — Interface Stability

A minimal GateContext needs 11-13 fields:
- `submission_kind: str`
- `python_code: str`
- `evidence_text: str`
- `features_module: dict | None`
- `fit_decl: FitDeclaration | None`
- `substrate_class_inferred: str`
- `project_dir: Path`
- `test_model_path: Path`
- `probability_dag: dict | None`
- `rubric_data: dict`

Frozen dataclass (`frozen=True`); optional fields handled via `| None`
type hints. NOT a 20-field explosion. New fields added at end only,
covariant design.

### Fixture Test Scope — 154-Cell Matrix Realism

22 gates × 7 substrate classes = 154 test cells. At ~15 min/cell =
~40 engineer-hours = 5 days of focused work. **High-risk area**: if
substrate inference returns wrong class, gates stay dormant despite
being eligible. Phase 2 covers `feature_dict` gates only (~6-7 gates,
42-49 cells) for initial parity.

### Breaking Changes — Rubric Flag Migration

11 distinct enable_X flags in circulation. Three tiers:
- **Tier 1 (drop at v5.0)**: flags whose sole purpose is gate
  engagement (e.g., `enable_fit_primitive_features` becomes predicate).
- **Tier 2 (keep, repurpose)**: flags controlling algorithm behavior
  (`fit_score_mode`, `composition_budget`) — become rubric philosophy
  flags.
- **Tier 3 (soft deprecation)**: warning log + still works (backward
  compat layer).

### Rollback Story

Don't delete old if-block code during Phase 1-3. Wrap in
`if USE_CAGE_ORCHESTRATOR:` toggles. Keep both paths live in v5.0 RC.
48-hour revert + hotfix is plausible; a clean 2-week undo without
data inspection is not.

### Concurrency / State

Each gate's `run()` method must be pure (no module-level mutation)
or use a context manager for locking. `CageOrchestrator.dispatch()`
must accept optional `workspace_lock: threading.Lock`. GateContext
itself should be immutable (frozen=True).

### Disk vs Memory — Architecturally Prevented?

Cage provides structural guardrails but not perfect protection. A
gate author could still ignore `python_code` and read test_model.py
from disk. **Mitigation**: type-signature rule "Gates that need
python_code must declare it in a `requires` tuple". Auditing:
`make gates` includes a "disk I/O audit" step — grep each gate for
hardcoded file reads and warn if orthogonal to GateContext inputs.

### Top 5 Implementation-Cost Concerns

1. **GateContext field creep**: freeze at 11-13; use
   `extensibility_dict` for future additions.
2. **Substrate inference brittleness**: needs formal priorities;
   emit warning when >1 class matches.
3. **DAG dependency cycle on ship**: Tarjan at registration time;
   test suite includes cycle anti-patterns.
4. **Fixture parity test definition**: per-(gate, substrate)
   expected matrix, not blanket 95%.
5. **Live rollout risk during Phase 2**: hybrid loop creates
   debug-path explosion; strict parity test must match exactly,
   roll back Phase 2 if diverged.

**Effort phasing**:
- Phase 1 (infra): GateContext + CageOrchestrator + Protocol +
  inference + fixture suite = 3-4 agent-days.
- Phase 2 (one substrate class): 6-7 gates migrated = 2 agent-days.
- Phase 3 (remaining): 1d_curve + time_series + proof_target +
  meta_audit = 2-3 agent-days.
- Phase 4 (release): docs + cleanup = 0.5 agent-day.
- **Total: 8-11 agent-days, 1.5-3 weeks engineer-time.**

**Final verdict**: Cage is sound. **Don't oversell as a primary
performance win** (LoC savings are 150-400 not 500+); sell as a
*capability debt fix* (apparatus visibility + reusability) that
happens to save code. **Start Phase 1 now; v5.0 beta entry on
Phase 2 completion.**

## Appendix D — Skeptic panelist full transcript

**Verdict**: **Rationalize existing code + Hybrid approach (Build
Cage only after completing [1] inventory audit of 27 gates [2]
explicit retirement/reclassification decisions [3] Python
smoke-test + execution-hostile-audit protocol commitment).**

### 1. Have We Tried This Before?

`global_gates.py` (L1-56) shows the apparatus ALREADY HAS a
dispatch-like pattern: per-substrate gate registration via
`_load_model_fn()`, shape-based routing, and a result-merge contract
into `deterministic_charter_gates`. The seam calls Cage
"substrate-agnostic dispatch" but what Cage actually proposes is
*predicate-based* dispatch (via `can_handle()`) instead of
*rubric-flag-based* dispatch.

However: `global_gates.py` **still uses rubric flags** (`disable_*_gate`,
`enable_*`) to control engagement. So Cage isn't inventing dispatch;
it's replacing the **flag-gating layer** with **shape-matching
predicates**. This is a narrower claim than "fix the architecture,"
and narrower claims are more defensible.

### 2. Root Cause Classification

The seam identifies 13 unwired gates. Three possible root causes:
- **Laziness/coordination**: operator forgot to set `enable_X: true`,
  or two people thought "the other one would wire it."
- **Untested-by-default**: the gate was built but no fixture verifies
  it fires under intended substrates.
- **Substrate-not-deployed**: the gate was built for a substrate class
  that hasn't run in weeks (gp146 chaos / time-series substrates).

The audit data shows 13 unwired gates across substrate classes (chaos,
time-series, Lean-formalizable, proof-target) that "haven't run since
gp146." **That is primarily a deployment-class problem, not a
wiring-coordination problem.** Cage fixes coordination but doesn't
address the root: "we built gates for substrates we don't run anymore."
The honest fix is to retire those gates, not to "wire them via
predicates."

### 3. GP-152 Framer Promised the Same Kind of Fix

Framer v2.0 shipped after a 24-iter audit. Today's audit shows it
fires ZERO times in production across all today's runs. The
postmortem `GP-152_153_ztare_on_ztare_sycophancy_loop` documents why
v2.0 shipped with three latent bugs:
**Prose-vs-Code Mirage** (the audit was spec-only; no Python
interpreter ran), **Lookup-Table Ghost** (a memorization pass disguised
as a law), and **Sycophancy Loop** (LLM mutator + LLM judge reinforced
each other's framing). The fix was to mandate **Step 1 (Python
integration smoke test)** before shipping any architectural fix.

**Cage's credibility problem**: Cage is another clean-sheet
architectural redesign. The seam does not commit to the GP-152 fix
protocol. Without that protocol, Cage runs the same risk: the
`can_handle()` predicates could be theoretically elegant in the seam
and silently broken in autoresearch_loop because the integration test
was not run before declaring victory. **The pattern is not broken;
the validation cadence is.**

### 4. Success Criterion: "Wired" vs "Justified"

The seam's win condition is: "`make gates` shows 0 'shipped but not
wired' gates." This conflates **having everything wired** with
**having a clean policy for everything**.

If a gate is dead code (no substrate in the last 60 days would invoke
it), wiring it via Cage's `can_handle()` predicate is just **noise in
cage_dispatch_iter_NNN.json**. The predicate will say
`(False, "substrate_class != time_series_chaotic")` on every iter,
forever. The output is "clean" but the gate is still a zombie.

**The more honest win condition**: "0 gates deployed with no explicit
policy (retirement OR substrate class definition OR predicate
contract)."

### 5. gp156 Success — Apparatus Healthy or Broken?

The seam cites gp156 (apparatus hardening review) as finding bugs
continuously today. The interpretation: "the apparatus is broken,
Cage will fix it."

**Inverted interpretation**: "The apparatus is healthy enough that
gp156 can find bugs." gp156 found three classes of apparatus defects.
All three are **validation-protocol failures, not architecture
failures.** If we ship Cage without the validation protocol, gp156
will find bugs in Cage's `can_handle()` predicates next.

The right investment is not "Cage Orchestrator" but "Apparatus
Validation Protocol v2" (Python smoke test + execution-hostile audit
before any architectural change). That protocol would have caught
v2.0 Framer's bugs before they shipped. **Apply it to Cage and Cage
becomes credible. Skip it and Cage reproduces the same failure mode.**

### 6. Path-Dependent vs Path-Independent Fix History

ZTARE itself is organic: it accumulated over weeks of panicked
construction. The seam acknowledges this and proposes a clean-sheet
redesign. But the codebase's history shows clean-sheet rewrites
typically come with high switching cost (a month of migration, 3×
test coverage, explicit rollback plan). **Ambitious refactors in this
codebase fail when they skip the validation protocol** (GP-152 →
GP-152/153 postmortem). The pattern is clear.

**Recommended path forward**: Cage's predicate dispatch is technically
sound, but deploying it without the GP-152 validation fix and an
honest gate curation audit (retire vs. reclassify vs. wire) risks
reproducing the same postmortem postmortems — invisible until gp156
finds it.

## Decision log (continued)

- **2026-04-25 (panel + ship)** — 4-perspective panel returned
  unanimous "ship with corrections" verdict (Newton, Munger, Engineer,
  Skeptic). 10 consolidated corrections logged above. AST pre-flight
  for module-level I_model calls SHIPPED in mutation_suite_guard.py
  same day as a programmatic-enforcement exemplar (operator's "prompt
  enforcement is shit if ignored — we need a programmatic way" insight).

- **2026-04-25 (reachability defect class — Bug #11)** — operator
  noticed verbose telemetry banner never printed despite shipped.
  Root cause: GP-156 Proposal 3 wire-in was nested INSIDE
  `if rubric_data.get("enable_fit_primitive", False)` (the 1D fit
  branch), not as a SIBLING dispatch. gp155/gp154 have
  `enable_fit_primitive=false` (Proposal 3 only), so the entire 1D
  branch was skipped, taking the wire-in with it. 30+ iters across
  gp154+gp155 ran with NO Proposal 3 engagement. **Spec ambiguity
  contributed**: spec said "near existing fit_primitive call" — "near"
  was read as nested. **Smoke test gap**: scripts/public/audits/gp156_integration_smoke_test.py
  tested fit_features() in isolation but never asserted REACHABILITY
  from the iter body on a Proposal-3-only substrate. New v5.0 hard
  requirement (#11 corrections list above): each gate must have a
  fixture that simulates an iter against a real-shape substrate and
  asserts the dispatcher actually invokes the gate. Reachability
  testing is non-negotiable for Cage; gates must prove they fire
  on their declared substrate classes via simulation, not just
  via in-vitro unit tests.

## Lesson: Reachability vs Correctness in apparatus testing

This bug class is distinct from the disk-vs-memory class and the
prose-enforcement class. Add to v5.0 testing protocol:

| Test class | What it verifies | Today's coverage | v5.0 requirement |
|------------|------------------|------------------|------------------|
| Unit / smoke | Function correctness in isolation | Good (`gp156_integration_smoke_test.py`) | Required |
| Reachability | Dispatcher actually calls the gate on substrate of class C | NONE | **Required for every gate × substrate-class pair** |
| Cage parity | Pre-Cage and post-Cage produce identical engagement matrix | N/A pre-v5.0 | Required during Phase 2 / Phase 3 |
| Substrate inference | Real substrate → correct class label | NONE | Required for new substrate classes |

The integration smoke test that DOES test reachability would be: spin
up a synthetic substrate fixture that has features.py + a mutator-style
test_model.py with PARAMETRIC_FORM declared. Run the autoresearch_loop's
iter body (mocking only the LLM call) and assert that
`fit_features_result.json` lands in workspace. That's REACHABILITY
testing — guarantees the wire-in is in the right place.

GP-157's required corrections #6 (per-(gate, substrate) expected
engagement matrix) IS reachability testing under another name. This
seam now treats reachability as decisive for v5.0.

## Consolidation: fit_primitive (1D) + fit_primitive_features (N-D) → unified fit engine

**Added 2026-04-25** during gp154/gp155 debugging session.

### Current state — two parallel scipy fitters

The codebase ships two structurally similar primitives that diverged by
substrate shape, not by algorithm:

| Property | `fit_primitive.py` | `fit_primitive_features.py` |
|---|---|---|
| Engages on | rubric `enable_fit_primitive=true` + thesis `FIT_DECLARATION` block | rubric `enable_fit_primitive_features=true` + test_model.py module-level `PARAMETRIC_FORM` |
| Input shape | 1D paired `(x, y)` evidence rows | N-D `(features_dict, y)` rows |
| Form parser | `parse_fit_declaration` markdown block extractor | `extract_form_declaration` AST module-level reader |
| Engine | `scipy.optimize.curve_fit` multi-start | `scipy.optimize.minimize` multi-start with auto-escalation |
| AST whitelist | bare-name expression parser | `_safe_compile_form` (features+params subscripts allowed) |
| Engagement gating | rubric flag + declaration parse-success | rubric flag + `should_engage` predicate |
| Telemetry | fit_result.json | fit_features_result.json + 🧮 banner (verbose) |
| Wire-in (autoresearch_loop) | line ~4175 (1D branch) | line ~4538 (sibling block, post Bug #11 fix) |
| Failure-mode parity audit | partial — no equivalent of Flat-Desert bypass detection (?) | full — pre-fit feature-key cross-check + post-hoc penalty detection + NaN-mask defense |
| 🧮 verbose banner on every iter | NO — failure mode visibility gap | YES |

### Risk that motivates consolidation

The "residual void exploitation" failure class observed historically
on the 1D primitive (gp149 mining surfaced silent fallbacks to
LLM-written code when fit_primitive engagement gating misfired) is
the **same structural class** as Bug #11 today on the features
primitive (wire-in nested under wrong rubric flag → 30+ iters fell
back to LLM silently). Two primitives, same bug class, fixed in only
one place. Without consolidation, every void-exploitation defense we
ship to one primitive must be retro-applied to the other, manually,
forever.

The "Sycophancy Loop" + "prose-vs-code gap" defenses we shipped
under GP-156 today (visible-MRE attestation, AST contract enforcement,
post-hoc penalty detection, R1 compiler bounce 3-strike retry) are
all single-primitive. The 1D fitter has none of them. Any project
running on a 1D substrate today has weaker defenses than gp154/gp155.

### Proposed v5.0 unified architecture

Inside the Cage Orchestrator (substrate-agnostic dispatch) define a
single `fit_engine` that the orchestrator routes to based on substrate
class:

```
class FitEngine(Protocol):
    def should_engage(substrate, candidate) -> tuple[bool, str]: ...
    def fit(declaration, evidence) -> FitResult: ...
    def write_result(workspace_dir, result) -> None: ...

# Concrete impls — share the scipy multi-start core, vary only by
# input-shape adapter and form-extraction strategy.
class OneDFitEngine(FitEngine): ...
class FeatureVectorFitEngine(FitEngine): ...
```

Shared core (Mungerian "compress" pivot — extract the invariant from
the variations):
- `scipy.optimize.minimize` multi-start with init_range escalation
- AST whitelist for form expression (extended to allow both 1D
  bare-name and N-D `params['k']` / `features['key']` styles)
- Pre-fit input-key cross-check (Flat-Desert bypass defense)
- Post-hoc penalty detection (NaN/inf/sentinel detection)
- Verbose 🧮 banner on every iter
- Engagement-decision logging (engage/skip + reason) — visibility on
  silent fallback class

Adapters (the only thing that varies):
- 1D: parse `FIT_DECLARATION` markdown block; evidence rows parsed
  from evidence.txt as `(x, y)` pairs
- N-D: parse module-level `PARAMETRIC_FORM` + `PARAMETER_NAMES`;
  evidence rows from `features.visible_rows()` as `(dict, y)` triples

### Sequencing

This consolidation is v5.0-Cage-class refactor, not today's emergency
fix. Order of operations:

1. Today: ship Bug #13 (AST whitelist for `params[...]`) and Bug #14
   (params-contract opt-in enforcement) — both single-file, both
   urgent for unblocking gp154/gp155.
2. Within v5.0 Phase 2 (Cage scaffolding): retro-port the four GP-156
   defenses (🧮 banner, post-hoc penalty detection, contract AST
   enforcement, R1 compiler bounce) to the 1D primitive. This is
   pre-consolidation parity work — guarantees no regression when
   the unified engine cuts over.
3. v5.0 Phase 3 (engine cutover): introduce `FitEngine` Protocol and
   the two concrete impls; route via Cage; deprecate the standalone
   modules.
4. Phase 4 (cleanup): delete the parallel modules; the old wire-ins
   become Cage dispatch entries.

### Why this matters for the Cage Orchestrator scope

GP-157 was originally framed as substrate-agnostic dispatch. The fit
primitive is a *gate*, not a substrate, but it has the same shape:
parallel implementations diverging by input class with no shared
contract. The Cage's job is to be the single dispatcher that routes
dispatch-by-shape decisions. Fit engine consolidation is therefore
**within Cage scope** — it's the same "stop scattering substrate-
shaped logic across the apparatus" thesis applied to the fit layer.

### Anti-pattern flag

Avoid the temptation to ship a third fit primitive when the next
substrate shape arrives (e.g. tensor-shaped inputs for some future
gp159). Adding a third parallel implementation would be a Munger
"man with a hammer" failure: every new substrate class would force
us to reinvent the multi-start + AST + telemetry stack. The unified
engine is the structural fix that makes the cost of adding a new
substrate shape O(adapter-only), not O(full-fitter-rewrite).

## Consolidation: substrate-evaluation utility for new-law-recovery harnesses

**Added 2026-04-25** during gp154/gp155 emergency-fix session, after operator
flagged the gate_harness.py edits as engineered/overfitted to the two projects.

### The meta-pattern operator named

When recovering laws in a complex domain where **ground-truth recovery is
not available** (no closed-form law to compare against; the apparatus has to
infer the law from visible+holdout splits), the gate harness needs a recurring
set of structural invariants that have nothing to do with the specific
substrate:

1. **Per-row crash tracking with class histogram** — distinguish "model
   ran but predicted poorly" from "model crashed on every row." Today's
   `try/except: rel_err=1.0` pattern collapses the two into the same MRE
   number, hiding the failure class from the judge. Bug #16 today.
2. **Crash-rate harness-defect propagation** — when crash_rate ≥ 50% the
   harness must surface as `fail_runtime` (RuntimeError), not as
   `fail_assert` (AssertionError on poor MRE). Different judge handling,
   different mutator feedback. Bug #16 today.
3. **Graduated near-miss band** — when MRE is in `[threshold,
   k×threshold]` (k ≈ 1.5), tag the failure as `[near_miss — REFINE this
   form, do not redesign]`. Without this, the mutator gets the same 0
   score for *almost* fitting and for fitting nothing — and reasons
   "redesign from scratch." Bug #18 today.
4. **Pre-flight bypass for the loud-fail** — `--emit-deterministic-gates`
   smoke tests run the harness against a baseline stub which crashes
   100% by construction; the loud-fail must skip in pre-flight or the
   pre-flight gate is unrunnable. Bug surfaced in this session.

### Today's anti-pattern — copy-paste into per-project harnesses

Bugs #16 and #18 were shipped as inline edits to:
- `projects/gp154_scaling_law_exponents/gate_harness.py`
- `projects/gp155_synthetic_dense_d_N_substrate/gate_harness.py`

Both got the same logic, the same magic numbers (0.5 crash threshold, 1.5
near-miss factor), the same exception-class accumulator, the same pre-flight
bypass. **Every future feature-vector substrate will require re-copying
this.** That is the man-with-a-hammer failure operator caught: the
fix is a meta-pattern but it's been instantiated as a per-project stamp.

### v5.0 extraction sketch

New module: `src/ztare/gates/substrate_evaluation.py`

```python
@dataclass
class EvalResult:
    n: int
    mean_relative_error: float
    max_relative_error: float
    per_row: list[dict]
    crash_count: int
    crash_rate: float
    nonfinite_count: int
    crash_classes: dict[str, int]
    passed: bool
    near_miss: bool
    threshold: float

def evaluate_set(
    rows: list[tuple[int, float]],
    i_model: Callable,
    features_module,
    *,
    threshold: float,
    near_miss_factor: float = 1.5,
) -> EvalResult: ...

def assert_or_propagate_defect(
    result: EvalResult,
    gate_name: str,
    *,
    crash_threshold: float = 0.5,
    is_preflight: bool = False,
) -> None:
    """Raise RuntimeError if crash_rate ≥ crash_threshold (harness defect),
    else raise AssertionError with [near_miss] / [hard_miss] tag if not
    passed. Skipped under is_preflight."""
```

Per-project gate_harness.py reduces to ~40 lines: parse evidence, call
`evaluate_set` + `assert_or_propagate_defect` for each gate, print JSON,
done. New substrates inherit the four meta-pattern invariants for free.

### Composition with fit-engine consolidation

This sits at the same architectural layer as the fit-engine consolidation
described in the previous section. Together they give v5.0 Cage
Orchestrator three substrate-agnostic primitives:

| Primitive | Today | v5.0 |
|---|---|---|
| **Fit engine** | parallel `fit_primitive.py` (1D) + `fit_primitive_features.py` (N-D) | unified `FitEngine` Protocol with shape adapters |
| **Substrate evaluation** | per-project gate_harness.py with copy-pasted crash/near-miss logic | shared `substrate_evaluation.py` module imported by thin per-project shims |
| **Engagement gating** | per-rubric flags scattered across iter loop | Cage dispatcher with per-(gate × substrate-class) reachability matrix |

Each of the three is the same Munger pivot: extract the invariant from
the variations, ship the variations as adapters. None alone is load-
bearing; together they collapse a 6,000-LoC iter body into ~3,000 with
clearer composition.

### Anti-overfitting rule for v5.0

When shipping a new gate-harness or evaluation primitive, the test is:

  *"If I had to write this for the next substrate, would I re-derive
  the SAME magic numbers and the SAME crash-handling pattern?"*

If yes → the primitive belongs in `substrate_evaluation.py`, not in
the per-project harness. This is the version of the fit-engine
"don't ship a third parallel fitter" rule, applied to the gate
harness layer.

## Bug #21 (2026-04-25): hard-gate shape divergence + near-miss respect

### What surfaced
gp155 iter 1 produced a structurally-correct sigmoid blend that the apparatus
fit primitive successfully fitted. HOLDOUT passed. FARTHER_TAIL near-missed
(MRE=0.215 vs threshold=0.20, within the 1.5× near-miss band).

The judge correctly scored 73 with explicit reasoning citing the `[near_miss
— REFINE this form, do not redesign]` tag from Bug #18, identifying the
high-d regime as the refinement target.

Then `🚫 Holdout hard-gate FIRED (harness error): score 73 → 0`.
A *legitimate near-pass got zeroed by the apparatus*.

### Root cause — two compounded problems

1. **Gate-harness output shape divergence.** The legacy hard-gate code at
   `test_thesis.py:2337-2395` expected `{harness_ok, gates: [...]}`. The
   GP-156-shape harnesses (gp154, gp155) emit `{holdout: {passed,
   near_miss}, farther_tail: {...}, all_gates_pass, any_near_miss}`.
   When the harness raises `AssertionError` after printing JSON (returncode
   nonzero, but stdout has parseable JSON), the legacy code went to the
   "harness error" branch and zeroed the score, never parsing the JSON.

2. **No near-miss awareness in the hard-gate.** Even when the JSON parsed
   correctly, the rule was "any gate failed → score 0". The hard-gate is
   NAMED `holdout_hard_gate` but applied as `any_gate_hard_gate`. A
   FARTHER_TAIL near-miss on an otherwise-passing HOLDOUT zeroed the
   score the judge had carefully calibrated.

### Fix shipped (Bug #21)

`test_thesis.py:2337-2470` now:
- Tries to parse stdout JSON regardless of returncode (Bug #16-style:
  the harness may print valid JSON before raising AssertionError)
- Translates GP-156-shape harness output (`{holdout, farther_tail,
  all_gates_pass}`) into the legacy `{harness_ok, gates: [...]}` shape
  in-flight, preserving `near_miss` per gate
- Refined hard-gate semantics:
  - HOLDOUT hard-miss → score 0 (unchanged)
  - HOLDOUT near-miss → floor at 30 (model is structurally close)
  - HOLDOUT pass + FARTHER_TAIL/asymptotic fail → keep judge score
    (judge has already calibrated per Bug #18 prompt addendum)

### What this is the symptom of (architecture lesson)

This is the THIRD instance today of the same architectural smell:

| Bug | Where | Smell |
|-----|-------|-------|
| #11 | autoresearch_loop:4538 | Wire-in nested inside wrong rubric flag → unreachable |
| #16 | gate_harness per-project | Per-row crash silenced as MRE=1.0 |
| #21 | test_thesis hard-gate | Output shape divergence + binary semantics |

All three are "two parallel implementations of the same gate concept got
out of sync because there's no shared contract." This is exactly what
the v5.0 substrate-evaluation utility from the previous section is
designed to fix — a single gate-harness output schema that the hard-gate
code reads through one parser, with explicit near-miss / partial-pass
fields. Each per-project harness becomes an adapter; the parser knows
the canonical shape.

The Bug #21 fix today is a **translation layer** (in-flight conversion
between shapes); the v5.0 fix is **schema unification** (one shape, one
parser, no translation needed).

### Anti-pattern flag for v5.0 implementation

When designing the substrate-evaluation utility, the canonical output
schema MUST include:
- per-gate `passed: bool`
- per-gate `near_miss: bool`
- per-gate `value` + `threshold` (for diagnostic)
- top-level `harness_ok: bool` + `gates: list[...]` (for legacy compat)
- top-level `all_gates_pass: bool`
- top-level `any_near_miss: bool`

The hard-gate code becomes a single fixed parser. New substrates inherit
the schema; the hard-gate doesn't need updating per-substrate.

## K_law budget consolidation — flat-5 → BIC-justified (2026-04-25)

### What this is the third instance of

This is the **fourth** architectural smell flagged in this seam today:

| Bug | Where | Smell |
|-----|-------|-------|
| #11 | autoresearch_loop:4538 | Wire-in nested under wrong rubric flag → unreachable |
| #16 | gate_harness per-project | Per-row crash silenced as MRE=1.0 (hidden failure mode) |
| #21 | test_thesis hard-gate | Output shape divergence + binary semantics |
| **K_law=5** | **fit_primitive_features:307 + multiple rubrics** | **Flat magic number, audit failed to validate (gp152/153 sycophancy loop)** |

All four follow the same architectural anti-pattern: *a number or
mechanism gets calibrated by intuition, copy-pasted across files,
presented as if hardened, and the validation run that was supposed
to certify it failed silently or wasn't actually performed.* The
cumulative cost is high — gp154 lost iters today because gpt-4.1's
5-modality encoding hit the K_law=5 cliff.

### What shipped 2026-04-25

`fit_primitive_features.fit_features` now computes BIC per GP-152
framer spec v2.0:

```
σ̂² = SSE / N
BIC = N · log(σ̂²) + K · log(N)
```

`FeatureFitResult` carries `bic`, `sigma_sq`, `n_fit_rows`, `k_params`.
The 🧮 dispatch banner prints BIC. `fit_features_result.json` exposes
all four fields.

K_law hard ceiling raised from 5 to 8 (with rubric override via
`fit_primitive_features_k_max`). gp154 rubric updated to 8 with
explicit BIC-justification language in the persona.

### What v5.0 Cage Orchestrator must do with this

The `FitEngine` Protocol consolidation must:

1. **Standardize BIC across BOTH 1D and N-D engines.** Today the 1D
   `fit_primitive` has GP-088-style discrete exponent grid search but
   no BIC field on `FitSuccess`. The N-D fitter has BIC but no grid
   search. v5.0 should expose BIC uniformly.

2. **Remove the hard K ceiling entirely** in favor of BIC-only ranking.
   Today's K=8 hard ceiling is a defensive measure against memorization
   on small N. BIC handles this naturally — high K with σ̂² → 0 still
   gets penalized by `K·log(N)` term, AND a model-comparison gate
   should reject if BIC > BIC of a baseline-K model. Hard ceiling
   becomes redundant.

3. **Add baseline-BIC comparison to the engagement loop.** Today the
   judge sees BIC alone without context. v5.0 should compute BIC for
   a K=2 baseline (intercept + linear feature) on the same data and
   pass `BIC_thesis - BIC_baseline = ΔBIC` to the judge. Negative ΔBIC
   = the thesis earned its parameters; positive = the parameters didn't
   pay for themselves.

4. **Inherit GP-152 framer spec v2.0's frame-invariance proof.** The
   feature-vector case is frame-invariance-trivial (no framing transforms),
   but if v5.0 ever adds feature-frame transforms (e.g.
   `intrinsic_dim_d → log(d)` for resolution-limited regimes), the
   raw-coord BIC formula still works — that's the spec's contribution.

### Postmortem reference

The flat K_law=5 came from an audit that itself failed. See
`research_areas/private/postmortems/gp152_153_ztare_on_ztare_sycophancy_loop_2026_04_25.md`.
The fact that K_law=5 survived for weeks despite a documented audit
failure is exactly the architectural drift the v5.0 Cage Orchestrator
must close: every magic number must have an audit trail, and audits
that fail must invalidate the number, not get silently filed.

## Panel debate — dormant gate triage (2026-04-25 night, post-Phase-3a)

After Phase 1+2+3 modules shipped (substrate_evaluation, fit_engine, cage),
17 dormant gates were inventoried (Class L finding). A 5-perspective panel
(Chaos / Quantum / Physics / Math / CS Software Engineer) evaluated each
for WIRE / RETIRE / CONDITIONAL. Munger synthesis below records final
decisions.

### Per-gate panel verdicts (full transcript)

#### Ansatz Survivor Gate
- Chaos: CONDITIONAL — substrate-agnostic; useful only after Phase C ensembles
- Quantum: WIRE — proof-shortness as Occam selector
- Physics: CONDITIONAL — shortness ≠ structural correctness without invariance pairing
- Math: WIRE — top-K Lean-shortness is real; sub-gates 2/3 honestly deferred
- CS: CONDITIONAL — clobbers compression_results.json; race risk
- **Consensus**: CONDITIONAL — wire only sub-gate 1 behind proof_target flag

#### Asymptotic Claim Discipline
- All 5 perspectives: WIRE
- **Consensus**: WIRE — decisive on 1d_curve + feature_dict; no integration cost

#### Bridge Scope Contract
- Chaos: RETIRE — no chaos signal; pure mutation-discipline
- Quantum: CONDITIONAL — scope hygiene only matters during bridge campaigns
- Physics: RETIRE — no physical content
- Math: CONDITIONAL — brittle blacklist code-smell
- CS: CONDITIONAL — dead unless bridge-discovery active; freeze and stash
- **Consensus**: RETIRE — keep importable, do not register in v5.0 Cage

#### Continuum Limit Gate
- Chaos: WIRE — RMS-chaos-trap precheck (T·λ_max>5) is canonical Lyapunov sanity
- All others: CONDITIONAL — sub-gates 2/3 (BKM/Leray) blocked on PDE substrate
- **Consensus**: CONDITIONAL — wire ONLY RMS-chaos-trap precheck; defer rest

#### Coordinate Invariance Gate
- All 5 perspectives: WIRE (unanimous, highest priority)
- **Consensus**: WIRE — frame-invariance is non-negotiable on 1d_curve / time_series

#### Deterministic Charter Gates
- All 5 perspectives: WIRE
- **Consensus**: WIRE — already foundational; ensure Cage routes 1d+nd_features through it

#### Domain Match Gate
- Chaos: RETIRE — Lean-specific
- Quantum: WIRE — hypothesis-injection detection critical
- Physics: CONDITIONAL — only proof_target
- Math: WIRE — closes silent-narrowing loophole
- CS: CONDITIONAL — regex-based Lean parsing fragile but contained
- **Consensus**: CONDITIONAL — wire on proof_target / feature_dict (Lean) only, not universal

#### Ensemble Ambiguity Gate
- All 5 perspectives: WIRE
- **Consensus**: WIRE — universal; firing depends on Phase C emitting >1 candidate

#### Prompt Leak Audit
- Chaos/Quantum/Math/CS: WIRE; Physics: CONDITIONAL (apparatus integrity not physics)
- **Consensus**: WIRE — meta_audit substrate; mandatory before proof_target / closed_form runs

#### Proof Surveyability Gate
- Chaos: RETIRE — proof-target only
- All others: WIRE
- **Consensus**: WIRE — proof_target substrate; sub-gates 1+2 live, sub-gate 3 deferred

#### PSLQ Falsity Audit Gate
- Chaos: RETIRE — closed-form-constant only
- All others: WIRE
- **Consensus**: WIRE — closed_form_constant; mandatory for PSLQ-derived claims

#### Residual Norm
- All 5: WIRE
- **Consensus**: WIRE — utility, not gate; Cage doesn't register but downstream gates import

#### Semantic Gate Stabilization
- Chaos/Physics/CS: CONDITIONAL; Quantum/Math: WIRE
- **Consensus**: WIRE — universal; foundational self-reference machinery

#### Translation Diff Gate
- Chaos: RETIRE — Lean-translation only
- All others: WIRE
- **Consensus**: WIRE — proof_target; pairs with domain_match

#### Wasserstein Persistence Gate
- All 5: WIRE
- **Consensus**: WIRE — time_series_chaotic; decisive for GP-143/146 program

### Cross-cutting concerns (Munger anti-complexity)

1. **translation_diff + domain_match merge candidate** — both regex-parse Lean
   source. DEFER: keep separate during v5.0; merge later when Lean tooling stabilizes.
2. **proof_surveyability + ansatz_survivor composition** — surveyability filters,
   ansatz_survivor ranks. DEFER: keep both wired during v5.0; fold post-v5.0.
3. **asymptotic_claim_discipline + coordinate_invariance** — orthogonal axes
   (asymptotic = tail; invariance = transform). KEEP BOTH SEPARATE.

### Munger synthesis — final v5.0 decisions

| Gate | Decision | Rationale |
|---|---|---|
| asymptotic_claim_discipline | WIRE | unanimous; no cost |
| bridge_scope_contract | **RETIRE** | 3 perspectives flagged; brittle blacklist; revive when bridge campaigns return |
| continuum_limit | CONDITIONAL WIRE | RMS-trap subgate only; BKM/Leray dormant per PDE roadmap |
| coordinate_invariance | WIRE | unanimous |
| deterministic_charter_gates | WIRE | foundational |
| domain_match | WIRE (proof_target + nd_features) | Lean-only scope per panel |
| ensemble_ambiguity | WIRE | universal |
| prompt_leak_audit | WIRE | mandatory pre-judge for audit substrates |
| proof_surveyability | WIRE | sub-gates 1+2 live |
| pslq_falsity_audit | WIRE | closed_form_constant decisive |
| residual_norm | UTILITY (no Cage registration) | |
| semantic_gate_stabilization | WIRE | universal foundation |
| translation_diff | WIRE | proof_target |
| wasserstein_persistence | WIRE | time_series_chaotic decisive |
| ansatz_survivor | CONDITIONAL WIRE | sub-gate 1 only |

**Net**: 14 WIRE (10 unconditional + 3 CONDITIONAL + 1 utility) + 1 RETIRE.
RETIRE rationale recorded in `DECISION_LOG.md`; module remains importable
for revival when bridge-discovery campaigns return.

### Substrate classes added to `cage.py:VALID_SUBSTRATE_CLASSES`

Panel surfaced three additional substrate classes the original v5.0 spec
missed:
- `proof_target` — Lean / formal-proof substrates (GP-122, GP-139)
- `closed_form_constant` — PSLQ integer-relation discovery (GP-145)
- `time_series_chaotic` — chaotic-dynamics subset of time_series (GP-143/146)

These augment {1d, nd_features, time_series, audit, literature} → 8 total
substrate classes the v5.0 Cage dispatcher routes against.

## 2026-04-25 night — v6.0 → v5.0 scope expansion

**Operator decision**: "V6 needs to be V5". The §8.1 (autoresearch
refactor), §8.2 (docs reform), §8.3 (substrate validator) items
originally deferred to v6.0 are PROMOTED into v5.0 as Phases 4, 5, 6.

**Rationale**: 6,300-line autoresearch_loop.py with 14 scattered dispatch
sites + 150+ GP-NNN artifacts with no central index = mounting drift cost.
v5.0 Cage already has the infrastructure (Cage Protocol + FitEngine +
substrate_evaluation + registry); shipping v6 work INSIDE v5 means each
phase pays off Cage's investment immediately.

**Sequence decided** (Munger ordering: apparatus → docs):
  Phase 1-3b ✅ (already shipped tonight)
  Phase 3c ⏳ Cage authoritative dispatch
  Phase 4 ⏳ orchestrator/ split (atomic commits)
  Phase 5 ⏳ GP-XXX docs reform (gp_index + frontmatter + CHANGELOG)
  Phase 6 ⏳ generate_substrate validator

**Panel review in flight**: 5-perspective OSS-engineering panel
(Torvalds / Knuth / Karpathy / Hickey / Kernighan) launched to refine
the orchestrator split + docs reform proposals. Verdicts will be
appended below when agent completes. Munger synthesis follows.

**Substrate readiness for new sequential runs**: gp159/160/161 migrated
to declare canonical `cage_meta` + `cage_observe_mode=true` so observe-
mode can compare engagement matrices across substrates as they run.
This generates the parity dataset Phase 3c needs to flip observe →
authoritative.

**For gp154/156/158 (already in flight)**: gp154 rubric migrated to
`heterogeneous` + `frame_invariant_y=False` (Class K honest declaration);
others tracked separately.

---

## 2026-04-25 night — Panel debate: Phase 4d substrate-contract-hint A/B/C taxonomy

**Trigger:** gp159 wrong-class regression + iter 3 deferred-`_post_fit_sanity`
metaprogramming → I_model returned NaN → score 0 across iters 1-3 even
after Phase 4d shipped. Operator concern: "are contracts too restrictive?
will the LLM care or just ignore? we have 15 prompt sections."

**Context shipped before debate:**
- Three contracts taxonomized — A (assert-based legacy), B
  (`I_model(features: dict) -> float`), C (`I_model(d: float, params=...) -> float`).
- `select_substrate_contract_hint` resolves B before C; mutually exclusive
  at rubric layer (`cage_meta.class` differs).
- `verify_class_consistency_with_substrate` — filesystem ↔ class
  consistency check (gp159 wrong-class incident structurally prevented).
- `contract_adherence.py` — telemetry detecting 6 violation classes.
- Override classes NARROWED 2026-04-25 night to `{nd_features}` only;
  audit/literature/proof_target previously included was wrong (those
  substrates have entirely different contracts).

**Panel composition (5 experts, agent-simulated):**
1. Compiler / programming-language designer (interface-contract
   precedent — Java interfaces, Rust traits, Protocol-Oriented
   Programming).
2. Prompt engineer (recent LLM behavior research — instruction-following
   degrades with prompt length, position bias, conflicting-instruction
   failure modes).
3. Cognitive scientist / instruction-disambiguation expert.
4. Software architect (Hickey decomplecting, anti-overfitting).
5. Empirical software empiricist (false-positive rate, observability).

### Per-expert verdicts

#### E1 — Compiler / language designer
*Position.* A/B/C taxonomy is **interface-shaped** but not
**interface-typed**. Java/Rust idiom would ship a `Protocol` (PEP 544)
or `abc.ABC` with `I_model_scalar(d, params)` vs `I_model_features(features)`
and let the substrate scaffold inherit. Shipped instead is *prose-injected
typing* enforced post-hoc by regex. Contracts B and C properly orthogonal
at rubric layer; Contract A is the residual default — defined by absence
of B/C plus filesystem state. That is a leaky discriminant.
*Concern.* `verify_class_consistency_with_substrate` does an unbounded
text search on `evidence.txt` for `"Lean"` — substring matches `"cleanly"`,
`"cleanup"`, `"Leans toward"` in evidence prose. **Fix: word-boundary
regex on Lean / PSLQ tokens.**
*Severity.* SHIP-IT-WITH-CAVEATS.

#### E2 — Prompt engineer
*Position.* gpt-4.1 is reasonably good at following position-bias-resistant
instructions in 16k+ contexts; adherence degrades when (a) the contract
block is buried mid-prompt, (b) it conflicts with another section,
(c) framing is *prohibitive* without paired *constructive* skeleton.
The `_I_MODEL_*_CONTRACT_HINT` blocks are well-structured (numbered
shape, code skeleton, FORBIDDEN list, "why this hint is here" provenance)
— exactly the patterns that improve adherence. Risk: section-11-of-15
problem; existing prompt likely contains legacy assert-based template
that this hint contradicts.
*Recommendation.* **Position the contract hint immediately before the
rubric/evidence block (terminal third), not buried in section 11.
Surface a one-line summary at the top: `ACTIVE CONTRACT: C (scalar
I_model)`. LLMs anchor on first + last; give it both ends.**
*Severity.* SHIP-IT-WITH-CAVEATS.

#### E3 — Cognitive scientist
*Position.* When two sources conflict (standard prompt template +
evidence.txt), a well-trained agent looks for *meta-signals* of
authority — explicit precedence statements, recency, specificity. The
mutator with no explicit precedence picks the *more concrete* source,
often evidence.txt because it has actual data. Adding a *third* source
(the contract hint) doesn't necessarily increase confusion — it can
*resolve* it if the third source is explicitly framed as **authoritative
over the other two**. Current hint text does this implicitly but never
says so.
*Recommendation.* **Add one explicit precedence line at the top of each
hint: "This contract supersedes any test_model.py shape described
elsewhere in this prompt or in evidence.txt." Without precedence the
mutator may still average over conflicting sources.**
*Severity.* SHIP-IT-WITH-CAVEATS. One-sentence fix.

#### E4 — Software architect
*Position.* Three contracts is one too many. B and C differ in *first
argument type* (`features: dict` vs `d: float`). A unified contract
`I_model(row) -> float` where `row` is whatever `visible_rows()` yields
would collapse B and C — let the substrate decide whether `row` is
scalar or dict. Contract A is fundamentally different (assert suite,
no fit primitive at all) — a different *programming model*, not a
different contract. Hint code is *somewhat* overfit:
`_post_fit_sanity`, `_validate`, `_sanity_check`, `_verify_assumptions`
hardcoded helper-name list. The next mutator hiding asserts in
`_check_invariants()` evades this.
*Recommendation.* **Replace hardcoded helper-name regex with structural
check: any `def _<anything>(...)` containing `assert` and never called
at module scope or inside I_model body. Generalizes the gp159 lesson
without name-overfitting.** Defer the B/C unification — current taxonomy
is honestly motivated by the actual recurring bug; unifying now risks
paving over a real distinction.
*Severity.* SHIP-IT-WITH-CAVEATS.

#### E5 — Empiricist
*Position.* Telemetry surface is well-designed for low-FP detection —
returns codes, doesn't gate the run, `format_adherence_summary` silent
on adherent iterations. FP risk concentrates in two checks.
(1) `module_level_imodel_call` flags `if __name__ == "__main__":\n    I_model(1.0)`
debug guards which are legitimate. (2) `deferred_assert_helper` fires
on intentionally-disabled scaffolding. A clean gp159 run today logs
`{"adheres": true}` per iter — boring JSONL operator can `jq 'select(.adheres == false)'`
on. Actionable.
*Concern.* **`module_level_imodel_call` doesn't handle `if __name__`
guards. Add an `if __name__` skip.**
*Severity.* NICE-TO-HAVE.

### Munger synthesis (operator-as-multidisciplinary-synthesizer)

**Agreement (4-of-5).** Shipped logic is correct in structure and
motivated by a real failure (gp159). Hint blocks are well-written.
False-positive discipline is good. Ship with refinements; don't redesign.

**Disagreement.** E4 wants B/C unified; E1 + E2 think 3-way split mirrors
real interface-shape distinction worth preserving. E3 is orthogonal —
wants precedence statement regardless of taxonomy.

**On Contracts D/E/F (time_series, closed_form_constant, proof_target).**
Don't add now. **Criterion for adding later:** recurring (≥2 incidents)
class-confusion bug for that substrate type, evidenced in
`contract_violations.jsonl` *or* in postmortem record. Adding speculatively
replicates the gp159 wrong-class regression in reverse.
`verify_class_consistency_with_substrate` already covers them at the
*consistency* layer — enough until evidence forces more.

### Action — five refinements landed 2026-04-25 night

1. ✅ Word-boundary regex on `"Lean"` / `"pslq"` token search (E1) —
   `prompt.py:339, 351`.
2. ✅ Add precedence sentence to both hint blocks (E3) — both
   `_I_MODEL_OVERRIDE_CONTRACT_HINT` and `_I_MODEL_SCALAR_CONTRACT_HINT`
   now open with **"THIS SECTION OVERRIDES ANY test_model.py SHAPE
   DESCRIBED ELSEWHERE."**
3. ✅ Generalize deferred-assert detector beyond hardcoded helper names
   (E4) — `contract_adherence.py:150-153` now checks ANY private helper
   `def _<name>(...)` containing `assert` and uncalled.
4. ✅ Skip `if __name__ == "__main__"` blocks in module-level-call
   detector (E5) — `contract_adherence.py:116-138`.
5. ✅ Position fix (E2) — `active_contract_label()` returns top-of-prompt
   one-liner; `select_substrate_contract_hint` block moved to
   terminal-third (after `style_guide`, before `output_requirements`).
   Implementation: autoresearch_loop.py f-string slot reordered;
   one-line `🛑 ACTIVE CONTRACT: X 🛑` injected near `task_header`.

### Decision criteria for future contract additions

To add Contract D (time_series), E (closed_form_constant), or F
(proof_target):
- ≥2 documented incidents of class-confusion failure for that substrate
  type in `contract_violations.jsonl` OR seam postmortem.
- Panel review of the proposed hint block with the same 5-expert pass.
- Tightening: the `_OVERRIDE_CONTRACT_CLASSES` set must NEVER expand
  speculatively. The gp159 audit/literature/proof_target false-add
  taught this lesson once.

---

## 2026-04-25 night — Panel debate: Phase 4e parallel-mutator skeleton

**Trigger:** Operator question on master-agent parallelization (Gemini Pro
MCTS framing). Module shipped as ADDITIVE skeleton at
`src/ztare/orchestrator/parallel_mutator.py` (174 lines, 18 tests, NOT
WIRED). Pull-forward of GP-060 Parallel Champion Synthesis design.

**Panel composition (5 experts, agent-simulated):**
1. HPC / distributed-systems engineer (kernel-internals patterns).
2. Bayesian inference / MCMC expert.
3. Genetic-algorithm / evolutionary-computation expert.
4. LLM-as-search-engine expert.
5. Empirical software empiricist (cost-benefit).

### Per-expert verdicts

#### E1 — HPC engineer (kernel-internals)
*Position.* Skeleton itself is clean: frozen dataclasses, deterministic
worker_id sort post-completion, per-worker exception capture. Concern
is wire-in. `mutator_fn` in tests has no side effects, but real
`mutate_thesis` writes to `workspace/`, appends to `contract_violations.jsonl`,
evidence files, cost ledgers, possibly `test_model.py` at a fixed path.
Three threads racing on those writers is a corruption ticket.
"Caller bears responsibility for thread-safety" docstring is hand-wave
that, in this codebase, is false. Subprocess.run with shared cwd
pointing at a single `test_model.py` will clobber in <1s
(memory: `feedback_mutator_relative_path_harness_bug`).
*Concern.* **Before wire-in, audit every write target inside the real
`mutate_thesis` → `judge` → telemetry chain. At minimum each worker
needs a `workspace/worker_<id>/` subdir and JSONL appenders need
`fcntl.flock` or per-worker files merged afterward.**
*Severity.* SHIP-IT-WITH-CAVEATS for skeleton. **BLOCKER on wire-in**
until per-worker workspace isolation specified.

#### E2 — MCMC expert
*Position.* Calling this "MCTS" or even "multi-chain" is a category
error. Real parallel tempering uses replica exchange — proposals at
one temperature can swap with another, which is what actually escapes
local minima. Here: K independent one-shot mutator calls, then argmax.
That's a "best-of-K sampler", not a chain. Helps if the mutator's
per-call distribution is genuinely multi-modal and one persona is
closer to the true mode; doesn't help if all three personas concentrate
near the same wrong basin (the GP-149 tail_generalization failure mode).
Personas function as different priors, not different temperatures.
*Recommendation.* **Add a temperature axis crossed with persona —
e.g., (newton, T=0.3), (munger, T=1.0), (engineer, T=0.7). Three
priors at three temperatures dominates three priors at one temperature,
at the same K=3 cost. Consider a cheap "exchange" between iters by
feeding iter-N's runner-up persona to iter-N+1.**
*Severity.* NICE-TO-HAVE. Skeleton is fine; framing is overclaimed.

#### E3 — Genetic-algorithm expert
*Position.* This is **not** an Island Model. Island Model = K
populations evolving in parallel with periodic migration. What's
shipped is K=3 single-individual populations, one generation, then
truncation selection — closer to (μ+λ)-ES with μ=1, λ=3, no
recombination. Crossover for theses would mean: "take rate-law from
worker A and boundary-condition treatment from worker B and synthesize"
— that's the GP-060 *combiner* role, and `pick_best_candidate` does
**NOT** do that. It does argmax. **The decisive component of the
original GP-060 design (the synthesizing combiner) has been silently
dropped in the pull-forward.** Real loss: the combiner is precisely
what addresses GP-060's "dimensional blindness" failure mode.
*Concern.* **`pick_best_candidate` is selection-only. GP-060 memory
explicitly calls the combiner "the decisive new component". Skeleton
docstring does not flag the omission.** Either rename to
`select_best_candidate` and acknowledge the scope cut, or add
`combine_candidates(results, llm_combiner_fn)` as a sibling primitive
before wire-in.
*Severity.* SHIP-IT-WITH-CAVEATS — omission must be explicit in spec;
full GP-060 fidelity can be Phase 4e.2.

#### E4 — LLM-search expert
*Position.* This is the decisive empirical question and the operator
already named it. Engineered persona divergence vs. sampled stochasticity
at T>0 is genuinely unknown for *this* mutator on *these* substrates.
Prior leans toward **sampled stochasticity captures most of the gain
at lower complexity cost**, because LLM persona-prompting tends to
produce surface stylistic differences while leaving the underlying
solution distribution similar — except when personas trigger genuinely
different in-context retrieval (Munger's INVERSION primitive vs. Newton's
continuous-limit prior probably do). Answer is bimodal: personas help
when they switch *which exemplars get retrieved*, not when they switch
*prose register*.
*Recommendation.* **Cheapest discriminating experiment: pick one
substrate where iter-10 stochastic luck broke the ceiling (gp140
Chebyshev). Re-run 5 fresh seeds with (a) K=3 same-persona at T=0.9,
(b) K=3 distinct-persona at T=0.7, (c) K=1 sequential T=0.7 baseline at
3× iter budget. Compare iter-to-first-climb + best-score distribution.
~45 mutator calls × 3 conditions = ~135 calls total. If (b) doesn't
dominate (a), the persona axis is decoration.**
*Severity.* WIRE-AFTER-EXPERIMENT.

#### E5 — Empiricist
*Position.* K=3 = 3× LLM spend per iter, **forever** on any substrate
where it's enabled. Skeleton's opt-in-via-rubric design
(`parallel_mutator_k`) is correct architecturally — default-off prevents
silent 3×. But selection guidance in module docstring is too soft.
"Substrates where local-minimum trapping is the binding constraint" is
not operator-actionable. **GP-149 already produced an empirical taxonomy:**
pivots help on catastrophic_assumption / exhaustiveness_claim /
unverified_bound classes (mean Δ +14.4 / +10.4 / +1.4) and *actively
hurt* on tail_generalization (Δ −0.7). Persona-divergence is
mechanistically closer to a pivot than to a refinement.
*Recommendation.* **Before wire-in, add a hard predicate to
autoresearch_loop: enable `parallel_mutator_k>1` only when the iter-N
weakest-link classifier (`src/ztare/validator/weakest_link_classifier.py`)
returns one of {catastrophic_assumption, exhaustiveness_claim,
unverified_bound}. On tail_generalization, force K=1 or escalate to a
tail-extension primitive. Breakeven gain at K=3: parallel must yield
≥0.4 score-points/iter average advantage to beat 3× iters at K=1.**
*Severity.* BLOCKER on wire-in default; SHIP-IT-WITH-CAVEATS as opt-in
module.

### Munger synthesis

**Agreement (4-of-5).** Skeleton sound as code; blockers all at wire-in
boundary. No expert flags a bug in the 174 shipped lines.

**Disagreement.** E2 thinks framing overclaimed but harmless; E3 thinks
missing combiner is real scope regression vs GP-060; E1 wants per-worker
workspace isolation; E4 wants empirical gate before any wiring; E5 wants
*programmatic* gate (weakest-link class) not *judgment* gate.

**Recommended action: WIRE-AFTER-EXPERIMENT.** Specifically E4's
discriminating experiment is the cheapest decisive test. If
engineered personas don't beat T=0.9 sampling on gp140 replay, the
persona machinery is dead weight; only the parallelism scaffolding is
worth keeping. If they do, layer E5's weakest-link gate on top + E1's
per-worker workspace isolation before flipping any rubric flag to K>1.

**Cheapest experiment to resolve decisive uncertainty.** ~45 mutator
calls on gp140 Chebyshev replay across three conditions. ≤1 day of
compute. Single test discriminates whether persona engineering is a
real axis or theater.

### Action — pre-wire-in checklist (Task #63)

1. ⏳ Run E4 discriminating experiment on gp140 Chebyshev replay.
2. ⏳ If experiment supports persona engineering: implement E1 per-worker
   workspace isolation (`workspace/worker_<id>/` subdirs, JSONL flock or
   per-worker merge).
3. ⏳ Implement E5 programmatic gate: enable K>1 only on weakest-link ∈
   {catastrophic_assumption, exhaustiveness_claim, unverified_bound};
   force K=1 on tail_generalization.
4. ⏳ Restore GP-060 combiner per E3 (or explicitly document scope cut
   in spec).
5. ⏳ Optional E2 enhancement: temperature axis crossed with persona
   (defer until experiment + weakest-link gate land).

DO NOT wire `parallel_mutator_k>1` on by default before all five
land. Default-off is the correct architectural posture; opt-in only.

---

## 2026-04-25 night — Mutator submission persistence (per-iter diagnostic snapshot)

**Trigger:** gp159 contract-confusion debugging surfaced a critical
diagnostic-blindness gap. When an iter scores 0, the apparatus REVERTS
`projects/<slug>/test_model.py` back to the substrate baseline, **erasing
the mutator's actual submission from disk**. Combined with empty
`history/<run_id>_iter*_score_0_*.md` files, postmortem investigators had
**zero ground-truth visibility** into what the mutator wrote.

This forced agents into a guessing loop: read JSONL telemetry, infer the
submission shape, ship apparatus features in response. Six rounds of fixes
shipped during gp159 debugging before the agent finally read
`last_prompt_debug.txt` and identified the actual root cause (substrate
evidence.txt teaching wrong pattern). Multiple unresolved hypotheses about
the mutator's actual code remained UNFALSIFIABLE because the code was gone.

This violates the standing AGENTS.md §5b1 *read-the-data-first reflex* —
you cannot read data that no longer exists.

### Decision

Per-iter mutator submission snapshot is now ALWAYS-ON. Wire site:
`autoresearch_loop.py` immediately after the apparatus writes
`test_model.py` from the mutator's `python_code` (post-R1, post-adherence,
pre-gate-harness). Snapshot lands at:

```
projects/<slug>/workspace/submissions/iter_<NNN>_<UTC>.py
projects/<slug>/workspace/submissions/iter_<NNN>_<UTC>.md
```

The `.py` is the canonicalized python_code (same content the gate harness
ran against). The `.md` is the cleaned thesis text. Iter index is
zero-padded to 3 digits + UTC timestamp without delimiters so files sort
naturally.

### Why ALWAYS-ON, not opt-in

Operator concern: "we are flying blind" surfaced repeatedly during gp159.
A debug flag that defaults OFF means the agent will forget to flip it
when stuck — exactly the moment the data is most needed. Default-ON +
opt-out via `MUTATOR_SUBMISSION_SNAPSHOT=0` (env var) inverts the friction:
silence is opt-in, visibility is the default.

Cost: ~3-10 KB per iter on disk. ZTARE iter rates are O(10/hour) per
project; total cost is trivial vs the diagnostic value.

### Wire site (autoresearch_loop.py near L5340)

```python
# GP-157 v5.0 — per-iter mutator submission snapshot (diagnostic).
# The apparatus may revert test_model.py to baseline on score=0,
# erasing the mutator's actual submission and leaving us blind on
# postmortem. Snapshot the python_code + clean_thesis to
# workspace/submissions/iter_<N>_<utc>.{py,md} so failed iters are
# always inspectable. No-op when MUTATOR_SUBMISSION_SNAPSHOT=0.
if os.environ.get("MUTATOR_SUBMISSION_SNAPSHOT", "1") != "0":
    _submissions_dir = workspace_dir / "submissions"
    _submissions_dir.mkdir(parents=True, exist_ok=True)
    _snap_stem = f"iter_{i + 1:03d}_{iteration_start_utc.replace(':', '').replace('-', '')}"
    (_submissions_dir / f"{_snap_stem}.py").write_text(...)
    if clean_thesis:
        (_submissions_dir / f"{_snap_stem}.md").write_text(...)
```

### How to use

After any run:
```
ls -t projects/<slug>/workspace/submissions/ | head
cat projects/<slug>/workspace/submissions/iter_001_*.py
```

### Stale Makefile-seam observation

There is no dedicated Makefile-discipline seam in
`research_areas/private/seams/` — operator suspected one but it does not
exist. Makefile guidance currently lives:
  - `Makefile help` target (CLI invocation contract)
  - `AGENTS.md §5a` (CLI command discipline — verify against Makefile)
  - This seam (orchestrator-level features that surface as `make` flags)

Decision: do NOT create a Makefile seam. Makefile changes that affect
the orchestrator (like new env vars, new targets) get logged in this
seam alongside the architectural change that motivated them. A
standalone Makefile seam would duplicate without adding signal.

### Links to related discipline

- `AGENTS.md §5b1` — Read-the-data-first reflex (mandatory pre-fix sequence).
- `feedback_read_data_before_guessing.md` — durable memory of the
  gp159-class incident.
- `projects/gp159_retrieval_trap/POSTMORTEM_evidence_template_taught_wrong_pattern.md`
  — the specific incident this snapshot mechanism was built to make
  cheaper to diagnose next time.

---

## 2026-04-25 night — Panel debate: typed Linux-kernel-style mutator-apparatus contract

**Trigger:** Operator request after the gp159 contract-confusion chain
(three incidents in one week — wrong-class migration, evidence template
teaching wrong pattern, gate_harness placeholder bypassing mutator).
*"we need a typified way of dealing with this like in the linux kernel
while harnessing the stochasticity of the llm and not being restrictive."*

**Panel composition (5 distinct experts):**
1. Linux kernel maintainer (uAPI/sysfs/vDSO/seccomp-bpf precedent).
2. Programming language designer (PEP 544 Protocols, Rust traits).
3. AST/compiler engineer (canonicalize-don't-reject pattern).
4. LLM-application engineer (structured-output / FIT_DECLARATION generalization).
5. Empirical software architect (Hickey/anti-overengineering).

### Per-expert verdicts

#### E1 — Linux kernel maintainer
*Position.* Three concurrent contracts (A/B/C) is the symptom of having
no *syscall table*. Linux discipline: one stable ABI per arch, monotonic
numbering, one canonical errno set per syscall, capability bits gating
access. The chaos in `prompt.py` (three textually distinct override
blocks all claiming "I OVERRIDE everything") collapses if you declare
ONE source of truth and generate the rest from it.
*Proposal.* `src/ztare/orchestrator/contract_table.py` with
`SubstrateABI(Enum)` + `ContractSpec` dataclass holding signature,
errno_table, cap_required. Substrate `cage_meta` declares one ABI
number; `verify_class_consistency_with_substrate` becomes the analogue
of `capable()`. evidence.txt Evidence Set D *generated from*
ContractSpec, never authored by hand.
*Severity.* PARTIAL-REWORK-WARRANTED.

#### E2 — Programming language designer
*Position.* Use `typing.Protocol` (PEP 544) but as a **receiver**
contract on the apparatus side, not a requirement the mutator must
inherit. Inheritance leaks structural pressure into LLM output and
kills stochasticity. Structural typing with `@runtime_checkable` is
duck-typing-with-teeth — checked at the boundary, one `TypeError` on
mismatch, no string-matching needed.
*Proposal.* `src/ztare/orchestrator/protocols.py`:

```python
@runtime_checkable
class ScalarModel(Protocol):
    def __call__(self, d: float, params: Mapping | None = ...) -> float: ...

@runtime_checkable
class FeatureModel(Protocol):
    def __call__(self, features: Mapping[str, Any]) -> float: ...

def adapt(module, spec: ContractSpec) -> Callable[..., float]:
    fn = getattr(module, "I_model", None)
    if fn is None: raise ContractError(MISSING_IMODEL, spec)
    if not _matches(inspect.signature(fn), spec.signature):
        raise ContractError(WRONG_SIGNATURE, spec, observed=...)
    return fn
```

Mutator never sees the Protocol; apparatus does. Replaces ~600 LOC of
`contract_adherence.py` regex with ~50 LOC of structural check.
*Severity.* PARTIAL-REWORK-WARRANTED.

#### E3 — AST/compiler engineer
*Position.* Linting-then-rejecting is the wrong end of the loop.
Extend `_ast_check_no_module_level_i_model_call` from a *rejector* to
a *normalizer*. Compiler discipline: lower surface syntax to a
normalized IR, then type-check the IR. Risk: silently rewriting LLM
output can mask scientific errors. Mitigation: log every rewrite;
semantic-affecting violations still raise.
*Proposal.* `src/ztare/fit/canonicalize_test_model.py`:

```python
def canonicalize(src: str, spec: ContractSpec) -> tuple[str, list[Rewrite]]:
    # 1. Strip module-level I_model(...) calls.
    # 2. Hoist module-level asserts → __main__ guard.
    # 3. Verify signature matches spec; if not, ContractError (no rewrite).
```

Pairs naturally with E1's table.
*Severity.* PARTIAL-REWORK-WARRANTED (LAYER 2).

#### E4 — LLM-application engineer
*Position.* Free-form Python + regex linting is exactly what
structured-output / tool-calling APIs eliminated. Mutator should emit
JSON: `{"functional_form": "a*exp(-b*d)+c", "param_priors": {...}, ...}`
— apparatus templates `test_model.py` from it. Five sources of
contradiction collapse to *zero* because the mutator never writes
Python. gpt-4.1 / o3 / Claude all support strict JSON schema; failure
rate ≈ 0%. Cost: lose mutator's ability to write arbitrary scientific
code (piecewise, recursion). Bounded by extending the schema
(`{"form_kind": "piecewise|closed_form|recursive", "branches": [...]}`).
*Severity.* REDESIGN-MANDATORY for declaratively-expressible substrates
(B, C, most A). Keep free-form Python only for `proof_target` (Lean) +
genuine algorithmic novelty.

#### E5 — Empirical software architect
*Position.* Counter the other four — proposed redesigns would NOT have
fixed gp159 unless evidence.txt also gets templated. The
substrate-side issue (hand-authored evidence.txt teaching wrong
pattern) is orthogonal to the apparatus-side issue (Protocol checks).
A Protocol/syscall-table redesign that still draws evidence.txt from
hand-edited markdown has the same five-sources problem with extra
ceremony.
*Counter-test.* Aggregate `contract_violations.jsonl` across next 20
sealed substrates. **If gp159-class incidents recur ≥3 times,
redesign warranted. If they don't, patches + AGENTS.md §5b0/§5b1
sufficient.**
*Severity.* PATCHES-ARE-FINE (conditional on telemetry).

### Munger synthesis (operator-as-multidisciplinary-synthesizer)

**Where they agree.**
1. **Five sources of contradiction is the actual bug**, not "the
   mutator is dumb."
2. **Prose-as-contract is structurally weaker than code-as-contract.**
3. **`evidence.txt` is currently a second source of truth and must
   be generated, not authored**, regardless of which redesign path is
   chosen. (E5 dissents on apparatus-side redesign but agrees on
   evidence-generation.)

**Where they disagree.**
- E1/E2: typed receiver (Protocol + ABI table) — bounds apparatus,
  leaves mutator free.
- E3: canonicalizing rewriter — accept any reasonable Python.
- E4: constrained generator — eliminate Python emission entirely
  for declarative forms.
- E5: status quo + telemetry — until incident rate proves redesign
  is mandatory.

### 2026-04-25 night — Gap closure (Failure Modes 1-6 from panel review)

After Gemini Pro panel verdict on the Ada-style typed contract direction
+ four failure modes, six concrete gaps were identified and shipped:

| Gap | Component | Failure Mode | Status |
|---|---|---|---|
| #1 | sanitize_stderr_for_mutator | F1: Popper leakage | ✅ shipped |
| #2 | ContractSpec.nullable_feature_keys | F2: over-constrained schemas | ✅ shipped |
| #3a | substrate_probe.classify_substrate | substrate identification | ✅ shipped |
| #3b | generate_substrate.py auto-classify | data-driven ingestion | ✅ shipped |
| #3c | verify_class_against_data wired into make seal | SubstrateAmbiguityError | ✅ shipped |
| #4 | verify_convention_bridge_in_form | Class K trap | ✅ shipped |
| #5 | FrozenFittedModel | F3: DAG phase contamination | ✅ shipped |
| #6 | audit must-fail constraint in judge prompt | F4: recursive audit hallucination | ✅ shipped |
| L2 | EvidenceFormat enum + parser registry | typed evidence contract | ✅ Task #71 SHIPPED |
| L1 enforcement | adapt() wired into make seal | Protocol boundary at seal | ✅ Task #71 follow-on |

Tests: 453 passing (was 440 before this gap-closure pass). Arch maps:
119/119 across 10 maps clean. The architecture now has typed contracts
at all four boundaries:
  - mutator → apparatus (L1: SubstrateABI, ScalarModel/FeatureModel Protocols)
  - apparatus → fit dispatch (L70: FitEngine.select_adapter authoritative)
  - data shape → substrate class (Gap #3: data-shape probes)
  - Phase 1 → Phase 2 (Gap #5: FrozenFittedModel handoff)

The remaining boundary — substrate evidence text format — is L2 / Task #71.

### Verdict — LAYERED, NOT EXCLUSIVE

| Layer | Cost | Action | Verdict |
|---|---|---|---|
| **L1** | ~200 LOC, ~1 day | E1 + E2 combined: `contract_table.py` (ABI enum + ContractSpec) + `protocols.py` (PEP 544 Protocols). **Generate evidence.txt Evidence Set D from ContractSpec.** | **SHIP NOW** |
| **L2** | ~400 LOC, conditional | E3's canonicalizing AST normalizer (rewrite, don't reject) | Defer until L1 telemetry |
| **L3** | Substantial | E4's structured-output FIT_DECLARATION generalization | Defer indefinitely |

**L1 is the no-regret move:** shrinks code (~300 LOC across `prompt.py`
+ `contract_adherence.py` + `mutation_suite_guard.py` collapse into
table-driven dispatch), eliminates the five-source failure mode by
construction (one ContractSpec per ABI; evidence.txt generated), and
costs ~1 day. Fund it.

**L2/L3 gated on telemetry.** Aggregate `contract_violations.jsonl` +
`workspace/submissions/iter_*.py` divergence rate across next 10
sealed substrates. ≥3 recurrences → fund L3; ≤1 → L1 sufficient.

### Empirical context for the verdict

**E5's "≥3 incidents → redesign" criterion has already tripped:**
- gp159a (wrong cage_meta.class migration) — apparatus-level
- gp159b (evidence.txt module-level I_model template) — substrate-level
- gp159c (gate_harness.py placeholder bypassing mutator) — substrate-level

Three incidents in one substrate in one week. Patches-are-fine no
longer holds. **L1 ship is empirically justified.**

### Files this touches (L1 only)

- New: `src/ztare/orchestrator/contract_table.py`
- New: `src/ztare/orchestrator/protocols.py`
- New: `src/ztare/orchestrator/render_evidence_template.py`
- (Future shrinks once L2/L3 land): `prompt.py` lines 60-180 → template render call;
  `contract_adherence.py` regex → Protocol checks;
  `mutation_suite_guard.py` lines 95-180 → AST canonicalizer call.
- (Future deletes): hand-authored `evidence.txt` Evidence Set D blocks
  across substrates (replaced by `make seal` template render).

### Tracked tasks

- Task #67 (this debate) — completed.
- Task #68 — make-seal LLM-driven substrate triumvirate consistency
  checker (operator proposal — pairs with L1 to catch divergences L1
  cannot see, like prose-content drift).
- Task #69 — Layer 1 typed-contract refactor (this seam's
  recommended ship).

---

## Deferred follow-ups from 2026-04-25 deep audit (lower priority)

Reference: `research_areas/private/seams/2026_04_25_deep_audit_findings.md`.

### F1 — `validate_substrate_meta` at every Cage entry point
The deep audit flagged silent-default semantics in `check_min_rows_per_category`
(G1): when `substrate.meta` is missing fields, the gate falls back to
permissive defaults rather than failing closed. To prevent silent
mis-engagement on substrates that don't declare their meta block, run
`validate_substrate_meta(meta, required_keys=…)` at every Cage entry
point. Required keys per substrate-class are already in the registry's
contract docstrings; promote them to a runtime check.

### F5 — Cage Phase 3b: ensure no autoresearch_loop callsite reads `run_results` from registry stub callbacks as if they were verdicts
Phase 3b of GP-157 promotes the registry's `run` callbacks from
engagement-sentinel emitters (current state) to actual gate verdicts.
Until that lands, autoresearch_loop callers must not treat
`gate.run(...)` return values as pass/fail signals. The deep audit
flagged this as a gap (G3) — currently safe because no callsite
treats them as verdicts, but a regression risk if a developer adds one
before Phase 3b. **Defensive fix:** make `Gate.run()` return a typed
`EngagementSentinel | GateVerdict` enum with explicit `.is_verdict`
property; any caller treating an `EngagementSentinel` as a verdict
gets a runtime assertion failure with a pointer to Phase 3b.
