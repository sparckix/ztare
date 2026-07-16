# T2 reconstruction: orbit-label obstruction pencil

Date: 2026-07-15

## Eigenquestion

Once an elementary type-2 tetrahedron operation has the orbit-action form

\[
T(x,y,z)=\kappa(o(x),o(z))\mathbin{\cdot}y,
\]

what additional condition is exactly equivalent to the reconstruction in
preprint Question 9.12 / published Question 9.69 of Bardakov et al.?

## Candidate statement

Let an abelian group `G` act on `X`, let `o : X -> O` be invariant under the
action, and let `kappa : O -> O -> G`.  Assume the diagonal labels act as the
identity, as they do for finalist one.  Fix `c : X`.  With the identity unary
extraction, the paper's reconstructed operation is

\[
\widehat T_c(x,y,z)
 =T(x,T(c,y,z),c)
 =\bigl(\kappa(o(x),o(c))\kappa(o(c),o(z))\bigr)\mathbin{\cdot}y.
\]

Therefore reconstruction at `c` is equivalent, at action level, to

\[
\kappa(o(x),o(z))\mathbin{\cdot}y
 =\bigl(\kappa(o(x),o(c))\kappa(o(c),o(z))\bigr)\mathbin{\cdot}y
\]

for all `x,y,z`.  If the action is faithful, this is equivalent on every
indexed orbit pair to the label factorization

\[
\kappa(o(x),o(z))
 =\kappa(o(x),o(c))\kappa(o(c),o(z)).
\]

Thus the reconstruction question asks whether the extraction hypotheses force
the label matrix to factor through one chosen orbit.  The T2-groupoid laws do
not force that condition.

## Stronger raw finalist-one corollary

The orbit syntax can be eliminated.  Suppose `T` has injective middle slices
and the finalist-one consequences

\[
T(x,x,z)=x,\qquad T(x,y,x)=y.
\]

If reconstruction holds through one basepoint `c`, then

\[
T(x,T(c,x,z),c)=T(x,x,z)=x=T(x,x,c).
\]

Injectivity of `T(x,-,c)` gives `T(c,x,z)=x`.  Substitution back into the
reconstruction identity gives

\[
T(x,y,z)=T(x,y,c).
\]

Taking `z=x` and using `T(x,y,x)=y` shows `T(x,y,z)=y` everywhere.  The
converse is immediate.  Consequently, within the middle-injective
finalist-one class, reconstruction through one basepoint is equivalent to the
middle projection law.  Every nonprojection member of this class answers the
published question negatively.

## Finite witness specialization

For finalist one, the translation group is `C2 = {1,s}` acting by swapping
`0` and `1` and fixing `2`.  Its two orbits are

\[
A=\{0,1\},\qquad B=\{2\},
\]

and the label matrix is

\[
\kappa(B,A)=s,\qquad
\kappa(A,A)=\kappa(A,B)=\kappa(B,B)=1.
\]

- If `o(c)=A`, the pair `(B,B)` violates factorization:
  `1 = kappa(B,B) != kappa(B,A) kappa(A,B) = s`.
- If `o(c)=B`, the pair `(A,A)` violates factorization:
  `1 = kappa(A,A) != kappa(A,B) kappa(B,A) = s`.

This explains why every basepoint fails and recovers the explicit mismatches
already checked by the finite certificate.

## Proof skeleton

1. Expand both occurrences of the orbit-action operation.
2. Rewrite the orbit of the inner action using orbit invariance.
3. Combine the two actions with `smul_smul`.
4. Use commutativity only to match the selected product orientation.
5. For the reverse implication from equality of reconstructed operations to
   label equality, quantify over `y` and use faithfulness of the action.
6. Instantiate the abstract criterion with the finalist-one orbit map and
   label, or retain the existing direct finite mismatch theorem as the small
   counterexample certificate.
7. Prove the raw finalist-one corollary directly from middle injectivity,
   source fixing, and diagonal identity, without orbit-action assumptions.

## Attack vectors and counterattacks

- **Unary extraction is not the identity.**  For finalist one,
  `T(c,x,c)=x`; the paper's inverse-slice hypothesis forces every admissible
  unary map to be the identity.  If this derivation fails under the published
  orientation, the criterion must be generalized to a nontrivial diagonal
  inverse rather than asserted as written.
- **Action is not faithful.**  Equality of labels is then too strong.  Retain
  the action-level iff, and state group-element factorization only under
  `FaithfulSMul`.
- **The orbit map is not action invariant.**  Then the inner label need not
  retain `o(z)`.  The orbit-action representation supplies invariance; without
  it, this theorem does not apply.
- **The paper reconstructs with the other extracted operation or argument
  order.**  Compare directly against Proposition 9.11 / published Proposition
  9.68 before formalization.  The displayed formula is
  `x R (y circle z) = T(x,{T(c,y,z)},c)`, matching the expansion above.
- **A later source already gives the same obstruction or counterexample.**
  This removes the originality claim but does not affect the theorem.

## Recurrence check

The 2008 differential-mode sources classify orbit/block structure and
commuting translations.  The current bounded review has not located this
specific basepoint-factorization criterion in the elementary type-2
tetrahedron literature.  Forward-citation review of the 2024 published paper
is still in progress.

## Intended formal surface

Add general lemmas near the orbit-action definitions:

1. an expansion theorem for `T(x,T(c,y,z),c)`;
2. an action-level reconstruction iff;
3. a faithful-action label-factorization iff.

The finite counterexample remains a separate theorem.  The general criterion
must not import or depend on that witness.

Also add a raw theorem to the finalist-one bridge stating that, under the
already proved finalist-one hypotheses, the basepoint reconstruction identity
is equivalent to the middle projection law.  This theorem must not depend on
finiteness, the orbit quotient, or the explicit witness.

## Kill conditions

- Any source-orientation mismatch changes the reconstructed term.
- A missing orbit-invariance or faithfulness hypothesis is used silently.
- The action-level equality fails to be equivalent to the original universal
  reconstruction statement.
- The factorization condition follows automatically from the exact T2 laws;
  this would contradict the finite witness and indicate a formalization bug.
