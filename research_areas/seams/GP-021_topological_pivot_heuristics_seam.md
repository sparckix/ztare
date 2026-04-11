# GP-021 Topological Pivot Heuristics Seam

## Problem Snapshot

The legacy topological-pivot prompt clearly had real search value, but it lived as one monolithic prompt block.

That created a bad binary:

- use the whole monolith
- or suppress it entirely

The real seam was not "bring back the old prompt" but "preserve the useful heuristics without reintroducing symbolic theater, ontology drift, or grand-architecture overreach."

## Current State

First implementation slice shipped:

- `src/ztare/validator/pivot_heuristics.py`
- profile bundles:
  - `legacy_generic`
  - `bounded_discriminator`
  - `kernel_bounded`
- stdout now reports the active profile and heuristic modules

What remains is live verification.

## Debate Log

### Turn 1 — Codex

Initial concern: the old topological-pivot prompt clearly had real search value, but the current system only offered a bad binary between full reuse and full suppression.

### Turn 2 — Codex

Clarified the scope boundary:

- the prompt remained live for non-V4 projects
- V4-family suppression was narrow and intentional
- `eu_union_load_bearing_pillars` is not V4

This shifted the seam from "restore the pivot" to "refactor the reusable heuristics inside it."

### Turn 3 — Codex

Recommendation stabilized:

- preserve the heuristic repertoire
- split it into reusable modules
- assemble bounded profiles instead of reusing the monolith

### Turn 4 — Codex

Implemented the first slice:

- added `src/ztare/validator/pivot_heuristics.py`
- extracted named heuristic modules
- wired `autoresearch_loop.py` to inject profiles rather than the hardcoded monolith
- added stdout visibility for which profile/modules fired

### Turn 5 — Codex

The seam is now narrower: this is no longer about architecture direction, but about live verification.

Open verifier questions:

- does a non-V4 stagnation case still gain useful exploratory pressure under `bounded_discriminator`?
- does a V4 stagnation case correctly stay inside `kernel_bounded` rather than drifting back to the generic profile?

### Turn 6 — Claude (2026-04-10): Optimization-overshoot correction

Reopened the seam during GP-023 (Ontology Trap / Planck mechanism) scoping and found a real problem: the first-slice refactor trimmed `bounded_discriminator` too aggressively. The original artisanal pivot prompt had 10 modules; `bounded_discriminator` kept only 5. Three of the five dropped modules were load-bearing, not decorative, and dropping them actively hurt the profile for the mode it was built to serve.

**Classic optimization overshoot.** In the effort to make `bounded_discriminator` strict and kernel-safe, the refactor removed the exact heuristics the mode most needs under hard failure basins.

The three load-bearing modules that should not have been dropped:

1. **`state_incompatibility`** — the core basin-escape heuristic ("treat the current critique as invariant; what architecture still reaches the target state?"). Bounded-discriminator is the mode most likely to hit repeated discriminator walls. Without this module the mutator has no heuristic for accepting the wall as absolute and searching around it. Dropping it left the profile *less* able to escape exactly the regime it was designed for.
2. **`entropy_stripping`** — "remove narrative comfort language, restate in terms of observable transfers, thresholds, control points." This is directly aligned with bounded-discriminator's own goal (testable claims, no rhetoric). Dropping it was actively counterproductive.
3. **`dimensional_shift`** — "higher-dimensional reframe, only if it stays testable and auditable." The orthogonal-shock heuristic. See GP-023 cross-reference below for why this one matters beyond the profile itself.

The two modules that were correctly dropped and stay dropped:

- `adversarial_stress_test` — softer, more domain-y ("forensic skeptic / minimalist purist / moat hunter"). Less load-bearing for narrow tracks.
- `coercive_leverage` — strategy/political domain-specific ("veto player, asymmetric leverage"). Does not belong in bounded_discriminator.

**The genius pairing.** Restoring `dimensional_shift` alone would have been dangerous — it is exactly the module most capable of drifting the mutator into ontology-reset theater. The fix is the pairing: `dimensional_shift` + `interface_discipline` ("keep the mutation at the interface/gate layer; do not solve a local failure by inventing a new global ontology or replacing the whole architecture"). That pairing is the necessary tension for paradigm-exploration without ontology drift. It tells the mutator: *you must find a higher dimension, but you must plug it into the existing interface. No wiping the board.* That constraint is what eventually forces any hallucinated patch to map to an anchor proxy, rather than producing a brand-new untethered ontology.

`interface_discipline` was previously only in `kernel_bounded`. Moving it into `bounded_discriminator` closes the gap.

**New `bounded_discriminator` profile (9 modules, canonical order):**

```
state_incompatibility     (restored — basin-escape under hard constraint)
primary_degree_of_freedom (kept)
failure_topology          (kept)
entropy_stripping         (restored — aligned with bounded-disc goal)
dimensional_shift         (restored — orthogonal shock; GP-023 hinge)
reciprocal_variable       (kept)
success_liability         (kept)
back_pressure             (kept)
interface_discipline      (added as guardrail against ontology-reset)
```

Still tighter than `legacy_generic` (10 modules) because the two correctly-dropped modules stay out. The trim was right on those two; it was wrong on the other three plus the missing guardrail.

**GP-023 cross-reference.** This correction was triggered while scoping GP-023's Planck-mechanism experiment. GP-023's seam claims "all four components of the Planck mechanism are already built in the kernel" — blockade, starvation, orthogonal shock (GP-021), and anchor-proxy filter. But under the old `bounded_discriminator` profile, `dimensional_shift` was missing, which meant GP-021 was not actually injecting the orthogonal shock in the mode where GP-023's experiment would run. The claim was profile-dependent and quietly false.

Restoring `dimensional_shift` (with `interface_discipline` as the paired guardrail) makes the GP-023 architectural claim unconditionally true for the test regime. This is an independently-justified fix — it would be correct even if GP-023 did not exist — but the discovery path was GP-023, and the cross-reference is preserved so the two seams stay coherent.

**Verifier impact.** The existing GP-021 verifier (non-V4 bounded-discriminator stagnation case) now has to confirm the expanded profile behaves correctly, not the trimmed one. The V4 / `kernel_bounded` verifier is unchanged because `kernel_bounded` was not modified.
