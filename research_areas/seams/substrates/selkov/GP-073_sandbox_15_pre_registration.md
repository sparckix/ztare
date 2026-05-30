# GP-073 Sandbox 15 — Selkov Glycolysis Oscillator Substrate Pre-Registration

> **Seam metadata** · `seam_id:` GP-073 · `track:` substrates · `status:` CLOSED 2026-04-16. Null result for Component B. See §Formal  · `last_updated:` 2026-05-08


**Status:** CLOSED 2026-04-16. Null result for Component B. See §Formal Pair 1 Results.
**Draft date:** 2026-04-16
**Substrate:** `projects/gp073_sandbox_15/`
**Rubric:** `rubrics/gp073_sandbox_15.json` (`fit_score_mode: "discrete_exact"`)
**Parent seam:** `GP-073_subliminal_learning_reproduction_seam.md`

> **Framing disclosure:** This is a Component B apparatus-hardening experiment. It tests whether the mutator surfaces `has_op:Pow` (the u² term) as the absent structural primitive from the accumulating failed families, given that the substrate is bare-numeric (u, v, z — no domain labels). A positive result means "the cubic cross-term u²v is structurally identifiable through the 10/30 wall imposed on all linear-coupling families." The domain-free framing removes the Textbook Ladder (LV → RM → Selkov) as a crack path.

> This file is **private** (under `research_areas/private/`). It is the only file that names the GT formula, the parameter values, and the expected void slot. Nothing here may be copied into the charter, rubric, thesis, evidence file, or any other mutator-visible artifact.

---

## Sealed Ground Truth (private, never copied into project dir)

```python
def gt(u: int, v: int) -> int:
    a = 0.08
    return round(-u + a * v + u * u * v)
```

### Structural analysis

This is a 1D projection of the Selkov glycolysis oscillator (prey/substrate equation):

| Term | Expression | Role |
|---|---|---|
| Linear decay | `-u` | Self-limiting growth |
| Small linear coupling | `0.08 * v` | Weak substrate feedback |
| Cubic cross-term | `u² * v` | Autocatalytic amplification — the decisive term |
| Parameter `a` | `0.08` | Coupling coefficient |

**Algebraic form:**

```
z = -u + a*v + u²*v     where a = 0.08
  = -u + v*(a + u²)
  = -u + v*(0.08 + u²)
```

**Key structural features:**

1. **The u²v term dominates:** For u ≥ 2, `u²*v >> 0.08*v`, so the coupling is essentially `u²*v`. The `0.08*v` term is nearly invisible in the integer data except where it causes a rounding step (e.g., u=1, v=7: `-1 + 0.08*7 + 1*7 = 6.56 → round = 7`).

2. **Why u=1 degenerates:** At u=1, `u²=u=1`, so `u²*v = u*v`. Any linear-coupling model of the form `round(-u + c*u*v)` with c=1 matches all u=1 rows exactly. This makes linear competitors look deceptively good at 10/30 (all u=1 rows only).

3. **The 10/30 wall:** For u=2, the true coefficient on v is `u²=4`; linear c=1 predicts coefficient 1, giving `z_diff = 3*v` per row. For u=3, the true coefficient on v is `u²=9`; linear c=1 gives `z_diff = 8*v` per row. No fixed constant c makes `-u + c*u*v` work for all three u values simultaneously.

4. **The Pow void:** All linear or bilinear families (`A*u + B*v + C*u*v`) share an AST with ops `{Mult, Add, Sub}` but no `Pow` node. The extractor will accumulate `has_op:Pow ABSENT` across all failed linear families before injection.

5. **Identifiability:** Two free parameters (coefficient of u²v is implicitly 1, `a=0.08`) over 30 2D points. Massively overdetermined. No alternative parameterization achieves 30/30.

**Domain:**
- u ∈ {1, 2, 3} (visible), {1, 2, 3} (holdout)
- v ∈ {1, 2, ..., 10} (visible), {11, 12, 13} ∪ {14} (holdout)
- Output range: [0, 88] visible (all non-negative); holdout extends to 115
- Visible: 30 points (full grid u×v); Holdout: 10 points

