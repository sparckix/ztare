# Orbit-action classification pencil

Date: 2026-07-15

## Eigenquestion

For the two frozen finalist pairs, what conditions do the laws impose on the
abelian orbit-action label

\[
T(x,y,z)=\kappa(Hx,Hz)\mathbin{\cdot}y,
\]

and do those conditions also suffice for the tetrahedron equation and the
corresponding pair?

## Target input

This is a non-NS algebra problem, so there is no Clay-equivalent input.  The
inputs are the middle-coordinate permutation hypothesis, the tetrahedron
equation, and one frozen finalist pair.  The representation layer is
`AxiomPackOrbitAction.lean`; the equational descents are the two finalist bridge
files.

## Candidate classification

- Finalist zero is equivalent, on an orbit action, to every
  `kappa(Hx, Hz)` fixing `x` and `z`.  Quantifying over representatives makes
  this pointwise fixing of both indexed orbits.
- Finalist one is equivalent, for a faithful action, to
  `kappa(Hx, Hx) = 1` and every `kappa(Hx, Hz)` fixing `x`.  The faithfulness
  assumption is necessary to recover equality of group elements from equality
  of their actions.
- In the canonical translation-orbit representation the acting group is the
  generated subgroup of permutations, hence its action is faithful.  The
  canonical label must therefore satisfy the corresponding constraints on all
  generated orbit points.

The claim is equality of the displayed operation with its canonical
translation-orbit reconstruction.  No isomorphism classification is asserted.

## Proof skeleton

1. Orbit invariance reduces the tetrahedron equation to commutation of the two
   label products; the acting group is abelian.
2. For finalist zero, substitute `(x,x,x,z)` into the first law to obtain first
   indexed-orbit fixing, and `(x,z,z)` into the second law to obtain second
   indexed-orbit fixing.  Conversely, simplify each law using orbit invariance
   and the appropriate fixing condition.
3. For finalist one, simplify diagonal inverse to
   `kappa(Hx,Hx) . y = y` for every `y`; faithfulness gives
   `kappa(Hx,Hx)=1`.  Cross diagonal then gives first indexed-orbit fixing.
   The reverse implications are direct simplifications.
4. Apply the bridge descent to obtain source-fixing and commuting translations,
   then the existing factor-through-orbits lemmas.  The canonical label fixes
   the whole first generated orbit.  For finalist zero, its derived target
   diagonal supplies the analogous second-orbit statement.  For finalist one,
   its normalization supplies the diagonal label identity.

## Kill conditions

- Any converse needs an unmentioned faithfulness assumption or constrains label
  entries outside the image of the orbit map.
- The canonical theorem proves fixing only one chosen representative rather
  than every point in its generated orbit.
- The construction proves the finalist laws but omits tetrahedron coherence.
- Compilation introduces `sorry`, a new axiom, or an implicit isomorphism claim.

## Recurrence check and formal surface

The existing orbit-action file proves tetrahedron coherence, factorization,
source-orbit fixing, and diagonal identity.  It does not contain the two exact
law/label converses or second-orbit fixing.  The intended addition is one
separate Lean module importing the orbit-action and both bridge modules, with
general construction/iff theorems followed by canonical-label corollaries.
