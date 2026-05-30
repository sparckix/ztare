# GP-035 Mutator Fit Primitive Spec

## Status

Active

## Scope

- add a post-LLM numerical fitting step to the mutator loop
- visible-slice data only, mutator-side only
- opt-in via a single rubric flag for slice 1

Does not cover:

- changes to the evaluator, charter gates, judge, or hidden-slice access
- changes to `test_model.py` portability rules (stdlib-only stays)
- judge/auditor calibration for ontology-policing interactions (e.g. Weibull-recognition penalty — separate seam if decisive)
- symbolic regression or form search (the LLM proposes structure; the fitter estimates parameters)
- loop-control consumption of latent distance (GP-034, separate seam)

## Decision

Add an inline post-LLM fitting step to the mutator loop. After the LLM proposes a functional form, a deterministic server-side optimizer fits parameters against the visible-slice evidence and substitutes the result into the candidate `test_model.py` before evaluation. The fitter is opt-in, form-first/fit-second, and writes typed success/failure artifacts to workspace. GP-030 gates stay unchanged.

## Problem

The mutator loop is a text-to-text LLM call with no numerical optimization step. When a project requires a candidate to clear a quantitative residual threshold (e.g. `max |I_obs - I_model| < 0.05`), the LLM must mentally produce parameter values for the functional form it proposes. LLM token-level numerical reasoning consistently lands within ~50% of correct values but not close enough to clear tight residual thresholds.

This was discovered in GP-023 Phase 2 (`gp023_planck_sandbox_02`, iters 1-24): the mutator reached correct functional-form neighborhoods (power laws, composite rationals, Hill-like, additive decompositions) and died at visible-residual `fail_assert` every iteration because parameters were guessed, not fitted. The audit (GP-035 seam Turns 3-4) confirmed Cause 1: no fit primitive exists anywhere in `src/`, no subsystem the mutator can reach performs fitting, the falsification suite is forbidden from fitting at test time, and the mutator loop is strictly prompt -> LLM -> text -> disk -> run.

## Why It Matters

Without a fit primitive, any project with a quantitative residual gate is structurally unable to clear it regardless of how good the LLM's structural proposals are. The mutator produces form without landing parameters. This is not a prompt issue or a model-capability issue — it is a missing operation in the pipeline.

The fix sits upstream of the charter gates and does not weaken them. Principle 5 (enforcement floor must be deterministic) and Principle 12 (improvements must close a named failure class) both hold: the gates stay exactly where they are, and the improvement is that the mutator stops handing them un-fitted candidates.

## Constraints

Five hard design boundaries from seam debate (Codex Turn 4, ratified):

1. **Mutator-side only.** The fitter runs before evaluation and writes hardcoded parameters into the emitted thesis/harness. It must never fit inside `test_model.py`.
2. **Visible-slice only.** The fitter may only consume the same visible evidence the mutator already sees. It must never query hidden holdout data, deterministic-gate payloads, or gate-harness outputs.
3. **Form-first, fit-second.** The LLM proposes structure. The fitter estimates parameters for that declared structure. The fitter is not a symbolic regressor that invents forms.
4. **Auditable return payload.** The helper returns fitted params plus residual stats, preserved in workspace so the mutator cannot silently pretend the fit worked or failed.
5. **No evaluator weakening.** GP-030 stays unchanged. If the fitted candidate still misses residual, it fails.

Two additional tightenings from Codex Turn 6:

6. **Not unconditional.** The fitter runs only when the emitted candidate declares a parseable functional form inside the allowed template sub-language AND the project opts in. No brittle parser failures on non-quantitative projects.
7. **Typed failure artifact on fit failure.** If fit fails and the candidate proceeds with guessed parameters, the failure must be written to a typed workspace artifact (failure class, attempted template, solver diagnostics) that the next mutator prompt can read. No silent helpers.
8. **Typed fit declaration, not free-text inference.** Slice 1 must not try to recover the intended functional form by heuristically parsing arbitrary thesis prose. The candidate must expose an explicit machine-readable fit declaration.

## Options

### Option A — Multi-turn tool use

**Description**

Restructure the mutator into an agentic loop with tool dispatch. The LLM proposes a form, calls a `fit_parameters` tool, reads the result, and decides whether to keep or revise.

**Pros**

- More natural LLM interaction pattern.
- The LLM can react to fit results within the same turn.

**Cons**

- Requires restructuring `mutate_thesis(...)` into an agentic loop — touches mutation contract, pivot selector, style guide injection, test-extraction parser.
- Disproportionate architectural change for a single new operation.

**Verdict**

Rejected. Too large a delta for the first slice.

### Option B — Inline scratchpad (post-LLM deterministic step)

**Description**

Keep the mutator as a single LLM call. Add a deterministic post-processing stage: parse the declared functional form, call `scipy.optimize.curve_fit` server-side, substitute fitted parameters into the candidate `test_model.py`, write success/failure artifacts to workspace.

**Pros**

- Minimal architectural change. The mutator stays single-turn.
- The fit step is deterministic and auditable.
- Residual map injected into next-iteration prompt context gives the LLM diagnostic information without requiring multi-turn interaction.

**Cons**

- The LLM cannot react to fit results within the same turn. If the fit reveals the form is structurally wrong, the LLM discovers this only on the next iteration.
- Requires a parser for functional-form templates.

**Verdict**

Recommended.

## Recommendation

Adopt Option B.

## Implementation Sketch

### Step 1 — Template sub-language and parser