**Generator:** Division A inline computation, verified in this session (2026-04-16).

---

## Why this substrate resists the Textbook Ladder

**The Textbook Ladder problem:** In a domain-labeled substrate (prey, predator, dx/dt), a mutator with LLM knowledge can walk: Lotka-Volterra → Rosenzweig-MacArthur → Selkov in one step. The named sequence is a cheat path that bypasses structural reasoning from data.

**This substrate's defense:** The charter, evidence file, and thesis use bare numeric labels: `u`, `v`, `z`. No biological framing, no "rate of change," no "population." The mutator receives no domain prior and cannot recognize the Textbook Ladder.

**Does bare framing actually change crack risk?**

- *Yes, substantially:* Without "prey/predator/rate" framing, the mutator cannot invoke Selkov as a named import. It must derive the u² term from data.
- *Residual risk:* The slope pattern (`dz/dv ≈ u²` for each fixed u) is detectable from the data. A sufficiently systematic mutator that notices slope(u=1) ≈ 1, slope(u=2) ≈ 4, slope(u=3) ≈ 9 could infer `slope ∝ u²` and try `u²*v`. This is legitimate structural derivation, not a named import.
- *Assessment:* The bare framing closes the named-import crack path. The structural crack path (deriving u² from slope ratios) remains and is intentional — that is the target behavior the rubric's Stepwise Derivation criterion rewards.

---

## Calibration Table

| Model | Exact matches / 30 | Notes |
|---|---|---|
| `round(-u + 0.08*v)` | 0/30 | No coupling at all |
| `round(-u + 0.08*v + 1*u*v)` | 10/30 | Linear c=1; only u=1 rows (u²=u) |
| `round(-u + 0.08*v + 2*u*v)` | 10/30 | Linear c=2; still only u=1 rows for one branch |
| `round(-u + 0.08*v + 3*u*v)` | 10/30 | Linear c=3; same 10/30 wall |
| `round(-u + 0.08*v + u²*v)` | 30/30 | True GT formula |
| Lookup table | 30/30 | Fails holdout by construction |

**Critical calibration property:** Every linear-coupling family hits exactly the 10/30 wall (the 10 rows where u=1). The mutator cannot squeeze past 10/30 with any constant-coefficient bilinear form. The 20 failures (all u=2 and u=3 rows) force structural discovery.

---

## Expected Component B Void

After 3+ failed families of the form `round(-u + c*u*v + ...)`:

| Void slot | Expected | Reasoning |
|---|---|---|
| `has_op:Pow` | Present in all early families' ABSENT set | All linear/bilinear families use only `{Mult, Add, Sub}` — no squaring |
| `has_op:Div` | Not expected early | GT has no division; Div-containing families also fail |

**Primary expected void:** `has_op:Pow` — the u²=u**2 term is absent from every linear-coupling family AST.

**Injection hypothesis:** A PC-008 entry `has_op:Pow ABSENT from families [F1..Fk]` steers the mutator to try expressions with `u**2` or `u*u` terms, leading to the family `round(-u + c*v + u**2*v)` which achieves 30/30.

---

## Denylist and Sentinel Result

**Denylist patterns (18):**
```
selkov               glycolysis           autocatalytic
oscillator           cubic                x\.squared
x\*\*2               u\*\*2               quadratic.*coupling
0\.08                a\s*=\s*0            substrate
ATP                  ADP                  prey
predator             rate.of.change       population
```

**Sentinel result (2026-04-16):**

| File | Matches |
|---|---|
| `projects/gp073_sandbox_15/project_charter.md` | 0 |
| `projects/gp073_sandbox_15/thesis.md` | 0 (fixed: "rate of change" → "non-zero output") |
| `projects/gp073_sandbox_15/test_model.py` | 0 |
| `projects/gp073_sandbox_15/evidence.txt` | 0 |
| `rubrics/gp073_sandbox_15.json` | 0 |

