# GP-069 — Champion nesting-audit gate seam (draft)

> **Seam metadata** · `seam_id:` GP-069 · `track:` engine · `status:` DRAFT 2026-04-15. Not a spec. Debate-stage seam under AGENTS · `last_updated:` 2026-05-08


**Status:** DRAFT 2026-04-15. Not a spec. Debate-stage seam under AGENTS.md §spec-format.
**Context:** This seam formalizes the lesson from sandbox_09 v2 Outcome D and the sandbox_10 nesting-collapse audit into a reusable pre-seal gate for future curated sandboxes and live autoresearch targets.

---

## The problem

On any grid where the sealed GT is cleanly identifiable under its declared grammar, a mutator expressing a nested generalization of that GT — a strict super-family with 1–2 extra free parameters that collapses to GT at null extra-parameter values — can reach score 100 at iteration 1. The fit primitive drives the extras to zero, the model-report reduces to the sealed form, the harvest is empty, and Component B has nothing to read.

This pattern generalizes beyond RC and Kepler. Any sealed GT inside a polynomial-in-primitives closure is at risk. The pathology is grammar-structural, not sandbox-specific.

## Debate

### Position A: fix via grammar restriction (R1/R2 from sandbox_10 audit)

Claim: restrict the grammar axis so that nested wrappers are syntactically forbidden. For example, under `math_power_only`, disallow `sqrt(...)` where the arg contains more than one multiplicative term, or forbid sum-inside-sqrt entirely.

Counter: this forbids the sealed GT itself. Vis-viva is `sqrt(GM*(2/r - 1/a))` — a sum (difference) inside sqrt. Any restriction that bans the wrapper class also bans the target. RC has the same property. The restriction can only be narrow enough to forbid non-collapsing wrappers, but "collapses or not" is not a syntactic property — it depends on limit-value behavior of fit residuals. The restriction would need to be semantic, which means running the fit at seal time against every syntactically-possible wrapper, which is combinatorial.

**Verdict: A dies.**

### Position B: fix via forced-failure seed injection

Claim: seed the autoresearch loop with 3–5 structurally-diverse failed candidates before iter 1. The mutator's first proposal is then shaped by the forced-failure harvest rather than a clean slate.

Counter: the seed families would themselves need to survive the fit primitive without collapsing to GT. This reduces to the same problem — the seed corpus is just a curated harvest under a different name. And seeding pollutes the mutator's context with operator judgment about what "wrong" looks like, which is the single worst contamination axis Paper 1 identifies.

**Verdict: B dies.**

### Position C: fix via post-fit symbolic simplifier gate

Claim: after every iter 1 fit, symbolically inspect the fitted model. If any fitted parameter is within `epsilon` of a null value (typically 0 for additive, 1 for multiplicative, null for exponents), simplify the expression and check whether the simplified form equals the sealed GT (operator-side check, not mutator-visible). If yes, the iteration is **voided** (not failed — voided) and the mutator is forced to re-propose with a constraint prohibiting this wrapper class.

Subtlety: the "constraint prohibiting this wrapper class" must be expressible in mutator-visible terms without disclosing the sealed GT. One way: generate the constraint as "do not propose a model where parameter P_k collapses to null value under fit" — this is anti-overparameterization, not anti-GT.

Counter: this is a retroactive gate, not a pre-seal gate. Seal discipline is cleaner when violations are caught before the run, not during. But a pre-seal version requires enumerating the wrapper classes at seal time, which is the combinatorial problem from Position A.

**Verdict: C is the best option but requires clarity on seal-time vs run-time scope.**

### Position D: fix via protocol switch (R3b)

Claim: give up on live-mutator harvest for GP-061 over nesting-closed grammars. Use curated harvests (R3b) for cross-grammar tests and retrospective retrospective (R4) for consistency. The live-mutator path is preserved only on grammar axes where the sealed GT sits outside the polynomial-in-primitives closure.

Counter: this is narrow — it sidesteps GP-069 rather than solving it, and leaves the live-mutator axis permanently parked on grammars unlike RC and Kepler. However, it's honest about what's testable.

**Verdict: D is orthogonal to GP-069. D is already in force as the GP-061 v4 amendment. GP-069 is the parallel track that says "what would a live-mutator GP-061 pass require?"**

## Proposed seam direction (Position C variant)

A two-level gate:

**Level 1 — seal-time static check.** At seal time, the operator enumerates (manually or via a symbolic tool) the wrapper classes reachable in ≤1 mutator mutation from the sealed GT under the declared grammar. If any wrapper class collapses to GT at null extra-parameter values, the pre-reg is **not sealable** until either (a) the grammar is narrowed to exclude the wrapper class without also excluding the GT (if feasible), or (b) the protocol is switched to R3b. This is the sandbox_10 audit lesson codified.

**Level 2 — run-time dynamic check.** For any target that clears level 1, the autoresearch loop post-fit hook runs a symbolic simplifier on the fitted champion and flags any fitted parameter within `epsilon` of a null value. A flagged iteration is voided and the mutator is re-prompted with an anti-overparameterization constraint (operator-blinded to the sealed GT).

## Open questions

1. What symbolic simplifier? `sympy.simplify` is brittle on numeric residues; a custom rule set over `ast` might be more honest. This is a real engineering surface.
2. How to express "do not propose a model where parameter P_k collapses to null value" without leaking the sealed GT? This needs mutator-side wording that is operator-auditable.
3. What is `epsilon` for "within null value"? Absolute or relative? At what scale? Inherits from the sandbox_09 v2 `Rate_ref=1219.43 ≈ 1/C`-style detection, where the ratio was 4 sig figs. Needs calibration.
4. Does level 1 composition with R3b obviate level 2? Possibly — if every nesting-closed target routes to R3b, level 2 is unused. This would make GP-069 a seal-time-only gate, which is cleaner.

## Pre-decision: do NOT build level 2 yet

Level 1 is cheap and catches the sandbox_09/10 pathology. Level 2 is expensive and unproven. Build level 1 as a pre-seal checklist item in `docs/PRE_RUN_CHECKLIST.md` and revisit level 2 only if a GP-061 target ever clears level 1 and then still exhibits fit-collapse.

## Cross-references

- `GP-023_sandbox_09_post_run_audit.md`
- `GP-023_sandbox_10_nesting_collapse_audit.md`
- `research_areas/private/specs/active/GP-061_component_b_generalization_target_spec.md` (v4 amendment)
- `docs/PRE_RUN_CHECKLIST.md` — target for level 1 checklist insertion
- AGENTS.md §spec-format — seam first, spec after debate settles
