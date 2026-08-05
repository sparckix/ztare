# Every finite \(D\)-adic one-\(C\) layer

Let

\[
D=4P^3+27Q^2
\]

and consider an exact-depth-\(r\) multiplier

\[
P^aQ^bD^rC,\qquad a\in\{0,1,2\},\qquad r\ge2.
\]

Cone compatibility is equivalent to

\[
2b\ge a+3r+3.
\]

## Saturated cost-three quotient

In the fixed source chart, the three \(D\)-jet coefficients that reach
the saturated normal-four quotient are

\[
[D_0]_{(5,0)}=\frac{27}{8},\qquad
[D_0]_{(2,2)}=-\frac9{16},\qquad
[D_1]_{(7,0)}=\frac{27}{128}.
\]

Here the pair labels are radial degree and normal order.  Relative to
the leading \(D_0\) coefficient, the parameter-raising and normal-two
deficit factors are

\[
\frac{27/128}{27/8}=\frac1{16},
\qquad
\frac{-9/16}{27/8}=-\frac16.
\]

Their product is \(-1/96\).

One marked \(D\)-factor supplies the parameter-raising term and a
distinct factor supplies the radial-deficit/normal-two term.  There are

\[
r(r-1)
=x^{2-r}\frac{d^2}{dx^2}x^r
\]

ordered choices.  All single-factor and unmarked contributions lie in
the radial/current image.  Therefore, if \(A_{a,b,r}\) is the
zero-grade coefficient, the saturated cost-three seed is

\[
\boxed{
B_{a,b,r}
=-\frac{r(r-1)}{96}A_{a,b,r}.}
\]

The zero-grade coefficient is

\[
A_{a,b,r}
=\frac{(-1)^{a+b+1}3^{a+3r+2}}
{2^{2a+2b+3r+2}},
\]

so both \(A_{a,b,r}\) and \(B_{a,b,r}\) are nonzero in characteristic
zero.

## Terminal ray and current independence

Put

\[
\sigma=2a+3b+5r+1.
\]

The saturated ray is

\[
F_n
=u^{\sigma(n+1)}z^{\sigma(n+1)+4}
\]

at cost \(3+2n\).  Its adjoint multiplier is

\[
\alpha_n
=2A_{a,b,r}\bigl(\sigma(n-1)-2\bigr).
\]

The only algebraic zero is

\[
n=1+\frac2{\sigma}.
\]

Since \(\sigma\ge29\), this is strictly between one and two and is not
an integral depth.

At each later current row, offsets below zero fall outside the
saturated projection.  Offset zero has a nonzero normal-two pivot
strictly above the terminal and is forced to zero; any positive offsets
are eliminated first by still higher pivots.  No current column
contains \(F_n\).  The terminal coefficient is consequently independent
of all affine current freedom.

## Common all-order response

After division by the nonzero adjoint orbit, the logarithm is

\[
\phi_2(x)
=\frac{x}{e^x-1}\int_0^1t^2e^{t^2x}\,dt.
\]

At \(x=2\pi i\), integration by parts gives

\[
I_2(2\pi i)
=\frac{1-I_0(2\pi i)}{4\pi i}\ne0,
\]

because \(\operatorname{Re}I_0(2\pi i)<1\).  Hence \(\phi_2\) has a
nonremovable pole and infinitely many nonzero coefficients.  Every
exact-depth-\(r\ge2\) class therefore excites an infinite source
logarithmic ray of limiting rate \(\sigma\).

## Independent fixed-depth checks

For

\[
H_r=4^{-r}Q^{3r}D^rC,
\]

the complete projected replays give:

\[
\begin{array}{c|c|c}
r&[F_0]\Omega_3&[F_1]\Omega_5\\ \hline
2&
\dfrac{2187}{268435456}&
\dfrac{444816117}{22517998136852480}\\[2mm]
3&
-\dfrac{177147}{549755813888}&
\dfrac{282429536481}{18889465931478580854784}\\[2mm]
4&
\dfrac{4782969}{562949953421312}&
\dfrac{1349730754842699}{
198070406285660843983859875840}\\[2mm]
5&
-\dfrac{215233605}{1152921504606846976}&
\dfrac{405811421358553179}{
166153499473114484112975882535043072}.
\end{array}
\]

Every cost-five terminal velocity is zero.  The \(r=5\) row is the
held-out odd-depth check that distinguishes the exact
\(-r(r-1)/96\) ratio from the earlier parity interpolation.

The deterministic certificate is
[`gauge_cone_discriminant_finite_depth_phi2.py`](gauge_cone_discriminant_finite_depth_phi2.py).
Its `--verify-depth R` option reconstructs any selected fixed-depth
representative through cost five; \(R=2\) was rerun after the uniform
certificate was encoded.

Together with the separate depth-zero and depth-one results, this
classifies every nonzero finite one-\(C\) multiplier: take its finite
\(D\)-adic valuation and its nonzero residue class at that depth.  The
first non-\(D\)-divisible coefficient has the source-leading symbol and
cannot be canceled by higher \(D\)-adic terms.

Powers \(C^m\), \(m\ge2\), remain outside the theorem.
