# GP-211 Paper-8 Lean Proofs (Descent Invariance Under Equivalence) — Public Claim Summary

> Public-evidence surface for a sealed category-theory finding with a
> Lean-formalizable structure. Working directory private; cited by
> `docs/public_claim_register.md` under *Consciousness-Ascription
> Governance* (as one of the formal-adjacent follow-on artifacts).

## One-line claim (a sharpening, not a discovery)

If two sites `(C, J_C)` and `(D, J_D)` are categorically equivalent
via a functor `F : C → D`, descent (sheaf / effective descent) is
**not** automatically transferred between presheaves on the two sites
*unless the Grothendieck topologies correspond "on the nose"* under
the equivalence — i.e., `F` must preserve covering sieves strictly,
not only up to isomorphism. Categorical equivalence + topology
matching "up to isomorphism" is **insufficient** for descent
invariance.

## What this argues

The naive (rival) hypothesis is that equivalence of categories is
enough — "equivalence of site structure" should make all
presheaf-theoretic invariants (including sheaf and descent
properties) transfer regardless of topology subtleties. The thesis
demonstrates that this is **false** unless the pushforward topology
`F_*J_C` coincides with `J_D` strictly. If the pushforward and
target topologies do not match strictly, attempts to transfer the
sheaf property for all presheaves can fail.

The structural counterexample is independently checkable in Lean /
Mathlib: `CategoryTheory.Sites.Sheaf.pushforward` and the related
constructions require strict compatibility hypotheses, and no
general lemma exists in Mathlib that transfers descent or sheaf
properties just from categorical equivalence alone.

## Why this matters for the consciousness work

The descent-invariance question is central for any framework
that wants to transport consciousness-ascription verdicts across
equivalent "sites" (representations of the substrate). The result
here sharpens the consciousness-ascription governance work
(AID-MCVP and the veto protocol) by establishing that "equivalent
representation" alone is *not* a sufficient invariant for verdict
transport — the topology of evidence must correspond strictly, not
just up to isomorphism, before a verdict transferred across the
equivalence is admissible.

## Honest framing — a sharpening, not a discovery

This is a *sharpening* of a well-understood corner of categorical
sheaf theory, not a discovery. The contribution is the explicit
Lean-formalizable counter-example that closes a loose framing that
appears in some downstream literature (and in earlier drafts of the
consciousness work) — *not* a new theorem in category theory.

## Retest tag

*Methodology / framework claim with Lean formalization in flight.*
The Lean proof is staged but not yet fully closed at the
sealed-reference level; the structural claim and the Mathlib API
support are documented. A fully closed Lean proof tree against
Mathlib would convert this into a sealed formal result.

## Cross-reference

- Public claim register entry: `docs/public_claim_register.md`,
  section *Consciousness-Ascription Governance*
  (formal-adjacent follow-on work).
- Working directory (private): `projects/gp211_paper8_lean_proofs/`.
- Sibling consciousness-track projects (private):
  `projects/gp169_consciousness_ascription_audit/`,
  `projects/gp210_consciousness_theory/`,
  `projects/gp212_consciousness_omega_audit/`.
