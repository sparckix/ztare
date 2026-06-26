# Monotone comparative statics — GENERAL Topkis / Milgrom–Roberts (ordinal complementarity + existence + strong set order)

The formal core of "strategic fit": when a choice and a parameter are **complements**, the optimal choice rises
with the parameter — the rigorous backbone of why a tightly-fitted activity system resists piecemeal imitation.
This blueprint targets the GENERAL theorem, not the elementary corollary: choices multi-dimensional (a lattice),
optima possibly NON-unique, the complementarity **ordinal** (utility-free, single-crossing — not cardinal real
differences), and the optimal choices shown to **exist** before their monotonicity is asserted. None of this
vocabulary is in Mathlib — theory-building. Probe Mathlib with Loogle and the warm checker; decompose however
the kernel teaches. A non-closure is an honest gap, never a fake closure, and never a silent restriction.

## Theory file
topkis_general_theory.lean

The bespoke vocabulary Mathlib lacks — establish each once, over whatever order structure the result requires:
- **Ordinal complementarity (the single-crossing property)** between choice and parameter: raising the choice
  (from x to a higher x') that is weakly better at a lower parameter t stays weakly better at any higher
  parameter t' — the sign of the choice-gain is monotone in the parameter, with NO cardinal subtraction.
  (Cardinal *increasing differences* is its special case; state the ordinal form as the primitive.)
- **(Quasi-)supermodularity** of the objective in the choice on a lattice — the ordinal lattice complementarity
  that makes the set of optima a sublattice.
- The **strong set order (Veinott)** on sets of optimal choices.

## Target
Let `f(x, t)` be an objective in a choice `x` (ranging over a lattice — choices may be multi-dimensional) and a
parameter `t`, with **ordinal (single-crossing) complementarity** between choice and parameter. Prove BOTH:
1. **Existence** — under the conditions your formalization actually needs (e.g. a complete lattice with an
   order-continuity / compactness condition on `f`), the set of maximizers of `f(·, t)` is **non-empty**.
2. **Monotonicity** — as `t` rises, the set of maximizers rises in the **strong set (Veinott) order**: the
   optimal-choice correspondence is nondecreasing, with optima NOT assumed unique.

State and prove existence and monotonicity; do **not** let an empty maximizer set make monotonicity vacuous.

## Idea
The content is the complementarity, not the algebra, and it is **ordinal**: single crossing means a higher
choice never becomes relatively worse as the parameter rises, so an optimizer facing a higher parameter never
prefers a lower choice. Prefer the ordinal / quasi-supermodular formulation over cardinal real-valued
differences wherever the mathematics allows. Establish EXISTENCE before (or alongside) monotonicity so the
comparative-statics claim is not vacuous on an empty argmax. If the fully general statement is out of reach,
surface the exact obstruction as an honest gap and name which added hypothesis (a cardinal codomain, a lattice
completeness, an order-continuity) would close it — never silently restrict the theorem.
