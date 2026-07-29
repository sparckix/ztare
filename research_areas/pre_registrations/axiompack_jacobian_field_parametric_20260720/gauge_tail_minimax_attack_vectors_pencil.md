# Tail minimax attack vectors

**Status:** active pencil map for the unrestricted symmetric logarithmic
contact statistic

## Eigenquestion

For coefficientwise-polynomial formal contacts

\[
H_s\circ F_s=F_0\circ\Psi_s,
\]

determine

\[
\sigma_{\rm ct}
=
\inf\limsup_{n\to\infty}
\frac{\max\{e(Y_n),e(X_{K_n})\}}{n}.
\]

The all-prefix source statistic is already exactly two.  The tail statistic
can discard a finite prefix and charges target degree as well, so that result
does not determine \(\sigma_{\rm ct}\).

## Vector A: fixed-rational cusp cascade

The finite-prefix stabilizer calculation gives

\[
\Omega(\tau,\mu)
=
\log\!\left(e^{-\tau X_C}e^{\tau X_{C+\mu B}}\right).
\]

Every coefficient is nonzero over \(\mathbb Q(\mu)\), with exact ordinary
slope \(1/2\).  A prescribed rational amplitude is still open because
different powers of \(\mu\) can cancel.

The diagonal identity

\[
C+\mu B
=4(1-\mu/144)P^3+27(1-\mu/108)Q^2
\]

gives a stronger attack.  If

\[
\mu=\frac{432(r^5-1)}{4r^5-3},
\]

then

\[
C+\mu B=\kappa\,C(rP,r^{-1}Q),
\qquad
\kappa=\frac{1-\mu/144}{r^3}.
\]

For rational \(r\), both \(\mu\) and \(\kappa\) are rational.  The first test
is \(r=2\), giving

\[
\mu=\frac{13392}{125},
\qquad
\kappa=\frac4{125}.
\]

The attack succeeds if the top ordinary coefficient of every
\(\tau^n\)-Hamiltonian is nonzero at this amplitude and admits an all-order
recurrence, sign rule, or valuation proof.

It is killed if an exact coefficient vanishes, if the top coefficient is
not sufficient to detect the Hamiltonian, or if the observed finite prefix
has no recurrence-level explanation.

**Current disposition.**  The specialization \(\mu=144\) gives
\(C+144B=-9Q^2\).  The exact shell algebra

\[
H_{r,s}=P^{2r-s+1}Q^{s-r+1}
\]

reduces the critical coefficients to a two-index recurrence and extends the
nonzero fixed-amplitude prefix through order forty-one.  The even coefficient
is \(9(k+2)\) times its preceding odd coefficient at every order.  The
remaining odd recurrence is triangular but not scalar: a Wick rotation
removes the Bernoulli sign alternation, while an explicit mixed-shell
counterexample shows that the full positive coefficient cone is not
invariant.  Vector A remains open at that correlated-positivity step.

## Vector B: coefficientwise-finite staircase

The completed canonical target normalizer has infinitely many transverse
weights in its coefficient of \(s\), so it is excluded from
\(\mathbb Q[P,Q][[s]]\).  A valid alternative must distribute target
weights over increasing parameter orders while retaining polynomial source
coefficients.

Represent the support by points

\[
(n,m)
=
(\text{parameter order},\text{transverse layer}).
\]

Coefficientwise polynomiality says every row \(n\) is finite.  The canonical
normalizer occupies infinitely many points in row \(1\); the source-only
contact occupies finitely many points in every row but its Magnus logarithm
has slope two.

The attack succeeds with either:

1. a recursive locally finite staircase whose source and target logarithmic
   excesses both have slope below two; or
2. a scheduling inequality showing that every locally finite staircase
   must reproduce an infinite subsequence of the source or target critical
   shell.

It is killed by a repeated same-order target tail, a source lift failure, an
uncontrolled BCH word, or an inequality that bounds only a finite prefix.

**Current disposition.**  \(s\)-adic causality excludes delaying the
infinitely supported canonical first row: the mismatch is already visible
modulo \(s^2\).  The canonical row's size-three \(3/2\)-Jordan realization
also does not arise as an adjoint module of the complete cap-seven
first-order contact fiber.  That fiber is not adjoint-invariant, and positive
source filtration makes any finite-support graded adjoint action nilpotent.
A distinct coupled recursion is still possible; it must begin with a
polynomial first row and cannot be interpreted as a reindexing of the
completed canonical normalizer.

## Vector C: finite-dimensional orbit test

The family coefficients are rational in \(s\), and the reciprocal escaping
root can be flattened to \(s/(s+4)\) by an identity-normalized generator
change.  This raises a direct countermodel test: perhaps \(F_s\) is contained,
after rational reparameterization, in a finite-dimensional algebraic
source/target orbit whose logarithm has bounded spatial degree.

The attack searches for a constant or finite-dimensional Lie-algebra-valued
connection after exact source/target gauge, rather than fitting finite jets.

It succeeds only with an exact orbit identity or a bracket-closed connection
and a proved integration statement.  It is killed by an associated-graded
class outside every proposed finite-dimensional orbit, or by bracket growth
that survives the complete target image.

**Current disposition.**  Generic function-field degree excludes algebraic
polynomial orbits, and the reciprocal-root translation has an explicit
unbounded coefficient family.  For coefficientwise formal flows, the exact
\(\langle P^3,PQ\rangle\) connection has a nonzero source bracket ray of
degrees \(18+8j\).  The normalized abelian line has a separate ray of degrees
\(24+10j\), and the same calculation excludes every affine-normalized
weight-three line \(H_0+\lambda K_*\), including its two exceptional
parameters.  Vector C now survives only for higher seed-isotropy target
algebras or non-affine exceptional-divisor profiles.

## Consolidation rule

Finite prefixes are orientation evidence only.  A promoted conclusion about
\(\sigma_{\rm ct}\) requires an all-order construction or an infinite
gauge-independent obstruction.  The completed canonical recurrence and the
second transverse quotient are inputs to these attacks; neither is promoted
alone to the minimax conclusion.
