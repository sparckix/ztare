# Exceptional-divisor obstruction to a uniformly bounded contact

**Status:** theorem candidate; central divisor argument and degree orientation
independently audited, generic-field bivariate factorization kernel-ratified

## Eigenquestion

Can one compatible Hamiltonian contact

\[
H_s\circ F_s=F_0\circ\Psi_s,\qquad \det DH_s=1,
\]

have uniformly bounded spatial degree on both its target and source
coefficients?

The earlier degree-square reduction only gave such a contact as a route to a
plane Keller counterexample.  The weighted exceptional divisor supplies a
stronger discriminator.

This argument is killed by any of:

- failure of uniform coefficient degree to algebraize both maps over
  \(K=\mathbb Q((s))\);
- failure of the exact weighted-volume identity;
- another irreducible factor in \(\gamma\circ\Psi_K\);
- failure of a plane polynomial map preserving the linear exceptional
  coordinate to be triangular;
- or failure of generic-degree multiplicativity in the contact square.

## Algebraization

Suppose there are constants \(D_H,D_\Psi\) such that every coefficient of
\(H_s-\mathrm{id}\) has target degree at most \(D_H\), and every coefficient
of \(\Psi_s-\mathrm{id}\) has source degree at most \(D_\Psi\).

Only finitely many monomials occur.  Their scalar coefficient series assemble
into polynomial maps

\[
H_K\in K[P,Q]^2,\qquad
\Psi_K\in K[v,t]^2.
\]

The coefficientwise contact and determinant identities become polynomial
identities over \(K\).

## The exceptional divisor forces the source map to be triangular

Let

\[
\gamma=1-\frac32v+t.
\]

The exact source-volume identity attached to an area-preserving target
contact is

\[
\gamma(\Psi_K)^2\det D\Psi_K=\gamma^2.
\]

Put \(G=\gamma\circ\Psi_K\) and \(J=\det D\Psi_K\).  The equation

\[
G^2J=\gamma^2
\]

holds in the UFD \(K[v,t]\).  Its right side is the square of one irreducible
linear polynomial.  Hence

\[
G=c\gamma^a,\qquad a\in\{0,1\},\quad c\in K^\times.
\]

The equation also gives \(J\ne0\), so \(\Psi_K\) is dominant.  Therefore the
pullback of the nonconstant function \(\gamma\) cannot be constant, excluding
\(a=0\).  It follows that

\[
\gamma\circ\Psi_K=c\gamma,\qquad
\det D\Psi_K=c^{-2}.
\]

Choose affine coordinates \((x,y)=(\gamma,v)\).  In these coordinates write

\[
\Psi_K(x,y)=(cx,\phi(x,y)).
\]

Its constant Jacobian gives

\[
c\,\partial_y\phi=c^{-2}.
\]

Thus

\[
\phi(x,y)=c^{-3}y+p(x)
\]

for a polynomial \(p\in K[x]\).  Consequently \(\Psi_K\) is a triangular
polynomial automorphism and its generic degree is

\[
m=1.
\]

## Generic-degree contradiction

The special quotient map \(F_0\) has generic degree three and the generic
deformed quotient map \(F_s\) has generic degree four.  Since
\(\det DH_K=1\), the target map is dominant and generically finite; let its
generic degree be \(h\ge1\).

Generic degrees in

\[
H_K\circ F_s=F_0\circ\Psi_K
\]

therefore give

\[
4h=3m.
\]

But \(m=1\), so

\[
4h=3,
\]

which has no positive integral solution.

Hence:

\[
\boxed{
\text{no compatible Hamiltonian contact has both coefficient towers in
fixed polynomial-degree stages.}
}
\]

This conclusion is unconditional.  It does not use the two-variable
Jacobian conjecture.

## Scope

The theorem forces joint target/source escape.  By itself it does not prove
that the source coefficients are unbounded when the target gauge is allowed
unbounded degree, nor does it give a quantitative lower rate.

Combined with the root-cover construction, it places the normalized family
between:

\[
\max\{\deg[s^n](H_s-\mathrm{id}),
      \deg[s^n](\Psi_s-\mathrm{id})\}
\le 2n+O(1)
\]

for one compatible contact, while no compatible contact has a uniform
degree ceiling on both sides.

## Intended formal surface

The kernel target encodes the invariant terminal chain:

1. \(G^2J=\gamma^2\) in a polynomial UFD forces
   \(G=c\gamma\);
2. a plane polynomial map with first coordinate \(c\gamma\) and constant
   Jacobian is triangular and has generic degree one;
3. \(4h=3\) has no positive natural-number solution.

The deterministic bridge separately binds the displayed weighted-volume
identity, the degree-\(4/3\) quotient certificates, and the uniform-degree
algebraization hypothesis.

The compiled source is
[`AxiomPackJacobianExceptionalDivisorObstruction.lean`](../../../ztare_proofs/ZtareProofs/AxiomPackJacobianExceptionalDivisorObstruction.lean).
Its factorization lemmas are stated over an arbitrary field, so they apply to
\(K=\mathbb Q((s))\).  Provider-free LeanMill ratification of
`exceptional_divisor_bivariate_obstruction_certificate` closed with:

- zero provider calls;
- closure-record SHA-256
  `25479e36d2416508a44ea13ced4bb1b85d0f51f48dc35ce27b5e4be98c914bd1`;
- kernel-parity SHA-256
  `f5ff3e93e4d04c34620e2499b9583df66b2639a47c85b203ba864fd6c5f07f31`;
- governed closure SHA-256
  `5b26e9fd5ea0002db7842f36bb445a5371d6d2ecf23a5332a8c12af66bf3852f`;
- matched negated-conclusion control and axiom allowlist passed.

An independent audit re-expanded
\(\det DF_s=\det DF_0=-\gamma^2\), checked dominance, affine conjugation,
generic-degree orientation, and every algebraization hypothesis.  It found
no counterexample.  Historical priority remains unconfirmed.
