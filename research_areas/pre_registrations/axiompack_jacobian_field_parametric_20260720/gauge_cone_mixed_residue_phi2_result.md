# Mixed one-\(C\) residue classes modulo \(4P^3+27Q^2\)

## Symbolic cost-three transfer

At fixed cusp weight, let

\[
D=4P^3+27Q^2.
\]

Every multiplier class modulo \(D\) has a representative
\(P^aQ^b\) with \(a\in\{0,1,2\}\).  The \(a=0\) class is the
pure-\(Q\) family.  For the other two classes, exact symbolic
normal-layer reduction gives

\[
\boxed{
[u^{3b+1}z^{3b+5}]\Omega_3(PQ^bC)
=\frac{(-1)^{b+1}9b}{2^{2b+7}}}
\qquad(b\ge4),
\]

and

\[
\boxed{
[u^{3b+3}z^{3b+7}]\Omega_3(P^2Q^bC)
=\frac{(-1)^b27b}{2^{2b+9}}}
\qquad(b\ge3).
\]

Neither coefficient vanishes in its declared range.

## Nonpolynomial response

The current normalizer has zero terminal velocity at costs five and
seven in both representative checks.  The terminal logarithm is the
right-Magnus response

\[
\phi_2(x)
=\frac{x}{e^x-1}\int_0^1t^2e^{t^2x}\,dt.
\]

Its first coefficients are

\[
[x^0]\phi_2=\frac13,\qquad
[x^1]\phi_2=\frac1{30},\qquad
[x^2]\phi_2=-\frac1{1260}.
\]

The full projected replays for \(PQ^4C\) and \(P^2Q^3C\) agree through
cost seven.

The associated adjoint multipliers can vanish only at

\[
k=\frac{3b+7}{3(b+1)}
\]

for the \(a=1\) class, or

\[
k=\frac{3(b+3)}{3b+5}
\]

for the \(a=2\) class.  Each value lies strictly between one and two, so
no integral bracket depth is killed.

Finally, put

\[
I_0(x)=\int_0^1e^{t^2x}\,dt,\qquad
I_2(x)=\int_0^1t^2e^{t^2x}\,dt.
\]

Integration by parts gives

\[
I_2(x)=\frac{e^x-I_0(x)}{2x}.
\]

At \(x=2\pi i\), the real part of \(I_0\) is strictly less than one,
because \(\cos(2\pi t^2)<1\) on a set of positive measure.  Hence
\(I_2(2\pi i)\ne0\), and \(\phi_2\) has a nonremovable pole there.
It therefore has infinitely many nonzero coefficients.

The resulting limiting source rates are \(3b+3\) for \(PQ^bC\) and
\(3b+5\) for \(P^2Q^bC\).

## Verification and boundary

The symbolic and response replay is
[`gauge_cone_mixed_residue_phi2.py`](gauge_cone_mixed_residue_phi2.py).
This completes the stable non-pure residue classes modulo \(D\).
The low representatives \(PQ^2C,PQ^3C\) and multipliers divisible by a
positive power of \(D\) remain separate.
