# GP-170 — Symbolic Logic Cage (deductive cage on PARAMETRIC_FORM)

> **Seam metadata** · `seam_id:` GP-170 · `track:` engine · `status:` unrecorded · `last_updated:` 2026-05-08


Status: scaffolded (architectural proposal, no implementation yet)
Opened: 2026-04-27
Track: kernel
Related: GP-164 (REFRAME + ANALOGY), GP-167 (SubstrateCritic), GP-169 (Cold-LLM Erdős seed), GP-157 (v5 Cage)

## Trigger

ZTARE's existing gate stack is **statistical and heuristic**:
  - SubstrateCritic infers structural facts from data variance
  - noise_profile classifies residual structure post-fit
  - ANALOGY pulls cross-domain forms from LLM latent space (associative)
  - REFRAME proposes coordinate transforms (LLM-guided geometric intuition)
  - The judge LLM evaluates form quality against rubric prose

**None of these layers does deductive symbolic reasoning.** The mutator can submit a closed-form expression that algebraically violates a substrate's boundary condition, and the apparatus only detects the violation by running the form on data and observing high MRE — costing scipy time and an iter. The iter-7 failure on gp163d is the canonical example: the mutator submitted McGaugh interpolation `y = (x + √(x² + 4cx))/2`, the algebraic structure of which guarantees `y ≥ x` for `x > 0, c > 0`. The substrate's Class C requires `y/x < 1`. **A symbolic boundary check would have rejected the form in milliseconds; instead the apparatus burned an iter discovering it via failed holdout.**

