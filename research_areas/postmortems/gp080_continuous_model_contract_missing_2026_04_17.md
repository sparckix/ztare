# Post-Mortem: GP-080 Missing Continuous Model Contract

**Date:** 2026-04-17
**Agent:** Claude
**Context:** GP-080 Stage 1 run — first continuous_rmse substrate ever executed
**Iterations burned:** 3 (iter 0–2 all scored 0 due to `fail_runtime`)

---

## What Happened

GP-080 (tacrolimus PK) is the first ZTARE substrate using `fit_score_mode=continuous_rmse`. All prior substrates used `discrete_exact`. The run failed repeatedly with `test_model.py does not expose f()` at the gate harness.

The mutator produced valid fit declarations (GP-035 fit primitive returned `SUCCESS` with max residual 0.007), but the `test_model.py` code it wrote had no callable `def f(x1, x2)`. The gate harness crashed on import.

**Root cause:** The prompt contract telling the mutator to write `def f()` only existed inside the `DISCRETE EXACT-MATCH CONTRACT` block, which is gated by `if _fit_score_mode_prompt == "discrete_exact"`. For `continuous_rmse`, no equivalent contract existed. The mutator was never told to write a callable function.

**Why the safety nets failed:**
1. **AST auto-alias** (added earlier this session for renamed-function case): looked for functions with ≥ 2 args. The mutator wrote NO function — only `MODEL_PARAMS` and assertions. Nothing to alias.
2. **Component C check:** loaded `test_model.py` after `_restore_project_state` reverted it to the stub (which has `def f`), so the error message in the log was misleading — Component C was checking the post-revert stub, not the mutator's actual code.

---

## Why This Was Missed Across Multiple Fix Sessions

1. **Session 1 (Component C float fix):** Fixed evidence parsing (`int()→float()`). Correct fix, wrong layer — never touched the prompt path.
2. **Session 2 (AST auto-alias):** Fixed renamed functions (`concentration→f`). Correct fix for a different failure mode — assumed the mutator would write *some* function, just with the wrong name.
3. **Session 3 (Component D var_name threading):** Fixed BIVARIATE_SCALE crash. Correct fix, different layer entirely.
4. **No session traced the prompt path.** The visible symptom (`does not expose f()`) was downstream. Every fix addressed a downstream mechanism without asking: "what does the mutator's prompt actually say for this mode?"

This is the intersection of two existing patterns:
- **Pattern 8 (Prompt render-path trace):** "Before touching any prompt injection, trace the full render path: rubric flag → conditional → assembled prompt, across ALL execution branches." We never traced the continuous_rmse branch.
- **Pattern 11 (Three-item integration check):** "Load one real sample of each input the code will consume in production." We never assembled the actual prompt the continuous_rmse mutator would receive and checked it for completeness.

---

## The Fix (Three Layers)

1. **Prompt contract** (Layer 1 — belt): Added `CONTINUOUS MODEL CONTRACT` block parallel to the discrete one. Tells the mutator to write `def f(x1, x2)` returning float.
2. **AST alias** (Layer 2 — suspenders): Already existed. Catches renamed functions.
3. **Deterministic f() build from fit result** (Layer 3 — Cognitive Gym): If layers 1+2 both fail but the fit primitive succeeded, builds `def f()` from the fit declaration expression + fitted params. The LLM picks the form, SciPy fits the params, the harness builds the callable. This is the separation-of-concerns fix — don't ask the LLM to do what the deterministic sidecar already did.

---

## Structural Lesson

**When a new execution mode is added (new `fit_score_mode`, new `run-mode`, new grammar), the prompt contract completeness check must cover all branches — not just the branch being added, but all existing branches that assume the old mode.**

The discrete contract worked because it was the only mode. Adding `continuous_rmse` as a `fit_score_mode` option without adding a parallel prompt contract created a silent gap that only manifested at runtime.

**The generalized rule:** Every rubric flag that switches a code path should have a corresponding prompt-contract block for each value the flag can take. A `fit_score_mode` that can be `discrete_exact` or `continuous_rmse` needs two prompt contracts, not one plus silence.
