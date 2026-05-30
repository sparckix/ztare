# GP-078 — Component D: Topology Synthesizer via AST Composition

## Status

Active — spec revised 2026-04-17 from converged spec-review debate (Turns 7-11)

## Seam

research_areas/private/seams/GP-078_component_d_topology_synthesizer_seam.md

## Scope

- AST composition grammar (NEST, CONVOLVE, DERIVE, COMPOSE) and its four typed operations
- Failure Packager: reads `structural_memory.json` after library exhaustion, emits a typed `FailurePackage`
- AST Composition Mutator: constrained LLM prompt consuming the `FailurePackage`, outputting a JSON composition command
- Library Compiler: deterministic Python compiler that translates composition commands into new `FitDeclaration` entries and registers them in `structural_memory.json` with provenance
- Integration with existing `fit_primitive.py` (AST whitelist, `curve_fit` pipeline), `structural_memory.py` (family fingerprinting, deduplication), and holdout gate
- Three typed wall-exit codes: `WALL_DEPTH_INSUFFICIENT`, `WALL_LIBRARY_INSUFFICIENT`, `WALL_BUDGET_EXHAUSTED`
- PySR benchmark as a required pre-implementation convergence gate (see Implementation Sketch)
- First test substrate: GP-077 OEIS calibration sequences (noiseless, computable generator, known closed forms for benchmark validation)
- **Out of scope:** Multivariate substrates (pharmacokinetics, clinical data) — requires GP-079
- **Out of scope:** Semantic primitive naming / human-readable labels for composed forms
- **RESOLVED 2026-04-18:** Depth-2 composition implemented. After depth-1 LLM-guided rounds: (1) deterministic ratio probes try COMPOSE(X, /, Y) for exponential-family primitives, gated by residual statistics (relative residual + autocorrelation); (2) depth-2 pass composes top-K depth-1 results with base primitives. Cost: K×|bases|×|ops| ≈ 50, not O(5152²). Backtested against Langevin data: best depth-2 form achieves max|res|=0.001 (50× below gate threshold)

## Decision

Component D converts library exhaustion (the Feynman Wall) from a terminal state into a typed intermediate state by composing existing primitives under a strict AST grammar. When the 32-primitive library is exhausted and the holdout gate has rejected all candidates, the Failure Packager identifies the apex loser primitive, computes its pointwise residual over the visible slice, and emits a structured `FailurePackage`. An LLM-guided composition mutator (or, if the PySR benchmark shows evolutionary search is more evaluation-efficient, a PySR-based search strategy using the same compilation target) proposes a typed composition command — NEST, CONVOLVE, DERIVE, or COMPOSE — motivated by residual statistics. The Library Compiler deterministically compiles the command into a new primitive, registers it with full composition provenance, and re-enters it into the normal sweep pipeline. The composed primitive is subject to the same holdout gate as any original primitive; no special treatment is granted. The search strategy (LLM-guided vs. PySR) is the variable component; the Library Compiler, FailurePackage, and provenance infrastructure are durable regardless of which search strategy is adopted.

## Problem

When the current 32-primitive library plus EML grammar is exhausted against a target substrate, ZTARE hits the Feynman Wall: the holdout gate correctly rejects all candidates, structural memory shows full family coverage, and the trajectory extractor emits a thrash constraint. The existing architecture has no next move — it either stagnates or the LLM generates unconstrained free-form math. The unconstrained hallucination path is the GPT-4o failure mode: epicycles rather than laws, thrashing without convergence. The problem is how to extend the engine's own dictionary while remaining inside the zero-trust architecture.

## Why It Matters

Library exhaustion is a predictable event, not an edge case. Any sufficiently novel substrate will exhaust a fixed primitive library. Without a principled next move, ZTARE's discovery claims are bounded by its initial vocabulary. Component D makes the boundary explicit (three typed wall-exit codes) and provides a structured extension mechanism. The typed provenance chain (which primitives were composed, which command, which residual feature motivated it) also makes composed-primitive discoveries auditable — a formula with a derivation history is epistemically stronger than a formula with no composition story.

## Constraints