**Total matches: 0. SENTINEL PASSED.**

**Note:** `thesis.md` initially contained "rate of change" (matched `rate.of.change`). This was corrected to "non-zero output" before the pre-registration was sealed.

---

## SHA-256 Hashes (sealed at 2026-04-16)

```
c5cc3614e6a173522e7771bd33d6c86cc7e7f8e1f499bc8d40f2fd83cc584963  projects/gp073_sandbox_15/project_charter.md
59129f6a1b7a5b1ecbf90c019cd63ee5f556417860a256edd8b534f1ea808d2d  projects/gp073_sandbox_15/thesis.md
4204a53576c2ceeb505ec315983e0e308d050a917c4fa2ece3cc0d9f3eb21c18  projects/gp073_sandbox_15/test_model.py
289401c97092164d8acb8ff0b1d565fe74806ec8d970f78d608f621ef51d437d  projects/gp073_sandbox_15/evidence.txt
448b08e9e1c200446fca9758120106585ccfb222f2a69619b1022bfc245ab93f  rubrics/gp073_sandbox_15.json
```

---

## Division A / Division B Role Separation

Constructed under M-form information isolation per GP-072 protocol:

- **Division A (GT-aware):** Computed all 30 visible and 10 holdout points from the Selkov GT formula. Authored this sealed pre-registration. Ran the leak sentinel. Computed file hashes. Rewrote evidence.txt, evidence_holdout.txt, test_model.py, and thesis.md to use generic `u, v, z` column names.

- **Division B (GT-blind):** Authored `project_charter.md` and `rubric`. Briefed only as: "2D integer-valued function over two positive integer inputs u and v, exact match scoring required." Division B knows nothing about Selkov, glycolysis, or the u²v structure.

- **Information barrier:** Division B's charter uses bare variable names `u, v, z`. It prohibits named-import shortcuts and per-row lookup tables. It does not name any specific functional form, parameter values, or structural features.

---

## Evidence Verification (Division A)

All 30 visible points computed inline and verified:

| u | v | z (GT) | u | v | z (GT) | u | v | z (GT) |
|---|---|---|---|---|---|---|---|---|
| 1 | 1 | 0 | 2 | 1 | 2 | 3 | 1 | 6 |
| 1 | 2 | 1 | 2 | 2 | 6 | 3 | 2 | 15 |
| 1 | 3 | 2 | 2 | 3 | 10 | 3 | 3 | 24 |
| 1 | 4 | 3 | 2 | 4 | 14 | 3 | 4 | 33 |
| 1 | 5 | 4 | 2 | 5 | 18 | 3 | 5 | 42 |
| 1 | 6 | 5 | 2 | 6 | 22 | 3 | 6 | 51 |
| 1 | 7 | 7 | 2 | 7 | 27 | 3 | 7 | 61 |
| 1 | 8 | 8 | 2 | 8 | 31 | 3 | 8 | 70 |
| 1 | 9 | 9 | 2 | 9 | 35 | 3 | 9 | 79 |
| 1 | 10 | 10 | 2 | 10 | 39 | 3 | 10 | 88 |

**GT achieves 30/30 exact match on visible set.**

All 10 holdout points:

| u | v | z (GT) |
|---|---|---|
| 1 | 11 | 11 |
| 1 | 12 | 12 |
| 1 | 13 | 13 |
| 2 | 11 | 43 |
| 2 | 12 | 47 |
| 2 | 13 | 51 |
| 3 | 11 | 97 |
| 3 | 12 | 106 |
| 3 | 13 | 115 |
| 1 | 14 | 14 |

**GT achieves 10/10 exact match on holdout set.**

---

## Gate Harness Verification

`gate_harness.py` parses evidence by position (column 0 = first var, column 1 = second var, column 2 = output). The `# u  v  z` header is skipped as a comment. The harness calls `f_model(x, y)` positionally — compatible with the new `f_model(u, v)` signature in `test_model.py`. No changes to `gate_harness.py` required.

