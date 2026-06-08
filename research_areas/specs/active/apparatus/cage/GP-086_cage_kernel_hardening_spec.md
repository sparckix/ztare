# GP-086 — Cage & Kernel Hardening: Automated Promotion of Gaming Patterns

## Status

Active — revised 2026-04-18 from three-reviewer panel (gate-design critic, Munger inverter, implementation feasibility)

## Seam

research_areas/private/seams/GP-086_cage_kernel_hardening_seam.md

## Scope

- Phase 0: `evidence_fit` hard CAGE gate (prerequisite for all Phase 1 gates)
- Phase 1: three CAGE gates — `uniqueness_gap`, `parsimony_violation`, `extrapolation_gap` generalization
- Phase 2: two RUBRIC dimension additions — `falsifiability`, `derivation_path`; `gate_provenance` schema update
- Phase 3 and 4 (KERNEL contracts + extractor automation): **deferred** pending Phase 0–2 validation across ≥3 production runs

**Out of scope:**
- `v4_meta_runner` stage gates for hardening projects
- Debate log quality scoring or exclusion logic
- Cross-domain calibration beyond what Phase 0–2 validation produces

---

## Decision

Gaming signals from 1,115 debate logs are promoted into the engine via a two-channel phased plan: CAGE gates in `gate_harness.py` (Phases 0–1) and RUBRIC dimension additions (Phase 2). KERNEL contracts and extractor automation (Phases 3–4) are deferred until the simpler intervention is validated. The plan is deliberately proportionate: the immediate risk (specificity inflation on tacrolimus drug model from missing `uniqueness_gap` gate) can be closed by Phase 0 + Phase 1 item 1. The remaining gates are warranted by measured signal prevalence but are not the blocking concern.

---

## Problem

Gaming signals appear at measurable frequencies across 604 substantive debate logs. The immediate risk is `uniqueness_gap` (12.4% prevalence): before the Tacrolimus domain run, the mutator can assert uniqueness without enumerating rivals, the judge soft-penalizes but does not block, and the paper inherits a false uniqueness claim. Secondary signals (`parsimony_violation`, `extrapolation_gap`) are real but not time-critical.

---

## Why It Matters

| Risk | Consequence | Urgency |
|---|---|---|
| No `uniqueness_gap` gate before Tacrolimus | False uniqueness claim enters drug binding model | **Immediate** |
| No `parsimony_violation` gate | Overfit theses advance without structural penalty | Medium |
| `extrapolation_gap` silently skipped on general domains | Structural laws and curve fits indistinguishable | Medium |
| No `no_structural_progress` kernel contract | 47.7% of debates waste compute (deferred) | Low — defer |

---

## Constraints

- CAGE gates must be deterministic and non-circumventable by mutator reasoning
- Gates must FAIL loudly on absent configuration — no silent defaults (GP-077 precedent)
- KERNEL contracts require stable mutator output format — format not yet formally specified; Phase 3 is deferred until format contract exists
- Extractor state schema changes must be backward-compatible
- All escalation triggers must be extractor-computable; calendar-duration triggers are unenforceable
- **Proportionality constraint (Munger panel):** do not build Phase 3–4 infrastructure until Phase 0–2 are validated across ≥3 production runs and signal drop is measured

---

## Options

| Option | Verdict |
|---|---|
| CAGE only for all signals | Rejected — KERNEL fragility risk for `no_structural_progress` at current mutator format stability |
| RUBRIC only for all signals | Rejected — empirical record shows soft penalties insufficient for 29.3% and 12.4% signals |
| Full 4-phase plan shipped immediately | Rejected — disproportionate; Phases 3–4 add sequential dependency brittleness before Phase 0–2 are validated |
| **Phase 0+1 CAGE + Phase 2 RUBRIC, then pause and measure** | **Accepted** — closes immediate Tacrolimus risk; scales proportionately to evidence |

---

## Recommendation

### Phase 0 — Prerequisite CAGE gate (blocks Phase 1 item 1)

**`evidence_fit` gate in `gate_harness.py`**