Define a constrained sub-language for functional-form templates expressed as safe Python expressions over the project's independent variables (e.g. `phi`, `psi`) and named free parameters. The parser validates the expression against a whitelist of allowed operations (`+`, `-`, `*`, `/`, `**`, `math.exp`, `math.log`, `math.sqrt`, etc.) and extracts the list of free parameters.

Slice 1 should require the mutator to emit a typed `FIT_DECLARATION` block alongside the thesis / harness payload. Minimum fields:

- `expression`
- `independent_vars`
- `parameter_names`
- `initial_guesses` (optional)
- `bounds` (optional)

The parser must reject:

- expressions that import modules
- expressions with side effects
- expressions that reference variables outside the declared parameter set and independent variables

### Step 2 — Server-side fitter

A function that takes:

- a parsed functional-form template (callable)
- visible-slice data points as `(independent_vars, observed_values)`
- optional initial parameter guesses from the LLM
- optional parameter bounds

And returns a typed result:

**On fit success:**

- fitted parameter values (dict)
- residual summary: max |residual|, mean |residual|, RMSE
- residual map: per-point `(independent_vars, observed, predicted, residual)`

**On fit failure:**

- failure class (e.g. `divergence`, `singular_jacobian`, `parse_error`, `bounds_violation`)
- attempted template string
- solver diagnostics (if available)

Implementation: `scipy.optimize.curve_fit` or `scipy.optimize.least_squares` with bounds. Runs server-side in the mutator process, not inside `test_model.py`.

### Step 3 — Mutator loop integration

After the LLM call and before writing `test_model.py` to disk:

1. Check rubric opt-in flag (`enable_fit_primitive`). If off, skip.
2. Attempt to parse the candidate's declared `FIT_DECLARATION`.
3. If parseable: run the fitter against visible-slice evidence.
4. If fit succeeds: substitute fitted parameters as hardcoded constants in `test_model.py`. Write success artifact to `workspace/fit_result.json`.
5. If fit fails: proceed with the LLM's original guessed parameters. Write failure artifact to `workspace/fit_result.json` with typed failure class, attempted template, and solver diagnostics.
6. If not parseable: proceed unchanged. Write a `parse_failure` artifact to `workspace/fit_result.json`.

The `workspace/fit_result.json` artifact is injected into the next iteration's mutator prompt as part of the evidence/history context, alongside the residual map on success.

### Step 4 — Opt-in flag

Add `enable_fit_primitive: true/false` to the rubric schema. Default: `false`. This is the single source of truth for slice 1. The flag is a temporary scaffold — once verified on the 3b substrate-swap and any follow-on, the default should flip to `true` for all projects with numerical discriminators.

### Step 5 — Residual map injection

On fit success, the residual map (per-point table + summary stats) is formatted as a compact table and appended to the mutator prompt's evidence section for the next iteration. This gives the LLM diagnostic visibility into where the form breaks without requiring multi-turn interaction. The map uses only visible-slice data (constraint #2).

## Open Questions

- What is the right initial-guess strategy when the LLM's guessed parameters are not explicitly extractable from the response? Default to `curve_fit`'s own initial-guess heuristic, or require the LLM to declare initial guesses as part of the template sub-language?
- Should the fit primitive have a timeout? A badly conditioned problem could hang `scipy.optimize`. Lean: yes, a conservative timeout (e.g. 10 seconds) with `timeout` failure class on expiry.
- Should the residual map be injected into every subsequent iteration's prompt, or only the immediately following one? Lean: only the next iteration, to avoid prompt bloat.
- Should the fitter's parameter bounds be derived from the charter's stated constraints, or should they be a separate declaration? Lean: separate declaration in the template sub-language, to keep the fitter decoupled from charter semantics.

## Review Notes

### 2026-04-12 01:19:47 EDT — Codex

Option B is the right first slice and the spec is close, but two corrections are decisive:

1. **Typed declaration required.** Do not parse arbitrary prose or recover the intended form from free text. Slice 1 should require an explicit `FIT_DECLARATION` block so the fitter contract is auditable and non-brittle.
2. **One opt-in source of truth.** Use the rubric flag only for slice 1. `rubric-or-charter` is ambiguous and will create drift between configuration surfaces.

With those corrections, the spec is strong enough to proceed to implementation debate after the 3b verifier is approved.

### 2026-04-12 12:40:06 EDT — Codex

One additional contract clarification surfaced during 3b:

- the fit primitive should be specified at the **schema** level
- not at the level of a sandbox-shaped model-function signature

Concretely, the stable slice-1 contract is:

- typed `FIT_DECLARATION`
- exact `MODEL_PARAMS` key matching for substitution
- no requirement for a fixed function name like `I_model(...)`
- no requirement for project-specific variable names like `phi, psi`

Reason:

- the fitter consumes `FIT_DECLARATION`
- substitution consumes `MODEL_PARAMS`
- neither component needs a fixed function-name or argument-name convention

So the prompt/API boundary should stay:

- generic
- schema-driven
- reusable across numerical projects

and should avoid leaking verifier-specific shape into the kernel contract.

### 2026-04-12 13:11:05 EDT — Codex

One live verifier correction should now be treated as part of the slice-1 contract:

- the GP-035 prompt contract must be present whenever `enable_fit_primitive = true`
- it must **not** be conditional on there already being a prior `fit_result.json`

Reason:

- a first attempt with no previous fit artifact still needs to know that `FIT_DECLARATION` is mandatory
- prior fit feedback is optional state, not the thing that turns the contract on

So the implementation rule is:

1. unconditional fit-contract injection when the rubric flag is enabled
2. optional previous-fit sub-block when available
3. place the contract close to the active task / weakest-link section rather than burying it in passive context
