# Sandbox_10 (Kepler) — Nesting-Collapse Audit

> **Seam metadata** · `seam_id:` GP-023 · `track:` substrates · `status:` `open / pre-seal` - 2026-04-15 20:00:00 · `last_updated:` 2026-05-08


**Status:** `open / pre-seal` — 2026-04-15 20:00:00
**Parent spec:** `research_areas/private/specs/active/GP-061_component_b_generalization_target_spec.md` v3
**Trigger:** sandbox_09 v2 closure (Outcome D, harvest under-convergence). See `GP-023_sandbox_09_post_run_audit.md` §5 — "sandbox_10 must pass an explicit nesting-collapse audit before sealing."
**Blocks:** sealing the sandbox_10 pre-reg. Sandbox_10 does not get a pre-reg draft until this audit closes.

---

## 0. Eigenquestion

**Can a mutator operating under the `math_power_only` grammar propose a strict generalization of Kepler vis-viva `v(r, a) = sqrt(GM * (2/r − 1/a))` such that the least-squares fit primitive drives the extra parameters to null values and collapses the generalization back to the sealed GT at iter 1, exactly as happened in sandbox_09 under `math_exp_only`?**

If yes, sandbox_10 inherits the sandbox_09 pathology and cannot produce a failed-family harvest, so the sealed Component B cold-test claim cannot be adjudicated on sandbox_10 either. The two-run promotion gate stalls.

If no, sandbox_10 is viable and a pre-reg draft can proceed.

---

## 1. The sealed GT and the grammar

**GT (vis-viva form):**
```
v(r, a) = sqrt(GM * (2/r - 1/a))
```

Observables: `r` (current radius), `a` (semi-major axis), `v` (instantaneous speed).
Identifiable parameter: `GM` (one-dimensional).

**Grammar (`math_power_only`, per GP-061 spec v3 §Target):**
- Allowed calls: `math.sqrt`, `math.pow` (equivalently `**`), arithmetic (`+`, `-`, `*`, `/`).
- Forbidden calls: `math.exp`, `math.log`, `math.sin`, `math.cos`, `math.tan`, any non-`math` call.
- Allowed constants: numeric literals, `math.pi`, `math.e`.

The grammar is chosen so that Component B's detector feature vocabulary (`fn:{fname}|arg{i}|has_op:{OP}`) must fire on function names and AST operators it has never touched on the sandbox_07/08 Planck targets (`eml`, `exp`, etc.). The expected cold-run void slot under this grammar is approximately `fn:sqrt | arg0 | has_op:Sub` — across failed families harvested from sandbox_10, the first positional argument to `math.sqrt` should never contain a `Sub` AST node unless the mutator has discovered vis-viva.

---

## 2. Enumeration of candidate wrappers

The question is: what five-parameter (or fewer) strict generalizations of vis-viva can a mutator express under `math_power_only` such that every wrapper reduces to vis-viva at some null parameter assignment?

### 2.1 Wrapper class W1 — polynomial-inside-sqrt with extra terms

```
v(r, a) = sqrt( C1 * r^p + C2 * a^q + C3 * (r^s) * (a^u) )
```

Free parameters: `(C1, C2, C3, p, q, s, u)` — seven. Collapse to vis-viva requires `C1 = 2·GM`, `p = -1`, `C2 = -GM`, `q = -1`, `C3 = 0`, `s, u` unconstrained. **Collapse is clean:** setting `C3 → 0` kills the cross term, and the fitter identifies `C1, C2, p, q` uniquely from the visible grid (vis-viva is identifiable).

**Verdict: W1 collapses. W1 is available to any mutator that can write `sqrt` of a sum.**

### 2.2 Wrapper class W2 — sqrt with a polynomial prefactor

```
v(r, a) = r^α * sqrt( C1 * r^p + C2 * a^q )
```

Free parameters: `(α, C1, C2, p, q)` — five. Collapse: `α = 0`, `C1 = 2·GM`, `p = -1`, `C2 = -GM`, `q = -1`. **Collapse is clean:** `α → 0` makes the prefactor unity.

**Verdict: W2 collapses.**

### 2.3 Wrapper class W3 — sum of two sqrt terms

```
v(r, a) = sqrt( C1 * r^p + C2 * a^q ) + C3 * sqrt( C4 * r^s + C5 * a^u )
```

Free parameters: eight. Collapse: `C3 → 0` kills the second sqrt, first sqrt recovers vis-viva. **Collapse is clean.**

**Verdict: W3 collapses.**

### 2.4 Wrapper class W4 — nested sqrt

```
v(r, a) = sqrt( C1 * r^p + C2 * a^q + C3 * sqrt(C4 * r^s + C5 * a^u) )
```

Free parameters: eight. Collapse: `C3 → 0` kills the inner sqrt, outer sqrt recovers vis-viva. **Collapse is clean.**

**Verdict: W4 collapses.**

### 2.5 Wrapper class W5 — polynomial outside sqrt

```
v(r, a) = sqrt( C1 * r^p + C2 * a^q ) * (1 + C3 * r^s * a^u)
```