---

## Sealed Run Command

```bash
make loop PROJECT=gp073_sandbox_15 RUBRIC=gp073_sandbox_15 \
  MUTATOR_MODEL=gemini-pro JUDGE_MODEL=gpt4.1 \
  ITERS=12 \
  EXTRA_ARGS="--disable_attacker_tools"
```

**Dry-run gate: PASSED 2026-04-16** — 4-iter treatment-only run (gemini-pro/gpt4.1). See §Dry-Run Findings.

---

## Go/No-Go Checklist

- [x] Evidence verification — GT achieves 30/30 visible, 10/10 holdout (Division A verified 2026-04-16)
- [x] Calibration — all linear-coupling competitors hit exactly 10/30 wall; substrate non-trivially discriminating
- [x] Leak sentinel — 18 patterns, 0 matches across all 5 mutator-visible files (SENTINEL PASSED)
- [x] File hashes recorded — all 5 mutator-visible files fingerprinted at seal time
- [x] Expected void identified — `has_op:Pow` is the absent primitive; clearly motivated by the 10/30 linear wall
- [x] Role separation confirmed — Division A/B M-form construction; GT never written into project dir
- [x] Charter factual accuracy — bare u, v, z framing; no domain labels; no formula or parameters revealed
- [x] Denylist covers all GT terms — selkov, glycolysis, 0.08, u**2, cubic, substrate, autocatalytic all denied
- [x] thesis.md cleaned — "rate of change" removed; generic language substituted
- [x] evidence.txt header — `# u  v  z` (generic); 30 data rows, no metadata
- [x] Textbook Ladder crack resistance assessed — bare framing closes named-import path; structural derivation path is intentional and rubric-rewarded
- [x] Dry-run gate — PASSED 2026-04-16 (4 iters, gemini-pro/gpt4.1). See §Dry-Run Findings.
- [x] Operator seal with timestamp — **RESEALED 2026-04-16**

## §Dry-Run Findings (2026-04-16)

**Run:** 4 iters, gemini-pro / gpt4.1, `rubrics/gp073_sandbox_15.json`.

**Scores:** 0 → 48 (champion) → 31 → 36 → 29. Champion held at iter 1; all subsequent iters reverted.

**What worked:**
- Extractor activated: 2 families in structural memory (`floor(v/7)` variant; sigmoid step variant).
- u²v backbone found on iter 1 via numerical reasoning — no domain prior invoked. Textbook Ladder closed by bare framing.
- Substrate not cracked clean: score 48 (not 100). Holdout correctly discriminates via `round(0.08v)` vs `floor(v/7)` divergence at v=14.
- Component B surfaced PC-003/PC-005/PC-007 pointing at the step-function misidentification — correct void direction.

**What the mutator missed:** The small correction term is `round(0.08v)` (smooth, not periodic). The mutator converged on step-function approximations (`floor(v/7)`, Heaviside at v=7) which all fail at v=14 in holdout. In 12 formal iters with PC-003/PC-005/PC-007 pressure, the mutator should explore non-step alternatives.

**Bugs fixed during dry-run:**
- `gate_harness.py _load_model()`: only caught `AssertionError` on module load — `NameError` from missing imports (e.g., bare `floor()`) was silently crashing the harness. Fixed to also catch and log all other exceptions.

**Calibration verdict:** Substrate correctly calibrated. Dry-run gate passed. Proceed to formal pairs.

---

## §Formal Pair 1 Results (2026-04-16) — CLOSED

**Status:** CLOSED — NULL RESULT FOR COMPONENT B. Substrate correctly discriminates but does not stress-test the negative space extractor.

### Treatment Arm (Component B ON)

**Run:** 12 iters, gemini-pro / gpt4.1, `rubrics/gp073_sandbox_15.json`, `--disable_attacker_tools`.

