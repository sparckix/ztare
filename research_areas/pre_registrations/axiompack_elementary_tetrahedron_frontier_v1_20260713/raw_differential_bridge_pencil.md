# Raw elementary-tetrahedron / differential-mode bridge pencil

Date: 2026-07-15

## Eigenquestion

Does the elementary type-2 tetrahedron equation plus either frozen finalist
normalization force the differential-mode axioms after the coordinate exchange

\[
F(a,b,c)=T(b,a,c)
\]

at the level of arbitrary ternary operations, without first replacing the
middle slices by permutations?

## Falsifiable claim

1. For every ternary operation `T`, the conjunction of the tetrahedron equation
   and finalist-zero laws is equivalent to `F` being a hemisemiprojection
   differential mode.
2. For finalist one, the tetrahedron equation, the two finalist-one laws, and
   injectivity of every middle slice imply that `F` is a differential mode with
   source fixing and last-pair projection.

The first statement uses no cancellation, finiteness, or slice bijectivity. The
second retains exactly the base theory's middle-injectivity hypothesis.

## Proof skeleton

### Finalist zero, forward

The existing raw descent file proves:

- `T x x z = x`;
- right absorption `T x y (T z w v) = T x y w`;
- left-label descent `T (T x y z) w v = T y w v`;
- global commutation of middle translations.

Under `F(a,b,c)=T(b,a,c)`, source fixing gives idempotence and global
commutation gives left normality. Right absorption followed by left-label
descent gives

\[
F(x,F(y_1,z_1,z_2),F(y_2,t_1,t_2))=F(x,y_1,y_2),
\]

which is left reductivity. The coordinate form of the finalist-zero laws then
becomes the known hemisemiprojection specialization.

### Finalist zero, reverse

Differential-mode axioms imply the tetrahedron equation after coordinate
exchange. Hemisemiprojection gives source fixing; the existing
`differentialFinalistZero_iff_hemisemiprojection` theorem recovers the exact
coordinate form of both finalist laws, which transports back to `T`.

### Finalist one

The existing raw finalist-one proof gives source fixing and global commutation
from the tetrahedron equation, middle injectivity, and the two normalization
laws. Its cancellation argument also establishes right-label constancy.
Expose that lemma, derive left-label descent from the tetrahedron equation, and
obtain left reductivity as above. The existing coordinate theorem turns the
normalization into last-pair projection.

## Discriminating test

Add raw-operation theorems to `AxiomPackDifferentialModeBridge.lean` and compile
the umbrella `ZtareProofs.lean`. Audit the resulting declarations with
`#print axioms`.

Success requires:

- an F0 biconditional over arbitrary `T`;
- an F1 forward implication using `Function.Injective` only;
- no new axioms, `sorry`, finiteness, `Equiv.Perm`, or implicit surjectivity in
  either raw theorem.

## Kill conditions

- Left reductivity requires a cancellation or orbit-representative assumption
  absent from the candidate statement.
- The F0 reverse implication recovers only a weaker normalization.
- The coordinate exchange proves the wrong tetrahedron orientation.
- Compilation adds a trust assumption beyond the ordinary imported logic.

## Claim boundary and recurrence check

The 2008 differential-mode paper defines and classifies the target variety and
its hemisemiprojection specialization. This test can establish only the exact
cross-theory implication/equivalence. A bounded terminology audit has not found
that bridge in the checked primary sources; publication-level novelty remains
subject to broader bibliographic and expert review.