A second class of cost: ANALOGY pulls forms from cross-domain fields. Pulled-form's dimensions may not match the substrate's feature dimensions (e.g. an enzyme-kinetics form applied to a substrate where features are masses + radii — the form may add quantities that aren't dimensionally homogeneous). The current apparatus has no mechanism to enforce Buckingham π / dimensional consistency.

A third class: the mutator periodically submits algebraically-equivalent "new" forms across iters. `c0 · exp(x) · exp(y)` and `c0 · exp(x+y)` are the same form. The apparatus runs scipy on both as if they were distinct candidates.

## Eigenquestion

Can a SymPy / Z3 SMT solver layer be wired into the Cage at the PRE_FIT phase such that:
  (a) Substrate boundary constraints (declared in `cage_meta.algebraic_constraints`) are checked against PARAMETRIC_FORM via algebraic reduction, with form rejection on UNSATISFIABLE before scipy runs.
  (b) Dimensional homogeneity is checked via AST traversal when `cage_meta.feature_dimensions` is declared.
  (c) Canonical-form deduplication prevents redundant fits across iters.

If yes, what's the right SymPy interface, what algebraic-constraint vocabulary does the substrate need to expose, and how does the apparatus avoid the symbolic-engine becoming a Goodhart layer (mutator games the SAT solver)?

## Phase 1 — Boundary-condition cage (highest leverage)

### What changes

`cage_meta` extends with `algebraic_constraints`:

```yaml
cage_meta:
  class: nd_features
  target_convention_homogeneity: homogeneous
  algebraic_constraints:
    - "y >= x"                       # gp163d: MOND y always >= Newtonian x
    - "y > 0"                        # gp163d, gp154: positivity
    - "diff(y, x) >= 0"              # gp163d: monotonicity in x
    - "limit(y, x, oo) / x == 1"     # gp163d: high-x asymptote → Newtonian
```

PRE_FIT phase runs new gate:

```python
# src/ztare/gates/symbolic_logic_cage.py

def check_algebraic_constraints(
    parametric_form: str,
    constraint_strs: list[str],
    feature_keys: set[str],
    parameter_keys: set[str],
) -> tuple[bool, list[str]]:
    """Parse PARAMETRIC_FORM as a SymPy expression. For each constraint,
    construct the implication (form ∧ ¬constraint) and ask Z3/SymPy if
    UNSATISFIABLE. If any constraint is provably violable, return ok=False
    with diagnostic. If all constraints are provably satisfied, return
    ok=True. If symbolic engine times out or returns unknown, return
    ok=True with a 'symbolic_indeterminate' diagnostic (don't block; defer
    to numerical check).
    """
```

The check fires AFTER the mutator submits a form, BEFORE scipy fits constants. Forms that violate boundary constraints get an R1 strike with the symbolic counterexample as the diagnostic.

### Why this works on iter-7

Form: `y = (x + sqrt(x**2 + 4*c*x)) / 2`
Constraint: `y/x < 1` for class C, OR equivalently `y < x`
SymPy step: simplify `(x + sqrt(x² + 4cx))/2 < x`
Reduces to: `sqrt(x² + 4cx) < x` for `x > 0` → `x² + 4cx < x²` → `4cx < 0`
Under domain `c > 0, x > 0`, this is FALSE. So `y < x` is unsatisfiable; therefore `y ≥ x` always; therefore the form cannot fit Class C.

The apparatus would have rejected iter-7 in <100ms, with the R1 strike message: *"PARAMETRIC_FORM algebraically guarantees y ≥ x for c > 0, x > 0 (proof: 4cx > 0 implies sqrt(x² + 4cx) > x). Class C requires y/x < 1 in 12/12 rows. The form structurally cannot satisfy this; choose a form whose algebraic boundary admits y < x."*

That R1 strike forces the mutator to respond architecturally on the same iter. Compare to current behavior: scipy runs to completion, gate harness reports MRE, judge gives weakest_point, next iter starts — 1 iter consumed, 5+ minutes wall-clock.

## Phase 2 — Dimensional consistency cage (Buckingham π)

`cage_meta.feature_dimensions` declares each feature's dimension:

```yaml
feature_dimensions:
  x: "L T^-2"               # acceleration
  y: "L T^-2"               # acceleration
  radius_log10: "log10(L)"   # log-space length
  mass_log10: "log10(M)"     # log-space mass
  gas_fraction: "1"          # dimensionless
  SBdisk_log10: "log10(L M T^-2 / L^2)"  # log-space surface brightness
```

The gate traverses the form's AST. For each binary `+`, `-`, `*`, `/`, `**` it computes the dimensions of left and right operands using `feature_dimensions` for terminals, and propagates. If `+` or `-` operands have different dimensions, fail. If the form's overall dimension doesn't match `cage_meta.target_dimension`, fail.

This catches ANALOGY-induced unit violations from cross-domain pulls.

## Phase 3 — AST canonical-form deduplication

After scipy fit succeeds, compute SymPy `simplify(form)` to canonical form, hash. Store hash + iter in workspace. On subsequent submissions, compare new form's canonical hash against history. If duplicate, log `redundant_form_resubmission` and skip the iter (no scipy re-run, no judge call).

This is purely an efficiency gain; it doesn't change the apparatus's epistemic posture, just prevents wasted compute on equivalent forms.

## Phase 4 — Symbolic limit / asymptotic verification (deferred)

For substrates where the rubric declares asymptotic anchors (gp163d: y → x as x → ∞; gp154: L → E as N, D → ∞), use `sympy.limit()` to prove the form's symbolic limit matches the declared asymptote. Forms that don't symbolically recover the asymptote are rejected, regardless of how well they fit visible data.

This is structurally similar to Phase 1 (boundary-condition cage) but operates on infinite-domain limits rather than finite-domain inequalities.

## Risk catalog

  - **Solver timeout / unknown verdict**: SymPy boundary-checking can be undecidable for highly nonlinear forms. Mitigation: timeout at 5s per constraint; on timeout return `symbolic_indeterminate` and defer to numerical check (graceful degradation, never block).
  - **Mutator gaming the symbolic layer**: a sufficiently capable mutator could write forms that pass symbolic checks but fail numerically. This is a feature, not a bug — symbolic check is necessary, not sufficient. Numerical layer remains.
  - **Constraint declaration burden on operator**: writing algebraic_constraints for each substrate is non-trivial. Mitigation: provide a starter library (`y > 0`, `dimensionally_consistent`, `monotonic_in(x)`) that operators can compose. **CORRECTED 2026-04-27 per Gemini Pro panel review**: SubstrateCritic must NOT autonomously propose constraints derived from visible data for inclusion in `cage_meta.algebraic_constraints`. The earlier suggestion that "if `min(y/x) > 0.1` across visible, suggest the operator declare `y > 0.1·x`" was epistemically lethal: it conflates empirical bounds (data-driven, can be broken out-of-sample) with axiomatic constraints (immutable, follow from declared physical law). Encoding the former as the latter hardcodes the apparatus to reject any form that legitimately breaks the visible distribution out-of-sample. SubstrateCritic surfaces empirical bounds to the operator as **candidate constraints requiring explicit promotion**; they are not auto-applied. Operator-declared axioms in `cage_meta.algebraic_constraints` must carry an explicit `provenance` field (e.g. `"declared_physical_law: y is an acceleration magnitude, hence y > 0"`, `"definitional: gas_fraction = M_gas/M_bary ∈ [0,1] by construction"`). Constraints without provenance are rejected at rubric validation. See §Cross-Seam Collision-3 below.
  - **SymPy as a dependency weight**: SymPy is heavy (~30MB import). Mitigation: load lazily; gate is opt-in via rubric flag `enable_symbolic_logic_cage: true`.
  - **Goodhart at the symbolic layer**: a mutator could write forms designed to pass Z3 but encode nothing. SymPy doesn't validate physics. The numerical + judge layers remain the substantive checks; symbolic is the cheap-rejection prefilter.

## Why this complements GP-169 (Cold-LLM Erdős seed) cleanly

Cold-LLM Erdős = creative leap, breaks home-discipline anchor.
Symbolic Logic Cage = deductive verification, ensures the leap obeys algebra.

Together they form the user's stated principle: *"start with cross-domain creative leaps, bounded by strict mathematical verification."* GP-169 supplies the leap. GP-170 supplies the verification. Without GP-170, the cold-LLM seeds could legitimately propose forms that algebraically violate the substrate's boundaries — as ANALOGY currently can — and the apparatus would only catch the violation via expensive numerical fit. With GP-170, the seeds are filtered through deductive constraints before the iter spends compute on them.

## Open audits

  1. SymPy version pinning: SymPy's boundary-decision logic varies across versions. Pin to a specific SymPy version in requirements.txt; document in spec.
  2. Z3 vs SymPy choice: Z3 is faster on quantifier-free SAT but harder to integrate; SymPy is slower but native Python. Phase 1 ships SymPy; revisit Z3 if performance is binding.
  3. Constraint-vocabulary expansion: which substrate-side constraint patterns generalize? Initial set: positivity, monotonicity, asymptotic limits, sign patterns. Larger vocabulary follows as substrates surface specific needs.

  ## Adversarial blindspots (Gemini Pro panel review, 2026-04-27)

  Two concrete vulnerabilities that turn the cage into a sieve if not addressed at implementation time:

  ### Blindspot A — Python Ternary Parsing Crash (the LLM-bypass channel)

  GPT-5.5 in recent iters wrote forms like `(10.0 if features['system_class'] == 'B' else 1.0)`. Feeding that string directly to `sympy.parse_expr()` raises `SyntaxError` because SymPy's parser does not understand Python inline `if/else` ternaries — it expects `Piecewise` or `Heaviside` constructs. Per the risk catalog above, the gate's graceful-degradation path returns `symbolic_indeterminate` and lets the form through to scipy. **The mutator will accidentally or intentionally discover that ternary syntax is a free pass through the symbolic cage.** Same for `for ... in ...` comprehensions, `lambda` expressions, and any other Python-control-flow construct.

  Mandatory fix at implementation time:
  - Lightweight regex pre-parser that detects Python control-flow keywords (`if`, `else`, `for`, `while`, `lambda`, `yield`) inside the form string. If detected, the gate REJECTS the form with a clear diagnostic naming the offending keyword and pointing the mutator to `where(cond, a, b)` (already in the apparatus's whitelisted primitive set, semantically equivalent to ternary, AST-parseable by SymPy).
  - Alternatively (more permissive): convert ternary syntax to `sympy.Piecewise` via AST rewrite before `parse_expr`. The `where(cond, a, b)` form already does this implicitly; the AST rewrite handles raw Python ternaries. Reject only forms that have ternaries the rewrite cannot handle.
  - Either way, **the gate must explicitly fail-CLOSED on unparseable forms**, not fail-OPEN. The current spec text "graceful degradation, never block" must be revised to "graceful degradation only when the engine returns SAT/UNSAT-undecidable, NOT when the parser cannot ingest the form. Parser failures are fail-closed: the form is rejected as malformed."

  ### Blindspot B — Unstated Domain Assumptions (the complex-number trap)

  SymPy's default symbol declaration `x = Symbol('x')` admits complex values. The proof sketch in §Phase 1 — *"4cx < 0 under domain c > 0, x > 0 is FALSE"* — implicitly assumes `c` and `x` are strictly real and positive. Without explicit declaration, **SymPy's SAT solver will find a complex satisfying assignment (e.g. `x = -1 + 0i, c = 0.5`) and return SATISFIABLE, defeating the cage.** Same issue for `sqrt(x² + 4cx) < x` — over complex domain there's no consistent inequality at all.

  Mandatory fix at implementation time:
  - Symbols MUST be declared with assumptions matching the substrate's INIT_RANGE and feature semantics. For each parameter `p` in `PARAMETER_NAMES` whose `INIT_RANGE` is `(lo, hi)`:
    - if `lo > 0`: `Symbol(p, positive=True, real=True)`
    - if `lo >= 0`: `Symbol(p, nonnegative=True, real=True)`
    - else: `Symbol(p, real=True)` (no sign assumption)
  - For each feature `f` in `referenced_feature_keys`, read `features.feature_dimensions[f]` (or fall back to substrate-class heuristics: `radius_log10` is real, `gas_fraction` is `[0,1]`-bounded, etc.) and emit matching `Symbol(f, …)` assumptions.
  - When dimensions/ranges are not declared, FALL-BACK posture is conservative: assume `real=True` only, do NOT assume positivity. This means some forms that ARE algebraically guaranteed to violate constraints under realistic positive-only domains will pass through. That's acceptable for the fall-back; the operator is responsible for declaring `feature_dimensions` and substrate constraints to harden the cage.

  ### Implementation order revised

  Phase 1 must ship with BOTH the regex-based pre-parser (Blindspot A) AND the assumption-aware symbol-declaration step (Blindspot B). Without either one, the gate is a sieve. Spec §Phase 1 implementation contract is updated accordingly: the `check_algebraic_constraints` function takes `init_ranges: dict[str, tuple[float, float]]` and `feature_dimensions: dict[str, str]` as required inputs, not optional kwargs.

  ### Test cases to ship with Phase 1

  Each test asserts the gate ACCEPTS or REJECTS as labeled.

  - `(10.0 if features['system_class'] == 'B' else 1.0)` → REJECT (regex catches `if`/`else`).
  - `where(features['system_class'] == 'B', 10.0, 1.0)` → ACCEPT (whitelisted primitive).
  - `(features['x'] + sqrt(features['x']**2 + 4*params['c']*features['x']))/2` with constraint `y < x`, `c > 0`, `x > 0` → REJECT (provably UNSATISFIABLE).
  - Same form, no positivity assumptions → ACCEPT with `symbolic_indeterminate` note (fall-back posture; operator should declare assumptions).
  - `sympy.simplify(form)` raises → REJECT as malformed.

## Cross-seam collision review (Gemini Pro panel 2026-04-27)

GP-170 written in isolation collides with GP-169 (Cold-LLM Erdős seed) at three points. Both seams now incorporate the fixes; tracked here for v5 wire-in:

### Collision-1 — Syntax mismatch

GP-169's prompt asks the cold LLM for "Python syntax." Cold LLMs default to `math.exp`, `numpy.log`, list comprehensions, lambdas. GP-170's parser rejects all of those. **Result without fix**: every cold-seed candidate dies at the GP-170 prefilter; iter 1 has no usable seeds.

Fix landed in GP-169 prompt: explicit SymPy-parseable syntax constraint with the bare-function-name vocabulary the apparatus already accepts via `_safe_compile_form`. Cold LLM still has full algebraic vocabulary; only surface syntax is constrained.

### Collision-2 — Buckingham π paradox (cross-domain dimensional violation)

GP-169's purpose: pull forms from biology, economics, statistical mechanics. GP-170 Phase 2's purpose: enforce dimensional homogeneity. **Direct collision**: an enzyme-kinetics form `Vmax · x / (Km + x)` is dimensionally fine when `x, Km` share units, but in an astrophysical substrate where `x` is `[L T⁻²]` (acceleration) the form is meaningless without dimension-bridging free constants. GP-170 Phase 2 would reject every cross-domain seed unless the apparatus understands that cross-domain pulls come with implicit dimension-canceling roles for the free parameters.

Fix landed in GP-170: when Phase 2 dimensional check fails on a form tagged as a cold-LLM seed (the tag is preserved through the briefing chain), the R1 bounce message MUST instruct: *"Dimensional violation detected on a cross-domain seed candidate. Free parameters implicitly carry unit-canceling dimensions. Declare each parameter's dimensional role in the form (e.g. `features['x']/params['Km']` where `params['Km']` is declared with units matching `features['x']`), or resubmit a home-domain form. Bare cross-domain copies will not pass dimensional homogeneity."* This converts the rejection from a hard wall into a constructive R1 retry that asks the mutator to take ownership of dimensional bridging.

### Collision-3 — Empirical vs axiomatic constraint conflation

The earlier risk-catalog suggestion that SubstrateCritic could auto-propose constraints derived from data (`min(y/x) > 0.1` → declare `y > 0.1·x`) is structurally identical to the failure mode the apparatus exists to prevent. Empirical bounds from visible data are not axioms. Encoding them in the symbolic cage hardcodes overfitting. Discovery requires the freedom to legitimately break the visible distribution.

Fix landed in GP-170 risk catalog (now corrected): SubstrateCritic does NOT auto-write SymPy constraints. Empirical bounds surface to the operator as **candidate constraints requiring explicit promotion**. Operator-declared `cage_meta.algebraic_constraints` must carry a `provenance` field naming the source: declared physical law, definitional, or operator-promoted-from-empirical. Constraints without provenance are rejected at rubric validation. The separation principle from paper 5 (distinguish "data shows X" from "X is necessarily true") is enforced at the apparatus layer.

### Implementation order revised again

Phase 1 ships `symbolic_logic_cage.py` with:
1. Regex pre-parser rejecting Python control-flow keywords.
2. Assumption-aware symbol declaration reading INIT_RANGE + feature_dimensions.
3. Provenance-required constraint validation at rubric load time (constraints without `provenance` field are silently dropped with a warning).
4. R1 bounce message templates that distinguish (a) "form has fundamental algebraic violation" from (b) "form is a cross-domain seed needing dimensional bridging" — different prose, different remediation.

Phase 2 (dimensional consistency) ships only AFTER GP-169 is wired and producing seeds, so the cross-seam collision-2 prose is testable end-to-end.

---

## Panel Review (independent adversarial agent, 2026-04-27)

A general-purpose Opus agent reviewed this seam adversarially without knowing about the GP-169↔GP-170 cross-seam paradoxes Gemini Pro had separately identified. The panel produced seven concrete blindspots independently. Logged here verbatim as the debate record.

### Panel Blindspot C — `where(cond, a, b)` is on the AST whitelist but invisible to SymPy

The seam's Blindspot A remediation tells the mutator to "use `where(cond, a, b)` instead of Python ternary." `where` is in `_ALLOWED_FUNCTIONS` (`fit_primitive_features.py:118-137`); `_where` is registered in `_SAFE_NS_BASE`. But `sympy.parse_expr("where(x > 0, a, b)")` produces `Function('where')(x > 0, a, b)` — an *unknown applied function* with no algebraic semantics. Asking SymPy to prove `where(x>0, a, b) >= x` returns UNKNOWN every time. The seam's escape hatch (`symbolic_indeterminate` falls through to numerical) means **the gate becomes a free pass for any form using the apparatus's officially-blessed branching primitive**. The mutator quickly learns: wrap everything in `where(...)` and the symbolic gate goes silent.

**Remediation:** AST-rewrite layer that converts `where(cond, a, b)` → `sympy.Piecewise((a, cond), (b, True))` and `sigmoid(x, c, w)` → closed form `1 / (1 + exp(-(x-c)/w))` BEFORE calling `parse_expr`. Reject any whitelisted-but-not-rewritten function with the same fail-closed posture as Blindspot A.

### Panel Blindspot D — `sigmoid` and `erf` smuggle continuous regime switches past the cage

This compounds C and is the RH-18 attack at continuous scale. Mutator writes `y = base_form(x) + amplitude * sigmoid((x - threshold) / width)`. Sigmoid is bounded [0,1], smooth, infinitely differentiable, visibly innocuous to `simplify()`. For `width → small`, it implements the same hardcoded class-bucketing kernel that R10's `kernel_camouflage_rh18_candidate` flag is built to detect. With `sigmoid` registered as SymPy `Function` symbol with no algebraic content, the constraint `diff(y, x) >= 0` becomes undecidable; gate returns `symbolic_indeterminate`; iter passes. **The seam's claim that GP-170 catches the iter-7 McGaugh case is true; the claim that it generalizes to RH-18 is false.** RH-18 attacks live exactly in the smooth-function regime where SymPy SAT is least useful.

**Remediation:** when `sigmoid`/`erf`/`tanh`/`where` appear with parameters whose `INIT_RANGE` includes `width < 0.05` or `sharpness > 100`, route the form to the existing R10 kernel-camouflage check rather than relying on symbolic SAT. **Symbolic and statistical gates need to be coupled, not stacked-and-hoped.**

### Panel Blindspot E — Goodhart on the constraint declaration: trivial-wrapping satisfies any constraint

The constraint vocabulary listed (`y > 0`, `y >= x`, `diff(y, x) >= 0`) is exactly the vocabulary an adversarial mutator can satisfy by structural wrapping with no informational content:

- `y > 0` → mutator writes `y = exp(arbitrary_form)`. Trivially satisfied.
- `y >= x` → mutator writes `y = x + abs(arbitrary_form)`. Trivially satisfied.
- `diff(y, x) >= 0` → mutator writes `y = integrate(abs(g(x)), x)`. Trivially satisfied.
- `limit(y, x, oo) / x == 1` → mutator writes `y = x + tanh(arbitrary)*decay(x)`. Trivially satisfied with `decay(x) → 0`.

The cage rewards forms that wear the substrate's algebraic skin while the inside is whatever Goodhart ornament the mutator wants. None pass the data, but all pass the gate, and iter compute is still spent. The cage's claim was rejecting in <100ms before scipy; the cage now ADMITS forms that would have failed scipy quickly anyway.

**Remediation:** pair every algebraic constraint with a structural-complexity floor on the inner form (`y = exp(g(x))` only admissible when `g` is not a constant or a single primitive call). Treat trivial-wrapping detection as part of the gate, not a downstream judge concern.

### Panel Blindspot F — `simplify()` latency and per-iter wall-clock budget

The seam mentions 5s timeout per constraint check. There are at least four constraints in the example `cage_meta`. The seam doesn't bound how many forms get checked per iter. `sympy.simplify` on a 10-parameter, 200-character form with nested `exp`/`log`/`sqrt` and 3 piecewise branches is empirically multi-minute. SymPy's `simplify` has no useful early-termination. Phase 4's `sympy.limit(form, x, oo)` is famously susceptible to non-terminating Gruntz-algorithm expansions on forms with mixed `exp(exp(x))` or oscillatory tails. `discovery_class_classifier.py:54-75` catches this with a bare `except Exception` and returns `None` — same fail-open posture.

A stagnated mutator stuck in a basin will resubmit forms that all hit the slow path, multiplying gate-time by 10×. The seam never says: budget, what fires when budget exceeded, how timeout interacts with `dependencies` in Cage topo (R10/R11 wait on this gate; if it stalls, downstream gates starve).

**Remediation:** hard wall-clock budget per iter (15s total for symbolic gate across all constraints), AST-complexity precheck (reject above N nodes before `simplify`), explicit Cage-side handling for "gate budget exceeded" as distinct verdict from `symbolic_indeterminate`. Pin SymPy version, document simplify-latency benchmark.

### Panel Blindspot G — `py_exec` substrates have no PARAMETRIC_FORM string

The seam assumes the form is a Python expression parseable by `parse_expr`. ZTARE has parallel `py_exec` substrate class (referenced in `discovery_class_classifier.py` docstring: "py_exec generators / list comps that aren't pure mathematical expressions") where mutator submits a multi-statement function body. There is no single SymPy expression to check. Current draft would either crash on `parse_expr` (fail-closed, regression on every existing OEIS substrate) or silently return `symbolic_indeterminate` with no operator-visible signal that the cage was disabled, leading to false confidence ("R-symbolic passed!") on substrates where it never ran.

**Remediation:** `symbolic_logic_cage_can_handle` returns `False` with explicit reason when `cage_meta.class` is `oeis_py_exec` or when the form contains AST nodes outside SymPy-supported set. Telemetry MUST distinguish "gate engaged and passed" from "gate refused to engage."

### Panel Blindspot H — Constraint-data divergence when operator's belief is wrong

The seam treats `algebraic_constraints` as ground truth. The data is the actual ground truth. On gp163d, Class C nominally satisfies `y/x < 1` but Class C deprojection is artifact-corrupted. If operator declares `y >= x` based on belief but actual data has `y < x` rows due to artifact, the cage rejects the only forms that fit the data. **Worse than absent**: it ENFORCES a wrong belief and starves the search of forms that would have surfaced the artifact.

**Remediation:** at gate-engagement time, run the declared constraint over the visible data and refuse to engage if the data itself violates the constraint by >5% of rows. Surface high-priority operator alert ("declared constraint disagrees with visible data; cage disabled until reconciled") rather than silently filtering forms.

### Panel Blindspot I — Cage interaction with R8/R10/R11 produces contradictory verdicts

R10's `kernel_camouflage_rh18_candidate` flag fires on per-class Spearman near-zero AND class MRE good. A mutator submits a form that the symbolic cage admits (constraints satisfied) but R10 flags as kernel camouflage. The seam doesn't say which gate's verdict is decisive, what the briefing tells the mutator, or whether R10's diagnostic counts as R1 strike or soft signal. Worse: symbolic gate at PRE_FIT runs *before* R10 has data, so R10's signal can't feed back into symbolic admission within the same iter.

**Remediation:** declare verdict-precedence rule in spec — "R10 kernel-camouflage flag overrides symbolic-cage admission and triggers R1 strike on the next iter's submission." Briefing-prompt provider consolidates symbolic + statistical signals into one reasoned verdict.

---

## Synthesis (operator-facing, Munger-style inversion)

The panel did adversarial inversion on what GP-170 misses. Three principles emerge:

**Principle D — The apparatus's whitelisted primitives are the cage's primary attack surface.** Panel Blindspots C and D together are devastating: `where()`, `sigmoid()`, `erf()`, `tanh()` are all in the AST whitelist (mutators have been told to use them as the canonical branching/smoothing primitives), and SymPy treats them as opaque `Function` symbols with no algebraic content. The cage was designed to enforce algebraic discipline; the apparatus's own grammar makes the cage blind on exactly the constructs the mutator has been incentivized to use. **The cage cannot be a SymPy passthrough; it must include an AST-rewrite layer that maps whitelisted primitives to SymPy's own algebraic objects (`Piecewise`, closed-form sigmoid expansion, etc.) BEFORE invoking `parse_expr`.** Without this rewrite, GP-170 is a sieve at the smooth-function regime — exactly where RH-18 attacks live.

**Principle E — Constraint declaration is itself a Goodhart surface.** Blindspots E and H together: the operator's declared constraints become the new optimization target. Mutators trivially wrap forms to satisfy positivity, monotonicity, asymptotic limits without encoding any informational content. And when the operator's belief is wrong, the cage actively harms discovery by enforcing the wrong axiom. The remediation is dual: (a) structural-complexity floors paired with each constraint (cannot satisfy `y > 0` by writing `y = exp(constant)`), and (b) data-belief reconciliation at gate-engagement time (refuse to enforce a constraint the data itself violates).

**Principle F — Symbolic gate is necessary but not sufficient. Coupling with statistical gates is decisive.** Blindspots D and I both demand cross-gate coupling. The symbolic gate at PRE_FIT cannot see post-fit residuals. R10/R11 at POST_FIT/PRE_JUDGE see residuals but not algebraic structure. Forms that pass the symbolic gate but get caught by R10 produce contradictory signals to the mutator if the apparatus presents them independently. **The brief-rendering layer must consolidate symbolic + statistical signals into one coherent verdict, not stack them as independent flags.**

### Cross-seam paradox triangulation (panel did not see Gemini Pro's three; logged for the record)

The panel reviewed GP-170 in isolation. The three Gemini Pro paradoxes are independent of the panel's seven blindspots:

- **Syntax collision** (cold-LLM seeds use `math.exp`; SymPy parser rejects) — addressed in GP-169 prompt update. Compounds with Panel-C: even if the cold seed produced syntax-clean forms, the `where()`/`sigmoid()` invisibility issue means SymPy can't reason about most apparatus-grammar forms.
- **Buckingham π paradox** (cross-domain forms violate dimensional homogeneity) — independent of panel findings. Now landed in GP-170 R1 bounce message with explicit "dimension-canceling free constants" instruction.
- **Empirical-vs-axiomatic trap** (SubstrateCritic auto-promoting empirical bounds) — independent of panel findings. Strengthens Panel-H: not only can the operator's belief be wrong, the apparatus-side critic can fabricate beliefs from data and elevate them to axioms. Both surfaces require provenance-required declaration.

Both reviewer postures (within-seam panel + cross-seam Gemini Pro) were necessary; neither alone caught all the failure modes. **Future seam reviews must use both postures explicitly: (a) adversarial agent reviewing the seam in isolation, (b) cross-seam-collision review pairing seams that interact at runtime.**

### Implementation priority order

1. **Mandatory before Phase 1 ships (any of these missing turns cage into sieve):**
   - Panel-C + Panel-D fix: AST-rewrite layer mapping `where`/`sigmoid`/`erf`/`tanh` to SymPy `Piecewise` / closed-form expansions BEFORE `parse_expr`.
   - Panel-G fix: explicit `can_handle` returns False on `py_exec` substrates with telemetry distinguishing engaged-and-passed from refused-to-engage.
   - Panel-F fix: hard 15s wall-clock budget across all constraints per iter; AST-complexity precheck; "budget_exceeded" as distinct verdict.

2. **Mandatory before Phase 1 declared production-ready:**
   - Panel-E fix: structural-complexity floor paired with each constraint.
   - Panel-H fix: data-belief reconciliation at gate-engagement (refuse to enforce constraints the data violates).
   - Panel-I fix: R10/R11 + symbolic-cage verdict-precedence rule, briefing-render consolidation.

3. **Phase 2 prerequisites (dimensional consistency):**
   - All Phase 1 items above.
   - GP-169 wired and producing seeds (so Cross-seam Collision-2 prose is end-to-end testable).
   - `cage_meta.feature_dimensions` declaration validation at rubric load time.

The current GP-170 seam is a thoughtful spec but has not yet been implemented. The Phase 1 module (`src/ztare/gates/symbolic_logic_cage.py`) does not exist. **The remediations above are the implementation contract. Without all three Phase-1 items in §1 above, the cage is a sieve and should not ship.**

## Per GP-157 §3a: GP-170 ships Cage-routed

GP-170's symbolic_logic_cage gate ships with `can_handle` predicate reading `cage_meta.algebraic_constraints` (engages when non-empty list declared). No autoresearch_loop direct-wire. Registered with Cage at `build_cage_runtime` initialization, just as R10/R11 are.