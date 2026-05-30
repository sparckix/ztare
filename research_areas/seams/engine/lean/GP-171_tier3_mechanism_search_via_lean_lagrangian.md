---
id: GP-171
status: SEAM OPEN — Tier-3 mechanism search
summary: Apply existing Lean+G3+G4+G5+Cage stack to search the Lagrangian space for a generator of the gp163d Galaxy-Cluster Bridge form. Kepler→Newton template, mechanized.
---

# GP-171 — Tier-3 Mechanism Search via Lean-Audited Lagrangian Generation

> **Seam metadata** · `seam_id:` GP-171 · `track:` engine · `status:` **SEAM OPEN.** Awaiting panel debate before implementation. · `last_updated:` 2026-05-08


**Status:** SEAM OPEN
**Created:** 2026-04-27 (post gp163d v3.1 substrate fix; bridge form verified across A+B+C; user inversion of Tier-3 from "needs theoretical physicist" to "instrument is there")
**Owner:** Claude (orchestrator) — to be debated jointly before implementation
**Visibility:** private until first iter ships

---

## Problem statement

The gp163d_unified_accel run produced a 2-parameter form (Galaxy-Cluster Bridge) that jointly fits SPARC galaxies + CLASH clusters + Chae wide binaries at MRE ≤ 0.30 across ~10 dex of g_bar. Sacred-DNA locked. NFW-distinguishable.

This is **Tier 1** unification: phenomenological scaling law. The standard move from here is **Tier 2** (predictive use on a regime not in the training set) and **Tier 3** (derivation from a Lagrangian / action principle).

Conventional wisdom: Tier 3 requires a theoretical physicist to write the Lagrangian, derive equations of motion, verify the reduction to the bridge.

**Inversion**: the apparatus already contains every primitive that derivation needs. The Kepler→Newton chain is structurally the same as bridge→Lagrangian, and we have it as code:

| Kepler→Newton step | Apparatus primitive | Status |
|--------------------|---------------------|--------|
| Empirical scaling law | gp163d Sacred-DNA bridge form | ✅ shipped |
| Asymptotic constraints | Evidence Set B (Newtonian limit, MOND-low-x) | ✅ shipped |
| Dimensional consistency | GP-170 Symbolic Logic Cage | ✅ shipped |
| Symbolic derivation | sympy + (gap: functional_derivative primitive) | ⚠ one gap |
| Proof verification | G5 translation_diff (Lean compiler pre/post) | ✅ shipped |
| Ansatz soundness | G3 ansatz_survivor (proof shortness) | ✅ shipped |
| Surveyability | G4 proof_surveyability (sketch wrapper) | ✅ shipped |
| Falsifiability | G-FALSIFY gate | ✅ shipped |
| Anti-circularity | G-CIRC gate | ✅ shipped |

The instrument is there. The gap is one primitive: **`functional_derivative`** — a sympy-backed variational-calculus wrapper that takes a Lagrangian density `L[φ, ∂φ, g_μν, ψ_matter]` and returns `δL/δφ` symbolically. Once shipped, the apparatus can search the space of Lagrangians the same way it searches the space of parametric forms.

## Substrate spec — gp163e_tier3_mechanism

**Goal**: produce a Lagrangian `L` whose Euler-Lagrange equations reduce, in the spherical-symmetry weak-field limit, to the gp163d Sacred-DNA bridge form (or a strictly tighter form), with all sigmoid centers and `η = 0.832` derived rather than fitted.

**Substrate inputs (visible to mutator)**:
1. **Sacred-DNA bridge form** — pinned, must be reproduced.
2. **Asymptotic constraints**:
   - `y → x` as `x → ∞` (Newtonian / Solar System limit)
   - `y → √(c₀ · x)` as `x → 0` (MOND-like deep-MOND)
   - `c_eff` smooth in (M, r), monotonic in m, bounded by a fixed scale
3. **Dimensional rules** (for Cage gate enforcement):
   - `[L] = [energy density]` in natural units
   - All terms in `L` must have consistent dimensions
4. **Restricted Lagrangian class** — to keep the search tractable, mutator chooses from:
   - Scalar-tensor: `L = R/16πG + L_φ[φ, ∂φ] + L_matter[ψ_matter, φ]`
   - Modified-action f(R): `L = f(R)/16πG + L_matter`
   - TeVeS-flavored: `L = R/16πG + L_φ + L_vector + L_matter[coupled]`
   - MOG-flavored: `L = R/16πG + L_χ[χ, μ]` with running gravitational constant
   - AQUAL: `L = R/16πG + (a₀² / 8πG) · F(|∇φ|² / a₀²) + L_matter[ρ + ∂φ coupling]`

**Substrate falsification gates**:
- **G-CIRC**: any Lagrangian that defines `c_eff` directly as a free function (i.e., `L` contains `c_eff(M, r)` as a primitive) is circular. Rejected.
- **G-FALSIFY**: any Lagrangian whose equations of motion don't make a prediction beyond the bridge (i.e., the same MRE on the same data) is not falsifiable. Rejected.
- **G3 ansatz_survivor**: any Lagrangian whose derivation chain takes more than N steps (Lean-counted) is over-fit by parameter laundering. Rejected.
- **Symbolic Logic Cage** dimensional gate: any term in `L` with inconsistent dimensions is rejected at admission.
- **Newtonian-limit gate**: equations of motion must reduce to Newton's `F = GMm/r²` to ≤1e-9 fractional error in the deep-Newtonian limit (g_bar > 1e-3 m/s²).
- **Bridge-reproduction gate**: equations of motion must reproduce the Sacred-DNA bridge MRE on gp163d v3.1 substrate; if MRE > 0.35, the Lagrangian is rejected as "fits worse than the phenomenology it's supposed to derive."

