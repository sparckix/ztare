# Magnus audit of the moving minimum-section cone

**Status:** exact mixed-orientation prefix through logarithmic order seven

## Eigenquestion

The cone-constrained instantaneous contact passes through the current exact
moving prefix.  What are the degrees and top shells of the corresponding
source and target logarithms?

The distinction is essential.  A bounded-degree rational velocity can have
an unbounded Magnus logarithm, while a velocity profile that rises for a few
orders can later saturate.  Instantaneous source caps therefore cannot be
used as tail-complexity data without the logarithmic calculation.

## Exact finite test

For the complete carried cone prefix:

1. convert derivative-normalized coefficients
   \(V_s=\sum s^jV_j/j!\) and
   \(K_s=\sum s^jK_j/j!\) into ordinary power-series coefficients;
2. solve the target equation \(A'=X A\) with the left-multiplying-velocity
   `dexp⁻¹` recursion and the source equation
   \(\psi'=D\psi\,V\) with the right-multiplying-velocity recursion;
3. use vector-field brackets on the source and Poisson brackets on target
   Hamiltonians;
4. report every nonzero logarithmic coefficient, ordinary degree, top
   homogeneous shell, and exact hash;
5. replay `dexp` back to the carried velocity.

## Counterattacks

- **Orientation error:** bind each recursion to its displayed flow equation
  and round-trip through the matching `dexp`.  The two factors require
  opposite first-bracket signs.
- **Factorial error:** compare ordinary and derivative-normalized series
  explicitly.
- **Finite-prefix overreach:** record only the computed logarithmic prefix.
- **Gauge overreach:** this is one cone-valued connection, not a minimax
  theorem.
- **Source-only ceiling:** remember that the exact source-only velocity has
  spatial degree eleven.  Any extrapolation of the finite minimum-cap
  sequence beyond that ceiling is invalid.

## Success and kill conditions

- A finite result is useful if it separates target and source logarithmic
  growth from their velocity profiles.
- An asymptotic conclusion requires either a finite-dimensional Lie closure
  or an exact nonzero recurrence for the top Magnus shell.
- A vanishing or gauge-dependent top sequence kills that candidate, even if
  velocity degrees increase.

## Intended verification surface

Reuse the existing generic vector-field Magnus recursion.  Add only the
Poisson-Hamiltonian analogue and a round-trip check.  No new campaign branch
or solver category is required.

## Exact prefix result

The replay is
[`gauge_moving_lie_cone_magnus.py`](gauge_moving_lie_cone_magnus.py).
It consumes the exact carried moving connection, converts
derivative-normalized coefficients by \(V_j/j!\), \(K_j/j!\), and passes
the forward-`dexp` round trip on both source and target.

The target factor satisfies \(A'=XA\), so its inverse-`dexp` coefficient
at bracket depth one is \(-1/2\).  The source factor satisfies
\(\psi'=D\psi\,V\), so its coefficient is \(+1/2\).  A shared
equation-typed formal-Lie-series primitive now enforces this distinction.

Through logarithmic order seven, the source component degrees are

\[
\boxed{(5,5,9,11,14,18,22)}.
\]

The corresponding target Hamiltonian degrees are

\[
\boxed{(2,3,3,3,4,4,5)},
\]

so the target derivation-excess degrees are
\((1,2,2,2,3,3,4)\).

In the adapted source coordinates

\[
V=v,\qquad G=t-\frac32v,
\]

the first new high source shells are exactly

\[
\operatorname{top}\Omega^{\rm src}_3
=\frac1{112}W_6,
\qquad
\operatorname{top}\Omega^{\rm src}_4
=\frac{115}{24576}W_7,
\]

where

\[
W_m=
\left(V^mG^{m-3},-V^{m-1}G^{m-2}\right).
\]

These are tangent to the top cusp because \(d(VG)(W_m)=0\).  Hence the
moving source burden is already different from the transverse
\(U_m\)-transfer law.

### Exact top-shell Lie algebra

The two shell families admit a coordinate-free calculation inside the
adapted \((V,G)\) chart.  Put

\[
r=VG,\qquad
E=V\partial_V-G\partial_G,\qquad
R=V\partial_V+G\partial_G.
\]

Then

\[
W_m=V^2r^{m-3}E,
\qquad
U_m=\frac12r^{m-1}\bigl(R+(m+1)E\bigr).
\]

Since \([R,E]=0\), \(E(r)=0\), \(R(r^d)=2d\,r^d\), and
\(E(V^2r^d)=2V^2r^d\), direct substitution gives

\[
\boxed{
\begin{aligned}
[W_m,W_n]&=0,\\
[U_m,W_n]&=(m+n-1)W_{m+n-1},\\
[U_m,U_n]&=(n-m)U_{m+n-1}.
\end{aligned}}
\]

Thus the tangent \(W\)-shells form an abelian ideal acted on by the
transverse \(U\)-shells.  In particular,

\[
\operatorname{ad}_{U_3}^{\,k}W_4
=2^k(3)^{\overline k}W_{4+2k}\ne0
\]

over characteristic zero, and

\[
\deg W_{4+2k}=4k+5.
\]

This identifies a mechanism for the observed \(W_6\) shell: the carried
order-zero shell contains \(W_4\), while the order-one shell contains
\(U_3\).  A word with one \(W_4\) and \(k\) copies of the order-one
\(U_3\) has parameter order \(2k+1\) and spatial degree \(4k+5\).
If its Magnus coefficient survives the complete moving connection, it
would have limiting source rate two.

That last conditional is essential.  Higher instantaneous coefficients
can contribute to the same \(W_{4+2k}\) shell, and the connection has
affine freedom at later orders.  The bracket recurrence proves nonvanishing
of the Lie word, but does not prove nonvanishing of its coefficient in the
fully normalized Magnus logarithm.

The exact orders five through seven already leave this two-family leading
shell.  Their source degrees are \(14,18,22\), and their complete top
coefficients are recorded in
[`gauge_moving_lie_cone_mixed_magnus_result.md`](gauge_moving_lie_cone_mixed_magnus_result.md).
Thus the \(U/W\) algebra identifies a certified submechanism, rather than
the complete leading associated-graded algebra of the selected connection.

### Complete minimum-cap affine check at order two

The order-two instantaneous system at source cap seven has one homogeneous
direction.  Its target Hamiltonian is \(-PQ\), and its source components
have degree seven.  Carrying a symbolic coefficient \(\lambda\) through the
source-flow Magnus recursion leaves the complete degree-nine shell at order three
unchanged: every top coefficient equation is a nonzero constant independent
of \(\lambda\).  Thus no value of this affine parameter cancels
\(W_6/112\).

This is complete only for the declared cap-seven/natural-target window.
The tail statistic permits a more expensive finite prefix, so the result
does not establish prefix-independent escape.

## Interpretation

The complete-affine selected velocity profile
\((5,5,7,9,11,13,14)\) understates the logarithmic cost: the corresponding
source logarithm profile is \((5,5,9,11,14,18,22)\).  Neither list can be
extrapolated: the exact source-only velocity \(K_s=0\) belongs to the cone
and has spatial degree eleven, while later affine choices can alter the
logarithmic shells.

The remaining minimax question is therefore sharper:

1. can a richer finite cone-compatible prefix remove the tangent \(W_m\)
   cascade; or
2. do the complete moving contact and eventual target-symbol rank two force
   a nonzero tangent quotient at infinitely many orders?

A finite connection prefix, even with exact `dexp` replay, answers neither
question by itself.
