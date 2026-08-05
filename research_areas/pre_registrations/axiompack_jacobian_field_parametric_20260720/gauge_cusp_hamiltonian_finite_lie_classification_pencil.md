# Cusp-Hamiltonian finite Lie classification pencil

**Status:** exact locally-finite adjoint classification completed

## Eigenquestion

Let

\[
H=P^3+9Q^2
\]

and equip \(\mathbb Q[P,Q]\) with the campaign Poisson bracket.  If a
finite-dimensional polynomial Hamiltonian Lie algebra contains \(H\), must
it be abelian and contained in \(\mathbb Q[H]\)?

The normalized target seed is a nonzero scalar multiple of \(H\).  A
positive answer would classify every finite-dimensional target algebra
compatible with that seed, including higher-weight extensions that are not
visible in \(\langle P^3,PQ,Q^2\rangle\).

## Candidate mechanism

Use cusp weights

\[
\operatorname{wt}(P)=2,\qquad \operatorname{wt}(Q)=3.
\]

Then \(H\) has weight six and

\[
D=\operatorname{ad}_H
\]

raises cusp weight by one.  If \(G\) belongs to a finite-dimensional
\(D\)-invariant polynomial space, the sequence \(D^nG\) cannot have
unbounded weight.  Hence \(D^NG=0\) for some \(N\).

It remains to identify the generalized kernel.  On the cusp \(H=0\), use

\[
P=-9u^2,\qquad Q=9u^3.
\]

The restricted derivation should be a nonzero scalar multiple of
\(u^2\partial_u\).  Its iterates kill only constants in \(\mathbb Q[u]\).
Therefore \(D^NG=0\) implies

\[
G-c\in(H).
\]

Since \(D(H)=0\), division by \(H\) and induction on polynomial degree
should give

\[
\bigcup_{N\ge1}\ker D^N=\mathbb Q[H].
\]

## Discriminating calculation

1. Verify the cusp parametrization and the induced derivation on
   \(\mathbb Q[u]\).
2. Check the exact monomial iteration law for \(u^k\).
3. Verify that \(H\) is the kernel generator of the parametrization.
4. Combine weight growth with the generalized-kernel calculation to
   classify a finite-dimensional \(D\)-invariant space.
5. Stress constants, multiples of \(H\), and a noncentral generator such
   as \(P\).

## Success and kill conditions

The classification succeeds if every finite-dimensional Hamiltonian Lie
algebra containing \(H\) is contained, modulo constants, in
\(\mathbb Q[H]\), and is therefore abelian.

It is killed by a polynomial \(G\notin\mathbb Q[H]\) whose iterated
\(\operatorname{ad}_H\)-orbit is finite-dimensional.

## Claim boundary

This is a target-algebra theorem.  It does not show that a
coefficientwise-finite staircase of polynomials in \(H\) has bounded source
complexity, nor does it classify infinite-dimensional target algebras with
sublinear degree growth.

## Outcome

The classification succeeds.  On the cusp parametrization,

\[
\left.\operatorname{ad}_H\right|_{H=0}
=-9u^2\frac d{du}.
\]

Its \(N\)-th iterate sends \(u^k\), \(k>0\), to a nonzero multiple of
\(u^{k+N}\).  Therefore \(D^NG=0\) makes the cusp restriction of \(G\)
constant, so \(G-c\) is divisible by \(H\).  Repeating this division proves

\[
\bigcup_{N\ge1}\ker(\operatorname{ad}_H^N)=\mathbb Q[H].
\]

Since \(\operatorname{ad}_H\) raises cusp weight by one, its orbit on every
element of a finite-dimensional invariant polynomial space must terminate.
Thus every finite-dimensional polynomial Hamiltonian algebra containing
\(H\) is contained modulo constants in \(\mathbb Q[H]\), and is abelian.
The exact replay is
[`gauge_cusp_hamiltonian_finite_lie_classification.py`](gauge_cusp_hamiltonian_finite_lie_classification.py).
