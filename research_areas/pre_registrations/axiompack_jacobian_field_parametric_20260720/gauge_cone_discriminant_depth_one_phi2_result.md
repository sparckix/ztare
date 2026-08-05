# The exact \(D^1\) one-\(C\) layer

Put

\[
D=4P^3+27Q^2.
\]

Every admissible multiplier of exact \(D\)-adic depth one has, at fixed
target weight, a unique representative

\[
P^aQ^bD,\qquad a\in\{0,1,2\}.
\]

The cone ranges are \(b\ge3\) for \(a=0\), and \(b\ge4\) for
\(a=1,2\).

## Symbolic terminal transfer

After removing the common source scale \((-1/4)^b\), exact
normal-layer reduction gives

\[
\begin{array}{c|c}
a&[r^{2a+5}z^4]\Omega_3(P^aQ^bDC)\\ \hline
0&-81b/512\\
1&27(9b+20)/2048\\
2&-81(9b+28)/8192.
\end{array}
\]

All three expressions are nonzero in their cone ranges.

Write

\[
\sigma=2a+3b+6.
\]

The zero-grade source letter has exponent
\((\sigma+1,\sigma+3)\), while the cost-three terminal seed has
exponent \((\sigma-1,\sigma+3)\).  The terminal ray is

\[
F_n=u^{\sigma-1+\sigma n}z^{\sigma+3+\sigma n}
\]

at cost \(3+2n\).

Its adjoint multiplier has the form

\[
\alpha_n
=2A\bigl(\sigma(n-1)-3\bigr),
\]

where \(A\ne0\) is the zero-grade coefficient.  The only algebraic zero
is

\[
n=1+\frac3{\sigma},
\]

strictly between one and two.  Hence the adjoint orbit never vanishes
at an integral depth.

## Current quotient

At every positive depth, the five current one-\(C\) columns have a
fixed support pattern.  Offsets \(-4,-3,-2\) lie below the terminal
projection and give three affine directions.  Offsets \(-1,0\) have
nonzero higher normal-two pivots and are forced to zero.  None contains
the normal-four terminal monomial.

The terminal equation is therefore independent of all current freedom.
After division by the adjoint orbit, it is the right-Magnus response

\[
\phi_2(x)
=\frac{x}{e^x-1}\int_0^1t^2e^{t^2x}\,dt.
\]

Its first coefficients are

\[
\frac13,\qquad \frac1{30},\qquad
-\frac1{1260},\qquad -\frac1{1890}.
\]

If

\[
I_0(x)=\int_0^1e^{t^2x}\,dt,\qquad
I_2(x)=\int_0^1t^2e^{t^2x}\,dt,
\]

then

\[
I_2(x)=\frac{e^x-I_0(x)}{2x}.
\]

At \(x=2\pi i\), \(\operatorname{Re}I_0(x)<1\), so
\(I_2(x)\ne0\).  Thus \(\phi_2\) has a nonremovable pole and is not a
polynomial.  Infinitely many terminal coefficients are nonzero.

## Held-out equal-weight replay

For

\[
H_{\rm pre}
=\frac14Q^3DC
=P^3Q^3C+\frac{27}{4}Q^5C,
\]

the complete projected connection gives

\[
\begin{array}{c|c|c}
q&(u,z)\text{-exponent}&[u^az^b]\Omega_q\\ \hline
3&(14,18)&243/131072\\
5&(29,33)&-531441/2684354560\\
7&(44,48)&-129140163/153931627888640\\
9&(59,63)&-31381059609/78812993478983680.
\end{array}
\]

The terminal instantaneous velocity is zero at costs five, seven, and
nine.  The held-out cost-nine coefficient agrees with the
\(\phi_2\) prediction.

The deterministic certificate is
[`gauge_cone_discriminant_depth_one_phi2.py`](gauge_cone_discriminant_depth_one_phi2.py).
Its `--verify-full-projection` mode rebuilds the equal-weight connection
through cost nine.

Therefore every admissible exact-depth-one multiplier excites an
infinite source logarithmic ray of limiting rate \(\sigma\).
Discriminant depth at least two and powers \(C^m\), \(m\ge2\), remain
outside this result.