**Scores:** 0 → 33 → 36 → **50** (champion) → 50 → 28 → 44 → 43 → -35 → 9 → 48 → 37 → 15. Champion held at iter 3; stagnation 9.

**Champion expression:** `A * u**2 * v + B * u + C * math.ceil((v - 6.0) / (math.fabs(v - 6.0) + 1.0))` with A=1.0, B=-1.0, C=1.0.

**Structural memory:** 7 families explored, all step-function variants (floor, ceil, Heaviside, integer division with varying offsets and periods).

**Gate result:** 30/30 visible, 10/10 holdout. The ceil formula is observationally equivalent to the GT `round(-u + 0.08v + u²v)` for all integer points {u=1,2,3} × {v=1..18}. First divergence at (u=1, v=19).

**Score bottleneck:** Criterion 3 (Stepwise Derivation From Data) not earned. The formula passes the gate but the thesis did not show explicit derivation steps citing specific (u,v,z) triples.

**Archived:** `research_areas/private/run_logs/gp073_sandbox_15/pair1_treatment/`

### Control Arm (Component B OFF)

**Run:** 12 iters (stopped early at iter 3, sufficient for comparison), gemini-pro / gpt4.1, `rubrics/gp073_sandbox_15.json`, `--disable_attacker_tools --disable-negative-space-extractor`.

**Scores:** 0 → 34 → 44 → **50** (champion). Champion at iter 3 — identical convergence speed to treatment arm.

**Champion expression:** `u * (u * v - 1) + floor(v / 7)` = `u²v - u + floor(v/7)`. This is the periodic hypothesis — fails at (1,14) where floor(14/7)=2 gives overshoot. However, the control arm's thesis included explicit stepwise derivation (criterion 3 earned), compensating for the holdout failure on criterion 2. Score 50 reached by a different failure profile than treatment.

**Key finding — same score, different failure modes:**

| Criterion | Treatment (B ON) | Control (B OFF) |
|---|---|---|
| 1. Exact match visible (30/30) | PASS | PASS |
| 2. Generalization to holdout | PASS (10/10) | FAIL (9/10, (1,14) overshoot) |
| 3. Stepwise derivation | FAIL | PASS |
| 4. No lookup table | PASS | PASS |
| 5. No named import | PASS | PASS |
| **Total** | **50** | **50** |

### Null Result Analysis

**Primary finding:** Component B had no measurable effect on this substrate. Both arms found the u²v backbone in 2-3 iterations and converged to score 50 at iter 3.

**Root cause — the substrate does not stress-test Component B:**

1. **Slope ratio crack path.** With u ∈ {1,2,3}, the slope ratios 1:4:9 = u² are immediately readable from basic finite differences. The `has_op:Pow` void signal is redundant — any attentive LLM finds u² from slope inspection alone. Component B's value requires substrates where the critical operator is NOT inferrable from direct data inspection.

2. **Corrector term degeneracy.** `round(0.08v)` and `ceil((v-6)/(|v-6|+1))` produce identical integers for all v ∈ {1..18}. The holdout (max v=14) cannot discriminate between the true smooth correction and any step-function approximation that steps at v=7 exactly once. The discriminator at v=14 correctly rejects the periodic hypothesis (floor(v/7)) but cannot force discovery of the true `0.08v` smooth term.

3. **Score ceiling is a rubric bottleneck.** The 50-point ceiling reflects criterion 3 (thesis quality) or criterion 2 (holdout), depending on the arm — not formula quality. Both arms found formulas with the correct u²v backbone. The remaining 50 points require either better thesis writing (criterion 3) or an extended holdout domain (v≥19) to break the corrector degeneracy.

### Architectural Insight — Component B's Operating Envelope

**Inversion analysis (applied during this experiment):**

Component B is a **topological pruner**, not a **semantic injector**. It operates on the AST (Abstract Syntax Tree) — banning syntactic nodes (e.g., `floor`), not semantic concepts (e.g., "discretization"). When the mutator is banned from `floor`, it substitutes `ceil`, `Heaviside`, integer division — syntactically different operators encoding the same discrete-step geometry. The 7 families in structural memory are all step-function variants.