Pass/fail criterion (resolved — was Open Question 1):
- Compute `max_abs_residual_normalized` on training data: `max(|predicted - observed| / |observed|)` across all training points
- **Pass:** `max_abs_residual_normalized < 0.15` (configurable via rubric field `evidence_fit_threshold`, default 0.15)
- **Fail:** gate blocks advancement; score capped regardless of judge score
- This reuses the same residual computation infrastructure already present in `gate_harness.py` for `hidden_global_residual` — no new metric infrastructure needed
- Gate fires post-fit (after `fit_primitive` runs), pre-scoring-finalization

**Integration point — engine-level, not per-project (resolved 2026-04-18):**

Gaming patterns are LLM behavioral pathologies, not substrate artifacts. Defenses must be universal. Per-project `gate_harness.py` files contain substrate-specific gates (hidden residuals, peak location checks for that domain's geometry). Global behavioral gates go in a new engine-level module:

- **`src/ztare/validator/global_gates.py`** — execution logic only. The `if/else`, FAIL/penalty code, and gate dispatch live here. No domain knowledge, no hardcoded thresholds.
- **`rubric.json`** — parameters only. Thresholds (`evidence_fit_threshold: 0.15`), region declarations (`farther_tail_region: {...}`), and opt-out flags (`"disable_parsimony_gate": true` with mandatory `"disable_reason": "..."` field). If a gate's config key is absent from rubric.json, the gate FAILs loudly — no silent defaults.

`global_gates.py` is called from `autoresearch_loop.py` after per-project `gate_harness.py` completes, using the same `deterministic_charter_gates` payload pattern. This ensures Tacrolimus and all future projects automatically inherit every GP-086 gate without manual backporting — config drift is architecturally impossible.

Existing per-project `gate_harness.py` files are NOT modified. The two layers are additive: substrate-specific gates (harness) + behavioral pathology gates (global_gates.py).

---

### Phase 1 — CAGE gates (require Phase 0 in place)

**1. `uniqueness_gap` gate → `gate_harness.py`**

- Fires only after `evidence_fit` gate passes (Phase 0 prerequisite)
- **Criterion:** thesis text must enumerate ≥2 rival structural forms that are: (a) distinct from the proposed form by at least one functional family, and (b) explicitly falsified or bounded by the evidence
- **Not satisfied by:** straw men ("no model at all"), trivial parameter variants of the same form, or rivals stated without falsification argument
- **Enforcement:** gate reads thesis text and checks for rival enumeration; if rubric scoring dimension `rival_construction` scores ≥1 (dimension already exists in most rubrics), gate treats rival enumeration as present. If dimension is absent or scores 0, gate applies score cap of 60.
- **Cap, not FAIL:** allows advancement but signals the gap to the judge

**2. `parsimony_violation` gate → `gate_harness.py`**

- **Criterion:** `param_count > evidence_point_count` → apply **−15 penalty** (not FAIL)
- **Resolved fork (was ambiguous in seam):** penalty, not FAIL. FAIL kills legitimate sparse-data domain theses where model complexity is justified by prior theory. Penalty preserves the deterrent while allowing advancement.
- `param_count`: count of free parameters in the fitted expression (from `FitDeclaration.parameter_names`)
- `evidence_point_count`: count of unique (x₁, x₂, ...) input tuples in `evidence.txt`
- Gate fires post-fit; if no `FitDeclaration` is present (fit not attempted), gate does not fire

**3. `extrapolation_gap` generalization → `gate_harness.py` + rubric schema**

- **Rubric schema change required:** add `farther_tail_region` field to `rubric.json` schema (currently absent — hardcoded to gp023 geometry in gate_harness.py)
- `farther_tail_region` format: `{"x1": [min, max], "x2": [min, max], ...}` — per-dimension ranges
- **Absence → loud FAIL** (not silent pass): if `farther_tail_region` is not declared in rubric.json, gate FAILs with explicit message "farther_tail_region not declared — extrapolation validation impossible"
- **Per-dimension overlap validation (resolved — was aggregate in seam):** for each declared dimension, check whether the declared range exceeds the training data boundary by at least one standard deviation of the training spacing. If any dimension is entirely interior to training data, gate emits a warning and degrades to a soft check (not hard FAIL), since some domains have legitimate full-range training coverage.
- Project owners must explicitly opt out by declaring `farther_tail_region: null` with a written justification in the rubric — not by omitting the field

---

### Phase 2 — RUBRIC fixes (prerequisite: `gate_provenance` schema update)

**Schema prerequisite:** Update `sandbox_gaming_state.json` schema in `sandbox_gaming_extractor.py` to include `gate_provenance` field:
```json
{
  "seen_files": {},
  "last_run_utc": null,
  "total_processed": 0,
  "active_gates": {}
}
```
Where `active_gates` maps signal name → `{"gate_type": "CAGE|KERNEL|RUBRIC", "activated_utc": "...", "gate_version": "..."}`. Historical entries backfill with `null` — absence of provenance data is interpretable as pre-gate baseline.

**RUBRIC additions:**
- `specificity_inflation`: add `falsifiability` dimension (0–15 pts) to all rubric templates. Criterion: thesis proposes ≥1 falsifiable prediction with a concrete test that could be run against available evidence. Boilerplate claims ("this would fail if X were true") without a proposed test score 0.
- `derivation_laundering`: add `derivation_path` dimension (0–20 pts) as candidate fix. Each fitted parameter must cite an independent motivation (prior theory, dimensional analysis, or structural argument) rather than pure fit-to-data.

---

### Phases 3–4 — Deferred

**KERNEL contracts** (`no_structural_progress`, `derivation_laundering`): deferred until:
- Phase 0–2 validated across ≥3 production runs
- Mutator output format contract formally specified (currently unstable — expression-class diversity not tracked in `FitDeclaration` schema)
- `gate_provenance` data exists for at least one full signal cycle to calibrate escalation thresholds

**Extractor automation** (Phase 4, PROMOTE/GATE_INEFFECTIVE alerting): deferred. The extractor's `active-gate registry` and rolling-window alerting require `gate_provenance` data that won't exist until Phase 2 has been running for ≥50 debates. Implement as Phase 5 after Phase 2 data exists.

---

## Phase 6 — Cross-substrate generalization (the deferred Phase 3–4 KERNEL-contract path, realized 2026-06-06)

GP-086 hardened ONE substrate (autoresearch) by promoting lexically-mined debate gaming signals into CAGE
gates. The deferred Phase 3–4 ("KERNEL contracts + extractor automation", "`v4_meta_runner` stage gates",
"cross-domain calibration") is now realized as a SUBSTRATE-AGNOSTIC kernel-hardening loop — because a real
laundering escape was found on a second substrate (leanmill) that the autoresearch-only catalog could not
name.

**Trigger.** The leanmill FALSIFY false-statement control caught an instance-shadowing closure: the agent
ADDED `local instance : HAdd α Nat α where hAdd a _ := a` so `∀ n, n = n+1` (verbatim, signature-clean,
`#print axioms` clean) elaborated to `∀ n, n = n` and `rfl` closed it. RCA: syntactic preservation ≠
semantic preservation — the ELABORATION CONTEXT (instances/notation/abbrev/open/set_option) was the
unguarded surface. Specification gaming on an impossible (false) target.

**The generalization (the cross-substrate hardener):** `common/kernel_hardener.py` —
`KernelHardener` protocol (`mine → reproduce → derive_gate → register`) + `GamingVector` (the cross-substrate
catalog entry, **Cage-aligned**: `substrate_class`/`cage_phase`/`gate_name`) + `to_cage_gate` (→ a real
`cage.Gate`; leanmill organs engage at `POST_JUDGE`/`proof_target`, beside the autoresearch gates). Instances:
- `validator/autoresearch_hardener` — CONFORMS this Phase-0–2 GP-086 hardener (the `sandbox_gaming_extractor`
  miner + the CAGE gaming-pattern gates) to the contract (§3b-safe wrap; the extractor + Cage are untouched).
- `leanmill/solver/leanmill_hardener` — the leanmill instance: mines closure certs; derives `cage.Gate`s.

The gaming catalog becomes the **cross-substrate registry** `analytics/public/queries/gaming_vector_catalog.jsonl`
(the 9 numeric `cheating_catalog.md` cheats remain; the registry adds the formal-substrate mechanism-classes).
Per GP-248, MINING may be neural (proposer column); GATES stay DETERMINISTIC; a learned gate is forbidden.

**Gates shipped (leanmill, deterministic):** `statement_integrity` added-core-class-instance leg +
degenerate-signature leg (in-signature `sorry`/admit, Sort/Type conclusion — the binders-after-colon
non-statement); `canonical_reelaboration` (strip added instance/notation/macro/set_option + recompile — the
airtight backstop for the WHOLE context-hijack class), wired into `run_anti_laundering_kernel`
(`ZTARE_CANONICAL_REELAB`, default-on).

**New mechanism-classes to add to the taxonomy** (the numeric 9-cheat catalog structurally cannot name
these): `statement_integrity_drift` (goal-mutation/negation-laundering/parse-degeneracy — GATED), `semantic_degeneracy`
(logical vacuity — advisory-partial via `randomized_differential_probe`; reorder/decorative-binder legs OPEN),
`category_type_smuggle` (RH-13/17/18 — autoresearch numeric), `vacuous_null_via_excluded_vocabulary`
(RH-14 — games the refutation channel; carrier = pos/neg controls through one code path).

**Open (Phase 6 residual):** full Cage routing (leanmill verify dispatches via `cage.dispatch_and_run`
INSTEAD of calling `run_anti_laundering_kernel` directly — staged: `leanmill_cage_gates()` makes the organs
Cage-dispatchable); re-run the adversarial re-mine with a robust schema (the first run's miners failed to
emit StructuredOutput → non-probative empty, NOT catalog-clean); promote semantic_degeneracy +
statement_integrity_drift to first-class catalog categories.

<!-- SPEC_GENERALIZED_CROSS_SUBSTRATE 2026-06-06 -->

---

## Gate Signal Summary

| Signal | Channel | Phase | Criterion | Resolved forks |
|---|---|---|---|---|
| `evidence_fit` | CAGE (prerequisite) | 0 | `max_abs_residual_normalized < 0.15` | Criterion specified; reuses existing metric infrastructure |
| `uniqueness_gap` | CAGE | 1 | ≥2 distinct, falsified rivals; score cap 60 | Cap not FAIL; quality check (not count) |
| `parsimony_violation` | CAGE | 1 | `param_count > evidence_points` → −15 penalty | Penalty not FAIL; FAIL rejected for sparse-data domains |
| `extrapolation_gap` | CAGE | 1 | Per-dimension farther_tail_region validation; loud FAIL on absent field | Per-dimension not aggregate; rubric schema addition required |
| `specificity_inflation` | RUBRIC | 2 | `falsifiability` dimension 0–15 pts | Concrete test required, not boilerplate |
| `derivation_laundering` | RUBRIC | 2 | `derivation_path` dimension 0–20 pts | Candidate — escalate to KERNEL only after Phase 2 data |
| `no_structural_progress` | KERNEL | deferred | — | Deferred: mutator format unstable |

---

## Open Questions (remaining after panel review + Gemini Pro consultation)

1. **`evidence_fit` threshold calibration:** Default 0.15 for `max_abs_residual_normalized` is a proposal, not empirically calibrated. Validate against 3–5 existing passing runs before Phase 0 ships. If >20% of correct-champion iterations would fail at 0.15, raise threshold or make it rubric-configurable only (no engine default).

2. **`uniqueness_gap` rival quality check implementation:** Use option (a) — `rival_construction` rubric dimension score ≥1. Lower fragility than text parsing. If `rival_construction` dimension is absent from rubric, gate treats it as score 0 (rivals absent) and applies cap.

3. **Phase 2 RUBRIC dimensions vs. GP-075:** GP-075 is researching GT-independent rubric criteria (derivation quality, parsimony, falsifiability). GP-086 Phase 2 adds `falsifiability` and `derivation_path` dimensions independently. Before Phase 2 ships, cross-reference GP-075 findings to avoid parallel definitions that diverge. If GP-075 has converged on a dimension definition for either, adopt it rather than defining a new one.

4. **Mutator output format contract for Phase 3 (deferred):** `FitDeclaration` schema needs expression-class diversity tracking before Phase 3 can be scoped. Not a current blocker — Phase 3 is deferred.

<!-- SPEC_REVISED_FROM_DEBATE 2026-04-18 -->