1. **Zero-trust parity with primary loop:** The composed primitive enters the same holdout gate as any other candidate — no special treatment. Component D inherits the same contamination pathway as the primary discovery loop (visible-slice correlation with holdout); the holdout gate is the same defense. The seam's guarantee is parity, not superiority, with the primary loop's zero-trust posture.
2. **Residual statistics over visible slice only:** The `FailurePackage` residual statistics must be computed exclusively over the visible slice, with no overlap with the holdout region. Implementation must include an explicit check that no holdout-region indices are included in the computation.
3. **No raw data to LLM:** The composition mutator receives the `FailurePackage` (structured residual statistics), not the raw `(n, a(n))` grid. This constraint is decisive for primary law discovery (prevents sequence memorization) and is applied conservatively to composition as well, with acknowledged degradation risk for fine-grained residual structure that summary statistics may not capture.
4. **Deterministic compilation:** The Library Compiler is pure Python with no LLM in the loop. The LLM (or PySR) proposes the composition; the compiler builds and validates it.
5. **Existing AST whitelist governs:** Composed primitives must compile to expressions that pass `_validate_expression` in `fit_primitive.py`. The grammar cannot introduce operations outside the existing whitelist.
6. **Structural memory integration:** Composed primitives must be fingerprinted by `build_structural_family_signature`. Re-proposing an already-tried composition is detected and skipped. Pre-implementation verification required (see Open Questions).
7. **Composition budget:** Maximum composition attempts per wall-hit must be pre-specified, analogous to the GP-075 holdout budget. When exhausted, the engine emits a typed exit code. The depth-1 candidate count is 5,152: 32×32 NEST + 32×32 CONVOLVE + 32 DERIVE + 32×3×32 COMPOSE = 1,024 + 1,024 + 32 + 3,072 = 5,152.
8. **CONVOLVE means Dirichlet convolution:** For integer sequences, CONVOLVE is defined as Dirichlet convolution. Arithmetic (signal-processing) convolution, if needed for a future substrate, is a separate command.
9. **Search strategy is the variable component:** The LLM composition mutator and the PySR-based fallback are alternative search strategies sharing the same Library Compiler and provenance infrastructure. The PySR benchmark determines which is adopted; both paths are valid.

## Options

| Option | Description | Pros | Cons | Verdict |
|---|---|---|---|---|
| **A: LLM-guided AST composition (Component D as specified)** | FailurePackage → LLM prompt → typed JSON composition command → Library Compiler | Leverages LLM's mathematical prior; typed provenance chain; constrained output prevents hallucination | LLM advantage over evolutionary search unproven for genuinely novel substrates; higher per-query overhead than PySR | **Adopt, subject to PySR benchmark** |
| **B: PySR-based composition search with same compilation target** | FailurePackage residual → PySR depth-1 search (same 32-primitive function set) → Library Compiler | Evaluation-efficient on residual signal; no LLM call overhead; fitness-guided exploration is well-characterized | No mathematical prior; no guided feature-to-composition mapping; produces formula without composition motivation reasoning | **Adopt if PySR wins benchmark; Library Compiler and provenance infrastructure are reused** |
| **C: Unconstrained LLM free-form math generation** | LLM generates arbitrary Python math strings on library exhaustion | No grammar engineering required | GPT-4o failure mode: epicycles, no convergence, breaks zero-trust AST whitelist | **Rejected** |
| **D: Halt and report at library exhaustion** | Engine reports exhaustion as terminal failure | Simple; honest scope boundary | Feynman Wall is a predictable event, not an edge case; leaves typed extension mechanism on the table | **Rejected for production; acceptable as fallback when composition budget is exhausted** |
| **E: Pipe into PySR without Library Compiler integration** | Route residual to PySR, use its formula directly | Minimal integration work | No provenance chain; formula not registered in structural memory; breaks fingerprinting and deduplication | **Rejected** |

## Recommendation