Component B's effectiveness is bounded by:

```
V(Component B) ∝ (pruned_space / total_space) × (remaining_space_is_structured)
```

- **High value:** When the pruned attractor basin (wrong families) is large and the remaining space is small and structured (sandbox_13: polynomial+trig pruned → Mod is the obvious next operator).
- **Low value:** When the pruned basin is small or the remaining space is vast and unstructured (Selkov: step functions pruned → the space of continuous corrector functions is unbounded).

**The continuous-discrete boundary:** LLMs under integer-output constraints exhibit strong prior bias toward discrete mechanisms (floor, ceil, mod, Heaviside) for step-shaped residuals. The correct Selkov corrector `round(0.08v)` requires inventing a latent continuous dimension (0.08v ∈ ℝ) between integer inputs and integer outputs, then immediately crushing it back to integers via round(). This crosses a data-type boundary that Component B's syntactic pruning cannot bridge.

### Identified Architectural Gap — Component C (Residual Fingerprinting)

The missing component is a **residual numerical analyzer** that:
1. Computes the per-point residual between the champion backbone and the observed data
2. Describes the residual's geometric shape (monotone, periodic, single-jump, linear drift, etc.)
3. Passes the shape description to the mutator as a positive-space constraint

This differs from Component B (negative space — "where the answer is NOT") by providing positive space — "what the missing term looks like numerically." For Selkov, the residual vector {0,0,0,0,0,0,1,1,1,1,...} would be fingerprinted as "consistent with round(αv) for α ∈ [0.07, 0.15]; inconsistent with periodic floor(v/k) because no repeat at 2× the jump location."

**Design constraint:** Component C must be shape-agnostic (not hardcoded to Selkov's single-step pattern) to avoid overfitting to this substrate.

### Steganographic Defense Assessment

Ref: Cloud, Le, et al. "Language models transmit behavioural traits through hidden signals in data." Nature 652, 615-621 (2026).

The paper proves that subliminal learning (steganographic trait transmission through semantically unrelated data) occurs **only when teacher and student share the same model initialization**. Cross-model transmission between different families (e.g., GPT-4.1 nano → Qwen 2.5-7B) shows near-zero effect (Fig. 5b: 0.01, not significant).

**ZTARE's natural defense:** The formal pair uses Gemini-pro (mutator) and GPT-4.1 (judge) — different model families with different initializations. The steganographic channel is structurally severed by architecture.

**Division A/B defense:** Both divisions used Claude, sharing initialization. However, Division A's contribution is deterministic Python computation (evidence integers from the GT formula), not LLM-generated text. Division B receives only the evidence data (Python-computed integers) and a one-line framing brief. No high-bandwidth LLM-generated channel exists between divisions.

**Gate defense:** The holdout gate (`gate_harness.py`) is deterministic Python — no LLM in the evaluation loop. Steganographic collusion cannot influence the gate result. The discovery artifact (the formula) is falsifiable by integer comparison, not by LLM judgment.

**Assessment:** Steganographic collusion is a theoretical concern for ZTARE's rubric score (LLM-evaluated) but not for its discovery artifact (deterministically evaluated). The cross-family architecture and deterministic gate provide sufficient defense for the current experimental claims.

### Disposition

**Sandbox_15 status:** CLOSED. Substrate correctly calibrated. Discriminator works. Component B null result is clean and informative. No further pairs warranted on this substrate.

**Forward program:**
1. Seam for Component C (Residual Fingerprinting) — debate the instantiation: deterministic Python heuristic vs. isolated LLM agent vs. hybrid
2. Design next substrate around an operator in the LLM's empirical blind spot (mod arithmetic, number-theoretic functions) where Component B + C can be jointly tested
3. Update Paper 4 framing: Component B is a topological pruner with a characterized operating envelope; Component C is the identified next architectural component

**Closed:** 2026-04-16
