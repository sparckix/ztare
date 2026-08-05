# Low-weight target Lie classification pencil

**Status:** exact mixed-pair classification completed

## Eigenquestion

Let

\[
\mathcal S=\langle P^3,PQ,Q^2\rangle
\]

and let

\[
A=P^3+rQ^2,\qquad r\ne0.
\]

Can a finite-dimensional polynomial Hamiltonian Lie algebra contain \(A\)
and a second independent element of \(\mathcal S\)?

This is the remaining lowest-weight target-algebra case behind the
finite-orbit attack.  The already tested affine-normalized lines contain
only one direction in \(\mathcal S\); a two-dimensional exceptional algebra
would evade that line classification.

## Candidate classification

After subtracting a multiple of \(A\), any independent second element has
the form

\[
B=bPQ+dQ^2.
\]

If \(b=0\), the pair separates \(P^3\) and \(Q^2\).  If \(b\ne0\), rescale
and write

\[
B=PQ+\delta Q^2.
\]

The symplectic shear

\[
X=P+\delta Q,\qquad Y=Q
\]

turns \(B\) into \(XY\) and

\[
A=(X-\delta Y)^3+rY^2.
\]

The proposed mechanism is spectral separation under
\(\operatorname{ad}_{XY}\).  Its five possible eigenweights are
\[
3,\ 1,\ -1,\ -3,\ -2,
\]
so polynomial projectors in \(\operatorname{ad}_{XY}\) should recover
\(X^3\) and \(rY^2\) from \(A\), uniformly in \(\delta\).

## Discriminating calculation

1. Verify that the shear preserves the Poisson bracket.
2. Apply the exact Lagrange spectral projectors at weights \(3\) and \(-2\)
   to \(A\).
3. Derive \(X^4\) and \(X^3Y\) from the recovered pair.
4. Prove an infinite monomial ray
   \[
   \operatorname{ad}_{X^3Y}^{\,j}(X^4)
   =c_jX^{4+2j},
   \qquad
   c_{j+1}=(4+2j)c_j.
   \]
5. Check separately the \(b=0\) branch and the parameter values
   \(\delta=0\) and \(r=0\).

## Success and kill conditions

The classification succeeds if every \(r\ne0\) and every independent
second direction in \(\mathcal S\) generate an infinite-dimensional target
Hamiltonian algebra by an exact all-order ray.

It is killed by a nonzero \(r\) and an independent \(B\) for which spectral
separation fails or the recovered monomials close in finite dimension.
The \(r=0\) Borel plane is an expected boundary case and does not kill the
claim.

## Claim boundary

This test classifies only the complete lowest-weight span
\(\mathcal S\).  It does not exclude a finite-dimensional algebra obtained
by adjoining higher seed-isotropy or higher-normal Hamiltonians to the
single mixed line.

## Outcome

The classification succeeds.  In the sheared coordinates the exact
spectral projectors recover

\[
X^3,\qquad rY^2.
\]

They generate \(X^4\) and \(X^3Y\), and

\[
\operatorname{ad}_{X^3Y}^{\,j}(X^4)
=c_jX^{4+2j},
\qquad
c_{j+1}=(4+2j)c_j.
\]

Every coefficient is nonzero in characteristic zero.  Hence a mixed line
\(P^3+rQ^2\), \(r\ne0\), and any independent second direction in
\(\mathcal S\) generate an infinite-dimensional target algebra.  The exact
replay is
[`gauge_low_weight_target_lie_classification.py`](gauge_low_weight_target_lie_classification.py).
