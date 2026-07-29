# Hamiltonian jet escape for the normalized cubic lift

**Status:** pre-run pencil for
`H-AXIOMPACK-JACOBIAN-JETS-20260720-09`

## Eigenquestion

The public cubic weighted-lift line has generic degree four away from its
degree-three seed, but its first derivative is a polynomial target-coordinate
motion.  At which formal jet does the family first leave the orbit of
polynomial source and target coordinate changes?

## Fixed coordinates

Use

\[
\gamma=1-\frac32v+t,\qquad P_s=\gamma\beta_s,\qquad
Q_s=\gamma^2\alpha_s,
\]

with the same rational normalization as the complete-shell calculation.  At
the seed,

\[
\begin{aligned}
\beta_0={}&-3tv^2-6tv-3t+\frac92v^3+6v^2+\frac12v,\\
\alpha_0={}&-2tv^3-6tv^2-6tv-2t+3v^4+7v^3+4v^2.
\end{aligned}
\]

Independent differentiation of the rational family should give

\[
\dot\beta=-\frac12\gamma\alpha_0,
\qquad
\dot\alpha=\frac1{12}\beta_0^2.
\]

Equivalently,

\[
(\dot P,\dot Q)=\left(-\frac12Q_0,\frac1{12}P_0^2\right)
=X_H(P_0,Q_0),
\]

where

\[
H(P,Q)=-\frac14Q^2-\frac1{36}P^3,
\qquad X_H=(\partial_QH,-\partial_PH).
\]

This identity must be checked from the independently differentiated family;
defining the tangent by the right-hand side would make the test circular.

## Second-jet mechanism

For a target isotopy generated initially by `X_H`, the forced second
derivative is

\[
X_H^2(P,Q)=\left(-\frac1{24}P^2,-\frac1{12}PQ\right).
\]

If the generator is allowed to vary with the parameter, its first variation
adds an arbitrary Hamiltonian field `X_K`.  Since the first-order source
generator in the exact decomposition is zero, a second-order source shear
adds

\[
f(\gamma)D_\gamma(P_0,Q_0),
\qquad D_\gamma=\partial_v+\frac32\partial_t,
\]

the derivative at fixed `gamma`.  Therefore the correct residual is

\[
\mathcal R=
\left(
\ddot P+\frac1{24}P_0^2,
\ddot Q+\frac1{12}P_0Q_0
\right),
\]

and the membership question is

\[
\mathcal R\stackrel{?}{=}
X_K(P_0,Q_0)+f(\gamma)D_\gamma(P_0,Q_0).
\]

This subtracts the Lie-square term before testing orbit membership.  Testing
the raw second derivative would confuse curvature of a coordinate orbit with
departure from it.

## Complete bounded test

Generate target monomials `K=P^i Q^j` by increasing weighted bound
`i+2j<=W` and source shears `f=gamma^m` by increasing `m`.  For every bound:

1. expand both components of every generator in the full `(v,t)` coefficient
   universe;
2. include every coordinate appearing in either a generator or the residual;
3. solve exact rational membership in that full matrix;
4. if membership holds, retain one exact decomposition and advance to the
   next jet;
5. if it fails, extract an exact left-kernel functional that annihilates the
   generator matrix and evaluates nonzero on the residual;
6. require the rank, membership verdict, and obstruction value to stabilize
   over successive bounds.

Higher-bound generators may not be projected into the residual support by
deleting their extra coefficients.  Any cancellation must occur in the full
expanded matrix.

## Candidate theorem or obstruction

The predicted outcome is a second-order obstruction: a rational functional
`ell` with

\[
\ell(X_K(P_0,Q_0))=0,
\quad
\ell(f(\gamma)D_\gamma(P_0,Q_0))=0,
\quad
\ell(\mathcal R)\ne0
\]

for the stabilized bounded generator family.  If the residual instead has an
exact decomposition, the prediction is rejected and the contact order is
advanced.  That negative result is useful: it says the public generic-degree
jump is invisible to at least two formal coordinate jets.

## Kill conditions

- any tangent identity is assumed rather than derived from the normalized
  family;
- the Lie-square term is omitted or uses the coefficient of `s^2` in place
  of the second derivative;
- the generator set is selected from the observed residual;
- out-of-support coefficients are discarded before membership;
- rank or membership is numerical;
- a bounded obstruction is promoted to a classification of all equivariant
  Keller maps;
- the public generic-degree result is counted as a new finding.

## Intended formal surface

The kernel surface should contain only the terminal finite certificate:
first-derivative Hamiltonian identities and either an exact second-jet
decomposition or a primitive integer left-kernel obstruction.  Symbolic
family differentiation and coefficient extraction remain deterministic
replay evidence bound to that certificate.
