# GP-023 Planck Sandbox 07 — EML Vocabulary Pre-Registration

> **Seam metadata** · `seam_id:` GP-023 · `track:` substrates · `status:` Sealed 2026-04-14. Re-sealed 2026-04-14 after charter-header · `last_updated:` 2026-05-08


**Status:** closed *(inferred 2026-05-08 — needs operator review)*

## Status

Sealed 2026-04-14. Re-sealed 2026-04-14 after charter-header gate-parser bug caught mid-first-run (seal #2), and again 2026-04-14 after charter-contamination leak caught on second attempt's iter 1 (seal #3; see "Second-kill patch note" below). Apparatus cleared. Pre-run smoke gate: PASS.

## Second-kill patch note (2026-04-14, charter contamination)

After the header fix, a second run (`--mutator_model gemini-pro --judge_model gemini`) was started. Iteration 1 produced a candidate that passed **all 9 deterministic gates at machine precision** (`failure_count: 0`, `harness_invoked: True`) with parameters `A=0.9500020, p=2.29999, gamma=0.72000, q=1.29999, offset=0.05999` and the form `A * (phi ** p) / eml((gamma * phi / psi) ** q, math.e) + offset`. Judge score was 83; operator flagged this as implausibly fast.

**Root cause:** `autoresearch_loop.py:1319` reads `project_charter.md` and injects it verbatim as `charter_context` into the mutator prompt (line 1748). The sandbox_07 charter, as authored, contained **four separate ground-truth leaks** visible to the mutator on turn 1:

1. Line 31 — `"required for the depth-1 Planck representation eml((gamma*phi/psi)**q, math.e)"` — leaks the target form under pretext of justifying the `{"e","pi"}` whitelist.
2. Line 50 — `"is algebraically equivalent to A * phi^p / (exp((gamma*phi/psi)^q) - 1) + offset"` — leaks the target form under pretext of stating the Core Question.
3. Line 58 — `Ground truth: (A, p, gamma, q, offset) = (0.95, 2.30, 0.72, 1.30, 0.06)` — leaks the literal target parameter values under pretext of the Identifiability section.
4. Lines 160–163 — worked algebraic derivation of `eml(chi^q, math.e) = exp(chi^q) − 1` under pretext of describing the operator grading protocol.

The mutator did not discover anything. It transcribed the charter. (The killed first run, with claude as mutator, had also transcribed the charter — using `2.718281828459045` as a literal float instead of `math.e`. Same leak, different surface form. That the same exact recovery arose twice under two different mutators on iter 1 is the post-hoc signature of contamination, not of rapid convergence.)

**Fix applied:** charter scrubbed of all four leaks. Mutator-visible sections now state the grammar rules, the enforcement surfaces, the 9-gate battery, and the hardening seam, but neither the target symbolic form, nor the GT parameter values, nor any derivation of the depth-1 representation. The target form and the algebraic-equivalence walkthrough live exclusively in this sealed pre-registration file, which is never loaded by `autoresearch_loop.py`. Construction record (`sandbox_construction_record.md`, audit-only, not loaded) retains the derivation for traceability but is not on the mutator path.

**Lesson (decisive):** any prose in the charter written to *motivate* an enforcement surface, *justify* a whitelist, *explain* a grading protocol, or *state* the Core Question becomes a cheat sheet the moment it mentions the target form. The charter is mutator-visible; it must be treated as adversarial input. Rule: **no GT form, no GT parameter values, and no derivation of the target representation in any file that `autoresearch_loop.py` reads on turn 1.** The charter should describe *that* the target exists and *how* it will be graded, not *what* it is.

This makes sandbox_07 the third seal on the same packet. Two non-diagnostic runs logged; first was the header exact-match bug, second was charter contamination.

## Post-kill patch note (2026-04-14, charter header bug)

An initial run (`--mutator_model gemini-pro --judge_model gemini`) was started and killed at iteration 2 after the operator noticed a score of 75 on iteration 1 with `criteria_failed: ["7_No_External_Domain_Import"]` — rubric criterion 7 explicitly caps the score at 40 on any external domain import, but the judge had not enforced it. Inspection of `latest_eval_results.json` revealed the actual defect was upstream: `score_contract.deterministic_charter_gates.harness_invoked = False`, `declared = 0`. The 9-gate battery was silently disabled.

**Root cause:** `src/ztare/validator/deterministic_charter_gates.py:151` does an **exact string match** on the charter section header: `stripped == "## Deterministic Gates"`. This packet's charter used the header `## Deterministic Gates (9 — identical to sandbox_06)`. The suffix made the match fail; the parser returned an empty gate list; the harness was never invoked; the Meta-Judge became the sole scorer.

**Observed bycatch (informative but non-diagnostic for H-SP2-03):** the iteration-1 candidate recovered the exact ground-truth parameters to six-decimal precision (`A=0.9500020, p=2.29999, gamma=0.72000, q=1.29999, offset=0.05999`) with the model form `eml(chi**q, 2.718281828459045)` — bypassing `math.e` with a literal float (grammar-legal: no `math.*` call in the expression). Had the gates been invoked, the candidate would almost certainly have cleared 9/9 at machine precision. This result is **not** counted as confirmation of H-SP2-03 because the run was pre-reg-invalid (enforcement surface disabled). A clean re-run is required.

**Fix applied:** charter section header changed to `## Deterministic Gates` (exact match). Workspace artifacts, latest/champion JSONs, and contaminated `thesis.md`/`current_iteration.md`/`test_model.py` files all reset to pre-run seed state. Smoke gate re-verified: PASS, 9 gates declared, harness_invoked True, seed fails 9/9 as expected.

**Bycatch to carry forward:** the mutator's literal-float trick (`2.718281828459045` instead of `math.e`) is grammar-legal and cannot be prevented without a per-constant detector. This is not a defect — it produces a numerically equivalent depth-1 Planck denominator. The operator-grading protocol (algebraic equivalence check) should recognize this form as equivalent to `exp(chi^q) - 1` and grade it as `algebraically_equivalent`.

## Purpose

Sandbox_06 proved the **binding-strength claim**: under the full inversion cage with
standard symbolic vocabulary, the mutator recovers the exact v3 ground-truth form
`A*phi^p / (exp((gamma*phi/psi)^q) - 1) + offset` at machine precision in ≤10 iterations.

Sandbox_07 tests **H-SP2-03** — the EML vocabulary axis: with the mutator's nonlinear
primitive set restricted to `eml(x, y) = exp(x) − ln(y)` (Odrzywołek 2026, arxiv
2603.21852), and with everything else held fixed (same ground truth, same evidence, same
9-gate battery, same hardening seam R1–R6), does the mutator still converge on the
correct closed form?

The key pre-registered discriminating question: is `eml(chi^q, math.e) = exp(chi^q) - 1`
reachable at depth 1 in practice under ZTARE gate pressure? The paper claims the EML
basis generates all elementary functions at tree depths ≤4; this sandbox tests the
in-practice depth at which the specific Planck denominator form becomes accessible.

## Experiment Object

Inherited **unchanged** from sandbox_06 (calibration reference frozen at
`projects/gp023_planck_sandbox_06/_frozen_reference/`):

- ground truth: `(A, p, gamma, q, offset) = (0.95, 2.30, 0.72, 1.30, 0.06)`
- evidence surfaces: `evidence.txt`, `evidence_holdout.txt`, `evidence_farther_tail.txt`
  (note: file headers read "SANDBOX 06 v3" — intentional provenance; same generator, same
  GT, same SHA-256 fingerprints as sandbox_06 evidence)
- 9-gate battery with identical thresholds
- hardening seam R1–R6
- fail-closed harness semantics
- GP-035 fit primitive
- cold residual successor mode

**Changed for sandbox_07 only:**

- `fit_expression_grammar: "eml_only"` — fit_declaration expressions may use only
  `eml(x,y)` as nonlinear call; `math.e` and `math.pi` are allowed as pure constants
  (not calls); all other `math.*` calls blocked
- `python_model_grammar: "eml_only"` — `I_model` body may call only `eml(...)`;
  `eml` helper body validated to be exactly `return math.exp(x) - math.log(y)`;
  violations → fail-closed NaN stub before GP-035 runs
- criterion 8 (EML grammar compliance) added to rubric

## Primary Hypothesis (H-SP2-03)

With the EML vocabulary restriction in force, the mutator can still recover the Planck
ground-truth form within the 9-gate battery at machine precision. The Odrzywołek depth-1
representation `eml((gamma*phi/psi)**q, math.e)` for the denominator `exp(chi^q) − 1` is
discoverable under gate pressure within the iteration budget.

## Null Hypothesis

The EML restriction is a binding constraint: the mutator either fails to discover the
depth-1 representation within 10 iterations, or the depth-cap binds and recovery fails
even if the correct form is found structurally.

## Pre-Registered Discriminating Outcomes

- **Outcome A (full success):** All 9 gates pass at machine precision AND recovered form
  is algebraically equivalent to GT via eml compositions. Confirms H-SP2-03.
- **Outcome B (gate pass, form differs):** All 9 gates pass but champion uses a different
  eml-expression that fits the data — informative about gate library cardinality.
- **Outcome C (form match, gate fail):** Correct algebraic structure found but coefficients
  cannot be fit tightly under eml grammar — depth-cap binding.
- **Outcome D (both fail):** Apparatus not sufficient under eml restriction OR enforcement
  defect. Refutes H-SP2-03.

## Enforcement Surfaces (pre-committed)

Two surfaces, both required; both verified prior to sealing:

1. **fit_primitive.py `_validate_expression()`** — `allowed_math_attrs=frozenset({"e","pi"})`,
   `allowed_direct_calls=frozenset({"eml"})` when `eml_only`.
2. **autoresearch_loop.py `_validate_eml_helper_body()` + `validate_python_model_grammar()`** —
   AST-walks `I_model` FunctionDef (rejects any non-`eml` call), AND validates the module-level
   `eml` helper body is exactly `return math.exp(x) - math.log(y)` (leading docstring
   permitted, nothing else).

Both surfaces patched and adversarially tested (10 cases) on 2026-04-14 after two
enforcement gaps were found in pre-seal review:
- BLOCKER (closed): eml helper body was not validated; mutator could smuggle nonlinearity.
- HIGH (closed): `math.e` was blocked; depth-1 Planck representation was unreachable.

## Iteration Budget

Hard cap: **10 iterations**.

## Pre-Run State (committed)

Seed `test_model.py` is a naive power law `A*(phi**n)*psi + c`. Grammar-valid (no `math.*`
in `I_model`). Expected gate result: 9/9 FAIL. Smoke gate: PASS (verified 2026-04-14).

## Anti-Overfitting Rule

This packet is interpretable as testing H-SP2-03 only if the EML vocabulary change is the
sole causal delta relative to sandbox_06. Forbidden:

- new gate thresholds
- new evidence surfaces
- carry-over of evolved sandbox_06 thesis text or mutated `test_model.py`
- loosening of harness semantics

## Grading Protocol

**Automated:** 9-gate battery — identical thresholds as sandbox_06.

**Manual (post-run operator):** Algebraic equivalence check — does the champion's
eml-expression reduce to `A * phi^p / (exp((gamma*phi/psi)^q) - 1) + offset`?
Specifically: is `eml((gamma*phi/psi)**q, math.e)` recognizable as the Planck denominator
at depth 1? Grading verdicts: `algebraically_equivalent` / `gate_passing_alternative` /
`depth_cap_binding` / `failed`.

## Success Band

Counts as confirmation of H-SP2-03 if both:
1. All 9 gates pass at machine precision (max_abs_residual < 0.05, etc. per charter), AND
2. Operator algebraic-equivalence check returns `algebraically_equivalent`.

Partial credit (informative negative): gates pass but algebraic form differs (Outcome B).

## Failure Band / Refutation Condition

H-SP2-03 is refuted if Outcome D: gates do not clear at machine precision under a valid
run with the committed iteration budget and enforcement surfaces active.

## Invalid / Non-Diagnostic Outcomes

- smoke gate failure before run
- enforcement surface disabled or bypassed
- provider fallback to a different model family mid-run
- operator reads sealed holdout evidence before run

## SHA-256 Fingerprints (sealed state, 2026-04-14)

| File | SHA-256 |
|------|---------|
| `rubrics/gp023_planck_sandbox_07.json` | `4bf30d92facf64c5540d5243df12b76ab8f203ab6835ca115ccc0cb3c06c19ae` |
| `projects/gp023_planck_sandbox_07/project_charter.md` | `76f28367380ebe8ef62e103d52c9751cce199f4eba8ebc09230faca127bafc1e` |
| `projects/gp023_planck_sandbox_07/sandbox_construction_record.md` | `60c8e85b6df179286e4b9a9ca19b5761be7e714fb09a840c64fa5e5d2582b062` |
| `projects/gp023_planck_sandbox_07/test_model.py` | `b4e8de8897beab31bfbbf56aaed91424a44f9cd52f07b8af5f8a191b9ab1f5c6` |
| `projects/gp023_planck_sandbox_07/evidence.txt` | `5c42891df802828d86d1c783449e8fbb7a85b5b1c469cbe44501746e47cc5a50` |
| `projects/gp023_planck_sandbox_07/evidence_holdout.txt` | `11c8fb202c1ab810f33c5e82ed87b4e138ae854bf26c0170cf7835cbaadf93e8` |
| `projects/gp023_planck_sandbox_07/evidence_farther_tail.txt` | `882472ce558c3b14abaf9bab8badc12cf93cb321fdb0e923f5c06f3a3eb7a19d` |
| `src/ztare/validator/autoresearch_loop.py` | `c3a36f6fa3dfd3bfa270c493e1501f09d500b8203dae51f758d9b41a93e82d4c` |
| `src/ztare/validator/fit_primitive.py` | `004c110cda503b32f9885aace2d58c7c56c057898cf4407f4c8322c32decec10` |

Note: `project_charter.md` and `autoresearch_loop.py` / `fit_primitive.py` fingerprints
reflect the post-patch state (two enforcement gaps closed 2026-04-14). The construction
record documents the patch history. The rubric, evidence, and seed `test_model.py`
fingerprints are unchanged from the pre-patch packet.

## Runtime Contract

```bash
python -m src.ztare.validator.autoresearch_loop \
    --project gp023_planck_sandbox_07 \
    --rubric gp023_planck_sandbox_07 \
    --iters 10 \
    --mutator_model gemini-pro \
    --judge_model gemini \
    --deterministic_score_gates \
    --underidentified_after 20 \
    --no_model_fallback
```

Pre-run smoke gate (must pass before starting):

```bash
python projects/gp023_planck_sandbox_07/harness_smoke_gate.py
```