Implement Component D with the LLM-guided AST composition mutator as the initial search strategy, **contingent on the PySR benchmark passing**. The benchmark must run before production deployment; if PySR wins on evaluation count (Component D requires more than 2× PySR's evaluations on the GP-077 calibration substrate), replace the LLM composition mutator with a PySR search while retaining the Library Compiler, FailurePackage, and provenance infrastructure unchanged. Interpretability (typed provenance chain) is a property of the Library Compiler and survives regardless of which search strategy is adopted; it is not a sufficient justification on its own if the LLM mutator is strictly dominated on performance.

## Implementation Sketch

### Pre-Implementation Gates (required before code)

**Gate 1 — PySR Benchmark Protocol:**
- Substrate: GP-077 OEIS calibration sequences (known closed forms, noiseless)
- Metric: Total numerical fitting cost, measured as sum of (data_points × parameters) across all fitting calls (including PySR internal fitness evaluations). If PySR internals are not instrumentable, use wall-clock time as primary metric.
- Win condition: Component D (LLM-guided) wins if it reaches a holdout-passing candidate in ≤50% of the evaluations PySR requires on the same substrate. PySR wins otherwise. The 50% threshold accounts for Component D's overhead (FailurePackage construction, LLM call, AST compilation).
- Scope: Depth-1 compositions only; PySR configured with the same 32-primitive function set
- Minimum: 3 substrates where at least one system succeeds; inconclusive substrates (both fail) do not count toward the minimum
- Outcome: Determines search strategy; does not affect Library Compiler or provenance design

**Gate 2 — Structural Memory Fingerprinting Verification:**
Verify that `build_structural_family_signature` (GP-042) produces distinct fingerprints for NEST(A, B), NEST(B, A), and the component primitives A and B individually. If collisions occur, extend the fingerprinting function to include composition provenance (command type + ordered operand fingerprints) in the hash before any composition code is written.

---

### Deliverable 1: Failure Packager

Reads `structural_memory.json` after library exhaustion. Identifies the **Apex Loser**: the primitive family with the smallest `max_abs_residual` among all families that failed the holdout gate (`exact_match_fraction` is a secondary tiebreaker). Computes the pointwise delta between the apex loser's predictions and ground truth over the visible slice only (implementation must verify no holdout-region indices are included).

```python
@dataclass
class FailurePackage:
    apex_family: StructuralFamilySignature
    apex_fit: FitSuccess
    residual_delta: list[tuple[float, float]]   # (input, error) pairs, visible slice only
    residual_statistics: dict                    # mean, std, autocorrelation, sign_change_count,
                                                 # multiplicativity_ratio (see below), sample_n
    exhausted_families: list[str]               # fingerprints of all tried families
    holdout_rejection_summary: dict             # gate metrics from the apex loser
    visible_slice_indices: list[int]            # explicit record of which indices were used
```

**`multiplicativity_ratio`:** For CONVOLVE-Dirichlet detection, compute the mean absolute ratio `|residual(p·q)| / (|residual(p)| · |residual(q)|)` over composite index pairs `(p, q, p·q)` where all three indices are present in the visible slice. Exclude pairs where `|residual(p)| < ε` or `|residual(q)| < ε` (ε = 1e-10). Report `n_multiplicativity_pairs` as the count of included pairs. If `n_multiplicativity_pairs < 5`, mark the ratio as unreliable; the composition mutator must not propose CONVOLVE on an unreliable ratio.

---

### Deliverable 2: AST Composition Mutator

A constrained prompt (LLM path) or PySR invocation (evolutionary path) that accepts the `FailurePackage` and outputs a typed JSON composition command. The four commands and their motivating residual features:

| Command | Semantics | Residual Motivator |
|---|---|---|
| `NEST(A, B)` | Substitute primitive B as argument to A | High sign-change count → periodic residual suggests NEST with trig |
| `CONVOLVE(A, B)` | Dirichlet convolution of A and B | `multiplicativity_ratio` ≈ 1 (reliable sample) |
| `DERIVE(A)` | Forward discrete derivative: `A(n+1) - A(n)` | Residual is first-difference-like (monotonic with step structure) |
| `COMPOSE(A, op, B)` | Arithmetic combination: op ∈ {+, ×, /} | Monotonic growth or multiplicative correction in residual |

LLM output is a JSON AST command, not a Python string. The composition mutator must:
- List exhausted families so the LLM does not re-propose them
- Require the LLM to state which residual statistic motivates the proposed composition
- Validate output against `_validate_expression` before passing to the Library Compiler
- Treat invalid compositions as typed failures (logged, not silently skipped)

---

### Deliverable 3: Library Compiler

Takes a validated JSON composition command and:
1. Compiles it deterministically into a new `FitDeclaration` with correct `independent_vars` and `parameter_names`
2. Runs `curve_fit` on the visible slice via the existing `fit_primitive.py` pipeline. **For DERIVE commands:** uses forward difference `A(n+1) - A(n)`, trims the visible slice by removing the last element, and correspondingly trims the ground truth vector. Must not pass mismatched input/output lengths to `curve_fit`.
3. If fit succeeds on the visible slice, submits to the holdout gate (same gate, no special treatment). **For DERIVE commands:** the holdout gate evaluates on the holdout region minus its last element.
4. Registers the result in `structural_memory.json` with full provenance: `{command, operand_a, operand_b, motivating_residual_statistic, visible_fit_metrics, holdout_outcome}`
5. Assigns the new primitive a monotonically increasing index managed by a counter in `structural_memory.json` (field: `composition_primitive_count`, initialized to 0). New primitive is `Primitive_{32 + count + 1}`. Counter increments after successful registration.

The Library Compiler is the durable component — it is used by both the LLM-guided and PySR search paths.

---

### Wall-Exit Codes

After the composition budget is exhausted (or earlier if criteria are met):

| Code | Criterion | Interpretation |
|---|---|---|
| `WALL_DEPTH_INSUFFICIENT` | Holdout score trending toward threshold across rounds but not crossing; visible-slice fit improving | Composition depth-1 is making progress; depth-2 extension warranted |
| `WALL_LIBRARY_INSUFFICIENT` | Visible-slice fit not improving; no trend in holdout metrics across rounds | Genuinely outside depth-1 composition space of current library |
| `WALL_BUDGET_EXHAUSTED` | Budget hit before trend can be determined | Ambiguous; requires operator judgment; recommend increasing budget or running PySR fallback |

A minimum of 5 composition rounds is required before `WALL_DEPTH_INSUFFICIENT` or `WALL_LIBRARY_INSUFFICIENT` can be emitted. If the budget is exhausted before 5 rounds, emit `WALL_BUDGET_EXHAUSTED` regardless of apparent trend.

**Degenerate case — zero-residual apex loser:** If the apex loser has `max_abs_residual < 1e-10` on the visible slice but fails the holdout gate, the FailurePackage is degenerate (residual delta is vacuous, all statistics are zero/undefined). Emit `WALL_LIBRARY_INSUFFICIENT` immediately without invoking the composition mutator. Record in provenance: `{cause: "overfit_visible_slice", apex_family: ..., holdout_rejection_summary: ...}`.

---

### Integration Points

- `fit_primitive.py` (GP-035): AST whitelist (`_validate_expression`), `curve_fit` pipeline, `FitDeclaration`
- `structural_memory.py` (GP-042): `build_structural_family_signature`, deduplication (requires Gate 2 verification)
- Holdout gate (GP-075): unchanged; composed primitives enter the normal gate
- GP-077 OEIS calibration: first test substrate and PySR benchmark substrate

## Implementation Correction — 2026-04-20

**Bug: Component D / H-GP103-5 seed injection silently discarded by Runner R1**

**Observed:** During gp096_sandbox_19_gagorder (gag order calibration run), H-GP103-5 correctly detected two regime-separated families and wrote additive composite seeds to `composition_seed.json`. Component D then read and injected these seeds. But every injection produced `Runner R1 rejection: Missing required Python falsification suite block` — the composite was never evaluated.

**Root cause:** The seed injection path in PHASE_A of autoresearch_loop.py bypasses `mutate_thesis` entirely (no LLM called). `new_content` was built as `thesis + fit_declaration` with no Python block. `_prepare_mutation_candidate` then calls `validate_python_suite_candidate(None)` which raises `ValueError` → R1 rejection. Layer 3 Mandatory (PHASE_D), which would have built the deterministic `f()` from the `fit_declaration`, never fired because PHASE_B rejected first.

**Diagnosis:** Munger/Karpathy inversion — "why does the system believe no Python block is needed?" Answer: it never asked the LLM. The seed injection path is entirely deterministic; it produces only a `fit_declaration` and expects downstream phases to build the Python. But the downstream validator runs before the downstream builder.

**Fix (autoresearch_loop.py, PHASE_A seed injection block, 2026-04-20):** Append a synthetic loud-fail sentinel Python stub to `new_content` immediately after the `fit_declaration` injection:

```python
"```python\n"
"assert False, 'Component D seed — Layer 3 Mandatory will overwrite this stub.'\n"
"```\n"
```

This satisfies `validate_python_suite_candidate`, passes R1, and allows PHASE_D (Layer 3 Mandatory) to fire and overwrite the stub with the fitted `f()` before `test_model.py` is written to disk. The stub never executes. Zero interface changes to `_prepare_mutation_candidate`.

**Invariant updated:** INV-1 in `autoresearch_loop_architectural_map.md` updated with full bug record.

## Open Questions

1. **Composition depth policy: RESOLVED 2026-04-18.** The O(5,152²) estimate was wrong — it assumed exhaustive depth-2 over all base-primitive pairs. Actual architecture: depth-2 composes the top-K depth-1 outputs (K=5) with selected base primitives (5 families × 2 ops), giving ~50 candidates per wall-hit. This is the same LLM-guided + deterministic hybrid as depth-1, just one more loop. Additionally, deterministic ratio probes (COMPOSE(X, /, X) for exponential families) are gated by residual statistics: relative residual < 0.5 AND (autocorrelation > 0.3 OR sign_changes < 0.4n). This addresses the LLM blind spot for same-family divisions without overfitting to any specific target. Implementation in `topology_synthesizer.py`: `_run_ratio_probes()` and `_run_depth2_pass()`.

2. **Composition budget calibration:** The budget must be set before the first run. What is the right default? The depth-1 candidate space is 5,152; a budget of 50–200 evaluations covers 1.0%–3.9% of the space. The PySR benchmark will provide empirical data on how many evaluations are typically needed; budget calibration should follow the benchmark results.