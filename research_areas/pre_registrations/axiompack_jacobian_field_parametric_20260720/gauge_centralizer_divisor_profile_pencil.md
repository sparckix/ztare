# Centralizer-valued divisor profile pencil

**Status:** complete finite-target/source-orbit obstruction

## Eigenquestion

Suppose the target connection belongs to a finite-dimensional polynomial
Hamiltonian algebra containing

\[
H_0=-\frac1{36}P^3-\frac14Q^2.
\]

The cusp-Hamiltonian classification reduces that algebra to
\(\mathbb Q[H_0]\).  Which scalar coefficient profiles on \(H_0\) can have
a finite-dimensional source Lie algebra after restriction to the
exceptional divisor?

Higher powers \(H_0^k\), \(k\ge2\), act trivially on the divisor.  Therefore
the divisor connection depends only on the coefficient \(u(s)\) of \(H_0\):

\[
D_s(y)
=S_s(y)-u(s)\,T_s(y),
\qquad u(0)=1,
\]

where \(S_s,T_s\) are exact cubic polynomial vector-field coefficients.

## Candidate classification

A finite-dimensional Lie algebra of polynomial vector fields on a line that
contains a cubic element must be either:

1. a one-dimensional line; or
2. after an affine shift \(z=y-a\), the solvable plane
   \[
   \langle z\partial_z,z^3\partial_z\rangle.
   \]

If the cubic coefficient vanishes identically, the connection belongs to
the degree-at-most-two category; the known scalar profile actually reduces
it to the affine algebra.

For

\[
D_s=c_3(s)y^3+c_2(s)y^2+c_1(s)y+c_0(s),
\]

the shifted cubic plane is characterized by

\[
c_2+3ac_3=0,
\qquad
c_0+ac_1-2a^3c_3=0
\]

for one constant \(a\).

## Discriminating calculation

1. Extract \(S_s,T_s\) exactly from the carried family.
2. Solve \(c_3=0\) and verify the resulting lower-degree connection.
3. Solve the two shifted-cubic-plane identities for \(u(s)\) and constant
   \(a\), including all denominator and seed-regularity conditions.
4. Test the one-dimensional-line alternative by requiring all coefficient
   wedges against the first nonzero parameter coefficient to vanish.
5. For every surviving profile, lift back to the full source connection and
   test its Lie closure with arbitrary higher powers of \(H_0\) kept as the
   remaining freedom.

## Full-source associated-graded attack

For the unique affine scalar profile, use

\[
y=2v+3,\qquad g=1-\frac32v+t.
\]

Every pullback of \(H_0^k\), \(k\ge2\), starts in tangential normal layer
\(g^{3k-3}\), hence in layer at least three.  The first two parameter
coefficients \(A=[s]V_s\) and \(B=[s^2]V_s\) therefore have invariant lower
jets under all higher-centralizer controls:

\[
\operatorname{gr}_0 A=D_{a_0}^{(0)},\qquad
\operatorname{gr}_1 B=D_{b_1}^{(1)}.
\]

The discriminating quotient test is:

1. shift \(z=y-10/9\), the root of the affine coefficient \(a_0\);
2. diagonalize the action of
   \(\operatorname{ad}_{D_{a_0}^{(0)}}\) on layer one;
3. use spectral projectors to isolate two nonzero monomial components
   \(D_{z^4}^{(1)}\) and \(D_{z^3}^{(1)}\) from \(B\);
4. bracket them to obtain a nonzero \(D_{z^6}^{(2)}\);
5. iterate the \(z^4\) component and prove
   \[
   \operatorname{gr}\!
   \left(\operatorname{ad}_{E_4}^{\,j}[E_4,E_3]\right)
   =c_jD_{z^{6+3j}}^{(2+j)}
   \]
   with no zero recurrence coefficient.

Because higher-centralizer additions begin three layers later, they cannot
alter the leading layer of any word in this ray.  Success would exclude
the complete finite-dimensional target-centralizer category, not merely
one selected scalar line.

## Outcome

Both stages succeed.

The divisor replay
[`gauge_centralizer_divisor_profile.py`](gauge_centralizer_divisor_profile.py)
finds the unique cubic-killing profile

\[
u(s)=
\frac{6912(s^2-3s-8)}
{(s-6)^3(s-4)^2(s+4)^2}.
\]

If the cubic remains, its coefficient ratio is

\[
\frac{c_2}{c_3}
=-\frac{5s^2}{(s-4)(s+4)},
\]

which is not the constant required by a shifted cubic Borel plane.  The
fixed-line constraint has rank four, so no one-dimensional cubic profile
survives.

For the unique affine profile, the full-source replay
[`gauge_centralizer_source_lie_escape.py`](gauge_centralizer_source_lie_escape.py)
gives

\[
\operatorname{gr}_0 A=-\frac{9y-10}{48},
\]

\[
\operatorname{gr}_1 B
=-\frac{(y-1)(21y^3+21y^2+5y-31)}{192}.
\]

With \(z=y-10/9\), spectral projectors isolate

\[
E_4=-\frac7{64}z^4,\qquad
E_3=-\frac{35}{72}z^3.
\]

Their seed bracket is

\[
[E_4,E_3]
=-\frac{1225}{18432}D_{z^6}^{(2)}.
\]

Subsequent adjoints obey

\[
\operatorname{gr}\!
\left(\operatorname{ad}_{E_4}^{\,j}[E_4,E_3]\right)
=c_jD_{z^{6+3j}}^{(2+j)},
\]

\[
\frac{c_{j+1}}{c_j}
=-\frac{7(j+6)(2j+1)}{64(j+5)}\ne0.
\]

The source degrees are \(8+4j\).  Hence every finite-dimensional
polynomial target Hamiltonian algebra compatible with the normalized cusp
seed has an infinite-dimensional full-source projection, including all
higher powers of \(H_0\).

This completes the finite-dimensional formal-orbit attack.  It does not
decide the tail minimax over infinite-dimensional coefficientwise-finite
target staircases.

## Success and kill conditions

The divisor classification succeeds if it gives a complete finite list of
regular scalar profiles or proves that the already tested affine profile is
the only one.

It is killed by a distinct regular \(u(s)\) whose divisor coefficient fields
lie in a finite-dimensional polynomial Lie algebra not represented by the
three categories above.

## Claim boundary

The divisor is a necessary-condition quotient.  Even a complete divisor
classification does not decide the full source connection until higher
powers of \(H_0\), which vanish on this quotient, are included.