**Score**:
- Tier-3 score = `bridge_MRE_match` × `simplicity_bonus` × `derivation_short_bonus`
- Where `simplicity_bonus = exp(-K_extra)` for K extra free parameters added to the Lagrangian (Lagrangian with 0 free params beyond G and a₀ is the holy grail)
- `derivation_short_bonus = exp(-N_steps / N_baseline)` where N_steps is Lean-counted derivation chain length

**Success criterion**: a Lagrangian L with ≤ 2 free dimensional constants (e.g., G and a₀) whose equations of motion reduce to the bridge form with MRE ≤ 0.30, with derivation chain Lean-verifiable in ≤ 50 steps.

## Primitive policy: discover, do not pre-build

**Correction (2026-04-27, post-panel debate)**: an earlier draft of this seam pre-specified a `functional_derivative` primitive as a half-day prerequisite. This was wrong by apparatus design.

The apparatus already has:
- `src/ztare/primitives/draft_primitives.py` — generates primitive candidates from incident traces
- `src/ztare/primitives/approve_primitive.py` — operator-approval flow
- `src/ztare/primitives/primitive_library.py` — registry

Per existing seam protocols, the mutator (gpt-5.5) proposes Lagrangians AND any symbolic operations it needs to reduce them (functional derivatives, weak-field expansion, spherical-symmetry reduction, PPN extraction). When a candidate references a primitive that isn't in the library, `draft_primitives.py` drafts the candidate primitive from the incident; `approve_primitive.py` approves it; the registry rebuilds. This is the Karpathy ALU/RAM pattern applied to the operator layer: ALU stays minimal, primitives accumulate as the apparatus encounters new symbolic moves.

gpt-5.5 has the world knowledge for chameleon scalar-tensor, f(R), AQUAL, MOG, TeVeS Lagrangians and the standard operations to reduce them (variational calculus, weak-field expansion, spherical symmetry, PPN parameterization). The substrate's job is to audit, not to provide. Let the mutator bring the math.

**No primitives are pre-required.** The substrate ships as soon as the gate semantics below are enforced. New primitives the mutator references get drafted on first use via the existing draft/approve seam.

## Falsification design

The Tier-3 search has a known failure mode: any Lagrangian with enough free parameters can fit anything. Defense:

1. **Lean derivation length** (G3 ansatz_survivor) — a derivation that takes 200+ symbolic steps is parameter-laundering disguised as math.
2. **Cross-substrate audit** — the same Lagrangian must reproduce known Solar-System tests (perihelion precession of Mercury, light bending, time delay) within their published precision. Add Solar-System data as a sanity-class.
3. **Anti-circular Cage** (G-CIRC) — fitted constants of the bridge form (m=11.43, r=1.83, etc.) cannot appear as free parameters in L.
4. **Cosmological consistency** — at the Lagrangian level, the form should have well-defined cosmological perturbation equations. If L breaks structure formation, it's wrong.

## Open questions for panel debate

1. **Restricted vs. open Lagrangian class**: should we restrict to scalar-tensor / TeVeS / MOG / AQUAL, or allow arbitrary L? Restricted is tractable but may miss the right answer; open is intractable.
2. **Solar-System sanity vs. bridge MRE**: should Solar-System be a hard gate (any failure = reject) or a tiered scoring component? Hard gate prevents drift but may reject candidates that need iterative refinement.
3. **Cosmological consistency**: do we add CMB/BAO constraints now or defer to a future tier? Adding now is rigor; deferring is execution speed.
4. **Functional-derivative primitive surface**: thin sympy wrapper or full IR with our own type system? Thin is faster; IR is more auditable.
5. **What is the right MRE bar for "successful derivation"?**: the bridge has MRE 0.28 on its training. Any L that derives a form with MRE 0.50 is worse than the phenomenology — clearly wrong. Any L with MRE 0.20 has a parameter-laundering smell. Bar = 0.30 (matches the bridge) is honest.
6. **Iter budget**: bridge form took 8 iters at gp163d v3. Tier-3 search probably needs 20-50 iters. Acceptable budget?

## Implementation plan (after panel debate)

1. Ship `functional_derivative` primitive + register in primitive library.
2. Build gp163e_tier3 substrate: features = bridge form parameters + asymptotic constraint flags + dimensional rule set; harness = Euler-Lagrange evaluator + bridge-MRE comparator.
3. Add Lagrangian-class taxonomy to evidence.txt (the 5 framings above).
4. Wire G-CIRC, G-FALSIFY, dimensional Cage, Newtonian-limit gate, bridge-reproduction gate.
5. Smoke test with a known-good seed: AQUAL Lagrangian with the standard a₀ — should reduce to the deep-MOND limit at low g_bar and pass G-CIRC.
6. First production iter: gpt-5.5 mutator proposes from the restricted class; apparatus audits.

## Status

**SEAM OPEN.** Awaiting panel debate before implementation.
