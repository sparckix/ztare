# Affine-divisor \(P^3\) orbit pencil

**Status:** candidate excluded by exact all-order bracket ray

## Eigenquestion

Does the regular one-dimensional target control

\[
K_s=a(s)P^3,\qquad
a(s)=
-\frac{192(s^2-3s-8)}
{(s-6)^3(s-4)^2(s+4)^2},
\]

place the moving contact inside a finite-dimensional formal source/target
orbit?

This case is not covered by the translation-normalized
\(\langle P^3,PQ\rangle\) connection or by the scalar
\(H_0+\lambda K_*\) lines.  Its target algebra is one-dimensional and
abelian, while its exact exceptional-divisor restriction is

\[
\frac{s(9s^2y-15s^2-144y+160)}
{3(s-4)^2(s+4)^2}\partial_y,
\]

which lies in the affine algebra
\(\langle\partial_y,y\partial_y\rangle\).

## Candidate mechanism

Let

\[
V_s=V_s^{\rm source}
-a(s)(dF_s)^{-1}X_{P^3}(F_s).
\]

The divisor and target projections have finite-dimensional Lie closure.
The candidate succeeds only if the complete polynomial source coefficient
fields also lie in a fixed finite-dimensional bracket-closed algebra and
their formal flow gives the contact.

## Discriminating calculation

1. Extract the exact source coefficient fields \(V_0,V_1,V_2,\ldots\).
2. Compute their highest nonzero homogeneous shells, including cancellations
   between shell pairs.
3. Search for a bracket word \(C\) and a coefficient field \(A\) whose
   leading weighted Hamiltonians obey a nonzero monomial recurrence
   \[
   \operatorname{top}h_{\operatorname{ad}_A^jC}
   =c_jv^{\alpha+pj}g^{\beta+qj}.
   \]
4. If such a word exists, prove \(c_j\ne0\) for every \(j\); a finite prefix
   alone is not sufficient.

## Success and kill conditions

The finite-orbit candidate survives only with an exact finite bracket table
and an integration identity.  It is excluded if the source projection has a
proved infinite family of nonzero brackets with unbounded polynomial degree.

The calculation is inconclusive if it finds only a growing finite prefix,
uses a divisor quotient in place of the full source field, or assumes that
the maximal possible bracket shell cannot cancel.

## Claim boundary

This pencil tests one regular affine-divisor control already singled out by
the complete divisor image.  It does not classify higher seed-isotropy
Hamiltonians or arbitrary higher-normal target controls.

## Outcome

The candidate is excluded.  The exact replay
[`gauge_affine_divisor_p3_bracket_escape.py`](gauge_affine_divisor_p3_bracket_escape.py)
finds

\[
\operatorname{top}h_{V_0}=\frac18(vg)^6,\qquad
\operatorname{top}h_{V_1}=-\frac3{56}(vg)^7.
\]

The first bracket has radial leading Hamiltonian \((vg)^8/32\), but the
second adjoint exposes the asymmetric shell

\[
\operatorname{top}h_{\operatorname{ad}_{V_0}^2V_1}
=-\frac3{128}v^{11}g^{10}.
\]

Subsequent adjoints have

\[
\operatorname{top}h_j
=c_jv^{11+5j}g^{10+3j},\qquad
c_{j+1}=\frac34(2j+1)c_j.
\]

Every coefficient is nonzero and the source degrees are \(18+8j\).
