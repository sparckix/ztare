# One-weight irreducible contraction over the coefficient ring

## Eigenquestion

Let `A` be a domain and let `h ∈ A[F]` be irreducible.  If `h` has only its
leading monomial,

\[
h=\operatorname{monomial}(\deg h,\operatorname{lc}(h)),
\]

must `h` either be an irreducible constant or be associated to the endpoint
variable `F`, without mapping `h` to `Frac(A)[F]`?

## Candidate theorem

The exact coefficient-ring statement is

```text
[CommRing A] [IsDomain A]
Irreducible h
-> h = monomial h.natDegree h.leadingCoeff
-> h.natDegree = 0 \/ Associated h X.
```

A UFD assumption is unnecessary.  The domain structure is enough for the
polynomial root/degree theorem and for `X` to be a nonunit.

## Proof skeleton

Split on `h.natDegree = 0`.  The zero-degree branch is returned unchanged;
an irreducible constant can arise from a nonunit irreducible coefficient and
must not be identified with `X`.

In the positive-degree branch, rewrite the one-weight equation as

\[
h=C(\operatorname{lc} h)X^{\deg h}.
\]

Evaluation at zero makes `0` a root of `h`.  Mathlib's
`Irreducible.not_isRoot_of_natDegree_ne_one` then forces
`h.natDegree = 1`: an irreducible polynomial over a domain with a root cannot
have any other positive degree.

Consequently

\[
h=C(\operatorname{lc} h)X.
\]

Apply irreducibility to this displayed factorization.  Since `X` is not a
unit, `C (leadingCoeff h)` is a unit.  Multiplication by that unit shows that
`h` and `X` are associated.

## Counterattacks and scope boundary

- The degree-zero disjunct is essential: irreducibility over a nonfield
  coefficient domain permits constant irreducibles.
- A nonunit leading coefficient in positive degree contradicts
  irreducibility through the displayed factorization.
- The case `X^n` with `n > 1` is excluded equivalently by its zero root and
  the irreducible-root degree theorem; no induction on `n` is needed.
- The one-weight equality is essential.  A general irreducible polynomial of
  degree greater than one need not have a root in `A`.
- Mapping irreducibility to `Frac(A)[F]` is deliberately avoided: such a map
  can turn a constant coefficient factor into a unit and would erase the
  branch this theorem must preserve.
- The result is a contraction lemma for one polynomial.  It does not prove
  that an eliminant is one-weight, irreducible, or nonconstant; callers must
  supply those facts.

## Discriminating test

The focused Lean module must compile over `[CommRing A] [IsDomain A]`, use no
fraction-field irreducibility transport and no UFD instance, preserve the
degree-zero branch, and conclude `Associated h X` in every positive-degree
case.  Its axiom audit must contain only Lean's standard logical axioms.

## Outcome

`FormalOneWeightIrreducibleContraction` passes direct focused compilation and
its named `lake build` target.  The theorem uses exactly `[CommRing A]
[IsDomain A]`; it imports no fraction-field construction and assumes no UFD.
The positive-degree proof makes zero a root, forces degree one by the
irreducible-root theorem, and then uses irreducibility once more to make the
constant factor a unit.  The degree-zero disjunct remains explicit.

`#print axioms` reports only `propext`, `Classical.choice`, and `Quot.sound`.
