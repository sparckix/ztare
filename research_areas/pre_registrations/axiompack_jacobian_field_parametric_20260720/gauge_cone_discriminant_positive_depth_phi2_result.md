# Every positive \(D\)-adic one-\(C\) layer

Put

\[
D=4P^3+27Q^2.
\]

At fixed target weight, an exact positive-depth multiplier has the
unique form

\[
P^aQ^bD^d,\qquad a\in\{0,1,2\},\quad d\ge1.
\]

The depth-one layer is covered by the separate
[`gauge_cone_discriminant_depth_one_phi2_result.md`](gauge_cone_discriminant_depth_one_phi2_result.md).
The result below treats every \(d\ge2\).

## Symbolic first quotient

Write

\[
\sigma=2a+3b+5d+1.
\]

Generalized-multinomial reduction in all nine
\((a,d\bmod3)\) canonical-control classes gives the cost-three terminal
row

\[
\boxed{
[u^\sigma z^{\sigma+4}]\Omega_3
=
\left(-\frac34\right)^a
\left(-\frac14\right)^b
\left(\frac{27}{8}\right)^d
\frac3{64}\binom d2 }.
\]

After all leading scales are removed, every residue class reduces to
\(-\binom d2/12\).  The displayed coefficient is therefore nonzero for
every integer \(d\ge2\).

The zero-grade cost-two letter is

\[
A=
-\frac94
\left(-\frac34\right)^a
\left(-\frac14\right)^b
\left(\frac{27}{8}\right)^d
u^{\sigma+1}z^{\sigma+3}.
\]

For

\[
F_n=u^{\sigma(n+1)}z^{\sigma(n+1)+4},
\]

direct bracketing gives

\[
[A,F_n]
=2A_0\{\sigma(n-1)-2\}F_{n+1},
\]

where \(A_0\) is the coefficient of \(A\).  Its only algebraic zero is

\[
n=1+\frac2{\sigma},
\]

strictly between one and two.  No integral adjoint depth vanishes.

## Current-column quotient

At cost \(2m+1\), the complete current one-\(C\) row has offsets
\(-4,-3,-2,-1,0\).  In the terminal grading

\[
\Gamma=(-\sigma-2,-\sigma+2),
\]

the first four columns lie below the projection.  Offset zero has a
nonzero higher normal-two pivot at
\((\sigma m+2,\sigma m+4)\), so its coefficient is forced to zero.  Its
support does not contain the terminal monomial
\((\sigma m,\sigma m+4)\).

Thus the terminal equation is independent of all four affine current
directions and receives no later instantaneous input.

## Nonpolynomial Magnus response

After division by the nonzero adjoint orbit, the terminal logarithm is

\[
\phi_2(x)
=\frac{x}{e^x-1}\int_0^1t^2e^{t^2x}\,dt.
\]

Its first coefficients are

\[
\frac13,\qquad\frac1{30},\qquad
-\frac1{1260},\qquad-\frac1{1890}.
\]

If \(I_j(x)=\int_0^1t^je^{t^2x}\,dt\), integration by parts gives

\[
I_2(x)=\frac{e^x-I_0(x)}{2x}.
\]

At \(x=2\pi i\), \(\operatorname{Re}I_0(x)<1\), hence
\(I_2(2\pi i)\ne0\).  The pole of \(\phi_2\) is not removable, so the
terminal coefficient sequence has infinite support.

Consequently every admissible exact-depth-\(d\) one-\(C\) multiplier,
\(d\ge2\), has an unbounded source logarithm.  Its terminal ray has
limiting source rate

\[
\boxed{\sigma/2}.
\]

## Verification and boundary

The symbolic quotient is
[`gauge_cone_discriminant_depth_symbolic.py`](gauge_cone_discriminant_depth_symbolic.py).
The Magnus and current-support certificate is
[`gauge_cone_discriminant_positive_depth_phi2.py`](gauge_cone_discriminant_positive_depth_phi2.py).

Its held-out full replay uses \(D^2Q^5C\).  It gives zero terminal
velocity at costs five and seven and

\[
\begin{aligned}
[u^{52}z^{56}]\Omega_5
&=\frac{100442349}{1374389534720},\\
[u^{78}z^{82}]\Omega_7
&=\frac{31381059609}{180143985094819840},
\end{aligned}
\]

exactly as predicted by \(\phi_2\).

Together with the depth-one theorem and the complete quotient modulo
\(D\), this classifies every nonzero finite one-\(C\) prefix.  Prefixes
involving \(C^m\) for \(m\ge2\) remain outside the theorem.
