# GP-162 — Convention Homogeneity Enforcement (3-Layer Design)

> **Seam metadata** · `seam_id:` GP-162 · `track:` engine · `status:` unrecorded · `last_updated:` 2026-05-09


Status: verify
Opened: 2026-04-25
Implemented: 2026-04-25
Track: kernel

## Origin

gp154 scaling-law-exponent substrate mixed separable Kaplan-style and
joint Chinchilla-style exponents without declaring the mixing. The same
nominal quantity (α_N for transformer LMs) disagrees by 3-4× between
conventions (0.076 vs 0.348). The mutator couldn't converge because the
data was silently heterogeneous.

## Proposed 3-Layer Fix

### Layer 1: generate_substrate.py (substrate-side discipline)
- Add `target_convention_homogeneity` field to substrate metadata
- Values: `"homogeneous"` | `"heterogeneous"` | `"not_applicable"`
- Schema validator refuses to ship without declaration
- `"not_applicable"` for substrates without a convention concept (gp155,
  gp077, etc.)

### Layer 2: Cage v5 can_handle (apparatus-side enforcement)
- If `"homogeneous"`: assert all visible rows share fit_convention value
- If `"heterogeneous"`: refuse engagement unless PARAMETRIC_FORM
  references `features['fit_convention']`
- If `"not_applicable"`: no-op (gate does not fire)

### Layer 3: Rubric flag
- `target_convention_homogeneity` in rubric JSON
- Cage reads it at dispatch time
- Required when `enable_fit_primitive_features = true`; optional otherwise

## Epistemic Panel Review (2026-04-25)

### Newton (Parsimony)
The problem occurred once. GP-154 already HAS `fit_convention` as a
feature AND a rubric dimension ("Measurement Uncertainty Accounting"
weight 10%) demanding convention-awareness. The actual failure was the
mutator ignoring both signals. A simpler fix: a single pre-flight
assertion in gate_harness.py that checks whether PARAMETRIC_FORM
references `features['fit_convention']` when that key exists in the
feature vector. One line, one file, zero new schema fields.

**Verdict:** 3-layer design is general infrastructure for a 1-occurrence
problem. Justified only if convention mixing recurs on future substrates.

### Munger (Inversion)
**Bug-causing scenario:** gp155 (synthetic dense substrate) has no
`fit_convention` feature. Under the proposed design, the constructor
must declare `"homogeneous"`. Layer 2 asserts all rows share the same
`fit_convention` value — but gp155 has no such feature. The assertion
either crashes (false positive) or requires a special case for absent-
field, which defeats the purpose.

**Gaming bypass:** A constructor who wants to ship heterogeneous data
declares `"homogeneous"` and assigns every row `fit_convention = "custom"`.
Layer 2 passes. The declaration is self-reported and unfalsifiable.

### Popper (Falsification)
Run gp154 with fix active vs without, same mutator (o3) and judge (o3).
Distinguishing observable: does champion score improve or iter-to-
convergence decrease? If neither changes, the fix added friction without
preventing the failure. If the mutator already ignored the feature AND
the rubric dimension, a cage-level error just shifts failure from "bad
fit" to "refused to engage."

### Engineer (Implementation)
`can_handle` does not exist in the codebase today. 133 rubric JSONs +
28 substrates would break if the field is required-not-defaulted. Most
ZTARE substrates have no convention concept — forcing them to declare
"homogeneous" is semantically vacuous. The real integration point is
autoresearch_loop.py's PARAMETRIC_FORM validation block (lines 2559-
2690), not a new Cage abstraction.

## Design Decision (post-panel)

**Accepted panel recommendations:**
1. Add `"not_applicable"` as a third value (Newton/Munger fix for substrates without conventions)
2. Make the field required only when `enable_fit_primitive_features = true` (Engineer migration fix)
3. Layer 2 checks for feature-key EXISTENCE before asserting homogeneity (Munger crash fix)
4. Layer 1+3 ship now as metadata + rubric field; Layer 2 deferred to Cage v5 `can_handle` implementation

**Rejected panel recommendations:**
1. "Single pre-flight assertion" (Newton's simplest fix) — rejected because the problem WILL recur. gp154 was the first N-D feature-dict substrate; future substrates (gp159-161, real-world cross-study analyses) will face the same convention-mixing risk. General infrastructure is warranted for a class of substrates, not just one instance.

## Implementation Sequencing

1. Substrates gp159/160/161 built and ready (2026-04-25) — can run on current apparatus
2. GP-157 Cage v5 ships (other agent implementing)
3. GP-158 audit validates Cage v5 design (champion 82, 16 iters, 6 defects found)
4. THEN: implement Layers 1-2-3 inside the Cage v5 `can_handle` framework
5. Backtest: re-run gp154 with convention enforcement active

## Debate Log

### Turn 1 (Claude, 2026-04-25)
Proposed 3-layer design. Created tasks #1-3.

### Turn 2 (Bounded Critique Agent, 2026-04-25)
4-persona panel review. Newton: over-engineered. Munger: gp155 crash,
gaming bypass. Popper: need A/B test. Engineer: can_handle doesn't exist,
migration breaks 133 rubrics.

### Turn 3 (Principal, 2026-04-25)
"Should run once Cage v5 is implemented." Accepted deferral. Substrates
gp159-161 proceed independently.

## Implementation (2026-04-25)

Cage v5 shipped with R9 already implemented:
- `cage.py`: `check_target_convention_homogeneity()` lines 205-263, tested
- `cage.py`: `REQUIRED_SUBSTRATE_META_KEYS` includes `target_convention_homogeneity`
- `cage.py`: `VALID_HOMOGENEITY = {"homogeneous", "heterogeneous"}`
- `test_cage.py`: 3 R9 test cases (homogeneous pass, heterogeneous pass/fail)
- `fit_engine.py`: `FeatureVectorFitEngine.can_handle()` calls R9 check

Additional wiring (this session):
- `generate_substrate.py`: writes `target_convention_homogeneity: "homogeneous"` for all generated substrates
- `autoresearch_loop.py`: reads field from rubric, injects convention-awareness prompt context for heterogeneous substrates, logs the flag at dispatch time

## Broader Substrate Construction Lessons (gp159/160/161, 2026-04-25)

The convention-homogeneity problem is one instance of a broader class:
**substrate construction discipline failures that cause silent run failures.**

Failures surfaced during gp159/160/161 runs:
1. **gate_harness.py = test_model.py copy** → infinite import recursion (gate_harness dynamically imports test_model)
2. **cage_meta.class mismatch** → wrong prompt contract injected (nd_features hint on a 1d substrate told mutator to `from features import ...` which doesn't exist)
3. **evidence.txt says "run this command"** → mutator can't execute commands; needs inline data
4. **Code template leaks GT form** → mutator copies template instead of discovering
5. **Global gates not opted out** → `global_extrapolation_gap` hard-zeros score on custom substrates missing `farther_tail_region: null`
6. **gpt-4.1 prose-vs-code mirage** → writes essays about the model instead of Python; o3 mutator required for code generation

All addressed by:
- `scripts/public/validators/validate_evidence.py` (Phase 3.5 in `make seal`)
- Experiment cookbook triumvirate section
- Substrate auto-classifier (`src/ztare/scaffold/substrate_probe.py`)

## Next Action

Verify on next heterogeneous substrate run (gp154 re-run after Cage v5 wiring completes in autoresearch_loop).