Free parameters: seven. Collapse: `C3 → 0` makes the factor unity. **Collapse is clean.**

**Verdict: W5 collapses.**

### 2.6 Wrapper class W6 — additive offset

```
v(r, a) = C0 + sqrt( C1 * r^p + C2 * a^q )
```

Free parameters: five. Collapse: `C0 → 0`. **Collapse is clean.**

**Verdict: W6 collapses.**

### 2.7 Wrappers that do NOT collapse

Families the `math_power_only` grammar cannot express (and therefore the mutator cannot propose) cannot nest vis-viva trivially. Examples: any GT involving `exp(−r/a)`, `log(r/a)`, or trigonometric functions. But these are also not available to the mutator, so they are not wrappers the mutator could write; they are non-starters.

Families the grammar **can** express but that are *not* sqrt-headed and therefore don't naturally nest vis-viva: e.g.

```
v(r, a) = C1 * r^p + C2 * a^q     (no sqrt, simple power law)
```

Free parameters: four. Does not collapse to vis-viva at any null parameter assignment — vis-viva is `sqrt(...)`-headed, while this family is `+`-headed. A fit of this family to vis-viva data will have non-negligible residual unless the fit pushes `p, q` into specific fractional values and the residuals are small by luck. **This is a non-nesting family.**

---

## 3. The audit result

**Six distinct wrapper classes (W1–W6) express vis-viva as an interior limit of a strict generalization, and all are expressible under `math_power_only`.** A mutator that proposes any of W1–W6 and runs the fit primitive will recover vis-viva to machine precision on an identifiable grid, by the same mechanism that collapsed sandbox_09 (extra parameters → null, core form → sealed GT, `max_abs_residual → 0`).

**Therefore: sandbox_10 under the current GP-061 spec inherits the sandbox_09 nesting-collapse pathology.** Sealing a pre-reg for sandbox_10 as currently specified would reproduce the Outcome D trajectory on a new target and burn the second of the two-run promotion gate's slots without any new evidence.

This is not a sandbox_10-specific failure — it is the same principle from sandbox_09 §5: **grid identifiability and failed-family harvest are in tension.** Any grid identifiable enough to pass an identifiability protocol is also identifiable enough for a nested wrapper to fit-collapse to the sealed GT. Changing the grammar from `math_exp_only` to `math_power_only` does not change this property; it only changes which wrappers are expressible. As long as *some* wrapper nests the GT, the mutator can use it.

---

## 4. Candidate remediations

### 4.1 R1 — choose a GT outside the nesting closure of the grammar

Find a physical target whose GT, when expressed under `math_power_only`, is not the interior limit of any shorter expression in the same grammar. Candidates that might qualify:

- **Pendulum period with small-angle approximation:** `T(L) = 2π * sqrt(L/g)`. Single free parameter `g`. Wrappers like `T = 2π * L^α * sqrt(L^p / g)` collapse at `α = 0, p = 1`. **Does collapse.** Not a fix.
- **Ideal gas law:** `P(V, T, n) = n*R*T / V`. Free parameter `R`. Wrappers like `P = n*R*T^α / V^β` collapse at `α = 1, β = 1`. **Does collapse.** Not a fix.
- **Stefan-Boltzmann:** `P(T) = σ * T^4`. Two free params at most (σ and the 4). Wrapper `P = σ * T^α` collapses at `α = 4`. **Collapses trivially.** Not a fix.

**General observation:** simple physical laws in power-law form are *always* in the interior of a polynomial family under the power grammar. The nesting closure is essentially the whole grammar. R1 is a dead end for `math_power_only`.

### 4.2 R2 — forbid specific wrapper patterns in the grammar

Modify the grammar to explicitly forbid the nesting patterns:

- Disallow `sqrt(A + B + C + ...)` for expressions with more than two additive terms inside `sqrt`.
- Disallow coefficients on terms inside `sqrt` that are not literal 1 or -1.
- Disallow additive offsets outside `sqrt` when `sqrt` is the outermost operation.

**Problem:** these restrictions bite the sealed GT too. Vis-viva is `sqrt(2*GM/r - GM/a)` — two additive terms inside sqrt, with coefficients `2*GM` and `-GM`. Forbidding "coefficients on terms inside sqrt that are not 1 or -1" makes vis-viva itself unexpressible under the grammar. The mutator cannot be forced to find a form it cannot write. **R2 collapses the target before it collapses the wrapper. Not a fix.**

### 4.3 R3 — redefine what Component B's cold-test actually adjudicates

Accept that the nested-collapse pathway is unavoidable on any identifiable grid. Then the Component B sealed claim must be restated to not depend on an empty-harvest scenario. Two sub-options:

- **R3a — Forced-failure seed.** Pre-seed `thesis.md` with a deliberately non-nesting family (e.g., W_0 from §2.7, `v = C1*r^p + C2*a^q`, which cannot collapse to vis-viva). The mutator starts from a wrong family; iter 1 necessarily fails; harvest accumulates over several iterations as the mutator searches; Component B has something to cold-run against. This is operator-injected failure and scientifically messy (see Gemini Pro's Path 2 rebuttal in the sandbox_09 closure), but it is scientifically *legible* if the pre-reg explicitly declares "Component B is tested conditional on a forced non-nesting initial family, not on the mutator's unprompted first proposal." Not a capability claim about the mutator; a conditional capability claim about Component B given a failing harvest.
- **R3b — Rate-of-harvest test.** Instead of testing "the mutator produces a failed-family harvest," test "given a failed-family harvest (however produced), does Component B's cold run surface the expected void slot and no non-verifiable slots?" This sidesteps the nesting question entirely: the harvest is a direct input, not a downstream artifact of mutator behavior. The harvest can be assembled from sandbox_09 iter-3 thesis families plus any subsequent exploration, or from a hand-authored corpus of deliberately wrong vis-viva candidates. This is **not the same experiment** as the original GP-061 cold-test protocol — it moves the test from a two-stage (mutator generates harvest → extractor runs cold) to a one-stage (extractor runs cold on a curated harvest). The curation step is now the decisive operator move; its pre-registration discipline must be stated explicitly (what goes in the harvest, why, at seal time).

### 4.4 R4 — abandon the two-run promotion gate on Component B

If both R1 and R2 fail and R3 is considered too invasive, the honest move is to stop trying to run Component B under the current sandbox design and revisit the Component B live-emission question from a different angle: e.g., run Component B on historical closed-sandbox harvests (sandbox_06, sandbox_07, sandbox_08) in retrospective mode and ask "would the slot vocabulary have fired correctly on these historical failures?" instead of "does the slot vocabulary fire on new cold failures?"

Retrospective tests are weaker than prospective tests because the operator has already read the outcomes, but they are still informative about whether the detector's vocabulary is domain-agnostic. This is a demotion of the sealed claim, not a resolution of it.

---

## 5. Recommended next step

**Recommend R3b (rate-of-harvest test) paired with a retrospective R4 sanity check.** Rationale:

- R3b preserves a clean pre-registration discipline (curated harvest sealed before the cold run) while sidestepping the nesting-collapse pathology entirely. The operator commits in writing, pre-cold-run, to the exact harvest composition and the expected void slots, and the cold run is judged on whether it surfaces the expected slots.
- R4 (retrospective) is a cheap parallel sanity check: run Component B on the closed sandbox_07/08 harvests and verify it surfaces the already-known `fn:exp|arg0|has_op:Div` slot on retrospective data. If retrospective R4 passes and prospective R3b passes on sandbox_10, the combined evidence is stronger than either alone and the two-run promotion gate can be declared satisfied by substitution.
- R3a (forced-failure seed) is technically clean but cosmetically ugly and opens questions about whether the seed leaks information to the mutator. Not recommended as the first move; held in reserve.
- R1/R2 are dead ends under power grammar.

**Before any of this runs, GP-061 spec v3 needs a v4 amendment** that:

1. Names the nesting-collapse pathology explicitly (§A1 of this audit fills this purpose — copy into the spec).
2. Declares R3b the new sandbox_10 protocol and specifies the curated harvest composition.
3. Declares R4 the retrospective parallel check on sandbox_07/08.
4. Amends the two-run promotion gate: the original "two live prospective mode (c) passes on non-Planck targets" is replaced with "one prospective R3b pass on sandbox_10 + one retrospective R4 pass on closed Planck sandboxes + pre-registered criterion for each."

This is a significant amendment. It may be worth waiting one day, re-reading the GP-061 spec with fresh eyes, and writing the v4 amendment in a separate session rather than bolting it onto this audit.

---

## 6. What this audit does NOT decide

- **Whether sandbox_10 should run at all.** That's a GP-061 spec-level decision, not an audit decision. If the GP-061 spec owner decides the two-run gate is decisive enough to accept R3a (forced-failure seed) despite the cosmetic cost, sandbox_10 can still run. This audit only says "sandbox_10 as currently specified will reproduce sandbox_09 Outcome D."
- **Whether Component B is a valid claim at all.** That's a deeper question about whether negative-space extraction is a meaningful generalization check, and is well beyond the scope of a pre-seal nesting audit. If Component B's fundamental premise is unsound, R1–R4 are rearranging deck chairs.
- **Anything about sandbox_09's closure.** That is sealed at Outcome D and stays there.

---

## 7. Cross-references

- `research_areas/private/seams/GP-023_sandbox_09_post_run_audit.md` §5 (trigger)
- `research_areas/private/seams/GP-023_sandbox_09_pre_registration.md` §5, §7 (sealed decision tree, harvest-stress rule)
- `research_areas/private/specs/active/GP-061_component_b_generalization_target_spec.md` v3 §Target (math_power_only grammar, sandbox_10 spec)
- `papers/case_studies/rank_deficient_bootstrap.md` (the general principle: identifiability checks must vary the starting point; nested wrappers collapse under multi-start if they collapse at all)
- Sandbox_09 v2 champion form for the analogous sandbox_09 collapse pattern: `projects/gp023_sandbox_09/history/1776258959_iter1_score_100_gp023_sandbox_09.md`
